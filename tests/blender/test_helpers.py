# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Native regressions for nested test state and guaranteed cleanup."""

import unittest
from unittest.mock import patch

import bpy
from helpers import isolated_manager, online_access, submodule, temp_credentials


class HelperTests(unittest.TestCase):
    def test_credentials_restore_outer_values_after_an_exception(self):
        with temp_credentials("outer-key", "outer-secret") as prefs:
            with self.assertRaisesRegex(ValueError, "fixture failure"):
                with temp_credentials("inner-key", "inner-secret"):
                    raise ValueError("fixture failure")
            self.assertEqual((prefs.api_key, prefs.api_secret), ("outer-key", "outer-secret"))

    def test_online_access_restores_outer_preference_after_an_exception(self):
        with online_access(False):
            with self.assertRaisesRegex(ValueError, "fixture failure"):
                with online_access(True):
                    self.assertTrue(bpy.app.online_access)
                    raise ValueError("fixture failure")
            self.assertFalse(bpy.app.online_access)

    def test_ensure_manager_keeps_private_paths_and_restores_parent(self):
        runtime = submodule("blender.runtime")
        with isolated_manager() as outer:
            paths = outer.paths
            with isolated_manager() as inner:
                self.assertIs(runtime.ensure_manager(), inner)
                self.assertNotEqual(inner.paths.registry_file, paths.registry_file)
                inner.registry.save()
                inner_root = inner.paths.state_dir.parent
                self.assertTrue(inner.paths.registry_file.is_file())
            self.assertIs(runtime.state.manager, outer)
            self.assertEqual(runtime.paths(), paths)
            self.assertFalse(inner_root.exists())

    def test_manager_shuts_down_and_restores_state_after_an_exception(self):
        runtime = submodule("blender.runtime")
        previous = runtime.state.manager
        with self.assertRaisesRegex(ValueError, "fixture failure"):
            with isolated_manager() as manager:
                root = manager.paths.state_dir.parent
                manager._spawn(lambda: manager._stop.wait(10))
                raise ValueError("fixture failure")
        self.assertIs(runtime.state.manager, previous)
        self.assertFalse(manager.has_active())
        self.assertFalse(root.exists())

    def test_worker_timeout_preserves_the_original_test_failure(self):
        manager_class = submodule("core.jobs.manager").JobManager
        with patch.object(manager_class, "has_active", return_value=True):
            with self.assertRaisesRegex(AssertionError, "original test failure") as failure:
                with isolated_manager():
                    raise AssertionError("original test failure")
        self.assertIn("Test job workers did not stop", failure.exception.__notes__[0])

    def test_worker_timeout_still_fails_a_successful_test(self):
        manager_class = submodule("core.jobs.manager").JobManager
        with patch.object(manager_class, "has_active", return_value=True):
            with self.assertRaisesRegex(RuntimeError, "Test job workers did not stop"):
                with isolated_manager():
                    pass
