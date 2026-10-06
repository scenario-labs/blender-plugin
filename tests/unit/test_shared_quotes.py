# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Scoped metadata and quote ownership through the real SDK and shared workers."""

import hashlib
import json
import sqlite3
import threading
from dataclasses import replace
from decimal import Decimal
from types import SimpleNamespace

import httpx
import pytest

from scenario.core.api.sdk_adapter import Credentials, SDKAdapter
from scenario.core.jobs.coordinator import JobCoordinator, QuoteError
from scenario.core.jobs.mesh_source import MeshSource, MeshSourceObject
from scenario.core.jobs.origins import OriginRevisions
from scenario.core.jobs.store import JobScope, JobState, JobStore
from scenario.core.jobs.upload_sources import UploadSources
from scenario.core.jobs.upload_store import UploadIntent, UploadState, UploadStore
from scenario.core.jobs.upload_transfers import PartUploader, S3UploadPolicy, UploadedPart
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
        scope=scope,
        origin=origin,
        revisions=revisions,
        model=model,
        workflow=None,
        calls=[],
        hook=None,
    )

    def handler(request):
        env.calls.append(request)
        if env.hook:
            env.hook(request)
        if request.url.path.endswith("/models/model-one"):
            return httpx.Response(200, json={"model": env.model})
        if request.url.path.endswith("/workflows/workflow-one"):
            return httpx.Response(
                200,
                json={
                    "workflow": env.workflow
                    or {"id": "workflow-one", "inputs_definition": model["inputs"]}
                },
            )
        if request.url.path.endswith("/models"):
            return httpx.Response(200, json={"models": [model]})
        if request.url.path.endswith("/workflows"):
            return httpx.Response(200, json={"workflows": [{"id": "workflow-one"}]})
        if request.url.params.get("dryRun") == "true":
            return httpx.Response(200, content=b'{"creativeUnitsCost":0.10000000000000001}')
        assert request.method in {"POST", "PUT"} and "dryRun" not in request.url.params
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
    uploads = UploadStore(tmp_path / "uploads.sqlite3", scope)
    (tmp_path / "upload-sources").mkdir(mode=0o700)
    coordinator = JobCoordinator(
        adapter,
        store,
        origin_guard=revisions.guard,
        upload_store=uploads,
        upload_sources=UploadSources(tmp_path / "upload-sources"),
        part_uploader=PartUploader(S3UploadPolicy(), online_access=lambda: True),
    )
    env.upload_store = uploads
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
            None,
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
    assert not any(
        request.method in {"POST", "PUT"} and "dryRun" not in request.url.params
        for request in env.calls
    )


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

    def prepare_inside_lock(*args, **kwargs):
        preparing.set()
        assert submitting.wait(5)
        return original_prepare(*args, **kwargs)

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
    assert (
        sum(
            request.method in {"POST", "PUT"} and "dryRun" not in request.url.params
            for request in env.calls
        )
        == 1
    )


def captured_upload(env, *, request_id="capture", asset_id="mesh-asset", scope=None):
    scope = scope or env.scope
    store = UploadStore(env.upload_store._path, scope)
    digest = hashlib.sha256(b"fixture GLB").hexdigest()
    source = MeshSource(
        digest,
        (
            MeshSourceObject(
                env.origin.target_id,
                hashlib.sha256(b"geometry").hexdigest(),
                ((1, 0, 0, 3), (0, 1, 0, 4), (0, 0, 1, 5), (0, 0, 0, 1)),
            ),
        ),
    )
    intent = UploadIntent(
        request_id,
        scope,
        env.origin,
        "3d",
        "source.glb",
        "model/gltf-binary",
        11,
        digest,
        11,
        (digest,),
        source,
    )
    record = store.create(intent)

    def advance(state, **kwargs):
        nonlocal record
        record = store.transition(
            request_id, expected_revision=record.revision, state=state, **kwargs
        )

    advance(UploadState.INITIALIZING)
    advance(UploadState.UPLOADING, upload_id="remote-upload-" + request_id)
    record = store.claim_part(request_id, expected_revision=record.revision)
    record = store.record_part(
        request_id, UploadedPart(1, 11, digest), expected_revision=record.revision
    )
    advance(UploadState.FINALIZING)
    advance(UploadState.PROCESSING)
    advance(UploadState.IMPORTED, asset_id=asset_id)
    return record


def mesh_quote(env, *, operation="model", value="mesh-asset", array=False):
    env.model["inputs"].append(
        {"name": "mesh", "type": "file_array" if array else "file", "kind": "3d", "required": True}
    )
    return getattr(env.coordinator, "quote_" + operation)(
        operation + "-one",
        {"prompt": "fixture", "mesh": value},
        origin=env.origin,
    )


@pytest.mark.parametrize("operation", ["model", "workflow"])
def test_captured_mesh_is_bound_to_exact_quote_and_persisted_before_spending(env, operation):
    upload = captured_upload(env)
    quote = mesh_quote(env, operation=operation)
    assert len(quote.mesh_sources) == 1
    source = quote.mesh_sources[0]
    assert (source.parameter, source.index, source.asset_id) == ("mesh", None, upload.asset_id)
    assert source.mesh_source == upload.intent.mesh_source
    assert source.origin == upload.intent.origin
    prepared = env.coordinator.prepare_quote(quote)
    assert (
        JobStore(env.store._path, env.scope).get(prepared.intent.request_id).intent.mesh_sources
        == quote.mesh_sources
    )

    def before_send(request):
        if request.method in {"POST", "PUT"} and "dryRun" not in request.url.params:
            saved = env.store.get(prepared.intent.request_id)
            assert saved.state == JobState.SUBMITTING
            assert saved.intent.mesh_sources == quote.mesh_sources
            assert json.loads(request.content) == quote.estimate.payload
            assert "mesh_sources" not in json.loads(request.content)

    env.hook = before_send
    result = env.coordinator.submit(
        prepared,
        origin=env.origin,
        operation=operation,
        target_id=operation + "-one",
        payload=quote.estimate.payload,
    )
    assert result.intent.mesh_sources == quote.mesh_sources
    assert len(env.calls) == 3


def test_array_positions_preserve_each_occurrence_without_binding_external_assets(env):
    captured_upload(env)
    quote = mesh_quote(env, value=["mesh-asset", "external-asset", "mesh-asset"], array=True)
    assert [source.index for source in quote.mesh_sources] == [0, 2]
    assert all(source.parameter == "mesh" for source in quote.mesh_sources)
    assert env.coordinator.prepare_quote(quote).intent.mesh_sources == quote.mesh_sources


def test_prompt_text_and_different_scope_cannot_claim_mesh_provenance(env):
    captured_upload(env, scope=replace(env.scope, account_id="other"))
    quote = mesh_quote(env)
    assert quote.mesh_sources == ()
    captured_upload(env)
    env.model["inputs"] = [{"name": "prompt", "type": "string", "required": True}]
    quote = env.coordinator.quote_model("model-one", {"prompt": "mesh-asset"}, origin=env.origin)
    assert quote.mesh_sources == ()


def test_ambiguous_export_asset_never_selects_the_first_origin(env):
    captured_upload(env)
    captured_upload(env, request_id="second-source")
    with pytest.raises(QuoteError, match="Several captured"):
        mesh_quote(env)
    assert env.store.records() == ()
    assert all("dryRun" in request.url.params for request in env.calls if request.method == "POST")


@pytest.mark.parametrize("phase", ["prepare", "submit"])
def test_missing_mesh_upload_blocks_before_persistence_or_paid_claim(env, phase):
    upload = captured_upload(env)
    quote = mesh_quote(env)
    prepared = env.coordinator.prepare_quote(quote) if phase == "submit" else None
    with sqlite3.connect(env.upload_store._path) as connection:
        connection.execute("DELETE FROM uploads WHERE request_id=?", (upload.intent.request_id,))
    with pytest.raises(QuoteError, match="captured input changed"):
        if phase == "prepare":
            env.coordinator.prepare_quote(quote)
        else:
            env.coordinator.submit(
                prepared,
                origin=env.origin,
                operation="model",
                target_id="model-one",
                payload=quote.estimate.payload,
            )
    assert len(env.calls) == 2
    assert (
        env.store.records() == ()
        if phase == "prepare"
        else env.store.get(prepared.intent.request_id).state == JobState.PREPARED
    )


def test_dictionary_input_schema_and_sdk_parameters_fallback_bind_same_source(env):
    upload = captured_upload(env)
    env.model["inputs"] = None
    env.model["parameters"] = {"mesh": {"type": "file", "kind": "3d", "required": True}}
    quote = env.coordinator.quote_model("model-one", {"mesh": upload.asset_id}, origin=env.origin)
    assert quote.mesh_sources[0].upload_id == upload.intent.request_id


@pytest.mark.parametrize(
    "operation,primary,fallback",
    [("model", "inputs", "parameters"), ("workflow", "inputs_definition", "inputs")],
)
@pytest.mark.parametrize("typed_primary", [True, False])
def test_mesh_binding_uses_the_same_schema_as_sdk_payload_preparation(
    env, operation, primary, fallback, typed_primary
):
    upload = captured_upload(env)
    mesh = {"name": "mesh", "type": "file", "kind": "3d", "required": True}
    text = {"name": "mesh", "type": "string", "required": True}
    metadata = {
        "id": operation + "-one",
        "type": "custom",
        primary: [mesh if typed_primary else text],
        fallback: [text if typed_primary else mesh],
    }
    setattr(env, operation, metadata)
    quote = getattr(env.coordinator, "quote_" + operation)(
        metadata["id"], {"mesh": upload.asset_id}, origin=env.origin
    )
    assert quote.estimate.payload == {"mesh": upload.asset_id}
    assert len(quote.mesh_sources) == int(typed_primary)
    if typed_primary:
        assert quote.mesh_sources[0].upload_id == upload.intent.request_id
    prepared = env.coordinator.prepare_quote(quote)
    result = env.coordinator.submit(
        prepared,
        origin=env.origin,
        operation=operation,
        target_id=metadata["id"],
        payload=quote.estimate.payload,
    )
    assert result.intent.mesh_sources == quote.mesh_sources
    assert json.loads(env.calls[-1].content) == quote.estimate.payload


@pytest.mark.parametrize(
    "operation,primary,fallback",
    [("model", "inputs", "parameters"), ("workflow", "inputs_definition", "inputs")],
)
@pytest.mark.parametrize("primary_present", [True, False])
def test_missing_or_null_primary_schema_uses_sdk_fallback_for_mesh_binding(
    env, operation, primary, fallback, primary_present
):
    upload = captured_upload(env)
    metadata = {
        "id": operation + "-one",
        "type": "custom",
        fallback: {"mesh": {"type": "file", "kind": "3d", "required": True}},
    }
    if primary_present:
        metadata[primary] = None
    setattr(env, operation, metadata)
    quote = getattr(env.coordinator, "quote_" + operation)(
        metadata["id"], {"mesh": upload.asset_id}, origin=env.origin
    )
    assert quote.mesh_sources[0].upload_id == upload.intent.request_id
    assert env.coordinator.prepare_quote(quote).intent.mesh_sources == quote.mesh_sources


@pytest.mark.parametrize(
    "operation,primary,fallback",
    [("model", "inputs", "parameters"), ("workflow", "inputs_definition", "inputs")],
)
@pytest.mark.parametrize("schemas_present", [True, False])
def test_absent_or_null_schemas_stop_before_estimation_or_mesh_binding(
    env, operation, primary, fallback, schemas_present
):
    captured_upload(env)
    metadata = {"id": operation + "-one", "type": "custom"}
    if schemas_present:
        metadata.update({primary: None, fallback: None})
    setattr(env, operation, metadata)
    with pytest.raises(ValueError, match="current input schema"):
        getattr(env.coordinator, "quote_" + operation)(metadata["id"], {}, origin=env.origin)
    assert len(env.calls) == 1 and env.calls[0].method == "GET"
    assert env.store.records() == ()
    assert env.coordinator._quotes == {}
