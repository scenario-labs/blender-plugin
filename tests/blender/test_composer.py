# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
import unittest
from types import SimpleNamespace
from unittest import mock

import bpy
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

    def _context(self, sidebar=True, overlap=True, flipped=False, geometry=None, preferences=None):
        """A 3D view area as Blender lays it out: window-relative region x, the sidebar on the right.

        `geometry` is (area x, area width, toolbar width, sidebar width), `preferences` stands in for
        Blender's (pixel size and UI scale)."""
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
            window = _region("WINDOW", x, w)
        else:
            window = _region("WINDOW", x + toolbar_w, w - toolbar_w - sidebar_w)
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
        # sidebar closed: drag the card to the bare right edge, where only MIN_VISIBLE px remain
        press, kind = self._grab_point(self.modal._layout(closed, state))
        self._drag(closed, state, press, kind, ((5000, 0),))
        parked = self.modal._layout(closed, state)
        keep = self.cl.MIN_VISIBLE * parked.scale
        self.assertAlmostEqual(parked.card_rect.x, closed.region.width - keep)
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
    # The physical desktop case: Retina pixel size 2 with a Preferences UI scale of 2 (composer scale 4),
    # a 226 px toolbar and a 1122 px sidebar at x=1355 over a 2477 px viewport. About 1129 px stay
    # uncovered, less than the 1680 px minimum card.
    RETINA = (0, 2477, 226, 1122)

    def _retina(self, sidebar=True):
        prefs = SimpleNamespace(
            system=SimpleNamespace(pixel_size=2.0), view=SimpleNamespace(ui_scale=2.0)
        )
        return self._context(sidebar=sidebar, geometry=self.RETINA, preferences=prefs)

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
                    self._click(self._operator(), ctx, press)
                open_settings.assert_called_once_with(ctx, "material")
                message.assert_called_once_with(self.modal.NO_ROOM_MESSAGE)
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
