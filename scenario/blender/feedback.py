# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Send feedback: the dialog, the text kept until it is sent, and one send at a time.

**Send feedback** opens a dialog with a rating, a message and an optional email; nothing is
sent until the user presses Send, and usage sharing is not required. What the user typed
is kept in this module, never in the blend file or the preferences, until a send succeeds,
so a refused or failed send can be retried with the same text. One worker thread posts the
body through core.telemetry.feedback and queues its outcome; the pump applies it on the
main thread with process(), and background Blender waits for it in the operator, as Test
connection does. The outcome becomes the status message and the preferences' status line.
"""

import queue
import threading

import bpy
from bpy.props import EnumProperty, StringProperty

from .. import __version__
from ..core.telemetry import feedback as core
from ..core.telemetry import relay
from . import runtime, usage

RATINGS = (
    ("NONE", "Not rated", "Send no rating"),
    ("1", "1", "1 out of 5, the lowest"),
    ("2", "2", "2 out of 5"),
    ("3", "3", "3 out of 5"),
    ("4", "4", "4 out of 5"),
    ("5", "5", "5 out of 5, the highest"),
)
FIELDS = ("rating", "message", "email")
EMPTY = {"rating": "NONE", "message": "", "email": ""}
SENDING = "Sending your feedback..."
BUSY = "Your feedback is being sent"
OFFLINE = "Enable Allow Online Access in Blender's System preferences"
NOTE = "Sent to Scenario with the extension, Blender and OS versions"
DIALOG_WIDTH = 440

_draft = dict(EMPTY)  # the dialog's text, kept until a send succeeds; main thread only
_results = queue.Queue()  # (worker, Outcome, the fields it sent) from finished sends
_worker = None  # the send in flight, until process() applies its outcome
_status = None  # (text, sent) of the last applied outcome
_send = None  # tests replace the relay POST


def draft():
    """A copy of the kept text, which the dialog opens with."""
    return dict(_draft)


def sending():
    return _worker is not None


def status():
    """(text, icon) of the send in flight or the last outcome, or None before any send."""
    if _worker is not None:
        return SENDING, "SORTTIME"
    if _status is None:
        return None
    text, sent = _status
    return text, "CHECKMARK" if sent else "ERROR"


def failure():
    """Why the last send failed, while its text is kept for another try; else None."""
    if _worker is None and _status is not None and not _status[1]:
        return _status[0]
    return None


def rating_value(identifier):
    return None if identifier == "NONE" else int(identifier)


def start(payload, fields):
    """Post one body on a worker thread; process() applies its outcome on the main thread."""
    global _worker
    worker = threading.Thread(
        target=_run, args=(payload, fields, _send), daemon=True, name="scenario-feedback"
    )
    _worker = worker
    worker.start()
    return worker


def _run(payload, fields, send):
    outcome = core.FAILED
    try:
        outcome = core.submit(payload, send=send)
    finally:
        _results.put((threading.current_thread(), outcome, fields))


def process():
    """Apply finished sends on the main thread; True when what is drawn changed."""
    global _draft, _status, _worker
    changed = False
    while True:
        try:
            worker, outcome, fields = _results.get_nowait()
        except queue.Empty:
            return changed
        if worker is not _worker:
            continue  # a send from before the extension was last unregistered
        _worker = None
        _status = (outcome.text, outcome.sent)
        if outcome.sent and _draft == fields:
            _draft = dict(EMPTY)
        runtime.set_message(outcome.text)
        changed = True


class SCENARIO_OT_send_feedback(bpy.types.Operator):
    bl_idname = "scenario.send_feedback"
    bl_label = "Send feedback"
    bl_description = (
        "Rate the extension or tell Scenario what to improve; nothing is sent until you press Send"
    )

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
        for name in FIELDS:
            if not self.properties.is_property_set(name):
                setattr(self, name, kept[name])
        return context.window_manager.invoke_props_dialog(
            self, width=DIALOG_WIDTH, confirm_text="Send"
        )

    def draw(self, context):
        from .panels import equal_segments

        layout = self.layout
        reason = failure()
        if reason:
            layout.label(text=reason, icon="ERROR")
        layout.label(text="How would you rate the extension? 5 is best")
        equal_segments(layout, self, "rating", [item[0] for item in RATINGS])
        layout.prop(self, "message", text="", placeholder="What should we improve?")
        layout.prop(
            self, "email", text="", placeholder="Email, if you would like a reply (optional)"
        )
        hint = core.problem(rating_value(self.rating), self.message, self.email)
        if hint:
            layout.label(text=hint, icon="INFO")
        note = layout.row()
        note.active = False
        note.label(text=NOTE)

    def execute(self, context):
        global _draft
        process()  # a send that ended since the last pump tick
        fields = {name: getattr(self, name) for name in FIELDS}
        _draft = dict(fields)  # kept until a send succeeds, so a refusal keeps the text
        if sending():
            self.report({"WARNING"}, BUSY)
            return {"CANCELLED"}
        if not runtime.online():  # access can change after poll
            self.report({"WARNING"}, "Allow Online Access is off; your feedback was not sent")
            return {"CANCELLED"}
        try:
            payload = core.build(
                rating_value(self.rating),
                self.message,
                self.email,
                context=relay.context(__version__, usage.blender_version()),
                install_id=usage.install_id(),
            )
        except core.FeedbackError as error:
            self.report({"WARNING"}, str(error))
            return {"CANCELLED"}
        worker = start(payload, fields)
        if bpy.app.background:  # no pump: wait for the outcome here
            worker.join(core.TIMEOUT + 1.0)
            process()
        text, icon = status()
        if icon == "SORTTIME":
            runtime.set_message(text)
        self.report({"WARNING"} if icon == "ERROR" else {"INFO"}, text)
        return {"FINISHED"}


CLASSES = (SCENARIO_OT_send_feedback,)


def register():
    for cls in CLASSES:
        bpy.utils.register_class(cls)


def unregister():
    global _status, _worker
    _worker = None  # a send still in flight is not applied
    _status = None
    for cls in reversed(CLASSES):
        bpy.utils.unregister_class(cls)
