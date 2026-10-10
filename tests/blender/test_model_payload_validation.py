# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Installed payload preparation with captured REST inputs and offline transport."""

import json
import unittest
import unittest.mock
from pathlib import Path
from types import SimpleNamespace

from helpers import online_access, submodule


class ModelPayloadValidationTests(unittest.TestCase):
    def test_panel_schema_cache_and_sdk_estimate_agree_on_undeclared_siblings(self):
        import httpx

        generation = submodule("blender.generation")
        runtime = submodule("blender.runtime")
        api = submodule("core.api.sdk_adapter")
        forms = submodule("core.schema.forms")
        for condition, required in (("ifDefined", False), ("ifNotDefined", True)):
            with self.subTest(condition=condition):
                # A sibling the schema does not declare is never defined.
                fields = [
                    {"name": "reference", "type": "file", "required": {condition: {"missing": {}}}}
                ]
                record = SimpleNamespace(parameters=fields, ui_config={})
                model = {"id": "fixture-schema", "type": "custom", "inputs": fields}
                requests = []

                def respond(request, requests=requests):
                    requests.append(request)
                    return httpx.Response(200, json={"creativeUnitsCost": 1})

                with (
                    unittest.mock.patch.dict(runtime.state.records, {"fixture-schema": record}),
                    unittest.mock.patch.dict(generation._schemas, {}, clear=True),
                    api.SDKAdapter(
                        api.Credentials("fixture-key", "fixture-secret"),
                        online=lambda: True,
                        transport=httpx.MockTransport(respond),
                    ) as adapter,
                    online_access(True),
                ):
                    # Both generate and Edit 3D panels call this cache while drawing.
                    parsed = generation.schema_for("fixture-schema")
                    self.assertIs(parsed, generation.schema_for("fixture-schema"))
                    spec = parsed.by_name("reference")
                    self.assertEqual(spec.required_always, required)
                    self.assertEqual(
                        (spec.required_if_defined, spec.required_if_not_defined), ((), ())
                    )
                    self.assertEqual(parsed.one_of, [])
                    if required:
                        with self.assertRaisesRegex(ValueError, "Reference is required"):
                            forms.prepare_run("fixture-schema", {"parameters": fields}, {})
                        with self.assertRaisesRegex(ValueError, "Reference is required"):
                            adapter.estimate_model(model, {})
                        self.assertEqual(requests, [])
                        values = {"reference": "asset"}
                    else:
                        values = {}
                    target, payload = forms.prepare_run(
                        "fixture-schema", {"parameters": fields}, values
                    )
                    quote = adapter.estimate_model(model, values)
                    self.assertEqual((quote.target_id, quote.payload), (target, payload))
                    self.assertEqual([json.loads(r.content) for r in requests], [values])

    def test_captured_minimax_conditional_matches_installed_sdk_adapter(self):
        import httpx

        forms = submodule("core.schema.forms")
        api = submodule("core.api.sdk_adapter")
        path = Path(__file__).parents[1] / "fixtures/models/model_minimax-h3.json"
        captured = json.loads(path.read_text())["model"]
        model = {key: captured[key] for key in ("id", "type", "inputs")}
        schema = {"parameters": model["inputs"]}
        requests = []

        def respond(request):
            requests.append(request)
            return httpx.Response(200, json={"creativeUnitsCost": 1})

        with (
            api.SDKAdapter(
                api.Credentials("fixture-key", "fixture-secret"),
                online=lambda: True,
                transport=httpx.MockTransport(respond),
            ) as adapter,
            online_access(True),
        ):
            values = {"prompt": "fixture", "lastFrameImage": "last"}
            with self.assertRaises(ValueError):
                forms.prepare_run(model["id"], schema, values)
            with self.assertRaises(ValueError):
                adapter.estimate_model(model, values)
            self.assertEqual(requests, [])
            values["firstFrameImage"] = "first"
            target, payload = forms.prepare_run(model["id"], schema, values)
            quote = adapter.estimate_model(model, values)
            self.assertEqual((quote.target_id, quote.payload), (target, payload))
            self.assertEqual(json.loads(requests[0].content), payload)

    def test_distinct_synthetic_requirement_groups_are_not_unioned(self):
        forms = submodule("core.schema.forms")
        schema = {
            "parameters": [
                {"name": "a", "type": "file", "required": {"ifNotDefined": {"b": {}}}},
                {"name": "b", "type": "file", "required": {"ifNotDefined": {"c": {}}}},
                {"name": "c", "type": "file"},
            ]
        }
        with self.assertRaises(ValueError):
            forms.prepare_run("base", schema, {"a": "asset"})
        self.assertEqual(forms.prepare_run("base", schema, {"b": "asset"})[1], {"b": "asset"})
        with self.assertRaises(ValueError):
            forms.prepare_run("base", schema, {"b": "  "})
        # An undeclared sibling is never set, so `a` is always required.
        schema["parameters"][0]["required"] = {"ifNotDefined": {"missing": {}}}
        with self.assertRaisesRegex(ValueError, "A is required"):
            forms.prepare_run("base", schema, {"b": "asset"})
        both = {"a": "asset", "b": "asset"}
        self.assertEqual(forms.prepare_run("base", schema, both)[1], both)

    def test_synthetic_routing_fills_required_fields_and_rejects_bad_target(self):
        forms = submodule("core.schema.forms")
        schema = {
            "runs_as": "composition",
            "parameters": [{"name": "modelId", "type": "model", "required": True}],
            "run_with": {
                "required_arguments": {
                    "model_id": "base",
                    "parameters": {"modelId": "selected"},
                }
            },
        }
        self.assertEqual(
            forms.prepare_run("selected", schema, {}), ("base", {"modelId": "selected"})
        )
        schema["run_with"]["required_arguments"]["model_id"] = 123
        with self.assertRaises(ValueError):
            forms.prepare_run("selected", schema, {})
