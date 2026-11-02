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


# Two teams with several projects each, and a team where the account has none.
TEAMS = {
    "teams": [
        {
            "id": "team_studio",
            "name": "Studio",
            "projects": [
                {"id": "proj_film", "name": "Film"},
                {"id": "proj_game", "name": "Game"},
            ],
        },
        {
            "id": "team_personal",
            "name": "Personal",
            "projects": [
                {"id": "proj_sketches", "name": "Sketches"},
                {"id": "proj_tests", "name": "Tests"},
            ],
        },
        {"id": "team_invited", "name": "Invited", "projects": []},
    ]
}


class _Session:
    """A signed-in account that holds no token and never refreshes."""

    def __init__(self, oauth, account):
        self.account = account
        self.ended = None
        self.app = oauth.OAuthApp(
            issuer="https://idp.example.invalid",
            client_id="fixture-client",
            service="https://service.example.invalid/v1",
        )

    def sign_out(self):
        pass


class _Adapter:
    """Stands in for the SDK adapter: answers GET /teams, contacts nothing."""

    def __init__(self, *args, **kwargs):
        self.online = kwargs["online"]

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def teams(self):
        assert self.online()
        return TEAMS


class DestinationTests(unittest.TestCase):
    """A browser account sends work only to the team and project it chose."""

    def setUp(self):
        self.sign_in = submodule("blender.sign_in")
        self.runtime = submodule("blender.runtime")
        self.oauth = submodule("core.api.oauth")
        self.destinations = submodule("core.api.destinations")
        self.prefs = self.runtime.prefs()
        self.saved = {
            name: getattr(self.prefs, name)
            for name in (
                "credential_source",
                "project_id",
                "browser_project_id",
                "browser_project_label",
                "browser_project_account",
            )
        }
        self.session = _Session(self.oauth, "https://idp.example.invalid#user_a")
        self.patch = patch.object(self.runtime, "browser_session", side_effect=lambda: self.session)
        self.patch.start()
        self.prefs.credential_source = "BROWSER"
        self.prefs.browser_project_id = ""
        self.prefs.browser_project_account = ""
        self.runtime.state.browser_teams = self.destinations.teams_from(TEAMS)
        self.runtime.state.browser_teams_error = ""

    def tearDown(self):
        self.patch.stop()
        for name, value in self.saved.items():
            setattr(self.prefs, name, value)
        self.runtime.state.browser_teams = None
        self.runtime.state.browser_teams_loading = False
        self.runtime.state.browser_teams_error = ""

    def test_nothing_runs_on_the_account_until_a_project_is_chosen(self):
        # The API-key override is not the browser account's destination.
        self.prefs.project_id = "proj_key_override"
        self.assertTrue(self.runtime.needs_browser_project())
        self.assertIsNone(self.runtime.project_id())
        with self.assertRaises(self.sign_in.ScenarioError) as raised:
            self.runtime.ensure_catalog()
        self.assertEqual(raised.exception.reason, self.runtime.CHOOSE_PROJECT)

    def test_the_dialog_switches_between_projects_of_different_teams(self):
        result = bpy.ops.scenario.choose_project(team="team_studio", project="proj_game")
        self.assertEqual(result, {"FINISHED"})
        self.assertEqual(self.runtime.project_id(), "proj_game")
        self.assertEqual(self.runtime.browser_project()[1], "Studio / Game")
        self.assertFalse(self.runtime.needs_browser_project())

        result = bpy.ops.scenario.choose_project(team="team_personal", project="proj_tests")
        self.assertEqual(result, {"FINISHED"})
        self.assertEqual(self.runtime.project_id(), "proj_tests")
        self.assertEqual(self.runtime.browser_project()[1], "Personal / Tests")
        # The key override field is untouched by the account's choice.
        self.assertEqual(self.prefs.project_id, self.saved["project_id"])

    def test_a_team_without_a_project_cannot_be_chosen(self):
        with self.assertRaises(RuntimeError):
            bpy.ops.scenario.choose_project(team="team_invited", project="NONE")
        self.assertIsNone(self.runtime.project_id())
        with self.assertRaises(self.sign_in.ScenarioError):
            self.sign_in.choose("proj_not_listed")
        self.assertIsNone(self.runtime.project_id())

    def test_another_account_does_not_inherit_the_choice(self):
        self.sign_in.choose("proj_film")
        self.assertEqual(self.runtime.project_id(), "proj_film")
        self.session = _Session(self.oauth, "https://idp.example.invalid#user_b")
        self.assertIsNone(self.runtime.project_id())
        self.assertTrue(self.runtime.needs_browser_project())

    def test_sign_out_forgets_the_choice(self):
        self.sign_in.choose("proj_sketches")
        with patch.object(self.runtime, "set_browser_session"):
            self.sign_in.sign_out()
        self.assertEqual(self.prefs.browser_project_id, "")
        self.assertEqual(self.prefs.browser_project_label, "")
        self.assertIsNone(self.runtime.project_id())

    def test_the_worker_reads_every_team_and_project(self):
        self.runtime.state.browser_teams = None
        try:
            with (
                online_access(True),
                patch.object(self.sign_in, "SDKAdapter", _Adapter),
            ):
                self.sign_in.load_teams()
                self.assertTrue(self.runtime.state.browser_teams_loading)
                self.sign_in.wait_teams()
        finally:
            if bpy.app.timers.is_registered(self.sign_in._poll_teams):
                bpy.app.timers.unregister(self.sign_in._poll_teams)
        teams = self.runtime.state.browser_teams
        self.assertEqual(self.runtime.state.browser_teams_error, "")
        self.assertFalse(self.runtime.state.browser_teams_loading)
        self.assertEqual(
            [(t.name, [p.name for p in t.projects]) for t in teams],
            [("Studio", ["Film", "Game"]), ("Personal", ["Sketches", "Tests"]), ("Invited", [])],
        )

    def test_offline_reads_nothing(self):
        self.runtime.state.browser_teams = None
        with patch.object(self.sign_in, "SDKAdapter") as adapter:
            self.sign_in.load_teams()
        adapter.assert_not_called()
        self.assertIsNone(self.runtime.state.browser_teams)
        self.assertIn("Allow Online Access", self.runtime.state.browser_teams_error)
