# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Check the actual MCP tool contract without importing Blender."""

import ast
import re
from pathlib import Path

import pytest

from scenario.core.ui.capability_status import UNAPPLIED_CAPABILITIES

ROOT = Path(__file__).resolve().parents[2]
EXPECTED = {
    "tools_scenario": {
        "list_assets",
        "search_assets",
        "list_workflows",
        "workflow_schema",
        "estimate_workflow",
        "run_workflow",
        "discard_workflow_estimate",
        "prepare_film_composition",
        "film_composition_review",
        "estimate_film_composition",
        "generate_film_composition",
        "film_capture_sources",
        "prepare_film_capture",
        "render_film_capture",
        "film_capture_review",
        "upload_film_capture",
        "film_shot_sources",
        "film_timeline_sources",
        "prepare_film_timeline",
        "film_timeline_review",
        "build_film_timeline",
        "prepare_film_shot",
        "film_shot_review",
        "build_film_shot",
        "film_recipe",
        "estimate_film_task",
        "approve_film_task",
        "discard_film_estimate",
        "bind_film_upload",
        "list_local_jobs",
        "cancel_prepared_job",
        "recover_local_job",
        "recover_cloud_job",
        "prepare_result_application",
        "apply_result_application",
        "list_models",
        "model_schema",
        "estimate_cost",
        "render_form",
        "estimate_prompt",
        "estimate_blockout",
        "approve_blockout",
        "read_model_text",
        "prepare_blockout_plan",
        "blockout_plan_status",
        "apply_blockout_plan",
        "approve_prompt",
        "read_prompt_result",
        "generate",
        "job_status",
        "wait_for_job",
        "import_result",
        "capture_reference",
        "upload_reference",
        "reference_upload_status",
        "list_reference_uploads",
        "recover_reference_upload",
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


def test_experimental_paths_are_explicit_without_removing_tools():
    _, calls = specs("tools_scenario")
    descriptions = {call.args[0].value: call.args[1].value for call in calls}
    film = {name for name in descriptions if "film" in name}
    assert film == {name for name in EXPECTED["tools_scenario"] if "film" in name}
    for name in film:
        assert "\nFilm is experimental. " in descriptions[name], name
    for name in ("estimate_cost", "generate"):
        description = descriptions[name]
        assert "are experimental" in description, name
        assert "results stay saved without Blender application" in description, name
        for capability in UNAPPLIED_CAPABILITIES:
            assert f"({capability})" in description, (name, capability)


def test_job_tools_advertise_both_reference_spellings_without_requiring_legacy_id():
    assignments, calls = specs("tools_scenario")
    for call in calls:
        if call.args[0].value not in {"job_status", "wait_for_job", "import_result"}:
            continue
        schema = call.args[2]
        assert schema.func.id == "_schema"
        assert {"job_id", "id"} <= property_names(schema.args[0], assignments)
        assert len(schema.args) == 1 or ast.literal_eval(schema.args[1]) == []
