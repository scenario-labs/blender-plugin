# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
import unittest

from helpers import submodule


class McpPanelTests(unittest.TestCase):
    def test_client_configs_carry_the_url_and_no_credential(self):
        service = submodule("blender.mcp_service")
        configs = service.client_configs()
        for key in ("claude_code", "cursor", "claude_desktop", "codex", "curl"):
            self.assertIn("/mcp", configs[key], key)
            for credential in ("Authorization", "Bearer", "--token", "TOKEN"):
                self.assertNotIn(credential, configs[key], key)
        self.assertIn("stdio_shim.py", configs["claude_desktop"])
