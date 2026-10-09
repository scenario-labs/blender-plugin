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


PRIVATE_PROJECT = "private-project-7f3a"
REJECTED = "Key or secret rejected (HTTP 401). Check the selected API key and secret."
DENIED = "Access denied (HTTP 403). Check the selected API key and secret."
DENIED_PROJECT = (
    "Access denied (HTTP 403). Check the selected API key and secret, and that the "
    "Project ID belongs to this key, or clear it to use the key's default scope."
)
LIMITED = "Too many requests (HTTP 429). Try again shortly."
SIDEBAR_CHARS = 36  # scenario.blender.panels wraps sidebar status text at this width


@pytest.mark.parametrize(
    "status,project,expected",
    [
        (401, None, REJECTED),
        (401, PRIVATE_PROJECT, REJECTED),
        (403, None, DENIED),
        (403, PRIVATE_PROJECT, DENIED_PROJECT),
        (429, None, LIMITED),
        (429, PRIVATE_PROJECT, LIMITED),
        (404, PRIVATE_PROJECT, "Scenario request failed (HTTP 404)"),
        (500, None, "Scenario request failed (HTTP 500)"),
    ],
)
def test_status_errors_are_actionable_without_private_details(adapter, status, project, expected):
    calls = []

    def handler(request):
        calls.append(request)
        return httpx.Response(
            status,
            json={"error": "selected-secret do-not-expose", "projectId": PRIVATE_PROJECT},
            headers={"Location": "https://elsewhere.example.invalid", "Retry-After": "0"},
        )

    credentials = Credentials("selected-key", "selected-secret")
    client = adapter(handler, credentials=credentials, project_id=project)
    with pytest.raises(AdapterError) as error:
        client.model_page(page_size=1)
    message = str(error.value)
    assert message == expected
    # The status sentence fits the first wrapped sidebar line; guidance never names a
    # credential source, since saved and environment keys share these messages.
    assert len(message.split(". ", 1)[0]) + 1 <= SIDEBAR_CHARS
    assert "Preferences" not in message
    assert error.value.__cause__ is None and error.value.__suppress_context__
    private = (
        "selected-key",
        "selected-secret",
        credentials.authorization().split()[1],
        PRIVATE_PROJECT,
        "do-not-expose",
        "example.invalid",
        "/v1/models",
    )
    assert not [value for value in private if value in message]
    assert dict(calls[0].url.params).get("projectId") == project
    assert len(calls) == 1


def test_unscoped_discovery_never_blames_the_project_override(adapter):
    client = adapter(lambda request: httpx.Response(403), project_id=PRIVATE_PROJECT)
    with pytest.raises(AdapterError) as error:
        client.teams()
    assert str(error.value) == DENIED


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


@pytest.mark.parametrize("project", [None, "selected-project"])
@pytest.mark.parametrize("hide_results", [None, True, False])
def test_job_discovery_keeps_filters_scope_and_extended_records(adapter, project, hide_results):
    calls = []
    first = {"jobId": "job-first", "status": "future-state", "metadata": {"future": True}}
    second = {"jobId": "job-second", "jobType": "workflow"}

    def handler(request):
        calls.append(request)
        assert len(calls) <= 2
        return httpx.Response(
            200,
            json={
                "jobs": [first] if len(calls) == 1 else [first, second],
                "nextPaginationToken": "opaque+/= cursor" if len(calls) == 1 else None,
            },
        )

    client = adapter(handler, project_id=project)
    assert client.jobs(
        author_id="author",
        workflow_id="workflow",
        job_type="workflow",
        status="success",
        page_size=2,
        max_pages=2,
        **({} if hide_results is None else {"hide_results": hide_results}),
    ) == [first, second]
    assert len(calls) == 2
    for index, request in enumerate(calls):
        assert (request.method, request.url.path) == ("GET", "/v1/jobs")
        assert request.content == b""
        query = {
            "authorId": "author",
            "workflowId": "workflow",
            "type": "workflow",
            "status": "success",
            "pageSize": "2",
            "hideResults": "false" if hide_results is False else "true",
        }
        if project:
            query["projectId"] = project
        if index:
            query["paginationToken"] = "opaque+/= cursor"
        assert dict(request.url.params) == query


@pytest.mark.parametrize(
    "page",
    [
        None,
        {},
        {"jobs": None},
        {"jobs": [None]},
        {"jobs": [{"id": "wrong-key"}]},
        {"jobs": [{"jobId": " "}]},
        {"jobs": [{"jobId": " job-1"}]},
        {"jobs": [{"jobId": "job-1 "}]},
        {"jobs": [{"jobId": "bad/id"}]},
        {"jobs": [{"jobId": "bad?id"}]},
        {"jobs": [{"jobId": 3}]},
    ],
)
def test_job_discovery_rejects_malformed_pages(adapter, page):
    with pytest.raises(AdapterError):
        adapter(lambda r: httpx.Response(200, json=page)).jobs()


@pytest.mark.parametrize("mode", ["loop", "limit", "bad-cursor", "conflict", "http-error"])
def test_job_discovery_never_returns_partial_or_conflicting_history(adapter, mode):
    calls = []

    def handler(request):
        calls.append(request)
        assert len(calls) <= 2
        if mode == "http-error" and len(calls) == 2:
            return httpx.Response(503, json={"private": "do-not-expose"})
        row = {"jobId": "job-one", "status": "pending"}
        if mode == "conflict" and len(calls) == 2:
            row["status"] = "success"
        return httpx.Response(
            200,
            json={
                "jobs": [row],
                "nextPaginationToken": 123 if mode == "bad-cursor" else "cursor",
            },
        )

    with pytest.raises(AdapterError) as error:
        adapter(handler).jobs(max_pages=1 if mode == "limit" else 4)
    assert "do-not-expose" not in str(error.value)
    assert len(calls) <= 2


def test_job_discovery_follows_empty_page_cursor_but_stops_when_exhausted(adapter):
    calls = []

    def handler(request):
        calls.append(request)
        assert len(calls) <= 2
        return httpx.Response(
            200,
            json={
                "jobs": [],
                "nextPaginationToken": "next" if len(calls) == 1 else "",
            },
        )

    assert adapter(handler).jobs() == []
    assert len(calls) == 2


def test_job_discovery_rechecks_online_permission_before_each_page(adapter):
    online = [True]
    calls = []

    def handler(request):
        calls.append(request)
        online[0] = False
        return httpx.Response(200, json={"jobs": [{"jobId": "one"}], "nextPaginationToken": "next"})

    with pytest.raises(AdapterError, match="Online access"):
        adapter(handler, online=lambda: online[0]).jobs()
    assert len(calls) == 1


@pytest.mark.parametrize(
    "options",
    [
        {"hide_results": "false"},
        {"hide_results": 0},
        {"page_size": 0},
        {"page_size": 201},
        {"page_size": True},
        {"page_size": 1.5},
        {"max_pages": 0},
        {"max_pages": False},
        {"max_pages": 1.5},
        {"status": "unknown"},
        {"status": []},
        {"author_id": "bad/id"},
        {"workflow_id": ""},
        {"job_type": "bad?type"},
    ],
)
def test_job_discovery_validates_options_before_network(adapter, options):
    def unexpected(request):
        pytest.fail("Invalid options must not send a request")

    with pytest.raises(ValueError):
        adapter(unexpected).jobs(**options)


def test_job_discovery_rejects_a_closed_client(adapter):
    client = adapter()
    client.close()
    with pytest.raises(AdapterError, match="closed"):
        client.jobs()


@pytest.mark.parametrize("privacy", ["public", "private"])
def test_model_page_preserves_wrapper_and_exact_cursor_without_auto_pagination(adapter, privacy):
    requests = []
    page = {
        "models": [{"id": "one", "unknown": True}],
        "nextPaginationToken": "next",
        "extension": [1],
    }

    def handle(request):
        requests.append(request)
        return httpx.Response(200, json=page)

    client = adapter(handle, project_id="fixture-project")
    assert (
        client.model_page(privacy=privacy, page_size=5, pagination_token="opaque+/= cursor") == page
    )
    assert len(requests) == 1
    expected = {
        "privacy": privacy,
        "pageSize": "5",
        "projectId": "fixture-project",
        "paginationToken": "opaque+/= cursor",
    }
    if privacy == "private":
        expected["status"] = "trained"
    assert dict(requests[0].url.params) == expected


@pytest.mark.parametrize(
    "options",
    [
        {"privacy": "unlisted"},
        {"page_size": 0},
        {"page_size": 501},
        {"page_size": True},
        {"page_size": 2.5},
        {"pagination_token": ""},
        {"pagination_token": 1},
    ],
)
def test_model_page_rejects_invalid_options_before_dispatch(adapter, options):
    client = adapter(lambda request: pytest.fail("invalid options must not dispatch"))
    with pytest.raises(ValueError):
        client.model_page(**options)


@pytest.mark.parametrize(
    "page",
    [
        {},
        {"models": None},
        {"models": [None]},
        {"models": [{"id": ""}]},
        {"models": [], "nextPaginationToken": 1},
    ],
)
def test_model_page_rejects_malformed_records_and_cursor(adapter, page):
    client = adapter(lambda request: httpx.Response(200, json=page))
    with pytest.raises(AdapterError):
        client.model_page()


@pytest.mark.parametrize("project", [None, "project"])
def test_prompt_quote_uses_exact_sdk_body_and_selected_scope(adapter, project):
    requests = []
    client = adapter(
        lambda request: requests.append(request) or httpx.Response(269, content=QUOTE),
        project_id=project,
    )
    parameters = {
        "mode": "contextual-v2",
        "prompt": "café",
        "modelId": "model",
        "images": ["asset-one"],
    }
    quote = client.estimate_prompt(parameters)
    parameters["images"].append("asset-two")
    assert quote.operation == quote.target_id == "prompt"
    assert quote.cost == Decimal("0.10000000000000001")
    assert quote.response_json == QUOTE
    assert quote.payload == {
        "mode": "contextual-v2",
        "prompt": "café",
        "modelId": "model",
        "images": ["asset-one"],
        "numResults": 1,
    }
    assert json.loads(requests[0].content) == quote.payload
    assert requests[0].method == "POST"
    assert requests[0].url.path == "/v1/generate/prompt"
    assert dict(requests[0].url.params) == {
        "dryRun": "true",
        **({"projectId": project} if project else {}),
    }
    assert client.owns_estimate(quote)
    assert not adapter(project_id=project).owns_estimate(quote)


@pytest.mark.parametrize(
    "change",
    [
        {"mode": []},
        {"mode": "unknown"},
        {"numResults": True},
        {"numResults": 0},
        {"numResults": 6},
        {"numResults": 1.5},
        {"prompt": None},
        {"modelId": "../bad"},
        {"images": "asset"},
        {"images": [None]},
        {"images": [" "]},
        {"images": ["asset"] * 6},
        {"dryRun": "false"},
        {"projectId": "other"},
        {"extra_body": {}},
    ],
)
def test_invalid_prompt_payload_never_reaches_transport(adapter, change):
    def deny(request):
        pytest.fail("Invalid prompt request reached transport")

    with pytest.raises(ValueError):
        adapter(deny).estimate_prompt({"mode": "contextual", **change})


def test_contextual_v2_reference_limit_is_fifteen(adapter):
    client = adapter()
    assert (
        len(
            client.estimate_prompt({"mode": "contextual-v2", "images": ["asset"] * 15}).payload[
                "images"
            ]
        )
        == 15
    )
    with pytest.raises(ValueError):
        client.estimate_prompt({"mode": "contextual-v2", "images": ["asset"] * 16})


@pytest.mark.parametrize("project", [None, "project"])
def test_translate_exact_quote_and_single_dispatch(adapter, project):
    calls = []

    def respond(request):
        calls.append(request)
        return (
            httpx.Response(269, content=QUOTE)
            if request.url.params.get("dryRun")
            else httpx.Response(200, json={"job": {"jobId": "translated"}})
        )

    client = adapter(respond, project_id=project)
    quote = client.estimate_translate({"prompt": "théière"})
    assert quote.cost == Decimal("0.10000000000000001")
    assert quote.operation == quote.target_id == "translate"
    claims = []
    client.submit_estimate(quote, before_send=lambda: claims.append(True))
    assert claims == [True]
    assert all(request.url.path == "/v1/generate/translate" for request in calls)
    assert json.loads(calls[0].content) == json.loads(calls[1].content) == {"prompt": "théière"}
    assert dict(calls[1].url.params) == ({"projectId": project} if project else {})
    with pytest.raises(ValueError):
        client.submit_estimate(quote, before_send=lambda: claims.append(True))
    assert len(calls) == 2


@pytest.mark.parametrize(
    "body", [{}, {"prompt": " "}, {"prompt": None}, {"prompt": "ok", "projectId": "other"}]
)
def test_translate_invalid_input_never_requests(adapter, body):
    with pytest.raises(ValueError):
        adapter(lambda request: pytest.fail("Unexpected service call")).estimate_translate(body)
