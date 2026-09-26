# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
import json
import unittest
from ctypes import c_float
from unittest.mock import Mock, patch

import bpy
from helpers import FIXTURES, isolated_manager, reset_scene, submodule


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

    def test_job_done_event_for_image_loads_images(self):
        records = submodule("core.jobs.records")
        rec = records.JobRecord.new(lane="image", kind="image", model_id="model_x", body={})
        rec.job_id, rec.status = "job_done_1", "success"
        rec.files = [str(FIXTURES / "patina-copper-512" / "albedo.png")]
        self.handlers.dispatch(("job_done", rec))
        self.assertTrue(any(img.filepath.endswith("albedo.png") for img in bpy.data.images))
        self.assertTrue(any(r.job_id == "job_done_1" for r in self.runtime.state.jobs_view))

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
