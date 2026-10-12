# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Installed composer job strip and job card over real shared jobs; not physical input proof.

The SDK transport is the synthetic fixture of test_model_generation. Dialogs and popups that a
strip click opens from the composer modal cannot be shown headless: these tests record the
operator call each click makes, and run the real operator where it needs no window."""

import contextlib
import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import bpy
import test_model_generation
from helpers import online_access, submodule


class RecordingOps:
    """Stands in for bpy.ops: records `category.name(*args, **properties)` calls."""

    def __init__(self):
        self.calls = []

    def __getattr__(self, category):
        calls = self.calls

        class Category:
            def __getattr__(self, name):
                def call(*args, **properties):
                    calls.append((f"{category}.{name}", args, properties))
                    return {"RUNNING_MODAL"}

                return call

        return Category()


class ComposerJobStripTests(unittest.TestCase):
    def setUp(self):
        self.jobs = test_model_generation.ModelGenerationTests()
        # Registered first, so a fixture setUp that fails partway still releases its patches.
        self.addCleanup(self.jobs.doCleanups)
        self.jobs.setUp()
        self.runtime = self.jobs.runtime
        self.generation = self.jobs.generation
        self.draw = submodule("blender.composer.draw")
        self.modal = submodule("blender.composer.modal")
        self.job_card = submodule("blender.composer.job_card")
        self.composer = submodule("blender.composer.state").ComposerState()
        self.composer.expanded = True
        self.runtime.state.composer = self.composer
        self.scene = bpy.context.scene
        self.scene.scenario.lane = "image"
        self.region = SimpleNamespace(
            type="WINDOW", x=0, y=0, width=1600, height=900, tag_redraw=MagicMock()
        )
        self.context = SimpleNamespace(
            region=self.region,
            area=None,
            scene=self.scene,
            space_data=SimpleNamespace(type="VIEW_3D", region_3d=object()),
            preferences=SimpleNamespace(system=SimpleNamespace(ui_scale=1.0)),
            window_manager=SimpleNamespace(modal_handler_add=MagicMock()),
        )
        # Glyphs 0.65 em wide, as in Blender's UI font; drawing and hit testing share them.
        self.metrics = {"size": 12.0}
        self.fake_blf = SimpleNamespace(
            size=lambda font, size: self.metrics.update(size=size),
            dimensions=lambda font, text: (0.65 * self.metrics["size"] * len(text), 12.0),
            color=lambda *args: None,
            position=lambda *args: None,
            draw=lambda *args: None,
        )
        self.enterContext(patch.object(self.draw, "blf", self.fake_blf))
        # Press time as the modal reads it; press() spaces clicks well beyond a double-click.
        self.clock = 0.0

    # -- fixtures -----------------------------------------------------------------
    def submit_image(self, progress=0.42, status="in-progress", job_type="inference"):
        """One Image form job, polled once: the strip's current job for this scene lane.

        Scenario reports it as `job_type`. Only a poll that confirms an inference job offers Cancel
        generation; captured model generations report custom."""
        self.jobs.job_type = job_type
        self.jobs.remote_status, self.jobs.remote_progress = status, progress
        self.jobs.ui_quote()
        view = self.generation.submit_generation(bpy.context, "image")
        self.jobs.deliver_results()
        return view

    @contextlib.contextmanager
    def read_only(self):
        """Drawing must not create job owners or sessions, read storage or write scene data."""
        owner = self.runtime.state.model_jobs
        store = self.jobs.store
        with (
            patch.object(self.runtime, "ensure_model_jobs", side_effect=AssertionError("ensure")),
            patch.object(self.runtime, "ensure_job_session", side_effect=AssertionError("session")),
            patch.object(self.runtime, "ensure_job_store", side_effect=AssertionError("store")),
            patch.object(store, "get", side_effect=AssertionError("store read in draw")),
            patch.object(store, "records", side_effect=AssertionError("store read in draw")),
        ):
            yield owner

    def drawn(self):
        """Run the real draw handler with recording primitives; return what it showed."""
        shown = SimpleNamespace(texts=[], chips=[], rects=[], dismiss=[])

        def chip(rect, label, *args, **kwargs):
            shown.chips.append(label)

        recorders = {
            "bpy": SimpleNamespace(context=self.context),
            "gpu": MagicMock(),
            "rect": MagicMock(side_effect=lambda *args, **kwargs: shown.rects.append(args)),
            "text": MagicMock(side_effect=lambda x, y, size, s, *a, **k: shown.texts.append(s)),
            "_chip": MagicMock(side_effect=chip),
            "_dismiss": MagicMock(side_effect=lambda *args, **kwargs: shown.dismiss.append(args)),
            "_prompt_field": MagicMock(),
            "_minus_button": MagicMock(),
            "_grip": MagicMock(),
        }
        with contextlib.ExitStack() as stack:
            for name, value in recorders.items():
                stack.enter_context(patch.object(self.draw, name, value))
            self.draw.draw_composer()
        shown.geometry = self.draw.composer_geometry(self.context, self.composer)
        shown.line = next((s for s in shown.texts if " · " in s), None)
        return shown

    def chip_point(self, key):
        strip = self.draw.composer_geometry(self.context, self.composer).strip
        rect = dict(strip.chip_rects)[key]
        return rect.x + rect.w / 2, rect.y + rect.h / 2

    def dismiss_point(self):
        strip = self.draw.composer_geometry(self.context, self.composer).strip
        rect = strip.dismiss_rect
        return rect.x + rect.w / 2, rect.y + rect.h / 2

    def press(self, point, ops=None):
        """One left click through the real modal handler and real geometry; returns the operator.

        Each press comes ten seconds after the previous one, so two presses on one target are two
        clicks, never a double-click."""
        self.clock += 10.0
        self.runtime.state.composer_modal_running = True
        event = SimpleNamespace(
            type="LEFTMOUSE",
            value="PRESS",
            mouse_region_x=point[0],
            mouse_region_y=point[1],
            shift=False,
            ctrl=False,
            oskey=False,
            alt=False,
            unicode="",
        )
        operator = SimpleNamespace(report=MagicMock(), _finish=MagicMock())
        recording = ops if ops is not None else RecordingOps()
        with (
            patch.object(self.modal, "bpy", SimpleNamespace(ops=recording)),
            patch.object(self.modal, "_now", return_value=self.clock),
        ):
            result = self.modal.SCENARIO_OT_composer_modal.modal(operator, self.context, event)
        self.assertEqual(result, {"RUNNING_MODAL"})
        operator.ops = recording
        return operator

    def click(self, point, when):
        """A press and its release at `point`, the press read at time `when`, as Blender hands a click
        to the running modal: a double-click arrives as two of these. Returns the operator."""
        cls = self.modal.SCENARIO_OT_composer_modal
        operator = SimpleNamespace(report=MagicMock(), ops=RecordingOps())
        for name in ("_finish", "_drag_move", "_drag_release"):
            setattr(operator, name, getattr(cls, name).__get__(operator))
        self.runtime.state.composer_modal_running = True
        results = []
        with (
            patch.object(self.modal, "bpy", SimpleNamespace(ops=operator.ops)),
            patch.object(self.modal, "_now", return_value=when),
        ):
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
                results.append(cls.modal(operator, self.context, event))
        self.assertEqual(results[0], {"RUNNING_MODAL"})
        return operator

    def descriptor(self, view, key):
        recovery = submodule("blender.job_recovery")
        return next(item for item in recovery.result_actions(view) if item.key == key)

    # -- drawing --------------------------------------------------------------------
    def test_strip_shows_the_scene_lane_job_and_drawing_is_read_only(self):
        view = self.submit_image()
        owner = self.runtime.state.model_jobs
        before = owner.session.capture(self.scene)
        meta = dict(view.meta)
        prompt, estimate = (
            self.scene.scenario.image.prompt,
            self.scene.scenario.image.estimate_state,
        )
        breaker = submodule("blender.composer.breaker").Breaker("fixture")
        with self.read_only():
            shown = self.drawn()
            for _ in range(30):
                breaker.guard(self.drawn)
        self.assertFalse(breaker.tripped, breaker.reason)
        self.assertIn("a teapot", shown.line)
        self.assertIn("Generating 42%", shown.line)
        self.assertIn("CU", shown.line)
        self.assertEqual(shown.chips[-2:], ["Cancel generation", "Inspect"])
        self.assertEqual(len(shown.dismiss), 1)
        # The determinate bar fills 42% of its track in the accent colour.
        bar = shown.geometry.strip.progress_rect
        fill = [r for r in shown.rects if r[:2] == (bar.x, bar.y) and r[4] == self.draw.ACCENT]
        self.assertEqual(len(fill), 1)
        self.assertAlmostEqual(fill[0][2], bar.w * 0.42)
        self.assertEqual(view.meta, meta)
        self.assertEqual(owner.session.capture(self.scene), before)
        self.assertEqual(self.scene.scenario.image.prompt, prompt)
        self.assertEqual(self.scene.scenario.image.estimate_state, estimate)
        self.assertEqual(
            self.composer.drawn_strips[self.draw.region_key(self.region)],
            shown.geometry.signature(),
        )
        self.assertEqual(len(self.jobs.paid), 1)

    def test_tray_sits_outside_the_card_and_hits_before_it(self):
        self.submit_image()
        geometry = self.draw.composer_geometry(self.context, self.composer)
        card, tray = geometry.layout.card_rect, geometry.strip.rect
        self.assertGreaterEqual(tray.y, card.top)
        self.assertEqual(geometry.hit(*self.chip_point("inspect")), ("job", "inspect"))
        self.assertEqual(geometry.hit(*self.dismiss_point()), ("job_dismiss",))
        self.assertEqual(geometry.hit(tray.x + 20, tray.y + tray.h / 2), ("drag",))
        # The card's own controls keep their hits.
        generate = geometry.layout.generate_rect
        point = (generate.x + generate.w / 2, generate.y + generate.h / 2)
        self.assertEqual(geometry.hit(*point), ("generate",))
        # Hovering the tray starts the modal like hovering the card.
        operator = SimpleNamespace()
        event = SimpleNamespace(mouse_region_x=tray.x + 20, mouse_region_y=tray.y + 5)
        self.runtime.state.composer_modal_running = False
        result = self.modal.SCENARIO_OT_composer_modal.invoke(operator, self.context, event)
        self.assertEqual(result, {"RUNNING_MODAL"})
        self.runtime.state.composer_modal_running = False

    def test_collapsed_pill_draws_an_indicator_and_keeps_its_hit(self):
        self.submit_image()
        self.composer.expanded = False
        shown = self.drawn()
        geometry = shown.geometry
        self.assertTrue(geometry.strip.hidden)
        bar = geometry.strip.indicator_rect
        self.assertIsNotNone(bar)
        self.assertTrue(any(r[:2] == (bar.x, bar.y) for r in shown.rects))
        self.assertEqual(shown.chips, [])
        self.assertIsNone(geometry.signature())
        pill = geometry.layout.pill_rect
        self.assertEqual(geometry.hit(pill.x + pill.w / 2, pill.y + pill.h / 2), ("expand",))

    def test_header_and_asset_shelf_heights_keep_the_tray_clear(self):
        area_regions = [
            SimpleNamespace(type="HEADER", x=0, y=874, width=1600, height=26),
            SimpleNamespace(type="TOOL_HEADER", x=0, y=848, width=1600, height=26),
            SimpleNamespace(type="ASSET_SHELF", x=0, y=0, width=1600, height=120),
            SimpleNamespace(type="UI", x=1300, y=0, width=300, height=900),
            self.region,
        ]
        space = SimpleNamespace(
            show_region_header=True, show_region_tool_header=True, show_region_asset_shelf=True
        )
        area = SimpleNamespace(regions=area_regions, spaces=SimpleNamespace(active=space))
        self.assertEqual(self.draw.overlap_vertical_insets(area, self.region), (120.0, 52.0))
        space.show_region_asset_shelf = False
        self.assertEqual(self.draw.overlap_vertical_insets(area, self.region), (0.0, 52.0))
        # Regions beside the viewport (no region overlap) do not cover it.
        space.show_region_asset_shelf = True
        beside = SimpleNamespace(type="WINDOW", x=0, y=120, width=1600, height=728)
        area_regions[-1] = beside
        self.assertEqual(self.draw.overlap_vertical_insets(area, beside), (0.0, 0.0))
        self.assertEqual(self.draw.overlap_vertical_insets(None, self.region), (0.0, 0.0))
        area_regions[-1] = self.region
        self.context.area = area
        self.submit_image()
        tray = self.draw.composer_geometry(self.context, self.composer).strip.rect
        self.assertGreaterEqual(tray.y, 120.0)
        self.assertLessEqual(tray.top, 848.0)
        self.assertLessEqual(tray.right, 1300.0)
        # A card dragged up stays whole in the viewport, its top under the headers: the tray moves
        # below it, clear of the headers, instead of under them.
        self.composer.offset = (0.0, 2000.0)
        geometry = self.draw.composer_geometry(self.context, self.composer)
        card, tray = geometry.layout.card_rect, geometry.strip.rect
        self.assertGreater(card.top, 848.0)
        self.assertFalse(geometry.strip.hidden)
        self.assertLessEqual(tray.top, card.y)
        self.assertGreaterEqual(tray.y, 120.0)
        # With the shelf reaching the card, neither side is clear: the tray hides instead.
        area_regions[2].height = card.y
        geometry = self.draw.composer_geometry(self.context, self.composer)
        self.assertTrue(geometry.strip.hidden)
        self.assertIsNone(geometry.signature())

    def test_real_viewport_regions_feed_the_vertical_insets(self):
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
        bottom, top = self.draw.overlap_vertical_insets(area, region)
        self.assertIsInstance(bottom, float)
        self.assertIsInstance(top, float)
        self.assertGreaterEqual(min(bottom, top), 0.0)
        self.assertLessEqual(bottom + top, region.height)

    # -- double-click -----------------------------------------------------------------
    # Blender hands a modal operator both presses of a double-click as plain presses; the composer
    # pairs them on the targets its clicks reach (see test_composer), the tray included.

    def test_a_double_click_on_the_tray_background_resets_the_placement(self):
        self.submit_image()
        quick = self.modal._double_click_seconds(self.context) / 2
        threshold = submodule("core.ui.composer_layout").DRAG_THRESHOLD
        saved = (-120.0, 80.0)
        cases = (
            ((10.0, 10.0 + quick), (0, 0), True),
            ((10.0, 10.0 + quick), (threshold, -threshold), True),  # a slight drift still pairs
            ((10.0, 10.0 + 2 * quick + 0.01), (0, 0), False),  # past the double-click time
            ((10.0, 10.0 + quick), (threshold + 1, 0), False),  # moved beyond the threshold
        )
        for times, drift, resets in cases:
            with self.subTest(times=times, drift=drift):
                self.composer.offset, self.composer.width = saved, 600
                self.composer.presses.reset()
                geometry = self.draw.composer_geometry(self.context, self.composer)
                tray = geometry.strip.rect
                point = (tray.x + 20, tray.y + tray.h / 2)
                second = (point[0] + drift[0], point[1] + drift[1])
                self.assertFalse(geometry.layout.card_rect.contains(*point))
                self.assertEqual(geometry.hit(*point), ("drag",))
                self.assertEqual(geometry.hit(*second), ("drag",))
                with patch.object(self.modal, "_save_layout") as save:
                    first = self.click(point, times[0])
                    self.assertEqual((self.composer.offset, self.composer.drag_mode), (saved, None))
                    last = self.click(second, times[1])
                if resets:
                    self.assertEqual(
                        (self.composer.offset, self.composer.width), ((0.0, 0.0), None)
                    )
                    save.assert_called_once_with()
                else:
                    self.assertEqual((self.composer.offset, self.composer.width), (saved, 600))
                    save.assert_not_called()
                self.assertIsNone(self.composer.drag_mode)
                self.assertEqual(first.ops.calls + last.ops.calls, [])
        self.assertEqual(len(self.jobs.paid), 1)

    def test_a_double_click_on_a_chip_dispatches_it_once(self):
        # As on Generate, the second press of a double-click does nothing more: a chip never opens
        # its confirmation or runs its operator twice for one double-click.
        view = self.submit_image()
        self.drawn()
        quick = self.modal._double_click_seconds(self.context) / 2
        point = self.chip_point("cancel")
        expected = [
            (
                "scenario.recover_job",
                ("INVOKE_DEFAULT",),
                dict(self.descriptor(view, "cancel").properties),
            )
        ]
        first = self.click(point, 10.0)
        second = self.click(point, 10.0 + quick)
        self.assertEqual(first.ops.calls, expected)
        self.assertEqual(second.ops.calls, [])
        second.report.assert_not_called()
        # The pair is spent: the next quick press is a click of its own.
        third = self.click(point, 10.0 + 2 * quick)
        self.assertEqual(third.ops.calls, expected)
        self.assertEqual(self.jobs.cancel_calls, [])
        self.assertEqual(len(self.jobs.paid), 1)

    # -- dispatch ---------------------------------------------------------------------
    def test_each_chip_dispatches_its_descriptor_with_invoke_default(self):
        view = self.submit_image()
        self.drawn()
        cancel = self.descriptor(view, "cancel")
        operator = self.press(self.chip_point("cancel"))
        self.assertEqual(
            operator.ops.calls,
            [("scenario.recover_job", ("INVOKE_DEFAULT",), dict(cancel.properties))],
        )
        self.assertEqual(dict(cancel.properties)["action"], "cancel")
        self.assertEqual(dict(cancel.properties)["expected_revision"], view.meta["saved_revision"])
        operator = self.press(self.chip_point("inspect"))
        self.assertEqual(
            operator.ops.calls,
            [("scenario.composer_job_card", ("INVOKE_DEFAULT",), {"request_id": view.local_id})],
        )
        # A remote cancellation keeps its native confirmation.
        recovery = submodule("blender.job_recovery")
        manager = SimpleNamespace(invoke_confirm=MagicMock(return_value={"RUNNING_MODAL"}))
        target = SimpleNamespace(action="cancel")
        target.execute = MagicMock()
        result = recovery.SCENARIO_OT_recover_job.invoke(
            target, SimpleNamespace(window_manager=manager), None
        )
        self.assertEqual(result, {"RUNNING_MODAL"})
        manager.invoke_confirm.assert_called_once_with(target, None)
        target.execute.assert_not_called()
        self.assertEqual(self.jobs.cancel_calls, [])
        self.assertEqual(len(self.jobs.paid), 1)

    def test_a_job_not_confirmed_as_inference_offers_no_cancel_chip(self):
        # Scenario documents cancellation only for inference jobs; a captured model generation
        # reports custom, so its tray offers Inspect alone, as its Jobs row offers no Cancel.
        view = self.submit_image(job_type="custom")
        shown = self.drawn()
        self.assertIn("Generating 42%", shown.line)
        self.assertEqual([chip.key for chip in shown.geometry.job.chips], ["inspect"])
        self.assertNotIn("Cancel generation", shown.chips)
        recovery = submodule("blender.job_recovery")
        self.assertNotIn("cancel", [item.key for item in recovery.result_actions(view)])
        self.assertEqual(self.jobs.cancel_calls, [])

    def test_result_actions_dispatch_alone_or_through_the_job_card(self):
        self.jobs.result_fixture()
        view = self.submit_image(progress=None, status="success")
        self.assertEqual(view.meta["saved_state"], "applied")
        shown = self.drawn()
        job = shown.geometry.job
        self.assertIn("Applied", shown.line)
        self.assertEqual(job.status.tone, "done")
        # The automatic import stays recorded once applied; the saved state decides the wording.
        self.assertTrue(self.runtime.state.model_jobs.imports_automatically(view.local_id))
        # A saved PNG can be imported again, set as World or handed to Render Video as its first
        # frame: one choice opens the card.
        reuse = [item.action for item in job.actions if item.group == "apply"]
        self.assertEqual(reuse, ["import_images", "apply_world", "use_first_frame"])
        self.assertEqual(shown.chips[-2:], ["Reuse... (3)", "Inspect"])
        operator = self.press(self.chip_point("choose"))
        self.assertEqual(
            operator.ops.calls,
            [("scenario.composer_job_card", ("INVOKE_DEFAULT",), {"request_id": view.local_id})],
        )
        # A single result action is its own chip and runs its operator's review.
        recovery = submodule("blender.job_recovery")
        single = (self.descriptor(view, "import_images"),)
        with patch.object(recovery, "result_actions", return_value=single):
            shown = self.drawn()
            self.assertEqual(shown.chips[-2:], ["Import saved images", "Inspect"])
            operator = self.press(self.chip_point("import_images"))
        self.assertEqual(
            operator.ops.calls,
            [("scenario.import_saved_images", ("INVOKE_DEFAULT",), dict(single[0].properties))],
        )
        self.assertEqual(len(self.jobs.paid), 1)

    def test_a_click_on_a_job_that_changed_since_drawing_is_consumed(self):
        view = self.submit_image()
        self.drawn()
        # The job finishes before the click: its revision and actions change.
        self.jobs.result_fixture()
        self.jobs.poll_now(view.local_id)
        operator = self.press(self.chip_point("inspect"))
        self.assertEqual(operator.ops.calls, [])
        operator.report.assert_called_once_with({"INFO"}, self.modal.JOB_CHANGED)
        # Once drawn again, the same chip dispatches.
        self.drawn()
        operator = self.press(self.chip_point("inspect"))
        self.assertEqual(len(operator.ops.calls), 1)
        # A strip that was never drawn in this region takes no action either.
        self.composer.drawn_strips.clear()
        operator = self.press(self.chip_point("inspect"))
        self.assertEqual(operator.ops.calls, [])
        operator.report.assert_called_once_with({"INFO"}, self.modal.JOB_CHANGED)

    def test_a_status_refresh_keeps_the_drawn_action_but_only_inspect_dispatches(self):
        view = self.submit_image()
        owner = self.runtime.state.model_jobs
        self.drawn()
        # Hold the next automatic status refresh in flight.
        self.jobs.block_cloud_read = True
        self.jobs.release.clear()
        owner._next_poll[view.local_id] = 0.0
        # The first poll offers the actions, then queues the refresh; the next one projects it.
        self.runtime.sync_catalog_context()
        self.runtime.sync_catalog_context()
        self.assertTrue(owner.busy(view.local_id))
        self.assertEqual(view.meta["recovery_actions"], ())
        try:
            shown = self.drawn()
            self.assertTrue(shown.geometry.job.held)
            self.assertEqual(shown.chips[-2:], ["Cancel generation", "Inspect"])
            operator = self.press(self.chip_point("cancel"))
            self.assertEqual(operator.ops.calls, [])
            operator.report.assert_called_once_with({"INFO"}, self.modal.JOB_BUSY)
            operator = self.press(self.chip_point("inspect"))
            self.assertEqual(operator.ops.calls[0][0], "scenario.composer_job_card")
        finally:
            self.jobs.release.set()
        self.jobs.deliver_results()
        self.assertFalse(owner.busy(view.local_id))
        self.drawn()
        operator = self.press(self.chip_point("cancel"))
        self.assertEqual(operator.ops.calls[0][0], "scenario.recover_job")
        self.assertEqual(len(self.jobs.paid), 1)

    def test_the_poll_that_starts_a_status_refresh_already_holds_the_actions(self):
        view = self.submit_image()
        owner = self.runtime.state.model_jobs
        self.jobs.block_cloud_read = True
        self.jobs.release.clear()
        owner._next_poll[view.local_id] = 0.0
        # This poll lists the job's actions before it queues the refresh, so until the next poll
        # the view still offers them while the job is busy.
        self.runtime.sync_catalog_context()
        self.assertTrue(owner.busy(view.local_id))
        self.assertIn("cancel", view.meta["recovery_actions"])
        try:
            # The strip was never drawn before this tick: it holds what the view lists.
            shown = self.drawn()
            self.assertTrue(shown.geometry.job.held)
            self.assertEqual(shown.chips[-2:], ["Cancel generation", "Inspect"])
            operator = self.press(self.chip_point("cancel"))
            self.assertEqual(operator.ops.calls, [])
            operator.report.assert_called_once_with({"INFO"}, self.modal.JOB_BUSY)
            # The next poll projects the running refresh; the strip keeps the same held chips.
            self.runtime.sync_catalog_context()
            self.assertEqual(view.meta["recovery_actions"], ())
            shown = self.drawn()
            self.assertTrue(shown.geometry.job.held)
            self.assertEqual(shown.chips[-2:], ["Cancel generation", "Inspect"])
        finally:
            self.jobs.release.set()
        self.jobs.deliver_results()
        self.assertFalse(owner.busy(view.local_id))
        self.assertFalse(self.drawn().geometry.job.held)
        self.assertEqual(self.jobs.cancel_calls, [])
        self.assertEqual(len(self.jobs.paid), 1)

    def test_a_queued_unsent_job_cancels_through_its_live_chip(self):
        quotes = [self.jobs.mcp_quote() for _ in range(3)]
        self.jobs.release.clear()
        try:
            # Occupy both shared workers so the third approved submission stays queued.
            for quote in quotes[:2]:
                self.jobs.entered.clear()
                self.jobs.mcp_submit(quote)
                self.assertTrue(self.jobs.entered.wait(5))
            request_id = self.jobs.mcp_submit(quotes[2])["local_id"]
            self.runtime.sync_catalog_context()
            owner = self.runtime.state.model_jobs
            self.assertTrue(owner.busy(request_id))
            shown = self.drawn()
            self.assertEqual(shown.geometry.job.request_id, request_id)
            self.assertFalse(shown.geometry.job.held)
            self.assertIn("+2 more", shown.line)
            self.assertEqual(shown.chips[-2:], ["Cancel prepared job", "Inspect"])
            operator = self.press(self.chip_point("cancel_prepared"))
            call = operator.ops.calls[0]
            self.assertEqual((call[0], call[1]), ("scenario.recover_job", ("INVOKE_DEFAULT",)))
            self.assertEqual(call[2]["action"], "cancel_prepared")
            self.assertEqual(call[2]["request_id"], request_id)
            # Confirming that dialog runs the operator with exactly these properties.
            self.assertEqual(bpy.ops.scenario.recover_job(**call[2]), {"FINISHED"})
        finally:
            self.jobs.release.set()
        self.jobs.settle()
        self.assertEqual(self.jobs.store.get(request_id).state.value, "canceled")
        self.assertEqual(len(self.jobs.paid), 2)

    def test_focused_prompt_conflict_blocks_dispatch_and_keeps_both_texts(self):
        view = self.submit_image()
        self.drawn()
        self.composer.sync_from_lane(self.scene)
        self.composer.focused = True
        self.composer.field.set_text("pending composer text")
        self.scene.scenario.image.prompt = "edited in the sidebar"
        operator = self.press(self.chip_point("inspect"))
        self.assertEqual(operator.ops.calls, [])
        operator.report.assert_called_once()
        self.assertEqual(operator.report.call_args.args[0], {"WARNING"})
        self.assertTrue(self.composer.focused)
        self.assertEqual(self.composer.field.text, "pending composer text")
        self.assertEqual(self.scene.scenario.image.prompt, "edited in the sidebar")
        # An unchanged form is committed, then the card opens.
        self.composer.focused = False
        self.composer.sync_from_lane(self.scene)
        self.composer.focused = True
        self.composer.field.set_text("committed before the card")
        self.drawn()
        operator = self.press(self.chip_point("inspect"))
        self.assertEqual(operator.ops.calls[0][2], {"request_id": view.local_id})
        self.assertFalse(self.composer.focused)
        self.assertEqual(self.scene.scenario.image.prompt, "committed before the card")

    def test_dismissal_hides_only_that_job_until_a_new_one_or_a_file_load(self):
        first = self.submit_image()
        self.drawn()
        state_before = self.jobs.store.get(first.local_id).state
        operator = self.press(self.dismiss_point())
        self.assertEqual(operator.ops.calls, [])
        self.region.tag_redraw.assert_called()
        shown = self.drawn()
        self.assertIsNone(shown.geometry.strip)
        self.assertIsNone(shown.line)
        # The job itself continues, with nothing canceled or sent.
        self.assertEqual(self.jobs.store.get(first.local_id).state, state_before)
        self.assertIn(first, self.runtime.state.jobs_view)
        self.assertEqual(self.jobs.cancel_calls, [])
        second = self.submit_image(progress=0.5)
        shown = self.drawn()
        self.assertEqual(shown.geometry.job.request_id, second.local_id)
        self.assertIn("+1 more", shown.line)
        # A file load forgets dismissals and drawn strips.
        self.composer.dismiss(shown.geometry.job.key, second.local_id)
        composer = submodule("blender.composer")
        composer._load_pre(None)
        self.assertEqual(
            (self.composer.dismissed, self.composer.drawn_strips, self.composer.offered),
            ({}, {}, {}),
        )
        self.assertEqual(len(self.jobs.paid), 2)

    def test_strip_follows_its_scene_and_lane_and_retires_with_the_connection(self):
        view = self.submit_image()
        self.assertIsNotNone(self.drawn().geometry.job)
        self.scene.scenario.lane = "video"
        self.assertIsNone(self.drawn().geometry.job)
        self.scene.scenario.lane = "image"
        other = bpy.data.scenes.new("Second composer scene")
        self.addCleanup(bpy.data.scenes.remove, other)
        other.scenario.lane = "image"
        self.context.scene = other
        self.assertIsNone(self.drawn().geometry.job)
        self.context.scene = self.scene
        self.assertEqual(self.drawn().geometry.job.request_id, view.local_id)
        # A credential change retires the job owner and its bindings.
        secret = self.jobs.prefs.api_secret
        self.jobs.prefs.api_secret = "different-fixture-secret"
        try:
            self.runtime.sync_catalog_context()
        finally:
            self.jobs.prefs.api_secret = secret
        self.assertIsNone(self.drawn().geometry.job)

    def test_uncertain_submission_offers_only_inspect(self):
        self.jobs.lose_response = True
        result = self.jobs.mcp_submit(self.jobs.mcp_quote())
        self.jobs.settle()
        shown = self.drawn()
        job = shown.geometry.job
        self.assertEqual(job.request_id, result["local_id"])
        self.assertIn("Submission unconfirmed; do not resubmit", shown.line)
        self.assertEqual(job.status.tone, "review")
        self.assertEqual([chip.key for chip in job.chips], ["inspect"])
        self.assertEqual(len(self.jobs.paid), 1)

    def test_failed_download_resume_chip_downloads_once_without_a_paid_request(self):
        self.jobs.result_fixture()
        self.jobs.download_error = True
        view = self.submit_image(progress=None, status="success")
        self.assertEqual(self.jobs.store.get(view.local_id).state.value, "download_failed")
        shown = self.drawn()
        # The paused delivery's own message replaces the state wording, in the review tone.
        self.assertIn(view.error, shown.line)
        self.assertEqual(shown.geometry.job.status.tone, "review")
        self.assertEqual(shown.chips[-2:], ["Resume download", "Inspect"])
        self.jobs.download_error = False
        # The real operator through its own invoke path: Resume download needs no dialog.
        self.press(self.chip_point("resume"), ops=bpy.ops)
        self.jobs.deliver_results()
        self.assertEqual(self.jobs.store.get(view.local_id).state.value, "ready")
        self.assertEqual(len(self.jobs.downloads), 1)
        self.assertEqual(len(self.jobs.paid), 1)

    def test_offline_jobs_say_so_in_the_strip(self):
        self.submit_image()
        with online_access(False):
            self.runtime.sync_catalog_context()
            shown = self.drawn()
        self.assertIn("(offline)", shown.line)

    def test_edit_mode_shows_the_edit_form_job_on_the_3d_tab(self):
        self.scene.scenario.lane = "3d"
        self.scene.scenario.three_d_mode = "EDIT"
        self.jobs.configure_ui_lane("edit3d")
        self.jobs.ui_quote("edit3d")
        view = self.generation.submit_generation(bpy.context, "edit3d")
        self.jobs.deliver_results()
        self.assertEqual(self.drawn().geometry.job.request_id, view.local_id)
        # The 3D tab's Text form is another form, with no job of its own.
        self.scene.scenario.three_d_mode = "TEXT"
        self.assertIsNone(self.drawn().geometry.job)
        self.scene.scenario.three_d_mode = "EDIT"
        self.assertEqual(self.drawn().geometry.job.request_id, view.local_id)
        self.assertEqual(len(self.jobs.paid), 1)

    def test_strip_card_and_studio_pages_share_one_view_object(self):
        view = self.submit_image()
        studio, recovery = submodule("blender.studio"), submodule("blender.job_recovery")
        page = bpy.context.window_manager.scenario_studio_view
        self.addCleanup(setattr, page, "page", page.page)
        owner = self.runtime.state.model_jobs
        geometry = self.draw.composer_geometry(self.context, self.composer)
        self.assertIs(owner.views[geometry.job.request_id], view)
        self.assertIs(self.job_card.find_view(view.local_id), view)
        with patch.object(recovery, "draw_controls") as controls:
            page.page = "JOBS"
            studio.draw_view(MagicMock(), bpy.context, width=960)
            self.job_card.draw_job(MagicMock(), view.local_id)
        drawn = [call.args[1] for call in controls.call_args_list]
        self.assertEqual(len(drawn), 2)
        self.assertTrue(all(item is view for item in drawn))

    # -- job card -------------------------------------------------------------------
    def test_job_card_draws_the_shared_view_read_only_and_handles_a_missing_job(self):
        view = self.submit_image()
        panels = submodule("blender.panels")
        self.assertIn(view, self.runtime.state.jobs_view)
        with (
            self.read_only(),
            patch.object(panels, "draw_active_job") as active,
            patch.object(panels, "draw_result") as result,
        ):
            layout = MagicMock()
            self.job_card.draw_job(layout, view.local_id)
            active.assert_called_once_with(layout, view)
            result.assert_not_called()
            # A finished job is an expanded result with its saved-result controls.
            view.status = "success"
            layout = MagicMock()
            self.job_card.draw_job(layout, view.local_id)
            result.assert_called_once_with(layout, view, collapsible=False)
            layout = MagicMock()
            self.job_card.draw_job(layout, "unknown-request")
        layout.label.assert_called_once_with(text=self.job_card.MISSING, icon="INFO")
        layout.operator.assert_called_once_with(
            "scenario.inspect_saved_jobs", text="Inspect saved jobs", icon="FILE_REFRESH"
        )

    def test_job_card_is_a_live_popup_bounded_by_the_area(self):
        studio = submodule("blender.studio")
        manager = SimpleNamespace(invoke_popup=MagicMock(return_value={"RUNNING_MODAL"}))
        context = SimpleNamespace(
            window_manager=manager,
            area=SimpleNamespace(width=400),
            window=SimpleNamespace(width=1200),
            preferences=SimpleNamespace(system=SimpleNamespace(ui_scale=1.0)),
        )
        operator = SimpleNamespace(request_id="fixture")
        cls = self.job_card.SCENARIO_OT_composer_job_card
        self.assertEqual(cls.invoke(operator, context, None), {"RUNNING_MODAL"})
        manager.invoke_popup.assert_called_once_with(operator, width=352)
        context.area.width = 2000
        cls.invoke(operator, context, None)
        self.assertEqual(manager.invoke_popup.call_args.kwargs["width"], self.job_card.CARD_WIDTH)

        class Owner:
            request_id = "fixture"
            layout = MagicMock()

        owner, region = Owner(), MagicMock()
        self.addCleanup(studio._popups.pop, owner, None)
        cls.draw(owner, SimpleNamespace(region_popup=region))
        self.assertIs(studio._popups[owner], region)
        studio.redraw_popups()
        region.tag_refresh_ui.assert_called_once_with()
        self.assertTrue(hasattr(bpy.ops.scenario, "composer_job_card"))
        properties = bpy.ops.scenario.composer_job_card.get_rna_type().properties["request_id"]
        self.assertTrue(properties.is_hidden)
        self.assertTrue(properties.is_skip_save)

    def test_card_result_ignores_the_sidebar_collapsed_flag(self):
        panels = submodule("blender.panels")
        records = submodule("core.jobs.records")
        rec = records.JobRecord("done", "model", "model", "fixture", {}, status="success")
        rec.meta["collapsed"] = True
        layout = MagicMock()
        panels.draw_result(layout, rec)
        header = layout.box.return_value.row.return_value
        header.operator.assert_any_call(
            "scenario.toggle_result", text="", icon="TRIA_RIGHT", emboss=False
        )
        layout = MagicMock()
        panels.draw_result(layout, rec, collapsible=False)
        box = layout.box.return_value
        names = [call.args[0] for call in box.row.return_value.operator.call_args_list]
        self.assertNotIn("scenario.toggle_result", names)
        self.assertIn("scenario.result_details", names)
        self.assertTrue(rec.meta["collapsed"])


class ComposerStripStateTests(unittest.TestCase):
    def setUp(self):
        self.state = submodule("blender.composer.state").ComposerState()

    def test_held_actions_cover_a_running_command_for_the_same_revision_only(self):
        offered = ("cancel-descriptor",)
        self.assertEqual(self.state.shown_actions("job", 3, offered, False), (offered, False))
        self.assertEqual(self.state.shown_actions("job", 3, (), True), (offered, True))
        self.assertEqual(self.state.shown_actions("job", 4, (), True), ((), False))
        # The poll that starts a command still lists what the job offered just before it: those
        # are held too, and kept until the command ends.
        listed = ("resume-descriptor",)
        self.assertEqual(self.state.shown_actions("job", 4, listed, True), (listed, True))
        self.assertEqual(self.state.shown_actions("job", 4, (), True), (listed, True))
        self.assertEqual(self.state.shown_actions("job", 3, (), True), ((), False))
        # A revision that offered nothing holds nothing.
        self.assertEqual(self.state.shown_actions("job", 5, (), False), ((), False))
        self.assertEqual(self.state.shown_actions("job", 5, (), True), ((), False))

    def test_display_caches_stay_bounded(self):
        state_mod = submodule("blender.composer.state")
        for index in range(state_mod.DRAWN_STRIP_LIMIT + 5):
            self.state.remember_strip(index, ("job", index, ()))
        self.assertEqual(len(self.state.drawn_strips), state_mod.DRAWN_STRIP_LIMIT)
        self.assertNotIn(0, self.state.drawn_strips)
        self.state.remember_strip(40, None)
        self.assertNotIn(40, self.state.drawn_strips)
        for index in range(state_mod.OFFERED_LIMIT + 5):
            self.state.shown_actions(f"job-{index}", 1, (), False)
        self.assertEqual(len(self.state.offered), state_mod.OFFERED_LIMIT)

    def test_dismissals_keep_only_the_newest_scene_lanes(self):
        # Per-shot scenes come and go in one session; their dismissals must not pile up.
        for index in range(200):
            self.state.dismiss((f"scene-{index}", "image"), f"job-{index}")
        self.assertLess(len(self.state.dismissed), 200)
        state_mod = submodule("blender.composer.state")
        self.assertEqual(len(self.state.dismissed), state_mod.DISMISSED_LIMIT)
        self.assertFalse(self.state.is_dismissed(("scene-0", "image"), "job-0"))
        self.assertTrue(self.state.is_dismissed(("scene-199", "image"), "job-199"))
        # Dismissing again in a scene lane makes it the newest entry.
        self.state.dismiss(("scene-150", "image"), "job-new")
        self.assertEqual(next(reversed(self.state.dismissed)), ("scene-150", "image"))
