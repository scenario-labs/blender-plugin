# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Actual registered command and clean native headless MCP process lifetime."""

import json
import os
import signal
import socket
import subprocess
import tempfile
import time
import unittest
import urllib.error
import urllib.request
from pathlib import Path

import bpy
from helpers import submodule


class McpCliTests(unittest.TestCase):
    def child_environment(self):
        env = dict(os.environ)
        profile = env.get("BLENDER_USER_RESOURCES", "")
        self.assertTrue(
            profile and Path(profile).is_absolute(), "Require the runner's isolated profile"
        )
        for key in list(env):
            if key.startswith("SCENARIO_"):
                env.pop(key)
        return env

    def test_cli_command_is_registered_and_has_help(self):
        self.assertIsNotNone(submodule("blender.runtime").state.cli_handle)
        for args, expected in [
            (["help"], "scenario_blender"),
            (["scenario_blender", "--help"], "usage: scenario_blender"),
        ]:
            result = subprocess.run(
                [bpy.app.binary_path, "--background", "--command", *args],
                env=self.child_environment(),
                capture_output=True,
                text=True,
                timeout=60,
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn(expected, result.stdout + result.stderr)

    @unittest.skipIf(os.name == "nt", "POSIX signal shutdown; Windows acceptance is separate")
    def test_cli_lists_tools_executes_on_main_thread_and_stops_cleanly(self):
        for stop_signal in (signal.SIGINT, signal.SIGTERM):
            with self.subTest(signal=stop_signal):
                self._exercise_cli(stop_signal)

    def _exercise_cli(self, stop_signal):
        with socket.socket() as reservation:
            reservation.bind(("127.0.0.1", 0))
            port = reservation.getsockname()[1]
        token = "synthetic-cli-token"
        env = self.child_environment()
        env["SCENARIO_BLENDER_TOKEN"] = token
        with tempfile.TemporaryFile(mode="w+") as log:
            process = subprocess.Popen(
                [
                    bpy.app.binary_path,
                    "--background",
                    "--online-mode",
                    "--command",
                    "scenario_blender",
                    "--port",
                    str(port),
                ],
                env=env,
                stdout=log,
                stderr=subprocess.STDOUT,
                text=True,
            )
            try:
                url = f"http://127.0.0.1:{port}/mcp"

                def request(method, params=None):
                    data = json.dumps(
                        {"jsonrpc": "2.0", "id": 1, "method": method, "params": params or {}}
                    ).encode()
                    req = urllib.request.Request(
                        url,
                        data=data,
                        headers={
                            "Authorization": f"Bearer {token}",
                            "Content-Type": "application/json",
                        },
                    )
                    with urllib.request.urlopen(req, timeout=5) as response:
                        return json.loads(response.read())

                deadline = time.monotonic() + 45
                while True:
                    if process.poll() is not None:
                        log.seek(0)
                        self.fail("CLI exited before serving: " + log.read())
                    try:
                        result = request("tools/list")
                        break
                    except (urllib.error.URLError, TimeoutError):
                        if time.monotonic() >= deadline:
                            raise
                        time.sleep(0.1)
                self.assertIn("scene_summary", [item["name"] for item in result["result"]["tools"]])
                scene = request("tools/call", {"name": "scene_summary", "arguments": {}})
                self.assertNotIn("error", scene)
                self.assertFalse(scene["result"].get("isError"))
                process.send_signal(stop_signal)
                returncode = process.wait(timeout=15)
                log.seek(0)
                output = log.read()
                self.assertEqual(returncode, 0, output)
                self.assertIn("token provided; hidden", output)
                self.assertNotIn(token, output)
                self.assertNotIn("not registered", output)
                with socket.socket() as closed:
                    closed.settimeout(1)
                    self.assertNotEqual(closed.connect_ex(("127.0.0.1", port)), 0)
            finally:
                if process.poll() is None:
                    process.kill()
                    process.wait(timeout=10)
