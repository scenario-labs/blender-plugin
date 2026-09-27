# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Main-thread Image generation commands shared by UI and local MCP."""

import json
import time
import uuid
from dataclasses import dataclass, field

import bpy

from ..core.api.errors import ScenarioError
from ..core.jobs.records import JobRecord
from ..core.jobs.store import JobState


def _snapshot(body):
    return json.dumps(body, sort_keys=True, separators=(",", ":"), allow_nan=False)


@dataclass
class ModelQuote:
    identifier: str
    model_id: str
    scene: object = field(repr=False)
    inputs: str = field(repr=False)
    task: object = field(repr=False)
    quote: object = field(default=None, repr=False)
    used: bool = False


class ModelJobs:
    """Own ephemeral quotes and display projections, never another job engine."""

    def __init__(self, session, store):
        self.session = session
        self.store = store
        self.quotes = {}
        self.submissions = {}
        self.views = {}

    def quote(self, scene, model_id, body):
        snapshot = _snapshot(body)
        if scene == bpy.context.scene:
            # Operators flush pending dependency updates before execute(). Do
            # that before capturing the quote's revision, not at paid dispatch.
            bpy.context.view_layer.update()
        if len(self.quotes) >= 128:
            for key, old in tuple(self.quotes.items()):
                if old.task.done():
                    self.session.drain(task=old.task)
                    del self.quotes[key]
                    break
            else:
                raise ScenarioError(0, "Too many pending estimates; wait for one to finish")
        origin = self.session.capture(scene)
        task = self.session.quote_model(model_id, json.loads(snapshot), origin=origin)
        quote = ModelQuote(uuid.uuid4().hex, model_id, scene, snapshot, task)
        self.quotes[quote.identifier] = quote
        return quote

    def finish_quote(self, ticket):
        if self.quotes.get(ticket.identifier) is not ticket or not self.session.active:
            raise ScenarioError(0, "The estimate context changed; estimate again")
        if ticket.quote is None:
            completions = self.session.drain(task=ticket.task)
            if not completions:
                raise ScenarioError(0, "The estimate is still running")
            ticket.quote = self.session.deliver(completions[0], lambda value, *_: value)
        return ticket.quote.estimate

    def require_quote(self, quote_id):
        ticket = self.quotes.get(quote_id) if isinstance(quote_id, str) else None
        if ticket is None or ticket.used:
            raise ScenarioError(0, "Use a fresh, unsubmitted estimate; inspect existing jobs first")
        return ticket

    def submit(self, quote_id, scene, model_id, body, *, approved_cost, meta=None):
        ticket = self.require_quote(quote_id)
        estimate = self.finish_quote(ticket)
        if (
            ticket.scene != scene
            or ticket.model_id != model_id
            or ticket.inputs != _snapshot(body)
            or approved_cost != str(estimate.cost)
        ):
            raise ScenarioError(0, "The request or approved cost changed; estimate again")
        # Consumption precedes persistence: an error may occur after a committed
        # write. A second click must never prepare another intent from this quote.
        ticket.used = True
        prepared = self.session.prepare_quote(ticket.quote)
        view = JobRecord(
            local_id=prepared.intent.request_id,
            lane="image",
            kind="image",
            model_id=model_id,
            body=estimate.payload,
            status="prepared",
            cu_cost=float(estimate.cost),
            created_at=time.time(),
            meta=dict(meta or {}),
        )
        self.views[view.local_id] = view
        try:
            task = self.session.submit(
                prepared, operation="model", target_id=model_id, payload=estimate.payload
            )
        except Exception:
            view.error = "Submission could not be queued; inspect the saved job before continuing"
            raise
        self.submissions[view.local_id] = task
        return view

    def poll(self):
        """Read durable receipts on the main thread; never retry a submission."""
        for request_id, task in tuple(self.submissions.items()):
            if task.done():
                outcomes = self.session.drain(task=task)
                if outcomes and outcomes[0].error is not None:
                    self.views[
                        request_id
                    ].error = "Submission did not complete; inspect the saved job before continuing"
                del self.submissions[request_id]
        for request_id, view in self.views.items():
            record = self.store.get(request_id)
            if record is None:
                raise ScenarioError(
                    0, "The saved job is unavailable; preserve storage for recovery"
                )
            view.job_id = record.remote_job_id
            view.status = record.state.value
            if record.state in (JobState.SUBMITTING, JobState.UNCERTAIN):
                view.error = "Submission outcome is not confirmed; do not submit it again"
            elif record.state == JobState.REMOTE:
                view.error = None

    def status(self, reference):
        self.poll()
        matches = [
            record
            for record in self.store.records()
            if reference in (record.intent.request_id, record.remote_job_id)
        ]
        if len(matches) != 1:
            return None
        record = matches[0]
        return {
            "local_id": record.intent.request_id,
            "job_id": record.remote_job_id,
            "status": record.state.value,
            "revision": record.revision,
            "cu_cost": float(record.intent.quote_cost),
            "cu_cost_exact": record.intent.quote_cost,
            "kind": self.views[record.intent.request_id].kind
            if record.intent.request_id in self.views
            else "model",
            "files": [],
            "note": "Saved submission state; remote refresh and result delivery are separate actions",
        }
