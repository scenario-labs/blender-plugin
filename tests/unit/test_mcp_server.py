# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Local MCP browser-origin, Host and bind-address boundaries."""

import ast
import socket
import threading
from pathlib import Path
from types import SimpleNamespace

import pytest

from scenario.mcp import server


def test_idle_blocking_loop_runs_maintenance_on_calling_thread_and_respects_stop():
    stop = threading.Event()
    calls = []
    owner = threading.get_ident()

    def maintain():
        calls.append(("maintain", threading.get_ident()))
        if len(calls) == 3:
            stop.set()

    def process():
        calls.append(("process", threading.get_ident()))
        return 0

    server.McpServer.serve_blocking(
        SimpleNamespace(process_pending=process), stop, interval=0, before_process=maintain
    )
    assert calls == [("maintain", owner), ("process", owner), ("maintain", owner)]


@pytest.mark.parametrize(
    "origin",
    [
        None,
        "http://127.0.0.1:39876",
        "http://localhost:9876",
        "http://LOCALHOST:9876",
        "http://[::1]:9876",
        "https://localhost",
    ],
)
def test_native_and_loopback_origins(origin):
    assert server.origin_allowed(origin)


@pytest.mark.parametrize(
    "origin",
    [
        "https://evil.example",
        "null",
        "",
        "127.0.0.1:9876",
        "http://127.0.0.1.evil.example",
        "ftp://localhost",
        "http://user@localhost",
        "http://localhost/path",
        "http://localhost?x=1",
        "http://localhost#fragment",
        "http://[::1",
        "http://localhost:65536",
        "http://localhost:bad",
        "http://localhost https://evil.example",
        " http://localhost",
        "http://local\nhost",
    ],
)
def test_non_origin_and_non_loopback_values_are_rejected(origin):
    assert not server.origin_allowed(origin)


@pytest.mark.parametrize(
    "host",
    [
        "127.0.0.1",
        "localhost",
        "LOCALHOST",
        "LocalHost:9876",
        "127.0.0.1:39876",
        "[::1]",
        "[::1]:9876",
        "localhost:1",
        "localhost:65535",
        " localhost:9876\t",
    ],
)
def test_loopback_hosts_with_and_without_port(host):
    assert server.host_allowed(host)


@pytest.mark.parametrize(
    "host",
    [
        None,
        "",
        "evil.example",
        "evil.example:9876",
        "127.0.0.1.evil.example",
        "localhost.evil.example:9876",
        "localhost.",
        "127.0.0.2",
        "0.0.0.0",
        "::1",
        "::1:9876",
        "[::1",
        "[::1]9876",
        "[0:0:0:0:0:0:0:1]",
        "[::ffff:127.0.0.1]",
        "localhost:",
        "localhost:0",
        "localhost:65536",
        "localhost:123456",
        "localhost:bad",
        "localhost:\u0669\u0668",
        "localhost:9876:1",
        "user@localhost",
        "localhost/path",
        "local host",
        b"localhost",
    ],
)
def test_rebinding_and_malformed_hosts_are_rejected(host):
    assert not server.host_allowed(host)


@pytest.mark.parametrize(
    "host", ["0.0.0.0", "", "192.168.1.20", "::", "::1", "localhost", "127.0.0.2", None]
)
def test_server_refuses_a_bind_address_other_than_ipv4_loopback(host):
    with pytest.raises(ValueError, match="binds only to 127.0.0.1"):
        server.McpServer(host, 0, None, {})


@pytest.mark.parametrize("idle", [0, -1, float("inf"), float("nan"), True, "60", None])
def test_idle_timeout_must_be_a_positive_finite_number(idle):
    with pytest.raises(ValueError, match="idle_timeout"):
        server.McpServer("127.0.0.1", 0, None, {}, idle_timeout=idle)


def test_idle_timeout_defaults_to_sixty_seconds_on_every_connection():
    owner = server.McpServer("127.0.0.1", 0, None, {})
    assert owner.idle_timeout == server.IDLE_TIMEOUT == 60.0
    assert server._make_handler(owner).timeout == 60.0
    short = server.McpServer("127.0.0.1", 0, None, {}, idle_timeout=0.25)
    assert server._make_handler(short).timeout == 0.25


def test_tool_execution_is_marked_only_while_a_handler_runs():
    owner = server.McpServer("127.0.0.1", 0, None, {}, timeout=5)
    seen = []

    def handler(arguments):
        seen.append(server.executing_tool())
        raise RuntimeError("a failing tool still ends the mark")

    pending = server._Pending(handler, {}, 5)
    owner._queue.put(pending)
    assert not server.executing_tool()
    assert owner.process_pending() == 1
    assert seen == [True]
    assert not server.executing_tool()
    with pytest.raises(RuntimeError, match="still ends"):
        pending.outcome()


def test_start_skips_the_reverse_dns_lookup_of_the_bind_address(monkeypatch):
    def lookup(host=""):
        raise AssertionError(f"start() resolved {host!r}; slow reverse DNS blocks the main thread")

    monkeypatch.setattr(socket, "getfqdn", lookup)
    owner = server.McpServer("127.0.0.1", 0, None, {})
    owner.start()
    try:
        assert owner._httpd.server_name == "127.0.0.1"
        assert owner._httpd.server_port == owner._httpd.server_address[1] > 0
    finally:
        owner.stop()
    assert not owner.running


def test_no_insecure_temporary_path_calls():
    root = Path(__file__).resolve().parents[2] / "scenario"
    offenders = []
    for path in root.rglob("*.py"):
        for node in ast.walk(ast.parse(path.read_text())):
            if (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Attribute)
                and node.func.attr == "mktemp"
            ):
                offenders.append(str(path.relative_to(root)))
    assert offenders == []
