# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Offline contracts for the published SDK selected for Studio adoption.

These exercise SDK public operations, not either prototype's client. Every
request uses MockTransport; socket connections are additionally forbidden.
"""

import base64
import copy
import json
import socket
from decimal import Decimal

import httpx
import pytest
from scenario_sdk import APIConnectionError, APIStatusError, APITimeoutError, Scenario

BASE_URL = "https://api.example.invalid/v1"
PROJECT = "fixture-project"
SDK_ENV = (
    "SCENARIO_SDK_API_KEY",
    "SCENARIO_SDK_API_SECRET",
    "SCENARIO_SDK_JWT",
    "SCENARIO_BASE_URL",
    "SCENARIO_CUSTOM_HEADERS",
)


@pytest.fixture(autouse=True)
def offline_environment(monkeypatch):
    # Test isolation only. Production must not mutate process-wide credentials.
    for name in SDK_ENV:
        monkeypatch.delenv(name, raising=False)

    def deny_network(*args, **kwargs):
        pytest.fail("SDK contract tests must not open network connections")

    monkeypatch.setattr(socket.socket, "connect", deny_network)
    monkeypatch.setattr(socket.socket, "connect_ex", deny_network)
    monkeypatch.setattr(socket, "create_connection", deny_network)


@pytest.fixture
def client_factory():
    clients = []

    def create(handler, **options):
        settings = {
            "base_url": BASE_URL,
            "api_key": "fixture-key",
            "api_secret": "fixture-secret",
            "max_retries": 0,
            "timeout": 5.0,
            "http_client": httpx.Client(
                transport=httpx.MockTransport(handler),
                follow_redirects=False,
                trust_env=False,
            ),
        }
        settings.update(options)
        sdk = Scenario(**settings)
        clients.append(sdk)
        return sdk

    yield create
    for sdk in clients:
        sdk.close()


@pytest.mark.parametrize("operation", ["model", "workflow"])
@pytest.mark.parametrize("dry_run", [True, False])
def test_generation_keeps_scope_and_dry_run_out_of_payload(client_factory, operation, dry_run):
    requests = []
    payload = {
        "prompt": "fixture prompt",
        "numImages": 2,
        "references": [{"assetId": "fixture-asset", "strength": 0.5}],
        "model_specific": {"preserveThisKey": True},
    }
    original = copy.deepcopy(payload)

    def respond(request):
        requests.append(request)
        return httpx.Response(200, json={"job": {"jobId": "fixture-job"}})

    sdk = client_factory(respond)
    if operation == "model":
        result = sdk.generate.run_model(
            "fixture-model", body=payload, dry_run=dry_run, project_id=PROJECT
        )
        method, path = "POST", "/v1/generate/custom/fixture-model"
    else:
        result = sdk.workflows.run(
            "fixture-workflow", body=payload, dry_run=dry_run, project_id=PROJECT
        )
        method, path = "PUT", "/v1/workflows/fixture-workflow/run"
    assert len(requests) == 1
    request = requests[0]
    assert (request.method, request.url.path) == (method, path)
    assert dict(request.url.params) == {"dryRun": str(dry_run).lower(), "projectId": PROJECT}
    assert json.loads(request.content) == original
    assert payload == original
    assert result.job.job_id == "fixture-job"
    assert result.to_dict()["job"]["jobId"] == "fixture-job"


def test_estimate_wrapper_preserves_exact_decimal_quote(client_factory):
    # Use the SDK's public response wrapper, not a low-level HTTP method.
    # JSON bytes retain precision that the generated float model cannot retain.
    quote = b'{"creativeUnitsCost":0.10000000000000001,"costDetails":{"generation":0.10000000000000001}}'
    sdk = client_factory(lambda request: httpx.Response(200, content=quote))
    response = sdk.generate.with_raw_response.run_model(
        "fixture-model", body={"prompt": "fixture"}, dry_run=True, project_id=PROJECT
    )
    estimate = json.loads(response.read(), parse_float=Decimal)
    assert estimate["creativeUnitsCost"] == Decimal("0.10000000000000001")
    assert estimate["costDetails"]["generation"] == estimate["creativeUnitsCost"]


@pytest.mark.parametrize(
    "resource,identifier,wrapper",
    [
        ("models", "fixture-model", "model"),
        ("assets", "fixture-asset", "asset"),
        ("jobs", "fixture-job", "job"),
    ],
)
def test_retrieve_keeps_scope_and_response_extensions(
    client_factory, resource, identifier, wrapper
):
    requests = []
    fixture = {wrapper: {"id": identifier, "futureField": {"retain": True}}}

    def respond(request):
        requests.append(request)
        return httpx.Response(200, json=fixture)

    sdk = client_factory(respond)
    result = getattr(sdk, resource).retrieve(identifier, project_id=PROJECT)
    assert len(requests) == 1
    request = requests[0]
    assert (request.method, request.url.path) == ("GET", f"/v1/{resource}/{identifier}")
    assert dict(request.url.params) == {"projectId": PROJECT}
    assert result.to_dict()[wrapper]["futureField"] == {"retain": True}


def test_cancel_uses_remote_action_and_keeps_acknowledged_status(client_factory):
    requests = []

    def respond(request):
        requests.append(request)
        # An action acknowledgement need not yet report a terminal status.
        return httpx.Response(200, json={"job": {"jobId": "fixture-job", "status": "in-progress"}})

    sdk = client_factory(respond)
    result = sdk.jobs.trigger_action("fixture-job", action="cancel", project_id=PROJECT)
    assert len(requests) == 1
    request = requests[0]
    assert (request.method, request.url.path) == ("POST", "/v1/jobs/fixture-job/action")
    assert dict(request.url.params) == {"projectId": PROJECT}
    assert json.loads(request.content) == {"action": "cancel"}
    assert result.job.status == "in-progress"


@pytest.mark.parametrize("status", [408, 409, 429, 500, 503])
@pytest.mark.parametrize("operation", ["model", "workflow"])
def test_submission_http_errors_never_retry(client_factory, status, operation):
    requests = []

    def respond(request):
        requests.append(request)
        return httpx.Response(
            status, json={"error": "fixture failure"}, headers={"Retry-After": "0"}
        )

    sdk = client_factory(respond)
    with pytest.raises(APIStatusError) as error:
        if operation == "model":
            sdk.generate.run_model("fixture-model", body={}, dry_run=False, project_id=PROJECT)
        else:
            sdk.workflows.run("fixture-workflow", body={}, dry_run=False, project_id=PROJECT)
    assert error.value.status_code == status
    assert len(requests) == 1


@pytest.mark.parametrize(
    "failure,expected",
    [
        (httpx.ReadTimeout, APITimeoutError),
        (httpx.ConnectError, APIConnectionError),
    ],
)
@pytest.mark.parametrize("operation", ["model", "workflow"])
def test_submission_transport_failure_never_retries(client_factory, failure, expected, operation):
    requests = []

    def fail(request):
        requests.append(request)
        raise failure("fixture lost response", request=request)

    sdk = client_factory(fail)
    with pytest.raises(expected):
        if operation == "model":
            sdk.generate.run_model("fixture-model", body={}, dry_run=False, project_id=PROJECT)
        else:
            sdk.workflows.run("fixture-workflow", body={}, dry_run=False, project_id=PROJECT)
    assert len(requests) == 1


def test_redirect_is_not_followed_by_explicit_transport(client_factory):
    requests = []

    def redirect(request):
        requests.append(request)
        return httpx.Response(307, headers={"Location": "https://storage.example.invalid/redirect"})

    sdk = client_factory(redirect)
    with pytest.raises(APIStatusError):
        sdk.generate.run_model("fixture-model", body={}, dry_run=False, project_id=PROJECT)
    assert len(requests) == 1
    assert requests[0].url.host == "api.example.invalid"


def test_explicit_basic_credentials_override_ambient_basic(client_factory, monkeypatch):
    monkeypatch.setenv("SCENARIO_SDK_API_KEY", "ambient-key")
    monkeypatch.setenv("SCENARIO_SDK_API_SECRET", "ambient-secret")
    requests = []

    def respond(request):
        requests.append(request)
        return httpx.Response(200, json={"job": {"jobId": "fixture-job"}})

    sdk = client_factory(respond)
    sdk.jobs.retrieve("fixture-job", project_id=PROJECT)
    expected = base64.b64encode(b"fixture-key:fixture-secret").decode("ascii")
    assert requests[0].headers["Authorization"] == f"Basic {expected}"


@pytest.mark.xfail(
    strict=True,
    raises=AssertionError,
    reason="SDK 2.1.0 auth precedence: https://github.com/scenario-labs/scenario-sdk-python/issues/26",
)
def test_explicit_bearer_must_override_ambient_basic(client_factory, monkeypatch):
    monkeypatch.setenv("SCENARIO_SDK_API_KEY", "ambient-key")
    monkeypatch.setenv("SCENARIO_SDK_API_SECRET", "ambient-secret")
    requests = []

    def respond(request):
        requests.append(request)
        return httpx.Response(200, json={"job": {"jobId": "fixture-job"}})

    sdk = client_factory(respond, api_key=None, api_secret=None, bearer_auth="selected-oauth")
    sdk.jobs.retrieve("fixture-job", project_id=PROJECT)
    assert requests[0].headers["Authorization"] == "Bearer selected-oauth"
