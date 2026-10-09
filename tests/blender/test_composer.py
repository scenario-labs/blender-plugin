# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
import contextlib
import json
import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import bpy
import test_model_generation
from helpers import reset_scene, submodule


class BreakerTests(unittest.TestCase):
    def test_trips_after_consecutive_failures_and_on_stall(self):
        breaker_mod = submodule("blender.composer.breaker")
        trips = []
        clock = {"t": 0.0}
        b = breaker_mod.Breaker(
            "t", failures=3, stall=2.0, on_trip=trips.append, clock=lambda: clock["t"]
        )

        def boom():
            raise RuntimeError("x")

        for _ in range(3):
            b.guard(boom)
        self.assertTrue(b.tripped)
        self.assertEqual(len(trips), 1)
        b.reset()
        self.assertEqual(b.guard(lambda: 1), 1)  # first call is exempt from the stall rule

        def slow():
            clock["t"] += 2.5
            return "ok"

        b.guard(slow)
        self.assertTrue(b.tripped and "took" in b.reason)


class ComposerStateTests(unittest.TestCase):
    def setUp(self):
        reset_scene()
        self.state_mod = submodule("blender.composer.state")
        self.runtime = submodule("blender.runtime")

    def test_state_mirrors_prompt_both_ways(self):
        scene = bpy.context.scene
        scene.scenario.lane = "image"
        scene.scenario.lane_state("image").prompt = "from panel"
        state = self.state_mod.ComposerState()
        state.sync_from_lane(scene)
        self.assertEqual(state.field.text, "from panel")
        state.field.insert(" and composer")
        state.commit_to_lane(scene)
        self.assertEqual(scene.scenario.lane_state("image").prompt, "from panel and composer")
        scene.scenario.lane = "material"
        scene.scenario.lane_state("material").prompt = "copper"
        state.sync_from_lane(scene)
        self.assertEqual(state.field.text, "copper")

    def test_composer_registered_with_state_and_operator(self):
        self.assertIsNotNone(self.runtime.state.composer)
        self.assertTrue(hasattr(bpy.types, "SCENARIO_OT_composer_modal"))
        self.assertFalse(self.runtime.state.composer.dragging)

    def test_lane_for_covers_the_six_generation_lanes_and_falls_back_to_image(self):
        scene = bpy.context.scene
        state = self.state_mod.ComposerState()
        for lane in ("image", "video", "3d", "material"):
            scene.scenario.lane = lane
            self.assertEqual(state.lane_for(scene), lane)
        for lane in ("render_image", "render_video"):
            try:
                scene.scenario.lane = lane
            except TypeError:
                self.skipTest(f"lane {lane} not in the scene enum yet")
            if scene.scenario.lane_state(lane) is None:
                self.skipTest(f"lane state {lane} not wired yet")
            self.assertEqual(state.lane_for(scene), lane)
            scene.scenario.lane_state(lane).prompt = "look"
            self.assertEqual(state.sync_from_lane(scene).prompt, "look")
        for lane in ("audio",):  # a lane tab the composer does not show
            scene.scenario.lane = lane
            self.assertEqual(state.lane_for(scene), "image")

    def test_selection_survives_commit_and_sync_resets_it(self):
        scene = bpy.context.scene
        scene.scenario.lane = "image"
        scene.scenario.lane_state("image").prompt = "hello world"
        state = self.state_mod.ComposerState()
        state.sync_from_lane(scene)
        state.field.caret_at(0)
        state.field.caret_at(5, extend=True)
        self.assertEqual(state.field.selected_text(), "hello")
        state.field.insert("bye")
        state.commit_to_lane(scene)
        self.assertEqual(scene.scenario.lane_state("image").prompt, "bye world")
        scene.scenario.lane_state("image").prompt = "from panel"
        state.sync_from_lane(scene)
        self.assertIsNone(state.field.selection)
        self.assertEqual(state.field.caret, len("from panel"))


class ComposerDrawHelpersTests(unittest.TestCase):
    def test_caret_index_at_maps_pixels_to_glyph_boundaries(self):
        draw = submodule("blender.composer.draw")
        cl = submodule("core.ui.composer_layout")
        field = cl.TextField("hello world")
        pr = cl.Rect(100, 100, 400, 34)
        try:
            font_px, start, end, x0 = draw.prompt_metrics(pr, field, 1.0)
        except Exception as err:  # blf without a font in some background builds
            self.skipTest(f"blf unavailable: {err}")
        self.assertEqual((start, end), (0, len(field.text)))
        self.assertEqual(draw.caret_index_at(x0 - 5, pr, field, 1.0), 0)
        self.assertEqual(draw.caret_index_at(x0 + 10_000, pr, field, 1.0), len(field.text))
        import blf

        blf.size(draw.FONT, font_px)
        mid = x0 + blf.dimensions(draw.FONT, "hello")[0]
        self.assertEqual(draw.caret_index_at(mid, pr, field, 1.0), 5)


class ComposerPlacementTests(unittest.TestCase):
    def setUp(self):
        reset_scene()
        self.composer = submodule("blender.composer")
        self.state_mod = submodule("blender.composer.state")
        self.runtime = submodule("blender.runtime")
        self.cl = submodule("core.ui.composer_layout")

    def _prefs(self):
        prefs = self.runtime.prefs()
        if prefs is None or not hasattr(prefs, "composer_offset_x"):
            self.skipTest("composer placement preferences not installed")
        return prefs

    def test_state_has_placement_fields_and_drag_lifecycle(self):
        state = self.state_mod.ComposerState()
        self.assertEqual(state.offset, (0.0, 0.0))
        self.assertIsNone(state.width)
        self.assertIsNone(state.drag_mode)
        state.begin_drag((10, 10), "drag")
        self.assertEqual(state.drag_mode, "pending")
        state.drag_mode, state.moved = "move", True
        state.offset = (40.0, 20.0)
        kind, mode, moved = state.end_drag()
        self.assertEqual((kind, mode, moved), ("drag", "move", True))
        self.assertEqual(state.offset, (40.0, 20.0))
        state.begin_drag((0, 0), "resize")
        self.assertEqual(state.drag_mode, "resize")
        state.width = 900
        state.cancel_drag()  # Escape restores what the press started from
        self.assertIsNone(state.width)
        self.assertIsNone(state.drag_mode)
        state.offset, state.width = (5.0, 5.0), 700
        state.reset_layout()
        self.assertEqual((state.offset, state.width), ((0.0, 0.0), None))

    def test_layout_round_trips_through_preferences(self):
        prefs = self._prefs()
        state = self.runtime.state.composer
        self.assertIsNotNone(state)
        saved = (prefs.composer_offset_x, prefs.composer_offset_y, prefs.composer_width)
        try:
            state.offset, state.width = (33.0, -12.0), 960
            self.assertTrue(self.composer.save_layout())
            self.assertEqual(
                (prefs.composer_offset_x, prefs.composer_offset_y, prefs.composer_width),
                (33.0, -12.0, 960),
            )
            state.offset, state.width = (0.0, 0.0), None
            self.assertTrue(self.composer.load_layout())
            self.assertEqual(state.offset, (33.0, -12.0))
            self.assertEqual(state.width, 960)
            prefs.composer_width = 0
            self.composer.load_layout()
            self.assertIsNone(state.width)
            bpy.ops.scenario.composer_reset_layout()
            self.assertEqual((state.offset, state.width), ((0.0, 0.0), None))
            self.assertEqual(
                (prefs.composer_offset_x, prefs.composer_offset_y, prefs.composer_width),
                (0.0, 0.0, 0),
            )
        finally:
            prefs.composer_offset_x, prefs.composer_offset_y, prefs.composer_width = saved
            self.composer.load_layout()

    def test_placement_feeds_the_layout_and_lane_for_still_works(self):
        state = self.state_mod.ComposerState()
        state.offset, state.width = (100.0, 50.0), 900
        layout = self.cl.pill_placement(
            1600, 900, True, 1.0, offset=state.offset, width=state.width
        )
        self.assertEqual(layout.card_rect.w, 900)
        self.assertEqual(layout.card_rect.y, self.cl.MARGIN + 50.0)
        scene = bpy.context.scene
        scene.scenario.lane = "video"
        self.assertEqual(state.lane_for(scene), "video")
        draw = submodule("blender.composer.draw")
        self.assertTrue(callable(draw.status_note))


class ComposerEditFormTests(unittest.TestCase):
    """The 3D tab in Edit mode: the composer shows, prices and submits the Edit 3D form."""

    def setUp(self):
        self.jobs = test_model_generation.ModelGenerationTests()
        self.jobs.setUp()
        self.addCleanup(self.jobs.doCleanups)
        self.runtime = self.jobs.runtime
        self.generation = self.jobs.generation
        self.panels = submodule("blender.panels")
        self.draw = submodule("blender.composer.draw")
        self.modal = submodule("blender.composer.modal")
        self.composer = submodule("blender.composer.state").ComposerState()
        self.composer.expanded = True
        self.runtime.state.composer = self.composer
        self.scene = bpy.context.scene
        self.scene.scenario.lane = "3d"
        self.scene.scenario.three_d_mode = "TEXT"
        self.models = {}
        prompt = {"name": "prompt", "type": "string", "required": True, "prompt": True}
        self.configure(
            "3d",
            {
                "id": "fixture-text-3d",
                "name": "Text to 3D",
                "type": "custom",
                "capabilities": ["txt23d"],
                "inputs": [prompt],
            },
            "a teapot",
        )
        self.quote("3d", "1.5")
        # Switching to Edit keeps the Text form's price; only the Edit form is repriced.
        self.scene.scenario.three_d_mode = "EDIT"
        bpy.ops.mesh.primitive_cube_add()
        mesh = {"name": "mesh", "type": "file", "kind": "3d", "required": True}
        self.configure(
            "edit3d",
            {
                "id": "fixture-retexture",
                "name": "Retexture",
                "type": "custom",
                "capabilities": ["3d23d"],
                "inputs": [prompt, mesh],
            },
            "rusty iron plates",
        )
        reference = self.scene.scenario.edit3d.references.add()
        reference.param_name, reference.source = "mesh", "ASSET"
        reference.asset_id = "uploaded-mesh"
        self.three_d = self.scene.scenario.three_d
        self.edit3d = self.scene.scenario.edit3d

    def configure(self, lane, model, prompt):
        self.models[lane] = model
        record = submodule("core.api.catalog").ModelRecord.from_api(model)
        self.runtime.state.records[record.id] = record
        self.runtime.state.lane_models[lane] = [record]
        self.generation._schemas.pop(record.id, None)
        self.runtime.set_enum_items(("models", lane), [(record.id, record.name, "")])
        state = self.scene.scenario.lane_state(lane)
        state.model_id = record.id
        self.generation.on_model_changed(bpy.context, state)
        state.prompt = prompt

    def quote(self, lane, cost):
        self.jobs.model = self.models[lane]  # the fixture describes the model it quotes
        self.jobs.dry_run_costs[self.scene.scenario.lane_state(lane).model_id] = cost
        self.jobs.ui_quote(lane)

    def drawn(self):
        """Run the real composer draw with recording primitives and return what it shows."""
        shown = SimpleNamespace(rects=[], texts=[], chips=[], fields=[])
        context = SimpleNamespace(
            region=SimpleNamespace(width=1600, height=900),
            scene=self.scene,
            space_data=SimpleNamespace(type="VIEW_3D", region_3d=object()),
            preferences=SimpleNamespace(
                system=SimpleNamespace(pixel_size=1.0), view=SimpleNamespace(ui_scale=1.0)
            ),
        )
        blf = MagicMock()
        blf.dimensions.return_value = (10.0, 10.0)
        placeholder_for = submodule("core.ui.composer_layout").placeholder_for

        def chip(rect, label, *args, fill=None, **kwargs):
            shown.chips.append(label)
            if fill == self.draw.ACCENT:
                shown.active_tab = label

        def prompt_field(rect, field, focused, lane, scale, placeholder=None):
            shown.fields.append(field.text or placeholder or placeholder_for(lane))

        recorders = {
            "bpy": SimpleNamespace(context=context),
            "gpu": MagicMock(),
            "blf": blf,
            "_minus_button": MagicMock(),
            "_grip": MagicMock(),
            "rect": MagicMock(side_effect=lambda *args, **kwargs: shown.rects.append(args)),
            "text": MagicMock(side_effect=lambda x, y, size, s, *a, **k: shown.texts.append(s)),
            "_chip": MagicMock(side_effect=chip),
            "_prompt_field": MagicMock(side_effect=prompt_field),
        }
        with contextlib.ExitStack() as stack:
            for name, value in recorders.items():
                stack.enter_context(patch.object(self.draw, name, value))
            self.draw.draw_composer()
        gr = self.composer.layout.generate_rect
        fill = next(args[4] for args in shown.rects if args[:4] == (gr.x, gr.y, gr.w, gr.h))
        shown.enabled = fill == self.draw.ACCENT
        shown.label = next(s for s in shown.texts if s.startswith("Generate"))
        return shown

    def press(self, kind=None, key=None, text="", expect=("RUNNING_MODAL",)):
        """Deliver one composer click (on `kind`) or one key press to the real modal handler."""
        self.runtime.state.composer_modal_running = True
        context = SimpleNamespace(scene=self.scene, region=MagicMock())
        event = SimpleNamespace(
            type=key or "LEFTMOUSE",
            value="PRESS",
            mouse_region_x=10,
            mouse_region_y=10,
            shift=False,
            ctrl=False,
            oskey=False,
            alt=False,
            unicode=text,
        )
        operator = SimpleNamespace(report=MagicMock(), _finish=MagicMock())
        with patch.object(self.modal, "_layout") as layout:
            layout.return_value.hit.return_value = (kind,) if kind else None
            result = self.modal.SCENARIO_OT_composer_modal.modal(operator, context, event)
        self.assertEqual(result, set(expect))
        return operator

    def switch_mode(self, mode):
        """Switch the 3D input mode like the sidebar or Settings; the fixture catalog lists the form's model again."""
        self.scene.scenario.three_d_mode = mode
        lane = "edit3d" if mode == "EDIT" else "3d"
        self.configure(lane, self.models[lane], self.scene.scenario.lane_state(lane).prompt)

    def focus_text_form(self):
        """Focus the composer on the 3D tab's Text form, then let the form behind it become Edit 3D."""
        self.composer.focused = False
        self.switch_mode("TEXT")
        self.edit3d.prompt, self.three_d.prompt = "rusty iron plates", "a teapot"
        self.drawn()
        self.composer.focused = True
        self.assertEqual(self.composer.field.text, "a teapot")
        # A Settings mode switch, a 3D-to-3D model pick, another window or a tool can change it.
        self.switch_mode("EDIT")
        self.quote("edit3d", "7.25")

    def assert_prompts_unchanged(self):
        self.assertEqual(
            (self.three_d.prompt, self.edit3d.prompt), ("a teapot", "rusty iron plates")
        )

    def test_composer_displays_and_submits_the_edit_form_price(self):
        self.quote("edit3d", "7.25")
        self.assertEqual((self.three_d.estimate_cu, self.edit3d.estimate_cu), (1.5, 7.25))
        shown = self.drawn()
        self.assertTrue(shown.enabled)
        self.assertIn("7.25 CU", shown.label)
        self.assertEqual(shown.active_tab, "3D")
        self.assertIn("Retexture", shown.chips)
        self.assertNotIn("Text to 3D", shown.chips)
        self.assertEqual(shown.fields, ["rusty iron plates"])
        text_ticket = self.runtime.state.estimates[self.three_d.estimate_key]
        edit_ticket = self.runtime.state.estimates[self.edit3d.estimate_key]
        self.press("generate")
        self.jobs.settle()
        self.assertTrue(edit_ticket.used)
        self.assertFalse(text_ticket.used)
        self.assertEqual(len(self.jobs.paid), 1)
        self.assertTrue(self.jobs.paid[0].url.path.endswith("/fixture-retexture"))
        self.assertEqual(json.loads(self.jobs.paid[0].content)["prompt"], "rusty iron plates")
        view = self.runtime.state.jobs_view[0]
        self.assertEqual((view.lane, view.cu_cost), ("edit3d", 7.25))
        # The Text form's quote is neither consumed nor repriced by the Edit submission.
        self.assertEqual(self.three_d.estimate_state, "READY")
        self.assertIs(self.runtime.state.estimates[self.three_d.estimate_key], text_ticket)

    def test_enter_in_the_edit_form_submits_its_own_quote(self):
        self.quote("edit3d", "7.25")
        self.drawn()
        self.composer.focused = True
        self.press(key="RET")
        self.jobs.settle()
        self.assertEqual(len(self.jobs.paid), 1)
        self.assertTrue(self.jobs.paid[0].url.path.endswith("/fixture-retexture"))
        self.assertEqual(self.runtime.state.jobs_view[0].cu_cost, 7.25)
        self.assertEqual(self.three_d.prompt, "a teapot")

    def test_text_form_price_never_enables_the_edit_form(self):
        self.assertEqual(self.three_d.estimate_state, "READY")
        self.assertNotEqual(self.edit3d.estimate_state, "READY")
        self.edit3d.prompt = ""
        shown = self.drawn()
        self.assertFalse(shown.enabled)
        self.assertNotIn("1.5 CU", shown.label)
        self.assertEqual(shown.fields, ["Describe the edit to the selected mesh"])
        operator = self.press("generate")
        self.jobs.settle()
        operator.report.assert_not_called()
        self.assertEqual((self.jobs.paid, self.edit3d.last_error), ([], ""))
        self.assertEqual(self.three_d.estimate_state, "READY")

    def test_rejected_submission_keeps_the_composer_responsive(self):
        self.quote("edit3d", "7.25")
        self.drawn()
        for obj in bpy.context.selected_objects:
            obj.select_set(False)
        bpy.context.view_layer.objects.active = None
        operator = self.press("generate")
        self.jobs.settle()
        # The operator's error report is surfaced without ending the composer's modal handler.
        self.assertTrue(self.runtime.state.composer_modal_running)
        operator._finish.assert_not_called()
        operator.report.assert_called_once()
        level, reason = operator.report.call_args.args
        self.assertEqual(level, {"WARNING"})
        self.assertIn("Select the mesh to edit", reason)
        self.assertIn("Select the mesh to edit", self.edit3d.last_error)
        self.assertEqual(self.jobs.paid, [])

    def test_prompt_mirror_and_flush_stay_with_the_edit_form(self):
        props = submodule("blender.props")
        state = self.composer
        self.assertEqual(
            (state.lane_for(self.scene), state.generation_lane(self.scene)), ("3d", "edit3d")
        )
        self.assertEqual(state.generation_lane(self.scene), props.active_lane(self.scene))
        state.sync_from_lane(self.scene)
        self.assertEqual(state.field.text, "rusty iron plates")
        state.focused = True
        state.field.set_text("mossy bronze")
        state.flush_focused_prompt(self.scene)
        self.assertEqual((self.edit3d.prompt, self.three_d.prompt), ("mossy bronze", "a teapot"))
        # Leaving Edit mode while typing changes the form: refuse instead of overwriting either prompt.
        state.focused = True
        state.field.set_text("pending edit")
        self.scene.scenario.three_d_mode = "TEXT"
        self.assertEqual(state.generation_lane(self.scene), props.active_lane(self.scene))
        with self.assertRaisesRegex(RuntimeError, "original prompt"):
            state.flush_focused_prompt(self.scene)
        self.assertEqual((self.edit3d.prompt, self.three_d.prompt), ("mossy bronze", "a teapot"))
        self.assertTrue(state.focused)

    def test_model_chip_picks_for_the_edit_form_and_settings_open_the_tab(self):
        dialogs = MagicMock()
        with (
            patch.object(self.modal, "bpy", SimpleNamespace(ops=SimpleNamespace(scenario=dialogs))),
            patch.object(self.modal, "_open_sidebar"),
        ):
            self.press("model")
            self.press("settings")
        dialogs.pick_model.assert_called_once_with("INVOKE_DEFAULT", lane="edit3d")
        # The 3D settings dialog holds the mode switch and the Edit form with its own Generate.
        dialogs.quick_settings.assert_called_once_with("INVOKE_DEFAULT", lane="3d")
        dialogs.generate.assert_not_called()

    def test_settings_edit_form_enables_generate_for_its_own_quote(self):
        self.quote("edit3d", "7.25")
        with patch.object(self.panels, "draw_generate_row") as row:
            self.panels.draw_generate_lane(MagicMock(), bpy.context, "3d")
        lane_state, lane = row.call_args.args[1:]
        self.assertEqual(lane_state.path_from_id(), self.edit3d.path_from_id())
        self.assertTrue(self.panels.generate_enabled(lane_state, lane))
        self.assertEqual(bpy.ops.scenario.generate(lane=lane), {"FINISHED"})
        self.jobs.settle()
        self.assertEqual(len(self.jobs.paid), 1)
        self.assertEqual(self.runtime.state.jobs_view[0].cu_cost, 7.25)

    def test_focused_prompt_never_writes_into_the_form_that_replaced_it(self):
        for key, text in (("S", "s"), ("BACK_SPACE", ""), ("RET", ""), ("ESC", "")):
            with self.subTest(key=key):
                self.focus_text_form()
                edit_ticket = self.runtime.state.estimates[self.edit3d.estimate_key]
                operator = self.press(key=key, text=text)
                self.jobs.settle()
                self.assert_prompts_unchanged()
                self.assertEqual(self.jobs.paid, [])
                self.assertFalse(edit_ticket.used)
                self.assertEqual(self.edit3d.estimate_state, "READY")
                if key in ("S", "BACK_SPACE"):
                    # Typing is refused and the text stays visible until Esc shows the new form.
                    self.assertTrue(self.composer.focused)
                    self.assertEqual(self.composer.field.text, "a teapot")
                    operator.report.assert_called_once()
                    self.assertIn("Esc", operator.report.call_args.args[1])
                else:
                    self.assertFalse(self.composer.focused)
                    self.assertEqual(self.drawn().fields, ["rusty iron plates"])
        self.assertEqual(self.runtime.state.jobs_view, [])

    def test_generate_click_after_the_form_changed_submits_nothing(self):
        self.focus_text_form()
        operator = self.press("generate")
        self.jobs.settle()
        self.assert_prompts_unchanged()
        self.assertEqual(self.jobs.paid, [])
        operator.report.assert_called_once()
        self.assertEqual(operator.report.call_args.args[0], {"WARNING"})
        self.assertFalse(self.composer.focused)
        shown = self.drawn()
        self.assertEqual(shown.fields, ["rusty iron plates"])
        self.assertTrue(shown.enabled)

    def test_card_keeps_describing_the_focused_form_until_esc(self):
        self.focus_text_form()
        shown = self.drawn()
        self.assertEqual(shown.fields, ["a teapot"])
        self.assertIn("Text to 3D", shown.chips)
        self.assertNotIn("Retexture", shown.chips)
        self.assertNotIn("7.25 CU", shown.label)
        self.assertFalse(shown.enabled)
        self.assertTrue(any("Esc" in s for s in shown.texts))
        self.assertTrue(self.composer.focused)
        self.press(key="ESC")
        shown = self.drawn()
        self.assertEqual(shown.fields, ["rusty iron plates"])
        self.assertIn("Retexture", shown.chips)
        self.assertIn("7.25 CU", shown.label)
        self.assertTrue(shown.enabled)

    def test_settings_and_model_chip_leave_the_prompt_before_their_dialogs(self):
        """The dialogs can switch the 3D mode; the typed text stays in its own form."""

        def switch_to_edit(*args, **kwargs):
            self.switch_mode("EDIT")

        for kind in ("settings", "model"):
            with self.subTest(kind=kind):
                self.composer.focused = False
                self.switch_mode("TEXT")
                self.three_d.prompt, self.edit3d.prompt = "a teapot", "rusty iron plates"
                self.drawn()
                self.composer.focused = True
                self.press(key="S", text="s")
                self.assertEqual(self.three_d.prompt, "a teapots")
                dialogs = MagicMock()
                dialogs.quick_settings.side_effect = switch_to_edit
                dialogs.pick_model.side_effect = switch_to_edit
                with (
                    patch.object(
                        self.modal, "bpy", SimpleNamespace(ops=SimpleNamespace(scenario=dialogs))
                    ),
                    patch.object(self.modal, "_open_sidebar"),
                ):
                    self.press(kind)
                self.assertFalse(self.composer.focused)
                self.assertEqual(self.scene.scenario.three_d_mode, "EDIT")
                # The next key reaches Blender instead of the replaced form.
                self.press(key="S", text="s", expect=("PASS_THROUGH",))
                self.assertEqual(
                    (self.three_d.prompt, self.edit3d.prompt), ("a teapots", "rusty iron plates")
                )
                self.assertEqual(self.drawn().fields, ["rusty iron plates"])

    def test_dialogs_do_not_open_over_a_replaced_focused_form(self):
        self.focus_text_form()
        dialogs = MagicMock()
        for kind in ("settings", "model"):
            with self.subTest(kind=kind):
                with (
                    patch.object(
                        self.modal, "bpy", SimpleNamespace(ops=SimpleNamespace(scenario=dialogs))
                    ),
                    patch.object(self.modal, "_open_sidebar"),
                ):
                    operator = self.press(kind)
                operator.report.assert_called_once()
                self.assertTrue(self.composer.focused)
                self.assert_prompts_unchanged()
        dialogs.quick_settings.assert_not_called()
        dialogs.pick_model.assert_not_called()

    def test_edit_task_without_a_prompt_offers_no_prompt_to_type(self):
        mesh = {"name": "mesh", "type": "file", "kind": "3d", "required": True}
        self.configure(
            "edit3d",
            {
                "id": "fixture-retopology",
                "name": "Retopology",
                "type": "custom",
                "capabilities": ["3d23d"],
                "inputs": [mesh],
            },
            "",
        )
        shown = self.drawn()
        self.assertEqual(shown.fields, ["This model takes no prompt"])
        operator = self.press("prompt")
        self.assertFalse(self.composer.focused)
        operator.report.assert_called_once()
        self.press(key="S", text="s", expect=("PASS_THROUGH",))
        self.assertEqual(self.edit3d.prompt, "")
