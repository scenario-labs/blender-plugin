# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
import json
import types
import unittest
from ctypes import c_float
from unittest.mock import Mock, patch

import bpy
from helpers import FIXTURES, isolated_manager, reset_scene, submodule, temp_credentials

UNAVAILABLE = "Scenario request failed (HTTP 503)"
FAILED_MESSAGE = f"Could not load this model: {UNAVAILABLE}"
NOT_LOADED = ("The model description is not loaded", "INFO")
LOADING = ("Loading the model description...", "TIME")


def fixture_record(name):
    data = json.loads((FIXTURES / "models" / f"{name}.json").read_text())["model"]
    return submodule("core.api.catalog").ModelRecord.from_api(data)


class RecordingLayout:
    """Record labels and operator properties a draw function sets, at any depth."""

    def __init__(self, log=None):
        self.log = [] if log is None else log

    def __getattr__(self, name):
        if name.startswith("__"):
            raise AttributeError(name)

        def call(*args, **kwargs):
            if name in ("row", "column", "box", "split", "grid_flow"):
                return RecordingLayout(self.log)
            entry = types.SimpleNamespace(name=name, args=args, kwargs=kwargs)
            self.log.append(entry)
            return entry  # operator properties are assigned on the recorded entry

        return call

    def labels(self):
        return [(e.kwargs.get("text"), e.kwargs.get("icon")) for e in self.log if e.name == "label"]

    def retries(self):
        return [
            e.lane for e in self.log if e.name == "operator" and e.args == ("scenario.retry_model",)
        ]


class GenerationTests(unittest.TestCase):
    def setUp(self):
        reset_scene()
        self.generation = submodule("blender.generation")
        self.runtime = submodule("blender.runtime")
        self.catalog = submodule("core.api.catalog")
        self.handlers = submodule("blender.handlers")
        self.runtime.state.reset()
        self.enterContext(isolated_manager())
        patina = json.loads((FIXTURES / "models" / "model_patina-material.json").read_text())[
            "model"
        ]
        gemini = json.loads(
            (FIXTURES / "models" / "model_google-gemini-3-1-flash.json").read_text()
        )["model"]
        records = [
            self.catalog.ModelRecord.from_api(patina),
            self.catalog.ModelRecord.from_api(gemini),
        ]
        self.handlers.dispatch(
            ("catalog", {"privacy": "public", "records": records, "detailed": records})
        )

    def test_catalog_event_fills_lane_enums_and_syncs_params(self):
        items = self.runtime.enum_items(("models", "image"))
        ids = [i[0] for i in items]
        self.assertEqual(ids[0], "model_google-gemini-3-1-flash")
        self.assertIn("model_patina-material", ids)
        self.assertEqual(
            [i[0] for i in self.runtime.enum_items(("models", "material"))],
            ["model_patina-material"],
        )
        lane = bpy.context.scene.scenario.lane_state("image")
        self.assertEqual(lane.model_id, "model_google-gemini-3-1-flash")
        self.assertIn("resolution", [p.name for p in lane.params])

    def test_progressive_schema_warmup_preserves_visible_estimate(self):
        lane = bpy.context.scene.scenario.lane_state("image")
        record = self.runtime.state.records[lane.model_id]
        lane.estimate_key, lane.estimate_state = "selected-quote", "READY"
        lane.estimate_cu = 13.25
        self.handlers.dispatch(
            ("models", {"detailed": [record], "failed": {}, "mark_dirty": False})
        )
        self.assertEqual(lane.estimate_key, "selected-quote")
        self.assertEqual(lane.estimate_state, "READY")
        self.assertAlmostEqual(lane.estimate_cu, 13.25)
        self.assertIn("resolution", [p.name for p in lane.params])

    def test_provisional_catalog_preserves_3d_quotes_without_bulk_schema_reads(self):
        models = [
            {"id": "first-image-3d", "name": "A first image model", "capabilities": ["img23d"]},
            {"id": "selected-text-3d", "name": "Z selected text model", "capabilities": ["txt23d"]},
            {"id": "other-text-3d", "capabilities": ["txt23d"]},
            {"id": "model_meshy-7-retexture", "capabilities": ["3d23d"]},
            {"id": "model_rodin-hyper3d-bang", "capabilities": ["3d23d"]},
        ]
        records = [self.catalog.ModelRecord.from_api(model) for model in models]
        detailed = [
            self.catalog.ModelRecord.from_api(
                {**model, "inputs": [{"name": "prompt", "type": "string"}]}
            )
            for model in models
        ]
        self.handlers.dispatch(("catalog", {"records": records, "detailed": detailed}))
        selected = bpy.context.scene.scenario.lane_state("3d")
        selected.model_id = "selected-text-3d"
        self.assertEqual(selected.model_key, "selected-text-3d")
        # A quote belongs to the already synchronized form. Simulate losing the
        # in-memory schema cache while preserving that unchanged form.
        for record in records:
            self.runtime.state.records[record.id] = record
            self.generation._schemas.pop(record.id, None)
        lanes = [bpy.context.scene.scenario.lane_state(lane) for lane in ("3d", "edit3d")]
        for lane in lanes:
            lane.estimate_key, lane.estimate_state = "existing-quote", "READY"
        context = Mock()
        context.load_cached.return_value = None
        manager = self.runtime.state.manager
        with (
            patch.object(self.runtime, "ensure_catalog", return_value=context),
            patch.object(self.runtime, "online", return_value=True),
            patch.object(manager, "fetch_models") as fetch,
            patch.object(self.generation, "request_models") as bulk,
        ):
            self.handlers.dispatch(
                ("catalog", {"records": records, "detailed": [], "warmup": True})
            )
            bulk.assert_not_called()
            for lane in lanes:
                self.assertEqual(lane.estimate_state, "READY")
                self.assertEqual(lane.estimate_key, "existing-quote")
            # The selected schema is still independently requested, with the
            # original background intent; the unselected defaults wait for warmup.
            self.assertEqual(fetch.call_count, 2)
            self.assertEqual(
                {call.args[1][0] for call in fetch.call_args_list},
                {lane.model_id for lane in lanes},
            )
            self.assertTrue(
                all(call.kwargs == {"mark_dirty": False} for call in fetch.call_args_list)
            )
        self.handlers.dispatch(
            ("models", {"detailed": detailed, "failed": {}, "mark_dirty": False})
        )
        self.handlers.dispatch(("catalog", {"records": records, "detailed": detailed}))
        for lane in lanes:
            self.assertEqual(lane.estimate_state, "READY")
            self.assertEqual(lane.estimate_key, "existing-quote")
        # Explicit mode/task callbacks keep invalidating their existing quotes.
        bpy.context.scene.scenario.three_d_mode = "TEXT"
        bpy.context.scene.scenario.edit3d_task = "RETEXTURE"
        for lane in lanes:
            self.assertEqual(lane.estimate_state, "PENDING")
            self.assertEqual(lane.estimate_key, "")

    def test_explicit_selection_invalidates_quote_while_background_schema_is_pending(self):
        self.check_pending_selection_rearms_quote(retry=False)

    def test_failed_schema_preserves_pending_selection_until_background_retry_succeeds(self):
        self.check_pending_selection_rearms_quote(retry=True)

    def test_failed_schema_retry_does_not_reprice_a_different_selected_model(self):
        self.check_pending_selection_rearms_quote(retry=True, switch_away=True)

    def check_pending_selection_rearms_quote(self, *, retry, switch_away=False):
        lane = bpy.context.scene.scenario.lane_state("image")
        model_id = "model_patina-material"
        detailed = self.runtime.state.records[model_id]
        self.runtime.state.records[model_id] = self.catalog.ModelRecord.from_api(
            {"id": model_id, "capabilities": ["txt2img"]}
        )
        self.generation._schemas.pop(model_id, None)
        context = Mock()
        context.load_cached.return_value = None
        manager = self.runtime.state.manager
        with (
            patch.object(self.runtime, "ensure_catalog", return_value=context),
            patch.object(self.runtime, "online", return_value=True),
            patch.object(manager, "fetch_models") as fetch,
        ):
            self.generation.request_model(model_id, mark_dirty=False)
            lane.estimate_key, lane.estimate_state = "previous-model-quote", "READY"
            lane.model_id = model_id
            self.assertEqual(lane.estimate_state, "PENDING")
            self.assertEqual(lane.estimate_key, "")
            fetch.assert_called_once_with(context, [model_id], mark_dirty=False)
            self.generation.request_estimate(bpy.context.scene, "image")
            self.assertEqual(lane.estimate_state, "UNAVAILABLE")
            self.assertEqual(lane.estimate_error, "Model not loaded yet")
            lane.estimate_dirty_at = 0.0
            if retry:
                self.handlers.dispatch(
                    (
                        "models",
                        {
                            "detailed": [],
                            "failed": {model_id: "Temporary outage"},
                            "mark_dirty": False,
                        },
                    )
                )
                self.assertEqual(lane.estimate_state, "UNAVAILABLE")
                self.generation.request_model(model_id, mark_dirty=False)
                self.assertEqual(fetch.call_count, 2)
                self.assertEqual(fetch.call_args.kwargs, {"mark_dirty": False})
        if switch_away:
            lane.model_id = "model_google-gemini-3-1-flash"
            lane.estimate_key, lane.estimate_state = "current-model-quote", "READY"
        self.handlers.dispatch(
            ("models", {"detailed": [detailed], "failed": {}, "mark_dirty": False})
        )
        if switch_away:
            self.assertEqual(lane.estimate_state, "READY")
            self.assertEqual(lane.estimate_key, "current-model-quote")
        else:
            self.assertEqual(lane.estimate_state, "PENDING")
            self.assertEqual(lane.estimate_key, "")
            self.assertGreater(lane.estimate_dirty_at, 0.0)
        self.assertIsNotNone(self.generation.schema_for(model_id))

    def test_enum_param_choices_survive_a_cache_miss(self):
        # after a .blend reload the params persist but the in-memory enum cache is empty; the dropdown must rebuild
        # its choices from the schema instead of showing "Loading..." forever (the Minimax H3 Resolution bug)
        props = submodule("blender.props")
        lane = bpy.context.scene.scenario.lane_state("image")
        schema = self.generation.schema_for(lane.model_id)
        enum_spec = next(
            s
            for s in schema.specs
            if s.allowed_values and s.ptype != "string_array" and not s.is_file
        )
        item = lane.params[lane.params.find(enum_spec.name)]
        self.runtime.state.enum_cache.clear()  # simulate the reloaded-file state
        ids = [i[0] for i in props._param_items(item, bpy.context)]
        self.assertNotEqual(ids, ["NONE"])  # not the "Loading..." fallback
        self.assertEqual(ids, [str(v) for v in enum_spec.allowed_values if str(v) != ""])

    def test_estimate_event_updates_lane_state(self):
        self.runtime.state.catalog = Mock()
        self.enterContext(patch.object(self.runtime, "sync_catalog_context"))
        lane = bpy.context.scene.scenario.lane_state("image")
        lane.estimate_key = "image:k1"
        lane.estimate_state = "PENDING"
        est = submodule("core.jobs.manager").EstimateResult(
            key="image:k1", cu_cost=13.25, catalog=self.runtime.state.catalog, quote=object()
        )
        self.runtime.state.estimate_origins[est.key] = (bpy.context.scene, "image")
        self.handlers.dispatch(("estimate", est))
        self.assertEqual(lane.estimate_state, "READY")
        self.assertAlmostEqual(lane.estimate_cu, 13.25)
        bad = submodule("core.jobs.manager").EstimateResult(
            key="image:k1", error="Input prompt is required", catalog=self.runtime.state.catalog
        )
        self.runtime.state.estimate_origins[bad.key] = (bpy.context.scene, "image")
        self.handlers.dispatch(("estimate", bad))
        self.assertEqual(lane.estimate_state, "ERROR")
        self.assertIn("prompt", lane.estimate_error)

    def test_build_request_from_scene_state(self):
        lane = bpy.context.scene.scenario.lane_state("image")
        lane.prompt = "a copper teapot"
        lane.params["resolution"].enum_value = "2K"
        ref = lane.references.add()
        ref.param_name, ref.source, ref.filepath = (
            "referenceImages",
            "FILE",
            str(FIXTURES / "patina-copper-512" / "albedo.png"),
        )
        request = self.generation.build_request(bpy.context.scene, "image")
        self.assertEqual(request.model_id, "model_google-gemini-3-1-flash")
        self.assertEqual(request.body["prompt"], "a copper teapot")
        self.assertEqual(request.body["resolution"], "2K")
        self.assertEqual(
            request.files["referenceImages"], [str(FIXTURES / "patina-copper-512" / "albedo.png")]
        )
        self.assertIn("referenceImages", request.array_params)
        self.assertEqual(request.errors, [])

    def test_unbound_job_done_events_cannot_apply_prototype_results(self):
        records = submodule("core.jobs.records")
        images = tuple(bpy.data.images)
        objects = tuple(bpy.data.objects)
        for kind, module, callback in (
            ("image", "apply_image", "on_image_result"),
            ("material", "apply_material", "on_material_result"),
            ("3d", "apply_3d", "on_3d_result"),
            ("video", "apply_video", "on_video_result"),
            ("audio", "apply_audio", "on_audio_result"),
        ):
            rec = records.JobRecord.new(lane=kind, kind=kind, model_id="model_x", body={})
            rec.job_id, rec.status = "job_done_" + kind, "success"
            rec.files = [str(FIXTURES / "patina-copper-512" / "albedo.png")]
            with (
                self.subTest(kind=kind),
                patch.object(submodule("blender." + module), callback) as apply,
                patch.object(submodule("blender.render_lanes"), "on_result") as render,
            ):
                self.handlers.dispatch(("job_done", rec))
                apply.assert_not_called()
                render.assert_not_called()
                self.assertEqual(tuple(bpy.data.images), images)
                self.assertEqual(tuple(bpy.data.objects), objects)
                self.assertIn(rec, self.runtime.state.jobs_view)
                self.assertIn("was not applied", self.runtime.state.last_message)

    def test_estimate_dirty_timestamp_fits_a_float_property(self):
        props = submodule("blender.props")
        lane = bpy.context.scene.scenario.lane_state("image")
        before = props.clock()
        props.mark_estimate_dirty(lane)
        after = props.clock()
        self.assertLess(
            lane.estimate_dirty_at, 1e6
        )  # relative clock, not an epoch (FloatProperty is 32-bit)
        # Blender stores this property as float32, which can round upward.
        self.assertGreaterEqual(lane.estimate_dirty_at, c_float(before).value)
        self.assertLessEqual(lane.estimate_dirty_at, c_float(after).value)
        self.assertEqual(lane.estimate_key, "")

    def unload_schema(self, model_id):
        """Keep only the list entry, as before a selected model's detail read finishes."""
        detailed = self.runtime.state.records[model_id]
        self.runtime.state.records[model_id] = self.catalog.ModelRecord.from_api(
            {"id": model_id, "capabilities": list(detailed.capabilities)}
        )
        self.generation._schemas.pop(model_id, None)
        return detailed

    def draw(self, lane):
        layout = RecordingLayout()
        if lane == "render_image":
            submodule("blender.render_lanes").draw_render_image_lane(layout, bpy.context)
        else:
            submodule("blender.panels").draw_generate_lane(layout, bpy.context, lane)
        return layout

    def test_failed_selected_schema_shows_persistent_error_and_retries(self):
        scenario = bpy.context.scene.scenario
        lane, neighbor = scenario.lane_state("image"), scenario.lane_state("render_image")
        model_id, neighbor_id = "model_patina-material", "model_google-gemini-3-1-flash"
        self.assertEqual(neighbor.model_id, neighbor_id)
        detailed = self.unload_schema(model_id)
        neighbor_record = self.runtime.state.records[neighbor_id]
        context = Mock()
        context.load_cached.return_value = None
        manager = self.runtime.state.manager
        with (
            patch.object(self.runtime, "ensure_catalog", return_value=context),
            patch.object(self.runtime, "online", return_value=True),
            patch.object(manager, "fetch_models") as fetch,
        ):
            lane.model_id = model_id
            fetch.assert_called_once_with(context, [model_id], mark_dirty=True)
            self.assertEqual(lane.last_error, "")
            loading = self.draw("image")
            self.assertIn(("Loading the model description...", "TIME"), loading.labels())
            self.assertEqual(loading.retries(), [])
            # The estimate debounce can price the form before its description arrives.
            self.generation.request_estimate(bpy.context.scene, "image")
            self.assertEqual(lane.estimate_error, "Model not loaded yet")
            # The failure arrives with a neighbor's successful description.
            self.handlers.dispatch(
                (
                    "models",
                    {
                        "detailed": [neighbor_record],
                        "failed": {model_id: UNAVAILABLE},
                        "mark_dirty": False,
                    },
                )
            )
            self.assertEqual(lane.last_error, FAILED_MESSAGE)
            self.assertEqual(self.runtime.state.model_errors, {model_id: FAILED_MESSAGE})
            self.assertEqual(submodule("blender.composer.draw").status_note(lane), FAILED_MESSAGE)
            self.assertEqual(neighbor.last_error, "")
            self.assertIsNotNone(self.generation.schema_for(neighbor_id))
            self.assertEqual(
                [item[0] for item in self.runtime.enum_items(("models", "image"))],
                [neighbor_id, model_id],
            )
            for _ in range(2):  # Drawing only reads the state set by the event handler.
                failed = self.draw("image")
                self.assertIn((FAILED_MESSAGE, "ERROR"), failed.labels())
                self.assertEqual(failed.retries(), ["image"])
                self.assertEqual(lane.last_error, FAILED_MESSAGE)
                self.assertEqual(self.runtime.state.model_errors, {model_id: FAILED_MESSAGE})
            self.assertEqual(fetch.call_count, 1)
            with temp_credentials():
                self.assertEqual(bpy.ops.scenario.retry_model(lane="image"), {"FINISHED"})
            self.assertEqual(fetch.call_count, 2)
            self.assertEqual(fetch.call_args.args, (context, [model_id]))
            self.assertEqual(fetch.call_args.kwargs, {"mark_dirty": True})
            self.assertEqual(lane.last_error, "")
            self.assertEqual(self.runtime.state.model_errors, {})
            retrying = self.draw("image")
            self.assertIn(("Loading the model description...", "TIME"), retrying.labels())
            self.assertEqual(retrying.retries(), [])
            self.handlers.dispatch(
                ("models", {"detailed": [], "failed": {model_id: UNAVAILABLE}, "mark_dirty": True})
            )
            self.assertEqual(lane.last_error, FAILED_MESSAGE)
        self.handlers.dispatch(
            ("models", {"detailed": [detailed], "failed": {}, "mark_dirty": True})
        )
        self.assertEqual(lane.last_error, "")
        self.assertEqual(self.runtime.state.model_errors, {})
        self.assertIsNotNone(self.generation.schema_for(model_id))
        self.assertEqual(self.draw("image").retries(), [])
        self.assertEqual(lane.estimate_state, "PENDING")

    def test_model_change_clears_failed_schema_and_reselection_reads_again(self):
        lane = bpy.context.scene.scenario.lane_state("image")
        model_id, other_id = "model_patina-material", "model_google-gemini-3-1-flash"
        self.unload_schema(model_id)
        context = Mock()
        context.load_cached.return_value = None
        manager = self.runtime.state.manager
        with (
            patch.object(self.runtime, "ensure_catalog", return_value=context),
            patch.object(self.runtime, "online", return_value=True),
            patch.object(manager, "fetch_models") as fetch,
        ):
            lane.model_id = model_id
            self.handlers.dispatch(
                ("models", {"detailed": [], "failed": {model_id: UNAVAILABLE}, "mark_dirty": True})
            )
            self.assertEqual(lane.last_error, FAILED_MESSAGE)
            lane.model_id = other_id
            self.assertEqual(lane.last_error, "")
            self.assertEqual(self.draw("image").retries(), [])
            self.assertIn("resolution", [p.name for p in lane.params])
            self.assertEqual(fetch.call_count, 1)
            lane.model_id = model_id
            self.assertEqual(fetch.call_count, 2)
            self.assertEqual(fetch.call_args.args, (context, [model_id]))
            self.assertEqual(lane.last_error, "")
            self.assertEqual(self.runtime.state.model_errors, {})

    def test_render_lane_failed_schema_retries_its_own_lane(self):
        lane = bpy.context.scene.scenario.lane_state("render_image")
        model_id = lane.model_id
        self.unload_schema(model_id)
        self.handlers.dispatch(
            ("models", {"detailed": [], "failed": {model_id: UNAVAILABLE}, "mark_dirty": False})
        )
        with patch.object(self.runtime, "online", return_value=True):
            layout = self.draw("render_image")
        self.assertIn((FAILED_MESSAGE, "ERROR"), layout.labels())
        self.assertEqual(layout.retries(), ["render_image"])
        with patch.object(self.runtime, "online", return_value=False):
            offline = self.draw("render_image")  # a retry cannot read until access returns
        self.assertEqual(offline.labels()[-1], (self.generation.MODEL_OFFLINE, "ERROR"))
        self.assertEqual(offline.retries(), [])

    def test_credential_retirement_clears_failed_schema_and_rejects_late_events(self):
        lane = bpy.context.scene.scenario.lane_state("material")
        model_id = lane.model_id
        self.unload_schema(model_id)
        retired = Mock()
        with temp_credentials("first-key", "first-secret") as prefs:
            self.runtime.state.catalog = retired
            self.runtime.state.catalog_credentials = self.runtime.credentials()
            self.runtime.state.catalog_project_id = self.runtime.project_id()
            failure = {
                "catalog": retired,
                "detailed": [],
                "failed": {model_id: UNAVAILABLE},
                "mark_dirty": False,
            }
            self.handlers.dispatch(("models", failure))
            self.assertEqual(lane.last_error, FAILED_MESSAGE)
            prefs.api_key = "second-key"  # The preference callback retires the old catalog.
            retired.close.assert_called()
            self.assertIsNone(self.runtime.state.catalog)
            self.assertEqual(lane.last_error, "")
            self.assertEqual(self.runtime.state.model_errors, {})
            self.handlers.dispatch(("models", failure))
            self.assertEqual(lane.last_error, "")
            self.assertEqual(self.runtime.state.model_errors, {})

    def failure_event(self, model_id, mark_dirty=False):
        return (
            "models",
            {"detailed": [], "failed": {model_id: UNAVAILABLE}, "mark_dirty": mark_dirty},
        )

    def test_offline_form_is_not_loading_and_returning_access_offers_retry(self):
        lane = bpy.context.scene.scenario.lane_state("image")
        model_id = "model_patina-material"
        self.unload_schema(model_id)
        context = Mock()
        context.load_cached.return_value = None
        manager = self.runtime.state.manager
        offline = self.generation.MODEL_OFFLINE
        with (
            patch.object(self.runtime, "ensure_catalog", return_value=context),
            patch.object(self.runtime, "online", return_value=False),
            patch.object(manager, "fetch_models") as fetch,
        ):
            lane.model_id = model_id
            # Access is live state; the lane keeps no refusal after it returns.
            self.assertEqual(lane.last_error, "")
            self.assertFalse(self.generation.is_loading(model_id))
            layout = self.draw("image")
            self.assertEqual(layout.labels()[-1], (offline, "ERROR"))
            self.assertNotIn(LOADING, layout.labels())
            self.assertEqual(layout.retries(), [])
            with self.assertRaises(submodule("core.api.errors").ScenarioError) as raised:
                submodule("mcp.tools_scenario").model_schema({"model_id": model_id})
            self.assertEqual(raised.exception.reason, offline)
            self.runtime.state.last_message = "An earlier unrelated message"
            retry = types.SimpleNamespace(lane="image", report=Mock())
            operator = submodule("blender.operators").SCENARIO_OT_retry_model
            self.assertEqual(operator.execute(retry, bpy.context), {"CANCELLED"})
            retry.report.assert_called_once_with({"WARNING"}, offline)
            fetch.assert_not_called()
        with (
            patch.object(self.runtime, "ensure_catalog", return_value=context),
            patch.object(self.runtime, "online", return_value=True),
            patch.object(manager, "fetch_models") as fetch,
        ):
            for _ in range(2):  # Drawing never starts the read it offers.
                idle = self.draw("image")
                self.assertEqual(idle.labels()[-1], NOT_LOADED)
                self.assertEqual(idle.retries(), ["image"])
            fetch.assert_not_called()
            with temp_credentials():
                self.assertEqual(bpy.ops.scenario.retry_model(lane="image"), {"FINISHED"})
                fetch.assert_called_once_with(context, [model_id], mark_dirty=True)
                self.assertTrue(self.generation.is_loading(model_id))
                loading = self.draw("image")
                self.assertEqual(loading.labels()[-1], LOADING)
                self.assertEqual(loading.retries(), [])

    def test_saved_lane_error_is_not_drawn_as_a_current_failure(self):
        lane = bpy.context.scene.scenario.lane_state("image")
        self.unload_schema(lane.model_id)
        lane.last_error = FAILED_MESSAGE  # as saved in a file reopened in a new session
        self.assertEqual(self.runtime.state.model_errors, {})
        with patch.object(self.runtime, "online", return_value=True):
            layout = self.draw("image")
        self.assertNotIn((FAILED_MESSAGE, "ERROR"), layout.labels())
        self.assertEqual(layout.labels()[-1], NOT_LOADED)
        self.assertEqual(layout.retries(), ["image"])

    def test_form_without_a_model_is_not_described_as_loading(self):
        layout = RecordingLayout()
        lane_state = types.SimpleNamespace(model_id="NONE", last_error=FAILED_MESSAGE)
        with patch.object(self.runtime, "online", return_value=True):
            submodule("blender.panels").draw_schema_status(layout, lane_state, "image")
        self.assertEqual(layout.labels(), [("Pick a model to show its settings", "INFO")])
        self.assertEqual(layout.retries(), [])

    def test_mcp_reports_a_recorded_failure_once_while_reading_again(self):
        lane = bpy.context.scene.scenario.lane_state("image")
        model_id = "model_patina-material"
        detailed = self.unload_schema(model_id)
        context = Mock()
        context.load_cached.return_value = None
        manager = self.runtime.state.manager
        tools = submodule("mcp.tools_scenario")
        error = submodule("core.api.errors").ScenarioError
        with (
            patch.object(self.runtime, "ensure_catalog", return_value=context),
            patch.object(self.runtime, "online", return_value=True),
            patch.object(manager, "fetch_models") as fetch,
        ):
            lane.model_id = model_id
            self.handlers.dispatch(self.failure_event(model_id, mark_dirty=True))
            self.assertEqual(lane.last_error, FAILED_MESSAGE)
            with self.assertRaises(error) as first:
                tools.model_schema({"model_id": model_id})
            self.assertEqual(
                first.exception.reason,
                f"Loading the model description again; the last read failed: {UNAVAILABLE}",
            )
            # The new read is shared: the form and MCP both wait for it now.
            self.assertEqual(fetch.call_count, 2)
            self.assertEqual(fetch.call_args.args, (context, [model_id]))
            self.assertEqual(lane.last_error, "")
            self.assertEqual(self.runtime.state.model_errors, {})
            self.assertEqual(self.draw("image").labels()[-1], LOADING)
            with self.assertRaises(error) as again:
                tools.model_schema({"model_id": model_id})
            self.assertEqual(again.exception.reason, "Loading the model description")
            self.assertEqual(fetch.call_count, 2)
        self.handlers.dispatch(("models", {"detailed": [detailed], "failed": {}}))
        self.assertEqual(tools.model_schema({"model_id": model_id})["model_id"], model_id)

    def test_catalog_and_cached_descriptions_clear_recorded_failures(self):
        lane = bpy.context.scene.scenario.lane_state("image")
        model_id = "model_patina-material"
        detailed = self.unload_schema(model_id)
        neighbor = self.runtime.state.records["model_google-gemini-3-1-flash"]
        context = Mock()
        context.load_cached.return_value = None
        manager = self.runtime.state.manager
        with (
            patch.object(self.runtime, "ensure_catalog", return_value=context),
            patch.object(self.runtime, "online", return_value=True),
            patch.object(manager, "fetch_models") as fetch,
        ):
            lane.model_id = model_id
            self.handlers.dispatch(self.failure_event(model_id))
            self.assertEqual(lane.last_error, FAILED_MESSAGE)
            records = [detailed, neighbor]
            self.handlers.dispatch(
                ("catalog", {"privacy": "public", "records": records, "detailed": records})
            )
            self.assertEqual(lane.last_error, "")
            self.assertEqual(self.runtime.state.model_errors, {})
            self.assertIsNotNone(self.generation.schema_for(model_id))
            self.unload_schema(model_id)
            self.handlers.dispatch(self.failure_event(model_id))
            self.assertEqual(lane.last_error, FAILED_MESSAGE)
            reads = fetch.call_count
            context.load_cached.return_value = detailed
            self.assertIs(self.generation.ensure_record(model_id), detailed)
            self.assertEqual(fetch.call_count, reads)  # the cache answers without a read
            self.assertEqual(lane.last_error, "")
            self.assertEqual(self.runtime.state.model_errors, {})
            self.assertEqual(self.draw("image").retries(), [])

    def test_edit3d_failed_schema_retries_the_edit3d_lane(self):
        scenario = bpy.context.scene.scenario
        model_id = "model_meshy-7-retexture"
        records = [*self.runtime.state.records.values(), fixture_record(model_id)]
        self.handlers.dispatch(
            ("catalog", {"privacy": "public", "records": records, "detailed": records})
        )
        scenario.three_d_mode = "EDIT"
        lane = scenario.lane_state("edit3d")
        self.assertEqual(lane.model_id, model_id)
        self.unload_schema(model_id)
        self.handlers.dispatch(self.failure_event(model_id))
        self.assertEqual(lane.last_error, FAILED_MESSAGE)
        context = Mock()
        context.load_cached.return_value = None
        with (
            patch.object(self.runtime, "ensure_catalog", return_value=context),
            patch.object(self.runtime, "online", return_value=True),
            patch.object(self.runtime.state.manager, "fetch_models") as fetch,
        ):
            layout = self.draw("3d")
            self.assertIn((FAILED_MESSAGE, "ERROR"), layout.labels())
            self.assertEqual(layout.retries(), ["edit3d"])
            with temp_credentials():
                self.assertEqual(bpy.ops.scenario.retry_model(lane="edit3d"), {"FINISHED"})
            fetch.assert_called_once_with(context, [model_id], mark_dirty=True)
        self.assertEqual(lane.last_error, "")
