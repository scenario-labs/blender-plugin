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
    if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repository) or any(
        part in {".", ".."} for part in repository.split("/")
    ):
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


def matrix_outcomes(repository, run_id, attempt, version):
    """Validate latest per-job results in this run before writing any issue.

    Successful jobs can retain an older attempt after a failed-jobs-only rerun.
    A result from a newer attempt is rejected instead of attributing it here.
    """
    expected = {
        f"blender {version} ({platform})": platform
        for platform in ("macos-latest", "windows-latest")
    }
    pages = github(
        f"repos/{repository}/actions/runs/{run_id}/jobs",
        "--method",
        "GET",
        "--paginate",
        "--slurp",
        "-f",
        "per_page=100",
        "-f",
        "filter=latest",
    )
    if not isinstance(pages, list) or not pages:
        raise ValueError("GitHub returned an invalid job listing")
    outcomes = {}
    ids = set()
    for page in pages:
        if not isinstance(page, dict) or not isinstance(page.get("jobs"), list):
            raise ValueError("GitHub returned an invalid job page")
        for job in page["jobs"]:
            if not isinstance(job, dict) or not isinstance(job.get("name"), str):
                raise ValueError("GitHub returned an invalid job")
            if job["name"] not in expected:
                continue
            platform = expected[job["name"]]
            number = job.get("id")
            if (
                platform in outcomes
                or type(number) is not int
                or number < 1
                or number in ids
                or type(job.get("run_id")) is not int
                or job.get("run_id") != run_id
                or type(job.get("run_attempt")) is not int
                or not 1 <= job["run_attempt"] <= attempt
                or job.get("status") != "completed"
                or job.get("conclusion")
                not in {"success", "failure", "timed_out", "cancelled", "skipped"}
            ):
                raise ValueError("GitHub returned an ambiguous or incomplete matrix result")
            ids.add(number)
            outcomes[platform] = (job["conclusion"], number, job["run_attempt"])
    if set(outcomes) != set(expected.values()):
        raise ValueError("GitHub did not return both expected OS jobs for this run")
    return outcomes


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repository", required=True)
    parser.add_argument("--version", required=True)
    parser.add_argument("--run-id", type=int, required=True)
    parser.add_argument("--run-attempt", type=int, required=True)
    args = parser.parse_args(argv)
    if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", args.repository) or any(
        part in {".", ".."} for part in args.repository.split("/")
    ):
        parser.error("--repository must be an owner/repository name")
    if not re.fullmatch(r"\d+\.\d+\.\d+", args.version):
        parser.error("--version must be a full Blender version")
    if args.run_id < 1 or args.run_attempt < 1:
        parser.error("--run-id and --run-attempt must be positive")
    try:
        outcomes = matrix_outcomes(args.repository, args.run_id, args.run_attempt, args.version)
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        # CLI output may contain credentials or API response content; do not echo it.
        print(
            f"Failure reporting failed ({type(error).__name__}); inspect this run.", file=sys.stderr
        )
        return 1
    status = 0
    for platform, (conclusion, number, job_attempt) in outcomes.items():
        if conclusion == "success":
            continue
        url = f"https://github.com/{args.repository}/actions/runs/{args.run_id}/job/{number}"
        title = f"ci: weekly headless run failed on {platform}"
        body = (
            f"Weekly headless workflow failed on {platform} with Blender {args.version}: {url}.\n\n"
            f"Workflow attempt {args.run_attempt}; job attempt {job_attempt}; "
            f"job conclusion: `{conclusion}`. "
            "Inspect the job log to distinguish setup, native tests, timeout and artifact "
            f"preservation failures. The `blender-tests-{platform}` artifact contains "
            "download logs, the exact candidate ZIP and runtime/test reports when available. "
            "The workflow remains informational; triage without loosening tests."
        )
        labels = [
            "bug",
            "area:ci",
            f"os:{platform.removesuffix('-latest')}",
            f"blender:{args.version.rsplit('.', 1)[0]}",
        ]
        try:
            outcome = report_failure(args.repository, title, body, labels)
        except (OSError, ValueError, subprocess.SubprocessError) as error:
            print(
                f"Failure reporting failed for {platform} ({type(error).__name__}); "
                "inspect this run.",
                file=sys.stderr,
            )
            status = 1
            continue
        print(f"Tracking issue {outcome} for {platform}.")
    return status


if __name__ == "__main__":
    sys.exit(main())
