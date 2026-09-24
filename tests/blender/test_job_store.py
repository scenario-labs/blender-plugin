# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Exercise SQLite and the installed intent store with Blender's own Python."""

import tempfile
import threading
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

    def test_installed_result_manifest_and_verified_file_recover_after_reopen(self):
        import hashlib

        module = submodule("core.jobs.store")
        transfers = submodule("core.jobs.transfers")
        scope = module.JobScope("https://service.example.invalid/v1", "fixture-account")
        intent = module.JobIntent(
            "result-request",
            scope,
            module.JobOrigin("file", "scene", "revision"),
            "model",
            "model",
            "a" * 64,
            "b" * 64,
            "1.0",
        )
        with tempfile.TemporaryDirectory(dir=bpy.utils.resource_path("USER")) as directory:
            root = Path(directory).resolve()
            store = module.JobStore(root / "jobs.sqlite3", scope)
            record = store.create(intent)
            for state in (
                module.JobState.SUBMITTING,
                module.JobState.REMOTE,
                module.JobState.SUCCEEDED,
            ):
                record = store.transition(
                    "result-request",
                    expected_revision=record.revision,
                    state=state,
                    remote_job_id="remote" if state == module.JobState.REMOTE else None,
                )
            content = b"offline result receipt"
            digest = hashlib.sha256(content).hexdigest()
            asset = module.ResultAsset("asset", "result.png", "image/png", len(content), digest)
            record = store.set_results(
                "result-request", (asset,), expected_revision=record.revision
            )
            record = store.transition(
                "result-request",
                expected_revision=record.revision,
                state=module.JobState.DOWNLOADING,
            )
            (root / asset.name).write_bytes(content)
            receipt = transfers.DownloadedResult(asset.name, len(content), digest)
            record = store.record_download(
                "result-request", "asset", receipt, expected_revision=record.revision
            )
            reopened = module.JobStore(root / "jobs.sqlite3", scope)
            self.assertEqual(reopened.get("result-request"), record)
            self.assertEqual(
                transfers.verify_download(root, record.results[0].receipt), root / asset.name
            )
            (root / asset.name).write_bytes(b"corrupt")
            with self.assertRaises(transfers.TransferError):
                transfers.verify_download(root, record.results[0].receipt)
            self.assertEqual(reopened.get("result-request"), record)

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

    def test_installed_recovery_polls_known_id_without_replay(self):
        self._check_recovery(worker=False)

    def test_installed_worker_polls_and_joins_without_blender_access(self):
        self._check_recovery(worker=True)

    def test_installed_cancellation_uses_retrieval_after_acknowledgement(self):
        self._check_recovery(worker=True, cancel=True)

    def test_installed_claimed_cancel_recovery_only_polls(self):
        self._check_recovery(worker=True, claimed=True)

    def _check_recovery(self, *, worker, cancel=False, claimed=False):
        import httpx

        api = submodule("core.api.sdk_adapter")
        storage = submodule("core.jobs.store")
        commands = submodule("core.jobs.coordinator")
        scope = storage.JobScope("https://service.example.invalid/v1", "fixture-account")
        with tempfile.TemporaryDirectory(dir=bpy.utils.resource_path("USER")) as directory:
            store = storage.JobStore(Path(directory) / "jobs.sqlite3", scope)
            intent = storage.JobIntent(
                "fixture-request",
                scope,
                storage.JobOrigin("fixture-file", "fixture-scene", "fixture-revision"),
                "model",
                "fixture-model",
                "a" * 64,
                "b" * 64,
                "0.1",
            )
            store.create(intent)
            store.transition(
                intent.request_id, expected_revision=0, state=storage.JobState.SUBMITTING
            )
            store.transition(
                intent.request_id,
                expected_revision=1,
                state=storage.JobState.REMOTE,
                remote_job_id="fixture-remote",
            )
            revision = 2
            if claimed:
                store.transition(
                    intent.request_id,
                    expected_revision=revision,
                    state=storage.JobState.CANCEL_REQUESTED,
                )
                store = storage.JobStore(Path(directory) / "jobs.sqlite3", scope)
                revision += 1
            calls = []

            main_thread = threading.get_ident()

            def respond(request):
                calls.append(request)
                self.assertEqual(threading.get_ident() != main_thread, worker)
                self.assertEqual(request.method, "POST" if cancel and len(calls) == 2 else "GET")
                status = "success"
                if cancel:
                    status = {1: "in-progress", 2: "canceled", 3: "success"}[len(calls)]
                    expected = (
                        storage.JobState.REMOTE
                        if len(calls) == 1
                        else storage.JobState.CANCEL_REQUESTED
                    )
                    self.assertEqual(store.get(intent.request_id).state, expected)
                return httpx.Response(
                    200,
                    json={
                        "job": {"jobId": "fixture-remote", "jobType": "custom", "status": status}
                    },
                )

            with api.SDKAdapter(
                api.Credentials("key", "secret"),
                online=lambda: True,
                account_id=scope.account_id,
                base_url=scope.service,
                transport=httpx.MockTransport(respond),
            ) as adapter:
                coordinator = commands.JobCoordinator(adapter, store)
                self.assertEqual(
                    coordinator.recovery_plan()[0].action, commands.RecoveryAction.POLL_REMOTE
                )
                self.assertEqual(calls, [])
                if worker:
                    owner = submodule("core.jobs.workers").JobWorkers(coordinator, workers=1)
                    try:
                        command = owner.cancel_remote if cancel else owner.refresh_remote
                        snapshot = command(intent.request_id, expected_revision=revision).result(
                            timeout=5
                        )
                    finally:
                        owner.shutdown()
                    self.assertTrue(all(not thread.is_alive() for thread in owner._threads))
                else:
                    snapshot = coordinator.refresh_remote(
                        intent.request_id, expected_revision=revision
                    )
                self.assertEqual(snapshot.record.state, storage.JobState.SUCCEEDED)
                self.assertEqual(len(calls), 3 if cancel else 1)
