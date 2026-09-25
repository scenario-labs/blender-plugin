# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Expired or stopped MCP requests never enter the mutation handler."""

import threading
import time
from concurrent.futures import ThreadPoolExecutor

import pytest

import scenario.mcp.server as mcp_server
from scenario.mcp.protocol import Registry, ToolSpec, ToolTimeout


def server(handler, timeout=0.03):
    registry = Registry()
    registry.add(ToolSpec("mutate", "Fixture mutation", {}, handler))
    return mcp_server.McpServer("127.0.0.1", 0, "fixture-token", registry, {}, timeout=timeout)


def message():
    return {"id": 1, "method": "tools/call", "params": {"name": "mutate"}}


def queued(target):
    deadline = time.monotonic() + 5
    while target._queue.empty() and time.monotonic() < deadline:
        time.sleep(0.001)
    assert not target._queue.empty()


def test_timed_out_mutation_does_not_execute_when_blender_resumes():
    mutations = []
    target = server(lambda args: mutations.append(args))
    with ThreadPoolExecutor(max_workers=1) as worker:
        result = worker.submit(target.handle, message()).result(5)
    assert result["error"]["code"] == -32000
    assert "not executed" in result["error"]["message"]
    target.process_pending()
    assert mutations == []
    assert target._queue.empty()


def test_expired_request_is_rejected_by_pump_even_before_waiter_wakes(monkeypatch):
    # Delay the caller after Event.wait reaches its deadline, exposing the race
    # where Blender resumes before the HTTP thread can mark the request expired.
    expired, release = threading.Event(), threading.Event()
    original = mcp_server._Pending

    class DelayedWaiter(original):
        def outcome(self):
            expired.set()
            assert release.wait(5)
            return super().outcome()

    monkeypatch.setattr(mcp_server, "_Pending", DelayedWaiter)
    mutations = []
    target = server(lambda args: mutations.append(args))
    with ThreadPoolExecutor(max_workers=1) as worker:
        result = worker.submit(target.handle, message())
        try:
            assert expired.wait(5)
            target.process_pending()
            assert mutations == []
        finally:
            release.set()
        assert "not executed" in result.result(5)["error"]["message"]


def test_stop_wakes_queued_callers_and_rejects_new_admission():
    mutations = []
    target = server(lambda args: mutations.append(args), timeout=60)
    with ThreadPoolExecutor(max_workers=1) as worker:
        result = worker.submit(target.handle, message())
        queued(target)
        target.stop()
        assert "not executed" in result.result(1)["error"]["message"]
    assert "stopped" in target.handle(message())["error"]["message"]
    target.process_pending()
    assert mutations == []
    assert target._queue.empty()


def test_started_timeout_reports_uncertainty_without_replaying_or_interrupting():
    entered, release = threading.Event(), threading.Event()
    mutations = []

    def mutate(args):
        entered.set()
        assert release.wait(5)
        mutations.append("finished once")
        return "done"

    target = server(mutate, timeout=1)
    with ThreadPoolExecutor(max_workers=2) as worker:
        caller = worker.submit(target.handle, message())
        queued(target)
        pump = worker.submit(target.process_pending)
        try:
            assert entered.wait(5)
            response = caller.result(5)
            assert "outcome is unknown" in response["error"]["message"]
            assert "not executed" not in response["error"]["message"]
            target.stop()
        finally:
            release.set()
        pump.result(5)
    assert mutations == ["finished once"]
    assert target.process_pending() == 0


def test_completed_result_wins_timeout_observation_race(monkeypatch):
    observing, release, finish = (threading.Event() for _ in range(3))
    original = mcp_server._Pending

    class DelayedObserver(original):
        def outcome(self):
            observing.set()
            assert release.wait(5)
            return super().outcome()

    monkeypatch.setattr(mcp_server, "_Pending", DelayedObserver)

    def mutate(args):
        assert finish.wait(5)
        return {"executed": True}

    target = server(mutate, timeout=1)
    with ThreadPoolExecutor(max_workers=2) as worker:
        result = worker.submit(target.handle, message())
        queued(target)
        pump = worker.submit(target.process_pending)
        try:
            assert observing.wait(5)
            finish.set()
            pump.result(5)
        finally:
            finish.set()
            release.set()
        assert "error" not in result.result(5)


def test_handler_errors_are_delivered_without_blocking_later_requests():
    def fail(args):
        raise ValueError("fixture error")

    target = server(fail, timeout=5)
    with ThreadPoolExecutor(max_workers=1) as worker:
        result = worker.submit(target.executor, fail, {})
        queued(target)
        target.process_pending()
        with pytest.raises(ValueError, match="fixture error"):
            result.result(1)
        result = worker.submit(target.executor, lambda args: 42, {})
        queued(target)
        target.process_pending()
        assert result.result(1) == 42


def test_stopping_multiple_requests_drains_queue_without_late_execution():
    target = server(lambda args: pytest.fail("Stopped request executed"), timeout=5)
    with ThreadPoolExecutor(max_workers=3) as worker:
        futures = [
            worker.submit(target.executor, target.registry.get("mutate").handler, {})
            for _ in range(3)
        ]
        deadline = time.monotonic() + 5
        while target._queue.qsize() < 3 and time.monotonic() < deadline:
            time.sleep(0.001)
        assert target._queue.qsize() == 3
        target.stop()
        for future in futures:
            with pytest.raises(ToolTimeout, match="not executed"):
                future.result(1)
    assert target.process_pending() == 0
