# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Budget the context that local MCP tool definitions cost every agent session.

A client loads every tools/list entry (name, description, input schema and
annotations) before its first call, and keeps it for the whole session. These
budgets sit just above the measured sizes, so growth is a reviewed decision
rather than drift.

Sizes are characters of each entry serialized as the server sends it
(json.dumps with default separators), rebuilt from source by
tools/mcp_tool_sizes.py without importing Blender, which also reports the size
change on each pull request.

To change a budget deliberately, update TOTAL_BUDGET or TOOL_BUDGETS below in
the PR that grows or trims the definitions, and state the old and new sizes in
the PR description. Prefer moving edge-case detail out of a description into
the tool's result or the reference docs.
"""

import importlib.util
import json
import math
from pathlib import Path

from scenario.mcp import protocol

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location("mcp_tool_sizes", ROOT / "tools/mcp_tool_sizes.py")
sizer = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(sizer)

# Measured for 88 tools with the video-to-text status: 129,333 characters in total, about
# 32,334 tokens at four characters per token.
TOTAL_BUDGET = 129_400
# A budget that the total undercuts by more than this fraction is lowered, so a
# trim is not silently spent by a later addition.
TOTAL_SLACK = 0.03
# Any tool not listed in TOOL_BUDGETS.
DEFAULT_TOOL_BUDGET = 2_500
TOOL_BUDGETS = {
    "job_status": 9_600,
    "prepare_result_application": 7_100,
    "render_form": 4_500,
    "inspect_result_previews": 3_200,
    "decide_workflow_step": 3_000,
    "list_models": 2_800,
    "apply_result_application": 3_000,
    "estimate_cost": 2_600,
}
HOW_TO_UPDATE = (
    "Local MCP tool definitions are loaded into every agent session. Shorten the "
    "description (move edge cases into the result or docs/MCP.md), or, if the growth "
    "is deliberate, raise the budget in tests/unit/test_mcp_context_budget.py in the "
    "same PR and state the old and new sizes in the PR description."
)


def registry():
    """The tools/list registry rebuilt from source, in the server's registration order."""
    built = protocol.Registry()
    for entry in sizer.payload():
        built.add(
            protocol.ToolSpec(
                entry["name"],
                entry["description"],
                entry["inputSchema"],
                None,
                entry.get("annotations"),
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
    assert sizer.payload() == payload  # the report measures exactly what the server lists
    names = [item["name"] for item in payload]
    assert len(names) == len(set(names))
    assert names[0] == "scene_summary"  # Blender tools register before Scenario tools.
    for item in payload:
        assert set(item) <= {"name", "description", "inputSchema", "annotations"}
        assert item["inputSchema"]["type"] == "object"
