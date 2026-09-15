# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Execute the workflow's shell with offline GitHub and HTTP substitutes."""

import json
import os
import subprocess
import textwrap
from pathlib import Path

import pytest

WORKFLOW = (
    Path(__file__).resolve().parents[2] / ".github/workflows/publish-changelog.yml"
)
VERSION = "0.9.10"
QUEUED = {"version": VERSION, "action": "create", "entryId": 123}
EXISTING = {"version": VERSION, "reason": "already exists", "entryId": 123}
BODY = "## [0.9.10](https://example.com/release) (2026-09-14)\n\n### Bug Fixes\n\n* Ship license"


def run_workflow(
    tmp_path, response, *, release=None, secret="test-secret", curl_exit=0
):
    # This workflow has a single final run block. Execute it verbatim so the
    # tests exercise jq, shell exit behavior, and the submitted payload together.
    script = textwrap.dedent(WORKFLOW.read_text().split("        run: |\n")[1])
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    temp_dir = tmp_path / "temp"
    temp_dir.mkdir()
    (tmp_path / "release.json").write_text(
        json.dumps(
            release
            or {
                "body": BODY,
                "isDraft": False,
                "isPrerelease": False,
            }
        )
    )
    (tmp_path / "response.json").write_text(response)
    stubs = {
        "gh": 'cat "$CASE_DIR/release.json"',
        "curl": """
            cat > "$CASE_DIR/curl-config"
            printf '%s\\n' "$@" > "$CASE_DIR/curl-args"
            while [ "$#" -gt 0 ]; do
              case "$1" in
                --output) output="$2"; shift ;;
                --data-binary) cp "${2#@}" "$CASE_DIR/payload.json"; shift ;;
              esac
              shift
            done
            cp "$CASE_DIR/response.json" "$output"
            exit "$CURL_EXIT"
        """,
    }
    for name, stub in stubs.items():
        path = bin_dir / name
        path.write_text("#!/bin/bash\nset -eu\n" + textwrap.dedent(stub))
        path.chmod(0o755)
    env = {
        **os.environ,
        "PATH": f"{bin_dir}:{os.environ['PATH']}",
        "CASE_DIR": str(tmp_path),
        "TMPDIR": str(temp_dir),
        "CHANGELOG_INGEST_SECRET": secret,
        "TAG": f"blender-plugin-v{VERSION}",
        "CURL_EXIT": str(curl_exit),
    }
    result = subprocess.run(
        ["bash", "-c", script], env=env, capture_output=True, text=True, check=False
    )
    assert list(temp_dir.iterdir()) == []
    if secret:
        assert secret not in result.stdout + result.stderr
    return result


@pytest.mark.parametrize(
    "response, message",
    [
        ({"queued": [QUEUED], "skipped": []}, "Queued"),
        ({"queued": [], "skipped": [EXISTING]}, "::warning::"),
    ],
)
def test_acknowledged_response_does_not_claim_publication(tmp_path, response, message):
    result = run_workflow(tmp_path, json.dumps(response))
    assert result.returncode == 0, result.stderr
    assert message in result.stdout
    assert "Published" not in result.stdout
    assert json.loads((tmp_path / "payload.json").read_text()) == {
        "repo": "blender-plugin",
        "changelog": BODY + "\n",
    }
    args = (tmp_path / "curl-args").read_text()
    assert "test-secret" not in args
    assert "--retry" not in args
    assert (
        'header = "Authorization: Bearer test-secret"'
        in (tmp_path / "curl-config").read_text()
    )


@pytest.mark.parametrize(
    "response",
    [
        {
            "queued": [],
            "skipped": [{"version": VERSION, "reason": "DB error: enum missing"}],
        },
        {
            "queued": [],
            "skipped": [{"version": VERSION, "reason": "Queue error: unavailable"}],
        },
        {"queued": [], "skipped": []},
        {"queued": [dict(QUEUED, version="0.9.11")], "skipped": []},
        {"queued": [dict(QUEUED, action="overwrite")], "skipped": []},
        {"queued": [QUEUED], "skipped": [EXISTING]},
        {"queued": [], "skipped": [{"version": VERSION, "reason": "already exists"}]},
        {"queued": None, "skipped": []},
        {"error": "Unauthorized"},
    ],
)
def test_http_200_application_errors_fail(tmp_path, response):
    result = run_workflow(tmp_path, json.dumps(response))
    assert result.returncode != 0
    assert "::error::Changelog ingest did not acknowledge" in result.stdout


@pytest.mark.parametrize("response", ["", "not json", "<html>Unavailable</html>"])
def test_unexpected_response_fails(tmp_path, response):
    assert run_workflow(tmp_path, response).returncode != 0


@pytest.mark.parametrize("field", ["isDraft", "isPrerelease"])
def test_unpublished_or_prerelease_never_posts(tmp_path, field):
    release = {"body": BODY, "isDraft": False, "isPrerelease": False, field: True}
    result = run_workflow(tmp_path, "{}", release=release)
    assert result.returncode != 0
    assert not (tmp_path / "curl-args").exists()


def test_hidden_only_release_never_posts(tmp_path):
    result = run_workflow(
        tmp_path,
        "{}",
        release={
            "body": "## 0.9.10",
            "isDraft": False,
            "isPrerelease": False,
        },
    )
    assert result.returncode == 0
    assert not (tmp_path / "curl-args").exists()


def test_missing_secret_never_posts(tmp_path):
    assert run_workflow(tmp_path, "{}", secret="").returncode != 0
    assert not (tmp_path / "curl-args").exists()


@pytest.mark.parametrize("exit_code", [22, 28])
def test_http_error_or_uncertain_timeout_fails(tmp_path, exit_code):
    result = run_workflow(
        tmp_path, json.dumps({"queued": [QUEUED], "skipped": []}), curl_exit=exit_code
    )
    assert result.returncode == exit_code
    assert "Queued" not in result.stdout
