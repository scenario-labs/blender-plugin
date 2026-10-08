# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Explicit shared-job ownership and guarded main-thread delivery.

Registration installs invalidation hooks only. No connection, worker or second
runtime starts until an integration explicitly creates a JobSession.
"""

import logging
import threading
import time
import uuid
from dataclasses import dataclass, field
from weakref import WeakKeyDictionary, WeakValueDictionary

import bpy
from bpy.app.handlers import persistent

from ..core.jobs.coordinator import (
    FilmUploadResult,
    JobCoordinator,
    LocalCaptureResult,
    OriginQuote,
    RemoteSnapshot,
)
from ..core.jobs.film_media import VerifiedComposition
from ..core.jobs.film_review_media import PreparedFilmReview
from ..core.jobs.origins import OriginRevisions
from ..core.jobs.results import ModelTextResult, PromptResults, VerifiedResults
from ..core.jobs.store import JobOrigin, JobState, StoredJob
from ..core.jobs.workers import JobWorkers
from .film_application import FilmShotCommands
from .image_application import ImageApplicationError, apply_images
from .material_application import (
    MaterialApplicationError,
    apply_material,
    selected_maps,
    validate_target,
)
from .media_application import MediaApplicationError, apply_media
from .mesh_result_application import MeshResultApplicationError, apply_saved_mesh
from .mesh_result_application import validate_request as validate_mesh_request
from .model_application import ModelApplicationError, apply_model
from .model_application import validate_destination as validate_model_destination
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


@dataclass(frozen=True, eq=False)
class FilmReviewOutcome:
    phase: str
    application: object = field(default=None, repr=False)
    inspection_required: bool = False
    receipt_retry_available: bool = False


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


class ModelResultUncertain(RuntimeError):
    """Model objects may already exist; only persistence may be retried."""

    def __init__(self, application=None):
        super().__init__("Model application needs inspection; do not import it again")
        self.application = application


@dataclass(frozen=True)
class AppliedModel:
    record: StoredJob
    application: object = field(repr=False)


@dataclass(frozen=True)
class AppliedMedia:
    record: StoredJob
    application: object = field(repr=False)


@dataclass(frozen=True)
class AppliedImages:
    record: StoredJob
    images: tuple = field(repr=False)


class MaterialResultUncertain(RuntimeError):
    """Scene assignment may have finished; only a known receipt may be retried."""

    def __init__(self, application=None):
        super().__init__("Material application is uncertain; inspect the saved job and target")
        self.application = application


@dataclass(frozen=True)
class AppliedMaterial:
    record: StoredJob
    application: object = field(repr=False)


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
    cloud_read: bool = False
    workflow_catalog: bool = False


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
        self._cloud_reads = {}
        self._workflow_reads = {}
        self._issued = WeakValueDictionary()
        self._world_receipts = WeakKeyDictionary()
        self._image_receipts = WeakKeyDictionary()
        self._media_receipts = WeakKeyDictionary()
        self._model_receipts = WeakKeyDictionary()
        self._material_receipts = WeakKeyDictionary()
        self._film_review_receipts = WeakKeyDictionary()
        self._film_cleanup_retry_at = 0.0
        self._upload_captures = {}
        self._mesh_sources = {}
        self._history_revision = 0
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
        self.film_shots = FilmShotCommands(self, store)
        from .film_timeline import FilmTimelineCommands

        self.film_timeline = FilmTimelineCommands(self)
        from .film_capture import FilmCaptureCommands

        self.film_capture = FilmCaptureCommands(self)
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

    @property
    def history_revision(self):
        """Generation of live Blender references; changes across load/undo/retirement."""
        return self._history_revision

    @staticmethod
    def _identity(records, value):
        for identity, existing in records.items():
            if existing is value:
                return identity
        identity = uuid.uuid4().hex
        records[identity] = value
        return identity

    def capture(self, scene, target=None):
        return self.capture_many(scene, (target,))[0]

    def has_scene(self, scene_id):
        """Read live scene ownership without capturing or renewing an origin revision."""
        _main_thread()
        scene = self._scenes.get(scene_id)
        try:
            return self._active and scene is not None and scene in tuple(bpy.data.scenes)
        except ReferenceError:
            return False

    def capture_many(self, scene, targets):
        """Validate one current scene-membership snapshot before recording any origins."""
        _main_thread()
        if not self._active:
            raise OriginUnavailable("This job context is inactive")
        targets = tuple(targets)
        try:
            if scene not in tuple(bpy.data.scenes):
                raise OriginUnavailable("The originating scene is unavailable")
            members = set(scene.objects) if any(target is not None for target in targets) else ()
            if any(target is not None and target not in members for target in targets):
                raise OriginUnavailable("The target is not in the originating scene")
        except ReferenceError:
            raise OriginUnavailable("The original scene or target was removed") from None
        scene_id = self._identity(self._scenes, scene)
        origins = []
        for target in targets:
            target_id = self._identity(self._targets, target) if target is not None else None
            if target_id is not None:
                self._target_scenes.setdefault(target_id, set()).add(scene_id)
            origins.append(self._origins.capture(scene_id, target_id))
        return tuple(origins)

    def retain_mesh_source(self, origin, source, target):
        """Retain a bounded live export guard; saved metadata cannot recreate it."""
        from .mesh_application import validate_target
        from .mesh_export_fingerprint import fingerprints

        _main_thread()
        validate_target(target)
        if self.capture(target.scene, target.obj) != origin or len(source.objects) != 1:
            raise OriginUnavailable("The captured mesh context changed during export")
        item = source.objects[0]
        # Export provenance and edit guards use distinct fingerprint formats.
        # Compare like formats while retaining the stricter validated edit guard.
        if (
            item.target_id != origin.target_id
            or item.geometry_sha256 != fingerprints((target.mesh,))[0].hex()
            or item.matrix_world != tuple(tuple(row) for row in target.obj.matrix_world)
        ):
            raise OriginUnavailable("The exported mesh does not match its live source")
        key = (origin, source)
        # Never evict an older export's authority to admit another snapshot.
        # Further uploads remain valid references, without original-source apply.
        if key in self._mesh_sources or len(self._mesh_sources) < 128:
            self._mesh_sources[key] = target

    def mesh_source_target(self, binding):
        """Resolve only a retained export; current selection and names are irrelevant."""
        from .mesh_application import validate_target

        _main_thread()
        target = self._mesh_sources.get((binding.origin, binding.mesh_source))
        if not self._active or target is None:
            raise OriginUnavailable(
                "The live captured source is unavailable; review another destination"
            )
        validate_target(target)
        current = self.capture(target.scene, target.obj)
        original = binding.origin
        # Unrelated scene changes may advance its revision. The frozen source
        # guard proves this object unchanged, while file/scene/object IDs must
        # still belong to this exact session. Undo/load retire that authority.
        if (current.file_id, current.scene_id, current.target_id) != (
            original.file_id,
            original.scene_id,
            original.target_id,
        ):
            raise OriginUnavailable("The captured source context was replaced")
        return target

    def quote_model(self, identifier, parameters, *, origin):
        return self._quote("model", identifier, parameters, origin)

    def quote_film_task(self, recipe, *, production_id, task_id, origin):
        _main_thread()
        self._check_capacity()
        self._resolve(origin)
        task = self._workers.quote_film_task(
            recipe,
            production_id=production_id,
            task_id=task_id,
            origin=origin,
        )
        self._pending.append((task, origin))
        return task

    def quote_film_composition(self, verified, *, origin):
        """Request a fresh exact price for this session's unchanged measured sources."""
        _main_thread()
        self._check_capacity()
        self._resolve(origin)
        task = self._workers.quote_film_composition(verified, origin=origin)
        self._pending.append((task, origin))
        return task

    def bind_film_upload(
        self, recipe, *, production_id, task_id, request_id, expected_revision, origin
    ):
        _main_thread()
        self._check_capacity()
        self._resolve(origin)
        task = self._workers.bind_film_upload(
            recipe,
            production_id=production_id,
            task_id=task_id,
            request_id=request_id,
            expected_revision=expected_revision,
            origin=origin,
        )
        self._pending.append((task, origin))
        return task

    def workflow_metadata(self, scene, *, identifier=None, privacy="private"):
        """Read workflow metadata off-thread, bound to this session and scene."""
        _main_thread()
        self._check_capacity()
        origin = self.capture(scene)
        if identifier is None:
            task = self._workers.workflows(privacy=privacy)
        else:
            task = self._workers.workflow(identifier)
        self._workflow_reads[task] = identifier
        self._pending.append((task, origin))
        return task

    def quote_workflow(self, identifier, parameters, *, origin):
        return self._quote("workflow", identifier, parameters, origin)

    def quote_prompt(self, parameters, *, origin):
        return self._quote("prompt", "prompt", parameters, origin)

    def quote_translate(self, parameters, *, origin):
        return self._quote("translate", "translate", parameters, origin)

    def _quote(self, operation, identifier, parameters, origin):
        _main_thread()
        self._check_capacity()
        self._resolve(origin)
        if operation in {"prompt", "translate"}:
            task = getattr(self._workers, f"quote_{operation}")(parameters, origin=origin)
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

    def adopt_cloud_job(self, identifier, *, expected_model_id, scene):
        """Queue an explicit cloud-result read; this never approves scene application."""
        _main_thread()
        self._check_capacity()
        origin = self.capture(scene)
        task = self._workers.adopt_cloud_job(
            identifier, expected_model_id=expected_model_id, origin=origin
        )
        self._cloud_reads[task] = (identifier, expected_model_id)
        self._pending.append((task, origin))
        return task

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

    def read_prompt_results(self, request_id, *, expected_revision):
        """Read full text off-thread; delivery still checks the originating scene."""
        return self._record_command("read_prompt_results", request_id, expected_revision)

    def read_model_text(self, request_id, *, expected_revision, asset_id):
        return self._record_command(
            "read_model_text", request_id, expected_revision, asset_id=asset_id
        )

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

    def prepare_film_composition(
        self, recipe, *, production_id, origin, mode="final", score_task_id="score"
    ):
        """Queue saved-media inspection; completion is a draft, never spend approval."""
        _main_thread()
        self._check_capacity()
        self._resolve(origin)
        root = bpy.utils.extension_path_user(
            __package__.rsplit(".", 1)[0], path="state", create=True
        )
        task = self._workers.prepare_film_composition(
            recipe,
            production_id=production_id,
            mode=mode,
            score_task_id=score_task_id,
            root=root,
            origin=origin,
        )
        self._pending.append((task, origin))
        return task

    def prepare_film_review(
        self,
        recipe,
        *,
        production_id,
        origin,
        mode="final",
        score_task_id="score",
        include_master=False,
    ):
        _main_thread()
        self._check_capacity()
        self._resolve(origin)
        root = bpy.utils.extension_path_user(
            __package__.rsplit(".", 1)[0], path="film-review", create=True
        )
        task = self._workers.prepare_film_review(
            recipe,
            production_id=production_id,
            origin=origin,
            mode=mode,
            score_task_id=score_task_id,
            include_master=include_master,
            root=root,
        )
        self._pending.append((task, origin))
        return task

    def apply_film_review(self, completion):
        """Explicitly approve this owner's prepared cut once in its original scene."""
        from ..core.jobs.store import _json
        from . import film_jobs, film_review

        _main_thread()
        film_review._main_thread()
        if self._issued.get(id(completion)) is not completion or completion.error is not None:
            raise OriginUnavailable("Use an unconsumed Film review completion")
        prepared = completion.result
        if not isinstance(prepared, PreparedFilmReview):
            raise OriginUnavailable("Prepare saved Film review media first")
        scene, _ = self._resolve(prepared.origin)
        raw, _ = film_jobs.recipe(scene)
        if (
            scene.scenario_film.production_id != prepared.production_id
            or _json(raw) != prepared.recipe_json
        ):
            raise OriginUnavailable("The Film recipe changed; prepare a new review")
        sources = dict(prepared.files)
        master = sources.pop(prepared.master_task) if prepared.master_task is not None else None
        film_review._plan(
            prepared.recipe, self.scope, sources, prepared.mode, prepared.score_task_id, master
        )
        self._coordinator.take_film_review(prepared, origin=prepared.origin)
        del self._issued[id(completion)]
        claims = []
        try:
            for verified in prepared.jobs:
                claims.append(
                    self._claim_saved_application(
                        verified,
                        prepared.origin,
                        "media",
                        tuple(item.asset.asset_id for item in verified.record.results),
                    )
                )
        except Exception:
            # A lost claim response may have committed. Never build or replay it.
            outcome = self._finish_film_review(claims, application=None, unknown=True)
            return self._cleanup_film_review(prepared, outcome)
        before = film_review._snapshot()
        try:
            application = film_review.build_prepared_review(prepared)
        except Exception:
            if film_review._snapshot() != before:
                return FilmReviewOutcome("UNCERTAIN", inspection_required=True)
            # Save the confirmed native outcome before attempting file cleanup.
            outcome = self._finish_film_review(claims, application=None)
            return self._cleanup_film_review(prepared, outcome)
        return self._finish_film_review(claims, application=application)

    def _cleanup_film_review(self, prepared, outcome):
        if outcome in self._film_review_receipts:
            # File ownership must outlive weak receipt handles and retirement.
            self._coordinator.cleanup_film_review(prepared, defer=True)
            claims, application, unknown, _ = self._film_review_receipts[outcome]
            self._film_review_receipts[outcome] = (claims, application, unknown, prepared)
            return outcome
        try:
            # Preflight can fail before the primitive enters its cleanup block.
            self._coordinator.cleanup_film_review(prepared)
        except OSError:
            retained = FilmReviewOutcome(
                "UNCERTAIN", outcome.application, True, outcome.receipt_retry_available
            )
            return retained
        return outcome

    def _finish_film_review(self, claims, *, application, unknown=False):
        pending = []
        command = (
            self._coordinator.complete_application
            if application is not None
            else self._coordinator.fail_application
        )
        for claim in claims:
            try:
                command(claim)
            except Exception:
                pending.append(claim)
        outcome = FilmReviewOutcome(
            "UNCERTAIN" if unknown or pending else "BUILT" if application is not None else "ERROR",
            application,
            unknown,
            bool(pending),
        )
        if pending:
            self._film_review_receipts[outcome] = (tuple(pending), application, unknown, None)
        return outcome

    def retry_film_review_receipt(self, outcome):
        """Retry only known saved outcomes; never copy media or invoke the builder."""
        _main_thread()
        if outcome not in self._film_review_receipts:
            raise ValueError("No known Film review receipt is available to retry")
        claims, application, unknown, cleanup = self._film_review_receipts.pop(outcome)
        pending = []
        for claim in claims:
            try:
                self._coordinator.retry_application_receipt(claim)
            except Exception:
                pending.append(claim)
        result = FilmReviewOutcome(
            "UNCERTAIN" if unknown or pending else "BUILT" if application is not None else "ERROR",
            application,
            unknown,
            bool(pending),
        )
        if pending:
            self._film_review_receipts[result] = (tuple(pending), application, unknown, cleanup)
        elif cleanup is not None:
            return self._cleanup_film_review(cleanup, result)
        return result

    def discard_film_review(self, completion):
        """Discard an unused issued result even after its scene context changed."""
        _main_thread()
        if self._issued.get(id(completion)) is not completion or not isinstance(
            completion.result, PreparedFilmReview
        ):
            raise ValueError("Use an unused Film media completion")
        self._coordinator.discard_film_review(completion.result)
        del self._issued[id(completion)]

    def render_local(self, spec, *, origin, source_origin):
        _main_thread()
        self._check_capacity()
        self._resolve(origin)
        if not self._origins.current(source_origin):
            raise OriginUnavailable("The selected capture scene changed")
        task = self._workers.render_local(spec, origin=origin, source_origin=source_origin)
        self._pending.append((task, origin))
        return task

    def cancel_local_render(self, task):
        _main_thread()
        if any(pending is task for pending, _ in self._pending):
            self._workers.cancel_local(task)

    def prepare_upload(
        self, source, *, origin, kind, content_type, mesh_source=None, expected_sha256=None
    ):
        """Stage a reference for the origin captured with its source, off the main thread."""
        _main_thread()
        self._check_capacity()
        self._resolve(origin)
        task = self._workers.prepare_upload(
            source,
            origin=origin,
            kind=kind,
            content_type=content_type,
            mesh_source=mesh_source,
            expected_sha256=expected_sha256,
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

    def _record_command(self, command, request_id, expected_revision, **parameters):
        _main_thread()
        self._check_capacity()
        records = self.recovery_plan()
        record = next(
            (item.record for item in records if item.record.intent.request_id == request_id), None
        )
        if record is None:
            raise OriginUnavailable("The job is not in this connection's store")
        task = getattr(self._workers, command)(
            request_id, expected_revision=expected_revision, **parameters
        )
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
            cloud_read = task in self._cloud_reads
            workflow_catalog = task in self._workflow_reads and self._workflow_reads[task] is None
            try:
                result = task.result()
                record = (
                    result.record
                    if isinstance(
                        result, (RemoteSnapshot, VerifiedResults, PromptResults, ModelTextResult)
                    )
                    else result
                )
                if cloud_read:
                    identifier, model_id = self._cloud_reads[task]
                    # A repeat read preserves the saved job's original origin.
                    # Metadata delivery needs the reader's active session, not
                    # its scene; application still needs destination approval.
                    matches = (
                        isinstance(result, StoredJob)
                        and record.intent.scope == self.scope
                        and record.remote_job_id == identifier
                        and record.intent.operation == "model"
                        and record.intent.target_id == model_id
                    )
                elif task in self._workflow_reads:
                    # Metadata has no job intent. Its exact task belongs to this
                    # scoped coordinator, which checks admission around the read;
                    # deliver() still validates the captured scene and session.
                    identifier = self._workflow_reads[task]
                    matches = (
                        isinstance(result, list)
                        if identifier is None
                        else (isinstance(result, dict) and result.get("id") == identifier)
                    )
                elif isinstance(
                    record,
                    (
                        OriginQuote,
                        FilmUploadResult,
                        LocalCaptureResult,
                        VerifiedComposition,
                        PreparedFilmReview,
                    ),
                ):
                    matches = record.origin == origin and record.scope == self.scope
                else:
                    matches = record.intent.origin == origin and record.intent.scope == self.scope
                if not matches:
                    raise OriginUnavailable("Worker returned a different job origin or scope")
            except Exception as exc:
                completion = JobCompletion(
                    origin, error=exc, cloud_read=cloud_read, workflow_catalog=workflow_catalog
                )
            else:
                completion = JobCompletion(
                    origin, result=result, cloud_read=cloud_read, workflow_catalog=workflow_catalog
                )
            finally:
                self._cloud_reads.pop(task, None)
                self._workflow_reads.pop(task, None)
                self._cleanup_upload_capture(task)
            self._issued[id(completion)] = completion
            completions.append(completion)
        return tuple(completions)

    def deliver_workflow_catalog(self, completion):
        """Consume only an owned catalog listing; grant no scene/form authority."""
        _main_thread()
        if (
            not self._active
            or self._issued.get(id(completion)) is not completion
            or not completion.workflow_catalog
        ):
            raise OriginUnavailable("Use an unconsumed workflow catalog from this active session")
        del self._issued[id(completion)]
        if completion.error is not None:
            raise completion.error
        return completion.result

    def deliver_cloud_read(self, completion):
        """Consume owned cloud metadata without granting any scene application."""
        _main_thread()
        if (
            not self._active
            or self._issued.get(id(completion)) is not completion
            or not completion.cloud_read
        ):
            raise OriginUnavailable("Use an unconsumed cloud read from this active session")
        del self._issued[id(completion)]
        if completion.error is not None:
            raise completion.error
        return completion.result

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

    def validate_destination(self, destination, *, frame=None, cursor=None):
        """Check a previously captured application destination without recapturing it."""
        _main_thread()
        if not isinstance(destination, JobOrigin):
            raise OriginUnavailable("Capture and approve the application destination")
        scene, _ = self._resolve(destination)
        if frame is not None and (type(frame) is not int or scene.frame_current != frame):
            raise OriginUnavailable("The destination frame changed; review it again")

        if cursor is not None and tuple(scene.cursor.location) != cursor:
            raise OriginUnavailable("The destination cursor changed; review it again")

    def _claim_saved_application(self, verified, destination, purpose, asset_ids):
        """Explicit recovered delivery may reuse a completed job under a new claim."""
        if verified.record.state == JobState.APPLIED:
            return self._coordinator.claim_local_application(
                verified, destination, purpose=purpose, asset_ids=asset_ids
            )
        return self._coordinator.claim_recovered_application(verified, destination)

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
            else self._claim_saved_application(
                verified,
                destination,
                "images",
                tuple(item.asset.asset_id for item in verified.record.results),
            )
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
        claim = self._claim_saved_application(verified, destination, "media", (asset_id,))
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

    def apply_recovered_model(self, completion, *, destination, asset_id, cursor):
        """Apply one selected asset to the approved scene/cursor after verification."""
        _main_thread()
        if self._issued.get(id(completion)) is not completion:
            raise OriginUnavailable("Use an unconsumed model verification from this session")
        if completion.error is not None:
            raise completion.error
        verified = completion.result
        if not isinstance(verified, VerifiedResults) or not isinstance(destination, JobOrigin):
            raise OriginUnavailable("Verify the model and approve its destination")
        scene, _ = self._resolve(destination)
        validate_model_destination(scene, cursor)
        if tuple(scene.cursor.location) != cursor:
            raise OriginUnavailable("The destination cursor changed; review it again")
        selected = [
            (item, path)
            for item, path in zip(verified.record.results, verified.paths, strict=True)
            if item.asset.asset_id == asset_id
        ]
        if len(selected) != 1:
            raise OriginUnavailable("Select one saved model asset")
        item, path = selected[0]
        del self._issued[id(completion)]
        claim = self._claim_saved_application(verified, destination, "model", (asset_id,))
        try:
            application = apply_model(scene, item, path, cursor=cursor)
        except ModelApplicationError:
            try:
                self._coordinator.fail_application(claim)
            except Exception:
                raise ModelResultUncertain() from None
            raise
        except Exception:
            raise ModelResultUncertain() from None
        try:
            record = self._coordinator.complete_application(claim)
        except Exception:
            outcome = ModelResultUncertain(application)
            self._model_receipts[outcome] = (claim, application)
            raise outcome from None
        return AppliedModel(record, application)

    def apply_recovered_mesh(
        self,
        completion,
        *,
        destination,
        asset_id,
        target,
        policy,
        result_to_source,
        keep_original,
    ):
        """Apply a selected GLB to an explicitly captured mesh, never current selection."""
        _main_thread()
        if self._issued.get(id(completion)) is not completion:
            raise OriginUnavailable("Use an unconsumed mesh verification from this session")
        if completion.error is not None:
            raise completion.error
        verified = completion.result
        if not isinstance(verified, VerifiedResults) or not isinstance(destination, JobOrigin):
            raise OriginUnavailable("Verify the mesh and approve its captured destination")
        scene, obj = self._resolve(destination)
        if target.scene != scene or target.obj != obj:
            raise OriginUnavailable("Use the exact captured mesh target")
        validate_mesh_request(
            target, policy=policy, result_to_source=result_to_source, keep_original=keep_original
        )
        selected = [
            (item, path)
            for item, path in zip(verified.record.results, verified.paths, strict=True)
            if item.asset.asset_id == asset_id
        ]
        if len(selected) != 1:
            raise OriginUnavailable("Select one saved mesh asset")
        item, path = selected[0]
        del self._issued[id(completion)]
        claim = self._claim_saved_application(verified, destination, "mesh_edit", (asset_id,))
        try:
            application = apply_saved_mesh(
                target,
                item,
                path,
                policy=policy,
                result_to_source=result_to_source,
                keep_original=keep_original,
            )
        except MeshResultApplicationError:
            try:
                self._coordinator.fail_application(claim)
            except Exception:
                raise ModelResultUncertain() from None
            raise
        except Exception:
            raise ModelResultUncertain() from None
        try:
            record = self._coordinator.complete_application(claim)
        except Exception:
            outcome = ModelResultUncertain(application)
            self._model_receipts[outcome] = (claim, application)
            raise outcome from None
        return AppliedModel(record, application)

    def retry_model_receipt(self, outcome):
        _main_thread()
        if not isinstance(outcome, ModelResultUncertain) or outcome not in self._model_receipts:
            raise OriginUnavailable("Use a pending model receipt from this session")
        claim, application = self._model_receipts[outcome]
        try:
            record = self._coordinator.retry_application_receipt(claim)
        except Exception:
            raise outcome from None
        del self._model_receipts[outcome]
        return AppliedModel(record, application)

    def apply_recovered_material(self, completion, *, destination, target):
        _main_thread()
        if self._issued.get(id(completion)) is not completion:
            raise OriginUnavailable("Use an unconsumed material verification from this session")
        if completion.error is not None:
            raise completion.error
        verified = completion.result
        if not isinstance(verified, VerifiedResults) or not isinstance(destination, JobOrigin):
            raise OriginUnavailable("Verify the material and approve its destination")
        scene, obj = self._resolve(destination)
        if target.scene != scene or target.obj != obj:
            raise OriginUnavailable("Use the exact approved material target")
        validate_target(target)
        roles = selected_maps(verified.record)
        del self._issued[id(completion)]
        claim = self._claim_saved_application(
            verified,
            destination,
            "material",
            tuple(verified.record.results[index].asset.asset_id for index in roles.values()),
        )
        try:
            application = apply_material(verified, target)
        except MaterialApplicationError:
            try:
                self._coordinator.fail_application(claim)
            except Exception:
                raise MaterialResultUncertain() from None
            raise
        except Exception:
            raise MaterialResultUncertain() from None
        try:
            record = self._coordinator.complete_application(claim)
        except Exception:
            outcome = MaterialResultUncertain(application)
            self._material_receipts[outcome] = (claim, application)
            raise outcome from None
        return AppliedMaterial(record, application)

    def retry_material_receipt(self, outcome):
        _main_thread()
        if (
            not isinstance(outcome, MaterialResultUncertain)
            or outcome not in self._material_receipts
        ):
            raise OriginUnavailable("Use a pending material receipt from this session")
        claim, application = self._material_receipts[outcome]
        try:
            record = self._coordinator.retry_application_receipt(claim)
        except Exception:
            raise outcome from None
        del self._material_receipts[outcome]
        return AppliedMaterial(record, application)

    def apply_world(self, completion, *, asset_id):
        return self._apply_world(completion, asset_id=asset_id)

    def apply_recovered_world(self, completion, *, destination, asset_id):
        if not isinstance(destination, JobOrigin):
            raise OriginUnavailable("Capture and approve the panorama destination")
        return self._apply_world(completion, asset_id=asset_id, destination=destination)

    def _apply_world(self, completion, *, asset_id, destination=None):
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
        scene, _ = self._resolve(completion.origin if destination is None else destination)
        previous = scene.world
        worlds, images = set(bpy.data.worlds), set(bpy.data.images)
        # Consumption precedes the durable claim: a storage failure can occur
        # after committing APPLYING. Never reuse this completion to infer safety.
        del self._issued[id(completion)]
        claim = (
            self._coordinator.claim_application(verified)
            if destination is None
            else self._claim_saved_application(verified, destination, "world", (asset_id,))
        )
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
        self._history_revision += 1
        self._origins.reset()
        self._scenes.clear()
        self._targets.clear()
        self._target_scenes.clear()
        self._mesh_sources.clear()

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
                self._cloud_reads.clear()
                self._workflow_reads.clear()
                self._issued.clear()
                self._world_receipts.clear()
                self._image_receipts.clear()
                self._media_receipts.clear()
                self._model_receipts.clear()
                self._material_receipts.clear()
                self._film_review_receipts.clear()
                self.film_shots.close()
                self.film_timeline.close()
                self.film_capture.close()
                if self._coordinator.film_review_cleanup_pending:
                    self._film_cleanup_retry_at = time.monotonic() + 5.0
                else:
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
            if (
                not session._active
                and time.monotonic() >= session._film_cleanup_retry_at
                and all(task.done() for task, _ in session._pending)
            ):
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
    if _session_snapshot() and not bpy.app.timers.is_registered(_reap_inactive):
        bpy.app.timers.register(_reap_inactive, first_interval=0.25, persistent=True)


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
