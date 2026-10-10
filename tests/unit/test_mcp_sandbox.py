# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Opt-in execute_python error text: the agent's frames, never the extension's own."""

import os
import sys
import types

import pytest

from scenario.mcp import sandbox


@pytest.fixture
def fake_bpy(monkeypatch):
    module = types.ModuleType("bpy")
    monkeypatch.setitem(sys.modules, "bpy", module)
    return module


def _assert_agent_frames_only(error):
    assert 'File "<scenario-mcp>"' in error
    assert sandbox.__file__ not in error
    assert os.path.dirname(sandbox.__file__) not in error
    assert "run_python" not in error


def test_runtime_error_reports_agent_frames_without_installed_sandbox_frame(fake_bpy):
    payload = sandbox.run_python(
        "def place():\n    raise ValueError('agent failure')\nprint('before')\nplace()\n"
    )
    error = payload["error"]
    assert error.startswith("ValueError: agent failure\nTraceback (most recent call last):\n")
    assert "in place" in error and error.rstrip().endswith("ValueError: agent failure")
    _assert_agent_frames_only(error)
    assert payload["stdout"] == "before\n"


def test_syntax_error_reports_agent_source_without_installed_sandbox_frame(fake_bpy):
    error = sandbox.run_python("def broken(:\n    pass\n")["error"]
    assert error.startswith("SyntaxError: ")
    _assert_agent_frames_only(error)


def test_success_has_no_error_and_blocked_tokens_are_refused(fake_bpy):
    assert "error" not in sandbox.run_python("result['value'] = 2")
    assert "blocked" in sandbox.run_python("bpy.ops.wm.quit_blender()")["error"]


def test_blocked_exit_reports_agent_frames_without_installed_sandbox_frame(fake_bpy):
    error = sandbox.run_python("import sys\nsys.exit(3)\n")["error"]
    assert error.startswith("RuntimeError: sys.exit() is blocked by Scenario MCP\n")
    _assert_agent_frames_only(error)
    assert "_blocked_exit" not in error


def test_chained_errors_keep_agent_context_without_installed_sandbox_frame(fake_bpy):
    error = sandbox.run_python(
        "try:\n    {}['missing']\nexcept KeyError:\n    raise ValueError('agent failure')\n"
    )["error"]
    assert "KeyError: 'missing'" in error and "During handling of the above exception" in error
    assert error.rstrip().endswith("ValueError: agent failure")
    _assert_agent_frames_only(error)
