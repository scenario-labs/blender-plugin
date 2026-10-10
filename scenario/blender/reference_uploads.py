# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Reference upload orchestration on the selected JobSession, without another pool."""

import tempfile
import time
import uuid
from collections import deque
from dataclasses import dataclass
from pathlib import Path
from weakref import WeakSet

import bpy

from ..core.api.errors import ScenarioError
from ..core.jobs.upload_store import UploadState
from ..core.jobs.uploads import UploadPlanUnavailable, UploadRecoveryAction
from ..core.jobs.workers import WorkerError
from .job_session import OriginUnavailable, SessionBusy

# Explicit extension policy follows the Scenario multipart upload guide. It
# chooses metadata, not a decoder or a claim that every model accepts the file.
_REFERENCE_TYPES = {
    "image": {
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".webp": "image/webp",
        ".gif": "image/gif",
        ".avif": "image/avif",
        ".tif": "image/tiff",
        ".tiff": "image/tiff",
        ".heic": "image/heic",
        ".heif": "image/heif",
        ".svg": "image/svg+xml",
    },
    "audio": {
        ".mp3": "audio/mpeg",
        ".wav": "audio/wav",
        ".ogg": "audio/ogg",
        ".m4a": "audio/m4a",
    },
    "video": {".mp4": "video/mp4", ".webm": "video/webm"},
    "3d": {
        ".glb": "model/gltf-binary",
        ".gltf": "model/gltf+json",
        ".obj": "model/obj",
        ".fbx": "application/vnd.autodesk.fbx",
        ".stl": "model/stl",
        ".ply": "model/ply",
        ".vox": "model/x-3d-vox",
    },
}


class UploadNotStarted(ScenarioError):
    """Local validation or queue admission failed before any task was accepted."""


def capture_upload(context, *, source="VIEWPORT", camera=None, force_solid=False):
    """Capture into private temporary storage retained through asynchronous staging."""
    from . import capture, mesh_export, mesh_provenance, runtime

    if source not in {"VIEWPORT", "CAMERA", "RENDER", "MESH", "VIEWPORT_CLIP", "CAMERA_CLIP"}:
        raise UploadNotStarted(0, "Choose a viewport, camera, render result or selected mesh")
    owner = runtime.ensure_reference_uploads()
    if not runtime.online():
        raise UploadNotStarted(0, "Allow Online Access before uploading a reference")
    directory = tempfile.TemporaryDirectory(prefix="reference-", dir=runtime.paths().state_dir)
    admitting = False
    origin, mesh_source = None, None
    try:
        kind, suffix = (
            ("3d", ".glb")
            if source == "MESH"
            else ("video", ".mp4")
            if source.endswith("_CLIP")
            else ("image", ".png")
        )
        path = Path(directory.name) / ("reference" + suffix)
        if source == "MESH":
            objects = mesh_export.source_objects(context)
            if not objects:
                raise ScenarioError(0, "Select a mesh before uploading its snapshot")
            origin, mesh_source = mesh_provenance.export_with_source(
                context, objects, path, owner.session
            )
        elif source == "RENDER":
            image = bpy.data.images.get("Render Result")
            if image is None or not image.has_data:
                raise ScenarioError(0, "Render an image before uploading the render result")
            settings = capture.RenderSettings.snapshot(context.scene)
            depth = context.scene.render.image_settings.color_depth
            try:
                capture.set_image_output(context.scene.render, "PNG")
                image.save_render(str(path), scene=context.scene)
            finally:
                settings.restore(context.scene)
                context.scene.render.image_settings.color_depth = depth
        else:
            if bpy.app.background:
                raise ScenarioError(0, "Viewport and camera captures require the Blender GUI")
            capture_fn = capture.capture_playblast if kind == "video" else capture.capture_still
            capture_fn(
                context,
                path,
                source=source.removesuffix("_CLIP"),
                camera=camera,
                width=1280,
                height=720,
                force_solid=force_solid,
            )
        admitting = True
        return owner.start(
            context.scene,
            path,
            kind=kind,
            temporary=directory,
            origin=origin,
            mesh_source=mesh_source,
        )
    except BaseException as error:
        directory.cleanup()
        if not admitting and isinstance(error, Exception):
            reason = (
                error.reason
                if isinstance(error, ScenarioError)
                else "Could not prepare the reference snapshot"
            )
            raise UploadNotStarted(0, reason) from None
        raise


@dataclass
class ReferenceUpload:
    identifier: str
    task: object
    scene: object
    command: str = "prepare_upload"
    record: object = None
    error: str | None = None
    next_poll: float = 0.0
    retry_admission_at: float = 0.0


@dataclass(eq=False)
class UploadRecovery:
    request_id: str
    task: object = None
    record: object = None
    error: str | None = None
    done: bool = False
    # Restart only: the scene that receives the replacement upload handle.
    scene: object = None
    reference_id: str | None = None
    replacement: object = None


class ReferenceUploads:
    """Keep transient progress handles; durable state belongs to the shared store."""

    def __init__(self, session, *, online):
        self.session, self._online = session, online
        self.references = {}
        self._recovering = {}
        self._recoveries = WeakSet()
        self.saved = {}
        self.saved_actions = {}
        self.recovery_errors = {}
        self.forms = {}
        self.form_errors = deque(maxlen=16)
        self.attachments = {}

    def start(
        self,
        scene,
        path,
        *,
        kind="image",
        temporary=None,
        origin=None,
        mesh_source=None,
        expected_sha256=None,
    ):
        """Upload the chosen typed reference once; never quote or generate."""
        task = None
        try:
            if not self._online():
                raise ScenarioError(0, "Allow Online Access before uploading a reference")
            if len(self.references) >= 128:
                raise ScenarioError(
                    0, "Reference upload capacity reached; inspect existing uploads"
                )
            path = Path(path)
            if not isinstance(kind, str) or kind not in _REFERENCE_TYPES:
                raise ScenarioError(0, "Choose image, audio, video or 3d as the reference kind")
            content_type = _REFERENCE_TYPES[kind].get(path.suffix.lower())
            if content_type is None:
                raise ScenarioError(0, f"Choose a supported {kind} reference format")
            if scene != bpy.context.scene:
                raise ScenarioError(0, "Select the originating scene before uploading")
            bpy.context.view_layer.update()
            if origin is None:
                origin = self.session.capture(scene)
            else:
                self.session.validate_destination(origin)
            task = self.session.prepare_upload(
                path,
                origin=origin,
                kind=kind,
                content_type=content_type,
                mesh_source=mesh_source,
                expected_sha256=expected_sha256,
            )
            if temporary is not None:
                self.session.retain_upload_capture(task, temporary)
            ticket = ReferenceUpload(uuid.uuid4().hex, task, scene)
            self.references[ticket.identifier] = ticket
            return ticket
        except BaseException as error:
            if temporary is not None:
                temporary.cleanup()
            if task is None and isinstance(error, Exception):
                reason = (
                    error.reason
                    if isinstance(error, ScenarioError)
                    else "Upload could not start; check the reference and try again"
                )
                raise UploadNotStarted(0, reason) from None
            raise

    def poll(self):
        if not self.session.active:
            return
        self._poll_recoveries()
        completed = False
        for ticket in tuple(self.references.values()):
            if ticket.task is not None:
                if not ticket.task.done():
                    continue
                completed = True
                try:
                    completion = self.session.drain(task=ticket.task)[0]
                    if completion.error is not None:
                        raise completion.error
                    ticket.record = self.session.inspect_upload(completion.result.intent.request_id)
                    ticket.next_poll = time.monotonic() + 2.0
                except UploadPlanUnavailable:
                    ticket.error = (
                        "Upload cannot continue in this session; restart it from saved uploads"
                    )
                    if ticket.record is not None:
                        ticket.record = self.session.inspect_upload(ticket.record.intent.request_id)
                except Exception:
                    ticket.error = "Upload stopped; inspect saved progress before trying again"
                    if ticket.record is not None:
                        ticket.record = self.session.inspect_upload(ticket.record.intent.request_id)
                finally:
                    ticket.task = None
                if ticket.record is not None:
                    self.saved[ticket.record.intent.request_id] = ticket.record
            if ticket.error or ticket.record is None or not self._online():
                continue
            # A timer can run with another window's scene (or no scene). Pause
            # admission until the origin is selected; unchanged-origin checks
            # still run in JobSession before any next command.
            if ticket.scene != bpy.context.scene:
                continue
            record = ticket.record
            if record.intent.request_id in self._recovering:
                continue
            if time.monotonic() < ticket.retry_admission_at:
                continue
            command = None
            if record.state == UploadState.PREPARED:
                command = "initialize_upload"
            elif record.state == UploadState.UPLOADING and record.active_part is None:
                command = (
                    "finalize_upload"
                    if len(record.receipts) == len(record.intent.part_sha256)
                    else "transfer_upload_part"
                )
            elif record.state == UploadState.PROCESSING and time.monotonic() >= ticket.next_poll:
                command = "refresh_upload"
            if command:
                try:
                    ticket.task = getattr(self.session, command)(
                        record.intent.request_id, expected_revision=record.revision
                    )
                    ticket.command = command
                except (WorkerError, SessionBusy):
                    # This call did not enqueue anything. It is safe to try
                    # admission later; never use this branch for task failures.
                    ticket.retry_admission_at = time.monotonic() + 0.25
                except Exception:
                    ticket.error = (
                        "The upload origin changed or work could not start; inspect saved progress"
                    )
        if completed:
            self._observe_actions()
        if self.forms:
            from .reference_form import deliver

            deliver(self)

    def status(self, identifier):
        self.poll()
        ticket = self.references.get(identifier)
        if ticket is None:
            raise ScenarioError(0, "This reference handle is unavailable; inspect saved uploads")
        record = ticket.record
        return {
            "reference_id": identifier,
            "request_id": record.intent.request_id if record else None,
            "revision": record.revision if record else None,
            "state": record.state.value if record else "failed" if ticket.error else "staging",
            "asset_id": record.asset_id if record else None,
            "kind": record.intent.kind if record else None,
            "content_type": record.intent.content_type if record else None,
            "error": ticket.error,
            "pending": ticket.task is not None,
        }

    def imported(self, identifier):
        """Return an asset only for attachment into the unchanged originating scene."""
        status = self.status(identifier)
        ticket = self.references[identifier]
        if status["error"] or status["state"] != "imported":
            raise ScenarioError(0, "The reference has not finished uploading")
        self.session.validate_destination(ticket.record.intent.origin)
        return ticket.record.asset_id

    def observe_saved(self, record):
        """Reflect explicit recovery without authorizing another mutation attempt."""
        self.saved[record.intent.request_id] = record
        for ticket in self.references.values():
            if ticket.task is None and ticket.record is not None:
                if ticket.record.intent.request_id == record.intent.request_id:
                    ticket.record = record
                    if record.state in {UploadState.IMPORTED, UploadState.PROCESSING}:
                        ticket.error = None
                        ticket.next_poll = time.monotonic() + 2.0
        self._observe_actions()

    def inspect_saved(self):
        items = self.session.upload_recovery_plan()
        self.saved = {item.record.intent.request_id: item.record for item in items}
        self.saved_actions = {item.record.intent.request_id: item.action for item in items}
        return tuple(item.record for item in items)

    def _observe_actions(self):
        """Keep inspected suggestions current on the main thread; draw() only reads them.

        A transfer can stop or a recovery finish while saved uploads are open.
        Records and actions come from one recovery plan, the same eligibility
        check a restart repeats. A failed read hides every suggestion until a
        new inspection.
        """
        if not self.saved_actions:
            return
        try:
            items = self.session.upload_recovery_plan()
        except Exception:
            self.saved_actions = {}
            return
        self.saved.update((item.record.intent.request_id, item.record) for item in items)
        self.saved_actions = {item.record.intent.request_id: item.action for item in items}

    def recover(self, request_id, expected_revision, action):
        commands = {
            "refresh": "refresh_upload",
            "cancel_prepared": "cancel_prepared_upload",
            "cleanup": "discard_upload_source",
            "restart": "restart_upload",
        }
        if action not in commands:
            raise ValueError("Choose refresh, cancel_prepared, cleanup or restart")
        if type(expected_revision) is not int or expected_revision < 0:
            raise ValueError("expected_revision must be a nonnegative integer")
        if request_id in self._recovering:
            raise ScenarioError(0, "Recovery is already running for this upload")
        command = UploadRecovery(request_id)
        self._recoveries.add(command)
        self._recovering[request_id] = command
        self.recovery_errors.pop(request_id, None)
        try:
            if action == "restart":
                result = self._restart(request_id, expected_revision, command)
            else:
                result = getattr(self.session, commands[action])(
                    request_id, expected_revision=expected_revision
                )
            if action == "cancel_prepared":
                command.record = result
                self.observe_saved(result)
                command.done = True
                del self._recovering[request_id]
            else:
                command.task = result
        except BaseException:
            del self._recovering[request_id]
            raise
        return command

    def _restart(self, request_id, expected_revision, command):
        """Queue an explicit restart; the replacement then advances like a new upload."""
        if not self._online():
            raise ScenarioError(0, "Allow Online Access before uploading a reference")
        if len(self.references) >= 128:
            raise ScenarioError(0, "Reference upload capacity reached; inspect existing uploads")
        item = next(
            (
                item
                for item in self.session.upload_recovery_plan()
                if item.record.intent.request_id == request_id
            ),
            None,
        )
        if item is None or item.record.revision != expected_revision:
            raise ScenarioError(0, "This upload changed or is not saved for this connection")
        if item.action != UploadRecoveryAction.RESTART_UPLOAD:
            raise ScenarioError(0, "Only an upload that cannot continue can be uploaded again")
        record = item.record
        scene = bpy.context.scene
        bpy.context.view_layer.update()
        try:
            # Keep the original origin, and any captured-mesh provenance, only
            # while it still identifies the selected scene and target.
            self.session.validate_destination(record.intent.origin)
            origin = record.intent.origin
        except OriginUnavailable:
            origin = self.session.capture(scene)
        command.scene = scene
        return self.session.restart_upload(
            request_id, expected_revision=expected_revision, origin=origin
        )

    def _poll_recoveries(self):
        for request_id, command in tuple(self._recovering.items()):
            if command.task is None or not command.task.done():
                continue
            try:
                completion = self.session.drain(task=command.task)[0]
                if completion.error is not None:
                    raise completion.error
                if command.scene is not None:
                    replacement = self.session.inspect_upload(completion.result.intent.request_id)
                    ticket = ReferenceUpload(
                        uuid.uuid4().hex,
                        None,
                        command.scene,
                        command="restart_upload",
                        record=replacement,
                    )
                    self.references[ticket.identifier] = ticket
                    self.saved[replacement.intent.request_id] = replacement
                    command.reference_id, command.replacement = ticket.identifier, replacement
                command.record = self.session.inspect_upload(request_id)
                self.observe_saved(command.record)
            except Exception:
                command.error = "Upload recovery failed; inspect its saved state"
                self.recovery_errors[request_id] = command.error
            finally:
                command.done = True
                del self._recovering[request_id]

    def recovery_result(self, command):
        if command not in self._recoveries or not self.session.active:
            raise ScenarioError(0, "The upload recovery context changed")
        self._poll_recoveries()
        if not command.done:
            raise ScenarioError(0, "Upload recovery is still running")
        if command.error:
            raise ScenarioError(0, command.error)
        return command.record
