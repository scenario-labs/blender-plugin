# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Offline failure reporting and actual weekly workflow shell contracts."""

import json
import os
import subprocess
from pathlib import Path
from types import SimpleNamespace

import pytest

from tools import report_ci_failure as reporter

ROOT = Path(__file__).resolve().parents[2]
TITLE = "ci: weekly headless run failed on macos-latest"
REPOSITORY = "example/extension"


def test_repeated_failure_comments_exact_issue_beyond_first_page(monkeypatch):
    calls = []
    issues = [
        {"number": 1, "title": TITLE + " (old version)"},
        {"number": 2, "title": TITLE, "pull_request": {}},
    ]

    def github(endpoint, *arguments, payload=None):
        calls.append((endpoint, arguments, payload))
        if payload is None:
            # Simulate API pagination, including an unrelated issue and PR.
            return [issues[:2], issues[2:]]
        if endpoint.endswith("/comments"):
            return {"id": 100}
        issues.append({"number": 42, "title": payload["title"]})
        return issues[-1]

    monkeypatch.setattr(reporter, "github", github)
    labels = ["bug", "area:ci", "os:macos", "blender:5.1"]
    assert reporter.report_failure(REPOSITORY, TITLE, "first run", labels) == "created"
    assert reporter.report_failure(REPOSITORY, TITLE, "second run", labels) == "commented"
    writes = [(endpoint, payload) for endpoint, _, payload in calls if payload is not None]
    assert writes == [
        (f"repos/{REPOSITORY}/issues", {"title": TITLE, "body": "first run", "labels": labels}),
        (f"repos/{REPOSITORY}/issues/42/comments", {"body": "second run"}),
    ]
    assert "--paginate" in calls[0][1]
    assert "--slurp" in calls[0][1]
    assert "state=open" in calls[0][1]


@pytest.mark.parametrize(
    "pages",
    [
        None,
        [],
        {"message": "API error"},
        [{"title": TITLE}],
        [[None]],
        [[{"title": 42}]],
        [[{"title": TITLE, "number": True}]],
        [[{"title": TITLE, "number": 0}]],
        [[{"title": TITLE, "number": 1}], [{"title": TITLE, "number": 2}]],
    ],
)
def test_invalid_or_ambiguous_listing_never_writes(monkeypatch, pages):
    calls = []

    def github(*arguments, payload=None):
        calls.append(payload)
        return pages

    monkeypatch.setattr(reporter, "github", github)
    with pytest.raises(ValueError):
        reporter.report_failure(REPOSITORY, TITLE, "run", ["area:ci"])
    assert calls == [None]


@pytest.mark.parametrize("fail_on", [1, 2])
def test_api_failure_is_not_retried(monkeypatch, fail_on):
    calls = []

    def github(*arguments, **kwargs):
        calls.append((arguments, kwargs))
        if len(calls) == fail_on:
            raise subprocess.CalledProcessError(1, "gh")
        return [[]]

    monkeypatch.setattr(reporter, "github", github)
    with pytest.raises(subprocess.CalledProcessError):
        reporter.report_failure(REPOSITORY, TITLE, "run", ["area:ci"])
    assert len(calls) == fail_on


def test_github_write_passes_json_stdin_without_shell_or_retry(monkeypatch):
    captured = {}

    def run(command, **kwargs):
        captured.update(command=command, **kwargs)
        return SimpleNamespace(stdout='{"number": 42}')

    monkeypatch.setattr(reporter.subprocess, "run", run)
    payload = {"body": 'Literal `command`, $(expression), quotes " and\nnewlines'}
    assert reporter.github("repos/example/extension/issues/42/comments", payload=payload) == {
        "number": 42
    }
    assert captured["command"] == [
        "gh",
        "api",
        "repos/example/extension/issues/42/comments",
        "--input",
        "-",
    ]
    assert json.loads(captured["input"]) == payload
    assert captured["check"] is True
    assert captured["timeout"] == 60
    assert not captured.get("shell")


def cli_arguments():
    return [
        "--repository",
        REPOSITORY,
        "--version",
        "5.1.2",
        "--run-id",
        "42",
        "--run-attempt",
        "2",
    ]


def test_cli_builds_scoped_tracking_issue(monkeypatch):
    monkeypatch.setattr(
        reporter,
        "matrix_outcomes",
        lambda *args: {"macos-latest": ("success", 1, 2), "windows-latest": ("failure", 2, 2)},
    )
    captured = []
    monkeypatch.setattr(
        reporter, "report_failure", lambda *args: captured.append(args) or "created"
    )
    assert reporter.main(cli_arguments()) == 0
    repository, title, body, labels = captured[0]
    assert repository == REPOSITORY
    assert title == "ci: weekly headless run failed on windows-latest"
    assert f"https://github.com/{REPOSITORY}/actions/runs/42" in body
    assert "blender-tests-windows-latest" in body
    assert labels == ["bug", "area:ci", "os:windows", "blender:5.1"]


@pytest.mark.parametrize(
    "flag,value",
    [
        ("--version", "5.1"),
        ("--repository", "../other"),
        ("--run-id", "0"),
        ("--run-attempt", "-1"),
    ],
)
def test_cli_rejects_invalid_context_before_reporting(monkeypatch, flag, value):
    calls = []
    monkeypatch.setattr(reporter, "github", lambda *args, **kwargs: calls.append(args))
    monkeypatch.setattr(reporter, "report_failure", lambda *args: calls.append(args))
    arguments = cli_arguments()
    arguments[arguments.index(flag) + 1] = value
    with pytest.raises(SystemExit, match="2"):
        reporter.main(arguments)
    assert not calls


def test_cli_does_not_print_github_error_content(monkeypatch, capsys):
    monkeypatch.setattr(
        reporter, "matrix_outcomes", lambda *args: {"windows-latest": ("failure", 2, 2)}
    )

    def report(*args):
        raise subprocess.CalledProcessError(1, "gh", stderr="private response fixture")

    monkeypatch.setattr(reporter, "report_failure", report)
    assert reporter.main(cli_arguments()) == 1
    output = capsys.readouterr()
    assert "CalledProcessError" in output.err
    assert "private response fixture" not in output.err + output.out


def matrix_job(platform, conclusion="success", **changes):
    return {
        "id": 1 if platform == "macos-latest" else 2,
        "name": f"blender 5.1.2 ({platform})",
        "run_id": 42,
        "run_attempt": 2,
        "status": "completed",
        "conclusion": conclusion,
        **changes,
    }


@pytest.mark.parametrize("conclusion", ["success", "failure", "timed_out", "cancelled", "skipped"])
def test_current_attempt_outcomes_are_read_before_reporting(monkeypatch, conclusion):
    calls = []
    writes = []

    def github(endpoint, *args, **kwargs):
        calls.append((endpoint, args))
        return [
            {
                "jobs": [
                    {"name": "report-native-failures", "status": "in_progress"},
                    matrix_job("macos-latest"),
                ]
            },
            {"jobs": [matrix_job("windows-latest", conclusion)]},
        ]

    monkeypatch.setattr(reporter, "github", github)
    monkeypatch.setattr(reporter, "report_failure", lambda *args: writes.append(args) or "created")
    assert reporter.main(cli_arguments()) == 0
    assert calls[0][0] == f"repos/{REPOSITORY}/actions/runs/42/jobs"
    assert "--paginate" in calls[0][1] and "--slurp" in calls[0][1]
    assert "filter=latest" in calls[0][1]
    assert len(writes) == (conclusion != "success")
    if writes:
        assert f"job conclusion: `{conclusion}`" in writes[0][2]
        assert "setup, native tests, timeout and artifact preservation" in writes[0][2]
        assert "actions/runs/42/job/2" in writes[0][2]


@pytest.mark.parametrize(
    "bad",
    [
        None,
        [],
        {},
        [{"jobs": None}],
        [{"jobs": [None]}],
        [{"jobs": []}],
        [{"jobs": [matrix_job("macos-latest")]}],
        [
            {
                "jobs": [
                    matrix_job("macos-latest"),
                    matrix_job("macos-latest"),
                    matrix_job("windows-latest"),
                ]
            }
        ],
        *[
            {"change": change}
            for change in [
                {"run_id": 41},
                {"run_attempt": 3},
                {"run_attempt": 0},
                {"run_attempt": True},
                {"id": True},
                {"id": 0},
                {"id": 1},
                {"status": "in_progress"},
                {"conclusion": None},
                {"conclusion": "unexpected"},
                {"name": 42},
                {"name": "blender 5.2.1 (windows-latest)"},
            ]
        ],
    ],
)
def test_missing_ambiguous_or_foreign_matrix_results_never_write(monkeypatch, bad):
    if isinstance(bad, dict) and "change" in bad:
        bad = [
            {
                "jobs": [
                    matrix_job("macos-latest", "failure"),
                    matrix_job("windows-latest", **bad["change"]),
                ]
            }
        ]
    writes = []
    monkeypatch.setattr(reporter, "github", lambda *args, **kwargs: bad)
    monkeypatch.setattr(reporter, "report_failure", lambda *args: writes.append(args))
    assert reporter.main(cli_arguments()) == 1
    assert not writes


def test_failed_only_rerun_retains_prior_success_without_duplicate_failure(monkeypatch):
    jobs = [matrix_job("macos-latest", run_attempt=1), matrix_job("windows-latest", "timed_out")]
    monkeypatch.setattr(reporter, "github", lambda *args, **kwargs: [{"jobs": jobs}])
    writes = []
    monkeypatch.setattr(reporter, "report_failure", lambda *args: writes.append(args))
    assert reporter.main(cli_arguments()) == 0
    assert len(writes) == 1
    assert "windows-latest" in writes[0][1]
    assert "job attempt 2" in writes[0][2]


def workflow_script(name):
    """Extract one named literal run block; shell behavior is tested below."""
    workflow = (ROOT / ".github/workflows/blender-os.yml").read_text()
    section = workflow.split(f"      - name: {name}\n", 1)[1].split("\n      - ", 1)[0]
    return (
        "\n".join(
            line.removeprefix("          ") for line in section.split("run: |\n", 1)[1].splitlines()
        )
        + "\n"
    )


@pytest.mark.skipif(os.name == "nt", reason="Exercises the workflow's hosted bash shell")
@pytest.mark.parametrize("exit_code", [0, 73])
def test_native_workflow_preserves_exit_status_through_tee(tmp_path, exit_code):
    binary = tmp_path / "uv"
    binary.write_text(f"#!/bin/sh\nprintf '%s\\n' native-output\nexit {exit_code}\n")
    binary.chmod(0o755)
    script = tmp_path / "step.sh"
    script.write_text(workflow_script("Test the exact ZIP in a new profile"))
    result = subprocess.run(
        ["bash", "--noprofile", "--norc", "-eo", "pipefail", str(script)],
        env={
            **os.environ,
            "PATH": f"{tmp_path}{os.pathsep}{os.environ['PATH']}",
            "RUNNER_TEMP": str(tmp_path),
            "BLENDER_VERSION": "5.1.2",
        },
        capture_output=True,
        text=True,
    )
    assert result.returncode == exit_code
    assert (tmp_path / "blender-tests.log").read_text() == "native-output\n"


@pytest.mark.skipif(os.name == "nt", reason="Exercises the workflow's hosted bash shell")
def test_failed_fetch_does_not_publish_binary_selection(tmp_path):
    binary = tmp_path / "uv"
    binary.write_text(
        "#!/bin/sh\nprintf '%s\\n' fake-path\nprintf '%s\\n' fetch-failed >&2\nexit 23\n"
    )
    binary.chmod(0o755)
    script = tmp_path / "step.sh"
    script.write_text(workflow_script("Fetch the pinned official Blender archive"))
    environment = tmp_path / "github.env"
    result = subprocess.run(
        ["bash", "--noprofile", "--norc", "-eo", "pipefail", str(script)],
        env={
            **os.environ,
            "PATH": f"{tmp_path}{os.pathsep}{os.environ['PATH']}",
            "RUNNER_TEMP": str(tmp_path),
            "BLENDER_VERSION": "5.1.2",
            "BLENDER_SHA256": "f" * 64,
            "GITHUB_ENV": str(environment),
        },
        capture_output=True,
        text=True,
    )
    assert result.returncode == 23
    assert not environment.exists()
    assert (tmp_path / "blender-download.log").read_text() == "fetch-failed\n"
