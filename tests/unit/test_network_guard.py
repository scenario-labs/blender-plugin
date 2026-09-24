# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Prove the default unit-test connection guard and its explicit opt-out."""

import socket

import pytest


@pytest.mark.parametrize("method", ["connect", "connect_ex"])
@pytest.mark.parametrize("host", ["192.0.2.1", "api.example.invalid"])
def test_remote_connections_fail_before_using_the_socket(method, host):
    with socket.socket() as client:
        with pytest.raises(RuntimeError, match="network access is not allowed"):
            getattr(client, method)((host, 443))


def test_create_connection_cannot_escape_guard():
    with pytest.raises(RuntimeError, match="network access is not allowed"):
        socket.create_connection(("192.0.2.1", 443), timeout=0.2)


@pytest.mark.parametrize("method", ["connect", "connect_ex"])
def test_loopback_connection_still_reaches_local_server(method):
    with socket.socket() as server, socket.socket() as client:
        server.settimeout(1)
        client.settimeout(1)
        server.bind(("127.0.0.1", 0))
        server.listen(1)
        result = getattr(client, method)(server.getsockname())
        assert result == (None if method == "connect" else 0)
        peer, _ = server.accept()
        with peer:
            peer.sendall(b"local")
            assert client.recv(5) == b"local"


@pytest.mark.skipif(not hasattr(socket, "AF_UNIX"), reason="Unix sockets are unavailable")
def test_unix_socket_connection_is_local(tmp_path, monkeypatch):
    # Relative paths also work when pytest's temporary root exceeds sun_path.
    monkeypatch.chdir(tmp_path)
    address = "unit.sock"
    with socket.socket(socket.AF_UNIX) as server, socket.socket(socket.AF_UNIX) as client:
        server.settimeout(1)
        client.settimeout(1)
        server.bind(address)
        server.listen(1)
        client.connect(address)
        peer, _ = server.accept()
        peer.close()


@pytest.mark.allow_network
def test_explicit_opt_out_restores_inherited_socket_methods():
    # No remote request is necessary to prove the fixture did not install wrappers.
    assert "connect" not in vars(socket.socket)
    assert "connect_ex" not in vars(socket.socket)
