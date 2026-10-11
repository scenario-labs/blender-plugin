# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Input-method text and the composer: Blender's own text field takes over where the custom prompt cannot."""

import unittest
from types import SimpleNamespace
from unittest import mock

import bpy
from helpers import reset_scene, submodule

PANEL = "SCENARIO_PT_composer_text_field"


class _Event:
    """A modal event that counts reads of its type: Blender logs a warning for each read of a type
    outside its Python enum, which it reports as an empty string."""

    def __init__(self, kind, value="PRESS", unicode="", is_repeat=False, **modifiers):
        self._type = kind
        self.type_reads = 0
        self.value = value
        self.unicode = unicode
        self.is_repeat = is_repeat
        self.mouse_region_x = self.mouse_region_y = 0
        for name in ("shift", "ctrl", "oskey", "alt"):
            setattr(self, name, modifiers.get(name, False))

    @property
    def type(self):
        self.type_reads += 1
        return self._type


class _Recorder:
    """A UILayout stand-in that records rows, labels and properties, with their activate_init flag."""

    def __init__(self, calls=None):
        self.calls = [] if calls is None else calls
        self.activate_init = False
        self.active = True

    def row(self, **_kwargs):
        child = _Recorder(self.calls)
        self.calls.append(("row", child))
        return child

    def label(self, **kwargs):
        self.calls.append(("label", kwargs))

    def prop(self, data, name, **kwargs):
        self.calls.append(("prop", data, name, kwargs, self.activate_init))


class ComposerTextInputTests(unittest.TestCase):
    def setUp(self):
        reset_scene()
        self.modal = submodule("blender.composer.modal")
        self.text_field = submodule("blender.composer.text_field")
        self.state_mod = submodule("blender.composer.state")
        self.runtime = submodule("blender.runtime")
        self.scene = bpy.context.scene
        self.scene.scenario.lane = "image"
        self.lane_state = self.scene.scenario.lane_state("image")
        self.lane_state.prompt = "hello world"
        self.wm = bpy.context.window_manager
        self.state = self.state_mod.ComposerState()
        self.state.expanded = True
        self.state.sync_from_lane(self.scene)
        self.state.focused = True
        self.state.field.caret_at(5)
        self.context = SimpleNamespace(
            region=SimpleNamespace(tag_redraw=lambda: None),
            scene=self.scene,
            window_manager=self.wm,
            window=None,
        )
        # an expanded card with nothing under the pointer: only the key handling matters here
        self.layout = SimpleNamespace(expanded=True, hit=lambda _x, _y: None, prompt_rect=None)

    def tearDown(self):
        self.wm.scenario_composer_text = ""

    def _modal(self, event, call_panel=None):
        call_panel = call_panel or mock.Mock(return_value={"INTERFACE"})
        operator = SimpleNamespace(report=mock.Mock())
        ops = SimpleNamespace(wm=SimpleNamespace(call_panel=call_panel))
        with (
            mock.patch.object(self.runtime.state, "composer", self.state),
            mock.patch.object(self.modal, "_layout", return_value=self.layout),
            mock.patch.object(self.modal, "bpy", SimpleNamespace(ops=ops)),
        ):
            result = self.modal.SCENARIO_OT_composer_modal.modal(operator, self.context, event)
        return result, call_panel, operator

    # -- the modal hands input-method composition to Blender's text field -------------------------
    def test_a_composition_opens_blenders_text_field_on_its_second_untyped_press(self):
        # stored without running its update, as a file load would
        self.wm["scenario_composer_text"] = "left over"
        # A composition starts with two presses in a row that have no Python type and no text (its start, then
        # its first update); a lone one may be a dead key, so the first press opens nothing.
        start, update = _Event(""), _Event("")
        result, call_panel, operator = self._modal(start)
        self.assertEqual(result, {"RUNNING_MODAL"})
        call_panel.assert_not_called()
        self.assertEqual(start.type_reads, 1)  # one warning per event, not one per comparison
        result, call_panel, operator = self._modal(update)
        self.assertEqual(result, {"RUNNING_MODAL"})
        call_panel.assert_called_once_with(name=PANEL, keep_open=False)
        self.assertEqual(update.type_reads, 1)
        self.assertEqual(self.wm.scenario_composer_text, "")  # the field opens empty
        self.assertTrue(self.state.focused)  # the text it adds goes to this prompt's caret
        self.assertFalse(self.state.dragging)
        self.assertEqual(self.lane_state.prompt, "hello world")
        operator.report.assert_not_called()
        # the run starts again: one more untyped press opens nothing
        result, call_panel, _ = self._modal(_Event(""))
        call_panel.assert_not_called()

    def test_a_dead_key_types_its_accent_without_opening_the_text_field(self):
        # A dead key (French ^, German acute) arrives as a press and a release with no Python type and no text;
        # the next key carries the accented character.
        for event in (
            _Event(""),
            _Event("", value="RELEASE"),
            _Event("E", unicode="ê"),
            _Event("E", value="RELEASE"),
        ):
            result, call_panel, _ = self._modal(event)
            self.assertEqual(result, {"RUNNING_MODAL"})
            call_panel.assert_not_called()
        self.assertEqual(self.lane_state.prompt, "helloê world")
        # a held dead key repeats its press without a release in between: repeats are not a composition
        for event in (_Event(""), _Event("", is_repeat=True), _Event("", is_repeat=True)):
            result, call_panel, _ = self._modal(event)
            self.assertEqual(result, {"RUNNING_MODAL"})
            call_panel.assert_not_called()
        self._modal(_Event("", value="RELEASE"))
        # a dead key followed by a named key, then another dead key, is not a composition either
        for event in (_Event(""), _Event("SPACE", unicode="^"), _Event("")):
            result, call_panel, _ = self._modal(event)
            call_panel.assert_not_called()
        self.assertEqual(self.lane_state.prompt, "helloê^ world")

    def test_untyped_keys_with_text_are_typed_with_one_read_of_their_type(self):
        # Some keys Blender cannot name still carry text (French ù, harness-injected characters).
        event = _Event("", unicode="é")
        result, call_panel, _ = self._modal(event)
        self.assertEqual(result, {"RUNNING_MODAL"})
        call_panel.assert_not_called()
        self.assertEqual(event.type_reads, 1)
        self.assertEqual(self.lane_state.prompt, "helloé world")
        self.assertEqual(self.state.field.caret, 6)
        # with Ctrl, Cmd or Alt the text is not typed, as for named keys; the event is still consumed
        for modifier in ("ctrl", "oskey", "alt"):
            event = _Event("", unicode="ù", **{modifier: True})
            result, call_panel, _ = self._modal(event)
            self.assertEqual(result, {"RUNNING_MODAL"})
            call_panel.assert_not_called()
            self.assertEqual(event.type_reads, 1)
        self.assertEqual(self.lane_state.prompt, "helloé world")
        # a key with text between two untyped presses ends the run: no text field
        for event in (_Event(""), _Event("", unicode="ù"), _Event("")):
            result, call_panel, _ = self._modal(event)
            call_panel.assert_not_called()
        self.assertEqual(self.lane_state.prompt, "helloéù world")

    def test_untyped_events_without_focus_on_release_or_during_a_drag_open_nothing(self):
        # without focus the composer leaves them to Blender, and the run of presses starts again
        self._modal(_Event(""))
        self.state.focused = False
        event = _Event("")
        result, call_panel, _ = self._modal(event)
        self.assertEqual(result, {"PASS_THROUGH"})
        call_panel.assert_not_called()
        self.assertEqual(event.type_reads, 1)
        self.state.focused = True
        result, call_panel, _ = self._modal(_Event(""))
        call_panel.assert_not_called()
        # a release (the key up of a dead key) is consumed by a focused prompt and ends the run
        event = _Event("", value="RELEASE")
        result, call_panel, _ = self._modal(event)
        self.assertEqual(result, {"RUNNING_MODAL"})
        call_panel.assert_not_called()
        self.assertEqual(event.type_reads, 1)
        # during a placement drag nothing else happens, and the drag ends the run
        self._modal(_Event(""))
        self.state.begin_drag((0, 0), "drag")
        result, call_panel, _ = self._modal(_Event(""))
        self.assertEqual(result, {"RUNNING_MODAL"})
        call_panel.assert_not_called()
        self.state.cancel_drag()
        result, call_panel, _ = self._modal(_Event(""))
        call_panel.assert_not_called()
        # a named key press between two untyped presses ends the run too
        self._modal(_Event("LEFT_ARROW"))
        result, call_panel, _ = self._modal(_Event(""))
        call_panel.assert_not_called()
        self.assertEqual(self.lane_state.prompt, "hello world")

    def test_f2_opens_the_text_field_only_while_the_prompt_has_focus(self):
        result, call_panel, _ = self._modal(_Event("F2"))
        self.assertEqual(result, {"RUNNING_MODAL"})
        call_panel.assert_called_once_with(name=PANEL, keep_open=False)
        self.assertTrue(self.state.focused)
        self.state.focused = False
        result, call_panel, _ = self._modal(_Event("F2"))
        self.assertEqual(result, {"PASS_THROUGH"})  # Blender's own F2 (rename) without focus
        call_panel.assert_not_called()

    def test_a_text_field_that_cannot_open_reports_it(self):
        failing = mock.Mock(side_effect=RuntimeError("poll failed"))
        self._modal(_Event(""), call_panel=failing)
        failing.assert_not_called()
        result, call_panel, operator = self._modal(_Event(""), call_panel=failing)
        self.assertEqual(result, {"RUNNING_MODAL"})
        call_panel.assert_called_once()
        operator.report.assert_called_once()
        self.assertEqual(operator.report.call_args.args[0], {"WARNING"})
        self.assertEqual(self.lane_state.prompt, "hello world")

    # -- the text field's text goes into the prompt like typed keys ------------------------------
    def test_text_from_the_field_is_typed_at_the_prompt_caret(self):
        with mock.patch.object(self.runtime.state, "composer", self.state):
            self.wm.scenario_composer_text = "日本"
            self.assertEqual(self.state.field.text, "hello日本 world")
            self.assertEqual(self.state.field.caret, 7)
            self.assertEqual(self.lane_state.prompt, "hello日本 world")
            # nothing stays in the window manager
            self.assertEqual(self.wm.scenario_composer_text, "")
            self.assertTrue(self.state.focused)
            # a selection is replaced, as typing replaces it
            self.state.field.caret_at(8)
            self.state.field.caret_at(13, extend=True)
            self.wm.scenario_composer_text = "語"
            self.assertEqual(self.lane_state.prompt, "hello日本 語")
            # an empty confirmation changes nothing
            self.wm.scenario_composer_text = ""
            self.assertEqual(self.lane_state.prompt, "hello日本 語")

    def test_text_for_a_prompt_without_focus_goes_to_its_current_form(self):
        self.state.focused = False
        self.lane_state.prompt = "edited in the sidebar"
        with mock.patch.object(self.runtime.state, "composer", self.state):
            self.wm.scenario_composer_text = " 雪"
        self.assertEqual(self.lane_state.prompt, "edited in the sidebar 雪")
        self.assertFalse(self.state.focused)

    def test_text_without_a_composer_is_dropped_from_the_window_manager(self):
        with mock.patch.object(self.runtime.state, "composer", None):
            self.wm.scenario_composer_text = "orphan"
        self.assertEqual(self.wm.scenario_composer_text, "")
        self.assertEqual(self.lane_state.prompt, "hello world")

    # -- the popover ------------------------------------------------------------------------------
    def test_panel_draws_one_field_activated_on_display_and_changes_nothing(self):
        self.assertTrue(hasattr(bpy.types, PANEL))
        self.assertIn("scenario_composer_text", bpy.types.WindowManager.bl_rna.properties)
        layout = _Recorder()
        panel = SimpleNamespace(layout=layout)
        with mock.patch.object(self.runtime.state, "composer", self.state):
            self.text_field.SCENARIO_PT_composer_text_field.draw(panel, bpy.context)
        props = [call for call in layout.calls if call[0] == "prop"]
        self.assertEqual(len(props), 1)
        _, data, name, kwargs, activated = props[0]
        self.assertEqual((data, name), (bpy.context.window_manager, "scenario_composer_text"))
        self.assertTrue(activated)  # typing (and composing) starts without a click
        self.assertEqual(kwargs.get("text"), "")
        labels = [call[1]["text"] for call in layout.calls if call[0] == "label"]
        self.assertTrue(any("Image prompt" in text for text in labels), labels)
        self.assertEqual(self.lane_state.prompt, "hello world")
        self.assertEqual(self.wm.scenario_composer_text, "")


if __name__ == "__main__":
    unittest.main()
