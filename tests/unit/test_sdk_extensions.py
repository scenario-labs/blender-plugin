# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Named discovery fallbacks use the real selected SDK, without network calls."""

import base64

import httpx
import pytest

from scenario.core.api.sdk_adapter import AdapterError, Credentials, SDKAdapter


@pytest.fixture
def adapter():
    clients = []

    def create(handler, **options):
        settings = dict(
            credentials=Credentials("fixture-key", "fixture-secret"),
            online=lambda: True,
            base_url="https://service.example.invalid/v1",
            transport=httpx.MockTransport(handler),
        )
        settings.update(options)
        client = SDKAdapter(**settings)
        clients.append(client)
        return client

    yield create
    for client in clients:
        client.close()


def discovery(client, kind):
    return client.teams() if kind == "teams" else client.projects("requested-team")


@pytest.mark.parametrize("kind", ["teams", "projects"])
@pytest.mark.parametrize("bearer", [False, True])
def test_discovery_reuses_selected_auth_without_inheriting_project(
    adapter, monkeypatch, kind, bearer
):
    monkeypatch.setenv("SCENARIO_SDK_API_KEY", "ambient-key")
    monkeypatch.setenv("SCENARIO_SDK_API_SECRET", "ambient-secret")
    monkeypatch.setenv("SCENARIO_BASE_URL", "https://wrong.invalid")
    monkeypatch.setenv(
        "SCENARIO_CUSTOM_HEADERS", "Authorization: Bearer ambient\nX-Project-Id: wrong"
    )
    requests = []
    payload = {kind: [{"id": "fixture-id", "future": {"retained": True}}], "futurePage": True}

    def respond(request):
        requests.append(request)
        return httpx.Response(200, json=payload)

    credentials = (
        Credentials(bearer_token="selected-token") if bearer else Credentials("key", "secret")
    )
    client = adapter(
        respond, credentials=credentials, project_id="stale-project", team_id="stale-team"
    )
    assert discovery(client, kind) == payload
    assert len(requests) == 1
    request = requests[0]
    assert request.method == "GET"
    assert request.url.host == "service.example.invalid"
    assert request.url.path == f"/v1/{kind}"
    assert dict(request.url.params) == ({} if kind == "teams" else {"teamId": "requested-team"})
    expected = (
        "Bearer selected-token" if bearer else "Basic " + base64.b64encode(b"key:secret").decode()
    )
    assert request.headers["Authorization"] == expected
    assert "X-Project-Id" not in request.headers
    assert request.content == b""
    assert client.project_id == "stale-project"
    assert client.team_id == "stale-team"
    assert client.account_id is None  # A listing is not a principal/default-project assertion.


@pytest.mark.parametrize("kind", ["teams", "projects"])
@pytest.mark.parametrize("state", ["offline", "closed"])
def test_discovery_respects_permission_and_client_lifetime(adapter, kind, state):
    requests = []
    client = adapter(lambda request: requests.append(request), online=lambda: state != "offline")
    if state == "closed":
        client.close()
    with pytest.raises(AdapterError, match="disabled|closed"):
        discovery(client, kind)
    assert not requests


@pytest.mark.parametrize("kind", ["teams", "projects"])
@pytest.mark.parametrize("failure", [401, 403, 429, 503, 302, "timeout"])
def test_discovery_failures_are_single_attempt_and_sanitized(adapter, kind, failure):
    requests = []

    def respond(request):
        requests.append(request)
        if failure == "timeout":
            raise httpx.ReadTimeout("private response and credential", request=request)
        return httpx.Response(
            failure,
            json={"error": "private response and credential"},
            headers={"Retry-After": "0", "Location": "https://wrong.invalid"},
        )

    client = adapter(respond)
    with pytest.raises(AdapterError) as error:
        discovery(client, kind)
    assert len(requests) == 1
    assert "private" not in str(error.value)
    assert "wrong.invalid" not in str(error.value)


@pytest.mark.parametrize("kind", ["teams", "projects"])
@pytest.mark.parametrize("records", [None, {}, "bad", [None], [{}], [{"id": "bad/id"}]])
def test_discovery_rejects_malformed_lists_and_identities(adapter, kind, records):
    client = adapter(lambda request: httpx.Response(200, json={kind: records}))
    with pytest.raises(AdapterError):
        discovery(client, kind)


@pytest.mark.parametrize("raw", [b"not json", b"[]", b'{"teams":[],"cost":NaN}'])
def test_discovery_rejects_invalid_json(adapter, raw):
    client = adapter(lambda request: httpx.Response(200, content=raw))
    with pytest.raises(AdapterError):
        client.teams()


@pytest.mark.parametrize("team", [None, "", " ", "../team", "team?projectId=wrong"])
def test_project_discovery_requires_valid_explicit_team(adapter, team):
    requests = []
    client = adapter(lambda request: requests.append(request))
    with pytest.raises(ValueError):
        client.projects(team)
    assert not requests


def test_discovery_does_not_select_first_project_or_hide_response_fields(adapter):
    payload = {
        "teams": [{"id": "team", "projects": [{"id": "one"}, {"id": "two"}]}],
        "nextPaginationToken": "opaque",
    }
    requests = []

    def respond(request):
        requests.append(request)
        return httpx.Response(200, json=payload)

    client = adapter(respond)
    assert client.teams() == payload
    assert len(requests) == 1  # No invented pagination/default-scope contract.
    assert client.project_id is None


def test_api_key_generation_needs_no_discovery_or_explicit_tenant(adapter):
    requests = []

    def respond(request):
        requests.append(request)
        if request.url.params.get("dryRun") == "true":
            return httpx.Response(200, json={"creativeUnitsCost": 1})
        return httpx.Response(200, json={"job": {"jobId": "fixture-job"}})

    client = adapter(respond)
    quote = client.estimate_model({"id": "fixture-model", "type": "custom", "inputs": []}, {})
    client.submit_estimate(quote, before_send=lambda: None)
    assert len(requests) == 2
    assert all(request.url.path == "/v1/generate/custom/fixture-model" for request in requests)
    assert [dict(request.url.params) for request in requests] == [
        {"dryRun": "true"},
        {},
    ]
    assert all(request.headers["Authorization"].startswith("Basic ") for request in requests)


@pytest.mark.parametrize("kind", ["teams", "projects"])
def test_empty_discovery_list_is_valid(adapter, kind):
    client = adapter(lambda request: httpx.Response(200, json={kind: []}))
    assert discovery(client, kind) == {kind: []}
