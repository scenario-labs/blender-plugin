# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Installed workflow form/approval behavior with the exact bundled SDK."""

import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import bpy
import test_workflow_commands
from helpers import submodule


class WorkflowControlTests(unittest.TestCase):
    def setUp(self):
        self.fixture = test_workflow_commands.WorkflowCommandTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.ui = submodule("blender.workflow_controls")
        self.runtime = self.fixture.runtime
        self.scene = bpy.context.scene
        self.form = self.scene.scenario_workflow
        self.owner = self.ui.controls()

    def wait(self, view):
        try:
            view.task.result(5)
        except Exception:
            # Polling consumes task failures into view.error; assertions below
            # check that outcome rather than failing at this synchronization step.
            pass
        self.owner.poll()
        return view

    def load(self):
        self.form.workflow_id = "fixture-workflow"
        bpy.context.view_layer.update()
        view = self.wait(self.owner.start(self.scene, "load"))
        self.assertFalse(view.error)
        self.form.inputs["prompt"].text = "a cup"
        return view

    def price(self):
        self.load()
        view = self.wait(self.owner.start(self.scene, "price"))
        self.assertFalse(view.error)
        self.assertEqual(view.cost, "0.1234567890123456789")
        self.assertFalse(self.fixture.paid)
        return view

    def test_load_form_and_shared_quote_then_mcp_submission(self):
        view = self.price()
        self.assertEqual(self.form.title, "Fixture workflow")
        self.assertEqual(self.ui.parameters(self.form), {"prompt": "a cup", "count": 1})
        result = self.fixture.tools.run_workflow(
            {
                "workflow_id": self.form.workflow_id,
                "parameters": self.ui.parameters(self.form),
                "quote_id": view.ticket.identifier,
                "approved_cost": view.cost,
            }
        )
        self.fixture.settle()
        self.assertEqual(len(self.fixture.paid), 1)
        self.assertIsNotNone(self.fixture.store.get(result["local_id"]))
        with self.assertRaises(ValueError):
            self.owner.ready(self.scene)

    def test_native_approval_is_separate_single_use_and_exact(self):
        view = self.price()
        operator = SimpleNamespace(report=MagicMock())
        context = SimpleNamespace(
            scene=self.scene,
            window_manager=SimpleNamespace(
                invoke_props_dialog=MagicMock(return_value={"RUNNING_MODAL"})
            ),
        )
        cls = self.ui.SCENARIO_OT_generate_workflow
        self.assertEqual(cls.invoke(operator, context, None), {"RUNNING_MODAL"})
        self.assertFalse(self.fixture.paid)
        operator.layout = MagicMock()
        cls.draw(operator, context)
        labels = [call.kwargs.get("text") for call in operator.layout.label.call_args_list]
        self.assertIn("Exact price: 0.1234567890123456789 CU", labels)
        # Waiting steps are decided in Jobs; only a waiting step can stop the workflow.
        self.assertIn("Approval and selection steps wait for your review in Jobs.", labels)
        self.assertIn("A running step cannot be canceled; Stop workflow at a waiting step.", labels)
        with self.assertRaises(ValueError):
            self.owner.approve(self.scene, view.ticket.identifier, "0.12")
        self.assertEqual(cls.execute(operator, context), {"FINISHED"})
        self.assertEqual(cls.execute(operator, context), {"CANCELLED"})
        self.fixture.settle()
        self.assertEqual(len(self.fixture.paid), 1)

    def test_changed_input_rejects_pending_confirmation(self):
        view = self.price()
        self.form.inputs["prompt"].text = "another cup"
        with self.assertRaises(ValueError):
            self.owner.approve(self.scene, view.ticket.identifier, view.cost)
        self.assertFalse(self.fixture.paid)

    def test_pending_metadata_cannot_overwrite_edited_form(self):
        self.form.workflow_id = "fixture-workflow"
        bpy.context.view_layer.update()
        view = self.owner.start(self.scene, "load")
        self.form.workflow_id = "another-workflow"
        self.wait(view)
        self.assertTrue(view.error)
        self.assertEqual(self.form.workflow_id, "another-workflow")
        self.assertFalse(self.form.loaded_id)

    def test_pending_price_does_not_attach_to_changed_input(self):
        self.load()
        view = self.owner.start(self.scene, "price")
        self.form.inputs["prompt"].text = "changed"
        self.wait(view)
        self.assertTrue(view.error)
        self.assertFalse(view.cost)
        self.assertTrue(view.ticket.used)

    def test_catalog_and_drawing_do_not_submit_or_create_another_owner(self):
        view = self.wait(self.owner.start(self.scene, "list", privacy="public"))
        self.assertFalse(view.error)
        self.assertEqual(self.owner.catalog[0]["id"], "other-workflow")
        self.assertEqual(self.owner.catalog_privacy, "public")
        before = len(self.fixture.calls)
        with patch.object(
            self.runtime, "ensure_model_jobs", side_effect=AssertionError("draw created owner")
        ):
            self.ui.draw(MagicMock(), bpy.context)
        self.assertEqual(len(self.fixture.calls), before)
        self.assertFalse(self.fixture.paid)

    def test_navigation_drawing_keeps_quote_and_admitted_job(self):
        view = self.price()
        before = len(self.fixture.calls)
        for page in ("WORKFLOWS", "JOBS", "WORKFLOWS"):
            navigation = bpy.context.window_manager.scenario_studio_view
            navigation.page = page
            navigation.id_data.update_tag()
            bpy.context.view_layer.update()
            submodule("blender.studio").draw_view(MagicMock(), bpy.context, width=960)
        self.assertEqual(len(self.fixture.calls), before)
        self.owner.approve(self.scene, view.ticket.identifier, view.cost)
        bpy.context.window_manager.scenario_studio_view.page = "CREATE"
        self.fixture.settle()
        self.assertEqual(len(self.fixture.paid), 1)
        self.assertEqual(len(self.fixture.store.records()), 1)

    def test_retired_connection_cannot_approve_and_form_is_preserved(self):
        view = self.price()
        original = self.ui.signature(self.form)
        self.runtime.state.retire_jobs()
        self.assertIsNone(self.ui.controls(create=False))
        with self.assertRaises(submodule("core.api.errors").ScenarioError):
            self.owner.approve(self.scene, view.ticket.identifier, view.cost)
        self.assertEqual(self.ui.signature(self.form), original)
        self.assertFalse(self.fixture.paid)

    def test_null_definition_fallback_and_explicit_empty_schema(self):
        record = dict(self.fixture.workflow, inputs_definition=None)
        self.ui.load_form(self.form, record)
        self.assertEqual(len(self.form.inputs), 2)
        record["inputs_definition"] = []
        self.ui.load_form(self.form, record)
        self.assertEqual(self.ui.parameters(self.form), {})

    def test_zero_false_arrays_and_conditional_requirements_are_preserved(self):
        record = {
            "id": "fixture-schema",
            "inputs": [
                {"name": "seed", "type": "integer", "default": 0},
                {"name": "enabled", "type": "boolean", "default": False},
                {
                    "name": "images",
                    "type": "file_array",
                    "required": {"ifNotDefined": {"prompt": True}},
                },
                {
                    "name": "prompt",
                    "type": "string",
                    "required": {"ifNotDefined": {"images": True}},
                },
            ],
        }
        self.ui.load_form(self.form, record)
        with self.assertRaises(ValueError):
            self.ui.parameters(self.form)
        self.form.inputs["images"].enabled = True
        self.form.inputs["images"].text = '["fixture-image"]'
        self.assertEqual(
            self.ui.parameters(self.form),
            {"seed": 0, "enabled": False, "images": ["fixture-image"]},
        )
        self.form.inputs["images"].text = '"fixture-image"'
        with self.assertRaises(ValueError):
            self.ui.parameters(self.form)

    def test_invalid_metadata_preserves_existing_form_and_defaults(self):
        self.load()
        before = self.ui.signature(self.form)
        with self.assertRaises(ValueError):
            self.ui.load_form(
                self.form, {"id": "invalid", "inputs": [{"name": "x"}, {"name": "x"}]}
            )
        self.assertEqual(self.ui.signature(self.form), before)
        self.assertEqual(json.loads(self.form.schema_json)["parameters"][1]["default"], 1)

    def test_reprice_retires_previous_quote(self):
        first = self.price().ticket
        second = self.wait(self.owner.start(self.scene, "price"))
        self.assertTrue(first.used)
        self.assertNotEqual(first.identifier, second.ticket.identifier)
        self.assertFalse(self.fixture.paid)

    def test_saved_form_reopens_with_values_and_rebuilds_enum_cache(self):
        self.ui.load_form(
            self.form,
            {
                "id": "fixture-enum",
                "inputs": [
                    {"name": "size", "type": "integer", "default": 2, "allowedValues": [1, 2, 3]},
                    {"name": "prompt", "type": "string", "default": "Café 雪"},
                ],
            },
        )
        self.form.inputs["size"].choice = "2"
        expected = {"size": 3, "prompt": "Café 雪"}
        self.assertEqual(self.ui.parameters(self.form), expected)
        with tempfile.TemporaryDirectory(dir=bpy.utils.resource_path("USER")) as directory:
            path = str(Path(directory) / "workflow-form.blend")
            bpy.ops.wm.save_as_mainfile(filepath=path)
            bpy.ops.wm.open_mainfile(filepath=path)
            self.runtime.state.enum_cache.clear()
            form = bpy.context.scene.scenario_workflow
            self.assertEqual(self.ui.parameters(form), expected)
            self.assertEqual(form.loaded_id, "fixture-enum")
            self.assertIsNone(self.ui.controls(create=False))
        self.assertFalse(self.fixture.paid)

    def test_structured_always_required_input_starts_enabled(self):
        self.ui.load_form(
            self.form,
            {
                "id": "required",
                "inputs": [
                    {"name": "prompt", "type": "string", "required": {"always": True}},
                ],
            },
        )
        self.assertTrue(self.form.inputs["prompt"].enabled)
        self.form.inputs["prompt"].text = "Café 雪"
        self.assertEqual(self.ui.parameters(self.form), {"prompt": "Café 雪"})

    def test_catalog_completion_survives_native_form_edit_without_overwriting_it(self):
        self.load()
        view = self.owner.start(self.scene, "list", privacy="public")
        self.form.inputs["prompt"].text = "edited while loading"
        self.scene.update_tag()
        bpy.context.view_layer.update()
        self.wait(view)
        self.assertFalse(view.error)
        self.assertTrue(self.owner.catalog)
        self.assertEqual(self.form.inputs["prompt"].text, "edited while loading")

    def test_catalog_delivery_cannot_consume_schema_or_quote_completion(self):
        session = self.owner.jobs.session
        task = session.workflow_metadata(self.scene, identifier="fixture-workflow")
        task.result(5)
        completion = session.drain(task=task)[0]
        with self.assertRaises(submodule("blender.job_session").OriginUnavailable):
            session.deliver_workflow_catalog(completion)
        self.assertEqual(
            session.deliver(completion, lambda value, *_: value)["id"], "fixture-workflow"
        )

    def test_idle_view_capacity_reclaims_quote_without_losing_saved_inputs(self):
        ticket = self.price().ticket
        scenes = []
        try:
            for index in range(32):
                scene = bpy.data.scenes.new(f"Workflow capacity {index}")
                scenes.append(scene)
                self.owner.view(scene, create=True)
            self.assertEqual(len(self.owner.views), 32)
            self.assertIsNone(self.owner.view(self.scene))
            self.assertTrue(ticket.used)
            self.assertEqual(self.ui.parameters(self.form)["prompt"], "a cup")
            self.assertFalse(self.fixture.paid)
        finally:
            for scene in scenes:
                bpy.data.scenes.remove(scene)

    def generate_labels(self, layout):
        return [
            call.kwargs.get("text")
            for call in layout.row.return_value.operator.call_args_list
            if call.args and call.args[0] == "scenario.generate_workflow"
        ]

    def test_loop_price_shows_lower_bound_and_warning_without_blocking(self):
        layout = MagicMock()
        view = self.price()
        self.ui.draw(layout, bpy.context)
        self.assertEqual(self.generate_labels(layout), ["Generate (0.1234567890123456789 CU)"])
        self.assertFalse(view.cost_warning)
        self.fixture.workflow["flow"] = [
            {"id": "loop", "type": "for-each", "loopBodyNodeIds": ["node-a"]},
            {"id": "node-a", "type": "custom-model"},
        ]
        view = self.wait(self.owner.start(self.scene, "price"))
        self.assertIn("covers one loop pass", view.cost_warning)
        layout = MagicMock()
        before = self.ui.signature(self.form)
        self.ui.draw(layout, bpy.context)
        self.assertEqual(self.ui.signature(self.form), before)
        self.assertEqual(self.generate_labels(layout), ["Generate (from 0.1234567890123456789 CU)"])
        warnings = [
            call.kwargs
            for call in layout.label.call_args_list
            if call.kwargs.get("icon") in {"ERROR", "BLANK1"}
        ]
        self.assertEqual(warnings[0]["icon"], "ERROR")
        self.assertIn("loop", " ".join(item["text"] for item in warnings))
        operator = SimpleNamespace(report=MagicMock(), layout=MagicMock())
        context = SimpleNamespace(
            scene=self.scene,
            window_manager=SimpleNamespace(
                invoke_props_dialog=MagicMock(return_value={"RUNNING_MODAL"})
            ),
            # The warning measures its lines with the interface font.
            preferences=bpy.context.preferences,
        )
        cls = self.ui.SCENARIO_OT_generate_workflow
        self.assertEqual(cls.invoke(operator, context, None), {"RUNNING_MODAL"})
        cls.draw(operator, context)
        labels = [call.kwargs.get("text") for call in operator.layout.label.call_args_list]
        self.assertIn("Exact price: 0.1234567890123456789 CU", labels)
        self.assertIn("one loop pass", " ".join(text or "" for text in labels))
        self.assertEqual(cls.execute(operator, context), {"FINISHED"})
        self.fixture.settle()
        self.assertEqual(len(self.fixture.paid), 1)
        # The session result row keeps the approved quote as a lower bound.
        (result,) = self.fixture.runtime.state.model_jobs.views.values()
        self.assertEqual(self.result_costs(result), ["from 0.123 CU"])

    def confirmation(self, *, scale=1.0):
        """The Generate confirmation's drawn labels as (text, icon), on Blender's first draw.

        Blender lays a popup out before it sizes the popup's region, so that region
        is 0 px wide, and the context region is the one the dialog was invoked
        from, such as a header that spans the whole area.
        """
        operator = SimpleNamespace(report=MagicMock(), layout=MagicMock())
        context = SimpleNamespace(
            scene=self.scene,
            window_manager=SimpleNamespace(
                invoke_props_dialog=MagicMock(return_value={"RUNNING_MODAL"})
            ),
            region=SimpleNamespace(width=2400),
            region_popup=SimpleNamespace(width=0),
            preferences=SimpleNamespace(
                system=SimpleNamespace(ui_scale=scale),
                ui_styles=bpy.context.preferences.ui_styles,
            ),
        )
        cls = self.ui.SCENARIO_OT_generate_workflow
        self.assertEqual(cls.invoke(operator, context, None), {"RUNNING_MODAL"})
        before = self.ui.signature(self.form)
        cls.draw(operator, context)
        self.assertEqual(self.ui.signature(self.form), before)
        self.assertFalse(self.fixture.paid)
        return [
            (c.kwargs.get("text"), c.kwargs.get("icon"))
            for c in operator.layout.label.call_args_list
        ]

    def form_labels(self):
        """The labels the Studio form draws beside its inputs' values."""
        layout = MagicMock()
        self.ui.draw(layout, bpy.context)
        value = layout.box.return_value.row.return_value.row.return_value
        return [call.kwargs["text"] for call in value.prop.call_args_list]

    def test_confirmation_names_inputs_by_the_labels_the_form_shows(self):
        # A physical check read "Image4:" and "Images1:" in the confirmation where
        # the form showed each workflow input's own label.
        self.fixture.workflow["inputs"][0]["label"] = "Product / brand reference"
        self.price()
        self.assertEqual(self.form_labels(), ["Product / brand reference", "Count"])
        texts = [text for text, _ in self.confirmation()]
        self.assertIn('Product / brand reference: "a cup"', texts)
        self.assertIn("Count: 1", texts)
        self.assertFalse([text for text in texts if text.startswith("Prompt")], texts)

    def test_confirmation_uses_the_parameter_name_when_an_input_has_no_label(self):
        self.fixture.workflow["inputs"][0]["label"] = ""
        self.price()
        # Without a label the form shows the input's readable parameter name; so does the confirmation.
        self.assertEqual(self.form_labels(), ["Prompt", "Count"])
        texts = [text for text, _ in self.confirmation()]
        self.assertIn('Prompt: "a cup"', texts)
        self.assertIn("Count: 1", texts)

    def warning_lines(self, labels):
        return [text for text, icon in labels if icon in {"ERROR", "BLANK1"}]

    def assert_fits(self, lines, units, scale):
        import blf

        blf.size(0, bpy.context.preferences.ui_styles[0].widget.points * scale)
        for line in lines:
            self.assertLessEqual(blf.dimensions(0, line)[0], units * scale, line)

    def test_loop_warning_wraps_by_the_measured_width_between_its_sentences(self):
        # A physical check saw the warning, wrapped at 60 characters, break after
        # "covers one" in both the confirmation and Studio's wide form.
        self.fixture.workflow["flow"] = [
            {"id": "loop", "type": "for-each", "loopBodyNodeIds": ["node-a"]},
            {"id": "node-a", "type": "custom-model"},
        ]
        warning = self.price().cost_warning
        sentences = [
            "This workflow repeats steps in a loop.",
            "The price covers one loop pass; the final charge can be higher.",
        ]
        self.assertEqual(warning, " ".join(sentences))
        for scale in (1.0, 2.0):
            with self.subTest(ui_scale=scale):
                # Measured against the dialog's declared width, not its unsized
                # region or the wide region it was invoked from. The whole warning
                # needs two lines there, so each sentence takes its own.
                lines = self.warning_lines(self.confirmation(scale=scale))
                self.assertEqual(lines, sentences)
                self.assert_fits(lines, self.ui.CONFIRMATION_WIDTH - self.ui.WARNING_INSET, scale)
        studio = submodule("blender.studio")
        navigation = bpy.context.window_manager.scenario_studio_view
        self.addCleanup(setattr, navigation, "page", navigation.page)
        navigation.page = "WORKFLOWS"
        scale = submodule("blender.label_wrap").ui_scale(bpy.context)
        for width in (960, 240):
            with self.subTest(studio_width=width):
                layout = MagicMock()
                studio.draw_view(layout, bpy.context, width=width)
                lines = self.warning_lines(
                    (call.kwargs.get("text"), call.kwargs.get("icon"))
                    for call in layout.label.call_args_list
                )
                self.assertEqual(" ".join(lines), warning)
                if width == 960:
                    # Studio's wide page fits the whole warning on one line.
                    self.assertEqual(lines, [warning])
                else:
                    self.assertGreater(len(lines), 2)
                    # No line runs one sentence into the next.
                    heads = [" ".join(lines[:count]) for count in range(1, len(lines))]
                    self.assertIn(sentences[0], heads)
                self.assert_fits(lines, width - self.ui.WARNING_INSET, scale)
        self.assertFalse(self.fixture.paid)

    def result_costs(self, record):
        layout = MagicMock()
        submodule("blender.panels").draw_result(layout, record)
        header = layout.box.return_value.row.return_value
        return [
            call.kwargs["text"]
            for call in header.label.call_args_list
            if call.kwargs.get("text", "").endswith("CU")
        ]

    def test_session_workflow_cost_is_a_lower_bound_unless_proven_loop_free(self):
        records = submodule("core.jobs.records")
        for meta, expected in (
            ({"workflow_loop_steps": 0}, "0.5 CU"),
            ({"workflow_loop_steps": 2}, "from 0.5 CU"),
            # Recovered saved jobs do not record the definition's loop count.
            ({}, "from 0.5 CU"),
        ):
            with self.subTest(meta=meta):
                record = records.JobRecord.new("workflow", "workflow", "fixture", {}, meta=meta)
                record.cu_cost = 0.5
                self.assertEqual(self.result_costs(record), [expected])
        model = records.JobRecord.new("image", "image", "fixture", {}, meta={})
        model.cu_cost = 0.5
        self.assertEqual(self.result_costs(model), ["0.5 CU"])
