# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Send feedback: the dialog, the text kept until it is sent, and one send at a time.

**Send feedback** opens a dialog with a rating, a message and an optional email; nothing is
sent until the user presses Send, and usage sharing is not required. What the user typed
is kept in this module, never in the blend file or the preferences, until a send succeeds,
so a refused or failed send, or a dialog closed without Send, can be retried with the same
text; the dialog edits it through controls whose edits Blender does not log (see CONTROLS).
The text keeps one submission ID until it is sent or edited, so a retry after an uncertain
failure is grouped with the response it may duplicate. One worker thread posts
the body through core.telemetry.feedback and queues its outcome; the pump applies it on the
main thread with process(), and background Blender waits for it in the operator, as Test
connection does. A send still running ABANDON_AFTER seconds after it started (urllib's
timeout does not bound name resolution) is given up as unanswered, so another can start; its
outcome still replaces that message if it arrives before another send starts. Each outcome
is shown as the status message, in the status bar and, as fresh as that message, in the
preferences.
"""

import logging
import queue
import threading
import time
import uuid

import bpy
from bpy.props import EnumProperty, StringProperty

from .. import __version__
from ..core.telemetry import feedback as core
from ..core.telemetry import relay
from . import runtime, usage

log = logging.getLogger("scenario.feedback")

RATINGS = (
    ("NONE", "Not rated", "Send no rating"),
    ("1", "1", "1 out of 5, the lowest"),
    ("2", "2", "2 out of 5"),
    ("3", "3", "3 out of 5"),
    ("4", "4", "4 out of 5"),
    ("5", "5", "5 out of 5, the highest"),
)
FIELDS = ("rating", "message", "email")
# The dialog's controls: get/set properties of the extension's preferences that read and
# edit the kept text through field() and edit(), and store nothing there. Blender logs every
# edit committed in a field to the Info editor as `<path> = <value>`, and its crash log
# copies that list (ui_apply_but_autokey, crashlog_file_generate). It skips only a PASSWORD
# property, which it masks even while it is edited, and data that belongs to no ID, such as
# the preferences. The operator's own properties belong to the window manager.
CONTROLS = {"rating": "feedback_rating", "message": "feedback_message", "email": "feedback_email"}
EMPTY = {"rating": "NONE", "message": "", "email": ""}
SENDING = "Sending your feedback..."
BUSY = "Your feedback is being sent"
OFFLINE = "Enable Allow Online Access in Blender's System preferences"
NOTE = (
    "Sent with your extension and Blender versions and system type,",
    "plus your install ID while usage data is shared",
)
DIALOG_WIDTH = 480
ABANDON_AFTER = core.TIMEOUT + 1.0

_draft = dict(EMPTY)  # the dialog's text, kept until a send succeeds; main thread only
_submission = None  # the kept text's submission ID, reused until it is sent or edited
_results = queue.Queue()  # (worker, Outcome, its submission ID) from finished sends
_worker = None  # the send in flight, until process() applies or abandons it
_gave_up = None  # the send last given up: its late outcome applies until another starts
_started = 0.0  # when the send in flight started, on _clock
_status = None  # (text, sent, when) of the last applied outcome
_send = None  # tests replace the relay POST
_clock = time.monotonic  # tests move time


def draft():
    """A copy of the kept text, which the dialog opens with."""
    return dict(_draft)


def _abandoned():
    return _worker is not None and _clock() - _started >= ABANDON_AFTER


def sending():
    return _worker is not None and not _abandoned()


def _fresh():
    """(text, sent) of the last outcome while it is current, as status messages are."""
    if _status is None:
        return None
    text, sent, at = _status
    return (text, sent) if _clock() - at <= runtime.MESSAGE_TTL else None


def status():
    """(text, icon) of the send in flight or a fresh outcome, else None."""
    if sending():
        return SENDING, "SORTTIME"
    fresh = _fresh()
    if fresh is None:
        return None
    text, sent = fresh
    return text, "CHECKMARK" if sent else "ERROR"


def failure():
    """Why the last send failed, while that is fresh and its text kept; else None."""
    fresh = None if sending() else _fresh()
    return fresh[0] if fresh is not None and not fresh[1] else None


def _keep(fields):
    """Keep the dialog's text; edited text is a new response, with a new submission ID."""
    global _draft, _submission
    if fields != _draft:
        _submission = None
    _draft = dict(fields)


def field(name):
    """A kept field as its control reads it; the rating as its index in RATINGS."""
    value = _draft[name]
    return [item[0] for item in RATINGS].index(value) if name == "rating" else value


def edit(name, value):
    """Keep an edit made in a control: edited text is a new response (see _keep)."""
    _keep({**_draft, name: RATINGS[value][0] if name == "rating" else value})


def _untag_preferences(operator, context):
    """Editing the controls marks the preferences modified, as any preference edit does.

    Undone when the dialog closes, unless they were already modified when it opened, so
    Blender does not save the preferences at quit for text that is not in them.
    """
    if getattr(operator, "preferences_were_dirty", True) is False:
        context.preferences.is_dirty = False


def rating_value(identifier):
    return None if identifier == "NONE" else int(identifier)


def start(payload):
    """Post one body on a worker thread; process() applies its outcome on the main thread."""
    global _gave_up, _started, _worker
    worker = threading.Thread(
        target=_run, args=(payload, _send), daemon=True, name="scenario-feedback"
    )
    _worker, _started, _gave_up = worker, _clock(), None
    worker.start()
    return worker


def _run(payload, send):
    outcome = core.UNCONFIRMED
    try:
        outcome = core.submit(payload, send=send)
    finally:
        _results.put((threading.current_thread(), outcome, payload["submission_id"]))


def _apply(outcome, submission):
    global _draft, _status, _submission
    _status = (outcome.text, outcome.sent, _clock())
    if outcome.sent and submission == _submission:  # the kept text was not edited meanwhile
        _draft, _submission = dict(EMPTY), None
    runtime.set_message(outcome.text)


def _give_up():
    global _gave_up, _worker
    _gave_up, _worker = _worker, None
    _apply(core.NO_ANSWER, None)


def _drain():
    global _gave_up, _worker
    changed = False
    while True:
        try:
            worker, outcome, submission = _results.get_nowait()
        except queue.Empty:
            return changed
        if worker is _worker:
            _worker = None
        elif worker is _gave_up:  # a late answer, and no other send started since
            _gave_up = None
        else:
            continue  # superseded, or from before the extension was last unregistered
        _apply(outcome, submission)
        changed = True


def _settle():
    """Give up the send in flight, unless it ended after the last drain."""
    worker = _worker
    if isinstance(worker, threading.Thread) and not worker.is_alive():
        return _drain()  # its outcome was queued before the thread ended
    _give_up()
    return True


def process():
    """Apply finished or abandoned sends on the main thread; True when what is drawn changed.

    Queued outcomes come first, so a tick delayed past ABANDON_AFTER (a long file load or
    bake) still applies the answer that arrived; only a send still running is given up.
    """
    changed = _drain()
    if _abandoned():
        changed |= _settle()
    return changed


def announce():
    """Report the outcome the pump just applied in the status bar, where Send reported sending.

    Only an operator's report reaches the status bar, and a script's operator call keeps
    the reports to itself unless the operator is still running when the call returns, so
    feedback_outcome reports at its first event in the first window. False without one;
    background Blender, whose operator reported the outcome itself, has no status bar.
    """
    manager = bpy.context.window_manager
    if bpy.app.background or manager is None:
        return False
    window = next((w for w in manager.windows if w.screen is not None), None)
    if window is None:
        return False
    try:
        with bpy.context.temp_override(window=window, screen=window.screen):
            return "RUNNING_MODAL" in bpy.ops.scenario.feedback_outcome()
    except Exception:  # the panel and the preferences still show the outcome
        log.debug("Showing the feedback outcome in the status bar failed", exc_info=True)
        return False


class SCENARIO_OT_send_feedback(bpy.types.Operator):
    bl_idname = "scenario.send_feedback"
    bl_label = "Send feedback"
    bl_description = (
        "Rate the extension or tell Scenario what to improve; nothing is sent until you press Send"
    )
    # Not REGISTER: the Info editor would log the message and email as a Python call, and
    # Repeat Last would send it again without the dialog.
    bl_options = set()

    # A script's call passes the text here; the dialog draws CONTROLS instead.
    rating: EnumProperty(name="Rating", items=RATINGS, default="NONE", options={"SKIP_SAVE"})
    message: StringProperty(
        name="Message", description="What should we improve?", options={"SKIP_SAVE"}
    )
    email: StringProperty(
        name="Email",
        description="Your email address, if you would like a reply",
        options={"SKIP_SAVE"},
    )

    @classmethod
    def poll(cls, context):
        if not runtime.online():
            cls.poll_message_set(OFFLINE)
            return False
        if sending():
            cls.poll_message_set(BUSY)
            return False
        return True

    def invoke(self, context, event):
        kept = draft()
        for name in FIELDS:  # the call's arguments replace the kept text the dialog shows
            if self.properties.is_property_set(name):
                kept[name] = getattr(self, name)
        _keep(kept)
        self.preferences_were_dirty = context.preferences.is_dirty
        return context.window_manager.invoke_props_dialog(
            self, width=DIALOG_WIDTH, confirm_text="Send"
        )

    def draw(self, context):
        from .panels import equal_segments

        layout = self.layout
        controls = runtime.prefs()
        reason = failure()
        if reason:
            layout.label(text=reason, icon="ERROR")
        layout.label(text="How would you rate the extension? 5 is best")
        equal_segments(layout, controls, CONTROLS["rating"], [item[0] for item in RATINGS])
        layout.prop(controls, CONTROLS["message"], text="", placeholder="What should we improve?")
        layout.prop(
            controls,
            CONTROLS["email"],
            text="",
            placeholder="Email, if you would like a reply (optional)",
        )
        hint = core.problem(rating_value(_draft["rating"]), _draft["message"], _draft["email"])
        if hint:
            layout.label(text=hint, icon="INFO")
        note = layout.column(align=True)
        note.active = False
        for line in NOTE:
            note.label(text=line)

    def cancel(self, context):
        # Blender calls it when the dialog closes without Send (Esc, Cancel, a click outside).
        # The controls have kept the text already.
        _untag_preferences(self, context)

    def execute(self, context):
        global _submission
        if self.options.is_invoke:  # Send in the dialog, whose controls edit the kept text
            _untag_preferences(self, context)
            fields = draft()
        else:  # a script's call, whose arguments are the text
            fields = {name: getattr(self, name) for name in FIELDS}
        _keep(fields)  # until a send succeeds
        if _submission is None:
            _submission = uuid.uuid4().hex
        # Fields and ID taken before process(): a late answer it applies may clear the kept
        # text, and a resend of that text must still carry its submission ID to be grouped
        # with it.
        submission = _submission
        process()  # a send that ended since the last pump tick
        if sending():
            self.report({"WARNING"}, BUSY)
            return {"CANCELLED"}
        if not runtime.online():  # access can change after poll
            self.report({"WARNING"}, "Allow Online Access is off; your feedback was not sent")
            return {"CANCELLED"}
        try:
            payload = core.build(
                rating_value(fields["rating"]),
                fields["message"],
                fields["email"],
                context=relay.context(__version__, usage.blender_version()),
                install_id=usage.install_id(),
                submission_id=submission,
            )
        except core.FeedbackError as error:
            self.report({"WARNING"}, str(error))
            return {"CANCELLED"}
        worker = start(payload)
        if bpy.app.background:  # no pump: wait for the outcome, or give the send up, here
            worker.join(ABANDON_AFTER)
            process()
            if worker is _worker:  # not over ABANDON_AFTER on the clock yet, but waited out
                _settle()
        text, icon = status() or (SENDING, "SORTTIME")
        if icon == "SORTTIME":
            runtime.set_message(text)
        self.report({"WARNING"} if icon == "ERROR" else {"INFO"}, text)
        return {"FINISHED"}


class SCENARIO_OT_feedback_outcome(bpy.types.Operator):
    # Started by announce(): runs modal for one event so its report reaches the status bar.
    bl_idname = "scenario.feedback_outcome"
    bl_label = "Feedback outcome"
    bl_description = "Show the outcome of the last feedback send in the status bar"
    bl_options = {"INTERNAL"}

    def execute(self, context):
        manager = context.window_manager
        self.timer = manager.event_timer_add(0.0, window=context.window)
        manager.modal_handler_add(self)
        return {"RUNNING_MODAL"}

    def modal(self, context, event):
        context.window_manager.event_timer_remove(self.timer)
        shown = status()
        if shown is not None and shown[1] != "SORTTIME":  # not replaced by another send
            text, icon = shown
            self.report({"WARNING"} if icon == "ERROR" else {"INFO"}, text)
        return {"FINISHED", "PASS_THROUGH"}

    def cancel(self, context):
        context.window_manager.event_timer_remove(self.timer)


CLASSES = (SCENARIO_OT_send_feedback, SCENARIO_OT_feedback_outcome)


def register():
    for cls in CLASSES:
        bpy.utils.register_class(cls)


def unregister():
    global _gave_up, _status, _worker
    _worker = _gave_up = None  # a send still in flight is not applied
    _status = None
    for cls in reversed(CLASSES):
        bpy.utils.unregister_class(cls)
