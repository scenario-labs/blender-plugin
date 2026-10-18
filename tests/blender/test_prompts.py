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
from unittest.mock import MagicMock, Mock, call, patch

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


class FeedbackPromptTests(unittest.TestCase):
    NOW = 1_800_000_000.0

    def setUp(self):
        self.prompts = submodule("blender.prompts")
        self.record = submodule("core.telemetry.prompts")
        self.usage = submodule("blender.usage")
        self.runtime = submodule("blender.runtime")
        self.feedback = submodule("blender.feedback")
        self.panels = submodule("blender.panels")
        self.prefs = bpy.context.preferences.addons[addon_name()].preferences
        self.assertFalse(self.prefs.share_usage)
        directory = tempfile.TemporaryDirectory(prefix="scenario-test-prompts-")
        self.addCleanup(directory.cleanup)
        self.state = pathlib.Path(directory.name)
        self.opened = Mock()
        self.jobs = SimpleNamespace(views={})
        for target, name, value in (
            (self.usage, "state_dir", Mock(return_value=self.state)),
            (self.prompts, "_saved", {"usage_card": "answered"}),
            (self.prompts, "_watched", set()),
            (self.prompts, "_clock", lambda: self.NOW),
            (self.prompts, "_open_feedback", self.opened),
            (self.feedback, "_draft", dict(self.feedback.EMPTY)),
            (self.feedback, "_worker", None),
            (self.feedback, "_status", None),
            (self.runtime.state, "model_jobs", self.jobs),
            (self.runtime.state, "last_message", ""),
        ):
            patcher = patch.object(target, name, value)
            patcher.start()
            self.addCleanup(patcher.stop)

    def saved(self):
        return self.record.read(self.state)

    def answer(self, answer):
        operator = SimpleNamespace(answer=answer, report=Mock())
        with online_access(True):
            return bpy.types.SCENARIO_OT_feedback_prompt.execute(operator, bpy.context)

    def report(self, error):
        operator = SimpleNamespace(error=error, report=Mock())
        with online_access(True):
            return bpy.types.SCENARIO_OT_report_error.execute(operator, bpy.context)

    def link(self, layout=None):
        layout = layout or Mock()
        with online_access(True):
            self.prompts.draw_error_link(layout, "Could not load models: 503")
        return layout

    def rated(self):
        self.prompts._saved = {**self.prompts._saved, "generations": self.record.RATING_AFTER}

    def test_registered_internal_and_never_recorded_as_usage(self):
        for operator in (
            bpy.types.SCENARIO_OT_report_error,
            bpy.types.SCENARIO_OT_feedback_prompt,
        ):
            with self.subTest(operator.bl_idname):
                self.assertEqual(operator.bl_options, {"INTERNAL"})
                self.assertIn(operator.bl_idname, self.usage.EXCLUDED_OPERATORS)
                self.assertNotIn(operator, self.usage._instrumented)
        description = bpy.types.SCENARIO_OT_feedback_prompt.description
        self.assertEqual(
            description(bpy.context, SimpleNamespace(answer="HIDE")), "Hide these links for a week"
        )

    def test_the_error_link_sits_under_each_error(self):
        records = submodule("core.jobs.records")
        generation = submodule("blender.generation")
        failed = records.JobRecord("failed", "model", "image", "m", {}, status="failed")
        failed.error = "Scenario rejected the job"
        lane_state = SimpleNamespace(
            model_id="m", estimate_state="IDLE", estimate_error="", estimate_key="", trained=()
        )
        cases = (
            (
                "catalog",
                lambda layout: self.panels.draw_loading(layout),
                (self.runtime.state, "catalog_error", "Could not load models: 503"),
                "Could not load models: 503",
            ),
            (
                "model",
                lambda layout: self.panels.draw_schema_status(layout, lane_state, "image"),
                (self.runtime.state, "model_errors", {"m": "The model could not be read"}),
                "The model could not be read",
            ),
            (
                "generate",
                lambda layout: self.panels.draw_generate_row(layout, lane_state, "image"),
                (generation, "lane_error", Mock(return_value="Submission failed")),
                "Submission failed",
            ),
            (
                "result",
                lambda layout: self.panels.draw_result(layout, failed),
                (self.runtime.state, "catalog_error", ""),
                "Scenario rejected the job",
            ),
        )
        for name, draw, state, error in cases:
            with (
                self.subTest(name),
                online_access(True),
                patch.object(*state),
                patch.object(generation, "is_loading", return_value=False),
                patch.object(self.prompts, "draw_error_link") as link,
            ):
                draw(MagicMock())
                self.assertEqual(link.call_args.args[1], error)
        with patch.object(self.prompts, "draw_error_link") as link:
            self.panels.draw_result(MagicMock(), failed, collapsible=False)
        link.assert_not_called()  # the composer's job card stays compact

    def test_the_link_follows_a_failed_test_connection(self):
        layout = MagicMock()
        with (
            online_access(True),
            patch.object(self.panels, "draw_account_strip", return_value=True),
            patch.object(self.panels, "draw_enum_tabs"),
            patch.object(self.runtime.state, "connection_status", "error"),
            patch.object(self.runtime.state, "account_label", "Connection failed: 401"),
            patch.object(self.runtime.state, "catalog_loaded", False),
            patch.object(self.prompts, "draw_error_link") as link,
        ):
            self.panels.SCENARIO_PT_main.draw(SimpleNamespace(layout=layout), bpy.context)
        self.assertEqual(link.call_args_list[0].args[1], "Connection failed: 401")

    def test_the_link_opens_feedback_and_hides_for_a_week(self):
        layout = self.link()
        row = layout.row.return_value
        self.assertEqual(
            row.operator.call_args_list,
            [
                call("scenario.report_error", text="Tell us what went wrong", icon="HEART"),
                call("scenario.feedback_prompt", text="", icon="X"),
            ],
        )
        offline = Mock()
        self.prompts.draw_error_link(offline, "Could not load models: 503")
        offline.row.assert_not_called()  # Allow Online Access is off
        self.assertEqual(self.answer("HIDE"), {"FINISHED"})
        self.opened.assert_not_called()
        week = self.NOW + self.record.QUIET_PERIOD
        self.assertEqual(self.saved(), {"quiet_until": week})
        self.link().row.assert_not_called()
        with patch.object(self.prompts, "_clock", lambda: week):
            self.link().row.assert_called_once()

    def test_reporting_prefills_the_stripped_error_unless_text_is_kept(self):
        error = "Could not read '/home/artist/a.png' for asset_AbCdEf123456"
        self.assertEqual(self.report(error), {"FINISHED"})
        self.opened.assert_called_once_with(message="Error: Could not read <name> for <id>")
        self.assertEqual(self.saved()["quiet_until"], self.NOW + self.record.QUIET_PERIOD)
        self.opened.reset_mock()
        self.feedback._draft = {**self.feedback.EMPTY, "message": "My own words"}
        self.report(error)
        self.opened.assert_called_once_with()

    def test_reporting_needs_online_access_and_no_send_in_flight(self):
        poll = bpy.types.SCENARIO_OT_report_error.poll
        self.assertFalse(poll(bpy.context))
        with online_access(True):
            self.assertTrue(poll(bpy.context))
            with patch.object(self.feedback, "sending", return_value=True):
                self.assertFalse(poll(bpy.context))
                operator = SimpleNamespace(answer="RATE", report=Mock())
                execute = bpy.types.SCENARIO_OT_feedback_prompt.execute
                self.assertEqual(execute(operator, bpy.context), {"CANCELLED"})
                self.assertEqual(
                    execute(SimpleNamespace(answer="DECLINE"), bpy.context), {"FINISHED"}
                )
        self.opened.assert_not_called()

    def test_the_rating_card_comes_after_enough_generations(self):
        with online_access(True):
            self.assertFalse(self.prompts.rating_card_shown())
            self.rated()
            self.assertTrue(self.prompts.rating_card_shown())
            with patch.object(self.prompts, "_saved", {"generations": 10}):
                self.assertFalse(self.prompts.rating_card_shown())  # usage card unanswered
                with (
                    patch.object(self.usage, "set_sharing"),
                    patch.object(self.prompts, "sharing_answered"),
                ):
                    self.prefs.share_usage = True
                    self.assertTrue(self.prompts.rating_card_shown())
                    self.prefs.share_usage = False
            quieted = {**self.prompts._saved, "quiet_until": self.NOW + 1}
            with patch.object(self.prompts, "_saved", quieted):
                self.assertFalse(self.prompts.rating_card_shown())  # in a quiet week
        self.assertFalse(self.prompts.rating_card_shown())  # offline
        layout = MagicMock()
        with online_access(True), patch.object(self.runtime.state, "jobs_view", []):
            self.panels.SCENARIO_PT_generations.draw(SimpleNamespace(layout=layout), bpy.context)
        box = layout.box.return_value
        box.label.assert_any_call(text=self.prompts.RATING_TITLE, icon="HEART")
        self.assertEqual(
            box.row.return_value.operator.call_args_list,
            [
                call("scenario.feedback_prompt", text="Send feedback..."),
                call("scenario.feedback_prompt", text="No thanks"),
            ],
        )

    def test_each_rating_answer_ends_the_card_and_quiets_the_links(self):
        for answer, opened in (("RATE", True), ("DECLINE", False)):
            with self.subTest(answer):
                self.prompts._saved = {"usage_card": "answered"}
                self.state.joinpath(self.record.PROMPTS_FILE).unlink(missing_ok=True)
                self.rated()
                self.opened.reset_mock()
                with patch.object(submodule("core.telemetry.relay"), "post_json") as post:
                    self.assertEqual(self.answer(answer), {"FINISHED"})
                post.assert_not_called()
                self.assertEqual(self.opened.called, opened)
                self.assertEqual(self.saved()["rating_prompt"], "answered")
                with (
                    patch.object(self.prompts, "_clock", lambda: self.NOW * 2),
                    online_access(True),
                ):
                    self.assertFalse(self.prompts.rating_card_shown())  # never again
                self.link().row.assert_not_called()

    def test_a_sent_feedback_retires_the_rating_card(self):
        core = submodule("core.telemetry.feedback")
        self.feedback._apply(core.UNREACHABLE, None)
        self.assertNotIn("rating_prompt", self.prompts._saved)
        self.feedback._apply(core.SENT, None)
        self.assertEqual(self.saved()["rating_prompt"], "answered")

    def test_generations_started_with_generate_are_counted_once_saved(self):
        view = SimpleNamespace(meta={"saved_state": "remote"})
        failed = SimpleNamespace(meta={"saved_state": "remote"})
        self.jobs.views.update(done=view, failed=failed, agent=SimpleNamespace(meta={}))
        self.prompts.watch_generation("done")
        self.prompts.watch_generation("failed")
        self.assertFalse(self.prompts.tick())
        self.assertNotIn("generations", self.saved())
        view.meta["saved_state"], failed.meta["saved_state"] = "applied", "failed"
        self.jobs.views["agent"].meta["saved_state"] = "ready"  # not watched: not counted
        self.assertFalse(self.prompts.tick())
        self.assertEqual(self.saved()["generations"], 1)
        self.assertEqual(self.prompts._watched, set())
        self.prompts.watch_generation("gone")  # its view retired with the connection
        self.prompts.tick()
        self.assertEqual(self.saved()["generations"], 1)
        self.prompts._saved["generations"] = self.record.RATING_AFTER - 1
        self.record.update(self.state, generations=self.record.RATING_AFTER - 1)
        self.prompts.watch_generation("done")
        self.assertTrue(self.prompts.tick())  # the card appears: redraw
        self.prompts.watch_generation("other")
        self.assertEqual(self.prompts._watched, set())  # nothing left to count

    def test_generate_watches_its_job(self):
        generation = submodule("blender.generation")
        rec = SimpleNamespace(local_id="submitted", meta={}, model_id="m")
        operator = SimpleNamespace(lane="image", report=Mock())
        with patch.object(generation, "submit_generation", return_value=rec):
            result = bpy.types.SCENARIO_OT_generate.execute(operator, bpy.context)
        self.assertEqual(result, {"FINISHED"})
        self.assertEqual(self.prompts._watched, {"submitted"})
