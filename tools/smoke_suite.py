# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Bound a reviewed model suite to one aggregate spending authorization."""

import argparse
import json
import os
import re
from decimal import Decimal, localcontext
from pathlib import Path
from types import SimpleNamespace

from tools import smoke_image as model
from tools.dev_config import live_settings

NAME = re.compile(r"[a-z][a-z0-9_-]{0,39}")
SHA256 = re.compile(r"[a-f0-9]{64}")
MAX_CASES = 8


def cases(value):
    if not isinstance(value, list) or not 1 <= len(value) <= MAX_CASES:
        raise model.SmokeError("Use one to eight distinct model cases")
    names = []
    for case in value:
        name = case.get("name") if isinstance(case, dict) else None
        if not isinstance(name, str) or not NAME.fullmatch(name) or name in names:
            raise model.SmokeError("Use distinct lowercase case names without paths")
        names.append(name)
    return value


def total_cost(values):
    # Each input is bounded to 64 integer and 64 fraction digits by decimal_cost.
    # Do not round approval totals using Decimal's default 28-digit context.
    with localcontext() as context:
        context.prec = 256
        return sum((model.decimal_cost(value) for value in values), Decimal(0))


def quote(args, settings, execute):
    plan = json.loads(model.read_bytes(args.plan))
    if not isinstance(plan, dict) or set(plan) != {"schema_version", "project_id", "cases"}:
        raise model.SmokeError("Plan requires schema_version, explicit project_id and cases")
    if plan["schema_version"] != 1 or plan["project_id"] != settings.project_id:
        raise model.SmokeError("Plan version or selected test project does not match")
    entries = cases(plan["cases"])
    for case in entries:
        if (
            set(case) != {"name", "result_kind", "model", "parameters"}
            or case["result_kind"] not in model.RESULT_KINDS
            or not isinstance(case["model"], str)
            or not case["model"].strip()
            or not isinstance(case["parameters"], dict)
        ):
            raise model.SmokeError("Each case requires a model, result kind and input object")
        model.json_bytes(case)
    root = args.run_dir
    root.mkdir(mode=0o700)
    model.sync_directory(root.parent)
    approved = []
    for case in entries:
        parameters = root / (case["name"] + "-parameters.json")
        model.create_file(parameters, model.json_bytes(case["parameters"]))
        code = execute(
            SimpleNamespace(
                command="quote",
                run_dir=root / case["name"],
                result_kind=case["result_kind"],
                model=case["model"],
                parameters=parameters,
            ),
            settings,
        )
        if code:
            raise model.SmokeError("Suite quotation stopped; no generation submitted", code)
        raw = model.read_bytes(root / case["name"] / "quote.json")
        saved = json.loads(raw)
        approved.append(
            {"name": case["name"], "quote_sha256": model.digest(raw), "cost": saved["cost"]}
        )
    total = total_cost(case["cost"] for case in approved)
    manifest = {"schema_version": 1, "cases": approved, "total_cost": format(total, "f")}
    raw = model.json_bytes(manifest)
    model.create_file(root / "suite.json", raw)
    print(f"Suite exact total: {total} CU")
    print(f"Suite approval SHA-256: {model.digest(raw)}")
    return raw


def inspect(root):
    raw = model.read_bytes(root / "suite.json")
    manifest = json.loads(raw)
    if (
        not isinstance(manifest, dict)
        or set(manifest) != {"schema_version", "cases", "total_cost"}
        or manifest["schema_version"] != 1
    ):
        raise model.SmokeError("Unsupported suite record")
    entries = cases(manifest["cases"])
    for case in entries:
        if (
            set(case) != {"name", "quote_sha256", "cost"}
            or not isinstance(case["quote_sha256"], str)
            or not SHA256.fullmatch(case["quote_sha256"])
        ):
            raise model.SmokeError("Invalid suite quote binding")
        path = root / case["name"]
        if path != path.resolve():
            raise model.SmokeError("Suite cases must not use symbolic links")
        quote_raw = model.read_bytes(path / "quote.json")
        if model.digest(quote_raw) != case["quote_sha256"]:
            raise model.SmokeError("A suite quote changed; no submission is permitted")
        saved = json.loads(quote_raw)
        if saved["cost"] != case["cost"]:
            raise model.SmokeError("A suite quote cost changed", 3)
    total = total_cost(case["cost"] for case in entries)
    if total != model.decimal_cost(manifest["total_cost"]):
        raise model.SmokeError("Suite total does not match its individual quotes", 3)
    return raw, entries, total


def submit(args, settings, execute):
    raw, entries, total = inspect(args.run_dir)
    if model.digest(raw) != args.approved_suite or total != args.approved_total:
        raise model.SmokeError("Suite contents or exact total differ from the approval", 3)
    if total > args.max_cu:
        raise model.SmokeError("Suite exceeds the aggregate cap; nothing submitted", 3)
    # Reserve the whole suite once, before any individual paid request. Failures
    # leave this marker even when a later case never starts. Recovery cannot spend.
    try:
        model.create_file(args.run_dir / "suite-attempt", b"Never repeat this suite submission.\n")
    except FileExistsError:
        raise model.SmokeError(
            "Suite submission was attempted; resume or inspect instead", 4
        ) from None
    for index, case in enumerate(entries, 1):
        print(f"Suite case {index}")
        cost = model.decimal_cost(case["cost"])
        code = execute(
            SimpleNamespace(
                command="submit",
                run_dir=args.run_dir / case["name"],
                approved_quote=case["quote_sha256"],
                approved_cost=cost,
                max_cu=cost,
                expected_result_kind=None,
                timeout=args.timeout,
            ),
            settings,
        )
        if code:
            return code
    return 0


def resume(args, settings, execute):
    _, entries, _ = inspect(args.run_dir)
    outcome = 0
    for index, case in enumerate(entries, 1):
        root = args.run_dir / case["name"]
        if not (root / "submission-attempt").is_file():
            print(f"Suite case {index}: not attempted; review required")
            outcome = outcome or 4
            continue
        code = execute(
            SimpleNamespace(
                command="resume", run_dir=root, expected_result_kind=None, timeout=args.timeout
            ),
            settings,
        )
        outcome = outcome or code
    return outcome


def run(args, settings, *, execute=model.execute):
    root = args.run_dir.absolute()
    if root != root.resolve() or (root.exists() and not root.is_dir()):
        raise model.SmokeError("Use a private suite directory without symbolic links")
    args.run_dir = root
    if args.command in {"quote", "budget-run"}:
        if args.command == "budget-run" and args.max_cu <= 0:
            raise model.SmokeError(
                "Budget-authorized execution requires a positive explicit cap", 3
            )
        raw = quote(args, settings, execute)
        if args.command == "quote":
            return 0
        # This mode is only for separately authorized automation. Exact saved
        # quotes still bind every request; a fresh price change refuses dispatch.
        args.approved_suite = model.digest(raw)
        args.approved_total = model.decimal_cost(json.loads(raw)["total_cost"])
        return submit(args, settings, execute)
    if args.command == "submit":
        return submit(args, settings, execute)
    return resume(args, settings, execute)


def parser():
    result = argparse.ArgumentParser(description=__doc__)
    commands = result.add_subparsers(dest="command", required=True)
    for command in ("quote", "submit", "resume", "budget-run"):
        item = commands.add_parser(command)
        item.add_argument("--run-dir", type=Path, required=True)
        if command in {"quote", "budget-run"}:
            item.add_argument("--plan", type=Path, required=True)
        if command != "quote":
            item.add_argument("--timeout", type=int, default=300, choices=range(1, 3601))
        if command in {"submit", "budget-run"}:
            item.add_argument("--max-cu", type=model.decimal_cost, required=True)
        if command == "submit":
            item.add_argument("--approved-suite", required=True)
            item.add_argument("--approved-total", type=model.decimal_cost, required=True)
    return result


def main(argv=None):
    args = parser().parse_args(argv)
    if args.command in {"submit", "budget-run"} and os.environ.get("SCENARIO_SMOKE") != "1":
        print("Set SCENARIO_SMOKE=1 only after project and budget authorization")
        return 2
    try:
        return run(args, live_settings())
    except model.SmokeError as error:
        print(str(error))
        return error.code
    except SystemExit:
        print("Configure the explicit test API-key pair before running this command")
        return 2
    except Exception:
        print("Suite stopped; preserve its private directory and review before any new spending")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
