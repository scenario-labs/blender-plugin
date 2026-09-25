# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Offline reporting and execution contracts for the scheduled API audit."""

import json
import os
import re
import subprocess
import sys
from pathlib import Path

import pytest

from tests.unit.test_workflows import block
from tools import report_api_failure as reporter
from tools import report_ci_failure as shared

ROOT = Path(__file__).resolve().parents[2]
WORKFLOW = ROOT / ".github/workflows/api-contract.yml"


def arguments(report, *, code="1", result="failure"):
    return [
        "--repository",
        "example/extension",
        "--run-id",
        "42",
        "--run-attempt",
        "2",
        "--job-result",
        result,
        "--audit-exit-code",
        code,
        "--artifact-id",
        "71",
        "--report",
        str(report),
    ]


def test_repeated_api_failure_uses_exact_paginated_tracking_issue(tmp_path, monkeypatch):
    report = tmp_path / "audit.md"
    report.write_text("# Payload audit\n\nA HIGH finding.\n")
    issues, writes = [], []

    def github(endpoint, *args, payload=None):
        if payload is None:
            assert "labels=area:ci" in args
            assert "--paginate" in args and "--slurp" in args
            return [[{"number": 1, "title": reporter.TITLE + " old"}], issues]
        writes.append((endpoint, payload))
        if not endpoint.endswith("/comments"):
            issues.append({"number": 9, "title": payload["title"]})
        return {"id": 9}

    monkeypatch.setattr(shared, "github", github)
    assert reporter.main(arguments(report)) == 0
    assert reporter.main(arguments(report)) == 0
    assert writes[0][0] == "repos/example/extension/issues"
    assert writes[0][1]["title"] == reporter.TITLE
    assert writes[0][1]["labels"] == ["bug", "feature:API", "quality", "area:ci"]
    assert "A HIGH finding" in writes[0][1]["body"]
    assert writes[1][0] == "repos/example/extension/issues/9/comments"


@pytest.mark.parametrize(
    "code,reason",
    [
        ("1", "HIGH schema finding or a fetch/schema/cache failure"),
        (
            "2",
            "could not complete cleanly: inspect credentials, configuration, report output or cache cleanup",
        ),
        ("0", "audit passed; inspect later workflow steps"),
        ("", "setup, runner timeout or interruption"),
        ("73", "exited unexpectedly with status 73"),
    ],
)
def test_failures_have_distinct_diagnostics_even_without_artifact(
    tmp_path, monkeypatch, code, reason
):
    writes = []
    monkeypatch.setattr(reporter, "report_failure", lambda *args: writes.append(args) or "created")
    assert reporter.main(arguments(tmp_path / "missing.md", code=code)) == 0
    body = writes[0][2]
    assert reason in body
    assert "No report was available" in body
    assert "Attempt 2; audit job result: `failure`" in body
    assert "https://github.com/example/extension/actions/runs/42" in body


def test_success_does_not_read_artifacts_or_write_issues(tmp_path, monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail("successful audit must not report")

    monkeypatch.setattr(reporter, "report_failure", forbidden)
    assert reporter.main(arguments(tmp_path, code="0", result="success")) == 0


def test_report_excerpt_is_literal_and_bounded_after_escaping(tmp_path, monkeypatch):
    report = tmp_path / "audit.md"
    report.write_text("</pre>\n@someone `$(command)` [link](https://example.org)\n" + "<&>" * 20000)
    writes = []
    monkeypatch.setattr(reporter, "report_failure", lambda *args: writes.append(args) or "created")
    assert reporter.main(arguments(report)) == 0
    body = writes[0][2]
    assert body.count("<pre>") == 1 and body.count("</pre>") == 1
    assert "&lt;/pre&gt;" in body
    assert "@someone `$(command)`" in body
    assert "Report excerpt truncated" in body
    assert len(body) < 60000


@pytest.mark.parametrize("kind", ["malformed-list", "ambiguous-list", "uncertain-write"])
def test_reporter_failure_is_sanitized_without_retry(tmp_path, monkeypatch, capsys, kind):
    calls = []

    def github(endpoint, *args, payload=None):
        calls.append(payload)
        if kind == "malformed-list":
            return {"error": "private-response"}
        if kind == "ambiguous-list":
            return [[{"title": reporter.TITLE, "number": n} for n in (1, 2)]]
        if payload is not None:
            raise subprocess.CalledProcessError(1, "gh", stderr="private-response")
        return [[]]

    monkeypatch.setattr(shared, "github", github)
    assert reporter.main(arguments(tmp_path / "absent")) == 1
    assert len(calls) == (2 if kind == "uncertain-write" else 1)
    assert "private-response" not in capsys.readouterr().err


@pytest.mark.parametrize(
    "extra",
    [
        ["--run-id", "0"],
        ["--run-attempt", "-1"],
        ["--repository", "../repo"],
        ["--job-result", ""],
        ["--audit-exit-code", "private"],
        ["--audit-exit-code", "256"],
        ["--artifact-id", "0"],
        ["--artifact-id", "-1"],
        ["--artifact-id", "71,72"],
        ["--artifact-id", "private"],
        ["--artifact-id", "1" * 21],
    ],
)
def test_bad_context_fails_before_reporting(tmp_path, monkeypatch, extra):
    monkeypatch.setattr(reporter, "report_failure", lambda *args: pytest.fail("invalid context"))
    with pytest.raises(SystemExit) as error:
        reporter.main(arguments(tmp_path / "absent") + extra)
    assert error.value.code == 2


def test_symlink_report_is_not_followed(tmp_path, monkeypatch, capsys):
    report = tmp_path / "audit.md"
    try:
        report.symlink_to(tmp_path / "absent")
    except OSError:
        pytest.skip("Host does not permit symlinks")
    monkeypatch.setattr(reporter, "report_failure", lambda *args: pytest.fail("untrusted file"))
    assert reporter.main(arguments(report)) == 1
    assert capsys.readouterr().err == "API failure reporting failed (ValueError).\n"


def test_workflow_keeps_credentials_and_writes_out_of_pr_ci():
    text = WORKFLOW.read_text()
    events = set(re.findall(r"^  ([\w-]+):", block(text, "on"), re.MULTILINE))
    assert events == {"schedule", "workflow_dispatch"}
    permissions = [
        line.strip()
        for line in block(text, "permissions").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]
    assert permissions == ["contents: read"]
    assert "cancel-in-progress: false" in block(text, "concurrency")
    audit = block(text, "audit", indent=2)
    report = block(text, "report", indent=2)
    for job in (audit, report):
        assert "github.repository == 'scenario-labs/blender-plugin'" in job
        assert "github.ref == 'refs/heads/main'" in job
        assert "persist-credentials: false" in job
    assert "issues: write" not in audit
    permissions = block(report, "permissions", indent=4)
    assert "issues: write" in permissions and "actions: read" in permissions
    assert "secrets." not in report
    assert "secrets.SCENARIO_TEST_API_KEY" in audit and "secrets.SCENARIO_TEST_API_SECRET" in audit
    assert "secrets.SCENARIO_TEST_PROJECT_ID" in audit
    assert "if: always()" in audit and "retention-days: 90" in audit
    assert "always() && !cancelled()" in report
    assert "needs.audit.result != 'success' || needs.audit.outputs.exit_code != '0'" in report
    assert "continue-on-error: true" in report


def test_report_download_selects_the_audit_upload_not_the_reporter_attempt():
    text = WORKFLOW.read_text()
    audit = block(text, "audit", indent=2)
    report = block(text, "report", indent=2)
    assert "artifact_id: ${{ steps.upload.outputs.artifact-id }}" in audit
    assert "id: upload" in audit
    assert "name: model-payload-audit-${{ github.run_attempt }}" in audit
    assert "if: needs.audit.outputs.artifact_id != ''" in report
    assert "artifact-ids: ${{ needs.audit.outputs.artifact_id }}" in report
    assert "AUDIT_ARTIFACT_ID: ${{ needs.audit.outputs.artifact_id }}" in report
    assert "model-payload-audit-${{ github.run_attempt }}" not in report
    assert "pattern:" not in report and "run-id:" not in report


def workflow_script(name):
    section = WORKFLOW.read_text().split(f"      - name: {name}\n", 1)[1]
    section = section.split("      - name:", 1)[0]
    return (
        "\n".join(
            line.removeprefix("          ") for line in section.split("run: |\n", 1)[1].splitlines()
        )
        + "\n"
    )


@pytest.fixture
def workflow_runner(tmp_path):
    binary = tmp_path / "uv"
    binary.write_text(
        f"#!{sys.executable}\n"
        "import json, os, sys\nfrom pathlib import Path\n"
        "from tools import audit_payloads as audit\n"
        "def run(args):\n"
        "    Path(os.environ['TEST_ARGS']).write_text(json.dumps(args))\n"
        "    return int(os.environ['TEST_STATUS'])\n"
        "audit.run = run\n"
        "exec(compile(sys.stdin.read(), '<workflow>', 'exec'))\n"
    )
    binary.chmod(0o755)

    def run(models="", status=0):
        args = tmp_path / "args.json"
        args.unlink(missing_ok=True)
        output = tmp_path / "output.txt"
        output.write_text("")
        result = subprocess.run(
            [
                "bash",
                "--noprofile",
                "--norc",
                "-eo",
                "pipefail",
                "-c",
                workflow_script("Audit current model schemas"),
            ],
            cwd=ROOT,
            env={
                **os.environ,
                "PATH": str(tmp_path) + os.pathsep + os.environ["PATH"],
                "PYTHONPATH": str(ROOT),
                "RUNNER_TEMP": str(tmp_path),
                "GITHUB_OUTPUT": str(output),
                "AUDIT_MODELS": models,
                "TEST_ARGS": str(args),
                "TEST_STATUS": str(status),
            },
            capture_output=True,
            text=True,
        )
        return result, json.loads(args.read_text()) if args.exists() else None, output.read_text()

    return run


@pytest.mark.skipif(os.name == "nt", reason="Execute hosted Ubuntu bash with a fake audit")
@pytest.mark.parametrize("status", [0, 1, 2, 73])
def test_actual_workflow_preserves_audit_status_and_models(workflow_runner, status):
    result, args, output = workflow_runner("model_one\nmodel_two\tmodel_three", status)
    assert result.returncode == status
    assert output == f"exit_code={status}\n"
    assert args[-4:] == ["--models", "model_one", "model_two", "model_three"]
    assert args[2:4] == ["--fail-on", "HIGH"]
    assert Path(args[1]).is_dir()


@pytest.mark.skipif(os.name == "nt", reason="Execute hosted Ubuntu bash with a fake audit")
@pytest.mark.parametrize(
    "models", ["$(touch injected)", "model_ok;touch injected", "--offline --cache target"]
)
def test_workflow_input_cannot_become_shell_or_cli_options(workflow_runner, models):
    result, args, output = workflow_runner(models)
    assert result.returncode == 2 and output == "exit_code=2\n"
    assert args is None
    assert result.stderr == "Invalid model IDs in workflow input\n"


@pytest.mark.skipif(os.name == "nt", reason="Execute hosted Ubuntu bash with a fake audit")
def test_each_workflow_invocation_gets_a_fresh_cache(workflow_runner):
    first, args, _ = workflow_runner()
    second, other, _ = workflow_runner("  \t\n")
    assert first.returncode == second.returncode == 0
    assert "--models" not in args and "--models" not in other
    assert args[1] != other[1]
    assert not any(Path(args[1]).iterdir()) and not any(Path(other[1]).iterdir())


@pytest.mark.skipif(os.name == "nt", reason="Execute hosted Ubuntu bash with a fake reporter")
@pytest.mark.parametrize("download", ["success", "failure", "skipped", "cancelled", ""])
@pytest.mark.parametrize("artifact_id", ["71", ""])
def test_failed_download_never_passes_leftover_report_to_reporter(tmp_path, download, artifact_id):
    report = tmp_path / "workdir/api-contract/audit.md"
    report.parent.mkdir(parents=True)
    report.write_text("Untrusted incomplete or stale artifact")
    binary = tmp_path / "uv"
    arguments_file = tmp_path / "args.json"
    binary.write_text(
        f"#!{sys.executable}\nimport json, os, sys\nfrom pathlib import Path\n"
        "Path(os.environ['TEST_ARGS']).write_text(json.dumps(sys.argv[1:]))\n"
    )
    binary.chmod(0o755)
    result = subprocess.run(
        [
            "bash",
            "--noprofile",
            "--norc",
            "-eo",
            "pipefail",
            "-c",
            workflow_script("Create or update the API tracking issue"),
        ],
        cwd=tmp_path,
        env={
            **os.environ,
            "PATH": str(tmp_path) + os.pathsep + os.environ["PATH"],
            "GITHUB_REPOSITORY": "example/extension",
            "GITHUB_RUN_ID": "42",
            "GITHUB_RUN_ATTEMPT": "2",
            "AUDIT_RESULT": "failure",
            "AUDIT_EXIT_CODE": "1",
            "AUDIT_ARTIFACT_ID": artifact_id,
            "REPORT_DOWNLOAD": download,
            "TEST_ARGS": str(arguments_file),
        },
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    args = json.loads(arguments_file.read_text())
    assert ("--report" in args) == (download == "success" and bool(artifact_id))
    assert ("--artifact-id" in args) == bool(artifact_id)
    if artifact_id:
        assert args[args.index("--artifact-id") + 1] == artifact_id


@pytest.mark.parametrize("report_attempt", [2, 3])
def test_reporter_rerun_reuses_the_audit_artifact_identity(tmp_path, monkeypatch, report_attempt):
    report = tmp_path / "audit.md"
    report.write_text("Report produced by the original audit.")
    writes = []
    monkeypatch.setattr(reporter, "report_failure", lambda *args: writes.append(args) or "created")
    assert reporter.main(arguments(report) + ["--run-attempt", str(report_attempt)]) == 0
    body = writes[0][2]
    assert f"Attempt {report_attempt};" in body
    assert "Report produced by the original audit." in body
    assert "https://github.com/example/extension/actions/runs/42/artifacts/71" in body
    assert "model-payload-audit-" not in body


def test_new_audit_uses_new_artifact_identity(tmp_path, monkeypatch):
    writes = []
    monkeypatch.setattr(reporter, "report_failure", lambda *args: writes.append(args) or "created")
    assert reporter.main(arguments(tmp_path / "absent") + ["--artifact-id", "72"]) == 0
    assert "/artifacts/72" in writes[0][2]
    assert "/artifacts/71" not in writes[0][2]


def test_missing_upload_id_does_not_invent_an_artifact(tmp_path, monkeypatch):
    writes = []
    monkeypatch.setattr(reporter, "report_failure", lambda *args: writes.append(args) or "created")
    args = arguments(tmp_path / "absent")[:-4]
    assert reporter.main(args) == 0
    assert "audit upload recorded no artifact ID" in writes[0][2]
    assert "/artifacts/" not in writes[0][2]


def test_report_without_upload_identity_fails_before_file_read_or_issue_write(
    tmp_path, monkeypatch
):
    monkeypatch.setattr(reporter, "report_failure", lambda *args: pytest.fail("invalid context"))
    monkeypatch.setattr(Path, "is_file", lambda *args: pytest.fail("unidentified artifact"))
    args = arguments(tmp_path / "untrusted")
    del args[args.index("--artifact-id") : args.index("--artifact-id") + 2]
    with pytest.raises(SystemExit) as error:
        reporter.main(args)
    assert error.value.code == 2


def test_omitted_report_never_reads_leftover_files(tmp_path, monkeypatch):
    writes = []
    monkeypatch.setattr(reporter, "report_failure", lambda *args: writes.append(args) or "created")
    monkeypatch.setattr(Path, "is_file", lambda *args: pytest.fail("no artifact was authorized"))
    assert reporter.main(arguments(tmp_path / "stale")[:-2]) == 0
    assert "No report was available" in writes[0][2]
