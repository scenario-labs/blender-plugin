# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Validate advisory remote progress readings without Blender or network access."""

import math
import typing
from types import SimpleNamespace

import pytest
from scenario_sdk.types.job_retrieve_response import Job

from scenario.core.jobs import progress
from scenario.core.jobs.store import JobState


def snapshot(response, *, state=JobState.REMOTE, remote_job_id="job-1", revision=3):
    record = SimpleNamespace(state=state, remote_job_id=remote_job_id, revision=revision)
    return SimpleNamespace(record=record, response=response)


def read(response, **record):
    return progress.observe(snapshot(response, **record), monotonic=lambda: 7.5, wall=lambda: 0.0)


@pytest.mark.parametrize(
    ("value", "expected"),
    [(0, 0.0), (0.0, 0.0), (-0.0, 0.0), (0.42, 0.42), (1, 1.0), (1.0, 1.0)],
)
def test_fraction_accepts_finite_values_from_zero_to_one(value, expected):
    result = progress.fraction(value)
    assert result == expected and type(result) is float
    assert math.copysign(1.0, result) == 1.0


@pytest.mark.parametrize(
    "value",
    [
        True,
        False,
        math.nan,
        math.inf,
        -math.inf,
        -0.01,
        1.01,
        2,
        10**400,
        -(10**400),
        "0.5",
        None,
        [0.5],
        {"value": 0.5},
    ],
)
def test_fraction_treats_invalid_values_as_unknown_never_zero(value):
    assert progress.fraction(value) is None


def test_every_sdk_status_is_either_an_active_reading_or_a_committed_terminal_state():
    statuses = set(typing.get_args(Job.model_fields["status"].annotation))
    assert statuses == set(progress.ACTIVE) | {"success", "failure", "canceled"}
    assert set(progress.LABELS) == set(progress.ACTIVE)


@pytest.mark.parametrize("state", [JobState.REMOTE, JobState.CANCEL_REQUESTED])
def test_active_snapshot_yields_a_reading_bound_to_its_record(state):
    reading = read(
        {"jobId": "job-1", "status": "in-progress", "progress": 0.429, "secret": "kept out"},
        state=state,
    )
    assert reading == progress.RemoteProgress("job-1", 3, "in-progress", 0.429, 0.0, 7.5)
    assert (reading.label, reading.percent, reading.stale) == ("generating", 42, False)
    assert reading.observed_utc == "1970-01-01T00:00:00Z"
    assert not hasattr(reading, "response")


@pytest.mark.parametrize(
    ("status", "label"),
    [
        ("pending", "waiting"),
        ("queued", "queued"),
        ("warming-up", "starting"),
        ("in-progress", "generating"),
        ("finalizing", "finishing"),
    ],
)
def test_every_active_status_has_a_display_word(status, label):
    reading = read({"jobId": "job-1", "status": status})
    assert (reading.status, reading.label, reading.fraction) == (status, label, None)


@pytest.mark.parametrize(
    ("status", "value", "percent"),
    [
        ("in-progress", 0.999, 99),
        ("in-progress", 0.005, 0),
        # Reported decimals whose binary product falls just below the whole value.
        ("in-progress", 0.29, 29),
        ("in-progress", 0.57, 57),
        ("in-progress", 0.58, 58),
        ("in-progress", 0.28, 28),
        ("in-progress", 0.9999999, 99),
        ("in-progress", 1, 100),
        ("finalizing", 0.5, 50),
        # Providers may keep 0 until completion; zero and unknown show no bar.
        ("in-progress", 0, None),
        ("in-progress", None, None),
        ("in-progress", math.nan, None),
        # A fraction outside measured statuses is not a generation percentage.
        ("queued", 0.5, None),
        ("pending", 1, None),
        ("warming-up", 0.2, None),
    ],
)
def test_percent_is_floor_of_a_measured_nonzero_fraction(status, value, percent):
    response = {"jobId": "job-1", "status": status}
    if value is not None:
        response["progress"] = value
    assert read(response).percent == percent


@pytest.mark.parametrize(
    ("response", "record"),
    [
        ({"jobId": "job-1", "status": "success", "progress": 1}, {"state": JobState.SUCCEEDED}),
        ({"jobId": "job-1", "status": "failure"}, {"state": JobState.FAILED}),
        ({"jobId": "job-1", "status": "canceled"}, {"state": JobState.CANCELED}),
        # The saved record, not the response, decides whether polling is active.
        ({"jobId": "job-1", "status": "in-progress"}, {"state": JobState.READY}),
        ({"jobId": "job-2", "status": "in-progress"}, {}),
        ({"jobId": "job-1", "status": "in-progress"}, {"remote_job_id": None}),
        ({"jobId": "job-1", "status": "success"}, {}),
        ({"jobId": "job-1", "status": "processing"}, {}),
        ({"jobId": "job-1", "status": ["in-progress"]}, {}),
        ({"jobId": "job-1"}, {}),
    ],
)
def test_terminal_mismatched_or_unknown_snapshots_yield_no_reading(response, record):
    assert read(response, **record) is None
