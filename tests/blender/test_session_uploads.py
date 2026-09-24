# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Installed upload facade, captured origins and read-only recovery after target loss."""

import tempfile
import threading
import unittest
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from pathlib import Path
from unittest.mock import Mock, patch

import bpy
from helpers import submodule


class SessionUploadTests(unittest.TestCase):
    def setUp(self):
        self.module = submodule("blender.job_session")
        self.api = submodule("core.api.sdk_adapter")
        self.jobs = submodule("core.jobs.store")
        self.uploads = submodule("core.jobs.upload_store")
        self.commands = submodule("core.jobs.uploads")
        self.transfer = submodule("core.jobs.upload_transfers")
        sources = submodule("core.jobs.upload_sources")
        policy = submodule("core.jobs.transfers")
        self.temp = tempfile.TemporaryDirectory(dir=bpy.utils.resource_path("USER"))
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.source = self.root / "reference.png"
        self.source.write_bytes(b"data")
        staging = self.root / "sources"
        staging.mkdir()
        self.sources = sources.UploadSources(staging, max_bytes=30, part_bytes=4)
        self.scope = self.jobs.JobScope("https://fixture.invalid/v1", "account", "project")
        self.upload_store = self.uploads.UploadStore(self.root / "uploads.sqlite3", self.scope)
        self.store = self.jobs.JobStore(self.root / "jobs.sqlite3", self.scope)
        self.previous = bpy.context.scene
        self.scene = bpy.data.scenes.new("Upload session fixture")
        bpy.context.window.scene = self.scene
        self.target = bpy.data.objects.new("Upload reference target", None)
        self.scene.collection.objects.link(self.target)
        bpy.context.view_layer.update()
        self.calls = []
        self.remote = {
            "id": "upload-one",
            "kind": "image",
            "source": "multipart",
            "status": "pending",
            "fileName": "reference.png",
            "contentType": "image/png",
            "fileSize": 4,
            "partsCount": 1,
            "parts": [
                {
                    "number": 1,
                    "expires": "2099-01-01T00:00:00Z",
                    "url": "https://storage.example.invalid/part?signature=fixture",
                }
            ],
        }

        def respond(request):
            import httpx

            self.calls.append((request, threading.current_thread()))
            result = dict(self.remote)
            if request.url.path.endswith("/action"):
                result["status"] = "validating"
            return httpx.Response(200, json={"upload": result})

        self.handler = respond
        self.uploader = self.transfer.PartUploader(
            policy.StoragePolicy(frozenset({"storage.example.invalid"}), max_bytes=4),
            online_access=lambda: True,
        )

        def put(url, data, *, number, content_type, expected_sha256):
            self.assertIsNot(threading.current_thread(), threading.main_thread())
            self.assertEqual(data, b"data")
            return self.transfer.UploadedPart(number, len(data), expected_sha256)

        self.uploader.upload = Mock(side_effect=put)
        self.session = self.new_session()

    def new_adapter(self, scope=None):
        import httpx

        scope = scope or self.scope
        return self.api.SDKAdapter(
            self.api.Credentials("fixture-key", "fixture-secret"),
            online=lambda: True,
            base_url=scope.service,
            account_id=scope.account_id,
            project_id=scope.project_id,
            transport=httpx.MockTransport(lambda request: self.handler(request)),
        )

    def new_session(self, *, completion_limit=128):
        return self.module.JobSession(
            self.new_adapter(),
            self.store,
            upload_store=self.upload_store,
            upload_sources=self.sources,
            part_uploader=self.uploader,
            workers=1,
            completion_limit=completion_limit,
        )

    def tearDown(self):
        self.session.shutdown()
        if self.previous in tuple(bpy.data.scenes):
            bpy.context.window.scene = self.previous
        if self.target is not None and self.target in tuple(bpy.data.objects):
            bpy.data.objects.remove(self.target, do_unlink=True)
        if self.scene in tuple(bpy.data.scenes):
            bpy.data.scenes.remove(self.scene)

    def prepare(self):
        origin = self.session.capture(self.scene, self.target)
        task = self.session.prepare_upload(
            self.source, origin=origin, kind="image", content_type="image/png"
        )
        record = task.result(5)
        self.assertEqual(record.intent.origin, origin)
        return record, self.session.drain()[0]

    def invoke(self, method, record):
        task = getattr(self.session, method)(
            record.intent.request_id, expected_revision=record.revision
        )
        result = task.result(5)
        completion = self.session.drain()[0]
        self.assertIsNone(completion.error)
        self.assertEqual(completion.origin, record.intent.origin)
        self.assertEqual(completion.result, result)
        return result, completion

    def initialized(self):
        record, _ = self.prepare()
        return self.invoke("initialize_upload", record)[0]

    def test_full_upload_runs_off_thread_and_delivers_original_target_once(self):
        threads = []
        stage = self.sources.stage

        def observed(*args, **kwargs):
            threads.append(threading.current_thread())
            return stage(*args, **kwargs)

        with patch.object(self.sources, "stage", side_effect=observed):
            record, _ = self.prepare()
        self.source.write_bytes(b"changed user source")
        for method in ("initialize_upload", "transfer_upload_part", "finalize_upload"):
            record, _ = self.invoke(method, record)
        self.assertEqual(record.state, self.uploads.UploadState.PROCESSING)
        self.assertIsNone(record.asset_id)
        self.remote.update(status="imported", entityId="asset-one")
        record, completion = self.invoke("refresh_upload", record)
        self.assertEqual(record.asset_id, "asset-one")
        self.assertTrue(all(thread is not threading.main_thread() for thread in threads))
        self.assertTrue(all(thread is not threading.main_thread() for _, thread in self.calls))
        self.assertTrue(all(r.url.params["projectId"] == "project" for r, _ in self.calls))
        self.assertEqual([r.method for r, _ in self.calls], ["POST", "GET", "POST", "GET"])
        delivered = []
        self.session.deliver(
            completion,
            lambda result, scene, target: delivered.append(
                (result, scene, target, threading.current_thread())
            ),
        )
        self.assertEqual(delivered, [(record, self.scene, self.target, threading.main_thread())])
        with self.assertRaises(self.module.OriginUnavailable):
            self.session.deliver(completion, lambda *args: self.fail("Delivered twice"))

    def test_scene_switch_blocks_delivery_instead_of_using_current_selection(self):
        _, completion = self.prepare()
        bpy.context.window.scene = self.previous
        with self.assertRaises(self.module.OriginUnavailable):
            self.session.deliver(completion, lambda *args: self.fail("Used current selection"))

    def test_queued_source_rechecks_scene_revision_before_staging(self):
        record, _ = self.prepare()
        entered, release = threading.Event(), threading.Event()
        original = self.handler

        def blocked(request):
            entered.set()
            self.assertTrue(release.wait(5))
            return original(request)

        self.handler = blocked
        running = self.session.initialize_upload(record.intent.request_id, expected_revision=0)
        try:
            self.assertTrue(entered.wait(5))
            queued = self.session.prepare_upload(
                self.source, origin=record.intent.origin, kind="image", content_type="image/png"
            )
            self.scene.frame_set(self.scene.frame_current + 1)
            release.set()
            completed = running.result(5)
            with self.assertRaisesRegex(self.commands.UploadError, "origin changed"):
                queued.result(5)
            self.assertEqual(completed.intent.origin, record.intent.origin)
            self.assertEqual(len(self.upload_store.records()), 1)
            self.assertEqual(len(tuple((self.root / "sources").iterdir())), 1)
            outcomes = self.session.drain()
            self.assertEqual(len(outcomes), 2)
            self.assertIsInstance(outcomes[1].error, self.commands.UploadError)
            with self.assertRaises(self.module.OriginUnavailable):
                self.session.deliver(outcomes[0], lambda *args: self.fail("Delivered stale upload"))
        finally:
            release.set()

    def test_full_completion_queue_blocks_staging_but_allows_inspection(self):
        self.session.shutdown()
        self.session = self.new_session(completion_limit=1)
        origin = self.session.capture(self.scene, self.target)
        record = self.session.prepare_upload(
            self.source, origin=origin, kind="image", content_type="image/png"
        ).result(5)
        with patch.object(self.sources, "stage") as stage:
            with self.assertRaisesRegex(RuntimeError, "Drain completed"):
                self.session.prepare_upload(
                    self.source, origin=origin, kind="image", content_type="image/png"
                )
            with self.assertRaisesRegex(RuntimeError, "Drain completed"):
                self.session.initialize_upload(record.intent.request_id, expected_revision=0)
            stage.assert_not_called()
        self.assertEqual(self.session.inspect_upload(record.intent.request_id), record)
        self.assertEqual(self.session.upload_recovery_plan()[0].record, record)
        self.session.drain()
        initialized, _ = self.invoke("initialize_upload", record)
        self.assertEqual(initialized.state, self.uploads.UploadState.UPLOADING)

    def test_restarted_uncertain_part_only_refreshes_without_replay_or_target_rebinding(self):
        record = self.initialized()
        self.uploader.upload.side_effect = self.transfer.UploadUncertain("synthetic loss")
        task = self.session.transfer_upload_part(
            record.intent.request_id, expected_revision=record.revision
        )
        with self.assertRaises(self.commands.UploadMutationUncertain):
            task.result(5)
        self.assertIsInstance(self.session.drain()[0].error, self.commands.UploadMutationUncertain)
        self.session.shutdown()
        self.session = self.new_session()
        saved = self.session.inspect_upload(record.intent.request_id)
        self.assertEqual(saved.state, self.uploads.UploadState.PART_UNCERTAIN)
        self.assertEqual(saved.active_part, 1)
        self.assertEqual(self.session.upload_recovery_plan()[0].action.value, "poll_remote")
        before = len(self.calls)
        for method in ("initialize_upload", "transfer_upload_part", "finalize_upload"):
            with self.assertRaises(self.module.OriginUnavailable):
                getattr(self.session, method)(
                    saved.intent.request_id, expected_revision=saved.revision
                )
        unchanged, _ = self.invoke("refresh_upload", saved)
        self.assertEqual(unchanged, saved)
        self.remote.update(status="imported", entityId="asset-one")
        imported, completion = self.invoke("refresh_upload", unchanged)
        self.assertEqual(imported.intent.origin, record.intent.origin)
        self.assertEqual([r.method for r, _ in self.calls[before:]], ["GET", "GET"])
        self.assertEqual(self.uploader.upload.call_count, 1)
        with self.assertRaises(self.module.OriginUnavailable):
            self.session.deliver(completion, lambda *args: self.fail("Rebound restarted origin"))

    def test_deleted_target_does_not_block_recovery_or_bind_a_replacement(self):
        record = self.initialized()
        name = self.target.name
        bpy.data.objects.remove(self.target, do_unlink=True)
        self.target = bpy.data.objects.new(name, None)
        self.scene.collection.objects.link(self.target)
        self.remote.update(status="imported", entityId="asset-one")
        imported, completion = self.invoke("refresh_upload", record)
        self.assertEqual(imported.intent.origin, record.intent.origin)
        with self.assertRaises(self.module.OriginUnavailable):
            self.session.deliver(completion, lambda *args: self.fail("Used same-name replacement"))

    def test_foreign_request_is_absent_and_all_upload_entry_points_require_main_thread(self):
        record, _ = self.prepare()
        foreign_scope = replace(self.scope, project_id="other-project")
        foreign = self.uploads.UploadStore(self.root / "uploads.sqlite3", foreign_scope)
        foreign.create(replace(record.intent, scope=foreign_scope, request_id="foreign-only"))
        self.assertIsNone(self.session.inspect_upload("foreign-only"))
        with self.assertRaises(self.module.OriginUnavailable):
            self.session.refresh_upload("foreign-only", expected_revision=0)
        methods = [
            (
                self.session.prepare_upload,
                (self.source,),
                {"origin": record.intent.origin, "kind": "image", "content_type": "image/png"},
            ),
            (self.session.inspect_upload, (record.intent.request_id,), {}),
            (self.session.upload_recovery_plan, (), {}),
        ]
        methods.extend(
            (getattr(self.session, name), (record.intent.request_id,), {"expected_revision": 0})
            for name in (
                "initialize_upload",
                "transfer_upload_part",
                "finalize_upload",
                "refresh_upload",
            )
        )
        with ThreadPoolExecutor(max_workers=1) as worker:
            for method, args, kwargs in methods:
                with self.subTest(method=method.__name__):
                    with self.assertRaisesRegex(RuntimeError, "main thread"):
                        worker.submit(method, *args, **kwargs).result(5)
        self.assertEqual(self.calls, [])

    def test_incomplete_configuration_fails_before_registering_another_owner(self):
        before = set(self.module._sessions)
        threads = set(threading.enumerate())
        adapter = self.new_adapter()
        options = {
            "upload_store": self.upload_store,
            "upload_sources": self.sources,
            "part_uploader": self.uploader,
        }
        try:
            for names in (
                ("upload_store",),
                ("upload_sources",),
                ("part_uploader",),
                ("upload_store", "upload_sources"),
                ("upload_store", "part_uploader"),
                ("upload_sources", "part_uploader"),
            ):
                with self.subTest(names=names):
                    with self.assertRaisesRegex(TypeError, "Configure.*together"):
                        self.module.JobSession(
                            adapter, self.store, **{name: options[name] for name in names}
                        )
                    self.assertEqual(self.module._sessions, before)
                    self.assertEqual(set(threading.enumerate()), threads)
            foreign = replace(self.scope, project_id="other-project")
            options["upload_store"] = self.uploads.UploadStore(
                self.root / "foreign.sqlite3", foreign
            )
            with self.assertRaisesRegex(ValueError, "Upload and job scopes must match"):
                self.module.JobSession(adapter, self.store, **options)
            self.assertEqual(self.module._sessions, before)
            self.assertEqual(set(threading.enumerate()), threads)
        finally:
            adapter.close()

    def test_file_load_during_claimed_upload_preserves_old_record_and_rejects_delivery(self):
        record, _ = self.prepare()
        entered, release = threading.Event(), threading.Event()
        original = self.handler

        def blocked(request):
            entered.set()
            self.assertTrue(release.wait(5))
            return original(request)

        self.handler = blocked
        task = self.session.initialize_upload(record.intent.request_id, expected_revision=0)
        try:
            self.assertTrue(entered.wait(5))
            self.module._load_pre(None)
            release.set()
            saved = task.result(5)
            self.assertEqual(self.upload_store.get(record.intent.request_id), saved)
            completion = self.session.drain()[0]
            self.assertEqual(completion.origin, record.intent.origin)
            with self.assertRaises(self.module.OriginUnavailable):
                self.session.deliver(completion, lambda *args: self.fail("Applied after file load"))
            with self.assertRaisesRegex(self.commands.UploadError, "inactive"):
                self.session.upload_recovery_plan()
        finally:
            release.set()
