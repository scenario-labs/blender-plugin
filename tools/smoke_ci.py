# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Fail closed before hosted smoke spending; seal private recovery artifacts."""

import argparse
import json
import os
import shutil
import subprocess
import tarfile
import tempfile
from decimal import Decimal
from pathlib import Path

from tools.smoke_image import SmokeError, create_file, decimal_cost, read_bytes

REPOSITORY = "scenario-labs/blender-plugin"
ROOT = Path(__file__).resolve().parents[1]
# The scheduled run always uses this committed plan and total cap (#40). Change
# either one only in a reviewed commit, never through repository settings.
MONTHLY_PLAN = ROOT / "tests" / "smoke" / "monthly-plan.json"
MONTHLY_MAX_CU = Decimal("40")
PLANS = ("monthly", "private")


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


def check_gate(environ):
    check_context(environ)
    endpoint = f"repos/{REPOSITORY}/environments/smoke"

    def read(suffix):
        result = subprocess.run(
            ["gh", "api", endpoint + suffix], capture_output=True, check=True, timeout=30
        )
        return json.loads(result.stdout)

    validate_gate(read(""), read("/deployment-branch-policies?per_page=100"))
    print("Verified smoke reviewers and main-only deployment policy")


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
    # post-approval recheck passes neither and freezes nothing.
    gate.add_argument("--max-cu")
    gate.add_argument("--plan")
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
            frozen = None
            if args.max_cu is not None or args.plan is not None:
                frozen = admission(os.environ, args.max_cu, args.plan)
            check_gate(os.environ)
            if frozen is not None:
                plan, cap = frozen
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
