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

    def test_transient_scene_selection_pauses_without_poisoning_attachment(self):
        binding = self.start()
        binding.ticket.task.result(5)
        # A timer's context may omit the active window without changing the
        # captured scene. Actual scene edits still invalidate its origin.
        alternate = SimpleNamespace(context=SimpleNamespace(scene=None))
        with (
            patch.object(self.form, "bpy", alternate),
            patch.object(self.fixture.module, "bpy", alternate),
        ):
            self.owner.poll()
            self.assertFalse(binding.error)
            self.assertIsNone(binding.ticket.error)
            self.assertFalse(binding.attached)
            self.assertEqual(self.ref.source, "FILE")
            self.assertEqual(self.fixture.fixture.calls, [])
        self.fixture.settle()
        self.assertTrue(binding.attached, binding.error)
        self.fixture.fixture.uploader.upload.assert_called_once()

    def test_local_validation_failure_preserves_reason_and_allows_corrected_input(self):
        for source, path, reason in (
            ("FILE", "", "Choose an image file"),
            ("FILE", "unsupported.blend", "supported image reference format"),
            ("RENDER", "", "Render an image"),
        ):
            with self.subTest(source=source, path=path):
                self.ref.source, self.ref.filepath = source, path
                with self.assertRaisesRegex(submodule("core.api.errors").ScenarioError, reason):
                    self.form.start(bpy.context, 0)
                self.assertFalse(self.ref.get(self.form._MARKER))
                self.assertEqual(self.owner.forms, {})
                self.assertEqual(self.owner.references, {})
        self.ref.source, self.ref.filepath = "FILE", str(self.fixture.fixture.source)
        binding = self.start()
        self.fixture.settle()
        self.assertTrue(binding.attached)

    def test_rejected_queue_admission_allows_retry_but_async_failure_stays_marked(self):
        with patch.object(
            self.owner.session,
            "prepare_upload",
            side_effect=submodule("blender.job_session").SessionBusy("Full"),
        ):
            with self.assertRaises(self.fixture.module.UploadNotStarted):
                self.form.start(bpy.context, 0)
        self.assertFalse(self.ref.get(self.form._MARKER))
        self.assertEqual(self.owner.forms, {})
        self.ref.filepath = str(self.fixture.fixture.root / "missing.png")
        binding = self.start()
        self.fixture.settle()
        self.assertTrue(binding.ticket.error)
        self.ref.filepath = str(self.fixture.fixture.source)
        with self.assertRaises(submodule("core.api.errors").ScenarioError):
            self.form.start(bpy.context, 0)
        self.assertTrue(self.ref.get(self.form._MARKER))
        self.assertEqual(self.fixture.fixture.calls, [])

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

    def saved_upload(self):
        binding = self.start()
        self.fixture.settle()
        return binding.ticket.record

    def approve(self, record, *, index=0, param_name="image"):
        return self.form.prepare_attachment(
            bpy.context,
            self.runtime.state.job_context_id,
            record.intent.request_id,
            record.revision,
            index,
            param_name,
        )[1]

    def test_saved_upload_attachment_requires_single_use_destination_approval(self):
        record = self.saved_upload()
        self.owner.session.invalidate_all()
        self.ref.source, self.ref.asset_id = "FILE", ""
        approval = self.approve(record)
        self.assertEqual(self.ref.source, "FILE")
        self.assertEqual(approval.reference_label, self.ref.label)
        ref = self.form.apply_attachment(self.runtime.state.job_context_id, approval.identifier)
        self.assertEqual(ref.asset_id, "reference-asset")
        self.assertEqual(self.lane.estimate_key, "")
        self.assertIsNone(self.form.scope_error(self.lane))
        with self.assertRaises(submodule("core.api.errors").ScenarioError):
            self.form.apply_attachment(self.runtime.state.job_context_id, approval.identifier)
        self.fixture.fixture.uploader.upload.assert_called_once()

    def test_changed_form_rejects_attachment_and_consumes_confirmation(self):
        record = self.saved_upload()
        approval = self.approve(record)
        self.ref.asset_id = "new-selection"
        with self.assertRaises(submodule("core.api.errors").ScenarioError):
            self.form.apply_attachment(self.runtime.state.job_context_id, approval.identifier)
        self.assertEqual(self.ref.asset_id, "new-selection")
        self.assertNotIn(approval.identifier, self.owner.attachments)

    def pending_reference(self, index):
        ref = self.ref if index == 0 else self.lane.references.add()
        for key in tuple(ref.keys()):
            del ref[key]
        ref.param_name, ref.source, ref.asset_id = "image", "FILE", ""
        ref.filepath = str(self.fixture.fixture.source)
        self.fixture.fixture.remote["id"] = "upload-two"
        binding = self.form.start(bpy.context, index)
        binding.ticket.task.result(5)
        return ref, binding

    def receipt_during_confirmation(self, index):
        record = self.saved_upload()
        ref, binding = self.pending_reference(index)
        approval = self.approve(record)
        self.assertNotIn(self.form._REQUEST, ref)
        with patch.object(self.owner, "_online", return_value=False):
            self.owner.poll()
        self.assertEqual(ref[self.form._REQUEST], binding.ticket.record.intent.request_id)
        self.assertEqual(ref.source, "FILE")
        self.form.apply_attachment(self.runtime.state.job_context_id, approval.identifier)
        self.assertEqual(self.ref.asset_id, record.asset_id)
        self.fixture.fixture.uploader.upload.assert_called_once()

    def test_target_upload_receipt_does_not_invalidate_confirmation(self):
        self.receipt_during_confirmation(0)

    def test_other_slot_upload_receipt_does_not_invalidate_confirmation(self):
        self.receipt_during_confirmation(1)

    def test_actual_attachment_during_confirmation_still_requires_new_review(self):
        record = self.saved_upload()
        ref, _ = self.pending_reference(1)
        approval = self.approve(record)
        self.fixture.settle()
        self.assertEqual(ref.source, "ASSET")
        with self.assertRaises(submodule("core.api.errors").ScenarioError):
            self.form.apply_attachment(self.runtime.state.job_context_id, approval.identifier)

    def test_native_undo_redo_requires_fresh_attachment_without_reupload(self):
        record = self.saved_upload()
        ref, binding = self.pending_reference(0)
        with patch.object(self.owner, "_online", return_value=False):
            self.owner.poll()
        marker = ref[self.form._MARKER]
        fixture = self.fixture.fixture
        names = self.scene.name, fixture.previous.name, fixture.target.name
        undo = bpy.context.preferences.edit.use_global_undo
        bpy.context.preferences.edit.use_global_undo = True

        def restored_references():
            self.scene = fixture.scene = bpy.data.scenes[names[0]]
            fixture.previous = bpy.data.scenes[names[1]]
            fixture.target = bpy.data.objects[names[2]]
            bpy.context.window.scene = self.scene
            self.lane = self.scene.scenario.lane_state("image")
            self.ref = self.lane.references[0]

        try:
            bpy.ops.ed.undo_push(message="Before saved reference attachment")
            approval = self.approve(record)
            self.assertEqual(
                bpy.ops.scenario.attach_saved_upload(
                    context_id=self.runtime.state.job_context_id,
                    approval_id=approval.identifier,
                ),
                {"FINISHED"},
            )
            self.assertTrue(binding.attached)
            bpy.ops.ed.undo_push(message="After saved reference attachment")
            pending = self.approve(record)
            calls = len(fixture.calls)
            self.assertEqual(bpy.ops.ed.undo(), {"FINISHED"})
            restored_references()
            self.owner.poll()
            self.assertEqual(self.ref.source, "FILE")
            self.assertEqual(self.ref[self.form._MARKER], marker)
            self.assertEqual(self.owner.forms, {})
            self.assertNotIn(pending.identifier, self.owner.attachments)
            with self.assertRaises(submodule("core.api.errors").ScenarioError):
                self.form.start(bpy.context, 0)
            # Redo restores the already authorized RNA change, not its consumed
            # approval. Neither history operation replays the network upload.
            self.assertEqual(bpy.ops.ed.redo(), {"FINISHED"})
            restored_references()
            self.owner.poll()
            self.assertEqual(self.ref.source, "ASSET")
            self.assertEqual(self.owner.forms, {})
            self.assertEqual(bpy.ops.ed.undo(), {"FINISHED"})
            restored_references()
            approval = self.approve(record)
            self.form.apply_attachment(self.runtime.state.job_context_id, approval.identifier)
            self.assertEqual(self.ref.asset_id, record.asset_id)
            self.assertEqual(self.owner.session.inspect_upload(record.intent.request_id), record)
            self.assertEqual(len(fixture.calls), calls)
            self.fixture.fixture.uploader.upload.assert_called_once()
        finally:
            restored_references()
            bpy.context.preferences.edit.use_global_undo = undo

    def test_new_slot_and_single_file_replacement_are_explicit(self):
        record = self.saved_upload()
        self.lane.references.clear()
        approval = self.approve(record, index=-1)
        self.assertIsNone(approval.reference)
        self.assertEqual(len(self.lane.references), 0)
        self.form.apply_attachment(self.runtime.state.job_context_id, approval.identifier)
        self.assertEqual(len(self.lane.references), 1)
        approval = self.approve(record, index=-1)
        self.assertIsNotNone(approval.reference)
        self.form.apply_attachment(self.runtime.state.job_context_id, approval.identifier)
        self.assertEqual(len(self.lane.references), 1)
        self.assertEqual(self.lane.references[0].asset_id, record.asset_id)

    def test_scene_or_context_change_rejects_saved_attachment(self):
        record = self.saved_upload()
        approval = self.approve(record)
        self.owner.session.invalidate_scene(self.scene)
        with self.assertRaises(self.fixture.fixture.module.OriginUnavailable):
            self.form.apply_attachment(self.runtime.state.job_context_id, approval.identifier)
        approval = self.approve(record)
        self.runtime.state.job_context_id = "another-context"
        with self.assertRaises(submodule("core.api.errors").ScenarioError):
            self.form.apply_attachment("fixture-context", approval.identifier)

    def test_native_cleanup_runs_without_dialog_and_preserves_original(self):
        record = self.saved_upload()
        source = self.fixture.fixture.source
        self.assertEqual(
            bpy.ops.scenario.recover_upload(
                context_id=self.runtime.state.job_context_id,
                request_id=record.intent.request_id,
                expected_revision=record.revision,
                action="cleanup",
            ),
            {"FINISHED"},
        )
        command = self.owner._recovering[record.intent.request_id]
        command.task.result(5)
        self.owner.poll()
        self.assertTrue(command.done)
        self.assertIsNone(command.error)
        self.assertEqual(self.owner.saved[record.intent.request_id], record)
        self.assertEqual(source.read_bytes(), b"data")

    def test_actual_blend_reopen_preserves_scope_and_requires_fresh_attachment(self):
        record = self.saved_upload()
        fixture = self.fixture.fixture
        names = self.scene.name, fixture.previous.name, fixture.target.name
        path = fixture.root / "reference-reopen.blend"
        bpy.ops.wm.save_as_mainfile(filepath=str(path), check_existing=False)
        fixture.session.shutdown()
        bpy.ops.wm.open_mainfile(filepath=str(path))
        self.scene = fixture.scene = bpy.data.scenes[names[0]]
        fixture.previous = bpy.data.scenes[names[1]]
        fixture.target = bpy.data.objects[names[2]]
        bpy.context.window.scene = self.scene
        self.lane = self.scene.scenario.lane_state("image")
        self.ref = self.lane.references[0]
        replacement = fixture.new_session()
        self.addCleanup(replacement.shutdown)
        self.runtime.state.job_session = replacement
        self.runtime.state.job_store = fixture.store
        self.runtime.state.reference_uploads = None
        self.runtime.state.job_context_id = "reopened-context"
        model = submodule("core.api.catalog").ModelRecord.from_api(self.model)
        self.generation.set_catalog([model], [model])
        with patch.object(self.runtime, "ensure_job_session", return_value=replacement):
            self.owner = self.runtime.ensure_reference_uploads()
            self.assertIsNone(self.form.scope_error(self.lane))
            self.ref.source = "FILE"
            with self.assertRaises(submodule("core.api.errors").ScenarioError):
                self.form.start(bpy.context, 0)
            approval = self.approve(record)
            self.assertEqual(self.ref.source, "FILE")
            self.form.apply_attachment("reopened-context", approval.identifier)
            self.assertEqual(self.ref.asset_id, record.asset_id)
            self.assertIsNone(self.form.scope_error(self.lane))
        self.assertEqual(len(self.owner.references), 0)
        self.fixture.fixture.uploader.upload.assert_called_once()
