# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Keep the user guide aligned with registered lanes and the Markdown renderer."""

import ast
import re
import tomllib
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
GUIDE = ROOT / "docs/USER_GUIDE.md"
TEMPLATE = ROOT / "docs/handbook-template.html"
STALE = re.compile(
    r"\b(?:\d+|fifteen|sixteen|seventeen|eighteen|nineteen|twenty)\s+tools\b"
    r"|\bPro plan\b|\btested on\b|\bVersion \d+\.\d+|\bv\d+\.\d+\.\d+\b"
    r"|scenario-mcp|Team > API Keys|build\.sh|SCENARIO_GUI_PROBE"
    r"|one collapsible|the pencil opens|August 2026|BUGS\.md",
    re.IGNORECASE,
)


def test_each_registered_creation_lane_has_a_guide_section():
    tree = ast.parse((ROOT / "scenario/blender/props.py").read_text())
    assignment = next(
        node
        for node in tree.body
        if isinstance(node, ast.Assign)
        and any(
            isinstance(target, ast.Name) and target.id == "LANE_ITEMS" for target in node.targets
        )
    )
    labels = {row[1] for row in ast.literal_eval(assignment.value)}
    headings = set(re.findall(r"^### (.+)$", GUIDE.read_text(), re.MULTILINE))
    assert labels <= headings, f"Missing lane sections: {sorted(labels - headings)}"


def test_guide_minimum_tracks_the_extension_manifest():
    manifest = tomllib.loads((ROOT / "scenario/blender_manifest.toml").read_text())
    minimum = manifest["blender_version_min"]
    if minimum.endswith(".0"):
        minimum = minimum.rsplit(".", 1)[0]
    assert f"Blender {minimum} or later" in GUIDE.read_text()


@pytest.mark.parametrize("document", [GUIDE, TEMPLATE], ids=["guide", "template"])
def test_public_guide_avoids_retired_or_unverified_claims(document):
    assert not STALE.search(document.read_text())


@pytest.mark.parametrize(
    "text",
    ["16 tools", "nineteen tools", "Pro plan", "tested on", "v0.9.9", "Team > API Keys"],
)
def test_stale_claim_guard_rejects_regressions(text):
    assert STALE.search(text)


def test_every_guide_illustration_exists():
    images = re.findall(r"!\[[^\]]*\]\((images/[^)]+)\)", GUIDE.read_text())
    assert images
    for image in images:
        assert (GUIDE.parent / image).is_file(), image


def test_handbook_has_one_generated_body_and_navigation():
    template = TEMPLATE.read_text()
    assert template.count("{{content}}") == 1
    assert template.count("{{toc}}") == 1
    assert template.count("{{version}}") == 2
    assert not re.search(r"<h2\b|<section\b|\{\{img:", template, re.IGNORECASE)
    assert not (ROOT / "docs/user-guide.src.html").exists()
    assert not (ROOT / "docs/user-guide.html").exists()
