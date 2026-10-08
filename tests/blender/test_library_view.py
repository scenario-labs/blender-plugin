# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Installed library navigation and confirmed references with offline SDK transport."""

import dataclasses
import gc
import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import bpy
import test_asset_library
from helpers import submodule


class LibraryViewTests(unittest.TestCase):
    def setUp(self):
        self.fixture = test_asset_library.AssetLibraryTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.runtime = self.fixture.runtime
        self.module = submodule("blender.library_view")
        self.reference = submodule("blender.reference_form")
        self.generation = submodule("blender.generation")
        self.owner = self.module.controls(create=True)
        self.scene = bpy.context.scene
        self.scene.scenario.lane = "image"
        self.lane = self.scene.scenario.image
        self.model = {
            "id": "fixture-library-model",
            "name": "Library model",
            "type": "custom",
            "capabilities": ["txt2img"],
            "inputs": [
                {"name": "prompt", "type": "string", "prompt": True},
                {"name": "image", "type": "file", "kind": "image"},
                {"name": "images", "type": "file_array", "kind": "image", "maxLength": 2},
                {"name": "audio", "type": "file", "kind": "audio"},
            ],
        }
        record = submodule("core.api.catalog").ModelRecord.from_api(self.model)
        self.generation.set_catalog([record], [record])
        self.lane.model_id = record.id
        self.view = bpy.context.window_manager.scenario_library_view
        for key in ("query", "public", "collection"):
            self.addCleanup(setattr, self.view, key, getattr(self.view, key))
        self.view.query, self.view.public, self.view.collection = "", False, ""

    def finish(self):
        try:
            self.owner.task.result(timeout=10)
        except Exception:
            pass
        self.owner.poll()
        self.assertIsNone(self.owner.task)

    def load(self, filters=("", False, ""), direction="REFRESH"):
        self.owner.start(self.scene, filters, direction)
        self.finish()
        self.assertFalse(self.owner.error, self.owner.error)

    def approval(self, name="image"):
        return next(
            x for x in self.owner.prepare(bpy.context, "fixture-asset") if x.param_name == name
        )

    def test_refresh_and_explicit_pagination_use_one_worker_read_per_page(self):
        self.load()
        self.assertEqual(self.owner.assets[0]["asset_id"], "fixture-asset")
        self.assertNotIn("url", self.owner.assets[0])
        self.assertEqual(len(self.fixture.calls), 1)
        self.load(direction="NEXT")
        self.assertEqual(self.owner.index, 1)
        self.assertIsNone(self.owner.next_cursor)
        self.load(direction="PREVIOUS")
        self.assertEqual(self.owner.index, 0)
        self.assertEqual(len(self.fixture.calls), 3)
        self.assertFalse(self.fixture.fixture.store.records())
        self.assertIsNone(self.runtime.state.model_jobs)

    def test_unrelated_scene_edits_do_not_discard_library_page(self):
        self.owner.start(self.scene, ("", False, ""))
        self.scene.frame_set(9)
        self.lane.prompt = "new prompt while browsing"
        self.scene.update_tag()
        bpy.context.view_layer.update()
        self.finish()
        self.assertFalse(self.owner.error)
        self.assertEqual(len(self.owner.assets), 1)
        self.assertEqual(self.lane.prompt, "new prompt while browsing")

    def test_catalog_delivery_is_owned_single_use_and_cannot_deliver_workflow_details(self):
        session = self.owner.session
        task = session.asset_library(self.scene)
        task.result(timeout=10)
        completion = session.drain(task=task)[0]
        forged = dataclasses.replace(completion)
        with self.assertRaises(submodule("blender.job_session").OriginUnavailable):
            session.deliver_asset_library(forged)
        self.assertEqual(len(session.deliver_asset_library(completion)["assets"]), 1)
        with self.assertRaises(submodule("blender.job_session").OriginUnavailable):
            session.deliver_asset_library(completion)
        # An actual owned workflow-catalog completion grants no library authority.
        from concurrent.futures import Future

        other = Future()
        other.set_result([])
        session._workflow_reads[other] = None
        session._pending.append((other, session.capture(self.scene)))
        completion = session.drain(task=other)[0]
        with self.assertRaises(submodule("blender.job_session").OriginUnavailable):
            session.deliver_asset_library(completion)
        self.assertEqual(session.deliver_workflow_catalog(completion), [])

    def test_filter_change_requires_refresh_and_search_does_not_ignore_collection(self):
        self.load()
        with self.assertRaisesRegex(ValueError, "Filters changed"):
            self.owner.start(self.scene, ("cup", False, ""), "NEXT")
        with self.assertRaisesRegex(ValueError, "Clear Collection"):
            self.owner.start(self.scene, ("cup", False, "collection"))
        self.assertEqual(len(self.fixture.calls), 1)
        self.load(("cup", True, ""))
        self.assertEqual(self.owner.next_cursor, 1)
        self.load(("cup", True, ""), "NEXT")
        self.assertEqual(self.owner.index, 1)

    def test_failure_preserves_last_page_and_explicit_retry(self):
        self.load()
        self.fixture.fail = True
        self.owner.start(self.scene, ("", False, ""), "NEXT")
        self.finish()
        self.assertTrue(self.owner.error)
        self.assertEqual(self.owner.index, 0)
        self.assertEqual(len(self.owner.assets), 1)
        self.fixture.fail = False
        self.load(direction="NEXT")

    def test_confirmation_attaches_asset_without_network_or_upload_and_invalidates_price(self):
        self.load()
        self.lane.estimate_state, self.lane.estimate_key = "READY", "old"
        approval = self.approval()
        self.assertEqual(len(self.lane.references), 0)
        ref = self.owner.attach(approval)
        self.assertEqual(
            (ref.source, ref.asset_id, ref.param_name), ("ASSET", "fixture-asset", "image")
        )
        self.assertFalse(ref.get(self.reference._MARKER))
        self.assertIsNone(self.reference.scope_error(self.lane))
        self.assertEqual(self.lane.estimate_key, "")
        self.assertEqual(len(self.fixture.calls), 1)
        request = self.generation.build_request(self.scene, "image", for_estimate=True)
        self.assertEqual(request.body["image"], "fixture-asset")
        self.assertFalse(request.files)
        self.assertFalse(request.captures)
        with self.assertRaisesRegex(ValueError, "Review this asset"):
            self.owner.attach(approval)
        self.assertFalse(self.fixture.fixture.store.records())

    def test_canceled_confirmation_retains_no_reference_or_approval(self):
        self.load()
        approvals = self.owner.prepare(bpy.context, "fixture-asset")
        self.assertEqual({x.param_name for x in approvals}, {"image", "images"})
        self.assertTrue(self.owner.approvals)
        del approvals
        gc.collect()
        self.assertFalse(self.owner.approvals)
        self.assertFalse(self.lane.references)

    def test_occupied_single_and_full_array_are_not_replaced(self):
        self.load()
        self.owner.attach(self.approval())
        choices = self.owner.prepare(bpy.context, "fixture-asset")
        self.assertEqual([x.param_name for x in choices], ["images"])
        self.owner.attach(choices[0])
        with self.assertRaisesRegex(ValueError, "No matching empty"):
            self.owner.prepare(bpy.context, "fixture-asset")
        ref = self.lane.references.add()
        ref.param_name, ref.source, ref.asset_id = "images", "ASSET", "other"
        self.owner.assets[0]["asset_id"] = "third"
        with self.assertRaisesRegex(ValueError, "No matching empty"):
            self.owner.prepare(bpy.context, "third")
        self.assertEqual(len(self.lane.references), 3)

    def test_edited_destination_and_forged_confirmation_cannot_attach(self):
        self.load()
        approval = self.approval()
        with self.assertRaises(ValueError):
            self.owner.attach(dataclasses.replace(approval))
        self.lane.references.add().param_name = "images"
        with self.assertRaisesRegex(ValueError, "destination changed"):
            self.owner.attach(approval)
        self.assertEqual(len(self.lane.references), 1)
        self.assertEqual(self.lane.references[0].asset_id, "")

    def test_connection_change_rejects_confirmation_and_persisted_reference(self):
        self.load()
        self.owner.attach(self.approval())
        approval = self.approval("images")
        self.fixture.fixture.prefs.project_id = "different-project"
        with self.assertRaises(ValueError):
            self.owner.attach(approval)
        self.runtime.ensure_job_session()
        self.assertIn("another connection", self.reference.scope_error(self.lane))
        self.assertIsNone(self.module.controls())
        self.assertEqual(len(self.lane.references), 1)

    def test_draw_and_navigation_are_read_only_and_unknown_types_cannot_attach(self):
        self.load()
        before = self.owner.session.capture(self.scene)
        self.view.query = "new filters"
        with patch.object(
            self.runtime, "ensure_job_session", side_effect=AssertionError("draw starts worker")
        ):
            self.module.draw(MagicMock(), bpy.context)
        self.assertEqual(self.owner.session.capture(self.scene), before)
        self.assertEqual(len(self.fixture.calls), 1)
        self.owner.assets[0]["mime_type"] = "application/octet-stream"
        with self.assertRaisesRegex(ValueError, "supported file type"):
            self.owner.prepare(bpy.context, "fixture-asset")
        self.assertTrue(self.view.bl_rna.properties["query"].is_skip_save)
        self.assertTrue(self.view.bl_rna.properties["public"].is_skip_save)

    def test_native_confirmation_shows_destination_and_requires_invoke(self):
        self.load()
        self.assertEqual(
            bpy.ops.scenario.library_reference(asset_id="fixture-asset"), {"CANCELLED"}
        )
        operator = SimpleNamespace(asset_id="fixture-asset", report=MagicMock(), layout=MagicMock())
        manager = SimpleNamespace(invoke_props_dialog=MagicMock(return_value={"RUNNING_MODAL"}))
        context = SimpleNamespace(scene=self.scene, window_manager=manager)
        cls = self.module.SCENARIO_OT_library_reference
        self.assertEqual(cls.invoke(operator, context, None), {"RUNNING_MODAL"})
        cls.draw(operator, context)
        labels = [call.kwargs.get("text") for call in operator.layout.label.call_args_list]
        self.assertIn("Scene: " + self.scene.name, labels)
        self.assertIn("Model: Library model", labels)
        self.assertFalse(self.lane.references)
        self.assertEqual(cls.execute(operator, context), {"FINISHED"})
        self.assertEqual(len(self.lane.references), 1)

    def test_changed_selected_scene_rejects_confirmation(self):
        self.load()
        approval = self.approval()
        other = bpy.data.scenes.new("Other library destination")
        try:
            bpy.context.window.scene = other
            with self.assertRaises(submodule("blender.job_session").OriginUnavailable):
                self.owner.attach(approval)
            self.assertFalse(other.scenario.image.references)
            self.assertFalse(self.lane.references)
        finally:
            bpy.context.window.scene = self.scene
            bpy.data.scenes.remove(other)

    def test_repeated_pagination_token_is_not_followed(self):
        self.load()
        self.owner.cursors = [None, "repeated"]
        self.owner.index = 1
        self.owner.next_cursor = "new-page"
        self.owner.start(self.scene, ("", False, ""), "NEXT")
        self.owner.task.result(timeout=10)
        with patch.object(
            self.owner.session,
            "deliver_asset_library",
            return_value={"assets": [self.fixture.asset], "next_pagination_token": "repeated"},
        ):
            self.owner.poll()
        self.assertTrue(self.owner.error)
        self.assertEqual(self.owner.index, 1)
        self.assertEqual(len(self.fixture.calls), 2)

    def test_deleted_scene_keeps_confirmation_draw_safe_and_cannot_attach(self):
        self.load()
        approval = self.approval()
        scene_name = self.scene.name
        operator = SimpleNamespace(_approvals=[approval], layout=MagicMock())
        replacement = bpy.data.scenes.new("Replacement Library scene")
        bpy.context.window.scene = replacement
        bpy.data.scenes.remove(self.scene)
        self.module.SCENARIO_OT_library_reference.draw(operator, bpy.context)
        labels = [call.kwargs.get("text") for call in operator.layout.label.call_args_list]
        self.assertIn("Scene: " + scene_name, labels)
        with self.assertRaises(submodule("blender.job_session").OriginUnavailable):
            self.owner.attach(approval)
        self.assertFalse(replacement.scenario.image.references)
