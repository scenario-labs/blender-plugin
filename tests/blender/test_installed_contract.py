# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Basic installed runtime and Blender-thread MCP checks, with no Scenario service."""

import importlib
import os
import pkgutil
import socket
import threading
import time
import unittest
from unittest.mock import patch

import bpy
from helpers import addon_name, reset_scene, submodule
from test_mcp_server import post


class InstalledContractTests(unittest.TestCase):
    def test_core_and_mcp_dependencies_import_from_the_installed_package(self):
        for folder in ("core", "mcp"):
            root = submodule(folder)
            for info in pkgutil.walk_packages(root.__path__, root.__name__ + "."):
                importlib.import_module(info.name)
        self.assertIn(addon_name(), bpy.context.preferences.addons)

    def test_runtime_is_offline_with_credentials_present(self):
        runtime = submodule("blender.runtime")
        prefs = runtime.prefs()
        saved = (prefs.api_key, prefs.api_secret)
        try:
            prefs.api_key, prefs.api_secret = "fixture-key", "fixture-secret"
            self.assertTrue(runtime.credentials().valid)
            self.assertFalse(runtime.online())
            self.assertFalse(bpy.ops.scenario.generate.poll())
        finally:
            prefs.api_key, prefs.api_secret = saved

    def test_blockout_network_operators_reject_probe_offline_and_missing_credentials(self):
        runtime = submodule("blender.runtime")
        prefs = runtime.prefs()
        saved = (prefs.api_key, prefs.api_secret)
        operators = (bpy.ops.scenario.blockout_design, bpy.ops.scenario.blockout_refine)
        try:
            prefs.api_key, prefs.api_secret = "fixture-key", "fixture-secret"
            for operator in operators:
                self.assertFalse(operator.poll())
            with patch.object(runtime, "online", return_value=True):
                with patch.dict(os.environ, {"SCENARIO_GUI_PROBE": "1"}):
                    for operator in operators:
                        self.assertFalse(operator.poll())
                        with self.assertRaises(RuntimeError):
                            operator()
                with patch.dict(os.environ, {"SCENARIO_GUI_PROBE": "0"}):
                    for operator in operators:
                        self.assertTrue(operator.poll())
                    prefs.api_key, prefs.api_secret = "", ""
                    for operator in operators:
                        self.assertFalse(operator.poll())
        finally:
            prefs.api_key, prefs.api_secret = saved

    def test_authenticated_mcp_scene_tool_runs_on_blender_main_thread(self):
        reset_scene()
        bpy.ops.mesh.primitive_cube_add()
        bpy.context.object.name = "RunnerCube"
        protocol = submodule("mcp.protocol")
        server_module = submodule("mcp.server")
        tools = submodule("mcp.tools_blender")
        registry = protocol.Registry()
        seen_threads = []

        def scene(args):
            seen_threads.append(threading.current_thread())
            return tools.scene_summary(args)

        registry.add(protocol.ToolSpec("scene_summary", "Scene", {"type": "object"}, scene))
        with socket.socket() as reservation:
            reservation.bind(("127.0.0.1", 0))
            port = reservation.getsockname()[1]
        server = server_module.McpServer(
            "127.0.0.1",
            port,
            "fixture-token",
            registry,
            {"name": "test", "version": "0"},
            timeout=5,
        )
        result = []
        server.start()
        request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {"name": "scene_summary", "arguments": {}},
        }
        worker = threading.Thread(
            target=lambda: result.append(post(server.url, "fixture-token", request)), daemon=True
        )
        try:
            worker.start()
            deadline = time.monotonic() + 10
            while worker.is_alive() and time.monotonic() < deadline:
                server.process_pending()
                time.sleep(0.01)
            worker.join(timeout=1)
            self.assertFalse(worker.is_alive())
            self.assertEqual(result[0][0], 200)
            self.assertIn("RunnerCube", str(result[0][1]))
            self.assertEqual(seen_threads, [threading.main_thread()])
        finally:
            server.stop()
