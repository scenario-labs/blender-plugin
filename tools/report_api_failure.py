# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Report a scheduled schema-audit failure without assuming all failures are drift."""

import argparse
import html
import re
import subprocess
import sys
from pathlib import Path

from tools.report_ci_failure import report_failure

TITLE = "api: model schema drift detected by the weekly contract check"
LIMIT = 50000


def diagnosis(exit_code):
    if exit_code == "1":
        return "The audit found a HIGH schema finding or a fetch/schema/cache failure."
    if exit_code == "2":
        return (
            "The audit could not complete cleanly: inspect credentials, configuration, "
            "report output or cache cleanup."
        )
    if exit_code == "0":
        return "The audit passed; inspect later workflow steps such as artifact preservation."
    if not exit_code:
        return "No audit exit code was recorded; inspect setup, runner timeout or interruption."
    return f"The audit process exited unexpectedly with status {exit_code}; inspect the run log."


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repository", required=True)
    parser.add_argument("--run-id", type=int, required=True)
    parser.add_argument("--run-attempt", type=int, required=True)
    parser.add_argument(
        "--job-result", choices=("success", "failure", "cancelled", "skipped"), required=True
    )
    parser.add_argument("--audit-exit-code", default="")
    parser.add_argument("--artifact-id", help="Exact artifact ID returned by the audit upload")
    parser.add_argument("--report", type=Path, help="Report from a successful artifact download")
    args = parser.parse_args(argv)
    if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", args.repository) or any(
        part in {".", ".."} for part in args.repository.split("/")
    ):
        parser.error("--repository must be an owner/repository name")
    if args.run_id < 1 or args.run_attempt < 1:
        parser.error("--run-id and --run-attempt must be positive")
    if args.artifact_id is not None and not re.fullmatch(r"[1-9][0-9]{0,19}", args.artifact_id):
        parser.error("--artifact-id must be one positive integer")
    if args.report is not None and args.artifact_id is None:
        parser.error("--report requires the audit upload's --artifact-id")
    code = args.audit_exit_code
    if code and (not re.fullmatch(r"\d{1,3}", code) or int(code) > 255):
        parser.error("--audit-exit-code must be empty or a process exit status")
    if args.job_result == "success" and code == "0":
        return 0
    url = f"https://github.com/{args.repository}/actions/runs/{args.run_id}"
    body = (
        f"The API contract workflow failed: {url}.\n\n"
        f"Attempt {args.run_attempt}; audit job result: `{args.job_result}`. "
        "Partial reruns can retain an earlier audit job result. "
        f"{diagnosis(code)}\n\n"
    )
    try:
        if args.report is not None and args.report.is_symlink():
            raise ValueError("Expected a regular retained report")
        if args.report is not None and args.report.is_file():
            with args.report.open(encoding="utf-8") as source:
                report = source.read(LIMIT + 1)
            # Treat schema-derived text as literal content, never Markdown/HTML
            # instructions, mentions or commands. Bound the escaped issue body too.
            escaped = html.escape(report, quote=False)
            body += "<pre>" + escaped[:LIMIT] + "</pre>\n\n"
            if len(escaped) > LIMIT:
                body += "Report excerpt truncated. "
        else:
            body += "No report was available; setup, timeout or artifact download may have failed. "
        if args.artifact_id is not None:
            body += (
                f"The audit upload recorded artifact {args.artifact_id}: "
                f"{url}/artifacts/{args.artifact_id}. "
                "A reporter-only rerun retains that audit's artifact; it may expire or be deleted. "
            )
        else:
            body += "The audit upload recorded no artifact ID. "
        body += "Inspect this run before attributing the failure to model schema drift."
        outcome = report_failure(
            args.repository, TITLE, body, ["bug", "feature:API", "quality", "area:ci"]
        )
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        print(f"API failure reporting failed ({type(error).__name__}).", file=sys.stderr)
        return 1
    print(f"API tracking issue {outcome}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
