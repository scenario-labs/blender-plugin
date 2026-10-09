# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Model picker with Scenario's modality tabs and category chips (headless)."""

import pathlib
import tempfile
import threading
import types
import unittest
from unittest.mock import Mock, patch

import bpy
from helpers import online_access, reset_scene, submodule


def fake_records():
    catalog = submodule("core.api.catalog")
    prompt = [{"name": "prompt", "type": "string", "prompt": True, "required": {"always": True}}]
    mesh = [{"name": "model", "type": "file", "kind": "3d", "required": {"always": True}}]
    return [
        catalog.ModelRecord.from_api(
            {
                "id": "model_openai-gpt-image-2",
                "name": "GPT Image 2",
                "type": "custom",
                "capabilities": ["txt2img", "img2img"],
                "tags": ["editing", "sc:featured", "sc:third-party"],
                "shortDescription": "Best-in-class prompt adherence",
                "inputs": prompt,
            }
        ),
        catalog.ModelRecord.from_api(
            {
                "id": "model_z-image",
                "name": "Z-Image",
                "type": "custom",
                "capabilities": ["txt2img"],
                "tags": ["sc:third-party"],
                "shortDescription": "Fast open model",
                "inputs": prompt,
            }
        ),
        catalog.ModelRecord.from_api(
            {
                "id": "model_bria-remove-background",
                "name": "Bria Remove Background",
                "type": "custom",
                "capabilities": ["img2img"],
                "tags": ["remove-background", "tool", "sc:third-party"],
                "inputs": [
                    {"name": "image", "type": "file", "kind": "image", "required": {"always": True}}
                ],
            }
        ),
        catalog.ModelRecord.from_api(
            {
                "id": "model_chibis",
                "name": "3D Chibis",
                "type": "flux.1-lora",
                "parentModelId": "model_flux",
                "capabilities": ["txt2img"],
                "tags": ["sc:scenario"],
                "shortDescription": "Cute chibi characters",
                "inputs": prompt,
            }
        ),
        catalog.ModelRecord.from_api(
            {
                "id": "model_bytedance-seedance-2-0",
                "name": "Seedance 2.0",
                "type": "custom",
                "capabilities": ["txt2video", "img2video", "video2video"],
                "tags": ["editing", "sc:featured", "sc:third-party"],
                "inputs": prompt,
            }
        ),
        catalog.ModelRecord.from_api(
            {
                "id": "model_rodin-hyper3d-bang",
                "name": "Rodin Hyper3D Bang!",
                "type": "custom",
                "capabilities": ["3d23d"],
                "tags": ["Retexture", "Segmentation", "sc:third-party"],
                "inputs": mesh,
            }
        ),
        catalog.ModelRecord.from_api(
            {
                "id": "model_meshy-7-txt23d",
                "name": "Meshy 7 - Text-to-3D",
                "type": "custom",
                "capabilities": ["txt23d"],
                "tags": ["sc:third-party"],
                "inputs": prompt,
            }
        ),
        catalog.ModelRecord.from_api(
            {
                "id": "model_ace-step-1-5",
                "name": "ACE-Step 1.5",
                "type": "custom",
                "capabilities": ["txt2audio"],
                "tags": ["Music", "sc:third-party"],
                "inputs": prompt,
            }
        ),
    ]


class FakeLayout:
    """Records the UILayout calls a draw function makes: containers (row, column, box, split) return a child that records
    its own calls, everything else is logged as (name, args, kwargs). Attributes like `alignment` are plain attributes."""

    CONTAINERS = ("row", "column", "box", "split", "grid_flow")

    def __init__(self, kind="layout", **kwargs):
        self.kind, self.kwargs, self.children, self.calls = kind, kwargs, [], []
        self.alignment, self.enabled = "EXPAND", True

    def __getattr__(self, name):
        if name.startswith("__"):
            raise AttributeError(name)

        def call(*args, **kwargs):
            if name in self.CONTAINERS:
                child = FakeLayout(name, **kwargs)
                self.children.append(child)
                return child
            self.calls.append((name, args, kwargs))
            return types.SimpleNamespace() if name == "operator" else None

        return call

    def walk(self):
        yield self
        for child in self.children:
            yield from child.walk()

    def named(self, name):
        """The recorded calls of `name` on this node."""
        return [c for c in self.calls if c[0] == name]


class ModelPickerTests(unittest.TestCase):
    def draw_dialog(self):
        """Run the dialog's draw against a FakeLayout; returns the root."""
        root = FakeLayout()
        self.picker.SCENARIO_OT_pick_model.draw(types.SimpleNamespace(layout=root), bpy.context)
        return root

    @staticmethod
    def enum_rows(root):
        """[(alignment, [values]) for each row holding prop_enum buttons], in draw order."""
        return [
            (node.alignment, [c[1][2] for c in node.named("prop_enum")])
            for node in root.walk()
            if node.named("prop_enum")
        ]

    def setUp(self):
        reset_scene()
        self.picker = submodule("blender.model_picker")
        self.mf = submodule("core.api.model_filter")
        runtime = submodule("blender.runtime")
        handlers = submodule("blender.handlers")
        runtime.state.reset()
        records = fake_records()
        handlers.dispatch(
            ("catalog", {"privacy": "public", "records": records, "detailed": records})
        )
        self.runtime = runtime
        recent_path = self.picker._recent().path
        if recent_path.exists():
            recent_path.unlink()  # recents from a previous test would otherwise reorder the list
        wm = bpy.context.window_manager
        wm.scenario_picker_query = ""

    def test_registered_classes_and_window_manager_props(self):
        self.assertTrue(hasattr(bpy.types, "SCENARIO_UL_models"))
        self.assertTrue(hasattr(bpy.types, "SCENARIO_OT_pick_model"))
        wm = bpy.context.window_manager
        for name in (
            "scenario_picker_items",
            "scenario_picker_index",
            "scenario_picker_query",
            "scenario_picker_modality",
            "scenario_picker_category",
        ):
            self.assertTrue(hasattr(wm, name), name)
        self.assertFalse(hasattr(wm, "scenario_picker_chip"))
        self.assertEqual(self.picker.SCENARIO_OT_pick_model.bl_label, "Choose a model")

    def test_prepare_opens_the_lane_modality_without_loras_and_highlights_current(self):
        scene = bpy.context.scene
        lane_state = scene.scenario.lane_state("image")
        lane_state.model_id = "model_z-image"
        items = self.picker.prepare(bpy.context, "image")
        wm = bpy.context.window_manager
        self.assertEqual(wm.scenario_picker_modality, "image")
        self.assertEqual(wm.scenario_picker_category, "all")
        self.assertEqual(
            [i.model_id for i in items],
            ["model_openai-gpt-image-2", "model_bria-remove-background", "model_z-image"],
        )  # featured first, no LoRA
        self.assertEqual(items[wm.scenario_picker_index].model_id, "model_z-image")
        self.assertEqual(items[0].modality, "image")

    def test_category_chips_and_query_refilter_live(self):
        self.picker.prepare(bpy.context, "image")
        wm = bpy.context.window_manager
        wm.scenario_picker_category = "remove_background"
        self.assertEqual(
            [i.model_id for i in wm.scenario_picker_items], ["model_bria-remove-background"]
        )
        wm.scenario_picker_category = "edit"
        self.assertEqual(
            [i.model_id for i in wm.scenario_picker_items], ["model_openai-gpt-image-2"]
        )
        wm.scenario_picker_category = "all"
        wm.scenario_picker_query = "z-image"
        self.assertEqual([i.model_id for i in wm.scenario_picker_items], ["model_z-image"])
        wm.scenario_picker_query = ""
        self.assertEqual(len(wm.scenario_picker_items), 3)

    def test_modality_tabs_list_every_visible_model_of_that_modality(self):
        self.picker.prepare(bpy.context, "image")
        wm = bpy.context.window_manager
        wm.scenario_picker_modality = "3d"
        self.assertEqual(wm.scenario_picker_category, "all")
        self.assertEqual(
            sorted(i.model_id for i in wm.scenario_picker_items),
            ["model_meshy-7-txt23d", "model_rodin-hyper3d-bang"],
        )
        wm.scenario_picker_category = "parts"
        self.assertEqual(
            [i.model_id for i in wm.scenario_picker_items], ["model_rodin-hyper3d-bang"]
        )
        wm.scenario_picker_modality = "audio"
        self.assertEqual([i.model_id for i in wm.scenario_picker_items], ["model_ace-step-1-5"])
        self.assertEqual(
            [c[0] for c in self.mf.category_items("audio")],
            ["all", "speech", "music", "sfx", "tools"],
        )

    def test_execute_sets_model_and_records_recent(self):
        scene = bpy.context.scene
        lane_state = scene.scenario.lane_state("image")
        self.picker.prepare(bpy.context, "image")
        wm = bpy.context.window_manager
        wm.scenario_picker_index = [i.model_id for i in wm.scenario_picker_items].index(
            "model_bria-remove-background"
        )
        self.assertEqual(bpy.ops.scenario.pick_model(lane="image"), {"FINISHED"})
        self.assertEqual(lane_state.model_key, "model_bria-remove-background")
        self.assertEqual(lane_state.model_id, "model_bria-remove-background")
        self.assertEqual(self.picker._recent().ids("image")[0], "model_bria-remove-background")
        self.picker.prepare(bpy.context, "image")
        self.assertEqual(
            wm.scenario_picker_items[0].model_id, "model_bria-remove-background"
        )  # recently used first under All

    def test_choosing_another_modality_switches_the_lane(self):
        scene = bpy.context.scene
        scene.scenario.lane = "image"
        self.picker.prepare(bpy.context, "image")
        wm = bpy.context.window_manager
        wm.scenario_picker_modality = "video"
        wm.scenario_picker_index = [i.model_id for i in wm.scenario_picker_items].index(
            "model_bytedance-seedance-2-0"
        )
        model_id, target = self.picker.apply_choice(bpy.context, "image")
        self.assertEqual((model_id, target), ("model_bytedance-seedance-2-0", "video"))
        self.assertEqual(scene.scenario.lane, "video")
        self.assertEqual(
            scene.scenario.lane_state("video").model_key, "model_bytedance-seedance-2-0"
        )
        # a mesh-to-mesh model lands in the Edit 3D lane (or the 3D lane's Edit mode when the tabs are merged)
        wm.scenario_picker_modality = "3d"
        wm.scenario_picker_index = [i.model_id for i in wm.scenario_picker_items].index(
            "model_rodin-hyper3d-bang"
        )
        model_id, target = self.picker.apply_choice(bpy.context, "video")
        self.assertEqual((model_id, target), ("model_rodin-hyper3d-bang", "edit3d"))
        self.assertIn(scene.scenario.lane, ("edit3d", "3d"))
        self.assertEqual(scene.scenario.lane_state("edit3d").model_key, "model_rodin-hyper3d-bang")
        # a text-to-3D model lands in the 3D lane in Text mode
        wm.scenario_picker_index = [i.model_id for i in wm.scenario_picker_items].index(
            "model_meshy-7-txt23d"
        )
        model_id, target = self.picker.apply_choice(bpy.context, "image")
        self.assertEqual(target, "3d")
        self.assertEqual(scene.scenario.three_d_mode, "TEXT")

    def test_material_lane_shows_only_patina(self):
        catalog = submodule("core.api.catalog")
        handlers = submodule("blender.handlers")
        patina = catalog.ModelRecord.from_api(
            {
                "id": "model_patina-material",
                "name": "PATINA Material",
                "type": "custom",
                "capabilities": ["txt2img", "img2img"],
                "tags": ["sc:scenario"],
                "inputs": [
                    {
                        "name": "prompt",
                        "type": "string",
                        "prompt": True,
                        "required": {"always": True},
                    }
                ],
            }
        )
        records = fake_records() + [patina]
        handlers.dispatch(
            ("catalog", {"privacy": "public", "records": records, "detailed": records})
        )
        items = self.picker.prepare(bpy.context, "material")
        self.assertEqual([i.model_id for i in items], ["model_patina-material"])
        self.assertTrue(self.picker._ctx["material_only"])

    def test_execute_without_rows_is_cancelled(self):
        wm = bpy.context.window_manager
        self.picker.prepare(bpy.context, "image")
        wm.scenario_picker_query = "nothing-matches-this"
        self.assertEqual(len(wm.scenario_picker_items), 0)
        self.assertEqual(bpy.ops.scenario.pick_model(lane="image"), {"CANCELLED"})

    def flat_enum_values(self, root):
        """Every prop_enum value in draw order (each sits in its own centred cell)."""
        return [v for _, values in self.enum_rows(root) for v in values]

    def test_dialog_justifies_tabs_and_wraps_chips_with_centred_cells(self):
        self.picker.prepare(bpy.context, "image")
        wm = bpy.context.window_manager
        root = self.draw_dialog()
        self.assertEqual(root.calls[0][0], "separator")  # breathing room under the title
        # a continuous segmented control: every value is a prop_enum in an even split region (no gaps), none expanded
        self.assertEqual(
            self.flat_enum_values(root),
            [
                "image",
                "video",
                "audio",
                "3d",
                "all",
                "generate",
                "edit",
                "expand",
                "upscale",
                "vectorize",
                "remove_background",
                "tools",
            ],
        )
        self.assertFalse(
            any(c[2].get("expand") for node in root.walk() for c in node.named("prop"))
        )  # no all-in-one expand enum
        self.assertTrue(
            any(child.kind == "split" for node in root.walk() for child in node.children)
        )  # split forces the full-width cells
        self.assertEqual(
            [c[1][1] for c in root.named("prop")], ["scenario_picker_query"]
        )  # search stays full width on the root
        self.assertEqual([c[1][0] for c in root.named("template_list")], ["SCENARIO_UL_models"])
        self.assertGreaterEqual(len(root.named("separator")), 2)  # top and between the groups
        wm.scenario_picker_modality = "audio"
        self.assertEqual(
            self.flat_enum_values(self.draw_dialog()),
            ["image", "video", "audio", "3d", "all", "speech", "music", "sfx", "tools"],
        )  # tabs unchanged, 5 audio chips in one row
        wm.scenario_picker_modality = "3d"
        self.assertEqual([len(r) for r in self.picker.chip_rows(range(6))], [6])
        self.assertEqual([len(r) for r in self.picker.chip_rows(range(7))], [4, 3])

    def test_dialog_draw_material_lane_shows_a_centred_header_without_tabs(self):
        self.picker.prepare(bpy.context, "material")
        root = self.draw_dialog()
        self.assertEqual(self.enum_rows(root), [])
        headers = [
            (node.alignment, c[1], c[2])
            for node in root.walk()
            for c in node.named("label")
            if "PATINA" in c[2].get("text", "")
        ]
        self.assertEqual(
            headers, [("CENTER", (), {"text": "Materials: PATINA models", "icon": "MATERIAL"})]
        )
        self.assertEqual([c[1][1] for c in root.named("prop")], ["scenario_picker_query"])

    def test_helpers_do_not_touch_the_network(self):
        record = self.runtime.state.records["model_openai-gpt-image-2"]
        self.assertFalse(self.picker.ensure_thumbnail(record))
        self.assertEqual(self.picker.thumbnail_icon(record.id), 0)
        self.assertEqual(
            self.picker.category_labels(self.runtime.state.records["model_rodin-hyper3d-bang"]),
            "Parts, Retexture",
        )
        self.assertTrue(callable(self.picker.draw_model_row))

    def thumbnail_fixture(self):
        """A catalog model with an https thumbnail, a private cache and a mocked downloader.

        Restores the module-level picker rows too, so a later test's refilter cannot
        reach this https record through the real cache and downloader."""
        catalog = submodule("core.api.catalog")
        handlers = submodule("blender.handlers")
        saved = {
            key: list(value) if isinstance(value, list) else value
            for key, value in self.picker._ctx.items()
        }
        self.addCleanup(self.picker._ctx.update, saved)
        url = "https://cdn.example.invalid/thumbnail.jpg"
        record = catalog.ModelRecord.from_api(
            {
                "id": "model_thumbnail-fixture",
                "name": "Thumbnail Fixture",
                "type": "custom",
                "capabilities": ["txt2img"],
                "tags": ["sc:third-party"],
                "thumbnail": {"url": url},
            }
        )
        records = fake_records() + [record]
        handlers.dispatch(
            ("catalog", {"privacy": "public", "records": records, "detailed": records})
        )
        cache = pathlib.Path(
            self.enterContext(tempfile.TemporaryDirectory(prefix="scenario-test-thumbs-"))
        )
        self.enterContext(
            patch.object(self.picker, "_thumb_path", lambda model_id: cache / f"{model_id}.jpg")
        )
        download = self.enterContext(patch.object(self.picker, "download_file"))
        self.addCleanup(self.picker._pending_thumbs.discard, record.id)
        return record, url, cache / f"{record.id}.jpg", download

    def test_opening_the_picker_downloads_thumbnails_only_with_online_access(self):
        record, url, cached, download = self.thumbnail_fixture()
        started = []

        def tracked_thread(*args, **kwargs):
            started.append(threading.Thread(*args, **kwargs))
            return started[-1]

        # Module-local: other Blender or test threads keep the real constructor.
        self.enterContext(
            patch.object(self.picker, "threading", types.SimpleNamespace(Thread=tracked_thread))
        )
        wm = bpy.context.window_manager

        with online_access(False):
            items = self.picker.prepare(bpy.context, "image")
            self.assertIn(record.id, [item.model_id for item in items])
            wm.scenario_picker_query = "thumbnail"  # a live refilter retries uncached rows
            self.assertFalse(self.picker.ensure_thumbnail(record))
        self.assertEqual(started, [])
        download.assert_not_called()
        self.assertNotIn(record.id, self.picker._pending_thumbs)

        with online_access(True):
            self.picker.prepare(bpy.context, "image")
        self.assertEqual([thread.name for thread in started], [f"scenario-thumb-{record.id}"])
        started[0].join(timeout=5)
        self.assertFalse(started[0].is_alive())
        download.assert_called_once_with(url, cached, timeout=30, retries=1)
        self.assertNotIn(record.id, self.picker._pending_thumbs)

        # The gate only blocks downloads; an already cached thumbnail still shows offline.
        cached.write_bytes(b"cached thumbnail")
        with online_access(False):
            self.assertTrue(self.picker.ensure_thumbnail(record))
        self.assertEqual(len(started), 1)
        download.assert_called_once()

    def test_a_queued_thumbnail_download_rechecks_online_access_before_connecting(self):
        record, url, cached, download = self.thumbnail_fixture()
        held = []

        class HeldThread(threading.Thread):
            def start(self):
                held.append(self)  # the test runs it after changing the permission

        def run_worker(thread):
            threading.Thread.start(thread)
            thread.join(timeout=5)
            self.assertFalse(thread.is_alive())

        # Module-local: other Blender or test threads keep the real constructor.
        self.enterContext(
            patch.object(self.picker, "threading", types.SimpleNamespace(Thread=HeldThread))
        )
        wm = bpy.context.window_manager

        # Without a catalog the main thread mirrors online access into a module Event.
        self.assertIsNone(self.runtime.state.catalog)
        with online_access(True):
            self.picker.prepare(bpy.context, "image")
        self.assertEqual([thread.name for thread in held], [f"scenario-thumb-{record.id}"])
        with online_access(False):
            wm.scenario_picker_query = "thumbnail"  # an offline refilter mirrors the change
        run_worker(held[0])
        download.assert_not_called()
        self.assertNotIn(record.id, self.picker._pending_thumbs)

        # The selected catalog's permission Event, which the pump syncs, wins over that mirror.
        sdk_catalog = submodule("core.api.sdk_catalog")
        catalog = sdk_catalog.SDKCatalog(
            types.SimpleNamespace(authorization=lambda: None), online=True, adapter_factory=Mock()
        )
        self.addCleanup(catalog.close)
        self.enterContext(patch.object(self.runtime.state, "catalog", catalog))
        with online_access(True):
            self.assertFalse(self.picker.ensure_thumbnail(record))
        self.assertEqual(len(held), 2)
        catalog.update_online(False)  # what sync_catalog_context does once access is withdrawn
        run_worker(held[1])
        download.assert_not_called()
        self.assertNotIn(record.id, self.picker._pending_thumbs)

        # Control: the same worker downloads while the captured permission still allows it.
        catalog.update_online(True)
        with online_access(True):
            self.assertFalse(self.picker.ensure_thumbnail(record))
        self.assertEqual(len(held), 3)
        run_worker(held[2])
        download.assert_called_once_with(url, cached, timeout=30, retries=1)
        self.assertNotIn(record.id, self.picker._pending_thumbs)
