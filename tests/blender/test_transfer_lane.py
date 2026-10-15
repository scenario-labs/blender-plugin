# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Installed transfer lane: polls and cancels progress beside a large loopback download."""

import hashlib
import json
import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest.mock import patch

import bpy
import httpx
import test_model_generation as model_tests
from helpers import LoopbackStorage, addon_name, submodule

# Large enough to outlast the checks below by a wide margin at the throttled rate.
SIZE = 96 * 1024 * 1024


class TransferLaneTests(unittest.TestCase):
    def setUp(self):
        self.module = submodule("blender.job_session")
        self.api = submodule("core.api.sdk_adapter")
        self.storage = submodule("core.jobs.store")
        self.results = submodule("core.jobs.results")
        self.transfers = submodule("core.jobs.transfers")
        directory = bpy.utils.extension_path_user(
            addon_name(), path="test-transfer-lane", create=True
        )
        self.temp = tempfile.TemporaryDirectory(dir=self.transfers._root(directory))
        self.addCleanup(self.temp.cleanup)
        base = (Path(directory) / Path(self.temp.name).name).resolve()
        self.root = base / "results"
        self.root.mkdir()
        self.previous = bpy.context.scene
        self.scene = bpy.data.scenes.new("Transfer lane fixture")
        bpy.context.window.scene = self.scene
        self.scope = self.storage.JobScope(
            "https://fixture.invalid/v1", "fixture-account", "fixture-project"
        )
        self.store = self.storage.JobStore(base / "jobs.sqlite3", self.scope)
        self.calls = []
        self.canceled = False
        self.session = self.module.JobSession(
            self.api.SDKAdapter(
                self.api.Credentials("fixture-key", "fixture-secret"),
                online=lambda: True,
                account_id=self.scope.account_id,
                project_id=self.scope.project_id,
                base_url=self.scope.service,
                transport=httpx.MockTransport(self.respond),
            ),
            self.store,
            # One job worker: before the transfer lane, the download occupied it.
            workers=1,
            result_downloader=self.transfers.ResultDownloader(
                self.transfers.StoragePolicy(frozenset({"storage.example.invalid"})),
                online_access=lambda: True,
            ),
            result_root=self.root,
        )
        origin = self.session.capture(self.scene)
        self.download = self.record(origin, "download", "remote-download", final="succeeded")
        self.other = self.record(origin, "other", "remote-other", final="remote")

    def tearDown(self):
        self.session.shutdown()
        if self.previous in tuple(bpy.data.scenes):
            bpy.context.window.scene = self.previous
        if self.scene in tuple(bpy.data.scenes):
            bpy.data.scenes.remove(self.scene)

    def record(self, origin, request_id, remote_id, *, final):
        record = self.store.create(
            self.storage.JobIntent(
                request_id,
                self.scope,
                origin,
                "model",
                "fixture-model",
                "a" * 64,
                "b" * 64,
                "1.0",
            )
        )
        states = [self.storage.JobState.SUBMITTING, self.storage.JobState.REMOTE]
        if final == "succeeded":
            states.append(self.storage.JobState.SUCCEEDED)
        for state in states:
            record = self.store.transition(
                request_id,
                expected_revision=record.revision,
                state=state,
                remote_job_id=remote_id if state == self.storage.JobState.REMOTE else None,
            )
        return record

    def respond(self, request):
        self.calls.append((request.method, request.url.path, threading.current_thread().name))
        if request.method == "POST":
            self.canceled = True
            return httpx.Response(
                200, json={"job": {"jobId": "remote-other", "status": "canceled"}}
            )
        if request.url.path == "/v1/jobs/remote-download":
            return httpx.Response(
                200,
                json={
                    "job": {
                        "jobId": "remote-download",
                        "status": "success",
                        "metadata": {"assetIds": ["asset-large"]},
                    }
                },
            )
        if request.url.path == "/v1/jobs/remote-other":
            status = "canceled" if self.canceled else "in-progress"
            return httpx.Response(
                200,
                json={"job": {"jobId": "remote-other", "jobType": "inference", "status": status}},
            )
        self.assertEqual(request.url.path, "/v1/assets/asset-large")
        return httpx.Response(
            200,
            json={
                "asset": {
                    "id": "asset-large",
                    "status": "success",
                    "mimeType": "application/octet-stream",
                    "properties": {"size": SIZE},
                    "url": "https://storage.example.invalid/large?signature=fixture",
                }
            },
        )

    def loopback(self, **options):
        """Serve the downloader's storage connection from a loopback server instead."""
        server = LoopbackStorage(SIZE, **options)
        self.addCleanup(server.close)
        return server, patch.object(self.transfers.http.client, "HTTPSConnection", server.connect)

    def assert_stopped_without_receipt(self):
        failed = self.store.get("download")
        self.assertEqual(failed.state, self.storage.JobState.DOWNLOAD_FAILED)
        self.assertIsNone(failed.results[0].receipt)
        self.assertEqual([path for path in self.root.rglob("*") if path.is_file()], [])
        self.assertEqual(list(self.root.rglob(".scenario-download-*")), [])

    def test_poll_and_cancel_progress_while_a_large_download_runs_then_it_cancels(self):
        state = self.storage.JobState
        server, redirect = self.loopback()
        with redirect:
            task = self.session.download_results(
                "download", expected_revision=self.download.revision
            )
            self.assertTrue(server.streaming.wait(15), "The download did not start")
            self.assertEqual(self.store.get("download").state, state.DOWNLOADING)
            # A status poll of another job completes while the download streams.
            polled = self.session.refresh_remote("other", expected_revision=self.other.revision)
            snapshot = polled.result(10)
            self.assertEqual(snapshot.record.state, state.REMOTE)
            self.assertFalse(task.done())
            # So does an explicit remote cancellation of that job.
            current = self.store.get("other")
            canceled = self.session.cancel_remote("other", expected_revision=current.revision)
            self.assertEqual(canceled.result(10).record.state, state.CANCELED)
            self.assertFalse(task.done(), "The download finished before the checks")
            # Canceling the download stops it promptly, unpublished and unreceipted.
            started = time.monotonic()
            self.session.cancel_download(task)
            with self.assertRaisesRegex(self.results.ResultError, "canceled"):
                task.result(10)
            self.assertLess(time.monotonic() - started, 5)
        self.session.drain()
        self.assert_stopped_without_receipt()
        self.assertTrue(server.closed.wait(5), "The canceled transfer kept its connection")
        self.assertEqual(len(server.requests), 1)
        self.assertEqual(len(server.threads), 1)
        self.assertTrue(server.threads[0].startswith("ScenarioTransfer"), server.threads)
        sdk_threads = {name for method, path, name in self.calls if "remote-other" in path}
        self.assertTrue(sdk_threads and all(name.startswith("ScenarioJob") for name in sdk_threads))

    def test_cancel_interrupts_a_download_blocked_on_a_silent_server(self):
        # Headers and 2 MiB arrive, then nothing. Body reads wait at most half a
        # second at a time, so cancellation does not wait for the 30-second
        # socket timeout on any operating system.
        server, redirect = self.loopback(silent_after=2 * 1024 * 1024)
        with redirect:
            task = self.session.download_results(
                "download", expected_revision=self.download.revision
            )
            self.assertTrue(server.streaming.wait(15), "The download did not start")
            time.sleep(0.5)  # Let the transfer drain the sent bytes and block.
            self.assertFalse(task.done())
            started = time.monotonic()
            self.session.cancel_download(task)
            with self.assertRaisesRegex(self.results.ResultError, "canceled"):
                task.result(10)
            self.assertLess(time.monotonic() - started, 5)
        self.session.drain()
        self.assert_stopped_without_receipt()
        # Canceled, never retried: one storage request.
        self.assertEqual(len(server.requests), 1)

    def test_retiring_the_session_stops_an_in_flight_download(self):
        server, redirect = self.loopback()
        with redirect:
            task = self.session.download_results(
                "download", expected_revision=self.download.revision
            )
            self.assertTrue(server.streaming.wait(15), "The download did not start")
            started = time.monotonic()
            # A credential change or file load retires the session the same way.
            self.session.deactivate()
            with self.assertRaises(self.results.ResultError):
                task.result(10)
            self.assertLess(time.monotonic() - started, 5)
        self.assert_stopped_without_receipt()


class StopDownloadTests(unittest.TestCase):
    """The Stop download action through ModelJobs.control, natively and over MCP."""

    generation = model_tests.ModelGenerationTests
    cleanup_jobs = generation.cleanup_jobs
    result_fixture = generation.result_fixture
    settle = generation.settle
    deliver_results = generation.deliver_results
    mcp_quote = generation.mcp_quote
    mcp_submit = generation.mcp_submit
    mcp_call = generation.mcp_call
    recovery_args = generation.recovery_args
    recover = generation.recover

    def setUp(self):
        model_tests.ModelGenerationTests.setUp(self)
        self.result_fixture()
        self.loopback = LoopbackStorage(16 * 1024 * 1024)
        self.addCleanup(self.loopback.close)
        # The asset size now describes the loopback body: zero bytes, slowly.
        self.result_bytes = bytes(self.loopback.size)
        transfers = submodule("core.jobs.transfers")
        self.enterContext(
            patch.object(transfers.http.client, "HTTPSConnection", self.loopback.connect)
        )
        self.model_jobs = submodule("blender.model_jobs")

    def downloading(self):
        """Submit a job and poll until this session's own download is streaming."""
        request_id = self.mcp_submit(self.mcp_quote())["local_id"]
        deadline = time.monotonic() + 15
        while True:
            self.runtime.sync_catalog_context()
            status = self.tools.job_status({"job_id": request_id})
            if self.loopback.streaming.is_set() and "stop_download" in status["actions"]:
                return request_id, status
            self.assertLess(time.monotonic(), deadline, status)
            time.sleep(0.05)

    def test_stop_download_natively_and_over_mcp_then_resume_restarts_it(self):
        state = self.storemod.JobState
        for route in ("native", "mcp"):
            with self.subTest(route=route):
                request_id, status = self.downloading()
                owner = self.runtime.state.model_jobs
                self.assertEqual(status["status"], "downloading")
                self.assertEqual(list(status["actions"]), ["stop_download"])
                command, task = owner._commands[request_id]
                self.assertEqual(command, "download_results")
                args = self.recovery_args(request_id, "stop_download")
                if route == "native":
                    # The Jobs row and saved-job card draw this descriptor's button.
                    recovery = submodule("blender.job_recovery")
                    # One more poll projects the view the Jobs panel draws.
                    self.runtime.sync_catalog_context()
                    view = owner.views[request_id]
                    (item,) = [
                        i for i in recovery.result_actions(view) if i.action == "stop_download"
                    ]
                    self.assertEqual(
                        (item.label, item.group, item.operator),
                        ("Stop download", "cancel", "scenario.recover_job"),
                    )
                    self.assertEqual(dict(item.properties), args)
                    self.assertEqual(
                        bpy.ops.scenario.recover_job(**dict(item.properties)), {"FINISHED"}
                    )
                    self.assertEqual(
                        self.runtime.state.last_message,
                        "Stopping the download; Resume download starts it again",
                    )
                else:
                    result = self.mcp_call("recover_local_job", args)
                    self.assertFalse(result.get("isError"), result)
                    stopped = json.loads(result["content"][0]["text"])
                    self.assertNotIn("stop_download", stopped["actions"])
                with self.assertRaises(self.results_error):
                    task.result(5)
                self.runtime.sync_catalog_context()
                status = self.tools.job_status({"job_id": request_id})
                self.assertEqual(status["status"], "download_failed")
                self.assertEqual(status["error"], self.model_jobs.DOWNLOAD_STOPPED)
                self.assertIn("resume", status["actions"])
                self.assertNotIn("stop_download", status["actions"])
                self.assertFalse(status["results"][0]["downloaded"])
                record = self.store.get(request_id)
                self.assertEqual(record.state, state.DOWNLOAD_FAILED)
                self.assertIsNone(record.results[0].receipt)
                # Stopping is never offered again for the stopped job.
                with self.assertRaises(self.request_error):
                    owner.control(request_id, record.revision, "stop_download")
        self.assertEqual(set(self.loopback.hosts), {"cdn.cloud.scenario.com"})
        self.assertTrue(all(name.startswith("ScenarioTransfer") for name in self.loopback.threads))
        # Resume downloads the stopped job again from zero and completes it.
        self.loopback.fast.set()
        requests = len(self.loopback.requests)
        self.recover(request_id, "resume")
        self.deliver_results()
        record = self.store.get(request_id)
        self.assertEqual(record.state, state.READY)
        self.assertEqual(
            record.results[0].receipt.sha256, hashlib.sha256(self.result_bytes).hexdigest()
        )
        self.assertEqual(len(self.loopback.requests), requests + 1)
        # Two generations were sent and none was repeated.
        self.assertEqual(len(self.paid), 2)

    def test_a_real_failure_at_stop_time_is_not_shown_as_a_stop(self):
        results = submodule("core.jobs.results")
        coordinator = self.runtime.ensure_job_session()._coordinator
        real = coordinator.download_results

        def coincidental(request_id, *, expected_revision, cancel):
            # The transfer ends just as the user stops it, but for another reason.
            try:
                return real(request_id, expected_revision=expected_revision, cancel=cancel)
            except results.DownloadCanceled:
                raise results.ResultError(
                    "Result download did not complete; review saved files before retrying"
                ) from None

        self.enterContext(patch.object(coordinator, "download_results", coincidental))
        request_id, _ = self.downloading()
        owner = self.runtime.state.model_jobs
        task = owner._commands[request_id][1]
        owner.control(request_id, self.store.get(request_id).revision, "stop_download")
        with self.assertRaises(self.results_error):
            task.result(5)
        self.runtime.sync_catalog_context()
        status = self.tools.job_status({"job_id": request_id})
        self.assertEqual(status["status"], "download_failed")
        self.assertNotEqual(status["error"], self.model_jobs.DOWNLOAD_STOPPED)
        self.assertEqual(
            status["error"], "Result delivery stopped; review the saved job before retrying"
        )

    @property
    def results_error(self):
        return submodule("core.jobs.results").ResultError
