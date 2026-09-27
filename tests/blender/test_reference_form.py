# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Native Image reference admission/attachment with actual upload session fixtures."""

import json
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

import bpy
import httpx
import test_reference_uploads as fixture_module
from helpers import submodule


class ReferenceFormTests(unittest.TestCase):
    def setUp(self):
        self.fixture = fixture = fixture_module.ReferenceUploadTests()
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        self.runtime, self.owner = fixture.runtime, fixture.owner
        self.form = submodule("blender.reference_form")
        self.generation = submodule("blender.generation")
        model = {
            "id": "fixture-reference-form",
            "name": "Reference form",
            "type": "custom",
            "capabilities": ["txt2img"],
            "inputs": [
                {"name": "prompt", "type": "string", "prompt": True},
                {"name": "image", "type": "file", "kind": "image"},
            ],
        }
        record = submodule("core.api.catalog").ModelRecord.from_api(model)
        self.model = model
        self.generation.set_catalog([record], [record])
        self.scene = fixture.fixture.scene
        self.runtime.state.job_store = fixture.fixture.store
        self.lane = self.scene.scenario.lane_state("image")
        self.lane.model_id = model["id"]
        self.ref = self.lane.references.add()
        self.ref.param_name, self.ref.source = "image", "FILE"
        self.ref.filepath = str(fixture.fixture.source)
        self.ref.label = "Chosen reference"
        self.enterContext(
            patch.object(submodule("blender.operators"), "_network_poll", return_value=True)
        )

    def start(self):
        self.assertEqual(bpy.ops.scenario.upload_image_reference(index=0), {"FINISHED"})
        return list(self.owner.forms.values())[-1]

    def test_upload_attaches_snapshot_and_invalidates_price_once(self):
        self.lane.estimate_state = "READY"
        self.lane.estimate_key = "old-approval"
        binding = self.start()
        self.assertEqual(self.lane.estimate_key, "")
        self.fixture.settle()
        self.assertTrue(binding.attached, binding.error)
        self.assertEqual(self.ref.source, "ASSET")
        self.assertEqual(self.ref.asset_id, "reference-asset")
        self.assertIn("uploaded snapshot", self.ref.label)
        self.assertEqual(self.lane.estimate_state, "PENDING")
        self.assertEqual(self.lane.estimate_key, "")
        request = self.generation.build_request(self.scene, "image", for_estimate=True)
        self.assertEqual(request.body["image"], "reference-asset")
        self.assertEqual(request.files, {})
        self.assertEqual(request.captures, [])
        self.assertFalse(request.errors, request.errors)
        label = self.ref.label
        self.owner.poll()
        self.assertEqual(self.ref.label, label)
        self.fixture.fixture.uploader.upload.assert_called_once()

    def test_duplicate_click_cannot_prepare_second_upload(self):
        self.start()
        with self.assertRaises(submodule("core.api.errors").ScenarioError):
            self.form.start(bpy.context, 0)
        self.fixture.settle()
        self.assertEqual(len(self.owner.references), 1)
        self.assertEqual(len(self.owner.session.upload_recovery_plan()), 1)
        self.fixture.fixture.uploader.upload.assert_called_once()

    def test_uploaded_reference_reaches_exact_quote_and_single_durable_submission(self):
        original = self.fixture.fixture.handler
        quotes, paid = [], []

        def respond(request):
            if "/uploads" in request.url.path:
                return original(request)
            if request.method == "GET":
                if "/jobs/" in request.url.path:
                    return httpx.Response(
                        200,
                        json={
                            "job": {
                                "jobId": "form-job",
                                "status": "in-progress",
                                "jobType": "custom",
                            }
                        },
                    )
                return httpx.Response(200, json={"model": self.model})
            if request.url.params.get("dryRun") == "true":
                quotes.append(request)
                return httpx.Response(269, content=b'{"creativeUnitsCost":0.1234567890123456789}')
            self.assertEqual(self.fixture.fixture.store.records()[0].state.value, "submitting")
            paid.append(request)
            return httpx.Response(200, json={"job": {"jobId": "form-job"}})

        self.fixture.fixture.handler = respond
        self.lane.prompt = "a teapot"
        self.generation.request_estimate(self.scene, "image")
        self.assertEqual(self.lane.estimate_state, "UNAVAILABLE")
        self.assertEqual(quotes, [])
        self.start()
        self.fixture.settle()
        self.generation.request_estimate(self.scene, "image")
        for ticket in self.runtime.state.model_previews.values():
            ticket.task.result(5)
        self.runtime.sync_catalog_context()
        self.assertEqual(self.lane.estimate_state, "READY", self.lane.estimate_error)
        ticket = self.runtime.state.estimates[self.lane.estimate_key]
        self.assertEqual(str(ticket.quote.estimate.cost), "0.1234567890123456789")
        self.generation.submit_generation(bpy.context, "image")
        for task in self.runtime.state.model_jobs.submissions.values():
            task.result(5)
        self.runtime.sync_catalog_context()
        with self.assertRaises(submodule("core.api.errors").ScenarioError):
            self.generation.submit_generation(bpy.context, "image")
        self.assertEqual(len(quotes), 1)
        self.assertEqual(len(paid), 1)
        self.assertEqual(quotes[0].content, paid[0].content)
        self.assertEqual(
            json.loads(paid[0].content), {"prompt": "a teapot", "image": "reference-asset"}
        )
        self.fixture.fixture.uploader.upload.assert_called_once()

    def test_changed_reference_or_model_cannot_receive_late_result(self):
        for changed in ("reference", "model"):
            with self.subTest(changed=changed):
                self.lane.references.clear()
                ref = self.lane.references.add()
                ref.param_name, ref.source = "image", "FILE"
                ref.filepath = str(self.fixture.fixture.source)
                self.lane.model_id = "fixture-reference-form"
                binding = self.start()
                if changed == "reference":
                    ref.filepath = "different.png"
                else:
                    record = submodule("core.api.catalog").ModelRecord.from_api(
                        dict(self.model, id="fixture-other-model")
                    )
                    self.runtime.state.records[record.id] = record
                    self.runtime.set_enum_items(
                        ("models", "image"),
                        [(self.model["id"], "Original", ""), (record.id, "Other", "")],
                    )
                    self.lane.model_id = record.id
                self.fixture.settle()
                self.assertFalse(binding.attached)
                self.assertTrue(binding.error)
                self.assertEqual(ref.source, "FILE")
                self.assertEqual(ref.asset_id, "")

    def test_deleted_reference_cannot_attach_to_replacement_slot(self):
        binding = self.start()
        self.lane.references.remove(0)
        replacement = self.lane.references.add()
        replacement.param_name, replacement.source = "image", "FILE"
        replacement.filepath = str(self.fixture.fixture.source)
        self.fixture.settle()
        self.assertFalse(binding.attached)
        self.assertTrue(binding.error)
        self.assertEqual(replacement.source, "FILE")
        self.assertEqual(replacement.asset_id, "")

    def test_changed_scene_cannot_receive_imported_reference(self):
        binding = self.start()
        self.owner.session.invalidate_scene(self.scene)
        self.fixture.settle()
        self.assertFalse(binding.attached)
        self.assertEqual(self.ref.source, "FILE")
        self.assertEqual(self.fixture.fixture.calls, [])

    def test_uploaded_asset_is_rejected_in_other_credentials_or_after_edit(self):
        self.start()
        self.fixture.settle()
        self.assertIsNone(self.form.scope_error(self.lane))
        self.runtime.state.job_store = None
        self.assertIsNotNone(self.form.scope_error(self.lane))
        self.runtime.state.job_store = self.fixture.fixture.store
        self.ref.asset_id = "another-asset"
        request = self.generation.build_request(self.scene, "image", for_estimate=True)
        self.assertTrue(request.errors)
        self.assertEqual(request.body, {})

    def test_saved_pending_marker_never_restarts_after_session_replacement(self):
        self.start()
        self.fixture.settle()
        self.ref.source = "FILE"
        self.runtime.state.reference_uploads = None
        replacement = self.runtime.ensure_reference_uploads()
        self.assertIsNot(replacement, self.owner)
        with self.assertRaises(submodule("core.api.errors").ScenarioError):
            self.form.start(bpy.context, 0)
        self.assertEqual(replacement.references, {})

    def test_draw_does_not_advance_uploads_or_change_properties(self):
        binding = self.start()
        before = dict(self.ref.items()), self.form.reference_values(self.ref)
        layout = Mock()
        layout.row.return_value = layout
        layout.operator.return_value = SimpleNamespace()
        with patch.object(self.owner, "poll", side_effect=AssertionError("Draw advanced upload")):
            self.form.draw(layout, self.lane, 0, self.ref)
        self.assertEqual(before, (dict(self.ref.items()), self.form.reference_values(self.ref)))
        self.assertFalse(binding.attached)

    def test_image_request_does_not_save_pending_render_implicitly(self):
        self.ref.source = "RENDER"
        with patch.object(
            self.generation, "_save_render_result", side_effect=AssertionError("Saved render")
        ):
            request = self.generation.build_request(self.scene, "image")
        self.assertTrue(request.captures)
