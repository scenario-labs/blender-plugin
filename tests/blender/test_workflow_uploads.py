# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Installed workflow-input uploads through the shared session with offline transport."""

import itertools
import json
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, Mock, patch

import bpy
import httpx
import test_reference_uploads as fixture_module
from helpers import submodule


class WorkflowUploadTests(unittest.TestCase):
    def setUp(self):
        self.fixture = fixture = fixture_module.ReferenceUploadTests()
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        self.runtime, self.owner = fixture.runtime, fixture.owner
        self.runtime.state.job_store = fixture.fixture.store
        self.enterContext(
            patch.object(self.runtime, "catalog_selection_matches", return_value=True)
        )
        self.enterContext(
            patch.object(submodule("blender.operators"), "_network_poll", return_value=True)
        )
        self.errors = submodule("core.api.errors")
        self.uploads = submodule("blender.workflow_uploads")
        self.ui = submodule("blender.workflow_controls")
        self.references = submodule("blender.workflow_references")
        self.form_module = submodule("blender.reference_form")
        self.record = {
            "id": "fixture-upload-workflow",
            "name": "Upload workflow",
            "inputs": [
                {"name": "prompt", "type": "string", "required": True},
                {"name": "image", "type": "file", "kind": "image"},
                {"name": "images", "type": "file_array", "kind": "image", "maxItems": 2},
                {"name": "clip", "type": "file", "kind": "video"},
                {"name": "mesh", "type": "file", "kind": "3d"},
                {"name": "hdr", "type": "file", "kind": "image-hdr"},
                {"name": "document", "type": "file", "kind": "document"},
                {"name": "preset", "type": "file", "kind": "image", "allowedValues": ["one"]},
            ],
        }
        self.quotes, self.paid = [], []
        self.asset_id = "uploaded-asset"
        self.counter = itertools.count(1)
        inner = fixture.fixture.handler

        def respond(request):
            if "/uploads" in request.url.path:
                result = inner(request)
                if request.url.path.endswith("/action"):
                    fixture.fixture.remote["entityId"] = self.asset_id
                return result
            if request.method == "GET":
                self.assertEqual(request.url.path, "/v1/workflows/fixture-upload-workflow")
                return httpx.Response(200, json={"workflow": self.record})
            self.assertEqual(request.url.path, "/v1/workflows/fixture-upload-workflow/run")
            if request.url.params.get("dryRun") == "true":
                self.quotes.append(json.loads(request.content))
                return httpx.Response(269, content=b'{"creativeUnitsCost":0.1234567890123456789}')
            self.paid.append(request)
            return httpx.Response(200, json={"job": {"jobId": "workflow-upload-job"}})

        fixture.fixture.handler = respond
        self.scene = fixture.fixture.scene
        self.form = self.scene.scenario_workflow
        self.ui.load_form(self.form, self.record)
        self.form.inputs["prompt"].text = "a cup"
        self.form.inputs["image"].upload_path = str(fixture.fixture.source)
        self.form.inputs["images"].upload_path = str(fixture.fixture.source)

    def remote(self, name="reference.png", kind="image", content_type="image/png"):
        remote = self.fixture.fixture.remote
        remote.update(
            id=f"upload-{next(self.counter)}",
            kind=kind,
            fileName=f"uploads/synthetic-storage/{name}",
            originalFileName=name,
            contentType=content_type,
            status="pending",
        )
        remote.pop("entityId", None)

    def start(self, name="image", source="FILE", *, asset_id="uploaded-asset"):
        self.asset_id = asset_id
        self.remote()
        return self.uploads.start(bpy.context, self.uploads.review(bpy.context, name, source))

    def upload(self, name="image", **options):
        binding = self.start(name, **options)
        self.fixture.settle()
        return binding

    def stalled(self, name="image"):
        """Leave one imported saved upload behind a retained duplicate guard."""
        binding = self.start(name)
        item = self.form.inputs[name]
        item.enabled = not item.enabled  # A changed input rejects the late result.
        self.fixture.settle()
        item.enabled = not item.enabled
        self.assertTrue(binding.error)
        self.assertTrue(item.get(self.ui.UPLOAD_MARKER))
        record = binding.ticket.record
        self.assertEqual(record.state.value, "imported")
        return record

    def price(self):
        workflow = self.ui.controls()
        view = workflow.start(self.scene, "price")
        view.task.result(timeout=10)
        workflow.poll()
        self.assertFalse(view.error, view.error)
        return workflow, view

    def snapshot(self):
        return [
            (dict(item.items()), self.uploads._values(item), item.upload_path)
            for item in self.form.inputs
        ]

    def test_upload_binds_only_its_input_with_scope_and_value_then_requires_new_price(self):
        workflow, view = self.price()
        self.assertEqual(self.quotes[-1], {"prompt": "a cup"})
        others = [self.uploads._values(x) for x in self.form.inputs if x.name != "image"]
        binding = self.start()
        item = self.form.inputs["image"]
        self.assertTrue(item.get(self.ui.UPLOAD_MARKER))
        with self.assertRaisesRegex(ValueError, "fresh workflow price"):
            workflow.ready(self.scene)
        self.fixture.settle()
        self.assertTrue(binding.attached, binding.error)
        self.assertEqual(self.owner.workflow_forms, {})
        self.assertNotIn(self.ui.UPLOAD_MARKER, item)
        self.assertEqual(item[self.ui.UPLOAD_REQUEST], binding.ticket.record.intent.request_id)
        self.assertEqual((item.text, item.enabled), ("uploaded-asset", True))
        self.assertEqual(
            item.asset_scope, self.form_module.scope_key(self.fixture.fixture.store.scope)
        )
        self.assertEqual(item.asset_value, json.dumps("uploaded-asset"))
        self.assertEqual(
            others, [self.uploads._values(x) for x in self.form.inputs if x.name != "image"]
        )
        self.assertEqual(
            self.ui.parameters(self.form), {"prompt": "a cup", "image": "uploaded-asset"}
        )
        with self.assertRaisesRegex(ValueError, "fresh workflow price"):
            workflow.approve(self.scene, view.ticket.identifier, view.cost)
        self.price()
        self.assertEqual(self.quotes[-1], {"prompt": "a cup", "image": "uploaded-asset"})
        self.assertFalse(self.paid)
        self.fixture.fixture.uploader.upload.assert_called_once()

    def test_occupied_single_input_is_refused_before_admission(self):
        item = self.form.inputs["image"]
        item.text, item.enabled = "existing-asset", True
        with self.assertRaisesRegex(self.errors.ScenarioError, "Clear the existing reference"):
            self.uploads.review(bpy.context, "image", "FILE")
        self.assertNotIn(self.ui.UPLOAD_MARKER, item)
        self.assertEqual((self.owner.references, self.owner.workflow_forms), ({}, {}))
        self.assertEqual(self.fixture.fixture.calls, [])

    def test_array_appends_within_capacity_and_refuses_a_full_input(self):
        for asset_id in ("first-asset", "second-asset"):
            self.assertTrue(self.upload("images", asset_id=asset_id).attached)
        item = self.form.inputs["images"]
        self.assertEqual(json.loads(item.text), ["first-asset", "second-asset"])
        self.assertEqual(json.loads(item.asset_value), ["first-asset", "second-asset"])
        with self.assertRaisesRegex(self.errors.ScenarioError, "at most 2"):
            self.uploads.review(bpy.context, "images", "FILE")
        self.assertEqual(self.ui.parameters(self.form)["images"], ["first-asset", "second-asset"])
        self.assertEqual(self.fixture.fixture.uploader.upload.call_count, 2)

    def test_duplicate_click_and_shared_capacity_are_refused_before_marking(self):
        self.start()
        with self.assertRaisesRegex(self.errors.ScenarioError, "already has an upload"):
            self.uploads.review(bpy.context, "image", "FILE")
        self.fixture.settle()
        self.assertEqual(len(self.owner.references), 1)
        self.fixture.fixture.uploader.upload.assert_called_once()
        self.owner.forms.update({str(index): object() for index in range(128)})
        before = dict(self.form.inputs["images"].items())
        with self.assertRaisesRegex(self.errors.ScenarioError, "capacity"):
            self.uploads.review(bpy.context, "images", "FILE")
        self.assertEqual(dict(self.form.inputs["images"].items()), before)

    def test_unsupported_enumerated_offline_and_wrong_sources_are_refused(self):
        cases = [
            ("hdr", "FILE", "image, audio, video and 3D"),
            ("document", "FILE", "image, audio, video and 3D"),
            ("preset", "FILE", "listed asset IDs"),
            ("prompt", "FILE", "file input"),
            ("clip", "VIEWPORT", "supported snapshot"),
            ("image", "MESH", "supported snapshot"),
            ("mesh", "CAMERA", "supported snapshot"),
            ("clip", "FILE", "Choose a file"),
        ]
        for name, source, reason in cases:
            with self.subTest(name=name, source=source):
                with self.assertRaisesRegex(self.errors.ScenarioError, reason):
                    self.uploads.review(bpy.context, name, source)
        with patch.object(self.runtime, "online", return_value=False):
            with self.assertRaisesRegex(self.errors.ScenarioError, "Online Access"):
                self.uploads.review(bpy.context, "image", "FILE")
        reviewed = self.uploads.review(bpy.context, "image", "FILE")
        with patch.object(self.owner, "_online", return_value=False):
            with self.assertRaises(self.fixture.module.UploadNotStarted):
                self.uploads.start(bpy.context, reviewed)
        for item in self.form.inputs:
            self.assertNotIn(self.ui.UPLOAD_MARKER, item)
        self.assertEqual((self.owner.references, self.owner.workflow_forms), ({}, {}))
        self.assertEqual(self.fixture.fixture.calls, [])

    def test_local_validation_failure_allows_a_corrected_retry(self):
        self.form.inputs["image"].upload_path = "unsupported.blend"
        with self.assertRaisesRegex(self.errors.ScenarioError, "supported image"):
            self.start()
        self.assertNotIn(self.ui.UPLOAD_MARKER, self.form.inputs["image"])
        self.form.inputs["image"].upload_path = str(self.fixture.fixture.source)
        self.assertTrue(self.upload().attached)

    def test_changed_workflow_schema_value_or_scene_rejects_late_result(self):
        def value():
            self.form.inputs["image"].text = "typed-asset"

        def workflow():
            self.form.workflow_id = "another-workflow"

        def schema():
            record = json.loads(json.dumps(self.record))
            record["inputs"][1]["description"] = "Changed"
            self.ui.load_form(self.form, record)

        def scene():
            self.owner.session.invalidate_scene(self.scene)

        for change in (value, workflow, schema, scene):
            with self.subTest(change=change.__name__):
                self.ui.load_form(self.form, self.record)
                self.form.inputs["image"].upload_path = str(self.fixture.fixture.source)
                binding = self.start()
                if change is scene:
                    # Change the origin only after the upload is imported.
                    with patch.object(self.uploads, "deliver"):
                        self.fixture.settle()
                change()
                self.fixture.settle()
                self.owner.poll()
                self.assertFalse(binding.attached)
                self.assertTrue(binding.error)
                self.assertEqual(self.owner.workflow_forms, {})
                self.assertIn(binding.error, self.owner.form_errors)
                self.assertNotEqual(self.form.inputs["image"].text, "uploaded-asset")
                record = binding.ticket.record
                self.assertIn(record, self.owner.inspect_saved())
                self.assertEqual(record.state.value, "imported")

    def test_connection_retirement_keeps_marker_until_saved_upload_is_reviewed(self):
        self.start()
        self.runtime.state.reference_uploads = None
        replacement = self.runtime.ensure_reference_uploads()
        self.assertIsNot(replacement, self.owner)
        with self.assertRaisesRegex(self.errors.ScenarioError, "saved upload; inspect"):
            self.uploads.review(bpy.context, "image", "FILE")
        with self.assertRaisesRegex(ValueError, "finish the reference upload"):
            self.ui.parameters(self.form)
        self.assertEqual(replacement.references, {})

    def test_pending_marker_blocks_pricing_and_generate(self):
        workflow, view = self.price()
        binding = self.start()
        with self.assertRaisesRegex(ValueError, "finish the reference upload"):
            self.ui.parameters(self.form)
        with self.assertRaisesRegex(ValueError, "finish the reference upload"):
            workflow.start(self.scene, "price")
        with self.assertRaises(ValueError):
            workflow.ready(self.scene)
        self.fixture.settle()
        self.assertTrue(binding.attached)
        self.assertEqual(self.ui.parameters(self.form)["image"], "uploaded-asset")
        self.assertFalse(self.paid)

    def test_library_choices_skip_pending_input_and_stale_approval_is_rejected(self):
        session = self.owner.session
        approval = next(
            x
            for x in self.references.choices(bpy.context, session, "library-asset", "Cup", "image")
            if x.param_name == "image"
        )
        self.start()
        names = [
            x.param_name
            for x in self.references.choices(bpy.context, session, "library-asset", "Cup", "image")
        ]
        self.assertNotIn("image", names)
        self.assertIn("images", names)
        with self.assertRaisesRegex(ValueError, "inputs changed"):
            self.references.attach(approval, session)
        self.assertEqual(self.form.inputs["image"].text, "")

    def test_clear_warns_releases_delivery_and_keeps_saved_upload(self):
        binding = self.start()
        operator = SimpleNamespace(input_name="image", report=MagicMock())
        confirm = MagicMock(return_value={"RUNNING_MODAL"})
        context = SimpleNamespace(
            scene=self.scene, window_manager=SimpleNamespace(invoke_confirm=confirm)
        )
        cls = self.references.SCENARIO_OT_clear_workflow_reference
        self.assertEqual(cls.invoke(operator, context, None), {"RUNNING_MODAL"})
        self.assertIn("stays in saved uploads", confirm.call_args.kwargs["message"])
        self.assertEqual(cls.execute(operator, context), {"FINISHED"})
        item = self.form.inputs["image"]
        self.assertNotIn(self.ui.UPLOAD_MARKER, item)
        self.assertEqual(self.owner.workflow_forms, {})
        self.fixture.settle()
        self.assertFalse(binding.attached)
        self.assertEqual((item.text, item.enabled), ("", False))
        self.assertEqual(list(self.owner.form_errors), [])
        self.assertEqual(binding.ticket.record.state.value, "imported")
        self.assertNotIn("image", self.ui.parameters(self.form))

    def test_operator_confirms_destination_and_rechecks_reviewed_input(self):
        cls = self.uploads.SCENARIO_OT_upload_workflow_input
        operator = SimpleNamespace(input_name="image", source="FILE", report=MagicMock())
        confirm = MagicMock(return_value={"RUNNING_MODAL"})
        context = SimpleNamespace(
            scene=self.scene, window_manager=SimpleNamespace(invoke_confirm=confirm)
        )
        self.assertEqual(cls.invoke(operator, context, None), {"RUNNING_MODAL"})
        message = confirm.call_args.kwargs["message"]
        self.assertIn("reference.png", message)
        self.assertIn("Image", message)
        self.assertIn("Upload workflow", message)
        self.assertNotIn(self.ui.UPLOAD_MARKER, self.form.inputs["image"])
        self.form.inputs["image"].upload_path = str(self.fixture.fixture.root / "other.png")
        self.assertEqual(cls.execute(operator, context), {"CANCELLED"})
        self.form.inputs["image"].upload_path = str(self.fixture.fixture.source)
        self.assertEqual(cls.invoke(operator, context, None), {"RUNNING_MODAL"})
        self.form.inputs["prompt"].text = "edited"
        self.assertEqual(cls.execute(operator, context), {"CANCELLED"})
        self.assertNotIn(self.ui.UPLOAD_MARKER, self.form.inputs["image"])
        self.assertEqual(cls.invoke(operator, context, None), {"RUNNING_MODAL"})
        self.remote()
        self.assertEqual(cls.execute(operator, context), {"FINISHED"})
        self.assertEqual(cls.execute(operator, context), {"CANCELLED"})
        self.assertEqual(
            bpy.ops.scenario.upload_workflow_input(input_name="images", source="FILE"),
            {"CANCELLED"},
        )
        self.fixture.settle()
        self.assertEqual(self.form.inputs["image"].text, "uploaded-asset")
        self.fixture.fixture.uploader.upload.assert_called_once()

    def test_selected_mesh_upload_binds_mesh_source_at_quote(self):
        bpy.ops.mesh.primitive_cube_add()
        cube = bpy.context.active_object
        self.addCleanup(lambda: bpy.data.objects.remove(cube, do_unlink=True))
        mesh = submodule("blender.mesh_export")

        def export_file(context, objects, *, path):
            Path(path).write_bytes(b"data")

        self.asset_id = "mesh-asset"
        self.remote("reference.glb", "3d", "model/gltf-binary")
        with (
            patch.object(mesh, "source_objects", return_value=[cube]),
            patch.object(mesh, "export_glb", side_effect=export_file),
        ):
            reviewed = self.uploads.review(bpy.context, "mesh", "MESH")
            binding = self.uploads.start(bpy.context, reviewed)
        self.fixture.settle()
        self.assertTrue(binding.attached, binding.error)
        self.assertIsNotNone(binding.ticket.record.intent.mesh_source)
        _, view = self.price()
        self.assertEqual(self.quotes[-1], {"prompt": "a cup", "mesh": "mesh-asset"})
        sources = view.ticket.quote.mesh_sources
        self.assertEqual(len(sources), 1)
        self.assertEqual(sources[0].parameter, "mesh")
        self.assertEqual(sources[0].asset_id, "mesh-asset")
        self.assertEqual(sources[0].upload_id, binding.ticket.record.intent.request_id)
        self.assertFalse(self.paid)

    def test_mcp_upload_reference_asset_reaches_estimate_workflow(self):
        self.asset_id = "mcp-asset"
        self.remote()
        tools = self.fixture.tools
        handle = tools.upload_reference({"path": str(self.fixture.fixture.source)})
        self.assertIn("estimate_workflow", handle["note"])
        self.fixture.settle()
        status = tools.reference_upload_status(handle)
        self.assertEqual((status["state"], status["asset_id"]), ("imported", "mcp-asset"))
        deferred = tools.estimate_workflow(
            {
                "workflow_id": self.record["id"],
                "parameters": {"prompt": "a cup", "image": status["asset_id"]},
            }
        )
        deferred.run()
        quote = deferred.finish(None)
        self.assertEqual(quote["payload"], {"prompt": "a cup", "image": "mcp-asset"})
        self.assertEqual(self.quotes[-1], {"prompt": "a cup", "image": "mcp-asset"})
        self.assertEqual(quote["cu_cost_exact"], "0.1234567890123456789")
        self.assertEqual(self.form.inputs["image"].text, "")
        self.assertFalse(self.paid)

    def test_saved_upload_after_blend_reopen_requires_single_use_confirmation(self):
        record = self.stalled()
        fixture = self.fixture.fixture
        names = self.scene.name, fixture.previous.name, fixture.target.name
        path = fixture.root / "workflow-upload-reopen.blend"
        bpy.ops.wm.save_as_mainfile(filepath=str(path), check_existing=False)
        fixture.session.shutdown()
        bpy.ops.wm.open_mainfile(filepath=str(path))
        self.scene = fixture.scene = bpy.data.scenes[names[0]]
        fixture.previous = bpy.data.scenes[names[1]]
        fixture.target = bpy.data.objects[names[2]]
        bpy.context.window.scene = self.scene
        self.form = self.scene.scenario_workflow
        replacement = fixture.new_session()
        self.addCleanup(replacement.shutdown)
        self.runtime.state.job_session = replacement
        self.runtime.state.reference_uploads = None
        self.runtime.state.job_context_id = "reopened-context"
        with patch.object(self.runtime, "ensure_job_session", return_value=replacement):
            owner = self.runtime.ensure_reference_uploads()
            item = self.form.inputs["image"]
            self.assertTrue(item.get(self.ui.UPLOAD_MARKER))
            with self.assertRaisesRegex(self.errors.ScenarioError, "saved upload; inspect"):
                self.uploads.review(bpy.context, "image", "FILE")
            with self.assertRaisesRegex(ValueError, "finish the reference upload"):
                self.ui.parameters(self.form)
            _, approval = self.form_module.prepare_attachment(
                bpy.context,
                "reopened-context",
                record.intent.request_id,
                record.revision,
                -1,
                "image",
                lane_name="workflow",
                destination_key=self.uploads.destination(self.scene, "image"),
            )
            self.assertEqual(item.text, "")
            lines = self.uploads.summary(approval)
            self.assertIn("Workflow: Upload workflow", lines)
            self.assertIn("Input: Image", lines)
            self.form_module.apply_attachment("reopened-context", approval.identifier)
            self.assertEqual(item.text, record.asset_id)
            self.assertNotIn(self.ui.UPLOAD_MARKER, item)
            self.assertEqual(item[self.ui.UPLOAD_REQUEST], record.intent.request_id)
            with self.assertRaises(self.errors.ScenarioError):
                self.form_module.apply_attachment("reopened-context", approval.identifier)
            self.assertEqual(self.ui.parameters(self.form)["image"], record.asset_id)
            self.assertEqual(owner.references, {})
        fixture.uploader.upload.assert_called_once()

    def test_saved_upload_dialogs_dispatch_to_the_workflow_input(self):
        record = self.stalled()
        layout = Mock()
        layout.row.return_value = layout
        layout.box.return_value = layout
        operators = []

        def operator(name, **kwargs):
            op = SimpleNamespace(name=name, **kwargs)
            operators.append(op)
            return op

        layout.operator.side_effect = operator
        cls = self.form_module.SCENARIO_OT_inspect_uploads
        inspect = SimpleNamespace(lane="workflow", param_name="image", index=-1, page=0)
        inspect.layout = layout
        context = SimpleNamespace(
            scene=self.scene,
            window_manager=SimpleNamespace(
                invoke_props_dialog=MagicMock(return_value={"RUNNING_MODAL"})
            ),
        )
        self.assertEqual(cls.invoke(inspect, context, None), {"RUNNING_MODAL"})
        cls.draw(inspect, context)
        attach = [op for op in operators if op.name == "scenario.attach_saved_upload"]
        self.assertEqual(len(attach), 1)
        self.assertEqual((attach[0].lane, attach[0].param_name), ("workflow", "image"))
        self.assertEqual(attach[0].request_id, record.intent.request_id)
        self.form.inputs["prompt"].text = "unrelated edit"
        operators.clear()
        cls.draw(inspect, context)
        self.assertTrue(any(op.name == "scenario.attach_saved_upload" for op in operators))
        self.form.inputs["image"].enabled = True
        operators.clear()
        cls.draw(inspect, context)
        self.assertFalse(any(op.name == "scenario.attach_saved_upload" for op in operators))
        self.form.inputs["image"].enabled = False
        dialog = SimpleNamespace(
            context_id=attach[0].context_id,
            request_id=attach[0].request_id,
            expected_revision=attach[0].expected_revision,
            index=attach[0].index,
            param_name="image",
            lane="workflow",
            destination_key=attach[0].destination_key,
            approval_id="",
            report=MagicMock(),
            layout=MagicMock(),
        )
        cls = self.form_module.SCENARIO_OT_attach_saved_upload
        self.assertEqual(cls.invoke(dialog, context, None), {"RUNNING_MODAL"}, dialog.report)
        cls.draw(dialog, context)
        labels = [call.kwargs.get("text") for call in dialog.layout.label.call_args_list]
        self.assertIn("Workflow: Upload workflow", labels)
        self.assertEqual(self.form.inputs["image"].text, "")
        self.assertEqual(cls.execute(dialog, context), {"FINISHED"})
        self.assertEqual(self.form.inputs["image"].text, record.asset_id)
        self.assertEqual(cls.execute(dialog, context), {"CANCELLED"})

    def test_saved_attachment_rejects_changed_form_or_context(self):
        record = self.stalled()
        args = (bpy.context, "fixture-context", record.intent.request_id, record.revision)
        _, approval = self.uploads.prepare_saved(*args, "image")
        self.form.inputs["prompt"].text = "changed"
        with self.assertRaisesRegex(self.errors.ScenarioError, "inputs changed"):
            self.form_module.apply_attachment("fixture-context", approval.identifier)
        self.assertNotIn(approval.identifier, self.owner.attachments)
        with self.assertRaisesRegex(self.errors.ScenarioError, "matching input type"):
            self.uploads.prepare_saved(*args, "clip")
        with self.assertRaisesRegex(self.errors.ScenarioError, "destination changed"):
            self.uploads.prepare_saved(*args, "image", destination_key="stale")
        _, approval = self.uploads.prepare_saved(*args, "image")
        self.owner.session.invalidate_scene(self.scene)
        with self.assertRaises(self.fixture.fixture.module.OriginUnavailable):
            self.form_module.apply_attachment("fixture-context", approval.identifier)
        with self.assertRaises(self.errors.ScenarioError):
            self.uploads.prepare_saved(bpy.context, "another-context", *args[2:], "image")
        self.assertTrue(self.form.inputs["image"].get(self.ui.UPLOAD_MARKER))
        self.assertEqual(self.form.inputs["image"].text, "")

    def test_saved_attachment_supersedes_an_in_flight_upload(self):
        record = self.stalled()
        binding = self.start("images")
        _, approval = self.uploads.prepare_saved(
            bpy.context, "fixture-context", record.intent.request_id, record.revision, "images"
        )
        self.form_module.apply_attachment("fixture-context", approval.identifier)
        item = self.form.inputs["images"]
        self.assertEqual(json.loads(item.text), [record.asset_id])
        self.assertNotIn(self.ui.UPLOAD_MARKER, item)
        self.assertEqual(self.owner.workflow_forms, {})
        self.fixture.settle()
        self.assertFalse(binding.attached)
        self.assertEqual(json.loads(item.text), [record.asset_id])

    def test_native_undo_redo_requires_fresh_attachment_without_reupload(self):
        record = self.stalled()
        fixture = self.fixture.fixture
        names = self.scene.name, fixture.previous.name, fixture.target.name
        undo = bpy.context.preferences.edit.use_global_undo
        bpy.context.preferences.edit.use_global_undo = True

        def restored():
            self.scene = fixture.scene = bpy.data.scenes[names[0]]
            fixture.previous = bpy.data.scenes[names[1]]
            fixture.target = bpy.data.objects[names[2]]
            bpy.context.window.scene = self.scene
            self.form = self.scene.scenario_workflow
            return self.form.inputs["image"]

        def approve(name="image"):
            return self.uploads.prepare_saved(
                bpy.context, "fixture-context", record.intent.request_id, record.revision, name
            )[1]

        try:
            marker = self.form.inputs["image"][self.ui.UPLOAD_MARKER]
            bpy.ops.ed.undo_push(message="Before saved workflow upload attachment")
            approval = approve()
            self.assertEqual(
                bpy.ops.scenario.attach_saved_upload(
                    context_id="fixture-context", approval_id=approval.identifier
                ),
                {"FINISHED"},
            )
            self.assertEqual(self.form.inputs["image"].text, record.asset_id)
            bpy.ops.ed.undo_push(message="After saved workflow upload attachment")
            pending = approve("images")
            calls = len(fixture.calls)
            self.assertEqual(bpy.ops.ed.undo(), {"FINISHED"})
            item = restored()
            self.owner.poll()
            self.assertEqual(item.text, "")
            self.assertEqual(item[self.ui.UPLOAD_MARKER], marker)
            self.assertNotIn(pending.identifier, self.owner.attachments)
            self.assertEqual(self.owner.workflow_forms, {})
            with self.assertRaisesRegex(self.errors.ScenarioError, "saved upload; inspect"):
                self.uploads.review(bpy.context, "image", "FILE")
            self.assertEqual(bpy.ops.ed.redo(), {"FINISHED"})
            item = restored()
            self.assertEqual(item.text, record.asset_id)
            self.assertEqual(bpy.ops.ed.undo(), {"FINISHED"})
            item = restored()
            self.form_module.apply_attachment("fixture-context", approve().identifier)
            self.assertEqual(item.text, record.asset_id)
            self.assertEqual(self.owner.session.inspect_upload(record.intent.request_id), record)
            self.assertEqual(len(fixture.calls), calls)
            fixture.uploader.upload.assert_called_once()
        finally:
            restored()
            bpy.context.preferences.edit.use_global_undo = undo

    def test_drawing_is_read_only_and_offers_kind_specific_sources(self):
        def drawn(name):
            calls = []
            layout = Mock()
            layout.row.return_value = layout

            def operator(identifier, **kwargs):
                op = SimpleNamespace()
                calls.append((identifier, op))
                return op

            layout.operator.side_effect = operator
            field = next(x for x in self.record["inputs"] if x["name"] == name)
            self.uploads.draw(layout, self.scene, self.form.inputs[name], field)
            return [(identifier, getattr(op, "source", None)) for identifier, op in calls], layout

        upload, inspect = "scenario.upload_workflow_input", "scenario.inspect_uploads"
        expected = {
            "image": [(upload, "FILE"), (upload, "VIEWPORT"), (upload, "CAMERA")]
            + [(upload, "RENDER"), (inspect, None)],
            "images": [(upload, "FILE"), (upload, "VIEWPORT"), (upload, "CAMERA")]
            + [(upload, "RENDER"), (inspect, None)],
            "clip": [(upload, "FILE"), (upload, "VIEWPORT_CLIP"), (upload, "CAMERA_CLIP")]
            + [(inspect, None)],
            "mesh": [(upload, "FILE"), (upload, "MESH"), (inspect, None)],
            "hdr": [],
            "document": [],
            "preset": [],
        }
        before = self.snapshot()
        for name, operators in expected.items():
            with self.subTest(name=name):
                self.assertEqual(drawn(name)[0], operators)
        self.assertEqual(before, self.snapshot())
        binding = self.start()
        before = self.snapshot()
        with patch.object(self.owner, "poll", side_effect=AssertionError("Draw advanced upload")):
            operators, layout = drawn("image")
            self.ui.draw(MagicMock(), bpy.context)
        self.assertEqual(operators, [(inspect, None)])
        layout.label.assert_called_once_with(text="Uploading reference…", icon="TIME")
        self.assertEqual(before, self.snapshot())
        self.assertFalse(binding.attached)

    def test_registration_exposes_operator_and_saved_path_property(self):
        self.assertTrue(hasattr(bpy.types, "SCENARIO_OT_upload_workflow_input"))
        prop = self.ui.ScenarioWorkflowInput.bl_rna.properties["upload_path"]
        self.assertEqual(prop.subtype, "FILE_PATH")
        signature = self.ui.signature(self.form)
        self.form.inputs["image"].upload_path = "//another.png"
        self.assertEqual(self.ui.signature(self.form), signature)
