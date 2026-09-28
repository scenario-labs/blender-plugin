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
from weakref import WeakKeyDictionary, WeakValueDictionary

import bpy
from bpy.app.handlers import persistent

from ..core.jobs.coordinator import JobCoordinator, OriginQuote, RemoteSnapshot
from ..core.jobs.origins import OriginRevisions
from ..core.jobs.results import VerifiedResults
from ..core.jobs.store import JobOrigin, StoredJob
from ..core.jobs.workers import JobWorkers
from .image_application import ImageApplicationError, apply_images
from .media_application import MediaApplicationError, apply_media
from .world_application import PanoramaError, WorldApplication, WorldApplicationError, apply_world

_log = logging.getLogger("scenario.jobs")
_sessions = set()
_sessions_lock = threading.Lock()
_registered = False


def _main_thread():
    if threading.current_thread() is not threading.main_thread():
        raise RuntimeError("Blender job contexts must be used on the main thread")


class OriginUnavailable(RuntimeError):
    """The result is available for review but cannot be applied automatically."""


class SessionBusy(RuntimeError):
    """Admission did not queue work because completed outcomes still need draining."""


class ImageResultUncertain(RuntimeError):
    """Images may already exist; retry only the saved receipt, never the mutation."""

    def __init__(self, images=()):
        super().__init__("Image application outcome is uncertain; inspect saved job and images")
        self.images = images


class MediaResultUncertain(RuntimeError):
    """A strip may already exist; only its persistence receipt may be retried."""

    def __init__(self, application=None):
        super().__init__("Media application needs inspection; do not insert it again")
        self.application = application


@dataclass(frozen=True)
class AppliedMedia:
    record: StoredJob
    application: object = field(repr=False)


@dataclass(frozen=True)
class AppliedImages:
    record: StoredJob
    images: tuple = field(repr=False)


class WorldResultUncertain(RuntimeError):
    """Inspect the saved job and scene before acting; never repeat application.

    When available, ``application`` retains the primitive's guarded restoration
    handle. Restoring it does not resolve or rewrite the saved job state.
    """

    def __init__(self, application: WorldApplication | None = None):
        super().__init__("World application outcome is uncertain; inspect the saved job and scene")
        self.application = application


@dataclass(frozen=True, eq=False)
class JobCompletion:
    origin: object
    result: object = field(default=None, repr=False)
    error: Exception | None = field(default=None, repr=False)


@dataclass(frozen=True)
class AppliedWorldResult:
    record: StoredJob
    application: WorldApplication = field(repr=False)


class JobSession:
    """One explicit connection/store owner, independent of view lifetime.

    Callers retain task handles or drain completions from a GUI pump/headless
    loop. Delivery is synchronous and never called from worker threads. It is
    an origin guard, not a durable import transaction or an OAuth identity source.
    """

    def __init__(
        self,
        adapter,
        store,
        *,
        workers=2,
        pending_limit=16,
        completion_limit=128,
        result_downloader=None,
        result_root=None,
        upload_store=None,
        upload_sources=None,
        part_uploader=None,
    ):
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
        self._world_receipts = WeakKeyDictionary()
        self._image_receipts = WeakKeyDictionary()
        self._media_receipts = WeakKeyDictionary()
        self._upload_captures = {}
        self._active = True
        self._coordinator = JobCoordinator(
            adapter,
            store,
            origin_guard=self._origins.guard,
            result_downloader=result_downloader,
            result_root=result_root,
            upload_store=upload_store,
            upload_sources=upload_sources,
            part_uploader=part_uploader,
        )
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

    @property
    def active(self):
        return self._active

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

    def quote_model(self, identifier, parameters, *, origin):
        return self._quote("model", identifier, parameters, origin)

    def quote_workflow(self, identifier, parameters, *, origin):
        return self._quote("workflow", identifier, parameters, origin)

    def quote_prompt(self, parameters, *, origin):
        return self._quote("prompt", "prompt", parameters, origin)

    def _quote(self, operation, identifier, parameters, origin):
        _main_thread()
        self._check_capacity()
        self._resolve(origin)
        if operation == "prompt":
            task = self._workers.quote_prompt(parameters, origin=origin)
        else:
            task = getattr(self._workers, f"quote_{operation}")(
                identifier, parameters, origin=origin
            )
        self._pending.append((task, origin))
        return task

    def prepare_quote(self, quote):
        _main_thread()
        if not isinstance(quote, OriginQuote):
            raise OriginUnavailable("Use a quote from this session")
        self._resolve(quote.origin)
        return self._coordinator.prepare_quote(quote)

    def prepare(self, estimate, *, origin):
        """Use the origin captured with inputs before requesting the estimate."""
        _main_thread()
        self._resolve(origin)
        return self._coordinator.prepare(estimate, origin)

    def _check_capacity(self):
        if len(self._pending) >= self._completion_limit:
            raise SessionBusy("Drain completed job outcomes before adding more commands")

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
        return self._record_command("refresh_remote", request_id, expected_revision)

    def recovery_plan(self):
        """Inspect this connection's saved jobs without resolving old Blender targets."""
        _main_thread()
        return self._coordinator.recovery_plan()

    def cancel_prepared(self, request_id, *, expected_revision):
        """Persist local cancellation now, even while the command queue is full."""
        _main_thread()
        return self._workers.cancel_prepared(request_id, expected_revision=expected_revision)

    def cancel_remote(self, request_id, *, expected_revision):
        """Queue explicit known model-job cancellation under its original scope."""
        return self._record_command("cancel_remote", request_id, expected_revision)

    def load_results(self, request_id, *, expected_revision):
        """Queue SDK metadata retrieval into the original job's durable manifest."""
        return self._record_command("load_results", request_id, expected_revision)

    def download_results(self, request_id, *, expected_revision):
        """Queue an explicit download using the configured private storage policy."""
        return self._record_command("download_results", request_id, expected_revision)

    def verify_results(self, request_id, *, expected_revision):
        """Queue local receipt verification; this does not authorize application."""
        return self._record_command("verify_results", request_id, expected_revision)

    def recover_downloads(self, request_id, *, expected_revision):
        """Queue explicit offline reconciliation without resolving or applying old targets."""
        return self._record_command("recover_downloads", request_id, expected_revision)

    def prepare_upload(self, source, *, origin, kind, content_type):
        """Stage a reference for the origin captured with its source, off the main thread."""
        _main_thread()
        self._check_capacity()
        self._resolve(origin)
        task = self._workers.prepare_upload(
            source, origin=origin, kind=kind, content_type=content_type
        )
        self._pending.append((task, origin))
        return task

    def inspect_upload(self, request_id):
        """Read scoped saved metadata without resolving an old Blender target."""
        _main_thread()
        return self._coordinator.inspect_upload(request_id)

    def retain_upload_capture(self, task, temporary):
        """Keep a private capture alive until staging ends, including retirement."""
        _main_thread()
        if not any(pending is task for pending, _ in self._pending):
            raise OriginUnavailable("Use this session's pending upload preparation")
        self._upload_captures[task] = temporary

    def _cleanup_upload_capture(self, task):
        temporary = self._upload_captures.get(task)
        if temporary is not None:
            try:
                temporary.cleanup()
            except OSError:
                _log.warning("Scenario upload capture cleanup failed; retained for cleanup")
            else:
                del self._upload_captures[task]

    def upload_recovery_plan(self):
        _main_thread()
        return self._coordinator.upload_recovery_plan()

    def initialize_upload(self, request_id, *, expected_revision):
        return self._upload_command("initialize_upload", request_id, expected_revision)

    def cancel_prepared_upload(self, request_id, *, expected_revision):
        """Cancel local upload intent even with a full queue or unavailable origin."""
        _main_thread()
        return self._workers.cancel_prepared_upload(request_id, expected_revision=expected_revision)

    def transfer_upload_part(self, request_id, *, expected_revision):
        return self._upload_command("transfer_upload_part", request_id, expected_revision)

    def finalize_upload(self, request_id, *, expected_revision):
        return self._upload_command("finalize_upload", request_id, expected_revision)

    def refresh_upload(self, request_id, *, expected_revision):
        return self._upload_command("refresh_upload", request_id, expected_revision, recover=True)

    def discard_upload_source(self, request_id, *, expected_revision):
        """Queue explicit cleanup of a finished upload's verified private snapshot."""
        return self._upload_command(
            "discard_upload_source", request_id, expected_revision, recover=True
        )

    def _upload_command(self, command, request_id, expected_revision, *, recover=False):
        _main_thread()
        self._check_capacity()
        record = self.inspect_upload(request_id)
        if record is None:
            raise OriginUnavailable("The upload is not in this connection's store")
        if not recover:
            self._resolve(record.intent.origin)
        task = getattr(self._workers, command)(request_id, expected_revision=expected_revision)
        self._pending.append((task, record.intent.origin))
        return task

    def _record_command(self, command, request_id, expected_revision):
        _main_thread()
        self._check_capacity()
        records = self.recovery_plan()
        record = next(
            (item.record for item in records if item.record.intent.request_id == request_id), None
        )
        if record is None:
            raise OriginUnavailable("The job is not in this connection's store")
        task = getattr(self._workers, command)(request_id, expected_revision=expected_revision)
        self._pending.append((task, record.intent.origin))
        return task

    def drain(self, *, task=None):
        """Return ready outcomes without applying them or waiting for network I/O."""
        _main_thread()
        completions = []
        selected = task
        for task, origin in tuple(self._pending):
            if (selected is not None and task is not selected) or not task.done():
                continue
            self._pending.remove((task, origin))
            try:
                result = task.result()
                record = (
                    result.record
                    if isinstance(result, (RemoteSnapshot, VerifiedResults))
                    else result
                )
                if isinstance(record, OriginQuote):
                    matches = record.origin == origin and record.scope == self.scope
                else:
                    matches = record.intent.origin == origin and record.intent.scope == self.scope
                if not matches:
                    raise OriginUnavailable("Worker returned a different job origin or scope")
            except Exception as exc:
                completion = JobCompletion(origin, error=exc)
            else:
                completion = JobCompletion(origin, result=result)
            finally:
                self._cleanup_upload_capture(task)
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

    def apply_images(self, completion):
        return self._apply_images(completion)

    def apply_recovered_images(self, completion, *, destination):
        """Import into an explicitly approved captured destination after recovery."""
        _main_thread()
        if not isinstance(destination, JobOrigin):
            raise OriginUnavailable("Capture and approve the image import destination")
        return self._apply_images(completion, destination=destination)

    def validate_destination(self, destination, *, frame=None):
        """Check a previously captured application destination without recapturing it."""
        _main_thread()
        if not isinstance(destination, JobOrigin):
            raise OriginUnavailable("Capture and approve the application destination")
        scene, _ = self._resolve(destination)
        if frame is not None and (type(frame) is not int or scene.frame_current != frame):
            raise OriginUnavailable("The destination frame changed; review it again")

    def _apply_images(self, completion, *, destination=None):
        _main_thread()
        if self._issued.get(id(completion)) is not completion:
            raise OriginUnavailable("Use an unconsumed verification from this session")
        if completion.error is not None:
            raise completion.error
        verified = completion.result
        if not isinstance(verified, VerifiedResults):
            raise OriginUnavailable("Verify the saved images before applying them")
        self._resolve(destination or completion.origin)
        before = set(bpy.data.images)
        del self._issued[id(completion)]
        claim = (
            self._coordinator.claim_application(verified)
            if destination is None
            else self._coordinator.claim_recovered_application(verified, destination)
        )
        try:
            images = apply_images(verified)
        except ImageApplicationError:
            if set(bpy.data.images) != before:
                raise ImageResultUncertain() from None
            try:
                self._coordinator.fail_application(claim)
            except Exception:
                raise ImageResultUncertain() from None
            raise
        except Exception:
            raise ImageResultUncertain() from None
        try:
            record = self._coordinator.complete_application(claim)
        except Exception:
            outcome = ImageResultUncertain(images)
            self._image_receipts[outcome] = (claim, images)
            raise outcome from None
        return AppliedImages(record, images)

    def retry_image_receipt(self, outcome):
        _main_thread()
        if not isinstance(outcome, ImageResultUncertain) or outcome not in self._image_receipts:
            raise OriginUnavailable("Use a pending image receipt from this session")
        claim, images = self._image_receipts[outcome]
        try:
            record = self._coordinator.retry_application_receipt(claim)
        except Exception:
            raise outcome from None
        del self._image_receipts[outcome]
        return AppliedImages(record, images)

    def apply_recovered_media(self, completion, *, destination, asset_id, frame):
        """Apply one selected asset to the approved scene/frame after verification."""
        _main_thread()
        if self._issued.get(id(completion)) is not completion:
            raise OriginUnavailable("Use an unconsumed media verification from this session")
        if completion.error is not None:
            raise completion.error
        verified = completion.result
        if not isinstance(verified, VerifiedResults) or not isinstance(destination, JobOrigin):
            raise OriginUnavailable("Verify the media and approve its destination")
        scene, _ = self._resolve(destination)
        if type(frame) is not int or scene.frame_current != frame:
            raise OriginUnavailable("The destination frame changed; review it again")
        selected = [
            (item, path)
            for item, path in zip(verified.record.results, verified.paths, strict=True)
            if item.asset.asset_id == asset_id
        ]
        if len(selected) != 1:
            raise OriginUnavailable("Select one saved media asset")
        item, path = selected[0]
        del self._issued[id(completion)]
        claim = self._coordinator.claim_recovered_application(verified, destination)
        try:
            application = apply_media(scene, item, path, frame=frame)
        except MediaApplicationError:
            try:
                self._coordinator.fail_application(claim)
            except Exception:
                raise MediaResultUncertain() from None
            raise
        except Exception:
            raise MediaResultUncertain() from None
        try:
            record = self._coordinator.complete_application(claim)
        except Exception:
            outcome = MediaResultUncertain(application)
            self._media_receipts[outcome] = (claim, application)
            raise outcome from None
        return AppliedMedia(record, application)

    def retry_media_receipt(self, outcome):
        _main_thread()
        if not isinstance(outcome, MediaResultUncertain) or outcome not in self._media_receipts:
            raise OriginUnavailable("Use a pending media receipt from this session")
        claim, application = self._media_receipts[outcome]
        try:
            record = self._coordinator.retry_application_receipt(claim)
        except Exception:
            raise outcome from None
        del self._media_receipts[outcome]
        return AppliedMedia(record, application)

    def apply_world(self, completion, *, asset_id):
        """Apply one explicitly selected panorama from an owned verification.

        This synchronous main-thread command claims the original job before
        touching Blender. It neither generates, downloads nor saves a blend file.
        """
        _main_thread()
        if (
            not isinstance(completion, JobCompletion)
            or self._issued.get(id(completion)) is not completion
        ):
            raise OriginUnavailable("Use an unconsumed completion from this session")
        if completion.error is not None:
            raise completion.error
        verified = completion.result
        if not isinstance(verified, VerifiedResults):
            raise OriginUnavailable("Verify the saved results before applying a panorama")
        selected = [
            (item, path)
            for item, path in zip(verified.record.results, verified.paths, strict=True)
            if item.asset.asset_id == asset_id
        ]
        if len(selected) != 1:
            raise OriginUnavailable("Select one panorama from this job's saved results")
        item, path = selected[0]
        scene, _ = self._resolve(completion.origin)
        previous = scene.world
        worlds, images = set(bpy.data.worlds), set(bpy.data.images)
        # Consumption precedes the durable claim: a storage failure can occur
        # after committing APPLYING. Never reuse this completion to infer safety.
        del self._issued[id(completion)]
        claim = self._coordinator.claim_application(verified)
        try:
            application = apply_world(scene, path, expected_receipt=item.receipt)
        except (WorldApplicationError, PanoramaError):
            try:
                restored = (
                    scene in tuple(bpy.data.scenes)
                    and scene.world == previous
                    and set(bpy.data.worlds) == worlds
                    and set(bpy.data.images) == images
                )
            except Exception:
                restored = False
            if not restored:
                raise WorldResultUncertain() from None
            try:
                self._coordinator.fail_application(claim)
            except Exception:
                raise WorldResultUncertain() from None
            raise
        except Exception:
            raise WorldResultUncertain() from None
        try:
            record = self._coordinator.complete_application(claim)
        except Exception:
            # The World is already applied. Keep its restoration handle, but do
            # not repeat/undo scene mutation merely because persistence failed.
            outcome = WorldResultUncertain(application)
            self._world_receipts[outcome] = (claim, application)
            raise outcome from None
        return AppliedWorldResult(record, application)

    def retry_world_receipt(self, outcome):
        """Save a known completed World assignment without reading or changing Blender."""
        _main_thread()
        if not isinstance(outcome, WorldResultUncertain) or outcome not in self._world_receipts:
            raise OriginUnavailable("Use a pending World receipt from this session")
        claim, application = self._world_receipts[outcome]
        try:
            record = self._coordinator.retry_application_receipt(claim)
        except Exception:
            raise outcome from None
        del self._world_receipts[outcome]
        return AppliedWorldResult(record, application)

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
                for task in tuple(self._upload_captures):
                    self._cleanup_upload_capture(task)
                self._pending.clear()
                self._issued.clear()
                self._world_receipts.clear()
                self._image_receipts.clear()
                self._media_receipts.clear()
                with _sessions_lock:
                    _sessions.discard(self)


def _session_snapshot():
    with _sessions_lock:
        return tuple(_sessions)


def reap_retired():
    """Service retired owners on main-thread headless loops as well as GUI ticks."""
    _reap_inactive()


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
