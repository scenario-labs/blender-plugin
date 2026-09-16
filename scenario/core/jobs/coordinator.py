# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Synchronous shared commands; workers/UI/MCP integration is a separate layer."""

import hashlib
import json
import math
import threading
import time
import uuid
from dataclasses import dataclass, field
from weakref import WeakValueDictionary

from ..api.sdk_adapter import Estimate, SDKAdapter
from .store import JobIntent, JobOrigin, JobScope, JobState, JobStore, StoreConflict


class QuoteError(ValueError):
    """The current request no longer matches an active, unexpired quote."""


class SubmissionUncertain(RuntimeError):
    """Do not resend; inspect/reconcile the persisted request identity."""


@dataclass(frozen=True)
class PreparedJob:
    intent: JobIntent
    expires_at: float
    estimate: Estimate = field(repr=False)


def _payload(value):
    if not isinstance(value, dict):
        raise QuoteError("The current payload must be a JSON object")
    try:
        return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)
    except (TypeError, ValueError):
        raise QuoteError("The current payload must contain finite JSON values") from None


class JobCoordinator:
    """One immutable selected connection/store; no automatic submission retry.

    Context switches deactivate the old coordinator. Already claimed work stays
    bound to its original scope/origin and may finish, without applying to Blender.
    Caller-supplied account/team IDs must come from the selected auth context.
    """

    def __init__(
        self, adapter: SDKAdapter, store: JobStore, *, quote_ttl=120.0, clock=time.monotonic
    ):
        if not isinstance(adapter, SDKAdapter) or not isinstance(store, JobStore):
            raise TypeError("Use the shared SDK adapter and job store")
        if (
            isinstance(quote_ttl, bool)
            or not isinstance(quote_ttl, (int, float))
            or not math.isfinite(quote_ttl)
            or quote_ttl <= 0
            or not callable(clock)
        ):
            raise ValueError("Use a positive finite quote lifetime and monotonic clock")
        scope = JobScope(adapter.base_url, adapter.account_id, adapter.project_id, adapter.team_id)
        if scope != store.scope:
            raise ValueError("Selected connection and job store scopes differ")
        self._adapter = adapter
        self._store = store
        self._ttl = quote_ttl
        self._clock = clock
        self._active = True
        self._lock = threading.RLock()
        self._prepared = WeakValueDictionary()

    @property
    def scope(self):
        return self._store.scope

    def deactivate(self):
        """Invalidate queued quotes without waiting for in-flight network calls."""
        with self._lock:
            self._active = False
            self._prepared.clear()

    def prepare(self, estimate: Estimate, origin: JobOrigin):
        """Persist an intent after the caller has chosen this quote; do not spend."""
        if not self._adapter.owns_estimate(estimate):
            raise QuoteError("Use a quote issued by the current active connection")
        with self._lock:
            if not self._active:
                raise QuoteError("Use a quote issued by the current active connection")
            intent = JobIntent(
                request_id=uuid.uuid4().hex,
                scope=self.scope,
                origin=origin,
                operation=estimate.operation,
                target_id=estimate.target_id,
                payload_sha256=hashlib.sha256(estimate.payload_json).hexdigest(),
                quote_sha256=hashlib.sha256(estimate.response_json).hexdigest(),
                quote_cost=str(estimate.cost),
            )
            expires_at = estimate.issued_at + self._ttl
            now = self._clock()
            if not math.isfinite(now) or now < estimate.issued_at or now >= expires_at:
                raise QuoteError("Quote expired; request a fresh estimate")
            prepared = PreparedJob(intent, expires_at, estimate)
            self._store.create(intent)
            self._prepared[id(prepared)] = prepared
            return prepared

    def submit(self, prepared, *, origin, operation, target_id, payload):
        """Explicit spending command; caller passes the current normalized request.

        Persistence errors propagate and stop dispatch. Once claimed, every lost
        or malformed response is uncertain, never an invitation to submit again.
        """
        current_payload = _payload(payload)
        claimed = False

        def claim():
            nonlocal claimed
            with self._lock:
                if not self._active or self._prepared.get(id(prepared)) is not prepared:
                    raise QuoteError("Prepared request is not owned by this active coordinator")
                now = self._clock()
                if (
                    not math.isfinite(now)
                    or now < prepared.estimate.issued_at
                    or now >= prepared.expires_at
                ):
                    raise QuoteError("Quote expired; request a fresh estimate")
                intent = prepared.intent
                if (
                    origin != intent.origin
                    or operation != intent.operation
                    or target_id != intent.target_id
                    or current_payload != _payload(prepared.estimate.payload)
                ):
                    raise QuoteError("Request or origin changed; request a fresh estimate")
                current = self._store.get(intent.request_id)
                if (
                    current is None
                    or current.intent != intent
                    or current.state != JobState.PREPARED
                ):
                    raise StoreConflict("Request is no longer prepared; do not resubmit")
                self._store.transition(
                    intent.request_id, expected_revision=current.revision, state=JobState.SUBMITTING
                )
                claimed = True

        if not isinstance(prepared, PreparedJob):
            raise QuoteError("Use a prepared request from this coordinator")
        try:
            receipt = self._adapter.submit_estimate(prepared.estimate, before_send=claim)
        except Exception:
            if not claimed:
                raise
            current = self._store.get(prepared.intent.request_id)
            if current is not None and current.state == JobState.SUBMITTING:
                self._store.transition(
                    current.intent.request_id,
                    expected_revision=current.revision,
                    state=JobState.UNCERTAIN,
                )
            raise SubmissionUncertain(
                "Submission outcome is unknown; do not submit it again"
            ) from None
        # Network work is outside the lock: a context switch can deactivate this
        # coordinator, while the receipt still goes only to its original store.
        current = self._store.get(prepared.intent.request_id)
        if current is None or current.intent != prepared.intent:
            raise StoreConflict("Cannot attach receipt to a changed request")
        return self._store.transition(
            current.intent.request_id,
            expected_revision=current.revision,
            state=JobState.REMOTE,
            remote_job_id=receipt["jobId"],
        )
