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
from ..core.jobs.credential_storage import open_credential_store
from ..core.jobs.manager import JobManager
from ..core.jobs.records import JobRegistry
from ..core.jobs.store import StoreError
from ..core.jobs.transfers import ResultDownloader, StoragePolicy
from ..core.jobs.upload_sources import UploadSources
from ..core.jobs.upload_store import UploadStore
from ..core.jobs.upload_transfers import PartUploader, S3UploadPolicy
from .job_session import JobSession, reap_retired

log = logging.getLogger("scenario")
PACKAGE = __package__.rsplit(".", 1)[0]  # the extension package, e.g. bl_ext.user_default.scenario


class RuntimeState:
    def __init__(self):
        self.manager = None
        self.catalog = None
        self.job_store = None
        self.job_session = None
        self.job_context_id = None
        self.model_jobs = None
        self.workflow_controls = None
        self.library_view = None
        self.prompt_jobs = None
        self.blockout_jobs = None
        self.film_jobs = None
        self.reference_uploads = None
        self.model_previews = {}
        self.estimates = {}  # Exact SDK responses for current UI previews, never spend approval.
        self.estimate_origins = {}  # Pending request key -> original scene and lane, main thread only.
        self.records = {}  # model_id -> ModelRecord (detailed)
        self.model_errors = {}  # model_id -> sanitized lane error of its last failed detail read
        self.lane_models = {}  # lane -> list[ModelRecord]
        self.catalog_loaded = False
        self.catalog_loading = False
        self.catalog_error = ""
        self.catalog_error_selection = None
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
        self.history = []
        self.history_token = None
        self.history_request = None
        self.history_loading = False
        self.history_loaded = False
        self.history_error = ""
        self.history_cursors = set()
        self.history_saved_ids = None
        self.mcp = None
        self.mcp_token = ""
        self.mcp_error = ""
        self.cli_handle = None
        self.composer = None
        self.composer_modal_running = False

    SESSION_ATTRS = (
        "mcp",
        "mcp_token",
        "mcp_error",
        "cli_handle",
        "composer",
        "composer_modal_running",
        "previews",
    )

    def reset(self):
        """Forget catalog, jobs and history; keep process-level services (MCP server, composer, previews)."""
        self.retire_jobs()
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
        if self.job_session is not None:
            self.job_session.deactivate()
            self.job_session = None
        self.job_context_id = None
        if self.model_jobs is not None:
            views = tuple(self.model_jobs.views.values())
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
        self.model_previews.clear()


state = RuntimeState()


def prefs():
    return prefs_module.get_prefs()


def online():
    return bool(getattr(bpy.app, "online_access", True))


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
            session = JobSession(
                adapter,
                state.job_store,
                result_downloader=ResultDownloader(policy, online_access=catalog.network_allowed),
                result_root=root,
                upload_store=UploadStore(upload_root / "uploads.sqlite3", state.job_store.scope),
                upload_sources=UploadSources(source_root),
                part_uploader=PartUploader(S3UploadPolicy(), online_access=catalog.network_allowed),
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
        state.model_jobs = ModelJobs(session, state.job_store, online=online)
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


def control_model_job(context_id, request_id, expected_revision, action):
    jobs = ensure_model_jobs()
    if context_id != state.job_context_id:
        raise ScenarioError(0, "The selected job context changed; list local jobs again")
    task = jobs.control(request_id, expected_revision, action)
    view = jobs.views[request_id]
    show_job_views((view,))
    return jobs, task


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


def prepare_model_application(context_id, request_id, expected_revision, scene, asset_id):
    jobs = ensure_model_jobs()
    if context_id != state.job_context_id:
        raise ScenarioError(0, "The selected job context changed; list local jobs again")
    return jobs, jobs.prepare_model_application(request_id, expected_revision, scene, asset_id)


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


def prepare_asset_application(context_id, request_id, expected_revision, scene, asset_id):
    jobs = ensure_model_jobs()
    if context_id != state.job_context_id:
        raise ScenarioError(0, "The selected job context changed; list local jobs again")
    return jobs, jobs.prepare_asset_application(request_id, expected_revision, scene, asset_id)


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
            state.catalog.close()
            state.retired_catalogs.append(state.catalog)
            state.catalog = None
            state.job_store = None
            state.catalog_credentials = None
            state.catalog_project_id = None
            state.history = []
            state.history_token = None
            state.history_request = None
            state.history_loading = False
            state.history_loaded = False
            state.history_error = ""
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
    if state.library_view is not None:
        state.library_view.poll()
    if state.workflow_controls is not None:
        state.workflow_controls.poll()
    if state.job_session is not None:
        state.job_session.film_shots.poll()
        state.job_session.film_capture.poll()
        state.job_session.film_review.poll()
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
