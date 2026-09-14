# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
import json
import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parents[2]

RELEASE_PLEASE = "release-please bumps blender_manifest.toml and scenario/__init__.py together (extra-files); do not bump by hand"


def test_manifest_package_and_changelog_agree_on_the_version():
    manifest = re.search(r'^version = "([^"]+)"', (ROOT / "scenario" / "blender_manifest.toml").read_text(), re.M).group(1)
    package = re.search(r'^__version__ = "([^"]+)"', (ROOT / "scenario" / "__init__.py").read_text(), re.M).group(1)
    changelog_head = re.search(r"^## \[?(\d+\.\d+\.\d+)\]?", (ROOT / "CHANGELOG.md").read_text(), re.M).group(1)
    assert manifest == package
    assert manifest == changelog_head, RELEASE_PLEASE


def test_release_please_manifest_holds_the_same_version():
    manifest = re.search(r'^version = "([^"]+)"', (ROOT / "scenario" / "blender_manifest.toml").read_text(), re.M).group(1)
    tracked = json.loads((ROOT / ".release-please-manifest.json").read_text())["."]
    assert tracked == manifest, RELEASE_PLEASE
