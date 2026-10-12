# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Only the credential-free launchers start the system's file opener or web browser.

Blender's ``wm.path_open`` and ``wm.url_open`` and Python's ``webbrowser``
start the opener with Blender's whole environment, which can hold the Scenario
credentials Credentials > Environment reads. Every folder, file, link and player
button goes through ``core.jobs.playback.system_open`` or ``system_open_url``.
"""

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PACKAGE = ROOT / "scenario"
BLENDER_OPENERS = {"path_open", "url_open", "url_open_preset"}
OPERATOR_NAMES = {f"wm.{name}" for name in BLENDER_OPENERS} | {
    f"WM_OT_{name}" for name in BLENDER_OPENERS
}
LAUNCHERS = {"xdg-open", "/usr/bin/open"}
# Modules that may name the system launchers themselves, and why.
ALLOWED = {
    "scenario/core/jobs/playback.py": (
        "The credential-free launcher: it starts /usr/bin/open, xdg-open or an isolated "
        "interpreter calling os.startfile with player_environment()."
    ),
}


def findings(source):
    """Direct opener uses in one module's code; docstrings and comments never match."""
    tree = ast.parse(source)
    # Docstrings and other bare strings describe; they never launch anything.
    prose = {
        id(node.value)
        for node in ast.walk(tree)
        if isinstance(node, ast.Expr) and isinstance(node.value, ast.Constant)
    }
    found = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str) and id(node) not in prose:
            if node.value in OPERATOR_NAMES:
                found.append(f"operator {node.value}")
            elif node.value in LAUNCHERS or "startfile" in node.value:
                found.append(f"launcher {node.value!r}")
        elif isinstance(node, ast.Attribute):
            if (
                node.attr in BLENDER_OPENERS
                and isinstance(node.value, ast.Attribute)
                and node.value.attr == "wm"
            ):
                found.append(f"operator wm.{node.attr}")
            elif node.attr == "startfile":
                found.append("launcher startfile")
        elif isinstance(node, ast.Import):
            found += [f"import {a.name}" for a in node.names if a.name == "webbrowser"]
        elif isinstance(node, ast.ImportFrom):
            if node.module == "webbrowser":
                found.append("import webbrowser")
            elif node.module == "os" and any(a.name == "startfile" for a in node.names):
                found.append("launcher startfile")
    return sorted(found)


def test_the_scan_finds_every_direct_opener_form():
    source = """
\"\"\"Prose about ``wm.path_open`` or ``os.startfile`` is not a call.\"\"\"
import webbrowser
from os import startfile
bpy.ops.wm.path_open(filepath=path)
bpy.ops.wm.url_open(url=url)
layout.operator("wm.url_open", text="Link").url = url
layout.operator("WM_OT_path_open")
subprocess.Popen(["xdg-open", path])
subprocess.Popen(["/usr/bin/open", path])
subprocess.Popen([python, "-c", "import os; os.startfile(path)"])
os.startfile(path)
"""
    assert findings(source) == sorted(
        [
            "import webbrowser",
            "launcher startfile",
            "operator wm.path_open",
            "operator wm.url_open",
            "operator wm.url_open",
            "operator WM_OT_path_open",
            "launcher 'xdg-open'",
            "launcher '/usr/bin/open'",
            "launcher 'import os; os.startfile(path)'",
            "launcher startfile",
        ]
    )
    assert findings('layout.operator("scenario.open_path").filepath = path') == []


def test_no_module_starts_the_system_opener_with_blenders_environment():
    offenders = {}
    scanned = 0
    for path in sorted(PACKAGE.rglob("*.py")):
        name = path.relative_to(ROOT).as_posix()
        found = findings(path.read_text(encoding="utf-8"))
        scanned += 1
        if found and name not in ALLOWED:
            offenders[name] = found
    assert scanned > 100
    assert offenders == {}
    # The allowlist stays exact: each entry still launches and has a reason.
    for name, reason in ALLOWED.items():
        assert findings((ROOT / name).read_text(encoding="utf-8")), name
        assert reason
