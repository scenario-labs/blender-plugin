# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Validated, in-memory progress readings for shared remote jobs. No bpy.

Polling already retrieves each known job with SDK `jobs.retrieve` through
`SDKAdapter.job` (`jobs.with_raw_response.retrieve`). The SDK documents
`Job.progress` as a fraction between 0 and 1 and `Job.status` as one of eight
literals. The coordinator validates the job ID and commits terminal states;
this module only interprets an active `RemoteSnapshot` for display.

A reading is advisory. It is bound to the saved record revision and remote job
ID that produced it, kept in memory by its owner and never persisted. Providers
may report 0 until completion, so a missing or invalid value is unknown (None),
never coerced to 0.
"""

import math
import time
from dataclasses import dataclass
from datetime import UTC, datetime

from .store import JobState

# Active SDK job statuses and their display words; terminal statuses are
# committed by the coordinator and never produce a reading.
LABELS = {
    "pending": "waiting",
    "queued": "queued",
    "warming-up": "starting",
    "in-progress": "generating",
    "finalizing": "finishing",
}
ACTIVE = tuple(LABELS)
# Only these statuses measure generation, so only they show a percentage.
_MEASURED = frozenset({"in-progress", "finalizing"})
_POLLED = frozenset({JobState.REMOTE, JobState.CANCEL_REQUESTED})


def fraction(value):
    """Return a finite fraction in [0, 1], or None for anything else."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    # Comparison rejects NaN, infinities and out-of-range numbers, including
    # integers too large to convert to float.
    if not 0 <= value <= 1:
        return None
    return 0.0 if value == 0 else float(value)


@dataclass(frozen=True)
class RemoteProgress:
    """One reading of an active known job, bound to the record that produced it.

    `stale` is set by the owner when automatic polling is not keeping the
    reading current. Wall time is for reports only; ages use monotonic time.
    """

    remote_job_id: str
    revision: int
    status: str
    fraction: float | None
    observed_at: float
    observed_monotonic: float
    stale: bool = False

    @property
    def label(self):
        return LABELS[self.status]

    @property
    def percent(self):
        """Whole percent to display, only while measured and above zero."""
        if self.status not in _MEASURED or not self.fraction:
            return None
        # Binary floats put 0.29 * 100 just below 29; snap to the reported
        # decimal before flooring so the bar never shows one percent too low.
        return math.floor(round(self.fraction * 100, 6))

    @property
    def observed_utc(self):
        return (
            datetime.fromtimestamp(self.observed_at, UTC)
            .isoformat(timespec="seconds")
            .replace("+00:00", "Z")
        )


def observe(snapshot, *, monotonic=time.monotonic, wall=time.time):
    """Interpret one coordinator RemoteSnapshot, or return None when it is not active.

    A terminal or mismatched snapshot yields None, which clears any earlier
    reading. The coordinator has already rejected unknown statuses and IDs.
    """
    record = snapshot.record
    if record.state not in _POLLED or record.remote_job_id is None:
        return None
    response = snapshot.response
    status = response.get("status")
    if (
        response.get("jobId") != record.remote_job_id
        or not isinstance(status, str)
        or status not in LABELS
    ):
        return None
    return RemoteProgress(
        record.remote_job_id,
        record.revision,
        status,
        fraction(response.get("progress")),
        wall(),
        monotonic(),
    )
