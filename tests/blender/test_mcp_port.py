# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""The local MCP server keeps the configured port, and a busy port is reported."""

import socket
import unittest

from helpers import online_access, submodule


def free_port():
    with socket.socket() as reservation:
        reservation.bind(("127.0.0.1", 0))
        return reservation.getsockname()[1]


class McpPortTests(unittest.TestCase):
    def setUp(self):
        self.service = submodule("blender.mcp_service")
        self.service.stop()
        self.addCleanup(self.service.stop)
        self.prefs = submodule("blender.runtime").prefs()
        self.addCleanup(setattr, self.prefs, "mcp_port", self.prefs.mcp_port)
        self.prefs.mcp_port = free_port()
        self.enterContext(online_access(True))

    def test_copied_setups_name_the_configured_port_while_stopped(self):
        self.prefs.mcp_port = 9912
        configs = self.service.client_configs()
        for key in ("claude_code", "cursor", "claude_desktop", "codex", "curl"):
            self.assertIn("http://127.0.0.1:9912/mcp", configs[key], key)
            self.assertNotIn(":9876/", configs[key], key)

    def test_a_busy_port_is_reported_and_no_other_port_is_taken(self):
        with socket.socket() as holder:
            holder.bind(("127.0.0.1", self.prefs.mcp_port))
            holder.listen()
            self.assertIsNone(self.service.start())
            status = self.service.status()
        self.assertFalse(status["running"])
        self.assertIn(f"Port {self.prefs.mcp_port}", status["error"])
        self.assertIn("MCP Port", status["error"])
        server = self.service.start()
        self.assertIsNotNone(server, self.service.status()["error"])
        self.assertEqual(server.url, f"http://127.0.0.1:{self.prefs.mcp_port}/mcp")
