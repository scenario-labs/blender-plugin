# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Background removal prepares the adopted Image flow without a paid shortcut."""

import json
import unittest
from unittest.mock import patch

import bpy
import httpx
import test_reference_form as form_fixture
from helpers import submodule


class BackgroundRemovalTests(unittest.TestCase):
    def setUp(self):
        self.case = case = form_fixture.ReferenceFormTests()
        case.setUp()
        self.addCleanup(case.doCleanups)
        self.model = {
            "id": "model_bria-remove-background",
            "name": "Fixture background removal",
            "type": "custom",
            "capabilities": ["img2img"],
            "inputs": [
                {"name": "image", "type": "file", "kind": "image", "required": {"always": True}},
                {"name": "refine", "type": "boolean", "default": False},
            ],
        }
        record = submodule("core.api.catalog").ModelRecord.from_api(self.model)
        existing = case.runtime.state.records[case.model["id"]]
        case.generation.set_catalog([existing, record], [existing, record])
        self.path = str(case.fixture.fixture.source)
        self.enterContext(
            patch.object(
                case.runtime, "ensure_manager", side_effect=AssertionError("Prototype manager used")
            )
        )

    def prepare(self):
        self.assertEqual(bpy.ops.scenario.remove_background(filepath=self.path), {"FINISHED"})

    def test_prepares_one_reference_and_invalidates_old_approval_without_submission(self):
        case = self.case
        case.scene.scenario.lane = "video"
        case.lane.prompt = "previous prompt"
        case.lane.estimate_state, case.lane.estimate_key = "READY", "previous-approved-quote"
        self.prepare()
        self.assertEqual(case.scene.scenario.lane, "image")
        self.assertEqual(case.lane.model_id, self.model["id"])
        self.assertEqual(case.lane.model_key, self.model["id"])
        self.assertEqual(case.lane.prompt, "")
        self.assertEqual(case.lane.estimate_state, "PENDING")
        self.assertEqual(case.lane.estimate_key, "")
        self.assertEqual(
            [(r.param_name, r.source, r.filepath) for r in case.lane.references],
            [("image", "FILE", self.path)],
        )
        self.assertEqual(case.fixture.fixture.calls, [])
        self.assertEqual(case.fixture.fixture.store.records(), ())
        self.assertEqual(case.owner.references, {})
        self.assertEqual(case.runtime.state.jobs_view, [])

    def test_repeated_preparation_resets_settings_and_never_starts_an_upload(self):
        case = self.case
        self.prepare()
        case.lane.params["refine"].bool_value = True
        case.lane.references.add().param_name = "image"
        self.prepare()
        self.assertFalse(case.lane.params["refine"].bool_value)
        self.assertEqual(len(case.lane.references), 1)
        self.assertEqual(case.owner.references, {})
        self.assertEqual(case.fixture.fixture.calls, [])

    def test_missing_file_or_model_preserves_existing_form(self):
        case = self.case
        before = case.lane.model_id, case.lane.references[0].filepath
        with self.assertRaisesRegex(RuntimeError, "File not found"):
            bpy.ops.scenario.remove_background(filepath=self.path + ".missing")
        case.runtime.state.records.pop(self.model["id"])
        case.runtime.state.lane_models["image"] = [case.runtime.state.records[case.model["id"]]]
        with self.assertRaisesRegex(RuntimeError, "No background removal model"):
            self.prepare()
        self.assertEqual((case.lane.model_id, case.lane.references[0].filepath), before)
        self.assertEqual(case.fixture.fixture.calls, [])

    def test_missing_schema_or_image_input_does_not_clear_the_form(self):
        case = self.case
        before = case.lane.model_id, case.lane.references[0].filepath
        with patch.object(
            case.generation,
            "ensure_record",
            side_effect=submodule("core.api.errors").ScenarioError(
                0, "Loading the model description"
            ),
        ):
            self.assertEqual(bpy.ops.scenario.remove_background(filepath=self.path), {"CANCELLED"})
        with patch.object(case.generation, "schema_for", return_value=None):
            with self.assertRaisesRegex(RuntimeError, "takes no image input"):
                self.prepare()
        self.assertEqual((case.lane.model_id, case.lane.references[0].filepath), before)
        self.assertEqual(case.fixture.fixture.calls, [])

    def test_prepared_background_removal_requires_upload_quote_and_one_explicit_generate(self):
        case = self.case
        original = case.fixture.fixture.handler
        quotes, paid = [], []

        def respond(request):
            if "/uploads" in request.url.path:
                return original(request)
            if request.method == "GET":
                if "/jobs/" in request.url.path:
                    return httpx.Response(
                        200,
                        json={
                            "job": {
                                "jobId": "background-job",
                                "status": "in-progress",
                                "jobType": "custom",
                            }
                        },
                    )
                return httpx.Response(200, json={"model": self.model})
            if request.url.params.get("dryRun") == "true":
                quotes.append(request)
                return httpx.Response(269, content=b'{"creativeUnitsCost":0.1234567890123456789}')
            self.assertEqual(case.fixture.fixture.store.records()[0].state.value, "submitting")
            paid.append(request)
            return httpx.Response(200, json={"job": {"jobId": "background-job"}})

        case.fixture.fixture.handler = respond
        self.prepare()
        with self.assertRaises(submodule("core.api.errors").ScenarioError):
            case.generation.submit_generation(bpy.context, "image")
        self.assertEqual(paid, [])
        case.ref = case.lane.references[0]
        case.start()
        case.fixture.settle()
        self.assertEqual(case.ref.source, "ASSET")
        case.generation.request_estimate(case.scene, "image")
        for ticket in case.runtime.state.model_previews.values():
            ticket.task.result(5)
        case.runtime.sync_catalog_context()
        self.assertEqual(case.lane.estimate_state, "READY", case.lane.estimate_error)
        ticket = case.runtime.state.estimates[case.lane.estimate_key]
        self.assertEqual(str(ticket.quote.estimate.cost), "0.1234567890123456789")
        case.generation.submit_generation(bpy.context, "image")
        for task in case.runtime.state.model_jobs.submissions.values():
            task.result(5)
        case.runtime.sync_catalog_context()
        with self.assertRaises(submodule("core.api.errors").ScenarioError):
            case.generation.submit_generation(bpy.context, "image")
        self.assertEqual(len(quotes), 1)
        self.assertEqual(len(paid), 1)
        self.assertEqual(quotes[0].content, paid[0].content)
        self.assertEqual(json.loads(paid[0].content)["image"], "reference-asset")
        self.assertEqual(case.fixture.fixture.uploader.upload.call_count, 1)
