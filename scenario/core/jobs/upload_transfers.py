# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""One credential-free signed PUT attempt for an immutable, verified upload part."""

import hashlib
import http.client
import re
import ssl
import time
from dataclasses import dataclass

import certifi

from .transfers import StoragePolicy, TransferError, _cleanup, _host


class S3UploadPolicy(StoragePolicy):
    """S3 REST destinations supplied by the scoped SDK multipart upload plan.

    This policy is for upload parts only, never arbitrary caller URLs or result
    downloads. The coordinator validates the known upload and source identity
    before selecting a part URL. See docs/SDK_UPLOADS.md for the trust boundary.
    """

    def __init__(self, *, max_bytes=8 * 1024 * 1024):
        super().__init__(frozenset({"s3.amazonaws.com"}), max_bytes=max_bytes)

    def _allows_host(self, host):
        if not _host(host):
            return False
        # Public S3 global/regional REST endpoints, optionally virtual-hosted or
        # dual-stack. This is not a wildcard for all AWS services or custom CNAMEs.
        return (
            re.fullmatch(
                r"(?:[a-z0-9][a-z0-9.-]{1,61}[a-z0-9]\.)?"
                r"s3(?:(?:\.dualstack)?[.-][a-z]{2}(?:-[a-z]+){1,2}-[0-9]+)?"
                r"\.amazonaws\.com",
                host,
            )
            is not None
        )


class UploadUncertain(TransferError):
    """A storage write may have happened; do not retry or finalize implicitly."""


@dataclass(frozen=True)
class UploadedPart:
    number: int
    size: int
    sha256: str


class PartUploader:
    """The caller persists upload/part intent before invoking this primitive.

    SDK initialization/retrieval/completion remain in the shared adapter. This
    class accepts already-snapshotted immutable bytes, has no Scenario credentials,
    and never initializes, retries or finalizes an upload.
    """

    def __init__(self, policy: StoragePolicy, *, online_access):
        if not isinstance(policy, StoragePolicy) or not callable(online_access):
            raise TypeError("Storage policy and online permission predicate required")
        self._policy = policy
        self._online_access = online_access

    @property
    def policy(self):
        return self._policy

    def upload(self, url, data, *, number, content_type, expected_sha256):
        host, target = self._policy.destination(url)
        if type(number) is not int or number < 1:
            raise TransferError("Upload part number must be a positive integer")
        if not isinstance(data, bytes) or not 1 <= len(data) <= self._policy.max_bytes:
            raise TransferError("Use nonempty immutable upload bytes within the part limit")
        if not isinstance(content_type, str) or not re.fullmatch(
            r"[A-Za-z0-9!#$&^_.+-]+/[A-Za-z0-9!#$&^_.+-]+", content_type
        ):
            raise TransferError("Use an upload MIME type without header parameters")
        digest = hashlib.sha256(data).hexdigest()
        if (
            not isinstance(expected_sha256, str)
            or not re.fullmatch(r"[a-f0-9]{64}", expected_sha256)
            or digest != expected_sha256
        ):
            raise TransferError("Upload part bytes do not match the saved identity")
        receipt = UploadedPart(number, len(data), digest)
        connection, response, attempted = None, None, False
        try:
            if not self._online_access():
                raise TransferError("Online access is disabled")
            deadline = time.monotonic() + self._policy.total_timeout
            context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
            context.load_verify_locations(cafile=certifi.where())
            connection = http.client.HTTPSConnection(
                host, timeout=min(self._policy.timeout, self._policy.total_timeout), context=context
            )
            connection.set_debuglevel(0)
            connection.connect()
            transfer_socket = connection.sock

            def check():
                remaining = deadline - time.monotonic()
                if remaining <= 0 or not self._online_access():
                    raise TransferError("Storage upload interrupted")
                if transfer_socket.fileno() != -1:
                    transfer_socket.settimeout(min(self._policy.timeout, remaining))

            check()
            connection.putrequest("PUT", target, skip_accept_encoding=True)
            connection.putheader("Content-Type", content_type)
            connection.putheader("Content-Length", str(len(data)))
            connection.putheader("Connection", "close")
            # Mark uncertainty before the first possible write, including a lost
            # response to headers/body. No redirect, retry or ambient proxy stack.
            attempted = True
            connection.endheaders()
            for offset in range(0, len(data), 65536):
                check()
                connection.send(data[offset : offset + 65536])
            check()
            response = connection.getresponse()
            if response.status not in {200, 201, 204}:
                raise UploadUncertain("Storage did not acknowledge the upload part")
            # No response body/ETag is logged or persisted. A 2xx acknowledges this
            # PUT only, not finalization, asset import or remote digest validation.
            return receipt
        except Exception:
            if attempted:
                raise UploadUncertain("Upload part outcome requires explicit review") from None
            raise TransferError("Upload part was not sent") from None
        finally:
            if response is not None:
                _cleanup(response.close)
            if connection is not None:
                _cleanup(connection.close)
