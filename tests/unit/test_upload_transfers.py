# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Signed PUT byte boundaries and uncertainty without contacting storage."""

import hashlib
import logging
import ssl
from dataclasses import asdict
from unittest.mock import Mock

import pytest

from scenario.core.jobs import upload_transfers as upload
from scenario.core.jobs.transfers import StoragePolicy, TransferError

URL = "https://storage.example.invalid/part?signature=private-fixture"
DATA = b"part" * 40000
DIGEST = hashlib.sha256(DATA).hexdigest()


@pytest.fixture
def connection(monkeypatch):
    conn = Mock()
    conn.getresponse.return_value.status = 200
    factory = Mock(return_value=conn)
    monkeypatch.setattr(upload.http.client, "HTTPSConnection", factory)
    return conn, factory


def uploader(*, online=lambda: True, **policy):
    return upload.PartUploader(
        StoragePolicy(frozenset({"storage.example.invalid"}), **policy), online_access=online
    )


def send(client, data=DATA, url=URL, **kwargs):
    options = {"number": 1, "content_type": "model/gltf-binary", "expected_sha256": DIGEST}
    options.update(kwargs)
    return client.upload(url, data, **options)


def test_put_uses_bounded_chunks_and_credential_free_headers(
    connection, monkeypatch, caplog, tmp_path
):
    for name in (
        "HTTPS_PROXY",
        "ALL_PROXY",
        "HTTP_PROXY",
        "SSLKEYLOGFILE",
        "SSL_CERT_FILE",
        "SSL_CERT_DIR",
        "SCENARIO_API_KEY",
        "SCENARIO_API_SECRET",
    ):
        monkeypatch.setenv(name, str(tmp_path / "private-environment"))
    caplog.set_level(logging.DEBUG)
    conn, factory = connection
    receipt = send(uploader())
    assert receipt == upload.UploadedPart(1, len(DATA), DIGEST)
    conn.putrequest.assert_called_once_with(
        "PUT", "/part?signature=private-fixture", skip_accept_encoding=True
    )
    headers = dict(call.args for call in conn.putheader.call_args_list)
    assert headers == {
        "Content-Type": "model/gltf-binary",
        "Content-Length": str(len(DATA)),
        "Connection": "close",
    }
    parts = [call.args[0] for call in conn.send.call_args_list]
    assert b"".join(parts) == DATA and max(map(len, parts)) <= 65536
    assert factory.call_count == conn.endheaders.call_count == conn.getresponse.call_count == 1
    context = factory.call_args.kwargs["context"]
    assert context.verify_mode == ssl.CERT_REQUIRED and context.check_hostname
    assert context.keylog_filename is None
    assert "signature" not in repr(receipt) + str(asdict(receipt)) + caplog.text
    conn.close.assert_called_once()
    conn.getresponse.return_value.close.assert_called_once()


@pytest.mark.parametrize(
    "kwargs",
    [
        {"number": 0},
        {"number": True},
        {"content_type": "image/png\r\nsecret: value"},
        {"expected_sha256": "a" * 64},
        {"expected_sha256": "invalid"},
    ],
)
def test_invalid_part_identity_fails_before_connect(connection, kwargs):
    with pytest.raises(TransferError):
        send(uploader(), **kwargs)
    connection[1].assert_not_called()


@pytest.mark.parametrize("data", [b"", bytearray(DATA), "text", b"changed"])
def test_only_matching_immutable_bounded_bytes_are_accepted(connection, data):
    with pytest.raises(TransferError):
        send(uploader(), data=data)
    connection[1].assert_not_called()


def test_size_limit_is_checked_before_connect(connection):
    with pytest.raises(TransferError):
        send(uploader(max_bytes=1))
    connection[1].assert_not_called()


@pytest.mark.parametrize(
    "url",
    [
        "http://storage.example.invalid/a",
        "https://other.example.invalid/a",
        "https://user:secret@storage.example.invalid/a",
        "https://storage.example.invalid:444/a",
        "https://storage.example.invalid/a#fragment",
        "https://storage.example.invalid/a\n",
    ],
)
def test_untrusted_destinations_are_rejected_before_connect(connection, url):
    with pytest.raises(TransferError):
        send(uploader(), url=url)
    connection[1].assert_not_called()


@pytest.mark.parametrize("status", [200, 201, 204])
def test_success_acknowledges_only_one_part(connection, status):
    conn, _ = connection
    conn.getresponse.return_value.status = status
    assert send(uploader()).number == 1
    conn.getresponse.return_value.read.assert_not_called()


@pytest.mark.parametrize("status", [301, 302, 307, 400, 403, 429, 500, 503])
def test_redirects_and_failures_are_uncertain_without_retry(connection, status):
    conn, factory = connection
    conn.getresponse.return_value.status = status
    with pytest.raises(upload.UploadUncertain) as error:
        send(uploader())
    assert "signature" not in str(error.value)
    assert factory.call_count == conn.endheaders.call_count == 1
    conn.getresponse.return_value.read.assert_not_called()


@pytest.mark.parametrize("stage", ["endheaders", "send", "getresponse"])
def test_lost_response_or_partial_write_never_retries(connection, stage):
    conn, factory = connection
    getattr(conn, stage).side_effect = OSError("signature=private-fixture")
    with pytest.raises(upload.UploadUncertain) as error:
        send(uploader())
    assert "private-fixture" not in str(error.value)
    assert factory.call_count == 1
    conn.close.assert_called_once()


def test_connect_failure_is_not_misreported_as_sent(connection):
    conn, _ = connection
    conn.connect.side_effect = OSError("private path")
    with pytest.raises(TransferError) as error:
        send(uploader())
    assert not isinstance(error.value, upload.UploadUncertain)
    conn.endheaders.assert_not_called()


def test_offline_and_permission_revocation_stop_before_more_bytes(connection):
    conn, factory = connection
    with pytest.raises(TransferError):
        send(uploader(online=lambda: False))
    factory.assert_not_called()
    allowed = True

    def revoke(*args):
        nonlocal allowed
        allowed = False

    conn.send.side_effect = revoke
    with pytest.raises(upload.UploadUncertain):
        send(uploader(online=lambda: allowed))
    assert conn.send.call_count == 1
    conn.getresponse.assert_not_called()


def test_deadline_between_chunks_stops_without_retry(connection, monkeypatch):
    conn, _ = connection
    now = 0.0
    monkeypatch.setattr(upload.time, "monotonic", lambda: now)

    def tick(*args):
        nonlocal now
        now += 2

    conn.send.side_effect = tick
    with pytest.raises(upload.UploadUncertain):
        send(uploader(total_timeout=1))
    assert conn.send.call_count == 1


def test_cleanup_error_does_not_replace_acknowledged_receipt(connection):
    conn, _ = connection
    conn.close.side_effect = OSError("private close failure")
    conn.getresponse.return_value.close.side_effect = OSError("private response failure")
    assert send(uploader()).sha256 == DIGEST


def test_control_exception_propagates_after_cleanup(connection):
    conn, _ = connection
    conn.send.side_effect = KeyboardInterrupt()
    with pytest.raises(KeyboardInterrupt):
        send(uploader())
    conn.close.assert_called_once()
