# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Trained LoRAs and compositions through the installed picker and forms (#97).

A synthetic Scenario service behind the installed SDK serves the captured public
FLUX.1 Dev base and trained records plus synthetic private ones. Nothing reaches
the network and no paid request is possible: only list, description and dryRun
quote requests are answered.
"""

import json
import pathlib
import tempfile
import threading
import types
import unittest
from unittest.mock import patch

import bpy
import httpx
import test_model_picker as picker_tests
from helpers import (
    FIXTURES,
    isolated_manager,
    online_access,
    reset_scene,
    submodule,
    temp_credentials,
)

TRAINED = FIXTURES / "models/trained"
FLUX1 = "model_bfl-flux-1-dev"
ZIMAGE = "model_z-image"
LORA_A = "model_YQrES2iPys22nYwh3YhVfMh8"
FLUX2_LORA = "model_CMUu7BjxV8TpdhG3FKoxZRxC"
COMPOSITION = "model_7oiHtKChpcLpy4jq3Jq2BG8n"
STUDIO_LORA = "model_studio-lora"
STUDIO_VOICE = "model_studio-voice"
STUDIO_CUSTOM = "model_studio-custom"
PROMPT = "a small wooden cabin in a snowy forest"
SCHEMA_FIELDS = ("inputs", "parameters", "uiConfig")


def load(relative):
    return json.loads((TRAINED / relative).read_text(encoding="utf-8"))["model"]


def row(record):
    """A list row: Scenario's model lists carry no input schema."""
    return {key: value for key, value in record.items() if key not in SCHEMA_FIELDS}


class TrainedModelTests(unittest.TestCase):
    def setUp(self):
        reset_scene()
        self.runtime = submodule("blender.runtime")
        self.generation = submodule("blender.generation")
        self.picker = submodule("blender.model_picker")
        self.trained = submodule("blender.trained_models")
        self.enterContext(patch.object(self.runtime, "state", self.runtime.RuntimeState()))
        self.prefs = self.enterContext(temp_credentials())
        self.enterContext(online_access(True))
        self.manager = self.enterContext(isolated_manager())
        self.addCleanup(self.runtime.state.reset)
        saved = {
            key: dict(value) if isinstance(value, dict) else value
            for key, value in self.picker._ctx.items()
        }
        self.addCleanup(self.picker._ctx.update, saved)
        self.calls, self.posts = [], []
        flux1, zimage = load(f"bases/{FLUX1}.json"), load(f"bases/{ZIMAGE}.json")
        lora, flux2_lora, composition = (
            load(f"public/{model_id}.json") for model_id in (LORA_A, FLUX2_LORA, COMPOSITION)
        )
        studio_lora = {
            "id": STUDIO_LORA,
            "name": "Studio LoRA",
            "type": "flux.1-lora",
            "privacy": "private",
            "status": "trained",
            "capabilities": ["txt2img", "img2img"],
        }
        studio_voice = {**studio_lora, "id": STUDIO_VOICE, "name": "Studio Voice"}
        studio_voice["type"] = "elevenlabs-voice"
        studio_custom = {**studio_lora, "id": STUDIO_CUSTOM, "name": "Studio Custom"}
        studio_custom["type"] = "custom"
        self.public = [row(flux1), row(zimage), lora, flux2_lora, composition]
        self.private = [studio_lora, studio_voice, studio_custom]
        self.details = {
            record["id"]: record
            for record in (flux1, zimage, lora, flux2_lora, composition, studio_lora)
        }
        for concept in composition["concepts"]:
            self.details.setdefault(
                concept["modelId"],
                {"id": concept["modelId"], "type": "flux.1-lora", "status": "trained"},
            )
        self.private_error = None
        adapter = submodule("core.api.sdk_adapter")

        def respond(request):
            self.assertIsNot(threading.current_thread(), threading.main_thread())
            path = request.url.path
            self.calls.append((request.method, path, dict(request.url.params)))
            if request.method == "GET" and path == "/v1/models":
                if request.url.params.get("privacy") == "private":
                    self.assertEqual(request.url.params.get("status"), "trained")
                    if self.private_error is not None:
                        return httpx.Response(self.private_error, json={"reason": "denied"})
                    return httpx.Response(200, json={"models": self.private})
                return httpx.Response(200, json={"models": self.public})
            if request.method == "GET" and path.startswith("/v1/models/"):
                record = self.details.get(path.rsplit("/", 1)[1])
                if record is None:
                    return httpx.Response(404, json={"reason": "not found"})
                return httpx.Response(200, json={"model": record})
            self.assertEqual(request.method, "POST")
            self.assertEqual(path, f"/v1/generate/custom/{FLUX1}")
            self.assertEqual(dict(request.url.params), {"dryRun": "true"})
            self.posts.append(json.loads(request.content))
            return httpx.Response(269, json={"creativeUnitsCost": 10.75})

        def factory(credentials, **kwargs):
            return adapter.SDKAdapter(credentials, transport=httpx.MockTransport(respond), **kwargs)

        self.enterContext(
            patch.object(submodule("core.api.sdk_catalog"), "SDKAdapter", side_effect=factory)
        )
        self.scene = bpy.context.scene
        self.lane = self.scene.scenario.lane_state("image")
        self.lane.prompt = PROMPT
        self.wm = bpy.context.window_manager

    # -- helpers -------------------------------------------------------------------
    def settle(self):
        """Run queued catalog workers and deliver their events until nothing is pending."""
        for _ in range(20):
            self.manager.join(5)
            if not self.generation.process_catalog_events() and not self.manager.has_active():
                return
        self.fail("Catalog workers did not settle")

    def load_catalog(self):
        self.assertTrue(self.generation.request_catalog())
        self.settle()
        self.assertTrue(self.runtime.state.catalog_loaded)

    def open_trained(self, lane="image"):
        self.picker.prepare(bpy.context, lane, "trained")
        self.settle()
        return {item.model_id: item for item in self.wm.scenario_picker_items}

    def highlight(self, model_id):
        ids = [item.model_id for item in self.wm.scenario_picker_items]
        self.wm.scenario_picker_index = ids.index(model_id)

    def pick(self, model_id, strength=None):
        self.highlight(model_id)
        if strength is not None:
            self.wm.scenario_picker_strength = strength
        return bpy.ops.scenario.pick_model(lane="image")

    def body(self):
        request = self.generation.build_request(self.scene, "image", for_estimate=True)
        self.assertFalse(request.errors, request.errors)
        return request.body

    def deliver_quote(self):
        for ticket in tuple(self.runtime.state.model_previews.values()):
            try:
                ticket.task.result(5)
            except Exception:
                pass  # main-thread delivery reports a refused quote
        self.runtime.sync_catalog_context()
        self.manager.join(5)

    def gets(self, model_id):
        return [call for call in self.calls if call[:2] == ("GET", f"/v1/models/{model_id}")]

    # -- catalog and picker ------------------------------------------------------
    def test_catalog_lists_trained_models_without_reading_base_descriptions(self):
        self.load_catalog()
        state = self.runtime.state
        self.assertTrue(state.trained_loaded, state.trained_error)
        self.assertEqual(
            [(kind, record.id) for kind, record in state.trained_pairs],
            [
                ("lora", STUDIO_LORA),
                ("unsupported", STUDIO_VOICE),
                ("custom_private", STUDIO_CUSTOM),
                ("lora", LORA_A),
                ("lora", FLUX2_LORA),
                ("composition", COMPOSITION),
            ],
        )
        self.assertEqual(state.trained_private, {STUDIO_LORA, STUDIO_VOICE, STUDIO_CUSTOM})
        lists = [call[2] for call in self.calls if call[1] == "/v1/models"]
        self.assertEqual(sorted(params["privacy"] for params in lists), ["private", "public"])
        self.assertEqual(self.gets(FLUX1), [])  # a base is described only for the Trained chip
        self.assertNotIn(FLUX1, [r.id for r in state.records.values() if r.parameters])
        # Base lanes still leave trained records out.
        self.assertNotIn(LORA_A, [r.id for r in state.lane_models["image"]])

    def test_trained_chip_reads_bases_lazily_once_and_explains_each_row(self):
        self.load_catalog()
        rows = self.open_trained()
        self.assertEqual(len(self.gets(FLUX1)), 1)
        self.assertEqual(
            [(item.model_id, item.available) for item in self.wm.scenario_picker_items],
            [
                (STUDIO_LORA, True),
                (LORA_A, True),
                (COMPOSITION, True),
                (STUDIO_VOICE, False),
                (FLUX2_LORA, False),
            ],
        )
        self.assertNotIn(STUDIO_CUSTOM, rows)  # a private custom model is not a LoRA
        self.assertEqual(rows[STUDIO_LORA].description, "Private LoRA via FLUX.1 Dev")
        self.assertEqual(rows[COMPOSITION].description, "Composition via FLUX.1 Dev")
        self.assertEqual(
            rows[FLUX2_LORA].description,
            "No base model in this form accepts flux.2-dev-lora models.",
        )
        self.assertEqual(
            rows[STUDIO_VOICE].description,
            "Not available in Blender: no base model runs this type.",
        )
        self.assertEqual(self.trained.scan_status("image"), "")
        self.open_trained()
        self.assertEqual(len(self.gets(FLUX1)), 1)  # descriptions are cached per connection
        self.picker.prepare(bpy.context, "image")
        self.assertNotIn(LORA_A, [item.model_id for item in self.wm.scenario_picker_items])

    def test_dialog_draw_reads_the_trained_choice_without_writing_it(self):
        self.load_catalog()
        self.open_trained()
        self.highlight(STUDIO_LORA)
        before = (
            self.wm.scenario_picker_index,
            self.wm.scenario_picker_base,
            round(self.wm.scenario_picker_strength, 4),
            len(self.wm.scenario_picker_items),
            self.lane.model_id,
            len(self.lane.trained),
            self.lane.estimate_state,
        )
        root = picker_tests.FakeLayout()
        self.picker.SCENARIO_OT_pick_model.draw(types.SimpleNamespace(layout=root), bpy.context)
        labels = [call[2] for node in root.walk() for call in node.named("label")]
        self.assertIn({"text": "Private LoRA"}, labels)
        self.assertIn({"text": "Runs with FLUX.1 Dev"}, labels)
        self.assertIn(
            {"text": "Experimental: LoRAs and compositions not accepted", "icon": "EXPERIMENTAL"},
            labels,
        )
        props = [call[1][1] for node in root.walk() for call in node.named("prop")]
        self.assertIn("scenario_picker_strength", props)
        self.assertNotIn("scenario_picker_base", props)  # one base: shown, not chosen silently
        after = (
            self.wm.scenario_picker_index,
            self.wm.scenario_picker_base,
            round(self.wm.scenario_picker_strength, 4),
            len(self.wm.scenario_picker_items),
            self.lane.model_id,
            len(self.lane.trained),
            self.lane.estimate_state,
        )
        self.assertEqual(before, after)
        self.assertIn(
            "trained",
            [v for _a, values in picker_tests.ModelPickerTests.enum_rows(root) for v in values],
        )

    def test_choosing_loras_sets_the_base_strengths_and_invalidates_the_price(self):
        self.load_catalog()
        self.open_trained()
        self.highlight(STUDIO_LORA)
        self.assertEqual(self.wm.scenario_picker_base, FLUX1)
        self.assertEqual(round(self.wm.scenario_picker_strength, 4), 1.0)  # visible start
        self.wm.scenario_picker_strength = 5.0
        self.assertEqual(round(self.wm.scenario_picker_strength, 4), 2.0)  # declared maximum
        self.lane.estimate_state = "READY"
        self.assertEqual(self.pick(STUDIO_LORA, 0.85), {"FINISHED"})
        self.assertEqual((self.lane.model_id, self.lane.model_key), (FLUX1, FLUX1))
        self.assertEqual(self.lane.estimate_state, "PENDING")
        (slot,) = self.lane.trained
        self.assertEqual(
            (slot.model_id, slot.kind, slot.name, slot.has_scale, slot.fmin, slot.fmax),
            (STUDIO_LORA, "lora", "Studio LoRA", True, 0.0, 2.0),
        )
        self.assertEqual(slot.get(self.trained.SCOPE), self.trained.current_scope())
        for hidden in ("loras", "lorasScale", "modelId"):
            self.assertLess(self.lane.params.find(hidden), 0, hidden)  # never a text field
        body = self.body()
        self.assertEqual((body["loras"], body["lorasScale"]), ([STUDIO_LORA], [0.85]))
        self.assertNotIn("modelId", body)
        self.open_trained()
        self.assertEqual(self.pick(LORA_A), {"FINISHED"})
        self.assertEqual(self.body()["loras"], [STUDIO_LORA, LORA_A])
        self.assertEqual(self.body()["lorasScale"], [0.85, 1.0])
        self.open_trained()
        self.highlight(STUDIO_LORA)
        self.assertEqual(round(self.wm.scenario_picker_strength, 4), 0.85)  # its current strength
        self.assertEqual(self.pick(STUDIO_LORA, 0.4), {"FINISHED"})
        self.assertEqual(self.body()["lorasScale"], [0.4, 1.0])
        self.open_trained()
        self.assertEqual(self.pick(COMPOSITION), {"FINISHED"})
        body = self.body()
        self.assertEqual(body["modelId"], COMPOSITION)
        self.assertNotIn("loras", body)
        self.assertEqual([slot.kind for slot in self.lane.trained], ["composition"])
        self.open_trained()
        self.highlight(FLUX2_LORA)
        self.assertEqual(bpy.ops.scenario.pick_model(lane="image"), {"CANCELLED"})
        self.assertEqual([slot.model_id for slot in self.lane.trained], [COMPOSITION])

    def test_the_quote_reads_trained_models_fresh_and_prices_the_exact_payload(self):
        self.load_catalog()
        self.open_trained()
        self.pick(STUDIO_LORA, 0.8)
        body = self.body()
        self.calls.clear()
        self.generation.request_estimate(self.scene, "image")
        self.deliver_quote()
        self.assertEqual(self.lane.estimate_state, "READY", self.lane.estimate_error)
        (sent,) = self.posts
        self.assertEqual((sent["loras"], sent["lorasScale"]), ([STUDIO_LORA], [0.8]))
        self.assertNotIn("modelId", sent)
        self.assertEqual({k: sent[k] for k in body}, body)  # the form's values, plus defaults
        self.assertEqual(len(self.gets(STUDIO_LORA)), 1)  # read fresh before the dry run
        # Local MCP prices the same payload byte for byte.
        tools = submodule("mcp.tools_scenario")
        deferred = tools.estimate_cost({"model_id": FLUX1, "parameters": body})
        from concurrent.futures import ThreadPoolExecutor

        with ThreadPoolExecutor(max_workers=1) as worker:
            worker.submit(deferred.run).result(5)
        self.assertEqual(len(self.posts), 2)
        self.assertEqual(
            json.dumps(self.posts[0], sort_keys=True), json.dumps(self.posts[1], sort_keys=True)
        )

    def test_a_trained_type_changed_since_listing_is_refused_before_any_dry_run(self):
        self.load_catalog()
        self.open_trained()
        self.pick(STUDIO_LORA, 0.8)
        self.details[STUDIO_LORA] = {**self.details[STUDIO_LORA], "type": "flux.2-dev-lora"}
        self.generation.request_estimate(self.scene, "image")
        self.deliver_quote()
        self.assertEqual(self.lane.estimate_state, "ERROR")
        self.assertEqual(
            self.lane.estimate_error,
            "Flux LoRA [1] is a flux.2-dev-lora model; Flux LoRA accepts flux.1-lora.",
        )
        self.assertEqual(self.posts, [])

    def test_a_base_change_keeps_the_choice_and_blocks_with_a_reason(self):
        self.load_catalog()
        self.open_trained()
        self.pick(LORA_A, 0.8)
        self.lane.model_id = ZIMAGE
        request = self.generation.build_request(self.scene, "image", for_estimate=True)
        self.assertEqual(
            request.errors,
            [
                "Z-Image LoRA accepts zimage-lora, zimage-turbo-lora, zimage-de-turbo-lora "
                "models, not flux.1-lora."
            ],
        )
        self.assertEqual([slot.model_id for slot in self.lane.trained], [LORA_A])
        self.assertEqual(bpy.ops.scenario.trained_remove(lane="image", index=0), {"FINISHED"})
        self.assertFalse(len(self.lane.trained))
        self.assertEqual(self.lane.estimate_state, "PENDING")
        self.assertFalse(
            self.generation.build_request(self.scene, "image", for_estimate=True).errors
        )

    def test_another_connection_cannot_use_a_saved_choice(self):
        self.load_catalog()
        self.open_trained()
        self.pick(LORA_A, 0.8)
        self.addCleanup(setattr, self.prefs, "project_id", self.prefs.project_id)
        self.prefs.project_id = "project-b"
        self.runtime.sync_catalog_context()  # retires the connection and its trained list
        self.assertFalse(self.runtime.state.trained_loaded)
        self.runtime.ensure_catalog()
        self.load_catalog()
        request = self.generation.build_request(self.scene, "image", for_estimate=True)
        self.assertEqual(request.errors, [self.trained.OTHER_SCOPE])
        self.posts.clear()
        self.generation.request_estimate(self.scene, "image")
        self.assertEqual(self.lane.estimate_state, "UNAVAILABLE")
        self.assertEqual(self.posts, [])

    def test_a_private_list_failure_never_blocks_lanes_without_a_trained_choice(self):
        self.private_error = 500
        self.load_catalog()
        state = self.runtime.state
        self.assertFalse(state.trained_loaded)
        self.assertTrue(state.trained_error)
        self.lane.model_id = ZIMAGE
        self.assertFalse(
            self.generation.build_request(self.scene, "image", for_estimate=True).errors
        )
        slot = self.lane.trained.add()
        slot.model_id, slot.kind, slot.lane = LORA_A, "lora", "image"
        slot.fmin, slot.fmax, slot.has_scale, slot.scale = 0.0, 2.0, True, 0.8
        slot[self.trained.SCOPE] = self.trained.current_scope()
        request = self.generation.build_request(self.scene, "image", for_estimate=True)
        self.assertEqual(request.errors, [f"Could not load trained models: {state.trained_error}"])
        # Only an explicit Trained chip (or refresh) reads the private list again.
        self.private_error = None
        private_reads = len([call for call in self.calls if call[2].get("privacy") == "private"])
        self.settle()
        self.assertFalse(state.trained_loaded)
        rows = self.open_trained()
        self.assertTrue(state.trained_loaded, state.trained_error)
        self.assertEqual(
            len([call for call in self.calls if call[2].get("privacy") == "private"]),
            private_reads + 1,
        )
        self.assertTrue(rows[LORA_A].available)  # the bases were then read for the chip
        self.lane.model_id = FLUX1
        self.assertEqual(self.body()["lorasScale"], [0.8])

    def test_model_row_lists_the_choice_and_removal_reprices(self):
        self.load_catalog()
        self.open_trained()
        self.pick(STUDIO_LORA, 0.8)
        self.open_trained()
        self.pick(LORA_A, 1.25)
        root = picker_tests.FakeLayout()
        before = [(slot.model_id, round(slot.scale, 4)) for slot in self.lane.trained]
        submodule("blender.panels").draw_model_row(root, self.lane, "image")
        labels = [call[2] for node in root.walk() for call in node.named("label")]
        self.assertIn({"text": "Studio LoRA (strength 0.8)", "icon": "SHADERFX"}, labels)
        self.assertIn(
            {"text": f"{self.lane.trained[1].name} (strength 1.25)", "icon": "SHADERFX"}, labels
        )
        removes = [
            call
            for node in root.walk()
            for call in node.named("operator")
            if call[1][0] == "scenario.trained_remove"
        ]
        self.assertEqual(len(removes), 2)
        self.assertEqual(
            before, [(slot.model_id, round(slot.scale, 4)) for slot in self.lane.trained]
        )
        self.lane.estimate_state = "READY"
        self.assertEqual(bpy.ops.scenario.trained_remove(lane="image", index=5), {"CANCELLED"})
        self.assertEqual(self.lane.estimate_state, "READY")
        self.assertEqual(bpy.ops.scenario.trained_remove(lane="image", index=-1), {"FINISHED"})
        self.assertEqual(self.lane.estimate_state, "PENDING")
        self.assertFalse(len(self.lane.trained))

    def test_slot_strength_stays_within_its_declared_range_and_reprices(self):
        self.load_catalog()
        self.open_trained()
        self.pick(LORA_A, 0.8)
        slot = self.lane.trained[0]
        self.lane.estimate_state = "READY"
        slot.scale = 3.5
        self.assertEqual(round(slot.scale, 4), 2.0)
        self.assertEqual(self.lane.estimate_state, "PENDING")

    def test_reload_parameters_restores_exactly_the_jobs_trained_choice(self):
        self.load_catalog()
        self.open_trained()
        self.pick(STUDIO_LORA, 0.8)
        records = submodule("core.jobs.records")
        body = {"prompt": PROMPT, "loras": [LORA_A, "model_gone"], "lorasScale": [0.3, 0.6]}
        job = records.JobRecord.new("image", "image", FLUX1, body, meta={"prompt": PROMPT})
        plain = records.JobRecord.new("image", "image", FLUX1, {"prompt": PROMPT})
        self.runtime.state.jobs_view[:] = [job, plain]
        self.assertEqual(bpy.ops.scenario.reload_generation(local_id=job.local_id), {"FINISHED"})
        self.assertEqual(
            [(slot.model_id, round(slot.scale, 4)) for slot in self.lane.trained], [(LORA_A, 0.3)]
        )
        self.assertEqual(self.body()["lorasScale"], [0.3])
        self.assertEqual(bpy.ops.scenario.reload_generation(local_id=plain.local_id), {"FINISHED"})
        self.assertFalse(len(self.lane.trained))

    def test_private_thumbnails_are_cached_per_connection_and_need_one(self):
        self.load_catalog()
        record = self.runtime.state.trained_records[STUDIO_LORA]
        record.raw["thumbnail"] = {"url": "https://cdn.example.invalid/private.jpg"}
        cache = pathlib.Path(
            self.enterContext(tempfile.TemporaryDirectory(prefix="scenario-test-thumbs-"))
        )
        paths = submodule("core.config").Paths(cache / "state", cache, cache / "output")
        self.enterContext(patch.object(self.runtime, "paths", return_value=paths))
        started = []

        def tracked(*args, **kwargs):
            started.append(kwargs)
            return types.SimpleNamespace(start=lambda: None)

        self.enterContext(
            patch.object(self.picker, "threading", types.SimpleNamespace(Thread=tracked))
        )
        self.addCleanup(self.picker._pending_thumbs.clear)
        scope = self.trained.current_scope()
        self.assertEqual(self.picker.thumbnail_scope(record), scope)
        self.assertFalse(self.picker.ensure_thumbnail(record))
        (call,) = started
        self.assertEqual(
            call["args"][1], cache / "thumbs" / "scoped" / scope[:32] / f"{STUDIO_LORA}.jpg"
        )
        with patch.object(self.runtime.state, "job_store", None):
            started.clear()
            self.picker._pending_thumbs.clear()
            self.assertFalse(self.picker.ensure_thumbnail(record))
            self.assertEqual(started, [])
        public = self.runtime.state.trained_records[LORA_A]
        self.assertEqual(self.picker.thumbnail_scope(public), "")
