# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Fork-safe workflow conventions and the real aggregate shell's failure policy.

These checks deliberately inspect the repository's block-style workflow subset;
they are not a YAML parser. Unsupported structural forms fail with a diagnostic
instead of silently omitting a workflow. Action syntax/pins have separate checks.
"""

import os
import re
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
WORKFLOWS = sorted(
    [*(ROOT / ".github/workflows").glob("*.yml"), *(ROOT / ".github/workflows").glob("*.yaml")]
)


def block(text, key, indent=0):
    """Read a mapping block at an exact indentation, rejecting inline values."""
    prefix = " " * indent
    match = re.search(rf"^{prefix}{re.escape(key)}:\s*(?:#.*)?$", text, re.MULTILINE)
    assert match is not None, f"Expected block-style {key}: at indentation {indent}"
    lines = []
    for line in text[match.end() :].splitlines():
        if (
            line.strip()
            and not line.lstrip().startswith("#")
            and len(line) - len(line.lstrip()) <= indent
        ):
            break
        lines.append(line)
    return "\n".join(lines)


def pr_sources(root, workflows):
    """Follow checked-in reusable workflows and composite actions from PR callers."""
    pending = []
    for path in workflows:
        events = []
        for line in block(path.read_text(), "on").splitlines():
            if (
                line.strip()
                and not line.lstrip().startswith("#")
                and len(line) - len(line.lstrip()) == 2
            ):
                event = re.match(r"^  ([\w-]+):", line)
                assert event, "Use plain, block-style workflow event keys"
                events.append(event[1])
        if "pull_request" in events:
            pending.append(path)
    assert pending, "Expected at least one pull_request workflow"
    found = set()
    while pending:
        path = pending.pop()
        if path in found:
            continue
        found.add(path)
        for match in re.finditer(
            r"""^\s*(?:-\s+)?uses:\s+(?:(['"])(\./[^'"]+)\1|(\./[^\s#]+))""",
            path.read_text(),
            re.MULTILINE,
        ):
            reference = match[2] or match[3]
            dependency = (root / reference).resolve()
            assert dependency.is_relative_to(root.resolve()), (
                "Local workflow/action escapes checkout"
            )
            if dependency.is_dir():
                dependency = dependency / "action.yml"
            assert dependency.is_file(), f"Missing local workflow/action: {reference}"
            pending.append(dependency)
    return found


def assert_readonly_source(text):
    assert not re.search(r"\bsecrets\b", text, re.IGNORECASE), "PR workloads must not use secrets"
    for match in re.finditer(r"""^( *)(["']?permissions["']?)\s*:(.*)$""", text, re.MULTILINE):
        inline = match[3].split("#", 1)[0].strip()
        assert inline in ("", "{}"), "Keep PR permissions in explicit read/none blocks"
        if inline == "{}":
            continue
        permissions = block(text[match.start() :], match[2], indent=len(match[1]))
        for line in permissions.splitlines():
            entry = line.split("#", 1)[0].strip()
            assert not entry or re.fullmatch(r"[\w-]+:\s*(read|none)", entry), (
                "PR permission entries must use explicit read/none values"
            )


def test_every_workflow_has_explicit_permissions_and_no_target_event():
    assert WORKFLOWS
    for path in WORKFLOWS:
        text = path.read_text()
        assert re.search(r"^permissions:", text, re.MULTILINE), path
        assert "pull_request" + "_target" not in text, path


def test_all_pr_workflows_and_local_dependencies_are_readonly_and_secret_free():
    for path in pr_sources(ROOT, WORKFLOWS):
        try:
            assert_readonly_source(path.read_text())
        except AssertionError as error:
            raise AssertionError(f"{path.relative_to(ROOT)}: {error}") from error


@pytest.mark.parametrize(
    "unsafe",
    [
        "env:\n  TOKEN: ${{ secrets.EXAMPLE }}\n",
        "env:\n  TOKEN: ${{ secrets['EXAMPLE'] }}\n",
        "env:\n  DUMP: ${{ toJSON(secrets) }}\n",
        "env:\n  DUMP: ${{ secrets }}\n",
        "env:\n  TOKEN: ${{ SeCrEtS.EXAMPLE }}\n",
        "jobs:\n  child:\n    secrets: inherit\n",
        "permissions:\n  issues: write\n",
        'permissions:\n  "issues": write\n',
        "permissions: write-all\n",
        "permissions: {contents: read, issues: write}\n",
    ],
)
def test_pr_policy_rejects_secret_and_permission_escalation(unsafe):
    with pytest.raises(AssertionError):
        assert_readonly_source(unsafe)


@pytest.mark.parametrize("quote", ["", "'", '"'])
def test_transitive_local_dependencies_are_included(tmp_path, quote):
    caller = tmp_path / "caller.yml"
    child = tmp_path / "child.yml"
    action = tmp_path / "action"
    action.mkdir()
    caller.write_text(
        f"on:\n  pull_request:\njobs:\n  tests:\n    uses: {quote}./child.yml{quote}\n"
    )
    child.write_text(
        f"on:\n  workflow_call:\njobs:\n  tests:\n    steps:\n      - uses: {quote}./action{quote}\n"
    )
    (action / "action.yml").write_text("runs:\n  using: composite\n")
    assert pr_sources(tmp_path, [caller, child]) == {caller, child, action / "action.yml"}


@pytest.mark.parametrize("trigger", ["on: [pull_request]\n", 'on:\n  "pull_request":\n'])
def test_unsupported_trigger_is_not_silently_skipped(tmp_path, trigger):
    workflow = tmp_path / "inline.yml"
    workflow.write_text(trigger)
    with pytest.raises(AssertionError, match="block-style"):
        pr_sources(tmp_path, [workflow])


def test_explicit_job_contexts_are_unique():
    contexts = {}
    for path in WORKFLOWS:
        for name in re.findall(r"^    name:\s*(.+)$", path.read_text(), re.MULTILINE):
            assert name not in contexts, (
                f"Duplicate check context {name}: {contexts.get(name)}, {path}"
            )
            contexts[name] = path


def aggregate():
    text = (ROOT / ".github/workflows/ci.yml").read_text()
    jobs = block(text, "jobs")
    job_ids = re.findall(r"^  ([\w-]+):\s*$", jobs, re.MULTILINE)
    gate = block(jobs, "ci-ok", indent=2)
    dependencies = re.search(r"^    needs:\s*\[([^\]]+)\]\s*$", gate, re.MULTILINE)
    assert dependencies, "Keep ci-ok needs explicit and in block-style jobs"
    needs = [value.strip() for value in dependencies[1].split(",")]
    assert len(needs) == len(set(needs)), "Duplicate aggregate dependency"
    assert set(needs) == set(job_ids) - {"ci-ok"}, "Every CI workload must reach ci-ok"
    assert re.search(r"^    if:\s*always\(\)\s*$", gate, re.MULTILINE), (
        "Gate must run after failures"
    )
    inputs = re.findall(
        r"^          ([A-Z_]+): \$\{\{ needs\.([\w-]+)\.result \}\}$", gate, re.MULTILINE
    )
    assert {job for _, job in inputs} == set(needs), "Gate must inspect every needed result"
    assert len(inputs) == len(needs), "Each result must have one distinct gate input"
    assert len({name for name, _ in inputs}) == len(inputs), "Duplicate gate environment variable"
    assert "NATIVE_CHANGES: ${{ needs.changes.outputs.native }}" in gate, (
        "Gate must read the changes classification"
    )
    script = block(gate.replace("run: |", "run:"), "run", indent=8)
    script = "\n".join(line.removeprefix("          ") for line in script.splitlines())
    assert script.strip(), "Expected the actual ci-ok shell script"
    return dict(inputs), script


def run_script(script, environment, cwd=None):
    return subprocess.run(
        ["bash", "-eo", "pipefail", "-c", script],
        env=environment,
        cwd=cwd,
        capture_output=True,
        text=True,
    )


def with_outcome(environment, variable, outcome):
    changed = {**environment, variable: outcome}
    if outcome is None:
        del changed[variable]
    return changed


@pytest.mark.skipif(os.name == "nt", reason="The CI aggregate executes on hosted Ubuntu bash")
def test_aggregate_accepts_only_all_success_when_native_inputs_change():
    inputs, script = aggregate()
    environment = {**os.environ, **dict.fromkeys(inputs, "success"), "NATIVE_CHANGES": "true"}
    result = run_script(script, environment)
    assert result.returncode == 0, result.stderr + result.stdout
    for variable in inputs:
        for outcome in ("failure", "cancelled", "skipped", "", None):
            result = run_script(script, with_outcome(environment, variable, outcome))
            assert result.returncode != 0, f"ci-ok accepted {variable}={outcome!r}"


@pytest.mark.skipif(os.name == "nt", reason="The CI aggregate executes on hosted Ubuntu bash")
def test_aggregate_accepts_a_skipped_baseline_only_without_native_changes():
    inputs, script = aggregate()
    blender = next(name for name, job in inputs.items() if job == "blender")
    environment = {
        **os.environ,
        **dict.fromkeys(inputs, "success"),
        "NATIVE_CHANGES": "false",
        blender: "skipped",
    }
    result = run_script(script, environment)
    assert result.returncode == 0, result.stderr + result.stdout
    for variable in inputs:
        for outcome in ("failure", "cancelled", "skipped", "", None):
            if variable == blender and outcome == "skipped":
                continue
            result = run_script(script, with_outcome(environment, variable, outcome))
            assert result.returncode != 0, f"ci-ok accepted {variable}={outcome!r}"
    for classification in ("true", "False", "", None):
        result = run_script(script, with_outcome(environment, "NATIVE_CHANGES", classification))
        assert result.returncode != 0, f"ci-ok accepted a skip with native={classification!r}"


def ci_job(name):
    return block(block((ROOT / ".github/workflows/ci.yml").read_text(), "jobs"), name, indent=2)


def test_blender_baseline_waits_for_a_native_classification():
    job = ci_job("blender")
    assert re.search(r"^    needs:\s*\[?changes\]?\s*$", job, re.MULTILINE)
    assert re.search(r"^    if:\s*needs\.changes\.outputs\.native == 'true'\s*$", job, re.MULTILINE)


def changes_script():
    job = ci_job("changes")
    assert re.search(r"^          fetch-depth: 2\s*$", job, re.MULTILINE), (
        "Fetch both parents of the pull request merge commit"
    )
    assert re.search(
        r"^      native: \$\{\{ steps\.classify\.outputs\.native \}\}$", job, re.MULTILINE
    ), "Publish the classify step's native output"
    script = block(job.replace("run: |", "run:"), "run", indent=8)
    script = "\n".join(line.removeprefix("          ") for line in script.splitlines())
    assert script.strip(), "Expected the actual changes shell script"
    return script


BASE_FILES = {
    "AGENTS.md": "# Rules\n",
    "README.md": "# Readme\n",
    "LICENSE": "License\n",
    "docs/index.md": "# Index\n",
    "scenario/core.py": "VALUE = 1\n",
    "tests/blender/README.md": "# Native tests\n",
    ".github/workflows/ci.yml": "name: CI\n",
}


def git(root, *args):
    return subprocess.check_output(["git", "-C", str(root), *args], text=True).strip()


def commit(root, files, message):
    for path, text in files.items():
        target = root / path
        if text is None:
            target.unlink()
        else:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(text)
    git(root, "add", "-A")
    git(root, "commit", "-q", "--allow-empty", "-m", message)


def classify(tmp_path, files, event="pull_request", merge=True):
    """Classify ``files`` changed by a PR merged over a base that moved meanwhile."""
    repo = tmp_path / "repo"
    repo.mkdir()
    git(repo, "init", "-q", "-b", "main")
    git(repo, "config", "user.name", "Workflow test")
    git(repo, "config", "user.email", "test@example.invalid")
    commit(repo, BASE_FILES, "test: base")
    git(repo, "checkout", "-q", "-b", "pr")
    commit(repo, files, "test: change")
    git(repo, "checkout", "-q", "main")
    commit(repo, {"tools/moved.py": "VALUE = 3\n"}, "test: base moves")
    if merge:
        git(repo, "merge", "-q", "--no-ff", "--no-edit", "pr")
    else:
        git(repo, "checkout", "-q", "pr")
    output = tmp_path / "output"
    environment = {**os.environ, "EVENT_NAME": event, "GITHUB_OUTPUT": str(output)}
    result = run_script(changes_script(), environment, cwd=repo)
    assert result.returncode == 0, result.stderr + result.stdout
    values = dict(line.split("=", 1) for line in output.read_text().splitlines())
    return values["native"]


@pytest.mark.skipif(os.name == "nt", reason="The CI classifier executes on hosted Ubuntu bash")
@pytest.mark.parametrize(
    "files",
    [
        {"AGENTS.md": "# Changed\n"},
        {"README.md": "# Changed\n", "docs/index.md": "# Changed\n"},
        {"docs/new/page.md": "# New\n", "docs/index.md": None},
        {".agents/skills/s/SKILL.md": "x\n", ".claude/CLAUDE.md": "x\n", ".codex/config.toml": ""},
        {".github/ISSUE_TEMPLATE/bug.yml": "x\n", ".github/pull_request_template.md": "x\n"},
    ],
)
def test_documentation_only_pull_requests_skip_native_checks(tmp_path, files):
    assert classify(tmp_path, files) == "false"


@pytest.mark.skipif(os.name == "nt", reason="The CI classifier executes on hosted Ubuntu bash")
@pytest.mark.parametrize(
    "files",
    [
        {"scenario/core.py": "VALUE = 2\n"},
        {"docs/index.md": "# Changed\n", "scenario/core.py": "VALUE = 2\n"},
        {"tests/blender/README.md": "# Changed\n"},
        {"LICENSE": "Changed\n"},
        {".github/workflows/ci.yml": "name: Changed\n"},
        {"scenario/core.py": None, "docs/core.py": "VALUE = 1\n"},
        {},
    ],
)
def test_any_other_pull_request_change_runs_native_checks(tmp_path, files):
    assert classify(tmp_path, files) == "true"


@pytest.mark.skipif(os.name == "nt", reason="The CI classifier executes on hosted Ubuntu bash")
def test_pushes_always_run_native_checks(tmp_path):
    assert classify(tmp_path, {"AGENTS.md": "# Changed\n"}, event="push") == "true"


@pytest.mark.skipif(os.name == "nt", reason="The CI classifier executes on hosted Ubuntu bash")
def test_a_checkout_without_the_merge_commit_runs_native_checks(tmp_path):
    assert classify(tmp_path, {"AGENTS.md": "# Changed\n"}, merge=False) == "true"


@pytest.mark.parametrize("count,command_exit", [(0, 0), (2, 0), (1, 0), (1, 17)])
def test_package_update_step_uses_one_exact_candidate_and_propagates_failure(
    tmp_path, count, command_exit
):
    text = (ROOT / ".github/workflows/blender-baseline.yml").read_text()
    step = text.split(
        "      - name: Test Scenario package state across native update and restart\n", 1
    )[1]
    step = step.split("\n      - ", 1)[0]
    command = "\n".join(line[10:] for line in step.split("        run: |\n", 1)[1].splitlines())
    run_root = tmp_path / "runner with spaces"
    candidates = run_root / "scenario-tests/run-fixture"
    candidates.mkdir(parents=True)
    for number in range(count):
        (candidates / f"scenario-{number}.zip").write_bytes(b"fixture")
    binary = tmp_path / "bin"
    binary.mkdir()
    fake = binary / "uv"
    fake.write_text('#!/bin/sh\nprintf "%s\\0" "$@" > "$UPDATE_ARGUMENTS"\nexit "$UPDATE_EXIT"\n')
    fake.chmod(0o755)
    args = tmp_path / "arguments"
    environment = dict(
        os.environ,
        PATH=str(binary) + os.pathsep + os.environ.get("PATH", ""),
        RUNNER_TEMP=str(run_root),
        BLENDER_VERSION="5.1.2",
        UPDATE_ARGUMENTS=str(args),
        UPDATE_EXIT=str(command_exit),
    )
    result = subprocess.run(
        ["bash", "-c", command], env=environment, capture_output=True, text=True
    )
    if count != 1:
        assert result.returncode != 0
        assert not args.exists()
        return
    assert result.returncode == command_exit
    values = args.read_bytes().decode().split("\0")[:-1]
    assert values[values.index("--candidate-zip") + 1] == str(candidates / "scenario-0.zip")
    assert values[values.index("--expected-version") + 1] == "5.1.2"
    assert "--test-predecessor" in values
    assert values[values.index("--artifacts") + 1] == str(
        run_root / "scenario-package-update-tests"
    )
