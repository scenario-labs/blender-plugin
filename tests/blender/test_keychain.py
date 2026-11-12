# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""The OS credential store from Blender's own Python, on CI runners only.

Windows Credential Manager is reached through ctypes, so its record layout is
only proven by a real call from the Python Blender bundles. Hosted runners are
disposable machines; on a developer's computer this test stays skipped and
never touches the personal keychain.
"""

import os
import secrets
import unittest

from helpers import submodule

TOKEN = "rt_Fixture.Token-123~/+="


@unittest.skipUnless(
    os.environ.get("GITHUB_ACTIONS") == "true", "touches the computer's credential store"
)
class KeychainTests(unittest.TestCase):
    def test_this_runners_store_round_trip(self):
        keychain = submodule("core.keychain")
        store = keychain.system_store({})
        if store is None:
            self.skipTest("no supported credential store on this runner")
        store.service = "Scenario for Blender tests"
        slot = secrets.token_hex(16)
        try:
            self.assertIsNone(store.read(slot))
            store.write(slot, TOKEN)
            self.assertEqual(store.read(slot), TOKEN)
            store.write(slot, TOKEN + "2")
            self.assertEqual(store.read(slot), TOKEN + "2")
        finally:
            store.delete(slot)
        self.assertIsNone(store.read(slot))
