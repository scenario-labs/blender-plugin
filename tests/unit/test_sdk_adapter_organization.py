# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Exercise adapter collection and tag writes against the real SDK, offline.

The fake service is an httpx.MockTransport. Writes are unpaid account mutations,
so the contract is one attempt, a definite rejection or an uncertain outcome,
and reconciliation by reading the assets back, never by sending again.
"""

import json
import os
import socket

import httpx
import pytest

from scenario.core.api.sdk_adapter import (
    MAX_ASSET_RECORDS,
    MAX_COLLECTION_ASSETS,
    MAX_TAG_CHANGES,
    AdapterError,
    Credentials,
    SDKAdapter,
    WriteRejected,
    WriteUncertain,
)

URL = "https://service.example.invalid/v1"
PRIVATE = "private-service-text"
COLLECTION = {
    "id": "fixture-collection",
    "name": "Hero props",
    "assetCount": 1,
    "itemCount": 1,
    "modelCount": 0,
    "futureField": {"keep": True},
}


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

    def create(handler, **options):
        settings = {
            "credentials": Credentials("selected-key", "selected-secret"),
            "base_url": URL,
            "online": lambda: True,
            "transport": httpx.MockTransport(handler),
        }
        settings.update(options)
        client = SDKAdapter(**settings)
        clients.append(client)
        return client

    yield create
    for client in clients:
        client.close()


def recorder(response):
    requests = []

    def handler(request):
        requests.append(request)
        return response(request) if callable(response) else response

    return requests, handler


def deny(request):
    pytest.fail("Invalid or unsent organization request reached transport")


WRITES = {
    "create": lambda client: client.create_collection("Hero props"),
    "add": lambda client: client.add_collection_assets("fixture-collection", ["asset-a"]),
    "remove": lambda client: client.remove_collection_assets("fixture-collection", ["asset-a"]),
    "tags": lambda client: client.update_asset_tags("asset-a", add=["hero"]),
}


@pytest.mark.parametrize("project", [None, "selected-project"])
@pytest.mark.parametrize(
    "operation,method,path,body",
    [
        ("create", "POST", "/v1/collections", {"name": "Hero props"}),
        (
            "add",
            "PUT",
            "/v1/collections/fixture-collection/assets",
            {"assetIds": ["asset-a"]},
        ),
        (
            "remove",
            "DELETE",
            "/v1/collections/fixture-collection/assets",
            {"assetIds": ["asset-a"]},
        ),
        ("tags", "PUT", "/v1/assets/asset-a/tags", {"add": ["hero"], "strict": False}),
    ],
)
def test_writes_send_one_scoped_sdk_request(adapter, project, operation, method, path, body):
    reply = (
        {"added": ["hero"], "deleted": []} if operation == "tags" else {"collection": COLLECTION}
    )
    requests, handler = recorder(httpx.Response(200, json=reply))
    result = WRITES[operation](adapter(handler, project_id=project))
    assert result == (reply if operation == "tags" else COLLECTION)
    assert len(requests) == 1
    request = requests[0]
    assert (request.method, request.url.path) == (method, path)
    assert dict(request.url.params) == ({"projectId": project} if project else {})
    assert json.loads(request.content) == body


@pytest.mark.parametrize("bearer", [False, True])
@pytest.mark.parametrize("operation", sorted(WRITES))
def test_writes_use_only_the_selected_account_and_project(adapter, monkeypatch, bearer, operation):
    ambient = {
        "SCENARIO_SDK_API_KEY": "ambient-key",
        "SCENARIO_SDK_API_SECRET": "ambient-secret",
        "SCENARIO_SDK_JWT": "ambient-jwt",
        "SCENARIO_BASE_URL": "https://wrong.example.invalid",
        "SCENARIO_CUSTOM_HEADERS": "Authorization: Bearer wrong\nX-Project-Id: wrong",
        "HTTPS_PROXY": "http://wrong.example.invalid",
    }
    for name, value in ambient.items():
        monkeypatch.setenv(name, value)
    reply = {"added": [], "deleted": []} if operation == "tags" else {"collection": COLLECTION}
    requests, handler = recorder(httpx.Response(200, json=reply))
    credentials = (
        Credentials(bearer_token="selected-token")
        if bearer
        else Credentials("selected-key", "selected-secret")
    )
    WRITES[operation](adapter(handler, credentials=credentials, project_id="selected-project"))
    request = requests[0]
    assert request.url.host == "service.example.invalid"
    assert request.headers.get_list("Authorization") == [credentials.authorization()]
    assert "X-Project-Id" not in request.headers
    assert dict(request.url.params) == {"projectId": "selected-project"}
    assert {name: os.environ[name] for name in ambient} == ambient


@pytest.mark.parametrize("operation", sorted(WRITES))
@pytest.mark.parametrize("state", ["offline", "closed"])
def test_unsent_writes_raise_plain_adapter_errors(adapter, operation, state):
    client = adapter(deny, online=lambda: state != "offline")
    if state == "closed":
        client.close()
    with pytest.raises(AdapterError, match="disabled|closed") as error:
        WRITES[operation](client)
    # Neither class: the caller can rely on nothing having been sent.
    assert not isinstance(error.value, (WriteRejected, WriteUncertain))


def test_online_permission_is_checked_before_each_write(adapter):
    online = [True]
    requests, handler = recorder(
        lambda request: (
            online.__setitem__(0, False)
            or httpx.Response(200, json={"added": ["hero"], "deleted": []})
        )
    )
    client = adapter(handler, online=lambda: online[0])
    client.update_asset_tags("asset-a", add=["hero"])
    with pytest.raises(AdapterError, match="Online access"):
        client.update_asset_tags("asset-b", add=["hero"])
    assert len(requests) == 1


@pytest.mark.parametrize("operation", sorted(WRITES))
@pytest.mark.parametrize(
    "status,text",
    [
        (400, "rejected this organization change"),
        (401, "rejected the selected credentials"),
        (403, "cannot change this asset or collection"),
        (404, "not found in the selected connection"),
        (405, "rejected this organization change"),
        (413, "rejected this organization change"),
        (422, "rejected this organization change"),
    ],
)
def test_definite_client_errors_are_rejections_without_retry(adapter, operation, status, text):
    requests, handler = recorder(
        httpx.Response(
            status,
            json={"error": PRIVATE, "assetIds": ["asset-a"]},
            headers={"Retry-After": "0", "x-should-retry": "true"},
        )
    )
    with pytest.raises(WriteRejected) as error:
        WRITES[operation](adapter(handler, project_id="selected-project"))
    assert error.value.status == status
    assert text in str(error.value)
    assert str(error.value).endswith(f"(HTTP {status})")
    assert len(requests) == 1
    assert_sanitized(error.value)


@pytest.mark.parametrize("operation", sorted(WRITES))
@pytest.mark.parametrize("failure", [307, 408, 409, 425, 429, 500, 502, 503, "timeout", "connect"])
def test_possible_application_is_uncertain_without_retry(adapter, operation, failure):
    def fail(request):
        if failure == "timeout":
            raise httpx.ReadTimeout(f"{PRIVATE} {request.url}", request=request)
        if failure == "connect":
            raise httpx.ConnectError(f"{PRIVATE} {request.url}", request=request)
        return httpx.Response(
            failure,
            json={"error": PRIVATE},
            headers={
                "Location": "https://elsewhere.example.invalid/redirect",
                "Retry-After": "0",
                "x-should-retry": "true",
            },
        )

    requests, handler = recorder(fail)
    with pytest.raises(WriteUncertain) as error:
        WRITES[operation](adapter(handler, project_id="selected-project"))
    assert error.value.status == (None if isinstance(failure, str) else failure)
    assert "read it back" in str(error.value)
    assert len(requests) == 1
    assert requests[0].url.host == "service.example.invalid"
    assert_sanitized(error.value)


def assert_sanitized(error):
    text = str(error)
    for private in (
        PRIVATE,
        "selected-secret",
        "selected-project",
        "service.example.invalid",
        "fixture-collection",
        "asset-a",
        "Hero props",
        "hero",
    ):
        assert private not in text
    # No chained SDK or transport exception can carry a URL or body upward.
    assert error.__cause__ is None
    assert error.__context__ is None or error.__suppress_context__


@pytest.mark.parametrize("operation", sorted(WRITES))
@pytest.mark.parametrize(
    "content",
    [
        b"",
        b"not json",
        b"[]",
        b'{"collection": null}',
        b'{"error": "private-service-text"}',
        b'{"added": NaN}',
    ],
)
def test_malformed_success_bodies_are_uncertain(adapter, operation, content):
    requests, handler = recorder(httpx.Response(200 if content else 204, content=content))
    with pytest.raises(WriteUncertain) as error:
        WRITES[operation](adapter(handler))
    assert error.value.status is None
    assert len(requests) == 1
    assert_sanitized(error.value)


@pytest.mark.parametrize(
    "operation,reply",
    [
        ("create", {"collection": {**COLLECTION, "name": "Other"}}),
        ("create", {"collection": {**COLLECTION, "name": "hero props"}}),
        ("create", {"collection": {**COLLECTION, "id": None}}),
        ("create", {"collection": {**COLLECTION, "id": "bad/id"}}),
        ("add", {"collection": {**COLLECTION, "id": "other-collection"}}),
        ("remove", {"collection": {**COLLECTION, "id": "other-collection"}}),
        ("add", {"collection": {"name": "Hero props"}}),
        ("tags", {"added": ["hero", "unrequested"], "deleted": []}),
        ("tags", {"added": ["HERO"], "deleted": []}),
        ("tags", {"added": ["hero"], "deleted": ["hero"]}),
        ("tags", {"added": ["hero"]}),
        ("tags", {"added": "hero", "deleted": []}),
        ("tags", {"added": [None], "deleted": []}),
    ],
)
def test_mismatched_acknowledgements_are_uncertain(adapter, operation, reply):
    requests, handler = recorder(httpx.Response(200, json=reply))
    with pytest.raises(WriteUncertain):
        WRITES[operation](adapter(handler))
    assert len(requests) == 1


def test_non_strict_tag_no_ops_are_valid_acknowledgements(adapter):
    reply = {"added": [], "deleted": [], "futureField": True}
    requests, handler = recorder(httpx.Response(200, json=reply))
    client = adapter(handler)
    assert client.update_asset_tags("asset-a", add=["hero"], remove=["draft"]) == reply
    assert client.update_asset_tags("asset-a", remove=["draft"]) == reply
    assert [json.loads(request.content) for request in requests] == [
        {"add": ["hero"], "delete": ["draft"], "strict": False},
        {"delete": ["draft"], "strict": False},
    ]


@pytest.mark.parametrize(
    "call",
    [
        lambda c: c.create_collection(""),
        lambda c: c.create_collection("   "),
        lambda c: c.create_collection(" Hero props"),
        lambda c: c.create_collection("Hero props\n"),
        lambda c: c.create_collection("Hero\tprops"),
        lambda c: c.create_collection("Hero\x7fprops"),
        lambda c: c.create_collection("Hero\x85props"),
        lambda c: c.create_collection("x" * 201),
        lambda c: c.create_collection(None),
        lambda c: c.create_collection(["Hero props"]),
        lambda c: c.add_collection_assets("fixture-collection", []),
        lambda c: c.add_collection_assets("fixture-collection", "asset-a"),
        lambda c: c.add_collection_assets("fixture-collection", ["asset-a", "asset-a"]),
        lambda c: c.add_collection_assets(
            "fixture-collection", [f"asset-{i}" for i in range(MAX_COLLECTION_ASSETS + 1)]
        ),
        lambda c: c.add_collection_assets("fixture-collection", ["bad/id"]),
        lambda c: c.add_collection_assets("fixture-collection", [" asset-a"]),
        lambda c: c.add_collection_assets("", ["asset-a"]),
        lambda c: c.remove_collection_assets("bad?collection", ["asset-a"]),
        lambda c: c.remove_collection_assets("fixture-collection", [None]),
        lambda c: c.update_asset_tags("asset-a"),
        lambda c: c.update_asset_tags("asset-a", add=[], remove=[]),
        lambda c: c.update_asset_tags("asset-a", add="hero"),
        lambda c: c.update_asset_tags("asset-a", add=["hero", "hero"]),
        lambda c: c.update_asset_tags("asset-a", add=["hero"], remove=["hero"]),
        lambda c: c.update_asset_tags("asset-a", add=[" hero"]),
        lambda c: c.update_asset_tags("asset-a", add=["he\nro"]),
        lambda c: c.update_asset_tags("asset-a", add=["x" * 201]),
        lambda c: c.update_asset_tags("asset-a", add=[1]),
        lambda c: c.update_asset_tags(
            "asset-a", add=[f"tag-{i}" for i in range(MAX_TAG_CHANGES + 1)]
        ),
        lambda c: c.update_asset_tags("../asset", add=["hero"]),
    ],
)
def test_invalid_writes_never_reach_transport(adapter, call):
    with pytest.raises(ValueError):
        call(adapter(deny))


def test_write_limits_accept_their_bounds_and_unicode_labels(adapter):
    assets = [f"asset-{i}" for i in range(MAX_COLLECTION_ASSETS)]
    tags = [f"tag-{i}" for i in range(MAX_TAG_CHANGES - 1)] + ["café, 東京"]
    name = "Accessoires d'été " + "x" * 182

    def respond(request):
        body = json.loads(request.content)
        if request.url.path.endswith("/tags"):
            return httpx.Response(200, json={"added": body["add"], "deleted": []})
        if request.method == "POST":
            return httpx.Response(200, json={"collection": {**COLLECTION, "name": body["name"]}})
        return httpx.Response(200, json={"collection": COLLECTION})

    requests, handler = recorder(respond)
    client = adapter(handler)
    assert client.create_collection(name)["name"] == name
    client.add_collection_assets("fixture-collection", tuple(assets))
    assert client.update_asset_tags("asset-a", add=tags)["added"] == tags
    assert len(name) == 200
    assert json.loads(requests[1].content) == {"assetIds": assets}
    assert len(requests) == 3


@pytest.mark.parametrize("project", [None, "selected-project"])
def test_collection_page_preserves_scope_records_and_cursor(adapter, project):
    page = {
        "collections": [COLLECTION, COLLECTION, {"id": "second", "name": "Second"}],
        "nextPaginationToken": "opaque+/= next",
        "extension": True,
    }
    requests, handler = recorder(httpx.Response(200, json=page))
    result = adapter(handler, project_id=project).collection_page(
        page_size=3, pagination_token="opaque+/= cursor"
    )
    assert result == {
        "collections": [COLLECTION, {"id": "second", "name": "Second"}],
        "next_pagination_token": "opaque+/= next",
    }
    assert len(requests) == 1
    assert (requests[0].method, requests[0].url.path) == ("GET", "/v1/collections")
    assert dict(requests[0].url.params) == {
        "pageSize": "3",
        "paginationToken": "opaque+/= cursor",
        **({"projectId": project} if project else {}),
    }


@pytest.mark.parametrize("token", [None, ""])
def test_empty_collection_page_is_valid_and_final(adapter, token):
    requests, handler = recorder(
        httpx.Response(200, json={"collections": [], "nextPaginationToken": token})
    )
    assert adapter(handler).collection_page() == {
        "collections": [],
        "next_pagination_token": None,
    }
    assert dict(requests[0].url.params) == {"pageSize": "50"}


@pytest.mark.parametrize(
    "page",
    [
        {},
        {"collections": None},
        {"collections": [None]},
        {"collections": [{"id": ""}]},
        {"collections": [{"id": "bad/id"}]},
        {"collections": [{"id": "one"}, {"id": "one", "name": "conflict"}]},
        {"collections": [{"id": "one"}, {"id": "two"}]},
        {"collections": [], "nextPaginationToken": 1},
        {"collections": [], "nextPaginationToken": "cursor"},
    ],
)
def test_collection_page_rejects_malformed_or_repeated_pages(adapter, page):
    requests, handler = recorder(httpx.Response(200, json=page))
    with pytest.raises(AdapterError):
        adapter(handler).collection_page(page_size=1, pagination_token="cursor")
    assert len(requests) == 1


@pytest.mark.parametrize(
    "options",
    [
        {"page_size": 0},
        {"page_size": 101},
        {"page_size": True},
        {"page_size": 2.5},
        {"pagination_token": ""},
        {"pagination_token": 1},
    ],
)
def test_collection_page_rejects_invalid_options_before_dispatch(adapter, options):
    with pytest.raises(ValueError):
        adapter(deny).collection_page(**options)


def test_collection_read_requires_the_requested_identity(adapter):
    requests, handler = recorder(httpx.Response(200, json={"collection": COLLECTION}))
    client = adapter(handler, project_id="selected-project")
    assert client.collection("fixture-collection") == COLLECTION
    assert requests[0].url.path == "/v1/collections/fixture-collection"
    assert dict(requests[0].url.params) == {"projectId": "selected-project"}
    with pytest.raises(AdapterError, match="different collection"):
        client.collection("other-collection")
    with pytest.raises(ValueError):
        client.collection("bad/id")
    assert len(requests) == 2


@pytest.mark.parametrize("project", [None, "selected-project"])
def test_asset_records_return_requested_order_and_omit_missing_assets(adapter, project):
    first = {"id": "asset-a", "tags": ["hero"], "collectionIds": ["fixture-collection"]}
    second = {"id": "asset-b", "tags": [], "collectionIds": [], "futureField": 1}
    requests, handler = recorder(httpx.Response(200, json={"assets": [second, first, first]}))
    records = adapter(handler, project_id=project).asset_records(
        ["asset-a", "asset-missing", "asset-b", "asset-a"]
    )
    assert list(records) == ["asset-a", "asset-b"]
    assert records == {"asset-a": first, "asset-b": second}
    assert len(requests) == 1
    assert (requests[0].method, requests[0].url.path) == ("POST", "/v1/assets/get-bulk")
    assert json.loads(requests[0].content) == {"assetIds": ["asset-a", "asset-missing", "asset-b"]}
    assert dict(requests[0].url.params) == ({"projectId": project} if project else {})


def test_asset_records_accept_an_empty_result_and_absent_metadata(adapter):
    _, empty = recorder(httpx.Response(200, json={"assets": []}))
    assert adapter(empty).asset_records(["asset-a"]) == {}
    _, sparse = recorder(httpx.Response(200, json={"assets": [{"id": "asset-a", "tags": None}]}))
    assert adapter(sparse).asset_records(("asset-a",)) == {
        "asset-a": {"id": "asset-a", "tags": None}
    }


@pytest.mark.parametrize(
    "page",
    [
        {},
        {"assets": None},
        {"assets": [None]},
        {"assets": [{"id": "asset-other"}]},
        {"assets": [{"id": "asset-a"}, {"id": "asset-a", "tags": ["conflict"]}]},
        {"assets": [{"id": "asset-a", "tags": "hero"}]},
        {"assets": [{"id": "asset-a", "collectionIds": [1]}]},
    ],
)
def test_asset_records_reject_unrequested_or_malformed_records(adapter, page):
    with pytest.raises(AdapterError):
        adapter(lambda request: httpx.Response(200, json=page)).asset_records(["asset-a"])


@pytest.mark.parametrize(
    "asset_ids",
    [
        [],
        "asset-a",
        [None],
        ["bad/id"],
        [f"asset-{i}" for i in range(MAX_ASSET_RECORDS + 1)],
    ],
)
def test_asset_records_validate_ids_before_dispatch(adapter, asset_ids):
    with pytest.raises(ValueError):
        adapter(deny).asset_records(asset_ids)


@pytest.mark.parametrize("failure", [404, 503, "timeout"])
def test_failed_verification_read_is_a_sanitized_adapter_error(adapter, failure):
    def fail(request):
        if failure == "timeout":
            raise httpx.ReadTimeout(PRIVATE, request=request)
        return httpx.Response(failure, json={"error": PRIVATE})

    requests, handler = recorder(fail)
    with pytest.raises(AdapterError) as error:
        adapter(handler).asset_records(["asset-a"])
    assert not isinstance(error.value, (WriteRejected, WriteUncertain))
    assert PRIVATE not in str(error.value)
    assert len(requests) == 1


class FakeLibrary:
    """A stateful service that can apply a change and then lose the response."""

    def __init__(self, *, lose_response=False, conflict_on_existing=False):
        self.members = {"asset-a"}
        self.tags = {"asset-a": ["draft"], "asset-b": []}
        self.lose_response = lose_response
        self.conflict_on_existing = conflict_on_existing
        self.writes = []

    def __call__(self, request):
        if request.url.path == "/v1/assets/get-bulk":
            assets = [
                {
                    "id": identifier,
                    "tags": list(self.tags[identifier]),
                    "collectionIds": ["fixture-collection"] if identifier in self.members else [],
                }
                for identifier in json.loads(request.content)["assetIds"]
                if identifier in self.tags
            ]
            return httpx.Response(200, json={"assets": assets})
        self.writes.append((request.method, request.url.path))
        body = json.loads(request.content)
        if request.url.path.endswith("/tags"):
            current = self.tags["asset-b"]
            current.extend(tag for tag in body.get("add", []) if tag not in current)
        elif request.method == "PUT":
            if self.conflict_on_existing and set(body["assetIds"]) & self.members:
                return httpx.Response(409, json={"error": PRIVATE})
            self.members.update(body["assetIds"])
        else:
            self.members.difference_update(body["assetIds"])
        if self.lose_response:
            raise httpx.ReadTimeout(PRIVATE, request=request)
        return httpx.Response(200, json={"collection": COLLECTION})


def test_applied_then_lost_membership_is_reconciled_by_reading_back(adapter):
    service = FakeLibrary(lose_response=True)
    client = adapter(service)
    with pytest.raises(WriteUncertain):
        client.add_collection_assets("fixture-collection", ["asset-b"])
    records = client.asset_records(["asset-b"])
    assert records["asset-b"]["collectionIds"] == ["fixture-collection"]
    assert service.writes == [("PUT", "/v1/collections/fixture-collection/assets")]


def test_applied_then_lost_tag_change_is_reconciled_by_reading_back(adapter):
    service = FakeLibrary(lose_response=True)
    client = adapter(service)
    with pytest.raises(WriteUncertain):
        client.update_asset_tags("asset-b", add=["hero"])
    assert client.asset_records(["asset-b"])["asset-b"]["tags"] == ["hero"]
    assert service.writes == [("PUT", "/v1/assets/asset-b/tags")]


def test_conflict_on_existing_member_is_uncertain_and_read_back_shows_membership(adapter):
    # Re-adding a member has undocumented status behavior. A 409 is neither
    # success nor rejection here; the read shows the actual state.
    service = FakeLibrary(conflict_on_existing=True)
    client = adapter(service)
    with pytest.raises(WriteUncertain) as error:
        client.add_collection_assets("fixture-collection", ["asset-a"])
    assert error.value.status == 409
    assert client.asset_records(["asset-a"])["asset-a"]["collectionIds"] == ["fixture-collection"]
    assert len(service.writes) == 1


def test_removal_body_reaches_transport_and_is_verified_by_reading_back(adapter):
    service = FakeLibrary()
    client = adapter(service)
    assert client.remove_collection_assets("fixture-collection", ["asset-a"]) == COLLECTION
    assert client.asset_records(["asset-a"])["asset-a"]["collectionIds"] == []
    assert service.writes == [("DELETE", "/v1/collections/fixture-collection/assets")]
