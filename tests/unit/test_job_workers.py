# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Worker ownership, bounded admission and shutdown at the actual SDK boundary."""

import json
import socket
import threading
from concurrent.futures import CancelledError, ThreadPoolExecutor

import httpx
import pytest

from scenario.core.api.sdk_adapter import Credentials, SDKAdapter
from scenario.core.jobs.coordinator import JobCoordinator, QuoteError, SubmissionUncertain
from scenario.core.jobs.store import (
    JobOrigin,
    JobScope,
    JobState,
    JobStore,
    StoreConflict,
    StoreError,
)
from scenario.core.jobs.workers import JobWorkers, WorkerError

SCOPE = JobScope("https://service.example.invalid/v1", "account", "project")
ORIGIN = JobOrigin("file", "scene", "revision", "object")


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    def deny(*args, **kwargs):
        pytest.fail("Worker tests must not open sockets")

    monkeypatch.setattr(socket.socket, "connect", deny)
    monkeypatch.setattr(socket.socket, "connect_ex", deny)
    monkeypatch.setattr(socket, "create_connection", deny)


@pytest.fixture
def setup(tmp_path):
    owners, gates, adapters = [], [], []

    def create(*, workers=1, pending_limit=1, fail=False, quote_ttl=120, on_paid=None):
        entered, release = threading.Event(), threading.Event()
        gates.append(release)
        calls = []
        store = JobStore(tmp_path / "jobs.sqlite3", SCOPE)

        def handler(request):
            if request.url.params.get("dryRun") == "true":
                return httpx.Response(200, json={"creativeUnitsCost": 1})
            if on_paid is not None:
                on_paid()
            calls.append((request, threading.get_ident()))
            entered.set()
            assert release.wait(5), "Test did not release network fixture"
            if fail:
                raise httpx.ReadTimeout("private fixture error", request=request)
            if request.method == "GET":
                return httpx.Response(200, json={"job": {"jobId": "remote", "status": "success"}})
            return httpx.Response(200, json={"job": {"jobId": "remote"}})

        adapter = SDKAdapter(
            Credentials("key", "secret"),
            online=lambda: True,
            base_url=SCOPE.service,
            account_id=SCOPE.account_id,
            project_id=SCOPE.project_id,
            transport=httpx.MockTransport(handler),
        )
        adapters.append(adapter)
        coordinator = JobCoordinator(adapter, store, quote_ttl=quote_ttl)
        owner = JobWorkers(coordinator, workers=workers, pending_limit=pending_limit)
        owners.append(owner)

        def prepare(prompt="fixture"):
            estimate = adapter.estimate_model(
                {"id": "model", "type": "custom", "inputs": [{"name": "prompt", "type": "string"}]},
                {"prompt": prompt},
            )
            return coordinator.prepare(estimate, ORIGIN)

        return owner, coordinator, store, prepare, entered, release, calls, adapter

    yield create
    for gate in gates:
        gate.set()
    for owner in owners:
        owner.shutdown()
    for adapter in adapters:
        adapter.close()


def submit(owner, prepared, payload=None):
    return owner.submit(
        prepared,
        origin=ORIGIN,
        operation="model",
        target_id="model",
        payload=payload if payload is not None else prepared.estimate.payload,
    )


def test_bounded_queue_and_payload_snapshot(setup):
    owner, _, store, prepare, entered, release, calls, _ = setup()
    first, second, rejected = prepare(), prepare("second"), prepare("third")
    running = submit(owner, first)
    assert entered.wait(2)
    payload = {"prompt": "second"}
    queued = submit(owner, second, payload)
    payload["prompt"] = "mutated"
    with pytest.raises(WorkerError, match="full"):
        submit(owner, rejected)
    assert store.get(rejected.intent.request_id).state == JobState.PREPARED
    release.set()
    assert running.result(2).state == queued.result(2).state == JobState.REMOTE
    assert [json.loads(c[0].content)["prompt"] for c in calls] == ["fixture", "second"]
    assert all(tid != threading.get_ident() for _, tid in calls)
    assert owner.scope == SCOPE and queued.done()


def test_queued_cancellation_is_durable_and_never_spends(setup):
    owner, _, store, prepare, entered, release, calls, _ = setup()
    first, second = prepare(), prepare()
    running = submit(owner, first)
    assert entered.wait(2)
    queued = submit(owner, second)
    canceled = owner.cancel_prepared(second.intent.request_id, expected_revision=0)
    assert canceled.state == JobState.CANCELED
    release.set()
    running.result(2)
    with pytest.raises(StoreConflict):
        queued.result(2)
    assert len(calls) == 1 and store.get(second.intent.request_id) == canceled


def test_shutdown_waits_for_receipt_and_closes_once(setup, monkeypatch):
    owner, coordinator, store, prepare, entered, release, calls, adapter = setup()
    first, second = prepare(), prepare()
    running = submit(owner, first)
    assert entered.wait(2)
    queued = submit(owner, second)
    closes = []
    close = adapter.close

    def observed_close():
        closes.append(store.get(first.intent.request_id).state)
        close()

    monkeypatch.setattr(adapter, "close", observed_close)
    owner.deactivate()  # Nonblocking context switch while the old request is in flight.
    assert queued.done() and not running.done() and not closes
    with pytest.raises(CancelledError):
        queued.result()
    with pytest.raises(WorkerError, match="inactive"):
        submit(owner, second)
    with pytest.raises(QuoteError):
        coordinator.prepare(second.estimate, ORIGIN)
    with ThreadPoolExecutor(max_workers=2) as joins:
        a, b = joins.submit(owner.shutdown), joins.submit(owner.shutdown)
        assert not a.done() and not b.done()
        release.set()
        a.result(2)
        b.result(2)
    assert closes == [JobState.REMOTE]
    assert running.result().intent.origin == ORIGIN
    assert store.get(second.intent.request_id).state == JobState.PREPARED
    assert len(calls) == 1


def test_worker_failure_is_uncertain_and_does_not_kill_capacity(setup):
    owner, _, store, prepare, entered, release, calls, _ = setup(fail=True)
    first, second = prepare(), prepare()
    one = submit(owner, first)
    assert entered.wait(2)
    two = submit(owner, second)
    release.set()
    for task, prepared in ((one, first), (two, second)):
        with pytest.raises(SubmissionUncertain) as error:
            task.result(2)
        assert "private" not in str(error.value)
        assert store.get(prepared.intent.request_id).state == JobState.UNCERTAIN
    assert len(calls) == 2


def test_queued_quote_is_revalidated_at_dispatch(setup):
    owner, coordinator, store, prepare, entered, release, calls, _ = setup()
    first, second = prepare(), prepare()
    one = submit(owner, first)
    assert entered.wait(2)
    two = submit(owner, second)
    coordinator._clock = lambda: second.expires_at
    release.set()
    one.result(2)
    with pytest.raises(QuoteError, match="expired"):
        two.result(2)
    assert store.get(second.intent.request_id).state == JobState.PREPARED
    assert len(calls) == 1


def test_persistence_error_reaches_owner_without_network(setup, monkeypatch):
    owner, _, store, prepare, _, _, calls, _ = setup()
    prepared = prepare()

    def fail(*args, **kwargs):
        raise StoreError("fixture write failure")

    monkeypatch.setattr(store, "transition", fail)
    with pytest.raises(StoreError):
        submit(owner, prepared).result(2)
    assert calls == []


def test_known_id_refresh_runs_on_worker(setup):
    owner, _, store, prepare, _, release, calls, _ = setup()
    prepared = prepare()
    record = store.transition(
        prepared.intent.request_id, expected_revision=0, state=JobState.SUBMITTING
    )
    record = store.transition(
        prepared.intent.request_id,
        expected_revision=record.revision,
        state=JobState.REMOTE,
        remote_job_id="remote",
    )
    release.set()
    snapshot = owner.refresh_remote(
        record.intent.request_id, expected_revision=record.revision
    ).result(2)
    assert snapshot.record.state == JobState.SUCCEEDED
    assert calls[0][0].method == "GET" and calls[0][1] != threading.get_ident()


@pytest.mark.parametrize(
    "options",
    [
        {"workers": 0},
        {"workers": True},
        {"workers": 1.5},
        {"pending_limit": 0},
        {"pending_limit": False},
    ],
)
def test_invalid_limits_do_not_start_workers(setup, options):
    _, coordinator, _, _, _, _, _, _ = setup()
    with pytest.raises(ValueError):
        JobWorkers(coordinator, **options)


def test_worker_cannot_join_itself(setup, monkeypatch):
    owner, coordinator, _, prepare, _, _, calls, _ = setup()
    prepared = prepare()
    monkeypatch.setattr(coordinator, "submit", lambda *a, **k: owner.shutdown())
    with pytest.raises(WorkerError, match="join its own"):
        submit(owner, prepared).result(2)
    assert calls == []


def test_active_network_concurrency_is_bounded(setup):
    both_entered = threading.Barrier(3)
    owner, _, _, prepare, entered, release, calls, _ = setup(
        workers=2, pending_limit=4, on_paid=lambda: both_entered.wait(timeout=3)
    )
    first, second = prepare(), prepare()
    one, two = submit(owner, first), submit(owner, second)
    both_entered.wait(timeout=3)
    assert entered.wait(2)
    release.set()
    one.result(2)
    two.result(2)
    assert len({tid for _, tid in calls}) == 2


def test_failed_thread_start_joins_started_workers(setup, monkeypatch):
    _, coordinator, _, _, _, _, _, _ = setup()
    start = threading.Thread.start
    threads = []

    def fail_second(thread):
        threads.append(thread)
        if len(threads) == 2:
            raise RuntimeError("fixture thread exhaustion")
        start(thread)

    monkeypatch.setattr(threading.Thread, "start", fail_second)
    with pytest.raises(RuntimeError, match="exhaustion"):
        JobWorkers(coordinator, workers=2)
    assert not any(thread.is_alive() for thread in threads)


@pytest.mark.parametrize("failure_type", [KeyboardInterrupt, SystemExit, GeneratorExit])
def test_control_exception_stops_owner_without_stranding_tasks(setup, monkeypatch, failure_type):
    owner, coordinator, store, prepare, entered, release, calls, _ = setup()
    first, second = prepare(), prepare()
    failure = failure_type("fixture worker interruption")
    propagated = []
    reported = threading.Event()

    def observe(args):
        propagated.append(args.exc_value)
        reported.set()

    def interrupt(*args, **kwargs):
        entered.set()
        assert release.wait(5), "Test did not release worker fixture"
        raise failure

    monkeypatch.setattr(threading, "excepthook", observe)
    monkeypatch.setattr(coordinator, "submit", interrupt)
    running = submit(owner, first)
    assert entered.wait(2)
    queued = submit(owner, second)
    release.set()
    with pytest.raises(failure_type) as error:
        running.result(2)
    assert error.value is failure
    assert reported.wait(2), "Control exception did not escape the worker"
    assert propagated == [failure]
    with pytest.raises(CancelledError):
        queued.result(2)
    with pytest.raises(WorkerError, match="inactive"):
        submit(owner, second)
    assert calls == []
    assert store.get(second.intent.request_id).state == JobState.PREPARED
    owner.shutdown()
    assert all(not thread.is_alive() for thread in owner._threads)
