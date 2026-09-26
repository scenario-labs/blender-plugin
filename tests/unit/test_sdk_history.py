# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""SDK history pages and captured worker delivery, without service calls."""

import threading
from concurrent.futures import ThreadPoolExecutor

import httpx
import pytest

from scenario.core.api.errors import ScenarioError
from scenario.core.api.sdk_adapter import AdapterError, Credentials, SDKAdapter
from scenario.core.jobs.manager import JobManager
from tests.unit.test_sdk_catalog import catalog


def job(identifier="job-fixture", prompt="a teapot"):
    return {
        "jobId": identifier,
        "jobType": "custom",
        "metadata": {"input": {"prompt": prompt}},
    }


def test_one_page_keeps_project_credentials_and_opaque_cursor(monkeypatch):
    monkeypatch.setenv("SCENARIO_API_KEY", "wrong-key")
    calls = []
    page = {"jobs": [job(), job()], "nextPaginationToken": "another", "future": True}

    def respond(request):
        calls.append(request)
        return httpx.Response(200, json=page)

    with SDKAdapter(
        Credentials("selected", "secret"),
        online=lambda: True,
        project_id="project-fixture",
        transport=httpx.MockTransport(respond),
    ) as adapter:
        result = adapter.job_page(pagination_token="opaque+/= cursor")
    assert result == {**page, "jobs": [job()]}
    assert len(calls) == 1
    request = calls[0]
    assert (request.method, request.url.path) == ("GET", "/v1/jobs")
    assert dict(request.url.params) == {
        "pageSize": "50",
        "hideResults": "false",
        "projectId": "project-fixture",
        "paginationToken": "opaque+/= cursor",
    }
    assert request.headers["Authorization"] == "Basic c2VsZWN0ZWQ6c2VjcmV0"


@pytest.mark.parametrize(
    "page",
    [
        {},
        {"jobs": None},
        {"jobs": [None]},
        {"jobs": [{"jobId": "bad/id"}]},
        {"jobs": [job(), {**job(), "status": "changed"}]},
        {"jobs": [], "nextPaginationToken": 3},
        {"jobs": [], "nextPaginationToken": "same"},
    ],
)
def test_invalid_page_never_reaches_history(page):
    with (
        SDKAdapter(
            Credentials("key", "secret"),
            online=lambda: True,
            transport=httpx.MockTransport(lambda r: httpx.Response(200, json=page)),
        ) as adapter,
        pytest.raises(AdapterError),
    ):
        adapter.job_page(pagination_token="same")


@pytest.mark.parametrize(
    "options",
    [
        {"page_size": True},
        {"page_size": 0},
        {"page_size": 201},
        {"pagination_token": 3},
        {"pagination_token": ""},
    ],
)
def test_invalid_history_request_never_sends(options):
    def unexpected(request):
        pytest.fail("Invalid parameters reached the service")

    with (
        SDKAdapter(
            Credentials("key", "secret"),
            online=lambda: True,
            transport=httpx.MockTransport(unexpected),
        ) as adapter,
        pytest.raises(ValueError),
    ):
        adapter.job_page(**options)


def test_prompts_are_connection_local_bounded_and_incomplete_previews_are_not_text():
    calls = []
    text = "first connection"

    def respond(request):
        calls.append(request)
        if request.url.path == "/v1/jobs":
            return httpx.Response(
                200,
                json={
                    "jobs": [job(f"job-{i}", f"asset_{i}") for i in range(32)],
                    "nextPaginationToken": "next",
                },
            )
        identifier = request.url.path.rsplit("/", 1)[1]
        if identifier == "asset_1":
            return httpx.Response(403, json={"secret": "private error"})
        return httpx.Response(
            200,
            json={
                "asset": {
                    "metadata": {
                        "preview": text,
                        "hasFullPreview": identifier != "asset_2",
                    }
                }
            },
        )

    context, pools = catalog(respond)
    try:
        first = context.history_page()
        assert len(calls) == 31 and len(pools) == 1
        assert first["jobs"][0]["metadata"]["input"]["prompt"] == text
        for index in (1, 2, 30, 31):
            assert first["jobs"][index]["metadata"]["input"]["prompt"] == f"asset_{index}"
        context.close()
        text = "replacement connection"
        other, _ = catalog(respond)
        try:
            second = other.history_page()
            assert second["jobs"][0]["metadata"]["input"]["prompt"] == text
        finally:
            other.close()
    finally:
        context.close()


def test_retired_history_read_cannot_deliver_and_closes_pool_after_completion():
    entered, release = threading.Event(), threading.Event()

    def respond(request):
        entered.set()
        assert release.wait(5)
        return httpx.Response(200, json={"jobs": [job()]})

    context, pools = catalog(respond)
    with ThreadPoolExecutor(max_workers=1) as worker:
        future = worker.submit(context.history_page)
        try:
            assert entered.wait(5)
            context.close()
            assert not pools[0]._closed
        finally:
            release.set()
        with pytest.raises(ScenarioError, match="connection changed"):
            future.result(5)
    assert pools[0]._closed


@pytest.mark.parametrize("failure", [False, True])
def test_worker_routes_history_to_headless_read_queue_and_sanitizes_errors(failure):
    def respond(request):
        if failure:
            raise RuntimeError("private transport detail")
        assert threading.current_thread() is not threading.main_thread()
        return httpx.Response(200, json={"jobs": [job()], "nextPaginationToken": "next"})

    context, _ = catalog(respond)
    manager = JobManager(None, None, None)  # No prototype client is available.
    try:
        manager.fetch_history(context, "request", "opaque", append=True)
        manager.join(5)
        assert not manager.has_active()
        assert not manager.drain()
        [(name, payload)] = manager.drain_catalog()
        assert name == "history"
        assert payload["catalog"] is context
        assert (payload["key"], payload["cursor"], payload["append"]) == ("request", "opaque", True)
        if failure:
            assert payload["error"] == "Could not reach Scenario"
        else:
            assert payload["jobs"] == [job()]
            assert payload["token"] == "next"
    finally:
        context.close()


def test_offline_history_never_sends():
    context, _ = catalog(lambda r: pytest.fail("Offline request reached transport"))
    context.update_online(False)
    try:
        with pytest.raises(ScenarioError, match="Online"):
            context.history_page()
    finally:
        context.close()
