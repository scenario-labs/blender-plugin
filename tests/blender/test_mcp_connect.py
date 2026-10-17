# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Connect writes the scenario-blender entry, with the saved token, into a temporary home."""

import json
import os
import tempfile
import tomllib
import unittest
from pathlib import Path
from unittest import mock

import bpy
from helpers import submodule


class McpConnectTests(unittest.TestCase):
    def setUp(self):
        self.runtime = submodule("blender.runtime")
        self.service = submodule("blender.mcp_service")
        self.service.stop()
        self.addCleanup(self.service.stop)
        self.home = Path(self.enterContext(tempfile.TemporaryDirectory(prefix="scenario-home-")))
        environ = {
            key: value
            for key, value in os.environ.items()
            if key not in {"CODEX_HOME", "APPDATA", "XDG_CONFIG_HOME"}
        }
        environ.update(HOME=str(self.home), USERPROFILE=str(self.home))
        self.enterContext(mock.patch.dict(os.environ, environ, clear=True))
        prefs = self.runtime.prefs()
        self.addCleanup(setattr, prefs, "mcp_port", prefs.mcp_port)
        prefs.mcp_port = 9911
        self.addCleanup(setattr, self.runtime.state, "mcp_token", self.runtime.state.mcp_token)
        self.runtime.state.mcp_token = ""
        self.addCleanup(self.service.connect_report.clear)

    def test_connect_writes_claude_code_and_codex_entries_with_the_saved_token(self):
        claude = self.home / ".claude.json"
        claude.write_text(json.dumps({"mcpServers": {"other": {"command": "keep"}}}))
        (self.home / ".codex").mkdir()
        found = {client.key for client in self.service.connect_clients() if client.detected}
        self.assertEqual(found, {"claude_code", "codex"})
        self.assertEqual(bpy.ops.scenario.mcp_connect(client="claude_code"), {"FINISHED"})
        token = self.runtime.state.mcp_token
        saved = Path(self.service.token_dir(), "mcp-token").read_text().strip()
        self.assertEqual(token, saved)  # the entry carries the token that survives restarts
        servers = json.loads(claude.read_text())["mcpServers"]
        self.assertEqual(servers["other"], {"command": "keep"})
        self.assertEqual(
            servers["scenario-blender"],
            {
                "type": "http",
                "url": "http://127.0.0.1:9911/mcp",
                "headers": {"Authorization": f"Bearer {token}"},
            },
        )
        report = list(self.service.connect_report)
        self.assertTrue(report[0].startswith("Claude Code: wrote scenario-blender to "))
        self.assertTrue(any(line.startswith("Previous file kept as ") for line in report))
        self.assertFalse(any(token in line for line in report))
        self.assertEqual(bpy.ops.scenario.mcp_connect(client="codex"), {"FINISHED"})
        codex = tomllib.loads((self.home / ".codex" / "config.toml").read_text())
        self.assertEqual(
            codex["mcp_servers"]["scenario-blender"]["http_headers"],
            {"Authorization": f"Bearer {token}"},
        )

    def test_a_client_that_was_never_run_is_not_configured(self):
        with self.assertRaises(RuntimeError):  # the operator reports an error
            bpy.ops.scenario.mcp_connect(client="cursor")
        self.assertEqual(list(self.home.iterdir()), [])
        self.assertIn("Cursor: not changed", self.service.connect_report[0])

    def test_a_file_that_cannot_be_parsed_is_left_alone(self):
        claude = self.home / ".claude.json"
        claude.write_text("{ not json")
        with self.assertRaises(RuntimeError):
            bpy.ops.scenario.mcp_connect(client="claude_code")
        self.assertEqual(claude.read_text(), "{ not json")
        self.assertEqual(sorted(p.name for p in self.home.iterdir()), [".claude.json"])
