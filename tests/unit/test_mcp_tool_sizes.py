# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location("mcp_tool_sizes", ROOT / "tools/mcp_tool_sizes.py")
sizer = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(sizer)


def test_measure_counts_wire_and_model_visible_bytes_and_utf16_headroom():
    entries = [
        {
            "name": "a",
            "description": "x\U0001f600",
            "inputSchema": {"type": "object", "properties": {}, "required": []},
            "annotations": {"readOnlyHint": True},
        }
    ]
    sizes = sizer.measure(entries)
    wire = len(json.dumps(entries).encode("utf-8"))
    assert sizes["tools"] == 1 and sizes["bytes"] == wire
    assert sizes["estimated_tokens"] == round(wire / 4)
    visible = [{key: entries[0][key] for key in ("name", "description", "inputSchema")}]
    assert sizes["model_visible_bytes"] == len(json.dumps(visible).encode("utf-8"))
    # Claude Code slices UTF-16 code units: the emoji counts twice.
    assert sizes["headroom"] == [{"name": "a", "chars": 3, "headroom": sizer.DESCRIPTION_CUT - 3}]


def test_report_compares_the_checkout_with_a_baseline(capsys):
    sha = "0" * 40
    sizer.main(["--base-root", str(ROOT), "--base-ref", sha])
    report = json.loads(capsys.readouterr().out)
    assert report["version"] == 1 and report["base_ref"] == sha
    assert report["baseline"] == report["current"]
    rows = report["current"]["headroom"]
    assert len(rows) == report["current"]["tools"]
    assert [row["headroom"] for row in rows] == sorted(row["headroom"] for row in rows)


@pytest.mark.parametrize(
    "argv",
    [["--base-ref", "0" * 40], ["--base-root", "."], ["--base-root", ".", "--base-ref", "main"]],
)
def test_baseline_needs_a_checkout_and_its_full_sha(argv):
    with pytest.raises(SystemExit):
        sizer.main(argv)
