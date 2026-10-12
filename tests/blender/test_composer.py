# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
import contextlib
import json
import os
import unittest
from types import SimpleNamespace
from unittest import mock
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


class ComposerFileLoadTests(unittest.TestCase):
    def test_every_file_load_resets_the_composer(self):
        # Blender drops a load_pre handler that is not persistent at the first file load it runs for.
        composer = submodule("blender.composer")
        runtime = submodule("blender.runtime")
        for _load in range(3):
            state = runtime.state.composer
            state.expanded = state.focused = True
            state.field.set_text("left from the previous file")
            runtime.state.composer_modal_running = True
            reset_scene()  # File > New, Open and Revert run the same load handlers
            self.assertIn(composer._load_pre, bpy.app.handlers.load_pre)
            self.assertIs(runtime.state.composer, state)
            self.assertFalse(state.expanded or state.focused)
            self.assertEqual(state.field.text, "")
            self.assertFalse(runtime.state.composer_modal_running)


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


def _region(kind, x, width, y=100, height=900):
    return SimpleNamespace(type=kind, x=x, y=y, width=width, height=height)


class ComposerSideRegionTests(unittest.TestCase):
    """The composer keeps clear of the toolbar and sidebar drawn over the viewport (region overlap)."""

    # narrow enough that a card centred in the whole region would run under the sidebar
    AREA_X, AREA_W, TOOLBAR_W, SIDEBAR_W = 10, 1200, 56, 300

    def setUp(self):
        reset_scene()
        self.draw = submodule("blender.composer.draw")
        self.modal = submodule("blender.composer.modal")
        self.state_mod = submodule("blender.composer.state")
        self.runtime = submodule("blender.runtime")
        self.cl = submodule("core.ui.composer_layout")

    def _context(
        self, sidebar=True, overlap=True, flipped=False, geometry=None, preferences=None, height=900
    ):
        """A 3D view area as Blender lays it out: window-relative region x, the sidebar on the right.

        `geometry` is (area x, area width, toolbar width, sidebar width), `preferences` stands in for
        Blender's (pixel size and UI scale), `height` is the viewport's."""
        x, w, toolbar_w, sidebar_open_w = geometry or (
            self.AREA_X,
            self.AREA_W,
            self.TOOLBAR_W,
            self.SIDEBAR_W,
        )
        sidebar_w = sidebar_open_w if sidebar else 1
        sidebar_x = x if flipped else x + w - sidebar_w
        toolbar_x = x + w - toolbar_w if flipped else x
        if overlap:
            window = _region("WINDOW", x, w, height=height)
        else:
            window = _region("WINDOW", x + toolbar_w, w - toolbar_w - sidebar_w, height=height)
        window.tag_redraw = lambda: None  # the modal's drag handlers redraw the region
        regions = [
            _region("HEADER", x, w, y=1000, height=26),
            _region("TOOLS", toolbar_x, toolbar_w),
            _region("UI", sidebar_x, sidebar_w),
            _region("HUD", x + 60, 1),
            window,
        ]
        space = SimpleNamespace(
            type="VIEW_3D",
            region_3d=object(),
            show_region_ui=sidebar,
            show_region_toolbar=True,
        )
        area = SimpleNamespace(
            type="VIEW_3D", regions=regions, spaces=SimpleNamespace(active=space)
        )
        return SimpleNamespace(
            area=area,
            region=window,
            space_data=space,
            scene=bpy.context.scene,
            preferences=preferences or bpy.context.preferences,
        )

    def _sidebar_x(self, context):
        """The sidebar's left edge in WINDOW-region coordinates."""
        ui = next(r for r in context.area.regions if r.type == "UI")
        return ui.x - context.region.x

    def test_insets_follow_visible_overlapping_side_regions(self):
        ctx = self._context()
        self.assertEqual(
            self.draw.overlap_insets(ctx.area, ctx.region),
            (float(self.TOOLBAR_W), float(self.SIDEBAR_W)),
        )
        hidden = self._context(sidebar=False)
        self.assertEqual(
            self.draw.overlap_insets(hidden.area, hidden.region), (float(self.TOOLBAR_W), 0.0)
        )
        shown_but_closed = self._context()
        shown_but_closed.space_data.show_region_ui = False
        self.assertEqual(
            self.draw.overlap_insets(shown_but_closed.area, shown_but_closed.region)[1], 0.0
        )
        beside = self._context(overlap=False)
        self.assertEqual(self.draw.overlap_insets(beside.area, beside.region), (0.0, 0.0))
        flipped = self._context(flipped=True)
        self.assertEqual(
            self.draw.overlap_insets(flipped.area, flipped.region),
            (float(self.SIDEBAR_W), float(self.TOOLBAR_W)),
        )
        self.assertEqual(self.draw.overlap_insets(None, ctx.region), (0.0, 0.0))

    def test_card_stays_left_of_the_open_sidebar_and_hits_what_it_draws(self):
        ctx = self._context()
        sidebar_x = self._sidebar_x(ctx)
        state = self.state_mod.ComposerState()
        state.expanded = True
        placements = (
            ((0.0, 0.0), None),
            ((5000.0, 0.0), None),
            ((0.0, 0.0), 5000),
            ((-5000.0, 0.0), 900),
        )
        for offset, width in placements:
            with self.subTest(offset=offset, width=width):
                state.offset, state.width = offset, width
                layout = self.modal._layout(ctx, state)
                self.assertEqual(layout, self.draw.composer_layout(ctx, state))
                card = layout.card_rect
                self.assertLessEqual(card.right, sidebar_x)
                self.assertGreaterEqual(card.x, self.TOOLBAR_W)
                for kind, rect in (
                    ("generate", layout.generate_rect),
                    ("collapse", layout.collapse_rect),
                ):
                    self.assertLess(rect.right, sidebar_x)
                    centre = (rect.x + rect.w / 2, rect.y + rect.h / 2)
                    self.assertEqual(layout.hit(*centre), (kind,))
                drawn = self._draw(ctx, state)
                self.assertEqual(state.layout, layout)
                self.assertIn((card.x, card.y, card.w, card.h), drawn)
                gr = layout.generate_rect
                self.assertIn((gr.x, gr.y, gr.w, gr.h), drawn)
                for x, _y, w, _h in drawn:
                    self.assertLessEqual(x + w, sidebar_x)
        state.expanded, state.offset, state.width = False, (5000.0, 0.0), None
        pill = self.modal._layout(ctx, state)
        self.assertLessEqual(pill.pill_rect.right, sidebar_x)
        drawn = self._draw(ctx, state)
        self.assertEqual(state.layout, pill)
        for x, _y, w, _h in drawn:
            self.assertLessEqual(x + w, sidebar_x)

    def test_closing_the_sidebar_restores_the_full_width_placement(self):
        state = self.state_mod.ComposerState()
        state.expanded = True
        cl = submodule("core.ui.composer_layout")
        closed = self.modal._layout(self._context(sidebar=False), state)
        plain = cl.pill_placement(
            self.AREA_W, 900, True, closed.scale, insets=(float(self.TOOLBAR_W), 0.0)
        )
        self.assertEqual(closed.card_rect, plain.card_rect)
        opened = self.modal._layout(self._context(), state)
        self.assertLess(
            opened.card_rect.x + opened.card_rect.w / 2, closed.card_rect.x + closed.card_rect.w / 2
        )

    def test_real_view3d_regions_feed_the_insets(self):
        window = next(iter(bpy.context.window_manager.windows), None)
        area = (
            next((a for a in window.screen.areas if a.type == "VIEW_3D"), None)
            if window is not None
            else None
        )
        if area is None:
            self.skipTest("no window with a 3D viewport in background mode")
        region = next(r for r in area.regions if r.type == "WINDOW")
        # real RNA regions and space flags on every supported Blender version
        left, right = self.draw.overlap_insets(area, region)
        self.assertIsInstance(left, float)
        self.assertIsInstance(right, float)
        self.assertGreaterEqual(min(left, right), 0.0)
        state = self.state_mod.ComposerState()
        state.expanded = True
        with bpy.context.temp_override(window=window, area=area, region=region):
            layout = self.modal._layout(bpy.context, state)
            self.assertEqual(layout, self.draw.composer_layout(bpy.context, state))
        if left + right >= region.width:
            self.assertEqual(layout.insets, (0.0, 0.0))
            return
        self.assertEqual(layout.insets, (left, right))
        # the card, or the pill standing in for it when the uncovered span cannot hold the card
        self.assertEqual(layout.expanded, layout.card_fits)
        box = layout.pill_rect
        if region.width - left - right >= box.w:
            self.assertGreaterEqual(box.x, left)
            self.assertLessEqual(box.right, region.width - right)

    def test_a_move_starts_from_the_clamped_placement_without_a_dead_zone(self):
        ctx = self._context()
        sidebar_x = self._sidebar_x(ctx)
        # parked against the right edge, or below the bottom edge too, while the sidebar was closed
        for expanded in (True, False):
            for saved in ((5000.0, 200.0), (5000.0, -5000.0)):
                with self.subTest(expanded=expanded, saved=saved):
                    state = self.state_mod.ComposerState()
                    state.expanded, state.offset = expanded, saved
                    state.width = 500 if expanded else None  # room to move inside the span
                    shown = self.modal._layout(ctx, state)
                    box = shown.pill_rect
                    self.assertAlmostEqual(box.right, sidebar_x)
                    press, kind = self._grab_point(shown)
                    moves = ((-60, 50), (-140, 90))
                    layouts, save = self._drag(ctx, state, press, kind, moves)
                    # the first move past the threshold already moves the composer by the pointer delta
                    for (dx, dy), layout in zip(moves, layouts, strict=True):
                        self.assertAlmostEqual(layout.pill_rect.x, box.x + dx)
                        self.assertAlmostEqual(layout.pill_rect.y, box.y + dy)
                    # the release stores the placement as drawn, not the saved value past the edge
                    last = layouts[-1]
                    self.assertEqual(state.offset, last.offset())
                    self.assertEqual(state.width, 500 if expanded else None)
                    self._assert_same_rect(self.modal._layout(ctx, state).pill_rect, last.pill_rect)
                    save.assert_called_once_with()
                    # Escape still puts back the offset the press started from
                    state.offset = saved
                    press, kind = self._grab_point(self.modal._layout(ctx, state))
                    state.begin_drag(press, kind)
                    self._move(ctx, state, press, -60, 50)
                    self.assertNotEqual(state.offset, saved)
                    state.cancel_drag()
                    self.assertEqual(state.offset, saved)

    def test_a_resize_starts_from_the_clamped_width_and_stores_what_it_draws(self):
        ctx = self._context()
        sidebar_x = self._sidebar_x(ctx)
        state = self.state_mod.ComposerState()
        # a wide card saved while the sidebar was closed, parked against the sidebar edge
        state.expanded, state.offset, state.width = True, (5000.0, 200.0), 5000
        shown = self.modal._layout(ctx, state)
        card = shown.card_rect
        self.assertAlmostEqual(card.right, sidebar_x)
        self.assertLess(card.w, 5000)
        grip = shown.resize_rect
        press = (grip.x + grip.w / 2, grip.y + grip.h / 2)
        self.assertEqual(shown.hit(*press), ("resize",))
        moves = ((-30, 0), (-120, 5))
        layouts, save = self._drag(ctx, state, press, "resize", moves)
        for (dx, _dy), layout in zip(moves, layouts, strict=True):
            self.assertAlmostEqual(layout.card_rect.w, card.w + dx)
            self.assertLessEqual(layout.card_rect.right, sidebar_x)
            self.assertEqual(layout.hit(*self._centre(layout.generate_rect)), ("generate",))
        last = layouts[-1]
        self.assertEqual(state.width, last.card_rect.w)
        self.assertEqual(state.offset, last.offset())
        self._assert_same_rect(self.modal._layout(ctx, state).card_rect, last.card_rect)
        save.assert_called_once_with()

    def test_closing_and_reopening_the_sidebar_keeps_the_composer_reachable(self):
        opened, closed = self._context(), self._context(sidebar=False)
        sidebar_x = self._sidebar_x(opened)
        state = self.state_mod.ComposerState()
        state.expanded, state.width = True, 500
        # sidebar closed: drag the card to the bare right edge, where the whole card stops
        press, kind = self._grab_point(self.modal._layout(closed, state))
        self._drag(closed, state, press, kind, ((5000, 0),))
        parked = self.modal._layout(closed, state)
        self.assertAlmostEqual(parked.card_rect.right, closed.region.width)
        self._assert_reachable(parked, closed, closed.region.width)
        # N opens the sidebar: the card stops at its edge, Generate and minus clickable
        shown = self.modal._layout(opened, state)
        self.assertAlmostEqual(shown.card_rect.right, sidebar_x)
        self._assert_reachable(shown, opened, sidebar_x)
        # a drag from there follows the pointer at once and is stored as drawn
        press, kind = self._grab_point(shown)
        layouts, _save = self._drag(opened, state, press, kind, ((-80, 0),))
        self.assertAlmostEqual(layouts[-1].card_rect.x, shown.card_rect.x - 80)
        # closing and reopening the sidebar keeps that placement reachable both ways
        self._assert_reachable(self.modal._layout(closed, state), closed, closed.region.width)
        reopened = self.modal._layout(opened, state)
        self._assert_same_rect(reopened.card_rect, layouts[-1].card_rect)
        self._assert_reachable(reopened, opened, sidebar_x)

    # -- large UI scale ----------------------------------------------------------
    # The physical desktop case: Retina with a Preferences resolution scale of 2 (custom-UI scale 4),
    # a 226 px toolbar and a 1122 px sidebar at x=1355 over a 2477 px viewport. About 1129 px stay
    # uncovered, less than the 1680 px minimum card.
    RETINA = (0, 2477, 226, 1122)

    @staticmethod
    def _preferences(scale):
        """Preferences whose custom-UI scale is `scale`, as Blender derives it from DPI and resolution scale."""
        return SimpleNamespace(system=SimpleNamespace(ui_scale=scale))

    def _retina(self, sidebar=True, geometry=None, flipped=False):
        return self._context(
            sidebar=sidebar,
            flipped=flipped,
            geometry=geometry or self.RETINA,
            preferences=self._preferences(4.0),
        )

    def test_composer_scale_is_blenders_custom_ui_scale_not_pixel_size_times_resolution(self):
        # Blender 5.2.1 on Retina at a resolution scale of 2 reports DPI 288: a custom-UI scale of 4 and a pixel
        # size (line width) of 4. Multiplying the pixel size by the resolution scale would draw at 8.
        prefs = SimpleNamespace(
            system=SimpleNamespace(ui_scale=4.0, pixel_size=4.0), view=SimpleNamespace(ui_scale=2.0)
        )
        self.assertEqual(self.draw.ui_scale(SimpleNamespace(preferences=prefs)), 4.0)
        self.assertEqual(
            self.draw.ui_scale(bpy.context),
            bpy.context.preferences.system.ui_scale or 1.0,
        )
        # Background Blender reports a custom-UI scale of 0; sizes never collapse to zero.
        zero = SimpleNamespace(preferences=self._preferences(0.0))
        self.assertEqual(self.draw.ui_scale(zero), 1.0)

    def test_large_scale_beside_the_sidebar_draws_and_hits_the_pill_instead_of_the_card(self):
        ctx = self._retina()
        self.assertEqual(self.draw.ui_scale(ctx), 4.0)
        self.assertEqual(self.draw.overlap_insets(ctx.area, ctx.region), (226.0, 1122.0))
        sidebar_x = self._sidebar_x(ctx)
        self.assertEqual(sidebar_x, 1355)
        state = self.state_mod.ComposerState()
        state.expanded, state.width = True, 1680  # the card at its minimum width, as saved
        layout = self.modal._layout(ctx, state)
        self.assertEqual(layout, self.draw.composer_layout(ctx, state))
        self.assertFalse(layout.expanded)
        self.assertFalse(layout.card_fits)
        self.assertIsNone(layout.card_rect)
        pill = layout.pill_rect
        self.assertGreaterEqual(pill.x, 226)
        self.assertLessEqual(pill.right, sidebar_x)
        self.assertEqual(layout.hit(*self._centre(pill)), ("form",))
        self.assertIsNone(layout.hit(sidebar_x + 10, pill.y + 1))
        texts = []
        drawn = self._draw(ctx, state, texts)
        self.assertEqual(state.layout, layout)
        self.assertIn((pill.x, pill.y, pill.w, pill.h), drawn)
        for x, _y, w, _h in drawn:
            # the pill and what it holds, nothing card-sized, nothing under the sidebar
            self.assertGreaterEqual(x, pill.x)
            self.assertLessEqual(x + w, pill.right)
        self.assertNotIn("Render Image", texts)
        # drawing changed nothing the user chose
        self.assertEqual((state.expanded, state.width, state.offset), (True, 1680, (0.0, 0.0)))

    def test_a_click_on_the_pill_without_room_opens_the_lane_form_instead_of_toggling(self):
        ctx = self._retina()
        ctx.scene.scenario.lane = "material"
        for expanded in (True, False):
            with self.subTest(expanded=expanded):
                state = self.state_mod.ComposerState()
                state.expanded, state.width = expanded, 1680
                press = self._centre(self.modal._layout(ctx, state).pill_rect)
                with (
                    mock.patch.object(self.runtime.state, "composer", state),
                    mock.patch.object(self.runtime, "set_message") as message,
                    mock.patch.object(self.modal, "_open_settings") as open_settings,
                    mock.patch.object(self.modal, "_save_layout") as save,
                ):
                    operator = self._operator()
                    self._click(operator, ctx, press)
                open_settings.assert_called_once_with(ctx, "material")
                message.assert_called_once_with(self.modal.NO_ROOM_MESSAGE)
                operator.report.assert_called_once_with({"INFO"}, self.modal.NO_ROOM_MESSAGE)
                save.assert_not_called()
                # neither the expanded choice nor the saved card width changed
                self.assertEqual((state.expanded, state.width), (expanded, 1680))
                self.assertEqual(state.offset, (0.0, 0.0))
                self.assertIsNone(state.drag_mode)

    def test_closing_the_sidebar_brings_the_card_back_with_readable_tab_labels(self):
        opened, closed = self._retina(), self._retina(sidebar=False)
        state = self.state_mod.ComposerState()
        state.expanded, state.width = True, 1680
        self.assertFalse(self.modal._layout(opened, state).expanded)
        layout = self.modal._layout(closed, state)
        self.assertTrue(layout.expanded and layout.card_fits)
        self.assertEqual(layout.card_rect.w, 1680)
        self._assert_reachable(layout, closed, closed.region.width)
        texts = []
        drawn = self._draw(closed, state, texts)
        card = layout.card_rect
        self.assertIn((card.x, card.y, card.w, card.h), drawn)
        # glyphs 0.65 em wide at 48 px: the long labels give way to their short ones, none is clipped
        shown = [label for label in texts if label in self._lane_labels()]
        self.assertEqual(shown, ["Image", "Video", "3D", "Mat", "R-Img", "R-Vid"])
        # the sidebar opens again: the pill once more, with the stored choice untouched
        self.assertFalse(self.modal._layout(opened, state).expanded)
        self.assertEqual((state.expanded, state.width), (True, 1680))

    def test_dragging_the_pill_without_room_moves_it_and_keeps_the_card_width(self):
        ctx = self._retina()
        sidebar_x = self._sidebar_x(ctx)
        state = self.state_mod.ComposerState()
        state.expanded, state.width = True, 1680
        shown = self.modal._layout(ctx, state)
        press, kind = self._grab_point(shown)
        self.assertEqual(kind, "form")
        moves = ((-60, 50), (5000, 90))
        with mock.patch.object(self.modal, "_open_settings") as open_settings:
            layouts, save = self._drag(ctx, state, press, kind, moves)
        open_settings.assert_not_called()  # a drag is not a click
        self.assertAlmostEqual(layouts[0].pill_rect.x, shown.pill_rect.x - 60)
        self.assertAlmostEqual(layouts[-1].pill_rect.right, sidebar_x)  # stops at the sidebar
        self.assertEqual(state.offset, layouts[-1].offset())
        save.assert_called_once_with()
        self.assertEqual((state.expanded, state.width), (True, 1680))

    def test_a_focused_prompt_is_left_when_the_card_gives_way_to_the_pill(self):
        scene = bpy.context.scene
        scene.scenario.lane = "image"
        scene.scenario.lane_state("image").prompt = "copper"
        state = self.state_mod.ComposerState()
        state.expanded = True
        state.sync_from_lane(scene)
        state.focused = True
        state.field.insert(" kettle")
        ctx = self._retina()  # the sidebar opened while the prompt had focus
        layout = self.modal._layout(ctx, state)
        self.assertFalse(layout.expanded)
        x, y = self._centre(layout.pill_rect)
        event = SimpleNamespace(
            type="MOUSEMOVE", value="NOTHING", mouse_region_x=x, mouse_region_y=y
        )
        with mock.patch.object(self.runtime.state, "composer", state):
            result = self.modal.SCENARIO_OT_composer_modal.modal(self._operator(), ctx, event)
        self.assertEqual(result, {"PASS_THROUGH"})
        self.assertFalse(state.focused)
        self.assertEqual(scene.scenario.lane_state("image").prompt, "copper kettle")
        self.assertTrue(state.expanded)

    def test_a_prompt_changed_elsewhere_is_kept_when_the_card_gives_way(self):
        scene = bpy.context.scene
        scene.scenario.lane = "image"
        scene.scenario.lane_state("image").prompt = "copper"
        state = self.state_mod.ComposerState()
        state.expanded = True
        state.sync_from_lane(scene)
        state.focused = True
        state.field.insert(" kettle")
        scene.scenario.lane_state("image").prompt = "edited in the sidebar"
        ctx = self._retina()
        x, y = self._centre(self.modal._layout(ctx, state).pill_rect)
        event = SimpleNamespace(
            type="MOUSEMOVE", value="NOTHING", mouse_region_x=x, mouse_region_y=y
        )
        operator = self._operator()
        with mock.patch.object(self.runtime.state, "composer", state):
            result = self.modal.SCENARIO_OT_composer_modal.modal(operator, ctx, event)
        self.assertEqual(result, {"PASS_THROUGH"})
        self.assertFalse(state.focused)
        self.assertEqual(scene.scenario.lane_state("image").prompt, "edited in the sidebar")
        operator.report.assert_called_once()
        self.assertEqual(operator.report.call_args.args[0], {"WARNING"})

    # -- short viewport ----------------------------------------------------------
    def test_a_short_viewport_shows_the_pill_instead_of_overlapping_card_rows(self):
        bpy.context.scene.scenario.lane = "video"
        for scale in (1.0, 2.0, 4.0):
            need = (self.cl.CARD_HEIGHT + 2 * self.cl.MARGIN) * scale
            geometry = (0, int(1800 * scale), int(56 * scale), int(300 * scale))
            prefs = self._preferences(scale)
            with self.subTest(scale=scale):
                state = self.state_mod.ComposerState()
                state.expanded, state.width = True, self.cl.MIN_CARD_WIDTH * scale
                tall = self._context(
                    sidebar=False, geometry=geometry, preferences=prefs, height=need
                )
                layout = self.modal._layout(tall, state)
                self.assertTrue(layout.expanded and layout.card_fits)
                card = layout.card_rect
                self.assertEqual(card.h, self.cl.CARD_HEIGHT * scale)
                self.assertGreaterEqual(card.y, 0)
                self.assertLessEqual(card.top, need)
                # the rows stack inside the card without overlapping
                self.assertGreaterEqual(layout.tab_rects["image"].y, layout.prompt_rect.top)
                self.assertGreaterEqual(layout.prompt_rect.y, layout.model_rect.top)
                self.assertGreaterEqual(layout.model_rect.y, card.y)
                self.assertIn((card.x, card.y, card.w, card.h), self._draw(tall, state))
                # one pixel shorter: the pill, drawn and hit as the pill
                short = self._context(
                    sidebar=False, geometry=geometry, preferences=prefs, height=need - 1
                )
                layout = self.modal._layout(short, state)
                self.assertEqual(layout, self.draw.composer_layout(short, state))
                self.assertFalse(layout.expanded or layout.card_fits)
                self.assertIsNone(layout.card_rect)
                pill = layout.pill_rect
                self.assertEqual(layout.hit(*self._centre(pill)), ("form",))
                drawn = self._draw(short, state)
                self.assertIn((pill.x, pill.y, pill.w, pill.h), drawn)
                for x, y, w, h in drawn:
                    self.assertGreaterEqual(x, pill.x)
                    self.assertLessEqual(x + w, pill.right)
                    self.assertLessEqual(y + h, pill.top)
                # a click on it opens the lane's form, and the stored choice stays
                with (
                    mock.patch.object(self.runtime.state, "composer", state),
                    mock.patch.object(self.runtime, "set_message") as message,
                    mock.patch.object(self.modal, "_open_settings") as open_settings,
                ):
                    operator = self._operator()
                    self._click(operator, short, self._centre(pill))
                open_settings.assert_called_once_with(short, "video")
                message.assert_called_once_with(self.modal.NO_ROOM_MESSAGE)
                operator.report.assert_called_once_with({"INFO"}, self.modal.NO_ROOM_MESSAGE)
                self.assertEqual(
                    (state.expanded, state.width), (True, self.cl.MIN_CARD_WIDTH * scale)
                )

    # -- model chip --------------------------------------------------------------
    def _press_model_chip(self, context, state):
        """A press on the model chip through the modal: returns the sidebar and picker mocks."""
        layout = self.modal._layout(context, state)
        self.assertTrue(layout.expanded)
        x, y = self._centre(layout.model_rect)
        self.assertEqual(layout.hit(x, y), ("model",))
        event = SimpleNamespace(
            type="LEFTMOUSE",
            value="PRESS",
            mouse_region_x=x,
            mouse_region_y=y,
            shift=False,
            ctrl=False,
            oskey=False,
            alt=False,
            unicode="",
        )
        pick = mock.Mock()
        ops = SimpleNamespace(scenario=SimpleNamespace(pick_model=pick))
        # each call is a separate click: milliseconds apart on one state they would pair
        state.presses.reset()
        with (
            mock.patch.object(self.runtime.state, "composer", state),
            mock.patch.object(self.modal, "bpy", SimpleNamespace(ops=ops)),
            mock.patch.object(self.modal, "_open_sidebar") as open_sidebar,
        ):
            result = self.modal.SCENARIO_OT_composer_modal.modal(self._operator(), context, event)
        self.assertEqual(result, {"RUNNING_MODAL"})
        pick.assert_called_once_with("INVOKE_DEFAULT", lane=state.lane_for(context.scene))
        return open_sidebar

    def test_the_model_chip_opens_the_sidebar_only_while_the_card_keeps_its_room(self):
        bpy.context.scene.scenario.lane = "image"
        state = self.state_mod.ComposerState()
        state.expanded = True
        # 1x: a hidden sidebar opens beside the picker, and the card still fits beside it
        closed = self._context(sidebar=False, preferences=self._preferences(1.0))
        self.assertTrue(self.draw.card_fits_with_sidebar(closed))
        self._press_model_chip(closed, state).assert_called_once_with(closed)
        opened = self._context(preferences=self._preferences(1.0))
        self.assertTrue(self.modal._layout(opened, state).expanded)
        # composer scale 4: the card fits with the sidebar hidden, not beside its default 880 px
        closed = self._retina(sidebar=False)
        self.assertTrue(self.modal._layout(closed, state).expanded)
        self.assertFalse(self.draw.card_fits_with_sidebar(closed))
        self._press_model_chip(closed, state).assert_not_called()
        default_width = self.draw.SIDEBAR_WIDTH * 4
        opened = self._retina(geometry=(0, 2477, 226, default_width))
        self.assertFalse(self.modal._layout(opened, state).expanded)  # what opening would cause
        flipped = self._retina(sidebar=False, flipped=True)
        self.assertFalse(self.draw.card_fits_with_sidebar(flipped))
        # a viewport wide enough for the card beside the open sidebar: showing it again changes nothing
        wide = self._retina(geometry=(0, 4000, 226, 1122))
        self.assertTrue(self.draw.card_fits_with_sidebar(wide))
        self._press_model_chip(wide, state).assert_called_once_with(wide)
        # a closed sidebar that still reports its width is predicted at that width, not the default
        widened = self._retina(geometry=(0, 3000, 226, 1122))
        widened.space_data.show_region_ui = False
        self.assertTrue(self.modal._layout(widened, state).expanded)
        need = (self.cl.MIN_CARD_WIDTH + 2 * self.cl.MARGIN) * 4
        self.assertGreaterEqual(3000 - 226 - default_width, need)  # the default estimate would fit
        self.assertFalse(self.draw.card_fits_with_sidebar(widened))
        self._press_model_chip(widened, state).assert_not_called()
        # a short viewport never gets this far: the pill stands in and the chip is not drawn
        short = self._context(sidebar=False, preferences=self._preferences(1.0), height=100)
        self.assertFalse(self.draw.card_fits_with_sidebar(short))

    # -- bare viewport edges -----------------------------------------------------
    def test_a_pill_dragged_to_the_edge_expands_with_minus_and_generate_in_the_viewport(self):
        # the physical case: the pill moved right shares its offset with the wider card, which ran
        # past the bare right edge with its minus button and Generate until dragged back
        ctx = self._context(sidebar=False)
        state = self.state_mod.ComposerState()
        pill = self.modal._layout(ctx, state)
        press, kind = self._grab_point(pill)
        self.assertEqual(kind, "expand")
        with mock.patch.object(self.runtime.state, "composer", state):
            operator = self._operator()
            self._event(operator, ctx, "LEFTMOUSE", "PRESS", press)
            for dx, dy in ((40, 10), (5000, 120)):
                point = (press[0] + dx, press[1] + dy)
                self._event(operator, ctx, "MOUSEMOVE", "NOTHING", point)
            with mock.patch.object(self.modal, "_save_layout") as save:
                self._event(operator, ctx, "LEFTMOUSE", "RELEASE", point)
            save.assert_called_once_with()
            moved = self.modal._layout(ctx, state)
            self.assertFalse(state.expanded)
            self.assertAlmostEqual(moved.pill_rect.right, ctx.region.width)
            # a click on the moved pill expands the card, whole and inside the viewport
            self._click(operator, ctx, self._centre(moved.pill_rect))
        self.assertTrue(state.expanded)
        card = self.modal._layout(ctx, state)
        self.assertAlmostEqual(card.card_rect.right, ctx.region.width)
        self._assert_reachable(card, ctx, ctx.region.width)
        self.assertEqual(card, self.draw.composer_layout(ctx, state))

    def test_a_saved_offset_keeps_minus_and_generate_in_the_viewport_once_the_sidebar_closes(self):
        # an offset saved in a larger window: the card parked at the open sidebar widens when it
        # closes, and the bare edge used to let its minus button and Generate run past it
        opened = self._context(geometry=(self.AREA_X, 900, self.TOOLBAR_W, self.SIDEBAR_W))
        closed = self._context(
            sidebar=False, geometry=(self.AREA_X, 900, self.TOOLBAR_W, self.SIDEBAR_W)
        )
        state = self.state_mod.ComposerState()
        state.expanded, state.offset = True, (81.5, 0.0)
        shown = self.modal._layout(opened, state)
        self.assertAlmostEqual(shown.card_rect.right, self._sidebar_x(opened))
        self._assert_reachable(shown, opened, self._sidebar_x(opened))
        wide = self.modal._layout(closed, state)
        self.assertGreater(wide.card_rect.w, shown.card_rect.w)
        self.assertAlmostEqual(wide.card_rect.right, closed.region.width)
        self._assert_reachable(wide, closed, closed.region.width)
        drawn = self._draw(closed, state)
        for x, y, w, h in drawn:
            self.assertGreaterEqual(min(x, y), 0)
            self.assertLessEqual(x + w, closed.region.width)
            self.assertLessEqual(y + h, closed.region.height)
        self.assertEqual(state.offset, (81.5, 0.0))  # drawing and layout keep the saved offset

    # -- double-click ----------------------------------------------------------
    # Blender converts a double-click into a plain press before calling a modal operator
    # (wm_event_modalkeymap_begin in Blender 5.0 to 5.2): only key maps see DOUBLE_CLICK. These
    # tests send what the modal really receives, two PRESS/RELEASE pairs, at pinned times.

    def _double_click_seconds(self):
        return bpy.context.preferences.inputs.mouse_double_click_time / 1000.0

    def _clicks(self, operator, context, point, times):
        """A press and a release at `point` for each time in `times`, as Blender hands them to the modal."""
        results = []
        for when in times:
            with mock.patch.object(self.modal, "_now", return_value=when):
                results.append(self._event(operator, context, "LEFTMOUSE", "PRESS", point))
                results.append(self._event(operator, context, "LEFTMOUSE", "RELEASE", point))
        return results

    def _word_point(self, context, state, word_end=5):
        """A point over the second character of the prompt's first word, and the caret index there."""
        layout = self.modal._layout(context, state)
        pr = layout.prompt_rect
        try:
            font_px, _start, _end, x0 = self.draw.prompt_metrics(pr, state.field, layout.scale)
        except Exception as err:  # blf without a font in some background builds
            self.skipTest(f"blf unavailable: {err}")
        import blf

        blf.size(self.draw.FONT, font_px)
        x = x0 + blf.dimensions(self.draw.FONT, "h")[0] + 1
        point = (x, pr.y + pr.h / 2)
        self.assertEqual(layout.hit(*point), ("prompt",))
        index = self.modal._caret_index(context, state, layout, x)
        self.assertTrue(0 < index < word_end, index)
        return point, index

    def _type(self, operator, context, text):
        for char in text:
            self._event(operator, context, char.upper(), "PRESS", (0, 0), unicode=char)

    def test_the_blender_double_click_time_preference_exists(self):
        self.assertGreater(bpy.context.preferences.inputs.mouse_double_click_time, 0)
        self.assertEqual(
            self.modal._double_click_seconds(bpy.context), self._double_click_seconds()
        )
        # a context without preferences (a stub) falls back to Blender's default
        self.assertEqual(
            self.modal._double_click_seconds(SimpleNamespace()), self.cl.DOUBLE_CLICK_MS / 1000.0
        )

    def test_a_double_click_in_the_prompt_selects_the_word_typing_replaces(self):
        scene = bpy.context.scene
        scene.scenario.lane = "image"
        ctx = self._context(sidebar=False)
        quick = self._double_click_seconds() / 2
        for times, expected in (((10.0, 10.0 + quick), "X world"), ((10.0, 12.0), None)):
            with self.subTest(times=times):
                scene.scenario.lane_state("image").prompt = "hello world"
                state = self.state_mod.ComposerState()
                state.expanded = True
                state.sync_from_lane(scene)
                point, index = self._word_point(ctx, state)
                with mock.patch.object(self.runtime.state, "composer", state):
                    operator = self._operator()
                    results = self._clicks(operator, ctx, point, times)
                    self.assertEqual(results, [{"RUNNING_MODAL"}] * 4)
                    self.assertTrue(state.focused)
                    if expected:
                        self.assertEqual(state.field.selected_text(), "hello")
                    else:  # too slow: two caret presses, no selection
                        self.assertIsNone(state.field.selection)
                        self.assertEqual(state.field.caret, index)
                    self._type(operator, ctx, "X")
                text = scene.scenario.lane_state("image").prompt
                self.assertEqual(
                    text, expected or "hello world"[:index] + "X" + "hello world"[index:]
                )

    def test_a_double_click_on_the_card_background_resets_the_placement(self):
        ctx = self._context(sidebar=False)
        quick = self._double_click_seconds() / 2
        threshold = self.cl.DRAG_THRESHOLD
        cases = (
            ((10.0, 10.0 + quick), (0, 0), True),
            ((10.0, 10.0 + quick), (threshold, -threshold), True),  # a slight drift still pairs
            ((10.0, 10.0 + 2 * quick + 0.01), (0, 0), False),  # past Blender's double-click time
            ((10.0, 10.0 + quick), (threshold + 1, 0), False),  # moved beyond the threshold
        )
        for times, drift, resets in cases:
            with self.subTest(times=times, drift=drift):
                state = self.state_mod.ComposerState()
                state.expanded, state.offset, state.width = True, (-120.0, 80.0), 600
                press, kind = self._grab_point(self.modal._layout(ctx, state))
                self.assertEqual(kind, "drag")
                second = (press[0] + drift[0], press[1] + drift[1])
                with (
                    mock.patch.object(self.runtime.state, "composer", state),
                    mock.patch.object(self.modal, "_save_layout") as save,
                ):
                    operator = self._operator()
                    self._clicks(operator, ctx, press, times[:1])
                    self.assertEqual(self.modal._layout(ctx, state).hit(*second), ("drag",))
                    self._clicks(operator, ctx, second, times[1:])
                if resets:
                    self.assertEqual((state.offset, state.width), ((0.0, 0.0), None))
                    save.assert_called_once_with()
                else:
                    self.assertEqual((state.offset, state.width), ((-120.0, 80.0), 600))
                    save.assert_not_called()
                self.assertIsNone(state.drag_mode)

    def test_a_double_click_on_the_resize_corner_survives_jitter_within_the_drag_threshold(self):
        # The grip follows the pointer from the first move, with no pending state, so the mouse moves a
        # real click reports while the button is held must not forget the press unless they leave the
        # drag threshold, as the card background's pending drag already allows.
        ctx = self._context(sidebar=False)
        quick = self._double_click_seconds() / 2
        saved = (-120.0, 80.0)
        threshold = (
            self.cl.DRAG_THRESHOLD * self.modal._layout(ctx, self.state_mod.ComposerState()).scale
        )
        jitter = threshold - 1
        cases = (
            ((), True),
            (((1, 0), (jitter, -jitter), (0, 1)), True),  # jitter while the first press is held
            (((threshold, 0), (0, 0)), False),  # a resize, even one brought back, is no click
        )
        for moves, resets in cases:
            with self.subTest(moves=moves):
                state = self.state_mod.ComposerState()
                state.expanded, state.offset, state.width = True, saved, 600
                press = self._centre(self.modal._layout(ctx, state).resize_rect)
                with (
                    mock.patch.object(self.runtime.state, "composer", state),
                    mock.patch.object(self.modal, "_save_layout") as save,
                ):
                    operator = self._operator()
                    with mock.patch.object(self.modal, "_now", return_value=10.0):
                        self._event(operator, ctx, "LEFTMOUSE", "PRESS", press)
                        self.assertEqual(state.drag_mode, "resize")
                        point = press
                        for dx, dy in moves:
                            point = (press[0] + dx, press[1] + dy)
                            self._event(operator, ctx, "MOUSEMOVE", "NOTHING", point)
                        self._event(operator, ctx, "LEFTMOUSE", "RELEASE", point)
                    self.assertEqual(self.modal._layout(ctx, state).hit(*press), ("resize",))
                    self._clicks(operator, ctx, press, (10.0 + quick,))
                if resets:
                    self.assertEqual((state.offset, state.width), ((0.0, 0.0), None))
                    save.assert_called_with()  # the reset is stored after any jitter's resize
                else:
                    self.assertEqual(state.offset, saved)
                    self.assertAlmostEqual(state.width, 600)  # stored as drawn by the resize
                    save.assert_called_once_with()  # by the resize release only
                self.assertIsNone(state.drag_mode)

    def test_escape_ends_the_press_so_the_next_click_never_pairs_with_it(self):
        # Escape cancels a press held on the card background, its corner or the pill. A later click on
        # the same spot within Blender's double-click time is a new first click: it neither resets the
        # placement nor gets swallowed as the second half of a double-click.
        ctx = self._context(sidebar=False)
        quick = self._double_click_seconds() / 2
        saved = (-120.0, 80.0)
        for target in ("drag", "resize", "expand"):
            with self.subTest(target=target):
                state = self.state_mod.ComposerState()
                state.expanded, state.offset, state.width = target != "expand", saved, 600
                layout = self.modal._layout(ctx, state)
                if target == "resize":
                    point = self._centre(layout.resize_rect)
                else:
                    point = self._grab_point(layout)[0]
                self.assertEqual(layout.hit(*point), (target,))
                with (
                    mock.patch.object(self.runtime.state, "composer", state),
                    mock.patch.object(self.modal, "_save_layout") as save,
                ):
                    operator = self._operator()
                    with mock.patch.object(self.modal, "_now", return_value=10.0):
                        self._event(operator, ctx, "LEFTMOUSE", "PRESS", point)
                        self._event(operator, ctx, "ESC", "PRESS", point)
                        self.assertIsNone(state.drag_mode)
                        self._event(operator, ctx, "LEFTMOUSE", "RELEASE", point)
                    self._clicks(operator, ctx, point, (10.0 + quick,))
                self.assertEqual((state.offset, state.width), (saved, 600))
                self.assertTrue(state.expanded)  # a click on the pill still expands it
                save.assert_not_called()

    def test_only_two_presses_on_one_target_with_nothing_between_make_a_double_click(self):
        ctx = self._context(sidebar=False)
        quick = self._double_click_seconds() / 4
        saved = (-120.0, 80.0)

        def card_state():
            state = self.state_mod.ComposerState()
            state.expanded, state.offset, state.width = True, saved, 600
            return state

        # a key pressed between the two clicks
        state = card_state()
        press, _kind = self._grab_point(self.modal._layout(ctx, state))
        with (
            mock.patch.object(self.runtime.state, "composer", state),
            mock.patch.object(self.modal, "_save_layout") as save,
        ):
            operator = self._operator()
            self._clicks(operator, ctx, press, (10.0,))
            self.assertEqual(
                self._event(operator, ctx, "G", "PRESS", press, unicode="g"), {"PASS_THROUGH"}
            )
            self._clicks(operator, ctx, press, (10.0 + quick,))
        self.assertEqual(state.offset, saved)
        save.assert_not_called()
        # a drag between the presses that brings the card back where it was
        state = card_state()
        with (
            mock.patch.object(self.runtime.state, "composer", state),
            mock.patch.object(self.modal, "_save_layout") as save,
        ):
            operator = self._operator()
            with mock.patch.object(self.modal, "_now", return_value=10.0):
                self._event(operator, ctx, "LEFTMOUSE", "PRESS", press)
                self._event(operator, ctx, "MOUSEMOVE", "NOTHING", (press[0] + 30, press[1]))
                self._event(operator, ctx, "MOUSEMOVE", "NOTHING", press)
                self._event(operator, ctx, "LEFTMOUSE", "RELEASE", press)
            self._clicks(operator, ctx, press, (10.0 + quick,))
        self.assertEqual(state.offset, saved)  # stored as drawn by the drag, not reset
        save.assert_called_once_with()  # by the drag release only
        # the pill expanding under the pointer: its click and the next press hit different targets
        state = self.state_mod.ComposerState()
        state.offset = saved
        pill = self._centre(self.modal._layout(ctx, state).pill_rect)
        with (
            mock.patch.object(self.runtime.state, "composer", state),
            mock.patch.object(self.modal, "_save_layout") as save,
        ):
            operator = self._operator()
            self._clicks(operator, ctx, pill, (10.0, 10.0 + quick))
        self.assertTrue(state.expanded)
        self.assertEqual(state.offset, saved)
        save.assert_not_called()
        # a completed pair is spent: a third quick press is a plain press again
        state = card_state()
        with (
            mock.patch.object(self.runtime.state, "composer", state),
            mock.patch.object(self.modal, "_save_layout") as save,
        ):
            operator = self._operator()
            self._clicks(operator, ctx, press, (10.0, 10.0 + quick))
            self.assertEqual(save.call_count, 1)
            state.offset = saved
            third = self._grab_point(self.modal._layout(ctx, state))[0]
            self._clicks(operator, ctx, third, (10.0 + 2 * quick,))
            self.assertEqual((save.call_count, state.offset), (1, saved))

    def test_an_untyped_key_between_two_clicks_starts_over_and_a_click_ends_a_composition_run(self):
        # A dead key or an input-method event reaches the modal with no Python type: between two clicks
        # it is a key like any other, and a click between two such presses is no composition either.
        scene = bpy.context.scene
        scene.scenario.lane = "image"
        scene.scenario.lane_state("image").prompt = "hello world"
        ctx = self._context(sidebar=False)
        ctx.window_manager = SimpleNamespace(scenario_composer_text="")  # the popover opens empty
        quick = self._double_click_seconds() / 2
        state = self.state_mod.ComposerState()
        state.expanded = True
        state.sync_from_lane(scene)
        point, index = self._word_point(ctx, state)
        call_panel = mock.Mock(return_value={"INTERFACE"})
        ops = SimpleNamespace(wm=SimpleNamespace(call_panel=call_panel))
        with (
            mock.patch.object(self.runtime.state, "composer", state),
            mock.patch.object(self.modal, "bpy", SimpleNamespace(ops=ops)),
        ):
            operator = self._operator()
            self._clicks(operator, ctx, point, (10.0,))
            self.assertTrue(state.focused)
            # a dead key's press and release between the two clicks: two caret presses, no selection
            self._event(operator, ctx, "", "PRESS", point)
            self._event(operator, ctx, "", "RELEASE", point)
            self._clicks(operator, ctx, point, (10.0 + quick,))
            self.assertIsNone(state.field.selection)
            self.assertEqual(state.field.caret, index)
            # an untyped press, a click in the prompt, another untyped press: no text field
            self._event(operator, ctx, "", "PRESS", point)
            self._clicks(operator, ctx, point, (20.0,))
            self._event(operator, ctx, "", "PRESS", point)
            call_panel.assert_not_called()
            # a modal session that ends forgets both runs
            operator._finish(ctx)
            self._event(operator, ctx, "", "PRESS", point)
            call_panel.assert_not_called()
            self.assertTrue(state.focused)
            self._clicks(operator, ctx, point, (30.0,))
            operator._finish(ctx)
            self._clicks(operator, ctx, point, (30.0 + quick,))
            self.assertIsNone(state.field.selection)
            # the same context opens the popover on two untyped presses in a row
            self._event(operator, ctx, "", "PRESS", point)
            self._event(operator, ctx, "", "PRESS", point)
            call_panel.assert_called_once()
        operator.report.assert_not_called()
        self.assertEqual(scene.scenario.lane_state("image").prompt, "hello world")

    def test_a_double_click_on_generate_submits_once(self):
        scene = bpy.context.scene
        scene.scenario.lane = "image"
        ctx = self._context(sidebar=False)
        state = self.state_mod.ComposerState()
        state.expanded = True
        # Drawing the card synchronizes it from the form its Generate submits.
        state.sync_from_lane(scene)
        layout = self.modal._layout(ctx, state)
        point = self._centre(layout.generate_rect)
        self.assertEqual(layout.hit(*point), ("generate",))
        generate = mock.Mock()
        ops = SimpleNamespace(scenario=SimpleNamespace(generate=generate))
        quick = self._double_click_seconds() / 2
        with (
            mock.patch.object(self.runtime.state, "composer", state),
            mock.patch.object(self.modal, "bpy", SimpleNamespace(ops=ops)),
            mock.patch.object(self.modal.panels, "generate_enabled", return_value=True),
        ):
            operator = self._operator()
            self._clicks(operator, ctx, point, (10.0, 10.0 + quick))
            generate.assert_called_once_with(lane="image")
            # two separate clicks still submit twice, as two clicks on a button do
            self._clicks(operator, ctx, point, (20.0, 30.0))
        self.assertEqual(generate.call_count, 3)

    def test_a_double_click_value_from_a_direct_caller_still_resets(self):
        ctx = self._context(sidebar=False)
        state = self.state_mod.ComposerState()
        state.expanded, state.offset = True, (-120.0, 80.0)
        press, _kind = self._grab_point(self.modal._layout(ctx, state))
        with (
            mock.patch.object(self.runtime.state, "composer", state),
            mock.patch.object(self.modal, "_save_layout") as save,
        ):
            result = self._event(self._operator(), ctx, "LEFTMOUSE", "DOUBLE_CLICK", press)
        self.assertEqual(result, {"RUNNING_MODAL"})
        self.assertEqual(state.offset, (0.0, 0.0))
        save.assert_called_once_with()

    # -- handler lifetime ------------------------------------------------------
    def _session(self, prompt="a red kettle"):
        """An expanded card on the Image form, its layout and a context that can start the modal."""
        scene = bpy.context.scene
        scene.scenario.lane = "image"
        scene.scenario.lane_state("image").prompt = prompt
        ctx = self._context(sidebar=False)
        ctx.window_manager = SimpleNamespace(modal_handler_add=mock.Mock())
        state = self.state_mod.ComposerState()
        state.expanded = True
        state.sync_from_lane(scene)
        return ctx, state, self.modal._layout(ctx, state)

    def _invoke(self, operator, context, point):
        """The pointer moving over `point`: the key map starts the composer's modal there."""
        event = SimpleNamespace(type="MOUSEMOVE", value="NOTHING")
        event.mouse_region_x, event.mouse_region_y = point
        return self.modal.SCENARIO_OT_composer_modal.invoke(operator, context, event)

    def test_a_refused_generate_keeps_the_composer_usable(self):
        # The physical repro: with the GUI spend guard, Generate's poll refuses and bpy.ops raises.
        ctx, state, layout = self._session()
        generate = self._centre(layout.generate_rect)
        with (
            mock.patch.object(self.runtime.state, "composer", state),
            mock.patch.object(self.runtime.state, "composer_modal_running", False),
            mock.patch.object(self.modal.panels, "generate_enabled", return_value=True),
            mock.patch.object(self.modal, "_caret_index", return_value=0),
            mock.patch.dict(os.environ, {"SCENARIO_GUI_PROBE": "1"}),
        ):
            operator = self._operator()
            self.assertEqual(self._invoke(operator, ctx, generate), {"RUNNING_MODAL"})
            self.assertEqual(self._clicks(operator, ctx, generate, (10.0,))[0], {"RUNNING_MODAL"})
            operator.report.assert_called_once()
            self.assertEqual(operator.report.call_args.args[0], {"WARNING"})
            # the same handler keeps the composer: the next click focuses the prompt
            self.assertTrue(self.runtime.state.composer_modal_running)
            self._clicks(operator, ctx, self._centre(layout.prompt_rect), (20.0,))
            self.assertTrue(state.focused)

    def test_an_error_while_handling_input_releases_the_composer(self):
        # Blender ends a modal handler whose modal() raises without calling it again: the composer must not
        # stay marked as running, or every later session is refused and clicks fall through to the viewport.
        ctx, state, layout = self._session()
        prompt = self._centre(layout.prompt_rect)
        failure = ValueError("simulated failure")
        with (
            mock.patch.object(self.runtime.state, "composer", state),
            mock.patch.object(self.runtime.state, "composer_modal_running", False),
            mock.patch.object(self.modal, "_caret_index", return_value=0),
        ):
            operator = self._operator()
            self.assertEqual(self._invoke(operator, ctx, prompt), {"RUNNING_MODAL"})
            self._clicks(operator, ctx, prompt, (10.0,))
            self.assertTrue(state.focused)
            with (
                mock.patch.object(self.modal.panels, "form_takes_prompt", side_effect=failure),
                self.assertRaises(ValueError) as raised,
            ):
                self._event(operator, ctx, "A", "PRESS", prompt, unicode="a")
            self.assertIs(raised.exception, failure)  # Blender still reports the error
            self.assertFalse(self.runtime.state.composer_modal_running)
            # no caret is left drawn in a prompt whose keys now reach the viewport
            self.assertFalse(state.focused or state.dragging)
            self.assertEqual(self.scene_prompt(), "a red kettle")
            # the next pointer move over the composer starts a new session that takes the click
            self.assertEqual(self._invoke(operator, ctx, prompt), {"RUNNING_MODAL"})
            self.assertTrue(self.runtime.state.composer_modal_running)
            self._clicks(operator, ctx, prompt, (20.0,))
            self.assertTrue(state.focused)

    def test_a_handler_blender_removes_releases_the_composer(self):
        # A closed window or a loaded file removes the handler and calls the operator's cancel(), not modal().
        ctx, state, layout = self._session()
        saved = state.offset
        grab, _kind = self._grab_point(layout)
        with (
            mock.patch.object(self.runtime.state, "composer", state),
            mock.patch.object(self.runtime.state, "composer_modal_running", False),
        ):
            operator = self._operator()
            self.assertEqual(self._invoke(operator, ctx, grab), {"RUNNING_MODAL"})
            self._event(operator, ctx, "LEFTMOUSE", "PRESS", grab)
            self.assertIsNotNone(state.drag_mode)
            self.modal.SCENARIO_OT_composer_modal.cancel(operator, ctx)
            self.assertFalse(self.runtime.state.composer_modal_running)
            self.assertIsNone(state.drag_mode)
            self.assertEqual(state.offset, saved)
            self.assertEqual(self._invoke(operator, ctx, grab), {"RUNNING_MODAL"})

    @staticmethod
    def scene_prompt():
        return bpy.context.scene.scenario.lane_state("image").prompt

    # -- drag helpers ----------------------------------------------------------
    @staticmethod
    def _centre(rect):
        return (rect.x + rect.w / 2, rect.y + rect.h / 2)

    def _grab_point(self, layout):
        """A press on the drag surface: the collapsed pill, or the card's top padding."""
        if layout.expanded:
            card = layout.card_rect
            point = (card.x + card.w / 2, card.top - self.cl.PAD * layout.scale / 2)
            kind = "drag"
        else:
            point = self._centre(layout.pill_rect)
            kind = "expand" if layout.card_fits else "form"
        self.assertEqual(layout.hit(*point), (kind,))
        return point, kind

    def _operator(self):
        """A stand-in for the running modal operator: its handlers bound to a plain object."""
        cls = self.modal.SCENARIO_OT_composer_modal
        operator = SimpleNamespace(report=mock.Mock())
        for name in ("_finish", "_drag_move", "_drag_release"):
            setattr(operator, name, getattr(cls, name).__get__(operator))
        return operator

    def _event(self, operator, context, kind, value, point, unicode=""):
        """One event through the modal's handler, as Blender hands it to a running modal operator."""
        event = SimpleNamespace(
            type=kind,
            value=value,
            mouse_region_x=point[0],
            mouse_region_y=point[1],
            shift=False,
            ctrl=False,
            oskey=False,
            alt=False,
            unicode=unicode,
            is_repeat=False,
        )
        return self.modal.SCENARIO_OT_composer_modal.modal(operator, context, event)

    def _click(self, operator, context, point):
        """A left press and release at `point` without moving, through the modal's event handler."""
        for value in ("PRESS", "RELEASE"):
            event = SimpleNamespace(
                type="LEFTMOUSE",
                value=value,
                mouse_region_x=point[0],
                mouse_region_y=point[1],
                shift=False,
                ctrl=False,
                oskey=False,
                alt=False,
                unicode="",
            )
            result = self.modal.SCENARIO_OT_composer_modal.modal(operator, context, event)
            self.assertEqual(result, {"RUNNING_MODAL"})

    def _lane_labels(self):
        return set(self.cl.LANE_LABELS.values()) | set(self.cl.LANE_SHORT_LABELS.values())

    def _move(self, context, state, press, dx, dy):
        event = SimpleNamespace(mouse_region_x=press[0] + dx, mouse_region_y=press[1] + dy)
        self.modal.SCENARIO_OT_composer_modal._drag_move(SimpleNamespace(), context, state, event)
        return self.modal._layout(context, state)

    def _drag(self, context, state, press, kind, moves):
        """Press, move by each (dx, dy) from the press through the modal's handlers, then release."""
        state.begin_drag(press, kind)
        layouts = [self._move(context, state, press, dx, dy) for dx, dy in moves]
        operator = self.modal.SCENARIO_OT_composer_modal
        with mock.patch.object(self.modal, "_save_layout") as save:
            operator._drag_release(SimpleNamespace(), context, state, context.scene)
        self.assertIsNone(state.drag_mode)
        return layouts, save

    def _assert_same_rect(self, actual, expected):
        for name in ("x", "y", "w", "h"):
            self.assertAlmostEqual(getattr(actual, name), getattr(expected, name), msg=name)

    def _assert_reachable(self, layout, context, right_edge):
        """Card, Generate and minus lie between the toolbar and `right_edge` and take their clicks."""
        self.assertGreaterEqual(layout.card_rect.x, self.TOOLBAR_W)
        self.assertLessEqual(layout.card_rect.right, right_edge)
        for kind in ("generate", "collapse"):
            rect = getattr(layout, f"{kind}_rect")
            self.assertGreaterEqual(rect.y, 0)
            self.assertLessEqual(rect.top, context.region.height)
            self.assertEqual(layout.hit(*self._centre(rect)), (kind,))

    def _draw(self, context, state, texts=None):
        """Run the draw handler with gpu/blf stubbed (background Blender has no GPU) and return the drawn rects.

        Glyphs are 0.65 em wide, like Blender's UI font; drawn strings are appended to `texts` when given."""
        drawn = []
        metrics = {"size": 12.0}

        def rect(x, y, w, h, color, radius=8.0):
            if w > 0 and h > 0:
                drawn.append((x, y, w, h))

        fake_blf = SimpleNamespace(
            size=lambda font, size: metrics.update(size=size),
            dimensions=lambda font, text: (0.65 * metrics["size"] * len(text), metrics["size"]),
            color=lambda *args: None,
            position=lambda *args: None,
            draw=lambda font, text: texts.append(text) if texts is not None else None,
        )
        fake_gpu = SimpleNamespace(state=SimpleNamespace(blend_set=lambda mode: None))
        with (
            mock.patch.object(self.draw, "bpy", SimpleNamespace(context=context)),
            mock.patch.object(self.draw, "gpu", fake_gpu),
            mock.patch.object(self.draw, "blf", fake_blf),
            mock.patch.object(self.draw, "rect", rect),
            mock.patch.object(self.draw, "_grip", lambda *args, **kwargs: None),
            mock.patch.object(self.runtime.state, "composer", state),
        ):
            self.draw.draw_composer()
        return drawn


class ComposerEditFormTests(unittest.TestCase):
    """The 3D tab in Edit mode: the composer shows, prices and submits the Edit 3D form."""

    def setUp(self):
        self.jobs = test_model_generation.ModelGenerationTests()
        # Registered first, so a fixture setUp that fails partway still releases its patches.
        self.addCleanup(self.jobs.doCleanups)
        self.jobs.setUp()
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
                system=SimpleNamespace(ui_scale=1.0, pixel_size=1.0),
                view=SimpleNamespace(ui_scale=1.0),
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

    def press(
        self,
        kind=None,
        key=None,
        text="",
        expect=("RUNNING_MODAL",),
        tab=None,
        value="PRESS",
        when=0.0,
    ):
        """Deliver one composer click (on `kind` or a lane `tab`) or one key press to the real modal handler.

        `when` is the press time the composer reads; presses at the same point less than Blender's double-click
        time apart pair into a double-click, as real input does."""
        self.runtime.state.composer_modal_running = True
        context = SimpleNamespace(scene=self.scene, region=MagicMock())
        event = SimpleNamespace(
            type=key or "LEFTMOUSE",
            value=value,
            mouse_region_x=10,
            mouse_region_y=10,
            shift=False,
            ctrl=False,
            oskey=False,
            alt=False,
            unicode=text,
        )
        operator = SimpleNamespace(report=MagicMock(), _finish=MagicMock())
        hit = ("tab", tab) if tab else (kind,) if kind else None
        with (
            patch.object(self.modal, "_layout") as layout,
            patch.object(self.modal, "_caret_index", return_value=0),
            patch.object(self.modal, "_now", return_value=when),
        ):
            layout.return_value.hit.return_value = hit
            layout.return_value.scale = 1.0
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

    def retopology(self, prompt=""):
        """Load an Edit 3D task whose model takes no prompt into the Edit form."""
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
            prompt,
        )

    def focus_image_form(self):
        """Focus the composer on the Image tab's prompt."""
        self.composer.focused = False
        self.scene.scenario.lane = "image"
        self.scene.scenario.lane_state("image").prompt = "a lighthouse"
        self.drawn()
        self.composer.focused = True
        self.assertEqual(self.composer.field.text, "a lighthouse")

    def test_edit_task_without_a_prompt_offers_no_prompt_to_type(self):
        self.retopology()
        shown = self.drawn()
        self.assertEqual(shown.fields, ["This model takes no prompt"])
        operator = self.press("prompt")
        self.assertFalse(self.composer.focused)
        operator.report.assert_called_once()
        self.press(key="S", text="s", expect=("PASS_THROUGH",))
        self.assertEqual(self.edit3d.prompt, "")

    def test_tab_click_keeps_focus_only_for_a_form_that_takes_a_prompt(self):
        image = self.scene.scenario.lane_state("image")
        self.focus_image_form()
        self.press(tab="3d")
        # The Edit form takes a prompt: typing continues there.
        self.assertTrue(self.composer.focused)
        self.assertEqual(self.composer.field.text, "rusty iron plates")
        self.press(key="S", text="s")
        self.assertEqual((self.edit3d.prompt, image.prompt), ("rusty iron platess", "a lighthouse"))
        self.press(tab="image")
        self.assertTrue(self.composer.focused)
        self.assertEqual(self.composer.field.text, "a lighthouse")
        # The Edit task now takes no prompt: the tab shows why instead of keeping a focused field.
        self.retopology()
        self.press(tab="3d")
        self.assertFalse(self.composer.focused)
        self.assertEqual(self.drawn().fields, ["This model takes no prompt"])
        self.press(key="S", text="s", expect=("PASS_THROUGH",))
        self.assertEqual((self.edit3d.prompt, image.prompt), ("", "a lighthouse"))

    def test_tab_click_leaves_a_replaced_form_without_writing_either_form(self):
        image = self.scene.scenario.lane_state("image")
        image.prompt = "a lighthouse"
        for tab, field in (("3d", "rusty iron plates"), ("image", "a lighthouse")):
            with self.subTest(tab=tab):
                self.scene.scenario.lane = "3d"
                self.focus_text_form()
                edit_ticket = self.runtime.state.estimates[self.edit3d.estimate_key]
                operator = self.press(tab=tab)
                # Like Esc: the tab shows its current form and the field is no longer focused.
                self.assertFalse(self.composer.focused)
                operator.report.assert_not_called()
                shown = self.drawn()
                self.assertEqual(shown.fields, [field])
                self.assertFalse(any("Esc" in s for s in shown.texts))
                # The next key reaches Blender instead of the form the tab shows.
                self.press(key="S", text="s", expect=("PASS_THROUGH",))
                self.assert_prompts_unchanged()
                self.assertEqual(image.prompt, "a lighthouse")
                self.assertFalse(edit_ticket.used)
                self.assertEqual(self.edit3d.estimate_state, "READY")

    def test_double_click_keeps_a_replaced_form_until_esc(self):
        self.focus_text_form()
        self.press("prompt", value="DOUBLE_CLICK")
        # The double-click selects a word of the original text; it does not adopt the new form.
        self.assertTrue(self.composer.focused)
        self.assertEqual(self.composer.field.text, "a teapot")
        self.assertTrue(self.composer.form_replaced(self.scene))
        operator = self.press(key="S", text="s")
        operator.report.assert_called_once()
        self.assertIn("Esc", operator.report.call_args.args[1])
        self.assert_prompts_unchanged()
        self.assertEqual(self.drawn().fields, ["a teapot"])

    def test_real_double_clicks_keep_the_replaced_form_and_no_prompt_rules(self):
        # Blender hands the modal both presses of a real double-click as plain presses; the composer pairs them.
        self.focus_text_form()
        self.press("prompt", when=10.0)
        self.press("prompt", when=10.1)
        # The pair selects a word of the original text and adopts nothing from the form that replaced it.
        self.assertTrue(self.composer.focused)
        self.assertEqual(self.composer.field.selected_text(), "a")
        self.assertTrue(self.composer.form_replaced(self.scene))
        self.assert_prompts_unchanged()
        self.press(key="ESC")
        self.assertFalse(self.composer.focused)
        self.retopology()
        self.assertEqual(self.drawn().fields, ["This model takes no prompt"])
        first = self.press("prompt", when=20.0)
        second = self.press("prompt", when=20.1)
        # The first press explains the field; the paired second press neither focuses it nor repeats that.
        self.assertFalse(self.composer.focused)
        first.report.assert_called_once()
        second.report.assert_not_called()
        self.press(key="S", text="s", expect=("PASS_THROUGH",))
        self.assertEqual((self.three_d.prompt, self.edit3d.prompt), ("a teapot", ""))

    def test_focused_prompt_leaves_when_its_model_stops_taking_a_prompt(self):
        self.drawn()
        self.composer.focused = True
        self.assertEqual(self.composer.field.text, "rusty iron plates")
        # Another window or a tool loads an Edit task without a prompt into the same form.
        self.retopology("rusty iron plates")
        operator = self.press(key="S", text="s")
        self.assertFalse(self.composer.focused)
        operator.report.assert_called_once_with({"WARNING"}, "This model takes no prompt")
        self.assertEqual(self.edit3d.prompt, "rusty iron plates")
        self.assertEqual(self.drawn().fields, ["This model takes no prompt"])

    def key(self, key="", text=""):
        """Deliver one key press, named or with no Python type, with Blender's text field recorded, not opened."""
        self.runtime.state.composer_modal_running = True
        wm = bpy.context.window_manager
        context = SimpleNamespace(scene=self.scene, region=MagicMock(), window_manager=wm)
        event = SimpleNamespace(
            type=key,
            value="PRESS",
            mouse_region_x=10,
            mouse_region_y=10,
            shift=False,
            ctrl=False,
            oskey=False,
            alt=False,
            unicode=text,
            is_repeat=False,
        )
        operator = SimpleNamespace(report=MagicMock(), _finish=MagicMock())
        call_panel = MagicMock(return_value={"INTERFACE"})
        ops = SimpleNamespace(wm=SimpleNamespace(call_panel=call_panel))
        with (
            patch.object(self.modal, "_layout") as layout,
            patch.object(self.modal, "bpy", SimpleNamespace(ops=ops)),
        ):
            layout.return_value.hit.return_value = None
            layout.return_value.scale = 1.0
            result = self.modal.SCENARIO_OT_composer_modal.modal(operator, context, event)
        self.assertEqual(result, {"RUNNING_MODAL"})
        return operator, call_panel

    def confirm_text_field(self, text):
        """Confirm Blender's text field with `text`, as Enter in the popover does."""
        wm = bpy.context.window_manager
        self.runtime.state.last_message = ""
        wm.scenario_composer_text = text
        self.assertEqual(wm.scenario_composer_text, "")

    def test_text_field_types_into_the_edit_form_the_composer_shows(self):
        self.drawn()
        self.composer.focused = True
        self.confirm_text_field(" 日本")
        self.assertEqual(self.edit3d.prompt, "rusty iron plates 日本")
        self.assertEqual(self.three_d.prompt, "a teapot")
        self.assertTrue(self.composer.focused)

    def test_input_method_text_never_reaches_the_form_that_replaced_it(self):
        # A key with text Blender cannot name, F2, and a composition's second press all type into the prompt.
        for keys in ((("", "é"),), (("F2", ""),), (("", ""), ("", ""))):
            with self.subTest(keys=keys):
                self.focus_text_form()
                for key, text in keys:
                    operator, call_panel = self.key(key, text)
                call_panel.assert_not_called()
                operator.report.assert_called_once()
                self.assertIn("Esc", operator.report.call_args.args[1])
                self.assertTrue(self.composer.focused)
                self.assertEqual(self.composer.field.text, "a teapot")
                self.assert_prompts_unchanged()
        # Blender's text field may be confirmed after the form changed: neither form takes its text.
        self.focus_text_form()
        self.confirm_text_field("日本")
        self.assertTrue(self.composer.focused)
        self.assertEqual(self.composer.field.text, "a teapot")
        self.assert_prompts_unchanged()
        self.assertIn("Esc", self.runtime.state.last_message)

    def test_input_method_text_leaves_a_form_without_a_prompt(self):
        self.drawn()
        # Another window or a tool loads an Edit task without a prompt into the focused form.
        self.retopology("rusty iron plates")
        for keys in ((("", "é"),), (("F2", ""),), (("", ""), ("", ""))):
            with self.subTest(keys=keys):
                self.composer.focused = True
                for key, text in keys:
                    operator, call_panel = self.key(key, text)
                call_panel.assert_not_called()
                operator.report.assert_called_once_with({"WARNING"}, "This model takes no prompt")
                self.assertFalse(self.composer.focused)
                self.assertEqual(self.edit3d.prompt, "rusty iron plates")
        self.composer.focused = True
        self.confirm_text_field("日本")
        self.assertFalse(self.composer.focused)
        self.assertEqual(self.edit3d.prompt, "rusty iron plates")
        self.assertEqual(self.runtime.state.last_message, "This model takes no prompt")


class ComposerEditFormFixtureTests(unittest.TestCase):
    def test_a_failed_fixture_setup_still_releases_its_patches(self):
        released = []

        def failing_setup(jobs):
            jobs.addCleanup(released.append, "fixture patches")
            raise RuntimeError("fixture setup failed")

        test = ComposerEditFormTests("test_composer_displays_and_submits_the_edit_form_price")
        with (
            patch.object(test_model_generation.ModelGenerationTests, "setUp", failing_setup),
            self.assertRaisesRegex(RuntimeError, "fixture setup failed"),
        ):
            test.setUp()
        test.doCleanups()
        self.assertEqual(released, ["fixture patches"])
