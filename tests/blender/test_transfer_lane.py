# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Installed transfer lane: polls and cancels progress beside a large loopback download."""

import http.client
import http.server
import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest.mock import patch

import bpy
import httpx
from helpers import addon_name, submodule

# Large enough to outlast the checks below by a wide margin at the throttled rate.
SIZE = 96 * 1024 * 1024
CHUNK = 64 * 1024


class StorageHandler(http.server.BaseHTTPRequestHandler):
    """A loopback stand-in for signed storage that streams a synthetic body slowly."""

    def do_GET(self):
        server = self.server
        server.requests.append(self.path)
        self.send_response(200)
        self.send_header("Content-Length", str(SIZE))
        self.send_header("ETag", '"loopback-fixture"')
        self.send_header("Connection", "close")
        self.end_headers()
        sent, chunk = 0, b"\0" * CHUNK
        try:
            while sent < SIZE and not server.stop.is_set():
                self.wfile.write(chunk)
                sent += CHUNK
                server.sent = sent
                if sent >= 1024 * 1024:
                    server.streaming.set()
                # About 3 MiB/s: the whole body would take about 30 seconds.
                time.sleep(0.02)
        except OSError:
            # The client closed the connection: the download was canceled.
            server.closed.set()

    def log_message(self, *args):
        pass


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
        self.server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), StorageHandler)
        self.server.daemon_threads = True
        self.server.requests, self.server.sent = [], 0
        self.server.stop, self.server.streaming = threading.Event(), threading.Event()
        self.server.closed = threading.Event()
        thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        thread.start()
        self.addCleanup(thread.join, 5)
        self.addCleanup(self.server.server_close)
        self.addCleanup(self.server.shutdown)
        self.addCleanup(self.server.stop.set)
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
        self.server.stop.set()
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

    def loopback(self):
        """Send the downloader's storage connection to the loopback server instead."""
        port = self.server.server_address[1]
        threads = []

        def connect(host, *, timeout, context):
            self.assertEqual(host, "storage.example.invalid")
            threads.append(threading.current_thread().name)
            return http.client.HTTPConnection("127.0.0.1", port, timeout=timeout)

        return patch.object(self.transfers.http.client, "HTTPSConnection", connect), threads

    def test_poll_and_cancel_progress_while_a_large_download_runs_then_it_cancels(self):
        state = self.storage.JobState
        redirect, threads = self.loopback()
        with redirect:
            task = self.session.download_results(
                "download", expected_revision=self.download.revision
            )
            self.assertTrue(self.server.streaming.wait(15), "The download did not start")
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
            self.assertLess(self.server.sent, SIZE)
            # Canceling the download stops it promptly, unpublished and unreceipted.
            started = time.monotonic()
            self.session.cancel_download(task)
            with self.assertRaisesRegex(self.results.ResultError, "canceled"):
                task.result(10)
            self.assertLess(time.monotonic() - started, 5)
        self.session.drain()
        failed = self.store.get("download")
        self.assertEqual(failed.state, state.DOWNLOAD_FAILED)
        self.assertIsNone(failed.results[0].receipt)
        self.assertEqual([path for path in self.root.rglob("*") if path.is_file()], [])
        self.assertEqual(list(self.root.rglob(".scenario-download-*")), [])
        self.assertTrue(self.server.closed.wait(5), "The canceled transfer kept its connection")
        self.assertEqual(len(self.server.requests), 1)
        self.assertEqual(len(threads), 1)
        self.assertTrue(threads[0].startswith("ScenarioTransfer"), threads)
        sdk_threads = {name for method, path, name in self.calls if "remote-other" in path}
        self.assertTrue(sdk_threads and all(name.startswith("ScenarioJob") for name in sdk_threads))

    def test_retiring_the_session_stops_an_in_flight_download(self):
        state = self.storage.JobState
        redirect, _ = self.loopback()
        with redirect:
            task = self.session.download_results(
                "download", expected_revision=self.download.revision
            )
            self.assertTrue(self.server.streaming.wait(15), "The download did not start")
            started = time.monotonic()
            # A credential change or file load retires the session the same way.
            self.session.deactivate()
            with self.assertRaises(self.results.ResultError):
                task.result(10)
            self.assertLess(time.monotonic() - started, 5)
        failed = self.store.get("download")
        self.assertEqual(failed.state, state.DOWNLOAD_FAILED)
        self.assertIsNone(failed.results[0].receipt)
        self.assertEqual([path for path in self.root.rglob("*") if path.is_file()], [])
        self.assertEqual(list(self.root.rglob(".scenario-download-*")), [])
