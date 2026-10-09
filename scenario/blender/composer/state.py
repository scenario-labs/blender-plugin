# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Interaction state of the floating composer, mirrored into the Scene lane state."""

from ...core.ui.composer_layout import LANE_ORDER, TextField
from .. import props

COMPOSER_LANES = tuple(LANE_ORDER)


class ComposerState:
    def __init__(self):
        self.expanded = False
        self.focused = False
        # left button held inside the prompt: mouse moves extend the selection
        self.dragging = False
        self.hover = None
        self.mouse = (0, 0)
        self.field = TextField("")
        self.synced_scene = None
        self.synced_lane = ""
        self.synced_text = None
        self.layout = None
        # placement: offset from the default bottom-centre spot (region pixels) and an optional card width
        self.offset = (0.0, 0.0)
        self.width = None
        self.drag_mode = None  # None | "pending" | "move" | "resize"
        self.drag_start = None  # dict(mouse, offset, width, kind) captured at the press
        self.moved = False

    def lane_for(self, scene):
        """The composer drives the six generation lanes; other tabs (Generations, MCP, 3D tools) fall back to Image."""
        lane = scene.scenario.lane
        if lane in COMPOSER_LANES and scene.scenario.lane_state(lane) is not None:
            return lane
        return "image"

    def generation_lane(self, scene):
        """The form behind the visible tab: its prompt, model, price and Generate (3D Edit mode is Edit 3D)."""
        return props.effective_lane(scene, self.lane_for(scene))

    def sync_from_lane(self, scene):
        lane = self.generation_lane(scene)
        lane_state = scene.scenario.lane_state(lane)
        if (
            scene != self.synced_scene
            or lane != self.synced_lane
            or lane_state.prompt != self.synced_text
        ):
            self.field.set_text(lane_state.prompt)
            self.field.end()
            self.synced_scene = scene
            self.synced_lane, self.synced_text = lane, lane_state.prompt
        return lane_state

    def owns_form(self, scene):
        """Whether the field mirrors the form shown now: the scene and form it was synchronized from."""
        try:
            return self.synced_scene == scene and self.synced_lane == self.generation_lane(scene)
        except ReferenceError:
            return False

    def form_replaced(self, scene):
        """Whether another form replaced the one the focused prompt belongs to.

        A Settings mode switch, a model pick, another window or a tool can do it. Each edit was
        committed to the original form as it was typed.
        """
        return self.focused and not self.owns_form(scene)

    def replaced_form(self, scene):
        """(tab, lane) of the original form a replaced focused prompt still describes in this scene."""
        if not self.form_replaced(scene):
            return None
        try:
            same_scene = self.synced_scene == scene
        except ReferenceError:
            return None
        if not same_scene or scene.scenario.lane_state(self.synced_lane) is None:
            return None
        return props.form_tab(self.synced_lane), self.synced_lane

    def commit_to_lane(self, scene):
        """Write the field into the form it was synchronized from, never into one that replaced it."""
        if not self.owns_form(scene):
            return None
        lane_state = scene.scenario.lane_state(self.synced_lane)
        if lane_state.prompt != self.field.text:
            lane_state.prompt = self.field.text
        self.synced_text = self.field.text
        return lane_state

    def leave_focus(self, scene):
        """Esc, Enter, Generate, collapse or a drag: commit to the original form only, then blur."""
        self.commit_to_lane(scene)
        self.focused = False
        self.dragging = False

    def flush_focused_prompt(self, scene):
        """Leave text focus only after committing to the unchanged original form."""
        if not self.focused:
            return
        try:
            valid = (
                self.owns_form(scene)
                and self.synced_text == scene.scenario.lane_state(self.synced_lane).prompt
            )
        except ReferenceError:
            valid = False
        if not valid:
            raise RuntimeError("Finish editing the original prompt before leaving the composer")
        self.leave_focus(scene)

    # -- placement ------------------------------------------------------------
    def begin_drag(self, mouse, kind):
        """Remember where a press happened so a move beyond the threshold turns into a drag (or a resize)."""
        self.drag_mode = "resize" if kind == "resize" else "pending"
        self.drag_start = {
            "mouse": tuple(mouse),
            "offset": tuple(self.offset),
            "width": self.width,
            "kind": kind,
        }
        self.moved = False

    def cancel_drag(self):
        """Escape: put the composer back where it was when the press happened."""
        if self.drag_start is not None:
            self.offset = tuple(self.drag_start["offset"])
            self.width = self.drag_start["width"]
        self.drag_mode = None
        self.drag_start = None
        self.moved = False

    def end_drag(self):
        kind = self.drag_start["kind"] if self.drag_start else None
        mode, moved = self.drag_mode, self.moved
        self.drag_mode = None
        self.drag_start = None
        self.moved = False
        return kind, mode, moved

    def reset_layout(self):
        self.offset = (0.0, 0.0)
        self.width = None
