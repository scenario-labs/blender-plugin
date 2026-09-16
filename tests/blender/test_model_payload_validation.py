# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Installed payload preparation with captured REST inputs and offline transport."""

import json
import unittest
from pathlib import Path

from helpers import online_access, submodule


class ModelPayloadValidationTests(unittest.TestCase):
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
        schema["parameters"][0]["required"] = {"ifNotDefined": {"missing": {}}}
        with self.assertRaises(ValueError):
            forms.prepare_run("base", schema, {"b": "asset"})

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
