# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""This session's spend: the exact quoted price of each job Scenario accepted, counted once."""

from decimal import Decimal

# Sent requests remembered until Scenario confirms them; past this, the oldest stops counting.
WAITING_LIMIT = 256


class SessionSpend:
    """Totals the exact quote of each sent request once its saved record carries a job ID.

    Main thread only, for one connection (`scope`). A request canceled before sending,
    refused, or whose outcome stays unconfirmed is not counted; one later linked to its
    cloud job counts then. Quotes are what was approved, not Scenario's billing record.
    """

    def __init__(self, scope=None):
        self.scope = scope
        self._waiting = {}  # request_id -> exact quoted cost
        self.total = Decimal(0)
        self.count = 0

    def sent(self, request_id, cost):
        """Remember a request handed to the workers with its exact quoted cost."""
        if request_id in self._waiting:
            return
        if len(self._waiting) >= WAITING_LIMIT:
            self._waiting.pop(next(iter(self._waiting)))
        self._waiting[request_id] = Decimal(str(cost))

    def accepted(self, record):
        """Count a sent request once its record has Scenario's job ID; True when it counted."""
        intent = getattr(record, "intent", None)
        if intent is None or getattr(record, "remote_job_id", None) is None:
            return False
        cost = self._waiting.pop(getattr(intent, "request_id", None), None)
        if cost is None:
            return False
        self.total += cost
        self.count += 1
        return True

    def snapshot(self):
        """(total, count) for redraw checks and drawing; reads memory only."""
        return self.total, self.count
