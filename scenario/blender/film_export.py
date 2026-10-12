# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Session-owned Film video export handles over the owned offline export primitive.

Choosing the destination (prepare) and starting the render (approve) are separate
explicit approvals; the render approval repeats the exact resolved destination.
A copy-only re-publish needs its own destination choice and approval. Handles add
no executor, store, service client or persisted state; restart drops them.
"""

import hashlib
import logging
import os
import shutil
import uuid
from dataclasses import dataclass, field
from pathlib import Path

import bpy

from ..core.jobs import film_export_policy, local_export
from ..core.jobs.local_render import LocalRenderError, RenderCancelled
from ..core.jobs.store import _json
from ..core.jobs.workers import WorkerError
from ..core.scene.film_plan import require_plan_scope
from . import film_jobs, local_capture
from .film_application import _main_thread

_log = logging.getLogger("scenario.film_export")

KINDS = {"downloaded_final_review": "final", "downloaded_previs_review": "previs"}
# Like Film reviews, a READY export binds the recipe and review scenes' captured
# origins: frame changes, edits, Undo/Redo or reselecting a scene revoke them.
STALE = (
    "The Film recipe, review scene, frame or connection changed, or a scene was"
    " selected again; prepare the export again"
)
_FAILED = "Film export failed; inspect its private files, then export again"
_CHANGED = "The review scene changed; prepare the export again"
_RUNNING = {"EXPORTING", "PUBLISHING", "CANCELLING"}
_OPEN = {"READY", "PUBLISH_FAILED", *_RUNNING}
_LIMIT = 8
_SOURCES = 256


def encoder_available():
    """Whether this Blender build links FFmpeg; codec support is checked by the child."""
    return bool(bpy.app.ffmpeg.supported)


def verifier():
    """Name the verification an export will use: installed ffprobe, else Blender decode."""
    return "ffprobe" if shutil.which("ffprobe") else "blender"


def _readable(error, fallback):
    from .job_session import OriginUnavailable, SessionBusy

    # These carry first-party wording without private paths; anything else is generic.
    known = (ValueError, LocalRenderError, WorkerError, OriginUnavailable, SessionBusy)
    return str(error) if isinstance(error, known) and str(error) else fallback


def _redraw():
    from . import pump

    try:
        pump.redraw()
    except (AttributeError, ReferenceError):
        # A closing window has no screen; the next maintenance tick redraws again.
        pass


@dataclass(frozen=True, eq=False)
class _Source:
    identifier: str
    scene: object = field(repr=False)
    name: str
    kind: str
    origin: object
    binding: tuple = field(repr=False)
    digest: str
    default_name: str
    frames: int
    fps: int
    width: int
    height: int
    percentage: int
    strips: int
    media: int
    audible: bool
    blocked: str


@dataclass(eq=False)
class _Export:
    identifier: str
    scene: object = field(repr=False)
    scene_name: str
    binding: tuple = field(repr=False)
    origin: object
    source: _Source
    destination: str
    width: int
    height: int
    audio: bool
    within: object = None
    phase: str = "READY"
    task: object = field(default=None, repr=False)
    progress: tuple = ("", 0, 0)
    directory: object = field(default=None, repr=False)
    staged: object = field(default=None, repr=False)
    published: object = field(default=None, repr=False)
    pending: str = ""
    pending_within: object = None
    error: str = ""


class FilmExportCommands:
    """Bounded export handles; the session owns the export thread, child and receipts."""

    def __init__(self, session):
        self.session = session
        self._sources, self._reviews = {}, {}

    @staticmethod
    def _root():
        package = __package__.rsplit(".", 1)[0]
        return Path(bpy.utils.extension_path_user(package, path="state", create=True)).resolve()

    def _get(self, identifier):
        try:
            return self._reviews[identifier]
        except (KeyError, TypeError):
            raise ValueError("The Film export is unavailable") from None

    def _recipe(self, scene):
        if not self.session.active:
            raise ValueError("The Film connection changed")
        try:
            if scene != bpy.context.scene or scene.library or scene.override_library:
                raise ValueError("Select the current local Film recipe scene")
            binding = film_jobs.snapshot(scene)
            raw, plan = film_jobs.recipe(scene)
        except ReferenceError:
            raise ValueError("The Film recipe scene was removed") from None
        require_plan_scope(plan, self.session.scope)
        # The same canonical recipe digest the review builder writes on its scene.
        return binding, plan, hashlib.sha256(_json(raw).encode()).hexdigest()

    @staticmethod
    def _kind(candidate, binding, digest):
        """Return final or previs for a local review scene of this recipe, else None."""
        try:
            if candidate.library or candidate.override_library:
                return None
            value = candidate.get("scenario_sequence_kind")
            # Custom properties can hold any IDProperty; only exact strings match.
            kind = KINDS.get(value) if isinstance(value, str) else None
            if (
                kind is None
                or candidate.get("scenario_production_id") != binding[0]
                or candidate.get("scenario_recipe_sha256") != digest
            ):
                return None
        except ReferenceError:
            return None
        return kind

    @staticmethod
    def _describe(candidate):
        """Read export bounds and a blocking reason; never changes the scene."""
        render = candidate.render
        percentage = render.resolution_percentage
        frames = candidate.frame_end - candidate.frame_start + 1
        editor = candidate.sequence_editor
        details = {
            "frames": frames,
            "fps": render.fps,
            # The snapshot's default: Blender's truncated size, rounded down to even.
            "width": local_export.default_dimension(render.resolution_x, percentage),
            "height": local_export.default_dimension(render.resolution_y, percentage),
            "percentage": percentage,
            "strips": len(editor.strips_all) if editor is not None else 0,
            "media": 0,
            "audible": False,
            "blocked": "",
        }
        if not details["strips"]:
            details["blocked"] = "Add sequencer strips to this review scene"
        elif render.fps_base != 1 or not 1 <= render.fps <= 120:
            details["blocked"] = "Use an integer frame rate from 1 to 120"
        elif candidate.frame_start < 1 or not 1 <= frames <= min(
            local_export.MAX_FRAMES, local_export.MAX_SECONDS * render.fps
        ):
            details["blocked"] = "Export at most fifteen minutes of positive frames"
        else:
            try:
                media = local_capture._export_media(candidate)
                details["media"] = len(media)
                details["audible"] = local_capture._audible(candidate)
            except (ValueError, local_export.LocalExportError) as error:
                # Blocked strip types, missing media or the media count, in first-party text.
                details["blocked"] = str(error)
            else:
                # The snapshot enforces the byte budget too; report it before any approval.
                if sum(item.size for item in media) > local_export.MAX_MEDIA_BYTES:
                    details["blocked"] = "Export at most 16 GiB of distinct media files"
        return details

    @staticmethod
    def _choice(source):
        return {
            "source_id": source.identifier,
            "scene": source.name,
            "kind": source.kind,
            "frames": source.frames,
            "fps": source.fps,
            "width": source.width,
            "height": source.height,
            "resolution_percentage": source.percentage,
            "strips": source.strips,
            "media": source.media,
            "audible": source.audible,
            "blocked_reason": source.blocked,
            "default_name": source.default_name,
        }

    def inspect(self, scene):
        """List this recipe's built review scenes as opaque sources; renders nothing."""
        _main_thread()
        binding, plan, digest = self._recipe(scene)
        sources, choices = {}, []
        for candidate in bpy.data.scenes:
            kind = self._kind(candidate, binding, digest)
            if kind is None:
                continue
            if len(sources) >= _SOURCES:
                raise ValueError("Keep at most 256 Film review scenes")
            # Synchronize the scene's own view layers as the snapshot will (the Blender
            # 5.2 copy guard). This evaluation is not an edit, so it keeps the origin
            # of a ready export of the same scene; approval rereads the shown bounds.
            with self.session.synchronizing((candidate,)):
                for layer in candidate.view_layers:
                    layer.update()
            source = _Source(
                uuid.uuid4().hex,
                candidate,
                candidate.name,
                kind,
                self.session.capture(candidate),
                binding,
                digest,
                film_export_policy.default_name(plan["title"], kind),
                **self._describe(candidate),
            )
            sources[source.identifier] = source
            choices.append(self._choice(source))
        self._sources = sources
        return {
            "production_id": binding[0],
            "scene": scene.name,
            "sources": choices,
            "encoder_available": encoder_available(),
            "verification": verifier(),
        }

    def _check(self, review, *, selected=False):
        source = review.source
        try:
            current = (
                self.session.active
                and review.scene in tuple(bpy.data.scenes)
                and not review.scene.library
                and not review.scene.override_library
                and film_jobs.snapshot(review.scene) == review.binding
                and self.session._origins.current(review.origin)
                and source.scene in tuple(bpy.data.scenes)
                and self._kind(source.scene, review.binding, source.digest) == source.kind
                and self.session._origins.current(source.origin)
            )
        except ReferenceError:
            current = False
        if not current:
            raise ValueError(STALE)
        if selected:
            self.session.validate_destination(review.origin)

    def _destination(self, destination, staging, within):
        """Resolve one destination under the session's policy plus any agent folder."""
        if within is not None:
            within = Path(within)
            destination = film_export_policy.require_within(
                destination, within, create=within / "Film"
            )
        return str(self.session._export_destination(destination, staging))

    def _running(self):
        return any(
            item.task is not None or item.phase in _RUNNING for item in self._reviews.values()
        )

    def prepare(
        self, scene, *, source_id, destination, width=None, height=None, audio=None, within=None
    ):
        """Bind one source scene, settings and a new destination; nothing renders yet.

        ``within`` restricts the destination to that folder (the agent policy);
        native file browser choices pass None and get the session policy only.
        """
        _main_thread()
        binding, _, digest = self._recipe(scene)
        source = self._sources.get(source_id) if isinstance(source_id, str) else None
        if source is None or source.binding != binding or source.digest != digest:
            raise ValueError("Use a source from the current Film export inspection")
        if source.blocked:
            raise ValueError(source.blocked)
        if not encoder_available():
            raise ValueError("This Blender build cannot encode video")
        width = source.width if width is None else width
        height = source.height if height is None else height
        audio = source.audible if audio is None else audio
        if type(audio) is not bool:
            raise ValueError("Choose explicitly whether the export includes audio")
        self.poll()
        for existing in self._reviews.values():
            try:
                same = existing.source.scene == source.scene
            except ReferenceError:
                same = False
            if same and existing.phase in _OPEN:
                raise ValueError("Finish or discard this review scene's current export first")
        root = self._root()
        # A settings-only specification validates the bounds before any file is written.
        local_export.ExportSpec(
            root,
            Path(bpy.app.binary_path).resolve(),
            Path(local_capture.__file__).with_name("film_export_worker.py").resolve(),
            source.name,
            "0" * 64,
            1,
            source.frames,
            source.fps,
            width,
            height,
            audio,
        )
        retired = None
        if len(self._reviews) >= _LIMIT:
            # Retire only finished handles that own no private files.
            retired = next(
                (
                    key
                    for key, item in self._reviews.items()
                    if item.phase not in _OPEN and item.directory is None and item.task is None
                ),
                None,
            )
            if retired is None:
                raise ValueError("Discard a previous Film export before preparing another")
        resolved = self._destination(destination, root, within)
        # Flush pending depsgraph updates so they cannot invalidate the new origin.
        bpy.context.view_layer.update()
        review = _Export(
            uuid.uuid4().hex,
            scene,
            scene.name,
            binding,
            self.session.capture(scene),
            source,
            resolved,
            width,
            height,
            audio,
            Path(within) if within is not None else None,
        )
        self._check(review, selected=True)
        if retired is not None:
            del self._reviews[retired]
        self._reviews[review.identifier] = review
        return self.status(review.identifier)

    def _remove(self, review):
        """Delete one handle's private staging; the published video is never touched."""
        directory = review.directory
        if directory is not None and os.path.lexists(directory):
            try:
                local_export.discard_staging(directory)
            except (OSError, local_export.LocalExportError):
                _log.warning("Film export staging cleanup failed; retained for cleanup")
                return False
        review.directory, review.staged = None, None
        return True

    def approve(self, identifier, *, approved_destination, within=None):
        """Separately approve one ready export; consumed even if it cannot start.

        ``within`` is the approver's folder policy: an agent approval passes the
        Output Folder, so it cannot approve a native choice elsewhere.
        """
        _main_thread()
        self.poll()
        review = self._get(identifier)
        if review.phase != "READY":
            raise ValueError("Prepare and approve a fresh ready Film export")
        if type(approved_destination) is not str or approved_destination != review.destination:
            raise ValueError("Approve the exact destination shown for this Film export")
        if within is not None:
            # Refused without consuming: the handle stays for an approver allowed to use it.
            film_export_policy.require_within(review.destination, within)
        if bpy.context.mode != "OBJECT":
            raise ValueError("Switch to Object Mode to export video")
        if self._running():
            raise ValueError("Wait for the current Film export to finish")
        self._check(review, selected=True)
        source, spec = review.source, None
        review.phase = "EXPORTING"
        try:
            if review.within is not None:
                film_export_policy.require_within(review.destination, review.within)
            # A review scene no window shows keeps tags from changes elsewhere until
            # the snapshot synchronizes it. That evaluation is not an edit
            # (JobSession.synchronizing), so the bounds the approval showed are reread.
            details = self._describe(source.scene)
            if any(getattr(source, key) != value for key, value in details.items()):
                raise ValueError(_CHANGED)
            with self.session.synchronizing((source.scene,)):
                spec = local_capture.export_snapshot(
                    source.scene,
                    self._root(),
                    width=review.width,
                    height=review.height,
                    audio=review.audio,
                )
            review.directory = spec.directory
            if (spec.frames, spec.fps, len(spec.media)) != (
                source.frames,
                source.fps,
                source.media,
            ):
                raise ValueError(_CHANGED)
            review.task = self.session.export_film(
                spec, review.destination, origin=review.origin, source_origin=source.origin
            )
        except Exception as error:
            review.phase = "ERROR"
            review.error = _readable(error, "The export could not start; prepare it again")
            # Nothing ran, so the unused snapshot is removed rather than kept for diagnosis.
            self._remove(review)
        else:
            review.progress = review.task.progress()
        return self.status(identifier)

    def _finish(self, review):
        from .job_session import OriginUnavailable

        completions = self.session.drain(task=review.task)
        review.task = None
        try:
            if len(completions) != 1:
                raise RuntimeError("Missing Film export outcome")
            result = self.session.deliver_local_export(completions[0])
        except local_export.ExportPublishCancelled as error:
            review.staged = error.staged
            review.phase, review.error = "CANCELLED", ""
        except local_export.ExportPublishError as error:
            # The verified video stays private for an explicit copy-only re-publish.
            review.staged = error.staged
            review.phase, review.error = "PUBLISH_FAILED", str(error) or _FAILED
        except RenderCancelled:
            review.phase, review.error = "CANCELLED", ""
        except LocalRenderError as error:
            review.phase, review.error = "ERROR", str(error) or _FAILED
        except OriginUnavailable:
            review.phase, review.error = "ERROR", "The Film connection changed; the export stopped"
        except Exception:
            review.phase, review.error = "ERROR", _FAILED
        else:
            review.published, review.staged = result.export, result.staged
            review.destination = str(result.export.destination)
            review.phase, review.error = "EXPORTED", ""

    def poll(self):
        """Main-thread maintenance: invalidate stale approvals and deliver finished work."""
        _main_thread()
        changed = False
        for review in tuple(self._reviews.values()):
            if review.phase == "READY":
                try:
                    self._check(review)
                    exists = os.path.lexists(review.destination)
                except Exception:
                    review.phase, review.error, changed = "ERROR", STALE, True
                else:
                    if exists:
                        review.phase = "ERROR"
                        review.error = "The destination now exists; prepare the export again"
                        changed = True
            task = review.task
            if task is not None:
                progress = task.progress()
                if progress != review.progress:
                    review.progress, changed = progress, True
                if task.done():
                    self._finish(review)
                    changed = True
        if changed:
            _redraw()
        return changed

    def cancel(self, identifier):
        _main_thread()
        review = self._get(identifier)
        if review.phase not in {"EXPORTING", "PUBLISHING"} or review.task is None:
            raise ValueError("Cancel only a running Film export")
        self.session.cancel_film_export(review.task)
        review.phase = "CANCELLING"
        return self.status(identifier)

    def discard(self, identifier):
        """Delete only the private snapshot, staged video and logs; the export remains."""
        _main_thread()
        self.poll()
        review = self._get(identifier)
        if review.task is not None or review.phase in _RUNNING or review.phase == "DISCARDED":
            raise ValueError("Discard a Film export only after its work stops")
        if not self._remove(review):
            raise ValueError("Export cleanup failed; close files using it and discard again")
        review.phase, review.pending, review.pending_within = "DISCARDED", "", None
        return self.status(identifier)

    def prepare_republish(self, identifier, destination, *, within=None):
        """Choose a new destination for a verified export whose publish failed."""
        _main_thread()
        self.poll()
        review = self._get(identifier)
        if review.phase != "PUBLISH_FAILED" or review.staged is None:
            raise ValueError("Choose another destination only after a failed Film export publish")
        review.pending = self._destination(destination, review.staged.directory.parent, within)
        review.pending_within = Path(within) if within is not None else None
        return self.status(identifier)

    def republish(self, identifier, *, approved_destination, within=None):
        """Copy the verified staged video to the approved new destination; never re-renders.

        ``within`` is the approver's folder policy, as for ``approve``.
        """
        _main_thread()
        self.poll()
        review = self._get(identifier)
        if review.phase != "PUBLISH_FAILED" or review.staged is None or not review.pending:
            raise ValueError("Choose a new destination for this verified Film export first")
        if type(approved_destination) is not str or approved_destination != review.pending:
            raise ValueError("Approve the exact new destination shown for this Film export")
        if self._running():
            raise ValueError("Wait for the current Film export to finish")
        if within is not None:
            # An agent cannot confirm a native choice elsewhere; that choice stays pending.
            film_export_policy.require_within(review.pending, within)
        destination, bound = review.pending, review.pending_within
        review.pending, review.pending_within = "", None
        try:
            if bound is not None:
                film_export_policy.require_within(destination, bound)
            review.task = self.session.publish_film_export(
                review.staged,
                destination,
                origin=review.origin,
                source_origin=review.source.origin,
            )
        except Exception as error:
            review.error = _readable(error, "The copy could not start; choose another destination")
            return self.status(identifier)
        review.destination, review.within = destination, bound
        review.phase, review.error = "PUBLISHING", ""
        review.progress = review.task.progress()
        return self.status(identifier)

    def current(self, scene):
        """Read cached status only: running work first, else the latest kept handle."""
        latest = None
        for review in reversed(tuple(self._reviews.values())):
            try:
                if review.scene != scene or review.phase == "DISCARDED":
                    continue
            except ReferenceError:
                continue
            if review.phase in _RUNNING:
                return self.status(review.identifier)
            if latest is None:
                latest = review.identifier
        return self.status(latest) if latest is not None else None

    def status(self, identifier):
        _main_thread()
        review = self._get(identifier)
        source, published = review.source, review.published
        stage, done, total = review.progress
        exported = review.phase == "EXPORTED" and published is not None
        return {
            "review_id": identifier,
            "production_id": review.binding[0],
            "phase": review.phase,
            "scene": review.scene_name,
            "source_id": source.identifier,
            "source_scene": source.name,
            "kind": source.kind,
            "frames": source.frames,
            "fps": source.fps,
            "duration": round(source.frames / source.fps, 3),
            "width": review.width,
            "height": review.height,
            "audio": review.audio,
            "media": source.media,
            "destination": review.destination,
            "output_folder_only": review.within is not None,
            "pending_destination": review.pending,
            "progress": {"stage": stage, "done": done, "total": total},
            "percent": min(100, done * 100 // total) if total else 0,
            "published": exported,
            "sha256": published.sha256 if exported else "",
            "size": published.size if exported else 0,
            "verification": published.verification if exported else "",
            "republish_available": review.phase == "PUBLISH_FAILED" and review.staged is not None,
            "directory": str(review.directory) if review.directory is not None else "",
            "error": review.error,
        }

    def close(self):
        """Called once the export thread and workers have stopped; removes private staging."""
        _main_thread()
        for review in self._reviews.values():
            self._remove(review)
        self._reviews.clear()
        self._sources.clear()
