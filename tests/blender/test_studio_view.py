# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Installed Studio navigation and shared-state contracts; not physical input proof."""

import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import bpy
import test_workflow_commands
from helpers import submodule


class StudioViewTests(unittest.TestCase):
    def setUp(self):
        self.workflow = test_workflow_commands.WorkflowCommandTests()
        self.workflow.setUp()
        self.addCleanup(self.workflow.doCleanups)
        self.studio = submodule("blender.studio")
        self.runtime = self.workflow.runtime
        self.view = bpy.context.window_manager.scenario_studio_view
        self.addCleanup(setattr, self.view, "page", self.view.page)
        self.addCleanup(setattr, self.view, "film_page", self.view.film_page)
        self.composer = submodule("blender.composer.state").ComposerState()
        self.runtime.state.composer = self.composer

    def test_registration_exposes_only_explicit_operator_and_unsaved_navigation(self):
        self.assertTrue(hasattr(bpy.ops.scenario, "open_studio"))
        self.assertFalse(self.studio.SCENARIO_OT_open_studio.poll(bpy.context))
        self.assertTrue(self.view.bl_rna.properties["page"].is_skip_save)
        self.assertTrue(self.view.bl_rna.properties["film_page"].is_skip_save)
        self.assertFalse(self.workflow.sessions)
        self.assertFalse(self.workflow.calls)

    def test_page_changes_and_drawing_preserve_exact_quote_and_scope(self):
        quote = self.workflow.quote()
        owner = self.runtime.state.model_jobs
        ticket = owner.require_quote(quote["quote_id"])
        scene = bpy.context.scene
        before = owner.session.capture(scene)
        original_parameters = scene.scenario.image.prompt
        for page, _, _ in self.studio.PAGES:
            self.view.page = page
            # Native edits tag their owner, unlike direct Python assignment.
            self.view.id_data.update_tag()
            bpy.context.view_layer.update()
            pages = self.studio.FILM_PAGES if page == "FILM" else (("TASKS", "", ""),)
            for film_page, _, _ in pages:
                self.view.film_page = film_page
                self.view.id_data.update_tag()
                bpy.context.view_layer.update()
                layout = MagicMock()
                with patch.object(
                    self.runtime,
                    "ensure_model_jobs",
                    side_effect=AssertionError("draw started jobs"),
                ):
                    self.studio.draw_view(layout, bpy.context, width=960)
                self.assertEqual(owner.session.capture(scene), before)
                self.assertIs(owner.require_quote(quote["quote_id"]), ticket)
        self.assertEqual(scene.scenario.image.prompt, original_parameters)
        self.assertFalse(self.workflow.store.records())
        self.assertFalse(self.workflow.paid)
        self.assertEqual(len(self.workflow.calls), 2)

    def test_surface_navigation_preserves_admitted_work_and_results_owner(self):
        result = self.workflow.approve(self.workflow.quote())
        owner = self.runtime.state.model_jobs
        self.view.page = "RESULTS"
        self.studio.draw_view(MagicMock(), bpy.context, width=400)
        self.view.page = "CREATE"
        self.studio.prepare_view(bpy.context)
        self.workflow.settle()
        self.assertIs(self.runtime.state.model_jobs, owner)
        self.assertEqual(self.workflow.store.get(result["local_id"]).state.value, "remote")
        self.assertEqual(len(self.workflow.paid), 1)

    def test_preparing_view_flushes_focused_prompt_and_preserves_references(self):
        scene = bpy.context.scene
        scene.scenario.lane = "image"
        state = scene.scenario.lane_state("image")
        state.prompt = "original"
        reference = state.references.add()
        reference.source, reference.asset_id = "ASSET", "fixture-reference"
        self.composer.sync_from_lane(scene)
        self.composer.focused = True
        self.composer.field.set_text("Café 雪 updated")
        self.studio.prepare_view(bpy.context)
        self.assertEqual(state.prompt, "Café 雪 updated")
        self.assertEqual(state.references[0].asset_id, "fixture-reference")
        self.assertFalse(self.composer.focused)
        self.assertFalse(self.workflow.calls)

    def test_changed_form_rejects_flush_without_overwriting_either_prompt(self):
        scene = bpy.context.scene
        scene.scenario.lane = "image"
        state = scene.scenario.lane_state("image")
        state.prompt = "original"
        self.composer.sync_from_lane(scene)
        self.composer.focused = True
        self.composer.field.set_text("pending composer")
        state.prompt = "new sidebar value"
        with self.assertRaisesRegex(RuntimeError, "original prompt"):
            self.studio.prepare_view(bpy.context)
        self.assertEqual(state.prompt, "new sidebar value")
        self.assertEqual(self.composer.field.text, "pending composer")
        self.assertTrue(self.composer.focused)

    def test_click_outside_focused_composer_commits_and_reaches_native_controls(self):
        modal = submodule("blender.composer.modal")
        scene = bpy.context.scene
        scene.scenario.lane = "image"
        self.composer.sync_from_lane(scene)
        self.composer.focused = True
        self.composer.field.set_text("Café 雪 pending")
        self.runtime.state.composer_modal_running = True
        context = SimpleNamespace(scene=scene, region=MagicMock())
        event = SimpleNamespace(
            type="LEFTMOUSE", value="PRESS", mouse_region_x=10, mouse_region_y=10
        )
        operator = SimpleNamespace()
        operator._finish = lambda ctx: modal.SCENARIO_OT_composer_modal._finish(operator, ctx)
        with patch.object(modal, "_layout") as layout:
            layout.return_value.hit.return_value = None
            result = modal.SCENARIO_OT_composer_modal.modal(operator, context, event)
        self.assertEqual(result, {"FINISHED", "PASS_THROUGH"})
        self.assertEqual(scene.scenario.image.prompt, "Café 雪 pending")
        self.assertFalse(self.composer.focused)
        self.assertFalse(self.runtime.state.composer_modal_running)
        self.assertFalse(self.workflow.calls)

    def test_other_scene_with_same_prompt_cannot_receive_pending_composer_text(self):
        original = bpy.context.scene
        original.scenario.lane = "image"
        self.composer.sync_from_lane(original)
        self.composer.focused = True
        self.composer.field.set_text("pending original scene")
        other = bpy.data.scenes.new("Other Studio scene")
        try:
            other.scenario.image.prompt = original.scenario.image.prompt
            with self.assertRaisesRegex(RuntimeError, "original prompt"):
                self.studio.prepare_view(SimpleNamespace(scene=other))
            self.assertEqual(other.scenario.image.prompt, original.scenario.image.prompt)
        finally:
            bpy.data.scenes.remove(other)

    def test_outside_click_rejects_changed_prompt_lane_or_scene_before_native_handoff(self):
        modal = submodule("blender.composer.modal")
        original = bpy.context.scene
        other = bpy.data.scenes.new("Other blur scene")
        self.addCleanup(bpy.data.scenes.remove, other)
        for conflict in ("prompt", "lane", "scene"):
            with self.subTest(conflict=conflict):
                original.scenario.lane = "image"
                original.scenario.image.prompt = "original"
                self.composer.sync_from_lane(original)
                self.composer.focused = True
                self.composer.field.set_text("pending composer")
                scene = original
                if conflict == "prompt":
                    original.scenario.image.prompt = "new sidebar value"
                elif conflict == "lane":
                    original.scenario.lane = "video"
                    original.scenario.video.prompt = "original"
                else:
                    scene = other
                    other.scenario.lane = "image"
                    other.scenario.image.prompt = "original"
                lane_state = scene.scenario.lane_state(self.composer.lane_for(scene))
                before = lane_state.prompt
                self.runtime.state.composer_modal_running = True
                context = SimpleNamespace(scene=scene, region=MagicMock())
                event = SimpleNamespace(
                    type="LEFTMOUSE", value="PRESS", mouse_region_x=10, mouse_region_y=10
                )
                operator = SimpleNamespace(report=MagicMock(), _finish=MagicMock())
                with patch.object(modal, "_layout") as layout:
                    layout.return_value.hit.return_value = None
                    result = modal.SCENARIO_OT_composer_modal.modal(operator, context, event)
                self.assertEqual(lane_state.prompt, before)
                self.assertEqual(self.composer.field.text, "pending composer")
                self.assertTrue(self.composer.focused)
                self.assertTrue(self.runtime.state.composer_modal_running)
                self.assertEqual(result, {"RUNNING_MODAL"})
                operator._finish.assert_not_called()
                operator.report.assert_called_once()
                with self.assertRaisesRegex(RuntimeError, "original prompt"):
                    self.studio.prepare_view(context)
        self.assertFalse(self.workflow.calls)

    def test_outside_click_without_focus_does_not_commit_stale_composer_text(self):
        modal = submodule("blender.composer.modal")
        scene = bpy.context.scene
        scene.scenario.lane = "image"
        self.composer.sync_from_lane(scene)
        scene.scenario.image.prompt = "new sidebar value"
        context = SimpleNamespace(scene=scene, region=MagicMock())
        event = SimpleNamespace(
            type="LEFTMOUSE", value="PRESS", mouse_region_x=10, mouse_region_y=10
        )
        operator = SimpleNamespace(_finish=MagicMock(return_value={"FINISHED"}))
        with patch.object(modal, "_layout") as layout:
            layout.return_value.hit.return_value = None
            result = modal.SCENARIO_OT_composer_modal.modal(operator, context, event)
        self.assertEqual(scene.scenario.image.prompt, "new sidebar value")
        self.assertEqual(result, {"FINISHED", "PASS_THROUGH"})

    def test_popup_width_respects_area_window_and_dpi(self):
        context = SimpleNamespace(
            area=SimpleNamespace(width=1280),
            window=SimpleNamespace(width=1920),
            preferences=SimpleNamespace(system=SimpleNamespace(ui_scale=1)),
        )
        self.assertEqual(self.studio.popup_width(context), 960)
        context.area.width = 640
        self.assertEqual(self.studio.popup_width(context), 592)
        context.preferences.system.ui_scale = 2
        self.assertEqual(self.studio.popup_width(context), 272)
        context.area.width, context.window.width = 1920, 800
        self.assertEqual(self.studio.popup_width(context), 352)

    def test_compact_navigation_bounds_segment_rows(self):
        panels = submodule("blender.panels")
        self.view.page = "JOBS"
        with patch.object(panels, "draw_enum_tabs") as tabs:
            self.studio.draw_view(MagicMock(), bpy.context, width=400)
        self.assertEqual(len(tabs.call_args.args[3]), 3)
        self.assertTrue(all(len(row) <= 3 for row in tabs.call_args.args[3]))
        with patch.object(panels, "draw_enum_tabs") as tabs:
            self.studio.draw_view(MagicMock(), bpy.context, width=960)
        self.assertEqual(len(tabs.call_args.args[3]), 1)

    def test_invoke_requests_popup_without_starting_shared_workers(self):
        manager = SimpleNamespace(invoke_popup=MagicMock(return_value={"RUNNING_MODAL"}))
        context = SimpleNamespace(
            scene=bpy.context.scene,
            window_manager=manager,
            area=SimpleNamespace(width=1000),
            window=SimpleNamespace(width=1200),
            preferences=bpy.context.preferences,
        )
        operator = SimpleNamespace(report=MagicMock())
        result = self.studio.SCENARIO_OT_open_studio.invoke(operator, context, None)
        self.assertEqual(result, {"RUNNING_MODAL"})
        manager.invoke_popup.assert_called_once_with(operator, width=operator._width)
        self.assertFalse(self.workflow.sessions)
        self.assertFalse(self.workflow.calls)

    def test_popup_refresh_uses_temporary_region_without_owning_operator_lifetime(self):
        import gc

        class Owner:
            pass

        owner = Owner()
        region = MagicMock()
        self.studio._popups[owner] = region
        self.studio.redraw_popups()
        region.tag_refresh_ui.assert_called_once_with()
        del owner
        gc.collect()
        self.assertFalse(self.studio._popups)

    def test_popup_refresh_discards_removed_region(self):
        class Owner:
            pass

        owner = Owner()
        region = MagicMock()
        region.tag_refresh_ui.side_effect = ReferenceError("closed popup")
        self.studio._popups[owner] = region
        self.studio.redraw_popups()
        self.assertFalse(self.studio._popups)
