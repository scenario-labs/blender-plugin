# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Session-owned Film review handles over the existing prepare/apply session commands.

Preparation and the native build are separate explicit approvals. These handles
add no executor, store, service client or persisted state; restart drops them.
"""

import logging
import uuid
from dataclasses import dataclass, field

import bpy

from ..core.jobs.film_review_media import PreparedFilmReview
from ..core.jobs.media_probe import MediaProbeError
from ..core.jobs.workers import WorkerError
from ..core.scene.film_plan import require_plan_scope
from . import film_jobs, film_review, film_scene
from .film_application import _main_thread

_log = logging.getLogger("scenario.film_review")

_STALE = "The Film recipe, scene or connection changed; prepare again"
_PREPARE_FAILED = (
    "Inspect saved Film media, frame rates and the declared master before preparing again"
)
_REJECTED = "The Film recipe, sources or scene changed; prepare a new review"
_INSPECT = "Inspect saved jobs, scenes and private copies; do not build this review again"
_ROLLED_BACK = "The review build rolled back; saved jobs record the failure. Prepare again"
_UNCERTAIN = "Inspect the uncertain Film review before preparing another"
_ACTIVE = {"PREPARING", "CANCELLING", "WAITING", "READY", "BUILDING"}
_TERMINAL = {"BUILT", "ERROR", "CANCELLED", "DISCARDED"}
_LIMIT = 16


@dataclass(eq=False)
class _Review:
    identifier: str
    scene: object = field(repr=False)
    scene_name: str
    binding: tuple = field(repr=False)
    origin: object
    mode: str
    score_task_id: str
    include_master: bool
    frames: int
    fps: int
    phase: str = "PREPARING"
    task: object = field(default=None, repr=False)
    completion: object = field(default=None, repr=False)
    outcome: object = field(default=None, repr=False)
    review_scene: object = field(default=None, repr=False)
    shots: int = 0
    sources: int = 0
    bytes: int = 0
    audio_segments: int = 0
    master: bool = False
    error: str = ""
    inspection_required: bool = False
    receipt_retry_available: bool = False


class FilmReviewCommands:
    """Bounded review handles; the session owns workers, copies, claims and receipts."""

    def __init__(self, session, store):
        self.session, self.store = session, store
        self._reviews = {}

    def _get(self, identifier):
        try:
            return self._reviews[identifier]
        except (KeyError, TypeError):
            raise ValueError("The Film review is unavailable") from None

    def _check(self, review, *, selected=False):
        try:
            current = (
                self.session.active
                and review.scene in tuple(bpy.data.scenes)
                and not review.scene.library
                and not review.scene.override_library
                and film_jobs.snapshot(review.scene) == review.binding
                and self.session._origins.current(review.origin)
            )
        except ReferenceError:
            current = False
        if not current:
            raise ValueError(_STALE)
        if selected:
            self.session.validate_destination(review.origin)

    def _uncertain(self, scene):
        for review in self._reviews.values():
            try:
                if review.scene == scene and review.phase == "UNCERTAIN":
                    return True
            except ReferenceError:
                continue
        return False

    def _release(self, completion):
        """Delete an unused preparation's private copies; never a built or claimed review."""
        if (
            completion is None
            or completion.error is not None
            or not isinstance(completion.result, PreparedFilmReview)
            or self.session._issued.get(id(completion)) is not completion
        ):
            # Errors own no copies; retired sessions already cleaned unconsumed ones.
            return
        try:
            self.session.discard_film_review(completion)
        except Exception:
            # The coordinator keeps unconsumed copies and removes them at shutdown.
            _log.warning("Unused Film review copies are retained for shutdown cleanup")

    def master_available(self, scene, mode):
        """Read whether the recipe's declared master has one saved video; never verifies it."""
        _main_thread()
        production, _ = film_jobs.snapshot(scene)
        _, plan = film_jobs.recipe(scene)
        record = self.store.film_job(production, plan[mode + "_master_task"])
        return bool(
            record is not None
            and len(record.results) == 1
            and record.results[0].asset.media_type.startswith("video/")
            and record.results[0].receipt is not None
        )

    def prepare(self, scene, *, mode="final", score_task_id="score", include_master=False):
        _main_thread()
        if mode not in {"final", "previs"}:
            raise ValueError("Choose a final or previs review")
        if type(include_master) is not bool:
            raise ValueError("Choose explicitly whether to include the saved master")
        if not isinstance(score_task_id, str) or not score_task_id:
            raise ValueError("Name the Film score task")
        if (
            not self.session.active
            or scene != bpy.context.scene
            or scene.library
            or scene.override_library
        ):
            raise ValueError("Select the current local Film recipe scene")
        self.poll()
        raw, plan = film_jobs.recipe(scene)
        require_plan_scope(plan, self.session.scope)
        if self._uncertain(scene):
            raise ValueError(_UNCERTAIN)
        for existing in self._reviews.values():
            try:
                same = existing.scene == scene and existing.mode == mode
            except ReferenceError:
                same = False
            if same and existing.phase in _ACTIVE:
                raise ValueError("Finish, cancel or discard this Film review first")
        if len(self._reviews) >= _LIMIT:
            retired = next(
                (
                    key
                    for key, item in self._reviews.items()
                    if item.phase in _TERMINAL and item.task is None and item.completion is None
                ),
                None,
            )
            if retired is None:
                raise ValueError("Finish or discard an existing Film review first")
            del self._reviews[retired]
        # Flush pending depsgraph updates so they cannot invalidate the new origin.
        bpy.context.view_layer.update()
        binding = film_jobs.snapshot(scene)
        review = _Review(
            uuid.uuid4().hex,
            scene,
            scene.name,
            binding,
            self.session.capture(scene),
            mode,
            score_task_id,
            include_master,
            plan["total_frames"],
            plan["fps"],
        )
        self._check(review, selected=True)
        try:
            review.task = self.session.prepare_film_review(
                raw,
                production_id=binding[0],
                origin=review.origin,
                mode=mode,
                score_task_id=score_task_id,
                include_master=include_master,
            )
        except WorkerError as error:
            # First-party admission text, such as waiting for the single local media slot.
            raise ValueError(str(error)) from None
        self._reviews[review.identifier] = review
        return self.status(review.identifier)

    def _stale(self, review):
        if review.phase == "PREPARING":
            if review.task is not None:
                self.session.cancel_local_render(review.task)
        else:
            self._release(review.completion)
            review.completion = None
        review.phase, review.error = "ERROR", _STALE

    def _ready(self, review):
        completion = review.completion
        error = _STALE
        try:
            self._check(review, selected=True)
            error = _PREPARE_FAILED
            prepared = completion.result
            if (
                self.session._issued.get(id(completion)) is not completion
                or not isinstance(prepared, PreparedFilmReview)
                or prepared.mode != review.mode
                or prepared.production_id != review.binding[0]
            ):
                raise ValueError("Unexpected Film review preparation")
            sources = dict(prepared.files)
            master = sources.pop(prepared.master_task) if prepared.master_task is not None else None
            # The same main-thread plan check apply_film_review repeats before consuming.
            plan, pictures, audio = film_review._plan(
                prepared.recipe,
                prepared.scope,
                sources,
                prepared.mode,
                prepared.score_task_id,
                master,
            )
        except Exception:
            self._release(completion)
            review.completion = None
            review.phase, review.error = "ERROR", error
            return
        review.frames, review.fps = plan["total_frames"], plan["fps"]
        review.shots, review.audio_segments = len(pictures), len(audio)
        review.sources, review.master = len(sources), master is not None
        review.bytes = sum(source.result.receipt.size for _, source in prepared.files)
        review.phase = "READY"

    def poll(self):
        """Main-thread maintenance; drains owned preparation without delivering it."""
        _main_thread()
        for review in tuple(self._reviews.values()):
            if review.phase in {"PREPARING", "WAITING", "READY"}:
                try:
                    self._check(review)
                except Exception:
                    self._stale(review)
            if review.task is not None and review.task.done():
                completions = self.session.drain(task=review.task)
                review.task = None
                completion = completions[0] if len(completions) == 1 else None
                if review.phase == "PREPARING":
                    if completion is None or completion.error is not None:
                        error = completion.error if completion is not None else None
                        review.phase = "ERROR"
                        review.error = (
                            str(error) if isinstance(error, MediaProbeError) else _PREPARE_FAILED
                        )
                    else:
                        # apply_film_review consumes this issued completion itself.
                        review.completion, review.phase = completion, "WAITING"
                else:
                    # A late success after cancellation or invalidation never becomes ready.
                    if review.phase == "CANCELLING":
                        review.phase = "CANCELLED"
                    self._release(completion)
            if review.phase == "WAITING":
                try:
                    selected = review.scene == bpy.context.scene
                except ReferenceError:
                    selected = False
                if selected:
                    self._ready(review)

    def _outcome(self, review, outcome):
        application = outcome.application
        if application is not None:
            review.review_scene = application.scene
            review.frames, review.fps = application.frames, application.fps
            review.shots, review.audio_segments = application.shots, application.audio_segments
            review.master = application.master_imported
        review.inspection_required = outcome.inspection_required
        review.receipt_retry_available = outcome.receipt_retry_available
        # Keep only an uncertain outcome: it is the session's receipt-retry key.
        review.outcome = outcome if outcome.phase == "UNCERTAIN" else None
        if outcome.phase == "BUILT":
            review.phase, review.error = "BUILT", ""
        elif outcome.phase == "ERROR":
            review.phase, review.error = "ERROR", _ROLLED_BACK
        else:
            review.phase = "UNCERTAIN"
            if outcome.receipt_retry_available:
                review.error = (
                    "The review scene exists but its saved receipt needs recovery; do not build again"
                    if application is not None
                    else "No review scene remains, but its saved receipt needs recovery; do not build again"
                )
            else:
                review.error = _INSPECT

    def approve(self, identifier):
        """Separately approve one ready review; never retried after it is consumed."""
        _main_thread()
        film_scene._main_thread()
        self.poll()
        review = self._get(identifier)
        if review.phase != "READY" or review.completion is None:
            raise ValueError("Prepare and approve a fresh ready Film review")
        if self._uncertain(review.scene):
            raise ValueError(_UNCERTAIN)
        self._check(review, selected=True)
        completion, review.completion = review.completion, None
        review.phase = "BUILDING"
        try:
            outcome = self.session.apply_film_review(completion)
        except Exception:
            if self.session._issued.get(id(completion)) is completion:
                # Rejected before consumption: nothing was claimed or built.
                self._release(completion)
                review.phase, review.error = "ERROR", _REJECTED
            else:
                review.phase, review.error = "UNCERTAIN", _INSPECT
                review.inspection_required = True
            return self.status(identifier)
        self._outcome(review, outcome)
        return self.status(identifier)

    def retry_receipt(self, identifier):
        """Save only the known outcome; never copies media or invokes the builder."""
        _main_thread()
        review = self._get(identifier)
        if (
            review.phase != "UNCERTAIN"
            or not review.receipt_retry_available
            or review.outcome is None
        ):
            raise ValueError("No known Film review receipt is available to retry")
        try:
            result = self.session.retry_film_review_receipt(review.outcome)
        except ValueError:
            review.outcome, review.receipt_retry_available = None, False
            review.inspection_required, review.error = True, _INSPECT
            raise
        self._outcome(review, result)
        return self.status(identifier)

    def dismiss_uncertain(self, identifier, *, inspected):
        """Retire an inspected review without changing jobs, receipts, scenes or files."""
        _main_thread()
        review = self._get(identifier)
        if review.phase != "UNCERTAIN":
            raise ValueError("Dismiss only an uncertain Film review")
        if inspected is not True:
            raise ValueError("Confirm inspection of the scenes and saved jobs first")
        if review.receipt_retry_available:
            raise ValueError("Save the known Film review receipt before dismissal")
        review.phase, review.outcome = "DISCARDED", None
        return self.status(identifier)

    def cancel(self, identifier):
        _main_thread()
        review = self._get(identifier)
        if review.phase == "PREPARING":
            self.session.cancel_local_render(review.task)
            review.phase = "CANCELLING"
        elif review.phase == "WAITING":
            self._release(review.completion)
            review.completion, review.phase = None, "CANCELLED"
        else:
            raise ValueError("Cancel only active Film review preparation")
        return self.status(identifier)

    def discard(self, identifier):
        """Delete only an unbuilt review's private copies; built scenes stay untouched."""
        _main_thread()
        self.poll()
        review = self._get(identifier)
        if review.phase in {"READY", "WAITING"}:
            self._release(review.completion)
            review.completion = None
        elif review.phase not in {"ERROR", "CANCELLED"}:
            raise ValueError("Discard only an unbuilt Film review after its work stops")
        review.phase = "DISCARDED"
        return self.status(identifier)

    def current(self, scene, mode):
        """Read cached status only; unresolved uncertainty for the scene is shown first."""
        latest = None
        for review in reversed(tuple(self._reviews.values())):
            try:
                if review.scene != scene:
                    continue
                if review.phase == "UNCERTAIN":
                    return self.status(review.identifier)
                if (
                    latest is None
                    and review.mode == mode
                    and review.phase != "DISCARDED"
                    and review.binding == film_jobs.snapshot(scene)
                ):
                    latest = review.identifier
            except ReferenceError:
                continue
        return self.status(latest) if latest is not None else None

    def status(self, identifier):
        _main_thread()
        review = self._get(identifier)
        review_scene = ""
        if review.review_scene is not None:
            try:
                review_scene = review.review_scene.name
            except ReferenceError:
                # Undo or deletion removed the built scene; report no replacement.
                review_scene = ""
        return {
            "review_id": identifier,
            "production_id": review.binding[0],
            "mode": review.mode,
            "phase": review.phase,
            "scene": review.scene_name,
            "review_scene": review_scene,
            "frames": review.frames,
            "fps": review.fps,
            "shots": review.shots,
            "sources": review.sources,
            "bytes": review.bytes,
            "audio_segments": review.audio_segments,
            "include_master": review.include_master,
            "master": review.master,
            "error": review.error,
            "receipt_retry_available": review.receipt_retry_available,
            "inspection_required": review.inspection_required,
        }

    def close(self):
        """Called after workers joined; the coordinator already removed unused copies."""
        _main_thread()
        self._reviews.clear()
