# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Bounded application-owned workers for the shared job commands, without bpy."""

import json
import logging
import os
import threading
import time
from collections import deque
from concurrent.futures import Future
from pathlib import Path

from ..scene.splats import SplatOptions
from .coordinator import JobCoordinator, QuoteError, _payload

# A cancelled export terminates its child within about 0.1 s and kills it 3 s later.
EXPORT_STOP_TIMEOUT = 5.0


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

    Result previews use one dedicated lane thread with its own bounded queue, so
    preview polling and downloads never occupy the job workers used by remote
    refresh, result downloads and submissions.
    """

    def __init__(
        self, coordinator: JobCoordinator, *, workers=2, pending_limit=16, preview_limit=8
    ):
        if not isinstance(coordinator, JobCoordinator):
            raise TypeError("Use the shared job coordinator")
        for value in (workers, pending_limit, preview_limit):
            if not isinstance(value, int) or isinstance(value, bool) or value < 1:
                raise ValueError("Worker and pending limits must be positive integers")
        self._coordinator = coordinator
        self._limit = pending_limit
        self._condition = threading.Condition()
        self._pending = deque()
        self._local_cancels = {}
        self._accepting = True
        self._preview_limit = preview_limit
        self._preview_condition = threading.Condition()
        self._previews = deque()
        self._preview_cancels = {}
        self._preview_accepting = True
        self._preview_running = False
        self._closed = False
        self._shutdown_lock = threading.Lock()
        self._threads = [
            threading.Thread(target=self._run, name=f"ScenarioJob-{i}") for i in range(workers)
        ]
        self._threads.append(threading.Thread(target=self._run_previews, name="ScenarioPreview"))
        started = []
        try:
            for thread in self._threads:
                thread.start()
                started.append(thread)
        except BaseException:
            with self._condition:
                self._accepting = False
                self._condition.notify_all()
            with self._preview_condition:
                self._preview_accepting = False
                self._preview_condition.notify_all()
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

    @property
    def previews_idle(self):
        """Whether the preview lane has no queued or running command.

        A running SDK read or storage transfer can outlast its cancellation, so
        a main-thread owner checks this before ``shutdown`` joins the lane.
        """
        with self._preview_condition:
            return not self._previews and not self._preview_running

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

    def collection_page(self, **options):
        return self._enqueue(self._coordinator.collection_page, **_snapshot(options))

    def organization_snapshot(self, request):
        """Queue the read an organization review shows; requests are immutable."""
        return self._enqueue(self._coordinator.organization_snapshot, request)

    def organize(self, snapshot):
        """Queue one approved organization change; deactivation cancels it unsent."""
        return self._enqueue(self._coordinator.organize, snapshot)

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

    def _enqueue_preview(self, command, *args, **kwargs):
        """Admit one command to the dedicated preview lane, never the job workers."""
        with self._preview_condition:
            if not self._preview_accepting:
                raise WorkerError("This job owner is inactive")
            if len(self._previews) >= self._preview_limit:
                raise WorkerError("Preview queue is full; wait before adding more previews")
            cancel = threading.Event()
            task = JobTask()
            self._previews.append((task, command, args, {**kwargs, "cancel": cancel}))
            self._preview_cancels[task] = cancel
            self._preview_condition.notify()
            return task

    def prepare_result_previews(self, work, *, root, maintain=False):
        return self._enqueue_preview(
            self._coordinator.prepare_result_previews,
            tuple(work),
            root=os.fspath(root),
            maintain=maintain,
        )

    def maintain_result_previews(self, *, root):
        return self._enqueue_preview(
            self._coordinator.maintain_result_previews, root=os.fspath(root)
        )

    def finish_result_preview(self, request, *, root, envelope=None):
        return self._enqueue_preview(
            self._coordinator.finish_result_preview,
            request,
            root=os.fspath(root),
            envelope=envelope,
        )

    def decode_result_preview(self, request, *, root, waveform):
        """Queue an audio envelope decode; cancellation terminates its Blender child."""
        return self._enqueue_preview(
            self._coordinator.decode_result_preview,
            request,
            root=os.fspath(root),
            waveform=waveform,
        )

    def discard_result_preview(self, request, *, root):
        return self._enqueue_preview(
            self._coordinator.discard_result_preview, request, root=os.fspath(root)
        )

    def prepare_playback(
        self, request_id, *, expected_revision, asset_id, root, reuse=None, discard=(), keep=()
    ):
        """Queue a private player copy of one saved result on the preview lane."""
        return self._enqueue_preview(
            self._coordinator.prepare_playback,
            request_id,
            expected_revision=expected_revision,
            asset_id=asset_id,
            root=os.fspath(root),
            reuse=reuse,
            discard=tuple(os.fspath(path) for path in discard),
            keep=tuple(os.fspath(path) for path in keep),
        )

    def world_sizes(self, targets):
        """Queue a header read of saved World candidates on the preview lane."""
        return self._enqueue_preview(self._coordinator.world_sizes, tuple(targets))

    def result_files(self, targets):
        """Queue a rehash of saved results for status display on the preview lane."""
        return self._enqueue_preview(self._coordinator.result_files, tuple(targets))

    def cancel_preview(self, task):
        with self._preview_condition:
            cancel = self._preview_cancels.get(task)
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

    def restart_upload(self, request_id, *, expected_revision, origin):
        return self._enqueue(
            self._coordinator.restart_upload,
            request_id,
            expected_revision=expected_revision,
            origin=origin,
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

    def prepare_model_import(self, request_id, *, expected_revision, asset_id, options):
        """Decode one saved splat in the cancellable local-operation slot."""
        if not isinstance(options, SplatOptions):
            raise TypeError("Use reviewed splat options")
        return self._enqueue_local(
            self._coordinator.prepare_model_import,
            request_id,
            expected_revision=expected_revision,
            asset_id=asset_id,
            options=options,
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

    def decide_workflow_node(
        self, request_id, *, expected_revision, node_id, review_id, action, selected_indices=None
    ):
        """Queue one reviewed workflow-step decision; it is sent at most once."""
        picks = None if selected_indices is None else tuple(selected_indices)
        return self._enqueue(
            self._coordinator.decide_workflow_node,
            request_id,
            expected_revision=expected_revision,
            node_id=node_id,
            review_id=review_id,
            action=action,
            selected_indices=picks,
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

    def _run_previews(self):
        """The preview lane: one command at a time, independent of the job workers."""
        while True:
            with self._preview_condition:
                self._preview_condition.wait_for(
                    lambda: self._previews or not self._preview_accepting
                )
                if not self._previews:
                    return
                task, command, args, kwargs = self._previews.popleft()
                self._preview_running = True
            if task._future.set_running_or_notify_cancel():
                try:
                    result = command(*args, **kwargs)
                except Exception as exc:
                    self._finish_preview(task)
                    task._future.set_exception(exc)
                except BaseException as exc:
                    self._finish_preview(task)
                    task._future.set_exception(exc)
                    self.deactivate()
                    raise
                else:
                    self._finish_preview(task)
                    task._future.set_result(result)
                    del result
            else:
                self._finish_preview(task)
            del task, command, args, kwargs

    def _finish_preview(self, task):
        with self._preview_condition:
            self._preview_cancels.pop(task, None)
            self._preview_running = False

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
        with self._preview_condition:
            self._preview_accepting = False
            for cancel in self._preview_cancels.values():
                cancel.set()
            while self._previews:
                task, _, _, _ = self._previews.popleft()
                task._future.cancel()
                self._preview_cancels.pop(task, None)
            self._preview_condition.notify_all()

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


def _absolute(destination):
    """Refuse a relative export path before a thread starts; never use the working folder."""
    from .local_export import LocalExportError

    path = os.fspath(destination)
    if not isinstance(path, str) or not Path(path).is_absolute():
        raise LocalExportError("Choose an absolute destination path")
    return Path(path)


class LocalExportWorker:
    """Own one Film export thread at a time, outside the shared job workers.

    A multi-hour local encode never occupies a polling/download worker or the
    capture/review media slot. At most one video export, case-study export or
    re-publish runs per owner.
    Deactivation cancels it and reaps its child; shutdown waits a bounded time.
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
            _absolute(destination),
            origin=origin,
            source_origin=source_origin,
        )

    def export_case_study(self, spec, destination, *, origin, source_origin):
        from .local_case_study import CaseStudySpec

        if not isinstance(spec, CaseStudySpec):
            raise TypeError("Use a Film case-study specification")
        return self._start(
            self._coordinator.export_case_study,
            spec,
            _absolute(destination),
            origin=origin,
            source_origin=source_origin,
        )

    def publish_film_export(self, staged, destination, *, origin, source_origin):
        from .local_export import StagedFile

        if not isinstance(staged, StagedFile):
            raise TypeError("Use a verified staged Film export")
        return self._start(
            self._coordinator.publish_film_export,
            staged,
            _absolute(destination),
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
                # A read blocked on an unresponsive mount must not keep Blender open.
                daemon=True,
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
        """Cancel the owned export thread, then wait at most ``EXPORT_STOP_TIMEOUT`` seconds.

        Cancellation reaps the child, but a media or destination read blocked in
        the kernel cannot be interrupted. Such a thread is left running with a
        warning and ``stopped`` stays false until it finishes. At its next
        cancellation check it stops before starting a child or replacing the
        destination placeholder.
        """
        with self._lock:
            threads = tuple(self._threads)
        if threading.current_thread() in threads:
            raise WorkerError("An export thread cannot join its own owner")
        self.deactivate()
        deadline = time.monotonic() + EXPORT_STOP_TIMEOUT
        for thread in threads:
            thread.join(max(0.0, deadline - time.monotonic()))
        if any(thread.is_alive() for thread in threads):
            logging.getLogger("scenario.jobs").warning(
                "A cancelled Film export thread is still blocked on file access"
            )
