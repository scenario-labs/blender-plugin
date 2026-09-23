# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Explicit shared-job ownership and guarded main-thread delivery.

Registration installs invalidation hooks only. No connection, worker or second
runtime starts until an integration explicitly creates a JobSession.
"""

import logging
import threading
import uuid
from dataclasses import dataclass, field
from weakref import WeakValueDictionary

import bpy
from bpy.app.handlers import persistent

from ..core.jobs.coordinator import JobCoordinator, RemoteSnapshot
from ..core.jobs.origins import OriginRevisions
from ..core.jobs.workers import JobWorkers

_log = logging.getLogger("scenario.jobs")
_sessions = set()
_sessions_lock = threading.Lock()
_registered = False


def _main_thread():
    if threading.current_thread() is not threading.main_thread():
        raise RuntimeError("Blender job contexts must be used on the main thread")


class OriginUnavailable(RuntimeError):
    """The result is available for review but cannot be applied automatically."""


@dataclass(frozen=True, eq=False)
class JobCompletion:
    origin: object
    result: object = field(default=None, repr=False)
    error: Exception | None = field(default=None, repr=False)


class JobSession:
    """One explicit connection/store owner, independent of view lifetime.

    Callers retain task handles or drain completions from a GUI pump/headless
    loop. Delivery is synchronous and never called from worker threads. It is
    an origin guard, not a durable import transaction or an OAuth identity source.
    """

    def __init__(self, adapter, store, *, workers=2, pending_limit=16, completion_limit=128):
        _main_thread()
        if not _registered:
            raise RuntimeError("Register Blender lifecycle hooks before creating a session")
        if type(completion_limit) is not int or completion_limit < 1:
            raise ValueError("Use a positive completion limit")
        self._completion_limit = completion_limit
        self._origins = OriginRevisions()
        self._scenes = {}
        self._targets = {}
        self._target_scenes = {}
        self._pending = []
        self._issued = WeakValueDictionary()
        self._active = True
        self._coordinator = JobCoordinator(adapter, store, origin_guard=self._origins.guard)
        self._workers = JobWorkers(self._coordinator, workers=workers, pending_limit=pending_limit)
        with _sessions_lock:
            _sessions.add(self)
        try:
            if not bpy.app.timers.is_registered(_reap_inactive):
                bpy.app.timers.register(_reap_inactive, first_interval=0.25, persistent=True)
        except BaseException:
            self.shutdown()
            raise

    @property
    def scope(self):
        return self._coordinator.scope

    @staticmethod
    def _identity(records, value):
        for identity, existing in records.items():
            if existing is value:
                return identity
        identity = uuid.uuid4().hex
        records[identity] = value
        return identity

    def capture(self, scene, target=None):
        _main_thread()
        if not self._active:
            raise OriginUnavailable("This job context is inactive")
        try:
            if scene not in tuple(bpy.data.scenes):
                raise OriginUnavailable("The originating scene is unavailable")
            if target is not None and target not in tuple(scene.objects):
                raise OriginUnavailable("The target is not in the originating scene")
        except ReferenceError:
            raise OriginUnavailable("The original scene or target was removed") from None
        scene_id = self._identity(self._scenes, scene)
        target_id = self._identity(self._targets, target) if target is not None else None
        if target_id is not None:
            self._target_scenes.setdefault(target_id, set()).add(scene_id)
        return self._origins.capture(scene_id, target_id)

    def prepare(self, estimate, *, origin):
        """Use the origin captured with inputs before requesting the estimate."""
        _main_thread()
        self._resolve(origin)
        return self._coordinator.prepare(estimate, origin)

    def _check_capacity(self):
        if len(self._pending) >= self._completion_limit:
            raise RuntimeError("Drain completed job outcomes before adding more commands")

    def submit(self, prepared, *, operation, target_id, payload):
        _main_thread()
        self._check_capacity()
        self._resolve(prepared.intent.origin)
        if prepared.intent.scope != self.scope:
            raise OriginUnavailable("The request belongs to another connection")
        task = self._workers.submit(
            prepared,
            origin=prepared.intent.origin,
            operation=operation,
            target_id=target_id,
            payload=payload,
        )
        self._pending.append((task, prepared.intent.origin))
        return task

    def refresh_remote(self, request_id, *, expected_revision):
        _main_thread()
        self._check_capacity()
        records = self._coordinator.recovery_plan()
        record = next(
            (item.record for item in records if item.record.intent.request_id == request_id), None
        )
        if record is None:
            raise OriginUnavailable("The job is not in this connection's store")
        task = self._workers.refresh_remote(request_id, expected_revision=expected_revision)
        self._pending.append((task, record.intent.origin))
        return task

    def drain(self):
        """Return ready outcomes without applying them or waiting for network I/O."""
        _main_thread()
        completions = []
        for task, origin in tuple(self._pending):
            if not task.done():
                continue
            self._pending.remove((task, origin))
            try:
                result = task.result()
                record = result.record if isinstance(result, RemoteSnapshot) else result
                if record.intent.origin != origin or record.intent.scope != self.scope:
                    raise OriginUnavailable("Worker returned a different job origin or scope")
            except Exception as exc:
                completion = JobCompletion(origin, error=exc)
            else:
                completion = JobCompletion(origin, result=result)
            self._issued[id(completion)] = completion
            completions.append(completion)
        return tuple(completions)

    def _resolve(self, origin):
        if not self._active or not self._origins.current(origin):
            raise OriginUnavailable("Origin changed; review the result before explicit application")
        scene = self._scenes.get(origin.scene_id)
        target = self._targets.get(origin.target_id) if origin.target_id else None
        try:
            if scene not in tuple(bpy.data.scenes) or scene != bpy.context.scene:
                raise OriginUnavailable("The originating scene is unavailable or not selected")
            if origin.target_id and (target is None or target not in tuple(scene.objects)):
                raise OriginUnavailable("The original target is unavailable")
        except ReferenceError:
            raise OriginUnavailable("The original scene or target was removed") from None
        return scene, target

    def deliver(self, completion, callback):
        """Deliver once on the main thread, rechecking context immediately before use.

        Callback receives the captured scene/target, never the current selection.
        Failed or stale outcomes remain caller-owned for manual recovery review.
        """
        _main_thread()
        if self._issued.get(id(completion)) is not completion:
            raise OriginUnavailable("Use an unconsumed completion from this session")
        if completion.error is not None:
            raise completion.error
        scene, target = self._resolve(completion.origin)
        del self._issued[id(completion)]
        return callback(completion.result, scene, target)

    def prune_missing_scenes(self):
        """Prune deleted scene/target references and invalidate their captured origins."""
        _main_thread()
        live_scenes = tuple(bpy.data.scenes)
        for scene_id, scene in tuple(self._scenes.items()):
            try:
                present = scene in live_scenes
            except ReferenceError:
                present = False
            if not present:
                self._origins.invalidate(scene_id)
                del self._scenes[scene_id]
                for scene_ids in self._target_scenes.values():
                    scene_ids.discard(scene_id)
        # Reading the captured RNA reference checks liveness in O(captured
        # targets), without scanning all scene objects or resolving a name.
        # Unlinked but still live datablocks remain eligible for explicit reuse.
        for target_id, target in tuple(self._targets.items()):
            try:
                _ = target.name
            except ReferenceError:
                for scene_id in self._target_scenes.pop(target_id, ()):
                    self._origins.invalidate(scene_id)
                del self._targets[target_id]

    def invalidate_scene(self, scene):
        _main_thread()
        for scene_id, existing in self._scenes.items():
            if existing is scene:
                self._origins.invalidate(scene_id)

    def invalidate_all(self):
        _main_thread()
        self._origins.reset()
        self._scenes.clear()
        self._targets.clear()
        self._target_scenes.clear()

    def deactivate(self):
        _main_thread()
        self._active = False
        self.invalidate_all()
        self._workers.deactivate()

    def shutdown(self):
        _main_thread()
        self.deactivate()
        try:
            self._workers.shutdown()
        finally:
            # A failed SDK close occurs after joining. Release local ownership
            # then, but retain it if a control exception interrupted live workers.
            if self._workers.stopped:
                self._pending.clear()
                self._issued.clear()
                with _sessions_lock:
                    _sessions.discard(self)


def _session_snapshot():
    with _sessions_lock:
        return tuple(_sessions)


def _reap_inactive():
    """Close retired connections once their tracked network work has finished."""
    _main_thread()
    for session in _session_snapshot():
        try:
            session.prune_missing_scenes()
            if not session._active and all(task.done() for task, _ in session._pending):
                session.shutdown()
        except Exception:
            # Do not include transport errors/tracebacks that may contain secrets.
            # An ordinary cleanup failure must not cancel Blender's timer service.
            _log.warning("Scenario job session cleanup failed")
    return 0.25 if _session_snapshot() else None


@persistent
def _load_pre(_):
    for session in _session_snapshot():
        session.deactivate()


@persistent
def _scene_changed(scene, depsgraph=None):
    # Rendering can invoke frame/dependency handlers on a render thread. Never
    # inspect bpy data there: conservatively invalidate the pure revision state.
    if threading.current_thread() is not threading.main_thread():
        for session in _session_snapshot():
            session._origins.reset()
        return
    sessions = _session_snapshot()
    # A deleted scene cannot emit its own update. Inspect all captured scenes
    # even when the surviving scene's depsgraph has no evaluated changes.
    for session in sessions:
        session.prune_missing_scenes()
    if depsgraph is None or any(depsgraph.updates):
        for session in sessions:
            session.invalidate_scene(scene)


@persistent
def _frame_change_pre(scene, depsgraph=None):
    # The supplied depsgraph has not been evaluated yet; frame invalidation
    # must not depend on its update collection. Render threads use the same
    # pure-state fallback as dependency handlers.
    _scene_changed(scene)


@persistent
def _history_pre(_):
    for session in _session_snapshot():
        session.invalidate_all()


_HOOKS = (
    (bpy.app.handlers.load_pre, _load_pre),
    (bpy.app.handlers.depsgraph_update_post, _scene_changed),
    (bpy.app.handlers.frame_change_pre, _frame_change_pre),
    (bpy.app.handlers.undo_pre, _history_pre),
    (bpy.app.handlers.redo_pre, _history_pre),
)


def register():
    global _registered
    _main_thread()
    for handlers, callback in _HOOKS:
        if callback not in handlers:
            handlers.append(callback)
    _registered = True


def unregister():
    global _registered
    _main_thread()
    try:
        for session in _session_snapshot():
            try:
                session.shutdown()
            except Exception:
                _log.warning("Scenario job session cleanup failed")
    finally:
        try:
            if bpy.app.timers.is_registered(_reap_inactive):
                bpy.app.timers.unregister(_reap_inactive)
        finally:
            for handlers, callback in _HOOKS:
                if callback in handlers:
                    handlers.remove(callback)
            _registered = False
