# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Opt-in usage data in the installed extension: preference, gating and operator counting.

A fake transport replaces the relay POST; nothing leaves the process. Background Blender
calls an operator's execute through bpy.ops but never its invoke (there is no event), so
invoke and modal paths call the installed wrappers directly, as Blender would.
"""

import pathlib
import tempfile
import time
import types
import unittest
from concurrent.futures import ThreadPoolExecutor
from types import SimpleNamespace
from unittest.mock import Mock, patch

import bpy
from helpers import addon_name, online_access, submodule


class Transport:
    def __init__(self):
        self.payloads = []

    def __call__(self, url, payload, timeout):
        self.payloads.append(payload)
        return 202


class SCENARIO_OT_usage_probe(bpy.types.Operator):
    bl_idname = "scenario.usage_probe"
    bl_label = "Usage probe"
    bl_options = {"INTERNAL"}

    mode: bpy.props.StringProperty(default="finish")

    def invoke(self, context, event):
        if self.mode == "dialog":
            return {"RUNNING_MODAL"}  # what invoke_props_dialog returns while it is open
        return self.execute(context)

    def execute(self, context):
        if self.mode == "fail":
            raise ValueError("probe failure")
        if self.mode == "nested":
            bpy.ops.scenario.usage_probe(mode="finish")
        return {"CANCELLED"} if self.mode == "cancel" else {"FINISHED"}

    def modal(self, context, event):
        return {"FINISHED"} if event.type == "RET" else {"RUNNING_MODAL"}


class UsageTests(unittest.TestCase):
    def setUp(self):
        self.usage = submodule("blender.usage")
        self.events = submodule("core.telemetry.usage")
        self.prefs = bpy.context.preferences.addons[addon_name()].preferences
        self.assertFalse(self.prefs.share_usage)
        self.assertIsNone(self.usage.recorder())
        directory = tempfile.TemporaryDirectory(prefix="scenario-test-usage-")
        self.addCleanup(directory.cleanup)
        self.state = pathlib.Path(directory.name)
        state_dir = patch.object(self.usage, "state_dir", return_value=self.state)
        state_dir.start()
        self.addCleanup(state_dir.stop)
        self.transport = Transport()
        self.usage.activate(send=self.transport)
        self.addCleanup(self.usage.deactivate)
        self.addCleanup(setattr, self.prefs, "share_usage", False)
        bpy.utils.register_class(SCENARIO_OT_usage_probe)
        self.addCleanup(bpy.utils.unregister_class, SCENARIO_OT_usage_probe)
        self.assertTrue(self.usage.instrument(SCENARIO_OT_usage_probe))
        self.addCleanup(self.usage.restore, SCENARIO_OT_usage_probe)

    def sent(self):
        recorder = self.usage.recorder()
        self.assertIsNotNone(recorder)
        recorder.flush()
        events = [
            (event["event"], event["properties"])
            for payload in self.transport.payloads
            for event in payload["events"]
        ]
        self.transport.payloads.clear()
        return events

    def share(self):
        self.prefs.share_usage = True
        self.usage.follow_online_access()
        self.assertEqual(self.sent(), [("extension_started", {})])

    def probe(self, mode, method="execute", event_type="NONE"):
        operator = SimpleNamespace(mode=mode)
        operator.execute = types.MethodType(SCENARIO_OT_usage_probe.execute, operator)
        if method == "execute":
            return SCENARIO_OT_usage_probe.execute(operator, bpy.context)
        event = SimpleNamespace(type=event_type)
        return getattr(SCENARIO_OT_usage_probe, method)(operator, bpy.context, event)

    def used(self, outcome, **extra):
        return ("operator_used", {"operator": "scenario.usage_probe", "outcome": outcome, **extra})

    def test_preference_is_off_by_default_and_drawn_in_its_own_box(self):
        self.assertFalse(self.prefs.bl_rna.properties["share_usage"].default)
        prefs_module = submodule("prefs")
        for enabled, online in ((False, False), (True, True), (True, False)):
            owner = SimpleNamespace(
                layout=Mock(), credential_source="PREFERENCES", composer_enabled=True
            )
            owner.share_usage = enabled
            runtime = submodule("blender.runtime")
            with (
                patch.object(prefs_module.updates, "draw"),
                patch.object(runtime, "online", return_value=online),
            ):
                prefs_module.ScenarioPreferences.draw(owner, bpy.context)
            box = owner.layout.box.return_value
            box.prop.assert_any_call(owner, "share_usage")
            box.label.assert_any_call(text="Usage data", icon="FUND")
            notice = "Nothing is sent while Allow Online Access is off"
            drawn = [call.kwargs.get("text") for call in box.label.call_args_list]
            self.assertEqual(notice in drawn, enabled and not online)
        self.assertIn(
            "FUND", bpy.types.UILayout.bl_rna.functions["label"].parameters["icon"].enum_items
        )

    def test_turning_sharing_on_and_off_manages_the_install_id_and_sender(self):
        with online_access(True):
            self.prefs.share_usage = True
            install_id = self.events.read_install_id(self.state)
            self.assertRegex(install_id, r"^[0-9a-f]{32}$")
            self.assertEqual(self.usage.recorder().install_id, install_id)
            self.assertEqual(self.sent(), [("extension_started", {})])
            payload_context = self.usage.recorder().context
            self.assertEqual(payload_context["blender_version"], self.usage.blender_version())
            self.assertIn(payload_context["os"], ("macos", "windows", "linux", "other"))
            bpy.ops.scenario.usage_probe()
            self.prefs.share_usage = False
            self.assertIsNone(self.usage.recorder())
            self.assertIsNone(self.events.read_install_id(self.state))
            self.assertEqual(list(self.state.iterdir()), [])
            # The unsent operator event was discarded, not sent on the way out.
            self.assertEqual(self.transport.payloads, [])
            self.prefs.share_usage = True
            self.assertNotEqual(self.events.read_install_id(self.state), install_id)
            self.assertEqual(self.sent(), [("extension_started", {})])

    def test_nothing_is_recorded_or_sent_while_online_access_is_off(self):
        self.assertFalse(bpy.app.online_access)
        self.prefs.share_usage = True
        self.usage.follow_online_access()
        recorder = self.usage.recorder()
        self.assertIsNotNone(recorder)
        bpy.ops.scenario.usage_probe()
        self.assertEqual(recorder.pending(), 0)
        with online_access(True):
            self.usage.follow_online_access()
            # extension_started waited until it could be sent.
            self.assertEqual(self.sent(), [("extension_started", {})])
            bpy.ops.scenario.usage_probe()
        self.usage.follow_online_access()
        self.assertEqual(recorder.pending(), 1)
        self.assertEqual(self.sent(), [])  # the sender rechecks online access before sending

    def test_a_preference_on_without_the_saved_id_shares_nothing(self):
        """The ID file is the opt-in record: another Blender may have switched sharing off."""
        with online_access(True):
            self.share()
            self.usage.deactivate()
            # Off in another Blender whose preferences were not saved: its ID file is gone.
            self.events.delete_install_id(self.state)
            self.usage.activate(send=self.transport)  # as the scenario_blender command does
            self.assertTrue(self.prefs.share_usage)
            self.assertIsNone(self.usage.recorder())
            self.assertIsNone(self.events.read_install_id(self.state))
            bpy.ops.scenario.usage_probe()
            self.usage.tick()
            self.assertEqual(self.transport.payloads, [])

    def test_switching_sharing_off_in_another_blender_stops_sending(self):
        with online_access(True):
            self.share()
            bpy.ops.scenario.usage_probe()
            self.events.delete_install_id(self.state)
            self.assertEqual(self.sent(), [])

    def test_the_tick_turns_sharing_off_when_the_preference_changed_silently(self):
        """Revert to Saved Preferences changes the preference without its update callback."""
        runtime = submodule("blender.runtime")
        with online_access(True):
            self.share()
            bpy.ops.scenario.usage_probe()
            reverted = SimpleNamespace(share_usage=False)
            with patch.object(runtime, "prefs", return_value=reverted):
                self.usage.tick()
            self.assertIsNone(self.usage.recorder())
            self.assertIsNone(self.events.read_install_id(self.state))
            self.assertEqual(self.transport.payloads, [])
            # Unavailable preferences decide nothing.
            self.prefs.share_usage = False
            self.prefs.share_usage = True
            with patch.object(runtime, "prefs", return_value=None):
                self.usage.tick()
            self.assertIsNotNone(self.usage.recorder())

    def test_the_pump_mirrors_online_access_first_and_survives_a_usage_failure(self):
        pump = submodule("blender.pump")

        class Stop(Exception):
            pass

        self.usage._online.clear()
        with (
            online_access(True),
            patch.object(pump.generation, "process_catalog_events", side_effect=Stop),
        ):
            with self.assertRaises(Stop):
                pump._process()
            self.assertTrue(self.usage._online.is_set())
            with (
                patch.object(self.usage, "tick", side_effect=RuntimeError("usage")),
                self.assertRaises(Stop),  # the tick went on to its next step
            ):
                pump._process()
        pump._failures.pop("usage", None)

    def test_one_event_per_execute_only_action(self):
        with online_access(True):
            self.share()
            self.assertEqual(bpy.ops.scenario.usage_probe(), {"FINISHED"})
            self.assertEqual(bpy.ops.scenario.usage_probe(mode="cancel"), {"CANCELLED"})
            self.assertEqual(bpy.ops.scenario.usage_probe(mode="nested"), {"FINISHED"})
            self.assertEqual(
                self.sent(),
                [self.used("finished"), self.used("cancelled"), self.used("finished")],
            )

    def test_an_exception_is_recorded_by_class_and_still_raised(self):
        with online_access(True):
            self.share()
            with self.assertRaises(RuntimeError) as raised:
                bpy.ops.scenario.usage_probe(mode="fail")
            self.assertIn("ValueError: probe failure", str(raised.exception))
            with self.assertRaises(ValueError):
                self.probe("fail")
            self.assertEqual(
                self.sent(),
                [self.used("error", error_type="ValueError")] * 2,
            )

    def test_invoke_dialogs_and_modal_handlers_count_once_when_they_end(self):
        with online_access(True):
            self.share()
            # An invoke that runs execute itself is one action.
            self.assertEqual(self.probe("finish", "invoke"), {"FINISHED"})
            self.assertEqual(self.sent(), [self.used("finished")])
            # A props dialog: invoke opens it, Blender calls execute on OK.
            self.assertEqual(self.probe("dialog", "invoke"), {"RUNNING_MODAL"})
            self.assertEqual(self.sent(), [])
            self.assertEqual(self.probe("finish"), {"FINISHED"})
            self.assertEqual(self.sent(), [self.used("finished")])
            # A modal handler counts when it finishes, not on each event.
            self.assertEqual(self.probe("finish", "modal", "MOUSEMOVE"), {"RUNNING_MODAL"})
            self.assertEqual(self.probe("finish", "modal", "MOUSEMOVE"), {"RUNNING_MODAL"})
            self.assertEqual(self.probe("finish", "modal", "RET"), {"FINISHED"})
            self.assertEqual(self.sent(), [self.used("finished")])

    def test_nothing_is_recorded_when_sharing_is_off_or_an_agent_runs_the_operator(self):
        with online_access(True), patch.object(self.usage, "_record_operator") as record:
            self.assertEqual(bpy.ops.scenario.usage_probe(), {"FINISHED"})
            with self.assertRaises(ValueError):
                self.probe("fail")
            record.assert_not_called()
            self.share()
            with submodule("mcp.server")._running_tool():
                bpy.ops.scenario.usage_probe()
            record.assert_not_called()

    def test_the_extension_operators_are_instrumented_except_the_exclusions(self):
        self.assertEqual(self.usage.EXCLUDED_OPERATORS, frozenset({"scenario.composer_modal"}))
        marker = self.usage._ORIGINAL
        names = [name for name in dir(bpy.types) if name.startswith("SCENARIO_OT_")]
        self.assertGreater(len(names), 100)
        for name in names:
            cls = getattr(bpy.types, name)
            if cls is SCENARIO_OT_usage_probe:
                continue
            methods = [
                method
                for name in ("execute", "invoke", "modal")
                if isinstance(method := getattr(cls, name, None), types.FunctionType)
            ]
            with self.subTest(operator=cls.bl_idname):
                self.assertTrue(methods)
                wrapped = [hasattr(method, marker) for method in methods]
                excluded = cls.bl_idname in self.usage.EXCLUDED_OPERATORS
                self.assertEqual(wrapped, [not excluded] * len(methods))
        modal = bpy.types.SCENARIO_OT_composer_modal
        self.assertFalse(hasattr(modal.invoke, marker) or hasattr(modal.modal, marker))
        # Instrumenting is idempotent and restoring puts the class's own methods back.
        self.assertFalse(self.usage.instrument(SCENARIO_OT_usage_probe))
        wrapped = SCENARIO_OT_usage_probe.__dict__["execute"]
        self.usage.restore(SCENARIO_OT_usage_probe)
        self.assertIs(SCENARIO_OT_usage_probe.__dict__["execute"], getattr(wrapped, marker))
        self.assertTrue(self.usage.instrument(SCENARIO_OT_usage_probe))

    def test_every_registered_mcp_tool_name_fits_the_relay_allowlist(self):
        names = submodule("blender.mcp_service").build_registry().names()
        self.assertGreater(len(names), 20)
        for name in names:
            with self.subTest(tool=name):
                properties = {"tool": name, "outcome": "ok", "duration_ms": 0}
                self.assertEqual(
                    self.events.sanitize_event("mcp_tool_called", properties), properties
                )

    def test_local_mcp_reports_the_client_and_its_tool_calls(self):
        server_module = submodule("mcp.server")
        registry = submodule("blender.mcp_service").build_registry()
        server = server_module.McpServer(
            "127.0.0.1", 0, registry, {}, timeout=5, observer=self.usage.MCP_OBSERVER
        )

        def call(message):
            with ThreadPoolExecutor(max_workers=1) as worker:
                result = worker.submit(server.handle, message)
                deadline = time.monotonic() + 5
                while not result.done() and time.monotonic() < deadline:
                    server.process_pending()
                    time.sleep(0.001)
                return result.result(1)

        with online_access(True):
            self.share()
            call(
                {
                    "id": 1,
                    "method": "initialize",
                    "params": {"clientInfo": {"name": "probe client", "version": "1.0"}},
                }
            )
            response = call(
                {
                    "id": 2,
                    "method": "tools/call",
                    "params": {"name": "scene_summary", "arguments": {}},
                }
            )
            self.assertNotIn("isError", response["result"])
            call({"id": 3, "method": "tools/call", "params": {"name": "no_such_tool"}})
            sent = self.sent()
        self.assertEqual(
            sent[0], ("mcp_client_connected", {"client": "probe client", "client_version": "1.0"})
        )
        self.assertEqual(len(sent), 2)
        event, properties = sent[1]
        self.assertEqual(event, "mcp_tool_called")
        self.assertEqual(
            {key: properties[key] for key in ("tool", "outcome")},
            {"tool": "scene_summary", "outcome": "ok"},
        )
        self.assertEqual(sorted(properties), ["duration_ms", "outcome", "tool"])
