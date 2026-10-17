# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""When a failed status refresh of a known remote job is retried later. No bpy.

A refresh only reads the job with SDK `jobs.retrieve`, which the adapter
already retries a few times within one request. When those retries are also
exhausted by a timeout, a dropped connection, HTTP 408, 429 or a 5xx, the job
is still running on Scenario as far as anyone knows, so its owner polls again
later instead of stopping delivery. The wait doubles from the poll interval up
to BACKOFF_MAX, or follows a longer Retry-After up to RETRY_AFTER_MAX. After
FAILURE_CEILING consecutive transient failures, or on any other error, the
owner pauses delivery for review. Nothing here sends, submits or cancels.
"""

import math

from ..api.sdk_adapter import AdapterStatusError, AdapterUnreachable

# Consecutive transient refresh failures; the one that reaches this pauses.
# With the backoff below that is about four minutes without a status reply.
FAILURE_CEILING = 8
BACKOFF_MAX = 60.0
# A server may ask for a longer wait than the backoff, but never this much more.
RETRY_AFTER_MAX = 300.0
_TRANSIENT_STATUSES = frozenset({408, 429})


def transient(error):
    """Whether a refresh failed for a reason that a later read may not repeat."""
    if isinstance(error, AdapterUnreachable):
        return True
    if isinstance(error, AdapterStatusError):
        return error.status_code in _TRANSIENT_STATUSES or error.status_code >= 500
    return False


def delay(failures, error, *, interval):
    """Seconds before the next refresh after `failures` consecutive transient failures."""
    wait = min(BACKOFF_MAX, interval * 2.0 ** min(failures, 32))
    retry_after = getattr(error, "retry_after", None)
    if (
        isinstance(retry_after, (int, float))
        and not isinstance(retry_after, bool)
        and math.isfinite(retry_after)
        and retry_after > 0
    ):
        wait = max(wait, min(float(retry_after), RETRY_AFTER_MAX))
    return wait


def exhausted(failures):
    """Whether this many consecutive transient failures pause delivery."""
    return failures >= FAILURE_CEILING
