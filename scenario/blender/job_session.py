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
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path
from weakref import WeakKeyDictionary, WeakValueDictionary

import bpy
from bpy.app.handlers import persistent

from ..core.jobs import local_case_study, local_export
from ..core.jobs.coordinator import (
    FilmUploadResult,
    JobCoordinator,
    LocalCaptureResult,
    LocalExportResult,
    OriginQuote,
    RemoteSnapshot,
)
from ..core.jobs.film_media import VerifiedComposition
from ..core.jobs.film_review_media import PreparedFilmReview
from ..core.jobs.organization import (
    OrganizationRequest,
    OrganizationResult,
    OrganizationSnapshot,
)
from ..core.jobs.origins import OriginRevisions
from ..core.jobs.preview_scheduler import ResultPreviewScheduler
from ..core.jobs.reconcile import CandidateLookup
from ..core.jobs.results import (
    ModelTextResult,
    PreparedModelImport,
    PromptResults,
    VerifiedResults,
)
from ..core.jobs.session_spend import SessionSpend
from ..core.jobs.store import JobOrigin, JobState, StoredJob
from ..core.jobs.workers import ExportTask, JobWorkers, LocalExportWorker
from ..core.scene import landing
from . import file_state, mesh_result_application, model_application
from .film_application import FilmShotCommands
from .image_application import ImageApplicationError, apply_images
from .landing_application import (
    LandingApplicationError,
    apply_camera_background,
    apply_image_plane,
)
from .material_application import (
    MaterialApplicationError,
    apply_material,
    selected_maps,
    validate_target,
)
from .media_application import MediaApplicationError, apply_media
from .mesh_result_application import (
    MeshResultApplicationError,
    apply_saved_mesh,
    prepare_saved_mesh,
)
from .mesh_result_application import validate_request as validate_mesh_request
from .model_application import (
    MESH_FORMATS,
    ModelApplicationError,
    import_plan,
    import_snapshot,
    importable,
    prepare_snapshot,
    worker_prepared,
)
from .model_application import validate_destination as validate_model_destination
from .splat_application import import_splat
from .world_application import PanoramaError, WorldApplication, WorldApplicationError, apply_world

_log = logging.getLogger("scenario.jobs")


def _changed(message, *, recorded=False):
    """Mark the file modified once an application changed scene data, or may have.

    Results arrive from the maintenance pump or a local MCP call, outside any
    operator that records Undo. A refusal whose rollback was verified marks
    nothing; an uncertain outcome, which may leave data behind, is marked.
    Saved models and mesh edits record their own desktop Undo checkpoints when
    Blender allows it (``recorded``); a second step would make the next Undo
    appear to do nothing.
    """
    if not recorded:
        file_state.mark_modified(message)


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


class LandingResultUncertain(MediaResultUncertain):
    """A camera background or image plane may already exist; retry only its receipt."""

    def __init__(self, application=None):
        RuntimeError.__init__(self, "Result application needs inspection; do not apply it again")
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
    asset_library: bool = False
    local_export: bool = False
    asset_organization: bool = False


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
        preview_root=None,
        preview_waveform=None,
        spend=None,
    ):
        _main_thread()
        if not _registered:
            raise RuntimeError("Register Blender lifecycle hooks before creating a session")
        if type(completion_limit) is not int or completion_limit < 1:
            raise ValueError("Use a positive completion limit")
        self._completion_limit = completion_limit
        # Accepted jobs' quotes for the Jobs panel; the runtime keeps one per connection.
        self.spend = SessionSpend(getattr(store, "scope", None)) if spend is None else spend
        self._origins = OriginRevisions()
        self._scenes = {}
        self._synchronizing = ()
        self._targets = {}
        self._target_scenes = {}
        self._pending = []
        self._cloud_reads = {}
        self._workflow_reads = {}
        self._asset_reads = set()
        self._organization_tasks = {}
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
        # Previews poll and download on the workers' dedicated preview lane,
        # which also runs the owned offline Blender that decodes audio envelopes.
        self._previews = (
            None
            if preview_root is None
            else ResultPreviewScheduler(
                self._workers, self._coordinator, preview_root, waveform=preview_waveform
            )
        )
        # Film video export owns its thread: hours of local encoding must not
        # reduce the shared workers' polling/download capacity.
        self._exports = LocalExportWorker(self._coordinator)
        self.film_shots = FilmShotCommands(self, store)
        from .film_timeline import FilmTimelineCommands

        self.film_timeline = FilmTimelineCommands(self)
        from .film_capture import FilmCaptureCommands

        self.film_capture = FilmCaptureCommands(self)
        from .film_review_commands import FilmReviewCommands

        self.film_review = FilmReviewCommands(self, store)
        from .film_export import FilmExportCommands

        self.film_export = FilmExportCommands(self)
        from .film_case_study import FilmCaseStudyCommands

        self.film_case_study = FilmCaseStudyCommands(self, store)
        from .asset_organization import AssetOrganization

        self.asset_organization = AssetOrganization(self)
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

    @property
    def result_previews(self):
        """Receipt-bound saved-result previews for this connection, on the main thread.

        Previews never resolve an origin, mutate the scene or authorize application.
        """
        _main_thread()
        if self._previews is None:
            raise OriginUnavailable("Result previews are not configured for this connection")
        if not self._active:
            raise OriginUnavailable("This job connection is no longer active")
        return self._previews

    def service_previews(self):
        """Advance preview polling from the main-thread GUI timer or headless loop."""
        _main_thread()
        if not self._active or self._previews is None:
            return False
        return self._previews.pump()

    def prepare_playback(
        self, request_id, *, expected_revision, asset_id, root, reuse=None, discard=(), keep=()
    ):
        """Queue a private verified player copy of one saved result on the preview lane.

        The returned task resolves to a ``PlaybackCopy`` that the caller owns
        and must discard; it is not a session completion, so ``drain`` never
        returns it. Like previews, it resolves no origin and grants no
        application authority.
        """
        _main_thread()
        if not self._active:
            raise OriginUnavailable("This job connection is no longer active")
        return self._workers.prepare_playback(
            request_id,
            expected_revision=expected_revision,
            asset_id=asset_id,
            root=root,
            reuse=reuse,
            discard=discard,
            keep=keep,
        )

    def cancel_playback(self, task):
        """Signal a queued or running playback copy; its partial copy is removed."""
        _main_thread()
        self._workers.cancel_preview(task)

    def world_sizes(self, targets):
        """Queue a header read of saved World candidates on the preview lane.

        Targets are (request_id, asset_id, receipt SHA-256) triples. The task
        resolves to each target with its declared (width, height) or None. Like
        playback copies it is not a session completion, so ``drain`` never
        returns it, and it resolves no origin and grants no application authority.
        """
        _main_thread()
        if not self._active:
            raise OriginUnavailable("This job connection is no longer active")
        return self._workers.world_sizes(targets)

    def result_files(self, targets):
        """Queue a rehash of saved results for local MCP job_status on the preview lane.

        Targets are (request_id, asset_id, receipt SHA-256) triples. The task
        resolves to each target with its ``FileCheck`` or None. Like the World
        size read it is not a session completion and grants no authority.
        """
        _main_thread()
        if not self._active:
            raise OriginUnavailable("This job connection is no longer active")
        return self._workers.result_files(targets)

    def verified_files(self, request_id):
        """(asset_id, FileCheck) pairs this connection verified while downloading or
        importing the job's results. Memory only: nothing is read or queued."""
        _main_thread()
        if not self._active:
            return ()
        return self._coordinator.verified_files(request_id)

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

    def origin_current(self, origin):
        """Whether a captured origin is still current; reads only, captures nothing new."""
        _main_thread()
        return self._active and isinstance(origin, JobOrigin) and self._origins.current(origin)

    def capture_destination(self, scene):
        """Capture only the scene a payload is for, when that payload does not come from it.

        A file the user chose keeps its bytes whatever the scene does, and an Image
        job's results import into the scene it was submitted from, so scene, frame
        and render updates keep this origin. Removing the scene, Undo/Redo, file
        loading and retirement revoke it, and delivery still requires the selected
        scene. Never use it to price, submit or apply scene content.
        """
        return self._origins.capture_destination(self._scene_identity(scene, ()))

    def capture_many(self, scene, targets):
        """Validate one current scene-membership snapshot before recording any origins."""
        _main_thread()
        targets = tuple(targets)
        scene_id = self._scene_identity(scene, targets)
        origins = []
        for target in targets:
            target_id = self._identity(self._targets, target) if target is not None else None
            if target_id is not None:
                self._target_scenes.setdefault(target_id, set()).add(scene_id)
            origins.append(self._origins.capture(scene_id, target_id))
        return tuple(origins)

    def _scene_identity(self, scene, targets):
        _main_thread()
        if not self._active:
            raise OriginUnavailable("This job context is inactive")
        try:
            if scene not in tuple(bpy.data.scenes):
                raise OriginUnavailable("The originating scene is unavailable")
            members = set(scene.objects) if any(target is not None for target in targets) else ()
            if any(target is not None and target not in members for target in targets):
                raise OriginUnavailable("The target is not in the originating scene")
        except ReferenceError:
            raise OriginUnavailable("The original scene or target was removed") from None
        return self._identity(self._scenes, scene)

    def retain_mesh_source(self, origin, source, target):
        """Retain a bounded live export guard; saved metadata cannot recreate it.

        `target` is one `MeshTarget`, or a tuple of them in export order for a
        several-object export, whose origin is the scene's rather than an object's.
        """
        from dataclasses import replace

        from .mesh_application import validate_target
        from .mesh_export_fingerprint import fingerprints

        _main_thread()
        targets = target if isinstance(target, tuple) else (target,)
        for item in targets:
            validate_target(item)
        several = isinstance(target, tuple)
        if (
            len(source.objects) != len(targets)
            or several != (len(targets) > 1)
            or (several and self.capture(targets[0].scene) != origin)
        ):
            raise OriginUnavailable("The captured mesh context changed during export")
        hashes = fingerprints(item.mesh for item in targets)
        for item, exported, digest in zip(targets, source.objects, hashes, strict=True):
            if self.capture(item.scene, item.obj) != replace(origin, target_id=exported.target_id):
                raise OriginUnavailable("The captured mesh context changed during export")
            # Export provenance and edit guards use distinct fingerprint formats.
            # Compare like formats while retaining the stricter validated edit guard.
            if exported.geometry_sha256 != digest.hex() or exported.matrix_world != tuple(
                tuple(row) for row in item.obj.matrix_world
            ):
                raise OriginUnavailable("The exported mesh does not match its live source")
        key = (origin, source)
        # Never evict an older export's authority to admit another snapshot.
        # Further uploads remain valid references, without original-source apply.
        if key in self._mesh_sources or len(self._mesh_sources) < 128:
            self._mesh_sources[key] = target

    def retained_mesh_source(self, binding):
        """The retained targets for `binding`, in export order, without validating them.

        None when this session holds no live export guard for it.
        """
        _main_thread()
        target = self._mesh_sources.get((binding.origin, binding.mesh_source))
        if not self._active or target is None:
            return None
        return target if isinstance(target, tuple) else (target,)

    def mesh_source_targets(self, binding):
        """Resolve only a retained export, every object in export order.

        Current selection and names are irrelevant. Every target must still be
        unchanged, or the whole retained export is refused.
        """
        from .mesh_application import validate_target

        _main_thread()
        target = self._mesh_sources.get((binding.origin, binding.mesh_source))
        if not self._active or target is None:
            raise OriginUnavailable(
                "The live captured source is unavailable; review another destination"
            )
        targets = target if isinstance(target, tuple) else (target,)
        original = binding.origin
        for item, exported in zip(targets, binding.mesh_source.objects, strict=True):
            validate_target(item)
            current = self.capture(item.scene, item.obj)
            # Unrelated scene changes may advance its revision. The frozen source
            # guard proves this object unchanged, while file/scene/object IDs must
            # still belong to this exact session. Undo/load retire that authority.
            if (current.file_id, current.scene_id, current.target_id) != (
                original.file_id,
                original.scene_id,
                exported.target_id,
            ):
                raise OriginUnavailable("The captured source context was replaced")
        return targets

    def mesh_source_objects(self, binding, scene):
        """The live objects of one uploaded mesh source in `scene`, in export order, or None.

        Reads only, for where an import of the edit may land: unlike
        `mesh_source_targets`, it grants no in-place edit, so the source may have
        changed since export. Undo, file loading and retirement forget the
        identities, and an object removed or out of `scene` gives None.
        """
        _main_thread()
        objects = []
        try:
            if not self._active or self._scenes.get(binding.origin.scene_id) != scene:
                return None
            members = tuple(scene.objects)
            for exported in binding.mesh_source.objects:
                obj = self._targets.get(exported.target_id)
                if obj is None or obj not in members or obj.type != "MESH":
                    return None
                objects.append(obj)
        except ReferenceError:
            return None
        return tuple(objects)

    def mesh_source_target(self, binding):
        """Resolve a retained single-object export; see `mesh_source_targets`."""
        targets = self.mesh_source_targets(binding)
        if len(targets) != 1:
            raise OriginUnavailable("The captured source has several objects")
        return targets[0]

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

    def asset_library(self, scene, *, query=None, **options):
        """Read one library page through this session's existing scoped workers."""
        _main_thread()
        self._check_capacity()
        origin = self.capture(scene)
        task = (
            self._workers.asset_page(**options)
            if query is None
            else self._workers.search_assets(query, **options)
        )
        self._asset_reads.add(task)
        self._pending.append((task, origin))
        return task

    def _organization_command(self, kind, command, *args, **options):
        """Admit connection-scoped organization work; it records no scene origin.

        Organization changes Scenario metadata, not Blender data, so scene
        switches and undo do not affect it. Retirement still stops admission
        and rejects late delivery into a replacement connection.
        """
        _main_thread()
        if not self._active:
            raise OriginUnavailable("This job context is inactive")
        self._check_capacity()
        task = getattr(self._workers, command)(*args, **options)
        self._organization_tasks[task] = kind
        self._pending.append((task, None))
        return task

    def organization_snapshot(self, request):
        """Queue the fresh read an organization review shows; it sends no write."""
        if not isinstance(request, OrganizationRequest) or request.scope != self.scope:
            raise OriginUnavailable("The organization request belongs to another connection")
        return self._organization_command("snapshot", "organization_snapshot", request)

    def organize(self, snapshot):
        """Queue one approved organization change on this session's workers."""
        if not isinstance(snapshot, OrganizationSnapshot) or snapshot.scope != self.scope:
            raise OriginUnavailable("The organization review belongs to another connection")
        return self._organization_command("apply", "organize", snapshot)

    def collection_page(self, *, page_size=50, pagination_token=None):
        """Queue one collection page read in the selected connection."""
        return self._organization_command(
            "collections", "collection_page", page_size=page_size, pagination_token=pagination_token
        )

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
        # Refuse before saving an intent that submit() could not queue.
        self._check_capacity()
        self._resolve(quote.origin)
        return self._coordinator.prepare_quote(quote)

    def prepare(self, estimate, *, origin):
        """Use the origin captured with inputs before requesting the estimate."""
        _main_thread()
        self._resolve(origin)
        return self._coordinator.prepare(estimate, origin)

    def mark_unconfirmed_reviewed(self, request_id, *, expected_revision):
        """Let identical requests through again this session; local, sends nothing."""
        _main_thread()
        self._coordinator.mark_unconfirmed_reviewed(request_id, expected_revision=expected_revision)

    def unconfirmed_reviewed(self, request_id):
        return self._coordinator.unconfirmed_reviewed(request_id)

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
        self.spend.sent(prepared.intent.request_id, prepared.intent.quote_cost)
        return task

    def refresh_remote(self, request_id, *, expected_revision, automatic=False):
        """Queue one known-job read; `automatic` polls make a single attempt."""
        return self._record_command(
            "refresh_remote", request_id, expected_revision, automatic=automatic
        )

    def unconfirmed_candidates(self, request_id, *, expected_revision):
        """Queue a read-only cloud listing for an unconfirmed request; saves nothing."""
        return self._record_command("unconfirmed_candidates", request_id, expected_revision)

    def link_unconfirmed(self, request_id, *, expected_revision, remote_job_id):
        """Queue a confirmed, verified link of one cloud job; never submits."""
        return self._record_command(
            "link_unconfirmed", request_id, expected_revision, remote_job_id=remote_job_id
        )

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

    def decide_workflow_node(
        self, request_id, *, expected_revision, node_id, review_id, action, selected_indices=None
    ):
        """Queue one reviewed waiting-step decision under the saved job's original scope.

        Like cancellation it needs no current scene: the completion carries the
        stored origin, and the coordinator checks the step and review again.
        """
        return self._record_command(
            "decide_workflow_node",
            request_id,
            expected_revision,
            node_id=node_id,
            review_id=review_id,
            action=action,
            selected_indices=selected_indices,
        )

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
        """Queue an explicit download on the transfer lane under the private storage policy."""
        return self._record_command("download_results", request_id, expected_revision)

    def cancel_download(self, task):
        """Stop one of this session's downloads at its next chunk, without a receipt.

        The job then reads `download_failed`; its completed receipts stay and a
        later explicit download resumes the rest. Retirement cancels them all.
        """
        _main_thread()
        if any(pending is task for pending, _ in self._pending):
            self._workers.cancel_transfer(task)

    def verify_results(self, request_id, *, expected_revision):
        """Queue local receipt verification; this does not authorize application."""
        return self._record_command("verify_results", request_id, expected_revision)

    def prepare_model_import(self, request_id, *, expected_revision, asset_id, options):
        """Queue worker verification and one saved splat decode in the local slot.

        A PLY without splat data comes back as a mesh. Like verification, the
        preparation authorizes nothing until an approved application claims it.
        """
        return self._record_command(
            "prepare_model_import",
            request_id,
            expected_revision,
            asset_id=asset_id,
            options=options,
        )

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

    @staticmethod
    def _export_destination(destination, staging, *, suffix=".mp4"):
        """Resolve an approved export path outside staging, extension and Blender storage.

        Every UI or MCP caller passes through here, so a relative, existing,
        non-portable or private destination never reaches a thread or placeholder.
        ``suffix`` is ``.mp4`` for a video and ``.zip`` for a case-study archive.
        """
        package = __package__.rsplit(".", 1)[0]
        roots = (
            staging,
            bpy.utils.extension_path_user(package),
            Path(__file__).resolve().parent.parent,
            bpy.utils.resource_path("USER"),
            bpy.utils.user_resource("EXTENSIONS"),
        )
        return local_export.validate_destination(destination, private_roots=roots, suffix=suffix)

    @staticmethod
    def _export_programs(spec):
        """Refuse a specification whose child is not this Blender running the bundled worker."""
        expected = (
            Path(bpy.app.binary_path).resolve(),
            Path(__file__).with_name("film_export_worker.py").resolve(),
        )
        if (spec.binary, spec.worker) != expected:
            raise ValueError("Use a Film export snapshot from this Blender and extension")

    def export_film(self, spec, destination, *, origin, source_origin):
        """Start one approved offline video export on the session's owned export thread.

        ``origin`` is the selected working scene and ``source_origin`` the exported
        scene. The caller owns destination approval and the snapshot's staging
        directory. The destination is validated here, on the main thread, before
        any thread, placeholder or media hashing starts. No Scenario request, spend
        or scene mutation follows.
        """
        _main_thread()
        if not isinstance(spec, local_export.ExportSpec):
            raise TypeError("Use a Film export specification")
        self._export_programs(spec)
        self._check_capacity()
        self._resolve(origin)
        if not self._origins.current(source_origin):
            raise OriginUnavailable("The selected export scene changed")
        destination = self._export_destination(destination, spec.directory.parent)
        local_export.check_unused(spec)
        task = self._exports.export_film(
            spec, destination, origin=origin, source_origin=source_origin
        )
        self._pending.append((task, origin))
        return task

    @staticmethod
    def _case_study_programs(spec):
        """Refuse a case study whose child is not this Blender running the bundled worker."""
        expected = (
            Path(bpy.app.binary_path).resolve(),
            Path(__file__).with_name("film_case_study_worker.py").resolve(),
        )
        if (spec.binary, spec.worker) != expected:
            raise ValueError("Use a Film case-study snapshot from this Blender and extension")

    def export_case_study(self, spec, destination, *, origin, source_origin):
        """Start one approved case-study bundle on the session's owned export thread.

        As for ``export_film``, the caller owns approval and the staging directory,
        and the ``.zip`` destination is validated here before any work starts. No
        Scenario request, spend or scene mutation follows.
        """
        _main_thread()
        if not isinstance(spec, local_case_study.CaseStudySpec):
            raise TypeError("Use a Film case-study specification")
        self._case_study_programs(spec)
        self._check_capacity()
        self._resolve(origin)
        if not self._origins.current(source_origin):
            raise OriginUnavailable("The selected case-study scene changed")
        destination = self._export_destination(destination, spec.directory.parent, suffix=".zip")
        local_export.check_unused(spec)
        task = self._exports.export_case_study(
            spec, destination, origin=origin, source_origin=source_origin
        )
        self._pending.append((task, origin))
        return task

    def publish_film_export(self, staged, destination, *, origin, source_origin):
        """Copy a verified staged export to another approved destination; never re-render."""
        _main_thread()
        if not isinstance(staged, local_export.StagedFile):
            raise TypeError("Use a verified staged Film export")
        self._check_capacity()
        if not self._active:
            raise OriginUnavailable("This export session is inactive")
        suffix = ".zip" if isinstance(staged, local_case_study.StagedBundle) else ".mp4"
        destination = self._export_destination(destination, staged.directory.parent, suffix=suffix)
        task = self._exports.publish_film_export(
            staged, destination, origin=origin, source_origin=source_origin
        )
        self._pending.append((task, origin))
        return task

    def cancel_film_export(self, task):
        _main_thread()
        if any(pending is task for pending, _ in self._pending):
            self._exports.cancel(task)

    def deliver_local_export(self, completion):
        """Consume one export outcome from this active session; no scene is resolved.

        Export never mutates Blender data. Like the asset library, workflow catalog
        and cloud read deliveries, an inactive session hands out no outcome, even
        before a shutdown clears issued outcomes.
        """
        _main_thread()
        if (
            not self._active
            or self._issued.get(id(completion)) is not completion
            or not completion.local_export
        ):
            raise OriginUnavailable(
                "Use an unconsumed Film export outcome from this active session"
            )
        del self._issued[id(completion)]
        if completion.error is not None:
            raise completion.error
        return completion.result

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

    def restart_upload(self, request_id, *, expected_revision, origin):
        """Queue abandonment of an uncompleted upload and restaging under a current origin."""
        _main_thread()
        self._check_capacity()
        if self.inspect_upload(request_id) is None:
            raise OriginUnavailable("The upload is not in this connection's store")
        self._resolve(origin)
        task = self._workers.restart_upload(
            request_id, expected_revision=expected_revision, origin=origin
        )
        self._pending.append((task, origin))
        return task

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
                if isinstance(result, PreparedModelImport):
                    record = result.verified.record
                elif isinstance(
                    result,
                    (
                        RemoteSnapshot,
                        VerifiedResults,
                        PromptResults,
                        ModelTextResult,
                        CandidateLookup,
                    ),
                ):
                    record = result.record
                else:
                    record = result
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
                elif task in self._asset_reads:
                    matches = isinstance(result, dict) and isinstance(result.get("assets"), list)
                elif task in self._organization_tasks:
                    # Connection-scoped: the result names its scope, not a scene.
                    kind = self._organization_tasks[task]
                    if kind == "collections":
                        matches = isinstance(result, dict) and isinstance(
                            result.get("collections"), list
                        )
                    else:
                        expected = (
                            OrganizationSnapshot if kind == "snapshot" else OrganizationResult
                        )
                        matches = isinstance(result, expected) and result.scope == self.scope
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
                        LocalExportResult,
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
                    origin,
                    error=exc,
                    cloud_read=cloud_read,
                    workflow_catalog=workflow_catalog,
                    asset_library=task in self._asset_reads,
                    local_export=isinstance(task, ExportTask),
                    asset_organization=task in self._organization_tasks,
                )
            else:
                completion = JobCompletion(
                    origin,
                    result=result,
                    cloud_read=cloud_read,
                    workflow_catalog=workflow_catalog,
                    asset_library=task in self._asset_reads,
                    local_export=isinstance(task, ExportTask),
                    asset_organization=task in self._organization_tasks,
                )
                # A submission, or a later read of a linked one, that carries Scenario's job ID.
                self.spend.accepted(record)
            finally:
                self._cloud_reads.pop(task, None)
                self._workflow_reads.pop(task, None)
                self._asset_reads.discard(task)
                self._organization_tasks.pop(task, None)
                self._cleanup_upload_capture(task)
            self._issued[id(completion)] = completion
            completions.append(completion)
        return tuple(completions)

    def deliver_asset_library(self, completion):
        """Consume scoped library metadata without granting destination authority."""
        _main_thread()
        if (
            not self._active
            or self._issued.get(id(completion)) is not completion
            or not completion.asset_library
        ):
            raise OriginUnavailable("Use an unconsumed asset library page from this active session")
        del self._issued[id(completion)]
        if completion.error is not None:
            raise completion.error
        return completion.result

    def deliver_asset_organization(self, completion):
        """Consume one owned organization outcome; it never resolves a scene.

        A retired session rejects delivery, so a late outcome cannot reach a
        replacement connection. Writes already sent keep their service effect.
        """
        _main_thread()
        if (
            not self._active
            or self._issued.get(id(completion)) is not completion
            or not completion.asset_organization
        ):
            raise OriginUnavailable(
                "Use an unconsumed organization outcome from this active session"
            )
        del self._issued[id(completion)]
        if completion.error is not None:
            raise completion.error
        return completion.result

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

    def apply_images(self, completion, *, destination=None):
        """Import an Image job's verified results without another review.

        Into the intent's origin, or into `destination`, the destination-only origin
        captured when the job was submitted (`capture_destination`). Never imports an
        applied job again.
        """
        _main_thread()
        if destination is not None and not isinstance(destination, JobOrigin):
            raise OriginUnavailable("Capture the image import destination at submission")
        return self._apply_images(completion, destination=destination, reuse=False)

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

    def verified_result(self, completion, *, destination, asset_id):
        """Consume one verification for an approved destination, without a claim.

        For form bindings that reuse a saved asset rather than change scene
        content. Returns the resolved scene, the selected result and its path;
        the caller rechecks its own destination before any mutation.
        """
        _main_thread()
        if self._issued.get(id(completion)) is not completion:
            raise OriginUnavailable("Use an unconsumed verification from this session")
        if completion.error is not None:
            raise completion.error
        verified = completion.result
        if not isinstance(verified, VerifiedResults) or not isinstance(destination, JobOrigin):
            raise OriginUnavailable("Verify the saved result and approve its destination")
        scene, _ = self._resolve(destination)
        selected = [
            (item, path)
            for item, path in zip(verified.record.results, verified.paths, strict=True)
            if item.asset.asset_id == asset_id
        ]
        if len(selected) != 1:
            raise OriginUnavailable("Select one saved result asset")
        del self._issued[id(completion)]
        return (scene, *selected[0])

    def _claim_saved_application(self, verified, destination, purpose, asset_ids):
        """Explicit recovered delivery may reuse a completed job under a new claim."""
        if verified.record.state == JobState.APPLIED:
            return self._coordinator.claim_local_application(
                verified, destination, purpose=purpose, asset_ids=asset_ids
            )
        return self._coordinator.claim_recovered_application(verified, destination)

    def _apply_images(self, completion, *, destination=None, reuse=True):
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
        if destination is None:
            claim = self._coordinator.claim_application(verified)
        elif reuse:
            claim = self._claim_saved_application(
                verified,
                destination,
                "images",
                tuple(item.asset.asset_id for item in verified.record.results),
            )
        else:
            # Same claim as recovery, without reopening an applied job.
            claim = self._coordinator.claim_recovered_application(verified, destination)
        try:
            images = apply_images(verified)
        except ImageApplicationError:
            if set(bpy.data.images) != before:
                _changed("Scenario image import")
                raise ImageResultUncertain() from None
            try:
                self._coordinator.fail_application(claim)
            except Exception:
                raise ImageResultUncertain() from None
            raise
        except Exception:
            if set(bpy.data.images) != before:
                _changed("Scenario image import")
            raise ImageResultUncertain() from None
        _changed("Scenario image import")
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
            _changed("Scenario media import")
            raise MediaResultUncertain() from None
        _changed("Scenario media import")
        try:
            record = self._coordinator.complete_application(claim)
        except Exception:
            outcome = MediaResultUncertain(application)
            self._media_receipts[outcome] = (claim, application)
            raise outcome from None
        return AppliedMedia(record, application)

    def apply_recovered_landing(
        self, completion, *, destination, asset_id, purpose, frame=None, cursor=None, unlit=False
    ):
        """Add one verified image or video as the approved camera's background, or an image plane.

        The destination binds the scene and, for a background, its camera; a video
        background also binds the current frame and a plane the cursor. A video is
        claimed as media and an image as images, so stored labels stay unchanged.
        """
        _main_thread()
        if self._issued.get(id(completion)) is not completion:
            raise OriginUnavailable("Use an unconsumed verification from this session")
        if completion.error is not None:
            raise completion.error
        verified = completion.result
        if not isinstance(verified, VerifiedResults) or not isinstance(destination, JobOrigin):
            raise OriginUnavailable("Verify the saved result and approve its destination")
        scene, camera = self._resolve(destination)
        if frame is not None and (type(frame) is not int or scene.frame_current != frame):
            raise OriginUnavailable("The destination frame changed; review it again")
        if cursor is not None and tuple(scene.cursor.location) != cursor:
            raise OriginUnavailable("The destination cursor changed; review it again")
        background = purpose == landing.CAMERA_BACKGROUND
        if purpose not in landing.PURPOSES or (
            background and (camera is None or scene.camera != camera)
        ):
            raise OriginUnavailable("The scene camera changed; review it again")
        if not background and (cursor is None or type(unlit) is not bool):
            raise OriginUnavailable("Approve the plane's cursor again")
        selected = [
            (item, path)
            for item, path in zip(verified.record.results, verified.paths, strict=True)
            if item.asset.asset_id == asset_id and landing.accepts(purpose, item.asset.media_type)
        ]
        if len(selected) != 1:
            raise OriginUnavailable("Select one saved image or video")
        item, path = selected[0]
        del self._issued[id(completion)]
        label = "media" if landing.kind(item.asset.media_type) == "video" else "images"
        claim = self._claim_saved_application(verified, destination, label, (asset_id,))
        try:
            if background:
                application = apply_camera_background(scene, camera, item, path, frame=frame)
            else:
                application = apply_image_plane(scene, item, path, cursor=cursor, unlit=unlit)
        except LandingApplicationError:
            try:
                self._coordinator.fail_application(claim)
            except Exception:
                raise LandingResultUncertain() from None
            raise
        except Exception:
            _changed("Scenario result application")
            raise LandingResultUncertain() from None
        _changed("Scenario result application")
        try:
            record = self._coordinator.complete_application(claim)
        except Exception:
            outcome = LandingResultUncertain(application)
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

    def apply_recovered_model(
        self,
        completion,
        *,
        destination,
        asset_id,
        cursor,
        options=None,
        target_size=None,
        placement=None,
    ):
        """Import one saved model unit at the approved scene/cursor after worker preparation.

        `asset_id` is the unit key classified from the verified record. A mesh unit
        comes from `verify_results`: every member is rehashed into a private
        snapshot before the claim, so a changed or unsupported package raises
        ModelPreflightError and leaves the saved job and the scene unchanged. An
        SPZ, .splat or PLY unit comes from `prepare_model_import` with exactly the
        approved `options`; decoded splats become a new point cloud, and a PLY
        without splat data takes the mesh snapshot path. A PLY may also come from
        `verify_results` when the local-operation slot was busy; it then imports
        only as a mesh. A reuse claim of a completed job names every member read.
        `target_size` is the approved longest side in metres, or None for the saved size.
        `placement` is where the bottom center lands when it is not the approved
        cursor, such as on the source mesh an edit replaces; the cursor is checked either way.
        """
        _main_thread()
        if self._issued.get(id(completion)) is not completion:
            raise OriginUnavailable("Use an unconsumed model verification from this session")
        if completion.error is not None:
            raise completion.error
        prepared = completion.result if isinstance(completion.result, PreparedModelImport) else None
        verified = prepared.verified if prepared is not None else completion.result
        if not isinstance(verified, VerifiedResults) or not isinstance(destination, JobOrigin):
            raise OriginUnavailable("Verify the model and approve its destination")
        scene, _ = self._resolve(destination)
        validate_model_destination(scene, cursor)
        if tuple(scene.cursor.location) != cursor:
            raise OriginUnavailable("The destination cursor changed; review it again")
        if placement is None:
            placement = cursor
        validate_model_destination(scene, placement)
        try:
            unit = import_plan(verified.record).unit(asset_id)
        except ValueError:
            unit = None
        if unit is None or not importable(unit):
            raise OriginUnavailable("Select one importable saved model")
        # A worker-read unit needs the preparation of this exact file and options.
        # A PLY verified without it, while the local slot was busy, imports only
        # through the mesh snapshot path, which refuses splat data.
        if prepared is None:
            accepted = unit.format in MESH_FORMATS
        else:
            accepted = (
                worker_prepared(unit)
                and prepared.asset_id == unit.key
                and prepared.options == options
            )
        if not accepted:
            raise OriginUnavailable("Prepare the selected model with its approved options again")
        files = {
            item.asset.asset_id: (item, path)
            for item, path in zip(verified.record.results, verified.paths, strict=True)
        }
        del self._issued[id(completion)]
        if prepared is not None and prepared.splat is not None:
            claim = self._claim_saved_application(verified, destination, "model", unit.members)
            return self._finish_model(
                claim,
                lambda: import_splat(
                    scene,
                    prepared.splat,
                    cursor=placement,
                    unit_key=unit.key,
                    members=unit.members,
                    fmt=unit.format.value,
                    history=True,
                    target_size=target_size,
                ),
            )
        snapshot = prepare_snapshot(unit, files)
        try:
            claim = self._claim_saved_application(verified, destination, "model", snapshot.members)
            return self._finish_model(
                claim,
                lambda: import_snapshot(
                    scene, snapshot, cursor=placement, history=True, target_size=target_size
                ),
            )
        finally:
            snapshot.cleanup()

    def _finish_model(self, claim, run):
        """Run one claimed model import; failures keep receipt-only recovery."""
        try:
            application = run()
        except ModelApplicationError:
            try:
                self._coordinator.fail_application(claim)
            except Exception:
                raise ModelResultUncertain() from None
            raise
        except Exception:
            # Its checkpoint before importing already marked the file.
            _changed("Scenario model import", recorded=model_application._undo_enabled())
            raise ModelResultUncertain() from None
        _changed("Scenario model import", recorded=model_application._undo_enabled())
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
        """Apply one saved import unit to an explicitly captured mesh, never current selection.

        `asset_id` is the unit key classified from the verified record: a GLB,
        JSON glTF, FBX, or OBJ with its MTL and maps. Every member is rehashed into
        a private snapshot before the claim, so a changed or unsupported result
        raises ModelPreflightError with the saved job and the scene unchanged. The
        claim names every member read, unit key first.

        `target` may be a tuple of captured sources edited together; the claim's
        destination is then their scene, and the job's mesh source lists them.
        """
        _main_thread()
        if self._issued.get(id(completion)) is not completion:
            raise OriginUnavailable("Use an unconsumed mesh verification from this session")
        if completion.error is not None:
            raise completion.error
        verified = completion.result
        if not isinstance(verified, VerifiedResults) or not isinstance(destination, JobOrigin):
            raise OriginUnavailable("Verify the mesh and approve its captured destination")
        scene, obj = self._resolve(destination)
        # Several captured sources bind their scene; one source binds its object.
        if isinstance(target, tuple):
            if obj is not None or any(item.scene != scene for item in target):
                raise OriginUnavailable("Use the exact captured mesh targets")
        elif target.scene != scene or target.obj != obj:
            raise OriginUnavailable("Use the exact captured mesh target")
        validate_mesh_request(
            target, policy=policy, result_to_source=result_to_source, keep_original=keep_original
        )
        try:
            unit = import_plan(verified.record).unit(asset_id)
        except ValueError:
            unit = None
        if unit is None or not mesh_result_application.applicable(unit):
            raise OriginUnavailable("Select one saved GLB, glTF, FBX or OBJ mesh result")
        files = {
            item.asset.asset_id: (item, path)
            for item, path in zip(verified.record.results, verified.paths, strict=True)
        }
        del self._issued[id(completion)]
        snapshot = prepare_saved_mesh(
            target,
            unit,
            files,
            policy=policy,
            result_to_source=result_to_source,
            keep_original=keep_original,
        )
        try:
            claim = self._claim_saved_application(
                verified, destination, "mesh_edit", snapshot.members
            )
            return self._finish_mesh(
                claim,
                lambda: apply_saved_mesh(
                    target,
                    snapshot,
                    policy=policy,
                    result_to_source=result_to_source,
                    keep_original=keep_original,
                ),
            )
        finally:
            snapshot.cleanup()

    def _finish_mesh(self, claim, run):
        """Run one claimed mesh edit; failures keep receipt-only recovery."""
        try:
            application = run()
        except MeshResultApplicationError:
            try:
                self._coordinator.fail_application(claim)
            except Exception:
                raise ModelResultUncertain() from None
            raise
        except Exception:
            # Its checkpoint before replacing already marked the file.
            _changed("Scenario mesh edit", recorded=mesh_result_application._undo_enabled())
            raise ModelResultUncertain() from None
        _changed("Scenario mesh edit", recorded=application.undo_available)
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
            _changed("Scenario material")
            raise MaterialResultUncertain() from None
        _changed("Scenario material")
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

        def unchanged():
            try:
                return (
                    scene in tuple(bpy.data.scenes)
                    and scene.world == previous
                    and set(bpy.data.worlds) == worlds
                    and set(bpy.data.images) == images
                )
            except Exception:
                return False

        try:
            application = apply_world(
                scene, path, expected_receipt=item.receipt, media_type=item.asset.media_type
            )
        except (WorldApplicationError, PanoramaError):
            if not unchanged():
                _changed("Scenario World")
                raise WorldResultUncertain() from None
            try:
                self._coordinator.fail_application(claim)
            except Exception:
                raise WorldResultUncertain() from None
            raise
        except Exception:
            if not unchanged():
                _changed("Scenario World")
            raise WorldResultUncertain() from None
        _changed("Scenario World")
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
                self._origins.remove(scene_id)
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

    @contextmanager
    def synchronizing(self, scenes):
        """Keep every origin of these scenes while the caller evaluates their own view layers.

        A window evaluates only the scenes it shows. Any other scene keeps pending
        depsgraph tags, such as the relations rebuild that removing any datablock
        requests, until something updates it explicitly, and that update reports a
        change even when the scene's data is unchanged. Such tags cannot be told
        apart from an edit made without showing the scene, so callers recheck the
        content they approved instead.

        Inside the block, main-thread dependency and frame updates to a named scene
        revoke none of that scene's origins. Origins share one revision per scene
        (``OriginRevisions``), so this keeps every origin captured in it, including
        origins other features captured, not only the caller's. Other scenes,
        updates outside the block, deleted scenes and targets, render-thread
        callbacks, Undo/Redo and file loading still revoke origins.
        """
        _main_thread()
        previous = self._synchronizing
        self._synchronizing = (*previous, *scenes)
        try:
            yield
        finally:
            self._synchronizing = previous

    def invalidate_scene(self, scene):
        _main_thread()
        if any(item is scene for item in self._synchronizing):
            return
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
        if self._previews is not None:
            self._previews.close()
        self._exports.deactivate()
        self._workers.deactivate()
        # Session-local reviews end with their connection, including on file load.
        self.asset_organization.close()

    def shutdown(self):
        _main_thread()
        self.deactivate()
        try:
            # Wait a bounded time for the cancelled export before the coordinator
            # closes; a thread blocked on file access keeps this session owned.
            self._exports.shutdown()
            self._workers.shutdown()
        finally:
            # A failed SDK close occurs after joining. Release local ownership
            # then, but retain it if a control exception interrupted live workers.
            if self._workers.stopped and self._exports.stopped:
                if self._previews is not None:
                    self._previews.release()
                for task in tuple(self._upload_captures):
                    self._cleanup_upload_capture(task)
                self._pending.clear()
                self._cloud_reads.clear()
                self._workflow_reads.clear()
                self._asset_reads.clear()
                self._organization_tasks.clear()
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
                self.film_review.close()
                # The export thread has stopped, so its private staging can be removed.
                self.film_export.close()
                self.film_case_study.close()
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
            session.service_previews()
            if (
                not session._active
                and time.monotonic() >= session._film_cleanup_retry_at
                and all(task.done() for task, _ in session._pending)
                # A preview SDK read or transfer can outlast its cancellation;
                # never let shutdown join it on Blender's main thread.
                and session._workers.previews_idle
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
    # Rendering changes no scene's identity, so destination-only origins remain.
    if threading.current_thread() is not threading.main_thread():
        for session in _session_snapshot():
            session._origins.reset(keep_destinations=True)
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
