# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Installed Film video export controls share session handles, approvals and staging."""

import hashlib
import tempfile
import threading
import time
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, Mock, call, patch

import bpy
import test_film_review_controls as review_controls
from helpers import submodule


class Rows(list):
    """A stand-in for an operator CollectionProperty outside a registered instance."""

    def add(self):
        row = SimpleNamespace()
        self.append(row)
        return row


class Gate:
    def __init__(self):
        self.started, self.release = threading.Event(), threading.Event()


class FilmExportControlTests(unittest.TestCase):
    def setUp(self):
        self.reviews = review_controls.FilmReviewControlTests()
        self.reviews.setUp()
        self.addCleanup(self.reviews.doCleanups)
        reviews = self.reviews
        self.session, self.scene, self.store = reviews.session, reviews.scene, reviews.store
        self.media, self.runtime, self.tools = reviews.media, reviews.runtime, reviews.tools
        self.film, self.production = reviews.film, reviews.production
        self.ui = submodule("blender.film_export_controls")
        self.module = submodule("blender.film_export")
        self.export = submodule("core.jobs.local_export")
        self.local_render = submodule("core.jobs.local_render")
        self.commands = self.session.film_export
        # Videos are published outside Blender's user and extension storage.
        root = Path(self.enterContext(tempfile.TemporaryDirectory())).resolve()
        self.output, self.outside = root / "Scenario", root / "Elsewhere"
        self.outside.mkdir()
        self.folder = self.output / "Film"
        self.enterContext(
            patch.object(
                self.runtime, "paths", return_value=SimpleNamespace(output_dir=self.output)
            )
        )
        status = self.tools.build_film_review({"review_id": reviews.ready()})
        self.assertEqual(status["phase"], "BUILT", status["error"])
        self.review = bpy.data.scenes[status["review_scene"]]

    def staging(self):
        return sorted(self.media.review_root.glob("film-export-*"))

    def state(self):
        return (
            bpy.data.filepath,
            bpy.context.scene,
            self.scene.frame_current,
            set(bpy.data.scenes),
            self.film.snapshot(self.scene),
            self.review.frame_current,
        )

    def sources(self):
        return self.tools.film_export_sources({"production_id": self.production})

    def source_id(self, scene=None):
        name = (scene or self.review).name
        (source,) = [item for item in self.sources()["sources"] if item["scene"] == name]
        return source["source_id"]

    def mcp_prepare(self, name="Cut.mp4", **options):
        arguments = {
            "context_id": "fixture-context",
            "production_id": self.production,
            "source_id": options.pop("source_id", None) or self.source_id(),
            "destination_path": str(self.folder / name),
            **options,
        }
        status = self.tools.prepare_film_export(arguments)
        self.assertEqual(status["phase"], "READY", status["error"])
        return status

    def render(self, status):
        return self.tools.render_film_export(
            {"review_id": status["review_id"], "approved_destination": status["destination"]}
        )

    def settle(self, identifier, timeout=120):
        review = self.commands._reviews[identifier]
        deadline = time.monotonic() + timeout
        while review.task is not None and not review.task.done():
            self.assertLess(time.monotonic(), deadline, "Film export did not finish")
            time.sleep(0.05)
        # Application-owned maintenance advances exports without drawing a panel.
        self.runtime.sync_catalog_context()
        return self.tools.film_export_review({"review_id": identifier})

    def fake_render(self, gate=None, data=b"verified fixture video"):
        """A fast handoff instead of the child; the real publish still runs."""
        calls = []

        def render(spec, *, cancel, progress):
            calls.append(spec)
            progress("render", spec.frames // 2, spec.frames)
            if gate is not None:
                gate.started.set()
                while not gate.release.wait(0.02):
                    if cancel.is_set():
                        raise self.local_render.RenderCancelled("Film export cancelled")
            output = spec.directory / "output"
            output.mkdir()
            (output / "film.mp4").write_bytes(data)
            return self.export.StagedExport(
                spec.directory,
                output / "film.mp4",
                hashlib.sha256(data).hexdigest(),
                len(data),
                spec.frames,
                spec.fps,
                spec.width,
                spec.height,
                spec.audio,
                "ffprobe",
                (),
            )

        return patch.object(self.export, "render", side_effect=render), calls

    def panel(self):
        layout = MagicMock()
        self.ui.SCENARIO_PT_film_export.draw(SimpleNamespace(layout=layout), bpy.context)
        box = layout.box.return_value
        return box, [item.kwargs.get("text") for item in box.label.call_args_list]

    def assert_offline(self):
        self.assertFalse(self.media.calls or self.media.downloads)

    def test_inspection_lists_only_this_recipes_review_scenes_without_changes(self):
        tags = {
            key: self.review[key]
            for key in (
                "scenario_sequence_kind",
                "scenario_production_id",
                "scenario_recipe_sha256",
            )
        }

        def tagged(name, **changes):
            scene = bpy.data.scenes.new(name)
            self.addCleanup(bpy.data.scenes.remove, scene)
            for key, value in {**tags, **changes}.items():
                scene[key] = value
            return scene

        tagged("Foreign review", scenario_production_id="other-production")
        tagged("Changed recipe review", scenario_recipe_sha256="0" * 64)
        tagged("Timeline", scenario_sequence_kind="scene_timeline")
        tagged("Grouped tag", scenario_sequence_kind={"kind": "downloaded_final_review"})
        empty = tagged("Empty review")
        nested = tagged("Nested review", scenario_sequence_kind="downloaded_previs_review")
        nested.sequence_editor_create().strips.new_scene("Nested 3D", self.scene, 1, 1)
        before = self.state()
        result = self.sources()
        self.assertEqual(before, self.state())
        self.assertEqual(result["context_id"], "fixture-context")
        self.assertEqual(result["default_directory"], str(self.folder))
        self.assertTrue(result["encoder_available"])
        sources = {item["scene"]: item for item in result["sources"]}
        self.assertEqual(set(sources), {self.review.name, empty.name, nested.name})
        source = sources[self.review.name]
        self.assertEqual(
            (source["kind"], source["frames"], source["fps"], source["width"], source["height"]),
            ("final", 48, 24, 1920, 1080),
        )
        # Picture and native audio strips read one private copy: one media file.
        self.assertEqual(
            (source["media"], source["audible"], source["blocked_reason"]), (1, True, "")
        )
        self.assertEqual(source["default_name"], "Prepared cut - Final Review.mp4")
        self.assertIn("sequencer strips", sources[empty.name]["blocked_reason"])
        self.assertEqual(sources[nested.name]["kind"], "previs")
        self.assertIn("movie, sound", sources[nested.name]["blocked_reason"])
        with self.assertRaisesRegex(ValueError, "movie, sound"):
            self.mcp_prepare(source_id=sources[nested.name]["source_id"])
        # The snapshot's media byte budget blocks before preparation, not after approval.
        with patch.object(self.export, "MAX_MEDIA_BYTES", 1):
            budget = {item["scene"]: item for item in self.sources()["sources"]}
        self.assertIn("16 GiB", budget[self.review.name]["blocked_reason"])
        with self.assertRaisesRegex(ValueError, "16 GiB"):
            self.mcp_prepare(source_id=budget[self.review.name]["source_id"])
        self.assertFalse(self.output.exists())
        self.assertEqual(self.commands._reviews, {})
        self.assert_offline()

    def test_default_size_is_the_even_size_the_snapshot_uses(self):
        # Blender's output truncates 1920x1080 at 33% to 633x356; the snapshot's
        # default rounds that down to even, so inspection must show and bind it.
        render = self.review.render
        self.addCleanup(setattr, render, "resolution_percentage", render.resolution_percentage)
        render.resolution_percentage = 33
        source = {item["scene"]: item for item in self.sources()["sources"]}[self.review.name]
        self.assertEqual((source["width"], source["height"]), (632, 356))
        self.assertEqual(source["blocked_reason"], "")
        status = self.mcp_prepare(source_id=source["source_id"])
        self.assertEqual((status["width"], status["height"]), (632, 356))
        self.tools.film_export_review({"review_id": status["review_id"], "action": "discard"})
        self.assert_offline()

    def test_prepare_refuses_unsafe_destinations_and_settings_before_work(self):
        self.folder.mkdir(parents=True)
        (self.folder / "Taken.mp4").write_bytes(b"keep")
        source_id = self.source_id()
        base = {
            "context_id": "fixture-context",
            "production_id": self.production,
            "source_id": source_id,
        }
        refused = {
            str(self.outside / "Cut.mp4"): "only inside",
            str(self.folder / "Taken.mp4"): "already exists",
            "Film/Cut.mp4": "absolute",
            str(self.folder / "Cut.mov"): ".mp4",
            str(self.folder / "CON.mp4"): "portable",
            str(self.output / "Missing" / "Cut.mp4"): "already exist",
        }
        for destination, message in refused.items():
            with self.subTest(destination=Path(destination).name):
                with self.assertRaisesRegex(self.export.LocalExportError, message):
                    self.tools.prepare_film_export({**base, "destination_path": destination})
        good = {**base, "destination_path": str(self.folder / "Cut.mp4")}
        with self.assertRaisesRegex(ValueError, "even export dimensions"):
            self.tools.prepare_film_export({**good, "width": 129})
        with self.assertRaisesRegex(ValueError, "explicitly"):
            self.tools.prepare_film_export({**good, "include_audio": "yes"})
        with patch.object(self.module, "encoder_available", return_value=False):
            with self.assertRaisesRegex(ValueError, "cannot encode"):
                self.tools.prepare_film_export(good)
        with self.assertRaisesRegex(ValueError, "connection changed"):
            self.tools.prepare_film_export({**good, "context_id": "old"})
        with self.assertRaises(self.runtime.ScenarioError):
            self.tools.prepare_film_export({**good, "production_id": "other"})
        with self.assertRaisesRegex(ValueError, "current Film export inspection"):
            self.tools.prepare_film_export({**good, "source_id": "unknown"})
        # The session policy also refuses private storage for native choices.
        private = Path(bpy.utils.extension_path_user("unused"))
        with self.assertRaisesRegex(self.export.LocalExportError, "outside Blender"):
            self.commands.prepare(
                self.scene, source_id=source_id, destination=str(private / "Cut.mp4")
            )
        self.assertEqual(self.commands._reviews, {})
        self.assertEqual(sorted(p.name for p in self.folder.iterdir()), ["Taken.mp4"])
        self.assertFalse(list(self.output.glob("Missing")))
        self.assertEqual(self.staging(), [])
        self.assert_offline()

    def test_agent_destinations_resolve_inside_the_output_folder(self):
        self.assertFalse(self.output.exists())
        status = self.mcp_prepare()
        # Only the default Film folder was created, and nothing inside it.
        self.assertTrue(self.folder.is_dir())
        self.assertEqual(list(self.folder.iterdir()), [])
        self.assertTrue(status["output_folder_only"])
        self.assertEqual(status["destination"], str(self.folder.resolve() / "Cut.mp4"))
        self.tools.film_export_review({"review_id": status["review_id"], "action": "discard"})
        (self.output / "escape").symlink_to(self.outside, target_is_directory=True)
        with self.assertRaisesRegex(self.export.LocalExportError, "only inside"):
            self.mcp_prepare(destination_path=str(self.output / "escape" / "Cut.mp4"))
        # A native file browser choice is not limited to the Output Folder.
        native = self.commands.prepare(
            self.scene, source_id=self.source_id(), destination=str(self.outside / "Cut.mp4")
        )
        self.assertEqual(native["phase"], "READY")
        self.assertFalse(native["output_folder_only"])
        # Agents cannot approve it: refused before the snapshot, without consuming it.
        with self.assertRaisesRegex(self.export.LocalExportError, "only inside"):
            self.render(native)
        self.assertEqual(self.commands.status(native["review_id"])["phase"], "READY")
        self.assertEqual(self.staging(), [])
        self.assertEqual(list(self.outside.iterdir()), [])
        self.assert_offline()

    def test_render_needs_the_exact_destination_and_publishes_once(self):
        status = self.mcp_prepare()
        identifier = status["review_id"]
        for wrong in (str(self.folder / "Cut.mp4") + " ", "", None, str(self.outside / "Cut.mp4")):
            with self.assertRaisesRegex(ValueError, "exact destination"):
                self.commands.approve(identifier, approved_destination=wrong)
        self.assertEqual(self.commands.status(identifier)["phase"], "READY")
        self.assertEqual(self.staging(), [])
        before = self.state()
        patcher, calls = self.fake_render()
        with patcher:
            started = self.render(status)
            self.assertEqual(started["phase"], "EXPORTING")
            status = self.settle(identifier)
        self.assertEqual(status["phase"], "EXPORTED", status["error"])
        self.assertEqual(before, self.state())
        destination = Path(status["destination"])
        self.assertEqual(destination.read_bytes(), b"verified fixture video")
        self.assertEqual(status["sha256"], hashlib.sha256(b"verified fixture video").hexdigest())
        self.assertTrue(status["published"])
        self.assertEqual(len(calls), 1)
        self.assertEqual((calls[0].width, calls[0].height, calls[0].audio), (1920, 1080, True))
        with self.assertRaisesRegex(ValueError, "fresh ready"):
            self.render(status)
        self.assertEqual(sorted(p.name for p in self.folder.iterdir()), ["Cut.mp4"])
        self.assert_offline()

    def test_native_destination_choice_and_render_dialog(self):
        before = self.state()
        manager = Mock()
        context = SimpleNamespace(scene=self.scene, window_manager=manager, blend_data=bpy.data)
        operator = SimpleNamespace(
            report=Mock(),
            layout=MagicMock(),
            filepath="",
            filename_ext=".mp4",
            choices=Rows(),
            choice_index=0,
            audio_track="OFF",
            scene_size=False,
            width=64,
            height=64,
        )
        prepare = self.ui.SCENARIO_OT_prepare_film_export
        self.assertEqual(prepare.invoke(operator, context, None), {"RUNNING_MODAL"})
        manager.fileselect_add.assert_called_once_with(operator)
        self.assertEqual(operator.filepath, str(self.folder / "Prepared cut - Final Review.mp4"))
        self.assertEqual((operator.audio_track, operator.scene_size), ("AUTO", True))
        prepare.draw(operator, context)
        labels = [c.kwargs.get("text") for c in operator.layout.label.call_args_list]
        self.assertIn("48 frames at 24 fps", labels)
        self.assertIn("Render video asks again.", labels)
        # Dismissing the file browser creates no handle or file.
        self.assertEqual(self.commands._reviews, {})
        (self.folder / "Prepared cut - Final Review.mp4").write_bytes(b"keep")
        operator.filepath = ""
        prepare.invoke(operator, context, None)
        self.assertEqual(operator.filepath, str(self.folder / "Prepared cut - Final Review 2.mp4"))
        # Explicit choices override the scene's size and audible sound strips.
        operator.audio_track, operator.scene_size = "OFF", False
        operator.width, operator.height = 128, 72
        self.assertEqual(prepare.execute(operator, bpy.context), {"FINISHED"})
        status = self.commands.current(self.scene)
        self.assertEqual(status["phase"], "READY")
        self.assertEqual((status["audio"], status["width"], status["height"]), (False, 128, 72))
        self.assertEqual(Path(status["destination"]).name, "Prepared cut - Final Review 2.mp4")
        render = self.ui.SCENARIO_OT_render_film_export
        dialog = SimpleNamespace(
            review_id=status["review_id"],
            approved_destination="",
            report=Mock(),
            layout=MagicMock(),
        )
        manager.invoke_props_dialog.return_value = {"RUNNING_MODAL"}
        self.assertEqual(render.invoke(dialog, context, None), {"RUNNING_MODAL"})
        self.assertEqual(dialog.approved_destination, status["destination"])
        render.draw(dialog, context)
        labels = [c.kwargs.get("text") for c in dialog.layout.label.call_args_list]
        self.assertIn("Renders in an offline Blender process; never overwrites a file.", labels)
        self.assertIn("H.264 MP4 with no audio track; 1 media files", labels)
        self.assertIn("48 frames at 24 fps (2 s); 128 x 72", labels)
        # Cancelling the dialog is inert; Python callers must repeat the destination.
        self.assertEqual(
            bpy.ops.scenario.render_film_export(review_id=status["review_id"]), {"CANCELLED"}
        )
        self.assertEqual(self.commands.status(status["review_id"])["phase"], "READY")
        self.assertEqual(self.staging(), [])
        patcher, calls = self.fake_render()
        with patcher:
            self.assertEqual(render.execute(dialog, bpy.context), {"FINISHED"})
            status = self.settle(status["review_id"])
        self.assertEqual(status["phase"], "EXPORTED", status["error"])
        self.assertEqual((calls[0].audio, calls[0].width, calls[0].height), (False, 128, 72))
        self.assertEqual(before[1:], self.state()[1:])
        box, labels = self.panel()
        self.assertIn("Exported Prepared cut - Final Review 2.mp4", labels)
        operators = [c.args[0] for c in box.row.return_value.operator.call_args_list]
        self.assertEqual(operators, ["wm.path_open", "scenario.copy_text"])
        self.assert_offline()

    def test_real_child_export_is_verified_and_discard_keeps_the_video(self):
        before = self.state()
        status = self.mcp_prepare(width=128, height=72)
        # Blender's decode check runs everywhere; ffprobe is covered by the primitive tests.
        with patch.object(self.export.shutil, "which", return_value=None):
            self.render(status)
            status = self.settle(status["review_id"], timeout=300)
        self.assertEqual(status["phase"], "EXPORTED", status["error"])
        self.assertEqual(before, self.state())
        destination = Path(status["destination"])
        self.assertEqual(status["sha256"], self.local_render.digest(destination))
        self.assertEqual(status["verification"], "blender")
        self.assertEqual((status["width"], status["height"], status["frames"]), (128, 72, 48))
        summary = submodule("core.jobs.mp4_inspection").inspect(destination)
        self.assertEqual((summary.video[0].codec, summary.audio[0].codec), ("h264", "aac"))
        self.assertEqual(sorted(p.name for p in self.folder.iterdir()), ["Cut.mp4"])
        self.assertEqual(len(self.staging()), 1)
        discarded = self.tools.film_export_review(
            {"review_id": status["review_id"], "action": "discard"}
        )
        self.assertEqual(discarded["phase"], "DISCARDED")
        self.assertEqual(self.staging(), [])
        self.assertEqual(self.local_render.digest(destination), status["sha256"])
        self.assertIsNone(self.commands.current(self.scene))
        self.assert_offline()

    def test_progress_is_cached_and_cancel_leaves_no_destination(self):
        status = self.mcp_prepare()
        gate = Gate()
        patcher, _ = self.fake_render(gate)
        with patcher:
            self.render(status)
            self.assertTrue(gate.started.wait(10))
            self.commands.poll()
            current = self.tools.film_export_review({"review_id": status["review_id"]})
            self.assertEqual(current["progress"], {"stage": "render", "done": 24, "total": 48})
            self.assertEqual(current["percent"], 50)
            box, labels = self.panel()
            self.assertIn("Rendering 24/48 frames (50%)", labels)
            self.assertIn(
                call("scenario.cancel_film_export", icon="CANCEL"), box.operator.call_args_list
            )
            cancelled = self.tools.film_export_review(
                {"review_id": status["review_id"], "action": "cancel"}
            )
            self.assertEqual(cancelled["phase"], "CANCELLING")
            status = self.settle(status["review_id"])
        self.assertEqual(status["phase"], "CANCELLED")
        self.assertFalse((self.folder / "Cut.mp4").exists())
        self.assertEqual(list(self.folder.iterdir()), [])
        self.assertEqual(len(self.staging()), 1)  # Retained until discarded.
        self.tools.film_export_review({"review_id": status["review_id"], "action": "discard"})
        self.assertEqual(self.staging(), [])
        self.assert_offline()

    def test_failed_publish_saves_a_verified_copy_without_rendering_again(self):
        status = self.mcp_prepare()
        identifier = status["review_id"]
        publish, failures = self.export.publish, []

        def fail_once(staged, destination, *args, **kwargs):
            if not failures:
                failures.append(destination)
                self.export.release(args[0])
                raise self.export.ExportPublishError(
                    "Could not move the verified video into place", staged
                )
            return publish(staged, destination, *args, **kwargs)

        patcher, calls = self.fake_render()
        with patcher, patch.object(self.export, "publish", side_effect=fail_once):
            self.render(status)
            status = self.settle(identifier)
            self.assertEqual(status["phase"], "PUBLISH_FAILED")
            self.assertTrue(status["republish_available"])
            self.assertIn("verified video", status["error"])
            self.assertEqual(list(self.folder.iterdir()), [])
            box, labels = self.panel()
            self.assertIn("Video verified but not saved", labels)
            with self.assertRaisesRegex(self.export.LocalExportError, "only inside"):
                self.tools.film_export_review(
                    {
                        "review_id": identifier,
                        "action": "prepare_republish",
                        "destination_path": str(self.outside / "Copy.mp4"),
                    }
                )
            with self.assertRaisesRegex(ValueError, "new destination"):
                self.tools.film_export_review({"review_id": identifier, "action": "republish"})
            # A native choice outside the Output Folder stays pending for the user to confirm.
            elsewhere = self.commands.prepare_republish(identifier, str(self.outside / "Copy.mp4"))
            with self.assertRaisesRegex(self.export.LocalExportError, "only inside"):
                self.tools.film_export_review(
                    {
                        "review_id": identifier,
                        "action": "republish",
                        "approved_destination": elsewhere["pending_destination"],
                    }
                )
            status = self.commands.status(identifier)
            self.assertEqual(
                (status["phase"], status["pending_destination"]),
                ("PUBLISH_FAILED", elsewhere["pending_destination"]),
            )
            self.assertEqual(list(self.outside.iterdir()), [])
            # The native file choice, then a separate confirmation of the exact file.
            choose = self.ui.SCENARIO_OT_choose_film_export_copy
            manager = Mock()
            context = SimpleNamespace(scene=self.scene, window_manager=manager, blend_data=bpy.data)
            operator = SimpleNamespace(
                review_id=identifier, report=Mock(), filepath="", filename_ext=".mp4"
            )
            self.assertEqual(choose.invoke(operator, context, None), {"RUNNING_MODAL"})
            self.assertEqual(operator.filepath, str(self.folder.resolve() / "Cut.mp4"))
            operator.filepath = str(self.folder / "Copy.mp4")
            self.assertEqual(choose.execute(operator, bpy.context), {"FINISHED"})
            pending = self.commands.status(identifier)["pending_destination"]
            self.assertEqual(Path(pending).name, "Copy.mp4")
            with self.assertRaisesRegex(ValueError, "exact new destination"):
                self.tools.film_export_review(
                    {"review_id": identifier, "action": "republish", "approved_destination": "x"}
                )
            confirm = self.ui.SCENARIO_OT_publish_film_export_copy
            dialog = SimpleNamespace(
                review_id=identifier, approved_destination="", report=Mock(), layout=MagicMock()
            )
            manager.invoke_props_dialog.return_value = {"RUNNING_MODAL"}
            self.assertEqual(confirm.invoke(dialog, context, None), {"RUNNING_MODAL"})
            self.assertEqual(dialog.approved_destination, pending)
            self.assertEqual(confirm.execute(dialog, bpy.context), {"FINISHED"})
            status = self.settle(identifier)
        self.assertEqual(status["phase"], "EXPORTED", status["error"])
        self.assertEqual(sorted(p.name for p in self.folder.iterdir()), ["Copy.mp4"])
        self.assertEqual(list(self.outside.iterdir()), [])
        self.assertEqual(len(calls), 1)  # Copy-only: rendered once.
        self.assertEqual(status["sha256"], hashlib.sha256(b"verified fixture video").hexdigest())
        self.assert_offline()

    def test_ready_exports_go_stale_but_running_exports_survive_edits(self):
        target = self.media.target
        for change in ("frame", "selection", "destination"):
            with self.subTest(change=change):
                status = self.mcp_prepare(name=change + ".mp4")
                self.assertIn("Selecting, editing or Undo here discards it", self.panel()[1])
                if change == "frame":
                    self.scene.frame_set(self.scene.frame_current + 1)
                elif change == "selection":
                    target.select_set(not target.select_get())
                    bpy.context.view_layer.update()
                else:
                    Path(status["destination"]).write_bytes(b"someone else")
                current = self.tools.film_export_review({"review_id": status["review_id"]})
                self.assertEqual(current["phase"], "ERROR")
                self.assertIn("prepare the export again", current["error"])
                with self.assertRaisesRegex(ValueError, "fresh ready"):
                    self.render(status)
        self.assertEqual(self.staging(), [])
        status = self.mcp_prepare()
        gate = Gate()
        patcher, _ = self.fake_render(gate)
        with patcher:
            self.render(status)
            self.assertTrue(gate.started.wait(10))
            # The snapshot binds the bytes: edits after it do not stop the export.
            self.scene.frame_set(self.scene.frame_current + 1)
            self.commands.poll()
            self.assertEqual(self.commands.status(status["review_id"])["phase"], "EXPORTING")
            gate.release.set()
            status = self.settle(status["review_id"])
        self.assertEqual(status["phase"], "EXPORTED", status["error"])
        self.assert_offline()

    def test_synchronizing_the_unshown_review_scene_is_not_an_edit(self):
        # Removing any datablock requests a relations rebuild of every depsgraph. A
        # window evaluates only the scenes it shows, so the review scene keeps that
        # tag until the export synchronizes it, which then reports an update although
        # nothing changed.
        def rebuild_relations():
            bpy.data.texts.remove(bpy.data.texts.new("Unrelated"))

        source_id = self.source_id()
        rebuild_relations()
        status = self.mcp_prepare(source_id=source_id)
        patcher, calls = self.fake_render()
        with patcher:
            started = self.render(status)
            self.assertEqual(started["phase"], "EXPORTING", started["error"])
            status = self.settle(status["review_id"])
        self.assertEqual(status["phase"], "EXPORTED", status["error"])
        self.assertEqual(len(calls), 1)
        # Inspecting again synchronizes the same scene without revoking a ready export.
        status = self.mcp_prepare(name="Again.mp4")
        rebuild_relations()
        self.sources()
        current = self.tools.film_export_review({"review_id": status["review_id"]})
        self.assertEqual(current["phase"], "READY", current["error"])
        self.tools.film_export_review({"review_id": status["review_id"], "action": "discard"})
        # A real edit of the unshown scene still refuses: approval rereads what it showed.
        sound = next(
            strip for strip in self.review.sequence_editor.strips_all if strip.type == "SOUND"
        )
        render, kept = self.review.render, self.staging()
        edits = {
            "size": (render, "resolution_percentage", 50),
            "audio": (sound, "mute", True),
            "rate": (render, "fps", 25),
        }
        for change, (owner, name, value) in edits.items():
            with self.subTest(change=change):
                status = self.mcp_prepare(name=change + ".mp4")
                previous = getattr(owner, name)
                setattr(owner, name, value)
                try:
                    refused = self.render(status)
                finally:
                    setattr(owner, name, previous)
                self.assertEqual(refused["phase"], "ERROR")
                self.assertIn("review scene changed", refused["error"])
                self.assertFalse(Path(status["destination"]).exists())
                # Only the first export's private files remain; refusal wrote none.
                self.assertEqual(self.staging(), kept)
        self.assertEqual(len(calls), 1)
        self.assert_offline()

    def test_panel_and_studio_draw_only_read_cached_status(self):
        studio = submodule("blender.studio")
        view = bpy.context.window_manager.scenario_studio_view
        self.addCleanup(setattr, view, "page", view.page)
        self.addCleanup(setattr, view, "film_page", view.film_page)
        view.page, view.film_page = "FILM", "REVIEW"
        _, labels = self.panel()
        self.assertIn("Renders a built review scene to a new MP4.", labels)
        status = self.mcp_prepare()
        before = (self.commands.status(status["review_id"]), self.staging(), self.state())
        layout = MagicMock()
        with (
            patch.object(
                self.runtime, "ensure_film_jobs", side_effect=AssertionError("draw starts work")
            ),
            patch.object(self.commands, "poll", side_effect=AssertionError("draw polls work")),
            patch.object(self.commands, "inspect", side_effect=AssertionError("draw inspects")),
            patch.object(self.session, "drain", side_effect=AssertionError("draw drains work")),
        ):
            box, labels = self.panel()
            studio.draw_view(layout, bpy.context, width=400)
        self.assertIn(call(text="Export video", icon="FILE_MOVIE"), box.label.call_args_list)
        self.assertIn("To Cut.mp4", labels)
        self.assertIn(
            call("scenario.render_film_export", icon="RENDER_ANIMATION"),
            box.operator.call_args_list,
        )
        studio_box = layout.box.return_value
        self.assertIn(call(text="Export video", icon="FILE_MOVIE"), studio_box.label.call_args_list)
        self.assertEqual(
            before, (self.commands.status(status["review_id"]), self.staging(), self.state())
        )
        self.assert_offline()

    def test_shutdown_cancels_running_export_and_removes_private_files(self):
        status = self.mcp_prepare()
        gate = Gate()
        patcher, _ = self.fake_render(gate)
        with patcher:
            self.render(status)
            self.assertTrue(gate.started.wait(10))
            self.assertEqual(len(self.staging()), 1)
            self.assertTrue((self.folder / "Cut.mp4").exists())  # The reserved placeholder.
            self.session.shutdown()
        self.assertTrue(self.session._exports.stopped)
        self.assertEqual(self.staging(), [])
        self.assertEqual(list(self.folder.iterdir()), [])
        self.assertEqual(self.commands._reviews, {})
        self.assert_offline()

    def test_one_open_export_per_source_and_a_bounded_handle_set(self):
        status = self.mcp_prepare()
        with self.assertRaisesRegex(ValueError, "current export first"):
            self.mcp_prepare(name="Second.mp4")
        self.tools.film_export_review({"review_id": status["review_id"], "action": "discard"})
        self.commands._reviews.clear()
        template = self.commands._reviews
        source = next(iter(self.commands._sources.values()))
        for index in range(8):
            item = self.module._Export(
                f"held-{index}",
                self.scene,
                self.scene.name,
                self.film.snapshot(self.scene),
                self.media.origin,
                source,
                str(self.outside / f"{index}.mp4"),
                64,
                64,
                False,
                phase="EXPORTED",
                directory=self.outside,
            )
            template[item.identifier] = item
        with self.assertRaisesRegex(ValueError, "Discard a previous"):
            self.mcp_prepare(name="Third.mp4")
        self.assertEqual(len(self.commands._reviews), 8)
        template["held-3"].directory = None  # Owns no private files any more.
        status = self.mcp_prepare(name="Third.mp4")
        self.assertNotIn("held-3", self.commands._reviews)
        self.assertEqual(len(self.commands._reviews), 8)
        for item in template.values():
            if item.identifier.startswith("held-"):
                item.directory = None  # Never remove the fixture folder.
        self.assertTrue(self.outside.is_dir())
        self.assertEqual(status["phase"], "READY")

    def test_edit_mode_blocks_rendering_without_consuming(self):
        bpy.ops.mesh.primitive_cube_add()
        cube = bpy.context.object
        self.addCleanup(bpy.data.objects.remove, cube, do_unlink=True)
        bpy.ops.object.mode_set(mode="EDIT")
        try:
            status = self.mcp_prepare()
            self.assertFalse(bpy.ops.scenario.render_film_export.poll())
            with self.assertRaisesRegex(ValueError, "Object Mode"):
                self.commands.approve(
                    status["review_id"], approved_destination=status["destination"]
                )
            self.assertEqual(self.commands._reviews[status["review_id"]].phase, "READY")
        finally:
            bpy.ops.object.mode_set(mode="OBJECT")
        self.assertTrue(bpy.ops.scenario.render_film_export.poll())
        self.assertEqual(self.staging(), [])

    def test_native_operators_share_mcp_handles_and_retired_sessions_reject_them(self):
        status = self.mcp_prepare()
        identifier = status["review_id"]
        patcher, _ = self.fake_render()
        with patcher:
            result = bpy.ops.scenario.render_film_export(
                review_id=identifier, approved_destination=status["destination"]
            )
            self.assertEqual(result, {"FINISHED"})
            status = self.settle(identifier)
        self.assertEqual(status["phase"], "EXPORTED", status["error"])
        self.assertEqual(bpy.ops.scenario.discard_film_export(review_id=identifier), {"FINISHED"})
        self.assertEqual(
            self.tools.film_export_review({"review_id": identifier})["phase"], "DISCARDED"
        )
        ready = self.mcp_prepare(name="Later.mp4")
        self.session.deactivate()
        with self.assertRaisesRegex(ValueError, "fresh ready"):
            self.render(ready)
        self.assertEqual(self.commands.status(ready["review_id"])["phase"], "ERROR")
        self.assertFalse((self.folder / "Later.mp4").exists())
        self.assert_offline()

    def test_registration_orders_export_after_review(self):
        film = submodule("blender.film")
        classes = list(film.CLASSES)
        review = submodule("blender.film_review_controls").SCENARIO_PT_film_review
        self.assertLess(classes.index(review), classes.index(self.ui.SCENARIO_PT_film_export))
        self.assertEqual(self.ui.SCENARIO_PT_film_export.bl_parent_id, "SCENARIO_PT_film")
        for name in (
            "prepare_film_export",
            "render_film_export",
            "cancel_film_export",
            "discard_film_export",
            "choose_film_export_copy",
            "publish_film_export_copy",
            "film_export_error",
        ):
            self.assertTrue(hasattr(bpy.ops.scenario, name), name)
        layout = MagicMock()
        film.SCENARIO_PT_film.draw(SimpleNamespace(layout=layout), bpy.context)
        labels = [c.kwargs.get("text") for c in layout.label.call_args_list]
        self.assertIn("Assemble saved media under Review; export a video under Export", labels)
