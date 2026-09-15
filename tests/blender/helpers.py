# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Helpers for tests that run inside `blender --background`."""

import importlib
import pathlib
import sys
import tempfile
from contextlib import contextmanager
from unittest.mock import patch

import bpy

ROOT = pathlib.Path(__file__).resolve().parents[2]
FIXTURES = ROOT / "tests" / "fixtures"


_PACKAGE = None
_INSTALLED = None


def configure(package, installed, profile):
    global _PACKAGE, _INSTALLED
    _PACKAGE, _INSTALLED = package, installed
    prefs = bpy.context.preferences.addons[package].preferences
    prefs.output_dir = str(profile / "output")
    prefs.api_key = prefs.api_secret = ""


def addon_name():
    if _PACKAGE is None:
        raise RuntimeError("Installed package not verified: use make test-blender")
    return _PACKAGE


def addon():
    return importlib.import_module(addon_name())


def submodule(path):
    module = importlib.import_module(f"{addon_name()}.{path}")
    if not pathlib.Path(module.__file__).resolve().is_relative_to(_INSTALLED):
        raise RuntimeError("Submodule is outside the verified installed package")
    return module


def reset_scene():
    bpy.ops.wm.read_homefile(use_empty=True)


@contextmanager
def temp_credentials(key="fixture-key", secret="fixture-secret"):
    """Restore the exact incoming preference values, including on setup failure."""
    prefs = bpy.context.preferences.addons[addon_name()].preferences
    saved = prefs.api_key, prefs.api_secret
    try:
        prefs.api_key, prefs.api_secret = key, secret
        yield prefs
    finally:
        prefs.api_key, prefs.api_secret = saved


@contextmanager
def online_access(enabled):
    """Opt into a real Blender preference branch without leaving it enabled."""
    system = bpy.context.preferences.system
    saved = system.use_online_access
    try:
        system.use_online_access = enabled
        if bool(bpy.app.online_access) != enabled:
            raise RuntimeError("Blender command-line override prevents online-access testing")
        yield
    finally:
        system.use_online_access = saved


@contextmanager
def isolated_manager():
    """Use private job storage after state.reset(), restoring the previous manager.

    The runner starts offline, so tests must explicitly use online_access(True)
    for online branches and provide a synthetic service before starting workers.
    Keep runtime.paths patched too: ensure_manager refreshes an existing manager's
    paths and must never redirect the test back to the profile-wide registry.
    """
    runtime = submodule("blender.runtime")
    config = submodule("core.config")
    records = submodule("core.jobs.records")
    manager_module = submodule("core.jobs.manager")
    previous = runtime.state.manager
    with tempfile.TemporaryDirectory(prefix="scenario-test-jobs-") as directory:
        root = pathlib.Path(directory)
        paths = config.Paths(root / "state", root / "cache", root / "output")
        manager = manager_module.JobManager(
            runtime.make_client, records.JobRegistry(paths.registry_file).load(), paths
        )
        with patch.object(runtime, "paths", return_value=paths):
            runtime.state.manager = manager
            try:
                yield manager
            finally:
                manager.shutdown()
                manager.join(timeout=5)
                runtime.state.manager = previous
                if manager.has_active():
                    message = "Test job workers did not stop before storage cleanup"
                    original = sys.exception()
                    if original is None:
                        raise RuntimeError(message)
                    original.add_note(message)
