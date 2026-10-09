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

    def _context(self, sidebar=True, overlap=True, flipped=False):
        """A 3D view area as Blender lays it out: window-relative region x, the sidebar on the right."""
        x, w = self.AREA_X, self.AREA_W
        sidebar_w = self.SIDEBAR_W if sidebar else 1
        sidebar_x = x if flipped else x + w - sidebar_w
        toolbar_x = x + w - self.TOOLBAR_W if flipped else x
        if overlap:
            window = _region("WINDOW", x, w)
        else:
            window = _region("WINDOW", x + self.TOOLBAR_W, w - self.TOOLBAR_W - sidebar_w)
        regions = [
            _region("HEADER", x, w, y=1000, height=26),
            _region("TOOLS", toolbar_x, self.TOOLBAR_W),
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
            preferences=bpy.context.preferences,
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
        if region.width - left - right >= layout.card_rect.w:
            self.assertGreaterEqual(layout.card_rect.x, left)
            self.assertLessEqual(layout.card_rect.right, region.width - right)

    def _draw(self, context, state):
        """Run the draw handler with gpu/blf stubbed (background Blender has no GPU) and return the drawn rects."""
        drawn = []

        def rect(x, y, w, h, color, radius=8.0):
            if w > 0 and h > 0:
                drawn.append((x, y, w, h))

        fake_blf = SimpleNamespace(
            size=lambda font, size: None,
            dimensions=lambda font, text: (6.0 * len(text), 10.0),
            color=lambda *args: None,
            position=lambda *args: None,
            draw=lambda font, text: None,
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
