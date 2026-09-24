# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Generated reference stays aligned with tool source without importing bpy."""

import importlib.util
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location("gen_mcp_docs", ROOT / "tools/gen_mcp_docs.py")
generator = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(generator)


def test_committed_reference_matches_all_registered_source_contracts():
    doc = (ROOT / "docs/MCP.md").read_text()
    assert generator.replace_block(doc, generator.generated()) == doc
    mapping = doc.split("## Local server and mcp.scenario.com", 1)[1]
    names = []
    for _, relative in generator.GROUPS:
        for tool in generator.parse_specs(ROOT / relative):
            names.append(tool["name"])
            assert re.search(r"`" + re.escape(tool["name"]) + r"(?:\(|`)", mapping)
    assert len(names) == len(set(names))
    for relative in ("README.md", "docs/USER_GUIDE.md", "docs/MCP.md"):
        assert not re.search(r"\b\d+ tools\b", (ROOT / relative).read_text())


def test_renamed_tool_is_detected_as_documentation_drift(tmp_path):
    source = ROOT / "scenario/mcp/tools_blender.py"
    changed = tmp_path / "tools_blender.py"
    changed.write_text(source.read_text().replace('"scene_summary",', '"renamed_summary",', 1))
    groups = [
        (generator.GROUPS[0][0], generator.parse_specs(changed)),
        (generator.GROUPS[1][0], generator.parse_specs(ROOT / generator.GROUPS[1][1])),
    ]
    doc = (ROOT / "docs/MCP.md").read_text()
    assert generator.replace_block(doc, generator.render(groups)) != doc


def test_parser_handles_shared_job_properties_and_dynamic_enum_without_execution(tmp_path):
    path = tmp_path / "tool.py"
    path.write_text("""raise RuntimeError("source must never execute")
_JOB_REF = {"job_id": {"type": "string"}, "id": {"type": "string"}}
SPECS = (ToolSpec("example", "First line | summary.\\nArgs: rest", _schema(
    {**_JOB_REF, "lane": {"type": "string", "enum": list(LANES)}}, ["lane"]),
    handler, {"readOnlyHint": True}),)
""")
    tools = generator.parse_specs(path)
    assert set(tools[0]["properties"]) == {"id", "job_id", "lane"}
    assert tools[0]["properties"]["lane"]["enum"] == "list(LANES)"
    rendered = generator.render([("Example", tools)])
    assert "`lane`*: string" in rendered
    assert "read-only annotation" in rendered
    assert "First line \\| summary." in rendered
    assert "Args: rest" not in rendered


@pytest.mark.parametrize(
    "document",
    [
        "no markers",
        "<!-- tools:end --><!-- tools:start -->",
        "<!-- tools:start --><!-- tools:start --><!-- tools:end -->",
    ],
)
def test_malformed_markers_fail_instead_of_rewriting_unrelated_text(document):
    with pytest.raises(ValueError):
        generator.replace_block(document, "replacement\n")


def test_initialize_guidance_identifies_hosted_platform_boundary():
    from scenario.mcp.protocol import INSTRUCTIONS

    assert "mcp.scenario.com" in INSTRUCTIONS
