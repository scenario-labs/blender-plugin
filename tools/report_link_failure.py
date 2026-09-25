# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Create or update the scheduled link-check issue from its retained report."""

import argparse
import re
import subprocess
import sys
from pathlib import Path

from tools.report_ci_failure import report_failure


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repository", required=True)
    parser.add_argument("--run-url", required=True)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args(argv)
    if not re.fullmatch(
        rf"https://github\.com/{re.escape(args.repository)}/actions/runs/\d+", args.run_url
    ):
        parser.error("--run-url must identify a GitHub Actions run in this repository")
    body = f"Link checking failed: {args.run_url}.\n\n"
    try:
        if args.report.is_file():
            with args.report.open(encoding="utf-8") as source:
                report = source.read(50001)
            body += report[:50000]
            if len(report) > 50000:
                body += "\n\nReport truncated; the links-report artifact contains the full output."
        else:
            body += "No report was produced. Inspect the run for setup or scanner errors."
        body += "\n\nFix the reported links or triage the scan failure, then close this issue."
        outcome = report_failure(
            args.repository,
            "docs: broken or redirected links",
            body,
            ["documentation", "area:docs"],
            scope_label="area:docs",
        )
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        print(f"Link failure reporting failed ({type(error).__name__}).", file=sys.stderr)
        return 1
    print(f"Link tracking issue {outcome}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
