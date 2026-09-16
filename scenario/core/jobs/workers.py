# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Bounded application-owned workers for the shared job commands, without bpy."""

import json
import threading
from collections import deque
from concurrent.futures import Future

from .coordinator import JobCoordinator, QuoteError, _payload


class WorkerError(RuntimeError):
    """The application owner cannot accept this command."""


class JobTask:
    """Poll or read a command result on the caller's thread; no worker callbacks.

    This intentionally exposes no add_done_callback: a Blender owner must poll
    from its main-thread pump, or block explicitly in a headless command loop.
    """

    def __init__(self):
        self._future = Future()

    def done(self):
        return self._future.done()

    def result(self, timeout=None):
        return self._future.result(timeout=timeout)


class JobWorkers:
    """Own one coordinator until shutdown, independently of any UI view.

    Admission bounds queued commands separately from active workers. Queued
    quotes are revalidated by the coordinator immediately before dispatch.
    Deactivation abandons queued execution (records remain reviewable) and lets
    already claimed requests persist their original-scope receipts.
    """

    def __init__(self, coordinator: JobCoordinator, *, workers=2, pending_limit=16):
        if not isinstance(coordinator, JobCoordinator):
            raise TypeError("Use the shared job coordinator")
        for value in (workers, pending_limit):
            if not isinstance(value, int) or isinstance(value, bool) or value < 1:
                raise ValueError("Worker and pending limits must be positive integers")
        self._coordinator = coordinator
        self._limit = pending_limit
        self._condition = threading.Condition()
        self._pending = deque()
        self._accepting = True
        self._closed = False
        self._shutdown_lock = threading.Lock()
        self._threads = [
            threading.Thread(target=self._run, name=f"ScenarioJob-{i}") for i in range(workers)
        ]
        started = []
        try:
            for thread in self._threads:
                thread.start()
                started.append(thread)
        except BaseException:
            with self._condition:
                self._accepting = False
                self._condition.notify_all()
            for thread in started:
                thread.join()
            raise

    @property
    def scope(self):
        return self._coordinator.scope

    @property
    def stopped(self):
        """Whether every owned worker has exited, independently of SDK close success."""
        return all(not thread.is_alive() for thread in self._threads)

    def _enqueue(self, command, *args, **kwargs):
        with self._condition:
            if not self._accepting:
                raise WorkerError("This job owner is inactive")
            if len(self._pending) >= self._limit:
                raise WorkerError("Job queue is full; wait before adding more commands")
            task = JobTask()
            self._pending.append((task, command, args, kwargs))
            self._condition.notify()
            return task

    def submit(self, prepared, *, origin, operation, target_id, payload):
        """Queue an explicitly chosen paid action using an immutable payload copy."""
        try:
            snapshot = json.loads(_payload(payload))
        except (RecursionError, OverflowError):
            raise QuoteError("The current payload must contain finite JSON values") from None
        return self._enqueue(
            self._coordinator.submit,
            prepared,
            origin=origin,
            operation=operation,
            target_id=target_id,
            payload=snapshot,
        )

    def refresh_remote(self, request_id, *, expected_revision):
        return self._enqueue(
            self._coordinator.refresh_remote, request_id, expected_revision=expected_revision
        )

    def cancel_prepared(self, request_id, *, expected_revision):
        """Persist local cancellation now; a queued command then cannot dispatch."""
        with self._condition:
            if not self._accepting:
                raise WorkerError("This job owner is inactive")
            return self._coordinator.cancel_prepared(
                request_id, expected_revision=expected_revision
            )

    def _run(self):
        while True:
            with self._condition:
                self._condition.wait_for(lambda: self._pending or not self._accepting)
                if not self._pending:
                    return
                task, command, args, kwargs = self._pending.popleft()
            if task._future.set_running_or_notify_cancel():
                try:
                    result = command(*args, **kwargs)
                except Exception as exc:
                    task._future.set_exception(exc)
                except BaseException as exc:
                    # Settle the handle and stop queued work before propagating
                    # thread-control exceptions; never leave a running future.
                    task._future.set_exception(exc)
                    self.deactivate()
                    raise
                else:
                    task._future.set_result(result)
                    del result
            # Do not retain payloads/results while the worker waits for more work.
            del task, command, args, kwargs

    def deactivate(self):
        """Stop admission/queued work promptly; in-flight work keeps its scope."""
        with self._condition:
            self._accepting = False
            self._coordinator.deactivate()
            while self._pending:
                task, _, _, _ = self._pending.popleft()
                task._future.cancel()
            self._condition.notify_all()

    def shutdown(self):
        """Wait for in-flight persistence before closing the connection, once.

        Call on extension disable/exit, not on view closure. Network timeout
        policy bounds HTTP waits; this method never claims to kill running I/O.
        """
        if threading.current_thread() in self._threads:
            raise WorkerError("A job worker cannot join its own owner")
        with self._shutdown_lock:
            if self._closed:
                return
            self.deactivate()
            for thread in self._threads:
                thread.join()
            self._coordinator.close()
            self._closed = True
