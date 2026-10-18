# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Send feedback in the installed extension: dialog, refusals, outcomes and online access.

A fake transport replaces the relay POST; nothing leaves the process. Background Blender
has no pump, so the operator waits for its worker and applies the outcome itself; the
dialog's invoke and draw are called directly, as Blender would.
"""

import pathlib
import tempfile
import unittest
import urllib.error
from types import SimpleNamespace
from unittest.mock import ANY, Mock, patch

import bpy
from helpers import addon, addon_name, online_access, submodule

HEX = r"^[0-9a-f]{32}$"


class Transport:
    def __init__(self, answer=202):
        self.answer, self.calls = answer, []

    def __call__(self, url, payload, timeout):
        self.calls.append((url, payload, timeout))
        if isinstance(self.answer, BaseException):
            raise self.answer
        return self.answer


def refusal(status):
    return urllib.error.HTTPError("https://relay.invalid/feedback", status, "refused", {}, None)


class FeedbackTests(unittest.TestCase):
    def setUp(self):
        self.feedback = submodule("blender.feedback")
        self.core = submodule("core.telemetry.feedback")
        self.usage = submodule("blender.usage")
        self.runtime = submodule("blender.runtime")
        self.operator = bpy.types.SCENARIO_OT_send_feedback
        self.prefs = bpy.context.preferences.addons[addon_name()].preferences
        self.assertFalse(self.prefs.share_usage)
        self.assertFalse(bpy.app.online_access)
        self.transport = Transport()
        for name, value in (
            ("_send", self.transport),
            ("_draft", dict(self.feedback.EMPTY)),
            ("_status", None),
            ("_worker", None),
        ):
            patcher = patch.object(self.feedback, name, value)
            patcher.start()
            self.addCleanup(patcher.stop)
        message = patch.object(self.runtime.state, "last_message", "")
        message.start()
        self.addCleanup(message.stop)

    def send(self, **fields):
        with online_access(True):
            return bpy.ops.scenario.send_feedback(**fields)

    def sent(self):
        self.assertEqual(len(self.transport.calls), 1)
        url, payload, timeout = self.transport.calls.pop()
        self.assertEqual((url, timeout), (self.core.FEEDBACK_URL, self.core.TIMEOUT))
        return payload

    def test_registered_with_its_dialog_fields_and_icons(self):
        operator = self.operator
        self.assertEqual(operator.bl_label, "Send feedback")
        self.assertIn("nothing is sent until you press Send", operator.bl_description)
        properties = bpy.ops.scenario.send_feedback.get_rna_type().properties
        rating = properties["rating"]
        self.assertEqual(rating.default, "NONE")
        self.assertEqual(
            [item.identifier for item in rating.enum_items], ["NONE", "1", "2", "3", "4", "5"]
        )
        self.assertEqual(rating.enum_items["NONE"].name, "Not rated")
        for name in ("rating", "message", "email"):
            self.assertTrue(properties[name].is_skip_save, name)
        icons = bpy.types.UILayout.bl_rna.functions["label"].parameters["icon"].enum_items
        for icon in ("HEART", "FUND", "SORTTIME", "CHECKMARK", "ERROR", "INFO"):
            self.assertIn(icon, icons)

    def test_valid_feedback_is_sent_once_and_its_text_cleared(self):
        self.assertEqual(
            self.send(rating="4", message="  Works well\n", email=" me@example.com "),
            {"FINISHED"},
        )
        payload = self.sent()
        self.assertRegex(payload.pop("submission_id"), HEX)
        context = payload.pop("context")
        self.assertEqual(payload, {"rating": 4, "message": "Works well", "email": "me@example.com"})
        self.assertEqual(context["blender_version"], self.usage.blender_version())
        self.assertEqual(context["extension_version"], addon().__version__)
        self.assertIn(context["os"], ("macos", "windows", "linux", "other"))
        self.assertEqual(self.feedback.draft(), self.feedback.EMPTY)
        self.assertFalse(self.feedback.sending())
        self.assertEqual(self.feedback.status(), (self.core.SENT.text, "CHECKMARK"))
        self.assertIsNone(self.feedback.failure())
        self.assertEqual(self.runtime.message_visible(), self.core.SENT.text)
        # A rating alone, or a message alone, is enough.
        self.assertEqual(self.send(rating="1"), {"FINISHED"})
        self.assertNotIn("message", self.sent())
        self.assertEqual(self.send(message="Only words"), {"FINISHED"})
        self.assertNotIn("rating", self.sent())

    def test_the_install_id_is_sent_only_while_usage_sharing_is_on(self):
        directory = tempfile.TemporaryDirectory(prefix="scenario-test-feedback-")
        self.addCleanup(directory.cleanup)
        state = pathlib.Path(directory.name)
        state_dir = patch.object(self.usage, "state_dir", return_value=state)
        state_dir.start()
        self.addCleanup(state_dir.stop)
        self.addCleanup(setattr, self.prefs, "share_usage", False)
        self.send(rating="5")
        self.assertNotIn("install_id", self.sent())
        self.prefs.share_usage = True
        install_id = submodule("core.telemetry.usage").read_install_id(state)
        self.assertRegex(install_id, HEX)
        self.send(rating="5")
        self.assertEqual(self.sent()["install_id"], install_id)
        # Switched off in another Blender whose preferences were not saved: the ID file,
        # the opt-in record, is gone while this preference still reads on.
        events = submodule("core.telemetry.usage")
        events.delete_install_id(state)
        self.assertTrue(self.prefs.share_usage)
        self.send(rating="5")
        self.assertNotIn("install_id", self.sent())
        events.create_install_id(state)
        self.prefs.share_usage = False
        self.send(rating="5")
        self.assertNotIn("install_id", self.sent())

    def test_a_refused_entry_keeps_the_text_and_sends_nothing(self):
        for fields, reason in (
            ({}, self.core.NEEDS_CONTENT),
            ({"message": " \n\t "}, self.core.NEEDS_CONTENT),
            ({"rating": "3", "email": "not an address"}, self.core.EMAIL_INVALID),
            ({"message": "x" * 5001}, self.core.MESSAGE_TOO_LONG),
        ):
            with self.subTest(fields=fields):
                self.assertEqual(self.send(**fields), {"CANCELLED"})
                self.assertEqual(self.transport.calls, [])
                self.assertEqual(self.feedback.draft(), {**self.feedback.EMPTY, **fields})
                self.assertIsNone(self.feedback.status())
                self.assertEqual(
                    self.core.problem(
                        self.feedback.rating_value(fields.get("rating", "NONE")),
                        fields.get("message", ""),
                        fields.get("email", ""),
                    ),
                    reason,
                )

    def test_a_failed_send_keeps_the_text_for_another_try(self):
        fields = {"rating": "2", "message": "It crashed", "email": "me@example.com"}
        for answer, outcome in (
            (refusal(503), self.core.UNAVAILABLE),
            (refusal(429), self.core.RATE_LIMITED),
            (refusal(400), self.core.FAILED),
            (refusal(502), self.core.FAILED),
            (urllib.error.URLError("unreachable"), self.core.UNREACHABLE),
            (TimeoutError("timed out"), self.core.UNREACHABLE),
        ):
            with self.subTest(outcome=outcome.text):
                self.transport.answer = answer
                with self.assertLogs("scenario", level="DEBUG") as logs:
                    self.assertEqual(self.send(**fields), {"FINISHED"})
                self.sent()
                self.assertEqual(self.feedback.draft(), fields)
                self.assertEqual(self.feedback.status(), (outcome.text, "ERROR"))
                self.assertEqual(self.feedback.failure(), outcome.text)
                self.assertEqual(self.runtime.message_visible(), outcome.text)
                for private in ("It crashed", "me@example.com"):
                    self.assertNotIn(private, "\n".join(logs.output))
        # Retrying the kept text succeeds and clears it.
        self.transport.answer = 202
        self.assertEqual(self.send(**self.feedback.draft()), {"FINISHED"})
        self.assertEqual(self.sent()["message"], "It crashed")
        self.assertEqual(self.feedback.draft(), self.feedback.EMPTY)
        self.assertIsNone(self.feedback.failure())

    def test_nothing_is_sent_while_online_access_is_off(self):
        self.assertFalse(self.operator.poll(bpy.context))
        with self.assertRaises(RuntimeError) as refused:
            bpy.ops.scenario.send_feedback(rating="5", message="offline")
        self.assertIn(self.feedback.OFFLINE, str(refused.exception))
        # Access can change between poll and execute: execute checks again.
        operator = SimpleNamespace(rating="5", message="offline", email="", report=Mock())
        self.assertEqual(self.operator.execute(operator, bpy.context), {"CANCELLED"})
        operator.report.assert_called_once_with(
            {"WARNING"}, "Allow Online Access is off; your feedback was not sent"
        )
        self.assertEqual(self.transport.calls, [])
        self.assertEqual(self.feedback.draft()["message"], "offline")
        with online_access(True):
            self.assertTrue(self.operator.poll(bpy.context))

    def test_one_send_at_a_time(self):
        with patch.object(self.feedback, "_worker", object()), online_access(True):
            self.assertTrue(self.feedback.sending())
            self.assertFalse(self.operator.poll(bpy.context))
            self.assertEqual(self.feedback.status(), (self.feedback.SENDING, "SORTTIME"))
            operator = SimpleNamespace(rating="5", message="again", email="", report=Mock())
            self.assertEqual(self.operator.execute(operator, bpy.context), {"CANCELLED"})
            operator.report.assert_called_once_with({"WARNING"}, self.feedback.BUSY)
        self.assertEqual(self.transport.calls, [])

    def test_the_pump_applies_an_outcome_once(self):
        fields = {"rating": "4", "message": "Pumped", "email": ""}
        self.feedback._draft = dict(fields)
        payload = self.core.build(4, "Pumped", submission_id="0" * 32)
        worker = self.feedback.start(payload, fields)
        self.assertTrue(self.feedback.sending())
        worker.join(5)
        self.assertTrue(self.feedback.process())
        self.assertFalse(self.feedback.process())
        self.assertEqual(self.sent(), payload)
        self.assertEqual(self.feedback.status(), (self.core.SENT.text, "CHECKMARK"))
        self.assertEqual(self.feedback.draft(), self.feedback.EMPTY)
        # Text edited while a send was in flight is not cleared by its success.
        edited = {**fields, "message": "Edited meanwhile"}
        worker = self.feedback.start(payload, fields)
        self.feedback._draft = dict(edited)
        worker.join(5)
        self.assertTrue(self.feedback.process())
        self.sent()
        self.assertEqual(self.feedback.draft(), edited)

    def test_the_dialog_opens_with_the_kept_text_and_send_button(self):
        self.feedback._draft = {"rating": "3", "message": "Kept", "email": "me@example.com"}
        operator = SimpleNamespace(
            rating="NONE",
            message="",
            email="",
            properties=SimpleNamespace(is_property_set=lambda name: name == "rating"),
        )
        window_manager = Mock()
        window_manager.invoke_props_dialog.return_value = {"RUNNING_MODAL"}
        context = SimpleNamespace(window_manager=window_manager)
        self.assertEqual(self.operator.invoke(operator, context, None), {"RUNNING_MODAL"})
        # An explicitly passed rating wins; the rest come from the kept text.
        self.assertEqual(
            (operator.rating, operator.message, operator.email),
            ("NONE", "Kept", "me@example.com"),
        )
        window_manager.invoke_props_dialog.assert_called_once_with(
            operator, width=self.feedback.DIALOG_WIDTH, confirm_text="Send"
        )

    def drawn(self, **fields):
        operator = SimpleNamespace(rating="NONE", message="", email="", layout=Mock())
        for name, value in fields.items():
            setattr(operator, name, value)
        self.operator.draw(operator, bpy.context)
        layout = operator.layout
        labels = [call.kwargs for call in layout.label.call_args_list]
        labels += [call.kwargs for call in layout.row.return_value.label.call_args_list]
        return layout, labels

    def test_the_dialog_draws_its_fields_note_and_reasons(self):
        layout, labels = self.drawn(rating="4", message="Nice")
        layout.prop.assert_any_call(ANY, "message", text="", placeholder="What should we improve?")
        layout.prop.assert_any_call(
            ANY,
            "email",
            text="",
            placeholder="Email, if you would like a reply (optional)",
        )
        self.assertIn({"text": self.feedback.NOTE}, labels)
        self.assertEqual(
            self.feedback.NOTE, "Sent to Scenario with the extension, Blender and OS versions"
        )
        self.assertFalse([label for label in labels if label.get("icon") == "ERROR"])
        self.assertNotIn({"text": self.core.NEEDS_CONTENT, "icon": "INFO"}, labels)
        # Every rating cell, Not rated first, in one segmented row.
        segments = layout.row.return_value
        cells = [
            call.args[2]
            for call in segments.mock_calls
            if call[0].endswith("prop_enum") and call.args[1] == "rating"
        ]
        self.assertEqual(cells, ["NONE", "1", "2", "3", "4", "5"])
        _, labels = self.drawn()
        self.assertIn({"text": self.core.NEEDS_CONTENT, "icon": "INFO"}, labels)
        _, labels = self.drawn(rating="2", email="nope")
        self.assertIn({"text": self.core.EMAIL_INVALID, "icon": "INFO"}, labels)
        self.feedback._status = (self.core.UNREACHABLE.text, False)
        _, labels = self.drawn(message="Kept")
        self.assertIn({"text": self.core.UNREACHABLE.text, "icon": "ERROR"}, labels)

    def test_entry_points_in_the_sidebar_and_the_preferences(self):
        panels = submodule("blender.panels")
        prefs_module = submodule("prefs")
        with online_access(True):
            for valid in (True, False):
                with (
                    self.subTest(credentials=valid),
                    patch.object(
                        self.runtime, "credentials", return_value=SimpleNamespace(valid=valid)
                    ),
                ):
                    layout = Mock()
                    self.assertEqual(panels.draw_account_strip(layout, bpy.context), valid)
                    layout.row.return_value.operator.assert_any_call(
                        "scenario.send_feedback", text="", icon="HEART"
                    )
        for online, status in ((True, None), (True, ("Sent", True)), (False, ("Lost", False))):
            with self.subTest(online=online, status=status):
                self.feedback._status = status
                owner = SimpleNamespace(
                    layout=Mock(),
                    credential_source="PREFERENCES",
                    composer_enabled=True,
                    share_usage=False,
                )
                with (
                    patch.object(prefs_module.updates, "draw"),
                    patch.object(self.runtime, "online", return_value=online),
                ):
                    prefs_module.ScenarioPreferences.draw(owner, bpy.context)
                box = owner.layout.box.return_value
                box.label.assert_any_call(text="Usage data and feedback", icon="FUND")
                box.operator.assert_any_call(
                    "scenario.send_feedback", text="Send feedback...", icon="HEART"
                )
                drawn = [call.kwargs for call in box.label.call_args_list]
                if status is not None:
                    icon = "CHECKMARK" if status[1] else "ERROR"
                    self.assertIn({"text": status[0], "icon": icon}, drawn)
                notice = {
                    "text": "Nothing is sent while Allow Online Access is off",
                    "icon": "ERROR",
                }
                self.assertEqual(notice in drawn, not online)

    def test_the_sidebar_shows_the_outcome_without_credentials(self):
        panels = submodule("blender.panels")
        self.runtime.set_message(self.core.SENT.text)
        layout = Mock()
        with patch.object(panels, "draw_account_strip", return_value=False):
            panels.SCENARIO_PT_main.draw(SimpleNamespace(layout=layout), bpy.context)
        layout.label.assert_called_once_with(text=self.core.SENT.text)
