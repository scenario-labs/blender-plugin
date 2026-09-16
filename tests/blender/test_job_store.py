# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Exercise SQLite and the installed intent store with Blender's own Python."""

import tempfile
import unittest
from pathlib import Path

import bpy
from helpers import submodule


class JobStoreTests(unittest.TestCase):
    def test_installed_store_preserves_scope_and_uncertain_intent(self):
        module = submodule("core.jobs.store")
        scope = module.JobScope("https://service.example.invalid/v1", "fixture-account")
        intent = module.JobIntent(
            request_id="fixture-request",
            scope=scope,
            origin=module.JobOrigin("fixture-file", "fixture-scene", "fixture-revision"),
            operation="workflow",
            target_id="fixture-workflow",
            payload_sha256="a" * 64,
            quote_sha256="b" * 64,
            quote_cost="0.10000000000000001",
        )
        with tempfile.TemporaryDirectory(dir=bpy.utils.resource_path("USER")) as directory:
            path = Path(directory) / "jobs.sqlite3"
            store = module.JobStore(path, scope)
            record = store.create(intent)
            record = store.transition(
                intent.request_id,
                expected_revision=record.revision,
                state=module.JobState.SUBMITTING,
            )
            record = store.transition(
                intent.request_id,
                expected_revision=record.revision,
                state=module.JobState.UNCERTAIN,
            )
            reopened = module.JobStore(path, scope)
            self.assertEqual(reopened.get(intent.request_id), record)
            with self.assertRaises(ValueError):
                reopened.transition(
                    intent.request_id,
                    expected_revision=record.revision,
                    state=module.JobState.SUBMITTING,
                )
            other = module.JobStore(path, module.JobScope(scope.service, "other-account"))
            self.assertIsNone(other.get(intent.request_id))
            self.assertEqual(other.records(), ())

    def test_installed_coordinator_persists_before_sdk_dispatch(self):
        import httpx

        api = submodule("core.api.sdk_adapter")
        storage = submodule("core.jobs.store")
        commands = submodule("core.jobs.coordinator")
        scope = storage.JobScope("https://service.example.invalid/v1", "fixture-account")
        origin = storage.JobOrigin("fixture-file", "fixture-scene", "fixture-revision")
        with tempfile.TemporaryDirectory(dir=bpy.utils.resource_path("USER")) as directory:
            store = storage.JobStore(Path(directory) / "jobs.sqlite3", scope)
            calls = []

            def respond(request):
                calls.append(request)
                if request.url.params["dryRun"] == "true":
                    return httpx.Response(200, content=b'{"creativeUnitsCost":0.10000000000000001}')
                self.assertEqual(store.records()[0].state, storage.JobState.SUBMITTING)
                return httpx.Response(200, json={"job": {"jobId": "fixture-remote"}})

            with api.SDKAdapter(
                api.Credentials("fixture-key", "fixture-secret"),
                online=lambda: True,  # Only MockTransport is allowed; sockets remain guarded.
                account_id=scope.account_id,
                base_url=scope.service,
                transport=httpx.MockTransport(respond),
            ) as adapter:
                estimate = adapter.estimate_workflow({"id": "fixture-workflow", "inputs": []}, {})
                coordinator = commands.JobCoordinator(adapter, store)
                prepared = coordinator.prepare(estimate, origin)
                record = coordinator.submit(
                    prepared,
                    origin=origin,
                    operation="workflow",
                    target_id="fixture-workflow",
                    payload={},
                )
                self.assertEqual(record.state, storage.JobState.REMOTE)
                self.assertEqual(record.intent.quote_cost, "0.10000000000000001")
                self.assertEqual(len(calls), 2)
                with self.assertRaises(ValueError):
                    coordinator.submit(
                        prepared,
                        origin=origin,
                        operation="workflow",
                        target_id="fixture-workflow",
                        payload={},
                    )
                self.assertEqual(len(calls), 2)
