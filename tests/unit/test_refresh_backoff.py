# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Classify a failed status refresh and schedule the next one, without Blender."""

import math
import pickle

import pytest

from scenario.core.api.sdk_adapter import (
    AdapterError,
    AdapterStatusError,
    AdapterUnavailable,
    AdapterUnreachable,
)
from scenario.core.jobs import refresh_backoff
from scenario.core.jobs.coordinator import (
    CancellationUncertain,
    CancellationUnsupported,
    RecoveryError,
)
from scenario.core.jobs.store import StoreConflict


@pytest.mark.parametrize(
    "error",
    [
        AdapterUnreachable(),
        AdapterStatusError(408, "timeout"),
        AdapterStatusError(429, "limited", 3.0),
        AdapterStatusError(500, "failed"),
        AdapterStatusError(502, "failed"),
        AdapterStatusError(503, "failed"),
        AdapterStatusError(504, "failed"),
    ],
)
def test_lost_replies_timeouts_rate_limits_and_server_errors_are_transient(error):
    assert refresh_backoff.transient(error)


@pytest.mark.parametrize(
    "error",
    [
        AdapterStatusError(400, "bad"),
        AdapterStatusError(401, "rejected"),
        AdapterStatusError(403, "denied"),
        AdapterStatusError(404, "missing"),
        AdapterStatusError(409, "conflict"),
        AdapterUnavailable(404),
        AdapterError("Online access is disabled"),
        AdapterError("Scenario returned no job record"),
        RecoveryError("Scenario returned an unrecognized job state"),
        StoreConflict("Job changed during polling"),
        CancellationUncertain("unknown"),
        CancellationUnsupported("nothing was sent"),
        ValueError("local"),
        RuntimeError("Could not reach Scenario"),
    ],
)
def test_refusals_malformed_replies_and_local_errors_are_not_transient(error):
    assert not refresh_backoff.transient(error)


def test_backoff_doubles_from_the_poll_interval_up_to_its_cap():
    delays = [
        refresh_backoff.delay(failures, AdapterUnreachable(), interval=2.0)
        for failures in range(1, refresh_backoff.FAILURE_CEILING)
    ]
    assert delays == [4.0, 8.0, 16.0, 32.0, 60.0, 60.0, 60.0]
    assert refresh_backoff.delay(1000, AdapterUnreachable(), interval=2.0) == 60.0
    assert refresh_backoff.BACKOFF_MAX == 60.0


@pytest.mark.parametrize(
    "retry_after,expected",
    [(None, 4.0), (0.0, 4.0), (1.5, 4.0), (45.0, 45.0), (299.0, 299.0), (3600.0, 300.0)],
)
def test_a_longer_retry_after_is_honoured_up_to_five_minutes(retry_after, expected):
    error = AdapterStatusError(429, "limited", retry_after)
    assert refresh_backoff.delay(1, error, interval=2.0) == expected
    assert refresh_backoff.RETRY_AFTER_MAX == 300.0


@pytest.mark.parametrize("value", [math.nan, math.inf, -1.0, "60", True])
def test_an_invalid_retry_after_is_ignored(value):
    error = AdapterStatusError(503, "failed")
    error.retry_after = value
    assert refresh_backoff.delay(2, error, interval=2.0) == 8.0


def test_the_ceiling_pauses_on_the_eighth_consecutive_failure():
    assert refresh_backoff.FAILURE_CEILING == 8
    assert not refresh_backoff.exhausted(refresh_backoff.FAILURE_CEILING - 1)
    assert refresh_backoff.exhausted(refresh_backoff.FAILURE_CEILING)


def test_retry_after_survives_copy_and_pickle():
    error = pickle.loads(pickle.dumps(AdapterStatusError(429, "Too many requests", 7.0)))
    assert (error.status_code, str(error), error.retry_after) == (429, "Too many requests", 7.0)
    unreachable = pickle.loads(pickle.dumps(AdapterUnreachable()))
    assert isinstance(unreachable, AdapterUnreachable)
    assert str(unreachable) == "Could not reach Scenario"
