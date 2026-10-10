# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Interaction state of the floating composer, mirrored into the Scene lane state."""

from ...core.ui.composer_layout import LANE_ORDER, DoubleClick, TextField
from .. import props

COMPOSER_LANES = tuple(LANE_ORDER)
# Regions whose last drawn job strip a click is checked against; more windows than this are rare.
DRAWN_STRIP_LIMIT = 32
# Jobs whose last offered actions the strip holds while a status refresh is running.
OFFERED_LIMIT = 64


def _bounded(cache, key, value, limit):
    """Store `value` as the newest entry of `cache`, dropping the oldest beyond `limit`."""
    cache.pop(key, None)
    cache[key] = value
    while len(cache) > limit:
        del cache[next(iter(cache))]


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
        # pairs the presses of a double-click, which the modal only receives as presses
        self.presses = DoubleClick()
        # A press with no Python type and no text reached the focused prompt, with no release or other press
        # since. An input-method composition starts with two in a row; a dead key sends one, then its release.
        self.untyped_press = False
        # Job strip display state, Python only and never saved: a file load starts over.
        # (scene session_uid, lane) -> request ID of the job whose strip the user dismissed
        self.dismissed = {}
        # region key -> what its last drawn strip offered (strip_signature), for the click guard
        self.drawn_strips = {}
        # request ID -> (saved revision, action descriptors) last offered while no command ran
        self.offered = {}

    def dismiss(self, key, request_id):
        """Hide the strip of `request_id` for this scene lane; a newer job there shows again."""
        self.dismissed[key] = request_id

    def is_dismissed(self, key, request_id):
        return self.dismissed.get(key) == request_id

    def remember_strip(self, region_key, signature):
        """Record what a region's strip showed; None when it shows none."""
        if signature is None:
            self.drawn_strips.pop(region_key, None)
        else:
            _bounded(self.drawn_strips, region_key, signature, DRAWN_STRIP_LIMIT)

    def shown_actions(self, request_id, revision, actions, busy):
        """(actions, held): the actions the strip shows for a job, and whether they are held.

        The job offers no action while a status refresh or another command is running, so the strip
        keeps the actions it last offered for the same saved revision instead of blinking every poll.
        Held actions are for display only: a click on one waits for the command to finish. Actions
        the job offers while busy, such as cancelling a queued unsent job, stay live."""
        actions = tuple(actions)
        if not busy:
            _bounded(self.offered, request_id, (revision, actions), OFFERED_LIMIT)
            return actions, False
        offered = self.offered.get(request_id)
        if not actions and offered is not None and offered[0] == revision and offered[1]:
            return offered[1], True
        return actions, False

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

    def shown_form(self, scene):
        """(tab, lane) the card describes: the form behind the visible tab, or until Esc, the
        original form of a replaced focused prompt. Its job strip follows the same form."""
        original = self.replaced_form(scene)
        if original is not None:
            return original
        return self.lane_for(scene), self.generation_lane(scene)

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

    def type_text(self, scene, text):
        """Type `text` at the caret as typed keys would: it replaces a selection and is committed to the lane.

        A prompt without focus takes it at its last caret, or at the end when its lane prompt changed since."""
        if not self.focused:
            self.sync_from_lane(scene)
        self.field.insert(text)
        return self.commit_to_lane(scene)

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
