# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""A local agent's job wait leaves the installed main-thread executor available."""

import json
import threading
import time
import unittest
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch

from helpers import isolated_manager, submodule, temp_credentials


class McpWaitTests(unittest.TestCase):
    def setUp(self):
        self.runtime = submodule("blender.runtime")
        self.tools = submodule("mcp.tools_scenario")
        self.records = submodule("core.jobs.records")
        self.enterContext(patch.object(self.runtime, "state", self.runtime.RuntimeState()))
        self.prefs = self.enterContext(temp_credentials())
        self.manager = self.enterContext(isolated_manager())
        self.rec = self.records.JobRecord.new("image", "image", "fixture-model", {})
        self.rec.job_id, self.rec.status = "job_fixture", "running"
        self.manager.registry.add(self.rec)

    def pending(self, timeout=0.01):
        result = self.tools.wait_for_job({"job_id": self.rec.job_id, "timeout": timeout})
        self.assertIsInstance(result, submodule("mcp.protocol").DeferredTool)
        return result

    def test_timeout_reports_current_status_without_cancelling_or_resubmitting(self):
        pending = self.pending()
        with ThreadPoolExecutor(max_workers=1) as worker:
            worker.submit(pending.run).result(2)
        result = pending.finish(None)
        self.assertEqual(result["status"], "running")
        self.assertIn("still running", result["note"])
        self.assertEqual(self.manager.registry.all(), [self.rec])
        self.assertFalse(self.manager.has_active())

    def test_zero_timeout_and_terminal_jobs_return_immediately(self):
        result = self.tools.wait_for_job({"id": self.rec.local_id, "timeout": 0})
        self.assertIn("note", result)
        for status in ("success", "failed", "cancelled"):
            self.rec.status = status
            result = self.tools.wait_for_job({"id": self.rec.local_id})
            self.assertEqual(result["status"], status)
            self.assertNotIn("note", result)

    def test_invalid_timeouts_fail_before_runtime_access(self):
        with patch.object(self.runtime, "ensure_manager") as manager:
            for value in (-1, 171, True, None, "1", float("nan"), float("inf"), 10**1000):
                with self.subTest(value=repr(value)[:30]):
                    with self.assertRaisesRegex(ValueError, "finite number"):
                        self.tools.wait_for_job({"job_id": self.rec.job_id, "timeout": value})
            manager.assert_not_called()

    def test_waiter_reads_only_captured_python_records(self):
        pending = self.pending(1)
        with (
            patch.object(self.runtime, "credentials", side_effect=AssertionError("Worker bpy")),
            patch.object(self.runtime, "ensure_manager", side_effect=AssertionError("Worker bpy")),
            ThreadPoolExecutor(max_workers=1) as worker,
        ):
            future = worker.submit(pending.run)
            self.rec.status, self.rec.files = "success", ["fixture.png"]
            future.result(2)
        result = pending.finish(None)
        self.assertEqual(result["files"], ["fixture.png"])
        self.assertNotIn("note", result)

    def test_credentials_changed_before_delivery_reject_old_status(self):
        pending = self.pending()
        pending.run()
        self.prefs.api_secret = "replacement-secret"
        with self.assertRaisesRegex(RuntimeError, "context changed"):
            pending.finish(None)

    def test_reset_or_record_replacement_rejects_old_status(self):
        pending = self.pending()
        pending.run()
        replacement = self.records.JobRecord.from_dict(self.rec.to_dict())
        self.manager.registry.add(replacement)
        with self.assertRaisesRegex(RuntimeError, "context changed"):
            pending.finish(None)
        self.manager.registry.add(self.rec)
        self.runtime.state.reset()
        with self.assertRaisesRegex(RuntimeError, "context changed"):
            pending.finish(None)

    def test_manager_shutdown_releases_waiter_without_cancelling_job(self):
        pending = self.pending(170)
        with ThreadPoolExecutor(max_workers=1) as worker:
            future = worker.submit(pending.run)
            self.manager.shutdown()
            with self.assertRaisesRegex(RuntimeError, "not cancelled"):
                future.result(2)
        self.assertEqual(self.rec.status, "running")

    def test_authenticated_wait_keeps_scene_executor_available(self):
        protocol = submodule("mcp.protocol")
        server_module = submodule("mcp.server")
        registry = protocol.Registry()
        for spec in self.tools.SPECS:
            registry.add(spec)
        scene_calls = []

        def scene_probe(args):
            self.assertIs(threading.current_thread(), threading.main_thread())
            scene_calls.append(True)
            return {"available": True}

        registry.add(protocol.ToolSpec("scene_probe", "Fixture", {}, scene_probe))
        server = server_module.McpServer(
            "127.0.0.1", 0, "fixture-wait-token", registry, {}, timeout=2
        )
        server.start()
        server.port = server._httpd.server_address[1]
        self.addCleanup(server.stop)
        self.runtime.state.mcp = server

        def request(name, arguments=None):
            req = urllib.request.Request(
                server.url,
                data=json.dumps(
                    {
                        "id": 1,
                        "method": "tools/call",
                        "params": {"name": name, "arguments": arguments or {}},
                    }
                ).encode(),
                headers={
                    "Authorization": "Bearer fixture-wait-token",
                    "Content-Type": "application/json",
                },
            )
            with urllib.request.urlopen(req, timeout=5) as response:
                return json.load(response)

        def pump_until(condition):
            deadline = time.monotonic() + 3
            while not condition() and time.monotonic() < deadline:
                server.process_pending()
                time.sleep(0.001)
            self.assertTrue(condition())

        with ThreadPoolExecutor(max_workers=2) as worker:
            waiting = worker.submit(
                request, "wait_for_job", {"job_id": self.rec.job_id, "timeout": 2}
            )
            deadline = time.monotonic() + 3
            while server._queue.empty() and time.monotonic() < deadline:
                time.sleep(0.001)
            self.assertFalse(server._queue.empty())
            started = time.monotonic()
            server.process_pending()
            self.assertLess(time.monotonic() - started, 0.5)
            scene = worker.submit(request, "scene_probe")
            pump_until(scene.done)
            self.assertFalse(waiting.done())
            self.assertEqual(scene_calls, [True])
            self.assertNotIn("error", scene.result())
            self.rec.status = "success"
            pump_until(waiting.done)
            result = waiting.result()
        self.assertFalse(result["result"].get("isError"), result)
        status = json.loads(result["result"]["content"][0]["text"])
        self.assertEqual(status["status"], "success")

    def test_stopped_server_releases_worker_and_rejects_late_delivery(self):
        server = submodule("mcp.server").McpServer(
            "127.0.0.1", 0, "fixture-wait-token", submodule("mcp.protocol").Registry(), {}
        )
        server.start()
        server.port = server._httpd.server_address[1]
        self.addCleanup(server.stop)
        self.runtime.state.mcp = server
        pending = self.pending(170)
        with ThreadPoolExecutor(max_workers=1) as worker:
            future = worker.submit(pending.run)
            server.stop()
            with self.assertRaisesRegex(RuntimeError, "not cancelled"):
                future.result(2)
        self.rec.status = "success"
        with self.assertRaisesRegex(RuntimeError, "context changed"):
            pending.finish(None)
