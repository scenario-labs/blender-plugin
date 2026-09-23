# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Synchronous shared commands; workers/UI/MCP integration is a separate layer."""

import hashlib
import json
import math
import threading
import time
import uuid
from contextlib import contextmanager, nullcontext
from dataclasses import dataclass, field
from enum import StrEnum
from weakref import WeakValueDictionary

from ..api.sdk_adapter import Estimate, SDKAdapter
from .results import ResultCommands, ResultError
from .store import (
    JobIntent,
    JobOrigin,
    JobScope,
    JobState,
    JobStore,
    StoreConflict,
    StoredJob,
    _identity,
)


class QuoteError(ValueError):
    """The current request no longer matches an active, unexpired quote."""


class SubmissionUncertain(RuntimeError):
    """Do not resend; inspect/reconcile the persisted request identity."""


@dataclass(frozen=True)
class PreparedJob:
    intent: JobIntent
    expires_at: float
    estimate: Estimate = field(repr=False)


class RecoveryError(RuntimeError):
    """Remote evidence is missing or inconsistent; preserve local state."""


class CancellationUncertain(RecoveryError):
    """Cancellation was claimed; poll the known ID instead of replaying it."""


class RecoveryAction(StrEnum):
    REVIEW_QUOTE = "review_quote"
    RECONCILE_UNKNOWN = "reconcile_unknown"
    POLL_REMOTE = "poll_remote"
    DOWNLOAD_RESULT = "download_result"
    REVIEW_DOWNLOAD = "review_download"
    REVIEW_APPLICATION = "review_application"
    FINISHED = "finished"


@dataclass(frozen=True)
class RecoveryItem:
    record: StoredJob
    action: RecoveryAction


@dataclass(frozen=True)
class RemoteSnapshot:
    record: StoredJob
    response_json: bytes = field(repr=False)

    @property
    def response(self):
        return json.loads(self.response_json)


_RECOVERY = {
    JobState.PREPARED: RecoveryAction.REVIEW_QUOTE,
    JobState.SUBMITTING: RecoveryAction.RECONCILE_UNKNOWN,
    JobState.UNCERTAIN: RecoveryAction.RECONCILE_UNKNOWN,
    JobState.REMOTE: RecoveryAction.POLL_REMOTE,
    JobState.CANCEL_REQUESTED: RecoveryAction.POLL_REMOTE,
    JobState.SUCCEEDED: RecoveryAction.DOWNLOAD_RESULT,
    JobState.DOWNLOADING: RecoveryAction.REVIEW_DOWNLOAD,
    JobState.DOWNLOAD_FAILED: RecoveryAction.REVIEW_DOWNLOAD,
    JobState.READY: RecoveryAction.REVIEW_APPLICATION,
    JobState.APPLYING: RecoveryAction.REVIEW_APPLICATION,
    JobState.APPLY_FAILED: RecoveryAction.REVIEW_APPLICATION,
    JobState.FAILED: RecoveryAction.FINISHED,
    JobState.CANCELED: RecoveryAction.FINISHED,
    JobState.APPLIED: RecoveryAction.FINISHED,
}


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
        self,
        adapter: SDKAdapter,
        store: JobStore,
        *,
        quote_ttl=120.0,
        clock=time.monotonic,
        origin_guard=None,
        result_downloader=None,
        result_root=None,
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
        if adapter.account_id is None:
            raise ValueError("JobCoordinator requires an explicit adapter account_id")
        scope = JobScope(adapter.base_url, adapter.account_id, adapter.project_id, adapter.team_id)
        if scope != store.scope:
            raise ValueError("Selected connection and job store scopes differ")
        if origin_guard is not None and not callable(origin_guard):
            raise TypeError("Origin guard must be a thread-safe context manager factory")
        self._origin_guard = origin_guard
        self._adapter = adapter
        self._store = store
        self._ttl = quote_ttl
        self._clock = clock
        self._active = True
        self._lock = threading.RLock()
        self._prepared = WeakValueDictionary()
        self._results = ResultCommands(
            adapter, store, self._result_guard, downloader=result_downloader, root=result_root
        )

    @property
    def scope(self):
        return self._store.scope

    @contextmanager
    def _result_guard(self):
        with self._lock:
            if not self._active:
                raise ResultError("This result context is inactive")
            yield

    def load_results(self, request_id, *, expected_revision):
        return self._results.load_manifest(request_id, expected_revision=expected_revision)

    def download_results(self, request_id, *, expected_revision):
        return self._results.download(request_id, expected_revision=expected_revision)

    def verify_results(self, request_id, *, expected_revision):
        return self._results.verify_ready(request_id, expected_revision=expected_revision)

    def deactivate(self):
        """Invalidate queued quotes without waiting for in-flight network calls."""
        with self._lock:
            self._active = False
            self._prepared.clear()

    def close(self):
        """Release the SDK client after the application owner has joined workers."""
        self.deactivate()
        self._adapter.close()

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
                guard = self._origin_guard(origin) if self._origin_guard else nullcontext(True)
                with guard as current_origin:
                    if not current_origin:
                        raise QuoteError("Origin changed while queued; request a fresh estimate")
                    current = self._store.get(intent.request_id)
                    if (
                        current is None
                        or current.intent != intent
                        or current.state != JobState.PREPARED
                    ):
                        raise StoreConflict("Request is no longer prepared; do not resubmit")
                    self._store.transition(
                        intent.request_id,
                        expected_revision=current.revision,
                        state=JobState.SUBMITTING,
                    )
                    claimed = True

        if not isinstance(prepared, PreparedJob):
            raise QuoteError("Use a prepared request from this coordinator")
        try:
            receipt = self._adapter.submit_estimate(prepared.estimate, before_send=claim)
            # A receipt must also satisfy the exact persisted identity contract.
            # Validate inside the uncertainty boundary before storing its ID.
            _identity(receipt["jobId"])
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

    def recovery_plan(self):
        """Inspect only this scope; never replay or guess that a worker is dead.

        In-flight records remain unchanged because another process might still
        own them. The application owner decides when explicit recovery is safe.
        """
        with self._lock:
            if not self._active:
                raise RecoveryError("This job context is inactive")
            return tuple(
                RecoveryItem(record, _RECOVERY[record.state]) for record in self._store.records()
            )

    def cancel_prepared(self, request_id, *, expected_revision):
        """Cancel queued local intent only. This sends no remote cancel request."""
        with self._lock:
            if not self._active:
                raise RecoveryError("This job context is inactive")
            current = self._store.get(request_id)
            if current is None or current.state != JobState.PREPARED:
                raise StoreConflict("Only a prepared local request can be canceled here")
            return self._store.transition(
                request_id, expected_revision=expected_revision, state=JobState.CANCELED
            )

    def refresh_remote(self, request_id, *, expected_revision):
        """Poll a known ID and persist its terminal status; never submit/rebind."""
        with self._lock:
            if not self._active:
                raise RecoveryError("This job context is inactive")
            current = self._store.get(request_id)
            if (
                current is None
                or current.revision != expected_revision
                or current.state not in {JobState.REMOTE, JobState.CANCEL_REQUESTED}
                or current.remote_job_id is None
            ):
                raise StoreConflict("Only the current known remote job can be refreshed")
        response = self._adapter.job(current.remote_job_id)
        return self._observe_remote(current, response)

    def _observe_remote(self, current, response):
        """Commit only retrieval evidence, never cancellation acknowledgements."""
        request_id = current.intent.request_id
        if response.get("jobId") != current.remote_job_id:
            raise RecoveryError("Scenario returned a different remote job identity")
        status = response.get("status")
        terminal = {
            "success": JobState.SUCCEEDED,
            "failure": JobState.FAILED,
            "canceled": JobState.CANCELED,
        }
        active = {"pending", "queued", "warming-up", "in-progress", "finalizing"}
        if not isinstance(status, str) or status not in active | terminal.keys():
            raise RecoveryError("Scenario returned an unrecognized job state")
        try:
            raw = json.dumps(response, allow_nan=False).encode()
        except (TypeError, ValueError):
            raise RecoveryError("Scenario returned invalid job result data") from None
        if status in terminal:
            try:
                updated = self._store.transition(
                    request_id, expected_revision=current.revision, state=terminal[status]
                )
            except StoreConflict:
                updated = self._store.get(request_id)
                if (
                    updated is None
                    or updated.intent != current.intent
                    or updated.remote_job_id != current.remote_job_id
                    or updated.state != terminal[status]
                ):
                    raise
        else:
            updated = self._store.get(request_id)
            if updated != current:
                raise StoreConflict("Job changed during polling; refresh the local record")
        return RemoteSnapshot(updated, raw)

    def cancel_remote(self, request_id, *, expected_revision):
        """Claim one known model-job cancellation durably, then retrieve its state.

        CANCEL_REQUESTED is never replayed or reset on restart. It remains
        pollable after a lost acknowledgement or a crash before sending.
        """
        with self._lock:
            if not self._active:
                raise RecoveryError("This job context is inactive")
            current = self._store.get(request_id)
            if current is not None and current.state == JobState.CANCEL_REQUESTED:
                raise StoreConflict("Cancellation already requested; refresh the known job")
            if (
                current is None
                or current.revision != expected_revision
                or current.state != JobState.REMOTE
                or current.remote_job_id is None
            ):
                raise StoreConflict("Only the current known remote job can be canceled")
            if current.intent.operation != "model":
                raise RecoveryError("General workflow cancellation is not supported")
        response = self._adapter.job(current.remote_job_id)
        snapshot = self._observe_remote(current, response)
        if snapshot.record.state != JobState.REMOTE:
            return snapshot
        # Captured model-generation records use custom. The pinned SDK also
        # enumerates inference; neither spelling is a general workflow cancel.
        if response.get("jobType") not in ("custom", "inference"):
            raise RecoveryError("Only a verified model-generation job can be canceled")
        # CAS persists the claim before the remote action across coordinator
        # instances/processes. No expiration can make an uncertain action replayable.
        with self._lock:
            if not self._active:
                raise RecoveryError("This job context is inactive")
            current = self._store.transition(
                request_id, expected_revision=current.revision, state=JobState.CANCEL_REQUESTED
            )
        try:
            self._adapter.cancel_inference(current.remote_job_id)
            response = self._adapter.job(current.remote_job_id)
        except Exception:
            raise CancellationUncertain(
                "Cancellation outcome is unknown; refresh the known job without repeating cancellation"
            ) from None
        return self._observe_remote(current, response)
