# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Installed SDK history integration with synthetic network responses."""

import threading
import unittest
from unittest.mock import patch

import bpy
import httpx
from helpers import isolated_manager, online_access, reset_scene, submodule, temp_credentials


def job(identifier="job-fixture", prompt="asset_prompt"):
    return {
        "jobId": identifier,
        "jobType": "custom",
        "status": "success",
        "metadata": {"input": {"modelId": "fixture-model", "prompt": prompt}},
    }


class SDKHistoryTests(unittest.TestCase):
    def setUp(self):
        reset_scene()
        self.runtime = submodule("blender.runtime")
        self.history = submodule("blender.history")
        self.generation = submodule("blender.generation")
        self.handlers = submodule("blender.handlers")
        self.tools = submodule("mcp.tools_scenario")
        self.enterContext(patch.object(self.runtime, "state", self.runtime.RuntimeState()))
        self.prefs = self.enterContext(temp_credentials())
        self.enterContext(online_access(True))
        self.manager = self.enterContext(isolated_manager())
        self.addCleanup(self.runtime.state.reset)
        self.calls = []
        self.page = {"jobs": [job()], "nextPaginationToken": "page-two"}
        self.status = 200
        self.preview = "resolved prompt"
        self.steps = {}
        adapter = submodule("core.api.sdk_adapter")

        def respond(request):
            self.assertIsNot(threading.current_thread(), threading.main_thread())
            self.calls.append(request)
            if request.url.path == "/v1/jobs":
                self.assertEqual(request.url.params["hideResults"], "false")
                return httpx.Response(self.status, json=self.page)
            if request.url.path.startswith("/v1/jobs/"):
                identifier = request.url.path.rsplit("/", 1)[1]
                if identifier not in self.steps:
                    return httpx.Response(404, json={"message": "private fixture"})
                return httpx.Response(200, json={"job": self.steps[identifier]})
            self.assertEqual(request.url.path, "/v1/assets/asset_prompt")
            return httpx.Response(200, json={"asset": {"metadata": {"preview": self.preview}}})

        def factory(credentials, **kwargs):
            return adapter.SDKAdapter(credentials, transport=httpx.MockTransport(respond), **kwargs)

        self.enterContext(
            patch.object(submodule("core.api.sdk_catalog"), "SDKAdapter", side_effect=factory)
        )

    def completed(self):
        self.manager.join(5)
        self.assertFalse(self.manager.has_active())
        return self.manager.drain_catalog()

    def deliver(self):
        self.manager.join(5)
        self.assertFalse(self.manager.has_active())
        self.generation.process_catalog_events()

    def saved_job(self, request_id="saved-request"):
        module = submodule("core.jobs.store")
        store = self.runtime.ensure_job_store()
        intent = module.JobIntent(
            request_id,
            store.scope,
            module.JobOrigin("file", "scene", "revision"),
            "model",
            "fixture-model",
            "a" * 64,
            "b" * 64,
            "1.25",
        )
        store.create(intent)
        store.transition(request_id, state=module.JobState.SUBMITTING, expected_revision=0)
        store.transition(
            request_id,
            state=module.JobState.REMOTE,
            expected_revision=1,
            remote_job_id="job-fixture",
        )
        return store.transition(request_id, state=module.JobState.SUCCEEDED, expected_revision=2)

    def legacy_collision(self):
        record = submodule("core.jobs.records").JobRecord.new(
            lane="image",
            kind="image",
            model_id="fixture-model",
            body={},
        )
        record.job_id, record.status, record.files = "job-fixture", "success", ["unverified.png"]
        self.manager.registry.add(record)
        return record

    def test_cloud_history_exposes_saved_request_ids_without_legacy_files(self):
        saved = self.saved_job()
        self.legacy_collision()
        self.history.refresh()
        self.deliver()
        entry = self.runtime.state.history[0]
        self.assertEqual(entry.local_request_ids, (saved.intent.request_id,))
        self.assertEqual(entry.local_files, [])
        row = self.tools.list_generations({})["generations"][0]
        self.assertEqual(row["local_request_ids"], [saved.intent.request_id])
        self.assertEqual(row["local_files"], [])
        self.assertEqual(len(self.calls), 2)

    def test_native_history_import_routes_saved_job_to_explicit_recovery(self):
        saved = self.saved_job()
        legacy = self.legacy_collision()
        before = tuple(bpy.data.objects)
        with (
            patch.object(self.handlers, "dispatch") as dispatch,
        ):
            self.assertEqual(bpy.ops.scenario.import_result(job_id="job-fixture"), {"FINISHED"})
            self.assertFalse(self.manager.has_active())
            dispatch.assert_not_called()
        self.assertEqual(tuple(bpy.data.objects), before)
        self.assertEqual(self.runtime.state.job_store.get(saved.intent.request_id), saved)
        self.assertEqual(self.manager.registry.all(), [legacy])
        self.assertEqual(self.runtime.state.jobs_view[0].local_id, saved.intent.request_id)
        self.assertFalse(self.calls)

    def test_mcp_saved_job_precedes_legacy_collision_and_never_imports_directly(self):
        saved = self.saved_job()
        self.legacy_collision()
        with patch.object(self.handlers, "dispatch") as dispatch:
            for reference in (saved.intent.request_id, saved.remote_job_id):
                status = self.tools.job_status({"job_id": reference})
                self.assertEqual(status["local_id"], saved.intent.request_id)
                self.assertEqual(status["files"], [])
                with self.assertRaisesRegex(ValueError, "explicit destination approval"):
                    self.tools.import_result({"job_id": reference})
            dispatch.assert_not_called()
        self.assertFalse(self.calls)

    def test_incomplete_credentials_cannot_import_a_colliding_legacy_result(self):
        saved = self.saved_job()
        store = self.runtime.state.job_store
        self.legacy_collision()
        self.prefs.api_secret = ""
        with patch.object(self.handlers, "dispatch") as dispatch:
            with self.assertRaisesRegex(
                submodule("core.api.errors").ScenarioError, "complete credentials"
            ):
                self.tools.import_result({"job_id": "job-fixture"})
            dispatch.assert_not_called()
        self.assertEqual(store.get(saved.intent.request_id), saved)
        self.assertFalse(self.calls)

    def test_ambiguous_saved_remote_id_does_not_fall_back_to_legacy_import(self):
        self.saved_job("first")
        self.saved_job("second")
        self.legacy_collision()
        with self.assertRaisesRegex(ValueError, "Several saved jobs"):
            self.tools.import_result({"job_id": "job-fixture"})
        self.assertEqual(self.tools.job_status({"job_id": "first"})["local_id"], "first")
        self.assertFalse(self.calls)

    def test_failed_storage_read_does_not_fall_back_to_legacy(self):
        self.saved_job()
        self.legacy_collision()
        with (
            patch.object(self.runtime.state.job_store, "records", side_effect=OSError("fixture")),
            patch.object(self.handlers, "dispatch") as dispatch,
        ):
            with self.assertRaisesRegex(RuntimeError, "Could not inspect saved jobs"):
                bpy.ops.scenario.import_result(job_id="job-fixture")
            with self.assertRaisesRegex(
                submodule("core.api.errors").ScenarioError, "Could not inspect saved jobs"
            ):
                self.tools.import_result({"job_id": "job-fixture"})
            self.assertFalse(self.manager.has_active())
            dispatch.assert_not_called()

    def test_history_draw_offers_saved_controls_without_files_or_mutation(self):
        from test_model_picker import FakeLayout

        self.saved_job()
        self.legacy_collision()
        self.history.refresh()
        self.deliver()
        layout = FakeLayout()
        before = self.runtime.state.job_store.records()
        with (
            patch.object(
                self.runtime, "ensure_model_jobs", side_effect=AssertionError("Draw mutation")
            ),
            patch.object(
                self.runtime.state.job_store,
                "records",
                side_effect=AssertionError("Storage read during redraw"),
            ),
        ):
            for _ in range(30):
                submodule("blender.panels").draw_history(layout, bpy.context)
        operators = [call[1][0] for node in layout.walk() for call in node.named("operator")]
        self.assertIn("scenario.inspect_saved_jobs", operators)
        self.assertNotIn("scenario.import_result", operators)
        self.assertEqual(self.runtime.state.job_store.records(), before)

    def test_live_saved_view_overrides_history_snapshot_without_storage_read(self):
        from test_model_picker import FakeLayout

        self.legacy_collision()
        self.history.refresh()
        self.deliver()
        self.assertEqual(self.runtime.state.history_saved_ids, frozenset())
        saved = self.saved_job()
        self.runtime.inspect_model_jobs()
        self.assertEqual(self.runtime.state.jobs_view[0].job_id, saved.remote_job_id)
        layout = FakeLayout()
        panels = submodule("blender.panels")
        with (
            patch.object(panels, "thumbnail", side_effect=AssertionError("Legacy file read")),
            patch.object(
                self.runtime.state.job_store,
                "records",
                side_effect=AssertionError("Storage read during redraw"),
            ),
        ):
            panels.draw_history(layout, bpy.context)
        operators = [call[1][0] for node in layout.walk() for call in node.named("operator")]
        self.assertIn("scenario.inspect_saved_jobs", operators)
        self.assertNotIn("scenario.import_result", operators)

    def test_failed_saved_read_disables_history_actions_until_explicit_refresh(self):
        from test_model_picker import FakeLayout

        self.saved_job()
        self.history.refresh()
        self.deliver()
        store = self.runtime.state.job_store
        self.assertEqual(self.runtime.state.history_saved_ids, frozenset({"job-fixture"}))
        with patch.object(store, "records", side_effect=OSError("fixture")):
            self.history.refresh()
            self.deliver()
        self.assertIsNone(self.runtime.state.history_saved_ids)
        layout = FakeLayout()
        submodule("blender.panels").draw_history(layout, bpy.context)
        self.assertFalse([call for node in layout.walk() for call in node.named("operator")])
        self.assertIn("Could not inspect saved jobs", self.runtime.state.history_error)
        self.history.refresh()
        self.deliver()
        self.assertEqual(self.runtime.state.history_saved_ids, frozenset({"job-fixture"}))
        self.assertFalse(self.runtime.state.history_error)
        self.prefs.api_secret = "other-fixture-secret"
        self.runtime.sync_catalog_context()
        self.assertIsNone(self.runtime.state.history_saved_ids)

    def test_unsaved_cloud_draw_ignores_legacy_files_and_offers_only_recovery(self):
        from test_model_picker import FakeLayout

        self.legacy_collision()
        self.history.refresh()
        self.deliver()
        layout = FakeLayout()
        panels = submodule("blender.panels")
        with (
            patch.object(panels, "thumbnail", side_effect=AssertionError("Legacy file read")),
            patch.object(panels, "draw_result", side_effect=AssertionError("Legacy actions")),
            patch.object(
                self.runtime, "ensure_model_jobs", side_effect=AssertionError("Draw mutation")
            ),
        ):
            panels.draw_history(layout, bpy.context)
        operators = [call for node in layout.walk() for call in node.named("operator")]
        self.assertTrue(
            any(
                call[1][0] == "scenario.import_result"
                and call[2].get("text") == "Save for recovery"
                for call in operators
            )
        )
        self.assertEqual(self.tools.list_generations({})["generations"][0]["local_files"], [])
        self.assertFalse(self.runtime.state.job_store.records())

    def test_legacy_session_row_cannot_hide_cloud_recovery_controls(self):
        from types import SimpleNamespace

        from test_model_picker import FakeLayout

        legacy = self.legacy_collision()
        self.runtime.state.jobs_view.append(legacy)
        self.history.refresh()
        self.deliver()
        bpy.context.scene.scenario.show_cloud_history = True
        layout = FakeLayout()
        panels = submodule("blender.panels")
        with patch.object(panels, "draw_result"):
            panels.SCENARIO_PT_generations.draw(SimpleNamespace(layout=layout), bpy.context)
        operators = [call[1][0] for node in layout.walk() for call in node.named("operator")]
        self.assertIn("scenario.import_result", operators)

    def test_saved_acknowledgement_after_page_load_overrides_stale_legacy_projection(self):
        from test_model_picker import FakeLayout

        self.legacy_collision()
        self.history.refresh()
        self.deliver()
        self.assertEqual(self.runtime.state.history[0].local_files, ["unverified.png"])
        self.saved_job()
        row = self.tools.list_generations({})["generations"][0]
        self.assertEqual(row["local_request_ids"], ["saved-request"])
        self.assertEqual(row["local_files"], [])
        layout = FakeLayout()
        panels = submodule("blender.panels")
        with patch.object(panels, "thumbnail", side_effect=AssertionError("Legacy file read")):
            panels.draw_history(layout, bpy.context)
        operators = [call[1][0] for node in layout.walk() for call in node.named("operator")]
        self.assertIn("scenario.inspect_saved_jobs", operators)
        self.assertNotIn("scenario.import_result", operators)
        self.prefs.api_secret = "replacement-fixture-secret"
        layout = FakeLayout()
        submodule("blender.panels").draw_history(layout, bpy.context)
        self.assertFalse([call for node in layout.walk() for call in node.named("operator")])

    def test_saved_history_binding_survives_restart_but_not_credential_switch(self):
        saved = self.saved_job()
        self.runtime.state.reset()
        self.assertEqual(self.history.saved_matches("job-fixture"), (saved,))
        self.prefs.api_secret = "other-fixture-secret"
        self.assertEqual(self.history.saved_matches("job-fixture"), ())
        self.assertFalse(self.calls)

    def test_ui_refresh_and_headless_mcp_share_resolved_history(self):
        self.history.refresh()
        self.manager.join(5)
        result = self.tools.list_generations({})  # Delivers without a GUI tick.
        self.assertEqual(result["generations"][0]["prompt"], self.preview)
        self.assertEqual(result["generations"][0]["job_id"], "job-fixture")
        self.assertEqual(len(self.calls), 2)
        self.assertTrue(self.runtime.state.history_loaded)
        self.assertFalse(self.runtime.state.history_loading)
        self.assertEqual(self.runtime.state.history_token, "page-two")

    def test_empty_page_is_loaded_once_and_mcp_does_not_start_repeated_reads(self):
        self.page = {"jobs": []}
        first = self.tools.list_generations({})
        self.assertIn("note", first)
        self.manager.join(5)
        self.assertEqual(self.tools.list_generations({}), {"generations": []})
        self.assertEqual(self.tools.list_generations({}), {"generations": []})
        self.assertEqual(len(self.calls), 1)

    def test_older_page_keeps_cursor_deduplicates_and_has_one_pending_request(self):
        self.history.refresh()
        self.deliver()
        self.page = {"jobs": [job(), job("job-older", "older prompt")]}
        self.assertTrue(self.history.older())
        self.assertFalse(self.history.older())
        self.deliver()
        self.assertEqual(
            [e.job_id for e in self.runtime.state.history], ["job-fixture", "job-older"]
        )
        self.assertIsNone(self.runtime.state.history_token)
        self.assertEqual(self.calls[2].url.params["paginationToken"], "page-two")

    def test_ui_and_mcp_refresh_share_a_pending_read(self):
        with patch.object(self.manager, "fetch_history") as fetch:
            self.history.refresh()
            key = self.runtime.state.history_request
            for _ in range(3):
                self.history.refresh()
                self.tools.list_generations({"refresh": True})
            self.assertEqual(fetch.call_count, 1)
            self.assertEqual(self.runtime.state.history_request, key)
        self.handlers.dispatch(
            (
                "history",
                {
                    "catalog": self.runtime.state.catalog,
                    "key": key,
                    "jobs": [],
                    "error": None,
                },
            )
        )
        self.history.refresh()
        self.deliver()
        self.assertEqual(len(self.calls), 2)

    def test_mcp_rejects_non_boolean_refresh_without_reading(self):
        for value in ("false", "true", 0, 1, None, [], {}):
            with self.subTest(value=value):
                with self.assertRaisesRegex(ValueError, "refresh must be a boolean"):
                    self.tools.list_generations({"refresh": value})
        self.assertFalse(self.calls)
        self.assertFalse(self.runtime.state.history_loading)
        self.runtime.state.history_loaded = True
        self.assertEqual(self.tools.list_generations({"refresh": False}), {"generations": []})

    def test_credentials_clear_visible_history_and_reject_queued_old_results(self):
        self.history.refresh()
        self.deliver()
        self.history.refresh()
        queued = self.completed()
        self.prefs.api_secret = "replacement-secret"
        self.runtime.ensure_catalog()
        for event in queued:
            self.handlers.dispatch(event)
        self.assertFalse(self.runtime.state.history)
        self.assertFalse(self.runtime.state.history_loaded)
        self.assertIsNone(self.runtime.state.history_token)
        self.preview = "new account prompt"
        self.history.refresh()
        self.deliver()
        self.assertEqual(self.runtime.state.history[0].prompt, self.preview)

    def test_old_failure_does_not_replace_new_context_or_message(self):
        self.status = 403
        self.page = {"message": "private response"}
        self.history.refresh()
        queued = self.completed()
        self.prefs.api_secret = "replacement-secret"
        self.runtime.ensure_catalog()
        self.runtime.set_message("current message")
        for event in queued:
            self.handlers.dispatch(event)
        self.assertEqual(self.runtime.state.last_message, "current message")
        self.assertFalse(self.runtime.state.history_error)

    def test_failed_refresh_keeps_last_page_and_cursor(self):
        self.history.refresh()
        self.deliver()
        with patch.object(self.manager, "fetch_history"):
            self.history.refresh()
            pending = self.tools.list_generations({})
            self.assertIn("pending", pending["note"])
            self.assertEqual(pending["generations"][0]["job_id"], "job-fixture")
        self.handlers.dispatch(
            (
                "history",
                {
                    "catalog": self.runtime.state.catalog,
                    "key": self.runtime.state.history_request,
                    "error": "fixture read failed",
                },
            )
        )
        self.status = 503
        self.page = {"private": "response details"}
        self.history.refresh()
        self.deliver()
        self.assertEqual([e.job_id for e in self.runtime.state.history], ["job-fixture"])
        self.assertEqual(self.runtime.state.history_token, "page-two")
        self.assertTrue(self.runtime.state.history_error)
        self.assertNotIn("response details", self.runtime.state.history_error)
        self.assertFalse(self.runtime.state.history_loading)
        with self.assertRaisesRegex(RuntimeError, "refresh=true"):
            self.tools.list_generations({})

    def test_mcp_failed_initial_read_can_be_retried_explicitly(self):
        self.status = 503
        self.tools.list_generations({})
        self.deliver()
        with self.assertRaisesRegex(RuntimeError, "refresh=true"):
            self.tools.list_generations({})
        self.status = 200
        self.tools.list_generations({"refresh": True})
        self.deliver()
        self.assertEqual(self.tools.list_generations({})["generations"][0]["job_id"], "job-fixture")

    def test_cross_page_cursor_cycle_preserves_last_valid_page(self):
        self.history.refresh()
        self.deliver()
        self.page = {"jobs": [job("job-two", "two")], "nextPaginationToken": "page-three"}
        self.history.older()
        self.deliver()
        self.page = {"jobs": [job("job-three", "three")], "nextPaginationToken": "page-two"}
        self.history.older()
        self.deliver()
        self.assertEqual([e.job_id for e in self.runtime.state.history], ["job-fixture", "job-two"])
        self.assertEqual(self.runtime.state.history_token, "page-three")
        self.assertIn("repeated", self.runtime.state.history_error)

    def test_malformed_metadata_and_billing_fail_without_partial_delivery(self):
        for malformed in ({"metadata": [1]}, {"billing": {"cuCost": "invalid"}}):
            with self.subTest(malformed=malformed):
                self.page = {"jobs": [{**job(prompt="text"), **malformed}]}
                self.history.refresh()
                self.deliver()
                self.assertFalse(self.runtime.state.history)
                self.assertFalse(self.runtime.state.history_loading)
                self.assertTrue(self.runtime.state.history_error)

    def test_workflow_run_cost_sums_steps_and_unknown_steps_are_unavailable(self):
        from test_model_picker import FakeLayout

        def step(identifier, main, parent="job-run"):
            return {
                **job(identifier, prompt="step"),
                "billing": {
                    "cuCost": main,
                    "cuDiscount": 0,
                    "cuCostDetails": {"quality-gate": 1.75},
                },
                "metadata": {
                    "input": {"modelId": "fixture-model", "prompt": "step"},
                    "workflowJobId": parent,
                },
            }

        def run(identifier, steps):
            return {
                "jobId": identifier,
                "jobType": "workflow",
                "status": "success",
                "billing": {"cuCost": 0, "cuDiscount": 0},
                "metadata": {
                    "input": {"prompt": "loop run"},
                    "workflowId": "fixture-workflow",
                    "flow": [{"id": "loop", "type": "for-each", "status": "success"}]
                    + [
                        {"id": f"n-{s}", "type": "custom-model", "status": "success", "jobId": s}
                        for s in steps
                    ],
                },
            }

        self.page = {
            "jobs": [
                step("job-a", 1),
                step("job-b", 1),
                run("job-run", ["job-a", "job-b", "job-c"]),
                run("job-lost", ["job-gone"]),
            ]
        }
        self.steps = {"job-c": step("job-c", 2)}
        self.history.refresh()
        self.deliver()
        entries = {e.job_id: e for e in self.runtime.state.history}
        self.assertEqual(set(entries), {"job-a", "job-b", "job-run", "job-lost"})
        self.assertEqual(entries["job-run"].cu_cost, 9.25)
        self.assertTrue(entries["job-lost"].cost_unavailable)
        reads = sorted(r.url.path for r in self.calls if r.url.path.startswith("/v1/jobs/"))
        self.assertEqual(reads, ["/v1/jobs/job-c", "/v1/jobs/job-gone"])
        count = len(self.calls)
        with patch.object(
            self.runtime, "ensure_model_jobs", side_effect=AssertionError("Draw mutation")
        ):
            for _ in range(5):
                layout = FakeLayout()
                submodule("blender.panels").draw_history(layout, bpy.context)
        self.assertEqual(len(self.calls), count)
        labels = [call[2].get("text") for node in layout.walk() for call in node.named("label")]
        self.assertIn("9.25 CU", labels)
        self.assertIn("Cost unavailable", labels)
        self.assertIn("2.75 CU", labels)
        # True while the run is running or its total is unavailable too.
        self.assertIn("Workflow step; included in its run's total once known", labels)
        operators = [call for node in layout.walk() for call in node.named("operator")]
        recover = [
            call[2].get("text") for call in operators if call[1][0] == "scenario.import_result"
        ]
        self.assertEqual(len(recover), 2)  # Only the two listed model steps.
        rows = {row["job_id"]: row for row in self.tools.list_generations({})["generations"]}
        self.assertEqual((rows["job-run"]["kind"], rows["job-run"]["cu_cost"]), ("workflow", 9.25))
        self.assertEqual(rows["job-run"]["workflow_id"], "fixture-workflow")
        self.assertIsNone(rows["job-lost"]["cu_cost"])
        self.assertTrue(rows["job-lost"]["cost_unavailable"])
        self.assertEqual(rows["job-a"]["workflow_job_id"], "job-run")
        self.assertEqual(rows["job-a"]["cu_cost"], 2.75)
