# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Blender's own text field over the composer prompt, for input-method (IME) text.

Blender composes input-method text (Japanese, Chinese, Korean) only in its native UI text fields: Python receives
no composition data, and its event types have no Python name. The composer opens this popover, like F2 rename,
with an empty field that starts editing at once; Enter types the field's text at the prompt's caret.
"""

import bpy
from bpy.props import StringProperty

from ...core.ui import composer_layout as cl
from .. import runtime

PANEL = "SCENARIO_PT_composer_text_field"


def _redraw_views(context):
    for window in getattr(context.window_manager, "windows", ()):
        for area in window.screen.areas:
            if area.type == "VIEW_3D":
                area.tag_redraw()


def _on_text(wm, context):
    """The field was confirmed: type its text into the composer prompt, then empty the field."""
    text = wm.scenario_composer_text
    if not text:
        return
    wm.scenario_composer_text = ""  # runs this callback again with nothing to type
    state = runtime.state.composer
    scene = getattr(context, "scene", None)
    if state is None or scene is None or not hasattr(scene, "scenario"):
        return
    state.type_text(scene, text)
    _redraw_views(context)


class SCENARIO_PT_composer_text_field(bpy.types.Panel):
    bl_space_type = "TOPBAR"  # dummy: opened only as a popover, like Blender's F2 rename
    bl_region_type = "HEADER"
    bl_label = "Type into the prompt"
    bl_ui_units_x = 20

    def draw(self, context):
        layout = self.layout
        state = runtime.state.composer
        scene = getattr(context, "scene", None)
        lane = "image"
        if state is not None and scene is not None and hasattr(scene, "scenario"):
            lane = state.lane_for(scene)
        layout.label(text=f"Type into the {cl.LANE_LABELS.get(lane, 'Image')} prompt", icon="TEXT")
        row = layout.row()
        row.activate_init = True  # edits on display, so an input method composes here right away
        row.prop(
            context.window_manager,
            "scenario_composer_text",
            text="",
            placeholder="Text to add at the caret",
        )
        hint = layout.row()
        hint.active = False
        hint.label(text="Enter adds it to the prompt, Esc cancels")


def register():
    bpy.types.WindowManager.scenario_composer_text = StringProperty(
        name="Prompt text",
        description="Text to type into the composer prompt at its caret",
        options={"SKIP_SAVE"},
        update=_on_text,
    )
    bpy.utils.register_class(SCENARIO_PT_composer_text_field)


def unregister():
    bpy.utils.unregister_class(SCENARIO_PT_composer_text_field)
    del bpy.types.WindowManager.scenario_composer_text
