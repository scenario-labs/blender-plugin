# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Film capture approval and upload handoff on the existing selected job owner."""

import json
import logging
import tempfile
import uuid
from dataclasses import dataclass, field
from pathlib import Path

import bpy

from ..core.jobs.coordinator import LocalCaptureResult
from ..core.jobs.local_render import RenderSpec, media_tools
from ..core.jobs.upload_store import UploadState
from ..core.scene.film_plan import require_plan_scope
from . import film_jobs, film_scene, local_capture
from .film_application import _main_thread

_log = logging.getLogger("scenario.film_capture")


@dataclass(frozen=True)
class _Source:
    scene: object
    camera: object
    origin: object
    binding: tuple
    shot: dict
    digest: str
    fps: int


@dataclass(eq=False)
class _Review:
    identifier: str
    scene: object
    origin: object
    source: _Source
    spec: RenderSpec
    source_name: str
    phase: str = "READY"
    temporary: object = field(default=None, repr=False)
    task: object = field(default=None, repr=False)
    completion: object = field(default=None, repr=False)
    media: object = field(default=None, repr=False)
    upload: object = field(default=None, repr=False)
    error: str = ""


class FilmCaptureCommands:
    """Session-local reviews; no second executor, persistent registry or automatic upload."""

    def __init__(self, session):
        self.session = session
        self._sources, self._reviews = {}, {}

    def _recipe(self, scene):
        if not self.session.active:
            raise ValueError("The Film connection changed")
        try:
            if scene != bpy.context.scene or scene.library or scene.override_library:
                raise ValueError("Select the current local Film recipe scene")
            binding = film_jobs.snapshot(scene)
        except ReferenceError:
            raise ValueError("The Film recipe scene was removed") from None
        plan, digest = film_scene.timeline_recipe(json.loads(binding[1]), binding[0])
        require_plan_scope(plan, self.session.scope)
        return binding, plan, digest

    def inspect(self, scene, *, shot_id):
        _main_thread()
        binding, plan, digest = self._recipe(scene)
        shot = next((s for s in plan["shots"] if s["id"] == shot_id), None)
        if shot is None:
            raise ValueError("Choose a shot in the current recipe")
        sources, choices = {}, []
        for candidate in bpy.data.scenes:
            if not film_scene.matching_shot(
                candidate, production_id=binding[0], digest=digest, shot=shot, fps=plan["fps"]
            ):
                continue
            if len(sources) >= 256:
                raise ValueError("Keep at most 256 matching shot scenes")
            identifier = uuid.uuid4().hex
            sources[identifier] = _Source(
                candidate,
                candidate.camera,
                self.session.capture(candidate, candidate.camera),
                binding,
                shot,
                digest,
                plan["fps"],
            )
            choices.append({"source_id": identifier, "scene": candidate.name})
        self._sources = sources
        return {
            "shot_id": shot_id,
            "choices": choices,
            "frames": shot["frames"],
            "fps": plan["fps"],
            "source_duration": shot["source_duration"],
            "source_trim": shot["source_trim"],
        }

    def _check(self, review, *, selected=False):
        if not self.session.active or not self.session._origins.current(review.origin):
            raise ValueError("The capture recipe or connection changed")
        source = review.source
        try:
            valid = (
                review.scene in tuple(bpy.data.scenes)
                and not review.scene.library
                and not review.scene.override_library
                and film_jobs.snapshot(review.scene) == source.binding
                and self.session._origins.current(source.origin)
                and film_scene.matching_shot(
                    source.scene,
                    production_id=source.binding[0],
                    digest=source.digest,
                    shot=source.shot,
                    fps=source.fps,
                )
                and source.scene.camera == source.camera
            )
        except ReferenceError:
            valid = False
        if not valid:
            raise ValueError("The recipe or selected shot changed; prepare another capture")
        if selected:
            self.session.validate_destination(review.origin)

    def prepare(
        self,
        scene,
        *,
        shot_id,
        source_id,
        kind="VIDEO",
        width=1280,
        height=720,
        color_type="MATERIAL",
    ):
        _main_thread()
        film_scene._main_thread()
        binding, _, _ = self._recipe(scene)
        source = self._sources.get(source_id)
        if source is None or source.binding != binding or source.shot["id"] != shot_id:
            raise ValueError("Use a source from the current capture inspection")
        self.poll()
        if len(self._reviews) >= 8:
            raise ValueError("Discard a previous capture review before preparing another")
        for old in self._reviews.values():
            try:
                same = old.scene == scene and old.source.shot["id"] == shot_id
            except ReferenceError:
                same = False
            if same and old.phase in {
                "READY",
                "RENDERING",
                "WAITING",
                "CANCELLING",
                "CAPTURED",
                "UPLOADING",
            }:
                raise ValueError("Finish or discard this shot's existing capture first")
        # A settings-only specification validates without exporting the scene.
        root = Path(
            bpy.utils.extension_path_user(__package__.rsplit(".", 1)[0], path="state", create=True)
        ).resolve()
        spec = RenderSpec(
            root,
            Path(bpy.app.binary_path).resolve(),
            Path(local_capture.__file__).with_name("render_worker.py").resolve(),
            source.scene.name,
            "0" * 64,
            1,
            1 if kind == "STILL" else source.shot["frames"],
            source.fps,
            width,
            height,
            kind,
            color_type,
        )
        if kind == "VIDEO":
            media_tools()
        review = _Review(
            uuid.uuid4().hex, scene, self.session.capture(scene), source, spec, source.scene.name
        )
        self._check(review, selected=True)
        self._reviews[review.identifier] = review
        return self.status(review.identifier)

    def _get(self, identifier):
        review = self._reviews.get(identifier)
        if review is None:
            raise ValueError("The Film capture review is unavailable")
        return review

    def approve(self, identifier):
        _main_thread()
        review = self._get(identifier)
        if review.phase != "READY":
            raise ValueError("Approve a new ready capture once")
        self._check(review, selected=True)
        spec = review.spec
        review.phase = "RENDERING"
        try:
            review.temporary = tempfile.TemporaryDirectory(
                prefix="film-capture-", dir=spec.directory
            )
            review.spec = local_capture.snapshot(
                review.source.scene,
                review.temporary.name,
                frame_start=spec.frame_start,
                frame_end=spec.frame_end,
                kind=spec.kind,
                width=spec.width,
                height=spec.height,
                color_type=spec.color_type,
            )
            self._check(review, selected=True)
            review.task = self.session.render_local(
                review.spec, origin=review.origin, source_origin=review.source.origin
            )
        except Exception:
            review.phase, review.error = "ERROR", "Capture could not start; inspect local files"
        return self.status(identifier)

    def poll(self):
        _main_thread()
        for review in self._reviews.values():
            if review.phase in {"READY", "RENDERING", "WAITING", "CAPTURED"}:
                try:
                    self._check(review)
                except Exception:
                    review.phase, review.error = (
                        "ERROR",
                        "Capture recipe, shot or connection changed",
                    )
                    review.completion = None
                    if review.task is not None:
                        self.session.cancel_local_render(review.task)
            if review.task is not None and review.task.done():
                completions = self.session.drain(task=review.task)
                review.task = None
                if review.phase == "CANCELLING":
                    review.phase = "CANCELLED"
                elif review.phase == "RENDERING":
                    if len(completions) != 1 or completions[0].error is not None:
                        review.phase, review.error = (
                            "ERROR",
                            "Local capture failed; inspect retained files",
                        )
                    else:
                        review.completion = completions[0]
                        review.phase = "WAITING"
            if review.phase == "WAITING" and review.scene == bpy.context.scene:
                try:
                    self._check(review, selected=True)

                    def accept(result, scene, target, review=review):
                        if not isinstance(result, LocalCaptureResult) or (
                            result.source_origin != review.source.origin
                        ):
                            raise ValueError("Capture source does not match the review")
                        review.media = result.media

                    self.session.deliver(review.completion, accept)
                    review.phase = "CAPTURED"
                except Exception:
                    review.phase, review.error = "ERROR", "The rendered capture needs a new review"
                finally:
                    review.completion = None
            if review.phase == "UPLOADING":
                ticket = review.upload
                state = ticket.record.state if ticket.record is not None else None
                if ticket.error or state in {
                    UploadState.FAILED,
                    UploadState.CANCELED,
                    UploadState.ABANDONED,
                }:
                    review.phase, review.error = (
                        "UPLOAD_REVIEW",
                        "Inspect saved upload progress; do not retry",
                    )
                elif state == UploadState.IMPORTED:
                    review.phase = "UPLOADED"

    def cancel(self, identifier):
        _main_thread()
        review = self._get(identifier)
        if review.phase not in {"RENDERING", "WAITING"}:
            raise ValueError("Cancel only an active local capture")
        review.completion = None
        if review.task is None:
            review.phase = "CANCELLED"
        else:
            self.session.cancel_local_render(review.task)
            review.phase = "CANCELLING"
        return self.status(identifier)

    def upload(self, identifier, references):
        _main_thread()
        review = self._get(identifier)
        if review.phase != "CAPTURED" or references.session is not self.session:
            raise ValueError("Upload a ready capture through its original session")
        self._check(review, selected=True)
        from .reference_uploads import UploadNotStarted

        review.phase = "UPLOADING"
        try:
            review.upload = references.start(
                review.scene,
                review.media.path,
                kind="image" if review.spec.kind == "STILL" else "video",
                origin=review.origin,
                expected_sha256=review.media.sha256,
            )
        except UploadNotStarted:
            review.phase = "CAPTURED"
            raise
        except Exception:
            review.phase, review.error = (
                "UPLOAD_REVIEW",
                "Inspect saved upload progress; do not retry",
            )
            raise
        return self.status(identifier)

    def discard(self, identifier):
        _main_thread()
        self.poll()
        review = self._get(identifier)
        if review.task is not None or review.phase == "UPLOADING":
            raise ValueError("Wait for capture or upload staging before discarding its files")
        if review.upload is not None and review.upload.task is not None:
            raise ValueError("Wait for upload work before discarding the capture")
        if not self._cleanup(review):
            raise ValueError("Capture cleanup failed; close files using it and discard again")
        del self._reviews[identifier]
        return {"review_id": identifier, "phase": "DISCARDED"}

    @staticmethod
    def _cleanup(review):
        if review.temporary is not None:
            try:
                review.temporary.cleanup()
            except OSError:
                _log.warning("Film capture cleanup failed; retained for cleanup")
                return False
            review.temporary = None
        return True

    def close(self):
        """Called only after the session workers (including upload staging) have joined."""
        for identifier, review in tuple(self._reviews.items()):
            if self._cleanup(review):
                del self._reviews[identifier]
        self._sources.clear()

    def current(self, scene, shot_id):
        for review in reversed(tuple(self._reviews.values())):
            try:
                if review.scene == scene and review.source.shot["id"] == shot_id:
                    return self.status(review.identifier)
            except ReferenceError:
                continue
        return None

    def status(self, identifier):
        _main_thread()
        review = self._get(identifier)
        spec, media, ticket = review.spec, review.media, review.upload
        return {
            "review_id": identifier,
            "shot_id": review.source.shot["id"],
            "phase": review.phase,
            "scene": review.source_name,
            "kind": spec.kind,
            "frames": spec.frames,
            "fps": spec.fps,
            "width": spec.width,
            "height": spec.height,
            "color_type": spec.color_type,
            "error": review.error,
            "path": str(media.path) if media is not None else "",
            "directory": review.temporary.name if review.temporary is not None else "",
            "sha256": media.sha256 if media is not None else "",
            "size": media.size if media is not None else 0,
            "reference_id": ticket.identifier if ticket is not None else "",
            "request_id": ticket.record.intent.request_id
            if ticket is not None and ticket.record
            else "",
        }
