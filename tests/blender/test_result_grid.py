# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Installed Results grid in Studio and the Generations panel; not physical input proof.

Session rows are synthetic and saved results come from the preview tile
fixture: private local bytes, an offline storage stub and no Scenario call.
Drawing is checked through a recording layout.
"""

import builtins
import io
import itertools
import os
import unittest
from collections import namedtuple
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import bpy
import test_result_preview_tiles
from helpers import online_access, submodule
from test_result_preview_tiles import MP4, png

CLAIMED = "2026-10-22T13:04:05.123Z"
CREATED = 1_800_000_000.0
# Studio's widest popup, and its narrow one at UI scale 2 (popup_width's cases).
WIDE, NARROW = 960, 352

Drawn = namedtuple("Drawn", "name args kwargs properties enabled alert")


class _Properties:
    def __init__(self, properties):
        object.__setattr__(self, "_values", properties)

    def __setattr__(self, name, value):
        self._values[name] = value


class Recorder:
    """Records every drawn call in order, nested layouts included.

    A row, column, box, split or grid flow is recorded where it is made and
    returns a layout that records into the same list. Each call records whether
    its layouts are enabled and in alert, as Blender's sublayouts inherit both,
    and an operator records the properties set on it.
    """

    CONTAINERS = ("row", "column", "box", "split", "grid_flow")

    def __init__(self, calls=None, parent=None):
        self.calls = [] if calls is None else calls
        self.parent = parent
        self.enabled, self.active, self.alert = True, True, False
        self.alignment, self.operator_context = "EXPAND", "INVOKE_DEFAULT"
        self.scale_x = self.scale_y = 1.0
        self.ui_units_x = self.ui_units_y = 0.0
        self.use_property_split, self.use_property_decorate = False, True

    def _chain(self):
        layout = self
        while layout is not None:
            yield layout
            layout = layout.parent

    def __getattr__(self, name):
        if name.startswith("_"):
            raise AttributeError(name)

        def record(*args, **kwargs):
            properties = {}
            chain = tuple(self._chain())
            enabled = all(layout.enabled for layout in chain)
            alert = any(layout.alert for layout in chain)
            self.calls.append(Drawn(name, args, kwargs, properties, enabled, alert))
            if name in self.CONTAINERS:
                return Recorder(self.calls, self)
            return _Properties(properties) if name.startswith("operator") else None

        return record


def named(calls, name, idname=None):
    return [c for c in calls if c.name == name and (idname is None or c.args[:1] == (idname,))]


def labels(calls):
    return [(c.kwargs.get("text", ""), c.kwargs.get("icon", "NONE")) for c in named(calls, "label")]


def fresh_views(test):
    """Results view at its defaults on Studio's Results page; both restored after ``test``."""
    manager = bpy.context.window_manager
    view, studio = manager.scenario_results_view, manager.scenario_studio_view
    for name in ("sidebar_layout", "studio_layout", "page", "result"):
        test.addCleanup(setattr, view, name, getattr(view, name))
    test.addCleanup(setattr, studio, "page", studio.page)
    scene = bpy.context.scene.scenario
    test.addCleanup(setattr, scene, "show_cloud_history", scene.show_cloud_history)
    view.sidebar_layout, view.studio_layout, view.page, view.result = "LIST", "GRID", 0, ""
    studio.page, scene.show_cloud_history = "RESULTS", False
    return view


class ResultGridTests(unittest.TestCase):
    """Synthetic session rows: the grid's pages, selection, toggle and draw cost."""

    def setUp(self):
        self.runtime = submodule("blender.runtime")
        self.grid = submodule("blender.result_grid")
        self.core = submodule("core.ui.result_grid")
        self.panels = submodule("blender.panels")
        self.studio = submodule("blender.studio")
        self.previews = submodule("blender.result_previews")
        self.recovery = submodule("blender.job_recovery")
        self.records = submodule("core.jobs.records")
        self.enterContext(patch.object(self.runtime, "state", self.runtime.RuntimeState()))
        self.previews.controller.retire()
        self.addCleanup(self.previews.controller.retire)
        self.view = fresh_views(self)
        self.controls = self.enterContext(patch.object(self.recovery, "draw_controls"))

    def rows(self, count, *, failed=(), shared=False, active=0):
        """``count`` finished image rows, newest first, after ``active`` running ones."""
        rows = [
            self.records.JobRecord(
                f"running-{index}", "image", "image", "fixture-model", {}, status="in-progress"
            )
            for index in range(active)
        ]
        for index in range(count):
            meta = {
                "prompt": f"Prompt {index}",
                "model_name": "Fixture Model",
                "result_sizes": {f"asset-{index}": 2_500_000},
            }
            if shared:
                meta.update(shared_job=True, saved_state="applied", saved_revision=1)
            rows.append(
                self.records.JobRecord(
                    local_id=f"job-{index}",
                    lane="image",
                    kind="image",
                    model_id="fixture-model",
                    body={},
                    job_id=f"remote-{index}",
                    status="failed" if index in failed else "success",
                    cu_cost=2.5,
                    asset_ids=[f"asset-{index}"],
                    error="Fixture failure" if index in failed else None,
                    created_at=CREATED,
                    meta=meta,
                )
            )
        self.runtime.state.jobs_view[:] = rows
        return [row for row in rows if row.is_terminal]

    def draw_studio(self, width=WIDE):
        layout = Recorder()
        with patch.object(
            self.runtime, "ensure_model_jobs", side_effect=AssertionError("Drawing started jobs")
        ):
            self.studio.draw_view(layout, bpy.context, width=width)
        return layout.calls

    def draw_grid(self, rows, surface="STUDIO"):
        """The grid's own drawing with file and job storage access refused."""
        layout = Recorder()
        refused = AssertionError("File or storage access while drawing")
        with (
            patch.object(builtins, "open", side_effect=refused),
            patch.object(io, "open", side_effect=refused),
            patch.object(os, "open", side_effect=refused),
            patch.object(os, "stat", side_effect=refused),
            patch.object(self.runtime, "ensure_job_store", side_effect=refused),
            patch.object(self.runtime, "ensure_model_jobs", side_effect=refused),
        ):
            self.grid.draw(layout, bpy.context, rows, surface)
        return layout.calls

    def tiles(self, calls):
        """Each tile's (local ID, icon value, icon scale) in drawn order."""
        icons = named(calls, "template_icon")
        buttons = named(calls, "operator", "scenario.show_result")
        self.assertEqual(len(icons), len(buttons))
        return [
            (button.properties["local_id"], icon.kwargs["icon_value"], icon.kwargs["scale"])
            for icon, button in zip(icons, buttons, strict=True)
        ]

    def pager(self, calls):
        """The grid pager's (direction, enabled) arrows and its range label."""
        arrows = [
            (c.properties["direction"], c.enabled)
            for c in named(calls, "operator", "scenario.page_results")
        ]
        ranges = [text for text, _ in labels(calls) if " of " in text]
        return arrows, ranges

    def page(self, direction):
        return bpy.ops.scenario.page_results(direction=direction)

    def show(self, local_id):
        return bpy.ops.scenario.show_result(local_id=local_id)

    def test_registration_keeps_each_layout_the_page_and_the_selection_unsaved(self):
        self.assertTrue(hasattr(bpy.ops.scenario, "show_result"))
        self.assertTrue(hasattr(bpy.ops.scenario, "page_results"))
        properties = self.view.bl_rna.properties
        for name in ("sidebar_layout", "studio_layout", "page", "result"):
            self.assertTrue(properties[name].is_skip_save, name)
        # The sidebar keeps its list; Studio's Results page opens on the grid.
        self.assertEqual(properties["sidebar_layout"].default, "LIST")
        self.assertEqual(properties["studio_layout"].default, "GRID")
        manager = bpy.types.WindowManager.bl_rna.properties["scenario_results_view"]
        self.assertTrue(manager.is_skip_save)
        self.assertEqual(self.grid.layout_of(bpy.context, "SIDEBAR"), "LIST")
        self.assertEqual(self.grid.layout_of(bpy.context, "STUDIO"), "GRID")

    def test_studio_results_open_on_a_page_of_tiles_without_storage_reads_or_writes(self):
        rows = self.rows(30, active=3)
        calls = self.draw_grid(rows)
        expected = [f"job-{index}" for index in range(12)]
        placeholder = self.previews.builtin_icon("IMAGE_DATA")
        self.assertEqual(
            [tile[:2] for tile in self.tiles(calls)], [(i, placeholder) for i in expected]
        )
        # Every tile names its prompt, which a list row's header shows too.
        texts = [c.kwargs["text"] for c in named(calls, "operator", "scenario.show_result")]
        self.assertEqual(texts, [f"Prompt {index}" for index in range(12)])
        self.assertEqual(self.pager(calls), ([("PREVIOUS", False), ("NEXT", True)], ["1-12 of 30"]))
        # Drawing changes neither the page nor the selection, and starts nothing.
        self.assertEqual((self.view.page, self.view.result), (0, ""))
        self.controls.assert_not_called()
        # Studio draws the same page under its List and Grid choice.
        calls = self.draw_studio()
        self.assertEqual([tile[0] for tile in self.tiles(calls)], expected)
        toggle = [c.args[1:] for c in named(calls, "prop_enum")]
        self.assertIn(("studio_layout", "LIST"), toggle)
        self.assertIn(("studio_layout", "GRID"), toggle)
        # The grid has no rows to collapse.
        self.assertFalse(named(calls, "operator", "scenario.collapse_results"))
        self.assertFalse(named(calls, "operator", "scenario.toggle_result"))

    def test_tile_columns_and_size_follow_the_popup_width(self):
        self.rows(14)
        for width in (WIDE, NARROW):
            with self.subTest(width=width):
                calls = self.draw_studio(width)
                columns, scale = self.core.tile_layout(width - self.grid.MARGIN["STUDIO"])
                (flow,) = named(calls, "grid_flow")
                self.assertEqual(flow.kwargs["columns"], columns)
                self.assertTrue(flow.kwargs["even_columns"])
                self.assertEqual({tile[2] for tile in self.tiles(calls)}, {scale})
        self.assertEqual(self.core.tile_layout(WIDE - 10)[0], 6)
        self.assertEqual(self.core.tile_layout(NARROW - 10)[0], 3)

    def test_paging_steps_through_results_and_stops_at_either_end(self):
        rows = self.rows(30)
        self.assertEqual(self.page("PREVIOUS"), {"CANCELLED"})
        self.assertEqual(self.page("NEXT"), {"FINISHED"})
        calls = self.draw_grid(rows)
        self.assertEqual(
            [tile[0] for tile in self.tiles(calls)], [f"job-{index}" for index in range(12, 24)]
        )
        self.assertEqual(self.pager(calls), ([("PREVIOUS", True), ("NEXT", True)], ["13-24 of 30"]))
        self.assertEqual(self.page("NEXT"), {"FINISHED"})
        calls = self.draw_grid(rows)
        # The last page is short rather than repeating results.
        self.assertEqual(
            [tile[0] for tile in self.tiles(calls)], [f"job-{index}" for index in range(24, 30)]
        )
        self.assertEqual(
            self.pager(calls), ([("PREVIOUS", True), ("NEXT", False)], ["25-30 of 30"])
        )
        self.assertEqual(self.page("NEXT"), {"CANCELLED"})
        self.assertEqual(self.view.page, 2)
        self.assertEqual(self.page("PREVIOUS"), {"FINISHED"})
        self.assertEqual(self.page("PREVIOUS"), {"FINISHED"})
        self.assertEqual(self.view.page, 0)
        with self.assertRaises(TypeError):
            self.page("LAST")  # Only the previous or next page.

    def test_one_page_of_results_draws_no_pager(self):
        rows = self.rows(12)
        calls = self.draw_grid(rows)
        self.assertEqual(len(self.tiles(calls)), 12)
        self.assertEqual(self.pager(calls), ([], []))
        self.assertEqual(self.page("NEXT"), {"CANCELLED"})

    def test_a_page_beyond_the_results_draws_the_last_one_without_writing_it(self):
        rows = self.rows(14)
        # Fewer results than when the page was chosen, as after a connection change.
        self.view.page = 7
        calls = self.draw_grid(rows)
        self.assertEqual([tile[0] for tile in self.tiles(calls)], ["job-12", "job-13"])
        self.assertEqual(self.pager(calls)[1], ["13-14 of 14"])
        self.assertEqual(self.view.page, 7)
        # The pager steps from the page drawn.
        self.assertEqual(self.page("PREVIOUS"), {"FINISHED"})
        self.assertEqual(self.view.page, 0)

    def test_a_short_page_keeps_its_tiles_as_wide_as_a_full_row(self):
        for count, page in ((12, 0), (13, 1)):
            with self.subTest(count=count):
                rows = self.rows(count)
                self.view.page = page
                calls = self.draw_grid(rows)
                (flow,) = named(calls, "grid_flow")
                columns = flow.kwargs["columns"]
                cells = calls[calls.index(flow) + 1 :]
                tiles = len(self.tiles(calls))
                # Blender spreads fewer cells than columns across the row: blank ones fill it.
                self.assertEqual(len(named(cells, "column")), max(columns, tiles))
                self.assertEqual(labels(cells), [("", "NONE")] * max(0, columns - tiles))
        self.assertEqual(tiles, 1)

    def test_choosing_a_tile_shows_it_large_with_its_facts_and_its_row_actions(self):
        rows = self.rows(30)
        self.assertEqual(self.show("job-14"), {"FINISHED"})
        # The grid returns to the page holding it.
        self.assertEqual((self.view.result, self.view.page), ("job-14", 1))
        calls = self.draw_studio()
        navigation = [
            (c.kwargs["text"], c.kwargs["icon"], c.properties["local_id"], c.enabled)
            for c in named(calls, "operator", "scenario.show_result")
        ]
        self.assertEqual(
            navigation,
            [
                ("", "TRIA_LEFT", "job-13", True),
                ("All results", "IMGDISPLAY", "", True),
                ("", "TRIA_RIGHT", "job-15", True),
            ],
        )
        row = rows[14]
        facts = [
            (text, icon)
            for text, icon in labels(calls)
            if icon in ("TEXT", "NODE_MATERIAL", "IMAGE_DATA", "TIME", "INFO")
        ]
        self.assertEqual(
            facts,
            [
                ("Prompt 14", "TEXT"),
                ("Fixture Model", "NODE_MATERIAL"),
                ("Image, 2.4 MiB", "IMAGE_DATA"),
                (f"Submitted {self.core.submitted_label(None, CREATED)}", "TIME"),
                (self.panels.result_cost_label(row), "INFO"),
            ],
        )
        # The same model row and actions a list row draws: Details and the saved-job controls.
        details = named(calls, "operator", "scenario.result_details")
        self.assertEqual([c.properties["local_id"] for c in details], ["job-14"])
        self.assertEqual(len(self.controls.call_args_list), 1)
        self.assertIs(self.controls.call_args.args[1], row)
        # No preview yet: no large placeholder, no pager and no other tile.
        self.assertFalse(named(calls, "template_icon"))
        self.assertFalse(named(calls, "operator", "scenario.page_results"))
        self.assertFalse(named(calls, "grid_flow"))

    def test_a_job_without_a_saved_model_name_shows_the_catalog_name(self):
        # A saved job listed after a restart keeps only its model ID.
        (row,) = self.rows(1, shared=True, active=1)
        running = self.runtime.state.jobs_view[0]
        del row.meta["model_name"]
        self.runtime.state.records["fixture-model"] = SimpleNamespace(name="Catalog Model")
        self.assertEqual(self.show("job-0"), {"FINISHED"})
        active = Recorder()
        self.panels.draw_active_job(active, running)
        for surface, calls in (("large view", self.draw_studio()), ("Jobs", active.calls)):
            with self.subTest(surface=surface):
                texts = [text for text, _icon in labels(calls)]
                self.assertTrue(any("Catalog Model" in text for text in texts), texts)
                self.assertFalse(any("fixture-model" in text for text in texts), texts)
        # A model the catalog does not list keeps its ID.
        del self.runtime.state.records["fixture-model"]
        self.assertIn(("fixture-model", "NODE_MATERIAL"), labels(self.draw_studio()))

    def test_neighbors_stop_at_either_end_and_all_results_returns_to_its_page(self):
        rows = self.rows(30)
        self.assertEqual(self.show("job-0"), {"FINISHED"})
        calls = self.draw_studio()
        arrows = [
            (c.kwargs["icon"], c.enabled)
            for c in named(calls, "operator", "scenario.show_result")
            if not c.kwargs["text"]
        ]
        self.assertEqual(arrows, [("TRIA_LEFT", False), ("TRIA_RIGHT", True)])
        self.assertEqual(self.show("job-29"), {"FINISHED"})
        calls = self.draw_studio()
        arrows = [
            (c.kwargs["icon"], c.enabled)
            for c in named(calls, "operator", "scenario.show_result")
            if not c.kwargs["text"]
        ]
        self.assertEqual(arrows, [("TRIA_LEFT", True), ("TRIA_RIGHT", False)])
        self.assertEqual(self.view.page, 2)
        self.assertEqual(self.show(""), {"FINISHED"})
        self.assertEqual((self.view.result, self.view.page), ("", 2))
        calls = self.draw_grid(rows)
        self.assertEqual(
            [tile[0] for tile in self.tiles(calls)], [f"job-{index}" for index in range(24, 30)]
        )

    def test_a_result_no_longer_listed_is_refused_and_a_stale_selection_draws_the_grid(self):
        rows = self.rows(14)
        self.assertEqual(self.show("gone"), {"CANCELLED"})
        self.assertEqual(self.view.result, "")
        self.assertEqual(self.show("job-3"), {"FINISHED"})
        # The selected row leaves the list, as when saved jobs are inspected again.
        remaining = [row for row in rows if row.local_id != "job-3"]
        self.runtime.state.jobs_view[:] = remaining
        calls = self.draw_grid(remaining)
        self.assertEqual(len(self.tiles(calls)), 12)
        self.assertEqual(self.view.result, "job-3")
        self.controls.assert_not_called()

    def test_failed_results_draw_an_alert_tile_and_their_failure_large(self):
        rows = self.rows(4, failed=(1,))
        calls = self.draw_grid(rows)
        error, image = self.previews.builtin_icon("ERROR"), self.previews.builtin_icon("IMAGE_DATA")
        self.assertEqual(
            [tile[:2] for tile in self.tiles(calls)],
            [("job-0", image), ("job-1", error), ("job-2", image), ("job-3", image)],
        )
        alerts = [c.alert for c in named(calls, "operator", "scenario.show_result")]
        self.assertEqual(alerts, [False, True, False, False])
        self.assertEqual(self.show("job-1"), {"FINISHED"})
        calls = self.draw_studio()
        drawn = labels(calls)
        self.assertIn(("Image, 2.4 MiB", "ERROR"), drawn)
        self.assertIn(("Failed: Fixture failure", "ERROR"), drawn)

    def test_the_sidebar_keeps_its_list_until_grid_is_chosen(self):
        self.rows(14)
        self.assertEqual(self.view.sidebar_layout, "LIST")
        layout = Recorder()
        with patch.object(self.panels, "draw_result", wraps=self.panels.draw_result) as rows:
            self.panels.SCENARIO_PT_generations.draw(SimpleNamespace(layout=layout), bpy.context)
        # The first twelve rows, as before, and the rows' collapse control.
        self.assertEqual(
            [call.args[1].local_id for call in rows.call_args_list],
            [f"job-{index}" for index in range(12)],
        )
        self.assertTrue(named(layout.calls, "operator", "scenario.collapse_results"))
        self.assertFalse(named(layout.calls, "operator", "scenario.show_result"))
        toggle = [c.args[1:] for c in named(layout.calls, "prop_enum")]
        self.assertEqual(toggle, [("sidebar_layout", "LIST"), ("sidebar_layout", "GRID")])
        self.view.sidebar_layout = "GRID"
        layout = Recorder()
        with patch.object(self.panels, "draw_result", wraps=self.panels.draw_result) as rows:
            self.panels.SCENARIO_PT_generations.draw(SimpleNamespace(layout=layout), bpy.context)
        rows.assert_not_called()
        self.assertEqual(len(named(layout.calls, "operator", "scenario.show_result")), 12)
        self.assertFalse(named(layout.calls, "operator", "scenario.collapse_results"))
        # Studio keeps its own choice.
        self.view.studio_layout = "LIST"
        calls = self.draw_studio()
        self.assertFalse(named(calls, "operator", "scenario.show_result"))
        self.assertEqual(len(named(calls, "operator", "scenario.toggle_result")), 12)

    def test_cloud_history_leaves_out_every_session_result_the_grid_pages_through(self):
        rows = self.rows(14, shared=True)
        bpy.context.scene.scenario.show_cloud_history = True
        for layout_name, shown in (("LIST", rows[:12]), ("GRID", rows)):
            with self.subTest(layout=layout_name):
                self.view.sidebar_layout = layout_name
                with patch.object(self.panels, "draw_history") as history:
                    self.panels.SCENARIO_PT_generations.draw(
                        SimpleNamespace(layout=MagicMock()), bpy.context
                    )
                self.assertEqual(history.call_args.args[2], {row.job_id for row in shown})

    def test_previews_follow_the_rows_each_surface_draws(self):
        self.rows(40, shared=True, active=2)
        controller = self.previews.controller

        def shown():
            return {view.local_id for view in controller._shown()}

        def jobs(first, last):
            return {f"job-{index}" for index in range(first, last)}

        # The sidebar's list and the grid's first page draw the same twelve.
        self.assertEqual(shown(), jobs(0, 12))
        self.view.page = 2
        self.assertEqual(shown(), jobs(0, 12) | jobs(24, 36))
        self.view.result = "job-39"
        self.assertEqual(shown(), jobs(0, 12) | jobs(24, 36) | {"job-39"})
        self.view.sidebar_layout = "GRID"
        self.assertEqual(shown(), jobs(24, 36) | {"job-39"})
        # Lists on both surfaces: the first twelve only, whatever was chosen in the grid.
        self.view.sidebar_layout = self.view.studio_layout = "LIST"
        self.assertEqual(shown(), jobs(0, 12))
        # A page beyond the results previews the last page that exists.
        self.view.studio_layout, self.view.result, self.view.page = "GRID", "", 9
        self.assertEqual(shown(), jobs(0, 12) | jobs(36, 40))

    def test_many_results_draw_one_page_and_preview_at_most_two_pages(self):
        rows = self.rows(1000, shared=True)
        self.view.page = 40
        with (
            patch.object(self.previews, "cover", wraps=self.previews.cover) as covers,
            patch.object(self.panels, "_short_prompt", wraps=self.panels._short_prompt) as titles,
        ):
            calls = self.draw_grid(rows)
        self.assertEqual(
            [tile[0] for tile in self.tiles(calls)], [f"job-{index}" for index in range(480, 492)]
        )
        self.assertEqual(self.pager(calls)[1], ["481-492 of 1000"])
        # Drawing reads one page of rows, never every result.
        self.assertEqual(covers.call_count, 12)
        self.assertEqual(titles.call_count, 12)
        self.view.result = "job-999"
        self.assertEqual(len(self.previews.controller._shown()), 25)


class ResultGridPreviewTests(unittest.TestCase):
    """Saved results with real previews: covers, the large view and its paged tiles."""

    def setUp(self):
        self.fixture = fixture = test_result_preview_tiles.ResultPreviewTileTests()
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        self.runtime, self.tiles = fixture.runtime, fixture.tiles
        self.grid = submodule("blender.result_grid")
        self.core = submodule("core.ui.result_grid")
        self.studio = submodule("blender.studio")
        self.recovery = submodule("blender.job_recovery")
        self.view = fresh_views(self)
        # Background Blender assigns no icon IDs; give each preview a distinct
        # stand-in so a drawn icon still names the tile it came from.
        controller = self.tiles.controller
        make, stand_ins = controller._icon, itertools.count(100_000)

        def icon(key, size, pixels):
            controller._icons[key] = make(key, size, pixels) or next(stand_ins)
            return controller._icons[key]

        self.enterContext(patch.object(controller, "_icon", side_effect=icon))

    def applied(self, assets=None, *, settled=None):
        """A saved job taken on to APPLIED, as Generations lists it; its projected view.

        Its submission saves ``CLAIMED``. ``assets`` saves those results;
        without them it saves the preview fixture's six material maps.
        """
        m = self.fixture.storemod
        store = self.runtime.ensure_job_store()
        transition = store.transition

        def onwards(request_id, **kwargs):
            if kwargs["state"] == m.JobState.SUBMITTING:
                kwargs["claimed_at"] = CLAIMED
            current = transition(request_id, **kwargs)
            if kwargs["state"] == m.JobState.READY:
                for state in (m.JobState.APPLYING, m.JobState.APPLIED):
                    current = transition(
                        request_id, expected_revision=current.revision, state=state
                    )
            return current

        with patch.object(store, "transition", side_effect=onwards):
            if assets is None:
                return self.fixture.six_maps(settled)
            return self.fixture.saved(assets)

    def draw_studio(self):
        """Studio's Results page with job storage reads refused.

        Returns the drawn calls and the views whose saved-job controls were drawn.
        """
        layout = Recorder()
        store = self.runtime.state.job_store
        refused = AssertionError("Store read in draw")
        controls = self.recovery.draw_controls
        with (
            patch.object(store, "get", side_effect=refused),
            patch.object(store, "records", side_effect=refused),
            patch.object(self.recovery, "draw_controls", wraps=controls) as drawn,
        ):
            self.studio.draw_view(layout, bpy.context, width=WIDE)
        return layout.calls, [call.args[1] for call in drawn.call_args_list]

    def icons(self, calls):
        return [(c.kwargs["icon_value"], c.kwargs["scale"]) for c in named(calls, "template_icon")]

    def test_a_saved_image_fills_its_tile_and_its_large_view(self):
        data = png(640, 320)
        with online_access(False):
            view = self.applied([("image", "result.png", "image/png", data)])
            self.fixture.settle(lambda: self.fixture.status() == "ready")
        self.assertTrue(view.is_terminal)
        # The view carries the saved size and submission time; drawing reads no storage.
        self.assertEqual(view.meta["result_sizes"], {"image": len(data)})
        self.assertEqual(view.meta["claimed_at"], CLAIMED)
        tile = self.fixture.tile()
        self.assertEqual(self.tiles.controller.covers["request"], tile)
        calls, controls = self.draw_studio()
        _, scale = self.core.tile_layout(WIDE - self.grid.MARGIN["STUDIO"])
        self.assertEqual(self.icons(calls), [(tile.icon_id, scale)])
        # A tile offers no actions of its own: they wait in the large view.
        self.assertEqual(controls, [])
        (button,) = named(calls, "operator", "scenario.show_result")
        self.assertEqual(button.properties, {"local_id": "request"})
        self.assertEqual(bpy.ops.scenario.show_result(local_id="request"), {"FINISHED"})
        calls, controls = self.draw_studio()
        # One large preview: the row's own single tile is left out.
        large = self.core.detail_scale(WIDE - self.grid.MARGIN["STUDIO"] - self.grid.BOX_MARGIN)
        self.assertEqual(self.icons(calls), [(tile.icon_id, large)])
        self.assertEqual(large, self.core.DETAIL_MAX_SCALE)
        drawn = labels(calls)
        self.assertIn((self.core.summary("image", len(data), 1), "IMAGE_DATA"), drawn)
        self.assertIn((f"Submitted {self.core.submitted_label(CLAIMED)}", "TIME"), drawn)
        # The store keeps no prompt: no prompt line, and the model is named.
        self.assertNotIn("TEXT", [icon for _, icon in drawn])
        name = submodule("blender.panels").result_model_name(view)
        self.assertIn((name, "NODE_MATERIAL"), drawn)
        # The saved-job controls a list row draws, for the same view.
        self.assertEqual(len(controls), 1)
        self.assertIs(controls[0], view)
        self.assertEqual(self.fixture.requests, [])

    def test_a_paged_material_keeps_its_base_color_on_the_tile_and_large(self):
        with online_access(False):
            view = self.applied()
            controller = self.tiles.controller
            albedo = controller.covers["request"]
            self.assertEqual((albedo.caption, albedo.status), ("Albedo (3)", "ready"))
            self.assertEqual(self.fixture.page("NEXT"), {"FINISHED"})
            self.fixture.settle(self.fixture.ready_page)
            self.assertEqual(
                self.fixture.captions(), ["Height (2)", "Metallic (4)", "AO (5)", "Edge (6)"]
            )
            # The grid's tile keeps the first ranked result while the row shows others.
            self.assertEqual(controller.covers["request"], albedo)
            calls, _ = self.draw_studio()
            self.assertEqual([icon for icon, _ in self.icons(calls)], [albedo.icon_id])
            self.assertEqual(bpy.ops.scenario.show_result(local_id="request"), {"FINISHED"})
            before = (dict(controller.tiles), dict(controller.covers), dict(controller.pages))
            calls, controls = self.draw_studio()
            after = (dict(controller.tiles), dict(controller.covers), dict(controller.pages))
        self.assertEqual(before, after)
        icons = [icon for icon, _ in self.icons(calls)]
        # The large base color, then the row's own page of four with its pager.
        self.assertEqual(icons[0], albedo.icon_id)
        self.assertEqual(len(icons), 5)
        arrows = named(calls, "operator", "scenario.page_result_previews")
        self.assertEqual([c.properties["direction"] for c in arrows], ["PREVIOUS", "NEXT"])
        drawn = labels(calls)
        self.assertIn(("3-6 of 6", "NONE"), drawn)
        size = len(png(8, 8))
        # Saved without a lane, the job is the material its saved map roles establish.
        self.assertIn((self.core.summary("material", size, 6), "MATERIAL"), drawn)
        self.assertEqual(len(controls), 1)
        self.assertIs(controls[0], view)

    def test_a_video_waiting_offline_shows_its_kind_icon_and_status_large(self):
        with online_access(False):
            self.applied([("clip", "clip.mp4", "video/mp4", MP4)])
            self.fixture.settle(lambda: self.fixture.status() == "offline")
            cover = self.tiles.controller.covers["request"]
            self.assertEqual((cover.status, cover.icon_id), ("offline", 0))
            film = self.tiles.builtin_icon("FILE_MOVIE")
            calls, _ = self.draw_studio()
            self.assertEqual([icon for icon, _ in self.icons(calls)], [film])
            self.assertEqual(bpy.ops.scenario.show_result(local_id="request"), {"FINISHED"})
            calls, _ = self.draw_studio()
        # The kind's icon at preview size, then the row's status line, never a decode.
        self.assertEqual([icon for icon, _ in self.icons(calls)], [film])
        texts = " ".join(text for text, _ in labels(calls))
        self.assertIn("Preview paused while online access is disabled", texts)
        self.assertIn((self.core.summary("video", len(MP4), 1), "FILE_MOVIE"), labels(calls))
        self.assertEqual(self.fixture.requests, [])
        self.assertEqual(self.fixture.downloads, [])
