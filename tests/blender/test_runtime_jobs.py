# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Selected application jobs and MCP recovery in the installed extension."""

import tempfile
import threading
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, call, patch

import bpy
from helpers import online_access, submodule, temp_credentials


class RuntimeJobTests(unittest.TestCase):
    def setUp(self):
        import httpx

        self.httpx = httpx
        self.runtime = submodule("blender.runtime")
        self.api = submodule("core.api.sdk_adapter")
        self.storemod = submodule("core.jobs.store")
        self.tools = submodule("mcp.tools_scenario")
        self.enterContext(patch.object(self.runtime, "state", self.runtime.RuntimeState()))
        self.enterContext(online_access(False))
        self.prefs = self.enterContext(temp_credentials())
        source = self.prefs.credential_source
        self.addCleanup(setattr, self.prefs, "credential_source", source)
        self.prefs.credential_source = "PREFERENCES"
        root = self.enterContext(tempfile.TemporaryDirectory(dir=bpy.utils.resource_path("USER")))
        self.root = Path(root)
        self.enterContext(
            patch.object(self.runtime, "paths", return_value=SimpleNamespace(state_dir=Path(root)))
        )
        self.adapters, self.sessions, self.requests = [], [], []
        catalog_type, session_type = self.runtime.SDKCatalog, self.runtime.JobSession

        def respond(request):
            self.requests.append(request)
            raise AssertionError("Local recovery must not contact Scenario")

        self.respond = respond

        def adapter(credentials, **options):
            value = self.api.SDKAdapter(
                credentials, transport=httpx.MockTransport(lambda req: self.respond(req)), **options
            )
            self.adapters.append(value)
            return value

        def session(*args, **options):
            value = session_type(*args, **options)
            self.sessions.append(value)
            return value

        self.enterContext(
            patch.object(
                self.runtime,
                "SDKCatalog",
                side_effect=lambda *a, **k: catalog_type(*a, adapter_factory=adapter, **k),
            )
        )
        self.enterContext(patch.object(self.runtime, "JobSession", side_effect=session))
        self.addCleanup(self.cleanup_jobs)

    def cleanup_jobs(self):
        self.runtime.state.reset()
        for session in self.sessions:
            session.shutdown()

    def seed(self, state=None):
        m = self.storemod
        store = self.runtime.ensure_job_store()
        rec = store.create(
            m.JobIntent(
                "request",
                store.scope,
                m.JobOrigin("file", "scene", "revision"),
                "model",
                "model",
                "a" * 64,
                "b" * 64,
                "0.10000000000000001",
            )
        )
        if state is not None:
            rec = store.transition("request", expected_revision=rec.revision, state=state)
        return store, rec

    def test_inspection_reuses_session_preserves_exact_cost_and_starts_no_requests(self):
        store, record = self.seed(self.storemod.JobState.SUBMITTING)
        first = self.tools.list_local_jobs({})
        session = self.runtime.ensure_job_session()
        second = self.tools.list_local_jobs({})
        self.assertEqual(first, second)
        self.assertIs(session, self.runtime.state.job_session)
        self.assertEqual(session.scope, self.runtime.state.catalog.scope)
        self.assertEqual(first["jobs"][0]["cu_cost_exact"], record.intent.quote_cost)
        self.assertEqual(first["jobs"][0]["action"], "reconcile_unknown")
        self.assertEqual(store.get("request"), record)
        self.assertEqual(self.requests, [])
        self.assertIsNone(self.runtime.state.manager)

    def test_reset_reopens_records_and_rejects_previous_context(self):
        _, record = self.seed()
        old = self.tools.list_local_jobs({})
        self.runtime.state.reset()
        new = self.tools.list_local_jobs({})
        self.assertEqual(old["jobs"], new["jobs"])
        self.assertNotEqual(old["context_id"], new["context_id"])
        with self.assertRaisesRegex(Exception, "context changed"):
            self.tools.cancel_prepared_job(
                dict(
                    context_id=old["context_id"],
                    request_id="request",
                    expected_revision=record.revision,
                )
            )
        self.assertTrue(self.adapters[0]._closed)

    def test_file_load_replaces_retired_session_and_invalidates_context_token(self):
        _, record = self.seed()
        old = self.tools.list_local_jobs({})
        session = self.runtime.state.job_session
        filepath = str(self.root / "recovery.blend")
        bpy.ops.wm.save_as_mainfile(filepath=filepath)
        bpy.ops.wm.open_mainfile(filepath=filepath)
        self.assertFalse(session.active)
        new = self.tools.list_local_jobs({})
        self.assertEqual(old["jobs"], new["jobs"])
        self.assertNotEqual(old["context_id"], new["context_id"])
        self.assertIsNot(session, self.runtime.state.job_session)
        self.assertTrue(self.runtime.state.job_session.active)
        args = dict(request_id="request", expected_revision=record.revision)
        with self.assertRaisesRegex(Exception, "context changed"):
            self.tools.cancel_prepared_job(dict(context_id=old["context_id"], **args))
        result = self.tools.cancel_prepared_job(dict(context_id=new["context_id"], **args))
        self.assertEqual(result["state"], "canceled")
        self.assertEqual(self.requests, [])

    def test_credential_change_isolates_records_and_cannot_cancel_same_id(self):
        _, original = self.seed()
        old = self.tools.list_local_jobs({})
        secret = self.prefs.api_secret
        self.prefs.api_secret = "other-fixture-secret"
        self.assertIsNone(self.runtime.state.job_session)
        other, other_record = self.seed()
        with self.assertRaisesRegex(Exception, "context changed"):
            self.tools.cancel_prepared_job(
                dict(
                    context_id=old["context_id"],
                    request_id="request",
                    expected_revision=original.revision,
                )
            )
        self.assertEqual(other.get("request"), other_record)
        self.prefs.api_secret = secret
        self.assertEqual(self.tools.list_local_jobs({})["jobs"][0]["state"], "prepared")

    def test_project_changes_isolate_jobs_and_invalidate_prior_context(self):
        self.addCleanup(setattr, self.prefs, "project_id", self.prefs.project_id)
        default_store, original = self.seed()
        old = self.tools.list_local_jobs({})
        session = self.runtime.state.job_session
        self.prefs.project_id = " project-a "
        self.assertFalse(session.active)
        self.assertIsNone(self.runtime.state.job_store)
        self.assertEqual(self.tools.list_local_jobs({})["jobs"], [])
        project_store, project_record = self.seed()
        self.assertEqual(project_store.scope.project_id, "project-a")
        self.assertEqual(project_store.scope.account_id, default_store.scope.account_id)
        with self.assertRaisesRegex(Exception, "context changed"):
            self.tools.cancel_prepared_job(
                dict(
                    context_id=old["context_id"],
                    request_id="request",
                    expected_revision=original.revision,
                )
            )
        self.prefs.project_id = "project-b"
        self.assertEqual(self.tools.list_local_jobs({})["jobs"], [])
        self.prefs.project_id = "project-a"
        self.assertEqual(self.runtime.ensure_job_store().get("request"), project_record)
        self.prefs.project_id = ""
        self.assertEqual(self.runtime.ensure_job_store().get("request"), original)
        self.assertEqual(self.requests, [])

    def test_normalized_project_does_not_retire_unchanged_selection(self):
        self.addCleanup(setattr, self.prefs, "project_id", self.prefs.project_id)
        self.prefs.project_id = "project-a"
        first = self.runtime.ensure_job_session()
        catalog = self.runtime.state.catalog
        self.prefs.project_id = " project-a "
        self.assertIs(first, self.runtime.ensure_job_session())
        self.assertIs(catalog, self.runtime.state.catalog)
        self.assertTrue(first.active)

    def test_invalid_project_retires_old_context_without_opening_an_adapter(self):
        self.addCleanup(setattr, self.prefs, "project_id", self.prefs.project_id)
        previous = self.runtime.ensure_job_session()
        self.prefs.project_id = "https://private.invalid/project"
        before = len(self.adapters)
        with self.assertRaisesRegex(Exception, "Project ID must be an opaque ID"):
            self.runtime.ensure_catalog()
        self.assertFalse(previous.active)
        self.assertIsNone(self.runtime.state.catalog)
        self.assertIsNone(self.runtime.state.job_store)
        self.assertEqual(len(self.adapters), before)
        self.assertEqual(self.requests, [])

    def test_local_cancellation_is_revision_guarded_and_rejects_claimed_work(self):
        store, record = self.seed()
        context = self.tools.list_local_jobs({})["context_id"]
        args = dict(context_id=context, request_id="request", expected_revision=record.revision)
        with self.assertRaises(self.storemod.StoreConflict):
            self.tools.cancel_prepared_job({**args, "expected_revision": 99})
        result = self.tools.cancel_prepared_job(args)
        self.assertEqual(result["state"], "canceled")
        self.assertEqual(store.get("request").state, self.storemod.JobState.CANCELED)
        with self.assertRaises(self.storemod.StoreConflict):
            self.tools.cancel_prepared_job(args)
        self.assertEqual(self.requests, [])

    def test_uncertain_work_cannot_be_canceled_as_prepared(self):
        store, record = self.seed(self.storemod.JobState.SUBMITTING)
        context = self.tools.list_local_jobs({})["context_id"]
        with self.assertRaises((ValueError, self.storemod.StoreError)):
            self.tools.cancel_prepared_job(
                dict(context_id=context, request_id="request", expected_revision=record.revision)
            )
        self.assertEqual(store.get("request"), record)

    def saved_job(self, request_id, *states, operation="model", film_task=None):
        m = self.storemod
        store = self.runtime.ensure_job_store()
        record = store.create(
            m.JobIntent(
                request_id,
                store.scope,
                m.JobOrigin("file", "scene", "revision"),
                operation,
                "model",
                "a" * 64,
                "b" * 64,
                "0.10000000000000001",
                film_task=film_task,
            )
        )
        for state in states:
            record = store.transition(
                request_id,
                expected_revision=record.revision,
                state=state,
                remote_job_id=f"remote-{request_id}" if state == m.JobState.REMOTE else None,
            )
        return record

    def native_cancel(self, context_id, record, **changes):
        args = dict(
            context_id=context_id,
            request_id=record.intent.request_id,
            expected_revision=record.revision,
            action="cancel_prepared",
        )
        return bpy.ops.scenario.recover_job(**dict(args, **changes))

    def test_native_controls_offer_local_cancellation_only_for_prepared_jobs(self):
        state = self.storemod.JobState
        records = {
            "prepared": self.saved_job("prepared"),
            "workflow": self.saved_job("workflow", operation="workflow"),
            "prompt": self.saved_job("prompt", operation="prompt"),
            "translate": self.saved_job("translate", operation="translate"),
            "submitting": self.saved_job("submitting", state.SUBMITTING),
            "uncertain": self.saved_job("uncertain", state.SUBMITTING, state.UNCERTAIN),
            "remote": self.saved_job("remote", state.SUBMITTING, state.REMOTE),
            "canceled": self.saved_job("canceled", state.CANCELED),
        }
        jobs = self.runtime.inspect_model_jobs()
        offered = {
            key for key in records if "cancel_prepared" in jobs.views[key].meta["recovery_actions"]
        }
        self.assertEqual(offered, {"prepared", "workflow", "prompt", "translate"})
        for key in offered:
            self.assertEqual(jobs.views[key].meta["recovery_actions"], ("cancel_prepared",))
            self.assertEqual(jobs.status(key)["actions"], ("cancel_prepared",))
        # Local cancellation never routes through the remote recovery dispatcher.
        with self.assertRaisesRegex(Exception, "available action changed"):
            jobs.control("prepared", records["prepared"].revision, "cancel_prepared")
        self.assertEqual({key: self.runtime.state.job_store.get(key) for key in records}, records)
        self.assertEqual(self.requests, [])

    def confirm_cancel(self, record):
        operator = SimpleNamespace(
            context_id=self.runtime.state.job_context_id,
            request_id=record.intent.request_id,
            expected_revision=record.revision,
            action="cancel_prepared",
        )
        confirm = MagicMock(return_value={"RUNNING_MODAL"})
        context = SimpleNamespace(window_manager=SimpleNamespace(invoke_confirm=confirm))
        cls = submodule("blender.job_recovery").SCENARIO_OT_recover_job
        self.assertEqual(cls.invoke(operator, context, "event"), {"RUNNING_MODAL"})
        return operator, confirm

    def test_native_cancellation_confirms_before_changing_saved_state(self):
        film = self.storemod.FilmTaskBinding("production", "take", "c" * 64, "d" * 64)
        records = {
            "prepared": self.saved_job("prepared"),
            "film": self.saved_job("film", film_task=film),
        }
        self.runtime.inspect_model_jobs()
        message = "Cancel this unsent request locally; nothing is sent to Scenario."
        film_note = " A Film task stays reserved; use a new take name to try again."
        for key, expected in (("prepared", message), ("film", message + film_note)):
            with self.subTest(key=key):
                operator, confirm = self.confirm_cancel(records[key])
                confirm.assert_called_once_with(
                    operator,
                    "event",
                    title="Cancel prepared job?",
                    message=expected,
                    confirm_text="Discard unsent job",
                )
                saved = self.runtime.state.job_store.get(key)
                self.assertEqual(saved, records[key])
                self.assertEqual(
                    (saved.state, saved.revision),
                    (self.storemod.JobState.PREPARED, records[key].revision),
                )
        self.assertEqual(self.requests, [])

    def test_native_cancellation_persists_locally_without_service_requests(self):
        record = self.saved_job("prepared")
        jobs = self.runtime.inspect_model_jobs()
        view = jobs.views["prepared"]
        view.error = "Submission did not complete; inspect the saved job before continuing"
        context = self.runtime.state.job_context_id
        self.assertEqual(self.native_cancel(context, record), {"FINISHED"})
        saved = self.runtime.state.job_store.get("prepared")
        self.assertEqual(saved.state, self.storemod.JobState.CANCELED)
        self.assertEqual(saved.revision, record.revision + 1)
        self.assertEqual((view.status, view.error), ("canceled", None))
        self.assertEqual(view.meta["recovery_actions"], ())
        self.assertNotIn("prepared", jobs._paused)
        self.assertIn(view, self.runtime.state.jobs_view)
        self.assertEqual(self.tools.list_local_jobs({})["jobs"][0]["state"], "canceled")
        with self.assertRaisesRegex(RuntimeError, "Recovery did not complete"):
            self.native_cancel(context, saved)
        self.assertEqual(self.runtime.state.job_store.get("prepared"), saved)
        self.assertEqual(self.requests, [])

    def test_native_cancellation_rejects_stale_revision_and_changed_context(self):
        record = self.saved_job("prepared")
        self.runtime.inspect_model_jobs()
        context = self.runtime.state.job_context_id
        with self.assertRaisesRegex(RuntimeError, "Recovery did not complete"):
            self.native_cancel(context, record, expected_revision=record.revision + 1)
        self.runtime.state.reset()
        self.runtime.inspect_model_jobs()
        self.assertNotEqual(context, self.runtime.state.job_context_id)
        with self.assertRaisesRegex(RuntimeError, "context changed"):
            self.native_cancel(context, record)
        self.assertEqual(self.runtime.ensure_job_store().get("prepared"), record)
        self.assertEqual(self.requests, [])

    def test_native_and_mcp_cancellation_share_one_runtime_command(self):
        native, agent = self.saved_job("native"), self.saved_job("agent")
        jobs = self.runtime.inspect_model_jobs()
        context = self.runtime.state.job_context_id
        shared = self.runtime.cancel_prepared_job
        with patch.object(self.runtime, "cancel_prepared_job", wraps=shared) as command:
            self.assertEqual(self.native_cancel(context, native), {"FINISHED"})
            result = self.tools.cancel_prepared_job(
                dict(context_id=context, request_id="agent", expected_revision=agent.revision)
            )
        self.assertEqual(
            command.call_args_list,
            [call(context, "native", native.revision), call(context, "agent", agent.revision)],
        )
        self.assertEqual(result["state"], "canceled")
        self.assertEqual({jobs.views[key].status for key in ("native", "agent")}, {"canceled"})
        self.assertEqual(self.requests, [])

    def test_invalid_revision_fails_before_context_creation(self):
        for value in (True, -1, 0.0, "0", None):
            with self.subTest(value=value), self.assertRaises(ValueError):
                self.tools.cancel_prepared_job(
                    dict(context_id="unknown", request_id="request", expected_revision=value)
                )
        self.assertIsNone(self.runtime.state.catalog)

    def test_session_factory_failure_closes_adapter(self):
        with patch.object(self.runtime, "JobSession", side_effect=RuntimeError("fixture")):
            with self.assertRaisesRegex(RuntimeError, "fixture"):
                self.runtime.ensure_job_session()
        self.assertTrue(self.adapters[0]._closed)
        self.assertIsNone(self.runtime.state.job_session)
        self.assertIsNone(self.runtime.state.job_context_id)

    def test_inflight_receipt_stays_in_old_scope_and_headless_loop_reaps_it(self):
        entered, release = threading.Event(), threading.Event()
        self.addCleanup(release.set)

        def respond(request):
            self.requests.append(request)
            if request.url.params.get("dryRun") == "true":
                return self.httpx.Response(200, json={"creativeUnitsCost": 1})
            entered.set()
            if not release.wait(5):
                raise AssertionError("Fixture did not release request")
            return self.httpx.Response(200, json={"job": {"jobId": "fixture-remote"}})

        self.respond = respond
        with online_access(True):
            session = self.runtime.ensure_job_session()
            store = self.runtime.state.job_store
            adapter = self.adapters[0]
            origin = session.capture(bpy.context.scene)
            estimate = adapter.estimate_workflow({"id": "fixture-workflow", "inputs": []}, {})
            prepared = session.prepare(estimate, origin=origin)
            task = session.submit(
                prepared, operation="workflow", target_id="fixture-workflow", payload={}
            )
            self.assertTrue(entered.wait(5))
            self.prefs.api_secret = "other-fixture-secret"
            self.assertFalse(adapter._closed)
            self.assertFalse(adapter._online())
            release.set()
            task.result(5)
            service = submodule("blender.mcp_service")
            server_type = service.McpServer
            serve = server_type.serve_blocking
            observed = []

            def serve_once(server, stop_event, *, before_process):
                self.assertIs(before_process, self.runtime.sync_catalog_context)

                def tick():
                    before_process()
                    observed.append(adapter._closed)
                    stop_event.set()

                serve(server, stop_event, before_process=tick)

            def ephemeral_server(host, port, *args, **kwargs):
                return server_type(host, 0, *args, **kwargs)

            with (
                patch.object(server_type, "serve_blocking", serve_once),
                patch.object(service, "McpServer", side_effect=ephemeral_server),
            ):
                self.assertEqual(service.cli(["--token", "synthetic-cli-token"]), 0)
            self.assertEqual(observed, [True])
            self.assertTrue(adapter._closed)
            self.assertEqual(store.get(prepared.intent.request_id).remote_job_id, "fixture-remote")
            self.assertEqual(self.tools.list_local_jobs({})["jobs"], [])
            self.assertEqual(len(self.requests), 2)
