# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Installed Film case-study bundles: portable archive, sanitized documents and controls."""

import hashlib
import json
import subprocess
import tempfile
import threading
import time
import unittest
import zipfile
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, Mock, call, patch

import bpy
import test_film_export_controls as export_controls
from helpers import FIXTURES, submodule

REOPEN = r"""
import json, os, sys
import bpy

report_path, frame_path = sys.argv[sys.argv.index("--") + 1 :]
review = next(s for s in bpy.data.scenes if s.get("scenario_sequence_kind"))
leftovers = []
for scene in bpy.data.scenes:
    leftovers += [k for k in scene.keys() if k.startswith("scenario")
                  and k not in {"scenario_film", "scenario_sequence_kind", "scenario_film_shot_id",
                                "scenario_film_sequence_kind", "scenario_audio_mix"}]
    editor = scene.sequence_editor
    for strip in (editor.strips_all if editor else ()):
        leftovers += [k for k in strip.keys() if k.startswith("scenario")]
for obj in bpy.data.objects:
    leftovers += [k for k in obj.keys() if k.startswith("scenario")
                  and k not in {"scenario_role", "scenario_primitive", "scenario_asset_policy",
                                "scenario_hero_id", "scenario_reference_task"}]
# Blender 5 keeps the extension's registered settings apart from custom properties.
system = []
for collection in (bpy.data.scenes, bpy.data.objects, bpy.data.materials, bpy.data.images):
    for owner in collection:
        group = owner.bl_system_properties_get(do_create=False)
        system += [k for k in (group.keys() if group is not None else ()) if "scenario" in k]
paths =bpy.utils.blend_paths(absolute=False, packed=False, local=False)
strips = review.sequence_editor.strips_all
sounds = [s for s in strips if s.type == "SOUND"]
render_paths = sorted({scene.render.filepath for scene in bpy.data.scenes})
review.render.resolution_x = review.render.resolution_y = 64
review.render.resolution_percentage = 100
review.render.image_settings.file_format = "PNG"
review.render.filepath = frame_path
review.frame_current = review.frame_start
bpy.ops.render.render(write_still=True, scene=review.name)
report = {
    "scenes": sorted(scene.name for scene in bpy.data.scenes),
    "libraries": len(bpy.data.libraries),
    "paths": paths,
    "resolved": [os.path.isfile(bpy.path.abspath(path)) for path in paths],
    "sounds": [os.path.isfile(bpy.path.abspath(s.sound.filepath)) for s in sounds],
    "images": {i.name: [i.filepath, i.packed_file is not None] for i in bpy.data.images
               if i.type == "IMAGE"},
    "leftovers": leftovers,
    "system": system,
    "render_paths": render_paths,
    "fake_users": all(scene.use_fake_user for scene in bpy.data.scenes),
    "sound_strips": sorted(
        [s.name, s.volume, s.get("note"), s.frame_final_start, s.frame_final_end] for s in sounds
    ),
    "curves": sorted(
        curve.data_path
        for layer in review.animation_data.action.layers
        for strip in layer.strips
        for bag in strip.channelbags
        for curve in bag.fcurves
    ),
}
with open(report_path, "w", encoding="utf-8") as stream:
    json.dump(report, stream)
"""


class Gate:
    def __init__(self):
        self.started, self.release = threading.Event(), threading.Event()


class FilmCaseStudyTests(unittest.TestCase):
    def setUp(self):
        self.exports = export_controls.FilmExportControlTests()
        self.exports.setUp()
        self.addCleanup(self.exports.doCleanups)
        exports = self.exports
        self.session, self.scene, self.store = exports.session, exports.scene, exports.store
        self.media, self.runtime, self.tools = exports.media, exports.runtime, exports.tools
        self.film, self.production, self.review = exports.film, exports.production, exports.review
        self.output, self.outside, self.folder = exports.output, exports.outside, exports.folder
        self.ui = submodule("blender.film_case_study_controls")
        self.module = submodule("blender.film_case_study")
        self.study = submodule("core.jobs.local_case_study")
        self.documents = submodule("core.scene.film_case_study")
        self.export = submodule("core.jobs.local_export")
        self.local_render = submodule("core.jobs.local_render")
        self.scenes = submodule("blender.film_scene")
        self.commands = self.session.film_case_study
        # Private values the bundle must never contain.
        record = self.store.get("picture")
        self.private = {
            self.production,
            record.remote_job_id,
            *(item.asset.asset_id for item in record.results),
            self.session.scope.account_id,
            self.session.scope.project_id,
        }

    def staging(self):
        return sorted(self.media.review_root.glob("film-export-case-study-*"))

    def state(self):
        strips = tuple(
            (strip.name, strip.get("scenario_asset"), getattr(strip, "filepath", None))
            for strip in self.review.sequence_editor.strips_all
        )
        return (
            bpy.data.filepath,
            bpy.context.scene,
            self.scene.frame_current,
            set(bpy.data.scenes),
            self.film.snapshot(self.scene),
            self.review.get("scenario_production_id"),
            strips,
        )

    def build_timeline(self):
        """A matching shot scene with a textured, tagged object and its built timeline."""
        raw = json.loads(self.scene.scenario_film.recipe_json)
        plan, digest = self.scenes.timeline_recipe(raw, self.production)
        shot = plan["shots"][0]
        scene = bpy.data.scenes.new("Film / shot / Shot")
        self.addCleanup(self.remove, scene)
        scene.render.fps, scene.render.fps_base = plan["fps"], 1
        scene.frame_start, scene.frame_end = 1, shot["frames"]
        scene["scenario_film_production_id"] = self.production
        scene["scenario_film_shot_id"] = shot["id"]
        scene["scenario_film_recipe_sha256"] = digest
        camera = bpy.data.objects.new("Case camera", bpy.data.cameras.new("Case camera"))
        scene.collection.objects.link(camera)
        scene.camera = camera
        texture = self.media.root / "texture-source" / "hero-texture.jpg"
        texture.parent.mkdir(exist_ok=True)
        texture.write_bytes((FIXTURES / "synthetic/panorama-progressive.jpg").read_bytes())
        image = bpy.data.images.load(str(texture))
        packed = bpy.data.images.load(str(texture), check_existing=False)
        packed.pack()
        material = bpy.data.materials.new("Case material")
        material.use_nodes = True
        for item in (image, packed):
            material.node_tree.nodes.new("ShaderNodeTexImage").image = item
        mesh = bpy.data.meshes.new("Case hero")
        mesh.materials.append(material)
        hero = bpy.data.objects.new("Film / Hero", mesh)
        hero["scenario_asset"] = "hero-asset-identifier-0001"
        hero["scenario_role"] = "hero"
        scene.collection.objects.link(hero)
        self.private.add("hero-asset-identifier-0001")
        timeline = self.scenes.build_timeline(
            raw,
            production_id=self.production,
            shots={shot["id"]: self.scenes.ShotScene(scene, camera, None, {}, ())},
        )
        self.addCleanup(self.remove, timeline)
        for item in (timeline, scene):
            for layer in item.view_layers:
                layer.update()
        bpy.context.view_layer.update()
        return timeline, scene

    @staticmethod
    def remove(scene):
        if scene in tuple(bpy.data.scenes):
            bpy.data.scenes.remove(scene)

    @staticmethod
    def clear_lanes(scenes):
        for scene in scenes:
            if scene in tuple(bpy.data.scenes):
                scene.scenario.image.references.clear()
                scene.scenario.image.concept_job = ""

    def sources(self):
        return self.tools.film_case_study_sources({"production_id": self.production})

    def mcp_prepare(self, name="Cut.zip", timeline=True, **options):
        result = self.sources()
        source_id = options.pop("source_id", None) or next(
            item["source_id"] for item in result["sources"] if item["scene"] == self.review.name
        )
        arguments = {
            "context_id": "fixture-context",
            "production_id": self.production,
            "source_id": source_id,
            "destination_path": str(self.folder / name),
            **options,
        }
        if timeline and result["timelines"]:
            arguments["timeline_id"] = result["timelines"][0]["timeline_id"]
        status = self.tools.prepare_film_case_study(arguments)
        self.assertEqual(status["phase"], "READY", status["error"])
        return status

    def approve(self, status):
        return self.tools.export_film_case_study(
            {"review_id": status["review_id"], "approved_destination": status["destination"]}
        )

    def settle(self, identifier, timeout=300):
        review = self.commands._reviews[identifier]
        deadline = time.monotonic() + timeout
        while review.task is not None and not review.task.done():
            self.assertLess(time.monotonic(), deadline, "Film case study did not finish")
            time.sleep(0.05)
        self.runtime.sync_catalog_context()
        return self.tools.film_case_study_review({"review_id": identifier})

    def fake_build(self, gate=None, data=b"verified fixture archive"):
        """A fast handoff instead of the children; the real publish still runs."""
        calls = []

        def build(spec, *, cancel, progress):
            calls.append(spec)
            progress("archive", 1, 2)
            if gate is not None:
                gate.started.set()
                while not gate.release.wait(0.02):
                    if cancel.is_set():
                        raise self.local_render.RenderCancelled("Film case-study export cancelled")
            output = spec.directory / "output"
            output.mkdir()
            (output / "case-study.zip").write_bytes(data)
            return self.study.StagedBundle(
                spec.directory,
                output / "case-study.zip",
                hashlib.sha256(data).hexdigest(),
                len(data),
                spec.scenes,
                "0" * 64,
                (),
            )

        return patch.object(self.study, "build", side_effect=build), calls

    def panel(self):
        layout = MagicMock()
        self.ui.SCENARIO_PT_film_case_study.draw(SimpleNamespace(layout=layout), bpy.context)
        box = layout.box.return_value
        return box, [item.kwargs.get("text") for item in box.label.call_args_list]

    def assert_offline(self):
        self.assertFalse(self.media.calls or self.media.downloads)

    def reopen(self, archive):
        """Extract the archive elsewhere and reopen it in a fresh isolated Blender."""
        root = Path(self.enterContext(tempfile.TemporaryDirectory())).resolve()
        with zipfile.ZipFile(archive) as bundle:
            bundle.extractall(root / "extracted")
        (top,) = (root / "extracted").iterdir()
        (blend,) = top.glob("*.blend")
        script = root / "reopen.py"
        script.write_text(REOPEN, encoding="utf-8")
        profile, temporary = root / "profile", root / "tmp"
        profile.mkdir()
        temporary.mkdir()
        report, frame = root / "report.json", root / "frame.png"
        subprocess.run(
            [
                bpy.app.binary_path,
                "--quiet",
                "--offline-mode",
                "--factory-startup",
                "--disable-autoexec",
                "--background",
                str(blend),
                "--python-exit-code",
                "1",
                "--python",
                str(script),
                "--",
                str(report),
                str(frame),
            ],
            env=self.local_render._environment(profile, temporary),
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=300,
            check=True,
        )
        return top, json.loads(report.read_text(encoding="utf-8")), frame

    def test_real_bundle_reopens_with_relative_media_and_no_private_data(self):
        timeline, shot = self.build_timeline()
        # A rebuilt sound strip keeps its timing, settings, own properties and animation.
        (sound,) = [s for s in self.review.sequence_editor.strips_all if s.type == "SOUND"]
        sound["note"] = "keep me"
        sound.volume = 0.25
        sound.keyframe_insert("volume", frame=1)
        timing = [sound.name, 0.25, "keep me", sound.frame_final_start, sound.frame_final_end]
        # Composer settings saved on bundled scenes are registered properties, which
        # Blender 5 stores apart from custom ones: a reference upload's request and
        # asset, a concept job and a local reference file.
        lanes = []
        for owner in (shot, self.review):
            lane = owner.scenario.image
            lane.concept_job = f"lane-concept-job-{owner.name}"
            reference = lane.references.add()
            reference.asset_id = f"lane-reference-asset-{owner.name}"
            reference.filepath = str(self.media.root / "lane-reference" / "reference.png")
            reference["_scenario_reference_request"] = f"lane-reference-request-{owner.name}"
            lanes.append(owner)
            self.private |= {
                lane.concept_job,
                reference.asset_id,
                reference["_scenario_reference_request"],
            }
        self.addCleanup(self.clear_lanes, lanes)
        bpy.context.view_layer.update()
        before = self.state()
        status = self.mcp_prepare()
        self.assertEqual((status["timeline_scene"], status["shots"]), (timeline.name, 1))
        # Review, timeline and shot scenes; one movie copy and one external texture.
        self.assertEqual((status["scenes"], status["media"]), (3, 2))
        self.assertEqual((status["approved_tasks"], status["priced_tasks"]), (1, 1))
        self.assertEqual(status["quoted_cost_total"], "1")
        self.approve(status)
        status = self.settle(status["review_id"])
        self.assertEqual(status["phase"], "EXPORTED", status["error"])
        self.assertEqual(before, self.state())
        archive = Path(status["destination"])
        self.assertEqual(archive.name, "Cut.zip")
        self.assertEqual(status["sha256"], self.local_render.digest(archive, maximum=1 << 32))
        top_name = "Prepared cut Case Study/"
        with zipfile.ZipFile(archive) as bundle:
            names = bundle.namelist()
            contents = {name: bundle.read(name) for name in names}
        self.assertEqual(
            sorted(names),
            sorted(
                top_name + name
                for name in (
                    "Prepared cut Case Study.blend",
                    "Film Recipe.json",
                    "Production Ledger.json",
                    "Case Study Manifest.json",
                    "Open The Case Study.md",
                    "Media/001 movie.mp4",
                    "Media/002 image.jpg",
                )
            ),
        )
        # No private identifier or local path appears in any archived byte.
        for name, data in contents.items():
            for value in self.private:
                self.assertNotIn(value.encode(), data, (name, value))
            for path in (self.media.root, self.media.review_root, self.output):
                self.assertNotIn(str(path).encode(), data, name)
        ledger = json.loads(contents[top_name + "Production Ledger.json"])
        self.assertEqual(
            ledger["tasks"],
            [
                {
                    "task": "shot-video",
                    "title": "Video",
                    "kind": "model",
                    "model": "fixture-model",
                    "source": "generated",
                    "state": "applied",
                    "quoted_cost": "1",
                    "result_types": ["video/mp4"],
                }
            ],
        )
        self.assertEqual((ledger["quoted_cost_total"], ledger["cost_unit"]), ("1", "CU"))
        manifest = json.loads(contents[top_name + "Case Study Manifest.json"])
        self.assertIn("Emmanuel de Maistre", manifest["attribution"])
        self.assertEqual(manifest["scenes"]["review"], self.review.name)
        self.assertEqual(manifest["scenes"]["timeline"], timeline.name)
        self.assertEqual(manifest["scenes"]["shots"], [shot.name])
        blend = contents[top_name + "Prepared cut Case Study.blend"]
        self.assertEqual(manifest["blend_file"]["sha256"], hashlib.sha256(blend).hexdigest())
        for item in manifest["media"]:
            data = contents[top_name + item["file"]]
            self.assertEqual(
                (item["size"], item["sha256"]), (len(data), hashlib.sha256(data).hexdigest())
            )
        self.assertEqual(manifest["media_storage"]["repacked_images"], 1)
        self.assertGreaterEqual(manifest["media_storage"]["recreated_sound_strips"], 1)
        recipe = json.loads(contents[top_name + "Film Recipe.json"])
        submodule("core.scene.film_plan").validate_film_plan(recipe)
        self.assertEqual([task["id"] for task in recipe["tasks"]], ["shot-video"])
        guide = contents[top_name + "Open The Case Study.md"].decode()
        self.assertIn("Extract this archive first", guide)
        self.assertIn(timeline.name, guide)
        top, report, frame = self.reopen(archive)
        self.assertEqual(report["scenes"], sorted((self.review.name, timeline.name, shot.name)))
        self.assertEqual(report["libraries"], 0)
        self.assertTrue(report["paths"])
        self.assertTrue(all(path.startswith("//Media/") for path in report["paths"]), report)
        self.assertTrue(all(report["resolved"]), report)
        self.assertTrue(report["sounds"] and all(report["sounds"]), report)
        self.assertEqual(report["leftovers"], [])
        self.assertEqual(report["system"], [])
        self.assertEqual(report["render_paths"], ["//render/"])
        self.assertTrue(report["fake_users"])
        self.assertEqual(report["sound_strips"], [timing])
        self.assertEqual(report["curves"], [f'sequence_editor.strips_all["{timing[0]}"].volume'])
        external, packed = sorted(report["images"].values(), key=lambda item: item[1])
        self.assertEqual(external, ["//Media/002 image.jpg", False])
        self.assertTrue(packed[0].startswith("//Packed/") and packed[1], packed)
        # The reopened review decodes its relative movie into a rendered frame.
        self.assertGreater(frame.stat().st_size, 0)
        self.assertEqual(len(self.staging()), 1)
        discarded = self.tools.film_case_study_review(
            {"review_id": status["review_id"], "action": "discard"}
        )
        self.assertEqual(discarded["phase"], "DISCARDED")
        self.assertEqual(self.staging(), [])
        self.assertEqual(self.local_render.digest(archive, maximum=1 << 32), status["sha256"])
        self.assert_offline()

    def test_inspection_lists_reviews_and_current_timelines_without_changes(self):
        timeline, shot = self.build_timeline()

        def tagged(name, source, **changes):
            scene = bpy.data.scenes.new(name)
            self.addCleanup(self.remove, scene)
            for key in source.keys():
                if key.startswith("scenario_"):
                    scene[key] = source[key]
            for key, value in changes.items():
                scene[key] = value
            return scene

        stale = tagged("Stale timeline", timeline)
        stale.sequence_editor_create().strips.new_scene("Old take", self.scene, 1, 1)
        tagged("Foreign timeline", timeline, scenario_film_production_id="other-production")
        nested = tagged("Nested review", self.review)
        nested.sequence_editor_create().strips.new_scene("Nested 3D", shot, 1, 1)
        empty = tagged("Empty review", self.review)
        before = self.state()
        result = self.sources()
        self.assertEqual(before, self.state())
        self.assertEqual(result["context_id"], "fixture-context")
        self.assertEqual(result["default_directory"], str(self.folder))
        self.assertEqual(result["default_name"], "Prepared cut - Case Study.zip")
        sources = {item["scene"]: item for item in result["sources"]}
        self.assertEqual(set(sources), {self.review.name, nested.name, empty.name})
        source = sources[self.review.name]
        self.assertEqual((source["kind"], source["frames"], source["fps"]), ("final", 48, 24))
        self.assertEqual((source["strips"], source["media"], source["blocked_reason"]), (2, 1, ""))
        self.assertIn("director timeline", sources[nested.name]["blocked_reason"])
        self.assertIn("sequencer strips", sources[empty.name]["blocked_reason"])
        timelines = {item["scene"]: item for item in result["timelines"]}
        self.assertEqual(set(timelines), {timeline.name, stale.name})
        self.assertEqual(
            (timelines[timeline.name]["shots"], timelines[timeline.name]["blocked_reason"]), (1, "")
        )
        self.assertIn("Rebuild the director timeline", timelines[stale.name]["blocked_reason"])
        base = {
            "context_id": "fixture-context",
            "production_id": self.production,
            "source_id": source["source_id"],
            "destination_path": str(self.folder / "Cut.zip"),
        }
        with self.assertRaisesRegex(ValueError, "director timeline"):
            self.tools.prepare_film_case_study(
                {**base, "source_id": sources[nested.name]["source_id"]}
            )
        with self.assertRaisesRegex(ValueError, "Rebuild the director timeline"):
            self.tools.prepare_film_case_study(
                {**base, "timeline_id": timelines[stale.name]["timeline_id"]}
            )
        self.assertFalse(self.output.exists())
        self.assertEqual(self.commands._reviews, {})
        self.assertEqual(self.staging(), [])
        self.assert_offline()

    def test_prepare_refuses_unsafe_destinations_before_work(self):
        self.folder.mkdir(parents=True)
        (self.folder / "Taken.zip").write_bytes(b"keep")
        result = self.sources()
        base = {
            "context_id": "fixture-context",
            "production_id": self.production,
            "source_id": result["sources"][0]["source_id"],
        }
        refused = {
            str(self.outside / "Cut.zip"): "only inside",
            str(self.folder / "Taken.zip"): "already exists",
            "Film/Cut.zip": "absolute",
            str(self.folder / "Cut.mp4"): ".zip",
            str(self.folder / "CON.zip"): "portable",
            str(self.output / "Missing" / "Cut.zip"): "already exist",
        }
        for destination, message in refused.items():
            with self.subTest(destination=Path(destination).name):
                with self.assertRaisesRegex(self.export.LocalExportError, message):
                    self.tools.prepare_film_case_study({**base, "destination_path": destination})
        good = {**base, "destination_path": str(self.folder / "Cut.zip")}
        with self.assertRaisesRegex(ValueError, "connection changed"):
            self.tools.prepare_film_case_study({**good, "context_id": "old"})
        with self.assertRaises(self.runtime.ScenarioError):
            self.tools.prepare_film_case_study({**good, "production_id": "other"})
        with self.assertRaisesRegex(ValueError, "current Film case-study inspection"):
            self.tools.prepare_film_case_study({**good, "source_id": "unknown"})
        with self.assertRaisesRegex(ValueError, "current Film case-study inspection"):
            self.tools.prepare_film_case_study({**good, "timeline_id": "unknown"})
        private = Path(bpy.utils.extension_path_user("unused"))
        with self.assertRaisesRegex(self.export.LocalExportError, "outside Blender"):
            self.commands.prepare(
                self.scene, source_id=base["source_id"], destination=str(private / "Cut.zip")
            )
        self.assertEqual(self.commands._reviews, {})
        self.assertEqual(sorted(p.name for p in self.folder.iterdir()), ["Taken.zip"])
        self.assertEqual(self.staging(), [])
        self.assert_offline()

    def test_exact_destination_and_agent_folder_policy_before_consuming(self):
        status = self.mcp_prepare(timeline=False)
        self.assertTrue(status["output_folder_only"])
        self.assertEqual(status["destination"], str(self.folder.resolve() / "Cut.zip"))
        identifier = status["review_id"]
        for wrong in (status["destination"] + " ", "", None, str(self.outside / "Cut.zip")):
            with self.assertRaisesRegex(ValueError, "exact destination"):
                self.commands.approve(identifier, approved_destination=wrong)
        self.assertEqual(self.commands.status(identifier)["phase"], "READY")
        self.tools.film_case_study_review({"review_id": identifier, "action": "discard"})
        result = self.sources()
        native = self.commands.prepare(
            self.scene,
            source_id=result["sources"][0]["source_id"],
            destination=str(self.outside / "Cut.zip"),
        )
        self.assertFalse(native["output_folder_only"])
        # Agents cannot approve a native choice outside the Output Folder; it stays READY.
        with self.assertRaisesRegex(self.export.LocalExportError, "only inside"):
            self.approve(native)
        self.assertEqual(self.commands.status(native["review_id"])["phase"], "READY")
        self.assertEqual(self.staging(), [])
        self.assertEqual(list(self.outside.iterdir()), [])
        self.assert_offline()

    def test_native_choice_and_save_dialog_share_mcp_handles(self):
        timeline, _ = self.build_timeline()
        before = self.state()
        manager = Mock()
        context = SimpleNamespace(scene=self.scene, window_manager=manager, blend_data=bpy.data)
        operator = SimpleNamespace(
            report=Mock(),
            layout=MagicMock(),
            filepath="",
            filename_ext=".zip",
            choices=export_controls.Rows(),
            choice_index=0,
            timelines=export_controls.Rows(),
            timeline_index=0,
            include_timeline=False,
        )
        prepare = self.ui.SCENARIO_OT_prepare_film_case_study
        self.assertEqual(prepare.invoke(operator, context, None), {"RUNNING_MODAL"})
        manager.fileselect_add.assert_called_once_with(operator)
        self.assertEqual(operator.filepath, str(self.folder / "Prepared cut - Case Study.zip"))
        self.assertTrue(operator.include_timeline)
        prepare.draw(operator, context)
        labels = [c.kwargs.get("text") for c in operator.layout.label.call_args_list]
        self.assertIn("48 frames at 24 fps", labels)
        self.assertIn("Save case study asks again.", labels)
        self.assertEqual(self.commands._reviews, {})
        (self.folder / "Prepared cut - Case Study.zip").write_bytes(b"keep")
        operator.filepath = ""
        prepare.invoke(operator, context, None)
        self.assertEqual(operator.filepath, str(self.folder / "Prepared cut - Case Study 2.zip"))
        self.assertEqual(prepare.execute(operator, bpy.context), {"FINISHED"})
        status = self.commands.current(self.scene)
        self.assertEqual((status["phase"], status["timeline_scene"]), ("READY", timeline.name))
        save = self.ui.SCENARIO_OT_save_film_case_study
        dialog = SimpleNamespace(
            review_id=status["review_id"],
            approved_destination="",
            report=Mock(),
            layout=MagicMock(),
        )
        manager.invoke_props_dialog.return_value = {"RUNNING_MODAL"}
        self.assertEqual(save.invoke(dialog, context, None), {"RUNNING_MODAL"})
        self.assertEqual(dialog.approved_destination, status["destination"])
        save.draw(dialog, context)
        labels = [c.kwargs.get("text") for c in dialog.layout.label.call_args_list]
        self.assertIn(f"Timeline: {timeline.name} (1 shot)", labels)
        self.assertIn("Ledger: 1 approved task; 1 CU quoted for 1 task", labels)
        self.assertIn("Builds in offline Blender processes; never overwrites a file.", labels)
        # Dismissing the dialog is inert; Python callers must repeat the destination.
        self.assertEqual(
            bpy.ops.scenario.save_film_case_study(review_id=status["review_id"]), {"CANCELLED"}
        )
        self.assertEqual(self.commands.status(status["review_id"])["phase"], "READY")
        patcher, calls = self.fake_build()
        with patcher:
            self.assertEqual(save.execute(dialog, bpy.context), {"FINISHED"})
            status = self.settle(status["review_id"])
        self.assertEqual(status["phase"], "EXPORTED", status["error"])
        self.assertEqual(len(calls), 1)
        self.assertEqual(before[1:], self.state()[1:])
        box, labels = self.panel()
        self.assertIn("Exported Prepared cut - Case Study 2.zip", labels)
        operators = [c.args[0] for c in box.row.return_value.operator.call_args_list]
        self.assertEqual(operators, ["wm.path_open", "scenario.copy_text"])
        self.assertEqual(
            self.tools.film_case_study_review({"review_id": status["review_id"]})["sha256"],
            hashlib.sha256(b"verified fixture archive").hexdigest(),
        )
        self.assertEqual(
            bpy.ops.scenario.discard_film_case_study(review_id=status["review_id"]), {"FINISHED"}
        )
        self.assertEqual(self.commands.status(status["review_id"])["phase"], "DISCARDED")
        self.assert_offline()

    def test_progress_cancel_failed_save_and_copy_only_republish(self):
        status = self.mcp_prepare(timeline=False)
        gate = Gate()
        patcher, _ = self.fake_build(gate)
        with patcher:
            self.approve(status)
            self.assertTrue(gate.started.wait(10))
            self.commands.poll()
            box, labels = self.panel()
            self.assertIn("Packing the archive (50%)", labels)
            self.assertIn(
                call("scenario.cancel_film_case_study", icon="CANCEL"), box.operator.call_args_list
            )
            cancelled = self.tools.film_case_study_review(
                {"review_id": status["review_id"], "action": "cancel"}
            )
            self.assertEqual(cancelled["phase"], "CANCELLING")
            status = self.settle(status["review_id"])
        self.assertEqual(status["phase"], "CANCELLED")
        self.assertEqual(list(self.folder.iterdir()), [])
        self.tools.film_case_study_review({"review_id": status["review_id"], "action": "discard"})
        self.assertEqual(self.staging(), [])
        status = self.mcp_prepare(name="Again.zip", timeline=False)
        identifier = status["review_id"]
        publish, failures = self.export.publish, []

        def fail_once(staged, destination, *args, **kwargs):
            if not failures:
                failures.append(destination)
                self.export.release(args[0])
                raise self.export.ExportPublishError(
                    "Could not move the verified case-study archive into place", staged
                )
            return publish(staged, destination, *args, **kwargs)

        patcher, calls = self.fake_build()
        with patcher, patch.object(self.export, "publish", side_effect=fail_once):
            self.approve(status)
            status = self.settle(identifier)
            self.assertEqual(status["phase"], "PUBLISH_FAILED")
            self.assertTrue(status["republish_available"])
            self.assertIn("Case study verified but not saved", self.panel()[1])
            with self.assertRaisesRegex(self.export.LocalExportError, "only inside"):
                self.tools.film_case_study_review(
                    {
                        "review_id": identifier,
                        "action": "prepare_republish",
                        "destination_path": str(self.outside / "Copy.zip"),
                    }
                )
            with self.assertRaisesRegex(self.export.LocalExportError, ".zip"):
                self.tools.film_case_study_review(
                    {
                        "review_id": identifier,
                        "action": "prepare_republish",
                        "destination_path": str(self.folder / "Copy.mp4"),
                    }
                )
            choose = self.ui.SCENARIO_OT_choose_film_case_study_copy
            context = SimpleNamespace(scene=self.scene, window_manager=Mock(), blend_data=bpy.data)
            operator = SimpleNamespace(
                review_id=identifier, report=Mock(), filepath="", filename_ext=".zip"
            )
            self.assertEqual(choose.invoke(operator, context, None), {"RUNNING_MODAL"})
            self.assertEqual(operator.filepath, str(self.folder.resolve() / "Again.zip"))
            operator.filepath = str(self.folder / "Copy.zip")
            self.assertEqual(choose.execute(operator, bpy.context), {"FINISHED"})
            confirm = self.ui.SCENARIO_OT_publish_film_case_study_copy
            dialog = SimpleNamespace(
                review_id=identifier, approved_destination="", report=Mock(), layout=MagicMock()
            )
            context.window_manager.invoke_props_dialog.return_value = {"RUNNING_MODAL"}
            self.assertEqual(confirm.invoke(dialog, context, None), {"RUNNING_MODAL"})
            self.assertEqual(confirm.execute(dialog, bpy.context), {"FINISHED"})
            status = self.settle(identifier)
        self.assertEqual(status["phase"], "EXPORTED", status["error"])
        self.assertEqual(sorted(p.name for p in self.folder.iterdir()), ["Copy.zip"])
        self.assertEqual(len(calls), 1)  # Copy-only: built once.
        self.assert_offline()

    def test_video_exports_and_case_studies_share_one_export_thread(self):
        study = self.mcp_prepare(timeline=False)
        video = self.exports.mcp_prepare(name="Cut.mp4")
        gate = Gate()
        patcher, _ = self.fake_build(gate)
        with patcher:
            self.approve(study)
            self.assertTrue(gate.started.wait(10))
            # The video handle is refused without consuming while the case study runs.
            with self.assertRaisesRegex(ValueError, "current Film export"):
                self.exports.render(video)
            self.assertEqual(self.session.film_export.status(video["review_id"])["phase"], "READY")
            gate.release.set()
            study = self.settle(study["review_id"])
        self.assertEqual(study["phase"], "EXPORTED", study["error"])
        again = self.mcp_prepare(name="Later.zip", timeline=False)
        render, _ = self.exports.fake_render(Gate())
        with render:
            self.exports.render(video)
            with self.assertRaisesRegex(ValueError, "current Film export"):
                self.approve(again)
            self.assertEqual(self.commands.status(again["review_id"])["phase"], "READY")
            self.session.film_export.cancel(video["review_id"])
            self.exports.settle(video["review_id"])
        self.assert_offline()

    def test_ready_case_study_goes_stale_when_the_timeline_or_a_shot_changes(self):
        timeline, shot = self.build_timeline()
        status = self.mcp_prepare(name="Shot.zip")
        self.assertIn("Selecting, editing or Undo here discards it", self.panel()[1])
        self.session.invalidate_scene(shot)
        current = self.tools.film_case_study_review({"review_id": status["review_id"]})
        self.assertEqual(current["phase"], "ERROR")
        self.assertIn("prepare the case study again", current["error"])
        status = self.mcp_prepare(name="Timeline.zip")
        self.remove(timeline)
        current = self.tools.film_case_study_review({"review_id": status["review_id"]})
        self.assertEqual(current["phase"], "ERROR")
        with self.assertRaisesRegex(ValueError, "fresh ready"):
            self.approve(status)
        self.assertEqual(self.staging(), [])
        self.assert_offline()

    def test_synchronizing_the_unshown_scenes_is_not_an_edit(self):
        # As for video exports: removing any datablock leaves every scene no window
        # shows tagged, and the snapshot's own synchronization must not count as an edit.
        def rebuild_relations():
            bpy.data.texts.remove(bpy.data.texts.new("Unrelated"))

        self.build_timeline()
        result = self.sources()
        rebuild_relations()
        status = self.tools.prepare_film_case_study(
            {
                "context_id": "fixture-context",
                "production_id": self.production,
                "source_id": next(
                    item["source_id"]
                    for item in result["sources"]
                    if item["scene"] == self.review.name
                ),
                "timeline_id": result["timelines"][0]["timeline_id"],
                "destination_path": str(self.folder / "Cut.zip"),
            }
        )
        self.assertEqual(status["phase"], "READY", status["error"])
        patcher, calls = self.fake_build()
        with patcher:
            started = self.approve(status)
            self.assertEqual(started["phase"], "EXPORTING", started["error"])
            status = self.settle(status["review_id"])
        self.assertEqual(status["phase"], "EXPORTED", status["error"])
        self.assertEqual(len(calls), 1)
        # Inspecting again synchronizes the same scenes without revoking a ready case study.
        status = self.mcp_prepare(name="Again.zip")
        rebuild_relations()
        self.sources()
        current = self.tools.film_case_study_review({"review_id": status["review_id"]})
        self.assertEqual(current["phase"], "READY", current["error"])
        self.tools.film_case_study_review({"review_id": status["review_id"], "action": "discard"})
        # A real edit of the unshown review scene still refuses: approval rereads its bounds.
        render, kept = self.review.render, self.staging()
        for change, (name, value) in {
            "size": ("resolution_percentage", 50),
            "rate": ("fps", 25),
        }.items():
            with self.subTest(change=change):
                status = self.mcp_prepare(name=change + ".zip")
                previous = getattr(render, name)
                setattr(render, name, value)
                try:
                    refused = self.approve(status)
                finally:
                    setattr(render, name, previous)
                self.assertEqual(refused["phase"], "ERROR")
                self.assertIn("changed after it was prepared", refused["error"])
                self.assertFalse(Path(status["destination"]).exists())
                self.assertEqual(self.staging(), kept)
        self.assertEqual(len(calls), 1)
        self.assert_offline()

    def test_contents_that_change_after_preparing_refuse_the_build(self):
        self.build_timeline()
        status = self.mcp_prepare(name="Changed.zip")
        texture = next(
            Path(image.filepath_raw)
            for image in bpy.data.images
            if image.packed_file is None and image.filepath_raw.endswith("hero-texture.jpg")
        )
        # A media file the confirmation counted grows without touching any scene.
        with texture.open("ab") as stream:
            stream.write(b"\0")
        before = self.state()
        result = self.approve(status)
        self.assertEqual(result["phase"], "ERROR")
        self.assertIn("changed after it was prepared", result["error"])
        self.assertEqual(before, self.state())
        self.assertFalse((self.folder / "Changed.zip").exists())
        self.assertEqual(self.staging(), [])
        with self.assertRaisesRegex(ValueError, "fresh ready"):
            self.approve(status)
        self.assert_offline()

    def test_unportable_data_is_refused_with_a_reason(self):
        editor = self.review.sequence_editor
        sound = next(strip for strip in editor.strips_all if strip.type == "SOUND").sound
        sound.pack()
        (source,) = [
            item for item in self.sources()["sources"] if item["scene"] == self.review.name
        ]
        self.assertIn("Unpack sound strip audio", source["blocked_reason"])
        sound.unpack(method="USE_ORIGINAL")
        timeline, shot = self.build_timeline()
        clip = bpy.data.movieclips.load(str(FIXTURES / "synthetic/film-four-seconds.mp4"))
        self.addCleanup(bpy.data.movieclips.remove, clip)
        shot.active_clip = clip
        result = self.sources()
        (row,) = [item for item in result["timelines"] if item["scene"] == timeline.name]
        self.assertIn("movie clips", row["blocked_reason"])
        (source,) = [item for item in result["sources"] if item["scene"] == self.review.name]
        self.assertEqual(source["blocked_reason"], "")
        shot.active_clip = None
        # Linked data, such as the Essentials brushes a scene references once a
        # sculpt or paint mode was used in it, is refused until it is made local.
        folder = Path(self.enterContext(tempfile.TemporaryDirectory()))
        material = bpy.data.materials.new("Case linked material")
        bpy.data.libraries.write(str(folder / "linked.blend"), {material})
        bpy.data.materials.remove(material)
        with bpy.data.libraries.load(str(folder / "linked.blend"), link=True) as (_, target):
            target.materials = ["Case linked material"]
        (linked,) = target.materials
        library = linked.library
        self.addCleanup(bpy.data.libraries.remove, library)
        hero = next(obj for obj in shot.objects if obj.get("scenario_role") == "hero")
        hero.data.materials.append(linked)
        self.addCleanup(hero.data.materials.pop)
        (row,) = [item for item in self.sources()["timelines"] if item["scene"] == timeline.name]
        self.assertIn("Make linked or overridden data local", row["blocked_reason"])
        self.assertEqual(self.commands._reviews, {})

    def test_panel_and_studio_draw_only_read_cached_status(self):
        studio = submodule("blender.studio")
        view = bpy.context.window_manager.scenario_studio_view
        self.addCleanup(setattr, view, "page", view.page)
        self.addCleanup(setattr, view, "film_page", view.film_page)
        view.page, view.film_page = "FILM", "REVIEW"
        _, labels = self.panel()
        self.assertIn("Packs a review, timeline, media, recipe and ledger", labels)
        status = self.mcp_prepare(timeline=False)
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
        self.assertIn(call(text="Case-study bundle", icon="PACKAGE"), box.label.call_args_list)
        self.assertIn("To Cut.zip", labels)
        studio_box = layout.box.return_value
        self.assertIn(
            call(text="Case-study bundle", icon="PACKAGE"), studio_box.label.call_args_list
        )
        self.assertEqual(
            before, (self.commands.status(status["review_id"]), self.staging(), self.state())
        )
        self.assert_offline()

    def test_shutdown_cancels_a_running_case_study_and_removes_private_files(self):
        status = self.mcp_prepare(timeline=False)
        gate = Gate()
        patcher, _ = self.fake_build(gate)
        with patcher:
            self.approve(status)
            self.assertTrue(gate.started.wait(10))
            self.assertEqual(len(self.staging()), 1)
            self.assertTrue((self.folder / "Cut.zip").exists())  # The reserved placeholder.
            self.session.shutdown()
        self.assertTrue(self.session._exports.stopped)
        self.assertEqual(self.staging(), [])
        self.assertEqual(list(self.folder.iterdir()), [])
        self.assertEqual(self.commands._reviews, {})
        self.assert_offline()

    def test_edit_mode_blocks_building_without_consuming(self):
        bpy.ops.mesh.primitive_cube_add()
        cube = bpy.context.object
        self.addCleanup(bpy.data.objects.remove, cube, do_unlink=True)
        bpy.ops.object.mode_set(mode="EDIT")
        try:
            status = self.mcp_prepare(timeline=False)
            self.assertFalse(bpy.ops.scenario.save_film_case_study.poll())
            with self.assertRaisesRegex(ValueError, "Object Mode"):
                self.commands.approve(
                    status["review_id"], approved_destination=status["destination"]
                )
            self.assertEqual(self.commands._reviews[status["review_id"]].phase, "READY")
        finally:
            bpy.ops.object.mode_set(mode="OBJECT")
        self.assertTrue(bpy.ops.scenario.save_film_case_study.poll())
        self.assertEqual(self.staging(), [])

    def test_registration_orders_case_study_after_export(self):
        film = submodule("blender.film")
        classes = list(film.CLASSES)
        export = submodule("blender.film_export_controls").SCENARIO_PT_film_export
        panel = self.ui.SCENARIO_PT_film_case_study
        self.assertLess(classes.index(export), classes.index(panel))
        self.assertEqual(panel.bl_parent_id, "SCENARIO_PT_film")
        studio = submodule("blender.studio")
        self.assertEqual(studio.FILM_PANELS["REVIEW"][-1], panel)
        for name in (
            "prepare_film_case_study",
            "save_film_case_study",
            "cancel_film_case_study",
            "discard_film_case_study",
            "choose_film_case_study_copy",
            "publish_film_case_study_copy",
            "film_case_study_error",
        ):
            self.assertTrue(hasattr(bpy.ops.scenario, name), name)
