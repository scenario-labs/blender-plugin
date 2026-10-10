# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Opt-in execute_python error text: the agent's frames, never the extension's own."""

import os
import sys
import traceback
import types

import pytest

from scenario.mcp import sandbox

_DIVE = "def dive(depth):\n    return dive(depth + 1)\n"
_LEAVE = "def leave():\n    import sys\n    sys.exit(3)\n"
_FAILURES = {
    "raise": ("def place():\n    raise ValueError('agent failure')\nplace()\n", False),
    "raise-from": (
        "def load():\n    {}['missing']\n"
        "try:\n    load()\nexcept KeyError as exc:\n    raise ValueError('wrapped') from exc\n",
        False,
    ),
    "implicit-context": (
        "def load():\n    {}['missing']\n"
        "try:\n    load()\nexcept KeyError:\n    raise ValueError('while handling')\n",
        False,
    ),
    "blocked-exit": (_LEAVE + "leave()\n", False),
    "group-member": (
        _LEAVE + "try:\n    leave()\nexcept RuntimeError as exc:\n"
        "    raise ExceptionGroup('batch failed', [exc])\n",
        False,
    ),
    "deep-recursion": (_DIVE + "dive(0)\n", True),
    "deep-recursion-chained": (
        _DIVE + "try:\n    dive(0)\nexcept RecursionError as exc:\n"
        "    raise ValueError('too deep') from exc\n",
        True,
    ),
}


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


def _full_walk(exc, limit=4):
    """Reference text: extract every frame of every chain link, then keep the agent's first ones.

    Returns the text, the number of formatted exceptions and the number of frames a full walk
    extracts.
    """
    report = traceback.TracebackException(type(exc), exc, exc.__traceback__)
    pending, seen, extracted = [report], set(), 0
    while pending:
        item = pending.pop()
        if item is None or id(item) in seen:
            continue
        seen.add(id(item))
        extracted += len(item.stack)
        frames = [frame for frame in item.stack if frame.filename != sandbox.__file__]
        item.stack = traceback.StackSummary.from_list(frames[:limit])
        pending += [item.__cause__, item.__context__, *(item.exceptions or ())]
    return "".join(report.format()), len(seen), extracted


@pytest.mark.parametrize(("code", "deep"), _FAILURES.values(), ids=list(_FAILURES))
def test_traceback_extraction_is_bounded_and_matches_a_full_walk(fake_bpy, monkeypatch, code, deep):
    failures, built = [], []
    agent_traceback, frame_init = sandbox._agent_traceback, traceback.FrameSummary.__init__

    def recording(exc):
        failures.append(exc)
        return agent_traceback(exc)

    def counting_init(self, *args, **kwargs):
        built.append(1)
        frame_init(self, *args, **kwargs)

    monkeypatch.setattr(sandbox, "_agent_traceback", recording)
    monkeypatch.setattr(traceback.FrameSummary, "__init__", counting_init)
    error = sandbox.run_python(code)["error"]
    extracted = len(built)

    (exc,) = failures
    expected, exceptions, full_walk_frames = _full_walk(exc)
    assert error == f"{type(exc).__name__}: {exc}\n{expected}"
    _assert_agent_frames_only(error)
    # run_python's own frame leads the traceback; at most four agent frames follow it.
    assert extracted <= exceptions * (4 + 1)
    if deep:
        assert full_walk_frames > 10 * exceptions * (4 + 1)
