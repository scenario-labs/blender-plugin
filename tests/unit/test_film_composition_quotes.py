# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Verified Film drafts retain source identity through shared SDK spending claims."""

import json
from dataclasses import replace
from decimal import Decimal

import httpx
import pytest
from test_film_media import env as env
from test_film_media import prepare

from scenario.core.jobs.coordinator import QuoteError, SubmissionUncertain
from scenario.core.jobs.store import JobState, JobStore, StoreConflict, StoreError

MODEL = "model_scenario-compose-video"
FIELDS = {
    "layers": "array",
    "canvasMode": "string",
    "canvasWidth": "integer",
    "canvasHeight": "integer",
    "durationMode": "string",
    "duration": "number",
    "fps": "number",
    "videoOutputFormat": "string",
    "compressionLevel": "integer",
}


@pytest.fixture
def ready(env):
    e = env
    e.verified = prepare(e).result(3)
    e.calls, e.hook, e.online = [], None, True

    def respond(request):
        e.calls.append(request)
        assert "projectId" not in request.url.params
        if e.hook:
            e.hook(request)
        if request.method == "GET":
            assert request.url.path == "/v1/models/" + MODEL
            return httpx.Response(
                200,
                json={
                    "model": {
                        "id": MODEL,
                        "type": "custom",
                        "inputs": [
                            {"name": name, "type": kind, "required": True}
                            for name, kind in FIELDS.items()
                        ],
                    }
                },
            )
        assert request.url.path == "/v1/generate/custom/" + MODEL
        body = json.loads(request.content)
        assert "dryRun" not in body and "projectId" not in body
        assert [item["source"] for item in body["layers"]] == [
            "asset-video",
            "asset-score",
            "asset-score",
        ]
        if request.url.params.get("dryRun") == "true":
            return httpx.Response(269, content=b'{"creativeUnitsCost":0.10000000000000001}')
        # A separate SQLite reader must observe the master claim before dispatch.
        saved = JobStore(e.root / "jobs.sqlite3", e.scope).film_job("production", "final-master")
        assert saved is not None and saved.state == JobState.SUBMITTING
        assert saved.intent.quote_cost == "0.10000000000000001"
        return httpx.Response(200, json={"job": {"jobId": "composition"}})

    e.handler = respond
    return e


def quote(e):
    return e.workers.quote_film_composition(e.verified, origin=e.origin).result(3)


def submit(e, prepared):
    return e.workers.submit(
        prepared,
        origin=e.origin,
        operation="model",
        target_id=MODEL,
        payload=prepared.estimate.payload,
    ).result(3)


def change_source(e):
    row = e.store.get("video")
    e.store.transition("video", expected_revision=row.revision, state=JobState.APPLYING)


def test_measured_draft_has_separate_exact_quote_and_single_durable_submission(ready):
    e = ready
    result = quote(e)
    assert result.estimate.cost == Decimal("0.10000000000000001")
    assert result.composition is e.verified.draft
    assert result.film_task.task_id == "final-master"
    assert e.store.film_job("production", "final-master") is None
    prepared = e.owner.prepare_quote(result)
    assert prepared.composition is result.composition
    assert e.store.get(prepared.intent.request_id).state == JobState.PREPARED
    assert len(e.calls) == 2
    assert submit(e, prepared).state == JobState.REMOTE
    with pytest.raises(ValueError):
        submit(e, prepared)
    assert len(e.calls) == 3
    with pytest.raises(StoreConflict, match="saved work"):
        quote(e)
    assert len(e.calls) == 3


@pytest.mark.parametrize(
    "stage", ["before_quote", "schema", "estimate", "before_prepare", "before_submit"]
)
def test_changed_source_blocks_each_boundary_without_spending(ready, stage):
    e = ready
    if stage == "before_quote":
        change_source(e)
    if stage in {"schema", "estimate"}:
        e.hook = lambda request: (
            change_source(e) if ((request.method == "GET") == (stage == "schema")) else None
        )
    prepared = None
    with pytest.raises(ValueError, match="sources changed"):
        q = quote(e)
        if stage == "before_prepare":
            change_source(e)
        prepared = e.owner.prepare_quote(q)
        if stage == "before_submit":
            change_source(e)
        submit(e, prepared)
    assert len(e.calls) == {"before_quote": 0, "schema": 1}.get(stage, 2)
    row = e.store.film_job("production", "final-master")
    assert row is None if prepared is None else row.state == JobState.PREPARED


@pytest.mark.parametrize("mutation", ["copy", "scope", "origin", "draft"])
def test_fabricated_or_modified_measurement_ticket_is_not_authority(ready, mutation):
    e = ready
    ticket = e.verified
    if mutation == "scope":
        ticket = replace(ticket, scope=replace(ticket.scope, project_id="other"))
    elif mutation == "origin":
        ticket = replace(ticket, origin=e.revisions.capture("another-scene"))
    elif mutation == "draft":
        recipe = ticket.draft.recipe
        recipe["tasks"][-1]["parameters"]["duration"] = 1
        ticket = replace(ticket, draft=replace(ticket.draft, recipe_json=json.dumps(recipe)))
    else:
        ticket = replace(ticket)
    with pytest.raises(QuoteError, match="Inspect composition media"):
        e.workers.quote_film_composition(ticket, origin=e.origin).result(3)
    assert not e.calls


def test_measurement_cannot_move_to_another_current_scene_or_owner(ready):
    e = ready
    with pytest.raises(QuoteError):
        e.workers.quote_film_composition(e.verified, origin=e.revisions.capture("other")).result(3)
    e.owner.deactivate()
    with pytest.raises(QuoteError):
        quote(e)
    assert not e.calls


def test_timeout_remains_uncertain_and_never_replays_or_accepts_a_second_master(ready):
    e = ready
    q = quote(e)
    prepared = e.owner.prepare_quote(q)

    def timeout(request):
        if request.method == "POST" and "dryRun" not in request.url.params:
            raise httpx.ReadTimeout("synthetic timeout", request=request)

    e.hook = timeout
    with pytest.raises(SubmissionUncertain):
        submit(e, prepared)
    row = e.store.get(prepared.intent.request_id)
    assert row.state == JobState.UNCERTAIN
    with pytest.raises(ValueError):
        submit(e, prepared)
    with pytest.raises(StoreConflict):
        quote(e)
    assert len(e.calls) == 3


def test_recipe_copy_edits_cannot_change_the_owned_draft_payload(ready):
    e = ready
    recipe = e.verified.draft.recipe
    recipe["tasks"][-1]["parameters"]["duration"] = 1
    q = quote(e)
    assert q.estimate.payload["duration"] == 4
    altered = q.estimate.payload
    altered["duration"] = 1
    prepared = e.owner.prepare_quote(q)
    with pytest.raises(QuoteError):
        e.workers.submit(
            prepared, origin=e.origin, operation="model", target_id=MODEL, payload=altered
        ).result(3)
    assert len(e.calls) == 2


def test_competing_composition_prices_cannot_reserve_two_masters(ready):
    e = ready
    first, second = quote(e), quote(e)
    e.owner.prepare_quote(first)
    with pytest.raises(StoreConflict):
        e.owner.prepare_quote(second)
    assert (
        len([row for row in e.store.records() if row.intent.film_task.task_id == "final-master"])
        == 1
    )
    assert len(e.calls) == 4


def test_lost_prepare_acknowledgement_does_not_authorize_another_master(ready, monkeypatch):
    e = ready
    q = quote(e)
    create = e.store.create

    def uncertain(intent):
        create(intent)
        raise StoreError("Synthetic lost acknowledgement")

    monkeypatch.setattr(e.store, "create", uncertain)
    with pytest.raises(StoreError):
        e.owner.prepare_quote(q)
    with pytest.raises(StoreConflict):
        e.owner.prepare_quote(q)
    assert e.store.film_job("production", "final-master").state == JobState.PREPARED
    assert len(e.calls) == 2
