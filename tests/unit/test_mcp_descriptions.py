# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Check the actual MCP tool contract without importing Blender."""

import ast
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
EXPECTED = {
    "tools_scenario": {
        "list_models",
        "model_schema",
        "estimate_cost",
        "generate",
        "job_status",
        "wait_for_job",
        "import_result",
        "capture_reference",
        "list_generations",
    },
    "tools_blender": {
        "scene_summary",
        "object_detail",
        "execute_python",
        "select_objects",
        "set_frame",
        "screenshot_viewport",
        "camera_path",
        "render_still",
        "blender_api_help",
        "datablocks_summary",
    },
}


def specs(module):
    tree = ast.parse((ROOT / f"scenario/mcp/{module}.py").read_text())
    assignments = {
        node.targets[0].id: node.value
        for node in tree.body
        if isinstance(node, ast.Assign) and isinstance(node.targets[0], ast.Name)
    }
    return assignments, assignments["SPECS"].elts


def property_names(node, assignments):
    assert isinstance(node, ast.Dict)
    names = set()
    for key, value in zip(node.keys, node.values, strict=True):
        if key is None:
            assert isinstance(value, ast.Name)
            names.update(property_names(assignments[value.id], assignments))
        else:
            names.add(ast.literal_eval(key))
    return names


@pytest.mark.parametrize("module", EXPECTED)
def test_real_tool_descriptions_are_complete_static_contracts(module):
    _, calls = specs(module)
    names = []
    for call in calls:
        assert isinstance(call, ast.Call) and call.func.id == "ToolSpec"
        name, description = call.args[:2]
        assert isinstance(name, ast.Constant) and isinstance(description, ast.Constant)
        name, description = name.value, description.value
        names.append(name)
        assert re.fullmatch(r"[a-z][a-z0-9_]*", name)
        assert len(description) >= 120, name
        assert all(label in description for label in ("Args:", "Returns:", "Example:")), name
        assert re.search(
            r"\n(?:Platform equivalent: [^\n]+|No platform equivalent)\.$", description
        )
        if module == "tools_scenario" and name != "import_result":
            assert "Platform equivalent:" in description, name
        else:
            assert description.endswith("No platform equivalent."), name
    assert len(names) == len(set(names))
    assert set(names) == EXPECTED[module]


def test_job_tools_advertise_both_reference_spellings_without_requiring_legacy_id():
    assignments, calls = specs("tools_scenario")
    for call in calls:
        if call.args[0].value not in {"job_status", "wait_for_job", "import_result"}:
            continue
        schema = call.args[2]
        assert schema.func.id == "_schema"
        assert {"job_id", "id"} <= property_names(schema.args[0], assignments)
        assert len(schema.args) == 1 or ast.literal_eval(schema.args[1]) == []
