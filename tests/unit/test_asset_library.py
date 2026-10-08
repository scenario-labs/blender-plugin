# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Asset library adapter contracts with the pinned SDK and no external transport."""

import json

import httpx
import pytest

from scenario.core.api.sdk_adapter import AdapterError, Credentials, SDKAdapter


def client(response, calls, **options):
    def respond(request):
        calls.append(request)
        return httpx.Response(200, json=response)

    return SDKAdapter(
        Credentials("fixture-key", "fixture-secret"),
        online=lambda: True,
        transport=httpx.MockTransport(respond),
        **options,
    )


def test_asset_page_preserves_project_and_filter_without_following_cursor():
    calls = []
    with client(
        {"assets": [{"id": "fixture-asset"}], "nextPaginationToken": "next"},
        calls,
        project_id="fixture-project",
    ) as api:
        page = api.asset_page(page_size=2, collection_id="fixture-collection")
    assert page == {"assets": [{"id": "fixture-asset"}], "next_pagination_token": "next"}
    assert len(calls) == 1
    assert dict(calls[0].url.params) == {
        "pageSize": "2",
        "collectionId": "fixture-collection",
        "projectId": "fixture-project",
    }


@pytest.mark.parametrize(
    "page",
    [
        {},
        {"assets": {}},
        {"assets": [None]},
        {"assets": [{"id": "bad/id"}]},
        {"assets": [{"id": "one"}, {"id": "two"}]},
    ],
)
def test_malformed_or_oversized_page_is_rejected(page):
    with client(page, []) as api, pytest.raises(AdapterError):
        api.asset_page(page_size=1)


def test_conflicting_duplicates_and_repeated_cursor_are_rejected():
    with (
        client({"assets": [{"id": "same", "name": "a"}, {"id": "same", "name": "b"}]}, []) as api,
        pytest.raises(AdapterError, match="conflicting"),
    ):
        api.asset_page()
    with (
        client({"assets": [], "nextPaginationToken": "repeat"}, []) as api,
        pytest.raises(AdapterError, match="cursor"),
    ):
        api.asset_page(pagination_token="repeat")


def test_search_offsets_count_raw_hits_before_deduplication():
    calls = []
    with client(
        {"hits": [{"id": "same"}, {"id": "same"}], "offset": 5, "estimatedTotalHits": 20},
        calls,
        project_id="fixture-project",
    ) as api:
        result = api.search_assets("cup", public=True, limit=2, offset=5)
    assert result == {"assets": [{"id": "same"}], "next_offset": 7, "estimated_total": 20}
    assert json.loads(calls[0].content) == {"query": "cup", "public": True, "limit": 2, "offset": 5}
    assert dict(calls[0].url.params) == {"projectId": "fixture-project"}


@pytest.mark.parametrize(
    "page",
    [
        {"hits": [], "estimatedTotalHits": True},
        {"hits": [], "estimatedTotalHits": -1},
        {"hits": [], "offset": 8},
        {"hits": [], "offset": False},
    ],
)
def test_search_rejects_invalid_pagination(page):
    with client(page, []) as api, pytest.raises(AdapterError):
        api.search_assets("cup")


@pytest.mark.parametrize(
    "options", [{"limit": True}, {"offset": -1}, {"public": "false"}, {"limit": 101}]
)
def test_invalid_search_options_make_no_request(options):
    calls = []
    with client({}, calls) as api, pytest.raises(ValueError):
        api.search_assets("cup", **options)
    assert not calls


def test_empty_or_unknown_total_has_bounded_explicit_continuation():
    with client({"hits": [], "estimatedTotalHits": 100}, []) as api:
        assert api.search_assets("cup")["next_offset"] is None
    with client({"hits": [{"id": "one"}]}, []) as api:
        assert api.search_assets("cup", limit=1, offset=4)["next_offset"] == 5
    with client({"hits": [{"id": "one"}], "offset": None}, []) as api:
        assert api.search_assets("cup", limit=1, offset=4)["next_offset"] == 5


def test_read_errors_are_sanitized_and_not_retried():
    calls = []

    def respond(request):
        calls.append(request)
        return httpx.Response(503, json={"message": "private server message"})

    with SDKAdapter(
        Credentials("fixture-key", "fixture-secret"),
        online=lambda: True,
        transport=httpx.MockTransport(respond),
    ) as api:
        with pytest.raises(AdapterError, match="HTTP 503") as caught:
            api.search_assets("cup")
    assert "private server" not in str(caught.value)
    assert len(calls) == 1
