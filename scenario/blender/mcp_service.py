# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Lifecycle of the local MCP server inside Blender, plus client setup snippets."""

import json
import logging
import os
import sys

import bpy

from .. import __version__
from ..mcp import protocol
from ..mcp.cli import CLI_COMMAND, cli_banner
from ..mcp.server import McpServer
from . import runtime

log = logging.getLogger("scenario.mcp")
SERVER_INFO = {"name": "scenario-blender", "version": __version__}


def build_registry():
    from ..mcp import tools_blender, tools_scenario

    registry = protocol.Registry()
    for spec in tools_blender.SPECS + tools_scenario.SPECS:
        registry.add(spec)
    return registry


def status():
    server = runtime.state.mcp
    return {
        "running": bool(server and server.running),
        "url": server.url if server else "",
        "error": runtime.state.mcp_error,
        "calls": server.calls_served if server else 0,
    }


def start():
    if runtime.state.mcp is not None and runtime.state.mcp.running:
        return runtime.state.mcp
    if not runtime.online():
        runtime.state.mcp_error = "Allow Online Access is off"
        return None
    prefs = runtime.prefs()
    port = prefs.mcp_port if prefs else 9876
    try:
        server = McpServer(
            "127.0.0.1",
            port,
            build_registry(),
            SERVER_INFO,
            blender_version=bpy.app.version_string,
        )
        server.start()
    except OSError as err:
        runtime.state.mcp_error = str(err)
        runtime.state.mcp = None
        return None
    runtime.state.mcp = server
    runtime.state.mcp_error = ""
    return server


def stop():
    server = runtime.state.mcp
    if server is not None:
        server.stop()
    runtime.state.mcp = None


def process_pending():
    runtime.sync_catalog_context()
    server = runtime.state.mcp
    if server is not None:
        server.process_pending()


def _blender_python():
    candidates = [
        os.path.join(sys.prefix, "bin", f"python{sys.version_info.major}.{sys.version_info.minor}"),
        os.path.join(sys.prefix, "bin", "python3"),
    ]
    for path in candidates:
        if os.path.exists(path):
            return path
    return "python3"


def shim_path():
    return os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "mcp", "stdio_shim.py"
    )


def client_configs():
    url = status()["url"] or "http://127.0.0.1:9876/mcp"
    stdio = {
        "mcpServers": {
            "scenario-blender": {"command": _blender_python(), "args": [shim_path(), "--url", url]}
        }
    }
    return {
        "claude_code": f"claude mcp add --transport http scenario-blender {url}",
        "cursor": json.dumps({"mcpServers": {"scenario-blender": {"url": url}}}, indent=2),
        "claude_desktop": json.dumps(stdio, indent=2),
        "codex": f"codex mcp add scenario-blender --url {url}",
        "curl": f'curl -s -X POST {url} -H "Content-Type: application/json" -d \'{{"jsonrpc":"2.0","id":1,"method":"tools/list"}}\'',
    }


def cli(argv):
    """blender --background file.blend --command scenario_blender [--port N]"""
    import argparse
    import signal
    import threading

    parser = argparse.ArgumentParser(prog=CLI_COMMAND)
    parser.add_argument("--port", type=int, default=9876)
    # Accepted so existing scripts keep working; the server needs no token.
    parser.add_argument("--token", help=argparse.SUPPRESS)
    args = parser.parse_args(argv)
    if not 1 <= args.port <= 65535:
        parser.error("port must be between 1 and 65535")
    if not runtime.online():
        parser.error("Allow Online Access is off; enable it before starting local MCP")
    server = McpServer(
        "127.0.0.1",
        args.port,
        build_registry(),
        SERVER_INFO,
        blender_version=bpy.app.version_string,
    )
    stop_event = threading.Event()
    previous = {}
    try:
        for sig in (signal.SIGINT, signal.SIGTERM):
            previous[sig] = signal.signal(sig, lambda *_: stop_event.set())
        try:
            server.start()
        except OSError as error:
            parser.error(f"Unable to start local MCP: {error}")
        print(cli_banner(server.url), flush=True)
        server.serve_blocking(stop_event, before_process=runtime.sync_catalog_context)
    except KeyboardInterrupt:
        stop_event.set()
    finally:
        server.stop()
        for sig, handler in previous.items():
            # Blender can install a native handler that Python reports as None.
            # None is not accepted by signal.signal; the command is exiting.
            if handler is not None:
                signal.signal(sig, handler)
    return 0
