# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Browser sign-in: start the system browser here, wait on a worker, apply the result here.

The callback port is opened and the browser started on Blender's main thread,
through the credential-free opener. A worker waits for the browser and swaps
the code for tokens; a timer applies the outcome on the main thread, where the
runtime's account, catalog and job context change.
"""

import logging
import threading

import bpy

from ..core.api import oauth
from ..core.api.errors import ScenarioError
from ..core.jobs import playback
from . import desktop, runtime

log = logging.getLogger("scenario")
POLL_INTERVAL = 0.25
_pending = None  # The one sign-in in progress, main thread only.
_reported_end = None  # The session whose end the pump already announced.


class _Attempt:
    def __init__(self, app, attempt, path):
        self.app = app
        self.attempt = attempt
        self.path = path
        self.cancelled = threading.Event()
        self.tokens = None
        self.error = ""
        self.thread = threading.Thread(target=self._run, name="ScenarioSignInWait", daemon=True)

    def _run(self):
        try:
            self.tokens = self.attempt.complete(cancelled=self.cancelled)
        except oauth.SignInError as error:
            self.error = str(error)
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
        _pending.cancelled.set()


def _poll():
    """Apply a finished attempt on the main thread; keep polling while it runs."""
    global _pending
    attempt = _pending
    if attempt is None:
        return None
    if attempt.thread.is_alive():
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
            # The GUI pump drains the check's outcome; headless callers run their own.
            if not bpy.app.background:
                try:
                    runtime.request_connection_check()
                except ScenarioError:
                    pass
    _redraw()
    return None


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


CLASSES = (SCENARIO_OT_sign_in, SCENARIO_OT_cancel_sign_in, SCENARIO_OT_sign_out)


def register():
    for cls in CLASSES:
        bpy.utils.register_class(cls)
    # Read the saved session here rather than from the first draw.
    runtime.browser_session()


def unregister():
    global _pending
    cancel()
    if bpy.app.timers.is_registered(_poll):
        bpy.app.timers.unregister(_poll)
    _pending = None
    for cls in reversed(CLASSES):
        bpy.utils.unregister_class(cls)
