# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Native Environment lane: tab, modes, contract form, panorama references and saved results."""

import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import bpy
import test_model_generation as generation_fixture
import test_reference_uploads as upload_fixture
from helpers import FIXTURES, draw_job_panels, drawn_texts, reset_scene, submodule

FLUX = "model_scenario-skybox-flux"
GPT = "model_scenario-skybox-gpt"
WORLD = "model_hunyuan-world-image-to-skybox"
HDRI = "model_hdri-skybox"
UPSCALE = "model_sc-upscale-flux-skybox"
MODE_MODELS = {
    "GENERATE": [FLUX, GPT],
    "FROM_IMAGE": [WORLD],
    "HDRI": [HDRI],
    "UPSCALE": [UPSCALE],
}
TABS_BEFORE_ENVIRONMENT = [
    "image",
    "video",
    "3d",
    "material",
    "audio",
    "render_image",
    "render_video",
    "blockout",
]


def recorded(model_id):
    return json.loads((FIXTURES / f"models/{model_id}.json").read_text())["model"]


def write_png(path, width, height):
    image = bpy.data.images.new("Panorama fixture", width=width, height=height)
    try:
        image.pixels[:] = [0.25, 0.5, 0.75, 1.0] * (width * height)
        image.file_format = "PNG"
        image.filepath_raw = str(path)
        image.save()
    finally:
        bpy.data.images.remove(image)
    return Path(path).read_bytes()


def form_state(scene):
    """Everything drawing could change on the scene's Environment form."""
    scenario = scene.scenario
    lane = scenario.panorama
    return {
        "tab": scenario.lane,
        "mode": scenario.panorama_mode,
        "size": scenario.panorama_size,
        "model": (lane.model_id, lane.model_key),
        "prompt": lane.prompt,
        "estimate": (lane.estimate_state, lane.estimate_key, lane.estimate_dirty_at),
        "error": lane.last_error,
        "params": [
            (
                item.name,
                item.bool_value,
                item.int_value,
                item.float_value,
                item.str_value,
                item.enabled,
            )
            for item in lane.params
        ],
        "references": [
            (ref.param_name, ref.source, ref.asset_id, ref.label, dict(ref.items()))
            for ref in lane.references
        ],
    }


def operators(layout):
    """Operator idnames drawn anywhere under a recording layout."""
    return [call.args[0] for call in layout.mock_calls if call[0].endswith("operator")]


class EnvironmentFormTests(unittest.TestCase):
    """The native form against the recorded contract model records, without a service."""

    def setUp(self):
        reset_scene()
        self.runtime = submodule("blender.runtime")
        self.generation = submodule("blender.generation")
        self.props = submodule("blender.props")
        self.panels = submodule("blender.panels")
        self.enterContext(patch.object(self.runtime, "state", self.runtime.RuntimeState()))
        catalog = submodule("core.api.catalog")
        self.records = [catalog.ModelRecord.from_api(recorded(m)) for m in MODE_MODELS["GENERATE"]]
        self.records += [catalog.ModelRecord.from_api(recorded(m)) for m in (WORLD, HDRI, UPSCALE)]
        submodule("blender.handlers").dispatch(
            ("catalog", {"privacy": "public", "records": self.records, "detailed": self.records})
        )
        self.scene = bpy.context.scene
        self.scene.scenario.lane = "panorama"
        self.lane = self.scene.scenario.lane_state("panorama")

    def models(self):
        return [item[0] for item in self.runtime.enum_items(("models", "panorama"))]

    def request(self):
        return self.generation.build_request(self.scene, "panorama", for_estimate=True)

    def test_environment_tab_is_appended_so_saved_tabs_keep_their_values(self):
        ids = [item[0] for item in self.props.LANE_ITEMS]
        self.assertEqual(ids, [*TABS_BEFORE_ENVIRONMENT, "panorama"])
        self.assertEqual(self.props.LANE_ATTR["panorama"], "panorama")
        self.assertEqual(self.props.GENERATION_LANES[-1], "panorama")
        # A blend saves the enum index: every older tab keeps its stored value.
        for index, lane in enumerate(ids):
            self.scene.scenario.lane = lane
            self.assertEqual(self.scene.scenario.get("lane"), index, lane)
        other = bpy.data.scenes.new("Environment reopen")
        self.scene.scenario.lane = "blockout"
        other.scenario.lane = "panorama"
        other.scenario.panorama_mode = "UPSCALE"
        other.scenario.panorama_size = "3840x1920"
        other.scenario.panorama.prompt = "Café 雪 dome"
        other.scenario.panorama.model_key = UPSCALE
        names = self.scene.name, other.name
        with tempfile.TemporaryDirectory(dir=bpy.utils.resource_path("USER")) as root:
            path = str(Path(root) / "environment.blend")
            bpy.ops.wm.save_as_mainfile(filepath=path, check_existing=False)
            bpy.ops.wm.open_mainfile(filepath=path)
            first, second = (bpy.data.scenes[name] for name in names)
            self.assertEqual(first.scenario.lane, "blockout")
            self.assertEqual(
                (
                    second.scenario.lane,
                    second.scenario.panorama_mode,
                    second.scenario.panorama_size,
                    second.scenario.panorama.prompt,
                    second.scenario.panorama.model_key,
                ),
                ("panorama", "UPSCALE", "3840x1920", "Café 雪 dome", UPSCALE),
            )

    def test_modes_list_only_their_contract_models_and_invalidate_the_price(self):
        self.assertEqual(self.models(), MODE_MODELS["GENERATE"])
        self.assertEqual(self.lane.model_id, FLUX)
        for mode, expected in MODE_MODELS.items():
            with self.subTest(mode=mode):
                self.lane.estimate_state, self.lane.estimate_key = "READY", "old-price"
                self.scene.scenario.panorama_mode = mode
                self.assertEqual(self.models(), expected)
                self.assertEqual(self.lane.model_id, expected[0])
                self.assertEqual(self.lane.model_key, expected[0])
                self.assertEqual(
                    (self.lane.estimate_state, self.lane.estimate_key), ("PENDING", "")
                )
        # The Image lane still lists the skybox models, as before the Environment lane.
        image = [item[0] for item in self.runtime.enum_items(("models", "image"))]
        self.assertIn(FLUX, image)

    def test_contract_values_are_forced_and_defaults_fill_only_new_settings(self):
        params = self.lane.params
        self.assertEqual(params["numOutputs"].int_value, 1)
        params["numOutputs"].int_value = 3
        self.scene.scenario.panorama_mode = "HDRI"
        self.assertEqual(
            {name: params[name].bool_value for name in ("outputExr", "outputHdr")},
            {"outputExr": True, "outputHdr": False},
        )
        self.assertFalse(params["conversionCubemapCross"].bool_value)
        self.scene.scenario.panorama_mode = "GENERATE"
        self.assertEqual(params["numOutputs"].int_value, 1)  # a new form gets the lane default
        params["numOutputs"].int_value = 3
        self.lane.estimate_state, self.lane.estimate_key = "READY", "kept-price"
        submodule("blender.handlers").dispatch(
            ("catalog", {"privacy": "public", "records": self.records, "detailed": self.records})
        )
        # A catalog refresh neither rewrites the user's value nor retires the price.
        self.assertEqual(params["numOutputs"].int_value, 3)
        self.assertEqual(
            (self.lane.estimate_state, self.lane.estimate_key), ("READY", "kept-price")
        )

    def test_drawing_reads_the_form_and_states_the_contract(self):
        expectations = {
            "GENERATE": "Result: LDR 2:1 panorama, saved until you set it as World",
            "FROM_IMAGE": "Result: LDR 2:1 panorama, saved until you set it as World",
            "HDRI": "Result: HDR OpenEXR environment, saved until you set it as World",
            "UPSCALE": "Result: LDR 2:1 panorama, saved until you set it as World",
        }
        for mode, line in expectations.items():
            with self.subTest(mode=mode):
                self.scene.scenario.panorama_mode = mode
                self.lane.prompt = "a misty valley"
                before = form_state(self.scene)
                layout = MagicMock()
                self.panels.draw_panorama_lane(layout, bpy.context)
                self.assertEqual(form_state(self.scene), before)
                texts = " ".join(drawn_texts(layout))
                self.assertIn(line.split(",")[0], texts)
                drawn = operators(layout)
                self.assertIn("scenario.generate", drawn)
                if mode in {"HDRI", "UPSCALE"}:
                    self.assertIn("scenario.use_saved_panorama", drawn)
                if mode == "HDRI":
                    # A panorama input offers a checked file and saved 360 results only.
                    self.assertNotIn("scenario.inspect_uploads", drawn)
                    self.assertNotIn("Viewport", texts.split())
                if mode == "FROM_IMAGE":
                    self.assertIn("Viewport", texts.split())
                    self.assertNotIn("scenario.use_saved_panorama", drawn)
        with (
            patch.object(self.panels, "draw_account_strip", return_value=True),
            patch.object(self.panels, "draw_panorama_lane") as lane,
        ):
            layout = MagicMock()
            self.panels.SCENARIO_PT_main.draw(SimpleNamespace(layout=layout), bpy.context)
        lane.assert_called_once_with(layout, bpy.context)
        tabs = [call.args[2] for call in layout.mock_calls if call[0].endswith("prop_enum")]
        self.assertIn("panorama", tabs)

    def test_native_request_applies_the_shared_contract(self):
        self.lane.prompt = "a misty valley"
        request = self.request()
        self.assertEqual(request.errors, [])
        self.assertEqual(
            (request.body["prompt"], request.body["numOutputs"]), ("a misty valley", 1)
        )
        self.lane.model_id = GPT
        self.scene.scenario.panorama_size = "3072x1536"
        request = self.request()
        self.assertEqual((request.body["width"], request.body["height"]), (3072, 1536))
        self.assertEqual(request.errors, [])
        self.scene.scenario.panorama_mode = "HDRI"
        request = self.request()
        self.assertEqual(request.errors[0], "Skybox Image: add a saved 360 panorama")
        self.assertEqual(
            {k: request.body[k] for k in ("outputExr", "outputHdr", "conversionCubemapFaces")},
            {"outputExr": True, "outputHdr": False, "conversionCubemapFaces": False},
        )
        ref = self.lane.references.add()
        ref.param_name, ref.source, ref.asset_id = "image", "ASSET", "asset_unchecked"
        self.assertIn("saved, downloaded 360 panorama", self.request().errors[0])
        ref.source, ref.asset_id = "VIEWPORT", ""
        self.assertIn("saved, downloaded 360 panorama", self.request().errors[0])
        # A local file waiting for upload is judged by its upload preflight.
        ref.source, ref.filepath = "FILE", "//panorama.png"
        errors = self.request().errors
        self.assertFalse([error for error in errors if "360" in error], errors)
        self.scene.scenario.panorama_mode = "FROM_IMAGE"
        self.lane.references.clear()
        still = self.lane.references.add()
        still.param_name, still.source, still.asset_id = "image", "ASSET", "asset_any_still"
        self.assertEqual(self.request().errors, [])
        # A model left from another mode is never priced under this mode.
        self.lane.model_key = FLUX
        self.assertEqual(self.request().errors, ["Pick the model again for this Environment mode"])

    def test_picker_lists_only_the_modes_contract_models(self):
        picker = submodule("blender.model_picker")
        items = picker.prepare(bpy.context, "panorama")
        self.assertEqual([item.model_id for item in items], MODE_MODELS["GENERATE"])
        self.assertEqual(picker.apply_choice(bpy.context, "panorama", 1), (GPT, "panorama"))
        self.assertEqual((self.scene.scenario.lane, self.lane.model_id), ("panorama", GPT))
        self.scene.scenario.panorama_mode = "HDRI"
        items = picker.prepare(bpy.context, "panorama")
        self.assertEqual([item.model_id for item in items], [HDRI])

    def test_quick_settings_and_reload_open_the_environment_form(self):
        operators_module = submodule("blender.operators")
        layout = MagicMock()
        operators_module.SCENARIO_OT_quick_settings.draw(
            SimpleNamespace(layout=layout, lane="panorama"), bpy.context
        )
        self.assertIn("scenario.generate", operators(layout))
        record = submodule("core.jobs.records").JobRecord(
            local_id="environment-reload",
            lane="panorama",
            kind="image",
            model_id=GPT,
            body={"prompt": "a dome", "width": 3840, "height": 1920, "quality": "medium"},
            status="success",
        )
        self.runtime.state.jobs_view.append(record)
        self.scene.scenario.lane = "image"
        self.scene.scenario.panorama_mode = "HDRI"
        self.assertEqual(
            bpy.ops.scenario.reload_generation(local_id="environment-reload"), {"FINISHED"}
        )
        scenario = self.scene.scenario
        self.assertEqual(
            (scenario.lane, scenario.panorama_mode, scenario.panorama_size),
            ("panorama", "GENERATE", "3840x1920"),
        )
        self.assertEqual((self.lane.model_id, self.lane.prompt), (GPT, "a dome"))
        self.assertEqual(self.lane.params["quality"].enum_value, "medium")
        self.assertEqual(submodule("blender.history")._kinds()[FLUX], "image")
        # The model list is shared by scenes; Reload relists an unchanged mode too.
        other = bpy.data.scenes.new("Environment other mode")
        self.addCleanup(bpy.data.scenes.remove, other)
        other.scenario.panorama_mode = "HDRI"
        self.generation.refresh_panorama_models(SimpleNamespace(scene=other))
        self.assertEqual(self.models(), [HDRI])
        self.assertEqual(
            bpy.ops.scenario.reload_generation(local_id="environment-reload"), {"FINISHED"}
        )
        self.assertEqual(self.models(), MODE_MODELS["GENERATE"])
        self.assertEqual((self.lane.model_id, self.lane.model_key), (GPT, GPT))
        self.lane.prompt = "a dome"
        self.assertEqual(self.request().errors, [])


class EnvironmentJobTests(unittest.TestCase):
    """Quote, submit, delivery and saved-result controls with the bundled SDK and a fake service."""

    def setUp(self):
        self.fixture = fixture = generation_fixture.ModelGenerationTests()
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        self.runtime, self.generation, self.tools = (
            fixture.runtime,
            fixture.generation,
            fixture.tools,
        )
        for model_id in (FLUX, GPT, WORLD, HDRI, UPSCALE):
            fixture.use_model(recorded(model_id))
        self.scene = bpy.context.scene
        self.scene.scenario.lane = "panorama"
        self.generation.refresh_panorama_models(bpy.context)
        self.lane = self.scene.scenario.lane_state("panorama")
        self.before_worlds = set(bpy.data.worlds)
        self.addCleanup(self.remove_worlds)

    def remove_worlds(self):
        for world in set(bpy.data.worlds) - self.before_worlds:
            bpy.data.worlds.remove(world, do_unlink=True)

    def panorama_result(self, asset_id="saved-panorama", model_id=FLUX):
        fixture = self.fixture
        fixture.result_bytes = write_png(self.runtime.paths().state_dir / "result.png", 8, 4)
        fixture.result_media_type = "image/png"
        fixture.remote_status = "success"
        fixture.result_assets = {asset_id: {"type": "skybox-base-360"}}
        fixture.job_model_id = model_id

    def actions(self, view):
        return submodule("blender.job_recovery").result_actions(view)

    def test_native_job_waits_for_world_approval_in_the_selected_scene(self):
        fixture = self.fixture
        self.panorama_result()  # writing the fixture image changes the scene revision
        self.lane.prompt = "a misty valley"
        fixture.ui_quote("panorama")
        sent = fixture.dry_runs()[-1]
        self.assertEqual((sent["prompt"], sent["numOutputs"]), ("a misty valley", 1))
        first, world, images = self.scene, self.scene.world, set(bpy.data.images)
        self.assertEqual(bpy.ops.scenario.generate(lane="panorama"), {"FINISHED"})
        fixture.deliver_results()
        self.assertEqual(json.loads(fixture.paid[-1].content), sent)
        view = self.runtime.state.jobs_view[0]
        saved = fixture.store.get(view.local_id)
        self.assertEqual((saved.state.value, view.lane, view.kind), ("ready", "panorama", "image"))
        # No automatic image import and no World change.
        self.assertEqual((first.world, set(bpy.data.images)), (world, images))
        labels = [item.label for item in self.actions(view)]
        self.assertEqual(labels[0], "360 panorama (LDR)")
        self.assertIn("Set panorama as World (1)", labels)
        self.assertIn("Make HDRI (1)", labels)
        _, jobs, generations, _ = draw_job_panels()
        self.assertIn("Make HDRI (1)", drawn_texts(jobs, generations))
        second = bpy.data.scenes.new("Environment destination")
        self.addCleanup(bpy.data.scenes.remove, second)
        self.addCleanup(setattr, bpy.context.window, "scene", first)
        bpy.context.window.scene = second
        context_id = self.runtime.state.job_context_id
        _, approval = self.runtime.prepare_world_application(
            context_id, view.local_id, saved.revision, bpy.context.scene, "saved-panorama"
        )
        self.assertEqual(approval.scene_name, "Environment destination")
        self.runtime.apply_saved_result(context_id, approval.identifier)
        fixture.deliver_results()
        self.assertIsNotNone(second.world)
        self.assertEqual(first.world, world)
        self.assertEqual(fixture.store.get(view.local_id).state.value, "applied")
        self.assertEqual(len(fixture.paid), 1)

    def test_restart_keeps_the_projection_label_world_action_and_make_hdri(self):
        _, result = self.fixture.saved_panorama()
        self.runtime.state.reset()
        self.assertEqual(bpy.ops.scenario.inspect_saved_jobs(), {"FINISHED"})
        view = self.runtime.state.model_jobs.views[result["local_id"]]
        self.assertEqual(view.kind, "model")  # restarted jobs are generic
        labels = [item.label for item in self.actions(view)]
        self.assertEqual(labels[0], "360 panorama (LDR)")
        self.assertIn("Set panorama as World (1)", labels)
        self.assertIn("Make HDRI (1)", labels)

    def test_make_hdri_prefills_a_scoped_saved_reference_and_needs_a_fresh_quote(self):
        fixture = self.fixture
        _, result = fixture.saved_panorama()
        view = self.runtime.state.model_jobs.views[result["local_id"]]
        item = next(i for i in self.actions(view) if i.operator == "scenario.panorama_to_hdri")
        stale = dict(item.properties, context_id="retired-context")
        self.scene.scenario.lane = "image"
        with self.assertRaisesRegex(RuntimeError, "connection changed"):
            bpy.ops.scenario.panorama_to_hdri(**stale)
        self.assertEqual(self.scene.scenario.lane, "image")
        self.lane.estimate_state, self.lane.estimate_key = "READY", "old-price"
        paid = len(fixture.paid)
        self.assertEqual(bpy.ops.scenario.panorama_to_hdri(**dict(item.properties)), {"FINISHED"})
        scenario = self.scene.scenario
        self.assertEqual((scenario.lane, scenario.panorama_mode), ("panorama", "HDRI"))
        self.assertEqual(self.lane.model_id, HDRI)
        self.assertEqual((self.lane.estimate_state, self.lane.estimate_key), ("PENDING", ""))
        ref = self.lane.references[0]
        self.assertEqual(
            (ref.param_name, ref.source, ref.asset_id), ("image", "ASSET", "saved-panorama")
        )
        self.assertEqual(ref["_scenario_reference_projection"], "equirectangular")
        self.assertIsNone(submodule("blender.reference_form").scope_error(self.lane))
        fixture.ui_quote("panorama")
        native = fixture.dry_runs()[-1]
        self.assertEqual(
            native,
            {
                "image": "saved-panorama",
                "outputExr": True,
                "outputHdr": False,
                "conversionCubemapCross": False,
                "conversionCubemapFaces": False,
            },
        )
        # Local MCP builds the same contract body for the same reference.
        fixture.panorama_estimate(HDRI, {"image": "saved-panorama"})
        self.assertEqual(fixture.dry_runs()[-1], native)
        self.assertEqual(len(fixture.paid), paid)

    def test_make_hdri_relists_hdri_after_another_scene_listed_its_mode(self):
        _, result = self.fixture.saved_panorama()
        view = self.runtime.state.model_jobs.views[result["local_id"]]
        item = next(i for i in self.actions(view) if i.operator == "scenario.panorama_to_hdri")
        paid = len(self.fixture.paid)
        self.scene.scenario.panorama_mode = "HDRI"
        other = bpy.data.scenes.new("Environment other mode")
        self.addCleanup(bpy.data.scenes.remove, other)
        # The list is shared by scenes: another scene's refresh lists its Generate mode.
        self.generation.refresh_panorama_models(SimpleNamespace(scene=other))
        listed = [entry[0] for entry in self.runtime.enum_items(("models", "panorama"))]
        self.assertEqual(listed, [FLUX, GPT])
        self.assertEqual(bpy.ops.scenario.panorama_to_hdri(**dict(item.properties)), {"FINISHED"})
        scenario = self.scene.scenario
        self.assertEqual((scenario.lane, scenario.panorama_mode), ("panorama", "HDRI"))
        self.assertEqual((self.lane.model_id, self.lane.model_key), (HDRI, HDRI))
        self.assertEqual(
            [(ref.param_name, ref.asset_id) for ref in self.lane.references],
            [("image", "saved-panorama")],
        )
        request = self.generation.build_request(self.scene, "panorama", for_estimate=True)
        self.assertEqual((request.body["image"], request.errors), ("saved-panorama", []))
        self.assertEqual(len(self.fixture.paid), paid)

    def test_saved_panorama_choices_hold_only_scoped_ldr_results(self):
        fixture = self.fixture
        _, panorama = fixture.saved_panorama()
        fixture.result_fixture()
        fixture.result_assets = {"plain-image": {}}
        fixture.job_model_id = fixture.model["id"]
        plain = fixture.mcp_submit(fixture.mcp_quote())
        fixture.deliver_results()
        lane_module = submodule("blender.panorama_lane")
        found = [(r.intent.request_id, i.asset.asset_id) for r, i in lane_module.candidates()]
        self.assertEqual(found, [(panorama["local_id"], "saved-panorama")])
        error = submodule("core.api.errors").ScenarioError
        with self.assertRaisesRegex(error, "saved, downloaded 360 panorama"):
            lane_module.attach_saved(self.scene, "image", plain["local_id"], "plain-image")
        operator = lane_module.SCENARIO_OT_use_saved_panorama
        fake = SimpleNamespace(
            param_name="image", choice="", report=MagicMock(), layout=MagicMock()
        )
        wm = MagicMock()
        wm.invoke_props_dialog.return_value = {"RUNNING_MODAL"}
        context = SimpleNamespace(scene=self.scene, window_manager=wm)
        self.assertEqual(operator.invoke(fake, context, None), {"RUNNING_MODAL"})
        self.assertEqual(fake.choice, f"{panorama['local_id']}:saved-panorama")
        before = form_state(self.scene)
        operator.draw(fake, context)
        self.assertEqual(form_state(self.scene), before)
        self.assertEqual(operator.execute(fake, context), {"FINISHED"})
        self.lane.prompt = "restyle at dusk"
        request = self.generation.build_request(self.scene, "panorama", for_estimate=True)
        self.assertEqual((request.body["image"], request.errors), ("saved-panorama", []))

    def test_credential_change_retires_the_price_and_saved_references(self):
        fixture = self.fixture
        _, result = fixture.saved_panorama()
        self.scene.scenario.panorama_mode = "HDRI"
        lane_module = submodule("blender.panorama_lane")
        lane_module.attach_saved(self.scene, "image", result["local_id"], "saved-panorama")
        fixture.ui_quote("panorama")
        self.assertTrue(submodule("blender.panels").generate_enabled(self.lane, "panorama"))
        fixture.prefs.api_key = "another-fixture-key"
        self.runtime.sync_catalog_context()
        self.assertFalse(submodule("blender.panels").generate_enabled(self.lane, "panorama"))
        self.runtime.ensure_job_store()
        self.assertIn(
            "another connection",
            submodule("blender.reference_form").scope_error(self.lane),
        )

    def test_uncertain_native_submission_is_shown_without_a_retry(self):
        fixture = self.fixture
        fixture.lose_response = True
        self.lane.prompt = "a misty valley"
        fixture.ui_quote("panorama")
        view = self.generation.submit_generation(bpy.context, "panorama")
        fixture.settle()
        self.assertEqual(fixture.store.get(view.local_id).state.value, "uncertain")
        self.assertIn("not confirmed", self.runtime.state.model_jobs.views[view.local_id].error)
        with self.assertRaisesRegex(fixture.request_error, "fresh price"):
            self.generation.submit_generation(bpy.context, "panorama")
        self.assertEqual(len(fixture.paid), 1)

    def test_gpt_body_matches_local_mcp_for_the_same_inputs(self):
        fixture = self.fixture
        self.lane.model_id = GPT
        self.lane.prompt = "a canyon at noon"
        self.scene.scenario.panorama_size = "3840x1920"
        fixture.ui_quote("panorama")
        native = fixture.dry_runs()[-1]
        self.assertEqual((native["width"], native["height"]), (3840, 1920))
        request = self.generation.build_request(self.scene, "panorama", for_estimate=True)
        fixture.panorama_estimate(GPT, request.body)
        self.assertEqual(fixture.dry_runs()[-1], native)
        self.assertEqual(fixture.paid, [])


class PanoramaFileTests(unittest.TestCase):
    """A local panorama file is checked before upload and bound to the checked bytes."""

    def setUp(self):
        self.fixture = fixture = upload_fixture.ReferenceUploadTests()
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        session = fixture.fixture
        self.runtime, self.owner = fixture.runtime, fixture.owner
        self.form = submodule("blender.reference_form")
        self.generation = submodule("blender.generation")
        self.error = submodule("core.api.errors").ScenarioError
        self.path = session.root / "panorama.png"
        self.data = write_png(self.path, 64, 32)
        # Accept this one larger part; the session fixture's limits fit its own 4 bytes.
        session.sources._max_bytes = session.sources._part_bytes = 1 << 20
        session.remote.update(
            originalFileName="panorama.png", fileSize=len(self.data), partsCount=1
        )
        transfer = submodule("core.jobs.upload_transfers")
        session.uploader.upload.side_effect = lambda _url, data, *, number, **kwargs: (
            transfer.UploadedPart(number, len(data), kwargs["expected_sha256"])
        )
        catalog = submodule("core.api.catalog")
        records = [catalog.ModelRecord.from_api(recorded(m)) for m in (HDRI, UPSCALE)]
        self.generation.set_catalog(records, records)
        self.scene = session.scene
        self.runtime.state.job_store = session.store
        self.scene.scenario.lane = "panorama"
        self.scene.scenario.panorama_mode = "UPSCALE"
        self.lane = self.scene.scenario.lane_state("panorama")
        self.assertEqual(self.lane.model_id, UPSCALE)
        self.ref = self.lane.references.add()
        self.ref.param_name, self.ref.source, self.ref.filepath = "image", "FILE", str(self.path)
        self.enterContext(
            patch.object(submodule("blender.operators"), "_network_poll", return_value=True)
        )

    def test_checked_file_uploads_its_exact_bytes_and_keeps_its_size(self):
        with patch.object(self.owner, "start", wraps=self.owner.start) as start:
            self.assertEqual(
                bpy.ops.scenario.upload_reference(index=0, lane="panorama"), {"FINISHED"}
            )
        self.assertEqual(
            start.call_args.kwargs["expected_sha256"], hashlib.sha256(self.data).hexdigest()
        )
        self.assertEqual(self.ref["_scenario_reference_panorama"], "64x32")
        self.fixture.settle()
        self.assertEqual((self.ref.source, self.ref.asset_id), ("ASSET", "reference-asset"))
        # A known size lifts the unknown-size cap of 2 within the World pixel limit.
        self.lane.params["upscaleFactor"].int_value = 8
        request = self.generation.build_request(self.scene, "panorama", for_estimate=True)
        self.assertEqual(request.errors, [])
        self.assertEqual(
            (request.body["image"], request.body["upscaleFactor"]), ("reference-asset", 8)
        )

    def test_file_that_is_not_a_2_1_panorama_is_refused_before_upload(self):
        write_png(self.path, 30, 20)
        with self.assertRaisesRegex(self.error, "not a usable 360 panorama"):
            self.form.start(bpy.context, 0, lane_name="panorama")
        self.assertFalse([key for key in self.ref.keys() if key.startswith("_scenario")])
        self.assertEqual(self.owner.forms, {})
        self.fixture.fixture.uploader.upload.assert_not_called()
        self.ref.source = "VIEWPORT"
        with self.assertRaisesRegex(self.error, "2:1 panorama file"):
            self.form.start(bpy.context, 0, lane_name="panorama")

    def test_bytes_changed_after_the_check_are_never_uploaded(self):
        lane_module = submodule("blender.panorama_lane")
        info = submodule("core.scene.panorama").inspect_panorama(self.data)
        with patch.object(lane_module, "preflight_file", return_value=(info, "0" * 64)):
            binding = self.form.start(bpy.context, 0, lane_name="panorama")
        self.fixture.settle()
        self.assertFalse(binding.attached)
        self.assertEqual(self.ref.source, "FILE")
        self.fixture.fixture.uploader.upload.assert_not_called()

    def test_saved_upload_cannot_fill_a_panorama_input(self):
        result = self.fixture.tools.upload_reference({"path": str(self.path)})
        self.fixture.settle()
        record = self.owner.references[result["reference_id"]].record
        self.assertEqual(record.state.value, "imported")
        with self.assertRaisesRegex(self.error, "Use saved panorama"):
            self.form.prepare_attachment(
                bpy.context,
                self.runtime.state.job_context_id,
                record.intent.request_id,
                record.revision,
                0,
                "image",
                lane_name="panorama",
            )
