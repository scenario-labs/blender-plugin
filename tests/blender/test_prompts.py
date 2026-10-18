# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""The usage data card in the installed extension: when it shows, and what each answer does.

A temporary state directory replaces the extension's user directory, so the record and the
install ID never reach the test profile's. Nothing here contacts Scenario or the relay.
"""

import json
import pathlib
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, call, patch

import bpy
from helpers import addon_name, online_access, submodule


class UsageCardTests(unittest.TestCase):
    def setUp(self):
        self.prompts = submodule("blender.prompts")
        self.record = submodule("core.telemetry.prompts")
        self.usage = submodule("blender.usage")
        self.runtime = submodule("blender.runtime")
        self.handlers = submodule("blender.handlers")
        self.prefs = bpy.context.preferences.addons[addon_name()].preferences
        self.assertFalse(self.prefs.share_usage)
        directory = tempfile.TemporaryDirectory(prefix="scenario-test-prompts-")
        self.addCleanup(directory.cleanup)
        self.state = pathlib.Path(directory.name)
        for target, name, value in (
            (self.usage, "state_dir", Mock(return_value=self.state)),
            (self.prompts, "_saved", {}),
            (self.prompts, "_connected", False),
            (self.runtime, "credentials", Mock(return_value=SimpleNamespace(valid=True))),
            (self.runtime.state, "connection_status", ""),
            (self.runtime.state, "connection_request", None),
            (self.runtime.state, "catalog_error", ""),
            (self.runtime.state, "account_label", ""),
            (self.runtime.state, "last_message", ""),
        ):
            patcher = patch.object(target, name, value)
            patcher.start()
            self.addCleanup(patcher.stop)
        self.addCleanup(setattr, self.prefs, "share_usage", False)
        preferences = bpy.context.preferences
        self.addCleanup(setattr, preferences, "is_dirty", preferences.is_dirty)

    def shown(self):
        with online_access(True):
            return self.prompts.usage_card_shown()

    def saved(self):
        path = self.state / self.record.PROMPTS_FILE
        return json.loads(path.read_text(encoding="utf-8")) if path.exists() else None

    def install_id(self):
        return submodule("core.telemetry.usage").read_install_id(self.state)

    def answer(self, answer):
        operator = SimpleNamespace(answer=answer, report=Mock())
        with online_access(True):
            result = bpy.types.SCENARIO_OT_usage_card.execute(operator, bpy.context)
        self.assertEqual(result, {"FINISHED"})
        return operator.report

    def test_registered_internal_and_never_recorded_as_usage(self):
        operator = bpy.types.SCENARIO_OT_usage_card
        self.assertEqual(operator.bl_options, {"INTERNAL"})
        self.assertIn("scenario.usage_card", self.usage.EXCLUDED_OPERATORS)
        self.assertNotIn(operator, self.usage._instrumented)
        self.assertFalse(self.usage.instrument(operator))
        descriptions = {
            answer: operator.description(bpy.context, SimpleNamespace(answer=answer))
            for answer in ("SHARE", "DECLINE")
        }
        self.assertIn("which commands and agent tools you use", descriptions["SHARE"])
        self.assertIn("does not ask again", descriptions["DECLINE"])

    def test_shown_once_test_connection_passes(self):
        self.assertFalse(self.shown())
        key = object()
        self.runtime.state.connection_request = key
        self.handlers.dispatch(("connection", {"key": key, "error": "Unauthorized"}))
        self.assertEqual(self.runtime.state.connection_status, "error")
        self.assertFalse(self.shown())
        self.runtime.state.connection_request = key
        self.handlers.dispatch(("connection", {"key": key, "error": None}))
        self.assertTrue(self.shown())

    def test_shown_once_the_model_list_arrives_from_scenario(self):
        generation = submodule("blender.generation")
        self.assertFalse(self.shown())
        with patch.object(generation, "set_catalog") as set_catalog:
            self.handlers.dispatch(("catalog", {"records": [], "detailed": [], "warmup": True}))
        set_catalog.assert_called_once_with([], [], warmup=True)
        self.assertTrue(self.shown())

    def test_hidden_offline_while_sharing_or_failing_or_without_credentials(self):
        self.prompts.connected()
        self.assertTrue(self.shown())
        self.assertFalse(self.prompts.usage_card_shown())  # Allow Online Access is off
        cases = (
            (self.runtime.state, "connection_status", "error"),
            (self.runtime.state, "catalog_error", "Could not load models"),
            (self.runtime, "credentials", Mock(return_value=SimpleNamespace(valid=False))),
            (self.runtime, "prefs", Mock(return_value=None)),
        )
        for target, name, value in cases:
            with self.subTest(name), patch.object(target, name, value):
                self.assertFalse(self.shown())
        with patch.object(self.usage, "set_sharing"):
            self.prefs.share_usage = True
            self.assertFalse(self.shown())
            self.prefs.share_usage = False

    def test_no_thanks_records_the_answer_and_nothing_else(self):
        self.prompts.connected()
        with (
            patch.object(self.usage, "set_sharing") as set_sharing,
            patch.object(submodule("core.telemetry.relay"), "post_json") as post,
        ):
            report = self.answer("DECLINE")
        report.assert_called_once_with({"INFO"}, self.prompts.DECLINED)
        set_sharing.assert_not_called()
        post.assert_not_called()
        self.assertFalse(self.prefs.share_usage)
        self.assertIsNone(self.install_id())
        self.assertIsNone(self.usage.recorder())
        self.assertEqual(self.saved(), {"usage_card": "answered"})
        self.assertEqual(sorted(path.name for path in self.state.iterdir()), ["prompts.json"])
        self.assertFalse(self.shown())

    def test_share_turns_the_preference_on_and_keeps_it(self):
        self.prompts.connected()
        bpy.context.preferences.is_dirty = False
        report = self.answer("SHARE")
        report.assert_called_once_with({"INFO"}, self.prompts.SHARED)
        self.assertTrue(self.prefs.share_usage)
        self.assertIsNotNone(self.install_id())
        self.assertTrue(bpy.context.preferences.is_dirty)
        self.assertEqual(self.saved(), {"usage_card": "answered"})
        self.assertFalse(self.shown())
        self.prefs.share_usage = False  # turning it off later does not bring the card back
        self.assertIsNone(self.install_id())
        self.assertFalse(self.shown())

    def test_the_preference_answers_the_card_either_way(self):
        for share in (True, False):
            with self.subTest(share=share), patch.object(self.prompts, "_saved", {}):
                self.state.joinpath(self.record.PROMPTS_FILE).unlink(missing_ok=True)
                with patch.object(self.usage, "set_sharing"):
                    self.prefs.share_usage = not share
                    self.prefs.share_usage = share
                self.assertEqual(self.saved(), {"usage_card": "answered"})

    def test_an_answer_survives_a_restart_and_a_failed_write(self):
        self.prompts.connected()
        self.answer("DECLINE")
        self.prompts._saved = {}
        self.prompts.load()
        self.assertFalse(self.shown())
        self.state.joinpath(self.record.PROMPTS_FILE).unlink()
        self.prompts.load()
        self.assertTrue(self.shown())
        with patch.object(self.record, "update", side_effect=PermissionError):
            self.answer("DECLINE")
        self.assertFalse(self.shown())  # kept for this session
        self.assertIsNone(self.saved())

    def test_the_card_sits_between_the_account_strip_and_the_lane_tabs(self):
        panels = submodule("blender.panels")
        self.prompts.connected()
        layout = Mock()
        with (
            online_access(True),
            patch.object(panels, "draw_account_strip", return_value=True) as strip,
            patch.object(panels, "draw_enum_tabs") as tabs,
            patch.object(self.runtime.state, "catalog_loaded", False),
            patch.object(self.record, "update") as update,
        ):
            owner = Mock()
            owner.attach_mock(strip, "strip")
            owner.attach_mock(layout.box, "box")
            owner.attach_mock(tabs, "tabs")
            panels.SCENARIO_PT_main.draw(SimpleNamespace(layout=layout), bpy.context)
        update.assert_not_called()  # drawing writes nothing
        self.assertEqual(
            [name for name, *_ in owner.mock_calls if name in ("strip", "box", "tabs")],
            ["strip", "box", "tabs"],
        )
        box = layout.box.return_value
        box.label.assert_any_call(text=self.prompts.USAGE_TITLE, icon="FUND")
        body = " ".join(
            entry.kwargs["text"] for entry in box.label.call_args_list if "icon" not in entry.kwargs
        )
        self.assertEqual(body, self.prompts.USAGE_TEXT)
        row = box.row.return_value
        self.assertEqual(
            row.operator.call_args_list,
            [
                call("scenario.usage_card", text="Share"),
                call("scenario.usage_card", text="No thanks"),
                call("scenario.open_url", text="Details"),
            ],
        )
        self.assertEqual(row.operator.return_value.url, self.prompts.DETAILS_URL)

    def test_nothing_drawn_once_answered(self):
        self.prompts.connected()
        self.answer("DECLINE")
        layout = Mock()
        with online_access(True):
            self.prompts.draw_usage_card(layout, bpy.context)
        layout.box.assert_not_called()
