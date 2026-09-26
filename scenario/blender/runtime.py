# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Process-wide singletons shared by panels, operators and the pump (main thread only)."""

import logging
import os
import pathlib
import threading

import bpy

from .. import prefs as prefs_module
from ..core import config
from ..core.api.client import ScenarioClient
from ..core.api.errors import ScenarioError
from ..core.api.sdk_adapter import Credentials as SDKCredentials
from ..core.api.sdk_catalog import SDKCatalog
from ..core.jobs.manager import JobManager
from ..core.jobs.records import JobRegistry

log = logging.getLogger("scenario")
PACKAGE = __package__.rsplit(".", 1)[0]  # the extension package, e.g. bl_ext.user_default.scenario


class RuntimeState:
    def __init__(self):
        self.manager = None
        self.catalog = None
        self.estimates = {}  # Exact SDK responses for current UI previews, never spend approval.
        self.estimate_origins = {}  # Pending request key -> original scene and lane, main thread only.
        self.records = {}  # model_id -> ModelRecord (detailed)
        self.lane_models = {}  # lane -> list[ModelRecord]
        self.catalog_loaded = False
        self.catalog_loading = False
        self.catalog_error = ""
        self.catalog_credentials = None
        self.retired_catalogs = []
        self.account_label = ""
        self.last_message = ""
        self.message_at = 0.0
        self.enum_cache = {}  # key -> list of (id, name, desc) tuples kept alive for EnumProperty
        self.previews = None  # bpy.utils.previews collection, created lazily
        self.jobs_view = []  # JobRecord list shown in the panel (active + recent)
        self.history = []
        self.history_token = None
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


def make_client():
    creds = credentials()
    if not creds.valid:
        raise ScenarioError(0, "Complete the selected credential source in Scenario Preferences")
    return ScenarioClient(creds.key, creds.secret)


_MAIN_THREAD = threading.main_thread()


def on_main_thread():
    return threading.current_thread() is _MAIN_THREAD


def ensure_manager():
    p = paths()
    if state.manager is None:
        registry = JobRegistry(p.registry_file).load()
        state.manager = JobManager(make_client, registry, p)
        if online():
            state.manager.resume()
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
            state.catalog = SDKCatalog(SDKCredentials(creds.key, creds.secret), online=online())
        except ValueError:
            raise ScenarioError(
                0, "The selected credentials are not a valid API key and secret"
            ) from None
        state.catalog_credentials = creds
    return state.catalog


def sync_catalog_context():
    """Refresh the worker-safe permission snapshot and retire changed credentials."""
    if not on_main_thread():
        raise RuntimeError("Catalog context must be refreshed on Blender's main thread")
    if state.catalog is not None:
        if state.catalog_credentials != credentials():
            from . import generation

            state.catalog.close()
            state.retired_catalogs.append(state.catalog)
            state.catalog = None
            state.catalog_credentials = None
            generation.clear_catalog()
        else:
            state.catalog.update_online(online())
    state.retired_catalogs[:] = [
        catalog for catalog in state.retired_catalogs if not catalog.closed
    ]


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
