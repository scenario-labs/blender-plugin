# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Run agent-authored Python on Blender's main thread with output capture and a few hard blocks.

This is a guard rail, not a security boundary: it blocks a few known destructive calls and reports
other execution results to the agent. It cannot make arbitrary Python safe.

The local MCP design acknowledges Blender Lab's blender_mcp project
(GPL-3.0-or-later, Blender Authors) as a design reference.
Upstream uses a separate stdio MCP server and TCP add-on
connection; this extension uses authenticated loopback HTTP and main-thread tool dispatch.
"""

# Design reference: https://projects.blender.org/lab/blender_mcp

import contextlib
import io
import json
import re
import sys
import traceback

BLOCKED_TOKENS = (
    "quit_blender",
    "read_factory_settings",
    "read_factory_userpref",
    "read_userpref",
    "os._exit",
    "os.kill",
    "shutil.rmtree",
    "os.remove",
    "os.unlink",
)
_TOKEN_RE = re.compile("|".join(re.escape(t) for t in BLOCKED_TOKENS))


def _blocked_exit(*args, **kwargs):
    raise RuntimeError("sys.exit() is blocked by Scenario MCP")


def blocked_token(code):
    match = _TOKEN_RE.search(code or "")
    return match.group(0) if match else None


def run_python(code):
    """Execute code with bpy and an empty result dict preloaded. Returns result, stdout, stderr and error."""
    import bpy

    token = blocked_token(code)
    if token:
        return {
            "result": {},
            "stdout": "",
            "stderr": "",
            "error": f"blocked by Scenario MCP: {token} is not allowed from an agent",
        }
    namespace = {"bpy": bpy, "result": {}, "__name__": "__scenario_mcp__"}
    out, err = io.StringIO(), io.StringIO()
    saved_exit = sys.exit
    sys.exit = _blocked_exit
    error = None
    try:
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            exec(
                compile(code, "<scenario-mcp>", "exec"), namespace
            )  # gated by a preference; this is the tool's purpose
    except Exception as exc:  # returned to the agent, never raised into Blender
        error = f"{type(exc).__name__}: {exc}\n{traceback.format_exc(limit=4)}"
    finally:
        sys.exit = saved_exit
    result = namespace.get("result")
    if not isinstance(result, dict):
        result = {"value": repr(result)}
    try:
        json.dumps(result)
    except (TypeError, ValueError):
        result = {key: repr(value) for key, value in result.items()}
    payload = {
        "result": result,
        "stdout": out.getvalue()[-20000:],
        "stderr": err.getvalue()[-20000:],
    }
    if error:
        payload["error"] = error
    return payload
