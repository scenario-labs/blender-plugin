# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Storage transport contracts without sockets or signed production URLs."""

import hashlib
import io
import logging
import ssl
from dataclasses import asdict
from pathlib import Path
from unittest.mock import Mock

import pytest

from scenario.core.jobs import transfers

URL = "https://storage.example.invalid/result?signature=private-fixture"
DATA = b"offline result bytes"


class Response(io.BytesIO):
    def __init__(self, data=DATA, *, status=200, headers=None):
        super().__init__(data)
        self.status = status
        self.headers = {"Content-Length": str(len(data))} if headers is None else headers

    def getheader(self, key, default=None):
        return self.headers.get(key, default)


@pytest.fixture
def storage(monkeypatch):
    connection = Mock()
    connection.getresponse.return_value = Response()
    constructor = Mock(return_value=connection)
    monkeypatch.setattr(transfers.http.client, "HTTPSConnection", constructor)
    return connection, constructor


def downloader(**kwargs):
    return transfers.ResultDownloader(
        transfers.StoragePolicy(frozenset({"storage.example.invalid"}), **kwargs),
        online_access=lambda: True,
    )


def test_success_ignores_ambient_secrets_and_does_not_log_url(
    tmp_path, monkeypatch, storage, caplog
):
    for key in (
        "HTTP_PROXY",
        "HTTPS_PROXY",
        "ALL_PROXY",
        "SSLKEYLOGFILE",
        "SSL_CERT_FILE",
        "SSL_CERT_DIR",
    ):
        monkeypatch.setenv(key, str(tmp_path / "must-not-be-opened"))
    caplog.set_level(logging.DEBUG)
    conn, constructor = storage
    result = downloader().download(
        URL,
        root=tmp_path,
        name="result.bin",
        expected_size=len(DATA),
        expected_sha256=hashlib.sha256(DATA).hexdigest(),
    )
    assert (tmp_path / result.name).read_bytes() == DATA
    assert result.size == len(DATA)
    assert result.sha256 == hashlib.sha256(DATA).hexdigest()
    assert list(tmp_path.iterdir()) == [tmp_path / result.name]
    assert "private-fixture" not in repr(result) + str(asdict(result)) + caplog.text
    context = constructor.call_args.kwargs["context"]
    assert context.verify_mode == ssl.CERT_REQUIRED and context.check_hostname
    assert context.keylog_filename is None
    conn.request.assert_called_once_with(
        "GET",
        "/result?signature=private-fixture",
        headers={"Accept-Encoding": "identity", "Connection": "close"},
    )
    conn.close.assert_called_once()


@pytest.mark.parametrize(
    "url",
    [
        "http://storage.example.invalid/a",
        "https://other.example.invalid/a",
        "https://storage.example.invalid.evil.invalid/a",
        "https://user:secret@storage.example.invalid/a",
        "https://storage.example.invalid:444/a",
        "https://storage.example.invalid/a#secret",
        "https://storage.example.invalid/a\n?secret",
        "https://storage.example.invalid/é",
        "https://storage.example.invalid\\@other.example.invalid/a",
        "https://127.0.0.1/a",
        "https://STORAGE.example.invalid/a",
        "https://storage.example.invalid./a",
        "https://storage.example.invalid:bad/a",
        None,
    ],
)
def test_rejected_destination_never_connects(url, tmp_path, storage):
    with pytest.raises(transfers.TransferError, match="destination rejected"):
        downloader().download(url, root=tmp_path, name="x")
    storage[1].assert_not_called()
    assert not list(tmp_path.iterdir())


@pytest.mark.parametrize(
    "hosts",
    [
        frozenset(),
        {"storage.example.invalid"},
        frozenset({"*.example.invalid"}),
        frozenset({"127.0.0.1"}),
        frozenset({"0x7f.0.0.1"}),
        frozenset({"127.0.0.0x1"}),
        frozenset({"0x7f.1"}),
        frozenset({"0177.0.0.1"}),
        frozenset({"localhost"}),
        frozenset({"printer.local"}),
        frozenset({"user@host.invalid"}),
    ],
)
def test_reject_invalid_allowlist(hosts):
    with pytest.raises(ValueError):
        transfers.StoragePolicy(hosts)


@pytest.mark.parametrize(
    "name",
    [
        "../result",
        "/result",
        "a/b",
        "a\\b",
        "CON.txt",
        "NUL",
        ".part",
        "x.",
        "x:stream",
        "",
        "x" * 121,
    ],
)
def test_reject_unsafe_filename(name, tmp_path, storage):
    with pytest.raises(transfers.TransferError):
        downloader().download(URL, root=tmp_path, name=name)
    storage[1].assert_not_called()


def test_offline_never_constructs_connection(tmp_path, storage):
    client = transfers.ResultDownloader(
        transfers.StoragePolicy(frozenset({"storage.example.invalid"})), online_access=lambda: False
    )
    with pytest.raises(transfers.TransferError, match="Online access"):
        client.download(URL, root=tmp_path, name="x")
    storage[1].assert_not_called()


@pytest.mark.parametrize("status", [301, 302, 307, 308, 400, 401, 404, 500, 206])
def test_status_never_follows_redirect_or_retries(status, tmp_path, storage):
    storage[0].getresponse.return_value = Response(
        status=status, headers={"Location": "https://evil.invalid/private"}
    )
    with pytest.raises(transfers.TransferError):
        downloader().download(URL, root=tmp_path, name="x")
    assert storage[0].request.call_count == 1
    assert not list(tmp_path.iterdir())


@pytest.mark.parametrize(
    "headers",
    [
        {"Content-Length": "2000"},
        {"Content-Length": "-1"},
        {"Content-Length": "1, 1"},
        {"Content-Length": "x"},
        {"Content-Length": "1"},
        {"Content-Encoding": "gzip"},
        {"Content-Length": "21"},
        {"Transfer-Encoding": "chunked"},
    ],
)
def test_invalid_response_cleans_staging(headers, tmp_path, storage):
    storage[0].getresponse.return_value = Response(headers=headers)
    with pytest.raises(transfers.TransferError):
        downloader(max_bytes=20).download(URL, root=tmp_path, name="x")
    assert not list(tmp_path.iterdir())


def test_stream_without_length_is_still_bounded(tmp_path, storage):
    storage[0].getresponse.return_value = Response(b"x" * 25, headers={})
    with pytest.raises(transfers.TransferError, match="byte limit"):
        downloader(max_bytes=20).download(URL, root=tmp_path, name="x")
    assert not list(tmp_path.iterdir())


@pytest.mark.parametrize(
    "expectations",
    [
        {"expected_size": 1},
        {"expected_sha256": "a" * 64},
        {"expected_sha256": "secret"},
        {"expected_size": True},
        {"expected_size": -1},
    ],
)
def test_mismatched_or_invalid_expectation_fails(expectations, tmp_path, storage):
    with pytest.raises(transfers.TransferError):
        downloader().download(URL, root=tmp_path, name="x", **expectations)
    assert not list(tmp_path.iterdir())


def test_existing_result_and_symlink_are_not_overwritten(tmp_path, storage):
    existing = tmp_path / "original"
    existing.write_bytes(b"keep")
    for name in ("original", "link"):
        if name == "link":
            (tmp_path / name).symlink_to(existing)
        with pytest.raises(transfers.TransferError, match="already exists"):
            downloader().download(URL, root=tmp_path, name=name)
    assert existing.read_bytes() == b"keep"
    storage[1].assert_not_called()


def test_symlink_root_rejected(tmp_path, storage):
    (tmp_path / "real").mkdir()
    (tmp_path / "alias").symlink_to(tmp_path / "real", target_is_directory=True)
    with pytest.raises(transfers.TransferError):
        downloader().download(URL, root=tmp_path / "alias", name="x")
    storage[1].assert_not_called()


@pytest.mark.parametrize(
    "failure", [TimeoutError(URL), OSError(URL), KeyboardInterrupt(), SystemExit()]
)
def test_read_failure_cleans_up_and_redacts_ordinary_errors(failure, tmp_path, storage):
    response = Response()
    response.read1 = Mock(side_effect=failure)
    storage[0].getresponse.return_value = response
    expected = (
        type(failure)
        if isinstance(failure, (KeyboardInterrupt, SystemExit))
        else transfers.TransferError
    )
    with pytest.raises(expected) as caught:
        downloader().download(URL, root=tmp_path, name="x")
    assert "private-fixture" not in str(caught.value)
    assert not list(tmp_path.iterdir())
    storage[0].close.assert_called_once()


def test_publication_race_preserves_other_writer(tmp_path, storage, monkeypatch):
    real_link = transfers.os.link

    def competing_link(source, destination):
        Path(destination).write_bytes(b"other writer")
        real_link(source, destination)

    monkeypatch.setattr(transfers.os, "link", competing_link)
    with pytest.raises(transfers.TransferError):
        downloader().download(URL, root=tmp_path, name="x")
    assert (tmp_path / "x").read_bytes() == b"other writer"
    assert list(tmp_path.iterdir()) == [tmp_path / "x"]


def test_revoked_permission_during_read_never_publishes(tmp_path, storage):
    permitted = True
    original_read = storage[0].getresponse.return_value.read1

    def read(size):
        nonlocal permitted
        permitted = False
        return original_read(size)

    storage[0].getresponse.return_value.read1 = read
    client = transfers.ResultDownloader(
        transfers.StoragePolicy(frozenset({"storage.example.invalid"})),
        online_access=lambda: permitted,
    )
    with pytest.raises(transfers.TransferError, match="interrupted"):
        client.download(URL, root=tmp_path, name="x")
    assert not list(tmp_path.iterdir())


def test_total_deadline_applies_after_read_before_publish(tmp_path, storage, monkeypatch):
    clock = 0.0
    monkeypatch.setattr(transfers.time, "monotonic", lambda: clock)
    original_read = storage[0].getresponse.return_value.read1

    def read(size):
        nonlocal clock
        clock += 2
        return original_read(size)

    storage[0].getresponse.return_value.read1 = read
    with pytest.raises(transfers.TransferError, match="interrupted"):
        downloader(total_timeout=1).download(URL, root=tmp_path, name="x")
    assert not list(tmp_path.iterdir())


def test_disk_sync_failure_does_not_publish(tmp_path, storage, monkeypatch):
    monkeypatch.setattr(transfers.os, "fsync", Mock(side_effect=OSError("disk full")))
    with pytest.raises(transfers.TransferError):
        downloader().download(URL, root=tmp_path, name="x")
    assert not list(tmp_path.iterdir())


def test_eof_closes_socket_before_atomic_publication(tmp_path, storage):
    conn = storage[0]
    conn.sock.fileno.return_value = 12
    original_read = conn.getresponse.return_value.read1

    def read(size):
        result = original_read(size)
        if not result:
            conn.sock.fileno.return_value = -1
            conn.sock.settimeout.side_effect = OSError("Socket already closed")
        return result

    conn.getresponse.return_value.read1 = read
    assert downloader().download(URL, root=tmp_path, name="x").size == len(DATA)


@pytest.mark.parametrize(
    "declared,valid", [(str(len(DATA)), True), (str(len(DATA) + 1), False), (None, True)]
)
def test_real_http_response_framing(declared, valid, tmp_path, storage):
    import http.client

    headers = f"Content-Length: {declared}\r\n" if declared is not None else ""
    wire = b"HTTP/1.1 200 OK\r\nConnection: close\r\n" + headers.encode() + b"\r\n" + DATA
    socket = Mock()
    socket.makefile.return_value = io.BytesIO(wire)
    response = http.client.HTTPResponse(socket)
    response.begin()
    storage[0].getresponse.return_value = response
    if valid:
        result = downloader().download(URL, root=tmp_path, name="x")
        assert result.size == len(DATA)
        assert (tmp_path / "x").read_bytes() == DATA
    else:
        with pytest.raises(transfers.TransferError, match="incomplete"):
            downloader().download(URL, root=tmp_path, name="x")
        assert not list(tmp_path.iterdir())


@pytest.mark.parametrize(
    "kwargs",
    [
        {"max_bytes": 0},
        {"max_bytes": True},
        {"timeout": float("nan")},
        {"timeout": 0},
        {"total_timeout": float("inf")},
        {"total_timeout": -1},
    ],
)
def test_invalid_policy_limits(kwargs):
    with pytest.raises(ValueError):
        downloader(**kwargs)


def test_connect_failure_redacted_without_retry(tmp_path, storage):
    storage[0].connect.side_effect = OSError(URL)
    with pytest.raises(transfers.TransferError) as caught:
        downloader().download(URL, root=tmp_path, name="x")
    assert "private-fixture" not in str(caught.value)
    storage[0].connect.assert_called_once()
    storage[0].set_debuglevel.assert_called_once_with(0)
    storage[0].request.assert_not_called()
    storage[0].close.assert_called_once()


def test_missing_root_reports_local_setup_error_before_network(tmp_path, storage):
    root = tmp_path / "missing-private-result-directory"
    with pytest.raises(
        transfers.TransferError, match="existing absolute private result directory"
    ) as caught:
        downloader().download(URL, root=root, name="result.bin")
    assert str(root) not in str(caught.value)
    storage[1].assert_not_called()
    assert not root.exists()


def test_root_permission_failure_reports_local_setup_error(tmp_path, storage, monkeypatch):
    def inaccessible(self, *, strict=False):
        raise PermissionError("private-path-that-must-not-be-logged")

    monkeypatch.setattr(Path, "resolve", inaccessible)
    with pytest.raises(
        transfers.TransferError, match="existing absolute private result directory"
    ) as caught:
        downloader().download(URL, root=tmp_path, name="result.bin")
    assert "private-path" not in str(caught.value)
    storage[1].assert_not_called()
