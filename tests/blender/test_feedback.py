# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Send feedback in the installed extension: dialog, refusals, outcomes and online access.

A fake transport replaces the relay POST; nothing leaves the process. Background Blender
has no pump, so the operator waits for its worker and applies the outcome itself; the
dialog's invoke and draw are called directly, as Blender would.
"""

import pathlib
import tempfile
import threading
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


class Stalled(Transport):
    """The first send hangs, as name resolution can past urllib's timeout, until released."""

    def __init__(self):
        super().__init__()
        self.release, self.stalled = threading.Event(), None

    def __call__(self, url, payload, timeout):
        if self.stalled is None:
            self.stalled = threading.current_thread()
            self.release.wait(10)
            return 202
        return super().__call__(url, payload, timeout)


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
            ("_submission", None),
            ("_status", None),
            ("_worker", None),
            ("_started", 0.0),
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
        # Never logged as a Python call in the Info editor, nor repeated without the dialog.
        self.assertFalse({"REGISTER", "UNDO"} & set(operator.bl_options), operator.bl_options)
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
        first = self.sent()
        self.assertNotIn("message", first)
        self.assertEqual(self.send(message="Only words"), {"FINISHED"})
        self.assertNotIn("rating", self.sent())
        # The same text sent again after a success is a new response.
        self.assertEqual(self.send(rating="1"), {"FINISHED"})
        self.assertNotEqual(self.sent()["submission_id"], first["submission_id"])

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

    def test_a_failed_send_keeps_the_text_and_its_submission_for_another_try(self):
        fields = {"rating": "2", "message": "It crashed", "email": "me@example.com"}
        submissions = set()
        for answer, outcome in (
            (refusal(503), self.core.UNAVAILABLE),
            (refusal(429), self.core.RATE_LIMITED),
            (refusal(400), self.core.FAILED),
            (refusal(502), self.core.UNCONFIRMED),
            (urllib.error.URLError("unreachable"), self.core.UNREACHABLE),
            (TimeoutError("timed out"), self.core.NO_ANSWER),
            (ConnectionResetError("reset"), self.core.NO_ANSWER),
        ):
            with self.subTest(outcome=outcome.text):
                self.transport.answer = answer
                with self.assertLogs("scenario", level="DEBUG") as logs:
                    self.assertEqual(self.send(**fields), {"FINISHED"})
                submissions.add(self.sent()["submission_id"])
                self.assertEqual(self.feedback.draft(), fields)
                self.assertEqual(self.feedback.status(), (outcome.text, "ERROR"))
                self.assertEqual(self.feedback.failure(), outcome.text)
                self.assertEqual(self.runtime.message_visible(), outcome.text)
                for private in ("It crashed", "me@example.com"):
                    self.assertNotIn(private, "\n".join(logs.output))
        # Every retry of the unchanged text is the same response, so PostHog groups any
        # duplicate an uncertain failure left behind.
        self.assertEqual(len(submissions), 1)
        self.assertIn("may not have been sent", self.core.NO_ANSWER.text)
        self.assertIn("may not have been sent", self.core.UNCONFIRMED.text)
        # Retrying the kept text succeeds with the same submission and clears it.
        self.transport.answer = 202
        self.assertEqual(self.send(**self.feedback.draft()), {"FINISHED"})
        retried = self.sent()
        self.assertEqual(
            (retried["message"], retried["submission_id"]), ("It crashed", *submissions)
        )
        self.assertEqual(self.feedback.draft(), self.feedback.EMPTY)
        self.assertIsNone(self.feedback._submission)
        self.assertIsNone(self.feedback.failure())

    def test_edited_text_is_a_new_submission(self):
        self.transport.answer = TimeoutError("timed out")
        self.send(rating="3", message="First words")
        first = self.sent()["submission_id"]
        self.send(rating="3", message="First words")
        self.assertEqual(self.sent()["submission_id"], first)
        self.send(rating="3", message="Other words")
        self.assertNotEqual(self.sent()["submission_id"], first)
        # Any edit is a new response, even one refused before sending; repeating it is not.
        kept = self.feedback._submission
        self.assertEqual(self.send(rating="3", message="Other words", email="nope"), {"CANCELLED"})
        edited = self.feedback._submission
        self.assertNotEqual(edited, kept)
        self.send(rating="3", message="Other words", email="nope")
        self.assertEqual(self.feedback._submission, edited)
        self.assertEqual(self.transport.calls, [])

    def test_the_pump_applies_an_outcome_once(self):
        fields = {"rating": "4", "message": "Pumped", "email": ""}
        self.feedback._draft = dict(fields)
        payload = self.core.build(4, "Pumped", submission_id="0" * 32)
        self.feedback._submission = payload["submission_id"]
        worker = self.feedback.start(payload)
        self.assertTrue(self.feedback.sending())
        worker.join(5)
        self.assertTrue(self.feedback.process())
        self.assertFalse(self.feedback.process())
        self.assertEqual(self.sent(), payload)
        self.assertEqual(self.feedback.status(), (self.core.SENT.text, "CHECKMARK"))
        self.assertEqual(self.feedback.draft(), self.feedback.EMPTY)
        # Text edited while a send was in flight is not cleared by its success.
        edited = {**fields, "message": "Edited meanwhile"}
        self.feedback._submission = payload["submission_id"]
        worker = self.feedback.start(payload)
        self.feedback._draft, self.feedback._submission = dict(edited), "1" * 32
        worker.join(5)
        self.assertTrue(self.feedback.process())
        self.sent()
        self.assertEqual(self.feedback.draft(), edited)

    def test_a_send_that_never_ends_is_given_up_and_its_late_outcome_ignored(self):
        stalled = self.transport = Stalled()
        self.feedback._send = stalled
        self.addCleanup(stalled.release.set)
        fields = {"rating": "5", "message": "Hung", "email": ""}
        with patch.object(self.feedback, "ABANDON_AFTER", 0.2):
            self.assertEqual(self.send(**fields), {"FINISHED"})
            # Background Blender waited ABANDON_AFTER, then gave the send up as unanswered.
            self.assertTrue(stalled.stalled.is_alive())
            self.assertFalse(self.feedback.sending())
            self.assertEqual(self.feedback.status(), (self.core.NO_ANSWER.text, "ERROR"))
            self.assertEqual(self.feedback.draft(), fields)
            with online_access(True):
                self.assertTrue(self.operator.poll(bpy.context))
            submission = self.feedback._submission
            self.assertEqual(self.send(**fields), {"FINISHED"})
        self.assertEqual(self.sent()["submission_id"], submission)
        self.assertEqual(self.feedback.status(), (self.core.SENT.text, "CHECKMARK"))
        stalled.release.set()
        stalled.stalled.join(5)
        self.assertFalse(self.feedback.process())
        self.assertEqual(self.feedback.status(), (self.core.SENT.text, "CHECKMARK"))
        # On the pump's clock: a send older than ABANDON_AFTER no longer blocks a new one.
        self.feedback._worker, self.feedback._started = object(), self.feedback._clock()
        later = self.feedback._started + self.feedback.ABANDON_AFTER
        with online_access(True):
            self.assertFalse(self.operator.poll(bpy.context))
            with patch.object(self.feedback, "_clock", return_value=later):
                self.assertTrue(self.operator.poll(bpy.context))
                self.assertTrue(self.feedback.process())
                self.assertIsNone(self.feedback._worker)
                self.assertEqual(self.feedback.status(), (self.core.NO_ANSWER.text, "ERROR"))

    def test_an_outcome_is_shown_only_while_it_is_current(self):
        self.send(rating="4")
        self.sent()
        self.transport.answer = refusal(502)
        self.send(rating="2")
        self.sent()
        self.assertEqual(self.feedback.failure(), self.core.UNCONFIRMED.text)
        later = self.feedback._clock() + self.runtime.MESSAGE_TTL + 1
        with patch.object(self.feedback, "_clock", return_value=later):
            self.assertIsNone(self.feedback.status())
            self.assertIsNone(self.feedback.failure())
            _, labels = self.drawn(rating="2")
            self.assertFalse([label for label in labels if label.get("icon") == "ERROR"])
        self.assertEqual(self.feedback.draft()["rating"], "2")  # the text itself stays

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
        labels += [call.kwargs for call in layout.column.return_value.label.call_args_list]
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
        for line in self.feedback.NOTE:
            self.assertIn({"text": line}, labels)
        self.assertEqual(
            " ".join(self.feedback.NOTE),
            "Sent with your extension and Blender versions and system type, "
            "plus your install ID while usage data is shared",
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
        self.feedback._status = (self.core.UNREACHABLE.text, False, self.feedback._clock())
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
                self.feedback._status = status and (*status, self.feedback._clock())
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
