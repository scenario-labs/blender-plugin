# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Manifest permission declarations and static source-use signals, not a sandbox."""

import ast
import pathlib
import tomllib

ROOT = pathlib.Path(__file__).resolve().parents[2]
PACKAGE = ROOT / "scenario"
MANIFEST = PACKAGE / "blender_manifest.toml"
KNOWN = {"files", "network", "clipboard", "camera", "microphone"}
NETWORK_MODULES = {
    "urllib.request",
    "http.client",
    "http.server",
    "socket",
    "socketserver",
    "httpx",
    "scenario_sdk",
}


def permissions():
    return tomllib.loads(MANIFEST.read_text(encoding="utf-8"))["permissions"]


def source_uses():
    clipboard, network = [], []
    for path in PACKAGE.rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if (
                isinstance(node, ast.Attribute)
                and node.attr == "clipboard"
                and isinstance(node.value, ast.Attribute)
                and node.value.attr == "window_manager"
            ):
                clipboard.append(str(path.relative_to(ROOT)))
            modules = []
            if isinstance(node, ast.Import):
                modules = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom) and not node.level:
                modules = [node.module or ""]
            if any(
                name == library or name.startswith(library + ".")
                for name in modules
                for library in NETWORK_MODULES
            ):
                network.append(str(path.relative_to(ROOT)))
    return {"clipboard": sorted(set(clipboard)), "network": sorted(set(network))}


def test_clipboard_permission_matches_code():
    uses = source_uses()["clipboard"]
    declared = "clipboard" in permissions()
    assert declared == bool(uses), f"Clipboard use: {uses}; declared={declared}"


def test_network_permission_matches_code():
    uses = source_uses()["network"]
    declared = "network" in permissions()
    assert declared == bool(uses), f"Network imports: {uses}; declared={declared}"


def test_permission_reasons_follow_manifest_rules():
    declared = permissions()
    assert declared
    for name, reason in declared.items():
        assert name in KNOWN
        assert isinstance(reason, str) and reason and reason == reason.strip()
        assert len(reason) <= 64 and "\n" not in reason and "\r" not in reason
        assert reason[-1] not in ".!?"


# The repository is live now; switch to the handbook only after Pages acceptance.
ALLOWED_WEBSITES = {
    "https://github.com/scenario-labs/blender-plugin",
    "https://scenario-labs.github.io/blender-plugin/",
}


def test_manifest_website_points_at_the_project():
    manifest = tomllib.loads(MANIFEST.read_text(encoding="utf-8"))
    assert manifest["website"] in ALLOWED_WEBSITES, manifest["website"]
