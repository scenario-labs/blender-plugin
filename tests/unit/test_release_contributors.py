# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Draft releases thank their human pull request authors before publication."""

import subprocess
from pathlib import Path

import pytest

from tools import release_contributors as rc

REPO = "scenario-labs/blender-plugin"
TAG = "blender-plugin-v0.13.0"
SHA = "a" * 40
URL = f"https://github.com/{REPO}/pull"
NOTES = f"""## What's Changed
* feat(ui): one by @qchantel in {URL}/1
* chore(deps): bump by @dependabot[bot] in {URL}/2
* fix(docs): two by @Hervenivon in {URL}/3
* docs: three by @qchantel in {URL}/4
* feat: four by @edemaistre in {URL}/5

## New Contributors
* @edemaistre made their first contribution in {URL}/5
* @dependabot[bot] made their first contribution in {URL}/2

**Full Changelog**: https://github.com/{REPO}/compare/a...b
"""
BODY = "## [0.13.0](https://example.invalid) (2026-11-04)\n\n### Features\n\n* one\n"
WORKFLOW = Path(__file__).resolve().parents[2] / ".github/workflows/release-please.yml"


def test_contributors_are_unique_sorted_humans_with_first_contributions():
    logins, first = rc.contributors(NOTES)
    assert logins == ["edemaistre", "Hervenivon", "qchantel"]
    assert first == [f"* @edemaistre made their first contribution in {URL}/5"]


@pytest.mark.parametrize(
    ("logins", "text"),
    [(["a"], "@a"), (["a", "b"], "@a and @b"), (["a", "b", "c"], "@a, @b and @c")],
)
def test_mention_list(logins, text):
    assert rc.mention_list(logins) == text


def test_section_is_appended_after_the_generated_sections():
    assert rc.with_contributors(BODY, NOTES) == (
        BODY
        + "\n### Contributors\n\nThanks to @edemaistre, @Hervenivon and @qchantel.\n\n"
        + f"* @edemaistre made their first contribution in {URL}/5\n"
    )


def test_existing_section_or_bot_only_notes_leave_the_body_alone():
    assert rc.with_contributors(BODY + "\n### Contributors\n\nThanks to @x.\n", NOTES) is None
    assert rc.with_contributors(BODY, f"* bump by @dependabot[bot] in {URL}/2\n") is None


def fake_gh(draft=None, latest="blender-plugin-v0.12.0"):
    calls, edits = [], []
    draft = draft or {"body": BODY, "isDraft": True, "targetCommitish": SHA}

    def request(*args):
        calls.append(args)
        if args[:2] == ("release", "view"):
            return draft
        if args[1] == f"repos/{REPO}/releases/latest":
            return {"tag_name": latest}
        return {"body": NOTES}

    def run(*args):
        edits.append(Path(args[-1]).read_text(encoding="utf-8"))

    return request, run, calls, edits


def test_update_edits_the_draft_with_notes_since_the_latest_release():
    request, run, calls, edits = fake_gh()
    assert rc.update(REPO, TAG, SHA, request, run) is True
    generate = calls[2]
    assert f"repos/{REPO}/releases/generate-notes" in generate
    assert "previous_tag_name=blender-plugin-v0.12.0" in generate
    assert f"target_commitish={SHA}" in generate
    assert edits == [rc.with_contributors(BODY, NOTES)]


@pytest.mark.parametrize(
    ("draft", "latest"),
    [
        ({"body": BODY, "isDraft": False, "targetCommitish": SHA}, "blender-plugin-v0.12.0"),
        ({"body": BODY, "isDraft": True, "targetCommitish": "b" * 40}, "blender-plugin-v0.12.0"),
        (None, TAG),
        (None, "v0.9.9"),
    ],
)
def test_update_refuses_a_published_release_another_commit_or_no_previous_tag(draft, latest):
    request, run, _, edits = fake_gh(draft, latest)
    with pytest.raises(ValueError):
        rc.update(REPO, TAG, SHA, request, run)
    assert edits == []


def test_main_reports_failures_without_output(capsys):
    def failing(*args):
        raise subprocess.CalledProcessError(1, ["gh"], output="secret")

    environ = {"GH_REPO": REPO, "TAG": TAG, "RELEASE_SHA": SHA}
    assert rc.main(environ, failing, failing) == 1
    assert "secret" not in capsys.readouterr().err


def test_workflow_thanks_contributors_before_publication_without_blocking_it():
    text = WORKFLOW.read_text()
    assets = text.split("  assets:\n", 1)[1].split("  validate:\n", 1)[0]
    step = assets.split("- name: Thank the release's contributors", 1)[1]
    assert "continue-on-error: true" in step
    assert "GH_TOKEN: ${{ steps.app-token.outputs.token }}" in step
    assert "python3 tools/release_contributors.py" in step
