# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Process-wide singletons shared by panels, operators and the pump (main thread only)."""

import logging
import os
import pathlib
import threading
import uuid

import bpy

from .. import prefs as prefs_module
from ..core import config
from ..core.api.errors import ScenarioError
from ..core.api.sdk_adapter import Credentials as SDKCredentials
from ..core.api.sdk_catalog import SDKCatalog
from ..core.jobs.audio_decode import WaveformSpec
from ..core.jobs.audio_player import PlayerSpec
from ..core.jobs.credential_storage import open_credential_store
from ..core.jobs.manager import JobManager
from ..core.jobs.model_defaults import ModelDefaults
from ..core.jobs.records import JobRegistry
from ..core.jobs.session_spend import SessionSpend
from ..core.jobs.store import StoreError
from ..core.jobs.transfers import ResultDownloader, StoragePolicy
from ..core.jobs.upload_sources import UploadSources
from ..core.jobs.upload_store import UploadStore
from ..core.jobs.upload_transfers import PartUploader, S3UploadPolicy
from ..core.ui.costs import session_spend_label as session_spend_text
from ..mcp.upload_policy import ChosenFiles
from .job_session import JobSession, OriginUnavailable, reap_retired

log = logging.getLogger("scenario")
PACKAGE = __package__.rsplit(".", 1)[0]  # the extension package, e.g. bl_ext.user_default.scenario


class RuntimeState:
    def __init__(self):
        self.manager = None
        self.catalog = None
        self.job_store = None
        self.model_defaults = None  # Explicit lane defaults of job_store's scope.
        self.job_session = None
        # Accepted jobs' quotes for the selected connection; kept across file loads.
        self.session_spend = None
        self.job_context_id = None
        self.model_jobs = None
        self.workflow_controls = None
        self.library_view = None
        self.prompt_jobs = None
        self.blockout_jobs = None
        self.film_jobs = None
        self.reference_uploads = None
        # Icons of waiting workflow steps' review assets; per job context.
        self.review_previews = None
        self.model_previews = {}
        self.estimates = {}  # Exact SDK responses for current UI previews, never spend approval.
        # (scene session_uid, lane) -> generation.Repeat after Generate; see generation.repeat_*.
        self.repeats = {}
        # (scene session_uid, lane) -> generation.Reprice while a revoked price is requested again.
        self.reprices = {}
        # (scene session_uid, lane) -> (estimate key, asset ID) of a failed price whose
        # captured meshes conflict; see generation.capture_conflict.
        self.capture_conflicts = {}
        # (scene session_uid, lane) -> generation.FreshUpload while a just-attached
        # upload's price may still be refused; see generation.retry_fresh_upload.
        self.fresh_uploads = {}
        self.estimate_origins = {}  # Pending request key -> original scene and lane, main thread only.
        self.records = {}  # model_id -> ModelRecord (detailed)
        self.model_errors = {}  # model_id -> sanitized lane error of its last failed detail read
        self.lane_models = {}  # lane -> list[ModelRecord]
        self.catalog_loaded = False
        self.catalog_loading = False
        self.catalog_error = ""
        self.catalog_error_selection = None
        # Trained LoRAs and compositions of the selected connection (#97), main thread only.
        self.trained_pairs = []  # (kind, ModelRecord): private trained list, then public
        self.trained_records = {}  # model_id -> ModelRecord of trained_pairs
        self.trained_private = set()  # IDs the private list returned
        self.trained_loading = False
        self.trained_loaded = False
        self.trained_error = ""
        self.trained_scans = {}  # lane -> progress of its lazy base-description reads
        # Saved lane defaults read through model_defaults for drawing (trained_defaults.Cache).
        self.trained_defaults = None
        self.catalog_credentials = None
        self.catalog_project_id = None
        self.retired_catalogs = []
        self.account_label = ""
        self.connection_request = None
        self.connection_worker = None
        self.connection_status = ""
        self.last_message = ""
        self.message_at = 0.0
        self.enum_cache = {}  # key -> list of (id, name, desc) tuples kept alive for EnumProperty
        self.previews = None  # bpy.utils.previews collection, created lazily
        self.jobs_view = []  # JobRecord list shown in the panel (active + recent)
        # Prompts and model names of this connection's saved jobs shown this session,
        # by request ID; kept across file loads so inspected jobs show them again.
        self.job_labels = {}
        # (credentials, project, job context) whose saved jobs show_saved_jobs listed.
        self.saved_jobs_listed = None
        self.history = []
        self.history_token = None
        self.history_request = None
        self.history_loading = False
        self.history_loaded = False
        self.history_error = ""
        self.history_older_error = ""
        self.history_cursors = set()
        self.history_saved_ids = None
        self.mcp = None
        self.mcp_error = ""
        # Online access the window session's server last followed; None until it starts
        # with the extension, so background Blender starts only its explicit command.
        self.mcp_online = None
        self.mcp_stopped_by_user = False  # Stop MCP server: online access changes keep it off.
        # Files the user chose in the extension's file fields this session; local MCP may
        # upload them (reference_uploads.agent_upload_path). Main thread only.
        self.chosen_files = ChosenFiles()
        self.cli_handle = None
        self.composer = None
        self.composer_modal_running = False

    SESSION_ATTRS = (
        "mcp",
        "mcp_error",
        "mcp_online",
        "mcp_stopped_by_user",
        "cli_handle",
        "composer",
        "composer_modal_running",
        "previews",
    )

    def reset(self):
        """Forget catalog, jobs and history; keep process-level services (MCP server, composer, previews)."""
        self.retire_jobs()
        self.retire_model_defaults()
        for catalog in [self.catalog, *self.retired_catalogs]:
            if catalog is not None:
                catalog.close()
        if self is state:
            from . import generation

            generation.clear_catalog()
        kept = {name: getattr(self, name) for name in self.SESSION_ATTRS}
        self.__init__()
        for name, value in kept.items():
            setattr(self, name, value)
        reap_retired()

    def retire_jobs(self):
        """Stop admissions; the session registry retains in-flight persistence."""
        from . import result_media, result_previews

        # Saved-media copies, waveforms and preview icons belong to the retiring
        # connection; their cleanup must never keep the session from retiring.
        try:
            result_media.controller.retire()
        except Exception:
            log.warning("Saved media cleanup failed")
        try:
            result_previews.controller.retire()
        except Exception:
            log.warning("Result preview cleanup failed")
        if self.job_session is not None:
            self.job_session.deactivate()
            self.job_session = None
        self.job_context_id = None
        if self.model_jobs is not None:
            from .model_jobs import labels

            views = tuple(self.model_jobs.views.values())
            self.job_labels.update(labels(views))
            self.jobs_view[:] = [
                view for view in self.jobs_view if all(view is not v for v in views)
            ]
        self.model_jobs = None
        self.workflow_controls = None
        self.library_view = None
        self.prompt_jobs = None
        self.blockout_jobs = None
        self.film_jobs = None
        self.reference_uploads = None
        if self.review_previews is not None:
            self.review_previews.clear()
        self.review_previews = None
        self.model_previews.clear()

    def retire_model_defaults(self):
        """Stop the old scope's defaults owner; saved rows stay in their own scope."""
        if self.model_defaults is not None:
            self.model_defaults.retire()
            self.model_defaults = None


state = RuntimeState()


def prefs():
    return prefs_module.get_prefs()


# The panel line and button shown while Blender's network preference is off.
ONLINE_ACCESS_NEEDED = "Scenario needs Blender's Allow Online Access"
STARTED_OFFLINE = "Blender started in offline mode (--offline-mode); restart it without that option"


def online():
    return bool(getattr(bpy.app, "online_access", True))


def started_offline():
    """Whether Blender's --offline-mode holds Allow Online Access off until a restart.

    Blender then refuses to change the preference, so no button can turn it on.
    """
    return bool(getattr(bpy.app, "online_access_override", False)) and not online()


def waveform_spec():
    """The owned offline audio decoder, resolved on the main thread; None without one.

    Blender run as a Python module, or a package without a usable executable
    path, cannot start the decoder: audio envelopes then fail explicitly.
    """
    binary = bpy.app.binary_path
    if not binary:
        return None
    try:
        executable = pathlib.Path(binary).resolve()
        worker = pathlib.Path(__file__).with_name("waveform_worker.py").resolve()
        if not executable.is_file() or not worker.is_file():
            return None
        return WaveformSpec(executable, worker)
    except (OSError, ValueError):
        return None


def audio_device():
    """The audio output chosen in Preferences > System > Sound, such as CoreAudio, or ''."""
    try:
        return str(bpy.context.preferences.system.audio_device)
    except (AttributeError, TypeError):
        return ""


def audio_player_spec(device):
    """The owned offline audio player for ``device``, resolved on the main thread; None without one.

    Like the waveform decoder, it needs Blender's executable and the bundled worker.
    """
    binary = bpy.app.binary_path
    if not binary:
        return None
    try:
        executable = pathlib.Path(binary).resolve()
        worker = pathlib.Path(__file__).with_name("audio_player_worker.py").resolve()
        if not executable.is_file() or not worker.is_file():
            return None
        return PlayerSpec(executable, worker, device)
    except (OSError, ValueError):
        return None


def paths():
    state_dir = pathlib.Path(bpy.utils.extension_path_user(PACKAGE, path="state", create=True))
    cache_dir = pathlib.Path(bpy.utils.extension_path_user(PACKAGE, path="cache", create=True))
    p = prefs()
    raw_out = p.output_dir if p and p.output_dir else "~/Downloads/Scenario"
    output_dir = pathlib.Path(os.path.expanduser(bpy.path.abspath(raw_out)))
    return config.Paths(state_dir=state_dir, cache_dir=cache_dir, output_dir=output_dir)


def credentials():
    p = prefs()
    return config.resolve_credentials(
        p.api_key if p else "",
        p.api_secret if p else "",
        source=p.credential_source if p else "PREFERENCES",
    )


def project_id():
    """Read the explicit optional override; never infer a key's server project."""
    p = prefs()
    return (getattr(p, "project_id", "") or "").strip() or None


def catalog_selection_matches():
    """Read-only check for drawing and admission; no discovery or storage access."""
    return state.catalog_credentials == credentials() and state.catalog_project_id == project_id()


_MAIN_THREAD = threading.main_thread()


def on_main_thread():
    return threading.current_thread() is _MAIN_THREAD


def ensure_manager():
    p = paths()
    if state.manager is None:
        registry = JobRegistry(p.registry_file).load()
        state.manager = JobManager(registry, p)
    else:
        state.manager.paths = p  # the output folder preference may have changed
    return state.manager


def ensure_catalog():
    sync_catalog_context()
    creds = credentials()
    if state.catalog is None:
        if not creds.valid:
            raise ScenarioError(
                0, "Complete the selected credential source in Scenario Preferences"
            )
        try:
            selected = SDKCredentials(creds.key, creds.secret)
            selected.authorization()
        except ValueError:
            raise ScenarioError(
                0, "The selected credentials are not a valid API key and secret"
            ) from None
        try:
            store = open_credential_store(
                paths().state_dir / "shared-jobs", selected, project_id=project_id()
            )
        except StoreError as error:
            raise ScenarioError(0, str(error)) from None
        except ValueError:
            raise ScenarioError(
                0,
                "Project ID must be an opaque ID, not a URL or whitespace; clear it for key scope",
            ) from None
        state.catalog = SDKCatalog(selected, online=online(), scope=store.scope)
        state.job_store = store
        state.catalog_credentials = creds
        state.catalog_project_id = store.scope.project_id
    return state.catalog


def ensure_job_store():
    """Select local durable jobs through the same context used by UI and MCP reads."""
    ensure_catalog()
    return state.job_store


def ensure_model_defaults():
    """Select explicit lane defaults for the selected credentials and project override.

    The scope comes from the selected job store, never from discovery or a guessed
    server project. No network or job session is needed; a credential or project
    change retires this owner in sync_catalog_context.
    """
    store = ensure_job_store()
    owner = state.model_defaults
    if owner is None or not owner.active or owner.scope != store.scope:
        state.retire_model_defaults()
        state.model_defaults = ModelDefaults(store)
    return state.model_defaults


def _current_model_defaults(context_id):
    owner = ensure_model_defaults()
    if context_id != owner.context_id:
        raise ScenarioError(
            0, "The selected credentials or project changed; review the default again"
        )
    return owner


def save_model_default(context_id, default, *, expected_revision):
    """Save an explicit lane default only in the context where the user reviewed it."""
    return _current_model_defaults(context_id).save(default, expected_revision=expected_revision)


def clear_model_default(context_id, lane, *, expected_revision):
    """Clear a lane default only in the context where the user reviewed it."""
    return _current_model_defaults(context_id).clear(lane, expected_revision=expected_revision)


def session_spend(scope):
    """The connection's running spend: kept across file loads, started over for another scope."""
    spend = state.session_spend
    if spend is None or spend.scope != scope:
        spend = state.session_spend = SessionSpend(scope)
    return spend


def session_spend_label():
    """The Jobs panel's "This session" line, or "" (reads memory only, safe in draw)."""
    spend = state.session_spend
    return "" if spend is None else session_spend_text(*spend.snapshot())


def ensure_job_session():
    """Select one application-owned job session, independent of open panels."""
    catalog = ensure_catalog()
    if state.job_session is None:
        adapter = catalog.create_job_adapter()
        try:
            # Exact hosts documented by Scenario's CDN and asset-retrieval guides.
            # Never derive this allowlist from a service response or signed URL.
            policy = StoragePolicy(frozenset({"cdn.cloud.scenario.com", "cdn.scenario.com"}))
            root = paths().state_dir / "shared-results"
            root.mkdir(mode=0o700, parents=True, exist_ok=True)
            upload_root = paths().state_dir / "shared-uploads"
            upload_root.mkdir(mode=0o700, parents=True, exist_ok=True)
            source_root = upload_root / "sources"
            source_root.mkdir(mode=0o700, exist_ok=True)
            # Disposable receipt-bound previews; the cache is safe to delete.
            # Jobs never depend on it: without a usable root, previews are off.
            preview_root = paths().cache_dir / "result-previews"
            try:
                preview_root.mkdir(mode=0o700, parents=True, exist_ok=True)
            except OSError:
                preview_root = None
            session = JobSession(
                adapter,
                state.job_store,
                result_downloader=ResultDownloader(policy, online_access=catalog.network_allowed),
                result_root=root,
                upload_store=UploadStore(upload_root / "uploads.sqlite3", state.job_store.scope),
                upload_sources=UploadSources(source_root),
                part_uploader=PartUploader(S3UploadPolicy(), online_access=catalog.network_allowed),
                preview_root=preview_root,
                preview_waveform=waveform_spec(),
                spend=session_spend(state.job_store.scope),
            )
        except BaseException:
            adapter.close()
            raise
        state.job_session = session
        state.job_context_id = uuid.uuid4().hex
    return state.job_session


def local_job_recovery():
    """Inspect only this credential context's durable jobs; never replay work."""
    session = ensure_job_session()
    return state.job_context_id, session.recovery_plan()


def ensure_model_jobs():
    from .model_jobs import ModelJobs

    session = ensure_job_session()
    if state.model_jobs is None:
        state.model_jobs = ModelJobs(
            session, state.job_store, online=online, labels=state.job_labels
        )
    return state.model_jobs


def ensure_film_jobs():
    from .film_jobs import FilmJobs

    models = ensure_model_jobs()
    if state.film_jobs is None:
        state.film_jobs = FilmJobs(models, online=online)
    return state.film_jobs


def ensure_prompt_jobs():
    from .prompt_jobs import PromptJobs

    session = ensure_job_session()
    if state.prompt_jobs is None:
        state.prompt_jobs = PromptJobs(session, state.job_store, online=online)
    return state.prompt_jobs


def ensure_blockout_jobs():
    from .blockout_jobs import BlockoutJobs

    session = ensure_job_session()
    if state.blockout_jobs is None:
        state.blockout_jobs = BlockoutJobs(session, state.job_store, online=online)
    return state.blockout_jobs


def blockout_recovery(context_id):
    jobs = ensure_blockout_jobs()
    if context_id != state.job_context_id:
        raise ScenarioError(0, "The saved-plan context changed; inspect saved jobs again")
    return jobs.recovery


def ensure_reference_uploads():
    from .reference_uploads import ReferenceUploads

    session = ensure_job_session()
    if state.reference_uploads is None:
        state.reference_uploads = ReferenceUploads(session, online=online)
    return state.reference_uploads


def cancel_prepared_job(context_id, request_id, expected_revision):
    """Shared native/MCP local cancellation of an unsent intent; it sends no request."""
    session = ensure_job_session()
    if context_id != state.job_context_id:
        raise ScenarioError(0, "The selected job context changed; list local jobs again")
    record = session.cancel_prepared(request_id, expected_revision=expected_revision)
    view = state.model_jobs.show_canceled(record) if state.model_jobs is not None else None
    if view is not None:
        show_job_views((view,))
    return record


def show_job_views(records):
    """Merge display rows stably; the prototype limit never evicts scoped jobs."""
    records = tuple(records)
    order = list(dict.fromkeys(row.local_id for row in state.jobs_view))
    existing = set(order)
    added = list(dict.fromkeys(row.local_id for row in records if row.local_id not in existing))
    rows = {}
    for row in (*state.jobs_view, *records):
        previous = rows.get(row.local_id)
        if previous is None or row.meta.get("shared_job") or not previous.meta.get("shared_job"):
            rows[row.local_id] = row
    visible = []
    prototype_count = 0
    for identifier in (*reversed(added), *order):
        row = rows[identifier]
        if not row.meta.get("shared_job"):
            prototype_count += 1
            if prototype_count > 50:
                continue
        visible.append(row)
    state.jobs_view[:] = visible


def inspect_model_jobs():
    jobs = ensure_model_jobs()
    show_job_views(jobs.inspect())
    return jobs


def show_saved_jobs():
    """List the selected connection's saved jobs once per job context (GUI pump).

    The read Inspect saved jobs makes: saved jobs show paused for review, never
    resumed, applied or submitted again. Starting Blender, opening a file or
    changing credentials leaves no listed context, so the Jobs list and the
    Results grid show them again without a click. The pump calls it after its
    context check this tick, which retires a session a file load deactivated.
    It lists only a connection the catalog step already selected, never
    selecting or switching one itself. Returns whether rows changed.
    """
    selection = (credentials(), project_id(), state.job_context_id)
    if (
        not selection[0].valid
        or state.catalog is None
        or not catalog_selection_matches()
        or selection == state.saved_jobs_listed
    ):
        return False
    state.saved_jobs_listed = selection  # one attempt per context, even when it fails
    try:
        store = ensure_job_store()
        if state.job_session is None and not store.records():
            return False  # nothing saved: no session is started for an empty list
        inspect_model_jobs()
    except Exception:
        log.warning("Could not list saved jobs; Inspect saved jobs reads them again")
        return False
    state.saved_jobs_listed = (credentials(), project_id(), state.job_context_id)
    return True


def control_model_job(context_id, request_id, expected_revision, action):
    jobs = ensure_model_jobs()
    if context_id != state.job_context_id:
        raise ScenarioError(0, "The selected job context changed; list local jobs again")
    task = jobs.control(request_id, expected_revision, action)
    view = jobs.views[request_id]
    show_job_views((view,))
    return jobs, task


def link_cloud_job(context_id, request_id, expected_revision, remote_job_id):
    """Native-only: queue the user's confirmed link of one listed cloud job."""
    jobs = ensure_model_jobs()
    if context_id != state.job_context_id:
        raise ScenarioError(0, "The selected job context changed; list local jobs again")
    task = jobs.link(request_id, expected_revision, remote_job_id)
    show_job_views((jobs.views[request_id],))
    return jobs, task


def read_workflow_steps(context_id, request_id):
    """Shared native/MCP entry that reads a saved workflow job's waiting steps again.

    Returns the owner and the retrieval task, or None when the job is no longer
    `remote` and has no waiting step to read.
    """
    jobs = ensure_model_jobs()
    if context_id != state.job_context_id:
        raise ScenarioError(0, "The selected job context changed; list local jobs again")
    task = jobs.read_steps(request_id)
    if request_id in jobs.views:
        show_job_views((jobs.views[request_id],))
    return jobs, task


def decide_workflow_step(
    context_id, request_id, expected_revision, node_id, review_id, action, selected_indices=None
):
    """Shared native/MCP entry for one reviewed waiting workflow-step decision."""
    jobs = ensure_model_jobs()
    if context_id != state.job_context_id:
        raise ScenarioError(0, "The selected job context changed; list local jobs again")
    task = jobs.decide(request_id, expected_revision, node_id, review_id, action, selected_indices)
    show_job_views((jobs.views[request_id],))
    return jobs, task


def load_review_previews(
    context_id, request_id, expected_revision, node_id, review_id, *, retry=False
):
    """Native entry that loads private previews of one waiting step's review assets.

    Bound like a decision to the context, saved revision and the step's
    `review_id`; previews are read-only and never decide, spend or apply.
    Returns the number of assets requested.
    """
    jobs = ensure_model_jobs()
    if context_id != state.job_context_id:
        raise ScenarioError(0, "The selected job context changed; list local jobs again")
    try:
        scheduler = ensure_job_session().result_previews
    except OriginUnavailable:
        raise ScenarioError(0, "Previews are unavailable for this connection") from None
    from .review_previews import ReviewPreviews

    if state.review_previews is None or state.review_previews.context_id != context_id:
        if state.review_previews is not None:
            state.review_previews.clear()
        state.review_previews = ReviewPreviews(context_id)
    return state.review_previews.request(
        jobs, scheduler, request_id, expected_revision, node_id, review_id, retry=retry
    )


def prepare_image_application(context_id, request_id, expected_revision, scene):
    jobs = ensure_model_jobs()
    if context_id != state.job_context_id:
        raise ScenarioError(0, "The selected job context changed; list local jobs again")
    return jobs, jobs.prepare_image_application(request_id, expected_revision, scene)


def prepare_media_application(context_id, request_id, expected_revision, scene, asset_id):
    jobs = ensure_model_jobs()
    if context_id != state.job_context_id:
        raise ScenarioError(0, "The selected job context changed; list local jobs again")
    return jobs, jobs.prepare_media_application(request_id, expected_revision, scene, asset_id)


def prepare_landing_application(
    context_id, request_id, expected_revision, scene, asset_id, **options
):
    """Review one saved result as a camera background or image plane (`purpose`)."""
    jobs = ensure_model_jobs()
    if context_id != state.job_context_id:
        raise ScenarioError(0, "The selected job context changed; list local jobs again")
    return jobs, jobs.prepare_landing_application(
        request_id, expected_revision, scene, asset_id, **options
    )


def revise_landing_application(context_id, application_id, **options):
    jobs = ensure_model_jobs()
    if context_id != state.job_context_id:
        raise ScenarioError(0, "The selected job context changed; review the result again")
    return jobs.revise_landing_application(application_id, **options)


def prepare_model_application(
    context_id, request_id, expected_revision, scene, asset_id, **options
):
    """Review one import unit; SPZ, PLY and .splat units take max_points and axes."""
    jobs = ensure_model_jobs()
    if context_id != state.job_context_id:
        raise ScenarioError(0, "The selected job context changed; list local jobs again")
    return jobs, jobs.prepare_model_application(
        request_id, expected_revision, scene, asset_id, **options
    )


def revise_model_application(context_id, application_id, **options):
    jobs = ensure_model_jobs()
    if context_id != state.job_context_id:
        raise ScenarioError(0, "The selected job context changed; review the import again")
    return jobs.revise_model_application(application_id, **options)


def prepare_mesh_application(
    context_id, request_id, expected_revision, scene, obj, asset_id, **options
):
    jobs = ensure_model_jobs()
    if context_id != state.job_context_id:
        raise ScenarioError(0, "Inspect the current connection's jobs before editing a mesh")
    return jobs, jobs.prepare_mesh_application(
        request_id, expected_revision, scene, obj, asset_id, **options
    )


def revise_mesh_application(context_id, application_id, **options):
    jobs = ensure_model_jobs()
    if context_id != state.job_context_id:
        raise ScenarioError(0, "The selected job context changed; review the mesh again")
    return jobs.revise_mesh_application(application_id, **options)


def prepare_material_application(context_id, request_id, expected_revision, scene, obj):
    jobs = ensure_model_jobs()
    if context_id != state.job_context_id:
        raise ScenarioError(0, "Inspect the current connection's jobs before applying a material")
    return jobs, jobs.prepare_material_application(request_id, expected_revision, scene, obj)


def prepare_world_application(
    context_id, request_id, expected_revision, scene, asset_id=None, *, restore=False
):
    jobs = ensure_model_jobs()
    if context_id != state.job_context_id:
        raise ScenarioError(0, "The selected job context changed; list local jobs again")
    return jobs, jobs.prepare_world_application(
        request_id, expected_revision, scene, asset_id, restore=restore
    )


def prepare_first_frame_application(context_id, request_id, expected_revision, scene, asset_id):
    jobs = ensure_model_jobs()
    if context_id != state.job_context_id:
        raise ScenarioError(0, "The selected job context changed; list local jobs again")
    return jobs, jobs.prepare_first_frame_application(
        request_id, expected_revision, scene, asset_id
    )


def prepare_asset_application(
    context_id, request_id, expected_revision, scene, asset_id, **options
):
    jobs = ensure_model_jobs()
    if context_id != state.job_context_id:
        raise ScenarioError(0, "The selected job context changed; list local jobs again")
    return jobs, jobs.prepare_asset_application(
        request_id, expected_revision, scene, asset_id, **options
    )


def apply_saved_result(context_id, application_id):
    jobs = ensure_model_jobs()
    if context_id != state.job_context_id:
        raise ScenarioError(0, "The selected job context changed; list local jobs again")
    request_id, task = jobs.apply_saved_result(application_id)
    view = jobs.views[request_id]
    show_job_views((view,))
    return jobs, request_id, task


def apply_saved_images(context_id, application_id):
    jobs = ensure_model_jobs()
    if context_id != state.job_context_id:
        raise ScenarioError(0, "The selected job context changed; review the import again")
    request_id, task = jobs.apply_saved_images(application_id)
    show_job_views(jobs.views.values())
    return jobs, request_id, task


def request_connection_check():
    """Queue a single model-access probe for the current selected credentials."""
    if not online():
        raise ScenarioError(0, "Allow Online Access is disabled in Blender's preferences")
    catalog = ensure_catalog()
    if state.connection_request is not None:
        return state.connection_worker
    manager = ensure_manager()
    key = object()
    state.connection_request = key
    state.account_label = "Checking Scenario connection..."
    state.connection_status = "pending"
    try:
        state.connection_worker = manager.check_connection(catalog, key)
    except Exception:
        state.connection_request = None
        state.connection_worker = None
        state.connection_status = ""
        state.account_label = ""
        raise ScenarioError(0, "Could not start the Scenario connection check") from None
    return state.connection_worker


def sync_catalog_context():
    """Refresh the worker-safe permission snapshot and retire changed credentials or project."""
    if not on_main_thread():
        raise RuntimeError("Catalog context must be refreshed on Blender's main thread")
    if state.catalog_error_selection is not None and state.catalog_error_selection != (
        credentials(),
        project_id(),
    ):
        state.catalog_error = ""
        state.catalog_error_selection = None
    if state.job_session is not None and not state.job_session.active:
        state.retire_jobs()
    if state.catalog is not None:
        if not catalog_selection_matches():
            from . import generation

            state.retire_jobs()
            state.retire_model_defaults()
            state.catalog.close()
            state.retired_catalogs.append(state.catalog)
            state.catalog = None
            state.job_store = None
            state.session_spend = None  # another account or project starts its own total
            state.job_labels = {}
            state.catalog_credentials = None
            state.catalog_project_id = None
            state.history = []
            state.history_token = None
            state.history_request = None
            state.history_loading = False
            state.history_loaded = False
            state.history_error = ""
            state.history_older_error = ""
            state.history_cursors.clear()
            state.history_saved_ids = None
            state.connection_request = None
            state.connection_worker = None
            state.connection_status = ""
            state.account_label = ""
            generation.clear_catalog()
        else:
            state.catalog.update_online(online())
    state.retired_catalogs[:] = [
        catalog for catalog in state.retired_catalogs if not catalog.closed
    ]
    reap_retired()

    from . import generation

    generation.process_model_jobs()
    if state.workflow_controls is not None:
        state.workflow_controls.poll()
    if state.job_session is not None:
        state.job_session.film_shots.poll()
        state.job_session.film_capture.poll()
        state.job_session.film_review.poll()
        state.job_session.film_export.poll()
        state.job_session.film_case_study.poll()
        state.job_session.asset_organization.poll()
    # After the shared owner, so a finished review reaches the Library card this tick.
    if state.library_view is not None:
        state.library_view.poll()
    if state.film_jobs is not None:
        state.film_jobs.poll()
    if state.prompt_jobs is not None:
        state.prompt_jobs.poll()
    if state.blockout_jobs is not None:
        state.blockout_jobs.poll()
    if state.reference_uploads is not None:
        state.reference_uploads.poll()


def enum_items(key):
    return state.enum_cache.get(key) or [("NONE", "Loading...", "Model list not loaded yet")]


def set_enum_items(key, items):
    state.enum_cache[key] = [tuple(item) for item in items] or [("NONE", "None available", "")]


MESSAGE_TTL = 8.0  # seconds a status line stays on screen; older ones read as if they were current


def set_message(text):
    import time

    state.last_message = text
    state.message_at = time.monotonic()
    log.info(text)


def message_visible(ttl=MESSAGE_TTL):
    """The last status line while it is fresh, else an empty string."""
    import time

    at = getattr(state, "message_at", 0.0)
    if not state.last_message or not at or time.monotonic() - at > ttl:
        return ""
    return state.last_message


def previews():
    import bpy.utils.previews

    if state.previews is None:
        state.previews = bpy.utils.previews.new()
    return state.previews


def shutdown():
    if state.manager:
        state.manager.shutdown()
    if state.mcp is not None:
        state.mcp.stop()
    if state.previews is not None:
        import bpy.utils.previews

        bpy.utils.previews.remove(state.previews)
    state.reset()
