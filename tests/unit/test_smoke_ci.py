# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Protected workflow admission and real encrypted recovery artifact coverage."""

import copy
import json
import shutil
import subprocess
import tarfile
from pathlib import Path
from types import SimpleNamespace

import pytest

from tools import smoke_ci as ci
from tools.smoke_image import SmokeError

CONTEXT = {
    "GITHUB_REPOSITORY": ci.REPOSITORY,
    "GITHUB_REF": "refs/heads/main",
    "GITHUB_EVENT_NAME": "workflow_dispatch",
    "GITHUB_RUN_ATTEMPT": "1",
}
ENVIRONMENT = {
    "name": "smoke",
    "deployment_branch_policy": {"protected_branches": False, "custom_branch_policies": True},
    "protection_rules": [{"type": "required_reviewers", "reviewers": [{"type": "Team"}]}],
}
BRANCHES = {"total_count": 1, "branch_policies": [{"name": "main", "type": "branch"}]}
SECRET = "synthetic-test-recovery-phrase-with-no-live-use"
ROOT = Path(__file__).resolve().parents[2]


@pytest.mark.parametrize(
    "field,value",
    [
        ("GITHUB_REPOSITORY", "fork/repository"),
        ("GITHUB_REF", "refs/heads/feature"),
        ("GITHUB_EVENT_NAME", "pull_request"),
        ("GITHUB_RUN_ATTEMPT", "2"),
        ("GITHUB_RUN_ATTEMPT", ""),
    ],
)
def test_hosted_context_refuses_forks_branches_other_events_and_reruns(field, value):
    with pytest.raises(SmokeError):
        ci.check_context({**CONTEXT, field: value})


@pytest.mark.parametrize("event", ["workflow_dispatch", "schedule"])
def test_main_new_dispatch_and_schedule_are_admitted(event):
    ci.check_context({**CONTEXT, "GITHUB_EVENT_NAME": event})


@pytest.mark.parametrize(
    "change", ["reviewers", "empty_reviewers", "name", "branch", "extra", "tag", "all"]
)
def test_missing_or_weakened_environment_protection_is_refused(change):
    environment, branches = copy.deepcopy(ENVIRONMENT), copy.deepcopy(BRANCHES)
    if change == "reviewers":
        environment["protection_rules"] = []
    elif change == "empty_reviewers":
        environment["protection_rules"][0]["reviewers"] = []
    elif change == "name":
        environment["name"] = "other"
    elif change == "all":
        environment["deployment_branch_policy"] = None
    elif change == "extra":
        branches["total_count"] = 2
    else:
        branches["branch_policies"][0]["name" if change == "branch" else "type"] = (
            "*" if change == "branch" else "tag"
        )
    with pytest.raises(SmokeError):
        ci.validate_gate(environment, branches)


def test_gate_reads_only_environment_and_exact_branch_policy(monkeypatch):
    calls = []

    def run(command, **kwargs):
        calls.append(command)
        value = BRANCHES if "deployment-branch-policies" in command[-1] else ENVIRONMENT
        return SimpleNamespace(stdout=json.dumps(value).encode())

    monkeypatch.setattr(ci.subprocess, "run", run)
    ci.check_gate(CONTEXT)
    assert calls == [
        ["gh", "api", f"repos/{ci.REPOSITORY}/environments/smoke"],
        [
            "gh",
            "api",
            f"repos/{ci.REPOSITORY}/environments/smoke/deployment-branch-policies?per_page=100",
        ],
    ]


def test_absent_environment_stops_the_gate_without_mutation(monkeypatch):
    monkeypatch.setattr(
        ci.subprocess,
        "run",
        lambda *args, **kwargs: (_ for _ in ()).throw(subprocess.CalledProcessError(1, "gh")),
    )
    with pytest.raises(subprocess.CalledProcessError):
        ci.check_gate(CONTEXT)


def test_zero_cap_stops_before_github_read_or_service_setup(monkeypatch):
    monkeypatch.setattr(ci, "check_gate", lambda env: pytest.fail("Gate read with no budget"))
    assert ci.main(["gate", "--max-cu", "0"]) == 2


def test_validated_cap_output_cannot_change_between_gate_and_approval(monkeypatch, tmp_path):
    output = tmp_path / "outputs"
    monkeypatch.setenv("GITHUB_OUTPUT", str(output))
    monkeypatch.setattr(ci, "check_gate", lambda env: None)
    assert ci.main(["gate", "--max-cu", "12.345678901234567890123456789"]) == 0
    assert output.read_text() == "max_cu=12.345678901234567890123456789\n"
    workflow = (ROOT / ".github/workflows/smoke.yml").read_text()
    protected = workflow.split("\n  smoke:\n", 1)[1]
    assert protected.count("needs.gate.outputs.max_cu") == 2
    assert "vars.SMOKE_MAX_TOTAL_CU" not in protected
    assert "inputs.max_cu" not in protected


@pytest.mark.skipif(
    shutil.which("gpg") is None, reason="GnuPG is required on the hosted smoke runner"
)
def test_encrypted_recovery_round_trip_and_wrong_passphrase(tmp_path, capsys):
    root = tmp_path / "private"
    environ = {
        **CONTEXT,
        "SMOKE_RECOVERY_PASSPHRASE": SECRET,
        "SMOKE_PLAN_JSON": '{"private":"plan-marker"}',
    }
    ci.prepare(root, environ)
    job = root / "suite" / "image"
    job.mkdir(parents=True)
    (job / "scope.key").write_bytes(b"synthetic scope key")
    (job / "jobs.sqlite3").write_bytes(b"synthetic private job id marker")
    sealed = tmp_path / "recovery.gpg"
    ci.seal(root, sealed, environ)
    assert sealed.is_file()
    assert b"plan-marker" not in sealed.read_bytes()
    assert b"private job" not in sealed.read_bytes()
    archive = tmp_path / "recovered.tar"
    ci.crypt(sealed, archive, ci.passphrase(environ), decrypt=True)
    with tarfile.open(archive) as saved:
        assert saved.extractfile("smoke/plan.json").read() == (root / "plan.json").read_bytes()
        assert saved.extractfile("smoke/suite/image/scope.key").read() == b"synthetic scope key"
        assert (
            saved.extractfile("smoke/suite/image/jobs.sqlite3").read()
            == b"synthetic private job id marker"
        )
    with pytest.raises(subprocess.CalledProcessError):
        ci.crypt(sealed, tmp_path / "wrong.tar", b"wrong test phrase\n", decrypt=True)
    assert SECRET not in capsys.readouterr().out


def test_missing_recovery_secret_blocks_before_creating_private_state(tmp_path):
    with pytest.raises(SmokeError, match="passphrase"):
        ci.prepare(tmp_path / "private", CONTEXT)
    assert not (tmp_path / "private").exists()


def test_workflow_never_spends_on_pr_or_uploads_plaintext():
    workflow = (ROOT / ".github/workflows/smoke.yml").read_text()
    assert "pull_request" not in workflow
    assert "environment: smoke" in workflow
    assert workflow.count("github.run_attempt == 1") == 2
    assert workflow.count("github.ref == 'refs/heads/main'") == 2
    assert workflow.count("github.repository == 'scenario-labs/blender-plugin'") == 2
    assert "cancel-in-progress: false" in workflow
    assert "needs: gate" in workflow
    assert workflow.count("python -m tools.smoke_ci gate") == 2
    assert workflow.index("smoke_ci prepare") < workflow.index("smoke_suite budget-run")
    assert "path: ${{ runner.temp }}/smoke-recovery.gpg" in workflow
    assert "retention-days: 7" in workflow
    assert "persist-credentials: true" not in workflow
    # Both gate reads use a read-only Actions token, without admin privileges.
    assert workflow.count("actions: read") == 2
    assert ": write" not in workflow
