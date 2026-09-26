# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Disclosure drift checks; native tests establish actual preference persistence."""

import ast
import re
from pathlib import Path
from urllib.parse import urlsplit

from tools.build_docs_html import build_handbook

ROOT = Path(__file__).resolve().parents[2]


def test_literal_network_destinations_require_a_disclosure_review():
    hosts = set()
    for path in (ROOT / "scenario").rglob("*.py"):
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            if isinstance(node, ast.Constant) and isinstance(node.value, str):
                for url in re.findall(r"https?://[A-Za-z0-9.:-]+", node.value):
                    hosts.add(urlsplit(url).hostname)
    assert hosts <= {
        "api.cloud.scenario.com",
        "app.scenario.com",
        "127.0.0.1",
        "blender.scenario.com",
        "github.com",
    }, hosts
    note = (ROOT / "docs/PRIVACY.md").read_text()
    assert all(host in note for host in hosts)
    # Dynamic content destinations cannot be established by literal-source scanning.
    assert "content URLs returned by the" in note


def test_privacy_entry_points_and_critical_storage_disclosures():
    note = (ROOT / "docs/PRIVACY.md").read_text()
    assert re.findall(r"^## (.*)$", note, re.M) == [
        "What leaves your machine, and when",
        "Where it goes",
        "What is stored on your machine",
        "The local MCP server",
        "Terms",
    ]
    for text in (
        "userpref.blend",
        "SCENARIO_API_KEY",
        "SCENARIO_API_SECRET",
        "jobs.json",
        "telemetry",
        "terms-and-conditions",
        "privacy-policy",
        "before you press",
        "Clipboard",
        "not an instantaneous network cutoff",
    ):
        assert text in note, text
    assert "Pro plan" not in note
    assert not re.search(r"20[0-9]{2}-[0-9]{2}-[0-9]{2}| CU\b", note)
    for path, link in (("README.md", "docs/PRIVACY.md"), ("docs/USER_GUIDE.md", "PRIVACY.md")):
        text = (ROOT / path).read_text()
        assert text.count(link) == 1
        assert text.count("## What leaves your machine") == 1
        assert "removed when the extension is uninstalled" not in text
    prefs = (ROOT / "scenario/prefs.py").read_text()
    assert "Saved as plain text in userpref.blend" in prefs
    assert "Select Environment to use SCENARIO_API_KEY + SCENARIO_API_SECRET" in prefs


def test_standalone_guide_preserves_disclosures(tmp_path):
    output = build_handbook(
        ROOT / "docs/USER_GUIDE.md",
        ROOT / "docs/handbook-template.html",
        ROOT / "scenario/blender_manifest.toml",
        tmp_path / "handbook.html",
        inline_images=True,
    )
    text = output.read_text()
    assert "What leaves your machine" in text
    assert "PRIVACY.md" in text
    assert "userpref.blend" in text
    assert "removed with the extension" not in text
