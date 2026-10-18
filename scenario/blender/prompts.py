# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""The Scenario panel's one-time invitation to share anonymous usage data.

The card shows under the account strip once a connection has succeeded in this session:
Test connection passed, or the model list arrived from Scenario (one read from the local
cache does not count). It never shows offline, while the connection or the catalog reports
an error, while sharing is on, or once answered. Share turns the preference on as its
checkbox does; No thanks only records the answer on this computer
(core.telemetry.prompts), so declining sends nothing and creates no install ID. Changing
the checkbox in the preferences, either way, answers the card too. The record is read at
registration and written on the main thread by the card's operator and the preference's
update; drawing reads this module's copy only.
"""

import logging

import bpy
from bpy.props import EnumProperty

from ..core.telemetry import prompts as record
from . import label_wrap, runtime, usage

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
# Interface units a body line cannot use in the sidebar: the panel's and the card's
# margins up to the category tabs, plus slack, as result_previews.TEXT_INSET measures.
TEXT_INSET = 96

_saved = {}  # the record as last read or written; main thread only
_connected = False  # a connection succeeded in this session


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


CLASSES = (SCENARIO_OT_usage_card,)


def register():
    load()
    for cls in CLASSES:
        bpy.utils.register_class(cls)


def unregister():
    global _connected, _saved
    for cls in reversed(CLASSES):
        bpy.utils.unregister_class(cls)
    _connected, _saved = False, {}
