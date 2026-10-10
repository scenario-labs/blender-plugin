# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Native Library organization text: dialog mapping, row summaries and review cards.

Review payloads come from the real shared reviews and commands against the
offline organization service, so the card text follows the projection MCP uses.
"""

import json
import socket

import pytest
from organization_service import PRIVATE, URL, OrganizationService, asset, collection

from scenario.core.api.sdk_adapter import MAX_TAG_CHANGES
from scenario.core.jobs.organization import (
    NOTICE,
    Operation,
    OrganizationCommands,
    OrganizationReviews,
    build_request,
    review_payload,
)
from scenario.core.jobs.store import JobScope
from scenario.core.ui import library_organization as organizing

SCOPE = JobScope(URL, "account", "project")
LONG = "x" * 200


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    def deny(*args, **kwargs):
        pytest.fail("Library organization tests must not open sockets")

    monkeypatch.setattr(socket.socket, "connect", deny)
    monkeypatch.setattr(socket, "create_connection", deny)


@pytest.fixture
def service():
    item = OrganizationService(
        assets=[
            asset("asset-a", name="Hero cup", tags=["ceramic"]),
            asset("asset-b", name="Teapot", collections=["props"]),
        ],
        collections=[collection("props", "Props")],
    )
    adapter = item.adapter()
    item.commands = OrganizationCommands(adapter)
    yield item
    adapter.close()


def review(service, operation, *, apply=False, faults=(), **arguments):
    """Return the shared JSON projection after preparing and, optionally, applying.

    ``faults`` are scripted only after the prepare read, so they hit the apply.
    """
    reviews = OrganizationReviews()
    request = build_request(SCOPE, operation, **arguments)
    review_id = reviews.open(request)
    reviews.prepared(review_id, service.commands.snapshot(request))
    if apply:
        for method, path, behavior in faults:
            service.fault(method, path, behavior)
        snapshot = reviews.begin_apply(review_id)
        reviews.finished(review_id, service.commands.execute(snapshot, lambda: None))
    return review_payload(reviews.status(review_id))


def texts(lines):
    return [text for text, _ in lines]


def joined(lines):
    return " ".join(texts(lines))


def assert_bounded(lines, width=organizing.WIDTH):
    for text, icon in lines:
        assert len(text) <= width, text
        assert isinstance(icon, str) and icon
    serialized = json.dumps(lines)
    for private in (PRIVATE, "cdn.example", "signature", "private-owner"):
        assert private not in serialized


def test_label_summary_counts_what_does_not_fit():
    assert organizing.label_summary("Tags: ", []) == ""
    assert organizing.label_summary("Tags: ", ["a", "b"]) == "Tags: a, b"
    values = [f"tag-{index}" for index in range(12)]
    text = organizing.label_summary("Tags: ", values, width=30)
    assert len(text) <= 30
    shown = text.removeprefix("Tags: ").rsplit(" +", 1)
    assert int(shown[1]) == 12 - len(shown[0].split(", "))
    # A single label longer than the width is clipped, keeping the count.
    text = organizing.label_summary("Tags: ", [LONG, "b"], width=30)
    assert len(text) <= 30 and text.endswith("… +1")
    assert organizing.label_summary("In 2 collections: ", [], more=2) == "In 2 collections: +2"


def test_row_summaries_name_loaded_collections_only():
    assert organizing.tags_summary([]) == "No tags"
    assert organizing.tags_summary(["雪", "héros"]) == "Tags: 雪, héros"
    assert organizing.membership_summary([], {}) == "In no collections"
    assert organizing.membership_summary(["props"], {}) == "In 1 collection"
    names = {"props": "Props", "sets": "Sets"}
    assert organizing.membership_summary(["props", "sets"], names) == (
        "In 2 collections: Props, Sets"
    )
    assert organizing.membership_summary(["props", "other"], names) == (
        "In 2 collections: Props +1"
    )
    assert len(organizing.membership_summary(["a"], {"a": LONG})) <= organizing.WIDTH


def test_connection_label_matches_the_studio_connection_page():
    assert organizing.connection_label(None) == "Project: API key default scope"
    assert organizing.connection_label("project-a") == "Project: project-a"
    assert len(organizing.connection_label(LONG)) <= organizing.WIDTH


@pytest.mark.parametrize(
    ("action", "fields", "expected"),
    [
        (
            "ADD",
            {"collection_id": "props"},
            ("add_to_collection", {"asset_ids": ["a"], "collection_id": "props"}),
        ),
        (
            "REMOVE",
            {"collection_id": "props"},
            ("remove_from_collection", {"asset_ids": ["a"], "collection_id": "props"}),
        ),
        (
            "ADD_TAGS",
            {"tags": " hero , 雪,,hero, prop "},
            ("update_tags", {"asset_ids": ["a"], "add_tags": ["hero", "雪", "prop"]}),
        ),
        (
            "REMOVE_TAGS",
            {"tags": "old"},
            ("update_tags", {"asset_ids": ["a"], "remove_tags": ["old"]}),
        ),
        (
            "CREATE",
            {"collection_name": "  Hero props "},
            ("create_collection", {"asset_ids": ["a"], "collection_name": "Hero props"}),
        ),
    ],
)
def test_dialog_choices_map_to_shared_prepare_arguments(action, fields, expected):
    operation, arguments = organizing.request_arguments(action, "a", **fields)
    assert (operation, arguments) == expected
    # The shared contract accepts exactly what the dialog produces.
    assert build_request(SCOPE, operation, **arguments).operation == Operation(operation)


@pytest.mark.parametrize(
    ("action", "fields", "message"),
    [
        ("ADD", {"collection_id": organizing.NO_COLLECTION}, "Load collections"),
        ("REMOVE", {"collection_id": ""}, "Load collections"),
        ("ADD_TAGS", {"tags": " , "}, "at least one tag"),
        ("ADD_TAGS", {"tags": "line\nbreak"}, "control"),
        ("ADD_TAGS", {"tags": LONG + "x"}, "at most 200"),
        (
            "REMOVE_TAGS",
            {"tags": ",".join(f"t{index}" for index in range(MAX_TAG_CHANGES + 1))},
            f"at most {MAX_TAG_CHANGES}",
        ),
        ("CREATE", {"collection_name": "   "}, "nonempty"),
        ("CREATE", {"collection_name": "bad‮name"}, "format"),
        ("RENAME", {}, "Choose an organization action"),
    ],
)
def test_invalid_dialog_choices_are_refused_with_safe_text(action, fields, message):
    with pytest.raises(ValueError, match=message):
        organizing.request_arguments(action, "a", **fields)


def test_dialog_problem_waits_for_typed_text_and_requires_loaded_collections():
    problem = organizing.dialog_problem
    common = {"collection_id": "props", "collection_name": "", "tags": ""}
    assert "Load collections" in problem("ADD", has_collections=False, **common)
    assert problem("ADD", has_collections=True, **common) == ""
    assert problem("ADD_TAGS", has_collections=False, **common) == ""
    assert problem("CREATE", has_collections=False, **common) == ""
    assert "control" in problem("ADD_TAGS", has_collections=False, **{**common, "tags": "a\tb"})
    assert problem("CREATE", has_collections=False, **{**common, "collection_name": "Ok"}) == ""


def test_card_actions_follow_the_review_phase():
    assert organizing.card_actions("READY") == ("APPLY", "DISCARD")
    assert organizing.card_actions("PREPARING") == ()
    assert organizing.card_actions("APPLYING") == ()
    for phase in ("UNCHANGED", "REJECTED", "FINISHED", "NOT_SENT", "EXPIRED", "UNAVAILABLE"):
        assert organizing.card_actions(phase) == ("DISMISS",)


def test_preparing_card_states_that_nothing_was_sent():
    reviews = OrganizationReviews()
    review_id = reviews.open(build_request(SCOPE, "update_tags", asset_ids=["a"], add_tags=["x"]))
    lines = organizing.review_lines(review_payload(reviews.status(review_id)))
    assert "Change tags" in texts(lines)
    assert "Project: project" in texts(lines)
    assert any("nothing has been sent" in text for text in texts(lines))
    assert_bounded(lines)


def test_ready_membership_card_shows_current_and_resulting_state(service):
    payload = review(service, "add_to_collection", asset_ids=["asset-a"], collection_id="props")
    lines = organizing.review_lines(payload)
    shown = texts(lines)
    assert shown[:3] == ["Add to collection", "Project: project", "Collection: Props"]
    assert "Hero cup" in shown
    assert "Now: not in this collection" in shown
    assert "Change: add to the collection" in shown
    assert "Apply sends 1 request once, with no retry" in shown
    assert "This review expires in 10 min" in shown
    assert "Blender Undo does not reverse them" in joined(organizing.review_lines(payload))
    assert ("DOT" in dict(lines).values()) and ("INFO" in dict(lines).values())
    assert_bounded(lines)
    removal = review(
        service, "remove_from_collection", asset_ids=["asset-b"], collection_id="props"
    )
    shown = texts(organizing.review_lines(removal))
    assert "Now: in this collection" in shown
    assert "Change: remove from the collection" in shown


def test_ready_tag_card_lists_only_the_differences(service):
    payload = review(
        service,
        "update_tags",
        asset_ids=["asset-a"],
        add_tags=["ceramic", "雪"],
        remove_tags=["old"],
    )
    shown = texts(organizing.review_lines(payload))
    assert "Add tags: ceramic, 雪" in shown
    assert "Remove tags: old" in shown
    assert "Now: Tags: ceramic" in shown
    assert "Change: add 雪" in shown


def test_unchanged_rejected_and_existing_name_cards_explain_without_actions(service):
    unchanged = review(service, "update_tags", asset_ids=["asset-a"], add_tags=["ceramic"])
    assert unchanged["phase"] == "UNCHANGED"
    lines = organizing.review_lines(unchanged)
    assert "Nothing to change; the assets are already organized this way" in joined(lines)
    assert next(icon for text, icon in lines if text.startswith("Nothing")) == "INFO"
    existing = review(service, "create_collection", collection_name="Props", asset_ids=["asset-a"])
    assert existing["phase"] == "REJECTED"
    lines = organizing.review_lines(existing, names={"props": "Props"})
    assert "New collection: Props" in texts(lines)
    assert "already exists; add the assets to it instead" in joined(lines)
    assert next(icon for text, icon in lines if text.startswith("A collection")) == "ERROR"
    assert ("Existing: Props", "NONE") in lines
    assert_bounded(lines)


def test_finished_cards_report_read_back_states(service):
    verified = review(service, "update_tags", apply=True, asset_ids=["asset-a"], add_tags=["new"])
    lines = organizing.review_lines(verified)
    assert ("Result: Verified by reading back", "CHECKMARK") in lines
    assert "Verified" in texts(lines)
    assert "Read back: Tags: ceramic, new" in texts(lines)
    assert_bounded(lines)
    unconfirmed = review(
        service,
        "update_tags",
        apply=True,
        faults=[
            ("PUT", "/v1/assets/asset-b/tags", "apply-timeout"),
            ("POST", "/v1/assets/get-bulk", 503),
        ],
        asset_ids=["asset-b"],
        add_tags=["x"],
    )
    lines = organizing.review_lines(unconfirmed)
    assert ("Result: Unconfirmed", "ERROR") in lines
    assert "Unconfirmed: refresh to inspect" in texts(lines)
    assert "nothing is resent automatically" in joined(lines)
    assert_bounded(lines)
    refused = review(
        service,
        "add_to_collection",
        apply=True,
        faults=[("PUT", "/v1/collections/props/assets", 403)],
        asset_ids=["asset-a"],
        collection_id="props",
    )
    lines = organizing.review_lines(refused)
    assert ("Result: Refused", "ERROR") in lines
    assert "Refused (HTTP 403)" in texts(lines)
    assert_bounded(lines)


def test_created_collection_outcome_is_named(service):
    payload = review(
        service,
        "create_collection",
        apply=True,
        collection_name="Hero props",
        asset_ids=["asset-a"],
    )
    shown = texts(organizing.review_lines(payload))
    assert "New collection: Hero props" in shown
    assert "New collection: Verified" in shown


def test_unknown_and_unavailable_reviews_never_claim_a_result():
    reviews = OrganizationReviews()
    request = build_request(SCOPE, "update_tags", asset_ids=["a"], add_tags=["x"])
    review_id = reviews.open(request)
    reviews.failed(review_id, "Could not read")
    lines = organizing.review_lines(review_payload(reviews.status(review_id)))
    assert ("Could not read", "ERROR") in lines
    unavailable = organizing.review_lines({"phase": "UNAVAILABLE", "message": "Gone; refresh"})
    assert unavailable == [("Gone; refresh", "ERROR")]
    assert organizing.review_lines({"phase": "UNAVAILABLE"}) == [
        ("This review is no longer available", "ERROR")
    ]


def test_long_untrusted_labels_wrap_or_clip_to_the_card_width(service):
    name = "N" * 200
    service.collections["long"] = collection("long", name)
    service.assets["asset-a"]["name"] = "A" * 200
    payload = review(
        service, "update_tags", asset_ids=["asset-a"], add_tags=["t" * 200, "雪" * 120]
    )
    lines = organizing.review_lines(payload)
    assert_bounded(lines)
    payload = review(service, "add_to_collection", asset_ids=["asset-a"], collection_id="long")
    lines = organizing.review_lines(payload)
    assert_bounded(lines)
    # The no-credit, no-undo notice is wrapped, never clipped.
    joined = " ".join(text for text, icon in lines)
    assert " ".join(NOTICE.split()) in " ".join(joined.split())


def test_not_sent_card_says_nothing_was_sent(service):
    reviews = OrganizationReviews()
    request = build_request(SCOPE, "update_tags", asset_ids=["asset-a"], add_tags=["x"])
    review_id = reviews.open(request)
    reviews.prepared(review_id, service.commands.snapshot(request))
    reviews.begin_apply(review_id)
    reviews.not_sent(review_id, "Online access is disabled")
    lines = organizing.review_lines(review_payload(reviews.status(review_id)))
    assert ("Online access is disabled", "ERROR") in lines
    assert "Nothing was sent; prepare the change again when ready" in joined(lines)
    assert organizing.card_actions("NOT_SENT") == ("DISMISS",)
    assert_bounded(lines)
