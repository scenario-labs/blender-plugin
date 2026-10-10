# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Quote-time checks of LoRAs and compositions through the real SDK, without sockets.

The base and trained records are the sanitized captures under
tests/fixtures/models/trained. A synthetic service answers reads from them and
fails the test on any request a refused selection must never send.
"""

import hashlib
import json
from copy import deepcopy
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace

import httpx
import pytest

from scenario.core.api import trained_routes
from scenario.core.api.sdk_adapter import AdapterError, Credentials, SDKAdapter
from scenario.core.jobs.coordinator import JobCoordinator, QuoteError, RouteQuoteError
from scenario.core.jobs.origins import OriginRevisions
from scenario.core.jobs.store import JobScope, JobStore
from scenario.core.jobs.workers import JobWorkers

TRAINED = Path(__file__).resolve().parents[1] / "fixtures/models/trained"
FLUX1 = "model_bfl-flux-1-dev"
LORA_A = "model_YQrES2iPys22nYwh3YhVfMh8"
LORA_B = "model_2taP2G9BJL1Rw8t81NwiXGZA"
FLUX2_LORA = "model_CMUu7BjxV8TpdhG3FKoxZRxC"
COMPOSITION = "model_7oiHtKChpcLpy4jq3Jq2BG8n"
WORKFLOW = "workflow-one"
PROMPT = {"prompt": "a small wooden cabin in a snowy forest"}
QUOTE = b'{"creativeUnitsCost":10.75,"creativeUnitsDiscount":0,"costDetails":{}}'


def _load(relative):
    return json.loads((TRAINED / relative).read_text(encoding="utf-8"))["model"]


def _records():
    records = {FLUX1: _load(f"bases/{FLUX1}.json")}
    for model_id in (LORA_A, LORA_B, FLUX2_LORA, COMPOSITION):
        records[model_id] = _load(f"public/{model_id}.json")
    for concept in records[COMPOSITION]["concepts"]:
        # The capture recorded each concept's type and readability, not its status.
        records[concept["modelId"]] = {
            "id": concept["modelId"],
            "type": "flux.1-lora",
            "status": "trained",
        }
    return records


@pytest.fixture
def env(tmp_path):
    scope = JobScope("https://service.example.invalid/v1", "account", "project")
    revisions = OriginRevisions()
    state = SimpleNamespace(
        records=_records(),
        denied={},
        calls=[],
        hook=None,
        origin=revisions.capture("scene", "target"),
        revisions=revisions,
        workflow={
            "id": WORKFLOW,
            "inputs": deepcopy(_records()[FLUX1]["inputs"]),
            "uiConfig": deepcopy(_records()[FLUX1]["uiConfig"]),
        },
    )

    def handler(request):
        state.calls.append(request)
        assert request.url.params["projectId"] == "project"
        if state.hook:
            state.hook(request)
        path = request.url.path
        if request.method == "GET" and path.startswith("/v1/models/"):
            model_id = path.rsplit("/", 1)[1]
            if model_id in state.denied:
                return httpx.Response(state.denied[model_id], json={"reason": "denied"})
            if model_id not in state.records:
                return httpx.Response(404, json={"reason": f"Model {model_id} not found"})
            return httpx.Response(200, json={"model": state.records[model_id]})
        if request.method == "GET" and path == f"/v1/workflows/{WORKFLOW}":
            return httpx.Response(200, json={"workflow": state.workflow})
        if request.method in {"POST", "PUT"} and request.url.params.get("dryRun") == "true":
            return httpx.Response(269, content=QUOTE)
        raise AssertionError(f"unexpected request {request.method} {path}")

    adapter = SDKAdapter(
        Credentials("fixture", "fixture-secret"),
        online=lambda: True,
        base_url=scope.service,
        account_id=scope.account_id,
        project_id=scope.project_id,
        transport=httpx.MockTransport(handler),
    )
    store = JobStore(tmp_path / "jobs.sqlite3", scope)
    state.store = store
    state.coordinator = JobCoordinator(adapter, store, origin_guard=revisions.guard)
    yield state
    state.coordinator.close()


def requests(env):
    return [(call.method, call.url.path.removeprefix("/v1")) for call in env.calls]


def dry_runs(env):
    return [call for call in env.calls if call.url.params.get("dryRun") == "true"]


def quote(env, parameters, *, operation="model"):
    identifier = FLUX1 if operation == "model" else WORKFLOW
    return getattr(env.coordinator, f"quote_{operation}")(
        identifier, {**PROMPT, **parameters}, origin=env.origin
    )


def test_a_stack_reads_each_lora_fresh_then_quotes_the_exact_payload(env):
    selection = {"loras": [LORA_A, LORA_B], "lorasScale": [0.8, 0.5]}
    result = quote(env, selection)
    assert requests(env) == [
        ("GET", f"/models/{FLUX1}"),
        ("GET", f"/models/{LORA_A}"),
        ("GET", f"/models/{LORA_B}"),
        ("POST", f"/generate/custom/{FLUX1}"),
    ]
    assert result.estimate.target_id == FLUX1
    assert result.estimate.cost == Decimal("10.75")
    assert {key: result.estimate.payload[key] for key in selection} == selection
    assert json.loads(dry_runs(env)[0].content) == result.estimate.payload
    assert env.store.records() == ()


def test_a_composition_reads_its_concepts_fresh_before_quoting(env):
    result = quote(env, {"modelId": COMPOSITION})
    concepts = [concept["modelId"] for concept in env.records[COMPOSITION]["concepts"]]
    assert requests(env) == [
        ("GET", f"/models/{FLUX1}"),
        ("GET", f"/models/{COMPOSITION}"),
        *[("GET", f"/models/{concept}") for concept in concepts],
        ("POST", f"/generate/custom/{FLUX1}"),
    ]
    assert result.estimate.payload["modelId"] == COMPOSITION
    assert "loras" not in result.estimate.payload


def test_a_request_without_trained_models_reads_nothing_more(env):
    quote(env, {})
    assert requests(env) == [("GET", f"/models/{FLUX1}"), ("POST", f"/generate/custom/{FLUX1}")]


@pytest.mark.parametrize("status", [403, 404])
def test_a_deleted_or_inaccessible_lora_fails_before_pricing(env, status):
    env.denied[LORA_B] = status
    with pytest.raises(RouteQuoteError) as error:
        quote(env, {"loras": [LORA_A, LORA_B], "lorasScale": [0.8, 0.5]})
    assert str(error.value) == (
        f"Flux LoRA [2] is not available to the selected credentials or project (HTTP {status}). "
        "Remove it or choose another model."
    )
    assert isinstance(error.value, QuoteError)
    assert not dry_runs(env)
    assert requests(env)[-1] == ("GET", f"/models/{LORA_B}")


@pytest.mark.parametrize(
    "parameters,changes,message",
    [
        (
            {"loras": [FLUX2_LORA], "lorasScale": [1]},
            {},
            "Flux LoRA [1] is a flux.2-dev-lora model; Flux LoRA accepts flux.1-lora.",
        ),
        (
            {"loras": [COMPOSITION], "lorasScale": [1]},
            {},
            "Flux LoRA [1] is a flux.1-composition model; Flux LoRA accepts flux.1-lora.",
        ),
        (
            {"loras": [LORA_A], "lorasScale": [1]},
            {LORA_A: {"status": "training"}},
            "Flux LoRA [1] is not ready to use (status: training).",
        ),
        (
            {"modelId": LORA_A},
            {},
            "LoRA or Composition Model is a LoRA. Add it to Flux LoRA with a strength instead.",
        ),
        (
            {"modelId": COMPOSITION},
            {COMPOSITION: {"concepts": [{"modelId": FLUX2_LORA, "scale": 0.5}]}},
            "LoRA or Composition Model combines flux.2-dev-lora LoRAs; Flux LoRA accepts "
            "flux.1-lora.",
        ),
    ],
)
def test_incompatible_or_untrained_selections_fail_before_pricing(
    env, parameters, changes, message
):
    for model_id, change in changes.items():
        env.records[model_id] = {**env.records[model_id], **change}
    with pytest.raises(RouteQuoteError) as error:
        quote(env, parameters)
    assert str(error.value) == message
    assert not dry_runs(env)


@pytest.mark.parametrize(
    "parameters,message",
    [
        ({"loras": [LORA_A]}, "LoRA Scale: provide a strength for each LoRA in Flux LoRA."),
        (
            {"loras": [LORA_A, LORA_B], "lorasScale": [0.8]},
            "LoRA Scale: provide one strength for each LoRA in Flux LoRA.",
        ),
        (
            {"modelId": COMPOSITION, "loras": [LORA_A], "lorasScale": [0.5]},
            "Use LoRA or Composition Model on its own, or remove it to stack Flux LoRA with "
            "strengths.",
        ),
    ],
)
def test_strength_policy_fails_before_any_reference_read(env, parameters, message):
    with pytest.raises(RouteQuoteError) as error:
        quote(env, parameters)
    assert str(error.value) == message
    assert requests(env) == [("GET", f"/models/{FLUX1}")]


def test_out_of_bounds_strengths_stay_form_errors_without_requests(env):
    with pytest.raises(ValueError, match=r"LoRA Scale \[1\]: minimum is 0.") as error:
        quote(env, {"loras": [LORA_A], "lorasScale": [-0.5]})
    assert not isinstance(error.value, QuoteError)
    assert requests(env) == [("GET", f"/models/{FLUX1}")]


def test_a_schema_change_between_selection_and_quote_is_caught(env):
    quote(env, {"loras": [LORA_A], "lorasScale": [1]})
    env.calls.clear()
    base = env.records[FLUX1]
    base["uiConfig"]["lorasComponent"]["scaleInput"] = "strengths"
    with pytest.raises(RouteQuoteError, match="LoRA inputs changed"):
        quote(env, {"loras": [LORA_A], "lorasScale": [1]})
    assert requests(env) == [("GET", f"/models/{FLUX1}")]
    base["uiConfig"]["lorasComponent"]["scaleInput"] = "lorasScale"
    next(field for field in base["inputs"] if field["name"] == "loras")["modelTypes"] = [
        "flux.2-dev-lora"
    ]
    env.calls.clear()
    with pytest.raises(RouteQuoteError, match="Flux LoRA accepts flux.2-dev-lora"):
        quote(env, {"loras": [LORA_A], "lorasScale": [1]})
    assert not dry_runs(env)


def test_reference_reads_are_bounded(env):
    concepts = [f"model_Concept{index:015d}" for index in range(16)]
    env.records[COMPOSITION] = {
        **env.records[COMPOSITION],
        "concepts": [{"modelId": concept, "scale": 0.5} for concept in concepts],
    }
    for concept in concepts:
        env.records[concept] = {"id": concept, "type": "flux.1-lora", "status": "trained"}
    with pytest.raises(RouteQuoteError, match="Too many models to check"):
        quote(env, {"modelId": COMPOSITION})
    # The base, then the composition and 15 of its concepts: 16 reference reads.
    assert len(env.calls) == 1 + trained_routes.MAX_REFERENCE_READS
    assert not dry_runs(env)


def test_a_transport_failure_during_reference_reads_is_not_a_route_error(env):
    def fail(request):
        if request.url.path.endswith(LORA_B):
            raise httpx.ConnectError("offline")

    env.hook = fail
    with pytest.raises(AdapterError, match="Could not reach Scenario") as error:
        quote(env, {"loras": [LORA_A, LORA_B], "lorasScale": [1, 1]})
    assert not isinstance(error.value, RouteQuoteError)
    assert not dry_runs(env)


def test_a_scene_change_during_reference_reads_discards_the_quote(env):
    def edit_scene(request):
        if request.url.path.endswith(LORA_A):
            env.revisions.invalidate("scene")

    env.hook = edit_scene
    with pytest.raises(QuoteError, match="origin changed"):
        quote(env, {"loras": [LORA_A, LORA_B], "lorasScale": [1, 1]})
    assert ("GET", f"/models/{LORA_B}") not in requests(env)
    assert not dry_runs(env)


def test_workflow_lora_inputs_get_the_same_guard(env):
    with pytest.raises(RouteQuoteError, match="is not available"):
        quote(
            env,
            {"loras": ["model_Missing0000000000000000"], "lorasScale": [1]},
            operation="workflow",
        )
    assert not dry_runs(env)
    result = quote(env, {"loras": [LORA_A], "lorasScale": [1]}, operation="workflow")
    assert result.estimate.operation == "workflow"
    assert requests(env)[-2:] == [
        ("GET", f"/models/{LORA_A}"),
        ("PUT", f"/workflows/{WORKFLOW}/run"),
    ]


def test_equal_selections_quote_identical_payload_bytes_through_workers(env):
    workers = JobWorkers(env.coordinator, workers=1)
    try:
        record = env.records[FLUX1]
        selection = trained_routes.apply(
            record, [trained_routes.Pick(LORA_A, 1)], env.records, PROMPT
        )
        first = workers.quote_model(FLUX1, selection, origin=env.origin).result(5)
        again = trained_routes.apply(
            record, [trained_routes.Pick(LORA_A, 1.0)], env.records, dict(PROMPT)
        )
        second = workers.quote_model(FLUX1, again, origin=env.origin).result(5)
        assert first.estimate.payload_json == second.estimate.payload_json
        posts = [call.content for call in dry_runs(env)]
        assert len(posts) == 2 and posts[0] == posts[1]
        # The durable intent targets the base; its payload hash covers the selection.
        prepared = env.coordinator.prepare_quote(first)
        assert prepared.intent.target_id == FLUX1
        assert (
            prepared.intent.payload_sha256
            == hashlib.sha256(first.estimate.payload_json).hexdigest()
        )
    finally:
        workers.shutdown()


def test_an_echoed_schema_default_is_not_read_but_a_changed_one_is(env):
    private_default = "model_AuthorDefault000000000"
    env.workflow["inputs"].append(
        {"name": "style", "label": "Style", "type": "model", "default": private_default}
    )
    env.denied[private_default] = 403
    result = quote(env, {"style": private_default}, operation="workflow")
    assert result.estimate.payload["style"] == private_default
    assert ("GET", f"/models/{private_default}") not in requests(env)
    env.calls.clear()
    with pytest.raises(RouteQuoteError, match=r"^Style is not available .*\(HTTP 404\)"):
        quote(env, {"style": "model_Changed00000000000000000"}, operation="workflow")
    assert not dry_runs(env)
