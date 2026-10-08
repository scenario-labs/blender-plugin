# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Installed Library-to-workflow references and SDK pricing with synthetic transport."""

import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import bpy
import httpx
import test_asset_library
from helpers import submodule


class WorkflowReferenceTests(unittest.TestCase):
    def setUp(self):
        self.fixture = test_asset_library.AssetLibraryTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.runtime = self.fixture.runtime
        self.library = submodule("blender.library_view")
        self.ui = submodule("blender.workflow_controls")
        self.references = submodule("blender.workflow_references")
        original = self.fixture.respond
        self.calls, self.paid = [], []
        self.record = {
            "id": "fixture-workflow",
            "name": "Reference workflow",
            "inputs": [
                {"name": "prompt", "type": "string", "required": True},
                {"name": "image", "type": "file", "kind": "image"},
                {
                    "name": "images",
                    "type": "file_array",
                    "kind": "image",
                    "minItems": 2,
                    "maxItems": 2,
                },
                {"name": "audio", "type": "file", "kind": "audio"},
            ],
        }

        def respond(request):
            if request.url.path in {"/v1/assets", "/v1/search/assets"}:
                return original(request)
            self.calls.append(request)
            if request.url.path == "/v1/jobs/workflow-reference-job":
                return httpx.Response(
                    200,
                    json={
                        "job": {
                            "jobId": "workflow-reference-job",
                            "jobType": "workflow",
                            "status": "in-progress",
                            "metadata": {"input": {"workflowId": self.record["id"]}},
                        }
                    },
                )
            if request.method == "GET":
                self.assertEqual(request.url.path, "/v1/workflows/fixture-workflow")
                return httpx.Response(200, json={"workflow": self.record})
            self.assertEqual(request.method, "PUT")
            self.assertEqual(request.url.path, "/v1/workflows/fixture-workflow/run")
            if request.url.params.get("dryRun") == "true":
                return httpx.Response(269, content=b'{"creativeUnitsCost":0.1234567890123456789}')
            self.paid.append(request)
            return httpx.Response(200, json={"job": {"jobId": "workflow-reference-job"}})

        self.fixture.respond = respond
        self.owner = self.library.controls(create=True)
        self.scene = bpy.context.scene
        self.form = self.scene.scenario_workflow
        self.ui.load_form(self.form, self.record)
        self.view = bpy.context.window_manager.scenario_library_view
        self.addCleanup(setattr, self.view, "target", self.view.target)
        self.view.target = "WORKFLOW"
        self.load()

    def load(self, asset_id="fixture-asset"):
        self.fixture.asset["id"] = asset_id
        self.owner.start(bpy.context.scene, ("", False, ""))
        self.owner.task.result(timeout=10)
        self.owner.poll()
        self.assertFalse(self.owner.error)

    def prepare(self, name="image", asset_id="fixture-asset"):
        return next(
            x
            for x in self.owner.prepare(bpy.context, asset_id, target="WORKFLOW")
            if x.param_name == name
        )

    def attach(self, name="image", asset_id="fixture-asset"):
        return self.owner.attach(self.prepare(name, asset_id))

    def price(self):
        self.form.inputs["prompt"].text = "a cup"
        self.workflow = self.ui.controls()
        view = self.workflow.start(bpy.context.scene, "price")
        view.task.result(timeout=10)
        self.workflow.poll()
        self.assertFalse(view.error, view.error)
        return view

    def test_library_reference_binds_input_and_preserves_full_required_validation(self):
        item = self.attach()
        self.assertEqual(item.text, "fixture-asset")
        self.assertTrue(item.enabled)
        self.assertTrue(item.asset_scope)
        with self.assertRaisesRegex(ValueError, "Prompt"):
            self.ui.parameters(self.form)
        self.form.inputs["prompt"].text = "a cup"
        self.assertEqual(
            self.ui.parameters(self.form), {"prompt": "a cup", "image": "fixture-asset"}
        )
        self.assertFalse(self.calls)
        self.assertFalse(self.paid)
        self.assertFalse(self.fixture.fixture.store.records())

    def test_array_can_be_built_incrementally_but_price_requires_minimum_and_capacity(self):
        self.attach("images")
        self.form.inputs["prompt"].text = "a cup"
        with self.assertRaisesRegex(ValueError, "at least 2"):
            self.ui.parameters(self.form)
        self.load("second")
        self.attach("images", "second")
        self.assertEqual(self.ui.parameters(self.form)["images"], ["fixture-asset", "second"])
        self.load("third")
        choices = self.owner.prepare(bpy.context, "third", target="WORKFLOW")
        self.assertEqual([x.param_name for x in choices], ["image"])

    def test_shared_sdk_quote_contains_reference_and_exact_mcp_approval(self):
        self.attach()
        view = self.price()
        self.assertEqual(view.cost, "0.1234567890123456789")
        self.assertEqual(
            json.loads(self.calls[-1].content), {"prompt": "a cup", "image": "fixture-asset"}
        )
        self.assertFalse(self.paid)
        result = self.fixture.tools.run_workflow(
            {
                "workflow_id": self.form.workflow_id,
                "parameters": self.ui.parameters(self.form),
                "quote_id": view.ticket.identifier,
                "approved_cost": view.cost,
            }
        )
        self.fixture.fixture.settle()
        self.assertEqual(len(self.paid), 1)
        self.assertEqual(
            json.loads(self.paid[0].content), {"prompt": "a cup", "image": "fixture-asset"}
        )
        self.assertIsNotNone(self.fixture.fixture.store.get(result["local_id"]))

    def test_new_reference_invalidates_existing_price_without_submission(self):
        view = self.price()
        self.attach()
        with self.assertRaisesRegex(ValueError, "fresh workflow price"):
            self.workflow.approve(self.scene, view.ticket.identifier, view.cost)
        self.assertFalse(self.paid)
        self.assertFalse(self.fixture.fixture.store.records())

    def test_changed_input_or_loaded_workflow_rejects_confirmation(self):
        approval = self.prepare()
        self.form.inputs["prompt"].text = "edited"
        with self.assertRaisesRegex(ValueError, "inputs changed"):
            self.owner.attach(approval)
        approval = self.prepare()
        self.form.workflow_id = "different-workflow"
        with self.assertRaises(ValueError):
            self.owner.attach(approval)
        self.assertFalse(self.form.inputs["image"].text)

    def test_manual_edit_or_scope_change_blocks_marked_input_even_before_session_refresh(self):
        item = self.attach()
        self.form.inputs["prompt"].text = "a cup"
        item.text = "edited-asset"
        with self.assertRaisesRegex(ValueError, "clear and choose"):
            self.ui.parameters(self.form)
        item.text = "fixture-asset"
        self.fixture.fixture.prefs.project_id = "different-project"
        with self.assertRaisesRegex(ValueError, "clear and choose"):
            self.ui.parameters(self.form)
        self.assertFalse(self.paid)

    def test_disabled_reference_is_omitted_but_binding_survives_reenable(self):
        item = self.attach()
        self.form.inputs["prompt"].text = "a cup"
        item.enabled = False
        self.fixture.fixture.prefs.project_id = "different-project"
        self.assertEqual(self.ui.parameters(self.form), {"prompt": "a cup"})
        self.assertTrue(item.asset_scope)
        item.enabled = True
        with self.assertRaises(ValueError):
            self.ui.parameters(self.form)

    def clear_operator(self):
        operator = SimpleNamespace(input_name="image", report=MagicMock())
        context = SimpleNamespace(
            scene=bpy.context.scene,
            window_manager=SimpleNamespace(
                invoke_confirm=MagicMock(return_value={"RUNNING_MODAL"})
            ),
        )
        cls = self.references.SCENARIO_OT_clear_workflow_reference
        self.assertEqual(cls.invoke(operator, context, None), {"RUNNING_MODAL"})
        return cls, operator, context

    def test_clear_requires_confirmation_and_preserves_other_inputs(self):
        self.attach()
        self.form.inputs["prompt"].text = "keep this"
        cls, operator, context = self.clear_operator()
        self.assertTrue(self.form.inputs["image"].asset_scope)
        self.assertEqual(cls.execute(operator, context), {"FINISHED"})
        item = self.form.inputs["image"]
        self.assertFalse(item.enabled)
        self.assertFalse(item.text)
        self.assertFalse(item.asset_scope)
        self.assertFalse(item.asset_value)
        self.assertEqual(self.form.inputs["prompt"].text, "keep this")
        self.assertEqual(cls.execute(operator, context), {"CANCELLED"})
        self.assertEqual(
            bpy.ops.scenario.clear_workflow_reference(input_name="image"), {"CANCELLED"}
        )

    def test_changed_form_rejects_pending_clear(self):
        self.attach()
        cls, operator, context = self.clear_operator()
        self.form.inputs["prompt"].text = "changed"
        self.assertEqual(cls.execute(operator, context), {"CANCELLED"})
        self.assertEqual(self.form.inputs["image"].text, "fixture-asset")

    def test_saved_connection_binding_survives_blend_reopen(self):
        self.attach()
        self.form.inputs["prompt"].text = "a cup"
        scope = self.form.inputs["image"].asset_scope
        with tempfile.TemporaryDirectory(dir=bpy.utils.resource_path("USER")) as directory:
            path = str(Path(directory) / "workflow-reference.blend")
            bpy.ops.wm.save_as_mainfile(filepath=path)
            bpy.ops.wm.open_mainfile(filepath=path)
            form = bpy.context.scene.scenario_workflow
            self.assertEqual(form.inputs["image"].asset_scope, scope)
            self.runtime.ensure_job_store()
            self.assertEqual(self.ui.parameters(form)["image"], "fixture-asset")
            self.fixture.fixture.prefs.project_id = "another-project"
            with self.assertRaises(ValueError):
                self.ui.parameters(form)

    def test_file_enum_remains_validated_without_retaining_a_cleared_choice(self):
        self.record["inputs"][1]["allowedValues"] = ["fixture-asset", "allowed-other"]
        self.ui.load_form(self.form, self.record)
        self.attach()
        self.form.inputs["prompt"].text = "a cup"
        self.assertEqual(self.ui.parameters(self.form)["image"], "fixture-asset")
        cls, operator, context = self.clear_operator()
        cls.execute(operator, context)
        self.assertFalse(self.form.inputs["image"].text)
        self.form.inputs["image"].enabled = True
        self.form.inputs["image"].text = "not-allowed"
        with self.assertRaisesRegex(ValueError, "allowed values"):
            self.ui.parameters(self.form)

    def test_workflow_confirmation_draw_names_destination_and_does_not_need_model(self):
        self.scene.scenario.image.model_id = "NONE"
        cls = self.library.SCENARIO_OT_library_reference
        operator = SimpleNamespace(asset_id="fixture-asset", report=MagicMock(), layout=MagicMock())
        context = SimpleNamespace(
            scene=self.scene,
            window_manager=SimpleNamespace(
                scenario_library_view=self.view,
                invoke_props_dialog=MagicMock(return_value={"RUNNING_MODAL"}),
            ),
        )
        self.assertEqual(cls.invoke(operator, context, None), {"RUNNING_MODAL"})
        cls.draw(operator, context)
        labels = [call.kwargs.get("text") for call in operator.layout.label.call_args_list]
        self.assertIn("Workflow: Reference workflow", labels)
        self.assertFalse(self.form.inputs["image"].text)
        self.assertEqual(cls.execute(operator, context), {"FINISHED"})
        self.assertEqual(self.form.inputs["image"].text, "fixture-asset")

    def test_removed_scene_draw_uses_captured_name_and_rejects_workflow_attachment(self):
        approval = self.prepare()
        name = self.scene.name
        operator = SimpleNamespace(_approvals=[approval], layout=MagicMock())
        replacement = bpy.data.scenes.new("Replacement workflow destination")
        bpy.context.window.scene = replacement
        bpy.data.scenes.remove(self.scene)
        self.library.SCENARIO_OT_library_reference.draw(operator, bpy.context)
        labels = [call.kwargs.get("text") for call in operator.layout.label.call_args_list]
        self.assertIn("Scene: " + name, labels)
        self.assertIn("Workflow: Reference workflow", labels)
        with self.assertRaises(submodule("blender.job_session").OriginUnavailable):
            self.owner.attach(approval)
        self.assertFalse(replacement.scenario_workflow.inputs)

    def test_removed_scene_rejects_pending_clear(self):
        self.attach()
        cls, operator, context = self.clear_operator()
        replacement = bpy.data.scenes.new("Replacement clear destination")
        bpy.context.window.scene = replacement
        bpy.data.scenes.remove(self.scene)
        self.assertEqual(cls.execute(operator, bpy.context), {"CANCELLED"})
        self.assertFalse(replacement.scenario_workflow.inputs)
