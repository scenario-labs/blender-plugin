# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Modal operator that owns the mouse and keyboard while the pointer is on the composer or the prompt has focus."""

import bpy

from ...core.ui import composer_layout as cl
from .. import panels, runtime


def _layout(context, state):
    from .draw import ui_scale

    region = context.region
    return cl.pill_placement(
        region.width,
        region.height,
        state.expanded,
        ui_scale(context),
        offset=state.offset,
        width=state.width if state.expanded else None,
    )


def _redraw(context):
    if context.region is not None:
        context.region.tag_redraw()


def _open_sidebar(context):
    from ..popover import open_sidebar

    open_sidebar(context.area)


def _caret_index(context, state, layout, px):
    from .draw import caret_index_at, ui_scale

    return caret_index_at(px, layout.prompt_rect, state.field, ui_scale(context))


def _cursor(context, name):
    window = getattr(context, "window", None)
    if window is None:
        return
    try:
        if name is None:
            window.cursor_modal_restore()
        else:
            window.cursor_modal_set(name)
    except (AttributeError, TypeError, RuntimeError):
        pass


def _save_layout():
    from . import save_layout

    save_layout()


def _generate(operator, scene, state):
    """Submit the form the composer shows, only with that form's own ready quote."""
    if not state.owns_form(scene):
        # The card described another form (one replaced while focused): show this one first.
        operator.report({"WARNING"}, cl.FORM_REPLACED_GENERATE)
        return
    lane = state.generation_lane(scene)
    if not panels.generate_enabled(scene.scenario.lane_state(lane), lane):
        return
    try:
        bpy.ops.scenario.generate(lane=lane)
    except RuntimeError as error:
        # Operator error reports arrive as exceptions; the form keeps the reason. Keep this handler alive.
        message = str(error).strip()
        reason = message.removeprefix("Error:").strip() if message.startswith("Error:") else ""
        operator.report({"WARNING"}, reason or "Generation is not available right now")


def _takes_prompt(scene, state):
    lane = state.generation_lane(scene)
    return panels.form_takes_prompt(scene.scenario.lane_state(lane), lane)


def _edits_text(event, command):
    """Keys that change the prompt text; caret moves, selection and copy only read it."""
    if event.type in ("BACK_SPACE", "DEL"):
        return True
    if command:
        return event.type in ("V", "X")
    return bool(event.unicode) and not event.alt


def _open_dialog(context, scene, state, kind):
    if kind == "model":
        # the model chip opens the search dialog for the form it shows; the sidebar shows the rest
        _open_sidebar(context)
        try:
            bpy.ops.scenario.pick_model("INVOKE_DEFAULT", lane=state.generation_lane(scene))
        except (RuntimeError, AttributeError):
            # No dialog in this context: the sidebar opened above still holds the model chooser.
            pass
        return
    # the tab's settings in a dialog right here (the 3D tab includes its Edit mode form)
    try:
        bpy.ops.scenario.quick_settings("INVOKE_DEFAULT", lane=state.lane_for(scene))
    except (RuntimeError, AttributeError):
        _open_sidebar(context)


class SCENARIO_OT_composer_modal(bpy.types.Operator):
    bl_idname = "scenario.composer_modal"
    bl_label = "Scenario composer"
    bl_options = {"INTERNAL"}

    @classmethod
    def poll(cls, context):
        prefs = runtime.prefs()
        return (
            runtime.state.composer is not None
            and (prefs is None or prefs.composer_enabled)
            and context.area is not None
            and context.area.type == "VIEW_3D"
        )

    def invoke(self, context, event):
        state = runtime.state.composer
        if state is None or context.region is None or context.region.type != "WINDOW":
            return {"PASS_THROUGH", "CANCELLED"}
        layout = _layout(context, state)
        inside = layout.hit(event.mouse_region_x, event.mouse_region_y) is not None
        if not inside and not state.focused:
            return {"PASS_THROUGH", "CANCELLED"}
        if getattr(runtime.state, "composer_modal_running", False):
            return {"PASS_THROUGH", "CANCELLED"}
        runtime.state.composer_modal_running = True
        state.mouse = (event.mouse_region_x, event.mouse_region_y)
        context.window_manager.modal_handler_add(self)
        _redraw(context)
        return {"RUNNING_MODAL"}

    def _finish(self, context):
        runtime.state.composer_modal_running = False
        state = runtime.state.composer
        if state is not None:
            state.hover = None
            state.dragging = False
            if state.drag_mode is not None:
                state.cancel_drag()
                _cursor(context, None)
        _redraw(context)
        return {"FINISHED"}

    # -- placement drags -------------------------------------------------------
    def _drag_move(self, context, state, event):
        """Mouse moved while the button is held on the card background, the pill or the grip."""
        start = state.drag_start
        dx = event.mouse_region_x - start["mouse"][0]
        dy = event.mouse_region_y - start["mouse"][1]
        scale = _layout(context, state).scale
        if state.drag_mode == "pending":
            if abs(dx) < cl.DRAG_THRESHOLD * scale and abs(dy) < cl.DRAG_THRESHOLD * scale:
                return
            state.drag_mode = "move"
            _cursor(context, "SCROLL_XY")
        state.moved = True
        region = context.region
        if state.drag_mode == "move":
            state.offset = (start["offset"][0] + dx, start["offset"][1] + dy)
        elif state.drag_mode == "resize":
            base = start["width"] or cl.CARD_WIDTH * scale
            state.width = cl.clamp_width(base + dx, region.width, scale, expanded=True)
        _redraw(context)

    def _drag_release(self, context, state, scene):
        kind, mode, moved = state.end_drag()
        _cursor(context, None)
        if mode in ("move", "resize") and moved:
            # keep the placement inside the region as the layout clamps it, then remember it
            layout = _layout(context, state)
            base_x = (context.region.width - layout.pill_rect.w) / 2
            base_y = cl.MARGIN * layout.scale
            state.offset = (layout.pill_rect.x - base_x, layout.pill_rect.y - base_y)
            _save_layout()
        elif kind == "expand" and not moved:
            state.expanded = True
            state.sync_from_lane(scene)
        _redraw(context)

    def modal(self, context, event):
        state = runtime.state.composer
        if state is None or context.region is None:
            return self._finish(context)
        scene = context.scene
        layout = _layout(context, state)
        if state.drag_mode is not None:
            if event.type == "MOUSEMOVE":
                state.mouse = (event.mouse_region_x, event.mouse_region_y)
                self._drag_move(context, state, event)
                return {"RUNNING_MODAL"}
            if event.type == "LEFTMOUSE" and event.value == "RELEASE":
                self._drag_release(context, state, scene)
                return {"RUNNING_MODAL"}
            if event.type == "ESC" and event.value == "PRESS":
                state.cancel_drag()
                _cursor(context, None)
                _redraw(context)
                return {"RUNNING_MODAL"}
            return {"RUNNING_MODAL"}
        if event.type == "MOUSEMOVE":
            state.mouse = (event.mouse_region_x, event.mouse_region_y)
            if state.dragging and state.focused and layout.prompt_rect is not None:
                state.field.caret_at(
                    _caret_index(context, state, layout, event.mouse_region_x), extend=True
                )
                _redraw(context)
                return {"RUNNING_MODAL"}
            hit = layout.hit(*state.mouse)
            if hit != state.hover:
                if hit == ("resize",):
                    # the corner shows a resize cursor instead of a permanent grip
                    _cursor(context, "MOVE_X")
                elif state.hover == ("resize",):
                    _cursor(context, None)
                state.hover = hit
                _redraw(context)
            if hit is None and not state.focused:
                return self._finish(context)
            return {"PASS_THROUGH"}
        if event.type == "LEFTMOUSE" and event.value == "RELEASE":
            if state.dragging:
                state.dragging = False
                _redraw(context)
                return {"RUNNING_MODAL"}
            return {"PASS_THROUGH"} if not state.focused else {"RUNNING_MODAL"}
        if event.type == "LEFTMOUSE" and event.value == "DOUBLE_CLICK":
            hit = layout.hit(event.mouse_region_x, event.mouse_region_y)
            if hit == ("prompt",) and state.expanded:
                # The press before it already explained a form without a prompt. A focused field
                # keeps the form it was synchronized from, even one that was replaced.
                if state.focused or _takes_prompt(scene, state):
                    if not state.focused:
                        state.sync_from_lane(scene)
                    state.focused = True
                    state.field.select_word_at(
                        _caret_index(context, state, layout, event.mouse_region_x)
                    )
                    state.dragging = False
                    _redraw(context)
            elif hit in (("drag",), ("resize",)):
                # double-click on the card background puts the composer back at its default place and size
                state.cancel_drag()
                state.reset_layout()
                _save_layout()
                _redraw(context)
            return {"RUNNING_MODAL"}
        if event.type == "LEFTMOUSE" and event.value == "PRESS":
            hit = layout.hit(event.mouse_region_x, event.mouse_region_y)
            if hit is None:
                try:
                    state.flush_focused_prompt(scene)
                except RuntimeError as error:
                    self.report({"WARNING"}, str(error))
                    return {"RUNNING_MODAL"}
                # Deliver the same click to the header/sidebar or viewport after blur.
                return self._finish(context) | {"PASS_THROUGH"}
            kind = hit[0]
            if kind == "expand":
                # a click expands the pill; a move beyond the threshold drags it instead (decided on release)
                state.begin_drag((event.mouse_region_x, event.mouse_region_y), "expand")
            elif kind == "drag":
                if state.focused:
                    state.leave_focus(scene)
                state.begin_drag((event.mouse_region_x, event.mouse_region_y), "drag")
            elif kind == "resize":
                state.begin_drag((event.mouse_region_x, event.mouse_region_y), "resize")
                _cursor(context, "MOVE_X")
            elif kind == "collapse":
                state.leave_focus(scene)
                state.expanded = False
            elif kind == "tab":
                if state.form_replaced(scene):
                    # Like Esc: leave the original form without writing to either form.
                    state.leave_focus(scene)
                else:
                    state.commit_to_lane(scene)
                scene.scenario.lane = hit[1]
                if state.focused and not _takes_prompt(scene, state):
                    # The new form takes no prompt: its field explains why instead of keeping focus.
                    state.leave_focus(scene)
                state.sync_from_lane(scene)
            elif kind == "prompt" and not state.focused and not _takes_prompt(scene, state):
                self.report({"INFO"}, cl.NO_PROMPT)
            elif kind == "prompt":
                if not state.focused:
                    state.sync_from_lane(scene)
                state.focused = True
                state.field.caret_at(
                    _caret_index(context, state, layout, event.mouse_region_x), extend=event.shift
                )
                state.dragging = True
            elif kind == "generate":
                state.leave_focus(scene)
                _generate(self, scene, state)
            elif kind in ("model", "settings"):
                # Their dialogs can switch the form (3D mode, model lane): commit and blur first.
                try:
                    state.flush_focused_prompt(scene)
                except RuntimeError as error:
                    self.report({"WARNING"}, str(error))
                else:
                    _open_dialog(context, scene, state, kind)
            _redraw(context)
            return {"RUNNING_MODAL"}
        if not state.focused:
            return {"PASS_THROUGH"}
        if event.value != "PRESS":
            return {"RUNNING_MODAL"}
        field = state.field
        command = event.ctrl or event.oskey
        if event.type == "ESC":
            # Leaves a replaced form without writing to either one; the next draw shows the new form.
            state.leave_focus(scene)
            _redraw(context)
            return {"RUNNING_MODAL"}
        if event.type in ("RET", "NUMPAD_ENTER"):
            state.leave_focus(scene)
            _generate(self, scene, state)
            _redraw(context)
            return {"RUNNING_MODAL"}
        if state.form_replaced(scene) and _edits_text(event, command):
            # Keep the keys away from the viewport, but never type into the form that replaced it.
            self.report({"WARNING"}, cl.FORM_REPLACED_TYPING)
            return {"RUNNING_MODAL"}
        if _edits_text(event, command) and not _takes_prompt(scene, state):
            # Another window or a tool loaded a model without a prompt into this form: write nothing.
            state.focused = state.dragging = False
            self.report({"WARNING"}, cl.NO_PROMPT)
            _redraw(context)
            return {"RUNNING_MODAL"}
        if event.type == "BACK_SPACE":
            field.backspace()
        elif event.type == "DEL":
            field.delete()
        elif event.type == "LEFT_ARROW":
            field.move(-1, extend=event.shift)
        elif event.type == "RIGHT_ARROW":
            field.move(1, extend=event.shift)
        elif event.type == "HOME":
            field.home(extend=event.shift)
        elif event.type == "END":
            field.end(extend=event.shift)
        elif command and event.type == "V":
            field.insert(context.window_manager.clipboard or "")
        elif command and event.type == "A":
            field.select_all()
        elif command and event.type == "C":
            context.window_manager.clipboard = field.copy()
            _redraw(context)
            return {"RUNNING_MODAL"}  # the text did not change
        elif command and event.type == "X":
            context.window_manager.clipboard = field.cut()
        elif event.unicode and not (command or event.alt):
            field.insert(event.unicode)
        else:
            return {"RUNNING_MODAL"}
        state.commit_to_lane(scene)
        _redraw(context)
        return {"RUNNING_MODAL"}
