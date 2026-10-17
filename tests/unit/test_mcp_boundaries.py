# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Local MCP Host check and idle connection timeout over real loopback sockets."""

import http.client
import json
import socket
import threading
import time
from unittest.mock import Mock

import pytest

from scenario.mcp import protocol, server

CALL = {
    "jsonrpc": "2.0",
    "id": 1,
    "method": "tools/call",
    "params": {"name": "echo", "arguments": {}},
}


@pytest.fixture
def owner(request, monkeypatch):
    """A started server whose main-thread queue a pump thread drains, as Blender's pump does."""
    options = getattr(request, "param", {})
    calls = []

    def echo(arguments):
        time.sleep(options.get("tool_seconds", 0))
        calls.append(arguments)
        return {"ok": True}

    registry = protocol.Registry()
    registry.add(protocol.ToolSpec("echo", "Echo", {"type": "object"}, echo))
    mcp = server.McpServer(
        "127.0.0.1",
        0,
        registry,
        {"name": "fixture", "version": "0"},
        timeout=5,
        blender_version="fixture-blender",
        idle_timeout=options.get("idle", server.IDLE_TIMEOUT),
    )
    monkeypatch.setattr(mcp, "handle", Mock(wraps=mcp.handle))
    mcp.calls = calls
    stop = threading.Event()

    def pump():
        while not stop.is_set():
            mcp.process_pending()
            stop.wait(0.005)

    mcp.start()
    mcp.bound = mcp._httpd.server_port  # Port 0 asks the OS for a free one.
    thread = threading.Thread(target=pump, daemon=True)
    thread.start()
    try:
        yield mcp
    finally:
        stop.set()
        thread.join(2)
        mcp.stop()


def send(owner, method, path, *, hosts=("localhost",), body=None, extra=()):
    raw = json.dumps(body).encode() if body is not None else b""
    lines = [f"{method} {path} HTTP/1.1"]
    lines += [f"Host: {host}" for host in hosts]
    lines += [f"{name}: {value}" for name, value in extra]
    lines.append(f"Content-Length: {len(raw)}")
    with socket.create_connection(("127.0.0.1", owner.bound), timeout=5) as client:
        client.sendall(("\r\n".join(lines) + "\r\n\r\n").encode("latin-1") + raw)
        response = http.client.HTTPResponse(client)
        response.begin()
        payload = response.read()
    return response, (json.loads(payload) if payload else None)


def closed_by_server(client, within):
    """True when the server closes the connection without sending a response byte."""
    client.settimeout(within)
    try:
        return client.recv(1) == b""
    except TimeoutError:
        return False


ROUTES = [
    ("GET", "/health", None),
    ("GET", "/mcp", None),
    ("POST", "/mcp", CALL),
    ("POST", "/missing", CALL),
    ("DELETE", "/mcp", None),
    ("OPTIONS", "/mcp", None),
]


@pytest.mark.parametrize("method,path,body", ROUTES)
@pytest.mark.parametrize(
    "host", ["evil.example", "evil.example:{port}", "127.0.0.1.evil.example", "[::2]:{port}"]
)
def test_rebinding_host_is_refused_before_routing(owner, method, path, body, host):
    response, payload = send(owner, method, path, hosts=[host.format(port=owner.bound)], body=body)
    assert response.status == 403
    assert payload == {"error": "forbidden host"}
    assert response.getheader("Connection") == "close"
    assert response.getheader("Access-Control-Allow-Origin") is None
    owner.handle.assert_not_called()
    assert owner.calls == []


@pytest.mark.parametrize("method,path,body", ROUTES)
@pytest.mark.parametrize("hosts", [[], ["localhost", "localhost"], ["localhost", "evil.example"]])
def test_missing_or_repeated_host_is_a_bad_request(owner, method, path, body, hosts):
    response, payload = send(owner, method, path, hosts=hosts, body=body)
    assert response.status == 400
    assert payload == {"error": "exactly one Host header is required"}
    owner.handle.assert_not_called()


def test_host_is_checked_before_origin(owner):
    for origin in ("https://evil.example", None, "null"):
        extra = [("Origin", origin)] if origin else []
        response, payload = send(
            owner, "POST", "/mcp", hosts=["evil.example"], body=CALL, extra=extra
        )
        assert (response.status, payload) == (403, {"error": "forbidden host"})
    response, payload = send(owner, "POST", "/mcp", body=CALL, extra=[("Origin", "null")])
    assert (response.status, payload) == (403, {"error": "forbidden origin"})
    owner.handle.assert_not_called()


@pytest.mark.parametrize(
    "host",
    [
        "localhost",
        "localhost:{port}",
        "LOCALHOST:{port}",
        "127.0.0.1",
        "127.0.0.1:{port}",
        "[::1]",
        "[::1]:{port}",
    ],
)
def test_loopback_host_reaches_health_and_tools(owner, host):
    host = host.format(port=owner.bound)
    response, payload = send(owner, "GET", "/health", hosts=[host])
    assert response.status == 200
    assert payload == {
        "ok": True,
        "blender": "fixture-blender",
        "server": {"name": "fixture", "version": "0"},
    }
    response, payload = send(owner, "POST", "/mcp", hosts=[host], body=CALL)
    assert response.status == 200
    assert json.loads(payload["result"]["content"][0]["text"]) == {"ok": True}
    assert owner.calls == [{}]


def test_tools_need_no_authorization_and_ignore_a_supplied_one(owner):
    for extra in ([], [("Authorization", "Bearer from-an-older-setup")]):
        response, payload = send(owner, "POST", "/mcp", body=CALL, extra=extra)
        assert response.status == 200
        assert json.loads(payload["result"]["content"][0]["text"]) == {"ok": True}
    assert owner.calls == [{}, {}]


@pytest.mark.parametrize("owner", [{"idle": 0.2}], indirect=True)
def test_idle_connection_is_closed_after_the_idle_timeout(owner):
    with socket.create_connection(("127.0.0.1", owner.bound), timeout=5) as client:
        started = time.monotonic()
        assert closed_by_server(client, within=3)
        assert time.monotonic() - started >= 0.15


@pytest.mark.parametrize("owner", [{"idle": 0.2}], indirect=True)
def test_stalled_headers_and_body_are_closed_without_dispatch(owner):
    for partial in (
        b"GET /health HTTP/1.1\r\nHost: localhost\r\n",
        b'POST /mcp HTTP/1.1\r\nHost: localhost\r\nContent-Length: 100\r\n\r\n{"jsonrpc"',
    ):
        with socket.create_connection(("127.0.0.1", owner.bound), timeout=5) as client:
            client.sendall(partial)
            assert closed_by_server(client, within=3)
    owner.handle.assert_not_called()


@pytest.mark.parametrize("owner", [{"idle": 0.2}], indirect=True)
def test_idle_keep_alive_connection_closes_after_a_response(owner):
    with socket.create_connection(("127.0.0.1", owner.bound), timeout=5) as client:
        client.sendall(b"GET /health HTTP/1.1\r\nHost: localhost\r\n\r\n")
        response = http.client.HTTPResponse(client)
        response.begin()
        assert response.status == 200
        assert response.getheader("Connection") is None  # HTTP/1.1 keeps it open
        response.read()
        assert closed_by_server(client, within=3)


@pytest.mark.parametrize("owner", [{"idle": 0.2, "tool_seconds": 0.6}], indirect=True)
def test_idle_timeout_does_not_cut_a_request_waiting_for_the_main_thread(owner):
    # The HTTP thread reads nothing while the tool runs, so only the tool timeout applies.
    started = time.monotonic()
    response, payload = send(owner, "POST", "/mcp", body=CALL)
    assert time.monotonic() - started >= 0.6
    assert response.status == 200
    assert json.loads(payload["result"]["content"][0]["text"]) == {"ok": True}
    assert owner.calls == [{}]
