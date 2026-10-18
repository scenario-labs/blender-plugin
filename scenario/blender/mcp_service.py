# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Lifecycle of the local MCP server inside Blender, plus client setup snippets."""

import json
import logging
import os
import sys

import bpy

from .. import __version__
from ..mcp import client_setup, protocol
from ..mcp.cli import CLI_COMMAND, cli_banner
from ..mcp.server import McpServer
from . import runtime, usage

log = logging.getLogger("scenario.mcp")
SERVER_INFO = {"name": "scenario-blender", "version": __version__}
OFFLINE = "Allow Online Access is off"


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


def start(*, by_user=False):
    if by_user:
        runtime.state.mcp_stopped_by_user = False
    if runtime.state.mcp is not None and runtime.state.mcp.running:
        return runtime.state.mcp
    if not runtime.online():
        runtime.state.mcp_error = OFFLINE
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
            observer=usage.MCP_OBSERVER,
        )
        server.start()
    except OSError as err:
        runtime.state.mcp_error = str(err)
        runtime.state.mcp = None
        return None
    runtime.state.mcp = server
    runtime.state.mcp_error = ""
    return server


def stop(*, by_user=False):
    if by_user:
        runtime.state.mcp_stopped_by_user = True
    server = runtime.state.mcp
    if server is not None:
        server.stop()
    runtime.state.mcp = None


def start_with_extension():
    """Start when the extension registers in a Blender window, then follow online access."""
    runtime.state.mcp_online = runtime.online()
    runtime.state.mcp_stopped_by_user = False
    return start()


def follow_online_access():
    """Start or stop the server when Allow Online Access is switched, without a restart.

    The GUI pump calls this every tick. Only start_with_extension arms it, so
    background Blender keeps the explicit scenario_blender command. After Stop
    MCP server the server stays stopped; a failed start waits for the next switch
    or Start MCP server instead of retrying every tick. Returns True when the
    status the panel draws changed.
    """
    previous = runtime.state.mcp_online
    online = runtime.online()
    if previous is None or online == previous:
        return False
    runtime.state.mcp_online = online
    if not online:
        stop()
        runtime.state.mcp_error = OFFLINE
    elif runtime.state.mcp_stopped_by_user:
        runtime.state.mcp_error = ""
    else:
        start()
    return True


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


def server_url():
    """The running server's URL, else the one the MCP Port preference will serve."""
    server = runtime.state.mcp
    if server is not None and server.running:
        return server.url
    prefs = runtime.prefs()
    return f"http://127.0.0.1:{prefs.mcp_port if prefs else 9876}/mcp"


# What the last Connect wrote, as panel lines. Main thread only.
connect_report = []


def connect_clients(home=None, environ=None):
    """The clients Connect can configure, in panel order, with whether each was found."""
    return client_setup.clients(home or os.path.expanduser("~"), environ)


def connect(key, home=None, environ=None):
    """Write the scenario-blender entry into one client's configuration; returns the report lines."""
    client = next((c for c in connect_clients(home, environ) if c.key == key), None)
    if client is None:
        raise ValueError(f"Unknown client {key!r}")
    url = server_url()
    entry = client_setup.entry(key, url, _blender_python(), shim_path())
    try:
        written = client_setup.write(client, entry, url)
    except (client_setup.SetupError, OSError) as error:
        connect_report[:] = [f"{client.label}: not changed, {error}"]
        raise
    lines = [f"{client.label}: wrote {client_setup.SERVER_NAME} to {written.path}", f"URL {url}"]
    if written.backup is not None:
        lines.append(f"Previous file kept as {written.backup.name}")
    lines.append(f"Then {client.reload_hint}")
    connect_report[:] = lines
    return lines


def client_configs():
    url = server_url()

    def servers(key):
        entry = client_setup.entry(key, url, _blender_python(), shim_path())
        return json.dumps({"mcpServers": {client_setup.SERVER_NAME: entry}}, indent=2)

    return {
        "claude_code": f"claude mcp add --transport http scenario-blender {url}",
        "cursor": servers("cursor"),
        "claude_desktop": servers("claude_desktop"),
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
        observer=usage.MCP_OBSERVER,
    )
    stop_event = threading.Event()
    previous = {}
    failures = {}

    def before_process():
        # Usage data must never end the command or drop its agents' connections.
        try:
            usage.tick()
            failures.pop("usage", None)
        except Exception as error:  # report each new failure once, as the pump does
            if type(error).__name__ != failures.get("usage"):
                failures["usage"] = type(error).__name__
                log.exception("usage data upkeep failed")
        runtime.sync_catalog_context()

    # Background Blender shares usage only here, where this loop follows online access.
    usage.activate()
    try:
        for sig in (signal.SIGINT, signal.SIGTERM):
            previous[sig] = signal.signal(sig, lambda *_: stop_event.set())
        try:
            server.start()
        except OSError as error:
            parser.error(f"Unable to start local MCP: {error}")
        print(cli_banner(server.url), flush=True)
        server.serve_blocking(stop_event, before_process=before_process)
    except KeyboardInterrupt:
        stop_event.set()
    finally:
        server.stop()
        # Blender exits after this command: give queued usage events one bounded send.
        usage.deactivate(wait=usage.FINAL_SEND_WAIT)
        for sig, handler in previous.items():
            # Blender can install a native handler that Python reports as None.
            # None is not accepted by signal.signal; the command is exiting.
            if handler is not None:
                signal.signal(sig, handler)
    return 0
