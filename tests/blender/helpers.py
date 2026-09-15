# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Helpers for tests that run inside `blender --background`."""

import importlib
import pathlib

import bpy

ROOT = pathlib.Path(__file__).resolve().parents[2]
FIXTURES = ROOT / "tests" / "fixtures"


_PACKAGE = None
_INSTALLED = None
_PROFILE = None


def configure(package, installed, profile):
    global _PACKAGE, _INSTALLED, _PROFILE
    _PACKAGE, _INSTALLED, _PROFILE = package, installed, profile
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
