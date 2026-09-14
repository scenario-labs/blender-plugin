# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Recovery preserves the original workflow commit used in build provenance."""

import copy
import json
import subprocess

import pytest

from tools import find_release_draft as recovery


REPO = "scenario-labs/blender-plugin"
TARGET = "a" * 40
CURRENT = TARGET
DRAFT = {
    "id": 123,
    "draft": True,
    "prerelease": False,
    "tag_name": "blender-plugin-v0.9.10",
    "target_commitish": TARGET,
    "author": {"login": recovery.RELEASE_APP},
}


def request_for(pages):
    calls = []

    def request(endpoint, *, paginate=False):
        calls.append((endpoint, paginate))
        assert endpoint == f"repos/{REPO}/releases?per_page=100"
        assert paginate
        return copy.deepcopy(pages)

    return request, calls


def test_no_draft_ignores_published_and_other_namespace_releases():
    request, calls = request_for([[dict(DRAFT, draft=False)], [dict(DRAFT, tag_name="skills-v1.0.0")]])
    assert recovery.find_draft(REPO, CURRENT, request) == {"found": "false"}
    assert len(calls) == 1


def test_original_workflow_can_recover_one_verified_draft_from_later_pages():
    request, calls = request_for([[], [DRAFT]])
    assert recovery.find_draft(REPO, CURRENT, request) == {
        "found": "true", "tag_name": DRAFT["tag_name"], "sha": TARGET, "release_id": "123",
    }
    assert len(calls) == 1


def test_multiple_drafts_fail_instead_of_selecting_one():
    request, calls = request_for([[DRAFT], [dict(DRAFT, id=124, tag_name="blender-plugin-v0.9.11")]])
    with pytest.raises(ValueError, match="Multiple"):
        recovery.find_draft(REPO, CURRENT, request)
    assert len(calls) == 1


@pytest.mark.parametrize("changes, message", [
    ({"author": {"login": "other-user"}}, "GitHub App"),
    ({"author": None}, "GitHub App"),
    ({"target_commitish": "main"}, "full commit SHA"),
    ({"target_commitish": "a" * 39}, "full commit SHA"),
    ({"tag_name": "blender-plugin-v0.9.10-rc.1"}, "stable"),
    ({"tag_name": "blender-plugin-v0.9.10\nsha=bad"}, "stable"),
    ({"prerelease": True}, "stable"),
    ({"id": "123\nfound=false"}, "release ID"),
])
def test_unsafe_drafts_are_rejected(changes, message):
    request, calls = request_for([[dict(DRAFT, **changes)]])
    with pytest.raises(ValueError, match=message):
        recovery.find_draft(REPO, CURRENT, request)
    assert len(calls) == 1


@pytest.mark.parametrize("other_sha", ["b" * 40, "c" * 40, "d" * 40], ids=["newer", "older", "unrelated"])
def test_any_different_workflow_commit_must_rerun_the_original(other_sha):
    request, calls = request_for([[DRAFT]])
    with pytest.raises(ValueError, match=f"Rerun the original release workflow for {TARGET}"):
        recovery.find_draft(REPO, other_sha, request)
    assert len(calls) == 1


def test_output_is_written_only_after_all_verification_passes(tmp_path):
    output = tmp_path / "outputs"
    output.write_text("existing=value\n")
    env = {"GH_REPO": REPO, "GITHUB_SHA": CURRENT, "GITHUB_OUTPUT": str(output)}
    invalid, _ = request_for([[dict(DRAFT, target_commitish="main")]])
    assert recovery.main(env, invalid) == 1
    assert output.read_text() == "existing=value\n"
    valid, _ = request_for([[DRAFT]])
    assert recovery.main(dict(env, GITHUB_SHA="b" * 40), valid) == 1
    assert output.read_text() == "existing=value\n"
    assert recovery.main(env, valid) == 0
    assert output.read_text().endswith(
        f"found=true\ntag_name=blender-plugin-v0.9.10\nsha={TARGET}\nrelease_id=123\n"
    )


def test_gh_pagination_keeps_tokens_out_of_command_arguments(monkeypatch):
    calls = []

    def run(command, **options):
        calls.append((command, options))
        return subprocess.CompletedProcess(command, 0, stdout=json.dumps([[DRAFT]]))

    monkeypatch.setattr(recovery.subprocess, "run", run)
    assert recovery.gh_json("repos/example/repo/releases?per_page=100", paginate=True) == [[DRAFT]]
    assert calls[0][0] == ["gh", "api", "repos/example/repo/releases?per_page=100", "--paginate", "--slurp"]
    assert calls[0][1]["check"] is True


def test_failed_api_call_does_not_emit_success_outputs(tmp_path, capsys):
    def failed(*args, **kwargs):
        raise subprocess.CalledProcessError(1, ["gh", "api"], stderr="private response")

    output = tmp_path / "outputs"
    env = {"GH_REPO": REPO, "GITHUB_SHA": CURRENT, "GITHUB_OUTPUT": str(output)}
    assert recovery.main(env, failed) == 1
    assert not output.exists()
    assert "private response" not in capsys.readouterr().err
