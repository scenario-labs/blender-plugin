# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Installed saved-job action descriptors and their native drawing; not physical input proof."""

import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import bpy
import test_runtime_jobs
from helpers import submodule

ACTIONS = (
    "refresh",
    "resume",
    "cancel",
    "cancel_prepared",
    "recover_download",
    "retry_receipt",
    "import_images",
    "import_media",
    "import_model",
    "apply_world",
    "restore_world",
    "apply_material",
    "apply_mesh",
    "apply_mesh_source",
    "recover_blockout",
)
ASSETS = {
    "panorama": "image/x-exr",
    "clip": "video/webm",
    "sound": "audio/mpeg",
    "mesh": "model/gltf-binary",
}


class Layout:
    """Records drawing calls and the properties set on each returned operator."""

    def __init__(self):
        self.calls = []

    def label(self, text, icon="NONE"):
        self.calls.append(("label", text, icon, {}))

    def operator(self, idname, text, icon="NONE"):
        properties = {}
        self.calls.append(("operator", idname, text, icon, properties))
        return Operator(properties)


class Operator:
    def __init__(self, properties):
        object.__setattr__(self, "_properties", properties)

    def __setattr__(self, name, value):
        self._properties[name] = value


def expected(items):
    return [
        ("label", item.label, item.icon, {})
        if item.operator is None
        else ("operator", item.operator, item.label, item.icon, dict(item.properties))
        for item in items
    ]


class ResultActionTests(unittest.TestCase):
    def setUp(self):
        self.runtime = submodule("blender.runtime")
        self.recovery = submodule("blender.job_recovery")
        self.enterContext(patch.object(self.runtime, "state", self.runtime.RuntimeState()))
        self.runtime.state.job_context_id = "fixture-context"

    def view(self, state, actions, **meta):
        record = submodule("core.jobs.records").JobRecord(
            local_id="fixture-request",
            lane="model",
            kind="model",
            model_id="fixture-model",
            body={},
            status="in-progress",
            asset_ids=list(ASSETS),
            asset_types=dict(ASSETS),
        )
        record.meta.update(
            {
                "shared_job": True,
                "saved_revision": 4,
                "saved_state": state,
                "recovery_actions": tuple(actions),
                **meta,
            }
        )
        return record

    def test_every_descriptor_targets_registered_operator_properties(self):
        reviews = (
            None,
            SimpleNamespace(task=None, phase="READY", identifier="fixture-review"),
        )
        operators = set()
        for review in reviews:
            jobs = SimpleNamespace(recovery=SimpleNamespace(current=lambda *_, r=review: r))
            self.runtime.state.blockout_jobs = jobs
            for action in ACTIONS:
                for item in self.recovery.result_actions(self.view("applied", (action,))):
                    if item.operator is None:
                        continue
                    category, name = item.operator.split(".")
                    rna = getattr(getattr(bpy.ops, category), name).get_rna_type()
                    operators.add(item.operator)
                    for key, value in item.properties:
                        with self.subTest(operator=item.operator, property=key):
                            prop = rna.properties[key]
                            if prop.type == "ENUM":
                                identifiers = {entry.identifier for entry in prop.enum_items}
                                self.assertIn(value, identifiers)
                            else:
                                kind = {"STRING": str, "INT": int, "BOOLEAN": bool}[prop.type]
                                self.assertIs(type(value), kind)
        self.assertEqual(
            operators,
            {
                "scenario.recover_job",
                "scenario.import_saved_images",
                "scenario.import_saved_media",
                "scenario.import_saved_model",
                "scenario.apply_saved_world",
                "scenario.apply_saved_material",
                "scenario.apply_saved_mesh",
                "scenario.read_saved_blockout",
                "scenario.use_saved_blockout",
            },
        )
        enum = bpy.ops.scenario.recover_job.get_rna_type().properties["action"].enum_items
        actions = submodule("core.ui.saved_job_actions").RECOVERY_ACTIONS
        self.assertEqual(tuple(entry.identifier for entry in enum), actions)

    def test_controls_draw_each_descriptor_in_order_with_exact_text(self):
        view = self.view(
            "ready",
            ("import_media", "import_model", "apply_world", "apply_mesh_source", "retry_receipt"),
        )
        items = self.recovery.result_actions(view)
        layout = Layout()
        self.recovery.draw_controls(layout, view)
        self.assertEqual(layout.calls, expected(items))
        self.assertEqual(
            [call[2] if call[0] == "operator" else call[1] for call in layout.calls],
            [
                "Add video strip (2)",
                "Add audio strip (3)",
                "Import model (4)",
                "Set panorama as World (1)",
                "Apply to captured source (4)",
                "Save import receipt",
                "Downloaded result awaits application review",
            ],
        )
        self.assertEqual(
            layout.calls[2][4],
            {
                "context_id": "fixture-context",
                "request_id": "fixture-request",
                "expected_revision": 4,
                "asset_id": "mesh",
            },
        )

    def test_unprojected_or_unshared_views_draw_nothing(self):
        unrevised = self.view("ready", ("import_images",))
        del unrevised.meta["saved_revision"]
        for view in (
            self.view("remote", ("refresh",), shared_job=False),
            submodule("core.jobs.records").JobRecord("local", "image", "image", "model", {}),
            unrevised,
        ):
            layout = MagicMock()
            self.recovery.draw_controls(layout, view)
            self.assertEqual(layout.mock_calls, [])

    def test_world_candidates_use_the_owner_media_types(self):
        owner = submodule("core.scene.panorama").WORLD_MEDIA_TYPES
        self.assertIs(self.recovery.RESULT_TYPES.world, owner)


class SavedJobActionTests(unittest.TestCase):
    """Real saved records projected by the shared owner."""

    def setUp(self):
        self.jobs = test_runtime_jobs.RuntimeJobTests()
        self.jobs.setUp()
        self.addCleanup(self.jobs.doCleanups)
        self.runtime = self.jobs.runtime
        self.recovery = submodule("blender.job_recovery")
        self.panels = submodule("blender.panels")

    def test_saved_views_draw_mcp_action_names_without_reading_or_changing_jobs(self):
        state = self.jobs.storemod.JobState
        records = {
            "prepared": self.jobs.saved_job("prepared"),
            "remote": self.jobs.saved_job("remote", state.SUBMITTING, state.REMOTE),
        }
        owner = self.runtime.inspect_model_jobs()
        store = self.runtime.state.job_store
        expected_labels = {
            "prepared": ["Cancel prepared job"],
            "remote": ["Refresh status", "Resume download", "Cancel generation"],
        }
        for key, labels in expected_labels.items():
            with self.subTest(key=key):
                view = owner.views[key]
                items = self.recovery.result_actions(view)
                self.assertEqual([item.label for item in items], labels)
                # Native controls and MCP job_status name the same follow-ups.
                self.assertEqual(tuple(item.action for item in items), owner.status(key)["actions"])
        refuse = AssertionError("drawing read or started jobs")
        drawn = []
        with (
            patch.object(self.runtime, "ensure_model_jobs", side_effect=refuse),
            patch.object(self.runtime, "ensure_job_session", side_effect=refuse),
            patch.object(self.runtime, "ensure_job_store", side_effect=refuse),
            patch.object(store, "get", side_effect=refuse),
            patch.object(store, "records", side_effect=refuse),
            patch.object(self.recovery, "draw_controls", wraps=self.recovery.draw_controls) as draw,
        ):
            for key in records:
                layout = Layout()
                self.recovery.draw_controls(layout, owner.views[key])
                drawn.append(layout.calls)
            self.panels.SCENARIO_PT_jobs.draw(SimpleNamespace(layout=MagicMock()), bpy.context)
        self.assertEqual(
            drawn,
            [expected(self.recovery.result_actions(owner.views[key])) for key in records],
        )
        panel_views = [call.args[1] for call in draw.call_args_list[len(records) :]]
        self.assertEqual({id(view) for view in panel_views}, {id(v) for v in owner.views.values()})
        self.assertEqual({key: store.get(key) for key in records}, records)
        self.assertEqual(self.jobs.requests, [])


if __name__ == "__main__":
    unittest.main()
