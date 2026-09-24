# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Private, bounded upload snapshots; never transfer directly from a user's file."""

import hashlib
import os
import stat
from dataclasses import asdict
from pathlib import Path

from .store import _identity, _json
from .transfers import TransferError, _root
from .upload_store import UploadIntent


def _stamp(value, *, timestamp="st_ctime_ns"):
    return value.st_dev, value.st_ino, value.st_size, value.st_mtime_ns, getattr(value, timestamp)


def _open(path):
    # NONBLOCK prevents a substituted FIFO from hanging before the regular-file check.
    fd = os.open(
        path,
        os.O_RDONLY
        | getattr(os, "O_NOFOLLOW", 0)
        | getattr(os, "O_NONBLOCK", 0)
        | getattr(os, "O_BINARY", 0),
    )
    try:
        info = os.fstat(fd)
        if not stat.S_ISREG(info.st_mode) or path.is_symlink():
            raise TransferError("Use a regular unchanged upload source")
        current = path.stat()
        # Windows Python 3.12+ can report different ctime meanings for a
        # descriptor and path. Use birthtime only across these APIs; _stamp's
        # default retains ctime for the before/after descriptor read checks.
        path_timestamp = (
            "st_birthtime_ns"
            if os.name == "nt"
            and hasattr(info, "st_birthtime_ns")
            and hasattr(current, "st_birthtime_ns")
            else "st_ctime_ns"
        )
        if _stamp(info, timestamp=path_timestamp) != _stamp(current, timestamp=path_timestamp):
            raise TransferError("Use a regular unchanged upload source")
        return os.fdopen(fd, "rb"), info
    except BaseException:
        os.close(fd)
        raise


class UploadSources:
    """The application owns the root and ancestors throughout staging and transfer."""

    def __init__(self, root, *, max_bytes=256 * 1024 * 1024, part_bytes=8 * 1024 * 1024):
        if (
            type(max_bytes) is not int
            or type(part_bytes) is not int
            or not 1 <= part_bytes <= max_bytes
        ):
            raise ValueError("Use positive bounded upload source and part sizes")
        self._root = _root(root)
        self._max_bytes, self._part_bytes = max_bytes, part_bytes

    @property
    def max_part_bytes(self):
        return self._part_bytes

    def _directory(self, scope, request_id):
        _identity(request_id)
        identity = _json({"scope": asdict(scope), "request": request_id})
        return self._root / hashlib.sha256(identity.encode()).hexdigest()

    def stage(self, source, *, request_id, scope, origin, kind, content_type):
        """Return an immutable identity only after the private snapshot is durable."""
        source = Path(source)
        directory = self._directory(scope, request_id)
        created = False
        completed = False
        try:
            _root(self._root)
            stream, before = _open(source)
            with stream:
                if not 1 <= before.st_size <= self._max_bytes:
                    raise TransferError("Upload source exceeds the configured size policy")
                part_size = min(self._part_bytes, before.st_size)
                if (before.st_size + part_size - 1) // part_size > 10000:
                    raise TransferError("Upload source needs too many parts")
                directory.mkdir(mode=0o700)
                created = True
                target = directory / "source.bin"
                fd = os.open(
                    target, os.O_CREAT | os.O_EXCL | os.O_WRONLY | getattr(os, "O_BINARY", 0), 0o600
                )
                whole, part = hashlib.sha256(), hashlib.sha256()
                digests, total, part_total = [], 0, 0
                with os.fdopen(fd, "wb") as output:
                    while total < before.st_size:
                        data = stream.read(
                            min(65536, before.st_size - total, part_size - part_total)
                        )
                        if not data:
                            raise TransferError("Upload source changed during staging")
                        output.write(data)
                        whole.update(data)
                        part.update(data)
                        total += len(data)
                        part_total += len(data)
                        if part_total == part_size or total == before.st_size:
                            digests.append(part.hexdigest())
                            part, part_total = hashlib.sha256(), 0
                    if stream.read(1) or _stamp(before) != _stamp(os.fstat(stream.fileno())):
                        raise TransferError("Upload source changed during staging")
                    output.flush()
                    os.fsync(output.fileno())
                intent = UploadIntent(
                    request_id,
                    scope,
                    origin,
                    kind,
                    source.name,
                    content_type,
                    total,
                    whole.hexdigest(),
                    part_size,
                    tuple(digests),
                )
                if os.name != "nt":
                    for path in (directory, self._root):
                        fd = os.open(path, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
                        try:
                            os.fsync(fd)
                        finally:
                            os.close(fd)
                completed = True
                return intent
        except (OSError, ValueError):
            raise TransferError("Could not stage the upload source") from None
        finally:
            # Successful staging intentionally survives until the application owns cleanup.
            # On failure remove only the new private files created by this call.
            if created and not completed:
                try:
                    (directory / "source.bin").unlink(missing_ok=True)
                    directory.rmdir()
                except OSError:
                    pass

    def _source(self, intent):
        if (
            not isinstance(intent, UploadIntent)
            or intent.file_size > self._max_bytes
            or intent.part_size > self._part_bytes
        ):
            raise TransferError("Upload source no longer fits the configured policy")
        directory = _root(self._directory(intent.scope, intent.request_id))
        stream, info = _open(directory / "source.bin")
        if info.st_size != intent.file_size:
            stream.close()
            raise TransferError("Staged upload size changed")
        return stream, info

    def verify(self, intent):
        """Verify the staged whole file before initialization, without unbounded reads."""
        try:
            stream, before = self._source(intent)
            with stream:
                whole = hashlib.sha256()
                for number, expected in enumerate(intent.part_sha256, 1):
                    part = hashlib.sha256()
                    remaining = intent.part_bytes(number)
                    while remaining:
                        data = stream.read(min(remaining, 65536))
                        if not data:
                            raise TransferError("Staged upload was truncated")
                        part.update(data)
                        whole.update(data)
                        remaining -= len(data)
                    if part.hexdigest() != expected:
                        raise TransferError("Staged upload part changed")
                if (
                    whole.hexdigest() != intent.file_sha256
                    or stream.read(1)
                    or _stamp(before) != _stamp(os.fstat(stream.fileno()))
                ):
                    raise TransferError("Staged upload changed")
        except OSError:
            raise TransferError("Could not verify the staged upload") from None

    def part(self, intent, number):
        """Return only the next bounded immutable part after identity verification."""
        size = intent.part_bytes(number)
        try:
            stream, before = self._source(intent)
            with stream:
                stream.seek((number - 1) * intent.part_size)
                data = stream.read(size)
                if (
                    len(data) != size
                    or hashlib.sha256(data).hexdigest() != intent.part_sha256[number - 1]
                    or _stamp(before) != _stamp(os.fstat(stream.fileno()))
                ):
                    raise TransferError("Staged upload part changed")
                return data
        except OSError:
            raise TransferError("Could not read the staged upload part") from None
