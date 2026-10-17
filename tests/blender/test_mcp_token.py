# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""The local MCP token and port stay the same across restarts, and a busy port is reported."""

import json
import os
import socket
import stat
import unittest
import urllib.error
import urllib.request

import bpy
from helpers import online_access, submodule


def free_port():
    with socket.socket() as reservation:
        reservation.bind(("127.0.0.1", 0))
        return reservation.getsockname()[1]


def list_tools(port, token):
    request = urllib.request.Request(
        f"http://127.0.0.1:{port}/mcp",
        data=json.dumps({"jsonrpc": "2.0", "id": 1, "method": "tools/list"}).encode(),
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(request, timeout=5) as response:
            return response.status
    except urllib.error.HTTPError as error:
        return error.code


class McpTokenTests(unittest.TestCase):
    def setUp(self):
        self.runtime = submodule("blender.runtime")
        self.service = submodule("blender.mcp_service")
        self.local_token = submodule("mcp.local_token")
        self.service.stop()
        self.addCleanup(self.service.stop)
        self.prefs = self.runtime.prefs()
        saved_port, saved_token = self.prefs.mcp_port, self.runtime.state.mcp_token
        self.addCleanup(setattr, self.prefs, "mcp_port", saved_port)
        self.addCleanup(setattr, self.runtime.state, "mcp_token", saved_token)
        self.prefs.mcp_port = free_port()
        self.path = os.path.join(self.service.token_dir(), self.local_token.TOKEN_FILE)
        if os.path.exists(self.path):
            os.replace(self.path, self.path + ".before-test")
            self.addCleanup(os.replace, self.path + ".before-test", self.path)
        self.runtime.state.mcp_token = ""
        self.enterContext(online_access(True))

    def restart_session(self):
        """What a new Blender session sees: no token in memory, the saved file on disk."""
        self.service.stop()
        self.runtime.state.mcp_token = ""
        return self.service.start()

    def test_token_and_port_survive_a_restart_from_a_private_file(self):
        server = self.service.start()
        self.assertIsNotNone(server, self.service.status()["error"])
        token, url = self.service.status()["token"], server.url
        self.assertEqual(url, f"http://127.0.0.1:{self.prefs.mcp_port}/mcp")
        with open(self.path, encoding="ascii") as handle:
            self.assertEqual(handle.read().strip(), token)
        if os.name == "posix":
            self.assertEqual(stat.S_IMODE(os.stat(self.path).st_mode), 0o600)
        again = self.restart_session()
        self.assertIsNotNone(again, self.service.status()["error"])
        self.assertEqual((self.service.status()["token"], again.url), (token, url))
        self.assertEqual(list_tools(again.port, token), 200)
        self.assertIn(token, self.service.client_configs()["claude_code"])

    def test_new_token_replaces_the_saved_one_and_the_running_server_refuses_the_old(self):
        server = self.service.start()
        old = self.service.status()["token"]
        self.assertEqual(bpy.ops.scenario.mcp_new_token(), {"FINISHED"})
        new = self.service.status()["token"]
        self.assertNotEqual(new, old)
        self.assertEqual(list_tools(server.port, old), 401)
        self.assertEqual(list_tools(server.port, new), 200)
        self.assertEqual(self.restart_session().token, new)

    def test_a_busy_port_is_reported_and_no_other_port_is_taken(self):
        with socket.socket() as holder:
            holder.bind(("127.0.0.1", self.prefs.mcp_port))
            holder.listen()
            self.assertIsNone(self.service.start())
            status = self.service.status()
        self.assertFalse(status["running"])
        self.assertIn(f"Port {self.prefs.mcp_port}", status["error"])
        self.assertIn("MCP Port", status["error"])
        # The token was still saved, so a later start keeps the same setup valid.
        with open(self.path, encoding="ascii") as handle:
            saved = handle.read().strip()
        server = self.service.start()
        self.assertIsNotNone(server, self.service.status()["error"])
        self.assertEqual(server.token, saved)

    def test_a_linked_token_file_is_refused_rather_than_followed(self):
        if os.name != "posix":
            self.skipTest("symbolic links need POSIX permissions here")
        target = self.path + ".target"
        with open(target, "w", encoding="ascii") as handle:
            handle.write("x" * 32)
        self.addCleanup(os.replace, target, target + ".done")
        os.symlink(target, self.path)
        self.addCleanup(os.replace, self.path, self.path + ".link-done")
        self.assertIsNone(self.service.start())
        self.assertIn("not a link", self.service.status()["error"])
