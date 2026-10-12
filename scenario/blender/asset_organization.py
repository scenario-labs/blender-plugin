# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Session-owned asset organization reviews shared by the native Library and MCP.

One entry point for both surfaces: prepare a fresh read, show it, apply it once
on the session's workers and report what the read-back verified. Reviews live
only as long as their JobSession; nothing is persisted and no scene is changed.
"""

import logging
import time

from ..core.api.sdk_adapter import AdapterError
from ..core.jobs.coordinator import QuoteError
from ..core.jobs.organization import (
    REVIEW_TTL,
    DuplicateCollection,
    OrganizationError,
    OrganizationNotSent,
    OrganizationReviews,
    build_request,
    collection_summary,
    review_payload,
)
from ..core.jobs.workers import WorkerError
from .job_session import OriginUnavailable, SessionBusy, _main_thread

_log = logging.getLogger("scenario.organization")
_SAFE = (OrganizationError, AdapterError, QuoteError, WorkerError, OriginUnavailable, SessionBusy)
_COLLECTIONS_FAILED = "Collections could not load; check the connection and try again"
_COLLECTIONS_EXPIRED = "This collection page expired unread; load collections again"


def safe_message(error, fallback="Scenario organization failed; refresh the Library to inspect"):
    """Use only messages written for UI boundaries; never echo unknown exception text."""
    return str(error) if isinstance(error, _SAFE) and str(error) else fallback


class AssetOrganization:
    """Prepare, apply and inspect organization reviews for one JobSession.

    Main thread only. Worker tasks run on the session's existing pool; the
    runtime pump and local MCP call ``poll`` to move finished work into the
    reviews. Retiring the session (credential, project or file change) closes
    this owner, so a late outcome is never delivered to another connection.
    """

    def __init__(self, session, *, reviews=None, clock=time.monotonic):
        self.session = session
        self.reviews = reviews or OrganizationReviews()
        self._clock = clock
        self._tasks = {}
        # Collection page task -> when poll first saw it finished, until taken.
        self._collection_reads = {}

    def _check(self):
        _main_thread()
        if not self.session.active:
            raise OriginUnavailable("The Scenario connection changed; prepare the change again")

    def prepare(self, operation, **arguments):
        """Validate a request now and queue its fresh read; returns the review ID."""
        self._check()
        self.poll()
        request = build_request(self.session.scope, operation, **arguments)
        review_id = self.reviews.open(request)
        try:
            task = self.session.organization_snapshot(request)
        except BaseException:
            self.reviews.remove(review_id)
            raise
        self._tasks[task] = (review_id, "snapshot")
        return review_id

    def apply(self, review_id):
        """Queue a READY review's writes once; returns its APPLYING status."""
        self._check()
        self.poll()
        snapshot = self.reviews.begin_apply(review_id)
        try:
            task = self.session.organize(snapshot)
        except BaseException:
            # Nothing was queued, so nothing can have been sent.
            self.reviews.abort_apply(review_id)
            raise
        self._tasks[task] = (review_id, "apply")
        return self.status(review_id)

    def task(self, review_id):
        """Return the pending worker handle so MCP can wait off the main thread."""
        for task, (identifier, _) in self._tasks.items():
            if identifier == review_id:
                return task
        return None

    def status(self, review_id):
        _main_thread()
        return review_payload(self.reviews.status(review_id))

    def discard(self, review_id):
        _main_thread()
        return review_payload(self.reviews.discard(review_id))

    def collections(self, *, page_size=50, pagination_token=None):
        """Queue one collection page read; take it with ``take_collections``."""
        self._check()
        task = self.session.collection_page(page_size=page_size, pagination_token=pagination_token)
        self._collection_reads[task] = None
        return task

    def take_collections(self, task):
        """Consume a finished collection page without thumbnails or owner IDs."""
        self._check()
        if task not in self._collection_reads:
            raise OrganizationError(_COLLECTIONS_EXPIRED)
        completions = self.session.drain(task=task)
        if not completions:
            raise OrganizationError("Collections are still loading")
        del self._collection_reads[task]
        try:
            page = self.session.deliver_asset_organization(completions[0])
        except _SAFE:
            raise
        except Exception as error:
            # As in poll(): unknown worker text never reaches the Library or MCP.
            raise OrganizationError(_COLLECTIONS_FAILED) from error
        return {
            "collections": [collection_summary(record) for record in page["collections"]],
            "next_pagination_token": page["next_pagination_token"],
        }

    def poll(self):
        """Move finished worker outcomes into their reviews; never sends a request."""
        _main_thread()
        if not self.session.active:
            self.close()
            return
        now = self._clock()
        for task, finished_at in tuple(self._collection_reads.items()):
            if not task.done():
                continue
            if finished_at is None:
                self._collection_reads[task] = now
            elif now - finished_at >= REVIEW_TTL:
                # Its caller stopped waiting (a local MCP request that timed
                # out or a closed view). Discard the page unread so it cannot
                # hold one of the session's admission slots forever.
                del self._collection_reads[task]
                self.session.drain(task=task)
        for task, (review_id, kind) in tuple(self._tasks.items()):
            if not task.done():
                continue
            del self._tasks[task]
            completions = self.session.drain(task=task)
            try:
                if not completions:
                    raise OrganizationError("The organization outcome was not delivered")
                result = self.session.deliver_asset_organization(completions[0])
            except DuplicateCollection as error:
                self.reviews.not_sent(review_id, str(error), error.collection_ids)
            except OrganizationNotSent as error:
                self.reviews.not_sent(review_id, str(error))
            except Exception as error:
                message = safe_message(error)
                if kind == "apply":
                    # A write may have been sent: report unknown, never unsent.
                    self.reviews.unknown(review_id, message)
                else:
                    self.reviews.failed(review_id, message)
            else:
                if kind == "apply":
                    self.reviews.finished(review_id, result)
                else:
                    self.reviews.prepared(review_id, result)

    def close(self):
        """Discard session-local reviews; queued work was already cancelled unsent."""
        if self.reviews.applying:
            # No IDs or names: the user inspects the Library of that connection.
            _log.info("A Scenario organization change ended with its connection; inspect assets")
        self._tasks.clear()
        self._collection_reads.clear()
        self.reviews.clear()
