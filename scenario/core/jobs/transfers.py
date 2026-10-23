# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Credential-free signed storage downloads; never a Scenario API client."""

import hashlib
import http.client
import io
import math
import os
import re
import ssl
import stat
import tempfile
import time
from contextlib import ExitStack
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlsplit

import certifi


class TransferError(RuntimeError):
    """Sanitized storage failure; signed URLs must not enter persistent errors.

    ``retryable`` marks a transport failure that another attempt with a fresh
    signed URL may cure. Policy, metadata, digest, permission and cancellation
    failures are never retryable.
    """

    retryable = False


class TransferInterrupted(TransferError):
    """Online Access or the caller's cancel event stopped the transfer; never retried."""


class RetryableTransferError(TransferError):
    """A transport failure: a refused or failed request, a cut-short body or the deadline."""

    retryable = True


# A strong entity tag: a quoted opaque string, never the weak "W/" form.
_STRONG_ETAG = re.compile(r'"[\x21\x23-\x7e]+"')
_CONTENT_RANGE = re.compile(r"bytes ([0-9]{1,20})-([0-9]{1,20})/([0-9]{1,20})")


def _positive(value):
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(value)
        and value > 0
    )


def _host(value):
    return (
        isinstance(value, str)
        and len(value) <= 253
        and value == value.lower()
        and "." in value
        and all(re.fullmatch(r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?", p) for p in value.split("."))
        and not all(re.fullmatch(r"(?:[0-9]+|0x[0-9a-f]+)", p) for p in value.split("."))
        and not value.endswith((".localhost", ".local"))
    )


@dataclass(frozen=True)
class StoragePolicy:
    """Exact trusted storage hosts, with no default or wildcard allowlist.

    Obtain hosts from reviewed application configuration, never from the URL
    being checked. DNS and the configured hosts are trusted infrastructure.
    """

    hosts: frozenset[str]
    max_bytes: int = 256 * 1024 * 1024
    timeout: float = 30.0
    # A new connection tries each address of the DNS answer in turn for this long,
    # so an address that never accepts delays it by this much, not by ``timeout``.
    connect_timeout: float = 5.0
    # Each attempt's elapsed budget scales with its size: the larger of this
    # floor and the size at ``min_rate`` bytes per second, at most the ceiling.
    total_timeout: float = 300.0
    min_rate: int = 256 * 1024
    max_total_timeout: float = 1800.0

    def __post_init__(self):
        if (
            not isinstance(self.hosts, frozenset)
            or not self.hosts
            or not all(map(_host, self.hosts))
        ):
            raise ValueError("Configure exact trusted storage hostnames")
        if (
            not isinstance(self.max_bytes, int)
            or isinstance(self.max_bytes, bool)
            or self.max_bytes < 1
        ):
            raise ValueError("Configure a positive byte limit")
        if (
            not _positive(self.timeout)
            or not _positive(self.connect_timeout)
            or not _positive(self.total_timeout)
            or not _positive(self.max_total_timeout)
            or self.max_total_timeout < self.total_timeout
        ):
            raise ValueError("Configure finite positive timeouts")
        if not _positive(self.min_rate):
            raise ValueError("Configure a positive minimum transfer rate")

    def deadline(self, size=None):
        """Seconds one attempt may take for ``size`` bytes; the floor when unknown."""
        if size is None:
            return self.total_timeout
        return min(self.max_total_timeout, max(self.total_timeout, size / self.min_rate))

    def destination(self, url):
        if (
            not isinstance(url, str)
            or not url.isascii()
            or any(ord(c) <= 32 or ord(c) == 127 for c in url)
            or "\\" in url
        ):
            raise TransferError("Storage destination rejected")
        try:
            parsed = urlsplit(url)
            if (
                parsed.scheme != "https"
                or not self._allows_host(parsed.hostname)
                or parsed.username is not None
                or parsed.password is not None
                or parsed.port not in (None, 443)
                or parsed.fragment
                or parsed.netloc not in (parsed.hostname, f"{parsed.hostname}:443")
            ):
                raise ValueError
        except ValueError:
            raise TransferError("Storage destination rejected") from None
        return parsed.hostname, (parsed.path or "/") + (f"?{parsed.query}" if parsed.query else "")

    def _allows_host(self, host):
        return host in self.hosts


@dataclass(frozen=True)
class DownloadedResult:
    """URL-free receipt for caller-owned persistence and subsequent verification."""

    name: str
    size: int
    sha256: str

    def __post_init__(self):
        validate_result_name(self.name)
        if type(self.size) is not int or not 0 <= self.size <= 2**63 - 1:
            raise TransferError("Invalid downloaded result size")
        if not isinstance(self.sha256, str) or not re.fullmatch(r"[a-f0-9]{64}", self.sha256):
            raise TransferError("Invalid downloaded result digest")


def _windows_storage_path(path):
    """Namespace an already validated absolute root for deep private descendants."""
    value = str(path)
    if value.startswith("\\\\.\\"):
        raise TransferError("Use an absolute drive or UNC result directory")
    if not path.drive or value.startswith("\\\\?\\"):
        return path
    if path.drive.startswith("\\\\"):
        value = "\\\\?\\UNC\\" + value[2:]
    else:
        value = "\\\\?\\" + value
    return type(path)(value)


def _root(root):
    path = Path(root)
    # The caller owns this private directory and its ancestors for the entire
    # operation. Resolving a symlink here would silently authorize another root.
    try:
        valid = path.is_absolute() and path == path.resolve(strict=True) and path.is_dir()
    except (OSError, RuntimeError):
        # Missing/inaccessible paths and symlink loops are local setup failures.
        valid = False
    if not valid:
        raise TransferError("Use an existing absolute private result directory")
    # Blender's Windows process need not opt into long Win32 paths. Keep the
    # canonical/symlink check above, then use the same root's extended namespace
    # before adding scope directories, result names or transfer staging files.
    return _windows_storage_path(path) if os.name == "nt" else path


def validate_result_name(name):
    # Portable basename only, including Windows reserved-name protection.
    if (
        not isinstance(name, str)
        or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,119}", name)
        or name.endswith(".")
        or name.split(".")[0].upper()
        in {
            "CON",
            "PRN",
            "AUX",
            "NUL",
            *(f"COM{i}" for i in range(1, 10)),
            *(f"LPT{i}" for i in range(1, 10)),
        }
    ):
        raise TransferError("Use a portable result filename")
    return name


class PartialDownload:
    """Private staged bytes kept between the attempts of one result download.

    One caller owns it for one result name in one root, on one thread. A later
    attempt resumes with ``Range`` and ``If-Range`` only when the earlier reply
    carried a strong ETag and a complete byte count; otherwise it starts from
    zero. Bytes stay in a private ``.scenario-download-*`` directory and are
    never published or receipted unless a whole verified body is complete.
    The owner calls ``discard`` when it stops trying.
    """

    def __init__(self):
        self._staging = None
        self._key = None
        self._reset()

    def _reset(self):
        self.size, self.etag, self.total = 0, None, None
        self._digest = hashlib.sha256()

    @property
    def resumable(self):
        return (
            self._staging is not None
            and self.etag is not None
            and self.total is not None
            and 0 < self.size < self.total
        )

    def _bind(self, root, name):
        key = (str(root), name)
        if self._key is not None and self._key != key:
            raise TransferError("This partial download belongs to another result")
        self._key = key
        if self._staging is None:
            self._staging = tempfile.TemporaryDirectory(prefix=".scenario-download-", dir=root)
            self._reset()
        return Path(self._staging.name) / "result.part"

    def discard(self):
        """Remove the staged bytes; the next attempt, if any, starts from zero."""
        staging, self._staging = self._staging, None
        self._reset()
        if staging is not None:
            _cleanup(staging.cleanup)


# Body reads wait at most this long, so cancellation and Online Access are seen
# within about half a second even while a server sends nothing. The policy's
# socket timeout still bounds inactivity, through a separate clock.
POLL_INTERVAL = 0.5


class _PollingReader(io.RawIOBase):
    """The response body's raw stream: a socket read that may time out and be retried.

    The standard ``socket.SocketIO`` refuses every read after one timeout. A
    timed-out ``recv_into`` consumes nothing, on plain and TLS sockets alike,
    so the body can be read again after the downloader checks cancellation.
    """

    def __init__(self, sock):
        super().__init__()
        # A counted reference, as the standard response holds, so the socket
        # stays open until this stream closes.
        self._stream = sock.makefile("rb", buffering=0)
        self._sock = sock

    def readable(self):
        return True

    def readinto(self, buffer):
        return self._sock.recv_into(buffer)

    def close(self):
        if not self.closed:
            _cleanup(self._stream.close)
        super().close()


class _PollingResponse(http.client.HTTPResponse):
    """An HTTP response whose body read can time out without ending the transfer."""

    def __init__(self, sock, *args, **kwargs):
        super().__init__(sock, *args, **kwargs)
        # Nothing has been read from the standard stream yet; replace it.
        self.fp.close()
        self.fp = io.BufferedReader(_PollingReader(sock))


def _cleanup(close):
    try:
        close()
    except Exception:
        # Do not mask the verified publication or an existing transfer/control
        # failure. Recovery can remove leftover staging after workers stop.
        pass


class ResultDownloader:
    """One attempt per explicit download, with no credentials or ambient proxies.

    The stdlib HTTPS connection has no cookie jar, netrc, authorization, proxy,
    automatic retry or URL-logging behavior. At most two same-host HTTPS
    redirects are validated explicitly. Debug output remains disabled.
    The application must supply its online-access predicate and a private root
    under extension_path_user. This primitive does not mutate job state.
    """

    def __init__(self, policy: StoragePolicy, *, online_access):
        if not isinstance(policy, StoragePolicy) or not callable(online_access):
            raise TypeError("Storage policy and online permission predicate required")
        self._policy = policy
        self._online_access = online_access

    def verify(self, root, receipt):
        """Verify local bytes with the same size bound as this transfer policy."""
        return verify_download(root, receipt, max_bytes=self._policy.max_bytes)

    def download(
        self,
        url,
        *,
        root,
        name,
        expected_size=None,
        expected_sha256=None,
        max_bytes=None,
        allow_size_mismatch=False,
        cancel=None,
        partial=None,
    ):
        """Publish complete verified bytes atomically without replacing a result.

        Content hashes supplied by a trusted manifest are optional. Without one,
        the returned digest detects later local changes, not server authenticity.
        Without an expected size, the response must declare a valid Content-Length
        (or, when resuming, Content-Range) that the streamed body matches; an
        unbounded body is never published. Temporary cleanup is attempted on
        ordinary/control exceptions. Once published, cleanup failures cannot turn
        verified output into a failed transfer. After cleanup failure or process
        death, unreferenced .scenario-download-* directories can be removed by
        the application after all its workers stop; never infer successful jobs
        from partial files or replay generation to recover a download.

        An optional ``cancel`` event is checked with online permission before
        each connection and chunk, and every ``POLL_INTERVAL`` while a body read
        waits; once set, the transfer stops unpublished. Each call is one attempt whose elapsed budget is ``policy.deadline`` of
        the expected (or declared) size. An optional caller-owned
        ``PartialDownload`` keeps staged bytes after a retryable failure so the
        caller's next attempt can resume them; see its docstring.
        """
        limit = self._policy.max_bytes
        if type(allow_size_mismatch) is not bool:
            raise TransferError("Choose an explicit result size policy")
        if cancel is not None and not callable(getattr(cancel, "is_set", None)):
            raise TransferError("Use a cancellation event")
        if partial is not None and not isinstance(partial, PartialDownload):
            raise TransferError("Use a partial download owned by this result")
        if max_bytes is not None:
            if type(max_bytes) is not int or max_bytes < 1:
                raise TransferError("Invalid result byte limit")
            limit = min(limit, max_bytes)
        host, target = self._policy.destination(url)
        if expected_size is not None and (
            not isinstance(expected_size, int)
            or isinstance(expected_size, bool)
            or not 0 <= expected_size <= limit
        ):
            raise TransferError("Invalid expected result size")
        if expected_sha256 is not None and (
            not isinstance(expected_sha256, str)
            or not re.fullmatch(r"[a-fA-F0-9]{64}", expected_sha256)
        ):
            raise TransferError("Invalid expected result digest")
        if expected_sha256 is not None:
            expected_sha256 = expected_sha256.lower()
        staged = PartialDownload() if partial is None else partial

        def permitted():
            return self._online_access() and (cancel is None or not cancel.is_set())

        connection = None
        retain = False
        try:
            root = _root(root)
            destination = root / validate_result_name(name)
            if destination.exists() or destination.is_symlink():
                raise TransferError("Result filename already exists")
            if not permitted():
                raise TransferInterrupted("Online access is disabled")
            temporary = staged._bind(root, name)
            resume = staged.resumable
            if resume:
                try:
                    # A staged file that lost bytes (or gained some) restarts from zero.
                    resume = temporary.lstat().st_size == staged.size
                except OSError:
                    resume = False
                if not resume:
                    staged._reset()
            started = time.monotonic()
            deadline = started + self._policy.deadline(expected_size)
            context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
            context.load_verify_locations(cafile=certifi.where())
            transfer_socket = None

            def check_permission_and_deadline(wait=None):
                if not permitted():
                    raise TransferInterrupted("Storage transfer interrupted")
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise RetryableTransferError("Storage transfer interrupted")
                if transfer_socket is not None and transfer_socket.fileno() != -1:
                    transfer_socket.settimeout(min(wait or self._policy.timeout, remaining))
                return remaining

            headers = {"Accept-Encoding": "identity", "Connection": "close"}
            if resume:
                # If-Range makes the server send the whole object when its strong
                # validator changed, so a resumed body cannot mix two versions.
                headers["Range"] = f"bytes={staged.size}-"
                headers["If-Range"] = staged.etag
            visited = {target}
            for redirects in range(3):
                remaining = check_permission_and_deadline()
                connection = http.client.HTTPSConnection(
                    host,
                    timeout=min(self._policy.connect_timeout, self._policy.timeout, remaining),
                    context=context,
                )
                connection.set_debuglevel(0)
                # Its body reads can time out briefly without ending the transfer.
                connection.response_class = _PollingResponse
                connection.connect()
                transfer_socket = connection.sock
                check_permission_and_deadline()
                connection.request("GET", target, headers=headers)
                check_permission_and_deadline()
                response = connection.getresponse()
                if response.status not in {301, 302, 303, 307, 308}:
                    break
                try:
                    if redirects == 2:
                        raise TransferError("Storage redirect limit exceeded")
                    next_host, next_target = self._policy.destination(
                        response.getheader("Location")
                    )
                    if next_host != host or next_target in visited:
                        raise TransferError("Storage redirect destination rejected")
                    visited.add(next_target)
                    target = next_target
                finally:
                    _cleanup(response.close)
                    _cleanup(connection.close)
                    connection = None
                    transfer_socket = None
            with ExitStack() as cleanup:
                cleanup.callback(_cleanup, response.close)
                etag = response.getheader("ETag")
                if response.status == 206 and resume:
                    offset, total = staged.size, self._content_range(response, staged)
                    if etag != staged.etag:
                        staged._reset()
                        raise RetryableTransferError("Storage resumed a different result")
                elif response.status == 200:
                    # A full reply, including one to a ranged request whose
                    # validator no longer matched: start again from zero.
                    offset, total = 0, None
                    staged._reset()
                else:
                    # A refused or failed request leaves the staged bytes as
                    # they were; only an unsatisfiable range invalidates them.
                    if response.status == 416:
                        staged._reset()
                    raise RetryableTransferError("Storage request did not return a complete result")
                if response.getheader("Content-Encoding", "identity").lower() != "identity":
                    raise TransferError("Encoded storage responses are unsupported")
                if response.getheader("Transfer-Encoding") is not None:
                    raise TransferError("Transfer-encoded storage responses are unsupported")
                length = response.getheader("Content-Length")
                if length is not None:
                    if not re.fullmatch(r"[0-9]{1,20}", length) or int(length) > limit:
                        raise TransferError("Storage response size is invalid")
                    length = int(length)
                    if offset and length != total - offset:
                        staged._reset()
                        raise RetryableTransferError("Storage resumed an inconsistent range")
                if not offset:
                    total = length
                # Without a trusted size, a close-delimited body that ends early
                # (including a TLS close without close_notify) reads like EOF.
                if (allow_size_mismatch or expected_size is None) and total is None:
                    raise TransferError("Storage response needs a complete byte count")
                if total is not None:
                    if total > limit:
                        raise TransferError("Storage response size is invalid")
                    if (
                        not allow_size_mismatch
                        and expected_size is not None
                        and total != expected_size
                    ):
                        raise TransferError("Storage response size does not match")
                    if expected_size is None:
                        deadline = started + self._policy.deadline(total)
                staged.total = total if total is not None else expected_size
                staged.etag = (
                    etag if isinstance(etag, str) and _STRONG_ETAG.fullmatch(etag) else None
                )
                if offset:
                    output = temporary.open("r+b")
                    output.seek(offset)
                    output.truncate()
                else:
                    if temporary.exists() or temporary.is_symlink():
                        temporary.unlink()
                    output = temporary.open("xb")
                    os.chmod(temporary, 0o600)
                with output:
                    idle_since = time.monotonic()
                    while True:
                        check_permission_and_deadline(POLL_INTERVAL)
                        # One underlying read prevents a trickling body from
                        # hiding inside a read-until-full call.
                        try:
                            chunk = response.read1(min(65536, limit - staged.size + 1))
                        except TimeoutError:
                            # Nothing arrived for a moment: check cancellation and
                            # permission again, up to the policy's inactivity limit.
                            if time.monotonic() - idle_since >= self._policy.timeout:
                                raise RetryableTransferError("Storage transfer stalled") from None
                            continue
                        idle_since = time.monotonic()
                        if not chunk:
                            break
                        if staged.size + len(chunk) > limit:
                            raise TransferError("Storage response exceeds the byte limit")
                        output.write(chunk)
                        staged.size += len(chunk)
                        staged._digest.update(chunk)
                    size = staged.size
                    if (total is not None and size != total) or (
                        not allow_size_mismatch
                        and expected_size is not None
                        and size != expected_size
                    ):
                        raise RetryableTransferError("Storage response is incomplete")
                    digest = staged._digest.hexdigest()
                    if expected_sha256 is not None and digest != expected_sha256:
                        raise TransferError("Storage response digest does not match")
                    output.flush()
                    os.fsync(output.fileno())
                # Hard-link publication is atomic and fails if anything already
                # occupies the name, including a symlink. Same filesystem only.
                check_permission_and_deadline()
                receipt = DownloadedResult(name, size, digest)
                os.link(temporary, destination)
                return receipt
        except Exception as error:
            cancelled = cancel is not None and cancel.is_set()
            if isinstance(error, TransferError) and not (cancelled and error.retryable):
                retain = error.retryable
                raise
            if cancelled:
                # A cancelled read may end in EOF, a reset or a TLS error: all
                # of them are this cancellation, never a retryable failure.
                raise TransferInterrupted("Storage transfer interrupted") from None
            # Sockets, TLS, HTTP framing and local writes: another attempt may succeed.
            retain = True
            raise RetryableTransferError("Storage transfer failed") from None
        finally:
            if connection is not None:
                _cleanup(connection.close)
            # Success, control exceptions and every non-retryable failure remove
            # the staging. A caller's PartialDownload survives a retryable one,
            # including one before any body byte, while its staged bytes still
            # resume: every reply that replaces or contradicts them resets it,
            # and the next attempt checks the staged file's size first.
            if partial is None or not retain or not staged.resumable:
                staged.discard()

    @staticmethod
    def _content_range(response, staged):
        """The full size a 206 reply declares; it must continue exactly at our offset."""
        match = _CONTENT_RANGE.fullmatch(response.getheader("Content-Range") or "")
        if match is None:
            staged._reset()
            raise RetryableTransferError("Storage resumed an inconsistent range")
        first, last, total = map(int, match.groups())
        if first != staged.size or total != staged.total or last != total - 1:
            staged._reset()
            raise RetryableTransferError("Storage resumed an inconsistent range")
        return total


def verify_download(root, receipt, *, max_bytes=256 * 1024 * 1024):
    """Rehash a private local file before explicit recovery/application.

    No network, repair, deletion or scene mutation. The caller continues owning
    the private directory and must prevent file replacement through application.
    A receipt proves local consistency, not authenticity of provider content.
    """
    if not isinstance(receipt, DownloadedResult):
        raise TransferError("A verified download receipt is required")
    if type(max_bytes) is not int or max_bytes < 1 or receipt.size > max_bytes:
        raise TransferError("Result verification exceeds the byte limit")
    try:
        path = _root(root) / validate_result_name(receipt.name)
        if not stat.S_ISREG(path.lstat().st_mode):
            raise TransferError("Result must be a regular local file")
        flags = (
            os.O_RDONLY
            | getattr(os, "O_NOFOLLOW", 0)
            | getattr(os, "O_NONBLOCK", 0)
            | getattr(os, "O_BINARY", 0)
        )
        descriptor = os.open(path, flags)
        with os.fdopen(descriptor, "rb") as source:
            before = os.fstat(source.fileno())
            if not stat.S_ISREG(before.st_mode) or before.st_size != receipt.size:
                raise TransferError("Result size does not match its receipt")
            digest, size = hashlib.sha256(), 0
            while True:
                chunk = source.read(min(65536, receipt.size - size + 1))
                if not chunk:
                    break
                size += len(chunk)
                if size > receipt.size:
                    raise TransferError("Result changed during verification")
                digest.update(chunk)
            after = os.fstat(source.fileno())
            current = path.lstat()

            def identity(value, *, timestamp="st_ctime_ns"):
                return (
                    value.st_dev,
                    value.st_ino,
                    value.st_size,
                    value.st_mtime_ns,
                    getattr(value, timestamp),
                    value.st_mode,
                )

            # Windows Python 3.12+ can report metadata-change ctime for a
            # descriptor and creation ctime for a path. Compare birthtime
            # across those APIs, while retaining the descriptor ctime check.
            path_timestamp = (
                "st_birthtime_ns"
                if os.name == "nt" and hasattr(after, "st_birthtime_ns")
                else "st_ctime_ns"
            )
            if (
                size != receipt.size
                or digest.hexdigest() != receipt.sha256
                or identity(before) != identity(after)
                or identity(after, timestamp=path_timestamp)
                != identity(current, timestamp=path_timestamp)
            ):
                raise TransferError("Result does not match its receipt")
        return path
    except TransferError:
        raise
    except (OSError, ValueError, RuntimeError):
        raise TransferError("Local result verification failed") from None
