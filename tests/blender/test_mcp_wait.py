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

    def test_prototype_wait_returns_snapshot_immediately_without_resubmitting(self):
        self.manager.registry.save()
        original = self.manager.paths.registry_file.read_bytes()
        for timeout in (0, 0.01, 170):
            result = self.tools.wait_for_job({"job_id": self.rec.job_id, "timeout": timeout})
            self.assertIsInstance(result, dict)
            self.assertEqual(result["status"], "running")
            self.assertIn("local snapshot", result["note"])
            self.assertIn("recover_cloud_job", result["note"])
            self.assertEqual(self.manager.registry.all(), [self.rec])
            self.assertEqual(self.manager.paths.registry_file.read_bytes(), original)
            self.assertFalse(self.manager.has_active())

    def test_terminal_prototype_jobs_return_their_saved_status(self):
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
            self.assertEqual(scene_calls, [True])
            self.assertNotIn("error", scene.result())
            pump_until(waiting.done)
            result = waiting.result()
        self.assertFalse(result["result"].get("isError"), result)
        status = json.loads(result["result"]["content"][0]["text"])
        self.assertEqual(status["status"], "running")
        self.assertIn("local snapshot", status["note"])
