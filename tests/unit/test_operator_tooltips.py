# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Every Scenario operator shows a tooltip that follows docs/UI_STYLE.md: one sentence, no
trailing period (Blender adds it). Internal operators, which no button draws, are exempt."""

import ast
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def _operators():
    for path in sorted((ROOT / "scenario").rglob("*.py")):
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            if not isinstance(node, ast.ClassDef):
                continue
            fields = {
                statement.targets[0].id: statement.value
                for statement in node.body
                if isinstance(statement, ast.Assign) and isinstance(statement.targets[0], ast.Name)
            }
            idname = fields.get("bl_idname")
            if not (isinstance(idname, ast.Constant) and str(idname.value).startswith("scenario.")):
                continue
            options = fields.get("bl_options")
            if options is not None and "INTERNAL" in ast.unparse(options):
                continue
            yield f"{path.relative_to(ROOT)}:{node.lineno} {idname.value}", fields, node


def test_every_drawn_operator_has_a_tooltip():
    missing = [
        where
        for where, fields, node in _operators()
        if "bl_description" not in fields and not ast.get_docstring(node)
    ]
    assert not missing, missing


def test_constant_tooltips_are_one_sentence_without_a_final_period():
    bad = []
    for where, fields, _node in _operators():
        value = fields.get("bl_description")
        if isinstance(value, ast.Constant) and isinstance(value.value, str):
            text = value.value.strip()
            if not text or text.endswith(".") or re.search(r"[.!?] [A-Z]", text):
                bad.append(f"{where}: {text}")
    assert not bad, bad
