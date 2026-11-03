# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""A pending browser sign-in follows Allow Online Access.

The listener and the browser are stood in for: no port is opened and nothing
contacts the identity provider. Switching the preference off while the browser
is pending must cancel the attempt before any token exchange.
"""

import os
import tempfile
import time
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


# One usable project, behind a team where the account has none.
ONE_PROJECT = {
    "teams": [
        {"id": "team_invited", "name": "Invited", "projects": []},
        {"id": "team_solo", "name": "Solo", "projects": [{"id": "proj_only", "name": "Only"}]},
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

    answer = TEAMS

    def teams(self):
        assert self.online()
        return self.answer


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
        self.runtime.state.browser_project_gone = ""

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

    def _sign_in_reads(self, answer, *, choose=True):
        self.runtime.state.browser_teams = None
        try:
            with (
                online_access(True),
                patch.object(self.sign_in, "SDKAdapter", _Adapter),
                patch.object(_Adapter, "answer", answer),
            ):
                self.sign_in.load_teams(choose=choose)
                self.sign_in.wait_teams()
        finally:
            if bpy.app.timers.is_registered(self.sign_in._poll_teams):
                bpy.app.timers.unregister(self.sign_in._poll_teams)

    def test_an_account_with_one_project_uses_it_without_asking(self):
        with patch.object(self.sign_in, "open_chooser") as chooser:
            self._sign_in_reads(ONE_PROJECT)
        chooser.assert_not_called()
        self.assertEqual(self.runtime.project_id(), "proj_only")
        self.assertEqual(self.runtime.browser_project()[1], "Solo / Only")
        self.assertFalse(self.runtime.needs_browser_project())

    def test_an_account_with_several_projects_is_asked(self):
        with patch.object(self.sign_in, "open_chooser") as chooser:
            self._sign_in_reads(TEAMS)
        chooser.assert_called_once_with()
        self.assertIsNone(self.runtime.project_id())
        self.assertTrue(self.runtime.needs_browser_project())

    def test_a_deleted_project_is_forgotten_when_the_list_arrives(self):
        self.sign_in.choose("proj_game")
        without_game = {
            "teams": [
                {**team, "projects": [p for p in team["projects"] if p["id"] != "proj_game"]}
                for team in TEAMS["teams"]
            ]
        }
        with patch.object(self.sign_in, "open_chooser") as chooser:
            self._sign_in_reads(without_game, choose=False)
        chooser.assert_not_called()
        self.assertIsNone(self.runtime.project_id())
        self.assertTrue(self.runtime.needs_browser_project())
        self.assertEqual(self.prefs.browser_project_label, "")
        self.assertIn("Studio / Game is no longer available", self.runtime.state.last_message)
        # The sidebar keeps saying why until another project is chosen.
        self.assertEqual(self.runtime.state.browser_project_gone, "Studio / Game")
        self.sign_in.use("proj_film")
        self.assertEqual(self.runtime.state.browser_project_gone, "")

    def test_a_deleted_project_falls_back_to_the_only_one_left(self):
        self.sign_in.choose("proj_film")
        with patch.object(self.sign_in, "open_chooser") as chooser:
            self._sign_in_reads(ONE_PROJECT, choose=False)
        chooser.assert_not_called()
        self.assertEqual(self.runtime.project_id(), "proj_only")

    def test_a_listed_choice_is_kept(self):
        self.sign_in.choose("proj_tests")
        with patch.object(self.sign_in, "open_chooser") as chooser:
            self._sign_in_reads(TEAMS, choose=False)
        chooser.assert_not_called()
        self.assertEqual(self.runtime.project_id(), "proj_tests")

    def test_offline_reads_nothing(self):
        self.runtime.state.browser_teams = None
        with patch.object(self.sign_in, "SDKAdapter") as adapter:
            self.sign_in.load_teams()
        adapter.assert_not_called()
        self.assertIsNone(self.runtime.state.browser_teams)
        self.assertIn("Allow Online Access", self.runtime.state.browser_teams_error)


class _AnsweredBrowser:
    """A sign-in attempt whose browser answers at once with the account's tokens."""

    url = "https://idp.example.invalid/oauth/authorize?fixture"

    def __init__(self, tokens):
        self.tokens = tokens

    def complete(self, *, cancelled=None, timeout=None, opener=None):
        return self.tokens

    def close(self):
        pass


class HeadlessSignInTests(unittest.TestCase):
    """Background Blender runs no timer: the operator applies the team list itself."""

    def setUp(self):
        self.sign_in = submodule("blender.sign_in")
        self.runtime = submodule("blender.runtime")
        self.desktop = submodule("blender.desktop")
        self.oauth = submodule("core.api.oauth")
        self.prefs = self.runtime.prefs()
        self.saved = {
            name: getattr(self.prefs, name)
            for name in (
                "credential_source",
                "browser_project_id",
                "browser_project_label",
                "browser_project_account",
            )
        }
        self.message = self.runtime.state.last_message
        self.session = (
            self.runtime.state.browser_session,
            self.runtime.state.browser_session_loaded,
        )
        self.directory = tempfile.TemporaryDirectory()
        self.app = self.oauth.OAuthApp(
            issuer="https://idp.example.invalid",
            client_id="fixture-client",
            service="https://service.example.invalid/v1",
        )
        tokens = self.oauth.TokenSet(
            issuer=self.app.issuer,
            client_id=self.app.client_id,
            service=self.app.service,
            subject="user_headless",
            access_token="fixture-access",
            refresh_token="fixture-refresh",
            expires_at=time.time() + 3600,
        )
        self.browser = _AnsweredBrowser(tokens)
        self.prefs.credential_source = "BROWSER"
        self.prefs.browser_project_id = ""
        self.prefs.browser_project_account = ""

    def tearDown(self):
        for timer in (self.sign_in._poll, self.sign_in._poll_teams):
            if bpy.app.timers.is_registered(timer):
                bpy.app.timers.unregister(timer)
        self.runtime.set_browser_session(None)
        self.runtime.state.browser_session, self.runtime.state.browser_session_loaded = self.session
        for name, value in self.saved.items():
            setattr(self.prefs, name, value)
        self.runtime.state.last_message = self.message
        self.directory.cleanup()

    def _sign_in(self, answer):
        path = os.path.join(self.directory.name, "sign-in.json")
        with (
            online_access(True),
            patch.object(self.oauth, "selected_app", return_value=self.app),
            patch.object(self.oauth, "SignInAttempt", return_value=self.browser),
            patch.object(self.desktop, "open_url"),
            patch.object(self.runtime, "browser_session_path", return_value=path),
            patch.object(self.sign_in, "SDKAdapter", _Adapter),
            patch.object(_Adapter, "answer", answer),
        ):
            result = bpy.ops.scenario.sign_in()
            self.assertEqual(result, {"FINISHED"})
            self.assertFalse(self.sign_in.pending())
            self.assertFalse(self.runtime.state.browser_teams_loading)

    def test_an_only_project_is_chosen_before_the_operator_returns(self):
        self._sign_in(ONE_PROJECT)
        self.assertEqual(self.runtime.project_id(), "proj_only")
        self.assertFalse(self.runtime.needs_browser_project())
        self.assertEqual(self.runtime.state.last_message, "Scenario work goes to Solo / Only")

    def test_several_projects_can_be_chosen_once_the_operator_returns(self):
        self._sign_in(TEAMS)
        self.assertTrue(self.runtime.needs_browser_project())
        self.assertEqual(len(self.runtime.state.browser_teams), 3)
        result = bpy.ops.scenario.choose_project(team="team_personal", project="proj_tests")
        self.assertEqual(result, {"FINISHED"})
        self.assertEqual(self.runtime.project_id(), "proj_tests")
