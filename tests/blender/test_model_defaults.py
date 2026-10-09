# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Installed runtime lane defaults follow the selected credentials and project, offline."""

import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import bpy
from helpers import online_access, submodule, temp_credentials


class ModelDefaultsRuntimeTests(unittest.TestCase):
    def setUp(self):
        self.runtime = submodule("blender.runtime")
        self.store = submodule("core.jobs.store")
        self.owners = submodule("core.jobs.model_defaults")
        self.errors = submodule("core.api.errors")
        self.enterContext(patch.object(self.runtime, "state", self.runtime.RuntimeState()))
        self.enterContext(online_access(False))
        self.prefs = self.enterContext(temp_credentials())
        for name in ("credential_source", "project_id"):
            self.addCleanup(setattr, self.prefs, name, getattr(self.prefs, name))
        self.prefs.credential_source = "PREFERENCES"
        self.prefs.project_id = ""
        directory = self.enterContext(
            tempfile.TemporaryDirectory(dir=bpy.utils.resource_path("USER"))
        )
        self.root = Path(directory).resolve()
        self.enterContext(
            patch.object(self.runtime, "paths", return_value=SimpleNamespace(state_dir=self.root))
        )
        self.addCleanup(self.runtime.state.reset)

    def stack(self, lane="image", model_id="model_lora"):
        module = self.store
        return module.TrainedModelDefault(
            lane, "stack", "model_base", (module.TrainedModelPick(model_id, 0.5),)
        )

    def test_owner_uses_the_selected_store_scope_without_network_or_workers(self):
        owner = self.runtime.ensure_model_defaults()
        state = self.runtime.state
        self.assertIs(self.runtime.ensure_model_defaults(), owner)
        self.assertEqual(owner.scope, state.job_store.scope)
        self.assertIsNone(owner.scope.project_id)
        self.assertIsNone(owner.scope.team_id)
        self.assertEqual(owner.lane("image"), self.store.TrainedDefaultState("image", 0))
        self.assertEqual(owner.saved(), ())
        # Defaults need no connection check, job session, manager or discovery.
        self.assertIsNone(state.job_session)
        self.assertIsNone(state.manager)
        self.assertIsNone(state.connection_request)
        self.assertFalse(state.catalog_loaded)

    def test_project_change_retires_the_owner_and_isolates_defaults(self):
        first = self.runtime.ensure_model_defaults()
        saved = first.save(self.stack(), expected_revision=0)
        self.prefs.project_id = "fixture-project"
        self.assertFalse(first.active)
        self.assertIsNone(self.runtime.state.model_defaults)
        for call in (
            lambda: first.lane("image"),
            lambda: first.save(self.stack(model_id="model_late"), expected_revision=1),
            lambda: first.clear("image", expected_revision=1),
        ):
            with self.assertRaises(self.owners.DefaultsRetired):
                call()
        project = self.runtime.ensure_model_defaults()
        self.assertEqual(project.scope.project_id, "fixture-project")
        self.assertNotEqual(project.context_id, first.context_id)
        self.assertEqual(project.lane("image"), self.store.TrainedDefaultState("image", 0))
        own = project.save(self.stack(model_id="model_project"), expected_revision=0)
        self.prefs.project_id = ""
        self.assertFalse(project.active)
        key_scope = self.runtime.ensure_model_defaults()
        self.assertEqual(key_scope.lane("image"), saved)
        self.prefs.project_id = "  fixture-project  "
        self.assertEqual(self.runtime.ensure_model_defaults().lane("image"), own)

    def test_equivalent_project_edit_keeps_the_owner(self):
        owner = self.runtime.ensure_model_defaults()
        self.prefs.project_id = "   "
        self.assertTrue(owner.active)
        self.assertIs(self.runtime.ensure_model_defaults(), owner)

    def test_credential_change_retires_the_owner_and_isolates_defaults(self):
        first = self.runtime.ensure_model_defaults()
        saved = first.save(self.stack(), expected_revision=0)
        original = self.prefs.api_secret
        self.prefs.api_secret = "other-fixture-secret"
        self.assertFalse(first.active)
        other = self.runtime.ensure_model_defaults()
        self.assertNotEqual(other.scope.account_id, first.scope.account_id)
        self.assertEqual(other.saved(), ())
        self.prefs.api_secret = original
        self.assertEqual(self.runtime.ensure_model_defaults().lane("image"), saved)

    def test_writes_require_the_context_that_showed_the_lane(self):
        owner = self.runtime.ensure_model_defaults()
        context = owner.context_id
        saved = self.runtime.save_model_default(context, self.stack(), expected_revision=0)
        self.prefs.project_id = "fixture-project"
        self.prefs.project_id = ""
        current = self.runtime.ensure_model_defaults()
        self.assertNotEqual(current.context_id, context)
        with self.assertRaisesRegex(self.errors.ScenarioError, "review the default again"):
            self.runtime.save_model_default(
                context, self.stack(model_id="model_stale"), expected_revision=1
            )
        with self.assertRaisesRegex(self.errors.ScenarioError, "review the default again"):
            self.runtime.clear_model_default(context, "image", expected_revision=1)
        self.assertEqual(current.lane("image"), saved)
        cleared = self.runtime.clear_model_default(current.context_id, "image", expected_revision=1)
        self.assertEqual(cleared, self.store.TrainedDefaultState("image", 2))
        with self.assertRaises(self.store.StoreConflict):
            self.runtime.save_model_default(current.context_id, self.stack(), expected_revision=1)

    def test_runtime_reset_retires_the_owner_and_reopens_saved_defaults(self):
        owner = self.runtime.ensure_model_defaults()
        saved = owner.save(self.stack("3d"), expected_revision=0)
        self.runtime.state.reset()
        self.assertFalse(owner.active)
        reopened = self.runtime.ensure_model_defaults()
        self.assertIsNot(reopened, owner)
        self.assertEqual(reopened.saved(), (saved,))

    def test_missing_credentials_open_no_defaults(self):
        self.prefs.api_key = ""
        with self.assertRaisesRegex(self.errors.ScenarioError, "Complete"):
            self.runtime.ensure_model_defaults()
        self.assertIsNone(self.runtime.state.model_defaults)
        self.assertEqual(list(self.root.iterdir()), [])
