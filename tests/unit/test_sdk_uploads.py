# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""SDK multipart metadata commands, without storage transfer or live service calls."""

import copy
import json
import socket

import httpx
import pytest

from scenario.core.api.sdk_adapter import AdapterError, Credentials, SDKAdapter

CREATE = dict(
    kind="image", file_name="référence.png", content_type="image/png", file_size=4096, parts=2
)
RECORD = {
    "id": "fixture-upload",
    "status": "pending",
    "parts": [
        {"number": 1, "url": "https://storage.invalid/part?signature=private", "expires": "future"}
    ],
    "futureField": {"keep": True},
}


@pytest.fixture(autouse=True)
def forbid_network(monkeypatch):
    def deny(*args, **kwargs):
        pytest.fail("Upload contracts must not open sockets")

    monkeypatch.setattr(socket.socket, "connect", deny)
    monkeypatch.setattr(socket.socket, "connect_ex", deny)
    monkeypatch.setattr(socket, "create_connection", deny)


@pytest.fixture
def client():
    clients = []

    def make(handler=None, **kwargs):
        options = dict(
            credentials=Credentials("selected-key", "selected-secret"),
            online=lambda: True,
            base_url="https://service.invalid/v1",
            project_id="selected-project",
            transport=httpx.MockTransport(
                handler or (lambda r: httpx.Response(200, json={"upload": RECORD}))
            ),
        )
        options.update(kwargs)
        value = SDKAdapter(**options)
        clients.append(value)
        return value

    yield make
    for value in clients:
        value.close()


def invoke(adapter, operation):
    if operation == "create":
        return adapter.create_upload(**CREATE)
    if operation == "retrieve":
        return adapter.upload("fixture-upload")
    return adapter.complete_upload("fixture-upload")


@pytest.mark.parametrize("project", [None, "selected-project"])
def test_create_maps_sdk_options_without_transferring_bytes(client, project):
    requests = []

    def respond(request):
        requests.append(request)
        return httpx.Response(200, json={"upload": RECORD})

    options = {"collection_ids": ["collection-1"], "parent_id": "parent-1", "hide": False}
    original = copy.deepcopy(options)
    adapter = client(respond, project_id=project)
    result = adapter.create_upload(**CREATE, asset_options=options)
    assert result == RECORD and options == original
    assert len(requests) == 1
    request = requests[0]
    assert (request.method, request.url.host, request.url.path) == (
        "POST",
        "service.invalid",
        "/v1/uploads",
    )
    assert dict(request.url.params) == ({"projectId": project} if project else {})
    assert json.loads(request.content) == {
        "kind": "image",
        "fileName": "référence.png",
        "contentType": "image/png",
        "fileSize": 4096,
        "parts": 2,
        "assetOptions": {"collectionIds": ["collection-1"], "parentId": "parent-1", "hide": False},
    }


@pytest.mark.parametrize("operation", ["retrieve", "complete"])
@pytest.mark.parametrize("status", ["validating", "imported", "failed", "future-status"])
def test_known_upload_preserves_exact_identity_status_and_future_fields(client, operation, status):
    requests = []
    record = {
        **RECORD,
        "status": status,
        "entityId": "fixture-asset",
        "jobId": "fixture-job",
        "errorMessage": "fixture error",
    }

    def respond(request):
        requests.append(request)
        return httpx.Response(200, json={"upload": record})

    result = invoke(client(respond), operation)
    assert result == record
    assert len(requests) == 1
    request = requests[0]
    assert dict(request.url.params) == {"projectId": "selected-project"}
    if operation == "retrieve":
        assert request.method == "GET" and request.url.path == "/v1/uploads/fixture-upload"
        assert not request.content
    else:
        assert request.method == "POST" and request.url.path == "/v1/uploads/fixture-upload/action"
        assert json.loads(request.content) == {"action": "complete"}


@pytest.mark.parametrize(
    "kind", ["3d", "asset", "audio", "avatar", "image", "model", "text", "video"]
)
def test_declared_multipart_kinds_and_zero_byte_count_are_not_guessed(client, kind):
    assert client().create_upload(**{**CREATE, "kind": kind, "file_size": 0}) == RECORD


@pytest.mark.parametrize(
    "updates",
    [
        {"kind": "unsupported"},
        {"kind": []},
        {"file_name": ""},
        {"file_name": "  "},
        {"file_name": "../private.png"},
        {"file_name": "C:\\private.png"},
        {"file_name": "a\x00.png"},
        {"file_name": ".."},
        {"content_type": ""},
        {"content_type": "image/png\r\nInjected: 1"},
        {"content_type": "text/plain; charset=utf-8"},
        {"content_type": 1},
        {"file_size": True},
        {"file_size": -1},
        {"file_size": 1.5},
        {"file_size": float("inf")},
        {"parts": False},
        {"parts": 0},
        {"parts": -1},
        {"parts": 1.5},
        {"asset_options": []},
        {"asset_options": {"project_id": "wrong"}},
        {"asset_options": {"collection_ids": "wrong"}},
        {"asset_options": {"collection_ids": ["bad/id"]}},
        {"asset_options": {"parent_id": None}},
        {"asset_options": {"hide": 1}},
        {"kind": "model", "asset_options": {}},
    ],
)
def test_invalid_input_never_dispatches(client, updates):
    adapter = client(lambda r: pytest.fail("Invalid metadata dispatched"))
    with pytest.raises(ValueError):
        adapter.create_upload(**{**CREATE, **updates})


@pytest.mark.parametrize("operation", ["upload", "complete_upload"])
@pytest.mark.parametrize(
    "identifier",
    [None, "", "..", "a/b", "a?b", "a%2fb", " padded ", "a\u00a0b", "a\x7fb", "a" * 257],
)
def test_upload_ids_fail_before_dispatch(client, operation, identifier):
    adapter = client(lambda r: pytest.fail("Invalid identity dispatched"))
    with pytest.raises(ValueError):
        getattr(adapter, operation)(identifier)


@pytest.mark.parametrize("operation", ["create", "retrieve", "complete"])
@pytest.mark.parametrize(
    "record",
    [
        None,
        [],
        {},
        {"id": "fixture-upload"},
        {"id": "bad/id", "status": "pending"},
        {"id": "fixture-upload", "status": []},
    ],
)
def test_malformed_upload_record_fails_without_leaking_body(client, operation, record):
    adapter = client(lambda r: httpx.Response(200, json={"upload": record, "private": "secret"}))
    with pytest.raises(AdapterError) as exc:
        invoke(adapter, operation)
    assert "secret" not in str(exc.value) and "bad/id" not in str(exc.value)


@pytest.mark.parametrize("operation", ["retrieve", "complete"])
def test_mismatched_receipt_never_rebinds_upload(client, operation):
    adapter = client(
        lambda r: httpx.Response(200, json={"upload": {**RECORD, "id": "another-upload"}})
    )
    with pytest.raises(AdapterError, match="different upload identity"):
        invoke(adapter, operation)


@pytest.mark.parametrize("operation", ["create", "retrieve", "complete"])
@pytest.mark.parametrize("failure", ["timeout", 307, 429, 503, "invalid-json"])
def test_failures_never_repeat_create_complete_or_poll(client, operation, failure):
    requests = []

    def respond(request):
        requests.append(request)
        if failure == "timeout":
            raise httpx.ReadTimeout("secret?signature=private", request=request)
        if failure == "invalid-json":
            return httpx.Response(200, content=b"secret?signature=private")
        return httpx.Response(
            failure,
            text="secret?signature=private",
            headers={"Retry-After": "0", "Location": "https://storage.invalid/?signature=private"},
        )

    with pytest.raises(AdapterError) as exc:
        invoke(client(respond), operation)
    assert len(requests) == 1
    assert "signature" not in str(exc.value) and "secret" not in str(exc.value)


@pytest.mark.parametrize("operation", ["create", "retrieve", "complete"])
def test_online_permission_checked_on_every_command_and_after_close(client, operation):
    enabled = True
    requests = []

    def respond(request):
        requests.append(request)
        return httpx.Response(200, json={"upload": RECORD})

    adapter = client(respond, online=lambda: enabled)
    invoke(adapter, operation)
    enabled = False
    with pytest.raises(AdapterError, match="Online access"):
        invoke(adapter, operation)
    enabled = True
    adapter.close()
    with pytest.raises(AdapterError, match="closed"):
        invoke(adapter, operation)
    assert len(requests) == 1


def test_selected_credentials_and_project_do_not_follow_ambient_settings(client, monkeypatch):
    monkeypatch.setenv("SCENARIO_SDK_API_KEY", "ambient-key")
    monkeypatch.setenv("SCENARIO_SDK_API_SECRET", "ambient-secret")
    monkeypatch.setenv(
        "SCENARIO_CUSTOM_HEADERS", "Authorization: Bearer wrong\nX-Project-Id: wrong"
    )
    requests = []

    def respond(request):
        requests.append(request)
        return httpx.Response(200, json={"upload": RECORD})

    adapter = client(respond, credentials=Credentials(bearer_token="selected-token"))
    for operation in ("create", "retrieve", "complete"):
        invoke(adapter, operation)
    assert len(requests) == 3
    assert all(r.headers["Authorization"] == "Bearer selected-token" for r in requests)
    assert all(dict(r.url.params) == {"projectId": "selected-project"} for r in requests)
    assert all("X-Project-Id" not in r.headers for r in requests)
