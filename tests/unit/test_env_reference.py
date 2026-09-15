# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Keep the contributor environment reference aligned with actual Python reads."""

import ast
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def documented_variables():
    section = (ROOT / "CONTRIBUTING.md").read_text().split("## Environment variables\n", 1)[1]
    section = section.split("\n## ", 1)[0]
    return set(re.findall(r"`(SCENARIO_[A-Z_]+)`", section))


def environment(receiver):
    return (isinstance(receiver, ast.Name) and receiver.id in {"environ", "env"}) or (
        isinstance(receiver, ast.Attribute)
        and isinstance(receiver.value, ast.Name)
        and receiver.value.id == "os"
        and receiver.attr == "environ"
    )


def test_reference_matches_code():
    reads = set()
    for directory in ("scenario", "tests", "tools"):
        for path in (ROOT / directory).rglob("*.py"):
            if path == Path(__file__):
                continue
            for node in ast.walk(ast.parse(path.read_text())):
                key = None
                if (
                    isinstance(node, ast.Call)
                    and isinstance(node.func, ast.Attribute)
                    and node.func.attr == "get"
                    and environment(node.func.value)
                    and node.args
                ):
                    key = node.args[0]
                elif (
                    isinstance(node, ast.Subscript)
                    and isinstance(node.ctx, ast.Load)
                    and environment(node.value)
                ):
                    key = node.slice
                if (
                    isinstance(key, ast.Constant)
                    and isinstance(key.value, str)
                    and re.fullmatch(r"SCENARIO_[A-Z_]+", key.value)
                ):
                    reads.add(key.value)
    assert documented_variables() - {"SCENARIO_BLENDER_TOKEN"} == reads


def test_env_example_keys_are_documented_and_empty():
    example = (ROOT / ".env.example").read_text()
    keys = set(re.findall(r"^#?\s*(SCENARIO_[A-Z_]+)=", example, re.M))
    assert keys <= documented_variables()
    active = [line for line in example.splitlines() if line and not line.startswith("#")]
    assert active == [
        "SCENARIO_TEST_API_KEY=",
        "SCENARIO_TEST_API_SECRET=",
        "SCENARIO_TEST_PROJECT_ID=",
    ]
