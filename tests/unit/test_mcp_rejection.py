# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Early MCP errors survive a delayed body without dispatch or unbounded drain."""

import http.client
import socket
import threading
from unittest.mock import Mock

import pytest

from scenario.mcp import server


@pytest.fixture
def listener(monkeypatch):
    make_handler = server._make_handler
    finished = threading.Event()

    def observed_handler(owner):
        class Observed(make_handler(owner)):
            def finish(self):
                try:
                    super().finish()
                finally:
                    finished.set()

        return Observed

    monkeypatch.setattr(server, "_make_handler", observed_handler)
    owner = server.McpServer("127.0.0.1", 0, "fixture-token", None, {})
    owner.handle = Mock(side_effect=AssertionError("A rejected request must not dispatch"))
    owner.start()
    try:
        yield owner, finished, ("127.0.0.1", owner._httpd.server_port)
    finally:
        owner.stop()
        assert finished.wait(2), "Rejected connection did not finish"
        owner.handle.assert_not_called()


def begin(client, *, method="POST", path="/mcp", token="fixture-token", extra=()):
    headers = [
        f"{method} {path} HTTP/1.1",
        "Host: localhost",
        f"Authorization: Bearer {token}",
        *(f"{name}: {value}" for name, value in extra),
    ]
    client.sendall(("\r\n".join(headers) + "\r\n\r\n").encode("ascii"))
    response = http.client.HTTPResponse(client)
    response.begin()
    assert response.getheader("Connection") == "close"
    assert response.getheader("Access-Control-Allow-Origin") is None
    assert response.read()
    return response


@pytest.mark.parametrize(
    "options,status",
    [
        ({"extra": [("Origin", "https://evil.example")]}, 403),
        ({"token": "wrong"}, 401),
        ({"path": "/missing"}, 404),
        ({"method": "OPTIONS"}, 403),
    ],
)
def test_error_arrives_before_delayed_body_and_connection_drains(listener, options, status):
    _owner, finished, address = listener
    options = dict(options)
    options["extra"] = [*options.get("extra", []), ("Content-Length", "5")]
    with socket.create_connection(address, timeout=2) as client:
        response = begin(client, **options)
        assert response.status == status
        if status == 401:
            assert response.getheader("WWW-Authenticate") == "Bearer"
        assert not finished.wait(0.05), "Connection closed before the declared body arrived"
        client.sendall(b"abcde")
        assert finished.wait(2)


def test_stalled_rejected_body_has_a_total_deadline(listener, monkeypatch):
    monkeypatch.setattr(server, "REJECT_DRAIN_TIMEOUT", 0.1)
    _owner, finished, address = listener
    with socket.create_connection(address, timeout=2) as client:
        response = begin(client, extra=[("Origin", "null"), ("Content-Length", "100")])
        assert response.status == 403
        assert finished.wait(1), "An absent body must not retain the handler"


def test_trickling_bytes_do_not_extend_rejection_deadline(listener, monkeypatch):
    monkeypatch.setattr(server, "REJECT_DRAIN_TIMEOUT", 0.1)
    _owner, finished, address = listener
    stop = threading.Event()
    with socket.create_connection(address, timeout=2) as client:
        assert begin(client, token="wrong", extra=[("Content-Length", "1000")]).status == 401

        def trickle():
            while not stop.wait(0.02):
                try:
                    client.sendall(b"x")
                except OSError:
                    return

        sender = threading.Thread(target=trickle)
        sender.start()
        try:
            assert finished.wait(0.5), "Each arriving byte must not restart the drain budget"
        finally:
            stop.set()
            sender.join(2)
        assert not sender.is_alive()


@pytest.mark.parametrize(
    "framing,status",
    [
        ([("Content-Length", "-1")], 400),
        ([("Content-Length", "invalid")], 400),
        ([("Content-Length", "1"), ("Content-Length", "1")], 400),
        ([("Transfer-Encoding", "chunked")], 400),
        ([("Content-Length", "1"), ("Transfer-Encoding", "chunked")], 400),
        ([("Content-Length", str(server.MAX_BODY + 1))], 413),
        ([("Content-Length", "9" * 100)], 400),
    ],
)
def test_ambiguous_or_oversized_body_is_rejected_without_waiting(listener, framing, status):
    _owner, finished, address = listener
    with socket.create_connection(address, timeout=2) as client:
        assert begin(client, extra=framing).status == status
        assert finished.wait(0.5), "Unsafe framing must not start a body drain"
