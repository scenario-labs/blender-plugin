# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Installed update controls use native operators and never bypass offline mode."""

import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

import bpy
from helpers import submodule


class UpdateTests(unittest.TestCase):
    def test_supported_native_operator_contracts(self):
        setup = bpy.ops.preferences.extension_repo_add.get_rna_type().properties
        for name in ("name", "remote_url", "use_sync_on_startup"):
            self.assertIn(name, setup)
        self.assertIn("repo_index", bpy.ops.extensions.repo_sync.get_rna_type().properties)
        self.assertIn("section", bpy.ops.screen.userpref_show.get_rna_type().properties)

    def test_offline_controls_reject_setup_and_sync(self):
        self.assertFalse(bpy.app.online_access)
        self.assertFalse(bpy.ops.scenario.setup_updates.poll())
        self.assertFalse(bpy.ops.scenario.check_updates.poll())

    def test_existing_repository_is_reused_and_disabled_repository_can_be_enabled(self):
        updates = submodule("blender.updates")
        repository = SimpleNamespace(
            use_remote_url=True, remote_url=updates.REPOSITORY_URL, enabled=False
        )
        context = SimpleNamespace(
            preferences=SimpleNamespace(extensions=SimpleNamespace(repos=[repository]))
        )
        native_setup = Mock(side_effect=AssertionError("Duplicate repository created"))
        fake_bpy = SimpleNamespace(
            app=SimpleNamespace(online_access=True),
            ops=SimpleNamespace(preferences=SimpleNamespace(extension_repo_add=native_setup)),
        )
        with patch.object(updates, "bpy", fake_bpy):
            operator = SimpleNamespace(report=Mock())
            self.assertEqual(
                updates.SCENARIO_OT_setup_updates.execute(operator, context), {"FINISHED"}
            )
            self.assertEqual(
                updates.SCENARIO_OT_setup_updates.execute(operator, context), {"FINISHED"}
            )
        self.assertTrue(repository.enabled)
        native_setup.assert_not_called()

    def test_check_targets_only_official_repository_without_installing(self):
        updates = submodule("blender.updates")
        official = SimpleNamespace(
            use_remote_url=True, remote_url=updates.REPOSITORY_URL, enabled=True
        )
        other = SimpleNamespace(use_remote_url=True, remote_url="https://example.invalid/")
        context = SimpleNamespace(
            preferences=SimpleNamespace(extensions=SimpleNamespace(repos=[other, official]))
        )
        sync = Mock(return_value={"FINISHED"})
        fake_bpy = SimpleNamespace(
            app=SimpleNamespace(online_access=True, background=True),
            ops=SimpleNamespace(extensions=SimpleNamespace(repo_sync=sync)),
        )
        operator = SimpleNamespace(poll=updates.SCENARIO_OT_check_updates.poll)
        with patch.object(updates, "bpy", fake_bpy):
            self.assertEqual(
                updates.SCENARIO_OT_check_updates.execute(operator, context), {"FINISHED"}
            )
            sync.assert_called_once_with("EXEC_DEFAULT", repo_index=1)
            fake_bpy.app.online_access = False
            self.assertEqual(
                updates.SCENARIO_OT_check_updates.execute(operator, context), {"CANCELLED"}
            )
            self.assertEqual(sync.call_count, 1)
