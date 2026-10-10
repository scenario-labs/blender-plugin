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
from unittest.mock import MagicMock, patch

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
        # Submissions are refused unless a test opts in; they reach this synthetic service only.
        self.accept_submissions, self.submitted = False, []
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
            if request.method == "GET" and path.startswith("/v1/jobs/") and self.accept_submissions:
                job = {
                    "jobId": path.rsplit("/", 1)[1],
                    "status": "in-progress",
                    "jobType": "custom",
                }
                return httpx.Response(200, json={"job": job})
            self.assertEqual(request.method, "POST")
            self.assertEqual(path, f"/v1/generate/custom/{FLUX1}")
            if self.accept_submissions and "dryRun" not in request.url.params:
                self.submitted.append(request.content)
                return httpx.Response(200, json={"job": {"jobId": f"job-{len(self.submitted)}"}})
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

    def test_a_closed_dialog_left_on_the_trained_chip_starts_no_base_reads(self):
        self.load_catalog()
        self.open_trained()
        self.assertEqual(len(self.gets(FLUX1)), 1)
        self.picker.SCENARIO_OT_pick_model.cancel(types.SimpleNamespace(), bpy.context)
        self.assertEqual(self.wm.scenario_picker_category, "trained")  # the chip stays selected
        self.assertFalse(self.picker.trained_view_open())
        # Another project retires the connection with its descriptions and scans.
        self.addCleanup(setattr, self.prefs, "project_id", self.prefs.project_id)
        self.prefs.project_id = "project-b"
        self.runtime.sync_catalog_context()
        self.load_catalog()
        self.assertTrue(self.runtime.state.trained_loaded, self.runtime.state.trained_error)
        self.assertEqual(len(self.gets(FLUX1)), 1)  # delivering the list read no description
        self.assertEqual(self.runtime.state.trained_scans, {})
        self.open_trained()
        self.assertEqual(len(self.gets(FLUX1)), 2)  # the reopened chip reads for this connection

    def test_a_rebuilt_list_keeps_the_highlighted_base_and_strength(self):
        self.load_catalog()
        self.open_trained()
        self.highlight(STUDIO_LORA)
        self.wm.scenario_picker_strength = 0.55
        # Base-description batches and the trained list rebuild the rows while the dialog is open.
        self.picker.refresh_trained()
        items = self.wm.scenario_picker_items
        self.assertEqual(items[self.wm.scenario_picker_index].model_id, STUDIO_LORA)
        self.assertEqual(self.wm.scenario_picker_base, FLUX1)
        self.assertEqual(round(self.wm.scenario_picker_strength, 4), 0.55)
        self.highlight(LORA_A)
        # Another row starts anew, at that LoRA's own declared strength.
        self.assertEqual(round(self.wm.scenario_picker_strength, 4), 0.8)
        self.highlight(STUDIO_LORA)
        self.assertEqual(round(self.wm.scenario_picker_strength, 4), 0.75)
        self.wm.scenario_picker_strength = 0.3
        self.open_trained()  # a new dialog starts from the form, not from the last dialog
        self.highlight(STUDIO_LORA)
        self.assertEqual(round(self.wm.scenario_picker_strength, 4), 0.75)

    def test_an_unusable_base_batch_ends_the_scan_instead_of_hanging(self):
        self.load_catalog()
        self.open_trained()
        scan = self.runtime.state.trained_scans["image"]
        scan["pending"] = True
        malformed = {"catalog": self.runtime.state.catalog, "lane": "image"}
        self.manager.catalog_events.put(("trained_bases", malformed))
        self.generation.process_catalog_events()
        self.assertFalse(scan["pending"])
        self.assertEqual(
            self.trained.scan_status("image"),
            "Could not check every base model: Could not read base model descriptions",
        )

    def test_a_stopped_base_scan_leaves_unread_bases_for_the_next_trained_chip(self):
        extra = [
            {
                "id": f"model_base-{number}",
                "name": f"Zz Base {number}",
                "type": "custom",
                "capabilities": ["txt2img"],
                "privacy": "public",
                "status": "trained",
            }
            for number in range(1, 6)
        ]
        self.public.extend(extra)
        self.load_catalog()
        self.open_trained()
        # Three descriptions after the captured bases fail in a row, which stops the scan.
        self.assertEqual([len(self.gets(record["id"])) for record in extra], [1, 1, 1, 0, 0])
        self.assertTrue(self.trained.scan_status("image").startswith("Could not check"))
        for record in extra:
            self.details[record["id"]] = {
                **record,
                "inputs": [{"name": "prompt", "type": "string"}],
            }
        self.open_trained()  # "choose Trained again to retry"
        self.assertEqual([len(self.gets(record["id"])) for record in extra], [1, 1, 1, 1, 1])
        self.assertEqual(self.trained.scan_status("image"), "")
        self.open_trained()  # failed reads wait for an explicit refresh
        self.assertEqual([len(self.gets(record["id"])) for record in extra], [1, 1, 1, 1, 1])

    def test_the_open_dialog_is_refreshed_when_base_descriptions_arrive(self):
        self.load_catalog()
        self.picker.prepare(bpy.context, "image", "trained")  # starts the base reads
        studio = submodule("blender.studio")

        class Dialog:
            layout = picker_tests.FakeLayout()

        dialog, region = Dialog(), MagicMock()
        self.addCleanup(studio._popups.pop, dialog, None)
        context = types.SimpleNamespace(window_manager=self.wm, region_popup=region)
        self.picker.SCENARIO_OT_pick_model.draw(dialog, context)
        self.assertTrue(self.trained.scan_status("image").startswith("Checking base models"))
        region.tag_refresh_ui.assert_not_called()
        self.settle()
        region.tag_refresh_ui.assert_called()
        rows = {item.model_id: item for item in self.wm.scenario_picker_items}
        self.assertTrue(rows[STUDIO_LORA].available)

    def test_a_row_highlighted_before_its_bases_arrive_runs_with_its_only_base(self):
        self.load_catalog()
        self.picker.prepare(bpy.context, "image", "trained")  # starts the base reads
        self.assertTrue(self.trained.scan_status("image").startswith("Checking base models"))
        items = self.wm.scenario_picker_items
        self.assertEqual((self.wm.scenario_picker_index, items[0].model_id), (0, STUDIO_LORA))
        self.assertIsNone(self.picker.chosen_base())  # no base description has arrived yet
        # The arriving descriptions rebuild the rows and assign the unchanged index 0.
        self.settle()
        self.assertEqual((self.wm.scenario_picker_index, items[0].model_id), (0, STUDIO_LORA))
        self.assertEqual(self.wm.scenario_picker_base, FLUX1)
        self.assertEqual(self.picker.chosen_base().id, FLUX1)
        self.assertEqual(round(self.wm.scenario_picker_strength, 4), 0.75)
        # OK takes the box's "Runs with FLUX.1 Dev" without another click on the row.
        self.assertEqual(bpy.ops.scenario.pick_model(lane="image"), {"FINISHED"})
        self.assertEqual(self.lane.model_id, FLUX1)
        self.assertEqual([slot.model_id for slot in self.lane.trained], [STUDIO_LORA])

    def test_a_reopened_picker_highlights_the_forms_trained_choice(self):
        self.load_catalog()
        self.open_trained()
        self.assertEqual(self.pick(COMPOSITION), {"FINISHED"})
        self.open_trained()
        items = self.wm.scenario_picker_items
        self.assertEqual(items[self.wm.scenario_picker_index].model_id, COMPOSITION)
        offer = self.picker.highlighted_offer()
        self.assertEqual(self.picker.trained_effect(offer, self.picker.chosen_base()), "")

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
        self.assertEqual(round(self.wm.scenario_picker_strength, 4), 0.75)  # visible start
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
        self.assertEqual(self.body()["lorasScale"], [0.85, 0.8])  # LORA_A's own strength
        self.open_trained()
        self.highlight(STUDIO_LORA)
        self.assertEqual(round(self.wm.scenario_picker_strength, 4), 0.85)  # its current strength
        self.assertEqual(self.pick(STUDIO_LORA, 0.4), {"FINISHED"})
        self.assertEqual(self.body()["lorasScale"], [0.4, 0.8])
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

    def test_a_new_lora_starts_at_its_own_strength_or_the_web_app_default(self):
        """As in the Scenario web app: the LoRA's first concept scale, otherwise 0.75."""
        self.load_catalog()
        self.open_trained()
        rna = bpy.types.WindowManager.bl_rna.properties["scenario_picker_strength"]
        self.assertEqual(rna.default, self.picker.STRENGTH_RESET)
        self.highlight(STUDIO_LORA)  # a private LoRA whose record declares no strength
        self.assertEqual(round(self.wm.scenario_picker_strength, 4), 0.75)
        self.wm.scenario_picker_strength = 1.3
        self.wm.scenario_picker_strength = rna.default  # what Reset to Default Value assigns
        self.assertEqual(round(self.wm.scenario_picker_strength, 4), 0.75)
        self.highlight(LORA_A)  # its record lists itself as a concept with scale 0.8
        self.assertEqual(round(self.wm.scenario_picker_strength, 4), 0.8)
        self.wm.scenario_picker_strength = 1.3
        self.wm.scenario_picker_strength = rna.default
        self.assertEqual(round(self.wm.scenario_picker_strength, 4), 0.8)
        self.assertEqual(self.pick(LORA_A), {"FINISHED"})
        self.assertEqual(self.body()["lorasScale"], [0.8])
        # A strength field never set for this base sends the LoRA's start, never the reset value.
        self.open_trained()
        self.highlight(STUDIO_LORA)
        self.picker._ctx["strength"] = None  # the field update then leaves the value alone
        self.wm.scenario_picker_strength = rna.default
        self.assertEqual(self.wm.scenario_picker_strength, self.picker.STRENGTH_RESET)
        self.assertEqual(
            self.picker.apply_trained_choice(bpy.context, "image"), (STUDIO_LORA, "image")
        )
        self.assertEqual(self.body()["lorasScale"], [0.8, 0.75])

    def test_the_starting_strength_stays_within_the_base_range(self):
        scale = next(f for f in self.details[FLUX1]["inputs"] if f["name"] == "lorasScale")
        scale.update({"min": 0.78, "max": 1.5})
        plain = {**self.details[STUDIO_LORA], "id": "model_studio-plain", "name": "Plain LoRA"}
        self.private.append(plain)
        self.details[STUDIO_LORA]["concepts"] = [{"modelId": STUDIO_LORA, "scale": 1.9}]
        self.load_catalog()
        self.open_trained()
        self.highlight("model_studio-plain")
        self.assertEqual(round(self.wm.scenario_picker_strength, 4), 0.78)  # 0.75, raised
        self.highlight(STUDIO_LORA)
        self.assertEqual(round(self.wm.scenario_picker_strength, 4), 1.5)  # its own 1.9, lowered
        self.highlight(LORA_A)
        self.assertEqual(round(self.wm.scenario_picker_strength, 4), 0.8)  # within the range
        self.assertEqual(self.pick(STUDIO_LORA), {"FINISHED"})
        self.assertEqual(self.body()["lorasScale"], [1.5])

    def test_reload_parameters_restores_the_base_default_the_job_ran_with(self):
        scale = next(f for f in self.details[FLUX1]["inputs"] if f["name"] == "lorasScale")
        scale["default"] = 0.65
        self.load_catalog()
        self.open_trained()
        records = submodule("core.jobs.records")
        body = {"prompt": PROMPT, "loras": [LORA_A]}
        job = records.JobRecord.new("image", "image", FLUX1, body, meta={"prompt": PROMPT})
        self.runtime.state.jobs_view[:] = [job]
        self.assertEqual(bpy.ops.scenario.reload_generation(local_id=job.local_id), {"FINISHED"})
        (slot,) = self.lane.trained
        self.assertEqual((slot.model_id, slot.has_scale), (LORA_A, True))
        self.assertEqual(round(slot.scale, 4), 0.65)  # the base default, not the LoRA's 0.8
        # A new choice still starts at the LoRA's own strength or the web app's default.
        self.open_trained()
        self.highlight(STUDIO_LORA)
        self.assertEqual(round(self.wm.scenario_picker_strength, 4), 0.75)

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
        # The Trained models section under the Model row names each LoRA above its strength.
        self.assertIn({"text": "Studio LoRA", "icon": "SHADERFX"}, labels)
        self.assertIn({"text": self.lane.trained[1].name, "icon": "SHADERFX"}, labels)
        strengths = [call[1][1] for node in root.walk() for call in node.named("prop")]
        self.assertEqual(strengths.count("scale"), 2)
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

    def test_reload_parameters_never_invents_a_strength_the_job_did_not_send(self):
        self.load_catalog()
        self.open_trained()  # reads the FLUX.1 Dev description, which declares no default
        records = submodule("core.jobs.records")
        body = {"prompt": PROMPT, "loras": [LORA_A]}
        job = records.JobRecord.new("image", "image", FLUX1, body, meta={"prompt": PROMPT})
        self.runtime.state.jobs_view[:] = [job]
        self.assertEqual(bpy.ops.scenario.reload_generation(local_id=job.local_id), {"FINISHED"})
        (slot,) = self.lane.trained
        self.assertEqual((slot.model_id, slot.has_scale), (LORA_A, False))
        request = self.generation.build_request(self.scene, "image", for_estimate=True)
        self.assertEqual(request.errors, ["LoRA Scale: provide a strength for each LoRA."])

    def test_reload_parameters_warns_about_loras_the_base_can_no_longer_describe(self):
        self.load_catalog()
        self.open_trained()
        records = submodule("core.jobs.records")
        body = {"prompt": PROMPT, "loras": [LORA_A, STUDIO_LORA], "lorasScale": [0.3, 0.6]}
        job = records.JobRecord.new("image", "image", FLUX1, body, meta={"prompt": PROMPT})
        self.runtime.state.jobs_view[:] = [job]
        # The base's LoRA inputs changed since the job ran: its strength input is gone.
        record = self.runtime.state.records[FLUX1]
        record.raw["uiConfig"]["lorasComponent"]["scaleInput"] = "missing"
        operator = types.SimpleNamespace(local_id=job.local_id, report=MagicMock())
        operators = submodule("blender.operators")
        result = operators.SCENARIO_OT_reload_generation.execute(operator, bpy.context)
        self.assertEqual(result, {"FINISHED"})
        self.assertFalse(len(self.lane.trained))
        levels, message = operator.report.call_args.args
        self.assertEqual(levels, {"WARNING"})
        self.assertIn("2 trained model(s) could not be restored", message)
        # A stack this slot cannot describe (misaligned strengths) is not restored silently either.
        record.raw["uiConfig"]["lorasComponent"]["scaleInput"] = "lorasScale"
        misaligned = {"prompt": PROMPT, "loras": [LORA_A], "lorasScale": [0.3, 0.6]}
        self.assertEqual(self.trained.restore(self.lane, "image", record, misaligned), 1)
        self.assertEqual(self.trained.restore(self.lane, "image", record, {"prompt": PROMPT}), 0)

    def test_reload_before_the_trained_list_arrives_keeps_the_jobs_choice_pending(self):
        """Picks wait for the list that names them; a reload never drops them for arriving early."""
        scale = next(f for f in self.details[FLUX1]["inputs"] if f["name"] == "lorasScale")
        scale["default"] = 0.65
        self.load_catalog()
        self.open_trained()  # reads the FLUX.1 Dev description
        state = self.runtime.state
        operators = submodule("blender.operators")
        records = submodule("core.jobs.records")

        def reload(body):
            job = records.JobRecord.new("image", "image", FLUX1, body, meta={"prompt": PROMPT})
            state.jobs_view[:] = [job]
            operator = types.SimpleNamespace(local_id=job.local_id, report=MagicMock())
            result = operators.SCENARIO_OT_reload_generation.execute(operator, bpy.context)
            self.assertEqual(result, {"FINISHED"})
            return operator.report.call_args.args

        def errors():
            return self.generation.build_request(self.scene, "image", for_estimate=True).errors

        def deliver_list():
            self.assertTrue(
                self.trained.request(self.runtime.ensure_manager(), self.runtime.ensure_catalog())
            )
            self.settle()

        self.trained.clear()  # the connection's trained list has not arrived yet
        levels, message = reload(
            {
                "prompt": PROMPT,
                "loras": [LORA_A, STUDIO_LORA, "model_gone"],
                "lorasScale": [0.3, 0.6, 0.9],
            }
        )
        self.assertEqual(levels, {"INFO"})
        self.assertIn("3 trained model(s), checked once the trained model list loads", message)
        self.assertNotIn("could not be restored", message)
        self.assertEqual(
            [(slot.model_id, slot.kind, round(slot.scale, 4)) for slot in self.lane.trained],
            [(LORA_A, "", 0.3), (STUDIO_LORA, "", 0.6), ("model_gone", "", 0.9)],
        )
        self.assertEqual(errors(), [self.trained.LOADING])
        self.lane.estimate_state = "UNAVAILABLE"
        deliver_list()
        self.assertTrue(state.trained_loaded, state.trained_error)
        self.assertEqual(self.lane.estimate_state, "PENDING")  # priced again with the list
        self.assertEqual(
            [(slot.model_id, slot.kind, slot.name) for slot in self.lane.trained],
            [
                (LORA_A, "lora", state.trained_records[LORA_A].name),
                (STUDIO_LORA, "lora", "Studio LoRA"),
                ("model_gone", "", "model_gone"),
            ],
        )
        # A pick the list does not name stays, blocking the price with its reason.
        self.assertEqual(
            errors(), ["Refresh trained models; a selected model is no longer listed."]
        )
        self.assertEqual(bpy.ops.scenario.trained_remove(lane="image", index=2), {"FINISHED"})
        body = self.body()
        self.assertEqual((body["loras"], body["lorasScale"]), ([LORA_A, STUDIO_LORA], [0.3, 0.6]))

        # A composition restored early sends no strength once the list names it, and a
        # failed list read keeps it with the reason until the Trained chip reads it again.
        self.trained.clear()
        self.private_error = 500
        reload({"prompt": PROMPT, "modelId": COMPOSITION})
        deliver_list()
        self.assertFalse(state.trained_loaded)
        self.assertEqual([slot.model_id for slot in self.lane.trained], [COMPOSITION])
        self.assertEqual(errors(), [f"Could not load trained models: {state.trained_error}"])
        self.private_error = None
        self.open_trained()
        self.assertTrue(state.trained_loaded, state.trained_error)
        (slot,) = self.lane.trained
        self.assertEqual((slot.kind, slot.has_scale), ("composition", False))
        body = self.body()
        self.assertEqual(body["modelId"], COMPOSITION)
        self.assertNotIn("lorasScale", body)

    def test_a_composition_reloaded_before_the_list_shows_as_one_without_a_strength(self):
        """The model ID input carries only a composition; the base's default strength is a LoRA's."""
        scale = next(f for f in self.details[FLUX1]["inputs"] if f["name"] == "lorasScale")
        scale["default"] = 0.65
        self.details[COMPOSITION]["name"] = "Snowy Cabins"
        self.load_catalog()
        self.open_trained()  # reads the FLUX.1 Dev description
        state = self.runtime.state
        operators = submodule("blender.operators")
        panels = submodule("blender.panels")
        records = submodule("core.jobs.records")

        def reload(body):
            job = records.JobRecord.new("image", "image", FLUX1, body, meta={"prompt": PROMPT})
            state.jobs_view[:] = [job]
            operator = types.SimpleNamespace(local_id=job.local_id, report=MagicMock())
            result = operators.SCENARIO_OT_reload_generation.execute(operator, bpy.context)
            self.assertEqual(result, {"FINISHED"})

        def choices():
            """The rows of the Trained models section under the Model row, one per choice."""
            root = picker_tests.FakeLayout()
            panels.draw_model_row(root, self.lane, "image")
            return [
                call[2]
                for node in root.walk()
                for call in node.named("label")
                if call[2].get("icon") in ("GROUP", "SHADERFX")
                and call[2].get("text") != "Trained models"
            ]

        self.trained.clear()  # the connection's trained list has not arrived yet
        reload({"prompt": PROMPT, "modelId": COMPOSITION})
        (slot,) = self.lane.trained
        self.assertEqual((slot.kind, slot.has_scale), ("composition", False))
        self.assertEqual(choices(), [{"text": f"{COMPOSITION} (composition)", "icon": "GROUP"}])
        # LoRAs from the stack still wait with the strength the job sent; the section
        # draws its strength field once the list names them LoRAs.
        reload({"prompt": PROMPT, "loras": [LORA_A], "lorasScale": [0.3]})
        self.assertEqual(choices(), [{"text": LORA_A, "icon": "SHADERFX"}])
        (slot,) = self.lane.trained
        self.assertEqual((slot.kind, slot.has_scale, round(slot.scale, 4)), ("", True, 0.3))
        # The delivered list names the composition; it still sends no strength.
        reload({"prompt": PROMPT, "modelId": COMPOSITION})
        self.assertTrue(
            self.trained.request(self.runtime.ensure_manager(), self.runtime.ensure_catalog())
        )
        self.settle()
        self.assertTrue(state.trained_loaded, state.trained_error)
        self.assertEqual(choices(), [{"text": "Snowy Cabins (composition)", "icon": "GROUP"}])
        (slot,) = self.lane.trained
        self.assertEqual((slot.kind, slot.has_scale), ("composition", False))
        body = self.body()
        self.assertEqual(body["modelId"], COMPOSITION)
        self.assertNotIn("lorasScale", body)

    def test_an_adopted_id_replaces_a_price_error_saved_with_the_file(self):
        """A file saved by an earlier version keeps its refusal until the adopted choice reprices."""
        self.load_catalog()
        self.open_trained()  # reads the FLUX.1 Dev description
        params_ui = submodule("blender.params_ui")
        self.lane.model_id = FLUX1
        params_ui.sync_params(self.lane, self.generation.schema_for(FLUX1), FLUX1)
        item = self.lane.params.add()
        item.name, item.ptype, item.model_id = "modelId", "model", FLUX1
        item.str_value, item.enabled = LORA_A, True
        self.lane.estimate_state = "ERROR"
        self.lane.estimate_error = "LoRA or Composition Model is a LoRA."
        # The catalog delivery after opening the file synchronizes the form without repricing it.
        self.generation.on_model_changed(bpy.context, self.lane, mark_dirty=False)
        (slot,) = self.lane.trained
        self.assertEqual((slot.model_id, slot.kind, slot.has_scale), (LORA_A, "lora", False))
        self.assertEqual(self.lane.estimate_state, "PENDING")
        request = self.generation.build_request(self.scene, "image", for_estimate=True)
        self.assertEqual(request.errors, ["LoRA Scale: provide a strength for each LoRA."])

    def test_a_price_asked_before_the_trained_list_arrives_runs_once_it_arrives(self):
        """A form priced while the list loads, or after its read failed, is priced again."""
        self.load_catalog()
        self.open_trained()  # reads the FLUX.1 Dev description
        self.assertEqual(self.pick(STUDIO_LORA, 0.8), {"FINISHED"})

        def price():
            self.generation.request_estimate(self.scene, "image")
            return self.lane.estimate_state, self.lane.estimate_error

        def deliver_list():
            self.assertTrue(
                self.trained.request(self.runtime.ensure_manager(), self.runtime.ensure_catalog())
            )
            self.settle()

        self.trained.clear()  # the connection's trained list has not arrived yet
        self.assertEqual(price(), ("UNAVAILABLE", self.trained.LOADING))
        self.private_error = 500
        deliver_list()
        self.assertEqual(self.lane.estimate_state, "PENDING")
        reason = f"Could not load trained models: {self.runtime.state.trained_error}"
        self.assertEqual(price(), ("UNAVAILABLE", reason))
        self.private_error = None
        deliver_list()
        self.assertEqual(self.lane.estimate_state, "PENDING")
        self.posts.clear()
        price()
        self.deliver_quote()
        self.assertEqual(self.lane.estimate_state, "READY", self.lane.estimate_error)
        self.assertTrue(submodule("blender.panels").generate_enabled(self.lane, "image"))
        (sent,) = self.posts
        self.assertEqual((sent["loras"], sent["lorasScale"]), ([STUDIO_LORA], [0.8]))

    def test_an_id_adopted_before_the_trained_list_arrives_shows_the_current_reason(self):
        """A file opened before the list arrives keeps no refusal an earlier version saved."""
        self.load_catalog()
        self.open_trained()  # reads the FLUX.1 Dev description
        params_ui = submodule("blender.params_ui")
        self.lane.model_id = FLUX1
        params_ui.sync_params(self.lane, self.generation.schema_for(FLUX1), FLUX1)
        self.trained.clear()  # the connection's trained list has not arrived yet
        item = self.lane.params.add()
        item.name, item.ptype, item.model_id = "modelId", "model", FLUX1
        item.str_value, item.enabled = LORA_A, True
        self.lane.estimate_state = "ERROR"
        self.lane.estimate_error = "LoRA or Composition Model is a LoRA."
        self.generation.on_model_changed(bpy.context, self.lane, mark_dirty=False)
        self.assertEqual(self.lane.estimate_state, "PENDING")
        self.generation.request_estimate(self.scene, "image")
        self.assertEqual(
            (self.lane.estimate_state, self.lane.estimate_error),
            ("UNAVAILABLE", self.trained.LOADING),
        )
        self.assertTrue(
            self.trained.request(self.runtime.ensure_manager(), self.runtime.ensure_catalog())
        )
        self.settle()
        self.assertEqual(self.lane.estimate_state, "PENDING")
        self.generation.request_estimate(self.scene, "image")
        self.assertEqual(
            (self.lane.estimate_state, self.lane.estimate_error),
            ("UNAVAILABLE", "LoRA Scale: provide a strength for each LoRA."),
        )

    def test_a_lora_list_typed_by_an_earlier_version_reprices_the_form(self):
        """Earlier versions drew a base's LoRA lists as text, which validation always refused."""
        self.load_catalog()
        self.open_trained()  # reads the FLUX.1 Dev description
        params_ui = submodule("blender.params_ui")
        self.lane.model_id = FLUX1
        params_ui.sync_params(self.lane, self.generation.schema_for(FLUX1), FLUX1)
        for name, ptype, value in (
            ("loras", "model_array", LORA_A),
            ("lorasScale", "number_array", "0.8"),
        ):
            item = self.lane.params.add()
            item.name, item.ptype, item.model_id = name, ptype, FLUX1
            item.str_value, item.enabled = value, True
        self.lane.estimate_state = "UNAVAILABLE"
        self.lane.estimate_error = "Flux LoRA: expected an array, even for a single item."
        # The catalog delivery after opening the file synchronizes the form without repricing it.
        self.generation.on_model_changed(bpy.context, self.lane, mark_dirty=False)
        self.assertLess(self.lane.params.find("loras"), 0)
        self.assertLess(self.lane.params.find("lorasScale"), 0)
        self.assertFalse(len(self.lane.trained))  # only the model input held a whole choice
        self.assertEqual(self.lane.estimate_state, "PENDING")
        self.posts.clear()
        self.generation.request_estimate(self.scene, "image")
        self.deliver_quote()
        self.assertEqual(self.lane.estimate_state, "READY", self.lane.estimate_error)
        (sent,) = self.posts
        self.assertNotIn("loras", sent)
        # The form is priced once: a later catalog delivery keeps the ready price.
        self.generation.on_model_changed(bpy.context, self.lane, mark_dirty=False)
        self.assertEqual(self.lane.estimate_state, "READY")

    def test_an_id_typed_by_an_earlier_version_becomes_the_trained_choice(self):
        """Earlier versions drew the base's LoRA inputs as text; a saved ID is kept, not dropped."""
        self.load_catalog()
        self.open_trained()  # reads the FLUX.1 Dev description
        params_ui = submodule("blender.params_ui")
        self.lane.model_id = FLUX1
        schema = self.generation.schema_for(FLUX1)

        def typed(value, enabled=True):
            item = self.lane.params.add()
            item.name, item.ptype, item.model_id = "modelId", "model", FLUX1
            item.str_value, item.enabled = value, enabled
            params_ui.sync_params(self.lane, schema, FLUX1)
            self.assertLess(self.lane.params.find("modelId"), 0)  # still never a text field

        typed(COMPOSITION, enabled=False)
        self.assertFalse(len(self.lane.trained))  # a disabled field sent nothing before either
        typed(COMPOSITION)
        (slot,) = self.lane.trained
        self.assertEqual(
            (slot.model_id, slot.kind, slot.has_scale, slot.get(self.trained.SCOPE)),
            (COMPOSITION, "composition", False, self.trained.current_scope()),
        )
        body = self.body()
        self.assertEqual(body["modelId"], COMPOSITION)
        self.assertNotIn("loras", body)
        typed("model_other")
        self.assertEqual([slot.model_id for slot in self.lane.trained], [COMPOSITION])
        self.lane.trained.clear()
        typed("model_gone")
        self.assertEqual([slot.model_id for slot in self.lane.trained], ["model_gone"])
        request = self.generation.build_request(self.scene, "image", for_estimate=True)
        self.assertEqual(
            request.errors, ["Refresh trained models; a selected model is no longer listed."]
        )

    def test_render_form_inspection_lists_the_trained_choice_its_quotes_include(self):
        self.load_catalog()
        render = self.scene.scenario.lane_state("render_image")
        slot = render.trained.add()
        slot.model_id, slot.kind, slot.lane = LORA_A, "lora", "render_image"
        slot.fmin, slot.fmax, slot.has_scale, slot.scale = 0.0, 2.0, True, 0.8
        slot[self.trained.SCOPE] = self.trained.current_scope()
        result = submodule("mcp.tools_scenario").render_form({"lane": "render_image"})
        self.assertEqual(
            result["trained_models"], [{"model_id": LORA_A, "kind": "lora", "strength": 0.8}]
        )
        render.trained.clear()
        result = submodule("mcp.tools_scenario").render_form({"lane": "render_image"})
        self.assertEqual(result["trained_models"], [])

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
