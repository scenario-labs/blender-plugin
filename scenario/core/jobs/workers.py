# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Bounded application-owned workers for the shared job commands, without bpy."""

import json
import os
import threading
from collections import deque
from concurrent.futures import Future

from .coordinator import JobCoordinator, QuoteError, _payload


def _snapshot(payload):
    try:
        return json.loads(_payload(payload))
    except (RecursionError, OverflowError):
        raise QuoteError("The current payload must contain finite JSON values") from None


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
        self._local_cancels = {}
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

    def models(self, *, privacy="public", max_pages=100):
        return self._enqueue(self._coordinator.models, privacy=privacy, max_pages=max_pages)

    def workflows(self, *, privacy="private", max_pages=100):
        return self._enqueue(self._coordinator.workflows, privacy=privacy, max_pages=max_pages)

    def asset_page(self, **options):
        return self._enqueue(self._coordinator.asset_page, **_snapshot(options))

    def search_assets(self, query, **options):
        return self._enqueue(self._coordinator.search_assets, query, **_snapshot(options))

    def model(self, identifier):
        return self._enqueue(self._coordinator.model, identifier)

    def workflow(self, identifier):
        return self._enqueue(self._coordinator.workflow, identifier)

    def quote_model(self, identifier, parameters, *, origin):
        snapshot = _snapshot(parameters)
        return self._enqueue(self._coordinator.quote_model, identifier, snapshot, origin=origin)

    def quote_film_composition(self, verified, *, origin):
        return self._enqueue(self._coordinator.quote_film_composition, verified, origin=origin)

    def quote_film_task(self, recipe, *, production_id, task_id, origin):
        snapshot = _snapshot(recipe)
        return self._enqueue(
            self._coordinator.quote_film_task,
            snapshot,
            production_id=production_id,
            task_id=task_id,
            origin=origin,
        )

    def bind_film_upload(
        self, recipe, *, production_id, task_id, request_id, expected_revision, origin
    ):
        snapshot = _snapshot(recipe)
        return self._enqueue(
            self._coordinator.bind_film_upload,
            snapshot,
            production_id=production_id,
            task_id=task_id,
            request_id=request_id,
            expected_revision=expected_revision,
            origin=origin,
        )

    def quote_workflow(self, identifier, parameters, *, origin):
        snapshot = _snapshot(parameters)
        return self._enqueue(self._coordinator.quote_workflow, identifier, snapshot, origin=origin)

    def quote_prompt(self, parameters, *, origin):
        snapshot = _snapshot(parameters)
        return self._enqueue(self._coordinator.quote_prompt, snapshot, origin=origin)

    def quote_translate(self, parameters, *, origin):
        snapshot = _snapshot(parameters)
        return self._enqueue(self._coordinator.quote_translate, snapshot, origin=origin)

    def render_local(self, spec, *, origin, source_origin):
        """Use the existing queue; at most one local renderer occupies this owner."""
        from .local_render import RenderSpec

        if not isinstance(spec, RenderSpec):
            raise TypeError("Use a local render specification")
        return self._enqueue_local(
            self._coordinator.render_local, spec, origin=origin, source_origin=source_origin
        )

    def prepare_film_composition(self, recipe, *, production_id, mode, score_task_id, root, origin):
        return self._enqueue_local(
            self._coordinator.prepare_film_composition,
            _snapshot(recipe),
            production_id=production_id,
            mode=mode,
            score_task_id=score_task_id,
            root=os.fspath(root),
            origin=origin,
        )

    def prepare_film_review(
        self, recipe, *, production_id, mode, score_task_id, include_master, root, origin
    ):
        return self._enqueue_local(
            self._coordinator.prepare_film_review,
            _snapshot(recipe),
            production_id=production_id,
            mode=mode,
            score_task_id=score_task_id,
            include_master=include_master,
            root=os.fspath(root),
            origin=origin,
        )

    def _enqueue_local(self, command, *args, **kwargs):
        """Bound local render/inspection processes on the same existing worker pool."""
        with self._condition:
            if self._local_cancels:
                raise WorkerError("Wait for the current local media operation to finish")
            cancel = threading.Event()
            task = self._enqueue(command, *args, cancel=cancel, **kwargs)
            self._local_cancels[task] = cancel
            return task

    def cancel_local(self, task):
        with self._condition:
            cancel = self._local_cancels.get(task)
            if cancel is not None:
                cancel.set()

    def prepare_upload(
        self, source, *, origin, kind, content_type, mesh_source=None, expected_sha256=None
    ):
        return self._enqueue(
            self._coordinator.prepare_upload,
            os.fspath(source),
            origin=origin,
            kind=kind,
            content_type=content_type,
            mesh_source=mesh_source,
            expected_sha256=expected_sha256,
        )

    def initialize_upload(self, request_id, *, expected_revision):
        return self._enqueue(
            self._coordinator.initialize_upload, request_id, expected_revision=expected_revision
        )

    def cancel_prepared_upload(self, request_id, *, expected_revision):
        """Persist cancellation immediately, including when initialization is queued."""
        with self._condition:
            if not self._accepting:
                raise WorkerError("This job owner is inactive")
            return self._coordinator.cancel_prepared_upload(
                request_id, expected_revision=expected_revision
            )

    def transfer_upload_part(self, request_id, *, expected_revision):
        return self._enqueue(
            self._coordinator.transfer_upload_part, request_id, expected_revision=expected_revision
        )

    def finalize_upload(self, request_id, *, expected_revision):
        return self._enqueue(
            self._coordinator.finalize_upload, request_id, expected_revision=expected_revision
        )

    def refresh_upload(self, request_id, *, expected_revision):
        return self._enqueue(
            self._coordinator.refresh_upload, request_id, expected_revision=expected_revision
        )

    def discard_upload_source(self, request_id, *, expected_revision):
        return self._enqueue(
            self._coordinator.discard_upload_source, request_id, expected_revision=expected_revision
        )

    def submit(self, prepared, *, origin, operation, target_id, payload):
        """Queue an explicitly chosen paid action using an immutable payload copy."""
        snapshot = _snapshot(payload)
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

    def adopt_cloud_job(self, identifier, *, expected_model_id, origin):
        return self._enqueue(
            self._coordinator.adopt_cloud_job,
            identifier,
            expected_model_id=expected_model_id,
            origin=origin,
        )

    def read_prompt_results(self, request_id, *, expected_revision):
        return self._enqueue(
            self._coordinator.read_prompt_results, request_id, expected_revision=expected_revision
        )

    def read_model_text(self, request_id, *, expected_revision, asset_id):
        return self._enqueue(
            self._coordinator.read_model_text,
            request_id,
            expected_revision=expected_revision,
            asset_id=asset_id,
        )

    def load_results(self, request_id, *, expected_revision):
        return self._enqueue(
            self._coordinator.load_results, request_id, expected_revision=expected_revision
        )

    def download_results(self, request_id, *, expected_revision):
        return self._enqueue(
            self._coordinator.download_results, request_id, expected_revision=expected_revision
        )

    def verify_results(self, request_id, *, expected_revision):
        return self._enqueue(
            self._coordinator.verify_results, request_id, expected_revision=expected_revision
        )

    def recover_downloads(self, request_id, *, expected_revision):
        return self._enqueue(
            self._coordinator.recover_downloads, request_id, expected_revision=expected_revision
        )

    def cancel_remote(self, request_id, *, expected_revision):
        """Queue an explicit remote cancel request; its acknowledgement is not success."""
        return self._enqueue(
            self._coordinator.cancel_remote, request_id, expected_revision=expected_revision
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
                    with self._condition:
                        self._local_cancels.pop(task, None)
                    task._future.set_exception(exc)
                except BaseException as exc:
                    # Settle the handle and stop queued work before propagating
                    # thread-control exceptions; never leave a running future.
                    with self._condition:
                        self._local_cancels.pop(task, None)
                    task._future.set_exception(exc)
                    self.deactivate()
                    raise
                else:
                    with self._condition:
                        self._local_cancels.pop(task, None)
                    task._future.set_result(result)
                    del result
            # Do not retain payloads/results while the worker waits for more work.
            del task, command, args, kwargs

    def deactivate(self):
        """Stop admission/queued work promptly; in-flight work keeps its scope."""
        with self._condition:
            self._accepting = False
            for cancel in self._local_cancels.values():
                cancel.set()
            self._coordinator.deactivate()
            while self._pending:
                task, _, _, _ = self._pending.popleft()
                task._future.cancel()
                self._local_cancels.pop(task, None)
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


class ExportTask(JobTask):
    """A pollable export handle with thread-safe progress for the main-thread pump."""

    def __init__(self):
        super().__init__()
        self._progress_lock = threading.Lock()
        self._progress = ("queued", 0, 0)

    def _report(self, phase, done, total):
        with self._progress_lock:
            self._progress = (phase, done, total)

    def progress(self):
        """Return ``(phase, done, total)``; phases are queued, media, render, verify, publish."""
        with self._progress_lock:
            return self._progress


class LocalExportWorker:
    """Own one Film export thread at a time, outside the shared job workers.

    A multi-hour local encode never occupies a polling/download worker or the
    capture/review media slot. At most one export or re-publish runs per owner.
    Deactivation cancels it and reaps its child; shutdown joins its thread.
    """

    def __init__(self, coordinator: JobCoordinator):
        if not isinstance(coordinator, JobCoordinator):
            raise TypeError("Use the shared job coordinator")
        self._coordinator = coordinator
        self._lock = threading.Lock()
        self._accepting = True
        self._threads = []
        self._task = None
        self._cancel = None

    @property
    def stopped(self):
        with self._lock:
            return all(not thread.is_alive() for thread in self._threads)

    def export_film(self, spec, destination, *, origin, source_origin):
        from .local_export import ExportSpec

        if not isinstance(spec, ExportSpec):
            raise TypeError("Use a Film export specification")
        return self._start(
            self._coordinator.export_film,
            spec,
            os.fspath(destination),
            origin=origin,
            source_origin=source_origin,
        )

    def publish_film_export(self, staged, destination, *, origin, source_origin):
        from .local_export import StagedExport

        if not isinstance(staged, StagedExport):
            raise TypeError("Use a verified staged Film export")
        return self._start(
            self._coordinator.publish_film_export,
            staged,
            os.fspath(destination),
            origin=origin,
            source_origin=source_origin,
        )

    def _start(self, command, *args, **kwargs):
        with self._lock:
            if not self._accepting:
                raise WorkerError("This job owner is inactive")
            if self._task is not None and not self._task.done():
                raise WorkerError("Wait for the current Film export to finish")
            self._threads = [thread for thread in self._threads if thread.is_alive()]
            task, cancel = ExportTask(), threading.Event()
            thread = threading.Thread(
                target=self._run,
                args=(task, cancel, command, args, kwargs),
                name="ScenarioFilmExport",
            )
            thread.start()
            self._threads.append(thread)
            self._task, self._cancel = task, cancel
            return task

    @staticmethod
    def _run(task, cancel, command, args, kwargs):
        if not task._future.set_running_or_notify_cancel():
            return
        try:
            result = command(*args, cancel=cancel, progress=task._report, **kwargs)
        except BaseException as exc:
            task._future.set_exception(exc)
            if not isinstance(exc, Exception):
                raise
        else:
            task._future.set_result(result)

    def cancel(self, task):
        with self._lock:
            if task is self._task and self._cancel is not None:
                self._cancel.set()

    def deactivate(self):
        """Stop admission and cancel the running export; publishing never resumes."""
        with self._lock:
            self._accepting = False
            if self._cancel is not None:
                self._cancel.set()

    def shutdown(self):
        """Cancel and join the owned export thread; the child is reaped before it exits."""
        with self._lock:
            threads = tuple(self._threads)
        if threading.current_thread() in threads:
            raise WorkerError("An export thread cannot join its own owner")
        self.deactivate()
        for thread in threads:
            thread.join()
