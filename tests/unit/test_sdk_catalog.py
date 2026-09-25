# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Active catalog reads use real SDK serialization without service connections."""

import base64
import threading
from concurrent.futures import Future, ThreadPoolExecutor

import httpx
import pytest

from scenario.core.api.errors import ScenarioError
from scenario.core.api.sdk_adapter import Credentials, SDKAdapter
from scenario.core.api.sdk_catalog import SDKCatalog


def catalog(handler, **options):
    pools = []

    def factory(credentials, **kwargs):
        adapter = SDKAdapter(credentials, transport=httpx.MockTransport(handler), **kwargs)
        pools.append(adapter)
        return adapter

    return SDKCatalog(
        Credentials("selected-key", "selected-secret"),
        online=True,
        adapter_factory=factory,
        **options,
    ), pools


def test_catalog_pagination_and_normalization_preserve_selected_credentials(monkeypatch):
    monkeypatch.setenv("SCENARIO_CUSTOM_HEADERS", "Authorization: Bearer wrong")
    requests = []

    def respond(request):
        requests.append(request)
        if "paginationToken" not in request.url.params:
            return httpx.Response(
                200,
                json={
                    "models": [
                        {"id": "first", "name": "First", "capabilities": [{"type": "txt2img"}]}
                    ],
                    "nextPaginationToken": "page-two",
                },
            )
        return httpx.Response(200, json={"models": [{"id": "second"}]})

    context, pools = catalog(respond)
    records = context.fetch_list()
    assert [record.id for record in records] == ["first", "second"]
    assert records[0].capabilities == ("txt2img",)
    assert requests[0].url.params["privacy"] == "public"
    assert "status" not in requests[0].url.params
    assert requests[1].url.params["paginationToken"] == "page-two"
    auth = "Basic " + base64.b64encode(b"selected-key:selected-secret").decode()
    assert all(request.headers["Authorization"] == auth for request in requests)
    assert len(pools) == 1 and not pools[0]._closed
    records[0].raw["name"] = "Changed by caller"
    assert context.load_list_cached()[0].name == "First"
    context.close()
    assert pools[0]._closed


def test_detail_cache_isolated_between_connections_and_defensive_copies():
    requests = []

    def respond(request):
        requests.append(request)
        return httpx.Response(
            200, json={"model": {"id": "fixture", "inputs": [{"name": "prompt", "type": "string"}]}}
        )

    context, pools = catalog(respond)
    record = context.get("fixture")
    record.raw["inputs"][0]["name"] = "changed"
    assert context.get("fixture").parameters[0]["name"] == "prompt"
    assert len(requests) == 1
    context.get("fixture", refresh=True)
    assert len(requests) == 2
    assert len(pools) == 1 and not pools[0]._closed
    other, _ = catalog(respond)
    assert other.load_cached("fixture") is None
    assert other.load_list_cached() is None
    context.close()
    other.close()
    assert pools[0]._closed


def test_private_model_list_preserves_sdk_trained_filter():
    requests = []

    def respond(request):
        requests.append(request)
        return httpx.Response(200, json={"models": []})

    context, _ = catalog(respond)
    assert context.fetch_list("private") == []
    assert requests[0].url.params["privacy"] == "private"
    assert requests[0].url.params["status"] == "trained"
    context.close()


def test_permission_revocation_stops_next_page_and_does_not_cache_partial_list():
    requests = []

    def respond(request):
        requests.append(request)
        context.update_online(False)
        return httpx.Response(
            200, json={"models": [{"id": "first"}], "nextPaginationToken": "next"}
        )

    context, pools = catalog(respond)
    with pytest.raises(ScenarioError, match="Online access is disabled"):
        context.fetch_list()
    assert len(requests) == 1
    assert context.load_list_cached() is None
    assert not pools[0]._closed
    context.close()
    assert pools[0]._closed


def test_retirement_waits_for_read_cleanup_without_closing_pool_under_worker():
    started, release = threading.Event(), threading.Event()

    def respond(request):
        started.set()
        assert release.wait(5)
        return httpx.Response(200, json={"model": {"id": "fixture"}})

    context, pools = catalog(respond)
    with ThreadPoolExecutor(max_workers=2) as workers:
        read = workers.submit(context.get, "fixture")
        try:
            assert started.wait(5)
            context.close()
            assert not context.closed and not pools[0]._closed
            closing = workers.submit(context.close, wait=True)
            assert not closing.done()
        finally:
            release.set()
        with pytest.raises(ScenarioError, match="connection changed"):
            read.result(5)
        closing.result(5)
    assert context.closed and pools[0]._closed
    with pytest.raises(ScenarioError, match="connection changed"):
        context.get("fixture")


@pytest.mark.parametrize(
    "response",
    [
        httpx.Response(200, json={"model": {"id": "other"}}),
        httpx.Response(503, text="private service details"),
    ],
)
def test_failed_reads_are_safe_and_leave_no_cached_record(response):
    context, pools = catalog(lambda request: response)
    with pytest.raises(ScenarioError) as error:
        context.get("fixture")
    assert "private service details" not in str(error.value)
    assert context.load_cached("fixture") is None
    assert len(pools) == 1 and not pools[0]._closed
    context.close()
    assert pools[0]._closed


def test_concurrent_reads_reuse_pool_and_retirement_closes_after_last_reader():
    entered = {name: threading.Event() for name in ("first", "second")}
    release = {name: threading.Event() for name in entered}

    def respond(request):
        name = request.url.path.rsplit("/", 1)[-1]
        entered[name].set()
        assert release[name].wait(5)
        return httpx.Response(200, json={"model": {"id": name}})

    context, pools = catalog(respond)
    with ThreadPoolExecutor(max_workers=2) as workers:
        reads = {name: workers.submit(context.get, name) for name in entered}
        try:
            assert all(event.wait(5) for event in entered.values())
            assert len(pools) == 1
            context.close()
            assert not pools[0]._closed
            release["first"].set()
            with pytest.raises(ScenarioError, match="connection changed"):
                reads["first"].result(5)
            assert not pools[0]._closed and not context.closed
        finally:
            for event in release.values():
                event.set()
        with pytest.raises(ScenarioError, match="connection changed"):
            reads["second"].result(5)
    assert pools[0]._closed and context.closed


def test_same_model_read_is_shared_while_other_selected_model_can_finish(monkeypatch):
    entered, release, waiting = threading.Event(), threading.Event(), threading.Event()
    requests = []

    class ObservedFuture(Future):
        def result(self, timeout=None):
            waiting.set()
            return super().result(timeout)

    monkeypatch.setattr("scenario.core.api.sdk_catalog.Future", ObservedFuture)

    def respond(request):
        name = request.url.path.rsplit("/", 1)[-1]
        requests.append(name)
        if name == "warming":
            entered.set()
            assert release.wait(5)
        return httpx.Response(200, json={"model": {"id": name, "name": "Original"}})

    context, pools = catalog(respond)
    with ThreadPoolExecutor(max_workers=3) as workers:
        warmup = workers.submit(context.get, "warming")
        try:
            assert entered.wait(5)
            repeated = workers.submit(context.get, "warming", refresh=True)
            assert waiting.wait(5)
            selected = workers.submit(context.get, "selected", refresh=True)
            assert selected.result(5).id == "selected"
            assert not warmup.done()
            assert not repeated.done()
        finally:
            release.set()
        first, second = warmup.result(5), repeated.result(5)
        first.raw["name"] = "Caller changed"
        assert second.raw["name"] == "Original"
    assert requests.count("warming") == 1
    assert len(pools) == 1
    context.close()


@pytest.mark.parametrize("retire", [False, True])
def test_shared_failed_read_releases_waiters_and_allows_retry(monkeypatch, retire):
    entered, release, waiting = threading.Event(), threading.Event(), threading.Event()
    requests = []

    class ObservedFuture(Future):
        def result(self, timeout=None):
            waiting.set()
            return super().result(timeout)

    monkeypatch.setattr("scenario.core.api.sdk_catalog.Future", ObservedFuture)

    def respond(request):
        requests.append(request)
        if len(requests) == 1:
            entered.set()
            assert release.wait(5)
            return httpx.Response(503, text="private failure")
        return httpx.Response(200, json={"model": {"id": "fixture"}})

    context, pools = catalog(respond)
    with ThreadPoolExecutor(max_workers=2) as workers:
        leader = workers.submit(context.get, "fixture")
        try:
            assert entered.wait(5)
            waiter = workers.submit(context.get, "fixture", refresh=True)
            assert waiting.wait(5)
            if retire:
                context.close()
                assert not pools[0]._closed
        finally:
            release.set()
        for read in (leader, waiter):
            with pytest.raises(ScenarioError) as error:
                read.result(5)
            assert "private failure" not in str(error.value)
    assert len(requests) == 1
    assert context._model_reads == {}
    if retire:
        assert context.closed and pools[0]._closed
    else:
        assert context.get("fixture").id == "fixture"
        assert len(requests) == 2
        context.close()


def test_overlapping_lists_share_all_pages_but_not_privacy_scopes(monkeypatch):
    entered, release, waiting = (threading.Event() for _ in range(3))
    requests = []

    class ObservedFuture(Future):
        def result(self, timeout=None):
            waiting.set()
            return super().result(timeout)

    monkeypatch.setattr("scenario.core.api.sdk_catalog.Future", ObservedFuture)

    def respond(request):
        privacy = request.url.params["privacy"]
        cursor = request.url.params.get("paginationToken")
        requests.append((privacy, cursor))
        if privacy == "public" and cursor is None:
            entered.set()
            assert release.wait(5)
            return httpx.Response(
                200,
                json={
                    "models": [{"id": "first", "name": "First"}],
                    "nextPaginationToken": "second-page",
                },
            )
        return httpx.Response(200, json={"models": [{"id": privacy}]})

    context, pools = catalog(respond)
    with ThreadPoolExecutor(max_workers=3) as workers:
        leader = workers.submit(context.fetch_list)
        try:
            assert entered.wait(5)
            waiter = workers.submit(context.fetch_list)
            assert waiting.wait(5)
            private = workers.submit(context.fetch_list, "private")
            assert [record.id for record in private.result(5)] == ["private"]
            assert not leader.done() and not waiter.done()
        finally:
            release.set()
        first, second = leader.result(5), waiter.result(5)
        assert [record.id for record in first] == ["first", "public"]
        assert [record.id for record in second] == ["first", "public"]
        first[0].raw["name"] = "Changed"
        assert second[0].raw["name"] == "First"
        second[0].raw["name"] = "Changed again"
        assert context.load_list_cached()[0].name == "First"
    assert requests.count(("public", None)) == 1
    assert requests.count(("public", "second-page")) == 1
    assert requests.count(("private", None)) == 1
    assert len(pools) == 1
    # A later explicit refresh still goes to the service.
    context.fetch_list()
    assert requests.count(("public", None)) == 2
    context.close()


@pytest.mark.parametrize("outcome", ["failure", "retired", "offline", "invalid-record"])
def test_shared_list_failure_releases_waiters_without_publishing_partial_data(monkeypatch, outcome):
    entered, release, waiting = (threading.Event() for _ in range(3))
    calls = []
    refreshed = False

    class ObservedFuture(Future):
        def result(self, timeout=None):
            waiting.set()
            return super().result(timeout)

    monkeypatch.setattr("scenario.core.api.sdk_catalog.Future", ObservedFuture)

    def respond(request):
        calls.append(request)
        if not refreshed:
            return httpx.Response(200, json={"models": [{"id": "saved"}]})
        entered.set()
        assert release.wait(5)
        if outcome == "failure":
            return httpx.Response(503, text="private service failure")
        if outcome == "invalid-record" and "paginationToken" in request.url.params:
            return httpx.Response(200, json={"models": [{"id": "invalid", "capabilities": [None]}]})
        return httpx.Response(
            200, json={"models": [{"id": "partial"}], "nextPaginationToken": "next"}
        )

    context, pools = catalog(respond)
    context.fetch_list()
    refreshed = True
    with ThreadPoolExecutor(max_workers=2) as workers:
        leader = workers.submit(context.fetch_list)
        try:
            assert entered.wait(5)
            waiter = workers.submit(context.fetch_list)
            assert waiting.wait(5)
            if outcome == "retired":
                context.close()
                assert not pools[0]._closed
            elif outcome == "offline":
                context.update_online(False)
        finally:
            release.set()
        for read in (leader, waiter):
            with pytest.raises(ScenarioError) as error:
                read.result(5)
            assert "private service failure" not in str(error.value)
    expected_calls = 3 if outcome == "invalid-record" else 2
    assert len(calls) == expected_calls
    assert context._list_reads == {}
    if outcome == "retired":
        assert context.closed and pools[0]._closed
        with pytest.raises(ScenarioError, match="connection changed"):
            context.load_list_cached()
    else:
        assert [record.id for record in context.load_list_cached()] == ["saved"]
        refreshed = False
        context.update_online(True)
        assert [record.id for record in context.fetch_list()] == ["saved"]
        assert len(calls) == expected_calls + 1
        context.close()


@pytest.mark.parametrize("privacy", ["all", None, [], {}, True])
def test_invalid_privacy_fails_before_opening_an_sdk_pool(privacy):
    context, pools = catalog(lambda request: pytest.fail("Unexpected request"))
    with pytest.raises(ScenarioError, match="request is invalid"):
        context.fetch_list(privacy)
    assert not pools
    context.close()
