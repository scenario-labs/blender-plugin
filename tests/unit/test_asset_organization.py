# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Shared organization reviews: guarded single writes, read-back and review state.

Everything runs offline against the real SDK through a stateful MockTransport.
The create dedup and no-replay cases are adapted from Scenario Blender Studio
``tests/test_organization.py`` at e2b0277064f0c502d46524fba1d006d0ac83f846
(original author Emmanuel de Maistre), moved from its remote-MCP catalog fake
to the SDK adapter.
"""

import json
import socket

import httpx
import pytest
from organization_service import (
    ALREADY_MEMBERS,
    PRIVATE,
    URL,
    OrganizationService,
    asset,
    collection,
)

from scenario.core.api.sdk_adapter import MAX_COLLECTION_ASSETS, MAX_TAG_CHANGES
from scenario.core.jobs.organization import (
    NOTICE,
    DuplicateCollection,
    Operation,
    OrganizationBusy,
    OrganizationCommands,
    OrganizationError,
    OrganizationNotSent,
    OrganizationRequest,
    OrganizationReviews,
    Outcome,
    Phase,
    ResultState,
    ReviewUnavailable,
    build_request,
    collection_summary,
    normalize_tags,
    parse_tags,
    review_payload,
)
from scenario.core.jobs.store import JobScope

SCOPE = JobScope(URL, "account", "project")


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    def deny(*args, **kwargs):
        pytest.fail("Organization tests must not open sockets")

    monkeypatch.setattr(socket.socket, "connect", deny)
    monkeypatch.setattr(socket.socket, "connect_ex", deny)
    monkeypatch.setattr(socket, "create_connection", deny)


@pytest.fixture
def service():
    item = OrganizationService(
        assets=[
            asset("asset-a"),
            asset("asset-b", tags=["hero"], collections=["props"]),
            asset("asset-c"),
        ],
        collections=[collection("props", "Props")],
    )
    adapters = []

    def adapter(**options):
        value = item.adapter(**options)
        adapters.append(value)
        return value

    item.make = adapter
    yield item
    for value in adapters:
        value.close()


def commands(service, **options):
    return OrganizationCommands(service.make(**options))


def request(operation, **arguments):
    return build_request(SCOPE, operation, **arguments)


def guarded(events=None, fail_at=None):
    calls = []

    def guard():
        calls.append(len(calls))
        if events is not None:
            events.append("guard")
        if fail_at is not None and len(calls) >= fail_at:
            raise RuntimeError("inactive")

    guard.calls = calls
    return guard


def states(result):
    return [(outcome.asset_id, outcome.state) for outcome in result.outcomes]


def test_tags_and_names_are_stripped_deduplicated_and_kept_in_order():
    built = request(
        "update_tags",
        asset_ids=["asset-a"],
        add_tags=[" hero ", "prop", "hero", "été"],
        remove_tags=("old",),
    )
    assert built.add_tags == ("hero", "prop", "été")
    assert built.remove_tags == ("old",)
    assert parse_tags(" hero, ,prop ,hero") == ("hero", "prop")
    assert normalize_tags(None) == ()
    created = request("create_collection", collection_name="  Hero props ")
    assert created.collection_name == "Hero props"
    assert created.asset_ids == ()


def test_tag_limit_errors_name_the_limit_each_check_enforces(service):
    assert normalize_tags(["hero"] * 200) == ("hero",)
    assert parse_tags(",".join(["hero"] * 200)) == ("hero",)
    raw = "Use at most 200 tag entries, counting duplicates"
    with pytest.raises(ValueError) as exceeded:
        normalize_tags(["hero"] * 201)
    assert str(exceeded.value) == raw
    with pytest.raises(ValueError, match="^Use at most 200 tag entries"):
        parse_tags(",".join(["hero"] * 201))
    with pytest.raises(ValueError, match="^Use at most 200 tag entries"):
        request("update_tags", asset_ids=["asset-a"], remove_tags=["old"] * 201)
    unique = f"Use at most {MAX_TAG_CHANGES} tags in one change"
    with pytest.raises(ValueError) as exceeded:
        normalize_tags([f"t{i}" for i in range(MAX_TAG_CHANGES + 1)] * 2)
    assert str(exceeded.value) == unique
    assert service.requests == []


@pytest.mark.parametrize(
    "operation,arguments",
    [
        ("rename", {"asset_ids": ["asset-a"]}),
        ("update_tags", {"asset_ids": ["asset-a"], "add_tags": ["a,b"]}),
        ("update_tags", {"asset_ids": ["asset-a"], "add_tags": ["x"], "remove_tags": ["x"]}),
        ("update_tags", {"asset_ids": ["asset-a"]}),
        ("update_tags", {"asset_ids": ["asset-a"], "add_tags": "hero"}),
        ("update_tags", {"asset_ids": ["asset-a"], "add_tags": [""]}),
        ("update_tags", {"asset_ids": ["asset-a"], "add_tags": ["bad\ntag"]}),
        ("update_tags", {"asset_ids": ["asset-a"], "add_tags": ["‮hidden"]}),
        ("update_tags", {"asset_ids": ["asset-a"], "add_tags": ["x" * 201]}),
        (
            "update_tags",
            {"asset_ids": ["asset-a"], "add_tags": [f"t{i}" for i in range(MAX_TAG_CHANGES + 1)]},
        ),
        ("update_tags", {"asset_ids": ["asset-a"], "add_tags": ["x"], "collection_id": "props"}),
        ("add_to_collection", {"asset_ids": ["asset-a"]}),
        ("add_to_collection", {"asset_ids": [], "collection_id": "props"}),
        ("add_to_collection", {"asset_ids": "asset-a", "collection_id": "props"}),
        ("add_to_collection", {"asset_ids": ["asset-a", "asset-a"], "collection_id": "props"}),
        ("add_to_collection", {"asset_ids": ["a/b"], "collection_id": "props"}),
        ("add_to_collection", {"asset_ids": [" asset-a"], "collection_id": "props"}),
        ("add_to_collection", {"asset_ids": ["asset-a"], "collection_id": "x?y"}),
        (
            "add_to_collection",
            {"asset_ids": ["asset-a"], "collection_id": "props", "add_tags": ["x"]},
        ),
        (
            "add_to_collection",
            {
                "asset_ids": [f"asset-{i}" for i in range(MAX_COLLECTION_ASSETS + 1)],
                "collection_id": "props",
            },
        ),
        ("remove_from_collection", {"asset_ids": ["asset-a"], "collection_name": "Props"}),
        ("create_collection", {"asset_ids": ["asset-a"]}),
        ("create_collection", {"collection_name": "  "}),
        ("create_collection", {"collection_name": "Props", "collection_id": "props"}),
    ],
)
def test_invalid_requests_are_refused_before_any_request(service, operation, arguments):
    with pytest.raises(ValueError):
        request(operation, **arguments)
    assert service.requests == []


def test_requests_cannot_be_constructed_unnormalized():
    with pytest.raises(ValueError, match="operation"):
        OrganizationRequest(SCOPE, "update_tags", ("asset-a",), add_tags=("x",))
    with pytest.raises(ValueError, match="normalized"):
        OrganizationRequest(SCOPE, Operation.UPDATE_TAGS, ("asset-a",), add_tags=(" x",))
    with pytest.raises(ValueError, match="normalized"):
        OrganizationRequest(SCOPE, Operation.CREATE_COLLECTION, collection_name=" x")
    with pytest.raises(ValueError, match="scope"):
        OrganizationRequest(object(), Operation.CREATE_COLLECTION, collection_name="x")


def test_snapshot_reads_current_state_without_writing(service):
    built = request(
        "add_to_collection", asset_ids=["asset-a", "asset-b", "asset-c"], collection_id="props"
    )
    snapshot = commands(service).snapshot(built)
    assert snapshot.problem == ""
    assert snapshot.collection_name == "Props"
    assert [change.membership for change in snapshot.changes] == [True, False, True]
    assert snapshot.request_count == 1
    assert service.writes == []
    assert [entry[:2] for entry in service.requests] == [
        ("POST", "/v1/assets/get-bulk"),
        ("GET", "/v1/collections/props"),
    ]


def test_missing_assets_reject_the_review(service):
    snapshot = commands(service).snapshot(
        request("update_tags", asset_ids=["asset-a", "gone"], add_tags=["x"])
    )
    assert snapshot.missing == ("gone",)
    assert "1 of 2 assets were not found" in snapshot.problem
    assert snapshot.request_count == 0
    with pytest.raises(OrganizationNotSent):
        commands(service).execute(snapshot, guarded())
    assert service.writes == []


def test_add_sends_one_request_for_changed_assets_then_verifies(service):
    owner = commands(service)
    snapshot = owner.snapshot(
        request(
            "add_to_collection", asset_ids=["asset-a", "asset-b", "asset-c"], collection_id="props"
        )
    )
    guard = guarded()
    result = owner.execute(snapshot, guard)
    assert service.writes == [
        ("PUT", "/v1/collections/props/assets", {"assetIds": ["asset-a", "asset-c"]})
    ]
    assert len(guard.calls) == 1
    assert result.state == ResultState.VERIFIED
    assert result.requests_sent == 1
    assert all(outcome.state == Outcome.VERIFIED for outcome in result.outcomes)
    assert service.requests[-1][:2] == ("POST", "/v1/assets/get-bulk")


def test_acknowledged_removal_without_effect_is_unconfirmed(service):
    owner = commands(service)
    snapshot = owner.snapshot(
        request("remove_from_collection", asset_ids=["asset-b"], collection_id="props")
    )
    # A 2xx whose DELETE body an intermediary dropped changes nothing.
    service.fault("DELETE", "/v1/collections/props/assets", "ack-only")
    result = owner.execute(snapshot, guarded())
    assert states(result) == [("asset-b", Outcome.UNCONFIRMED)]
    assert result.state == ResultState.UNCONFIRMED
    assert len(service.writes) == 1


def test_guard_runs_before_each_write_and_never_after(service):
    owner = commands(service)
    snapshot = owner.snapshot(
        request("update_tags", asset_ids=["asset-a", "asset-b", "asset-c"], add_tags=["new"])
    )
    service.events.clear()
    result = owner.execute(snapshot, guarded(service.events))
    assert service.events == [
        "guard",
        "PUT /v1/assets/asset-a/tags",
        "guard",
        "PUT /v1/assets/asset-b/tags",
        "guard",
        "PUT /v1/assets/asset-c/tags",
        "POST /v1/assets/get-bulk",
    ]
    assert result.state == ResultState.VERIFIED


def test_deactivation_between_tag_writes_leaves_the_rest_unsent(service):
    owner = commands(service)
    snapshot = owner.snapshot(
        request("update_tags", asset_ids=["asset-a", "asset-b", "asset-c"], add_tags=["new"])
    )
    result = owner.execute(snapshot, guarded(fail_at=2))
    assert len(service.writes) == 1
    assert states(result) == [
        ("asset-a", Outcome.VERIFIED),
        ("asset-b", Outcome.NOT_SENT),
        ("asset-c", Outcome.NOT_SENT),
    ]
    assert result.state == ResultState.PARTIAL
    assert "connection changed" in result.message


def test_guard_failure_before_any_write_sends_nothing(service):
    owner = commands(service)
    snapshot = owner.snapshot(request("update_tags", asset_ids=["asset-a"], add_tags=["new"]))
    with pytest.raises(OrganizationNotSent, match="connection changed; nothing was sent"):
        owner.execute(snapshot, guarded(fail_at=1))
    assert service.writes == []


def test_definite_rejection_continues_with_independent_assets(service):
    owner = commands(service)
    snapshot = owner.snapshot(
        request("update_tags", asset_ids=["asset-a", "asset-b", "asset-c"], add_tags=["new"])
    )
    service.fault("PUT", "/v1/assets/asset-b/tags", 403)
    result = owner.execute(snapshot, guarded())
    assert len(service.writes) == 3
    assert states(result) == [
        ("asset-a", Outcome.VERIFIED),
        ("asset-b", Outcome.REJECTED),
        ("asset-c", Outcome.VERIFIED),
    ]
    assert result.outcomes[1].status == 403
    assert result.state == ResultState.PARTIAL
    assert "cannot change this asset or collection (HTTP 403)" in result.message
    assert PRIVATE not in result.message


def test_first_uncertain_write_stops_later_writes(service):
    owner = commands(service)
    snapshot = owner.snapshot(
        request("update_tags", asset_ids=["asset-a", "asset-b", "asset-c"], add_tags=["new"])
    )
    service.fault("PUT", "/v1/assets/asset-b/tags", 503)
    result = owner.execute(snapshot, guarded())
    assert [entry[1] for entry in service.writes] == [
        "/v1/assets/asset-a/tags",
        "/v1/assets/asset-b/tags",
    ]
    assert states(result) == [
        ("asset-a", Outcome.VERIFIED),
        ("asset-b", Outcome.UNCONFIRMED),
        ("asset-c", Outcome.NOT_SENT),
    ]
    assert result.state == ResultState.UNCONFIRMED
    assert "nothing is resent" in result.message


def test_applied_then_lost_response_is_verified_without_a_second_write(service):
    owner = commands(service)
    snapshot = owner.snapshot(
        request("add_to_collection", asset_ids=["asset-a"], collection_id="props")
    )
    service.fault("PUT", "/v1/collections/props/assets", "apply-timeout")
    result = owner.execute(snapshot, guarded())
    assert len(service.writes) == 1
    assert states(result) == [("asset-a", Outcome.VERIFIED)]
    assert result.state == ResultState.VERIFIED


def test_failed_verification_read_is_unverified(service):
    owner = commands(service)
    snapshot = owner.snapshot(request("update_tags", asset_ids=["asset-a"], remove_tags=["x"]))
    assert snapshot.request_count == 0  # the tag is already absent
    snapshot = owner.snapshot(request("update_tags", asset_ids=["asset-b"], remove_tags=["hero"]))
    service.fault("POST", "/v1/assets/get-bulk", 500)
    result = owner.execute(snapshot, guarded())
    assert states(result) == [("asset-b", Outcome.UNVERIFIED)]
    assert result.state == ResultState.UNCONFIRMED
    assert len(service.writes) == 1


def test_refused_membership_without_a_read_back_is_not_called_definite(service):
    owner = commands(service)
    snapshot = owner.snapshot(
        request("add_to_collection", asset_ids=["asset-a", "asset-c"], collection_id="props")
    )
    service.fault("PUT", "/v1/collections/props/assets", 403)
    service.fault("POST", "/v1/assets/get-bulk", 500)
    result = owner.execute(snapshot, guarded())
    assert {outcome.state for outcome in result.outcomes} == {Outcome.UNVERIFIED}
    assert result.state == ResultState.UNCONFIRMED


def test_refused_membership_confirmed_by_read_back_is_rejected(service):
    owner = commands(service)
    snapshot = owner.snapshot(
        request("add_to_collection", asset_ids=["asset-a"], collection_id="props")
    )
    service.fault("PUT", "/v1/collections/props/assets", 404)
    result = owner.execute(snapshot, guarded())
    assert states(result) == [("asset-a", Outcome.REJECTED)]
    assert result.state == ResultState.REJECTED
    assert "Asset or collection not found in the selected connection" in result.message
    assert PRIVATE not in result.message
    assert result.outcomes[0].status == 404


ADD_PATH = "/v1/collections/props/assets"


def add_writes(service):
    return [body["assetIds"] for method, path, body in service.writes if path == ADD_PATH]


def join_props(service, *identifiers):
    """Another client adds these assets to the collection."""
    for identifier in identifiers:
        service.assets[identifier]["collectionIds"].append("props")


def test_synthetic_service_refuses_adds_as_one_transaction(service):
    # The fake models the observed backend: a re-add or more than 49 IDs is a
    # 400 that writes nothing; it never silently accepts a re-add.
    client = httpx.Client(transport=httpx.MockTransport(service), base_url=URL)
    params = {"projectId": "project"}
    refused = client.put(
        "/collections/props/assets", params=params, json={"assetIds": ["asset-c", "asset-b"]}
    )
    assert refused.status_code == 400
    assert refused.json()["reason"] == ALREADY_MEMBERS
    assert service.assets["asset-c"]["collectionIds"] == []
    many = [f"asset-{index}" for index in range(50)]
    too_many = client.put("/collections/props/assets", params=params, json={"assetIds": many})
    assert too_many.status_code == 400
    assert service.assets["asset-a"]["collectionIds"] == []
    client.close()


def test_member_added_after_review_is_skipped_and_the_rest_sent_again(service):
    owner = commands(service)
    snapshot = owner.snapshot(
        request("add_to_collection", asset_ids=["asset-a", "asset-c"], collection_id="props")
    )
    assert snapshot.request_count == 1
    join_props(service, "asset-a")
    service.events.clear()
    result = owner.execute(snapshot, guarded(service.events))
    assert add_writes(service) == [["asset-a", "asset-c"], ["asset-c"]]
    assert service.events == [
        "guard",
        f"PUT {ADD_PATH}",
        "POST /v1/assets/get-bulk",
        "guard",
        f"PUT {ADD_PATH}",
        "POST /v1/assets/get-bulk",
    ]
    assert states(result) == [("asset-a", Outcome.VERIFIED), ("asset-c", Outcome.VERIFIED)]
    assert result.state == ResultState.VERIFIED
    assert result.requests_sent == 2
    assert result.message.endswith(
        "Already in the collection: 1 of 2 assets; the rest were sent again"
    )
    assert ALREADY_MEMBERS not in result.message
    assert PRIVATE not in result.message


def test_every_target_already_a_member_sends_no_further_write(service):
    owner = commands(service)
    snapshot = owner.snapshot(
        request("add_to_collection", asset_ids=["asset-a", "asset-c"], collection_id="props")
    )
    join_props(service, "asset-a", "asset-c")
    guard = guarded()
    result = owner.execute(snapshot, guard)
    assert add_writes(service) == [["asset-a", "asset-c"]]
    assert len(guard.calls) == 1
    assert result.state == ResultState.VERIFIED
    assert result.requests_sent == 1
    assert result.message.endswith("All 2 assets were already in the collection")
    assert "sent again" not in result.message


def test_one_asset_already_added_is_verified_with_one_request(service):
    # The native Library reviews one asset: a refusal it explains needs no resend.
    owner = commands(service)
    snapshot = owner.snapshot(
        request("add_to_collection", asset_ids=["asset-c"], collection_id="props")
    )
    join_props(service, "asset-c")
    result = owner.execute(snapshot, guarded())
    assert add_writes(service) == [["asset-c"]]
    assert states(result) == [("asset-c", Outcome.VERIFIED)]
    assert result.outcomes[0].status is None
    assert result.requests_sent == 1
    assert result.message == (
        "Scenario confirmed every change. The asset was already in the collection"
    )


def test_another_add_refusal_reason_is_not_sent_again(service):
    owner = commands(service)
    snapshot = owner.snapshot(
        request("add_to_collection", asset_ids=["asset-a", "asset-c"], collection_id="props")
    )
    service.fault("PUT", ADD_PATH, 400)
    result = owner.execute(snapshot, guarded())
    assert len(add_writes(service)) == 1
    assert states(result) == [("asset-a", Outcome.REJECTED), ("asset-c", Outcome.REJECTED)]
    assert {outcome.status for outcome in result.outcomes} == {400}
    assert result.state == ResultState.REJECTED
    assert result.requests_sent == 1
    assert "rejected this organization change (HTTP 400)" in result.message


def test_already_member_refusal_the_read_back_cannot_explain_is_kept(service):
    owner = commands(service)
    snapshot = owner.snapshot(
        request("add_to_collection", asset_ids=["asset-a", "asset-c"], collection_id="props")
    )
    service.fault("PUT", ADD_PATH, "already-members")
    result = owner.execute(snapshot, guarded())
    assert len(add_writes(service)) == 1
    assert states(result) == [("asset-a", Outcome.REJECTED), ("asset-c", Outcome.REJECTED)]
    assert result.state == ResultState.REJECTED
    assert result.requests_sent == 1
    assert "some are already in the collection (HTTP 400)" in result.message
    assert PRIVATE not in result.message


def test_failed_read_after_an_already_member_refusal_sends_nothing_more(service):
    owner = commands(service)
    snapshot = owner.snapshot(
        request("add_to_collection", asset_ids=["asset-a", "asset-c"], collection_id="props")
    )
    join_props(service, "asset-a")
    service.fault("POST", "/v1/assets/get-bulk", 500)
    result = owner.execute(snapshot, guarded())
    assert len(add_writes(service)) == 1
    assert states(result) == [("asset-a", Outcome.VERIFIED), ("asset-c", Outcome.REJECTED)]
    assert result.state == ResultState.PARTIAL
    assert result.requests_sent == 1
    assert "some are already in the collection (HTTP 400)" in result.message


def test_repeated_concurrent_adds_stop_after_three_requests():
    service = OrganizationService(
        assets=[asset(f"asset-{name}") for name in "acde"],
        collections=[collection("props", "Props")],
    )
    racing = ["asset-a", "asset-c", "asset-d"]

    def other_client(request):
        if request.method == "PUT" and racing:
            join_props(service, racing.pop(0))

    owner = OrganizationCommands(service.adapter())
    snapshot = owner.snapshot(
        request(
            "add_to_collection",
            asset_ids=["asset-a", "asset-c", "asset-d", "asset-e"],
            collection_id="props",
        )
    )
    service.gate = other_client
    result = owner.execute(snapshot, guarded())
    assert add_writes(service) == [
        ["asset-a", "asset-c", "asset-d", "asset-e"],
        ["asset-c", "asset-d", "asset-e"],
        ["asset-d", "asset-e"],
    ]
    assert result.requests_sent == 3
    assert states(result) == [
        ("asset-a", Outcome.VERIFIED),
        ("asset-c", Outcome.VERIFIED),
        ("asset-d", Outcome.VERIFIED),
        ("asset-e", Outcome.REJECTED),
    ]
    assert result.state == ResultState.PARTIAL
    assert "after 3 requests" in result.message


def test_guard_failure_before_the_resend_stops_it(service):
    owner = commands(service)
    snapshot = owner.snapshot(
        request("add_to_collection", asset_ids=["asset-a", "asset-c"], collection_id="props")
    )
    join_props(service, "asset-a")
    guard = guarded(fail_at=2)
    result = owner.execute(snapshot, guard)
    assert len(add_writes(service)) == 1
    assert len(guard.calls) == 2
    assert states(result) == [("asset-a", Outcome.VERIFIED), ("asset-c", Outcome.REJECTED)]
    assert result.state == ResultState.PARTIAL
    assert result.requests_sent == 1
    assert "connection changed; later changes were not sent" in result.message
    assert result.message.endswith("Already in the collection: 1 of 2 assets")


def test_uncertain_resend_is_unconfirmed_and_never_sent_again(service):
    owner = commands(service)
    snapshot = owner.snapshot(
        request("add_to_collection", asset_ids=["asset-a", "asset-c"], collection_id="props")
    )
    join_props(service, "asset-a")
    service.fault("PUT", ADD_PATH, None, "timeout")
    result = owner.execute(snapshot, guarded())
    assert add_writes(service) == [["asset-a", "asset-c"], ["asset-c"]]
    assert states(result) == [("asset-a", Outcome.VERIFIED), ("asset-c", Outcome.UNCONFIRMED)]
    assert result.state == ResultState.UNCONFIRMED
    assert result.requests_sent == 2
    assert "nothing is resent" in result.message


def test_removal_is_never_sent_again_after_a_refusal(service):
    owner = commands(service)
    snapshot = owner.snapshot(
        request("remove_from_collection", asset_ids=["asset-b"], collection_id="props")
    )
    service.fault("DELETE", ADD_PATH, "already-members")
    result = owner.execute(snapshot, guarded())
    assert [entry[:2] for entry in service.writes] == [("DELETE", ADD_PATH)]
    assert states(result) == [("asset-b", Outcome.REJECTED)]
    assert result.requests_sent == 1


def test_online_access_off_sends_nothing(service):
    online = [True]
    owner = commands(service, online=lambda: online[0])
    snapshot = owner.snapshot(request("update_tags", asset_ids=["asset-a"], add_tags=["new"]))
    online[0] = False
    with pytest.raises(OrganizationNotSent, match="Online access is disabled"):
        owner.execute(snapshot, guarded())
    assert service.writes == []


def test_unready_snapshots_are_never_executed(service):
    owner = commands(service)
    unchanged = owner.snapshot(request("update_tags", asset_ids=["asset-b"], add_tags=["hero"]))
    assert unchanged.request_count == 0
    for snapshot in (unchanged, object()):
        with pytest.raises(OrganizationNotSent):
            owner.execute(snapshot, guarded())
    assert service.writes == []


# Adapted from Studio tests/test_organization.py at e2b0277:
# test_two_collection_requests_with_same_name_create_only_once.
def test_two_creates_with_the_same_name_send_only_one_post(service):
    owner = commands(service)
    built = request("create_collection", collection_name="Signal At Dawn")
    first = owner.snapshot(built)
    stale = owner.snapshot(built)
    result = owner.execute(first, guarded())
    assert result.state == ResultState.VERIFIED
    assert result.created_collection_id == "created-1"
    assert result.create_outcome == Outcome.VERIFIED
    # The second, already reviewed create finds the name before sending.
    with pytest.raises(DuplicateCollection) as refused:
        owner.execute(stale, guarded())
    assert refused.value.collection_ids == ("created-1",)
    again = owner.snapshot(built)
    assert again.existing_collection_ids == ("created-1",)
    assert again.problem and again.request_count == 0
    assert [entry[:2] for entry in service.writes] == [("POST", "/v1/collections")]


# Adapted from Studio test_existing_collection_is_reused_after_paginated_exact_name_search.
# Here the existing collection is refused and returned instead of silently reused.
def test_existing_name_on_a_later_page_refuses_create_and_returns_its_id():
    service = OrganizationService(
        collections=[
            collection("col_other", "Other"),
            collection("col_existing", "Signal At Dawn"),
        ],
        page_size=1,
    )
    with service.adapter() as adapter:
        owner = OrganizationCommands(adapter)
        built = request("create_collection", collection_name="Signal At Dawn")
        snapshot = owner.snapshot(built)
        assert snapshot.existing_collection_ids == ("col_existing",)
        assert "already exists" in snapshot.problem
        lists = [entry for entry in service.requests if entry[1] == "/v1/collections"]
        assert [entry[3].get("paginationToken") for entry in lists] == [None, "1"]
        assert all(entry[3]["pageSize"] == "100" for entry in lists)
        ready = OrganizationCommands(adapter)
        service.collections.pop("col_existing")
        stale = ready.snapshot(built)
        assert stale.request_count == 1
        service.collections["col_existing"] = collection("col_existing", "Signal At Dawn")
        with pytest.raises(DuplicateCollection) as refused:
            ready.execute(stale, guarded())
        assert refused.value.collection_ids == ("col_existing",)
    assert service.writes == []


# Adapted from Studio test_ambiguous_collection_create_is_not_replayed_when_listing_stays_empty.
def test_ambiguous_create_is_never_replayed(service):
    owner = commands(service)
    built = request("create_collection", collection_name="Signal At Dawn")
    first, stale = owner.snapshot(built), owner.snapshot(built)
    service.fault("POST", "/v1/collections", "timeout")
    result = owner.execute(first, guarded())
    assert result.state == ResultState.UNCONFIRMED
    assert result.create_outcome == Outcome.UNCONFIRMED
    assert result.created_collection_id is None
    with pytest.raises(OrganizationNotSent, match="unknown outcome"):
        owner.execute(stale, guarded())
    assert "unknown outcome" in owner.snapshot(built).problem
    assert [entry[:2] for entry in service.writes] == [("POST", "/v1/collections")]
    owner.reset()
    assert owner.snapshot(built).problem == ""


def test_uncertain_create_confirmed_by_lookup_continues_to_add(service):
    owner = commands(service)
    snapshot = owner.snapshot(
        request("create_collection", collection_name="Hero props", asset_ids=["asset-a"])
    )
    assert snapshot.request_count == 2
    service.fault("POST", "/v1/collections", "apply-timeout")
    result = owner.execute(snapshot, guarded())
    assert [entry[:2] for entry in service.writes] == [
        ("POST", "/v1/collections"),
        ("PUT", "/v1/collections/created-1/assets"),
    ]
    assert result.create_outcome == Outcome.VERIFIED
    assert result.created_collection_id == result.collection_id == "created-1"
    assert states(result) == [("asset-a", Outcome.VERIFIED)]
    assert result.state == ResultState.VERIFIED
    assert owner.snapshot(request("create_collection", collection_name="Other name")).problem == ""


def test_renamed_create_reconciles_by_id_and_does_not_add(service):
    owner = commands(service)
    snapshot = owner.snapshot(
        request("create_collection", collection_name="Hero Props", asset_ids=["asset-a"])
    )
    service.fault("POST", "/v1/collections", "rename")
    result = owner.execute(snapshot, guarded())
    assert [entry[:2] for entry in service.writes] == [("POST", "/v1/collections")]
    assert result.created_collection_id == "created-1"
    assert result.collection_id is None
    assert result.create_outcome == Outcome.UNCONFIRMED
    assert states(result) == [("asset-a", Outcome.NOT_SENT)]
    assert result.state == ResultState.UNCONFIRMED
    assert (
        "unknown outcome"
        in owner.snapshot(request("create_collection", collection_name="Hero Props")).problem
    )


def test_create_without_assets_is_verified_by_reading_it_back(service):
    owner = commands(service)
    result = owner.execute(
        owner.snapshot(request("create_collection", collection_name="Empty")), guarded()
    )
    assert result.state == ResultState.VERIFIED
    assert result.outcomes == ()
    assert service.requests[-1][:2] == ("GET", "/v1/collections/created-1")


def test_rejected_create_sends_no_membership_change(service):
    owner = commands(service)
    snapshot = owner.snapshot(
        request("create_collection", collection_name="Refused", asset_ids=["asset-a"])
    )
    service.fault("POST", "/v1/collections", 403)
    result = owner.execute(snapshot, guarded())
    assert result.create_outcome == Outcome.REJECTED
    assert result.create_status == 403
    assert states(result) == [("asset-a", Outcome.NOT_SENT)]
    assert result.state == ResultState.REJECTED
    assert len(service.writes) == 1


def test_bounded_lookup_refuses_create_instead_of_guessing():
    service = OrganizationService(
        collections=[collection(f"c{i}", f"Name {i}") for i in range(30)], page_size=1
    )
    with service.adapter() as adapter:
        owner = OrganizationCommands(adapter)
        with pytest.raises(OrganizationError, match="Too many collections"):
            owner.snapshot(request("create_collection", collection_name="Missing"))
    assert service.writes == []
    assert len(service.requests) == 20


class Clock:
    def __init__(self):
        self.now = 100.0

    def __call__(self):
        return self.now


def ready_review(service, reviews, built=None):
    built = built or request("update_tags", asset_ids=["asset-a"], add_tags=["new"])
    review_id = reviews.open(built)
    assert reviews.prepared(review_id, commands(service).snapshot(built))
    return review_id


def test_ready_reviews_expire_after_their_lifetime(service):
    clock = Clock()
    reviews = OrganizationReviews(ttl=600, clock=clock)
    review_id = ready_review(service, reviews)
    assert reviews.status(review_id).expires_in == 600
    clock.now += 599
    assert reviews.status(review_id).phase == Phase.READY
    clock.now += 1
    assert reviews.status(review_id).phase == Phase.EXPIRED
    with pytest.raises(ReviewUnavailable, match="expired"):
        reviews.begin_apply(review_id)


def test_apply_is_single_use_and_one_change_applies_at_a_time(service):
    reviews = OrganizationReviews()
    first, second = ready_review(service, reviews), ready_review(service, reviews)
    snapshot = reviews.begin_apply(first)
    assert reviews.status(first).phase == Phase.APPLYING
    with pytest.raises(OrganizationBusy):
        reviews.begin_apply(second)
    with pytest.raises(ReviewUnavailable):
        reviews.begin_apply(first)
    with pytest.raises(ReviewUnavailable, match="cannot be discarded"):
        reviews.discard(first)
    result = commands(service).execute(snapshot, guarded())
    reviews.finished(first, result)
    assert reviews.status(first).phase == Phase.FINISHED
    with pytest.raises(ReviewUnavailable):
        reviews.begin_apply(first)
    assert reviews.begin_apply(second) is not None
    reviews.abort_apply(second)
    assert reviews.status(second).phase == Phase.READY


def test_bounded_reviews_evict_only_finished_or_discarded_entries(service):
    reviews = OrganizationReviews(limit=2)
    built = request("update_tags", asset_ids=["asset-a"], add_tags=["new"])
    first, second = reviews.open(built), reviews.open(built)
    with pytest.raises(OrganizationBusy):
        reviews.open(built)
    reviews.discard(second)
    third = reviews.open(built)
    with pytest.raises(ReviewUnavailable):
        reviews.status(second)
    assert reviews.status(first).phase == Phase.PREPARING
    assert reviews.status(third).phase == Phase.PREPARING


def test_late_snapshot_for_a_discarded_review_is_ignored(service):
    reviews = OrganizationReviews()
    built = request("update_tags", asset_ids=["asset-a"], add_tags=["new"])
    review_id = reviews.open(built)
    reviews.discard(review_id)
    assert not reviews.prepared(review_id, commands(service).snapshot(built))
    assert reviews.status(review_id).phase == Phase.DISCARDED
    other = reviews.open(built)
    foreign = commands(service).snapshot(
        request("update_tags", asset_ids=["asset-c"], add_tags=["new"])
    )
    assert not reviews.prepared(other, foreign)
    assert reviews.status(other).phase == Phase.REJECTED


def test_prepare_outcomes_map_to_review_phases(service):
    reviews = OrganizationReviews()
    owner = commands(service)
    unchanged = request("update_tags", asset_ids=["asset-b"], add_tags=["hero"])
    review_id = reviews.open(unchanged)
    reviews.prepared(review_id, owner.snapshot(unchanged))
    assert reviews.status(review_id).phase == Phase.UNCHANGED
    missing = request("update_tags", asset_ids=["gone"], add_tags=["hero"])
    review_id = reviews.open(missing)
    reviews.prepared(review_id, owner.snapshot(missing))
    assert reviews.status(review_id).phase == Phase.REJECTED
    review_id = reviews.open(missing)
    reviews.failed(review_id, "Could not reach Scenario")
    assert reviews.status(review_id).message == "Could not reach Scenario"


def test_unknown_apply_outcome_is_unconfirmed_never_unsent(service):
    reviews = OrganizationReviews()
    review_id = ready_review(service, reviews)
    reviews.begin_apply(review_id)
    reviews.unknown(review_id, "Scenario organization failed")
    status = reviews.status(review_id)
    assert status.phase == Phase.FINISHED
    assert status.result is None
    assert "outcome is unknown" in status.message
    other = ready_review(service, reviews)
    reviews.begin_apply(other)
    reviews.not_sent(other, "Online access is disabled")
    assert reviews.status(other).phase == Phase.NOT_SENT


def test_mismatched_result_is_reported_as_unknown(service):
    reviews = OrganizationReviews()
    review_id = ready_review(service, reviews)
    other = request("update_tags", asset_ids=["asset-c"], add_tags=["new"])
    owner = commands(service)
    result = owner.execute(owner.snapshot(other), guarded())
    reviews.begin_apply(review_id)
    reviews.finished(review_id, result)
    status = reviews.status(review_id)
    assert status.phase == Phase.FINISHED and status.result is None


def test_review_payload_is_json_safe_and_omits_private_fields(service):
    reviews = OrganizationReviews()
    built = request("add_to_collection", asset_ids=["asset-a", "asset-b"], collection_id="props")
    review_id = ready_review(service, reviews, built)
    payload = review_payload(reviews.status(review_id))
    assert payload["phase"] == "READY"
    assert payload["collection_name"] == "Props"
    assert payload["request_count"] == 1
    assert payload["notice"] == NOTICE
    assert [item["in_collection"] for item in payload["assets"]] == [False, True]
    assert [item["change"]["membership"] for item in payload["assets"]] == ["add", None]
    snapshot = reviews.begin_apply(review_id)
    reviews.finished(review_id, commands(service).execute(snapshot, guarded()))
    payload = review_payload(reviews.status(review_id))
    assert payload["result"]["state"] == "VERIFIED"
    assert [item["in_collection"] for item in payload["result"]["outcomes"]] == [True, True]
    text = json.dumps(payload)
    for private in ("private-owner", "private-download", "signature", PRIVATE):
        assert private not in text


def test_collection_summary_omits_thumbnail_and_owner():
    summary = collection_summary(collection("props", "Props"))
    assert summary == {
        "collection_id": "props",
        "name": "Props",
        "asset_count": 0,
        "model_count": 0,
        "updated_at": "2026-01-01T00:00:00Z",
    }
    assert collection_summary({"id": "x", "assetCount": True, "updatedAt": 3}) == {
        "collection_id": "x",
        "name": "",
        "asset_count": None,
        "model_count": None,
        "updated_at": None,
    }
