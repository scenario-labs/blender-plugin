# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Credential source selection through the installed Blender preferences."""

import os
import unittest
from unittest.mock import patch

from helpers import submodule


class CredentialTests(unittest.TestCase):
    def test_selected_source_is_atomic_and_missing_preferences_fail_closed(self):
        runtime = submodule("blender.runtime")
        prefs = runtime.prefs()
        saved = prefs.credential_source, prefs.api_key, prefs.api_secret
        label = runtime.state.account_label
        try:
            prefs.api_key, prefs.api_secret = "saved-key", "saved-secret"
            env = {"SCENARIO_API_KEY": "launch-key", "SCENARIO_API_SECRET": "launch-secret"}
            with patch.dict(os.environ, env, clear=True):
                prefs.credential_source = "PREFERENCES"
                self.assertEqual(runtime.credentials().key, "saved-key")
                runtime.state.account_label = "Previously verified account"
                prefs.credential_source = "ENVIRONMENT"
                self.assertEqual(runtime.state.account_label, "")
                self.assertEqual(runtime.credentials().key, "launch-key")
                self.assertEqual(runtime.credentials().secret, "launch-secret")
                del os.environ["SCENARIO_API_SECRET"]
                self.assertFalse(runtime.credentials().valid)
                with self.assertRaisesRegex(Exception, "selected credential source"):
                    runtime.make_client()
                with patch.object(runtime, "prefs", return_value=None):
                    self.assertFalse(runtime.credentials().valid)
                prefs.credential_source = "PREFERENCES"
                self.assertTrue(runtime.credentials().valid)
        finally:
            prefs.credential_source, prefs.api_key, prefs.api_secret = saved
            runtime.state.account_label = label

    def test_defaults_and_password_fields_are_registered(self):
        prefs = submodule("blender.runtime").prefs()
        properties = prefs.bl_rna.properties
        self.assertEqual(properties["credential_source"].default, "PREFERENCES")
        for field in ("api_key", "api_secret"):
            self.assertEqual(properties[field].subtype, "PASSWORD")
