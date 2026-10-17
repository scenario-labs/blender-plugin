# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Committed Claude Code settings and MCP client template stay conservative.

The matcher below follows the documented Claude Code rule semantics closely
enough to check the intended commands; it is not Claude Code's implementation.
"""

import fnmatch
import importlib.util
import json
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SETTINGS = json.loads((ROOT / ".claude/settings.json").read_text(encoding="utf-8"))
MCP = json.loads((ROOT / ".mcp.json").read_text(encoding="utf-8"))
PERMISSIONS = SETTINGS["permissions"]
SERVER = "scenario-blender"

_SPEC = importlib.util.spec_from_file_location("gen_mcp_docs", ROOT / "tools/gen_mcp_docs.py")
generator = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(generator)

_RULE = re.compile(r"^(?P<tool>[\w-]+)(?:\((?P<spec>.*)\))?$")
_ASSIGNMENT = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*=\S*\s+")
_OPERATORS = re.compile(r"\s*(?:&&|\|\||;|\||\n)\s*")


def _rules(kind, tool):
    specs = []
    for rule in PERMISSIONS.get(kind, []):
        match = _RULE.match(rule)
        assert match, rule
        if match["tool"] == tool:
            specs.append(match["spec"])
    return specs


def _bash_pattern_matches(spec, command):
    if spec.endswith(":*"):
        spec = spec[:-2] + " *"
    pattern = ".*".join(re.escape(part) for part in spec.split("*"))
    if re.fullmatch(pattern, command, re.DOTALL):
        return True
    # A trailing " *" that is the only wildcard also matches the bare command.
    return spec.endswith(" *") and spec.count("*") == 1 and command == spec[:-2]


def _subcommands(command):
    for part in _OPERATORS.split(command.strip()):
        # Deny and ask rules match past any leading variable assignment.
        while _ASSIGNMENT.match(part):
            part = _ASSIGNMENT.sub("", part, count=1)
        if part:
            yield part


def bash_matches(kind, command):
    specs = _rules(kind, "Bash")
    return any(
        _bash_pattern_matches(spec, part) for part in _subcommands(command) for spec in specs
    )


def read_denied(path):
    for spec in _rules("deny", "Read"):
        assert "/" not in spec, "bare names match at any depth; anchored rules need new tests"
        if fnmatch.fnmatchcase(Path(path).name, spec):
            return True
    return False


def _documented_commands(relative):
    text = (ROOT / relative).read_text(encoding="utf-8")
    for block in re.findall(r"```sh\n(.*?)```", text, re.DOTALL):
        yield from block.replace("\\\n", " ").splitlines()


def test_settings_only_restrict_and_local_settings_stay_ignored():
    assert set(SETTINGS) == {"$schema", "permissions"}
    assert SETTINGS["$schema"] == "https://json.schemastore.org/claude-code-settings.json"
    assert set(PERMISSIONS) == {"deny", "ask"}
    for kind in ("deny", "ask"):
        assert len(PERMISSIONS[kind]) == len(set(PERMISSIONS[kind]))
    ignored = (ROOT / ".gitignore").read_text(encoding="utf-8").splitlines()
    assert ".claude/settings.local.json" in ignored


@pytest.mark.parametrize(
    "path", [".env", ".env.local", ".env.development.local", "tools/.env.local"]
)
def test_private_environment_files_are_unreadable(path):
    assert read_denied(path)


@pytest.mark.parametrize(
    "command",
    [
        "cat .env.local",
        "cat ./.env.local",
        "cat .env",
        "head -5 .env.local",
        "tail .env.development.local",
        "grep SCENARIO .env.local",
        "rg KEY .env.local",
        "sed -n 1,5p .env.local",
        "awk 1 .env.local",
        "less .env.local",
        "echo ok && cat .env.local | head -1",
    ],
)
def test_printing_private_environment_files_is_denied(command):
    assert bash_matches("deny", command)


@pytest.mark.parametrize(
    "command",
    [
        "cat .env.example",
        "grep SCENARIO .env.example",
        "uv run --locked --env-file .env.local python -m tools.check_sdk",
        "uv run --locked --env-file .env.local python tools/audit_payloads.py",
    ],
)
def test_example_and_explicit_dotenv_loading_stay_available(command):
    assert not bash_matches("deny", command)


def test_committed_environment_example_stays_readable():
    assert not read_denied(".env.example")


@pytest.mark.parametrize(
    "command",
    [
        "git push --force origin main",
        "git push -f origin main",
        "git push origin main --force",
        "git push --force-with-lease origin main",
        "git push origin +main",
        "git push origin HEAD:main",
        "git push origin +HEAD:main --force",
        "git push origin HEAD:refs/heads/main",
        "git push origin --delete main",
        "git push origin :main",
        "git push --mirror origin",
        "git fetch origin && git push -f origin main",
    ],
)
def test_pushes_that_replace_or_delete_main_are_denied(command):
    assert bash_matches("deny", command)


@pytest.mark.parametrize(
    "command",
    [
        "git push -u origin chore/54-agent-settings",
        "git push --force-with-lease origin feat/maintenance",
        "git push origin HEAD:feat/main-menu",
        "git push origin fix/domain",
        "git log --oneline origin/main..HEAD",
        "git rebase origin/main",
    ],
)
def test_branch_pushes_and_reads_of_main_are_not_denied(command):
    assert not bash_matches("deny", command)


def test_documented_paid_smoke_commands_ask_first():
    paid = [
        line
        for relative in ("tests/smoke/README.md", "CONTRIBUTING.md")
        for line in _documented_commands(relative)
        if line.startswith("SCENARIO_SMOKE=1 ")
    ]
    assert len(paid) >= 3
    for command in paid:
        assert bash_matches("ask", command), command
        assert not bash_matches("deny", command), command


@pytest.mark.parametrize(
    "command",
    [
        "make smoke",
        'SCENARIO_SMOKE=1 make smoke SMOKE_ARGS="budget-run --plan p.json --max-cu 40"',
        "SCENARIO_SMOKE=1 uv run --locked python -m tools.smoke_image submit --run-dir d",
        "SCENARIO_SMOKE=1 uv run --locked python -m tools.smoke_suite budget-run --max-cu 1",
        "SCENARIO_SMOKE=1 uv run --locked python tools/smoke_suite.py submit --run-dir d",
        "SCENARIO_SMOKE=1 uv run --locked python tests/smoke/smoke_video.py submit --run-dir d",
        "SCENARIO_SMOKE=1 python3 tests/smoke/smoke_image.py submit --run-dir d",
    ],
)
def test_paid_smoke_entry_points_ask_first(command):
    assert bash_matches("ask", command)


@pytest.mark.parametrize(
    "command",
    [
        "make test",
        "make test-blender",
        "uv run --locked --env-file .env.local python -m tools.smoke_model quote --run-dir d",
        "uv run --locked --env-file .env.local python -m tools.smoke_suite resume --run-dir d",
        "uv run --locked --no-env-file python -m pytest tests/unit/test_smoke_suite.py",
    ],
)
def test_free_commands_do_not_ask(command):
    assert not bash_matches("ask", command)
    assert not bash_matches("deny", command)


def test_every_paid_local_mcp_tool_asks_first():
    tools = [
        tool for _, relative in generator.GROUPS for tool in generator.parse_specs(ROOT / relative)
    ]
    paid = {tool["name"] for tool in tools if "approved_cost" in tool["required"]}
    assert "generate" in paid
    prefix = f"mcp__{SERVER}__"
    asked = {rule[len(prefix) :] for rule in PERMISSIONS["ask"] if rule.startswith(prefix)}
    assert asked == paid


def test_mcp_template_matches_documented_client_setup():
    assert set(MCP) == {"mcpServers"}
    assert set(MCP["mcpServers"]) == {SERVER}
    doc = (ROOT / "docs/MCP.md").read_text(encoding="utf-8")
    documented = re.search(r"claude mcp add --transport (\S+) (\S+) (\S+)", doc)
    assert documented[2] == SERVER
    assert MCP["mcpServers"][SERVER] == {"type": documented[1], "url": documented[3]}
