# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Storage transport contracts without sockets or signed production URLs."""

import hashlib
import io
import logging
import ssl
import threading
from dataclasses import asdict
from pathlib import Path, PurePosixPath, PureWindowsPath
from unittest.mock import Mock

import pytest

from scenario.core.jobs import transfers

URL = "https://storage.example.invalid/result?signature=private-fixture"
DATA = b"offline result bytes"


@pytest.mark.parametrize(
    "root, expected",
    [
        (r"C:\private\results", r"\\?\C:\private\results"),
        (r"\\server\share\results", r"\\?\UNC\server\share\results"),
        (r"\\?\C:\private\results", r"\\?\C:\private\results"),
        (r"\\?\UNC\server\share\results", r"\\?\UNC\server\share\results"),
    ],
)
def test_windows_private_roots_preserve_drive_or_unc_identity(root, expected):
    path = PureWindowsPath(root)
    converted = transfers._windows_storage_path(path)
    assert converted == PureWindowsPath(expected)
    assert transfers._windows_storage_path(converted) == converted


def test_posix_private_root_is_not_reinterpreted_as_a_windows_drive():
    path = PurePosixPath("/private/results")
    assert transfers._windows_storage_path(path) is path


def test_windows_device_path_is_not_reinterpreted_as_a_unc_root():
    with pytest.raises(transfers.TransferError):
        transfers._windows_storage_path(PureWindowsPath(r"\\.\C:\private"))


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
def test_status_never_follows_untrusted_redirect_or_retries(status, tmp_path, storage):
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
        downloader(max_bytes=20).download(URL, root=tmp_path, name="x", expected_size=20)
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
        # A read timeout is waited out up to the inactivity limit, kept short here.
        downloader(timeout=0.5).download(URL, root=tmp_path, name="x")
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


def test_cancel_event_during_read_never_publishes(tmp_path, storage):
    cancel = threading.Event()
    original_read = storage[0].getresponse.return_value.read1

    def read(size):
        cancel.set()
        return original_read(size)

    storage[0].getresponse.return_value.read1 = read
    with pytest.raises(transfers.TransferError, match="interrupted"):
        downloader().download(URL, root=tmp_path, name="x", cancel=cancel)
    assert not list(tmp_path.iterdir())
    with pytest.raises(transfers.TransferError, match="disabled"):
        downloader().download(URL, root=tmp_path, name="x", cancel=cancel)
    assert storage[1].call_count == 1
    with pytest.raises(transfers.TransferError, match="cancellation"):
        downloader().download(URL, root=tmp_path, name="x", cancel=True)


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
    "declared,expected,valid",
    [
        (str(len(DATA)), None, True),
        (str(len(DATA) + 1), None, False),
        # A close-delimited body needs a known size; see the cut-short test below.
        (None, len(DATA), True),
    ],
)
def test_real_http_response_framing(declared, expected, valid, tmp_path, storage):
    import http.client

    headers = f"Content-Length: {declared}\r\n" if declared is not None else ""
    wire = b"HTTP/1.1 200 OK\r\nConnection: close\r\n" + headers.encode() + b"\r\n" + DATA
    socket = Mock()
    socket.makefile.return_value = io.BytesIO(wire)
    response = http.client.HTTPResponse(socket)
    response.begin()
    storage[0].getresponse.return_value = response
    if valid:
        result = downloader().download(URL, root=tmp_path, name="x", expected_size=expected)
        assert result.size == len(DATA)
        assert (tmp_path / "x").read_bytes() == DATA
    else:
        with pytest.raises(transfers.TransferError, match="incomplete"):
            downloader().download(URL, root=tmp_path, name="x", expected_size=expected)
        assert not list(tmp_path.iterdir())


@pytest.mark.parametrize(
    "declared,body,error",
    [
        # A close-delimited body that ends early reads like a complete one.
        (None, DATA[:7], "complete byte count"),
        (len(DATA), DATA[:7], "incomplete"),
        (len(DATA), DATA, None),
    ],
)
def test_unknown_size_needs_a_declared_length_to_detect_a_cut_short_body(
    declared, body, error, tmp_path, storage
):
    import http.client

    headers = f"Content-Length: {declared}\r\n" if declared is not None else ""
    wire = b"HTTP/1.1 200 OK\r\nConnection: close\r\n" + headers.encode() + b"\r\n" + body
    socket = Mock()
    socket.makefile.return_value = io.BytesIO(wire)
    response = http.client.HTTPResponse(socket)
    response.begin()
    storage[0].getresponse.return_value = response
    if error is None:
        result = downloader().download(URL, root=tmp_path, name="x")
        assert (result.size, result.sha256) == (len(DATA), hashlib.sha256(DATA).hexdigest())
        assert (tmp_path / "x").read_bytes() == DATA
    else:
        with pytest.raises(transfers.TransferError, match=error):
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


@pytest.mark.parametrize("casing", ["upper", "mixed"])
def test_manifest_digest_accepts_hex_case_variants(casing, tmp_path, storage):
    canonical = hashlib.sha256(DATA).hexdigest()
    expected = (
        canonical.upper()
        if casing == "upper"
        else "".join(char.upper() if index % 2 else char for index, char in enumerate(canonical))
    )
    assert expected != canonical
    result = downloader().download(URL, root=tmp_path, name="result.bin", expected_sha256=expected)
    assert result.sha256 == canonical
    assert (tmp_path / result.name).read_bytes() == DATA


@pytest.mark.parametrize("failure_point", ["staging", "response", "connection"])
@pytest.mark.parametrize("publish", [True, False])
def test_cleanup_failure_preserves_publication_outcome(
    failure_point, publish, tmp_path, storage, monkeypatch
):
    temporary_directories = []
    original_directory = transfers.tempfile.TemporaryDirectory
    response = storage[0].getresponse.return_value
    original_response_close = response.close

    if failure_point == "staging":

        class FailingCleanup:
            def __init__(self, **kwargs):
                self.directory = original_directory(**kwargs)
                temporary_directories.append(self.directory)
                self.name = self.directory.name

            def cleanup(self):
                raise OSError(URL)

        monkeypatch.setattr(transfers.tempfile, "TemporaryDirectory", FailingCleanup)
    elif failure_point == "response":
        response.close = Mock(side_effect=OSError(URL))
    else:
        storage[0].close.side_effect = RuntimeError(URL)

    try:
        if publish:
            result = downloader().download(URL, root=tmp_path, name="result.bin")
            assert result.size == len(DATA)
            assert result.sha256 == hashlib.sha256(DATA).hexdigest()
            assert (tmp_path / result.name).read_bytes() == DATA
        else:
            with pytest.raises(transfers.TransferError) as caught:
                downloader().download(
                    URL, root=tmp_path, name="result.bin", expected_sha256="a" * 64
                )
            assert "private-fixture" not in str(caught.value)
            assert not (tmp_path / "result.bin").exists()
        assert storage[0].request.call_count == 1
        storage[0].close.assert_called_once()
    finally:
        original_response_close()
        for directory in temporary_directories:
            directory.cleanup()


def test_cleanup_errors_do_not_mask_control_exception(tmp_path, storage):
    response = storage[0].getresponse.return_value
    original_close = response.close
    response.read1 = Mock(side_effect=KeyboardInterrupt())
    response.close = Mock(side_effect=OSError(URL))
    storage[0].close.side_effect = RuntimeError(URL)
    try:
        with pytest.raises(KeyboardInterrupt):
            downloader().download(URL, root=tmp_path, name="result.bin")
        assert not list(tmp_path.iterdir())
        response.close.assert_called_once()
        storage[0].close.assert_called_once()
    finally:
        original_close()


@pytest.mark.parametrize(
    "headers,error", [({}, "byte limit"), ({"Content-Length": "20"}, "size is invalid")]
)
def test_per_request_limit_bounds_stream_and_headers(tmp_path, storage, headers, error):
    storage[0].getresponse.return_value = Response(b"x" * 20, headers=headers)
    with pytest.raises(transfers.TransferError, match=error):
        downloader(max_bytes=100).download(
            URL, root=tmp_path, name="x", max_bytes=10, expected_size=10
        )
    assert not list(tmp_path.iterdir())


def test_per_request_limit_cannot_expand_storage_policy(tmp_path, storage):
    storage[0].getresponse.return_value = Response(b"x" * 20, headers={})
    with pytest.raises(transfers.TransferError, match="byte limit"):
        downloader(max_bytes=10).download(
            URL, root=tmp_path, name="x", max_bytes=100, expected_size=10
        )
    assert not list(tmp_path.iterdir())


@pytest.mark.parametrize("status", [301, 302, 303, 307, 308])
def test_same_host_redirect_keeps_signed_target_and_checks_final_bytes(status, tmp_path, storage):
    conn, constructor = storage
    first = Response(
        status=status, headers={"Location": "https://storage.example.invalid/final?sig=next"}
    )
    final = Response()
    conn.getresponse.side_effect = [first, final]
    receipt = downloader().download(
        URL,
        root=tmp_path,
        name="x",
        expected_size=len(DATA),
        expected_sha256=hashlib.sha256(DATA).hexdigest(),
    )
    assert (tmp_path / receipt.name).read_bytes() == DATA
    assert first.closed and final.closed
    assert constructor.call_count == 2 and conn.close.call_count == 2
    assert conn.request.call_args.args == ("GET", "/final?sig=next")
    assert conn.request.call_args.kwargs["headers"] == {
        "Accept-Encoding": "identity",
        "Connection": "close",
    }


@pytest.mark.parametrize(
    "location",
    [
        None,
        "/relative",
        "http://storage.example.invalid/x",
        "https://user@storage.example.invalid/x",
        "https://storage.example.invalid:8443/x",
        "https://storage.example.invalid/x#fragment",
        URL,
    ],
)
def test_redirect_rejects_malformed_destination_or_loop(location, tmp_path, storage):
    conn, constructor = storage
    first = Response(status=302, headers={"Location": location})
    conn.getresponse.return_value = first
    with pytest.raises(transfers.TransferError):
        downloader().download(URL, root=tmp_path, name="x")
    assert first.closed and conn.close.call_count == 1
    assert constructor.call_count == 1 and not list(tmp_path.iterdir())


def test_redirect_cannot_switch_to_another_configured_host(tmp_path, storage):
    conn, constructor = storage
    conn.getresponse.return_value = Response(
        status=302, headers={"Location": "https://other.example.invalid/x"}
    )
    client = transfers.ResultDownloader(
        transfers.StoragePolicy(frozenset({"storage.example.invalid", "other.example.invalid"})),
        online_access=lambda: True,
    )
    with pytest.raises(transfers.TransferError):
        client.download(URL, root=tmp_path, name="x")
    assert constructor.call_count == 1


def test_redirect_chain_has_two_hop_limit_and_cleans_all_responses(tmp_path, storage):
    conn, constructor = storage
    responses = [
        Response(status=302, headers={"Location": f"https://storage.example.invalid/hop-{n}"})
        for n in range(3)
    ]
    conn.getresponse.side_effect = responses
    with pytest.raises(transfers.TransferError, match="limit"):
        downloader().download(URL, root=tmp_path, name="x")
    assert constructor.call_count == 3 and conn.close.call_count == 3
    assert all(response.closed for response in responses)
    assert not list(tmp_path.iterdir())


def test_permission_revoked_after_redirect_prevents_next_connection(tmp_path, storage):
    conn, constructor = storage
    allowed = [True]
    first = Response(status=302, headers={"Location": "https://storage.example.invalid/next"})

    def response():
        allowed[0] = False
        return first

    conn.getresponse.side_effect = response
    client = transfers.ResultDownloader(
        transfers.StoragePolicy(frozenset({"storage.example.invalid"})),
        online_access=lambda: allowed[0],
    )
    with pytest.raises(transfers.TransferError, match="interrupted"):
        client.download(URL, root=tmp_path, name="x")
    assert constructor.call_count == 1 and first.closed


def test_redirect_uses_original_total_deadline(tmp_path, storage, monkeypatch):
    conn, constructor = storage
    now = [0.0]
    monkeypatch.setattr(transfers.time, "monotonic", lambda: now[0])
    first = Response(status=302, headers={"Location": "https://storage.example.invalid/next"})

    def response():
        now[0] = 2.0
        return first

    conn.getresponse.side_effect = response
    with pytest.raises(transfers.TransferError, match="interrupted"):
        downloader(total_timeout=1).download(URL, root=tmp_path, name="x")
    assert constructor.call_count == 1 and first.closed
    assert not list(tmp_path.iterdir())


def test_two_redirects_can_complete_without_reading_redirect_bodies(tmp_path, storage):
    conn, constructor = storage
    responses = [
        Response(status=302, headers={"Location": f"https://storage.example.invalid/hop-{n}"})
        for n in range(2)
    ]
    for response in responses:
        response.read1 = Mock(side_effect=AssertionError("Redirect body must not be read"))
    conn.getresponse.side_effect = [*responses, Response()]
    downloader().download(URL, root=tmp_path, name="x")
    assert constructor.call_count == 3 and conn.close.call_count == 3
    assert (tmp_path / "x").read_bytes() == DATA


@pytest.mark.parametrize("declared", [1, len(DATA) + 5])
def test_legacy_size_policy_keeps_actual_length_and_receipt(tmp_path, storage, declared):
    result = downloader().download(
        URL,
        root=tmp_path,
        name="legacy.mtl",
        expected_size=declared,
        allow_size_mismatch=True,
    )
    assert result.size == len(DATA)
    assert result.sha256 == hashlib.sha256(DATA).hexdigest()


@pytest.mark.parametrize("headers", [{}, {"Content-Length": "100"}, {"Content-Length": "1"}])
def test_legacy_size_policy_rejects_missing_or_incomplete_length(tmp_path, storage, headers):
    storage[0].getresponse.return_value = Response(headers=headers)
    with pytest.raises(transfers.TransferError):
        downloader().download(
            URL,
            root=tmp_path,
            name="legacy.mtl",
            expected_size=1,
            allow_size_mismatch=True,
        )
    assert not list(tmp_path.iterdir())


@pytest.mark.parametrize("options", [{"max_bytes": len(DATA) - 1}, {"expected_sha256": "0" * 64}])
def test_legacy_size_policy_cannot_bypass_byte_cap_or_digest(tmp_path, storage, options):
    with pytest.raises(transfers.TransferError):
        downloader().download(
            URL,
            root=tmp_path,
            name="legacy.mtl",
            expected_size=1,
            allow_size_mismatch=True,
            **options,
        )
    assert not list(tmp_path.iterdir())


# Resumable attempts, retry classification and size-scaled deadlines (#453).

ETAG = '"strong-fixture"'
LARGE = bytes(range(256)) * 64  # 16 KiB


class Broken(Response):
    """A body that resets the connection after `fail_after` bytes."""

    def __init__(self, data=LARGE, *, fail_after, **kwargs):
        super().__init__(data, **kwargs)
        self.fail_after = fail_after

    def read1(self, size=-1):
        if self.tell() >= self.fail_after:
            raise ConnectionResetError("private-fixture reset")
        return super().read1(min(size, 1024, self.fail_after - self.tell()))


def connections(storage, *responses):
    """Serve one fresh connection per attempt, in order."""
    made = []
    for response in responses:
        connection = Mock()
        connection.getresponse.return_value = response
        made.append(connection)
    storage[1].side_effect = made
    return made


def sent_headers(connection):
    return connection.request.call_args.kwargs["headers"]


def test_size_scaled_deadline_has_a_floor_and_a_ceiling():
    policy = transfers.StoragePolicy(frozenset({"storage.example.invalid"}))
    assert policy.deadline(None) == policy.total_timeout == 300.0
    assert policy.deadline(1024) == 300.0
    assert policy.deadline(128 * 1024 * 1024) == 512.0
    assert policy.deadline(256 * 1024 * 1024) == 1024.0
    assert policy.deadline(2**40) == policy.max_total_timeout == 1800.0
    with pytest.raises(ValueError):
        transfers.StoragePolicy(
            frozenset({"storage.example.invalid"}), total_timeout=600, max_total_timeout=300
        )
    with pytest.raises(ValueError):
        transfers.StoragePolicy(frozenset({"storage.example.invalid"}), min_rate=0)


def test_large_download_gets_more_than_the_floor(tmp_path, storage, monkeypatch):
    # 4 KiB/s floor rate: a 16 KiB body may take 4 s where the floor is 1 s.
    clock = 0.0
    monkeypatch.setattr(transfers.time, "monotonic", lambda: clock)
    response = Response(LARGE)
    original_read = response.read1

    def read(size):
        nonlocal clock
        clock += 0.2
        return original_read(min(size, 1024))

    response.read1 = read
    storage[0].getresponse.return_value = response
    receipt = downloader(total_timeout=1, min_rate=4096).download(
        URL, root=tmp_path, name="x", expected_size=len(LARGE)
    )
    assert receipt.size == len(LARGE) and clock > 1


def test_unknown_size_deadline_follows_declared_length(tmp_path, storage, monkeypatch):
    clock = 0.0
    monkeypatch.setattr(transfers.time, "monotonic", lambda: clock)
    response = Response(LARGE)
    original_read = response.read1

    def read(size):
        nonlocal clock
        clock += 0.2
        return original_read(min(size, 1024))

    response.read1 = read
    storage[0].getresponse.return_value = response
    receipt = downloader(total_timeout=1, min_rate=4096).download(URL, root=tmp_path, name="x")
    assert receipt.size == len(LARGE)


def test_deadline_and_transport_failures_are_retryable_but_policy_failures_are_not(
    tmp_path, storage, monkeypatch
):
    storage[0].connect.side_effect = OSError(URL)
    with pytest.raises(transfers.TransferError) as caught:
        downloader().download(URL, root=tmp_path, name="x")
    assert caught.value.retryable
    storage[0].connect.side_effect = None
    for status in (403, 500, 503):
        storage[0].getresponse.return_value = Response(status=status)
        with pytest.raises(transfers.TransferError) as caught:
            downloader().download(URL, root=tmp_path, name="x")
        assert caught.value.retryable
    storage[0].getresponse.return_value = Response(headers={"Content-Encoding": "gzip"})
    with pytest.raises(transfers.TransferError) as caught:
        downloader().download(URL, root=tmp_path, name="x")
    assert not caught.value.retryable
    storage[0].getresponse.return_value = Response()
    with pytest.raises(transfers.TransferError) as caught:
        downloader().download(URL, root=tmp_path, name="x", expected_sha256="a" * 64)
    assert not caught.value.retryable
    with pytest.raises(transfers.TransferError) as caught:
        downloader().download("https://other.example.invalid/x", root=tmp_path, name="x")
    assert not caught.value.retryable
    cancel = threading.Event()
    cancel.set()
    with pytest.raises(transfers.TransferError) as caught:
        downloader().download(URL, root=tmp_path, name="x", cancel=cancel)
    assert not caught.value.retryable
    assert not list(tmp_path.iterdir())


def test_strong_etag_resumes_with_range_and_if_range(tmp_path, storage):
    first, second = connections(
        storage,
        Broken(fail_after=5000, headers={"Content-Length": str(len(LARGE)), "ETag": ETAG}),
        Response(
            LARGE[5000:],
            status=206,
            headers={
                "Content-Length": str(len(LARGE) - 5000),
                "Content-Range": f"bytes 5000-{len(LARGE) - 1}/{len(LARGE)}",
                "ETag": ETAG,
            },
        ),
    )
    client = downloader()
    partial = transfers.PartialDownload()
    with pytest.raises(transfers.TransferError) as caught:
        client.download(URL, root=tmp_path, name="x", expected_size=len(LARGE), partial=partial)
    assert caught.value.retryable and partial.size == 5000
    assert "Range" not in sent_headers(first)
    # Partial bytes stay private: nothing is published under the result name.
    assert not (tmp_path / "x").exists()
    receipt = client.download(
        "https://storage.example.invalid/result?signature=fresh",
        root=tmp_path,
        name="x",
        expected_size=len(LARGE),
        expected_sha256=hashlib.sha256(LARGE).hexdigest(),
        partial=partial,
    )
    headers = sent_headers(second)
    assert headers["Range"] == "bytes=5000-" and headers["If-Range"] == ETAG
    assert (receipt.size, receipt.sha256) == (len(LARGE), hashlib.sha256(LARGE).hexdigest())
    assert (tmp_path / "x").read_bytes() == LARGE
    assert list(tmp_path.iterdir()) == [tmp_path / "x"]
    assert partial.size == 0


@pytest.mark.parametrize("etag", [None, 'W/"weak-fixture"', "unquoted", '""'])
def test_missing_or_weak_etag_restarts_from_zero(etag, tmp_path, storage):
    headers = {"Content-Length": str(len(LARGE))}
    if etag is not None:
        headers["ETag"] = etag
    _, second = connections(
        storage, Broken(fail_after=5000, headers=dict(headers)), Response(LARGE)
    )
    partial = transfers.PartialDownload()
    client = downloader()
    with pytest.raises(transfers.TransferError):
        client.download(URL, root=tmp_path, name="x", expected_size=len(LARGE), partial=partial)
    assert partial.size == 0
    receipt = client.download(
        URL, root=tmp_path, name="x", expected_size=len(LARGE), partial=partial
    )
    assert "Range" not in sent_headers(second) and "If-Range" not in sent_headers(second)
    assert receipt.sha256 == hashlib.sha256(LARGE).hexdigest()


def test_full_reply_to_a_ranged_request_restarts_cleanly(tmp_path, storage):
    changed = bytes(reversed(LARGE))
    _, second = connections(
        storage,
        Broken(fail_after=5000, headers={"Content-Length": str(len(LARGE)), "ETag": ETAG}),
        # If-Range did not match: the server sends the whole (new) object.
        Response(changed, headers={"Content-Length": str(len(changed)), "ETag": '"new"'}),
    )
    partial = transfers.PartialDownload()
    client = downloader()
    with pytest.raises(transfers.TransferError):
        client.download(URL, root=tmp_path, name="x", expected_size=len(LARGE), partial=partial)
    receipt = client.download(
        URL, root=tmp_path, name="x", expected_size=len(LARGE), partial=partial
    )
    assert sent_headers(second)["Range"] == "bytes=5000-"
    assert receipt.sha256 == hashlib.sha256(changed).hexdigest()
    assert (tmp_path / "x").read_bytes() == changed
    assert list(tmp_path.iterdir()) == [tmp_path / "x"]


@pytest.mark.parametrize(
    "headers",
    [
        {"Content-Range": "bytes 4000-16383/16384", "ETag": ETAG},
        {"Content-Range": "bytes 5000-16383/20000", "ETag": ETAG},
        {"Content-Range": "bytes 5000-16000/16384", "ETag": ETAG},
        {"Content-Range": "bytes */16384", "ETag": ETAG},
        {"Content-Range": "bytes 5000-16383/16384", "ETag": '"other"'},
        {"Content-Range": "bytes 5000-16383/16384"},
        {"ETag": ETAG},
    ],
)
def test_inconsistent_partial_reply_is_retryable_and_restarts_next_time(headers, tmp_path, storage):
    third = Response(LARGE)
    _, _, last = connections(
        storage,
        Broken(fail_after=5000, headers={"Content-Length": str(len(LARGE)), "ETag": ETAG}),
        Response(LARGE[5000:], status=206, headers=headers),
        third,
    )
    partial = transfers.PartialDownload()
    client = downloader()
    for _ in range(2):
        with pytest.raises(transfers.TransferError) as caught:
            client.download(URL, root=tmp_path, name="x", expected_size=len(LARGE), partial=partial)
        assert caught.value.retryable
    assert partial.size == 0
    receipt = client.download(
        URL, root=tmp_path, name="x", expected_size=len(LARGE), partial=partial
    )
    assert "Range" not in sent_headers(last)
    assert receipt.sha256 == hashlib.sha256(LARGE).hexdigest()


def test_unsolicited_partial_reply_is_rejected(tmp_path, storage):
    storage[0].getresponse.return_value = Response(
        LARGE[:100],
        status=206,
        headers={"Content-Range": "bytes 0-99/16384", "ETag": ETAG, "Content-Length": "100"},
    )
    with pytest.raises(transfers.TransferError):
        downloader().download(URL, root=tmp_path, name="x", partial=transfers.PartialDownload())
    assert not (tmp_path / "x").exists()


def test_cancel_discards_partial_bytes_and_publishes_nothing(tmp_path, storage):
    cancel = threading.Event()
    response = Response(LARGE, headers={"Content-Length": str(len(LARGE)), "ETag": ETAG})
    original_read = response.read1

    def read(size):
        if response.tell() >= 4096:
            cancel.set()
        return original_read(min(size, 1024))

    response.read1 = read
    storage[0].getresponse.return_value = response
    partial = transfers.PartialDownload()
    with pytest.raises(transfers.TransferError) as caught:
        downloader().download(
            URL, root=tmp_path, name="x", expected_size=len(LARGE), cancel=cancel, partial=partial
        )
    assert not caught.value.retryable
    assert partial.size == 0
    assert not list(tmp_path.iterdir())


def test_partial_belongs_to_one_result(tmp_path, storage):
    connections(
        storage,
        Broken(fail_after=5000, headers={"Content-Length": str(len(LARGE)), "ETag": ETAG}),
    )
    partial = transfers.PartialDownload()
    with pytest.raises(transfers.TransferError):
        downloader().download(
            URL, root=tmp_path, name="x", expected_size=len(LARGE), partial=partial
        )
    with pytest.raises(transfers.TransferError, match="another result"):
        downloader().download(
            URL, root=tmp_path, name="y", expected_size=len(LARGE), partial=partial
        )
    partial.discard()
    assert not list(tmp_path.iterdir())


def test_shortened_staging_file_restarts_instead_of_resuming(tmp_path, storage):
    _, second = connections(
        storage,
        Broken(fail_after=5000, headers={"Content-Length": str(len(LARGE)), "ETag": ETAG}),
        Response(LARGE),
    )
    partial = transfers.PartialDownload()
    client = downloader()
    with pytest.raises(transfers.TransferError):
        client.download(URL, root=tmp_path, name="x", expected_size=len(LARGE), partial=partial)
    (staged,) = [path for path in tmp_path.rglob("*") if path.is_file()]
    with staged.open("r+b") as output:
        output.truncate(100)
    receipt = client.download(
        URL, root=tmp_path, name="x", expected_size=len(LARGE), partial=partial
    )
    assert "Range" not in sent_headers(second)
    assert receipt.sha256 == hashlib.sha256(LARGE).hexdigest()


class Silent(Response):
    """Headers arrive, then each read waits on a real socket that may stay silent."""

    def __init__(self, sock):
        super().__init__(LARGE, headers={"Content-Length": str(len(LARGE)), "ETag": ETAG})
        self.sock, self.received = sock, 0

    def read1(self, size=-1):
        # Like http.client, stop at the declared length instead of waiting for more.
        if self.received >= len(LARGE):
            return b""
        chunk = self.sock.recv(min(size, 1024, len(LARGE) - self.received))
        self.received += len(chunk)
        return chunk


@pytest.fixture
def socket_pair(storage):
    import socket

    client_end, server_end = socket.socketpair()
    storage[0].sock = client_end
    storage[0].getresponse.return_value = Silent(client_end)
    yield client_end, server_end
    client_end.close()
    server_end.close()


def test_cancel_stops_a_read_waiting_on_a_silent_server_within_the_poll(tmp_path, socket_pair):
    import time

    client_end, server_end = socket_pair
    server_end.sendall(LARGE[:2048])
    cancel = threading.Event()
    threading.Timer(0.3, cancel.set).start()
    partial = transfers.PartialDownload()
    started = time.monotonic()
    with pytest.raises(transfers.TransferError, match="interrupted") as caught:
        downloader().download(
            URL, root=tmp_path, name="x", expected_size=len(LARGE), cancel=cancel, partial=partial
        )
    # The 30-second inactivity limit never applies, and cancellation is final.
    assert time.monotonic() - started < 0.3 + transfers.POLL_INTERVAL + 1
    assert not caught.value.retryable
    assert partial.size == 0 and not list(tmp_path.iterdir())
    assert client_end.gettimeout() <= transfers.POLL_INTERVAL


def test_a_pause_shorter_than_the_inactivity_limit_is_waited_out(tmp_path, socket_pair):
    _, server_end = socket_pair
    server_end.sendall(LARGE[:4096])
    # Three poll intervals of silence, then the rest of the body.
    threading.Timer(3 * transfers.POLL_INTERVAL, server_end.sendall, (LARGE[4096:],)).start()
    receipt = downloader(timeout=5).download(
        URL,
        root=tmp_path,
        name="x",
        expected_size=len(LARGE),
        expected_sha256=hashlib.sha256(LARGE).hexdigest(),
    )
    assert receipt.size == len(LARGE)


def test_silence_past_the_inactivity_limit_is_a_retryable_stall(tmp_path, socket_pair):
    _, server_end = socket_pair
    server_end.sendall(LARGE[:4096])
    partial = transfers.PartialDownload()
    with pytest.raises(transfers.TransferError, match="stalled") as caught:
        downloader(timeout=1).download(
            URL, root=tmp_path, name="x", expected_size=len(LARGE), partial=partial
        )
    assert caught.value.retryable
    # With a strong ETag the next attempt resumes the bytes already received.
    assert partial.size == 4096 and partial.resumable
    partial.discard()


def test_real_http_body_reads_can_time_out_and_continue(tmp_path, storage, monkeypatch):
    """Through http.client: a timed-out body read is retried, never refused."""
    import http.client
    import socket

    client_end, server_end = socket.socketpair()
    try:
        head = (
            f"HTTP/1.1 200 OK\r\nContent-Length: {len(LARGE)}\r\nETag: {ETAG}\r\n"
            "Connection: close\r\n\r\n"
        ).encode()
        server_end.sendall(head + LARGE[:3000])
        threading.Timer(2 * transfers.POLL_INTERVAL, server_end.sendall, (LARGE[3000:],)).start()

        class Connection(http.client.HTTPConnection):
            def connect(self):
                self.sock = client_end

        connection = Connection("storage.example.invalid")
        storage[1].return_value = connection
        storage[1].side_effect = None
        monkeypatch.setattr(connection, "request", lambda *args, **kwargs: None)
        monkeypatch.setattr(connection, "_HTTPConnection__state", "Request-sent", raising=False)
        receipt = downloader(timeout=5).download(
            URL,
            root=tmp_path,
            name="x",
            expected_size=len(LARGE),
            expected_sha256=hashlib.sha256(LARGE).hexdigest(),
        )
        assert receipt.size == len(LARGE)
        assert isinstance(connection.response_class, type)
        assert issubclass(connection.response_class, http.client.HTTPResponse)
    finally:
        client_end.close()
        server_end.close()


@pytest.mark.parametrize("failure", ["status", "connect"])
def test_a_resume_attempt_that_fails_before_its_body_keeps_the_staged_bytes(
    failure, tmp_path, storage
):
    first = Mock()
    first.getresponse.return_value = Broken(
        fail_after=5000, headers={"Content-Length": str(len(LARGE)), "ETag": ETAG}
    )
    second = Mock()
    if failure == "status":
        second.getresponse.return_value = Response(status=503)
    else:
        second.connect.side_effect = OSError("private-fixture connect failure")
    third = Mock()
    third.getresponse.return_value = Response(
        LARGE[5000:],
        status=206,
        headers={
            "Content-Length": str(len(LARGE) - 5000),
            "Content-Range": f"bytes 5000-{len(LARGE) - 1}/{len(LARGE)}",
            "ETag": ETAG,
        },
    )
    storage[1].side_effect = [first, second, third]
    client, partial = downloader(), transfers.PartialDownload()
    for _ in range(2):
        with pytest.raises(transfers.TransferError) as caught:
            client.download(URL, root=tmp_path, name="x", expected_size=len(LARGE), partial=partial)
        assert caught.value.retryable and partial.size == 5000 and partial.resumable
    receipt = client.download(
        URL, root=tmp_path, name="x", expected_size=len(LARGE), partial=partial
    )
    assert sent_headers(third)["Range"] == "bytes=5000-"
    assert receipt.sha256 == hashlib.sha256(LARGE).hexdigest()


def test_a_range_the_server_cannot_satisfy_starts_again_from_zero(tmp_path, storage):
    first, second, third = connections(
        storage,
        Broken(fail_after=5000, headers={"Content-Length": str(len(LARGE)), "ETag": ETAG}),
        Response(status=416),
        Response(LARGE),
    )
    client, partial = downloader(), transfers.PartialDownload()
    for _ in range(2):
        with pytest.raises(transfers.TransferError):
            client.download(URL, root=tmp_path, name="x", expected_size=len(LARGE), partial=partial)
    assert partial.size == 0
    client.download(URL, root=tmp_path, name="x", expected_size=len(LARGE), partial=partial)
    assert "Range" not in sent_headers(third)
