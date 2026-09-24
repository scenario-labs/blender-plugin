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
from unittest.mock import patch

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
        self.before_worlds, self.before_images = set(bpy.data.worlds), set(bpy.data.images)
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
        self.media_type = "application/octet-stream"
        self.asset_ids = ["asset"]
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
        for world in set(bpy.data.worlds) - self.before_worlds:
            bpy.data.worlds.remove(world, do_unlink=True)
        for image in set(bpy.data.images) - self.before_images:
            bpy.data.images.remove(image, do_unlink=True)

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
                        "metadata": {"assetIds": self.asset_ids},
                    }
                },
            )
        asset_id = request.url.path.removeprefix("/v1/assets/")
        self.assertIn(asset_id, self.asset_ids)
        return httpx.Response(
            200,
            json={
                "asset": {
                    "id": asset_id,
                    "status": "success",
                    "mimeType": self.media_type,
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

    def test_reopened_ready_job_reports_missing_storage_without_changing_record(self):
        ready = self.ready()
        self.session.shutdown()
        self.store = self.storage.JobStore(self.root / "jobs.sqlite3", self.scope)
        self.session = self.module.JobSession(self.new_adapter(), self.store, workers=1)
        before = len(self.calls), len(self.downloads)
        task = self.session.verify_results("request", expected_revision=ready.revision)
        with self.assertRaisesRegex(self.results.ResultError, "storage has not been configured"):
            task.result(5)
        completion = self.session.drain()[0]
        self.assertIsInstance(completion.error, self.results.ResultError)
        self.assertEqual(str(completion.error), "Result storage has not been configured")
        self.assertEqual(self.store.get("request"), ready)
        self.assertEqual(self.store.get("request").revision, ready.revision)
        self.assertEqual((len(self.calls), len(self.downloads)), before)

    def world_completion(self):
        image = bpy.data.images.new("Session panorama", width=4, height=2)
        try:
            image.pixels[:] = [0.5, 0.25, 0.125, 1.0] * 8
            image.file_format = "PNG"
            image.filepath_raw = str(self.root / "panorama.png")
            image.save()
            self.body = (self.root / "panorama.png").read_bytes()
        finally:
            bpy.data.images.remove(image)
        self.media_type = "image/png"
        ready = self.ready()
        return self.command("verify_results", ready)

    def test_world_application_claims_before_mutation_and_preserves_restoration(self):
        verified, completion = self.world_completion()
        original = self.scene.world
        calls = len(self.calls), len(self.downloads)
        apply = self.module.apply_world

        def checked(scene, path, **kwargs):
            self.assertEqual(self.store.get("request").state, self.storage.JobState.APPLYING)
            self.assertEqual(scene, self.scene)
            self.assertEqual(path, verified.paths[0])
            self.assertEqual(kwargs["expected_receipt"], verified.record.results[0].receipt)
            self.assertIs(threading.current_thread(), threading.main_thread())
            return apply(scene, path, **kwargs)

        with patch.object(self.module, "apply_world", side_effect=checked):
            outcome = self.session.apply_world(completion, asset_id="asset")
        self.assertEqual(outcome.record, self.store.get("request"))
        self.assertEqual(outcome.record.state, self.storage.JobState.APPLIED)
        self.assertEqual(outcome.record.intent, self.record.intent)
        self.assertNotEqual(self.scene.world, original)
        self.assertEqual((len(self.calls), len(self.downloads)), calls)
        with self.assertRaises(self.module.OriginUnavailable):
            self.session.apply_world(completion, asset_id="asset")
        self.assertTrue(outcome.application.restore())
        self.assertEqual(self.scene.world, original)
        self.assertEqual(self.store.get("request").state, self.storage.JobState.APPLIED)

    def test_world_application_selects_exactly_one_of_multiple_results(self):
        self.asset_ids = ["asset", "second"]
        verified, completion = self.world_completion()
        with patch.object(self.module, "apply_world", wraps=self.module.apply_world) as apply:
            outcome = self.session.apply_world(completion, asset_id="second")
        apply.assert_called_once_with(
            self.scene, verified.paths[1], expected_receipt=verified.record.results[1].receipt
        )
        self.assertTrue(outcome.application.restore())

    def test_world_receipt_failure_allows_only_fresh_verified_local_retry(self):
        verified, completion = self.world_completion()
        verified.paths[0].write_bytes(self.body[:-1] + bytes([self.body[-1] ^ 1]))
        before = set(bpy.data.worlds), set(bpy.data.images)
        calls = len(self.calls), len(self.downloads)
        with self.assertRaises(self.module.WorldApplicationError):
            self.session.apply_world(completion, asset_id="asset")
        failed = self.store.get("request")
        self.assertEqual(failed.state, self.storage.JobState.APPLY_FAILED)
        self.assertEqual((set(bpy.data.worlds), set(bpy.data.images)), before)
        with self.assertRaises(self.module.OriginUnavailable):
            self.session.apply_world(completion, asset_id="asset")
        verified.paths[0].write_bytes(self.body)
        _, fresh = self.command("verify_results", failed)
        outcome = self.session.apply_world(fresh, asset_id="asset")
        self.assertEqual(outcome.record.state, self.storage.JobState.APPLIED)
        self.assertEqual((len(self.calls), len(self.downloads)), calls)
        outcome.application.restore()

    def test_world_requires_owned_verification_and_explicit_saved_asset(self):
        verified, completion = self.world_completion()
        for invalid in (None, True, object()):
            with self.assertRaises(self.module.OriginUnavailable):
                self.session.apply_world(invalid, asset_id="asset")
        foreign = self.new_session()
        try:
            with self.assertRaises(self.module.OriginUnavailable):
                foreign.apply_world(completion, asset_id="asset")
        finally:
            foreign.shutdown()
        with self.assertRaises(self.module.OriginUnavailable):
            self.session.apply_world(replace(completion), asset_id="asset")
        with self.assertRaises(self.module.OriginUnavailable):
            self.session.apply_world(completion, asset_id="missing")
        self.assertEqual(self.store.get("request"), verified.record)
        outcome = self.session.apply_world(completion, asset_id="asset")
        outcome.application.restore()

    def test_world_rejects_unverified_and_failed_completions(self):
        ready, completion = self.command("download_results", self.record)
        with self.assertRaises(self.module.OriginUnavailable):
            self.session.apply_world(completion, asset_id="asset")
        self.assertEqual(self.store.get("request"), ready)
        task = self.session.verify_results("request", expected_revision=-1)
        with self.assertRaises(self.storage.StoreConflict):
            task.result(5)
        failed = self.session.drain()[0]
        with self.assertRaises(self.storage.StoreConflict):
            self.session.apply_world(failed, asset_id="asset")

    def test_world_rejects_switched_scene_worker_and_invalidated_origin(self):
        verified, completion = self.world_completion()
        with ThreadPoolExecutor(max_workers=1) as pool:
            task = pool.submit(self.session.apply_world, completion, asset_id="asset")
            with self.assertRaisesRegex(RuntimeError, "main thread"):
                task.result(5)
        bpy.context.window.scene = self.previous
        with self.assertRaises(self.module.OriginUnavailable):
            self.session.apply_world(completion, asset_id="asset")
        bpy.context.window.scene = self.scene
        self.session.invalidate_scene(self.scene)
        with self.assertRaises(self.module.OriginUnavailable):
            self.session.apply_world(completion, asset_id="asset")
        self.assertEqual(self.store.get("request"), verified.record)

    def test_world_does_not_rebind_deleted_target_or_restarted_origin(self):
        verified, completion = self.world_completion()
        name = self.target.name
        bpy.data.objects.remove(self.target, do_unlink=True)
        self.target = bpy.data.objects.new(name, None)
        self.scene.collection.objects.link(self.target)
        with self.assertRaises(self.module.OriginUnavailable):
            self.session.apply_world(completion, asset_id="asset")
        self.session.shutdown()
        self.session = self.new_session()
        _, restarted = self.command("verify_results", verified.record)
        with self.assertRaises(self.module.OriginUnavailable):
            self.session.apply_world(restarted, asset_id="asset")
        self.assertEqual(self.store.get("request"), verified.record)

    def test_world_arbitrary_failure_remains_uncertain_without_replay(self):
        _, completion = self.world_completion()
        with patch.object(self.module, "apply_world", side_effect=RuntimeError("private detail")):
            with self.assertRaises(self.module.WorldResultUncertain) as caught:
                self.session.apply_world(completion, asset_id="asset")
        self.assertNotIn("private detail", str(caught.exception))
        self.assertIsNone(caught.exception.application)
        self.assertEqual(self.store.get("request").state, self.storage.JobState.APPLYING)
        with self.assertRaises(self.module.OriginUnavailable):
            self.session.apply_world(completion, asset_id="asset")

    def test_world_control_failure_preserves_uncertain_durable_claim(self):
        _, completion = self.world_completion()
        with patch.object(self.module, "apply_world", side_effect=KeyboardInterrupt):
            with self.assertRaises(KeyboardInterrupt):
                self.session.apply_world(completion, asset_id="asset")
        self.assertEqual(self.store.get("request").state, self.storage.JobState.APPLYING)

    def test_world_failed_cleanup_is_not_a_confirmed_rollback(self):
        _, completion = self.world_completion()

        def failed(*args, **kwargs):
            bpy.data.worlds.new("Uncertain orphan")
            raise self.module.WorldApplicationError("fixture cleanup failure")

        with patch.object(self.module, "apply_world", side_effect=failed):
            with self.assertRaises(self.module.WorldResultUncertain):
                self.session.apply_world(completion, asset_id="asset")
        self.assertEqual(self.store.get("request").state, self.storage.JobState.APPLYING)

    def test_world_changed_binding_is_not_a_confirmed_rollback(self):
        _, completion = self.world_completion()
        replacement = bpy.data.worlds.new("Existing replacement")

        def failed(*args, **kwargs):
            self.scene.world = replacement
            raise self.module.WorldApplicationError("fixture rollback failure")

        with patch.object(self.module, "apply_world", side_effect=failed):
            with self.assertRaises(self.module.WorldResultUncertain):
                self.session.apply_world(completion, asset_id="asset")
        self.assertEqual(self.store.get("request").state, self.storage.JobState.APPLYING)
        self.assertEqual(self.scene.world, replacement)

    def test_world_completion_write_failure_retains_applied_restoration_handle(self):
        _, completion = self.world_completion()
        with patch.object(
            self.session._coordinator,
            "complete_application",
            side_effect=self.storage.StoreError("private persistence detail"),
        ):
            with self.assertRaises(self.module.WorldResultUncertain) as caught:
                self.session.apply_world(completion, asset_id="asset")
        self.assertIsNotNone(caught.exception.application)
        self.assertEqual(self.store.get("request").state, self.storage.JobState.APPLYING)
        self.assertEqual(self.scene.world, caught.exception.application._world)
        self.assertTrue(caught.exception.application.restore())
        self.assertEqual(self.store.get("request").state, self.storage.JobState.APPLYING)

    def test_world_postcommit_failure_does_not_undo_or_repeat_application(self):
        _, completion = self.world_completion()
        finish = self.session._coordinator.complete_application

        def late_failure(claim):
            finish(claim)
            raise self.storage.StoreError("fixture acknowledgement loss")

        with patch.object(
            self.session._coordinator, "complete_application", side_effect=late_failure
        ):
            with self.assertRaises(self.module.WorldResultUncertain) as caught:
                self.session.apply_world(completion, asset_id="asset")
        self.assertEqual(self.store.get("request").state, self.storage.JobState.APPLIED)
        self.assertEqual(self.scene.world, caught.exception.application._world)
        with self.assertRaises(self.module.OriginUnavailable):
            self.session.apply_world(completion, asset_id="asset")
        caught.exception.application.restore()

    def test_world_failure_write_error_does_not_report_safe_retry(self):
        verified, completion = self.world_completion()
        verified.paths[0].write_bytes(b"changed")
        with patch.object(
            self.session._coordinator,
            "fail_application",
            side_effect=self.storage.StoreError("fixture write failure"),
        ):
            with self.assertRaises(self.module.WorldResultUncertain):
                self.session.apply_world(completion, asset_id="asset")
        self.assertEqual(self.store.get("request").state, self.storage.JobState.APPLYING)

    def test_world_application_can_finish_after_its_own_origin_invalidation(self):
        _, completion = self.world_completion()
        apply = self.module.apply_world

        def invalidate(*args, **kwargs):
            application = apply(*args, **kwargs)
            self.session.deactivate()
            return application

        with patch.object(self.module, "apply_world", side_effect=invalidate):
            outcome = self.session.apply_world(completion, asset_id="asset")
        self.assertEqual(outcome.record.state, self.storage.JobState.APPLIED)
        outcome.application.restore()
