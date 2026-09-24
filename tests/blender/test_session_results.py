# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Installed session result delivery with SDK metadata and private offline bytes."""

import hashlib
import tempfile
import threading
import unittest
from concurrent.futures import ThreadPoolExecutor
from dataclasses import FrozenInstanceError, replace
from pathlib import Path

import bpy
import httpx
from helpers import addon_name, submodule


class SessionResultTests(unittest.TestCase):
    def setUp(self):
        self.module = submodule("blender.job_session")
        self.api = submodule("core.api.sdk_adapter")
        self.storage = submodule("core.jobs.store")
        self.results = submodule("core.jobs.results")
        self.transfers = submodule("core.jobs.transfers")
        directory = bpy.utils.extension_path_user(
            addon_name(), path="test-session-results", create=True
        )
        # Cleanup must retain the namespace used to access deep Windows results.
        self.temp = tempfile.TemporaryDirectory(dir=self.transfers._root(directory))
        self.addCleanup(self.temp.cleanup)
        # SQLite uses an ordinary file URI; both spellings name the same directory.
        self.root = (Path(directory) / Path(self.temp.name).name).resolve()
        self.assertTrue(self.root.samefile(self.temp.name))
        self.previous = bpy.context.scene
        self.scene = bpy.data.scenes.new("Result session fixture")
        bpy.context.window.scene = self.scene
        self.target = bpy.data.objects.new("Result target", None)
        self.scene.collection.objects.link(self.target)
        bpy.context.view_layer.update()
        self.scope = self.storage.JobScope(
            "https://fixture.invalid/v1", "fixture-account", "fixture-project"
        )
        self.store = self.storage.JobStore(self.root / "jobs.sqlite3", self.scope)
        self.body = b"offline verified session result"
        self.calls, self.downloads = [], []
        self.fail_download = False
        owner = self

        class OfflineDownloader(self.transfers.ResultDownloader):
            def download(self, url, *, root, name, **kwargs):
                owner.downloads.append(threading.current_thread())
                if owner.fail_download:
                    raise RuntimeError("private signed transport detail")
                with (root / name).open("xb") as target:
                    target.write(owner.body)
                return owner.transfers.DownloadedResult(
                    name, len(owner.body), hashlib.sha256(owner.body).hexdigest()
                )

        self.downloader = OfflineDownloader(
            self.transfers.StoragePolicy(frozenset({"storage.example.invalid"})),
            online_access=lambda: True,
        )
        self.session = self.new_session()
        origin = self.session.capture(self.scene, self.target)
        record = self.store.create(
            self.storage.JobIntent(
                "request",
                self.scope,
                origin,
                "model",
                "fixture-model",
                "a" * 64,
                "b" * 64,
                "1.0",
            )
        )
        for state in (
            self.storage.JobState.SUBMITTING,
            self.storage.JobState.REMOTE,
            self.storage.JobState.SUCCEEDED,
        ):
            record = self.store.transition(
                "request",
                expected_revision=record.revision,
                state=state,
                remote_job_id="remote" if state == self.storage.JobState.REMOTE else None,
            )
        self.record = record

    def tearDown(self):
        self.session.shutdown()
        if self.previous in tuple(bpy.data.scenes):
            bpy.context.window.scene = self.previous
        if self.target in tuple(bpy.data.objects):
            bpy.data.objects.remove(self.target, do_unlink=True)
        if self.scene in tuple(bpy.data.scenes):
            bpy.data.scenes.remove(self.scene)

    def respond(self, request):
        self.calls.append((request, threading.current_thread()))
        self.assertEqual(request.method, "GET")
        self.assertEqual(request.url.params["projectId"], self.scope.project_id)
        if request.url.path == "/v1/jobs/remote":
            return httpx.Response(
                200,
                json={
                    "job": {
                        "jobId": "remote",
                        "status": "success",
                        "metadata": {"assetIds": ["asset"]},
                    }
                },
            )
        self.assertEqual(request.url.path, "/v1/assets/asset")
        return httpx.Response(
            200,
            json={
                "asset": {
                    "id": "asset",
                    "status": "success",
                    "mimeType": "application/octet-stream",
                    "properties": {"size": len(self.body)},
                    "url": "https://storage.example.invalid/result?signature=fixture",
                }
            },
        )

    def new_adapter(self):
        return self.api.SDKAdapter(
            self.api.Credentials("fixture-key", "fixture-secret"),
            online=lambda: True,
            account_id=self.scope.account_id,
            project_id=self.scope.project_id,
            base_url=self.scope.service,
            transport=httpx.MockTransport(self.respond),
        )

    def new_session(self):
        return self.module.JobSession(
            self.new_adapter(),
            self.store,
            workers=1,
            result_downloader=self.downloader,
            result_root=self.root,
        )

    def command(self, name, record):
        result = getattr(self.session, name)(
            record.intent.request_id, expected_revision=record.revision
        ).result(5)
        completion = self.session.drain()[0]
        self.assertIsNone(completion.error)
        self.assertEqual(completion.origin, self.record.intent.origin)
        return result, completion

    def ready(self):
        return self.command("download_results", self.record)[0]

    def test_manifest_download_and_verified_paths_deliver_to_original_target_once(self):
        manifest, _ = self.command("load_results", self.record)
        self.assertEqual(len(manifest.results), 1)
        ready, _ = self.command("download_results", manifest)
        verified, completion = self.command("verify_results", ready)
        self.assertIsInstance(verified, self.results.VerifiedResults)
        self.assertIsInstance(verified.paths, tuple)
        self.assertEqual(verified.paths[0].read_bytes(), self.body)
        with self.assertRaises(FrozenInstanceError):
            verified.paths = ()
        self.assertEqual(verified.record.intent, self.record.intent)
        self.assertEqual(len(self.calls), 3)
        self.assertEqual(len(self.downloads), 1)
        self.assertTrue(all(thread is not threading.main_thread() for _, thread in self.calls))
        self.assertIsNot(self.downloads[0], threading.main_thread())
        applied = self.session.deliver(
            completion,
            lambda result, scene, target: (result.paths, scene, target, threading.current_thread()),
        )
        self.assertEqual(
            applied, (verified.paths, self.scene, self.target, threading.main_thread())
        )
        self.assertEqual(self.store.get("request").state, self.storage.JobState.READY)
        with self.assertRaises(self.module.OriginUnavailable):
            self.session.deliver(completion, lambda *args: self.fail("Delivered twice"))

    def test_switched_scene_and_restarted_origin_cannot_deliver_verified_paths(self):
        ready = self.ready()
        bpy.context.window.scene = self.previous
        _, completion = self.command("verify_results", ready)
        with self.assertRaises(self.module.OriginUnavailable):
            self.session.deliver(completion, lambda *args: self.fail("Applied in another scene"))
        self.session.shutdown()
        bpy.context.window.scene = self.scene
        self.session = self.new_session()
        verified, completion = self.command("verify_results", ready)
        self.assertEqual(verified.paths[0].read_bytes(), self.body)
        with self.assertRaises(self.module.OriginUnavailable):
            self.session.deliver(completion, lambda *args: self.fail("Rebound a restarted target"))

    def test_failed_download_and_changed_bytes_do_not_retry_or_generate(self):
        self.fail_download = True
        failed = self.session.download_results("request", expected_revision=self.record.revision)
        with self.assertRaises(self.results.ResultError):
            failed.result(5)
        completion = self.session.drain()[0]
        self.assertIsInstance(completion.error, self.results.ResultError)
        self.assertNotIn("private signed", str(completion.error))
        current = self.store.get("request")
        self.assertEqual(current.state, self.storage.JobState.DOWNLOAD_FAILED)
        self.assertEqual(len(self.downloads), 1)
        self.fail_download = False
        ready, _ = self.command("download_results", current)
        verified, _ = self.command("verify_results", ready)
        verified.paths[0].write_bytes(b"changed")
        before = len(self.calls), len(self.downloads)
        task = self.session.verify_results("request", expected_revision=ready.revision)
        with self.assertRaises(self.results.ResultError):
            task.result(5)
        self.assertIsInstance(self.session.drain()[0].error, self.results.ResultError)
        self.assertEqual((len(self.calls), len(self.downloads)), before)
        self.assertEqual(self.store.get("request"), ready)

    def test_verified_result_with_foreign_scope_is_rejected_at_drain(self):
        ready = self.ready()
        verified, _ = self.command("verify_results", ready)
        foreign = replace(
            verified,
            record=replace(
                ready, intent=replace(ready.intent, scope=replace(self.scope, account_id="other"))
            ),
        )
        task = submodule("core.jobs.workers").JobTask()
        task._future.set_result(foreign)
        self.session._pending.append((task, ready.intent.origin))
        self.assertIsInstance(self.session.drain()[0].error, self.module.OriginUnavailable)

    def test_result_commands_reject_worker_entry_and_unconfigured_storage(self):
        with ThreadPoolExecutor(max_workers=1) as pool:
            for name in ("load_results", "download_results", "verify_results"):
                future = pool.submit(
                    getattr(self.session, name), "request", expected_revision=self.record.revision
                )
                with self.assertRaisesRegex(RuntimeError, "main thread"):
                    future.result(5)
        self.assertEqual(self.calls, [])
        self.session.shutdown()
        self.session = self.module.JobSession(self.new_adapter(), self.store, workers=1)
        task = self.session.download_results("request", expected_revision=self.record.revision)
        with self.assertRaises(self.results.ResultError):
            task.result(5)
        self.assertEqual(self.store.get("request"), self.record)
        self.assertEqual(self.calls, [])

    def test_incomplete_storage_policy_fails_before_starting_workers(self):
        before = set(threading.enumerate())
        for options in ({"result_root": self.root}, {"result_downloader": self.downloader}):
            with self.new_adapter() as adapter:
                with self.assertRaises(ValueError):
                    self.module.JobSession(adapter, self.store, **options)
        self.assertEqual(set(threading.enumerate()), before)
