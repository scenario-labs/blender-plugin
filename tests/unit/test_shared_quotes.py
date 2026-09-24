# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Scoped metadata and quote ownership through the real SDK and shared workers."""

import json
import threading
from dataclasses import replace
from decimal import Decimal
from types import SimpleNamespace

import httpx
import pytest

from scenario.core.api.sdk_adapter import Credentials, SDKAdapter
from scenario.core.jobs.coordinator import JobCoordinator, QuoteError
from scenario.core.jobs.origins import OriginRevisions
from scenario.core.jobs.store import JobScope, JobState, JobStore
from scenario.core.jobs.workers import JobWorkers


@pytest.fixture
def env(tmp_path):
    scope = JobScope("https://service.example.invalid/v1", "account", "project")
    revisions = OriginRevisions()
    origin = revisions.capture("scene", "target")
    model = {
        "id": "model-one",
        "type": "custom",
        "inputs": [
            {"name": "prompt", "type": "string", "required": True},
            {"name": "seed", "type": "number", "default": 0},
        ],
    }
    env = SimpleNamespace(
        scope=scope, origin=origin, revisions=revisions, model=model, calls=[], hook=None
    )

    def handler(request):
        env.calls.append(request)
        if env.hook:
            env.hook(request)
        if request.url.path.endswith("/models/model-one"):
            return httpx.Response(200, json={"model": env.model})
        if request.url.path.endswith("/workflows/workflow-one"):
            return httpx.Response(
                200, json={"workflow": {"id": "workflow-one", "inputs_definition": model["inputs"]}}
            )
        if request.url.path.endswith("/models"):
            return httpx.Response(200, json={"models": [model]})
        if request.url.path.endswith("/workflows"):
            return httpx.Response(200, json={"workflows": [{"id": "workflow-one"}]})
        if request.url.params.get("dryRun") == "true":
            return httpx.Response(200, content=b'{"creativeUnitsCost":0.10000000000000001}')
        assert request.url.params.get("dryRun") == "false"
        return httpx.Response(200, json={"job": {"jobId": "remote-one"}})

    adapter = SDKAdapter(
        Credentials("fixture", "fixture-secret"),
        online=lambda: True,
        base_url=scope.service,
        account_id=scope.account_id,
        project_id=scope.project_id,
        transport=httpx.MockTransport(handler),
    )
    store = JobStore(tmp_path / "jobs.sqlite3", scope)
    coordinator = JobCoordinator(adapter, store, origin_guard=revisions.guard)
    env.coordinator, env.store = coordinator, store
    yield env
    coordinator.close()


@pytest.mark.parametrize(
    "operation,identifier", [("model", "model-one"), ("workflow", "workflow-one")]
)
def test_exact_quote_is_bound_before_estimation_then_prepared_and_submitted_once(
    env, operation, identifier
):
    workers = JobWorkers(env.coordinator, workers=1)
    try:
        quote = getattr(workers, f"quote_{operation}")(
            identifier, {"prompt": "fixture"}, origin=env.origin
        ).result(5)
        assert quote.scope == env.scope and quote.origin == env.origin
        assert quote.estimate.cost == Decimal("0.10000000000000001")
        assert quote.estimate.payload == {"prompt": "fixture", "seed": 0}
        assert env.store.records() == ()
        prepared = env.coordinator.prepare_quote(quote)
        assert prepared.intent.origin == env.origin
        assert prepared.intent.quote_cost == "0.10000000000000001"
        with pytest.raises(QuoteError):
            env.coordinator.prepare_quote(quote)
        result = workers.submit(
            prepared,
            origin=env.origin,
            operation=operation,
            target_id=identifier,
            payload=quote.estimate.payload,
        ).result(5)
        assert result.state == JobState.REMOTE
        assert [request.url.params.get("dryRun") for request in env.calls] == [
            None,
            "true",
            "false",
        ]
        assert all(request.url.params["projectId"] == "project" for request in env.calls)
        assert json.loads(env.calls[1].content) == json.loads(env.calls[2].content)
    finally:
        workers.shutdown()


@pytest.mark.parametrize("phase", ["before", "metadata", "estimate", "prepare", "submit"])
def test_origin_changes_never_allow_rebinding_old_quote(env, phase):
    def invalidate(request):
        if (phase == "metadata" and request.method == "GET") or (
            phase == "estimate" and request.url.params.get("dryRun") == "true"
        ):
            env.revisions.invalidate("scene")

    env.hook = invalidate
    if phase == "before":
        env.revisions.invalidate("scene")
    if phase in {"before", "metadata", "estimate"}:
        with pytest.raises(QuoteError):
            env.coordinator.quote_model("model-one", {"prompt": "fixture"}, origin=env.origin)
    else:
        quote = env.coordinator.quote_model("model-one", {"prompt": "fixture"}, origin=env.origin)
        if phase == "submit":
            prepared = env.coordinator.prepare_quote(quote)
        env.revisions.invalidate("scene")
        if phase == "prepare":
            with pytest.raises(QuoteError):
                env.coordinator.prepare_quote(quote)
        else:
            with pytest.raises(QuoteError):
                env.coordinator.submit(
                    prepared,
                    origin=env.origin,
                    operation="model",
                    target_id="model-one",
                    payload=quote.estimate.payload,
                )
    assert not any(request.url.params.get("dryRun") == "false" for request in env.calls)


@pytest.mark.parametrize("change", ["copy", "origin", "scope"])
def test_copied_or_rebound_quote_is_not_an_issued_quote(env, change):
    quote = env.coordinator.quote_model("model-one", {"prompt": "fixture"}, origin=env.origin)
    kwargs = (
        {"origin": env.revisions.capture("other-scene")}
        if change == "origin"
        else {"scope": replace(env.scope, project_id="other-project")}
        if change == "scope"
        else {}
    )
    with pytest.raises(QuoteError):
        env.coordinator.prepare_quote(replace(quote, **kwargs))
    assert env.store.records() == ()
    assert env.coordinator.prepare_quote(quote).intent.origin == env.origin


def test_metadata_identity_mismatch_stops_estimation(env):
    env.model["id"] = "other-model"
    with pytest.raises(QuoteError, match="identity"):
        env.coordinator.quote_model("model-one", {"prompt": "fixture"}, origin=env.origin)
    assert len(env.calls) == 1
    assert env.calls[0].method == "GET"


def test_current_schema_is_fetched_and_validated_for_each_quote(env):
    env.coordinator.quote_model("model-one", {"prompt": "fixture"}, origin=env.origin)
    env.model["inputs"].append({"name": "reference", "type": "file", "required": True})
    with pytest.raises(ValueError):
        env.coordinator.quote_model("model-one", {"prompt": "fixture"}, origin=env.origin)
    assert [request.method for request in env.calls] == ["GET", "POST", "GET"]


def test_trained_model_route_remains_gated(env):
    env.model["type"] = "lora"
    with pytest.raises(ValueError, match="verified REST"):
        env.coordinator.quote_model("model-one", {"prompt": "fixture"}, origin=env.origin)
    assert len(env.calls) == 1


def test_worker_copies_parameters_at_admission_and_uses_same_metadata_pool(env):
    entered, release = threading.Event(), threading.Event()

    def gate(request):
        if request.url.path.endswith("/models"):
            entered.set()
            assert release.wait(5)

    env.hook = gate
    workers = JobWorkers(env.coordinator, workers=1)
    try:
        listing = workers.models(privacy="public")
        assert entered.wait(5)
        parameters = {"prompt": "original"}
        task = workers.quote_model("model-one", parameters, origin=env.origin)
        parameters["prompt"] = "changed"
        release.set()
        assert listing.result(5)[0]["id"] == "model-one"
        quote = task.result(5)
        assert quote.estimate.payload["prompt"] == "original"
        assert workers.workflows().result(5)[0]["id"] == "workflow-one"
        assert workers.model("model-one").result(5)["id"] == "model-one"
        assert workers.workflow("workflow-one").result(5)["id"] == "workflow-one"
    finally:
        release.set()
        workers.shutdown()


def test_deactivated_context_discards_late_catalog_and_quote_results(env):
    env.hook = lambda _: env.coordinator.deactivate()
    with pytest.raises(QuoteError, match="inactive"):
        env.coordinator.models()
    with pytest.raises(QuoteError, match="inactive"):
        env.coordinator.quote_model("model-one", {"prompt": "fixture"}, origin=env.origin)
    assert len(env.calls) == 1


def test_expired_bound_quote_cannot_persist_fresh_intent(env):
    quote = env.coordinator.quote_model("model-one", {"prompt": "fixture"}, origin=env.origin)
    env.coordinator._clock = lambda: quote.estimate.issued_at + 121
    with pytest.raises(QuoteError, match="expired"):
        env.coordinator.prepare_quote(quote)
    assert env.store.records() == ()


def test_legacy_prepare_cannot_remove_an_estimates_origin_binding(env):
    import gc

    quote = env.coordinator.quote_model("model-one", {"prompt": "fixture"}, origin=env.origin)
    estimate = quote.estimate
    with pytest.raises(QuoteError, match="prepare_quote"):
        env.coordinator.prepare(estimate, env.origin)
    del quote
    gc.collect()
    with pytest.raises(QuoteError, match="prepare_quote"):
        env.coordinator.prepare(estimate, env.revisions.capture("other-scene"))
    assert env.store.records() == ()


@pytest.mark.parametrize("origin", [None, "scene", {}])
def test_quote_requires_a_captured_origin_before_any_request(env, origin):
    with pytest.raises(QuoteError, match="origin"):
        env.coordinator.quote_model("model-one", {"prompt": "fixture"}, origin=origin)
    assert env.calls == []


@pytest.mark.parametrize("operation", ["model", "workflow"])
def test_deep_quote_payload_fails_before_queue_or_network(env, operation):
    payload = {}
    nested = payload
    # The C JSON encoder's nesting limit is separate from Python's frame
    # recursion limit on 3.13. Exceed both supported interpreters' limits.
    for _ in range(10_000):
        nested["nested"] = {}
        nested = nested["nested"]
    workers = JobWorkers(env.coordinator, workers=1)
    try:
        with pytest.raises(QuoteError, match="finite JSON"):
            getattr(workers, f"quote_{operation}")("identifier", payload, origin=env.origin)
        assert not env.calls
        assert env.store.records() == ()
    finally:
        workers.shutdown()


@pytest.mark.parametrize("operation", ["model", "workflow"])
def test_quote_encoder_overflow_is_sanitized_before_admission(env, monkeypatch, operation):
    def overflow(_):
        raise OverflowError("private payload")

    monkeypatch.setattr("scenario.core.jobs.workers._payload", overflow)
    workers = JobWorkers(env.coordinator, workers=1)
    try:
        with pytest.raises(QuoteError, match="finite JSON") as error:
            getattr(workers, f"quote_{operation}")("identifier", {}, origin=env.origin)
        assert "private" not in str(error.value)
        assert error.value.__suppress_context__
        assert not env.calls
    finally:
        workers.shutdown()


@pytest.mark.parametrize("bound", [False, True])
def test_preparation_overlapping_submission_does_not_invert_locks(env, monkeypatch, bound):
    from concurrent.futures import ThreadPoolExecutor

    coordinator = env.coordinator
    adapter = coordinator._adapter
    first = coordinator.quote_model("model-one", {"prompt": "first"}, origin=env.origin)
    prepared = coordinator.prepare_quote(first)
    second = (
        coordinator.quote_model("model-one", {"prompt": "second"}, origin=env.origin)
        if bound
        else adapter.estimate_model(env.model, {"prompt": "second"})
    )
    preparing, submitting = threading.Event(), threading.Event()
    original_prepare = coordinator._prepare

    class BoundedEstimateLock:
        # Fail a lock inversion instead of leaving deadlocked threads in the suite.
        def __init__(self):
            self.lock = threading.RLock()

        def __enter__(self):
            if not self.lock.acquire(timeout=2):
                raise TimeoutError("Estimate lock blocked by concurrent preparation")
            return self

        def __exit__(self, *args):
            self.lock.release()

    def prepare_inside_lock(*args):
        preparing.set()
        assert submitting.wait(5)
        return original_prepare(*args)

    def online():
        # submit_estimate calls this while holding the adapter lock, before claim.
        submitting.set()
        assert preparing.wait(5)
        return True

    monkeypatch.setattr(adapter, "_estimate_lock", BoundedEstimateLock())
    monkeypatch.setattr(adapter, "_online", online)
    monkeypatch.setattr(coordinator, "_prepare", prepare_inside_lock)

    def prepare_second():
        return (
            coordinator.prepare_quote(second) if bound else coordinator.prepare(second, env.origin)
        )

    with ThreadPoolExecutor(max_workers=2) as pool:
        pending_prepare = pool.submit(prepare_second)
        assert preparing.wait(5)
        pending_submit = pool.submit(
            coordinator.submit,
            prepared,
            origin=env.origin,
            operation="model",
            target_id="model-one",
            payload=first.estimate.payload,
        )
        next_prepared = pending_prepare.result(5)
        submitted = pending_submit.result(5)
    assert submitted.state == JobState.REMOTE
    assert env.store.get(next_prepared.intent.request_id).state == JobState.PREPARED
    assert sum(request.url.params.get("dryRun") == "false" for request in env.calls) == 1
