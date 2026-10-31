# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""A pending browser sign-in follows Allow Online Access.

The listener and the browser are stood in for: no port is opened and nothing
contacts the identity provider. Switching the preference off while the browser
is pending must cancel the attempt before any token exchange.
"""

import unittest
from unittest.mock import patch

import bpy
from helpers import online_access, submodule


class _PendingBrowser:
    """A sign-in attempt whose browser never answers; completes only once cancelled."""

    url = "https://idp.example.invalid/oauth/authorize?fixture"

    def __init__(self, oauth):
        self._oauth = oauth
        self.exchanged = False
        self.closed = False

    def complete(self, *, cancelled=None, timeout=None, opener=None):
        cancelled.wait(5)
        self.closed = True
        if cancelled.is_set():
            raise self._oauth.SignInError("Sign-in cancelled")
        self.exchanged = True
        return None

    def close(self):
        self.closed = True


class SignInTests(unittest.TestCase):
    def test_switching_online_access_off_cancels_the_pending_sign_in(self):
        sign_in = submodule("blender.sign_in")
        runtime = submodule("blender.runtime")
        desktop = submodule("blender.desktop")
        oauth = submodule("core.api.oauth")
        app = oauth.OAuthApp(
            issuer="https://idp.example.invalid",
            client_id="fixture-client",
            service="https://service.example.invalid/v1",
        )
        browser = _PendingBrowser(oauth)
        message = runtime.state.last_message
        try:
            with (
                patch.object(oauth, "selected_app", return_value=app),
                patch.object(oauth, "SignInAttempt", return_value=browser),
                patch.object(desktop, "open_url") as opened,
            ):
                with online_access(True):
                    sign_in.start()
                    self.assertTrue(sign_in.pending())
                    opened.assert_called_once_with(browser.url)
                    self.assertEqual(sign_in._poll(), sign_in.POLL_INTERVAL)
                    self.assertTrue(sign_in.pending())
                # The runner's profile is offline again: the next tick drops the attempt.
                self.assertEqual(sign_in._poll(), sign_in.POLL_INTERVAL)
                sign_in.wait()
            self.assertFalse(sign_in.pending())
            self.assertFalse(browser.exchanged)
            self.assertTrue(browser.closed)
            self.assertEqual(
                runtime.state.last_message, "Allow Online Access was disabled during the sign-in"
            )
        finally:
            if bpy.app.timers.is_registered(sign_in._poll):
                bpy.app.timers.unregister(sign_in._poll)
            sign_in.cancel()
            sign_in.wait()
            runtime.state.last_message = message


if __name__ == "__main__":
    unittest.main()
