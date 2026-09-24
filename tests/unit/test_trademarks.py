# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Keep the trademark notice and its public entry point present."""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_trademark_notice_covers_project_and_third_party_marks():
    notice = (ROOT / "TRADEMARKS.md").read_text(encoding="utf-8")
    for statement in ("Scenario Inc.", "Section 7(e)", "Blender Foundation", "respective owners"):
        assert statement in notice
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    assert any(target == "TRADEMARKS.md" for target in re.findall(r"\]\(([^)]+)\)", readme))
