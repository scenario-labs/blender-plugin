# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Selected application jobs and MCP recovery in the installed extension."""

import tempfile
import threading
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

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
            submodule("blender.mcp_service").process_pending()
            self.assertTrue(adapter._closed)
            self.assertEqual(store.get(prepared.intent.request_id).remote_job_id, "fixture-remote")
            self.assertEqual(self.tools.list_local_jobs({})["jobs"], [])
            self.assertEqual(len(self.requests), 2)
