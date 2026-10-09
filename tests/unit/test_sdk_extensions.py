# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Named SDK fallbacks use the real selected SDK, without network calls.

Covers discovery and the workflow step decisions that pair the generated
approval method with the user-selection fallback.
"""

import base64
import json

import httpx
import pytest

from scenario.core.api.sdk_adapter import (
    AdapterError,
    AdapterStatusError,
    Credentials,
    SDKAdapter,
)


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


WORKFLOW_JOB = "fixture-workflow-job"
DECISIONS = {
    "approve": ("user-approval", "approve", None),
    "approval-reject": ("user-approval", "reject", None),
    "select": ("user-selection", "select", [2, 0]),
    "selection-reject": ("user-selection", "reject", None),
}


def decide(client, case, workflow_id="fixture-workflow"):
    node_type, action, indices = DECISIONS[case]
    return client.workflow_decision(
        workflow_id, WORKFLOW_JOB, "fixture-node", node_type, action, selected_indices=indices
    )


def acknowledged(request):
    return httpx.Response(200, json={"job": {"jobId": WORKFLOW_JOB, "status": "in-progress"}})


@pytest.mark.parametrize("case", DECISIONS)
@pytest.mark.parametrize("bearer", [False, True])
@pytest.mark.parametrize("project", [None, "selected-project"])
def test_workflow_decisions_send_one_documented_request_in_selected_scope(
    adapter, monkeypatch, case, bearer, project
):
    monkeypatch.setenv("SCENARIO_SDK_API_KEY", "ambient-key")
    monkeypatch.setenv("SCENARIO_SDK_API_SECRET", "ambient-secret")
    monkeypatch.setenv("SCENARIO_BASE_URL", "https://wrong.invalid")
    monkeypatch.setenv(
        "SCENARIO_CUSTOM_HEADERS", "Authorization: Bearer ambient\nX-Project-Id: wrong"
    )
    requests = []

    def respond(request):
        requests.append(request)
        return acknowledged(request)

    credentials = (
        Credentials(bearer_token="selected-token") if bearer else Credentials("key", "secret")
    )
    client = adapter(respond, credentials=credentials, project_id=project)
    job = decide(client, case)
    assert job == {"jobId": WORKFLOW_JOB, "status": "in-progress"}
    assert len(requests) == 1
    request = requests[0]
    node_type, action, indices = DECISIONS[case]
    assert request.method == "PUT"
    assert request.url.host == "service.example.invalid"
    assert request.url.path == f"/v1/workflows/fixture-workflow/{node_type}"
    # Only the adapter's explicit project override is sent; API-key scope otherwise.
    assert dict(request.url.params) == ({} if project is None else {"projectId": project})
    expected = {"nodeId": "fixture-node", "workflowJobId": WORKFLOW_JOB, "action": action}
    if indices is not None:
        expected["selectedIndices"] = indices
    assert json.loads(request.content) == expected
    authorization = (
        "Bearer selected-token" if bearer else "Basic " + base64.b64encode(b"key:secret").decode()
    )
    assert request.headers["Authorization"] == authorization
    assert "X-Project-Id" not in request.headers


def test_selection_path_uses_the_generated_approval_encoding(adapter):
    requests = []

    def respond(request):
        requests.append(request)
        return acknowledged(request)

    client = adapter(respond)
    for case in ("approve", "select"):
        decide(client, case, workflow_id="workflow:é@team")
    approval, selection = (request.url.raw_path for request in requests)
    assert approval == b"/v1/workflows/workflow:%C3%A9@team/user-approval"
    assert selection == b"/v1/workflows/workflow:%C3%A9@team/user-selection"


@pytest.mark.parametrize("case", DECISIONS)
@pytest.mark.parametrize("state", ["offline", "closed"])
def test_workflow_decisions_respect_permission_and_client_lifetime(adapter, case, state):
    requests = []
    client = adapter(lambda request: requests.append(request), online=lambda: state != "offline")
    if state == "closed":
        client.close()
    with pytest.raises(AdapterError, match="disabled|closed"):
        decide(client, case)
    assert not requests


@pytest.mark.parametrize("case", DECISIONS)
@pytest.mark.parametrize("failure", [400, 409, 429, 503, 302, "timeout"])
def test_workflow_decision_failures_are_single_attempt_and_keep_status(adapter, case, failure):
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
        decide(client, case)
    assert len(requests) == 1
    assert "private" not in str(error.value)
    assert "wrong.invalid" not in str(error.value)
    if failure == "timeout":
        # A lost response is not a service reply: the decision may have applied.
        assert not isinstance(error.value, AdapterStatusError)
    else:
        assert isinstance(error.value, AdapterStatusError)
        assert error.value.status_code == failure
        generic = f"Scenario request failed (HTTP {failure})"
        limited = "Too many requests (HTTP 429). Try again shortly."
        assert str(error.value) == (limited if failure == 429 else generic)


@pytest.mark.parametrize("case", DECISIONS)
@pytest.mark.parametrize("project", [None, "selected-project"])
def test_workflow_decision_denial_names_the_project_only_when_one_was_sent(adapter, case, project):
    # An approval passes the SDK's omit sentinel when there is no override; that
    # request carries no projectId, so its 403 must not blame the Project ID.
    requests = []

    def respond(request):
        requests.append(request)
        return httpx.Response(403, json={"error": "private response and credential"})

    client = adapter(respond, project_id=project)
    with pytest.raises(AdapterStatusError) as error:
        decide(client, case)
    assert len(requests) == 1
    assert dict(requests[0].url.params) == ({} if project is None else {"projectId": project})
    assert error.value.status_code == 403
    message = str(error.value)
    assert message.startswith("Access denied (HTTP 403).")
    assert ("Project ID" in message) is (project is not None)


@pytest.mark.parametrize("case", DECISIONS)
@pytest.mark.parametrize(
    "raw",
    [
        b"not json",
        b"[]",
        b"{}",
        b'{"job":null}',
        b'{"job":{}}',
        b'{"job":{"jobId":"another-job"}}',
    ],
)
def test_workflow_decision_requires_the_matching_job_acknowledgement(adapter, case, raw):
    requests = []

    def respond(request):
        requests.append(request)
        return httpx.Response(200, content=raw)

    with pytest.raises(AdapterError) as error:
        decide(adapter(respond), case)
    assert not isinstance(error.value, AdapterStatusError)
    assert len(requests) == 1


@pytest.mark.parametrize(
    "arguments",
    [
        ("../workflow", WORKFLOW_JOB, "node", "user-approval", "approve", None),
        ("workflow/one", WORKFLOW_JOB, "node", "user-approval", "approve", None),
        ("workflow?projectId=wrong", WORKFLOW_JOB, "node", "user-selection", "reject", None),
        ("workflow", "", "node", "user-approval", "approve", None),
        ("workflow", "job/other", "node", "user-selection", "reject", None),
        ("workflow", WORKFLOW_JOB, "", "user-approval", "approve", None),
        ("workflow", WORKFLOW_JOB, " node", "user-approval", "approve", None),
        ("workflow", WORKFLOW_JOB, "node\n", "user-selection", "reject", None),
        # C1 control, bidi override and a lone surrogate, which UTF-8 cannot encode.
        ("workflow", WORKFLOW_JOB, "no\u0085de", "user-approval", "approve", None),
        ("workflow", WORKFLOW_JOB, "node\u202e", "user-selection", "reject", None),
        ("workflow", WORKFLOW_JOB, "\ud800", "user-selection", "select", [0]),
        ("workflow", WORKFLOW_JOB, "n" * 1025, "user-approval", "approve", None),
        ("workflow\ud800", WORKFLOW_JOB, "node", "user-approval", "approve", None),
        ("workflow", "job\u202e", "node", "user-selection", "reject", None),
        ("workflow", WORKFLOW_JOB, None, "user-approval", "approve", None),
        ("workflow", WORKFLOW_JOB, "node", "model", "approve", None),
        ("workflow", WORKFLOW_JOB, "node", None, "approve", None),
        ("workflow", WORKFLOW_JOB, "node", "user-approval", None, None),
        ("workflow", WORKFLOW_JOB, "node", "user-approval", "select", [0]),
        ("workflow", WORKFLOW_JOB, "node", "user-approval", "cancel", None),
        ("workflow", WORKFLOW_JOB, "node", "user-selection", "approve", None),
        ("workflow", WORKFLOW_JOB, "node", "user-approval", "approve", [0]),
        ("workflow", WORKFLOW_JOB, "node", "user-approval", "reject", []),
        ("workflow", WORKFLOW_JOB, "node", "user-selection", "reject", [0]),
        ("workflow", WORKFLOW_JOB, "node", "user-selection", "select", None),
        ("workflow", WORKFLOW_JOB, "node", "user-selection", "select", "0,1"),
        ("workflow", WORKFLOW_JOB, "node", "user-selection", "select", {0}),
        ("workflow", WORKFLOW_JOB, "node", "user-selection", "select", [1, 1]),
        ("workflow", WORKFLOW_JOB, "node", "user-selection", "select", [-1]),
        ("workflow", WORKFLOW_JOB, "node", "user-selection", "select", [True]),
        ("workflow", WORKFLOW_JOB, "node", "user-selection", "select", [1.0]),
        ("workflow", WORKFLOW_JOB, "node", "user-selection", "select", []),
        ("workflow", WORKFLOW_JOB, "node", "user-selection", "select", list(range(101))),
        ("workflow", WORKFLOW_JOB, "node", "user-selection", "select", [2**53]),
    ],
)
def test_invalid_workflow_decisions_never_reach_transport(adapter, arguments):
    requests = []
    client = adapter(lambda request: requests.append(request))
    workflow_id, job_id, node_id, node_type, action, indices = arguments
    with pytest.raises(ValueError) as error:
        client.workflow_decision(
            workflow_id, job_id, node_id, node_type, action, selected_indices=indices
        )
    # The adapter's own validation, not a codec failure during SDK serialization.
    assert not isinstance(error.value, UnicodeError)
    assert not requests


def test_node_ids_travel_only_in_the_body(adapter):
    requests = []

    def respond(request):
        requests.append(request)
        return acknowledged(request)

    client = adapter(respond)
    client.workflow_decision(
        "fixture-workflow", WORKFLOW_JOB, "loop/node#1?x", "user-selection", "select", (1,)
    )
    assert requests[0].url.raw_path == b"/v1/workflows/fixture-workflow/user-selection"
    assert json.loads(requests[0].content)["nodeId"] == "loop/node#1?x"
    assert json.loads(requests[0].content)["selectedIndices"] == [1]


def test_selection_accepts_the_documented_default_maximum(adapter):
    requests = []

    def respond(request):
        requests.append(request)
        return acknowledged(request)

    picks = [2**53 - 1, *range(99)]
    adapter(respond).workflow_decision(
        "fixture-workflow", WORKFLOW_JOB, "étape 1", "user-selection", "select", picks
    )
    body = json.loads(requests[0].content)
    assert body["selectedIndices"] == picks
    assert body["nodeId"] == "étape 1"
