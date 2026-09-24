# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Installed MCP Python gate and private capture-file lifetime."""

import base64
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import bpy
from helpers import submodule


class McpSecurityTests(unittest.TestCase):
    def setUp(self):
        self.tools = submodule("mcp.tools_blender")

    def test_execute_python_fails_closed_without_preferences(self):
        prefs = submodule("prefs")
        with patch.object(prefs, "get_prefs", return_value=None):
            with self.assertRaisesRegex(PermissionError, "not available"):
                self.tools.execute_python({"code": "raise AssertionError('must not execute')"})

    def test_execute_python_requires_enabled_preference(self):
        prefs = submodule("prefs").get_prefs()
        original = prefs.mcp_allow_python
        try:
            prefs.mcp_allow_python = False
            with self.assertRaises(PermissionError):
                self.tools.execute_python({"code": "result['value'] = 1"})
            prefs.mcp_allow_python = True
            result = self.tools.execute_python({"code": "result['value'] = 1"})
            self.assertEqual(result["result"]["value"], 1)
        finally:
            prefs.mcp_allow_python = original

    def test_private_png_lifetime_and_permissions(self):
        with self.tools._private_png("test.png") as path:
            directory = Path(path).parent
            if os.name == "posix":
                self.assertEqual(directory.stat().st_mode & 0o777, 0o700)
            Path(path).write_bytes(b"image")
        self.assertFalse(directory.exists())

    def test_render_capture_removes_directory_on_success_and_errors(self):
        capture = submodule("blender.capture")
        for failure in (None, "capture", "read"):
            with self.subTest(failure=failure):
                created = []

                def write_capture(context, path, *, created=created, failure=failure, **kwargs):
                    created.append(Path(path).parent)
                    Path(path).write_bytes(b"synthetic capture")
                    if failure == "capture":
                        raise RuntimeError("capture failure")

                with patch.object(capture, "capture_still", side_effect=write_capture):
                    if failure == "read":
                        with patch.object(
                            self.tools, "_png_content", side_effect=OSError("read failure")
                        ):
                            with self.assertRaises(OSError):
                                self.tools.render_still({})
                    elif failure:
                        with self.assertRaises(RuntimeError):
                            self.tools.render_still({})
                    else:
                        result = self.tools.render_still({})
                        self.assertEqual(base64.b64decode(result["_image"]), b"synthetic capture")
                self.assertEqual(len(created), 1)
                self.assertFalse(created[0].exists())

    def test_render_still_and_screenshot_leave_no_temp_directory_in_background(self):
        self.assertTrue(bpy.app.background)
        before = set(Path(tempfile.gettempdir()).glob("scenario-mcp-*"))
        with self.assertRaises(RuntimeError):
            self.tools.render_still({"source": "VIEWPORT"})
        with self.assertRaises(RuntimeError):
            self.tools.screenshot_viewport({})
        self.assertEqual(set(Path(tempfile.gettempdir()).glob("scenario-mcp-*")), before)
