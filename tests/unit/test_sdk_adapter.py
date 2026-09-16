# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Exercise the real SDK and adopted form rules without network or spending."""

import copy
import json
import os
import socket
from decimal import Decimal

import httpx
import pytest

from scenario import __version__
from scenario.core.api.sdk_adapter import AdapterError, Credentials, SDKAdapter

URL = "https://service.example.invalid/v1"
MODEL = {
    "id": "fixture-model",
    "type": "custom",
    "inputs": [
        {"name": "prompt", "type": "string", "required": True},
        {"name": "strength", "type": "number", "min": 0.1, "max": 1.0, "default": 0.5},
        {"name": "enabled", "type": "boolean", "default": False},
        {"name": "references", "type": "file_array"},
    ],
}
QUOTE = b'{"creativeUnitsCost":0.10000000000000001,"costDetails":{"model":0.10000000000000001}}'


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    def deny(*args, **kwargs):
        pytest.fail("Adapter contracts must not access the network")

    monkeypatch.setattr(socket.socket, "connect", deny)
    monkeypatch.setattr(socket.socket, "connect_ex", deny)
    monkeypatch.setattr(socket, "create_connection", deny)


@pytest.fixture
def adapter():
    clients = []

    def create(handler=None, **options):
        settings = {
            "credentials": Credentials("selected-key", "selected-secret"),
            "base_url": URL,
            "online": lambda: True,
            "transport": httpx.MockTransport(
                handler or (lambda r: httpx.Response(200, content=QUOTE))
            ),
        }
        settings.update(options)
        client = SDKAdapter(**settings)
        clients.append(client)
        return client

    yield create
    for client in clients:
        client.close()


@pytest.mark.parametrize("bearer", [False, True])
def test_account_and_headers_are_isolated_without_changing_environment(
    adapter, monkeypatch, bearer
):
    ambient = {
        "SCENARIO_SDK_API_KEY": "ambient-key",
        "SCENARIO_SDK_API_SECRET": "ambient-secret",
        "SCENARIO_SDK_JWT": "ambient-jwt",
        "SCENARIO_BASE_URL": "https://wrong.example.invalid",
        "SCENARIO_CUSTOM_HEADERS": "Authorization: Bearer wrong\nauthorization: Bearer wrong-case\nHost: wrong.example.invalid\nX-Project-Id: wrong\nX-Private: ambient",
        "HTTP_PROXY": "http://wrong.example.invalid",
        "HTTPS_PROXY": "http://wrong.example.invalid",
    }
    for name, value in ambient.items():
        monkeypatch.setenv(name, value)
    requests = []

    def handler(request):
        requests.append(request)
        return httpx.Response(200, json={"job": {"id": "fixture-job"}})

    credentials = (
        Credentials(bearer_token="selected-token")
        if bearer
        else Credentials("selected-key", "selected-secret")
    )
    client = adapter(handler, credentials=credentials, project_id="selected-project")
    client.job("fixture-job")
    request = requests[0]
    assert request.url.host == "service.example.invalid"
    assert request.headers["Host"] == "service.example.invalid"
    assert request.headers["Authorization"] == credentials.authorization()
    assert request.headers["User-Agent"] == f"ScenarioBlender/{__version__}"
    assert len(request.headers.get_list("Authorization")) == 1
    assert "X-Private" not in request.headers and "X-Project-Id" not in request.headers
    assert dict(request.url.params) == {"projectId": "selected-project"}
    assert {name: os.environ[name] for name in ambient} == ambient
    assert "selected" not in repr(credentials)


@pytest.mark.parametrize("project", [None, "fixture-project"])
@pytest.mark.parametrize("operation", ["model", "workflow"])
def test_estimate_preserves_scope_values_exact_quote_and_input(adapter, project, operation):
    requests = []

    def handler(request):
        requests.append(request)
        return httpx.Response(200, content=QUOTE)

    client = adapter(handler, project_id=project)
    model = copy.deepcopy(MODEL)
    parameters = {"prompt": "café", "references": []}
    if operation == "model":
        estimate = client.estimate_model(model, parameters)
        method, path = "POST", "/v1/generate/custom/fixture-model"
    else:
        estimate = client.estimate_workflow(
            {"id": "fixture-workflow", "inputs": model["inputs"]}, parameters
        )
        method, path = "PUT", "/v1/workflows/fixture-workflow/run"
    request = requests[0]
    assert len(requests) == 1
    assert (request.method, request.url.path) == (method, path)
    assert dict(request.url.params) == {
        "dryRun": "true",
        **({"projectId": project} if project else {}),
    }
    assert json.loads(request.content) == {"prompt": "café", "strength": 0.5, "enabled": False}
    assert "dryRun" not in json.loads(request.content)
    assert estimate.cost == Decimal("0.10000000000000001")
    assert estimate.details["costDetails"]["model"] == estimate.cost
    assert estimate.response_json == QUOTE
    assert client.owns_estimate(estimate)
    assert not adapter(project_id=project).owns_estimate(estimate)
    estimate.payload["prompt"] = "changed"
    assert estimate.payload["prompt"] == "café"
    assert model == MODEL and parameters == {"prompt": "café", "references": []}


@pytest.mark.parametrize(
    "method,wrapper",
    [("model", "model"), ("workflow", "workflow"), ("asset", "asset"), ("job", "job")],
)
def test_reads_preserve_extended_records(adapter, method, wrapper):
    seen = []
    record = {"id": "fixture-record", "futureField": {"keep": True}, "scale": 0.5}

    def handler(request):
        seen.append(request)
        return httpx.Response(200, json={wrapper: record})

    client = adapter(handler)
    assert getattr(client, method)("fixture-record") == record
    assert seen[0].url.path == f"/v1/{wrapper}s/fixture-record"
    assert "projectId" not in seen[0].url.params


def test_retrieved_numeric_schema_can_be_used_for_an_estimate(adapter):
    def handler(request):
        return (
            httpx.Response(200, json={"model": MODEL})
            if request.method == "GET"
            else httpx.Response(200, content=QUOTE)
        )

    client = adapter(handler)
    assert (
        client.estimate_model(client.model("fixture-model"), {"prompt": "test"}).payload["strength"]
        == 0.5
    )


@pytest.mark.parametrize("resource", ["models", "workflows"])
def test_catalog_exhausts_pages_and_deduplicates_without_losing_fields(adapter, resource):
    requests = []

    def handler(request):
        requests.append(request)
        first = {"id": "first", "unknown": True}
        page = (
            {resource: [first, {"id": "second"}]}
            if len(requests) == 2
            else {resource: [first], "nextPaginationToken": "cursor+one"}
        )
        return httpx.Response(200, json=page)

    client = adapter(handler, project_id="fixture-project")
    assert getattr(client, resource)(privacy="public") == [
        {"id": "first", "unknown": True},
        {"id": "second"},
    ]
    assert len(requests) == 2
    assert all(r.url.params["projectId"] == "fixture-project" for r in requests)
    assert requests[1].url.params["paginationToken"] == "cursor+one"
    assert requests[0].url.params["privacy"] == "public"


@pytest.mark.parametrize("mode", ["loop", "limit", "bad-list", "bad-id"])
def test_catalog_never_returns_a_silent_partial_result(adapter, mode):
    calls = []

    def handler(request):
        calls.append(request)
        rows = (
            "bad" if mode == "bad-list" else [{"id": None}] if mode == "bad-id" else [{"id": "one"}]
        )
        return httpx.Response(200, json={"models": rows, "nextPaginationToken": "loop"})

    with pytest.raises(AdapterError):
        adapter(handler).models(max_pages=1 if mode == "limit" else 5)
    assert len(calls) <= 2


def test_online_permission_is_rechecked_between_pages_and_for_estimates(adapter):
    permission = [True]
    calls = []

    def handler(request):
        calls.append(request)
        permission[0] = False
        return httpx.Response(200, json={"models": [], "nextPaginationToken": "next"})

    client = adapter(handler, online=lambda: permission[0])
    with pytest.raises(AdapterError, match="Online access"):
        client.models()
    with pytest.raises(AdapterError, match="Online access"):
        client.estimate_model(MODEL, {"prompt": "test"})
    assert len(calls) == 1


@pytest.mark.parametrize("failure", [307, 429, 500, "timeout"])
def test_errors_are_sanitized_redirects_blocked_and_no_retries(adapter, failure):
    calls = []

    def handler(request):
        calls.append(request)
        if failure == "timeout":
            raise httpx.ReadTimeout("selected-secret signed-url", request=request)
        return httpx.Response(
            failure,
            json={"error": "selected-secret signed-url"},
            headers={"Location": "https://elsewhere.example.invalid", "Retry-After": "0"},
        )

    with pytest.raises(AdapterError) as error:
        adapter(handler).estimate_model(MODEL, {"prompt": "test"})
    assert "selected-secret" not in str(error.value)
    assert "signed-url" not in str(error.value)
    assert len(calls) == 1


@pytest.mark.parametrize("cost", [None, True, -1, "1.23", float("nan"), float("inf")])
def test_estimate_requires_a_valid_server_cost(adapter, cost):
    with pytest.raises(AdapterError):
        adapter(
            lambda r: httpx.Response(200, content=json.dumps({"creativeUnitsCost": cost}).encode())
        ).estimate_model(MODEL, {"prompt": "test"})


def test_zero_cost_is_valid(adapter):
    result = adapter(lambda r: httpx.Response(200, json={"creativeUnitsCost": 0})).estimate_model(
        MODEL, {"prompt": "test"}
    )
    assert result.cost == Decimal(0)


def test_canonical_conditional_rules_survive_adopted_form_validation(adapter):
    client = adapter()
    model = {
        "id": "conditional",
        "type": "custom",
        "inputs": [
            {"name": "prompt", "type": "string", "prompt": True},
            {
                "name": "image",
                "type": "file",
                "required": True,
                "description": "Required if no prompt is provided",
            },
            {"name": "mask", "type": "file", "required": {"ifDefined": {"image": {}}}},
        ],
    }
    assert client.estimate_model(model, {"prompt": "test"}).payload == {"prompt": "test"}
    with pytest.raises(ValueError, match="Provide one"):
        client.estimate_model(model, {})
    with pytest.raises(ValueError, match="mask.*required"):
        client.estimate_model(model, {"image": "fixture-image"})
    assert client.estimate_model(model, {"image": "image", "mask": "mask"}).payload == {
        "image": "image",
        "mask": "mask",
    }


def test_explicit_either_or_rules_are_retained(adapter):
    model = {
        "id": "either-or",
        "type": "custom",
        "inputs": [
            {"name": "image", "type": "file", "required": {"ifNotDefined": {"mesh": {}}}},
            {"name": "mesh", "type": "file"},
        ],
    }
    with pytest.raises(ValueError, match="Provide one"):
        adapter().estimate_model(model, {})
    assert adapter().estimate_model(model, {"mesh": "fixture-mesh"}).payload == {
        "mesh": "fixture-mesh"
    }


@pytest.mark.parametrize(
    "changes",
    [
        {"type": "flux.1-lora"},
        {"parentModelId": "base"},
        {"runs_as": "composition"},
        {"id": "../other"},
        {"inputs": None, "parameters": None},
    ],
)
def test_unverified_routing_and_invalid_records_never_reach_transport(adapter, changes):
    def unexpected(request):
        pytest.fail("Invalid input reached the service")

    with pytest.raises(ValueError):
        adapter(unexpected).estimate_model({**MODEL, **changes}, {"prompt": "test"})


@pytest.mark.parametrize(
    "credentials",
    [
        Credentials(),
        Credentials("key"),
        Credentials("key", "secret", "token"),
        Credentials(bearer_token="bad\ntoken"),
    ],
)
def test_invalid_credentials_fail_before_client_creation(adapter, credentials):
    with pytest.raises(ValueError):
        adapter(credentials=credentials)


def test_closed_clients_and_blank_projects_are_rejected(adapter):
    with pytest.raises(ValueError):
        adapter(project_id="")
    client = adapter()
    client.close()
    with pytest.raises(AdapterError, match="closed"):
        client.job("fixture-job")
