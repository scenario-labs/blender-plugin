# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Credential-free signed storage downloads; never a Scenario API client."""

import hashlib
import http.client
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
    """Sanitized storage failure; signed URLs must not enter persistent errors."""


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
    total_timeout: float = 300.0

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
        if not _positive(self.timeout) or not _positive(self.total_timeout):
            raise ValueError("Configure finite positive timeouts")

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
                or parsed.hostname not in self.hosts
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
    return path


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
    redirect, retry or URL-logging behavior. Debug output remains disabled.
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

    def download(self, url, *, root, name, expected_size=None, expected_sha256=None):
        """Publish complete verified bytes atomically without replacing a result.

        Content hashes supplied by a trusted manifest are optional. Without one,
        the returned digest detects later local changes, not server authenticity.
        Temporary cleanup is attempted on ordinary/control exceptions. Once
        published, cleanup failures cannot turn verified output into a failed
        transfer. After cleanup failure or process death, unreferenced
        .scenario-download-* directories can be removed by
        the application after all its workers stop; never infer successful jobs
        from partial files or replay generation to recover a download.
        """
        host, target = self._policy.destination(url)
        if expected_size is not None and (
            not isinstance(expected_size, int)
            or isinstance(expected_size, bool)
            or not 0 <= expected_size <= self._policy.max_bytes
        ):
            raise TransferError("Invalid expected result size")
        if expected_sha256 is not None and (
            not isinstance(expected_sha256, str)
            or not re.fullmatch(r"[a-fA-F0-9]{64}", expected_sha256)
        ):
            raise TransferError("Invalid expected result digest")
        if expected_sha256 is not None:
            expected_sha256 = expected_sha256.lower()
        connection = None
        try:
            root = _root(root)
            destination = root / validate_result_name(name)
            if destination.exists() or destination.is_symlink():
                raise TransferError("Result filename already exists")
            if not self._online_access():
                raise TransferError("Online access is disabled")
            deadline = time.monotonic() + self._policy.total_timeout
            context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
            context.load_verify_locations(cafile=certifi.where())
            connection = http.client.HTTPSConnection(
                host,
                timeout=min(self._policy.timeout, self._policy.total_timeout),
                context=context,
            )
            connection.set_debuglevel(0)
            connection.connect()
            transfer_socket = connection.sock

            def check_permission_and_deadline():
                remaining = deadline - time.monotonic()
                if remaining <= 0 or not self._online_access():
                    raise TransferError("Storage transfer interrupted")
                if transfer_socket.fileno() != -1:
                    transfer_socket.settimeout(min(self._policy.timeout, remaining))

            check_permission_and_deadline()
            connection.request(
                "GET", target, headers={"Accept-Encoding": "identity", "Connection": "close"}
            )
            check_permission_and_deadline()
            response = connection.getresponse()
            with ExitStack() as cleanup:
                cleanup.callback(_cleanup, response.close)
                staging_directory = tempfile.TemporaryDirectory(
                    prefix=".scenario-download-", dir=root
                )
                cleanup.callback(_cleanup, staging_directory.cleanup)
                staging = staging_directory.name
                if response.status != 200:
                    raise TransferError("Storage request did not return a complete result")
                if response.getheader("Content-Encoding", "identity").lower() != "identity":
                    raise TransferError("Encoded storage responses are unsupported")
                if response.getheader("Transfer-Encoding") is not None:
                    raise TransferError("Transfer-encoded storage responses are unsupported")
                length = response.getheader("Content-Length")
                if length is not None:
                    if (
                        not re.fullmatch(r"[0-9]{1,20}", length)
                        or int(length) > self._policy.max_bytes
                    ):
                        raise TransferError("Storage response size is invalid")
                    length = int(length)
                    if expected_size is not None and length != expected_size:
                        raise TransferError("Storage response size does not match")
                size, digest = 0, hashlib.sha256()
                temporary = Path(staging) / "result.part"
                with temporary.open("xb") as output:
                    os.chmod(temporary, 0o600)
                    while True:
                        check_permission_and_deadline()
                        # One underlying read prevents a trickling body from
                        # hiding inside a read-until-full call.
                        chunk = response.read1(min(65536, self._policy.max_bytes - size + 1))
                        if not chunk:
                            break
                        size += len(chunk)
                        if size > self._policy.max_bytes:
                            raise TransferError("Storage response exceeds the byte limit")
                        digest.update(chunk)
                        output.write(chunk)
                    if (length is not None and size != length) or (
                        expected_size is not None and size != expected_size
                    ):
                        raise TransferError("Storage response is incomplete")
                    if expected_sha256 is not None and digest.hexdigest() != expected_sha256:
                        raise TransferError("Storage response digest does not match")
                    output.flush()
                    os.fsync(output.fileno())
                # Hard-link publication is atomic and fails if anything already
                # occupies the name, including a symlink. Same filesystem only.
                check_permission_and_deadline()
                receipt = DownloadedResult(name, size, digest.hexdigest())
                os.link(temporary, destination)
                return receipt
        except TransferError:
            raise
        except Exception:
            raise TransferError("Storage transfer failed") from None
        finally:
            if connection is not None:
                _cleanup(connection.close)


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

            def identity(value):
                return (
                    value.st_dev,
                    value.st_ino,
                    value.st_size,
                    value.st_mtime_ns,
                    value.st_ctime_ns,
                    value.st_mode,
                )

            if (
                size != receipt.size
                or digest.hexdigest() != receipt.sha256
                or identity(before) != identity(after)
                or identity(after) != identity(current)
            ):
                raise TransferError("Result does not match its receipt")
        return path
    except TransferError:
        raise
    except (OSError, ValueError, RuntimeError):
        raise TransferError("Local result verification failed") from None
