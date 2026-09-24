# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""File or update one weekly Blender failure issue per operating system."""

import argparse
import json
import re
import subprocess
import sys


def github(*arguments, payload=None):
    """Use the runner's GitHub CLI token; never retry an uncertain write."""
    command = ["gh", "api", *arguments]
    if payload is not None:
        command.extend(["--input", "-"])
    result = subprocess.run(
        command,
        input=json.dumps(payload) if payload is not None else None,
        capture_output=True,
        text=True,
        check=True,
        timeout=60,
    )
    return json.loads(result.stdout)


def report_failure(repository, title, body, labels):
    """Match exact open issue titles across all pages, without search-index lag.

    The calling workflow serializes runs. Ambiguous or malformed listing results
    fail before writing; existing duplicate issues require maintainer triage.
    """
    if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repository):
        raise ValueError("Expected an owner/repository name")
    endpoint = f"repos/{repository}/issues"
    pages = github(
        endpoint,
        "--method",
        "GET",
        "--paginate",
        "--slurp",
        "-f",
        "state=open",
        "-f",
        "labels=area:ci",
        "-f",
        "per_page=100",
    )
    matches = []
    if not isinstance(pages, list) or not pages:
        raise ValueError("GitHub returned an invalid issue listing")
    for page in pages:
        if not isinstance(page, list):
            raise ValueError("GitHub returned an invalid issue page")
        for issue in page:
            if not isinstance(issue, dict) or not isinstance(issue.get("title"), str):
                raise ValueError("GitHub returned an invalid issue")
            if issue["title"] == title and "pull_request" not in issue:
                number = issue.get("number")
                if type(number) is not int or number < 1:
                    raise ValueError("GitHub returned an invalid issue number")
                matches.append(number)
    if len(matches) > 1:
        raise ValueError("Multiple open tracking issues match; consolidate them before retrying")
    if matches:
        github(f"{endpoint}/{matches[0]}/comments", payload={"body": body})
        return "commented"
    github(endpoint, payload={"title": title, "body": body, "labels": labels})
    return "created"


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repository", required=True)
    parser.add_argument("--os", required=True, choices=("macos-latest", "windows-latest"))
    parser.add_argument("--version", required=True)
    parser.add_argument("--run-url", required=True)
    args = parser.parse_args(argv)
    if not re.fullmatch(r"\d+\.\d+\.\d+", args.version):
        parser.error("--version must be a full Blender version")
    if not re.fullmatch(
        rf"https://github\.com/{re.escape(args.repository)}/actions/runs/\d+", args.run_url
    ):
        parser.error("--run-url must identify a GitHub Actions run in this repository")
    platform = args.os.removesuffix("-latest")
    title = f"ci: weekly headless run failed on {args.os}"
    body = (
        f"Headless checks failed on {args.os} with Blender {args.version}: {args.run_url}.\n\n"
        f"Inspect the job log and `blender-tests-{args.os}` artifact for download logs, "
        "the exact candidate ZIP and native runtime/test reports when available. "
        "The workflow remains informational; triage the failure without loosening tests."
    )
    labels = ["bug", "area:ci", f"os:{platform}", f"blender:{args.version.rsplit('.', 1)[0]}"]
    try:
        outcome = report_failure(args.repository, title, body, labels)
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        # CLI output may contain credentials or API response content; do not echo it.
        print(
            f"Failure reporting failed ({type(error).__name__}); inspect this run.", file=sys.stderr
        )
        return 1
    print(f"Tracking issue {outcome} for {args.os}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
