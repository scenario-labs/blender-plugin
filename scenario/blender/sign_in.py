# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Browser sign-in: start the system browser here, wait on a worker, apply the result here.

The callback port is opened and the browser started on Blender's main thread,
through the credential-free opener. A worker waits for the browser and swaps
the code for tokens; a timer applies the outcome on the main thread, where the
runtime's account, catalog and job context change.

A signed-in account has no implicit destination. Right after the sign-in a
worker reads the account's teams and projects and the team and project dialog
opens; the same dialog switches the destination later.
"""

import logging
import threading

import bpy

from ..core.api import destinations, oauth
from ..core.api.errors import ScenarioError
from ..core.api.sdk_adapter import AdapterError, SDKAdapter
from ..core.api.sdk_adapter import Credentials as SDKCredentials
from ..core.jobs import playback
from . import desktop, runtime

log = logging.getLogger("scenario")
POLL_INTERVAL = 0.25
NO_PROJECT = "NONE"
_pending = None  # The one sign-in in progress, main thread only.
_reported_end = None  # The session whose end the pump already announced.
_listing = None  # The one team and project read in progress, main thread only.
# Blender keeps only references to dynamic enum strings: hold the latest items.
_enum_items = {"team": [], "project": []}


class _Attempt:
    def __init__(self, app, attempt, path):
        self.app = app
        self.attempt = attempt
        self.path = path
        self.cancelled = threading.Event()
        self.reason = ""  # Why the attempt was cancelled, when it was.
        self.tokens = None
        self.error = ""
        self.thread = threading.Thread(target=self._run, name="ScenarioSignInWait", daemon=True)

    def cancel(self, reason="Sign-in cancelled"):
        self.reason = reason
        self.cancelled.set()

    def _run(self):
        try:
            self.tokens = self.attempt.complete(cancelled=self.cancelled)
        except oauth.SignInError as error:
            self.error = self.reason or str(error)
        except Exception:  # The worker must end with an outcome, never a traceback.
            log.exception("browser sign-in failed")
            self.error = "The sign-in did not complete"


def pending():
    return _pending is not None


def unavailable_reason():
    """Why no sign-in can start, or an empty string when this build knows its application."""
    try:
        app = oauth.selected_app()
    except oauth.SignInError as error:
        return str(error)
    return "" if app.configured else "Browser sign-in is not available in this release yet"


def observe_session_end():
    """Announce once, on the main thread, a session a worker's refresh could not keep.

    Called from the pump. The worker already deleted the token file; this
    retires the account's catalog and jobs and shows the reason.
    """
    global _reported_end
    session = runtime.state.browser_session
    if session is None or session.ended is None or session is _reported_end:
        return False
    _reported_end = session
    runtime.set_browser_session(None)
    runtime.set_message(session.ended)
    return True


def start():
    """Open the browser on the authorize page; the result arrives through the timer."""
    global _pending
    if _pending is not None:
        return
    if not runtime.online():
        raise ScenarioError(0, "Allow Online Access is disabled in Blender's preferences")
    try:
        app = oauth.selected_app()
        attempt = oauth.SignInAttempt(app)
    except oauth.SignInError as error:
        raise ScenarioError(0, str(error)) from None
    try:
        desktop.open_url(attempt.url)
    except (ValueError, playback.PlaybackError, OSError, RuntimeError):
        attempt.close()
        raise ScenarioError(0, "The system could not open the web browser") from None
    _pending = _Attempt(app, attempt, runtime.browser_session_path())
    _pending.thread.start()
    if not bpy.app.timers.is_registered(_poll):
        bpy.app.timers.register(_poll, first_interval=POLL_INTERVAL, persistent=True)


def cancel():
    if _pending is not None:
        _pending.cancel()


def _poll():
    """Apply a finished attempt on the main thread; keep polling while it runs.

    Allow Online Access is read here, on the main thread, while the browser is
    pending: switched off, the attempt is cancelled before the worker can swap
    the code for tokens, so no request starts after the permission is withdrawn.
    """
    global _pending
    attempt = _pending
    if attempt is None:
        return None
    if attempt.thread.is_alive():
        if not runtime.online():
            attempt.cancel("Allow Online Access was disabled during the sign-in")
        return POLL_INTERVAL
    _pending = None
    if attempt.tokens is None:
        runtime.set_message(attempt.error or "The sign-in did not complete")
    else:
        try:
            oauth.save_tokens(attempt.path, attempt.tokens)
        except OSError:
            runtime.set_message("Could not save the Scenario session")
        else:
            session = oauth.TokenSession(attempt.app, attempt.tokens, attempt.path)
            runtime.set_browser_session(session)
            runtime.set_message("Signed in to Scenario")
            # Ask where the work goes now, not at the first Generate.
            load_teams(choose=True)
    _redraw()
    return None


class _Listing:
    """One read of the account's teams and projects on a worker."""

    def __init__(self, session, choose):
        self.session = session
        self.choose = choose
        self.allowed = threading.Event()  # Allow Online Access, as the main thread last read it.
        self.allowed.set()
        self.teams = None
        self.error = ""
        self.thread = threading.Thread(target=self._run, name="ScenarioTeamsRead", daemon=True)

    def _run(self):
        try:
            with SDKAdapter(
                SDKCredentials(token_source=self.session),
                online=self.allowed.is_set,
                base_url=self.session.app.service,
            ) as adapter:
                self.teams = destinations.teams_from(adapter.teams())
        except AdapterError as error:
            self.error = f"Could not read your teams: {error}"
        except Exception:  # The worker must end with an outcome, never a traceback.
            log.exception("reading the account's teams failed")
            self.error = "Could not read your teams"


def load_teams(*, choose=False):
    """Read the signed-in account's teams and projects; ``choose`` settles the destination after."""
    global _listing
    session = runtime.browser_session()
    if session is None:
        return
    if _listing is not None:
        _listing.choose = _listing.choose or choose
        return
    if not runtime.online():
        runtime.state.browser_teams_error = (
            "Allow Online Access is disabled in Blender's preferences"
        )
        return
    _listing = _Listing(session, choose)
    runtime.state.browser_teams_loading = True
    runtime.state.browser_teams_error = ""
    _listing.thread.start()
    if not bpy.app.timers.is_registered(_poll_teams):
        bpy.app.timers.register(_poll_teams, first_interval=POLL_INTERVAL, persistent=True)


def _poll_teams():
    """Apply a finished read on the main thread, for the account that started it."""
    global _listing
    listing = _listing
    if listing is None:
        return None
    if listing.thread.is_alive():
        if not runtime.online():
            listing.allowed.clear()
        return POLL_INTERVAL
    _listing = None
    if runtime.browser_session() is not listing.session:
        return None  # Signed out or another account since: this list is not theirs.
    runtime.state.browser_teams_loading = False
    runtime.state.browser_teams = listing.teams
    runtime.state.browser_teams_error = listing.error
    if listing.error:
        runtime.set_message(listing.error)
    else:
        _settle(listing.teams, ask=listing.choose)
    _redraw()
    return None


def _settle(teams, *, ask):
    """Drop a choice the list no longer holds, use an only project, else ask if told to."""
    chosen = runtime.browser_project()
    if chosen is not None and destinations.find(teams, chosen[0]) is None:
        _forget_choice()  # Deleted, or the account lost its role there.
        runtime.set_message(f"{chosen[1]} is no longer available: choose a team and project")
        chosen = None
    only = destinations.only(teams)
    try:
        if chosen is None and only is not None:
            use(only)  # No choice to make: the account's only project.
        elif ask:
            open_chooser()
    except ScenarioError:
        open_chooser()


def _forget_choice():
    p = runtime.prefs()
    if p is not None:
        p.browser_project_label = ""
        p.browser_project_account = ""
        p.browser_project_id = ""


def wait_teams():
    """Headless use: block until the read ends, then apply it."""
    if _listing is not None:
        _listing.thread.join()
        _poll_teams()


def open_chooser():
    """Open the team and project dialog in the window Blender's timers run with."""
    if bpy.app.background:
        return
    context = bpy.context
    manager = context.window_manager
    window = context.window or next(
        (w for w in (manager.windows if manager else ()) if w.screen is not None), None
    )
    if window is None:
        return
    with context.temp_override(window=window, screen=window.screen):
        bpy.ops.scenario.choose_project("INVOKE_DEFAULT", fresh=True)


def choose(project_id):
    """Send this account's work to ``project_id``, one of its listed projects."""
    found = destinations.find(runtime.state.browser_teams or (), project_id)
    session = runtime.browser_session()
    p = runtime.prefs()
    if found is None or session is None or p is None:
        raise ScenarioError(0, "Choose one of your account's projects")
    # Label and account first: the id's update retires the previous destination.
    p.browser_project_label = destinations.label(*found)
    p.browser_project_account = session.account
    p.browser_project_id = project_id


def use(project_id):
    """Choose ``project_id``, say where the work goes and check the connection to it."""
    choose(project_id)
    runtime.set_message(f"Scenario work goes to {runtime.browser_project()[1]}")
    if not bpy.app.background:
        try:
            runtime.request_connection_check()
        except ScenarioError:
            pass  # Chosen; the account strip reports the check's outcome.


def draw_destination(layout):
    """The destination row: what is chosen and the button that changes it. Reads only."""
    chosen = runtime.browser_project()
    row = layout.row(align=True)
    if runtime.state.browser_teams_loading:
        row.label(text="Reading your teams and projects...", icon="TIME")
        return
    if chosen is None:
        row.alert = True
        row.operator("scenario.choose_project", text="Choose team and project", icon="ERROR")
    else:
        row.operator("scenario.choose_project", text=chosen[1], icon="COMMUNITY")
    if runtime.state.browser_teams_error:
        layout.label(text=runtime.state.browser_teams_error, icon="ERROR")


def wait():
    """Headless use: block until the browser answers, then apply the outcome."""
    if _pending is not None:
        _pending.thread.join()
        _poll()


def sign_out():
    """Forget the saved account and retire its catalog and jobs context."""
    session = runtime.state.browser_session
    if session is not None:
        session.sign_out()
    else:
        oauth.clear_tokens(runtime.browser_session_path())
    _forget_choice()
    runtime.set_browser_session(None)
    runtime.set_message("Signed out of Scenario")
    _redraw()


def _redraw():
    from . import pump

    pump.redraw()


class SCENARIO_OT_sign_in(bpy.types.Operator):
    bl_idname = "scenario.sign_in"
    bl_label = "Sign in with Scenario"
    bl_description = "Sign in through your web browser; no API key to paste"

    def execute(self, context):
        try:
            start()
        except ScenarioError as err:
            self.report({"ERROR"}, f"Scenario: {err.reason}")
            return {"CANCELLED"}
        if bpy.app.background:
            wait()
            if runtime.browser_session() is None:
                self.report({"ERROR"}, f"Scenario: {runtime.state.last_message}")
                return {"CANCELLED"}
            self.report({"INFO"}, runtime.state.last_message)
            return {"FINISHED"}
        self.report({"INFO"}, "Continue in your web browser")
        return {"FINISHED"}


class SCENARIO_OT_cancel_sign_in(bpy.types.Operator):
    bl_idname = "scenario.cancel_sign_in"
    bl_label = "Cancel sign-in"
    bl_description = "Stop waiting for the web browser"
    bl_options = {"INTERNAL"}

    def execute(self, context):
        cancel()
        return {"FINISHED"}


class SCENARIO_OT_sign_out(bpy.types.Operator):
    bl_idname = "scenario.sign_out"
    bl_label = "Sign out"
    bl_description = "Forget the signed-in Scenario account on this computer"

    def execute(self, context):
        sign_out()
        return {"FINISHED"}


def _team_items(self, context):
    teams = runtime.state.browser_teams or ()
    _enum_items["team"] = [(t.id, t.name, "") for t in teams] or [
        (NO_PROJECT, "No team", "This account belongs to no team")
    ]
    return _enum_items["team"]


def _project_items(self, context):
    team = next((t for t in runtime.state.browser_teams or () if t.id == self.team), None)
    projects = team.projects if team is not None else ()
    _enum_items["project"] = [(p.id, p.name, "") for p in projects] or [
        (NO_PROJECT, "No project", "You have no project in this team")
    ]
    return _enum_items["project"]


def _team_changed(self, context):
    # Another team's list: start on its first project rather than an invalid value.
    self.project = _project_items(self, context)[0][0]


class SCENARIO_OT_choose_project(bpy.types.Operator):
    bl_idname = "scenario.choose_project"
    bl_label = "Choose team and project"
    bl_description = "Choose the team and project your generations, uploads and spend go to"
    bl_options = {"INTERNAL"}

    team: bpy.props.EnumProperty(name="Team", items=_team_items, update=_team_changed)
    project: bpy.props.EnumProperty(name="Project", items=_project_items)
    fresh: bpy.props.BoolProperty(options={"HIDDEN", "SKIP_SAVE"})

    def invoke(self, context, event):
        if runtime.browser_session() is None:
            self.report({"ERROR"}, "Scenario: sign in first")
            return {"CANCELLED"}
        if not self.fresh or runtime.state.browser_teams is None:
            # Read first, so projects created or deleted since show; the dialog
            # opens once the list arrives.
            load_teams(choose=True)
            if runtime.state.browser_teams_error:
                self.report({"ERROR"}, f"Scenario: {runtime.state.browser_teams_error}")
                return {"CANCELLED"}
            return {"FINISHED"}
        teams = runtime.state.browser_teams
        chosen = runtime.browser_project()
        found = destinations.find(teams, chosen[0]) if chosen is not None else None
        if found is not None:
            self.team, self.project = found[0].id, found[1].id
        elif teams:
            self.team = teams[0].id
            _team_changed(self, context)
        return context.window_manager.invoke_props_dialog(self, width=420, confirm_text="Use")

    def draw(self, context):
        layout = self.layout
        layout.label(text="Where your generations, uploads and spend go")
        layout.prop(self, "team")
        layout.prop(self, "project")
        if self.project == NO_PROJECT:
            layout.label(text="Pick another team, or create a project on app.scenario.com")
        layout.label(text="Switch at any time from the Scenario sidebar", icon="INFO")

    def execute(self, context):
        if self.project == NO_PROJECT:
            self.report({"ERROR"}, "Scenario: choose a project")
            return {"CANCELLED"}
        try:
            use(self.project)
        except ScenarioError as err:
            self.report({"ERROR"}, f"Scenario: {err.reason}")
            return {"CANCELLED"}
        self.report({"INFO"}, runtime.state.last_message)
        _redraw()
        return {"FINISHED"}


class SCENARIO_OT_reload_teams(bpy.types.Operator):
    bl_idname = "scenario.reload_teams"
    bl_label = "Reload teams and projects"
    bl_description = "Read your teams and projects from Scenario again"
    bl_options = {"INTERNAL"}

    def execute(self, context):
        runtime.state.browser_teams = None
        load_teams()
        return {"FINISHED"}


CLASSES = (
    SCENARIO_OT_sign_in,
    SCENARIO_OT_cancel_sign_in,
    SCENARIO_OT_sign_out,
    SCENARIO_OT_choose_project,
    SCENARIO_OT_reload_teams,
)


def register():
    for cls in CLASSES:
        bpy.utils.register_class(cls)
    # Read the saved session here rather than from the first draw, and check its
    # choice against the account's current teams (a project can be deleted).
    p = runtime.prefs()
    if (
        runtime.browser_session() is not None
        and getattr(p, "credential_source", "") == "BROWSER"
        and not bpy.app.background
        and runtime.online()
    ):
        load_teams()


def unregister():
    global _pending, _listing
    cancel()
    if bpy.app.timers.is_registered(_poll):
        bpy.app.timers.unregister(_poll)
    if bpy.app.timers.is_registered(_poll_teams):
        bpy.app.timers.unregister(_poll_teams)
    _pending = None
    _listing = None
    for cls in reversed(CLASSES):
        bpy.utils.unregister_class(cls)
