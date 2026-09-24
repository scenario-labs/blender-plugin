# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Keep contributor-facing scope names aligned with commitlint's authority."""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def configured_scopes():
    config = (ROOT / "commitlint.config.ts").read_text()
    match = re.search(r'"scope-enum":\s*\[\s*2,\s*"always",\s*\[(.*?)\]', config, re.S)
    assert match is not None, "Locate the authoritative commitlint scope-enum before editing copies"
    scopes = re.findall(r'^\s*"([^\"]+)",', match[1], re.M)
    assert scopes, "The commitlint scope list must not be empty"
    return scopes


def test_canonical_guide_scope_map_matches_commitlint_in_order():
    guide = (ROOT / "docs/development/contributions.md").read_text()
    section = guide.split("## Scopes\n", 1)[1].split("\n## ", 1)[0]
    assert re.findall(r"^\| `([^`]+)` \|", section, re.M) == configured_scopes()


def test_pr_template_scope_list_matches_commitlint_in_order():
    template = (ROOT / ".github/pull_request_template.md").read_text()
    comment = template.split("<!--", 1)[1].split("-->", 1)[0]
    scopes = comment.split("Scopes:", 1)[1].split("Example:", 1)[0]
    assert [scope.strip() for scope in scopes.strip().removesuffix(".").split(",")] == (
        configured_scopes()
    )


def test_contributor_entry_links_to_canonical_scope_map_and_template():
    guide = (ROOT / "CONTRIBUTING.md").read_text()
    section = guide.split("## Commits, branches and pull requests\n", 1)[1].split("\n## ", 1)[0]
    assert "(docs/development/contributions.md#scopes)" in section
    assert "(.github/pull_request_template.md)" in section
