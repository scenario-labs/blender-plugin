# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Reference upload orchestration on the selected JobSession, without another pool."""

import tempfile
import time
import uuid
from dataclasses import dataclass
from pathlib import Path

import bpy

from ..core.api.errors import ScenarioError
from ..core.jobs.upload_store import UploadState
from ..core.jobs.workers import WorkerError
from .job_session import SessionBusy

_IMAGE_TYPES = {
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
}


def capture_upload(context, *, source="VIEWPORT", camera=None):
    """Capture into private temporary storage retained through asynchronous staging."""
    from . import capture, runtime

    if source not in {"VIEWPORT", "CAMERA", "RENDER"}:
        raise ScenarioError(0, "Choose viewport, camera or render result")
    owner = runtime.ensure_reference_uploads()
    if not runtime.online():
        raise ScenarioError(0, "Allow Online Access before uploading a reference")
    directory = tempfile.TemporaryDirectory(prefix="reference-", dir=runtime.paths().state_dir)
    try:
        path = Path(directory.name) / "reference.png"
        if source == "RENDER":
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
            capture.capture_still(
                context, path, source=source, camera=camera, width=1280, height=720
            )
        return owner.start(context.scene, path, temporary=directory)
    except BaseException:
        directory.cleanup()
        raise


@dataclass
class ReferenceUpload:
    identifier: str
    task: object
    command: str = "prepare_upload"
    record: object = None
    error: str | None = None
    next_poll: float = 0.0
    retry_admission_at: float = 0.0


class ReferenceUploads:
    """Keep transient progress handles; durable state belongs to the shared store."""

    def __init__(self, session, *, online):
        self.session, self._online = session, online
        self.references = {}
        self._recovering = set()
        self.forms = {}

    def start(self, scene, path, *, temporary=None):
        """Upload the chosen image once; this action never quotes or generates."""
        try:
            if not self._online():
                raise ScenarioError(0, "Allow Online Access before uploading a reference")
            if len(self.references) >= 128:
                raise ScenarioError(
                    0, "Reference upload capacity reached; inspect existing uploads"
                )
            path = Path(path)
            content_type = _IMAGE_TYPES.get(path.suffix.lower())
            if content_type is None:
                raise ScenarioError(0, "Choose a supported image reference format")
            if scene != bpy.context.scene:
                raise ScenarioError(0, "Select the originating scene before uploading")
            bpy.context.view_layer.update()
            origin = self.session.capture(scene)
            task = self.session.prepare_upload(
                path, origin=origin, kind="image", content_type=content_type
            )
            if temporary is not None:
                self.session.retain_upload_capture(task, temporary)
            ticket = ReferenceUpload(uuid.uuid4().hex, task)
            self.references[ticket.identifier] = ticket
            return ticket
        except BaseException:
            if temporary is not None:
                temporary.cleanup()
            raise

    def poll(self):
        if not self.session.active:
            return
        for ticket in tuple(self.references.values()):
            if ticket.task is not None:
                if not ticket.task.done():
                    continue
                try:
                    completion = self.session.drain(task=ticket.task)[0]
                    if completion.error is not None:
                        raise completion.error
                    ticket.record = self.session.inspect_upload(completion.result.intent.request_id)
                    ticket.next_poll = time.monotonic() + 2.0
                except Exception:
                    ticket.error = "Upload stopped; inspect saved progress before trying again"
                    if ticket.record is not None:
                        ticket.record = self.session.inspect_upload(ticket.record.intent.request_id)
                finally:
                    ticket.task = None
            if ticket.error or ticket.record is None or not self._online():
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
        for ticket in self.references.values():
            if ticket.task is None and ticket.record is not None:
                if ticket.record.intent.request_id == record.intent.request_id:
                    ticket.record = record
                    if record.state in {UploadState.IMPORTED, UploadState.PROCESSING}:
                        ticket.error = None
                        ticket.next_poll = time.monotonic() + 2.0

    def begin_recovery(self, request_id):
        if request_id in self._recovering:
            raise ScenarioError(0, "Recovery is already running for this upload")
        self._recovering.add(request_id)

    def end_recovery(self, request_id):
        self._recovering.discard(request_id)
