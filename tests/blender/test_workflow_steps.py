# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Installed native review of waiting workflow steps; not physical input proof."""

import json
import textwrap
import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import bpy
import httpx
import test_workflow_commands
from helpers import online_access, submodule

REVIEW = "scenario.review_workflow_step"


class Layout:
    """Records drawn rows in order; nested layouts share the list."""

    def __init__(self, calls=None, enabled=True):
        self.calls = [] if calls is None else calls
        self.enabled = enabled

    def _child(self, *args, **kwargs):
        return Layout(self.calls, self.enabled)

    box = row = column = _child

    def split(self, factor=0.0, align=False, **kwargs):
        self.calls.append(("split", factor, align))
        return self._child()

    def separator(self, *args, **kwargs):
        pass

    def progress(self, *args, **kwargs):
        self.calls.append(("progress", kwargs.get("text")))

    def label(self, text="", icon="NONE", **kwargs):
        self.calls.append(("label", text, icon))

    def operator(self, idname, text="", icon="NONE", **kwargs):
        properties = {}
        self.calls.append(("operator", idname, text, properties, self.enabled))
        return _Properties(properties)

    def prop(self, data, name, text=None, **kwargs):
        self.calls.append(("prop", name, text, self.enabled))

    def prop_enum(self, data, name, value, text=None, **kwargs):
        self.calls.append(("prop_enum", value, text, self.enabled))

    def labels(self):
        return [call[1] for call in self.calls if call[0] == "label"]

    def operators(self, idname):
        return [call for call in self.calls if call[0] == "operator" and call[1] == idname]


class _Properties:
    def __init__(self, properties):
        object.__setattr__(self, "_properties", properties)

    def __setattr__(self, name, value):
        self._properties[name] = value


class Candidates(list):
    """The dialog's candidate collection, outside an operator instance."""

    def add(self):
        item = SimpleNamespace(label="", selected=False)
        self.append(item)
        return item


class WorkflowStepTests(unittest.TestCase):
    def setUp(self):
        self.fixture = test_workflow_commands.WorkflowCommandTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.runtime = self.fixture.runtime
        self.steps = submodule("blender.workflow_steps")
        self.recovery = submodule("blender.job_recovery")
        self.panels = submodule("blender.panels")
        self.studio = submodule("blender.studio")
        self.descriptors = submodule("core.ui.saved_job_actions")
        self.dialog = self.steps.SCENARIO_OT_review_workflow_step
        self.context = SimpleNamespace(
            window_manager=SimpleNamespace(
                invoke_props_dialog=MagicMock(return_value={"RUNNING_MODAL"})
            )
        )

    # Helpers.

    def paused(self, *nodes):
        local_id = self.fixture.paused_workflow(*nodes)
        self.show()
        return local_id

    def show(self):
        self.runtime.show_job_views(self.runtime.state.model_jobs.views.values())

    def owner(self):
        return self.runtime.state.model_jobs

    def view(self, local_id):
        return self.owner().views[local_id]

    def refresh(self, local_id):
        self.owner()._next_poll[local_id] = 0.0
        self.fixture.settle()
        self.show()

    def operator(self, local_id, node_id, **changes):
        record = self.fixture.store.get(local_id)
        values = {
            "context_id": self.runtime.state.job_context_id,
            "request_id": local_id,
            "expected_revision": record.revision,
            "node_id": node_id,
            "review_id": self.fixture.step(local_id, node_id).review_id,
            "decision": "CONTINUE",
            "candidates": Candidates(),
            "report": MagicMock(),
            "layout": Layout(),
            **changes,
        }
        return SimpleNamespace(**values)

    def opened(self, local_id, node_id, **changes):
        operator = self.operator(local_id, node_id, **changes)
        self.assertEqual(self.dialog.invoke(operator, self.context, None), {"RUNNING_MODAL"})
        return operator

    def draw(self, operator):
        operator.layout = Layout()
        self.dialog.draw(operator, self.context)
        return operator.layout

    def reported(self, operator):
        return operator.report.call_args.args[1]

    def finish_decision(self):
        owner = self.owner()
        for _, task in tuple(owner._commands.values()):
            try:
                task.result(5)
            except Exception:
                # The owner drains and reports the same completion.
                pass
        owner.poll()
        self.show()

    # Descriptors and read-only drawing.

    def test_waiting_steps_draw_review_controls_in_jobs_and_workflows(self):
        local_id = self.paused(self.fixture.approval(), self.fixture.selection())
        record = self.fixture.store.get(local_id)
        items = self.recovery.result_actions(self.view(local_id))
        self.assertEqual(
            [(item.label, item.operator) for item in items],
            [
                ("Workflow waits for your decision", None),
                ("Review approval", REVIEW),
                ("Choose 1 to 2 of 3", REVIEW),
                ("Refresh status", "scenario.recover_job"),
                ("Resume download", "scenario.recover_job"),
            ],
        )
        rna = bpy.ops.scenario.review_workflow_step.get_rna_type()
        for item, node_id in zip(items[1:3], ("check", "pick"), strict=True):
            properties = dict(item.properties)
            self.assertEqual(
                properties,
                {
                    "context_id": self.runtime.state.job_context_id,
                    "request_id": local_id,
                    "expected_revision": record.revision,
                    "node_id": node_id,
                    "review_id": self.fixture.step(local_id, node_id).review_id,
                },
            )
            for key, value in item.properties:
                kind = {"STRING": str, "INT": int}[rna.properties[key].type]
                self.assertIs(type(value), kind)
        owner, store = self.owner(), self.fixture.store
        form = bpy.context.scene.scenario_workflow
        ui = submodule("blender.workflow_controls")
        before = (ui.signature(form), dict(owner._commands), len(self.fixture.calls))
        refuse = AssertionError("drawing read or started jobs")
        navigation = bpy.context.window_manager.scenario_studio_view
        self.addCleanup(setattr, navigation, "page", navigation.page)
        with (
            patch.object(self.runtime, "ensure_model_jobs", side_effect=refuse),
            patch.object(self.runtime, "ensure_job_session", side_effect=refuse),
            patch.object(self.runtime, "ensure_job_store", side_effect=refuse),
            patch.object(store, "get", side_effect=refuse),
            patch.object(store, "records", side_effect=refuse),
        ):
            sidebar = Layout()
            self.panels.SCENARIO_PT_jobs.draw(SimpleNamespace(layout=sidebar), bpy.context)
            navigation.page = "WORKFLOWS"
            studio = Layout()
            self.studio.draw_view(studio, bpy.context, width=960)
            navigation.page = "JOBS"
            jobs_page = Layout()
            self.studio.draw_view(jobs_page, bpy.context, width=960)
        for drawn in (sidebar, studio, jobs_page):
            self.assertEqual(
                [call[2] for call in drawn.operators(REVIEW)],
                ["Review approval", "Choose 1 to 2 of 3"],
            )
        # The Workflows page lists the waiting job above its form, without recovery controls.
        labels = studio.labels()
        self.assertLess(labels.index("Waiting for your decision"), labels.index("Workflow"))
        self.assertIn("fixture-workflow", labels)
        self.assertIn("Job: workflow-job", labels)
        self.assertEqual(
            [call[2] for call in studio.operators("scenario.recover_job")],
            [],
        )
        self.assertEqual(
            (ui.signature(form), dict(owner._commands), len(self.fixture.calls)), before
        )
        # A read in flight hides the controls but keeps the job listed.
        context = self.runtime.state.job_context_id
        _, task = self.runtime.read_workflow_steps(context, local_id)
        self.assertEqual([view.local_id for view in self.steps.pending_views()], [local_id])
        self.assertNotIn(
            REVIEW, [item.operator for item in self.recovery.result_actions(self.view(local_id))]
        )
        task.result(5)
        owner.poll()
        self.assertFalse(self.fixture.decisions)
        self.assertEqual(len(self.fixture.paid), 1)

    def test_workflow_names_come_from_the_catalog_or_a_loaded_form(self):
        self.assertEqual(self.steps.workflow_name("fixture-workflow"), "fixture-workflow")
        form = bpy.context.scene.scenario_workflow
        form.loaded_id, form.title = "fixture-workflow", "Loaded form title"
        self.assertEqual(self.steps.workflow_name("fixture-workflow"), "Loaded form title")
        self.runtime.state.workflow_controls = SimpleNamespace(
            catalog=[{"id": "fixture-workflow", "name": "Catalog name"}]
        )
        self.assertEqual(self.steps.workflow_name("fixture-workflow"), "Catalog name")
        self.assertEqual(self.steps.workflow_name("other"), "other")

    def test_running_workflow_without_a_waiting_step_explains_it_cannot_be_canceled(self):
        local_id = self.paused()
        items = self.recovery.result_actions(self.view(local_id))
        self.assertEqual(
            [item.label for item in items],
            [
                "Refresh status",
                "Resume download",
                "Scenario cannot cancel a running",
                "workflow step; it finishes or pauses",
                "at its next approval or selection.",
            ],
        )
        self.assertNotIn("cancel", [item.action for item in items])
        self.assertTrue(all(item.operator is None for item in items[2:]))
        self.assertEqual(self.steps.pending_views(), ())
        studio = Layout()
        submodule("blender.workflow_controls").draw(studio, bpy.context)
        self.assertNotIn("Waiting for your decision", studio.labels())

    # The review dialog.

    def test_approval_dialog_shows_the_job_and_sends_one_decision_once(self):
        local_id = self.paused(self.fixture.approval())

        def proceed(request):
            self.fixture.waiting(self.fixture.approval("success"))

        self.fixture.decision_reply = proceed
        operator = self.opened(local_id, "check")
        dialog = self.context.window_manager.invoke_props_dialog
        self.assertEqual(dialog.call_args.kwargs["confirm_text"], "Send decision")
        # At least the Generate workflow confirmation's width, which wraps at the same width.
        self.assertGreaterEqual(dialog.call_args.kwargs["width"], 540)
        drawn = self.draw(operator)
        labels = drawn.labels()
        for text in (
            "Workflow: fixture-workflow",
            "Job: workflow-job",
            "Approved price: 0.1234567890123456789 CU",
            "Approval step",
            "Step ID: check",
            "Results to review before approving:",
            "asset-render",
        ):
            self.assertIn(text, labels)
        # The decision is one segmented control: two equal, touching cells.
        start = drawn.calls.index(("split", 0.5, True))
        self.assertEqual(
            drawn.calls[start + 1 : start + 3],
            [
                ("prop_enum", "CONTINUE", "Approve", True),
                ("prop_enum", "STOP", "Stop workflow", True),
            ],
        )
        self.assertTrue(any(text.startswith("Continuing runs the remaining") for text in labels))
        self.assertFalse(any("https" in text or "Signature" in text for text in labels))
        # Drawing changes neither the dialog nor the job.
        self.assertEqual((operator.decision, list(operator.candidates)), ("CONTINUE", []))
        self.assertFalse(self.fixture.decisions)
        self.assertEqual(self.dialog.execute(operator, self.context), {"FINISHED"})
        self.assertEqual(self.dialog.execute(operator, self.context), {"CANCELLED"})
        self.assertIn("Review the workflow step again", self.reported(operator))
        self.finish_decision()
        self.assertEqual(len(self.fixture.decisions), 1)
        self.assertEqual(
            json.loads(self.fixture.decisions[0].content),
            {"nodeId": "check", "workflowJobId": "workflow-job", "action": "approve"},
        )
        # MCP reads the native decision from the same projection.
        status = self.fixture.tools.job_status({"job_id": local_id})
        self.assertFalse(status["awaiting_decision"])
        self.assertEqual(status["pending_steps"], [])
        self.assertTrue(status["delivery_active"])
        self.assertNotIn(
            REVIEW, [item.operator for item in self.recovery.result_actions(self.view(local_id))]
        )
        self.assertEqual(len(self.fixture.paid), 1)

    def test_selection_dialog_enforces_bounds_and_sends_listed_order(self):
        local_id = self.paused(self.fixture.selection())
        operator = self.opened(local_id, "pick")
        self.assertEqual(
            [(item.label, item.selected) for item in operator.candidates],
            [("asset-a", False), ("asset-b", False), ("asset-c", False)],
        )
        drawn = self.draw(operator)
        self.assertIn(("label", "Selection step: choose 1 to 2 of 3", "QUESTION"), drawn.calls)
        self.assertIn(("label", "Selected 0; choose 1 to 2", "ERROR"), drawn.calls)
        self.assertEqual(
            [call[2] for call in drawn.calls if call[0] == "prop"],
            ["1. asset-a", "2. asset-b", "3. asset-c"],
        )
        for picks, message in (((), "Select 1 to 2 items"), ((0, 1, 2), "Select 1 to 2 items")):
            with self.subTest(picks=picks):
                operator = self.opened(local_id, "pick")
                for index in picks:
                    operator.candidates[index].selected = True
                self.assertEqual(self.dialog.execute(operator, self.context), {"CANCELLED"})
                self.assertIn(message, self.reported(operator))
        self.assertFalse(self.fixture.decisions)
        operator = self.opened(local_id, "pick")
        operator.candidates[2].selected = True
        operator.candidates[0].selected = True
        self.assertIn(
            ("label", "Selected 2; choose 1 to 2", "CHECKMARK"), self.draw(operator).calls
        )
        self.assertEqual(self.dialog.execute(operator, self.context), {"FINISHED"})
        self.finish_decision()
        self.assertEqual(len(self.fixture.decisions), 1)
        self.assertEqual(
            self.fixture.decisions[0].url.path, "/v1/workflows/fixture-workflow/user-selection"
        )
        self.assertEqual(json.loads(self.fixture.decisions[0].content)["selectedIndices"], [0, 2])

    def test_text_candidates_are_wrapped_under_their_checkbox_up_to_the_line_limit(self):
        text = "a long prompt " * 20
        huge = "word " * 800
        selection = {
            **self.fixture.selection(),
            "items": ["short prompt", text, huge],
            "inputs": [{"name": "prompts", "type": "string_array", "min": 1, "max": 1}],
        }
        local_id = self.paused(selection)
        drawn = self.draw(self.opened(local_id, "pick"))
        self.assertEqual([call[2] for call in drawn.calls if call[0] == "prop"], ["1.", "2.", "3."])
        labels = drawn.labels()
        self.assertIn("    short prompt", labels)
        width = self.steps.WRAP - 4
        lines = ["    " + line for line in textwrap.wrap(text, width)]
        self.assertGreater(len(lines), 1)
        start = labels.index(lines[0])
        self.assertEqual(labels[start : start + len(lines)], lines)
        # A very long candidate shows its first lines and says how many exist.
        limit = self.steps.ITEM_LINES
        wrapped = textwrap.wrap(huge, width)
        self.assertGreater(len(wrapped), limit)
        start = labels.index("    " + wrapped[0], start + len(lines))
        self.assertEqual(
            labels[start : start + limit + 1],
            [
                *("    " + line for line in wrapped[:limit]),
                f"    (first {limit} of {len(wrapped)} lines shown)",
            ],
        )
        self.assertIn(("label", "Selection step: choose 1 of 3", "QUESTION"), drawn.calls)

    def test_stopping_needs_the_explicit_choice_and_sends_one_reject(self):
        loop = {
            "id": "loop",
            "type": "for-each",
            "status": "pending",
            "inputs": [{"name": "items", "ref": {"node": "pick"}}],
        }
        local_id = self.paused(self.fixture.selection(), loop)
        labels = [item.label for item in self.recovery.result_actions(self.view(local_id))]
        self.assertIn("Review blocked selection", labels)
        operator = self.opened(local_id, "pick")
        drawn = self.draw(operator)
        self.assertIn(("prop_enum", "CONTINUE", "Select", False), drawn.calls)
        self.assertIn(("prop_enum", "STOP", "Stop workflow", True), drawn.calls)
        self.assertFalse([call for call in drawn.calls if call[0] == "prop"])
        self.assertTrue(any("ForEach loop" in text for text in drawn.labels()))
        # The default never stops the workflow: Stop workflow must be chosen.
        self.assertEqual(self.dialog.execute(operator, self.context), {"CANCELLED"})
        self.assertIn("Choose Stop workflow", self.reported(operator))
        self.assertFalse(self.fixture.decisions)

        def stop(request):
            self.fixture.waiting(self.fixture.selection("rejected"), loop, status="canceled")

        self.fixture.decision_reply = stop
        operator = self.opened(local_id, "pick")
        operator.decision = "STOP"
        drawn = self.draw(operator)
        self.assertTrue(
            any(text.startswith("Rejecting this step cancels") for text in drawn.labels())
        )
        self.assertEqual(self.dialog.execute(operator, self.context), {"FINISHED"})
        self.finish_decision()
        self.assertEqual(len(self.fixture.decisions), 1)
        self.assertEqual(
            json.loads(self.fixture.decisions[0].content),
            {"action": "reject", "nodeId": "pick", "workflowJobId": "workflow-job"},
        )
        self.assertEqual(self.fixture.store.get(local_id).state.value, "canceled")
        self.assertEqual(self.recovery.result_actions(self.view(local_id)), ())
        self.assertEqual(len(self.fixture.paid), 1)

    def test_an_unverified_selection_into_a_loop_offers_only_stop(self):
        loop = {"id": "loop", "type": "for-each", "status": "pending"}
        local_id = self.paused(self.fixture.live_selection(), loop)
        labels = [item.label for item in self.recovery.result_actions(self.view(local_id))]
        self.assertIn("Review blocked selection", labels)
        operator = self.opened(local_id, "pick")
        drawn = self.draw(operator)
        self.assertIn(("prop_enum", "CONTINUE", "Select", False), drawn.calls)
        self.assertIn(("prop_enum", "STOP", "Stop workflow", True), drawn.calls)
        self.assertTrue(
            any(text.startswith("This extension could not read") for text in drawn.labels())
        )
        self.assertEqual(self.dialog.execute(operator, self.context), {"CANCELLED"})
        self.assertFalse(self.fixture.decisions)

    def test_an_approval_with_unread_links_warns_that_results_may_be_missing(self):
        live = {"id": "check", "type": "user-approval", "status": "processing"}
        local_id = self.paused(live)
        drawn = self.draw(self.opened(local_id, "check"))
        labels = drawn.labels()
        self.assertTrue(any(text.startswith(self.steps.UNLINKED[:40]) for text in labels))
        self.assertIn("No result assets are listed for this step.", labels)
        self.assertFalse(self.fixture.decisions)

    def test_an_approval_lists_the_results_its_workflow_definition_links(self):
        self.fixture.live_definition(
            {"id": "check", "type": "user-approval", "dependsOn": ["render"]}
        )
        live = {"id": "check", "type": "user-approval", "status": "processing"}
        local_id = self.paused(live)
        labels = self.draw(self.opened(local_id, "check")).labels()
        self.assertIn("Results to review before approving:", labels)
        self.assertIn("asset-render", labels)
        self.assertFalse(any(text.startswith(self.steps.UNLINKED[:40]) for text in labels))

    def test_changed_step_revision_or_connection_rejects_the_reviewed_decision(self):
        local_id = self.paused(self.fixture.approval())
        operator = self.opened(local_id, "check")
        # The reviewed results changed: the same node now has another review.
        self.fixture.remote_job["metadata"]["flow"][0]["assets"].append(
            {"assetId": "asset-other", "url": "https://cdn.example.invalid/other.png"}
        )
        self.refresh(local_id)
        self.assertEqual(self.dialog.execute(operator, self.context), {"CANCELLED"})
        self.assertIn("step changed", self.reported(operator))
        # A stale review cannot even open.
        stale = self.operator(local_id, "check", review_id="0" * 64)
        self.assertEqual(self.dialog.invoke(stale, self.context, None), {"CANCELLED"})
        self.assertIn("step changed", self.reported(stale))
        # The saved job moved on while the dialog was open.
        operator = self.opened(local_id, "check")
        self.fixture.waiting(self.fixture.approval("failure"), status="failure")
        self.refresh(local_id)
        self.assertEqual(self.fixture.store.get(local_id).state.value, "failed")
        self.assertEqual(self.dialog.execute(operator, self.context), {"CANCELLED"})
        self.assertIn("job changed", self.reported(operator))
        self.assertFalse(self.fixture.decisions)
        # Another connection retires the reviewed context.
        local_id = self.paused(self.fixture.approval())
        operator = self.opened(local_id, "check")
        late = self.operator(local_id, "check")
        self.fixture.prefs.project_id = "another-project"
        self.fixture.project = "another-project"
        self.assertEqual(self.dialog.invoke(late, self.context, None), {"CANCELLED"})
        self.assertIn("context changed", self.reported(late))
        self.assertEqual(self.dialog.execute(operator, self.context), {"CANCELLED"})
        self.assertIn("context changed", self.reported(operator))
        self.assertFalse(self.fixture.decisions)

    def test_offline_review_is_disabled_and_sends_nothing(self):
        local_id = self.paused(self.fixture.approval())
        self.assertTrue(self.dialog.poll(bpy.context))
        operator = self.opened(local_id, "check")
        with online_access(False):
            self.assertFalse(self.dialog.poll(bpy.context))
            self.assertEqual(self.dialog.execute(operator, self.context), {"CANCELLED"})
            self.assertIn("Allow Online Access", self.reported(operator))
        self.assertFalse(self.fixture.decisions)
        self.assertNotIn(local_id, self.owner()._commands)

    def test_a_refused_decision_is_shown_until_the_step_waits_again(self):
        local_id = self.paused(self.fixture.approval())

        def refuse(request):
            return httpx.Response(409, json={"message": "private detail"})

        self.fixture.decision_reply = refuse
        operator = self.opened(local_id, "check")
        self.assertEqual(self.dialog.execute(operator, self.context), {"FINISHED"})
        sending = self.recovery.result_actions(self.view(local_id))
        self.assertEqual([item.label for item in sending], ["Sending your decision..."])
        self.assertEqual([view.local_id for view in self.steps.pending_views()], [local_id])
        self.finish_decision()
        items = self.recovery.result_actions(self.view(local_id))
        errors = [item for item in items if item.key.startswith("decision_error")]
        self.assertTrue(errors)
        self.assertTrue(" ".join(item.label for item in errors).startswith("Scenario refused"))
        self.assertNotIn("private", json.dumps([item.label for item in items]))
        # The step still waits, so it can be reviewed again with the error shown.
        drawn = self.draw(self.opened(local_id, "check"))
        self.assertTrue(
            any(text.startswith("Last decision: Scenario refused") for text in drawn.labels())
        )
        self.assertEqual(len(self.fixture.decisions), 1)

    def test_restarted_jobs_offer_review_only_after_an_explicit_refresh(self):
        local_id = self.paused(self.fixture.approval())
        self.runtime.state.reset()
        calls = len(self.fixture.calls)
        owner = self.runtime.ensure_model_jobs()
        self.runtime.show_job_views(owner.inspect())
        items = self.recovery.result_actions(owner.views[local_id])
        self.assertNotIn(REVIEW, [item.operator for item in items])
        self.assertEqual(self.steps.pending_views(), ())
        self.assertEqual(len(self.fixture.calls), calls)
        record = self.fixture.store.get(local_id)
        _, task = self.runtime.control_model_job(
            self.runtime.state.job_context_id, local_id, record.revision, "refresh"
        )
        task.result(5)
        owner.poll()
        self.show()
        items = self.recovery.result_actions(owner.views[local_id])
        self.assertIn(REVIEW, [item.operator for item in items])
        self.assertEqual([view.local_id for view in self.steps.pending_views()], [local_id])
        self.assertFalse(self.fixture.decisions)

    def test_job_rows_redraw_when_a_step_starts_waiting(self):
        pump = submodule("blender.pump")
        local_id = self.paused()
        owner = self.owner()
        owner._next_poll[local_id] = float("inf")
        pump._jobs_changed()
        self.assertFalse(pump._jobs_changed())
        # Only the step projection changes: same status, progress and revision.
        self.fixture.waiting(self.fixture.approval())
        self.refresh(local_id)
        self.assertTrue(owner.steps(local_id))
        self.assertTrue(pump._jobs_changed())
        self.assertFalse(pump._jobs_changed())
        self.fixture.decision_reply = lambda request: self.fixture.waiting(
            self.fixture.approval("success")
        )
        operator = self.opened(local_id, "check")
        self.dialog.execute(operator, self.context)
        # A decision being sent redraws too, and so does its completion.
        self.assertTrue(pump._jobs_changed())
        self.finish_decision()
        self.assertTrue(pump._jobs_changed())

    # Registration.

    def test_registration_and_unregistration_of_the_review_dialog(self):
        classes = self.steps.CLASSES
        self.assertTrue(all(cls.is_registered for cls in classes))
        self.assertIn("candidates", bpy.ops.scenario.review_workflow_step.get_rna_type().properties)
        modules = [
            module.__name__.rsplit(".", 1)[-1]
            for module in submodule("blender.registry")._modules()
        ]
        self.assertLess(modules.index("workflow_steps"), modules.index("workflow_controls"))
        self.steps.unregister()
        try:
            self.assertFalse(any(cls.is_registered for cls in classes))
        finally:
            self.steps.register()
        self.assertTrue(all(cls.is_registered for cls in classes))


if __name__ == "__main__":
    unittest.main()
