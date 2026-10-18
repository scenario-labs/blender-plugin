# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Invitations in the Scenario panels: share anonymous usage data once, then feedback prompts.

The usage data card shows under the account strip once a connection has succeeded in this
session: Test connection passed, or the model list arrived from Scenario (one read from the
local cache does not count). It never shows offline, while the connection or the catalog
reports an error, while sharing is on, or once answered. Share turns the preference on as
its checkbox does; No thanks only records the answer on this computer
(core.telemetry.prompts), so declining sends nothing and creates no install ID. Changing
the checkbox in the preferences, either way, answers the card too.

Two feedback prompts open the Send feedback dialog. **Tell us what went wrong** sits under
an error the panels draw, and pre-fills an empty message with that error, stripped of what
could identify the user (core.telemetry.feedback.strip_error). **How's it going?** tops the
Generations panel once RATING_AFTER generations started with Generate in this Blender have
saved their results; it is offered once, after the usage data card is settled, and a
successful feedback send also retires it. Acting on either prompt, including its dismissal,
keeps both away for QUIET_PERIOD; an ignored error link shows again under a later error.
No prompt shows offline. Nothing about a prompt or its answer is sent.

The record is read at registration and written on the main thread by the prompts'
operators, the preference's update, a successful feedback send and the pump's tick, which
counts generations; drawing reads this module's copy only.
"""

import logging
import time

import bpy
from bpy.props import EnumProperty, StringProperty

from ..core.telemetry import feedback as feedback_core
from ..core.telemetry import prompts as record
from . import feedback, label_wrap, runtime, usage

log = logging.getLogger("scenario.prompts")

USAGE_TITLE = "Help improve Scenario for Blender?"
USAGE_TEXT = (
    "Share anonymous usage data: which commands and agent tools you use, never prompts or files."
)
DETAILS_URL = "https://blender.scenario.com/#what-leaves-your-machine"
SHARED = "Usage data is shared; turn it off in the extension's preferences"
DECLINED = "Usage data stays off; turn it on in the extension's preferences"
ANSWERS = (
    ("SHARE", "Share", "Share anonymous usage data: which commands and agent tools you use"),
    ("DECLINE", "No thanks", "Keep usage data off; this card does not ask again"),
)
REPORT = "Tell us what went wrong"
RATING_TITLE = "How's it going?"
RATING_TEXT = "Rate Scenario for Blender or tell us what to improve."
FEEDBACK_ANSWERS = (
    ("RATE", "Send feedback...", "Rate the extension or tell Scenario what to improve"),
    ("DECLINE", "No thanks", "Do not offer this again"),
    ("HIDE", "", "Hide these links for a week"),
)
BUSY = feedback.BUSY
# Saved states of a generation whose results are saved, and of one that ended without.
SAVED_RESULTS = frozenset({"ready", "applying", "apply_failed", "applied"})
SETTLED = SAVED_RESULTS | {"failed", "canceled"}
# Interface units a body line cannot use in the sidebar: the panel's and the card's
# margins up to the category tabs, plus slack, as result_previews.TEXT_INSET measures.
TEXT_INSET = 96

_saved = {}  # the record as last read or written; main thread only
_connected = False  # a connection succeeded in this session
_watched = set()  # local IDs of generations started with Generate, until they settle
_clock = time.time  # tests move time


def load():
    """Read the saved record; never let it stop the extension from registering."""
    global _saved
    try:
        _saved = record.read(usage.state_dir())
    except (OSError, ValueError):  # no user directory for this package
        _saved = {}


def _answer(**entries):
    """Record answers; kept for this session even when the file cannot be written."""
    global _saved
    try:
        _saved = record.update(usage.state_dir(), **entries)
    except (OSError, ValueError) as error:
        _saved = {**_saved, **entries}
        log.warning("The answer was not saved (%s)", type(error).__name__)


def connected():
    """Test connection passed or the model list arrived from Scenario; main thread."""
    global _connected
    _connected = True


def sharing_answered():
    """The preference's update: setting the checkbox, either way, answers the card."""
    if _saved.get("usage_card") != record.ANSWERED:
        _answer(usage_card=record.ANSWERED)


def usage_card_shown():
    prefs = runtime.prefs()
    return (
        _connected
        and _saved.get("usage_card") != record.ANSWERED
        and prefs is not None
        and not prefs.share_usage
        and runtime.online()
        and runtime.credentials().valid
        and runtime.state.connection_status != "error"
        and not runtime.state.catalog_error
    )


def draw_usage_card(layout, context):
    if not usage_card_shown():
        return
    box = layout.box()
    box.label(text=USAGE_TITLE, icon="FUND")
    for line in label_wrap.label_lines(context, USAGE_TEXT, TEXT_INSET):
        box.label(text=line)
    row = box.row()
    for answer, text, _description in ANSWERS:
        row.operator(SCENARIO_OT_usage_card.bl_idname, text=text).answer = answer
    row.operator("scenario.open_url", text="Details").url = DETAILS_URL
    layout.separator(factor=0.5)


# -- feedback prompts ----------------------------------------------------------
def quiet():
    """Whether feedback prompts stay away: one was acted on less than QUIET_PERIOD ago."""
    return record.quiet(_saved, _clock())


def _act():
    """A feedback prompt was acted on: keep both away for QUIET_PERIOD."""
    _answer(quiet_until=_clock() + record.QUIET_PERIOD)


def error_link_shown():
    return runtime.online() and not quiet()


def draw_error_link(layout, error):
    """**Tell us what went wrong** under an error the panel draws, with its dismissal."""
    if not error or not error_link_shown():
        return
    row = layout.row(align=True)
    row.operator(SCENARIO_OT_report_error.bl_idname, text=REPORT, icon="HEART").error = error
    row.operator(SCENARIO_OT_feedback_prompt.bl_idname, text="", icon="X").answer = "HIDE"


def rating_card_shown():
    prefs = runtime.prefs()
    settled = _saved.get("usage_card") == record.ANSWERED or (
        prefs is not None and prefs.share_usage
    )
    return runtime.online() and settled and record.rating_due(_saved) and not quiet()


def draw_rating_card(layout, context):
    if not rating_card_shown():
        return
    box = layout.box()
    box.label(text=RATING_TITLE, icon="HEART")
    for line in label_wrap.label_lines(context, RATING_TEXT, TEXT_INSET):
        box.label(text=line)
    row = box.row()
    for answer, text, _description in FEEDBACK_ANSWERS[:2]:
        row.operator(SCENARIO_OT_feedback_prompt.bl_idname, text=text).answer = answer


def feedback_sent():
    """A feedback send succeeded: the rating prompt has nothing left to ask."""
    if _saved.get("rating_prompt") != record.ANSWERED:
        _answer(rating_prompt=record.ANSWERED)


def watch_generation(local_id):
    """Generate submitted this job; tick counts it once its results are saved."""
    if _saved.get("rating_prompt") != record.ANSWERED and not record.rating_due(_saved):
        _watched.add(local_id)


def tick():
    """Count watched generations whose results were saved; True when the card appears."""
    global _saved
    if not _watched:
        return False
    jobs = runtime.state.model_jobs
    views = jobs.views if jobs is not None else {}
    due = record.rating_due(_saved)
    for local_id in tuple(_watched):
        view = views.get(local_id)
        state = view.meta.get("saved_state") if view is not None else None
        if view is not None and state not in SETTLED:
            continue
        _watched.discard(local_id)
        if state in SAVED_RESULTS:
            try:
                _saved = record.count_generation(usage.state_dir())
            except (OSError, ValueError) as error:
                counted = min(record.RATING_AFTER, _saved.get("generations", 0) + 1)
                _saved = {**_saved, "generations": counted}
                log.warning("The generation was not counted (%s)", type(error).__name__)
    return record.rating_due(_saved) and not due


def _open_feedback(**fields):
    """Open the Send feedback dialog, with `fields` replacing the text it keeps."""
    bpy.ops.scenario.send_feedback("INVOKE_DEFAULT", **fields)


class SCENARIO_OT_usage_card(bpy.types.Operator):
    bl_idname = "scenario.usage_card"
    bl_label = "Usage data card"
    bl_description = "Answer the invitation to share anonymous usage data"
    # Not REGISTER: Repeat Last must not answer again. usage.EXCLUDED_OPERATORS keeps
    # an answer out of usage data.
    bl_options = {"INTERNAL"}

    answer: EnumProperty(items=ANSWERS, options={"SKIP_SAVE"})

    @classmethod
    def description(cls, context, properties):
        return next(item[2] for item in ANSWERS if item[0] == properties.answer)

    def execute(self, context):
        prefs = runtime.prefs()
        if prefs is None:
            return {"CANCELLED"}
        if self.answer == "SHARE":
            prefs.share_usage = True  # its update starts sharing and answers the card
            sharing_answered()  # also when it was on already
            context.preferences.is_dirty = True  # Auto-Save Preferences then keeps it
            self.report({"INFO"}, SHARED)
        else:
            _answer(usage_card=record.ANSWERED)
            self.report({"INFO"}, DECLINED)
        return {"FINISHED"}


def _feedback_poll(owner):
    """Whether Send feedback can open; a class's poll also says why not."""
    for blocked, reason in ((not runtime.online(), feedback.OFFLINE), (feedback.sending(), BUSY)):
        if blocked:
            if isinstance(owner, type):
                owner.poll_message_set(reason)
            return False
    return True


class SCENARIO_OT_report_error(bpy.types.Operator):
    bl_idname = "scenario.report_error"
    bl_label = REPORT
    bl_description = (
        "Open Send feedback with this error, without names, paths, links or IDs; "
        "nothing is sent until you press Send"
    )
    # Not REGISTER, and out of usage data: see SCENARIO_OT_usage_card.
    bl_options = {"INTERNAL"}

    error: StringProperty(options={"SKIP_SAVE", "HIDDEN"})

    @classmethod
    def poll(cls, context):
        return _feedback_poll(cls)

    def execute(self, context):
        _act()
        if feedback.draft()["message"].strip():  # the user's unsent text comes first
            _open_feedback()
        else:
            _open_feedback(message=f"Error: {feedback_core.strip_error(self.error)}")
        return {"FINISHED"}


class SCENARIO_OT_feedback_prompt(bpy.types.Operator):
    bl_idname = "scenario.feedback_prompt"
    bl_label = "Feedback prompt"
    bl_description = "Answer a feedback prompt"
    # Not REGISTER, and out of usage data: see SCENARIO_OT_usage_card.
    bl_options = {"INTERNAL"}

    answer: EnumProperty(items=FEEDBACK_ANSWERS, options={"SKIP_SAVE"})

    @classmethod
    def description(cls, context, properties):
        return next(item[2] for item in FEEDBACK_ANSWERS if item[0] == properties.answer)

    def execute(self, context):
        if self.answer == "RATE" and not _feedback_poll(self):  # dismissing always works
            self.report({"WARNING"}, BUSY if runtime.online() else feedback.OFFLINE)
            return {"CANCELLED"}
        _act()
        if self.answer != "HIDE":
            _answer(rating_prompt=record.ANSWERED)
        if self.answer == "RATE":
            _open_feedback()
        return {"FINISHED"}


CLASSES = (SCENARIO_OT_usage_card, SCENARIO_OT_report_error, SCENARIO_OT_feedback_prompt)


def register():
    load()
    for cls in CLASSES:
        bpy.utils.register_class(cls)


def unregister():
    global _connected, _saved
    for cls in reversed(CLASSES):
        bpy.utils.unregister_class(cls)
    _connected, _saved = False, {}
    _watched.clear()
