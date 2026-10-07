# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Installed Film upload association, origin delivery and shared quote commands."""

import tempfile
import unittest
from pathlib import Path

import bpy
from helpers import submodule


class FilmUploadTests(unittest.TestCase):
    def setUp(self):
        import httpx

        self.jobs = submodule("core.jobs.store")
        self.uploads = submodule("core.jobs.upload_store")
        self.session_module = submodule("blender.job_session")
        self.temp = tempfile.TemporaryDirectory(dir=bpy.utils.resource_path("USER"))
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.previous = bpy.context.scene
        self.scene = bpy.data.scenes.new("Film upload fixture")
        bpy.context.window.scene = self.scene
        bpy.context.view_layer.update()
        self.scope = self.jobs.JobScope("https://fixture.invalid/v1", "fixture")
        self.store = self.jobs.JobStore(self.root / "jobs.sqlite3", self.scope)
        self.upload_store = self.uploads.UploadStore(self.root / "uploads.sqlite3", self.scope)
        source_root = self.root / "sources"
        source_root.mkdir()
        self.calls = []

        def respond(request):
            self.calls.append(request)
            if request.method == "GET":
                return httpx.Response(
                    200,
                    json={
                        "model": {
                            "id": "model",
                            "type": "custom",
                            "inputs": [{"name": "prompt", "type": "string", "required": True}],
                        }
                    },
                )
            self.assertEqual(request.url.params.get("dryRun"), "true")
            return httpx.Response(200, json={"creativeUnitsCost": 1})

        api = submodule("core.api.sdk_adapter")
        adapter = api.SDKAdapter(
            api.Credentials("fixture", "fixture-secret"),
            online=lambda: True,
            base_url=self.scope.service,
            account_id=self.scope.account_id,
            transport=httpx.MockTransport(respond),
        )
        self.addCleanup(adapter.close)
        self.session = self.session_module.JobSession(
            adapter,
            self.store,
            workers=1,
            upload_store=self.upload_store,
            upload_sources=submodule("core.jobs.upload_sources").UploadSources(source_root),
            part_uploader=submodule("core.jobs.upload_transfers").PartUploader(
                submodule("core.jobs.transfers").StoragePolicy(frozenset({"storage.invalid"})),
                online_access=lambda: True,
            ),
        )
        self.recipe = {
            "title": "Film fixture",
            "shots": [
                {
                    "id": "shot",
                    "title": "Shot",
                    "duration": 4,
                    "scene": submodule("core.scene.film_scene_plan").local_plan("studio", "", 4),
                }
            ],
            "tasks": [
                {"id": "source", "title": "Source", "kind": "upload"},
                {
                    "id": "take",
                    "title": "Take",
                    "kind": "model",
                    "model": "model",
                    "parameters": {"prompt": "$source"},
                },
            ],
        }
        origin = self.session.capture(self.scene)
        record = self.upload_store.create(
            self.uploads.UploadIntent(
                "upload",
                self.scope,
                origin,
                "image",
                "reference.png",
                "image/png",
                4,
                "a" * 64,
                4,
                ("a" * 64,),
            )
        )
        for state, fields in [
            (self.uploads.UploadState.INITIALIZING, {}),
            (self.uploads.UploadState.UPLOADING, {"upload_id": "remote"}),
            (self.uploads.UploadState.IMPORTED, {"asset_id": "reference-asset"}),
        ]:
            record = self.upload_store.transition(
                record.intent.request_id, expected_revision=record.revision, state=state, **fields
            )
        self.upload = record

    def tearDown(self):
        self.session.shutdown()
        bpy.context.window.scene = self.previous
        bpy.data.scenes.remove(self.scene)

    def bind(self, scene=None):
        task = self.session.bind_film_upload(
            self.recipe,
            production_id="production",
            task_id="source",
            request_id="upload",
            expected_revision=self.upload.revision,
            origin=self.session.capture(scene or self.scene),
        )
        task.result(5)
        return self.session.drain(task=task)[0]

    def test_saved_upload_association_feeds_shared_model_quote_after_reopen(self):
        before = tuple(self.scene.objects)
        completion = self.bind()
        result = self.session.deliver(completion, lambda value, *_: value)
        reopened = self.jobs.JobStore(self.root / "jobs.sqlite3", self.scope)
        self.assertEqual(result.reference, reopened.film_upload("production", "source"))
        self.assertEqual(self.calls, [])
        task = self.session.quote_film_task(
            self.recipe,
            production_id="production",
            task_id="take",
            origin=self.session.capture(self.scene),
        )
        task.result(5)
        quote = self.session.deliver(self.session.drain(task=task)[0], lambda value, *_: value)
        self.assertEqual(quote.estimate.payload, {"prompt": "reference-asset"})
        self.assertEqual(quote.film_task.task_id, "take")
        self.assertEqual(len(self.calls), 2)
        self.assertEqual(tuple(self.scene.objects), before)

    def test_late_association_delivery_rejects_changed_scene_but_keeps_saved_reference(self):
        completion = self.bind()
        self.session.invalidate_scene(self.scene)
        with self.assertRaises(self.session_module.OriginUnavailable):
            self.session.deliver(completion, lambda *_: self.fail("Applied late association"))
        self.assertIsNotNone(self.store.film_upload("production", "source"))
        self.assertEqual(self.calls, [])

    def test_repeat_association_delivers_to_new_reader_without_replacing_saved_binding(self):
        first = self.bind()
        saved = self.session.deliver(first, lambda value, *_: value).reference
        bpy.context.window.scene = self.previous
        second = self.bind(self.previous)
        observed = self.session.deliver(second, lambda result, scene, _: (result.reference, scene))
        self.assertEqual(observed, (saved, self.previous))
        self.assertEqual(self.store.film_upload("production", "source"), saved)
        self.assertEqual(self.calls, [])
