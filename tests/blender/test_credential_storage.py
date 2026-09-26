# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Installed runtime storage follows the selected credentials without network work."""

import os
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import bpy
from helpers import online_access, submodule, temp_credentials


class CredentialStorageTests(unittest.TestCase):
    def setUp(self):
        self.runtime = submodule("blender.runtime")
        self.storage = submodule("core.jobs.store")
        self.enterContext(patch.object(self.runtime, "state", self.runtime.RuntimeState()))
        self.enterContext(online_access(False))
        self.prefs = self.enterContext(temp_credentials())
        source = self.prefs.credential_source
        self.addCleanup(setattr, self.prefs, "credential_source", source)
        self.prefs.credential_source = "PREFERENCES"
        directory = self.enterContext(
            tempfile.TemporaryDirectory(dir=bpy.utils.resource_path("USER"))
        )
        self.root = Path(directory).resolve()
        self.enterContext(
            patch.object(self.runtime, "paths", return_value=SimpleNamespace(state_dir=self.root))
        )
        self.addCleanup(self.runtime.state.reset)

    def seed(self, store):
        module = self.storage
        record = store.create(
            module.JobIntent(
                "request",
                store.scope,
                module.JobOrigin("file", "scene", "revision"),
                "model",
                "model",
                "a" * 64,
                "b" * 64,
                "0.1234567890123456789",
            )
        )
        return store.transition(
            "request", expected_revision=record.revision, state=module.JobState.SUBMITTING
        )

    def test_shared_store_reopens_after_runtime_reset_without_starting_workers(self):
        first = self.runtime.ensure_job_store()
        record = self.seed(first)
        self.assertEqual(self.runtime.state.catalog.scope, first.scope)
        self.assertIsNone(first.scope.project_id)
        self.assertIsNone(self.runtime.state.manager)
        self.runtime.state.reset()
        reopened = self.runtime.ensure_job_store()
        self.assertEqual(reopened.get("request"), record)
        self.assertIsNone(self.runtime.state.manager)

    def test_credential_change_retires_catalog_and_isolates_durable_records(self):
        first = self.runtime.ensure_job_store()
        record = self.seed(first)
        catalog = self.runtime.state.catalog
        original = self.prefs.api_secret
        self.prefs.api_secret = "other-fixture-secret"
        self.assertTrue(catalog.closed)
        self.assertIsNone(self.runtime.state.job_store)
        other = self.runtime.ensure_job_store()
        self.assertIsNone(other.get("request"))
        self.prefs.api_secret = original
        self.assertEqual(self.runtime.ensure_job_store().get("request"), record)

    def test_environment_selection_uses_only_the_complete_selected_pair(self):
        saved = self.runtime.ensure_job_store().scope
        self.prefs.credential_source = "ENVIRONMENT"
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaisesRegex(submodule("core.api.errors").ScenarioError, "Complete"):
                self.runtime.ensure_job_store()
        self.assertIsNone(self.runtime.state.job_store)
        with patch.dict(
            os.environ,
            {"SCENARIO_API_KEY": self.prefs.api_key, "SCENARIO_API_SECRET": self.prefs.api_secret},
        ):
            self.assertEqual(self.runtime.ensure_job_store().scope, saved)

    def test_missing_key_blocks_new_context_and_preserves_saved_jobs(self):
        first = self.runtime.ensure_job_store()
        record = self.seed(first)
        self.runtime.state.reset()
        (self.root / "shared-jobs/scope.key").unlink()
        with self.assertRaisesRegex(
            submodule("core.api.errors").ScenarioError, "scope key is missing"
        ):
            self.runtime.ensure_catalog()
        self.assertIsNone(self.runtime.state.catalog)
        self.assertIsNone(self.runtime.state.job_store)
        self.assertEqual(first.get("request"), record)

    def test_invalid_credentials_do_not_create_files(self):
        self.prefs.api_key = "invalid:key"
        with self.assertRaises(submodule("core.api.errors").ScenarioError):
            self.runtime.ensure_catalog()
        self.assertEqual(list(self.root.iterdir()), [])
