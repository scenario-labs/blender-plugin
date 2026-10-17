# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Fail closed before hosted smoke spending; seal private recovery artifacts."""

import argparse
import json
import os
import re
import shutil
import subprocess
import tarfile
import tempfile
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from urllib.parse import quote

from tools.smoke_image import SmokeError, create_file, decimal_cost, read_bytes

REPOSITORY = "scenario-labs/blender-plugin"
ROOT = Path(__file__).resolve().parents[1]
# The scheduled run always uses this committed plan and total cap (#40). Change
# either one only in a reviewed commit, never through repository settings.
MONTHLY_PLAN = ROOT / "tests" / "smoke" / "monthly-plan.json"
MONTHLY_MAX_CU = Decimal("40")
# Every hosted run, scheduled or dispatched, also fits this calendar-month (UTC)
# budget, set by the maintainer on 2026-10-14. Admission and the post-approval
# recheck add the requested total cap to the caps of this month's earlier runs
# whose paid job started; see monthly_reserved().
MONTHLY_BUDGET_CU = Decimal("5000")
PLANS = ("monthly", "private")
WORKFLOW = "smoke.yml"
# Environment approval waits at most 30 days, so a run created up to then can
# start its paid job in the current month.
LEDGER_LOOKBACK = timedelta(days=35)
LEDGER_PAGES = 10
# The paid job's name is the text the reviewer approved, frozen from admission
# outputs. Runs before the plan input named only the cap.
APPROVED_NAME = re.compile(
    r"Budget approval \((?:(?:monthly|private) plan, )?([0-9]{1,64}(?:\.[0-9]{1,64})?) CU total\)"
)


def check_context(environ):
    if (
        environ.get("GITHUB_REPOSITORY") != REPOSITORY
        or environ.get("GITHUB_REF") != "refs/heads/main"
        or environ.get("GITHUB_EVENT_NAME") not in {"workflow_dispatch", "schedule"}
        or environ.get("GITHUB_RUN_ATTEMPT") != "1"
    ):
        raise SmokeError("Hosted smokes require a new base-repository main dispatch or schedule")


def admission(environ, max_cu, plan):
    """Freeze one plan and total cap; a schedule ignores inputs and uses the monthly budget."""
    if environ.get("GITHUB_EVENT_NAME") == "schedule":
        return "monthly", MONTHLY_MAX_CU
    if plan not in PLANS:
        raise SmokeError("Choose the monthly or private smoke plan")
    cap = decimal_cost(max_cu)
    if cap <= 0:
        raise SmokeError("Authorize a positive aggregate budget before execution", 3)
    if cap > MONTHLY_BUDGET_CU:
        raise SmokeError("The total cap exceeds the monthly smoke budget", 3)
    return plan, cap


def validate_gate(environment, branches):
    policy = environment.get("deployment_branch_policy")
    rules = environment.get("protection_rules", [])
    if (
        environment.get("name") != "smoke"
        or policy != {"protected_branches": False, "custom_branch_policies": True}
        or not any(
            rule.get("type") == "required_reviewers" and rule.get("reviewers") for rule in rules
        )
        or branches.get("total_count") != 1
        or [(branch.get("name"), branch.get("type")) for branch in branches["branch_policies"]]
        != [("main", "branch")]
    ):
        raise SmokeError("Configure smoke required reviewers and exactly the main branch policy")


def gh_json(path):
    result = subprocess.run(["gh", "api", path], capture_output=True, check=True, timeout=30)
    return json.loads(result.stdout)


def check_gate(environ):
    check_context(environ)
    endpoint = f"repos/{REPOSITORY}/environments/smoke"
    validate_gate(gh_json(endpoint), gh_json(endpoint + "/deployment-branch-policies?per_page=100"))
    print("Verified smoke reviewers and main-only deployment policy")


def paged(path, key):
    """Every item of a paginated list; an incomplete listing fails closed."""
    items = []
    for page in range(1, LEDGER_PAGES + 1):
        body = gh_json(f"{path}&per_page=100&page={page}")
        batch = body[key]
        items += batch
        if len(items) >= body["total_count"]:
            return items
        if not batch:
            break
    raise SmokeError("Could not read the complete smoke run history")


def started_this_month(job, month):
    """Whether a paid job passed approval and started in this month; unknown counts."""
    if job.get("conclusion") == "skipped":
        return False
    times = [step["started_at"] for step in job.get("steps") or [] if step.get("started_at")]
    if times:
        return min(datetime.fromisoformat(value.replace("Z", "+00:00")) for value in times) >= month
    # A runner without step times, a running job or one that approval can start
    # at any moment counts; one rejected, cancelled or expired at approval does not.
    return job.get("status") in {"in_progress", "waiting"} or bool(job.get("runner_name"))


def reservation(job):
    match = APPROVED_NAME.fullmatch(job.get("name") or "")
    # A started paid job without a readable cap consumes the whole budget.
    return decimal_cost(match.group(1)) if match else MONTHLY_BUDGET_CU


def monthly_reserved(environ, now=None):
    """Sum the approved total caps of this month's other runs whose paid job started.

    Reserved caps bound actual spending from above. Workflow concurrency runs
    one run at a time, and each paid job rechecks after approval while it is
    itself in progress, so of two overlapping runs the later one counts the other.
    """
    now = now or datetime.now(UTC)
    month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    current = environ.get("GITHUB_RUN_ID", "")
    if not current.isdigit():
        raise SmokeError("Hosted smokes require the current workflow run identity")
    since = quote(">=" + (month - LEDGER_LOOKBACK).date().isoformat())
    runs = paged(
        f"repos/{REPOSITORY}/actions/workflows/{WORKFLOW}/runs?created={since}", "workflow_runs"
    )
    total = Decimal(0)
    for run in runs:
        if str(run["id"]) == current:
            continue
        # filter=all keeps every attempt, so a rerun cannot hide a paid attempt.
        jobs = paged(f"repos/{REPOSITORY}/actions/runs/{run['id']}/jobs?filter=all", "jobs")
        for job in jobs:
            if job.get("name") != "gate" and started_this_month(job, month):
                total += reservation(job)
    return total


def check_ledger(environ, cap, now=None):
    reserved = monthly_reserved(environ, now)
    if reserved + cap > MONTHLY_BUDGET_CU:
        raise SmokeError("This total cap would exceed the monthly smoke budget", 3)
    print(
        f"Monthly smoke ledger: {reserved:f} CU reserved this month, {cap:f} CU requested,"
        f" {MONTHLY_BUDGET_CU:f} CU budget"
    )


def passphrase(environ):
    value = environ.get("SMOKE_RECOVERY_PASSPHRASE", "")
    if len(value) < 32 or any(char in value for char in "\r\n\x00"):
        raise SmokeError("Configure a recovery passphrase of at least 32 characters")
    if not shutil.which("gpg") or not shutil.which("gpgconf"):
        raise SmokeError("Install GnuPG before running hosted smokes")
    return value.encode() + b"\n"


def crypt(source, destination, secret, *, decrypt=False):
    with tempfile.TemporaryDirectory(prefix="smoke-gpg-") as directory:
        command = [
            "gpg",
            "--no-options",
            "--homedir",
            directory,
            "--batch",
            "--pinentry-mode",
            "loopback",
            "--no-symkey-cache",
            "--passphrase-fd",
            "0",
            "--output",
            str(destination),
        ]
        if decrypt:
            command += ["--decrypt", str(source)]
        else:
            command += ["--symmetric", "--cipher-algo", "AES256", "--force-mdc", str(source)]
        child_env = {
            key: os.environ[key]
            for key in ("PATH", "SystemRoot", "WINDIR", "TEMP", "TMP", "TMPDIR")
            if key in os.environ
        }
        try:
            subprocess.run(
                command, input=secret, capture_output=True, check=True, timeout=120, env=child_env
            )
        finally:
            # Only this private home owns the agent; never stop the user's agent.
            subprocess.run(
                ["gpgconf", "--homedir", directory, "--kill", "gpg-agent"],
                capture_output=True,
                check=True,
                timeout=10,
                env=child_env,
            )


def plan_bytes(plan, environ):
    if environ.get("GITHUB_EVENT_NAME") == "schedule" and plan != "monthly":
        raise SmokeError("Scheduled smokes run only the committed monthly plan")
    if plan == "monthly":
        return read_bytes(MONTHLY_PLAN)
    if plan != "private":
        raise SmokeError("Choose the monthly or private smoke plan")
    raw = environ.get("SMOKE_PLAN_JSON", "").encode()
    if not raw or len(raw) > 1024 * 1024:
        raise SmokeError("Configure a private smoke plan of at most 1 MiB")
    return raw


def prepare(root, environ, plan="private"):
    check_context(environ)
    secret = passphrase(environ)
    # Test encryption AND recovery before permitting any Scenario request.
    with tempfile.TemporaryDirectory(prefix="smoke-encryption-check-") as directory:
        path = Path(directory)
        (path / "plain").write_bytes(b"smoke recovery round trip\n")
        crypt(path / "plain", path / "sealed", secret)
        crypt(path / "sealed", path / "restored", secret, decrypt=True)
        if (path / "restored").read_bytes() != (path / "plain").read_bytes():
            raise SmokeError("Recovery encryption self-check failed")
    raw = plan_bytes(plan, environ)
    if root.absolute() != root.resolve():
        raise SmokeError("Private smoke storage must not use symbolic links")
    root.mkdir(mode=0o700)
    create_file(root / "plan.json", raw)


def seal(root, output, environ):
    secret = passphrase(environ)
    if root.absolute() != root.resolve() or not root.is_dir():
        raise SmokeError("Keep the original private smoke directory for recovery")
    output = output.absolute()
    if output.exists() or output != output.resolve() or output.is_relative_to(root.resolve()):
        raise SmokeError("Use a new encrypted archive outside the private run directory")
    paths = list(root.rglob("*"))
    if any(path.is_symlink() or not (path.is_file() or path.is_dir()) for path in paths):
        raise SmokeError("Recovery archives cannot contain links or special files")
    with tempfile.TemporaryDirectory(prefix="smoke-archive-") as directory:
        source = Path(directory) / "recovery.tar"
        with tarfile.open(source, "w") as archive:
            archive.add(root, arcname="smoke", recursive=True)
        crypt(source, output, secret)
    print("Encrypted recovery archive created; do not publish its passphrase or decrypted contents")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    gate = commands.add_parser("gate")
    # Admission passes both raw inputs; they are empty on a schedule. The
    # post-approval recheck passes only the frozen cap and freezes nothing.
    gate.add_argument("--max-cu")
    gate.add_argument("--plan")
    gate.add_argument("--recheck-cu")
    for command in ("prepare", "seal"):
        item = commands.add_parser(command)
        item.add_argument("--root", type=Path, required=True)
        if command == "prepare":
            item.add_argument("--plan", choices=PLANS, required=True)
        if command == "seal":
            item.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == "gate":
            if args.recheck_cu is not None:
                if args.max_cu is not None or args.plan is not None:
                    raise SmokeError("Recheck only the cap frozen by admission")
                plan, cap = None, decimal_cost(args.recheck_cu)
                if cap <= 0:
                    raise SmokeError("Recheck a positive frozen cap", 3)
            else:
                plan, cap = admission(os.environ, args.max_cu, args.plan)
            check_gate(os.environ)
            check_ledger(os.environ, cap)
            if plan is not None:
                with Path(os.environ["GITHUB_OUTPUT"]).open("a") as output:
                    output.write(f"max_cu={cap:f}\nplan={plan}\n")
                print(f"Admitted the {plan} smoke plan with a {cap:f} CU total cap")
        elif args.command == "prepare":
            prepare(args.root, os.environ, args.plan)
        else:
            seal(args.root, args.output, os.environ)
        return 0
    except Exception:
        print("Hosted smoke safety check failed; inspect private configuration without printing it")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
