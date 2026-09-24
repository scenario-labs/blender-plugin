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
    assert not re.search(r"\bsecrets\s*(?:\.|\[|:)", text), "PR workloads must not use secrets"
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
    script = block(gate.replace("run: |", "run:"), "run", indent=8)
    script = "\n".join(line.removeprefix("          ") for line in script.splitlines())
    assert script.strip(), "Expected the actual ci-ok shell script"
    return dict(inputs), script


@pytest.mark.skipif(os.name == "nt", reason="The CI aggregate executes on hosted Ubuntu bash")
def test_aggregate_accepts_only_all_success():
    inputs, script = aggregate()
    environment = {**os.environ, **dict.fromkeys(inputs, "success")}
    result = subprocess.run(
        ["bash", "-eo", "pipefail", "-c", script], env=environment, capture_output=True, text=True
    )
    assert result.returncode == 0, result.stderr + result.stdout
    for variable in inputs:
        for outcome in ("failure", "cancelled", "skipped", "", None):
            changed = {**environment, variable: outcome}
            if outcome is None:
                del changed[variable]
            result = subprocess.run(
                ["bash", "-eo", "pipefail", "-c", script],
                env=changed,
                capture_output=True,
                text=True,
            )
            assert result.returncode != 0, f"ci-ok accepted {variable}={outcome!r}"
