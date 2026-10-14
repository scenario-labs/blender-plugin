# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Verified local files of saved results, for status display only.

A worker on the preview lane rehashes each downloaded result of a ready job
against its saved receipt and returns where the file is, with its identity
(device, inode, size, times and mode) as it was hashed. A status read on the
main thread then compares only that identity, with one ``lstat``, so a file
changed, replaced or removed after its check is checked again before it is
listed. Checks follow the saved store and receipts, not this session's
imports, so they work the same after a restart. A listed file grants no
application authority: every application still rehashes the bytes it reads.
"""

import os
from dataclasses import dataclass, field

from .store import JobState

# A job whose every result is downloaded; an interrupted transfer needs recovery first.
READY_STATES = frozenset(
    {JobState.READY, JobState.APPLYING, JobState.APPLY_FAILED, JobState.APPLIED}
)

VERIFIED = "verified"
MISSING = "missing"
CHANGED = "changed"
CHECKING = "checking"
UNAVAILABLE = "unavailable"
NOT_DOWNLOADED = "not_downloaded"
NOT_READY = "not_ready"


def file_stamp(path):
    """Identity of the file at ``path`` without following links, or None when absent.

    Any other failure is a stable marker, so an unreadable entry stays settled
    until it changes instead of being rehashed on every read.
    """
    try:
        value = os.lstat(path)
    except (FileNotFoundError, NotADirectoryError):
        return None
    except OSError:
        return ("unreadable",)
    return (
        value.st_dev,
        value.st_ino,
        value.st_size,
        value.st_mtime_ns,
        value.st_ctime_ns,
        value.st_mode,
    )


@dataclass(frozen=True)
class FileCheck:
    """One settled check of a receipt: verified, missing, changed or unavailable."""

    sha256: str
    state: str
    path: str | None = field(default=None, repr=False)
    stamp: tuple | None = None


@dataclass(frozen=True)
class FileRow:
    """A result's local file as status reports it; ``file`` only when verified."""

    asset_id: str
    file: str | None
    state: str


class ResultFiles:
    """Session memory of result file checks, owned by the main thread.

    ``pending`` alone may be read from another thread: it only looks up this
    memory. Jobs are checked once a status read asks for them (``watch``).
    One batch of at most ``BATCH_LIMIT`` targets is in flight at a time, so
    the checks never hold the preview lane longer than a preview batch.
    """

    def __init__(self):
        self._checks = {}
        self._watched = set()
        self._task = None

    @property
    def watched(self):
        return frozenset(self._watched)

    @property
    def busy(self):
        """Whether a batch is in flight; ``start`` queues nothing until it finishes."""
        return self._task is not None

    def watch(self, request_id):
        self._watched.add(request_id)

    def forget(self, request_id):
        self._watched.discard(request_id)
        for key in [key for key in self._checks if key[0] == request_id]:
            del self._checks[key]

    def _in_flight(self):
        task = self._task
        return task[1] if task is not None else frozenset()

    def _settled(self, request_id, item):
        check = self._checks.get((request_id, item.asset.asset_id))
        return check is not None and check.sha256 == item.receipt.sha256

    def unchecked(self, record):
        """Targets of a watched ready job that have no settled check and none in flight."""
        request_id = record.intent.request_id
        if request_id not in self._watched or record.state not in READY_STATES:
            return ()
        in_flight = self._in_flight()
        return tuple(
            target
            for item in record.results
            if item.receipt is not None
            for target in ((request_id, item.asset.asset_id, item.receipt.sha256),)
            if not self._settled(request_id, item) and target not in in_flight
        )

    def pending(self, record):
        """Whether a status read of this watched ready job would still say checking."""
        request_id = record.intent.request_id
        if request_id not in self._watched or record.state not in READY_STATES:
            return False
        return any(
            item.receipt is not None and not self._settled(request_id, item)
            for item in record.results
        )

    def retry_unavailable(self, record):
        """Let an explicit status read check again what a failed batch left unavailable."""
        request_id = record.intent.request_id
        for item in record.results:
            key = (request_id, item.asset.asset_id)
            check = self._checks.get(key)
            if check is not None and check.state == UNAVAILABLE:
                del self._checks[key]

    def project(self, record):
        """Rows in result order; a file whose identity changed since its check is unchecked."""
        request_id = record.intent.request_id
        ready = record.state in READY_STATES
        rows = []
        for item in record.results:
            asset_id = item.asset.asset_id
            if item.receipt is None:
                rows.append(FileRow(asset_id, None, NOT_DOWNLOADED))
                continue
            if not ready:
                rows.append(FileRow(asset_id, None, NOT_READY))
                continue
            key = (request_id, asset_id)
            check = self._checks.get(key)
            if check is not None and (
                check.sha256 != item.receipt.sha256
                or (check.state != UNAVAILABLE and file_stamp(check.path) != check.stamp)
            ):
                del self._checks[key]
                check = None
            if check is None:
                rows.append(FileRow(asset_id, None, CHECKING))
            else:
                rows.append(
                    FileRow(asset_id, check.path if check.state == VERIFIED else None, check.state)
                )
        return tuple(rows)

    def start(self, queue, targets):
        """Queue one bounded batch unless one is in flight; a refused queue is retried later."""
        # Imported here: the scheduler imports the workers, which import the results.
        from .preview_scheduler import BATCH_LIMIT

        if self._task is not None or not targets:
            return
        targets = tuple(targets[:BATCH_LIMIT])
        try:
            task = queue(targets)
        except Exception:
            # A full or retired preview lane: the next poll queues them again.
            return
        self._task = (task, frozenset(targets))

    def finish(self):
        """Record a finished batch; a failed one leaves its targets unavailable."""
        if self._task is None or not self._task[0].done():
            return
        task, targets = self._task
        self._task = None
        try:
            checks = {tuple(item[:3]): item[3] for item in task.result()}
        except Exception:
            checks = {target: FileCheck(target[2], UNAVAILABLE) for target in targets}
        for (request_id, asset_id, sha256), check in checks.items():
            if (request_id, asset_id, sha256) in targets and check is not None:
                self._checks[(request_id, asset_id)] = check
