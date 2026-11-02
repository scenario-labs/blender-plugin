# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""The Jobs panel's session total counts each accepted job's exact quote once."""

from decimal import Decimal
from types import SimpleNamespace

import pytest

from scenario.core.jobs import session_spend
from scenario.core.jobs.session_spend import SessionSpend
from scenario.core.ui.costs import session_spend_label

COST = "0.1234567890123456789"


def record(request_id, remote_job_id):
    return SimpleNamespace(
        intent=SimpleNamespace(request_id=request_id), remote_job_id=remote_job_id
    )


def test_an_accepted_request_counts_its_exact_quote_once():
    spend = SessionSpend("scope")
    spend.sent("a", COST)
    spend.sent("b", COST)
    assert spend.snapshot() == (Decimal(0), 0)
    assert spend.accepted(record("a", "job-a")) is True
    # Later reads of the same job never count it again.
    assert spend.accepted(record("a", "job-a")) is False
    assert spend.accepted(record("b", "job-b")) is True
    assert spend.snapshot() == (Decimal(COST) * 2, 2)
    assert spend.scope == "scope"


def test_unconfirmed_requests_count_only_once_linked_to_their_job():
    spend = SessionSpend()
    spend.sent("a", "12.5")
    # A refused or uncertain submission has no job ID: nothing counts yet.
    assert spend.accepted(record("a", None)) is False
    assert spend.snapshot() == (Decimal(0), 0)
    assert spend.accepted(record("a", "linked")) is True
    assert spend.snapshot() == (Decimal("12.5"), 1)


@pytest.mark.parametrize(
    "outcome",
    [
        record("never-sent", "job"),  # an adopted cloud job or an agent's other session
        SimpleNamespace(remote_job_id="job"),  # a result without a job intent
        {"assets": []},
        None,
    ],
)
def test_outcomes_of_requests_this_session_did_not_send_never_count(outcome):
    spend = SessionSpend()
    spend.sent("a", COST)
    assert spend.accepted(outcome) is False
    assert spend.snapshot() == (Decimal(0), 0)


def test_a_request_sent_twice_is_remembered_once():
    spend = SessionSpend()
    spend.sent("a", "1")
    spend.sent("a", "1")
    assert spend.accepted(record("a", "job")) is True
    assert spend.snapshot() == (Decimal(1), 1)


def test_waiting_requests_are_bounded_oldest_first(monkeypatch):
    monkeypatch.setattr(session_spend, "WAITING_LIMIT", 2)
    spend = SessionSpend()
    for name in ("a", "b", "c"):
        spend.sent(name, "1")
    assert spend.accepted(record("a", "job")) is False
    assert spend.accepted(record("c", "job")) is True
    assert spend.snapshot() == (Decimal(1), 1)


@pytest.mark.parametrize(
    ("total", "count", "expected"),
    [
        (Decimal(0), 0, ""),
        (Decimal(COST), 1, "This session: 0.123 CU across 1 job"),
        (Decimal(412), 6, "This session: 412 CU across 6 jobs"),
        (Decimal("12345.6"), 1234, "This session: 12.3K CU across 1,234 jobs"),
    ],
)
def test_session_spend_label(total, count, expected):
    assert session_spend_label(total, count) == expected
