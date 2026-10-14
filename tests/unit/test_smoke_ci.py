# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Protected workflow admission and real encrypted recovery artifact coverage."""

import copy
import json
import shutil
import subprocess
import tarfile
from datetime import UTC, datetime
from decimal import Decimal
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


@pytest.mark.parametrize(
    "arguments",
    [
        ["--max-cu", "0", "--plan", "monthly"],
        ["--max-cu", "", "--plan", "monthly"],
        ["--max-cu", "40", "--plan", "other"],
        ["--max-cu", "40"],
        ["--plan", "private"],
        ["--max-cu", "5000.01", "--plan", "private"],
        [],
        ["--recheck-cu", "0"],
        ["--recheck-cu", "40", "--plan", "monthly"],
    ],
)
def test_dispatch_without_a_positive_cap_and_known_plan_stops_before_github_read(
    monkeypatch, arguments
):
    monkeypatch.setenv("GITHUB_EVENT_NAME", "workflow_dispatch")
    monkeypatch.setattr(ci, "check_gate", lambda env: pytest.fail("Gate read with no budget"))
    monkeypatch.setattr(ci, "gh_json", lambda path: pytest.fail("Ledger read with no budget"))
    assert ci.main(["gate", *arguments]) == 2


def test_validated_cap_output_cannot_change_between_gate_and_approval(monkeypatch, tmp_path):
    output = tmp_path / "outputs"
    monkeypatch.setenv("GITHUB_OUTPUT", str(output))
    monkeypatch.setenv("GITHUB_EVENT_NAME", "workflow_dispatch")
    monkeypatch.setattr(ci, "check_gate", lambda env: None)
    monkeypatch.setattr(ci, "check_ledger", lambda env, cap: None)
    assert ci.main(["gate", "--max-cu", "12.345678901234567890123456789", "--plan", "private"]) == 0
    assert output.read_text() == "max_cu=12.345678901234567890123456789\nplan=private\n"
    workflow = (ROOT / ".github/workflows/smoke.yml").read_text()
    protected = workflow.split("\n  smoke:\n", 1)[1]
    assert protected.count("needs.gate.outputs.max_cu") == 3
    assert protected.count("needs.gate.outputs.plan") == 3
    assert "vars.SMOKE_MAX_TOTAL_CU" not in workflow
    assert "inputs.max_cu" not in protected
    assert "inputs.plan" not in protected


@pytest.mark.parametrize(
    "arguments", [["--max-cu", "", "--plan", ""], ["--max-cu", "1000", "--plan", "private"]]
)
def test_schedule_always_freezes_the_committed_monthly_plan_and_cap(
    monkeypatch, tmp_path, arguments
):
    output = tmp_path / "outputs"
    monkeypatch.setenv("GITHUB_OUTPUT", str(output))
    monkeypatch.setenv("GITHUB_EVENT_NAME", "schedule")
    monkeypatch.setattr(ci, "check_gate", lambda env: None)
    caps = []
    monkeypatch.setattr(ci, "check_ledger", lambda env, cap: caps.append(cap))
    assert ci.main(["gate", *arguments]) == 0
    assert output.read_text() == "max_cu=40\nplan=monthly\n"
    assert caps == [ci.MONTHLY_MAX_CU]


def test_post_approval_recheck_checks_the_ledger_and_freezes_nothing(monkeypatch, tmp_path):
    monkeypatch.setenv("GITHUB_OUTPUT", str(tmp_path / "outputs"))
    monkeypatch.setattr(ci, "check_gate", lambda env: None)
    caps = []
    monkeypatch.setattr(ci, "check_ledger", lambda env, cap: caps.append(cap))
    assert ci.main(["gate", "--recheck-cu", "249.50"]) == 0
    assert caps == [Decimal("249.50")]
    assert not (tmp_path / "outputs").exists()


def test_ledger_refusal_writes_no_admission_output(monkeypatch, tmp_path):
    output = tmp_path / "outputs"
    monkeypatch.setenv("GITHUB_OUTPUT", str(output))
    monkeypatch.setenv("GITHUB_EVENT_NAME", "workflow_dispatch")
    monkeypatch.setenv("GITHUB_RUN_ID", "900")
    monkeypatch.setattr(ci, "check_gate", lambda env: None)
    monkeypatch.setattr(ci, "monthly_reserved", lambda env, now=None: Decimal("4990"))
    assert ci.main(["gate", "--max-cu", "10.01", "--plan", "monthly"]) == 2
    assert not output.exists()
    assert ci.main(["gate", "--recheck-cu", "10.01"]) == 2
    assert ci.main(["gate", "--max-cu", "10", "--plan", "monthly"]) == 0
    assert output.read_text() == "max_cu=10\nplan=monthly\n"


NOW = datetime(2026, 10, 14, 12, tzinfo=UTC)
RUNS_PATH = (
    f"repos/{ci.REPOSITORY}/actions/workflows/smoke.yml/runs?created=%3E%3D2026-08-27"
    "&per_page=100&page=1"
)


def step(started="2026-10-09T14:48:48Z"):
    return {"name": "Set up job", "started_at": started}


def paid(name, *, status="completed", conclusion="success", steps=None, runner=None):
    return {
        "name": name,
        "status": status,
        "conclusion": conclusion,
        "steps": [step()] if steps is None else steps,
        "runner_name": runner,
    }


GATE = paid("gate")


def ledger_api(monkeypatch, runs, paths=None):
    """Answer gh api reads from synthetic run/job listings, never the network."""

    def read(path):
        if paths is not None:
            paths.append(path)
        if path == RUNS_PATH:
            listing = [{"id": run_id} for run_id in runs]
            return {"total_count": len(listing), "workflow_runs": listing}
        prefix = f"repos/{ci.REPOSITORY}/actions/runs/"
        run_id, suffix = path.removeprefix(prefix).split("/", 1)
        assert suffix == "jobs?filter=all&per_page=100&page=1"
        return {"total_count": len(runs[int(run_id)]), "jobs": runs[int(run_id)]}

    monkeypatch.setattr(ci, "gh_json", read)


def test_monthly_budget_is_the_maintainer_decision_and_covers_the_schedule():
    assert ci.MONTHLY_BUDGET_CU == Decimal("5000")
    assert 0 < ci.MONTHLY_MAX_CU <= ci.MONTHLY_BUDGET_CU


def test_ledger_sums_this_months_started_paid_jobs_only(monkeypatch):
    paths = []
    ledger_api(
        monkeypatch,
        {
            # Current plan-and-cap name, and the earlier cap-only name.
            1: [GATE, paid("Budget approval (monthly plan, 40 CU total)")],
            2: [GATE, paid("Budget approval (249.50 CU total)")],
            # Gate failure or another branch skips the paid job.
            3: [
                paid("gate", conclusion="failure"),
                paid("Budget approval ( plan,  CU total)", conclusion="skipped", steps=[]),
            ],
            # Rejected, cancelled or expired at approval: no runner, no steps.
            4: [
                GATE,
                paid(
                    "Budget approval (private plan, 900 CU total)", conclusion="failure", steps=[]
                ),
            ],
            # Created last month but approved and started this month.
            5: [
                GATE,
                paid(
                    "Budget approval (private plan, 100 CU total)",
                    steps=[step("2026-10-01T00:00:00Z")],
                ),
            ],
            # Started last month.
            6: [
                GATE,
                paid(
                    "Budget approval (private plan, 700 CU total)",
                    steps=[step("2026-09-30T23:59:59Z")],
                ),
            ],
            # The current run never counts itself.
            900: [
                GATE,
                paid(
                    "Budget approval (private plan, 3000 CU total)",
                    status="in_progress",
                    conclusion=None,
                ),
            ],
        },
        paths,
    )
    assert ci.monthly_reserved({"GITHUB_RUN_ID": "900"}, NOW) == Decimal("389.50")
    assert paths[0] == RUNS_PATH
    assert all("filter=all" in path for path in paths[1:])
    assert not any("/runs/900/" in path for path in paths)


@pytest.mark.parametrize(
    "job",
    [
        # Awaiting approval elsewhere: it can start at any moment.
        paid(
            "Budget approval (private plan, 300 CU total)",
            status="waiting",
            conclusion=None,
            steps=[],
        ),
        paid(
            "Budget approval (private plan, 300 CU total)",
            status="in_progress",
            conclusion=None,
            steps=[],
        ),
        paid("Budget approval (private plan, 300 CU total)", steps=[], runner="runner"),
    ],
)
def test_ledger_counts_unfinished_or_untimed_paid_jobs_this_month(monkeypatch, job):
    ledger_api(monkeypatch, {7: [GATE, job]})
    assert ci.monthly_reserved({"GITHUB_RUN_ID": "900"}, NOW) == Decimal("300")


@pytest.mark.parametrize(
    "name", ["Smoke", "Budget approval (${{ needs.gate.outputs.max_cu }} CU total)", None]
)
def test_started_paid_job_without_a_readable_cap_consumes_the_whole_budget(monkeypatch, name):
    ledger_api(monkeypatch, {8: [GATE, paid(name)]})
    assert ci.monthly_reserved({"GITHUB_RUN_ID": "900"}, NOW) == ci.MONTHLY_BUDGET_CU
    with pytest.raises(SmokeError, match="monthly smoke budget"):
        ci.check_ledger({"GITHUB_RUN_ID": "900"}, Decimal("0.01"), NOW)


def test_ledger_admits_exactly_the_remaining_budget(monkeypatch, capsys):
    ledger_api(monkeypatch, {9: [GATE, paid("Budget approval (private plan, 4960 CU total)")]})
    ci.check_ledger({"GITHUB_RUN_ID": "900"}, Decimal("40"), NOW)
    assert "4960 CU reserved" in capsys.readouterr().out
    with pytest.raises(SmokeError) as refused:
        ci.check_ledger({"GITHUB_RUN_ID": "900"}, Decimal("40.01"), NOW)
    assert refused.value.code == 3


def test_ledger_reads_every_page_and_fails_closed_on_an_incomplete_listing(monkeypatch):
    runs = [{"id": run_id} for run_id in range(1, 151)]
    pages = {1: runs[:100], 2: runs[100:]}

    def read(path):
        if "/workflows/" in path:
            page = int(path.rsplit("page=", 1)[1])
            return {"total_count": 150, "workflow_runs": pages.get(page, [])}
        return {"total_count": 1, "jobs": [paid("Budget approval (private plan, 1 CU total)")]}

    monkeypatch.setattr(ci, "gh_json", read)
    assert ci.monthly_reserved({"GITHUB_RUN_ID": "900"}, NOW) == Decimal("150")
    pages[2] = []
    with pytest.raises(SmokeError, match="complete smoke run history"):
        ci.monthly_reserved({"GITHUB_RUN_ID": "900"}, NOW)


@pytest.mark.parametrize("run_id", ["", "not-a-run"])
def test_ledger_requires_the_current_run_identity(monkeypatch, run_id):
    monkeypatch.setattr(ci, "gh_json", lambda path: pytest.fail("Ledger read without identity"))
    with pytest.raises(SmokeError, match="run identity"):
        ci.monthly_reserved({"GITHUB_RUN_ID": run_id}, NOW)


def test_ledger_api_failure_fails_closed(monkeypatch):
    monkeypatch.setattr(
        ci.subprocess,
        "run",
        lambda *args, **kwargs: (_ for _ in ()).throw(subprocess.CalledProcessError(1, "gh")),
    )
    with pytest.raises(subprocess.CalledProcessError):
        ci.check_ledger({"GITHUB_RUN_ID": "900"}, Decimal("40"), NOW)


def test_plan_selection_reads_the_committed_plan_or_the_private_secret():
    environ = {**CONTEXT, "SMOKE_PLAN_JSON": '{"private":"plan-marker"}'}
    assert ci.plan_bytes("monthly", environ) == ci.MONTHLY_PLAN.read_bytes()
    assert ci.plan_bytes("private", environ) == b'{"private":"plan-marker"}'
    with pytest.raises(SmokeError, match="private smoke plan"):
        ci.plan_bytes("private", CONTEXT)
    with pytest.raises(SmokeError, match="monthly or private"):
        ci.plan_bytes("other", environ)
    with pytest.raises(SmokeError, match="only the committed monthly plan"):
        ci.plan_bytes("private", {**environ, "GITHUB_EVENT_NAME": "schedule"})


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
    ci.prepare(root, environ, "private")
    job = root / "suite" / "image"
    job.mkdir(parents=True)
    (job / "scope.key").write_bytes(b"synthetic scope key")
    (job / "jobs.sqlite3").write_bytes(b"synthetic private job id marker")
    inputs = root / "suite-inputs"
    inputs.mkdir()
    (inputs / "source.bin").write_bytes(b"private staged input marker")
    (inputs / "inputs.json").write_bytes(b"private upload binding marker")
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
        assert (
            saved.extractfile("smoke/suite-inputs/source.bin").read()
            == b"private staged input marker"
        )
        assert (
            saved.extractfile("smoke/suite-inputs/inputs.json").read()
            == b"private upload binding marker"
        )
    with pytest.raises(subprocess.CalledProcessError):
        ci.crypt(sealed, tmp_path / "wrong.tar", b"wrong test phrase\n", decrypt=True)
    assert SECRET not in capsys.readouterr().out


@pytest.mark.skipif(
    shutil.which("gpg") is None, reason="GnuPG is required on the hosted smoke runner"
)
def test_scheduled_preparation_stores_the_committed_monthly_plan(tmp_path):
    root = tmp_path / "private"
    environ = {
        **CONTEXT,
        "GITHUB_EVENT_NAME": "schedule",
        "SMOKE_RECOVERY_PASSPHRASE": SECRET,
        "SMOKE_PLAN_JSON": '{"private":"plan-marker"}',
    }
    with pytest.raises(SmokeError, match="monthly"):
        ci.prepare(root, environ, "private")
    assert not root.exists()
    ci.prepare(root, environ, "monthly")
    assert (root / "plan.json").read_bytes() == ci.MONTHLY_PLAN.read_bytes()


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
    assert 'smoke_ci gate --recheck-cu "$MAX_TOTAL_CU"' in workflow
    assert workflow.count('cron: "0 6 1 * *"') == 1
    assert 'default: "40"' in workflow and "default: monthly" in workflow
    # Only an explicitly selected private plan receives the private plan secret.
    assert workflow.count("secrets.SMOKE_PLAN_JSON") == 1
    assert (
        "SMOKE_PLAN_JSON: ${{ needs.gate.outputs.plan == 'private' && secrets.SMOKE_PLAN_JSON"
        in workflow
    )
    assert workflow.index("smoke_ci prepare") < workflow.index("smoke_suite budget-run")
    assert '--upload-inputs --input-root "$GITHUB_WORKSPACE"' in workflow
    assert "path: ${{ runner.temp }}/smoke-recovery.gpg" in workflow
    assert "retention-days: 7" in workflow
    assert "persist-credentials: true" not in workflow
    # Both gate reads use a read-only Actions token, without admin privileges.
    assert workflow.count("actions: read") == 2
    assert ": write" not in workflow
