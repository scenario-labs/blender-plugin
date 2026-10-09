# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Active catalog reads use real SDK serialization without service connections."""

import base64
import json
import threading
from concurrent.futures import Future, ThreadPoolExecutor
from decimal import Decimal

import httpx
import pytest

from scenario.core.api import catalog as catalog_module
from scenario.core.api.errors import ScenarioError
from scenario.core.api.sdk_adapter import MODEL_BULK_LIMIT, AdapterError, Credentials, SDKAdapter
from scenario.core.api.sdk_catalog import SDKCatalog
from scenario.core.jobs.store import JobScope


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


ESTIMATE_MODEL = {
    "id": "fixture",
    "type": "custom",
    "inputs": [{"name": "prompt", "type": "string", "required": True}],
}


@pytest.mark.parametrize("project", [None, "selected-project"])
def test_local_scope_binds_adapter_without_sending_local_identity(project):
    scope = JobScope("https://api.cloud.scenario.com/v1", "local-key-fixture", project)
    calls = []

    def respond(request):
        calls.append(request)
        return httpx.Response(200, json={"models": []})

    context, pools = catalog(respond, scope=scope)
    try:
        context.fetch_list()
        assert context.scope == scope
        assert pools[0].account_id == scope.account_id
        assert pools[0].project_id == project
        assert calls[0].url.params.get("projectId") == project
        assert scope.account_id not in str(calls[0].url)
        assert scope.account_id not in str(calls[0].headers)
    finally:
        context.close()


def test_estimate_uses_selected_sdk_connection_and_keeps_exact_response():
    calls = []

    def respond(request):
        calls.append(request)
        if request.method == "GET":
            return httpx.Response(200, json={"model": ESTIMATE_MODEL})
        assert request.url.path == "/v1/generate/custom/fixture"
        assert dict(request.url.params) == {"dryRun": "true"}
        assert json.loads(request.content) == {"prompt": "teapot"}
        return httpx.Response(269, content=b'{"creativeUnitsCost":1.1234567890123456789}')

    context, pools = catalog(respond)
    try:
        quote = context.estimate("fixture", {"prompt": "teapot"})
        assert quote.cost == Decimal("1.1234567890123456789")
        assert quote.response_json == b'{"creativeUnitsCost":1.1234567890123456789}'
        assert quote.payload == {"prompt": "teapot"}
        assert len(pools) == 1
        assert pools[0].owns_estimate(quote)
        assert all(
            call.headers["Authorization"] == calls[0].headers["Authorization"] for call in calls
        )
        context.update_online(False)
        with pytest.raises(ScenarioError, match="Online access is disabled"):
            context.estimate("fixture", {"prompt": "offline"})
        assert len(calls) == 2
    finally:
        context.close()
    assert not pools[0].owns_estimate(quote)


@pytest.mark.parametrize(
    "raw",
    [
        b"{}",
        b'{"creativeUnitsCost":-1}',
        b'{"creativeUnitsCost":true}',
        b'{"creativeUnitsCost":"2"}',
    ],
)
def test_invalid_estimate_never_becomes_a_free_quote(raw):
    def respond(request):
        if request.method == "GET":
            return httpx.Response(200, json={"model": ESTIMATE_MODEL})
        return httpx.Response(269, content=raw)

    context, _ = catalog(respond)
    try:
        with pytest.raises(ScenarioError, match="no valid exact estimate"):
            context.estimate("fixture", {"prompt": "teapot"})
    finally:
        context.close()


def test_estimate_snapshots_inputs_and_rejects_retirement_during_request():
    entered, release = threading.Event(), threading.Event()
    bodies = []

    def respond(request):
        if request.method == "GET":
            entered.set()
            assert release.wait(5)
            return httpx.Response(200, json={"model": ESTIMATE_MODEL})
        bodies.append(json.loads(request.content))
        context.close()
        return httpx.Response(269, json={"creativeUnitsCost": 0})

    context, pools = catalog(respond)
    parameters = {"prompt": "original"}
    with ThreadPoolExecutor(max_workers=1) as worker:
        result = worker.submit(context.estimate, "fixture", parameters)
        try:
            assert entered.wait(5)
            parameters["prompt"] = "changed"
        finally:
            release.set()
        with pytest.raises(ScenarioError, match="connection changed"):
            result.result(5)
    assert bodies == [{"prompt": "original"}]
    assert context.closed and pools[0]._closed


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
        httpx.Response(200, json={"model": {"id": "fixture", "capabilities": [17]}}),
        httpx.Response(200, json={"model": {"id": "fixture", "tags": 17}}),
        httpx.Response(200, json={"model": {"id": "fixture", "inputs": [17]}}),
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


@pytest.mark.parametrize(
    "model",
    [
        {"id": "fixture", "inputs": [17]},
        {"id": "fixture", "inputs": [{"name": "size"}], "uiConfig": {"selects": [17]}},
    ],
)
def test_unparseable_form_schema_is_rejected_before_caching(model):
    context, _ = catalog(lambda request: httpx.Response(200, json={"model": model}))
    with pytest.raises(ScenarioError, match="^0 Scenario returned an invalid model description$"):
        context.get("fixture")
    assert context.load_cached("fixture") is None
    context.close()


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


def test_job_adapter_has_independent_pool_but_shared_permission_and_scope():
    scope = JobScope("https://api.cloud.scenario.com/v1", "local-fixture")
    context, pools = catalog(lambda _: httpx.Response(200, json={"models": []}), scope=scope)
    owner = context.create_job_adapter()
    try:
        context.fetch_list()
        assert len(pools) == 2
        assert owner is not pools[1]
        assert owner.account_id == scope.account_id
        context.update_online(False)
        with pytest.raises(AdapterError, match="[Oo]nline"):
            owner.model_page()
        context.update_online(True)
        owner.model_page()
        context.close()
        assert not owner._closed
        with pytest.raises(AdapterError, match="[Oo]nline"):
            owner.model_page()
        with pytest.raises(ScenarioError, match="connection changed"):
            context.create_job_adapter()
    finally:
        owner.close()
        context.close()


def test_job_owner_close_does_not_close_catalog_pool():
    scope = JobScope("https://api.cloud.scenario.com/v1", "local-fixture")
    context, _ = catalog(lambda _: httpx.Response(200, json={"models": []}), scope=scope)
    try:
        owner = context.create_job_adapter()
        context.fetch_list()
        owner.close()
        assert context.fetch_list() == []
    finally:
        context.close()


def test_job_adapter_requires_durable_scope():
    context, pools = catalog(lambda _: pytest.fail("No request expected"))
    try:
        with pytest.raises(ScenarioError, match="storage is not configured"):
            context.create_job_adapter()
        assert pools == []
    finally:
        context.close()


def bulk_handler(calls, missing=(), details=True):
    def respond(request):
        calls.append(request)
        if request.method == "POST":
            assert request.url.path == "/v1/models/get-bulk"
            ids = json.loads(request.content)["modelIds"]
            rows = [
                {"id": model_id, "name": model_id.upper(), "uiConfig": {"future": True}}
                for model_id in ids
                if model_id not in missing
            ]
            return httpx.Response(200, json={"models": rows})
        assert details
        model_id = request.url.path.rsplit("/", 1)[-1]
        return httpx.Response(
            200,
            json={"model": {"id": model_id, "inputs": [{"name": "prompt", "type": "string"}]}},
        )

    return respond


def bulk_ids(calls):
    return [json.loads(call.content)["modelIds"] for call in calls if call.method == "POST"]


@pytest.mark.parametrize("project", [None, "selected-project"])
def test_bulk_summaries_are_read_once_per_connection_apart_from_details(project):
    calls = []
    scope = JobScope("https://api.cloud.scenario.com/v1", "local-fixture", project)
    context, pools = catalog(bulk_handler(calls, missing={"missing"}), scope=scope)
    try:
        first = context.get_many(["base", "missing", "base"])
        assert list(first) == ["base"] and first["base"].name == "BASE"
        assert first["base"].ui_config == {"future": True}
        assert bulk_ids(calls) == [["base", "missing"]]
        assert all(call.url.params.get("projectId") == project for call in calls)
        first["base"].raw["name"] = "Changed by caller"
        # Cached summaries and remembered absences make no new request.
        again = context.get_many(("missing", "base"))
        assert list(again) == ["base"] and again["base"].name == "BASE"
        assert len(calls) == 1
        assert list(context.get_many(["base", "other"])) == ["base", "other"]
        assert bulk_ids(calls)[-1] == ["other"]
        # A summary never stands in for the detail used by forms and quotes.
        assert context.load_cached("base") is None
        assert context.get("base").parameters == [{"name": "prompt", "type": "string"}]
        assert calls[-1].method == "GET"
        context.get_many(["base", "missing"], refresh=True)
        assert bulk_ids(calls)[-1] == ["base", "missing"]
        assert context.get_many([]) == {}
        assert len(pools) == 1
        other, _ = catalog(bulk_handler(calls))
        try:
            assert list(other.get_many(["base"])) == ["base"]
            assert bulk_ids(calls)[-1] == ["base"]
        finally:
            other.close()
    finally:
        context.close()
    assert pools[0]._closed


@pytest.mark.parametrize(
    "model_ids",
    [
        "base",
        b"base",
        {"base"},
        None,
        [None],
        [f"m{index}" for index in range(MODEL_BULK_LIMIT + 1)],
    ],
)
def test_invalid_bulk_requests_fail_before_opening_a_pool(model_ids):
    context, pools = catalog(lambda request: pytest.fail("Unexpected request"))
    with pytest.raises(ScenarioError, match="request is invalid"):
        context.get_many(model_ids)
    assert not pools and context._summary_reads == {}
    context.close()


@pytest.mark.parametrize("model_id", ["", "../other", "padded "])
def test_invalid_bulk_identifiers_never_reach_the_service(model_id):
    context, _ = catalog(lambda request: pytest.fail("Unexpected request"))
    with pytest.raises(ScenarioError, match="request is invalid"):
        context.get_many([model_id])
    assert context._summary_reads == {} and context._summaries == {}
    context.close()


def test_overlapping_bulk_reads_share_pending_ids(monkeypatch):
    entered, release, waiting = (threading.Event() for _ in range(3))
    calls = []

    class ObservedFuture(Future):
        def result(self, timeout=None):
            waiting.set()
            return super().result(timeout)

    monkeypatch.setattr("scenario.core.api.sdk_catalog.Future", ObservedFuture)
    respond = bulk_handler(calls)

    def blocking(request):
        if json.loads(request.content)["modelIds"] == ["a", "b"]:
            entered.set()
            assert release.wait(5)
        return respond(request)

    context, pools = catalog(blocking)
    with ThreadPoolExecutor(max_workers=2) as workers:
        leader = workers.submit(context.get_many, ["a", "b"])
        try:
            assert entered.wait(5)
            waiter = workers.submit(context.get_many, ["b", "c"])
            assert waiting.wait(5)
            assert not waiter.done()
        finally:
            release.set()
        assert list(leader.result(5)) == ["a", "b"]
        shared = waiter.result(5)
    assert list(shared) == ["b", "c"]
    assert sorted(bulk_ids(calls)) == [["a", "b"], ["c"]]
    assert context._summary_reads == {} and len(pools) == 1
    context.close()


@pytest.mark.parametrize("outcome", ["failure", "retired", "offline", "invalid-record"])
def test_failed_bulk_read_releases_waiters_without_caching(monkeypatch, outcome):
    entered, release, waiting = (threading.Event() for _ in range(3))
    calls = []

    class ObservedFuture(Future):
        def result(self, timeout=None):
            waiting.set()
            return super().result(timeout)

    monkeypatch.setattr("scenario.core.api.sdk_catalog.Future", ObservedFuture)

    def respond(request):
        calls.append(request)
        if len(calls) == 1:
            entered.set()
            assert release.wait(5)
            if outcome == "failure":
                return httpx.Response(503, text="private service failure")
            if outcome == "invalid-record":
                return httpx.Response(200, json={"models": [{"id": "a", "capabilities": [None]}]})
        return httpx.Response(200, json={"models": [{"id": "a"}]})

    context, pools = catalog(respond)
    # Revoked permission refuses the next chunk; a dispatched chunk is not recalled.
    second_chunk = [f"x{index}" for index in range(50)] if outcome == "offline" else []
    with ThreadPoolExecutor(max_workers=2) as workers:
        leader = workers.submit(context.get_many, ["a", *second_chunk])
        try:
            assert entered.wait(5)
            waiter = workers.submit(context.get_many, ["a"], True)
            assert waiting.wait(5)
            if outcome == "retired":
                context.close()
            elif outcome == "offline":
                context.update_online(False)
        finally:
            release.set()
        for read in (leader, waiter):
            with pytest.raises(ScenarioError) as error:
                read.result(5)
            assert "private service failure" not in str(error.value)
    assert len(calls) == 1
    assert context._summary_reads == {} and context._summaries == {}
    if outcome == "retired":
        assert context.closed and pools[0]._closed
        with pytest.raises(ScenarioError, match="connection changed"):
            context.get_many(["a"])
    else:
        context.update_online(True)
        assert list(context.get_many(["a"])) == ["a"]
        assert len(calls) == 2
        context.close()


@pytest.mark.parametrize("status", [403, 404])
def test_inaccessible_model_detail_keeps_its_status_without_service_text(status):
    context, _ = catalog(lambda request: httpx.Response(status, text="private model of team-x"))
    try:
        with pytest.raises(ScenarioError) as error:
            context.get("private-model")
        assert error.value.status == status
        assert "not available" in error.value.reason
        assert "team-x" not in str(error.value) and "private-model" not in str(error.value)
        assert context.load_cached("private-model") is None
    finally:
        context.close()


def test_trained_models_reuse_cached_lists_and_classify_rest_records():
    calls = []
    private_rows = [
        {"id": "team-lora", "type": "flux.1-lora", "privacy": "private"},
        {"id": "team-mix", "type": "flux.1-composition", "privacy": "private"},
        {"id": "team-custom", "type": "custom", "privacy": "private"},
        {"id": "team-voice", "type": "elevenlabs-voice", "privacy": "private"},
    ]
    public_rows = [
        {"id": "base", "type": "custom", "privacy": "public", "capabilities": ["txt2img"]},
        {"id": "scenario-lora", "type": "zimage-lora", "privacy": "public"},
        {"id": "hosted", "type": "flux.1-pro", "privacy": "public"},
    ]

    def respond(request):
        calls.append(request)
        privacy = request.url.params["privacy"]
        if privacy == "private":
            assert request.url.params["status"] == "trained"
        rows = private_rows if privacy == "private" else public_rows
        return httpx.Response(200, json={"models": rows})

    context, pools = catalog(respond)
    try:
        expected = [
            ("lora", "team-lora"),
            ("composition", "team-mix"),
            ("custom_private", "team-custom"),
            ("unsupported", "team-voice"),
            ("lora", "scenario-lora"),
        ]
        pairs = context.trained_models()
        assert [(kind, record.id) for kind, record in pairs] == expected
        assert [call.url.params["privacy"] for call in calls] == ["private", "public"]
        pairs[0][1].raw["type"] = "custom"
        assert [(kind, record.id) for kind, record in context.trained_models()] == expected
        assert len(calls) == 2
        # Lane lists from the same public read keep excluding every trained record.
        lane = catalog_module.models_for_lane("image", context.load_list_cached("public"))
        assert [record.id for record in lane] == ["base"]
        context.trained_models(refresh=True)
        assert len(calls) == 4 and len(pools) == 1
    finally:
        context.close()
