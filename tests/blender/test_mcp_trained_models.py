# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Trained models through local MCP, with the native forms' payloads and defaults (#97).

These tests reuse the synthetic service of test_trained_models: the captured
public FLUX.1 Dev and Z-Image bases, public LoRAs and a composition, plus
synthetic private records. Nothing reaches the network. Submissions are
answered only where a test opts in, by that synthetic service; nothing is spent.
"""

import hashlib
import json
import unittest
from concurrent.futures import ThreadPoolExecutor

import bpy
import test_trained_models as trained_tests
from helpers import submodule

FLUX1 = trained_tests.FLUX1
ZIMAGE = trained_tests.ZIMAGE
LORA_A = trained_tests.LORA_A
FLUX2_LORA = trained_tests.FLUX2_LORA
COMPOSITION = trained_tests.COMPOSITION
STUDIO_LORA = trained_tests.STUDIO_LORA
STUDIO_VOICE = trained_tests.STUDIO_VOICE
STUDIO_CUSTOM = trained_tests.STUDIO_CUSTOM
PROMPT = trained_tests.PROMPT
STACK_LABEL = "FLUX.1 Dev · Studio LoRA (+1)"
STACK = {"prompt": PROMPT, "loras": [STUDIO_LORA, LORA_A], "lorasScale": [0.8, 1.25]}


def _shared(name):
    """A helper of test_trained_models' tests, without binding that TestCase here.

    Binding the class in this module would make discovery run its tests twice.
    """
    return getattr(trained_tests.TrainedModelTests, name)


class McpTrainedModelTests(unittest.TestCase):
    setUp = _shared("setUp")
    settle = _shared("settle")
    load_catalog = _shared("load_catalog")
    open_trained = _shared("open_trained")
    highlight = _shared("highlight")
    pick = _shared("pick")
    body = _shared("body")
    deliver_quote = _shared("deliver_quote")
    gets = _shared("gets")

    # -- helpers -------------------------------------------------------------------
    @property
    def tools(self):
        return submodule("mcp.tools_scenario")

    @property
    def error(self):
        return submodule("core.api.errors").ScenarioError

    @staticmethod
    def finish(deferred):
        """Run a deferred tool like the MCP server: work off the main thread, delivery on it."""
        with ThreadPoolExecutor(max_workers=1) as worker:
            value = worker.submit(deferred.run).result(5)
        return deferred.finish(value)

    def mcp_estimate(self, parameters, model_id=FLUX1, lane="image"):
        return self.finish(
            self.tools.estimate_cost({"model_id": model_id, "parameters": parameters, "lane": lane})
        )

    def estimate_of(self, quote):
        jobs = self.runtime.state.model_jobs
        return jobs.finish_quote(jobs.quotes[quote["quote_id"]])

    def ui_estimate(self):
        self.generation.request_estimate(self.scene, "image")
        self.deliver_quote()
        self.assertEqual(self.lane.estimate_state, "READY", self.lane.estimate_error)
        ticket = self.runtime.state.estimates[self.lane.estimate_key]
        return self.runtime.state.model_jobs.finish_quote(ticket)

    def choose_stack(self):
        """FLUX.1 Dev in the Image form with the private Studio LoRA at 0.8 and a public LoRA at 1.25."""
        self.load_catalog()
        self.open_trained()
        self.pick(STUDIO_LORA, 0.8)
        self.open_trained()
        self.pick(LORA_A, 1.25)

    def wait_submissions(self):
        owner = self.runtime.state.model_jobs
        for task in tuple(owner.submissions.values()):
            try:
                task.result(5)
            except Exception:
                pass  # the stored records below establish the outcome
        self.runtime.sync_catalog_context()

    def assert_refused(self, call, message):
        with self.assertRaises((ValueError, self.error)) as caught:
            call()
        self.assertIn(message, str(caught.exception))

    # -- payload parity: the key acceptance -------------------------------------
    def test_the_same_stack_through_the_form_and_mcp_has_one_payload_sha256_and_target(self):
        self.accept_submissions = True
        self.choose_stack()
        ui = self.ui_estimate()
        quote = self.mcp_estimate(dict(STACK))
        mcp = self.estimate_of(quote)
        self.assertEqual((ui.target_id, mcp.target_id), (FLUX1, FLUX1))
        self.assertEqual(ui.payload_json, mcp.payload_json)
        sent = json.loads(ui.payload_json)
        self.assertEqual((sent["loras"], sent["lorasScale"]), (STACK["loras"], [0.8, 1.25]))
        self.assertNotIn("modelId", sent)
        # The form's strength field holds 0.8 in 32-bit storage; both send the declared 0.8.
        self.assertIn(b'"strength": 0.8,', ui.payload_json)
        self.assertEqual(len(self.posts), 2)  # one dry run each
        self.assertEqual(self.submitted, [])
        # Both approvals are spent once, against the synthetic service only.
        view = self.generation.submit_generation(bpy.context, "image")
        result = self.tools.generate(
            {
                "lane": "image",
                "model_id": FLUX1,
                "parameters": dict(STACK),
                "quote_id": quote["quote_id"],
                "approved_cost": quote["cu_cost_exact"],
            }
        )
        self.wait_submissions()
        store = self.runtime.state.job_store
        references = (view.local_id, result["local_id"])
        intents = [store.get(reference).intent for reference in references]
        digest = hashlib.sha256(ui.payload_json).hexdigest()
        self.assertEqual([intent.payload_sha256 for intent in intents], [digest, digest])
        self.assertEqual([intent.target_id for intent in intents], [FLUX1, FLUX1])
        self.assertEqual(len(self.submitted), 2)
        self.assertEqual(self.submitted[0], self.submitted[1])
        self.assertEqual(json.loads(self.submitted[0]), sent)
        # Job views name the choice the same way on both surfaces.
        owner = self.runtime.state.model_jobs
        metas = [owner.views[reference].meta for reference in references]
        self.assertEqual([meta["model_name"] for meta in metas], [STACK_LABEL, STACK_LABEL])
        self.assertEqual(metas[0]["trained_models"], metas[1]["trained_models"])
        self.assertEqual(
            [(item["model_id"], item["strength"]) for item in metas[1]["trained_models"]],
            [(STUDIO_LORA, 0.8), (LORA_A, 1.25)],
        )

    def test_the_same_composition_through_the_form_and_mcp_has_one_payload(self):
        self.load_catalog()
        self.open_trained()
        self.pick(COMPOSITION)
        ui = self.ui_estimate()
        mcp = self.estimate_of(self.mcp_estimate({"prompt": PROMPT, "modelId": COMPOSITION}))
        self.assertEqual(ui.payload_json, mcp.payload_json)
        self.assertEqual(
            hashlib.sha256(ui.payload_json).digest(), hashlib.sha256(mcp.payload_json).digest()
        )
        self.assertEqual(json.loads(mcp.payload_json)["modelId"], COMPOSITION)
        # Spelling the schema defaults out changes nothing either.
        echoed = {"prompt": PROMPT, "modelId": COMPOSITION, "loras": [], "lorasScale": []}
        self.assertEqual(self.estimate_of(self.mcp_estimate(echoed)).payload_json, ui.payload_json)
        # An optional field switched off in the form matches null through MCP.
        self.lane.params["controlStart"].enabled = False
        ui = self.ui_estimate()
        mcp = self.mcp_estimate({"prompt": PROMPT, "modelId": COMPOSITION, "controlStart": None})
        self.assertEqual(self.estimate_of(mcp).payload_json, ui.payload_json)

    # -- refusals before any request ------------------------------------------------
    def test_choices_no_form_could_make_are_refused_before_any_request(self):
        extra = [
            {**self.private[0], "id": f"model_extra-{index}", "name": f"Extra {index}"}
            for index in range(6)
        ]
        self.private.extend(extra)
        self.load_catalog()
        self.open_trained()  # reads the FLUX.1 Dev description
        self.calls.clear()
        seven = [STUDIO_LORA, *(record["id"] for record in extra)]
        cases = [
            (
                {"loras": [FLUX2_LORA], "lorasScale": [0.8]},
                "Flux LoRA accepts flux.1-lora models, not flux.2-dev-lora.",
            ),
            ({"loras": [LORA_A], "lorasScale": [2.5]}, "LoRA Scale: use a strength from 0 to 2."),
            ({"loras": [LORA_A]}, "LoRA Scale: provide a strength for each LoRA."),
            ({"loras": [LORA_A, LORA_A], "lorasScale": [0.5, 0.5]}, "choose each LoRA once"),
            ({"loras": seven, "lorasScale": [0.5] * 7}, "Flux LoRA: use at most 6 LoRAs."),
            ({"loras": [LORA_A], "lorasScale": [0.83333]}, "at most 4 decimal places"),
            ({"loras": [LORA_A, STUDIO_LORA], "lorasScale": [0.5]}, "one strength per LoRA"),
            ({"modelId": COMPOSITION, "loras": [LORA_A]}, "Use a composition on its own"),
            ({"modelId": COMPOSITION, "lorasScale": [0.5]}, "applies its own strengths"),
            (
                {"modelId": LORA_A},
                "LoRA or Composition Model is a LoRA. Add it to Flux LoRA with a strength instead.",
            ),
            (
                {"loras": ["model_gone"], "lorasScale": [0.5]},
                "Refresh trained models; a selected model is no longer listed.",
            ),
            (
                {"loras": [STUDIO_VOICE], "lorasScale": [0.5]},
                "Only LoRAs and compositions run through a base model.",
            ),
        ]
        for parameters, message in cases:
            with self.subTest(parameters=parameters):
                self.assert_refused(
                    lambda parameters=parameters: self.tools.estimate_cost(
                        {"model_id": FLUX1, "parameters": {"prompt": PROMPT, **parameters}}
                    ),
                    message,
                )
        self.assert_refused(
            lambda: self.tools.estimate_cost(
                {"model_id": FLUX1, "parameters": dict(STACK), "lane": "video"}
            ),
            "Trained models run in the image and render_image lanes",
        )
        self.assertEqual(self.calls, [])  # no description, quote or any other request
        self.assertEqual(self.posts, [])
        self.assertEqual(
            self.runtime.state.model_jobs.quotes if self.runtime.state.model_jobs else {}, {}
        )

    def test_a_composition_in_the_lora_stack_is_refused_not_moved(self):
        """The service refuses it in that input (#374); it is never sent in modelId instead."""
        self.load_catalog()
        self.open_trained()  # reads the FLUX.1 Dev description
        quote = self.mcp_estimate({"prompt": PROMPT})  # a plain quote for the generate case
        self.calls.clear()
        self.posts.clear()
        stacked = (
            "Flux LoRA [{}] is a composition; Flux LoRA accepts flux.1-lora. "
            "Use it alone in LoRA or Composition Model, without a strength."
        )
        cases = [
            ({"loras": [COMPOSITION]}, stacked.format(1)),
            ({"loras": [COMPOSITION], "lorasScale": [0.8]}, stacked.format(1)),
            ({"loras": [LORA_A, COMPOSITION], "lorasScale": [0.5, 0.5]}, stacked.format(2)),
        ]
        approval = {"quote_id": quote["quote_id"], "approved_cost": quote["cu_cost_exact"]}
        for parameters, message in cases:
            request = {"model_id": FLUX1, "parameters": {"prompt": PROMPT, **parameters}}
            with self.subTest(parameters=parameters):
                for tool, args in (
                    (self.tools.estimate_cost, request),
                    (self.tools.generate, {**request, "lane": "image", **approval}),
                ):
                    with self.assertRaises((ValueError, self.error)) as caught:
                        tool(args)
                    self.assertEqual(str(caught.exception), message)
                    self.assertNotIn("remove the strength", str(caught.exception))
        self.assertEqual(self.calls, [])  # no description, quote or any other request
        self.assertEqual((self.posts, self.submitted), ([], []))
        self.assertEqual(self.runtime.state.job_store.records(), ())

    def test_a_trained_model_as_model_id_gets_a_final_refusal_without_repeated_reads(self):
        """A LoRA or composition has no schema of its own; polling it must not loop on reads."""
        route = (
            "Call list_models(source=trained) for its routes, then pass the route's base as "
            "model_id with this ID in the route's model_input"
        )
        lora = (
            "This model is a LoRA: it has no inputs of its own and runs only through a base model "
            f"that accepts LoRAs. {route} and a strength in its scale_input."
        )
        composition = (
            "This model is a composition: it has no inputs of its own and runs only through a "
            f"base model that accepts compositions. {route}, without a strength."
        )
        self.load_catalog()
        self.calls.clear()

        def calls(model_id):
            return (
                lambda: self.tools.model_schema({"model_id": model_id}),
                lambda: self.tools.estimate_cost(
                    {"model_id": model_id, "parameters": {"prompt": PROMPT}}
                ),
            )

        # Listed private and public trained models are refused before any request.
        for model_id, message in ((STUDIO_LORA, lora), (LORA_A, lora), (COMPOSITION, composition)):
            with self.subTest(model_id=model_id):
                for _ in range(2):
                    for call in calls(model_id):
                        self.assert_refused(call, message)
                    self.settle()
        self.assertEqual(self.calls, [])
        # An unlisted LoRA (a composition's concept) is read once: its description has no
        # inputs, so every later call gets the same final answer without another read.
        concept = trained_tests.load(f"public/{COMPOSITION}.json")["concepts"][0]["modelId"]
        self.assertNotIn(concept, self.runtime.state.trained_records)
        with self.assertRaisesRegex(self.error, "Loading the model description"):
            self.tools.model_schema({"model_id": concept})
        self.settle()
        for _ in range(3):
            for call in calls(concept):
                self.assert_refused(call, lora)
            self.settle()
        self.assertEqual(len(self.gets(concept)), 1)
        # The same holds for any description without inputs; it is not a trained model.
        plain = "model_no-inputs"
        self.details[plain] = {"id": plain, "name": "No Inputs", "type": "custom"}
        with self.assertRaisesRegex(self.error, "Loading the model description"):
            self.tools.model_schema({"model_id": plain})
        self.settle()
        for _ in range(3):
            for call in calls(plain):
                self.assert_refused(
                    call, "This model declares no inputs, so it cannot run; choose another"
                )
            self.settle()
        self.assertEqual(len(self.gets(plain)), 1)
        self.assertEqual(self.posts, [])

    def test_a_failed_trained_list_blocks_only_requests_that_name_trained_models(self):
        self.private_error = 500
        self.load_catalog()
        state = self.runtime.state
        self.assertFalse(state.trained_loaded)
        self.open_trained()  # the Trained chip reads the private list again, still failing
        self.lane.model_id = FLUX1  # reads its description, which declares the LoRA inputs
        self.settle()
        self.assertTrue(state.records[FLUX1].parameters)
        self.calls.clear()
        self.assert_refused(
            lambda: self.tools.estimate_cost({"model_id": FLUX1, "parameters": dict(STACK)}),
            "Could not load trained models",
        )
        self.assertEqual(self.calls, [])  # a failed list is not read again implicitly
        plain = self.mcp_estimate({"prompt": PROMPT})
        self.assertEqual(plain["model_id"], FLUX1)
        # list_models(source=trained) reads it again, like the picker's Trained chip.
        self.private_error = None
        with self.assertRaisesRegex(RuntimeError, "still loading"):
            self.tools.list_models({"lane": "image", "source": "trained"})
        self.settle()
        self.assertTrue(state.trained_loaded, state.trained_error)
        self.assertEqual(
            self.estimate_of(self.mcp_estimate(dict(STACK))).payload["lorasScale"], [0.8, 1.25]
        )

    def test_generate_needs_the_estimated_choice_and_its_exact_price(self):
        self.load_catalog()
        self.open_trained()
        parameters = {"prompt": PROMPT, "loras": [STUDIO_LORA], "lorasScale": [0.8]}
        quote = self.mcp_estimate(parameters)
        self.assertEqual(quote["cu_cost_exact"], "10.75")
        args = {
            "lane": "image",
            "model_id": FLUX1,
            "parameters": parameters,
            "quote_id": quote["quote_id"],
            "approved_cost": quote["cu_cost_exact"],
        }
        for changes in (
            {"parameters": {**parameters, "lorasScale": [0.85]}},
            {"parameters": {**parameters, "loras": [LORA_A]}},
            {"parameters": {"prompt": PROMPT}},
            {"approved_cost": "10.7500"},
            {"approved_cost": "10"},
        ):
            with self.subTest(changes=changes):
                with self.assertRaisesRegex(self.error, "changed; estimate again"):
                    self.tools.generate({**args, **changes})
        self.assertEqual(self.submitted, [])
        self.assertEqual(self.runtime.state.job_store.records(), ())

    # -- listing and schemas ----------------------------------------------------------
    def test_list_models_offers_the_pickers_trained_rows_with_their_routes(self):
        self.load_catalog()
        first = self.tools.list_models({"lane": "image", "source": "trained"})
        self.assertTrue(first["bases"]["pending"])  # base descriptions are read like the chip's
        self.assertIn("call again", first["note"])
        self.settle()
        result = self.tools.list_models({"lane": "image", "source": "trained"})
        self.assertEqual(result["bases"], {"checked": 1, "total": 1, "pending": False, "error": ""})
        self.assertNotIn("note", result)
        rows = {row["id"]: row for row in result["trained"]}
        self.assertEqual(
            [(row["id"], row["available"]) for row in result["trained"]],
            [
                (STUDIO_LORA, True),
                (LORA_A, True),
                (COMPOSITION, True),
                (STUDIO_VOICE, False),
                (FLUX2_LORA, False),
            ],
        )
        self.assertNotIn(STUDIO_CUSTOM, rows)  # a private custom model is not a LoRA
        studio = rows[STUDIO_LORA]
        self.assertEqual(
            (studio["kind"], studio["type"], studio["private"]), ("lora", "flux.1-lora", True)
        )
        self.assertEqual(
            studio["routes"],
            [
                {
                    "route": "stack",
                    "model_id": FLUX1,
                    "name": "FLUX.1 Dev",
                    "model_input": "loras",
                    "scale_input": "lorasScale",
                    "scale_range": [0, 2],
                    "scale_step": 0.05,
                    "default_scale": None,
                    "min_items": 0,
                    "max_items": 6,
                }
            ],
        )
        self.assertFalse(rows[LORA_A]["private"])
        self.assertEqual(
            rows[COMPOSITION]["routes"],
            [
                {
                    "route": "composition",
                    "model_id": FLUX1,
                    "name": "FLUX.1 Dev",
                    "model_input": "modelId",
                }
            ],
        )
        self.assertTrue(rows[COMPOSITION]["concepts"])
        self.assertEqual(
            rows[FLUX2_LORA]["reason"],
            "No base model in this form accepts flux.2-dev-lora models.",
        )
        self.assertEqual(
            rows[STUDIO_VOICE]["reason"], "Not available in Blender: no base model runs this type."
        )
        # The picker draws the same rows from the same reads.
        self.open_trained()
        self.assertEqual(
            [(item.model_id, item.available) for item in self.wm.scenario_picker_items],
            [(row["id"], row["available"]) for row in result["trained"]],
        )
        self.assertEqual(len(self.gets(FLUX1)), 1)  # descriptions are cached per connection
        self.assertEqual(self.posts, [])
        everything = self.tools.list_models({"lane": "image", "source": "all"})
        self.assertIn(FLUX1, [model["id"] for model in everything["models"]])
        self.assertEqual(everything["trained"], result["trained"])
        catalog = self.tools.list_models({"lane": "image"})
        self.assertEqual(set(catalog), {"lane", "models"})
        self.assertNotIn(LORA_A, [model["id"] for model in catalog["models"]])
        query = self.tools.list_models({"lane": "image", "source": "trained", "query": "studio"})
        self.assertEqual([row["id"] for row in query["trained"]], [STUDIO_LORA, STUDIO_VOICE])
        self.assert_refused(
            lambda: self.tools.list_models({"lane": "video", "source": "trained"}),
            "Trained models run in the image and render_image lanes",
        )
        self.assert_refused(
            lambda: self.tools.list_models({"lane": "image", "source": "private"}),
            "source must be one of",
        )

    def test_model_schema_reports_the_bases_lora_inputs_and_their_roles(self):
        self.load_catalog()
        self.open_trained()
        schema = self.tools.model_schema({"model_id": FLUX1})
        self.assertEqual(
            schema["lora_component"],
            {
                "model_input": "loras",
                "scale_input": "lorasScale",
                "model_id_input": "modelId",
                "model_types": ["flux.1-lora"],
                "model_id_types": ["flux.1-lora", "flux.1-composition"],
                "min_items": 0,
                "max_items": 6,
                "scale_range": [0, 2],
                "scale_step": 0.05,
                "scale_default": None,
            },
        )
        params = {item["name"]: item for item in schema["parameters"]}
        self.assertEqual(
            (params["loras"]["role"], params["loras"]["model_types"], params["loras"]["max_items"]),
            ("lora_models", ["flux.1-lora"], 6),
        )
        self.assertEqual(
            (params["lorasScale"]["role"], params["lorasScale"]["range"]),
            ("lora_strengths", [0, 2]),
        )
        self.assertEqual(params["modelId"]["role"], "composition")
        self.assertEqual(params["modelId"]["model_types"], ["flux.1-lora", "flux.1-composition"])
        self.assertNotIn("role", params["prompt"])
        self.assertNotIn("model_types", params["prompt"])
        zimage = self.tools.model_schema({"model_id": ZIMAGE})["lora_component"]
        self.assertEqual(
            zimage["model_types"], ["zimage-lora", "zimage-turbo-lora", "zimage-de-turbo-lora"]
        )

    # -- defaults ---------------------------------------------------------------------
    def test_model_defaults_follow_the_forms_rules_and_scope(self):
        self.load_catalog()
        self.open_trained()
        defaults = submodule("blender.trained_defaults")
        got = self.tools.model_defaults({})
        self.assertEqual(
            got["lanes"],
            [
                {"lane": "image", "revision": 0, "default": None},
                {"lane": "render_image", "revision": 0, "default": None},
            ],
        )
        context = got["context_id"]
        args = {
            "action": "set",
            "lane": "image",
            "context_id": context,
            "expected_revision": 0,
            "base_model_id": FLUX1,
            "picks": [
                {"model_id": STUDIO_LORA, "scale": 0.8},
                {"model_id": LORA_A, "scale": 1.25},
            ],
        }
        self.posts.clear()
        (saved,) = self.tools.model_defaults(args)["lanes"]
        self.assertEqual(
            saved,
            {
                "lane": "image",
                "revision": 1,
                "default": {
                    "route": "stack",
                    "base_model_id": FLUX1,
                    "picks": [
                        {"model_id": STUDIO_LORA, "scale": 0.8},
                        {"model_id": LORA_A, "scale": 1.25},
                    ],
                },
                "label": STACK_LABEL,
                "available": True,
                "parameters": {"loras": [STUDIO_LORA, LORA_A], "lorasScale": [0.8, 1.25]},
            },
        )
        self.assertEqual(self.posts, [])  # saving requests no price
        listed = self.tools.list_models({"lane": "image", "source": "trained"})["trained"]
        marked = {row["id"]: row for row in listed if row.get("default")}
        self.assertEqual(set(marked), {STUDIO_LORA, LORA_A})
        self.assertEqual(
            [route.get("default") for route in marked[LORA_A]["routes"]], [True]
        )  # the FLUX.1 Dev route the default uses
        # The native form reads the same default: this Image form had no choice, so it takes it.
        self.assertEqual(defaults.view(self.lane, "image").label, STACK_LABEL)
        self.assertEqual(
            (self.lane.model_id, [(s.model_id, round(s.scale, 4)) for s in self.lane.trained]),
            (FLUX1, [(STUDIO_LORA, 0.8), (LORA_A, 1.25)]),
        )
        # Using the default's parameters through MCP prices the form's exact payload.
        ui = self.ui_estimate()
        mcp = self.estimate_of(self.mcp_estimate({"prompt": PROMPT, **saved["parameters"]}))
        self.assertEqual(ui.payload_json, mcp.payload_json)
        # A stale revision, and choices the forms would refuse, change nothing.
        self.assert_refused(
            lambda: self.tools.model_defaults(args), "Review the project default again"
        )
        refused = [
            ([{"model_id": FLUX2_LORA, "scale": 0.8}], FLUX1, "accepts flux.1-lora models"),
            ([{"model_id": COMPOSITION, "scale": 0.5}], FLUX1, "applies its own strengths"),
            ([{"model_id": LORA_A}], FLUX1, "provide a strength for each LoRA"),
            ([{"model_id": LORA_A, "scale": 0.8}], ZIMAGE, "Z-Image LoRA accepts"),
            ([{"model_id": LORA_A, "scale": 0.8}], "model_unknown", "not in the model list"),
            ([], FLUX1, "Choose a LoRA or composition"),
        ]
        for picks, base, message in refused:
            with self.subTest(picks=picks, base=base):
                self.assert_refused(
                    lambda picks=picks, base=base: self.tools.model_defaults(
                        {**args, "expected_revision": 1, "picks": picks, "base_model_id": base}
                    ),
                    message,
                )
        self.assertEqual(self.tools.model_defaults({"lane": "image"})["lanes"][0], saved)
        # Another project neither sees the default nor clears it with this context.
        original = self.prefs.project_id
        self.addCleanup(setattr, self.prefs, "project_id", original)
        self.prefs.project_id = "project-b"
        other = self.tools.model_defaults({"lane": "image"})
        self.assertNotEqual(other["context_id"], context)
        self.assertEqual(other["lanes"], [{"lane": "image", "revision": 0, "default": None}])
        self.assert_refused(
            lambda: self.tools.model_defaults(
                {"action": "clear", "lane": "image", "context_id": context, "expected_revision": 1}
            ),
            "credentials or project changed",
        )
        self.prefs.project_id = original
        back = self.tools.model_defaults({"lane": "image"})
        self.assertEqual(back["lanes"][0]["default"], saved["default"])
        (cleared,) = self.tools.model_defaults(
            {
                "action": "clear",
                "lane": "image",
                "context_id": back["context_id"],
                "expected_revision": 1,
            }
        )["lanes"]
        self.assertEqual(cleared, {"lane": "image", "revision": 2, "default": None})
        self.assert_refused(
            lambda: self.tools.model_defaults({"action": "set", "lane": "video"}),
            "lane must be image or render_image",
        )

    def test_a_saved_composition_default_reports_its_parameters(self):
        self.load_catalog()
        self.open_trained()
        context = self.tools.model_defaults({"lane": "render_image"})["context_id"]
        (saved,) = self.tools.model_defaults(
            {
                "action": "set",
                "lane": "render_image",
                "context_id": context,
                "expected_revision": 0,
                "base_model_id": FLUX1,
                "picks": [{"model_id": COMPOSITION}],
            }
        )["lanes"]
        self.assertEqual(saved["default"]["route"], "composition")
        self.assertEqual(saved["parameters"], {"modelId": COMPOSITION})
        render = self.scene.scenario.lane_state("render_image")
        inspected = self.tools.render_form({"lane": "render_image"})
        self.assertEqual(
            inspected["trained_models"],
            [{"model_id": COMPOSITION, "kind": "composition", "strength": None}],
        )
        self.assertEqual(render.model_id, FLUX1)

    def test_a_listing_cut_to_its_limit_keeps_the_rows_the_default_uses(self):
        self.load_catalog()
        self.open_trained()
        context = self.tools.model_defaults({"lane": "image"})["context_id"]
        self.tools.model_defaults(
            {
                "action": "set",
                "lane": "image",
                "context_id": context,
                "expected_revision": 0,
                "base_model_id": FLUX1,
                "picks": [{"model_id": COMPOSITION}],
            }
        )
        # The composition is the third row; a cut to two still shows the default.
        self.addCleanup(setattr, self.tools, "TRAINED_LIMIT", self.tools.TRAINED_LIMIT)
        self.tools.TRAINED_LIMIT = 2
        listed = self.tools.list_models({"lane": "image", "source": "trained"})["trained"]
        self.assertEqual(
            [(row["id"], row.get("default", False)) for row in listed],
            [(STUDIO_LORA, False), (COMPOSITION, True)],
        )

    # -- render_form ------------------------------------------------------------------
    def test_render_form_sets_the_render_image_choice_with_the_pickers_rules(self):
        self.load_catalog()
        self.open_trained("render_image")
        render = self.scene.scenario.lane_state("render_image")
        configure = {"lane": "render_image", "action": "configure"}

        def snapshot():
            return (
                render.model_id,
                render.model_key,
                [(s.model_id, s.kind, s.has_scale, round(s.scale, 4)) for s in render.trained],
            )

        result = self.tools.render_form(
            {
                **configure,
                "settings": {
                    "model_id": FLUX1,
                    "trained": [
                        {"model_id": STUDIO_LORA, "scale": 0.8},
                        {"model_id": LORA_A, "scale": 1.25},
                    ],
                },
            }
        )
        self.assertEqual(
            result["trained_models"],
            [
                {"model_id": STUDIO_LORA, "kind": "lora", "strength": 0.8},
                {"model_id": LORA_A, "kind": "lora", "strength": 1.25},
            ],
        )
        self.assertEqual(render.model_key, FLUX1)
        trained = submodule("blender.trained_models")
        self.assertEqual(
            [(s.fmin, s.fmax, s.get(trained.SCOPE)) for s in render.trained],
            [(0.0, 2.0, trained.current_scope())] * 2,
        )
        body = self.generation.build_request(self.scene, "render_image", for_estimate=True).body
        self.assertEqual((body["loras"], body["lorasScale"]), (STACK["loras"], [0.8, 1.25]))
        before = snapshot()
        for picks, message in (
            ([{"model_id": FLUX2_LORA, "scale": 0.8}], "accepts flux.1-lora models"),
            ([{"model_id": LORA_A}], "provide a strength for each LoRA"),
            ([{"model_id": COMPOSITION, "scale": 0.5}], "applies its own strengths"),
            ([{"model_id": LORA_A, "scale": 0.12345}], "at most 4 decimal places"),
            ([{"model_id": "model_gone", "scale": 0.5}], "no longer listed"),
            ([{"model_id": LORA_A, "scale": 0.5, "kind": "lora"}], "an optional scale"),
        ):
            with self.subTest(picks=picks):
                self.assert_refused(
                    lambda picks=picks: self.tools.render_form(
                        {**configure, "settings": {"trained": picks, "look": "changed"}}
                    ),
                    message,
                )
                self.assertEqual(snapshot(), before)  # refused before any change
                self.assertNotEqual(render.prompt, "changed")
        result = self.tools.render_form(
            {**configure, "settings": {"trained": [{"model_id": COMPOSITION}]}}
        )
        self.assertEqual(
            result["trained_models"],
            [{"model_id": COMPOSITION, "kind": "composition", "strength": None}],
        )
        result = self.tools.render_form({**configure, "settings": {"trained": []}})
        self.assertEqual(result["trained_models"], [])
        self.assertFalse(len(render.trained))
