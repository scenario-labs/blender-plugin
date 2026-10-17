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
import time
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

# The identity of a path that exists but cannot be inspected; the same shape as
# a readable identity, so it compares like one and stays stable until it changes.
UNREADABLE = ("unreadable",) * 6
# Seconds before a check that could not run is tried again, doubling up to the cap.
RETRY_DELAY = 5.0
RETRY_CAP = 300.0
# Verifications a coordinator remembers for the status reads of this session.
VERIFIED_LIMIT = 4096


def file_stamp(path):
    """Identity of the file at ``path`` without following links, or None when absent.

    A path that exists but cannot be inspected has the ``UNREADABLE`` identity.
    """
    try:
        value = os.lstat(path)
    except (FileNotFoundError, NotADirectoryError):
        return None
    except OSError:
        return UNREADABLE
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
    """One check of a receipt: verified, missing, changed or unavailable."""

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

    ``pending`` alone may be read from another thread: it reads this memory
    and the identities of the files it lists, and changes nothing. Jobs are
    checked once a status read asks for them (``watch``). One batch of at most
    ``BATCH_LIMIT`` targets is in flight at a time, so the checks never hold
    the preview lane longer than a preview batch. A check that could not run
    (``unavailable``) is still to come: it is queued again after a delay that
    doubles up to ``RETRY_CAP``, and no wait waits for it.
    """

    def __init__(self, *, clock=time.monotonic):
        self._clock = clock
        self._checks = {}
        self._watched = set()
        self._task = None
        # key -> the verification this session last applied with ``seed``. A
        # verification is applied once: after its file changes, a worker checks it.
        self._seeded = {}
        # key -> (failures, clock time before which an unavailable check waits).
        self._retries = {}

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
        for memory in (self._checks, self._seeded, self._retries):
            for key in [key for key in memory if key[0] == request_id]:
                del memory[key]

    def _in_flight(self):
        task = self._task
        return task[1] if task is not None else frozenset()

    def _current(self, key, item):
        """The check of this receipt, or None; a stale identity counts as none."""
        check = self._checks.get(key)
        if check is None or check.sha256 != item.receipt.sha256:
            return None
        if check.state != UNAVAILABLE and file_stamp(check.path) != check.stamp:
            return None
        return check

    def unchecked(self, record, *, revalidate=False):
        """Targets of a watched ready job to check now: none settled, none in flight.

        An unavailable check is due again once its delay passed. With
        ``revalidate``, a file whose identity changed since its check is due
        too; otherwise only a status read (``project``) notices that change.
        """
        request_id = record.intent.request_id
        if request_id not in self._watched or record.state not in READY_STATES:
            return ()
        in_flight, now, due = self._in_flight(), self._clock(), []
        for item in record.results:
            if item.receipt is None:
                continue
            key = (request_id, item.asset.asset_id)
            target = (*key, item.receipt.sha256)
            if target in in_flight:
                continue
            check = self._checks.get(key)
            if check is not None and check.sha256 == item.receipt.sha256:
                if check.state == UNAVAILABLE:
                    if now < self._retries.get(key, (0, 0.0))[1]:
                        continue
                elif not revalidate or self._current(key, item) is not None:
                    continue
            due.append(target)
        return tuple(due)

    def pending(self, record):
        """Whether a wait on this watched ready job waits for a check.

        That is a result still checking, including a listed file whose identity
        changed since its check. An unavailable check's retry holds no wait.
        """
        request_id = record.intent.request_id
        if request_id not in self._watched or record.state not in READY_STATES:
            return False
        return any(
            item.receipt is not None
            and self._current((request_id, item.asset.asset_id), item) is None
            for item in record.results
        )

    def seed(self, record, verified):
        """Settle results this session already verified, from (asset_id, FileCheck) pairs.

        Only a verified check of the current receipt with no settled check of
        its own is used, and each one only once, so a later change of the file
        is checked by a worker rather than covered by the same verification.
        """
        request_id = record.intent.request_id
        receipts = {
            item.asset.asset_id: item.receipt.sha256
            for item in record.results
            if item.receipt is not None
        }
        for asset_id, check in verified:
            key = (request_id, asset_id)
            existing = self._checks.get(key)
            if (
                check.state != VERIFIED
                or receipts.get(asset_id) != check.sha256
                or self._seeded.get(key) == check
                or (
                    existing is not None
                    and existing.sha256 == check.sha256
                    and existing.state != UNAVAILABLE
                )
            ):
                continue
            self._seeded[key] = check
            self._checks[key] = check
            self._retries.pop(key, None)

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
            check = self._current(key, item)
            if check is None:
                self._checks.pop(key, None)
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
            if (request_id, asset_id, sha256) not in targets or check is None:
                continue
            key = (request_id, asset_id)
            self._checks[key] = check
            if check.state == UNAVAILABLE:
                failures = min(self._retries.get(key, (0, 0.0))[0] + 1, 32)
                delay = min(RETRY_CAP, RETRY_DELAY * 2 ** (failures - 1))
                self._retries[key] = (failures, self._clock() + delay)
            else:
                self._retries.pop(key, None)
