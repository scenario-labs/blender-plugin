# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Actual registered command and clean native headless MCP process lifetime."""

import io
import json
import os
import signal
import socket
import subprocess
import tempfile
import time
import types
import unittest
import urllib.error
import urllib.request
from contextlib import redirect_stderr
from pathlib import Path
from unittest.mock import patch

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

    def test_busy_ports_report_usage_error_and_restore_signal_handlers(self):
        service = submodule("blender.mcp_service")
        error_output = io.StringIO()
        with (
            patch.object(service.runtime, "online", return_value=True),
            patch.object(service.runtime.state, "mcp_token", service.runtime.state.mcp_token),
            patch.object(service, "McpServer") as constructor,
            patch.object(signal, "signal", return_value=signal.SIG_DFL) as handlers,
            redirect_stderr(error_output),
        ):
            server = constructor.return_value
            server.start.side_effect = OSError("no free port from 9876")
            with self.assertRaises(SystemExit) as error:
                service.cli(["--token", "synthetic-cli-token"])
            self.assertEqual(error.exception.code, 2)
            self.assertIn(
                "Unable to start local MCP: no free port from 9876", error_output.getvalue()
            )
            self.assertNotIn("Traceback", error_output.getvalue())
            server.stop.assert_called_once()
            server.serve_blocking.assert_not_called()
            self.assertEqual(handlers.call_args_list[-2].args, (signal.SIGINT, signal.SIG_DFL))
            self.assertEqual(handlers.call_args_list[-1].args, (signal.SIGTERM, signal.SIG_DFL))

    @unittest.skipIf(os.name == "nt", "POSIX signal shutdown; Windows acceptance is separate")
    def test_cli_lists_tools_executes_on_main_thread_and_stops_cleanly(self):
        for stop_signal in (signal.SIGINT, signal.SIGTERM):
            with self.subTest(signal=stop_signal):
                self._exercise_cli(stop_signal)

    @unittest.skipIf(os.name == "nt", "POSIX signal shutdown; Windows acceptance is separate")
    def test_cli_reads_the_selection_of_a_loaded_file(self):
        # A saved file read with --background gives the command a context without
        # selected_objects or active_object; the summary reads them from the view layer.
        with tempfile.TemporaryDirectory() as folder:
            path = str(Path(folder) / "selection.blend")
            script = (
                "import bpy, sys\n"
                "for obj in bpy.context.view_layer.objects:\n"
                "    obj.select_set(obj.type in {'MESH', 'CAMERA'})\n"
                "bpy.context.view_layer.objects.active = bpy.data.objects['Camera']\n"
                "bpy.ops.wm.save_as_mainfile(filepath=sys.argv[-1])\n"
            )
            subprocess.run(
                [
                    bpy.app.binary_path,
                    "--background",
                    "--factory-startup",
                    "--python-expr",
                    script,
                    "--",
                    path,
                ],
                env=self.child_environment(),
                capture_output=True,
                check=True,
                timeout=60,
            )
            summary = json.loads(
                self._exercise_cli(signal.SIGTERM, blend=path)["result"]["content"][0]["text"]
            )
        self.assertEqual(summary["file"], path)
        self.assertEqual(sorted(summary["selected"]), ["Camera", "Cube"])
        self.assertEqual(summary["selected_count"], 2)
        self.assertEqual(summary["active"], "Camera")

    def test_selection_reads_the_view_layer_without_screen_members(self):
        selection = submodule("blender.selection")
        layer = bpy.context.view_layer
        mesh = bpy.data.meshes.new("Selection probe")
        objects = [bpy.data.objects.new(f"Selection probe {i}", mesh) for i in range(3)]
        try:
            for obj in objects:
                layer.id_data.collection.objects.link(obj)
            layer.update()  # a base can be selected once the view layer has evaluated it
            for obj in layer.objects:
                obj.select_set(obj in objects[:2])
            layer.objects.active = objects[1]
            headless = types.SimpleNamespace(view_layer=layer)
            self.assertEqual(selection.selected_objects(headless), objects[:2])
            self.assertIs(selection.active_object(headless), objects[1])
            # On the desktop the context's own members win.
            desktop = types.SimpleNamespace(
                view_layer=layer, selected_objects=[objects[2]], active_object=None
            )
            self.assertEqual(selection.selected_objects(desktop), [objects[2]])
            self.assertIsNone(selection.active_object(desktop))
        finally:
            for obj in objects:
                bpy.data.objects.remove(obj)
            bpy.data.meshes.remove(mesh)

    def _exercise_cli(self, stop_signal, blend=None):
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
                    *([blend] if blend else []),
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
                return scene
            finally:
                if process.poll() is None:
                    process.kill()
                    process.wait(timeout=10)
