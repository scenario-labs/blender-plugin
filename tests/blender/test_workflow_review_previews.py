# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Installed private previews of waiting workflow steps' review assets; not physical input proof.

Decoding must leave the open file alone: no image is added or removed, the
dependency graph reports no update and a job origin captured beforehand stays
current. A cached still lost before decoding is fetched again once by itself,
then by Retry previews; Retry also sends a still Blender could not decode
through the lane again before decoding it again.
"""

import hashlib
import json
import threading
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import bpy
import test_workflow_commands
import test_workflow_steps
from helpers import online_access, submodule
from test_preview_decode import open_file_state
from test_result_previews import png

LOAD = "scenario.load_workflow_step_previews"
CDN = "https://cdn.cloud.scenario.com"
GIF = b"GIF89a" + b"\x00" * 64
WAITING = ("queued", "pending", "offline")


class Layout(test_workflow_steps.Layout):
    """The step tests' recording layout, plus preview icons."""

    def _child(self, *args, **kwargs):
        return Layout(self.calls, self.enabled)

    box = row = column = _child

    def template_icon(self, icon_value=0, scale=1.0, **kwargs):
        self.calls.append(("template_icon", icon_value, scale))

    def icons(self):
        return [call[1:] for call in self.calls if call[0] == "template_icon"]


class Dialog(SimpleNamespace):
    """A stand-in review dialog that, like an operator, is hashed and weakly referenced."""

    __hash__ = object.__hash__

    def __eq__(self, other):
        return self is other


class ReviewPreviewTests(unittest.TestCase):
    def setUp(self):
        self.fixture = test_workflow_commands.WorkflowCommandTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.runtime = self.fixture.runtime
        self.module = submodule("blender.review_previews")
        self.steps = submodule("blender.workflow_steps")
        self.recovery = submodule("blender.job_recovery")
        self.dialog = self.steps.SCENARIO_OT_review_workflow_step
        self.context = SimpleNamespace(
            window_manager=SimpleNamespace(
                invoke_props_dialog=MagicMock(return_value={"RUNNING_MODAL"})
            )
        )
        transfers = submodule("core.jobs.transfers")
        self.files, self.downloads = {}, []
        owner = self

        class OfflineDownloader(transfers.ResultDownloader):
            """The configured host policy and online predicate, with bytes from memory."""

            def download(self, url, *, root, name, max_bytes=None, cancel=None, **kwargs):
                self._policy.destination(url)
                if not self._online_access():
                    raise transfers.TransferError("Online access is disabled")
                owner.downloads.append((url, threading.current_thread().name))
                data = owner.files[url]
                if max_bytes is not None and len(data) > max_bytes:
                    raise transfers.TransferError("Storage response exceeds the byte limit")
                with (Path(root) / name).open("xb") as output:
                    output.write(data)
                return transfers.DownloadedResult(name, len(data), hashlib.sha256(data).hexdigest())

        # The session is created later, with this downloader and the real storage policy.
        self.enterContext(patch.object(self.runtime, "ResultDownloader", OfflineDownloader))
        self.fixture.bulk_assets = {
            "asset-render": self.asset("asset-render", png(300, 150)),
            "asset-a": self.asset("asset-a", png(8, 8)),
            "asset-b": self.asset("asset-b", GIF),
            "asset-c": self.asset("asset-c", b"", size=64 * 1024 * 1024),
        }

    # Helpers.

    def asset(self, asset_id, data, **properties):
        url = f"{CDN}/{asset_id}.png?Signature=fixture-secret"
        self.files[url] = data
        record = {"id": asset_id, "status": "success", "mimeType": "image/png", "url": url}
        if properties:
            record["properties"] = properties
        return record

    def paused(self, *nodes):
        local_id = self.fixture.paused_workflow(*nodes)
        self.runtime.show_job_views(self.runtime.state.model_jobs.views.values())
        return local_id

    def view(self, local_id):
        return self.runtime.state.model_jobs.views[local_id]

    def binding(self, local_id, node_id):
        return {
            "context_id": self.runtime.state.job_context_id,
            "request_id": local_id,
            "expected_revision": self.fixture.store.get(local_id).revision,
            "node_id": node_id,
            "review_id": self.fixture.step(local_id, node_id).review_id,
        }

    def load(self, local_id, node_id, *, retry=False, **changes):
        values = {
            **self.binding(local_id, node_id),
            "retry": retry,
            "report": MagicMock(),
            **changes,
        }
        operator = SimpleNamespace(**values)
        result = self.steps.SCENARIO_OT_load_workflow_step_previews.execute(operator, bpy.context)
        return result, operator

    def lane(self, done):
        """Service the session's preview lane until `done(scheduler)`; never pumps icons."""
        session = self.runtime.state.job_session
        for _ in range(100):
            session.service_previews()
            scheduler = session.result_previews
            for task in (scheduler._task, scheduler._maintenance):
                if task is not None:
                    try:
                        task.result(5)
                    except Exception:
                        # A failed batch is reported as a status by the next pump.
                        pass
            session.service_previews()
            if done(scheduler):
                return
        self.fail("The preview lane did not settle")

    def settled(self, local_id, *assets):
        def done(scheduler):
            for asset in assets:
                status = scheduler.status(local_id, asset, review=True)
                if status is None or status.get("still").state.value in WAITING:
                    return False
            return True

        self.lane(done)
        self.owner().pump()

    def owner(self):
        return self.runtime.state.review_previews

    def still(self, local_id, asset_id):
        scheduler = self.runtime.state.job_session.result_previews
        return scheduler.status(local_id, asset_id, review=True).get("still")

    def ready(self, local_id, asset_id):
        """Service the lane until the still is cached; the pump has not decoded it yet."""
        self.lane(lambda scheduler: self.still(local_id, asset_id).state.value == "ready")

    def transfers(self):
        return len(self.fixture.bulk_reads), len(self.downloads)

    def rows(self, local_id):
        layout = Layout()
        self.recovery.draw_controls(layout, self.view(local_id))
        return layout

    def opened(self, local_id, node_id):
        operator = Dialog(
            **self.binding(local_id, node_id),
            decision="CONTINUE",
            candidates=test_workflow_steps.Candidates(),
            report=MagicMock(),
            layout=Layout(),
        )
        self.assertEqual(self.dialog.invoke(operator, self.context, None), {"RUNNING_MODAL"})
        return operator

    def cache_files(self):
        root = self.runtime.paths().cache_dir / "result-previews"
        return [path for path in root.rglob("*") if path.is_file()]

    # Tests.

    def test_load_previews_fetches_on_the_lane_and_decodes_only_in_the_pump(self):
        local_id = self.paused(self.fixture.approval(), self.fixture.selection())
        rows = self.rows(local_id)
        loads = rows.operators(LOAD)
        self.assertEqual([call[2] for call in loads], ["Load previews (1)", "Load previews (3)"])
        rna = bpy.ops.scenario.load_workflow_step_previews.get_rna_type()
        for call, node_id in zip(loads, ("check", "pick"), strict=True):
            self.assertEqual(call[3], {**self.binding(local_id, node_id), "retry": False})
            for key, value in call[3].items():
                kind = {"STRING": str, "INT": int, "BOOLEAN": bool}[rna.properties[key].type]
                self.assertIs(type(value), kind)
        # Studio's Workflows page offers the same controls under the waiting job.
        studio = Layout()
        self.steps.draw_pending(studio, bpy.context)
        self.assertEqual(studio.operators(LOAD), loads)
        self.assertEqual((self.fixture.bulk_reads, self.downloads), ([], []))
        self.assertIsNone(self.owner())

        result, operator = self.load(local_id, "check")
        self.assertEqual(result, {"FINISHED"}, operator.report.call_args)
        images = len(bpy.data.images)

        def ready(scheduler):
            status = scheduler.status(local_id, "asset-render", review=True)
            return status.get("still").state.value == "ready"

        self.lane(ready)
        # The still is cached, but only the pump decodes it; drawing never does.
        self.assertEqual(self.owner().get(local_id, "asset-render").state, "loading")
        self.assertIn("Previews: 0 of 1 ready, 1 loading", self.rows(local_id).labels())
        self.assertEqual((len(bpy.data.images), self.owner()._icons), (images, {}))
        # Nor does the pump while a render job runs.
        with patch.object(self.module, "_rendering", return_value=True):
            self.assertTrue(self.owner().pump())
        self.assertEqual(self.owner().get(local_id, "asset-render").reason, "Preparing preview")
        self.assertEqual(self.owner()._icons, {})
        self.assertTrue(self.owner().pump())
        self.assertEqual(self.owner().get(local_id, "asset-render").state, "ready")
        _, name = self.owner()._icons[(local_id, "asset-render")]
        icon = self.owner()._collection[name]
        # Fitted to 256 pixels, with the stored colors.
        self.assertEqual(tuple(icon.image_size), (256, 128))
        for got, expected in zip(
            icon.image_pixels_float[:4], (0x40 / 255, 0x80 / 255, 0xC0 / 255, 1.0), strict=True
        ):
            self.assertAlmostEqual(got, expected, places=2)
        # Decoded in temporary data: the open file never gained an image.
        self.assertEqual(len(bpy.data.images), images)
        self.assertFalse(self.owner().pump())
        self.assertIn("Previews: 1 of 1 ready", self.rows(local_id).labels())
        # One metadata read for the step's assets only, then one transfer, both on the lane.
        self.assertEqual(len(self.fixture.bulk_reads), 1)
        body = json.loads(self.fixture.bulk_reads[0].content)
        self.assertEqual(body["assetIds"], ["asset-render"])
        self.assertEqual(
            self.downloads,
            [(f"{CDN}/asset-render.png?Signature=fixture-secret", "ScenarioPreview")],
        )
        # The flow's own signed URLs are never used, and no URL reaches the cache or MCP.
        files = self.cache_files()
        self.assertTrue(files)
        for path in files:
            content = path.read_bytes()
            self.assertNotIn(b"Signature", content)
            self.assertNotIn(b"https", content)
        status = self.fixture.tools.job_status({"job_id": local_id})
        self.assertNotIn("Signature", json.dumps(status))
        self.assertFalse(self.fixture.decisions)
        self.assertEqual(len(self.fixture.paid), 1)

    def test_decoding_keeps_job_origins_captured_in_the_scene_current(self):
        local_id = self.paused(self.fixture.approval())
        session = self.runtime.state.job_session
        origin = session.capture(bpy.context.scene)
        updates = []

        def record(scene, depsgraph=None):
            # Names only, read while the handler runs.
            names = () if depsgraph is None else (u.id.name for u in depsgraph.updates)
            updates.append(tuple(names))

        handlers = bpy.app.handlers.depsgraph_update_post
        handlers.append(record)
        self.addCleanup(lambda: record in handlers and handlers.remove(record))
        self.assertEqual(self.load(local_id, "check")[0], {"FINISHED"})
        self.ready(local_id, "asset-render")
        bpy.context.view_layer.update()
        self.assertTrue(session._origins.current(origin))
        before = open_file_state()
        updates.clear()
        self.assertTrue(self.owner().pump())
        self.assertEqual(self.owner().get(local_id, "asset-render").state, "ready")
        bpy.context.view_layer.update()
        self.assertTrue(session._origins.current(origin))
        self.assertEqual(session.capture(bpy.context.scene), origin)
        # No image entered or left the open file, so no ID was updated.
        self.assertEqual(open_file_state(), before)
        self.assertEqual([names for names in updates if names], [])

    def test_a_lost_cached_still_is_fetched_again_once_then_by_retry(self):
        local_id = self.paused(self.fixture.approval())
        self.assertEqual(self.load(local_id, "check")[0], {"FINISHED"})
        self.ready(local_id, "asset-render")
        owner, transfers = self.owner(), self.transfers()
        # The disposable cache loses the file after the lane verified it and
        # before the pump decodes it: the pump fetches it again by itself.
        self.still(local_id, "asset-render").preview.path.unlink()
        self.assertTrue(owner.pump())
        self.assertEqual(
            owner.get(local_id, "asset-render"),
            self.module.AssetPreview("loading", reason="Fetching preview again"),
        )
        self.assertEqual(self.still(local_id, "asset-render").state.value, "queued")
        self.ready(local_id, "asset-render")
        self.assertEqual(self.transfers(), (transfers[0] + 1, transfers[1] + 1))
        # Lost again before decoding: only once by itself, then Retry previews.
        self.still(local_id, "asset-render").preview.path.unlink()
        self.assertTrue(owner.pump())
        value = owner.get(local_id, "asset-render")
        self.assertEqual(value.state, "unavailable")
        self.assertIn("unavailable; use Retry", value.reason)
        self.assertEqual(self.still(local_id, "asset-render").state.value, "ready")
        self.assertFalse(owner.pump())
        self.assertEqual(self.transfers(), (transfers[0] + 1, transfers[1] + 1))
        rows = self.rows(local_id)
        self.assertIn("Previews: 0 of 1 ready, 1 unavailable", rows.labels())
        self.assertEqual(
            [(call[2], call[3]["retry"]) for call in rows.operators(LOAD)],
            [("Retry previews", True)],
        )
        self.assertEqual(self.load(local_id, "check", retry=True)[0], {"FINISHED"})
        self.assertEqual(self.still(local_id, "asset-render").state.value, "queued")
        self.settled(local_id, "asset-render")
        self.assertEqual(owner.get(local_id, "asset-render").state, "ready")
        self.assertEqual(self.transfers(), (transfers[0] + 2, transfers[1] + 2))
        self.assertFalse(self.fixture.decisions)

    def test_retry_checks_again_and_decodes_again_a_still_blender_could_not_decode(self):
        local_id = self.paused(self.fixture.approval())
        self.assertEqual(self.load(local_id, "check")[0], {"FINISHED"})
        decode = submodule("blender.preview_decode")
        with patch.object(
            decode, "decode", side_effect=decode.PreviewDecodeError("Blender could not decode")
        ):
            self.settled(local_id, "asset-render")
        owner, transfers = self.owner(), self.transfers()
        value = owner.get(local_id, "asset-render")
        self.assertEqual((value.state, value.reason), ("unavailable", "Blender could not decode"))
        # Never decoded again by itself.
        self.assertFalse(owner.pump())
        self.assertEqual(owner.get(local_id, "asset-render"), value)
        # Retry sends it through the lane again, which verifies the cache entry.
        self.assertEqual(self.load(local_id, "check", retry=True)[0], {"FINISHED"})
        self.assertEqual(self.still(local_id, "asset-render").state.value, "queued")
        self.settled(local_id, "asset-render")
        self.assertEqual(owner.get(local_id, "asset-render").state, "ready")
        # The entry still verified, so nothing was fetched again.
        self.assertEqual(self.transfers(), transfers)

    def test_an_icon_blender_could_not_fill_is_released(self):
        local_id = self.paused(self.fixture.approval())
        self.assertEqual(self.load(local_id, "check")[0], {"FINISHED"})
        decode = submodule("blender.preview_decode")
        # Decoding succeeds, but Blender refuses the pixels for the new icon.
        with patch.object(decode, "decode", return_value=((2, 2), None)):
            self.settled(local_id, "asset-render")
        owner = self.owner()
        value = owner.get(local_id, "asset-render")
        self.assertEqual(
            (value.state, value.reason), ("unavailable", "Blender could not decode this preview")
        )
        self.assertEqual((owner._icons, len(owner._collection)), ({}, 0))
        # Retry decodes it again into the only icon of the collection.
        self.assertEqual(self.load(local_id, "check", retry=True)[0], {"FINISHED"})
        self.settled(local_id, "asset-render")
        self.assertEqual(owner.get(local_id, "asset-render").state, "ready")
        self.assertEqual(list(owner._collection), [owner._icons[(local_id, "asset-render")][1]])

    def test_unavailable_candidates_are_reported_and_retried_explicitly(self):
        local_id = self.paused(self.fixture.selection())
        self.assertEqual(self.load(local_id, "pick")[0], {"FINISHED"})
        self.settled(local_id, "asset-a", "asset-b", "asset-c")
        owner = self.owner()
        self.assertEqual(
            [owner.get(local_id, asset).state for asset in ("asset-a", "asset-b", "asset-c")],
            ["ready", "unavailable", "unavailable"],
        )
        self.assertIn("unsupported format", owner.get(local_id, "asset-b").reason)
        self.assertIn("open it in Scenario", owner.get(local_id, "asset-c").reason)
        # A declared size above the bound is never downloaded.
        self.assertEqual(
            [url.rsplit("/", 1)[-1].split(".")[0] for url, _ in self.downloads],
            ["asset-a", "asset-b"],
        )
        rows = self.rows(local_id)
        self.assertIn("Previews: 1 of 3 ready, 2 unavailable", rows.labels())
        retry = rows.operators(LOAD)
        self.assertEqual(
            [(call[2], call[3]["retry"]) for call in retry], [("Retry previews", True)]
        )
        # The review dialog says why a candidate has no preview.
        operator = self.opened(local_id, "pick")
        self.dialog.draw(operator, self.context)
        labels = operator.layout.labels()
        self.assertIn(
            "    No preview: Scenario returned a preview in an unsupported format", labels
        )
        self.assertNotIn(self.steps.NO_PREVIEWS[:40], " ".join(labels))
        # Retry fetches only what failed, after the content changed.
        reads = len(self.fixture.bulk_reads)
        self.fixture.bulk_assets["asset-b"] = self.asset("asset-b", png(4, 4))
        self.assertEqual(self.load(local_id, "pick", retry=True)[0], {"FINISHED"})
        self.settled(local_id, "asset-a", "asset-b", "asset-c")
        self.assertEqual(owner.get(local_id, "asset-a").state, "ready")
        self.assertEqual(owner.get(local_id, "asset-b").state, "ready")
        self.assertEqual(len(self.fixture.bulk_reads), reads + 1)
        body = json.loads(self.fixture.bulk_reads[-1].content)
        self.assertEqual(body["assetIds"], ["asset-b", "asset-c"])
        self.assertFalse(self.fixture.decisions)

    def test_a_selection_listing_an_asset_twice_previews_it_once(self):
        pick = {**self.fixture.selection(), "items": ["asset-a", "asset-render", "asset-a"]}
        local_id = self.paused(pick)
        result, operator = self.load(local_id, "pick")
        self.assertEqual(result, {"FINISHED"}, operator.report.call_args)
        self.settled(local_id, "asset-a", "asset-render")
        owner = self.owner()
        self.assertEqual(
            [owner.get(local_id, asset).state for asset in ("asset-a", "asset-render")],
            ["ready", "ready"],
        )
        # One read and one transfer per distinct asset.
        self.assertEqual(
            [json.loads(read.content)["assetIds"] for read in self.fixture.bulk_reads],
            [["asset-a", "asset-render"]],
        )
        self.assertEqual(
            sorted(url.rsplit("/", 1)[-1].split(".")[0] for url, _ in self.downloads),
            ["asset-a", "asset-render"],
        )
        self.assertFalse(self.fixture.decisions)

    def test_rows_and_dialog_draw_loaded_icons_without_any_request(self):
        local_id = self.paused(self.fixture.approval(), self.fixture.selection())
        self.load(local_id, "check")
        self.load(local_id, "pick")
        self.settled(local_id, "asset-render", "asset-a", "asset-b", "asset-c")
        # Background Blender assigns no icon IDs; draw with a stand-in ID.
        owner, ready = self.owner(), self.module.AssetPreview("ready", 7)
        owner._tracked[(local_id, "asset-render")] = ready
        owner._tracked[(local_id, "asset-a")] = ready
        dialogs = {node_id: self.opened(local_id, node_id) for node_id in ("check", "pick")}
        before = (len(self.fixture.calls), len(self.downloads), len(bpy.data.images))
        refuse = AssertionError("drawing read, requested or decoded")
        store = self.fixture.store
        with (
            patch.object(self.runtime, "ensure_model_jobs", side_effect=refuse),
            patch.object(self.runtime, "ensure_job_session", side_effect=refuse),
            patch.object(store, "get", side_effect=refuse),
            patch.object(owner, "pump", side_effect=refuse),
            patch.object(owner, "_decode", side_effect=refuse),
        ):
            rows = self.rows(local_id)
            studio = Layout()
            self.steps.draw_pending(studio, bpy.context)
            for operator in dialogs.values():
                self.dialog.draw(operator, self.context)
        self.assertEqual(
            (len(self.fixture.calls), len(self.downloads), len(bpy.data.images)), before
        )
        for layout in (rows, studio):
            self.assertEqual(layout.icons(), [(7, 3.0), (7, 3.0)])
            self.assertIn("Previews: 1 of 1 ready", layout.labels())
            self.assertIn("Previews: 1 of 3 ready, 2 unavailable", layout.labels())
        # The dialog draws a grid of approval icons and an icon beside a candidate.
        check, pick = dialogs["check"].layout, dialogs["pick"].layout
        self.assertEqual(check.icons(), [(7, self.steps.GRID_SCALE)])
        self.assertIn("asset-render", check.labels())
        self.assertEqual(pick.icons(), [(7, self.steps.CANDIDATE_SCALE)])
        self.assertIn(("prop", "selected", "1. asset-a", True), pick.calls)
        self.assertEqual(
            (dialogs["pick"].decision, [item.selected for item in dialogs["pick"].candidates]),
            ("CONTINUE", [False, False, False]),
        )

    def test_dialog_without_loaded_previews_asks_to_load_them_and_sends_nothing(self):
        local_id = self.paused(self.fixture.approval())
        operator = self.opened(local_id, "check")
        self.dialog.draw(operator, self.context)
        labels = " ".join(operator.layout.labels())
        self.assertIn("Load previews from the Jobs row or Studio Workflows", labels)
        self.assertEqual((self.fixture.bulk_reads, self.downloads), ([], []))
        self.assertIsNone(self.owner())

    def test_the_dialog_is_refreshed_only_while_its_previews_load(self):
        local_id = self.paused(self.fixture.approval())
        popups = submodule("blender.studio")._popups
        context = SimpleNamespace(
            window_manager=self.context.window_manager, region_popup=MagicMock()
        )
        operator = self.opened(local_id, "check")
        self.addCleanup(popups.pop, operator, None)
        self.dialog.draw(operator, context)
        self.assertNotIn(operator, popups)
        self.load(local_id, "check")
        self.dialog.draw(operator, context)
        self.assertIs(popups[operator], context.region_popup)
        self.settled(local_id, "asset-render")
        self.dialog.draw(operator, context)
        self.assertNotIn(operator, popups)

    def test_stale_foreign_or_offline_requests_queue_nothing(self):
        local_id = self.paused(self.fixture.approval())
        for changes, reason in (
            ({"review_id": "0" * 64}, "step changed"),
            ({"context_id": "another-context"}, "context changed"),
            ({"expected_revision": 0}, "job changed"),
        ):
            result, operator = self.load(local_id, "check", **changes)
            self.assertEqual(result, {"CANCELLED"})
            self.assertIn(reason, operator.report.call_args.args[1])
        poll = self.steps.SCENARIO_OT_load_workflow_step_previews.poll
        self.assertTrue(poll(bpy.context))
        with online_access(False):
            self.assertFalse(poll(bpy.context))
            result, operator = self.load(local_id, "check")
            self.assertEqual(result, {"CANCELLED"})
            self.assertIn("Allow Online Access", operator.report.call_args.args[1])
        self.assertEqual((self.fixture.bulk_reads, self.downloads), ([], []))
        self.assertEqual(self.runtime.state.job_session.result_previews._entries, {})
        # Workers read the permission snapshot the main thread refreshes.
        self.runtime.sync_catalog_context()
        # A step that lists no asset has nothing to preview, and draws no control.
        self.fixture.waiting({**self.fixture.approval(), "dependsOn": []})
        self.runtime.state.model_jobs._next_poll[local_id] = 0.0
        self.fixture.settle()
        self.assertEqual(self.fixture.step(local_id, "check").review_asset_ids, ())
        self.assertEqual(self.rows(local_id).operators(LOAD), [])
        result, operator = self.load(local_id, "check")
        self.assertEqual(result, {"CANCELLED"})
        self.assertIn("no assets", operator.report.call_args.args[1])

    def test_decided_steps_release_their_icons(self):
        local_id = self.paused(self.fixture.approval())
        self.load(local_id, "check")
        self.settled(local_id, "asset-render")
        owner = self.owner()
        self.assertEqual(len(owner._collection), 1)
        self.fixture.decision_reply = lambda request: self.fixture.waiting(
            self.fixture.approval("success")
        )
        self.fixture.decide(local_id, "check", "approve")
        jobs = self.runtime.state.model_jobs
        for _, task in tuple(jobs._commands.values()):
            task.result(5)
        jobs.poll()
        self.assertTrue(owner.pump())
        self.assertIsNone(owner.get(local_id, "asset-render"))
        self.assertEqual(len(owner._collection), 0)
        self.assertEqual(self.rows(local_id).operators(LOAD), [])

    def test_retired_contexts_clear_icons_and_the_cache_serves_a_restart(self):
        local_id = self.paused(self.fixture.approval())
        self.load(local_id, "check")
        self.settled(local_id, "asset-render")
        owner = self.owner()
        reads, downloads = len(self.fixture.bulk_reads), len(self.downloads)
        self.runtime.state.reset()
        self.assertIsNone(self.runtime.state.review_previews)
        self.assertIsNone(owner._collection)
        self.assertEqual(owner._tracked, {})
        jobs = self.runtime.ensure_model_jobs()
        self.runtime.show_job_views(jobs.inspect())
        record = self.fixture.store.get(local_id)
        _, task = self.runtime.control_model_job(
            self.runtime.state.job_context_id, local_id, record.revision, "refresh"
        )
        task.result(5)
        jobs.poll()
        self.runtime.show_job_views(jobs.views.values())
        self.assertEqual(self.load(local_id, "check")[0], {"FINISHED"})
        self.settled(local_id, "asset-render")
        self.assertIsNot(self.owner(), owner)
        self.assertEqual(self.owner().get(local_id, "asset-render").state, "ready")
        # The verified cache entry served the new session: no metadata read or transfer.
        self.assertEqual((len(self.fixture.bulk_reads), len(self.downloads)), (reads, downloads))

    def test_registration_of_the_load_operator(self):
        cls = self.steps.SCENARIO_OT_load_workflow_step_previews
        self.assertTrue(cls.is_registered)
        self.assertEqual(cls.bl_idname, LOAD)
        self.assertIn(cls, self.steps.CLASSES)
        self.assertEqual(
            set(bpy.ops.scenario.load_workflow_step_previews.get_rna_type().properties.keys())
            - {"rna_type"},
            {"context_id", "request_id", "expected_revision", "node_id", "review_id", "retry"},
        )


if __name__ == "__main__":
    unittest.main()
