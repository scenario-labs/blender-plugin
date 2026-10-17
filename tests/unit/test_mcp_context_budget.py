# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Budget the context that local MCP tool definitions cost every agent session.

A client loads every tools/list entry (name, description, input schema and
annotations) before its first call, and keeps it for the whole session. These
budgets sit just above the measured sizes, so growth is a reviewed decision
rather than drift.

Sizes are characters of each entry serialized as the server sends it
(json.dumps with default separators), rebuilt from source with the same AST
parser as `make mcp-docs`, without importing Blender. A schema value computed
at import time, such as an enum built from a constant, is resolved from the
literal it names in source, so it counts at its real size.

To change a budget deliberately, update TOTAL_BUDGET or TOOL_BUDGETS below in
the PR that grows or trims the definitions, and state the old and new sizes in
the PR description. Prefer moving edge-case detail out of a description into
the tool's result or the reference docs.
"""

import ast
import importlib.util
import json
import math
from pathlib import Path
from unittest.mock import patch

from scenario.mcp import protocol

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location("gen_mcp_docs", ROOT / "tools/gen_mcp_docs.py")
generator = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(generator)
TOOL_SOURCES = [ROOT / relative for _, relative in generator.GROUPS]

# Measured on main for 87 tools: 124,132 characters in total, about 31,000 tokens
# at four characters per token.
TOTAL_BUDGET = 125_500
# A budget that the total undercuts by more than this fraction is lowered, so a
# trim is not silently spent by a later addition.
TOTAL_SLACK = 0.03
# Any tool not listed in TOOL_BUDGETS.
DEFAULT_TOOL_BUDGET = 2_500
TOOL_BUDGETS = {
    "job_status": 9_200,
    "prepare_result_application": 5_600,
    "render_form": 4_500,
    "inspect_result_previews": 3_200,
    "decide_workflow_step": 3_000,
    "list_models": 2_800,
    "apply_result_application": 2_800,
    "estimate_cost": 2_600,
}
HOW_TO_UPDATE = (
    "Local MCP tool definitions are loaded into every agent session. Shorten the "
    "description (move edge cases into the result or docs/MCP.md), or, if the growth "
    "is deliberate, raise the budget in tests/unit/test_mcp_context_budget.py in the "
    "same PR and state the old and new sizes in the PR description."
)


def _module_constants(path):
    """Module-level names in `path` bound to literals, including those imported by name."""
    tree = ast.parse(path.read_text(encoding="utf-8"))
    names = {}
    for node in tree.body:
        if isinstance(node, ast.ImportFrom) and node.level and node.module:
            source = (
                path.parents[node.level - 1].joinpath(*node.module.split(".")).with_suffix(".py")
            )
            wanted = {alias.name: alias.asname or alias.name for alias in node.names}
            if source.is_file() and wanted:
                found = _module_constants(source)
                names.update({wanted[n]: found[n] for n in wanted if n in found})
        elif isinstance(node, ast.Assign) and len(node.targets) == 1:
            target = node.targets[0]
            try:
                value = ast.literal_eval(node.value)
            except (ValueError, TypeError, SyntaxError):
                keys = getattr(node.value, "keys", None)
                if not isinstance(node.value, ast.Dict) or not all(
                    isinstance(k, ast.Constant) for k in keys
                ):
                    continue
                # A dispatch table of literal keys: list(NAME) in a schema reads its keys.
                value = tuple(k.value for k in keys)
            if isinstance(target, ast.Name):
                names[target.id] = value
            elif isinstance(target, ast.Tuple) and all(
                isinstance(e, ast.Name) for e in target.elts
            ):
                names.update(zip((e.id for e in target.elts), value, strict=True))
    return names


def _computed_value(node, names):
    """A schema value as the server computes it: constants by name, list(NAME), dicts."""
    if isinstance(node, ast.Constant):
        return node.value
    if isinstance(node, ast.Name) and node.id in names:
        return names[node.id]
    if (
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "list"
        and len(node.args) == 1
        and not node.keywords
    ):
        return list(_computed_value(node.args[0], names))
    if isinstance(node, ast.Dict) and None not in node.keys:
        return {
            _computed_value(k, names): _computed_value(v, names)
            for k, v in zip(node.keys, node.values, strict=True)
        }
    raise AssertionError(
        f"Cannot size the computed schema value {ast.unparse(node)}; extend "
        "_computed_value in tests/unit/test_mcp_context_budget.py"
    )


def registry():
    """The tools/list registry rebuilt from source, in the server's registration order."""
    built = protocol.Registry()
    for path in TOOL_SOURCES:
        names = _module_constants(path)

        def value(node, names=names):
            try:
                return ast.literal_eval(node)
            except (ValueError, TypeError):
                return _computed_value(node, names)

        with patch.object(generator, "_value", value):
            tools = generator.parse_specs(path)
        for tool in tools:
            schema = {
                "type": "object",
                "properties": tool["properties"],
                "required": tool["required"],
            }
            built.add(
                protocol.ToolSpec(
                    tool["name"], tool["description"], schema, None, tool["annotations"]
                )
            )
    return built


def sizes():
    return {item["name"]: len(json.dumps(item)) for item in registry().list_payload()}


def _table(measured, limit=12):
    rows = sorted(measured.items(), key=lambda item: -item[1])[:limit]
    return "\n".join(
        f"  {name}: {size} (budget {TOOL_BUDGETS.get(name, DEFAULT_TOOL_BUDGET)})"
        for name, size in rows
    )


def test_total_tool_definitions_stay_within_budget():
    measured = sizes()
    total = sum(measured.values())
    assert total <= TOTAL_BUDGET, (
        f"Tool definitions total {total} characters (about {math.ceil(total / 4)} tokens) "
        f"for {len(measured)} tools, over the budget of {TOTAL_BUDGET}. {HOW_TO_UPDATE}\n"
        f"Largest tools:\n{_table(measured)}"
    )
    floor = math.floor(TOTAL_BUDGET * (1 - TOTAL_SLACK))
    assert total >= floor, (
        f"Tool definitions total {total} characters, more than {TOTAL_SLACK:.0%} under "
        f"the budget of {TOTAL_BUDGET}. Lower TOTAL_BUDGET in "
        "tests/unit/test_mcp_context_budget.py to just above the new total, so the "
        "saving is kept."
    )


def test_each_tool_definition_stays_within_its_budget():
    measured = sizes()
    over = {
        name: size
        for name, size in measured.items()
        if size > TOOL_BUDGETS.get(name, DEFAULT_TOOL_BUDGET)
    }
    assert not over, (
        "Over their tool budget: "
        + ", ".join(
            f"{name} {size} > {TOOL_BUDGETS.get(name, DEFAULT_TOOL_BUDGET)}"
            for name, size in sorted(over.items())
        )
        + f". {HOW_TO_UPDATE}"
    )


def test_listed_budgets_name_registered_tools_above_the_default():
    measured = sizes()
    unknown = sorted(set(TOOL_BUDGETS) - set(measured))
    assert not unknown, f"TOOL_BUDGETS names unregistered tools: {', '.join(unknown)}"
    redundant = sorted(name for name in TOOL_BUDGETS if measured[name] <= DEFAULT_TOOL_BUDGET)
    assert not redundant, (
        f"Now within DEFAULT_TOOL_BUDGET; remove from TOOL_BUDGETS: {', '.join(redundant)}"
    )


def test_measurement_matches_the_server_payload_shape():
    payload = registry().list_payload()
    names = [item["name"] for item in payload]
    assert len(names) == len(set(names))
    assert names[0] == "scene_summary"  # Blender tools register before Scenario tools.
    for item in payload:
        assert set(item) <= {"name", "description", "inputSchema", "annotations"}
        assert item["inputSchema"]["type"] == "object"
