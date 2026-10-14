# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Receipt-bound static mesh replacement and durable session outcomes."""

import hashlib
import json
import math
import struct
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest.mock import patch

import bmesh
import bpy
from helpers import FIXTURES, animated_glb, parts_glb, submodule
from mathutils import Matrix


class MeshResultTests(unittest.TestCase):
    def setUp(self):
        self.module = submodule("blender.mesh_result_application")
        self.mesh = submodule("blender.mesh_application")
        self.model = submodule("blender.model_application")
        self.storage = submodule("core.jobs.store")
        self.transfers = submodule("core.jobs.transfers")
        self.before = self.model._snapshot()
        self.previous = bpy.context.scene
        self.scene = bpy.data.scenes.new("Saved mesh edit fixture")
        bpy.context.window.scene = self.scene
        data = bpy.data.meshes.new("Original source mesh")
        data.from_pydata([(0, 0, 0), (3, 0, 0), (0, 3, 0)], [], [(0, 1, 2)])
        data.update()
        self.source = bpy.data.objects.new("Original source", data)
        self.scene.collection.objects.link(self.source)
        self.source.select_set(True)
        bpy.context.view_layer.objects.active = self.source
        bpy.context.view_layer.update()
        self.temp = self.enterContext(tempfile.TemporaryDirectory())
        self.root = Path(self.temp)
        self.enterContext(patch.object(bpy.utils, "extension_path_user", return_value=self.temp))
        self.body = (FIXTURES / "synthetic/static-triangle.glb").read_bytes()
        self.path = self.root / "saved.glb"
        self.path.write_bytes(self.body)
        receipt = self.transfers.DownloadedResult(
            self.path.name, len(self.body), hashlib.sha256(self.body).hexdigest()
        )
        asset = self.storage.ResultAsset(
            "mesh", self.path.name, "model/gltf-binary", len(self.body)
        )
        self.item = self.storage.StoredResult(asset, receipt)
        self.target = self.mesh.capture_target(self.scene, self.source)
        self.session = None

    def tearDown(self):
        if self.session is not None:
            self.session.shutdown()
        bpy.context.window.scene = self.previous
        self.model._remove_new_data(self.before)

    def apply(self, **kwargs):
        options = dict(policy="REMESH", result_to_source=Matrix.Identity(4), keep_original=True)
        options.update(kwargs)
        return self.module.apply_saved_mesh(self.target, self.item, self.path, **options)

    def morph_result(self):
        length = struct.unpack_from("<I", self.body, 12)[0]
        document = json.loads(self.body[20 : 20 + length])
        mesh = document["meshes"][0]
        primitive = mesh["primitives"][0]
        primitive["targets"] = [{"POSITION": primitive["attributes"]["POSITION"]}]
        mesh["weights"] = [0.0]
        mesh["extras"] = {"targetNames": ["Fixture morph"]}
        value = json.dumps(document).encode()
        value += b" " * (-len(value) % 4)
        tail = self.body[20 + length :]
        self.body = (
            struct.pack("<4sIII4s", b"glTF", 2, 20 + len(value) + len(tail), len(value), b"JSON")
            + value
            + tail
        )
        self.path.write_bytes(self.body)
        self.item = self.storage.StoredResult(
            self.storage.ResultAsset("mesh", self.path.name, "model/gltf-binary", len(self.body)),
            self.transfers.DownloadedResult(
                self.path.name, len(self.body), hashlib.sha256(self.body).hexdigest()
            ),
        )

    def test_morph_rejection_restores_datablocks_and_allows_confirmed_local_retry(self):
        self.morph_result()
        record = self.ready_session()
        before = self.model._snapshot()
        importer = self.model._import
        imported_keys = []

        def observe(path):
            importer(path)
            imported_keys.append(len(set(bpy.data.shape_keys) - before["shape_keys"]))

        with patch.object(self.model, "_import", side_effect=observe):
            for _ in range(2):
                self.target = self.mesh.capture_target(self.scene, self.source)
                self.origin = self.session.capture(self.scene, self.source)
                with self.assertRaises(self.module.MeshResultApplicationError):
                    self.deliver(self.verify(record))
                record = self.store.get("edit")
                self.assertEqual(record.state, self.storage.JobState.APPLY_FAILED)
                self.assertEqual(self.model._snapshot(), before)
                self.mesh.validate_target(self.target)
        self.assertEqual(imported_keys, [1, 1])

    def test_successful_replacement_cleans_imported_helper_action_only(self):
        existing = bpy.data.actions.new("Keep existing action")
        existing.use_fake_user = True
        importer = self.model._import

        def add_action(path):
            importer(path)
            helper = next(obj for obj in bpy.context.scene.objects if obj.type == "EMPTY")
            helper.animation_data_create().action = bpy.data.actions.new("Imported helper action")
            group = bpy.data.node_groups.new("Unused imported group", "ShaderNodeTree")
            image = bpy.data.images.new("Unused imported image", width=1, height=1)
            image.pixels[:] = (1, 1, 1, 1)
            image.update()
            group.nodes.new("ShaderNodeTexImage").image = image

        with patch.object(self.model, "_import", side_effect=add_action):
            self.apply()
        self.assertEqual(set(bpy.data.actions) - self.before["actions"], {existing})
        self.assertNotIn("Unused imported group", bpy.data.node_groups)
        self.assertNotIn("Unused imported image", bpy.data.images)
        self.assertTrue(self.source.data.polygons)
        self.assertTrue(self.source.data.materials)

    def test_saved_glb_replaces_data_preserving_parent_transform_selection_and_original(self):
        parent = bpy.data.objects.new("Parent", None)
        self.scene.collection.objects.link(parent)
        parent.location = (7, 8, 9)
        self.source.parent = parent
        self.source.location = (3, 4, 5)
        self.source.scale = (2, 3, 4)
        bpy.context.view_layer.update()
        self.target = self.mesh.capture_target(self.scene, self.source)
        old_mesh, matrix = self.source.data, self.source.matrix_world.copy()
        result = self.apply(result_to_source=Matrix.Translation((0, 0, 4)))
        self.assertEqual(result.source, self.source)
        self.assertEqual(self.source.name, "Original source")
        self.assertEqual(self.source.parent, parent)
        self.assertEqual(self.source.matrix_world, matrix)
        self.assertEqual(result.original.data, old_mesh)
        self.assertEqual(result.original.matrix_world, matrix)
        self.assertNotEqual(self.source.data, old_mesh)
        self.assertEqual(min(v.co.x for v in self.source.data.vertices), 2)
        self.assertEqual(min(v.co.z for v in self.source.data.vertices), 4)
        self.assertEqual(self.source.data.materials[0].name, "Fixture material")
        images = set(bpy.data.images) - self.before["images"]
        self.assertTrue(images)
        self.assertTrue(all(image.packed_file and image.filepath == "" for image in images))
        self.assertEqual(set(self.scene.objects), {self.source, parent, result.original})
        self.assertEqual(bpy.context.view_layer.objects.active, self.source)
        self.assertEqual(set(bpy.context.selected_objects), {self.source})
        self.assertEqual(tuple(self.root.iterdir()), (self.path,))

    def test_without_keep_original_retains_shared_source_mesh(self):
        old_mesh = self.source.data
        alias = bpy.data.objects.new("Shared original", old_mesh)
        self.scene.collection.objects.link(alias)
        result = self.apply(keep_original=False)
        self.assertIsNone(result.original)
        self.assertEqual(alias.data, old_mesh)
        self.assertEqual(set(self.scene.objects), {self.source, alias})

    def test_saved_static_remesh_accepts_a_windowless_destination(self):
        old_mesh = self.source.data
        with bpy.context.temp_override(
            window=None, scene=self.scene, view_layer=self.scene.view_layers[0]
        ):
            result = self.apply()
            self.assertIsNone(bpy.context.window)
            self.assertEqual(result.source, self.source)
            self.assertNotEqual(self.source.data, old_mesh)
            self.assertEqual(result.original.data, old_mesh)
            self.assertEqual(bpy.context.view_layer.objects.active, self.source)
        self.assertEqual(set(self.scene.objects), {self.source, result.original})
        self.assertEqual(tuple(self.root.iterdir()), (self.path,))

    def test_changed_source_is_rejected_before_import(self):
        self.source.data.vertices[0].co.x = 1
        with patch.object(self.model, "_import") as importer:
            with self.assertRaises(self.mesh.MeshApplicationError):
                self.apply()
        importer.assert_not_called()

    def test_rename_transform_parent_and_membership_changes_invalidate_target(self):
        other = bpy.data.collections.new("Changed membership")
        self.scene.collection.children.link(other)
        parent = bpy.data.objects.new("Changed parent", None)
        self.scene.collection.objects.link(parent)
        changes = (
            lambda: setattr(self.source, "name", "Renamed source"),
            lambda: setattr(self.source, "location", (1, 0, 0)),
            lambda: setattr(self.source, "parent", parent),
            lambda: other.objects.link(self.source),
        )
        for change in changes:
            self.target = self.mesh.capture_target(self.scene, self.source)
            change()
            bpy.context.view_layer.update()
            with self.assertRaises(self.mesh.MeshApplicationError):
                self.mesh.validate_target(self.target)

    def test_deleted_target_does_not_bind_replacement_by_name(self):
        name, data = self.source.name, self.source.data
        bpy.data.objects.remove(self.source, do_unlink=True)
        replacement = bpy.data.objects.new(name, data)
        self.scene.collection.objects.link(replacement)
        with self.assertRaises(self.mesh.MeshApplicationError):
            self.apply()
        self.assertEqual(replacement.data, data)

    def test_invalid_mapping_is_rejected_before_import(self):
        with patch.object(self.model, "_import") as importer:
            with self.assertRaises(self.mesh.MeshApplicationError):
                self.apply(result_to_source=Matrix.Diagonal((-1, 1, 1, 1)))
        importer.assert_not_called()

    def test_worker_cannot_capture_or_apply(self):
        with ThreadPoolExecutor(max_workers=1) as pool:
            with self.assertRaises(self.mesh.MeshApplicationError):
                pool.submit(self.apply).result(5)
            with self.assertRaises(self.mesh.MeshApplicationError):
                pool.submit(self.mesh.capture_target, self.scene, self.source).result(5)

    def test_corrupt_saved_bytes_preserve_exact_scene(self):
        before = self.model._snapshot()
        self.path.write_bytes(self.body + b"changed")
        with self.assertRaises(self.module.MeshResultApplicationError):
            self.apply()
        self.assertEqual(self.model._snapshot(), before)
        self.mesh.validate_target(self.target)

    def test_multi_mesh_result_is_rejected_without_choosing_first(self):
        original = self.model._import
        before = self.model._snapshot()

        def add_variant(path):
            original(path)
            obj = next(obj for obj in bpy.context.scene.objects if obj.type == "MESH")
            bpy.context.scene.collection.objects.link(obj.copy())

        with patch.object(self.model, "_import", side_effect=add_variant):
            with self.assertRaises(self.module.MeshResultApplicationError):
                self.apply()
        self.assertEqual(self.model._snapshot(), before)
        self.mesh.validate_target(self.target)

    def test_multi_mesh_uv_and_retexture_results_are_rejected_without_mutation(self):
        self.matching_source()
        original = self.model._import

        def add_variant(path):
            original(path)
            obj = next(obj for obj in bpy.context.scene.objects if obj.type == "MESH")
            bpy.context.scene.collection.objects.link(obj.copy())

        mapping = Matrix.Translation((-2, 0, 0))
        for policy in ("UV", "RETEXTURE"):
            with self.subTest(policy=policy):
                before = self.model._snapshot()
                with patch.object(self.model, "_import", side_effect=add_variant):
                    with self.assertRaises(self.module.MeshResultApplicationError):
                        self.apply(policy=policy, result_to_source=mapping)
                self.assertEqual(self.model._snapshot(), before)
                self.mesh.validate_target(self.target)
        # The source matches the single-mesh result: only the variant was refused.
        self.assertEqual(self.apply(policy="UV", result_to_source=mapping).policy, "UV")

    def test_failed_cleanup_rolls_back_source_and_removes_created_data(self):
        before = self.model._snapshot()
        original = self.module._release_import

        def fail(*args):
            original(*args)
            raise RuntimeError("synthetic post-publication cleanup failure")

        with patch.object(self.module, "_release_import", side_effect=fail):
            with self.assertRaises(self.module.MeshResultApplicationError):
                self.apply()
        self.assertEqual(self.model._snapshot(), before)
        self.mesh.validate_target(self.target)

    def test_incomplete_rollback_preserves_uncertain_source_data(self):
        original = self.source.data
        with (
            patch.object(self.module, "_release_import", side_effect=RuntimeError("fixture")),
            patch.object(
                self.mesh.MeshApplication, "rollback", side_effect=RuntimeError("fixture")
            ),
        ):
            with self.assertRaisesRegex(RuntimeError, "uncertain") as raised:
                self.apply()
        self.assertNotIsInstance(raised.exception, self.module.MeshResultApplicationError)
        self.assertNotEqual(self.source.data, original)
        self.assertTrue(self.source.data.polygons)

    def test_uv_requires_exact_topology_and_preserves_original_on_mismatch(self):
        before = self.model._snapshot()
        with self.assertRaises(self.module.MeshResultApplicationError):
            self.apply(policy="UV")
        self.assertEqual(self.model._snapshot(), before)
        self.mesh.validate_target(self.target)

    def test_uv_copies_only_uvs_with_explicit_node_transform_correction(self):
        imported = self.model.apply_model(self.scene, self.item, self.path, cursor=(0, 0, 0))
        primary = next(obj for obj in imported.objects if obj.type == "MESH")
        self.source.data = primary.data.copy()
        material = bpy.data.materials.new("Keep source material")
        self.source.data.materials.clear()
        self.source.data.materials.append(material)
        expected = [tuple(loop.uv) for loop in primary.data.uv_layers.active.data]
        for loop in self.source.data.uv_layers.active.data:
            loop.uv = (0.25, 0.25)
        # The fixture node translates +2 on X; the explicit scene mapping undoes it.
        self.target = self.mesh.capture_target(self.scene, self.source)
        self.apply(policy="UV", result_to_source=Matrix.Translation((-2, 0, 0)))
        self.assertEqual(list(self.source.data.materials), [material])
        self.assertEqual(
            [tuple(loop.uv) for loop in self.source.data.uv_layers.active.data], expected
        )

    def test_saved_retexture_adopts_packed_materials_without_geometry_replacement(self):
        imported = self.model.apply_model(self.scene, self.item, self.path, cursor=(0, 0, 0))
        primary = next(obj for obj in imported.objects if obj.type == "MESH")
        self.source.data = primary.data.copy()
        material = bpy.data.materials.new("Keep original material")
        self.source.data.materials.clear()
        self.source.data.materials.append(material)
        attribute = self.source.data.attributes.new("User value", "FLOAT", "POINT")
        attribute.data[0].value = 0.25
        before = self.source.data
        geometry = [tuple(vertex.co) for vertex in before.vertices]
        self.target = self.mesh.capture_target(self.scene, self.source)
        result = self.apply(policy="RETEXTURE", result_to_source=Matrix.Translation((-2, 0, 0)))
        self.assertEqual(result.policy, "RETEXTURE")
        self.assertEqual([tuple(vertex.co) for vertex in self.source.data.vertices], geometry)
        self.assertEqual(self.source.data.attributes["User value"].data[0].value, 0.25)
        self.assertEqual(result.original.data, before)
        self.assertEqual(list(before.materials), [material])
        images = [
            node.image
            for node in self.source.data.materials[0].node_tree.nodes
            if node.type == "TEX_IMAGE"
        ]
        self.assertTrue(images)
        self.assertTrue(all(image.packed_file and image.filepath == "" for image in images))

    def test_retexture_topology_failure_preserves_source_and_saved_file(self):
        before = self.model._snapshot()
        with self.assertRaises(self.module.MeshResultApplicationError):
            self.apply(policy="RETEXTURE")
        self.assertEqual(self.model._snapshot(), before)
        self.mesh.validate_target(self.target)
        self.assertEqual(self.path.read_bytes(), self.body)

    def matching_source(self):
        """Give the source the saved result's exact indexed topology, then capture it."""
        imported = self.model.apply_model(self.scene, self.item, self.path, cursor=(0, 0, 0))
        primary = next(obj for obj in imported.objects if obj.type == "MESH")
        self.source.data = primary.data.copy()
        self.source.data.materials.clear()
        self.source.data.materials.append(bpy.data.materials.new("Matching source material"))
        self.target = self.mesh.capture_target(self.scene, self.source)

    def assert_topology_edit_preserves_transformed_source(self, policy):
        self.matching_source()
        parent = bpy.data.objects.new("Transformed parent", None)
        other = bpy.data.objects.new("Selected other", None)
        self.scene.collection.objects.link(parent)
        self.scene.collection.objects.link(other)
        extra = bpy.data.collections.new("Second membership")
        self.scene.collection.children.link(extra)
        extra.objects.link(self.source)
        parent.location = (7, 8, 9)
        parent.rotation_euler = (0.1, 0.2, 0.3)
        self.source.parent = parent
        self.source.location = (3, 4, 5)
        self.source.rotation_euler = (0.4, 0.5, 0.6)
        self.source.scale = (2, 3, 4)
        for obj in self.scene.objects:
            obj.select_set(obj == other)
        bpy.context.view_layer.objects.active = other
        bpy.context.view_layer.update()
        self.target = self.mesh.capture_target(self.scene, self.source)
        before = self.source.data
        geometry = [tuple(vertex.co) for vertex in before.vertices]
        world, local = self.source.matrix_world.copy(), self.source.matrix_local.copy()
        collections = set(self.source.users_collection)
        self.assertEqual(len(collections), 2)
        # The fixture node translates +2 on X; the explicit mapping undoes it.
        result = self.apply(policy=policy, result_to_source=Matrix.Translation((-2, 0, 0)))
        self.assertEqual(result.policy, policy)
        self.assertEqual(result.source, self.source)
        self.assertNotEqual(self.source.data, before)
        self.assertEqual([tuple(vertex.co) for vertex in self.source.data.vertices], geometry)
        for obj in (self.source, result.original):
            self.assertEqual(obj.parent, parent)
            self.assertEqual(obj.matrix_world, world)
            self.assertEqual(obj.matrix_local, local)
            self.assertEqual(set(obj.users_collection), collections)
        self.assertEqual(self.source.name, "Original source")
        self.assertEqual(result.original.data, before)
        self.assertEqual(bpy.context.view_layer.objects.active, other)
        self.assertEqual(set(bpy.context.selected_objects), {other})
        self.assertEqual(tuple(self.root.iterdir()), (self.path,))

    def test_saved_uv_preserves_transformed_parented_source_and_original(self):
        self.assert_topology_edit_preserves_transformed_source("UV")

    def test_saved_retexture_preserves_transformed_parented_source_and_original(self):
        self.assert_topology_edit_preserves_transformed_source("RETEXTURE")

    def use_parts(self, count=2):
        self.body = parts_glb(count)
        self.path.write_bytes(self.body)
        self.item = self.storage.StoredResult(
            self.storage.ResultAsset("mesh", self.path.name, "model/gltf-binary", len(self.body)),
            self.transfers.DownloadedResult(
                self.path.name, len(self.body), hashlib.sha256(self.body).hexdigest()
            ),
        )

    def test_parts_keep_source_as_parent_preserving_context_and_nested_placement(self):
        self.use_parts()
        parent = bpy.data.objects.new("Existing parent", None)
        child = bpy.data.objects.new("Existing child", None)
        self.scene.collection.objects.link(parent)
        self.scene.collection.objects.link(child)
        parent.location = (7, 8, 9)
        self.source.parent = parent
        self.source.location = (3, 4, 5)
        self.source.scale = (2, 3, 4)
        child.parent = self.source
        child.location = (2, 1, 0)
        bpy.context.view_layer.update()
        self.target = self.mesh.capture_target(self.scene, self.source)
        before = self.source.data
        matrix, child_matrix = self.source.matrix_world.copy(), child.matrix_world.copy()
        collections = tuple(self.source.users_collection)
        result = self.apply(policy="PARTS", result_to_source=Matrix.Translation((0, 0, 4)))
        self.assertEqual(result.source, self.source)
        self.assertEqual(self.source.parent, parent)
        self.assertEqual(self.source.name, self.target.name)
        self.assertEqual(self.source.matrix_world, matrix)
        self.assertEqual(child.matrix_world, child_matrix)
        self.assertEqual(tuple(self.source.users_collection), collections)
        self.assertEqual(len(self.source.data.vertices), 0)
        self.assertEqual(result.original.data, before)
        self.assertEqual(result.original.matrix_world, matrix)
        self.assertEqual(len(result.parts), 2)
        self.assertEqual(set(self.source.children), {*result.parts, child})
        for index, part in enumerate(result.parts):
            self.assertIn(f"Panel {index + 1}", part.name)
            self.assertEqual(tuple(part.users_collection), collections)
            self.assertEqual(part.matrix_world, matrix)
            self.assertEqual(min(v.co.x for v in part.data.vertices), 2 + 3 * index)
            self.assertEqual(min(v.co.z for v in part.data.vertices), 4)
            self.assertTrue(part.data.uv_layers)
            self.assertTrue(part.data.materials)
        self.assertEqual(set(bpy.context.selected_objects), {self.source})
        self.assertEqual(bpy.context.view_layer.objects.active, self.source)
        images = set(bpy.data.images) - self.before["images"]
        self.assertTrue(images)
        self.assertTrue(all(image.packed_file and image.filepath == "" for image in images))
        self.assertEqual(tuple(self.root.iterdir()), (self.path,))

    def test_parts_anchor_cannot_accumulate_another_group_as_a_source(self):
        self.use_parts()
        result = self.apply(policy="PARTS")
        self.target = self.mesh.capture_target(self.scene, self.source)
        before = self.model._snapshot()
        with self.assertRaisesRegex(self.module.MeshResultApplicationError, "surface geometry"):
            self.apply(policy="PARTS")
        self.assertEqual(self.model._snapshot(), before)
        self.assertEqual(set(self.source.children), set(result.parts))

    def test_parts_without_original_do_not_change_a_shared_source_mesh(self):
        self.use_parts()
        before = self.source.data
        alias = bpy.data.objects.new("Shared source", before)
        self.scene.collection.objects.link(alias)
        result = self.apply(policy="PARTS", keep_original=False)
        self.assertIsNone(result.original)
        self.assertEqual(alias.data, before)
        self.assertEqual(len(before.vertices), 3)
        self.assertEqual(len(self.source.data.vertices), 0)

    def test_parts_reject_single_mesh_and_excessive_part_count_without_mutation(self):
        for count in (1, 129):
            with self.subTest(count=count):
                self.use_parts(count)
                before = self.model._snapshot()
                with self.assertRaises(self.module.MeshResultApplicationError):
                    self.apply(policy="PARTS")
                self.assertEqual(self.model._snapshot(), before)
                self.mesh.validate_target(self.target)

    def test_parts_enforce_aggregate_geometry_bound_before_replacement(self):
        self.use_parts()
        before = self.model._snapshot()
        # Source is below the limit, but two independently safe parts exceed it.
        source_size = 3 + 3 + 3 + 1 + sum(len(a.data) for a in self.source.data.attributes)
        with patch.object(self.mesh, "MAX_COMPONENTS", source_size + 1):
            with self.assertRaises(self.module.MeshResultApplicationError):
                self.apply(policy="PARTS")
        self.assertEqual(self.model._snapshot(), before)
        self.mesh.validate_target(self.target)

    def test_parts_publication_failure_restores_source_and_removes_new_parts(self):
        self.use_parts()
        before = self.model._snapshot()
        publish = self.module._publish_parts

        def fail(*args):
            publish(*args)
            raise RuntimeError("fixture parts publication failure")

        with patch.object(self.module, "_publish_parts", side_effect=fail):
            with self.assertRaises(self.module.MeshResultApplicationError):
                self.apply(policy="PARTS")
        self.assertEqual(self.model._snapshot(), before)
        self.mesh.validate_target(self.target)
        self.assertEqual(self.path.read_bytes(), self.body)

    def test_parts_cleanup_failure_restores_source_after_imported_objects_are_removed(self):
        self.use_parts()
        before = self.model._snapshot()
        release = self.module._release_import

        def fail(*args):
            release(*args)
            raise RuntimeError("fixture parts cleanup failure")

        with patch.object(self.module, "_release_import", side_effect=fail):
            with self.assertRaises(self.module.MeshResultApplicationError):
                self.apply(policy="PARTS")
        self.assertEqual(self.model._snapshot(), before)
        self.mesh.validate_target(self.target)

    def test_parts_uncertain_rollback_retains_possible_applied_group(self):
        self.use_parts()
        with (
            patch.object(self.module, "_release_import", side_effect=RuntimeError("fixture")),
            patch.object(
                self.mesh.MeshApplication, "rollback", side_effect=RuntimeError("fixture")
            ),
        ):
            with self.assertRaisesRegex(RuntimeError, "uncertain") as raised:
                self.apply(policy="PARTS")
        self.assertNotIsInstance(raised.exception, self.module.MeshResultApplicationError)
        self.assertEqual(len(self.source.data.vertices), 0)
        self.assertEqual(len(self.source.children), 2)
        self.assertTrue(all(child.data.polygons for child in self.source.children))

    def ready_session(self):
        import httpx

        api = submodule("core.api.sdk_adapter")
        self.session_module = submodule("blender.job_session")
        scope = self.storage.JobScope("https://fixture.invalid/v1", "saved-mesh")
        self.store = self.storage.JobStore(self.root / "jobs.sqlite3", scope)

        def reject_network(_):
            raise AssertionError("Local mesh application must never call Scenario")

        adapter = api.SDKAdapter(
            api.Credentials("fixture-key", "fixture-secret"),
            account_id=scope.account_id,
            base_url=scope.service,
            online=lambda: True,
            transport=httpx.MockTransport(reject_network),
        )
        self.addCleanup(adapter.close)
        downloader = self.transfers.ResultDownloader(
            self.transfers.StoragePolicy(frozenset({"fixture.invalid"})),
            online_access=lambda: False,
        )
        self.session = self.session_module.JobSession(
            adapter, self.store, result_root=self.root, result_downloader=downloader
        )
        self.origin = self.session.capture(self.scene, self.source)
        record = self.store.create(
            self.storage.JobIntent(
                "edit", scope, self.origin, "model", "fixture-model", "a" * 64, "b" * 64, "1.0"
            )
        )
        for state in ("submitting", "remote", "succeeded"):
            record = self.store.transition(
                "edit",
                expected_revision=record.revision,
                state=self.storage.JobState(state),
                remote_job_id="fixture-remote" if state == "remote" else None,
            )
        record = self.store.set_results(
            "edit", (self.item.asset,), expected_revision=record.revision
        )
        record = self.store.transition(
            "edit", expected_revision=record.revision, state=self.storage.JobState.DOWNLOADING
        )
        directory = self.session._coordinator._results._directory(record)
        (directory / self.path.name).write_bytes(self.body)
        record = self.store.record_download(
            "edit", "mesh", self.item.receipt, expected_revision=record.revision
        )
        return self.store.transition(
            "edit", expected_revision=record.revision, state=self.storage.JobState.READY
        )

    def verify(self, record):
        self.session.verify_results("edit", expected_revision=record.revision).result(5)
        completion = self.session.drain()[0]
        self.assertIsNone(completion.error)
        return completion

    def deliver(self, completion, **kwargs):
        options = dict(
            destination=self.origin,
            asset_id="mesh",
            target=self.target,
            policy="REMESH",
            result_to_source=Matrix.Identity(4),
            keep_original=True,
        )
        options.update(kwargs)
        return self.session.apply_recovered_mesh(completion, **options)

    def test_session_records_success_and_consumes_owned_verification(self):
        record = self.ready_session()
        completion = self.verify(record)
        result = self.deliver(completion)
        self.assertEqual(result.record.state, self.storage.JobState.APPLIED)
        self.assertEqual(result.record.application_origin, self.origin)
        self.assertEqual(result.application.source, self.source)
        with self.assertRaises(self.session_module.OriginUnavailable):
            self.deliver(completion)

    def test_session_rejects_changed_target_before_claim(self):
        record = self.ready_session()
        completion = self.verify(record)
        self.source.data.vertices[0].co.x = 5
        with self.assertRaises(self.mesh.MeshApplicationError):
            self.deliver(completion)
        self.assertEqual(self.store.get("edit"), record)

    def test_session_known_failure_allows_only_local_retry(self):
        record = self.ready_session()
        with self.assertRaises(self.module.MeshResultApplicationError):
            self.deliver(self.verify(record), policy="UV")
        self.assertEqual(self.store.get("edit").state, self.storage.JobState.APPLY_FAILED)
        self.mesh.validate_target(self.target)

    def test_session_uncertainty_blocks_another_claim(self):
        record = self.ready_session()
        with patch.object(
            self.session_module, "apply_saved_mesh", side_effect=RuntimeError("fixture")
        ):
            with self.assertRaises(self.session_module.ModelResultUncertain):
                self.deliver(self.verify(record))
        self.assertEqual(self.store.get("edit").state, self.storage.JobState.APPLYING)

    def test_session_receipt_retry_never_replaces_mesh_again(self):
        record = self.ready_session()
        original = self.store.transition

        def fail_receipt(*args, **kwargs):
            if kwargs.get("state") == self.storage.JobState.APPLIED:
                raise OSError("fixture receipt error")
            return original(*args, **kwargs)

        with patch.object(self.store, "transition", side_effect=fail_receipt):
            with self.assertRaises(self.session_module.ModelResultUncertain) as caught:
                self.deliver(self.verify(record))
        mesh = self.source.data
        with patch.object(
            self.session_module, "apply_saved_mesh", side_effect=AssertionError("replayed")
        ):
            result = self.session.retry_model_receipt(caught.exception)
        self.assertEqual(result.record.state, self.storage.JobState.APPLIED)
        self.assertEqual(self.source.data, mesh)

    def test_completed_mesh_reuse_records_new_target_without_reopening_generation(self):
        record = self.ready_session()
        first = self.deliver(self.verify(record))
        first_mesh = self.source.data
        second = bpy.data.objects.new("Another explicit source", first_mesh.copy())
        self.scene.collection.objects.link(second)
        self.target = self.mesh.capture_target(self.scene, second)
        self.origin = self.session.capture(self.scene, second)
        result = self.deliver(self.verify(first.record))
        self.assertEqual(result.record.state, self.storage.JobState.APPLIED)
        self.assertEqual(result.record.intent, first.record.intent)
        self.assertEqual(result.record.application_origin, first.record.application_origin)
        self.assertEqual(self.source.data, first_mesh)
        local = result.record.local_applications[0]
        self.assertEqual(local.destination, self.origin)
        self.assertEqual(local.asset_ids, ("mesh",))
        self.assertEqual(local.state.value, "applied")

    def test_mesh_target_in_multiple_scenes_is_rejected(self):
        other = bpy.data.scenes.new("Other scene")
        other.collection.objects.link(self.source)
        with self.assertRaises(self.mesh.MeshApplicationError):
            self.mesh.capture_target(self.scene, self.source)

    def test_session_target_cannot_override_captured_job_destination(self):
        record = self.ready_session()
        other = bpy.data.objects.new("Wrong target", self.source.data.copy())
        self.scene.collection.objects.link(other)
        wrong = self.mesh.capture_target(self.scene, other)
        with self.assertRaises(self.session_module.OriginUnavailable):
            self.deliver(self.verify(record), target=wrong)
        self.assertEqual(self.store.get("edit"), record)

    def test_parent_transform_change_is_rejected_without_caller_depsgraph_update(self):
        parent = bpy.data.objects.new("Moving parent", None)
        self.scene.collection.objects.link(parent)
        self.source.parent = parent
        self.target = self.mesh.capture_target(self.scene, self.source)
        parent.location.x = 8
        with patch.object(self.model, "_import") as importer:
            with self.assertRaises(self.mesh.MeshApplicationError):
                self.apply()
        importer.assert_not_called()

    def test_animated_glb_still_cannot_replace_static_source(self):
        from helpers import animated_glb

        data = animated_glb()
        self.path.write_bytes(data)
        self.item = self.storage.StoredResult(
            self.storage.ResultAsset("model", self.path.name, "model/gltf-binary", len(data)),
            self.transfers.DownloadedResult(
                self.path.name, len(data), hashlib.sha256(data).hexdigest()
            ),
        )
        before = self.module.model_application._snapshot()
        with self.assertRaises(self.module.MeshResultApplicationError):
            self.module.apply_saved_mesh(
                self.target,
                self.item,
                self.path,
                policy="REMESH",
                result_to_source=Matrix.Identity(4),
                keep_original=True,
            )
        self.assertEqual(self.module.model_application._snapshot(), before)


class RigResultTests(unittest.TestCase):
    tearDown = MeshResultTests.tearDown
    apply = MeshResultTests.apply

    def setUp(self):
        MeshResultTests.setUp(self)
        self.body = animated_glb(morph=False)
        self.path.write_bytes(self.body)
        self.item = self.storage.StoredResult(
            self.storage.ResultAsset("rig", self.path.name, "model/gltf-binary", len(self.body)),
            self.transfers.DownloadedResult(
                self.path.name, len(self.body), hashlib.sha256(self.body).hexdigest()
            ),
        )
        # The native importer converts glTF Y-up to Blender Z-up.
        for vertex, position in zip(
            self.source.data.vertices, [(0, 0, 0), (1, 0, 0), (0, 0, 1)], strict=True
        ):
            vertex.co = position
        self.source.data.update()
        self.target = self.mesh.capture_target(self.scene, self.source)

    def test_rig_attachment_preserves_source_and_deforms_at_destination_fps(self):
        before = self.source.data
        result = self.apply(policy="RIG")
        self.assertEqual(result.source, self.source)
        self.assertEqual(result.original.data, before)
        self.assertEqual(len(result.rig.data.bones), 2)
        self.assertEqual(self.source.modifiers[0].object, result.rig)
        self.assertEqual(self.source.vertex_groups[0].name, "RootJoint")
        self.assertEqual(self.source.data.vertices[0].groups[0].weight, 1)
        self.assertEqual(bpy.context.view_layer.objects.active, self.source)
        self.scene.frame_set(0)
        start = (
            self.source.evaluated_get(bpy.context.evaluated_depsgraph_get())
            .data.vertices[0]
            .co.copy()
        )
        self.scene.frame_set(self.scene.render.fps)
        end = (
            self.source.evaluated_get(bpy.context.evaluated_depsgraph_get())
            .data.vertices[0]
            .co.copy()
        )
        self.assertAlmostEqual(end.x - start.x, 2, places=4)

    def test_importer_creates_no_bone_shape_helpers(self):
        before = self.model._snapshot()
        with self.model.staged_model(self.item, self.path, before, static_only=False) as (
            staging,
            objects,
        ):
            rigs = [obj for obj in objects if obj.type == "ARMATURE"]
            self.assertEqual(len(rigs), 1)
            self.assertEqual(len(rigs[0].pose.bones), 2)
            self.assertTrue(all(bone.custom_shape is None for bone in rigs[0].pose.bones))
            self.assertEqual([obj.type for obj in objects].count("MESH"), 1)
            self.assertEqual(set(bpy.data.collections), before["collections"])
            self.assertIn(staging, tuple(bpy.data.scenes))

    def test_bone_shape_helper_is_not_a_result_and_is_removed(self):
        # Blender's importer draws bones with a shared helper mesh unless told not to.
        importer = bpy.ops.import_scene.gltf
        shapes = []

        def with_bone_shapes(path):
            self.assertEqual(
                importer(
                    filepath=str(path),
                    import_pack_images=True,
                    import_select_created_objects=False,
                    import_scene_extras=False,
                    import_scene_as_collection=False,
                    bone_heuristic="BLENDER",
                    disable_bone_shape=False,
                ),
                {"FINISHED"},
            )
            rig = next(obj for obj in bpy.context.scene.objects if obj.type == "ARMATURE")
            shapes.extend({bone.custom_shape for bone in rig.pose.bones} - {None})

        objects, meshes = set(bpy.data.objects), set(bpy.data.meshes)
        collections = set(bpy.data.collections)
        with patch.object(self.model, "_import", side_effect=with_bone_shapes):
            result = self.apply(policy="RIG")
        self.assertEqual(len(shapes), 1)
        self.assertEqual(self.source.modifiers[0].object, result.rig)
        self.assertTrue(all(bone.custom_shape is None for bone in result.rig.pose.bones))
        new = set(bpy.data.objects) - objects
        self.assertEqual({obj for obj in new if obj.type == "MESH"}, {result.original})
        self.assertEqual(set(bpy.data.meshes) - meshes, {self.source.data})
        self.assertEqual(set(bpy.data.collections), collections)
        self.assertEqual(bpy.context.window.scene, self.scene)

    def test_unskinned_mesh_beside_a_skin_is_refused_not_discarded(self):
        # It may be an accessory the user wants: never drop it silently.
        importer = self.model._import

        def with_unskinned_mesh(path):
            importer(path)
            data = bpy.data.meshes.new("Accessory")
            data.from_pydata([(0, 0, 0), (1, 0, 0), (0, 1, 0)], [], [(0, 1, 2)])
            bpy.context.scene.collection.objects.link(bpy.data.objects.new("Accessory", data))

        before = self.model._snapshot()
        with (
            patch.object(self.model, "_import", side_effect=with_unskinned_mesh),
            self.assertRaises(self.module.MeshResultApplicationError),
        ):
            self.apply(policy="RIG")
        self.assertEqual(self.model._snapshot(), before)
        self.assertFalse(self.source.modifiers)
        self.mesh.validate_target(self.target)

    def test_rig_that_drives_no_mesh_fails_without_choosing_a_helper(self):
        # A clips-only result: its mesh is not skinned, so nothing is guessed.
        importer = self.model._import

        def without_skin(path):
            importer(path)
            body = next(obj for obj in bpy.context.scene.objects if obj.type == "MESH")
            body.modifiers.clear()

        before = self.model._snapshot()
        with (
            patch.object(self.model, "_import", side_effect=without_skin),
            self.assertRaises(self.module.MeshResultApplicationError),
        ):
            self.apply(policy="RIG")
        self.assertEqual(self.model._snapshot(), before)
        self.assertFalse(self.source.modifiers)
        self.mesh.validate_target(self.target)

    def test_transformed_parent_and_selection_are_preserved(self):
        parent = bpy.data.objects.new("Original parent", None)
        self.scene.collection.objects.link(parent)
        parent.location = (4, 5, 6)
        self.source.parent = parent
        self.source.location = (2, 3, 4)
        self.source.rotation_euler = (0.2, 0.3, 0.4)
        self.source.scale = (2, 3, 4)
        other = bpy.data.objects.new("Selected other", None)
        self.scene.collection.objects.link(other)
        self.source.select_set(False)
        other.select_set(True)
        bpy.context.view_layer.objects.active = other
        bpy.context.view_layer.update()
        self.target = self.mesh.capture_target(self.scene, self.source)
        world, local = self.source.matrix_world.copy(), self.source.matrix_local.copy()
        collections = tuple(self.source.users_collection)
        result = self.apply(policy="RIG")
        self.assertEqual(self.source.parent, parent)
        self.assertEqual(self.source.matrix_world, world)
        self.assertEqual(self.source.matrix_local, local)
        self.assertEqual(tuple(self.source.users_collection), collections)
        self.assertEqual(bpy.context.view_layer.objects.active, other)
        self.assertEqual(set(bpy.context.selected_objects), {other})
        self.assertEqual(result.rig.parent.parent, parent)
        self.scene.frame_set(0)
        start = (
            self.source.evaluated_get(bpy.context.evaluated_depsgraph_get())
            .data.vertices[0]
            .co.copy()
        )
        self.scene.frame_set(self.scene.render.fps)
        end = (
            self.source.evaluated_get(bpy.context.evaluated_depsgraph_get())
            .data.vertices[0]
            .co.copy()
        )
        self.assertAlmostEqual(end.x - start.x, 2, places=4)

    def test_source_material_uv_and_attributes_survive(self):
        material = bpy.data.materials.new("Source material")
        self.source.data.materials.append(material)
        uv = self.source.data.uv_layers.new(name="Keep UV")
        uv.data[0].uv = (0.25, 0.75)
        attr = self.source.data.attributes.new(name="Keep attribute", type="FLOAT", domain="POINT")
        attr.data[0].value = 42
        self.target = self.mesh.capture_target(self.scene, self.source)
        self.apply(policy="RIG", keep_original=False)
        self.assertEqual(tuple(self.source.data.materials), (material,))
        self.assertEqual(tuple(self.source.data.uv_layers["Keep UV"].data[0].uv), (0.25, 0.75))
        self.assertEqual(self.source.data.attributes["Keep attribute"].data[0].value, 42)

    def test_mismatched_geometry_or_stale_source_fails_without_mutation(self):
        for stale in (False, True):
            with self.subTest(stale=stale):
                if stale:
                    self.source.location.x += 1
                before = self.model._snapshot()
                with self.assertRaises(
                    (self.module.MeshResultApplicationError, self.mesh.MeshApplicationError)
                ):
                    self.apply(policy="RIG", result_to_source=Matrix.Translation((1, 0, 0)))
                self.assertEqual(self.model._snapshot(), before)
                self.assertFalse(self.source.modifiers)
                self.assertFalse(self.source.vertex_groups)
                self.assertTrue(self.path.exists())

    def test_morph_result_is_explicitly_rejected(self):
        body = animated_glb()
        self.path.write_bytes(body)
        self.item = self.storage.StoredResult(
            self.storage.ResultAsset("rig", self.path.name, "model/gltf-binary", len(body)),
            self.transfers.DownloadedResult(
                self.path.name, len(body), hashlib.sha256(body).hexdigest()
            ),
        )
        before = self.model._snapshot()
        with self.assertRaises(self.module.MeshResultApplicationError):
            self.apply(policy="RIG")
        self.assertEqual(self.model._snapshot(), before)
        self.mesh.validate_target(self.target)

    def test_cleanup_failure_rolls_back_source_and_all_new_rig_data(self):
        before = self.model._snapshot()
        with (
            patch.object(
                self.module,
                "_release_import",
                side_effect=RuntimeError("synthetic cleanup failure"),
            ),
            self.assertRaises(self.module.MeshResultApplicationError),
        ):
            self.apply(policy="RIG")
        self.assertEqual(self.model._snapshot(), before)
        self.mesh.validate_target(self.target)
        self.assertTrue(self.path.exists())

    def test_invalid_weights_constraints_and_extra_modifiers_are_rejected(self):
        for kind in ("weights", "constraint", "modifier"):
            with self.subTest(kind=kind):
                before = self.model._snapshot()
                original = self.model._import

                def alter(path, original=original, kind=kind):
                    original(path)
                    primary = next(obj for obj in bpy.context.scene.objects if obj.type == "MESH")
                    rig = next(obj for obj in bpy.context.scene.objects if obj.type == "ARMATURE")
                    if kind == "weights":
                        primary.vertex_groups[0].add([0], 0.5, "REPLACE")
                    elif kind == "constraint":
                        rig.pose.bones[0].constraints.new("LIMIT_LOCATION")
                    else:
                        primary.modifiers.new("Unsupported modifier", "DECIMATE")

                with (
                    patch.object(self.model, "_import", side_effect=alter),
                    self.assertRaises(self.module.MeshResultApplicationError),
                ):
                    self.apply(policy="RIG")
                self.assertEqual(self.model._snapshot(), before)
                self.mesh.validate_target(self.target)


def _skin(obj, mesh):
    """Exact source skin: modifier settings, group names and per-vertex weights."""
    return (
        tuple(mesh.modifier_settings(modifier) for modifier in obj.modifiers),
        tuple((group.name, group.lock_weight) for group in obj.vertex_groups),
        tuple(tuple((g.group, g.weight) for g in vertex.groups) for vertex in obj.data.vertices),
    )


def _rig_state(rig):
    return (
        rig.name,
        rig.data,
        tuple(tuple(row) for row in rig.matrix_world),
        tuple((bone.name, tuple(map(tuple, bone.matrix_local))) for bone in rig.data.bones),
        tuple(tuple(map(tuple, bone.matrix_basis)) for bone in rig.pose.bones),
        rig.parent,
        tuple(rig.modifiers),
        tuple(rig.constraints),
    )


class RiggedSourceTests(unittest.TestCase):
    tearDown = MeshResultTests.tearDown
    apply = MeshResultTests.apply
    ready_session = MeshResultTests.ready_session
    verify = MeshResultTests.verify
    deliver = MeshResultTests.deliver

    def setUp(self):
        from helpers import skin_to_new_rig

        RigResultTests.setUp(self)
        self.item = self.storage.StoredResult(
            self.storage.ResultAsset("mesh", self.path.name, "model/gltf-binary", len(self.body)),
            self.item.receipt,
        )
        self.rig_module = submodule("blender.rig_application")
        self.old_rig = skin_to_new_rig(self.scene, self.source)
        self.old_rig.location = (1, 2, 3)
        self.old_rig.rotation_euler = (0, 0, 0.5)
        self.source.location = (0.5, 0, 0)
        material = bpy.data.materials.new("Rigged source material")
        self.source.data.materials.append(material)
        bpy.context.view_layer.update()
        self.old_mesh = self.source.data
        self.old_skin = _skin(self.source, self.mesh)
        self.old_rig_state = _rig_state(self.old_rig)
        self.target = self.mesh.capture_target(self.scene, self.source)

    def evaluated(self, obj):
        depsgraph = bpy.context.evaluated_depsgraph_get()
        return [vertex.co.copy() for vertex in obj.evaluated_get(depsgraph).data.vertices]

    def assert_old_skin(self):
        self.assertIs(self.source.data, self.old_mesh)
        self.assertEqual(_skin(self.source, self.mesh), self.old_skin)
        self.assertEqual(_rig_state(self.old_rig), self.old_rig_state)
        self.mesh.validate_target(self.target)

    def test_capture_records_the_source_skin_for_rig(self):
        skin = self.target.skin
        self.assertIsNotNone(skin)
        self.assertIs(skin.rig, self.old_rig)
        self.assertEqual(skin.groups, (("Old bone", False),))
        self.assertEqual(self.target.context[1], self.old_rig)

    def test_rig_replaces_skin_preserving_context_and_old_rig(self):
        world, local = self.source.matrix_world.copy(), self.source.matrix_local.copy()
        collections = tuple(self.source.users_collection)
        materials = tuple(self.source.data.materials)
        name = self.source.name
        result = self.apply(policy="RIG")
        self.assertIs(result.source, self.source)
        self.assertEqual(self.source.name, name)
        self.assertEqual(self.source.matrix_world, world)
        self.assertEqual(self.source.matrix_local, local)
        self.assertEqual((self.source.parent, self.source.parent_type), (self.old_rig, "OBJECT"))
        self.assertEqual(tuple(self.source.users_collection), collections)
        self.assertEqual(tuple(self.source.data.materials), materials)
        self.assertEqual(len(self.source.modifiers), 1)
        modifier = self.source.modifiers[0]
        self.assertEqual((modifier.name, modifier.object), ("Scenario Rig", result.rig))
        self.assertNotIn("Old bone", self.source.vertex_groups)
        self.assertTrue(
            all(group.name in result.rig.data.bones for group in self.source.vertex_groups)
        )
        self.assertEqual(result.rig.parent.parent, self.old_rig)
        self.assertEqual(_rig_state(self.old_rig), self.old_rig_state)
        # The returned rig deforms the source, as for an unrigged source.
        self.scene.frame_set(0)
        start = self.evaluated(self.source)[0]
        self.scene.frame_set(self.scene.render.fps)
        self.assertAlmostEqual((self.evaluated(self.source)[0] - start).length, 2, places=4)
        # Keep original still deforms with the old rig; the source no longer does.
        original = result.original
        self.assertIs(original.data, self.old_mesh)
        self.assertEqual(_skin(original, self.mesh), self.old_skin)
        self.assertEqual((original.parent, original.matrix_local), (self.old_rig, local))
        source_before, original_before = self.evaluated(self.source), self.evaluated(original)
        self.old_rig.pose.bones["Old bone"].location = (0, 0, 1)
        bpy.context.view_layer.update()
        self.assertEqual(self.evaluated(self.source), source_before)
        self.assertNotEqual(self.evaluated(original), original_before)

    def test_skin_can_be_replaced_again(self):
        old_name = self.old_mesh.name
        first = self.apply(policy="RIG", keep_original=False)
        self.assertIsNone(first.original)
        self.assertNotIn("Scenario rollback", bpy.data.objects)
        self.assertNotIn(old_name, bpy.data.meshes)
        self.target = self.mesh.capture_target(self.scene, self.source)
        self.assertIs(self.target.skin.rig, first.rig)
        second = self.apply(policy="RIG")
        self.assertEqual(
            (self.source.modifiers[0].name, self.source.modifiers[0].object),
            ("Scenario Rig", second.rig),
        )
        self.assertEqual(second.original.modifiers[0].object, first.rig)

    def test_failures_after_replacement_restore_the_old_skin_exactly(self):
        failures = {
            "cleanup": (self.module, "_release_import"),
            "receipt": (self.rig_module, "RigApplication"),
        }
        for keep_original in (False, True):
            for kind, (owner, name) in failures.items():
                with self.subTest(keep_original=keep_original, failure=kind):
                    before = self.model._snapshot()
                    with (
                        patch.object(owner, name, side_effect=RuntimeError("synthetic")),
                        self.assertRaises(self.module.MeshResultApplicationError),
                    ):
                        self.apply(policy="RIG", keep_original=keep_original)
                    self.assertEqual(self.model._snapshot(), before)
                    self.assert_old_skin()
                    self.assertTrue(self.path.exists())

    def test_uncertain_rollback_retains_possible_applied_skin(self):
        with (
            patch.object(self.module, "_release_import", side_effect=RuntimeError("cleanup")),
            patch.object(
                self.rig_module.RigApplication, "rollback", side_effect=RuntimeError("rollback")
            ),
            self.assertRaises(RuntimeError) as raised,
        ):
            self.apply(policy="RIG")
        self.assertNotIsInstance(raised.exception, self.module.MeshResultApplicationError)
        self.assertEqual(self.source.modifiers[0].name, "Scenario Rig")
        self.assertEqual(_rig_state(self.old_rig), self.old_rig_state)

    def test_changed_skin_or_rig_makes_the_target_stale_before_import(self):
        def edit_rest():
            view_layer = bpy.context.view_layer
            view_layer.objects.active = self.old_rig
            bpy.ops.object.mode_set(mode="EDIT")
            try:
                self.old_rig.data.edit_bones["Old bone"].tail.z += 1
            finally:
                bpy.ops.object.mode_set(mode="OBJECT")
            view_layer.objects.active = self.source

        changes = {
            "weights": lambda: self.source.vertex_groups[0].add([0], 0.5, "REPLACE"),
            "group": lambda: setattr(self.source.vertex_groups[0], "name", "Renamed"),
            "modifier": lambda: setattr(
                self.source.modifiers[0], "use_deform_preserve_volume", False
            ),
            "rest": edit_rest,
            "rig transform": lambda: setattr(self.old_rig, "location", (4, 5, 6)),
            "rig name": lambda: setattr(self.old_rig, "name", "Renamed rig"),
        }
        for kind, change in changes.items():
            with self.subTest(kind=kind):
                try:
                    change()
                    bpy.context.view_layer.update()
                    with self.assertRaises(self.mesh.MeshApplicationError):
                        self.mesh.validate_target(self.target)
                    before = self.model._snapshot()
                    with (
                        patch.object(self.model, "_import") as importer,
                        self.assertRaises(self.mesh.MeshApplicationError),
                    ):
                        self.apply(policy="RIG")
                    importer.assert_not_called()
                    self.assertEqual(self.model._snapshot(), before)
                finally:
                    self.tearDown()
                    self.setUp()

    def test_posing_the_old_rig_keeps_the_target_valid(self):
        self.old_rig.pose.bones["Old bone"].rotation_quaternion = (0.9, 0.1, 0, 0)
        bpy.context.view_layer.update()
        self.mesh.validate_target(self.target)
        self.apply(policy="RIG")
        self.assertEqual(self.source.modifiers[0].name, "Scenario Rig")

    def test_static_policies_reject_rigged_source_before_import(self):
        for policy in ("REMESH", "UV", "RETEXTURE", "PARTS"):
            with self.subTest(policy=policy):
                before = self.model._snapshot()
                with (
                    patch.object(self.model, "_import") as importer,
                    self.assertRaisesRegex(self.module.MeshResultApplicationError, "RIG"),
                ):
                    self.apply(policy=policy)
                importer.assert_not_called()
                self.assertEqual(self.model._snapshot(), before)
                self.assert_old_skin()
        # The synchronous primitive keeps its static-only structure check.
        with self.assertRaises(self.mesh.MeshApplicationError):
            self.mesh.apply_mesh(
                self.scene,
                self.source,
                self.source,
                policy="REMESH",
                result_to_source=Matrix.Identity(4),
            )

    def test_unsupported_source_skins_fail_capture(self):
        modifier = None
        changes = {
            "second modifier": lambda: self.source.modifiers.new("Extra", "SUBSURF"),
            "envelopes": lambda: setattr(modifier, "use_bone_envelopes", True),
            "mask": lambda: setattr(modifier, "vertex_group", "Old bone"),
            "multi": lambda: setattr(modifier, "use_multi_modifier", True),
            "unbound": lambda: setattr(modifier, "object", None),
            "deform parent": lambda: setattr(self.source, "parent_type", "ARMATURE"),
            "groups only": lambda: self.source.modifiers.remove(modifier),
            "shape keys": lambda: self.source.shape_key_add(name="Basis"),
            "constraint": lambda: self.source.constraints.new("COPY_LOCATION"),
        }
        for kind, change in changes.items():
            with self.subTest(kind=kind):
                modifier = self.source.modifiers[0]
                try:
                    change()
                    with self.assertRaises(self.mesh.MeshApplicationError):
                        self.mesh.capture_target(self.scene, self.source)
                finally:
                    self.tearDown()
                    self.setUp()

    def test_session_receipt_retry_never_replaces_the_skin_again(self):
        record = self.ready_session()
        original = self.store.transition

        def fail_receipt(*args, **kwargs):
            if kwargs.get("state") == self.storage.JobState.APPLIED:
                raise OSError("fixture receipt error")
            return original(*args, **kwargs)

        with patch.object(self.store, "transition", side_effect=fail_receipt):
            with self.assertRaises(self.session_module.ModelResultUncertain) as caught:
                self.deliver(self.verify(record), policy="RIG")
        rig = self.source.modifiers[0].object
        before = set(bpy.data.armatures), self.source.data
        with patch.object(
            self.session_module, "apply_saved_mesh", side_effect=AssertionError("replayed")
        ):
            result = self.session.retry_model_receipt(caught.exception)
        self.assertEqual(result.record.state, self.storage.JobState.APPLIED)
        self.assertEqual((set(bpy.data.armatures), self.source.data), before)
        self.assertIs(self.source.modifiers[0].object, rig)
        self.assertEqual(_rig_state(self.old_rig), self.old_rig_state)

    def test_session_static_policy_on_rigged_source_is_rejected_before_claim(self):
        record = self.ready_session()
        completion = self.verify(record)
        with self.assertRaises(self.module.MeshResultApplicationError):
            self.deliver(completion, policy="REMESH")
        self.assertEqual(self.store.get("edit"), record)
        self.assert_old_skin()

    def test_export_sends_the_unposed_mesh_and_retains_the_rigged_target(self):
        self.ready_session()
        provenance = submodule("blender.mesh_provenance")
        self.old_rig.pose.bones["Old bone"].location = (0, 0.5, 0)
        bpy.context.view_layer.update()
        path = self.root / "source.glb"
        origin, source = provenance.export_with_source(
            bpy.context, (self.source,), path, self.session
        )
        target = self.session._mesh_sources[(origin, source)]
        self.assertIs(target.obj, self.source)
        self.assertIsNotNone(target.skin)
        data = path.read_bytes()
        length = struct.unpack_from("<I", data, 12)[0]
        document = json.loads(data[20 : 20 + length])
        binary = data[28 + length :]
        primitive = document["meshes"][0]["primitives"][0]
        self.assertNotIn("JOINTS_0", primitive["attributes"])
        accessor = document["accessors"][primitive["attributes"]["POSITION"]]
        view = document["bufferViews"][accessor["bufferView"]]
        offset = view.get("byteOffset", 0) + accessor.get("byteOffset", 0)
        values = struct.unpack_from("<" + "f" * 3 * accessor["count"], binary, offset)
        # glTF is Y-up: Blender (x, y, z) exports as (x, z, -y).
        exported = [tuple(values[index : index + 3]) for index in range(0, len(values), 3)]
        expected = [(v.co.x, v.co.z, -v.co.y) for v in self.source.data.vertices]
        for got, want in zip(exported, expected, strict=True):
            for a, b in zip(got, want, strict=True):
                self.assertAlmostEqual(a, b, places=6)


def _animation(rig):
    """The rig's assigned action and slot, and its NLA tracks with their strips."""
    data = rig.animation_data
    if data is None:
        return None
    return (
        data.action,
        data.action_slot,
        tuple(
            (track, track.name, track.mute, tuple((s.action, s.action_slot) for s in track.strips))
            for track in data.nla_tracks
        ),
    )


def _rest(rig):
    return (
        rig.name,
        rig.data,
        tuple(tuple(row) for row in rig.matrix_world),
        tuple((bone.name, tuple(map(tuple, bone.matrix_local))) for bone in rig.data.bones),
        tuple(bone.rotation_mode for bone in rig.pose.bones),
    )


class AnimateResultTests(unittest.TestCase):
    tearDown = MeshResultTests.tearDown
    apply = MeshResultTests.apply
    ready_session = MeshResultTests.ready_session
    verify = MeshResultTests.verify
    deliver = MeshResultTests.deliver

    def setUp(self):
        from helpers import skin_to_chain_rig

        MeshResultTests.setUp(self)
        self.animation = submodule("blender.animation_application")
        self.rig = skin_to_chain_rig(self.scene, self.source)
        self.use_clips()
        self.target = self.mesh.capture_target(self.scene, self.source)
        self.skin = _skin(self.source, self.mesh)
        self.timeline = self.timing()

    def use_clips(self, **options):
        from helpers import clip_glb

        self.body = clip_glb(**options)
        self.path.write_bytes(self.body)
        self.item = self.storage.StoredResult(
            self.storage.ResultAsset("mesh", self.path.name, "model/gltf-binary", len(self.body)),
            self.transfers.DownloadedResult(
                self.path.name, len(self.body), hashlib.sha256(self.body).hexdigest()
            ),
        )

    def timing(self):
        scene = self.scene
        render = scene.render
        return (
            scene.frame_start,
            scene.frame_end,
            scene.frame_current,
            render.fps,
            render.fps_base,
        )

    def assert_unchanged_source(self, objects):
        self.assertEqual(set(bpy.data.objects), objects)
        self.assertEqual(_skin(self.source, self.mesh), self.skin)
        self.assertIs(self.source.modifiers[0].object, self.rig)
        self.assertEqual(self.timing(), self.timeline)
        self.mesh.validate_target(self.target)

    def head_rise(self, clip):
        """Hips head rise and Spine rotation, in rig space, over one clip's frame range."""
        start, end = (round(frame) for frame in clip.frame_range)
        heads = []
        for frame in (start, end):
            self.scene.frame_set(frame)
            heads.append(self.rig.pose.bones["Hips"].head.copy())
        rotation = tuple(self.rig.pose.bones["Spine"].rotation_quaternion)
        self.scene.frame_set(self.timeline[2])
        return heads[1] - heads[0], rotation

    def test_clips_play_on_the_existing_rig_keeping_mesh_skin_and_timeline(self):
        import math

        objects, mesh, rest = set(bpy.data.objects), self.source.data, _rest(self.rig)
        armatures = set(bpy.data.armatures)
        result = self.apply(policy="ANIMATE")
        self.assertIs(result.source, self.source)
        self.assertIs(result.rig, self.rig)
        self.assertIsNone(result.original)
        self.assertIs(self.source.data, mesh)
        self.assertEqual(_rest(self.rig), rest)
        self.assertEqual(set(bpy.data.armatures), armatures)
        # Only the copied clips stay; the returned character is never added.
        self.assertEqual(set(bpy.data.actions) - self.before["actions"], set(result.clips))
        self.assert_unchanged_source(objects)
        first, second = result.clips
        self.assertEqual(first.name, "Chain rig Clip 1")
        data = self.rig.animation_data
        self.assertEqual((data.action, data.action_slot.identifier), (first, "OBChain rig"))
        tracks = [(track.name, track.mute, track.strips[0].action) for track in data.nla_tracks]
        self.assertEqual(tracks, [(first.name, True, first), (second.name, True, second)])
        self.assertEqual(data.nla_tracks[1].strips[0].action_slot, second.slots[0])
        # A 0.01 centimetre rig's root motion lands in this rig's metre units.
        rise, rotation = self.head_rise(first)
        self.assertAlmostEqual(rise.z, 1, places=3)
        self.assertAlmostEqual(rise.x, 0, places=3)
        expected = (math.cos(0.25), math.sin(0.25), 0, 0)
        for got, want in zip(rotation, expected, strict=True):
            self.assertAlmostEqual(got, want, places=3)
        self.assertEqual(self.timing(), self.timeline)

    def test_previous_action_is_kept_in_nla_and_restored_after_failure(self):
        # The rig's animation may change after review: application keeps what is there.
        data = self.rig.animation_data_create()
        kept = data.nla_tracks.new()
        kept.name = "User track"
        hips = self.rig.pose.bones["Hips"]
        hips.keyframe_insert("location", frame=1)
        previous = data.action
        previous.name = "User walk"
        hips.location = (0, 0, 0)
        self.mesh.validate_target(self.target)
        before = _animation(self.rig)
        track = self.animation._track
        failures = {
            "cleanup": (self.module, "_release_import", RuntimeError("synthetic")),
            "receipt": (self.animation, "AnimationApplication", RuntimeError("synthetic")),
            # A clip track that fails after Blender created it.
            "track": (
                self.animation,
                "_track",
                lambda data, name, action, slot: track(data, name, object(), slot),
            ),
        }
        for kind, (owner, name, effect) in failures.items():
            with self.subTest(failure=kind):
                snapshot = self.model._snapshot()
                with (
                    patch.object(owner, name, side_effect=effect),
                    self.assertRaises(self.module.MeshResultApplicationError),
                ):
                    self.apply(policy="ANIMATE")
                self.assertEqual(self.model._snapshot(), snapshot)
                self.assertEqual(_animation(self.rig), before)
                self.assertTrue(self.path.exists())
        result = self.apply(policy="ANIMATE")
        first = result.clips[0]
        self.assertEqual((data.action, data.action_slot.identifier), (first, "OBChain rig"))
        names = [(track.name, track.mute) for track in data.nla_tracks]
        self.assertEqual(
            names,
            [("User track", False), ("User walk", True)]
            + [(clip.name, True) for clip in result.clips],
        )
        self.assertIs(data.nla_tracks[1].strips[0].action, previous)
        self.assertEqual(data.nla_tracks[1].strips[0].action_slot.identifier, "OBChain rig")

    def test_clips_apply_again_keeping_the_earlier_clip(self):
        first = self.apply(policy="ANIMATE")
        self.target = self.mesh.capture_target(self.scene, self.source)
        second = self.apply(policy="ANIMATE")
        data = self.rig.animation_data
        self.assertIs(data.action, second.clips[0])
        self.assertNotEqual(second.clips[0], first.clips[0])
        # The earlier active clip is kept twice: its own track and the previous-action one.
        actions = [track.strips[0].action for track in data.nla_tracks]
        self.assertEqual(actions.count(first.clips[0]), 2)
        self.assertEqual(len(actions), 5)

    def test_smaller_rest_differences_and_another_scale_are_accepted(self):
        from helpers import CHAIN

        # Spine leans about 5.7 degrees; a two-unit rig at object scale 1 halves its keys.
        bones = (CHAIN[0], ("Spine", "Hips", (0, 0, 1.2), (0, 0.04, 1.6)), CHAIN[2])
        self.use_clips(bones=bones, unit=2.0, scale=1.0, clips=(1.0,))
        result = self.apply(policy="ANIMATE")
        rise, _ = self.head_rise(result.clips[0])
        self.assertAlmostEqual(rise.z, 1, places=3)

    def test_incompatible_rigs_and_results_fail_without_mutation(self):
        from helpers import CHAIN

        hips, spine, head = CHAIN
        cases = {
            "missing bone": dict(bones=(hips, spine, ("Skull", *head[1:]))),
            "hierarchy": dict(bones=(hips, spine, (head[0], "Hips", *head[2:]))),
            "rest": dict(bones=(hips, ("Spine", "Hips", (0, 0, 1.2), (0, 0.3, 1.6)), head)),
            "no clips": dict(clips=()),
            "rotation mode": dict(),
        }
        for kind, options in cases.items():
            with self.subTest(kind=kind):
                try:
                    self.use_clips(**options)
                    if kind == "rotation mode":
                        self.rig.pose.bones["Spine"].rotation_mode = "XYZ"
                    objects, before = set(bpy.data.objects), self.model._snapshot()
                    with self.assertRaises(self.module.MeshResultApplicationError):
                        self.apply(policy="ANIMATE")
                    self.assertEqual(self.model._snapshot(), before)
                    self.assertIsNone(_animation(self.rig))
                    self.assert_unchanged_source(objects)
                    self.assertTrue(self.path.exists())
                finally:
                    self.tearDown()
                    self.setUp()

    def test_changed_rig_is_stale_before_import(self):
        self.rig.location.x += 1
        bpy.context.view_layer.update()
        before = self.model._snapshot()
        with (
            patch.object(self.model, "_import") as importer,
            self.assertRaises(self.mesh.MeshApplicationError),
        ):
            self.apply(policy="ANIMATE")
        importer.assert_not_called()
        self.assertEqual(self.model._snapshot(), before)
        self.assertIsNone(_animation(self.rig))

    def test_policy_guards_hold_before_import(self):
        before = self.model._snapshot()
        with (
            patch.object(self.model, "_import") as importer,
            self.assertRaisesRegex(self.module.MeshResultApplicationError, "ANIMATE"),
        ):
            self.apply(policy="REMESH")
        # An unskinned mesh has no rig to animate.
        data = bpy.data.meshes.new("Plain mesh")
        data.from_pydata([(0, 0, 0), (1, 0, 0), (0, 1, 0)], [], [(0, 1, 2)])
        plain = bpy.data.objects.new("Plain", data)
        self.scene.collection.objects.link(plain)
        self.target = self.mesh.capture_target(self.scene, plain)
        with (
            patch.object(self.model, "_import") as unskinned,
            self.assertRaisesRegex(self.module.MeshResultApplicationError, "RIG"),
        ):
            self.apply(policy="ANIMATE")
        importer.assert_not_called()
        unskinned.assert_not_called()
        bpy.data.objects.remove(plain)
        bpy.data.meshes.remove(data)
        self.assertLessEqual(self.model._snapshot()["actions"], before["actions"])
        self.assertIsNone(_animation(self.rig))

    def test_session_receipt_retry_never_applies_clips_again(self):
        record = self.ready_session()
        original = self.store.transition

        def fail_receipt(*args, **kwargs):
            if kwargs.get("state") == self.storage.JobState.APPLIED:
                raise OSError("fixture receipt error")
            return original(*args, **kwargs)

        with patch.object(self.store, "transition", side_effect=fail_receipt):
            with self.assertRaises(self.session_module.ModelResultUncertain) as caught:
                self.deliver(self.verify(record), policy="ANIMATE")
        state, actions = _animation(self.rig), set(bpy.data.actions)
        with patch.object(
            self.session_module, "apply_saved_mesh", side_effect=AssertionError("replayed")
        ):
            result = self.session.retry_model_receipt(caught.exception)
        self.assertEqual(result.record.state, self.storage.JobState.APPLIED)
        self.assertEqual((_animation(self.rig), set(bpy.data.actions)), (state, actions))


def _rounded(vector):
    return tuple(round(component, 4) for component in vector)


def _corner_keys(mesh):
    """Stable (face centre, corner position) keys, independent of vertex order."""
    keys = []
    for polygon in mesh.polygons:
        centre = _rounded(polygon.center)
        keys.extend(
            (centre, _rounded(mesh.vertices[mesh.loops[loop].vertex_index].co))
            for loop in polygon.loop_indices
        )
    return keys


def _uvs(mesh, layer):
    return {key: tuple(item.uv) for key, item in zip(_corner_keys(mesh), layer.data, strict=True)}


class MatchedResultTests(unittest.TestCase):
    """Exported results that come back triangulated, seam-split or reordered."""

    tearDown = MeshResultTests.tearDown
    apply = MeshResultTests.apply

    def setUp(self):
        MeshResultTests.setUp(self)
        self.export = submodule("blender.mesh_export")
        data = self.source.data
        data.clear_geometry()
        mesh = bmesh.new()
        bmesh.ops.create_cube(mesh, size=2.0)
        ring = [
            mesh.verts.new((3 + math.cos(step * math.tau / 5), math.sin(step * math.tau / 5), 0))
            for step in range(5)
        ]
        mesh.faces.new(ring)
        mesh.to_mesh(data)
        mesh.free()
        for polygon in data.polygons:
            polygon.use_smooth = polygon.index % 2 == 0
            polygon.material_index = polygon.index % 2
        layer = data.uv_layers.new(name="Source UV")
        for index, item in enumerate(layer.data):
            item.uv = (index / 40, 0.5)
        for name in ("Source A", "Source B"):
            data.materials.append(bpy.data.materials.new(name))
        data.update()
        # Far from the scene origin, with rotation and nonuniform scale on both levels.
        parent = bpy.data.objects.new("Matched parent", None)
        self.scene.collection.objects.link(parent)
        parent.location = (400, -250, 120)
        parent.rotation_euler = (0.3, 0.1, 0.7)
        parent.scale = (1.5, 1.5, 1.5)
        self.source.parent = parent
        self.source.location = (2, 3, 4)
        self.source.rotation_euler = (0.2, 0.3, 0.4)
        self.source.scale = (2, 3, 4)
        bpy.context.view_layer.update()
        self.recapture()

    def recapture(self):
        self.target = self.mesh.capture_target(self.scene, self.source)
        self.mapping = self.source.matrix_world.inverted()
        self.geometry = [tuple(vertex.co) for vertex in self.source.data.vertices]

    def result(self, change):
        """Export an edited copy of the source with the plugin's Edit 3D exporter."""
        copy = self.source.copy()
        copy.data = self.source.data.copy()
        self.scene.collection.objects.link(copy)
        objects = change(copy) or [copy]
        bpy.context.view_layer.update()
        # Other fixture scenes stay out: the export uses only the active scene.
        self.export.export_glb(bpy.context, objects, str(self.path))
        for obj in objects:
            data, kind = obj.data, obj.type
            bpy.data.objects.remove(obj)
            (bpy.data.meshes if kind == "MESH" else bpy.data.armatures).remove(data)
        # Flush these scene edits now, so a later capture sees a settled scene.
        bpy.context.view_layer.update()
        self.body = self.path.read_bytes()
        self.item = self.storage.StoredResult(
            self.storage.ResultAsset("mesh", self.path.name, "model/gltf-binary", len(self.body)),
            self.transfers.DownloadedResult(
                self.path.name, len(self.body), hashlib.sha256(self.body).hexdigest()
            ),
        )

    @staticmethod
    def islands(copy, layer=None):
        """Give every face its own UV island, so the exporter splits each seam."""
        layer = layer or copy.data.uv_layers.active
        for polygon in copy.data.polygons:
            for corner, loop in enumerate(polygon.loop_indices):
                layer.data[loop].uv = (0.1 * polygon.index + 0.01 * corner, 0.2 + 0.05 * corner)
        return _uvs(copy.data, layer)

    def assert_unchanged(self, before, reason, **kwargs):
        with self.assertRaises(self.module.MeshResultApplicationError) as raised:
            self.apply(**{"result_to_source": self.mapping, **kwargs})
        self.assertIn(reason, raised.exception.reason)
        self.assertEqual(self.model._snapshot(), before)
        self.mesh.validate_target(self.target)
        self.assertEqual(self.path.read_bytes(), self.body)

    def assert_geometry_kept(self):
        self.assertEqual([tuple(vertex.co) for vertex in self.source.data.vertices], self.geometry)
        self.assertEqual(len(self.source.data.polygons), 7)

    def assert_uvs(self, layer, expected):
        actual = _uvs(self.source.data, layer)
        self.assertEqual(actual.keys(), expected.keys())
        for key, value in expected.items():
            for a, b in zip(actual[key], value, strict=True):
                self.assertAlmostEqual(a, b, places=5)

    def test_uv_applies_triangulated_seam_split_result_to_transformed_source(self):
        expected = {}
        self.result(lambda copy: expected.update(self.islands(copy)))
        materials = list(self.source.data.materials)
        indices = [polygon.material_index for polygon in self.source.data.polygons]
        result = self.apply(policy="UV", result_to_source=self.mapping)
        self.assertEqual(result.policy, "UV")
        self.assert_geometry_kept()
        self.assertEqual(list(self.source.data.materials), materials)
        self.assertEqual([p.material_index for p in self.source.data.polygons], indices)
        self.assertEqual(self.source.data.uv_layers.active.name, "Source UV")
        self.assert_uvs(self.source.data.uv_layers.active, expected)

    def test_uv_applies_reordered_vertices_and_faces(self):
        expected = {}

        def reorder(copy):
            mesh = bmesh.new()
            mesh.from_mesh(copy.data)
            mesh.verts.sort(key=lambda vertex: -vertex.index)
            mesh.faces.sort(key=lambda face: -face.index)
            mesh.to_mesh(copy.data)
            mesh.free()
            expected.update(self.islands(copy))

        self.result(reorder)
        self.apply(policy="UV", result_to_source=self.mapping)
        self.assert_geometry_kept()
        self.assert_uvs(self.source.data.uv_layers.active, expected)

    def test_uv_resolves_a_seam_split_source_by_face(self):
        mesh = bmesh.new()
        mesh.from_mesh(self.source.data)
        mesh.edges.ensure_lookup_table()
        bmesh.ops.split_edges(mesh, edges=[mesh.edges[0]])
        mesh.to_mesh(self.source.data)
        mesh.free()
        self.source.data.update()
        self.recapture()
        expected = {}
        self.result(lambda copy: expected.update(self.islands(copy)))
        self.apply(policy="UV", result_to_source=self.mapping)
        self.assert_geometry_kept()
        self.assert_uvs(self.source.data.uv_layers.active, expected)

    def test_retexture_adopts_split_result_materials_and_uv_layers(self):
        expected = {}
        faces = {}

        def retexture(copy):
            copy.data.materials.clear()
            for name in ("Result A", "Result B"):
                copy.data.materials.append(bpy.data.materials.new(name))
            for polygon in copy.data.polygons:
                polygon.material_index = 1 if polygon.index < 3 else 0
                faces[_rounded(polygon.center)] = ("Result A", "Result B")[polygon.material_index]
            expected["Source UV"] = self.islands(copy)
            detail = copy.data.uv_layers.new(name="Detail UV")
            for index, item in enumerate(detail.data):
                item.uv = (0.75, index / 30)
            expected["Detail UV"] = _uvs(copy.data, detail)

        self.result(retexture)
        result = self.apply(policy="RETEXTURE", result_to_source=self.mapping)
        self.assertEqual(result.policy, "RETEXTURE")
        self.assert_geometry_kept()
        data = self.source.data
        for polygon in data.polygons:
            name = data.materials[polygon.material_index].name
            self.assertTrue(name.startswith(faces[_rounded(polygon.center)]), name)
        self.assertEqual(len(data.uv_layers), 2)
        # glTF does not keep UV names; match each imported layer by its values.
        for layer in data.uv_layers:
            values = _uvs(data, layer)
            name = min(
                expected,
                key=lambda name, values=values: sum(
                    abs(a - b)
                    for key, uv in expected[name].items()
                    for a, b in zip(values[key], uv, strict=True)
                ),
            )
            self.assert_uvs(layer, expected.pop(name))
        self.assertFalse(expected)

    def fit(self):
        rows = [tuple(tuple(row) for row in matrix) for matrix in (self.mapping, Matrix())]
        return self.mesh.FitRequest((("WORLD", rows[0]), ("LOCAL", rows[1])))

    @staticmethod
    def regime(copy, *, bake, normalize):
        """Mimic provider coordinates: baked or dropped node transform, then normalized."""
        if bake:
            copy.data.transform(copy.matrix_world)
        copy.parent = None
        copy.matrix_world = Matrix()
        if normalize:
            low = [min(v.co[axis] for v in copy.data.vertices) for axis in range(3)]
            high = [max(v.co[axis] for v in copy.data.vertices) for axis in range(3)]
            scale = normalize / max(b - a for a, b in zip(low, high, strict=True))
            centre = [(a + b) / 2 for a, b in zip(low, high, strict=True)]
            copy.data.transform(Matrix.Scale(scale, 4) @ Matrix.Translation([-c for c in centre]))

    def test_fit_verifies_normalized_and_rescaled_provider_coordinates(self):
        for bake, normalize, base in (
            (True, 1.0, "WORLD"),
            (True, None, "WORLD"),
            (False, 2.0, "LOCAL"),
        ):
            with self.subTest(bake=bake, normalize=normalize):
                expected = {}

                def change(copy, bake=bake, normalize=normalize, expected=expected):
                    expected.update(self.islands(copy))
                    self.regime(copy, bake=bake, normalize=normalize)
                    if normalize is None:
                        # World coordinates in centimetres.
                        copy.data.transform(Matrix.Scale(100, 4))

                self.result(change)
                strict = self.mapping if base == "WORLD" else Matrix()
                self.assert_unchanged(self.model._snapshot(), "differs", policy="UV")
                result = self.apply(policy="UV", result_to_source=self.fit())
                self.assertEqual(result.fitted_from, base)
                self.assert_geometry_kept()
                self.assert_uvs(self.source.data.uv_layers.active, expected)
                self.assertNotEqual(Matrix(result.mapping), strict)
                self.recapture()

    def test_strict_world_accepts_baked_world_vertices(self):
        expected = {}

        def change(copy):
            expected.update(self.islands(copy))
            self.regime(copy, bake=True, normalize=None)

        self.result(change)
        result = self.apply(policy="UV", result_to_source=self.mapping)
        self.assertIsNone(result.fitted_from)
        self.assert_uvs(self.source.data.uv_layers.active, expected)

    def test_fit_fails_closed_when_both_bases_fit_differently(self):
        self.source.parent = None
        self.source.matrix_basis = Matrix.Rotation(math.pi / 2, 4, "Z")
        mesh = bmesh.new()
        mesh.from_mesh(self.source.data)
        mesh.faces.ensure_lookup_table()
        bmesh.ops.delete(mesh, geom=list(mesh.faces[6].verts), context="VERTS")
        mesh.to_mesh(self.source.data)
        mesh.free()
        bpy.context.view_layer.update()
        self.recapture()
        self.result(lambda copy: self.regime(copy, bake=True, normalize=1.0))
        # A cube rotated a quarter turn fits both bases with different corners.
        self.assert_unchanged(
            self.model._snapshot(), "several ways", policy="UV", result_to_source=self.fit()
        )
        self.apply(policy="UV", result_to_source=self.mapping @ Matrix.Scale(2, 4))

    def test_fit_is_refused_for_remesh_and_parts(self):
        for policy in ("REMESH", "PARTS"):
            with self.subTest(policy=policy):
                with self.assertRaises(self.module.MeshResultApplicationError):
                    self.apply(policy=policy, result_to_source=self.fit())
                self.mesh.validate_target(self.target)

    def split(self, copy, materials=None):
        """Return the copy as two result meshes, one per source material."""
        other = copy.copy()
        other.data = copy.data.copy()
        self.scene.collection.objects.link(other)
        for obj, keep in ((copy, 0), (other, 1)):
            mesh = bmesh.new()
            mesh.from_mesh(obj.data)
            bmesh.ops.delete(
                mesh, geom=[f for f in mesh.faces if f.material_index != keep], context="FACES"
            )
            mesh.to_mesh(obj.data)
            mesh.free()
        if materials:
            # Each mesh's faces use its first slot; shared slots must merge once.
            for obj, names in zip((copy, other), materials, strict=True):
                obj.data.materials.clear()
                for name in names:
                    material = bpy.data.materials.get(name) or bpy.data.materials.new(name)
                    obj.data.materials.append(material)
                for polygon in obj.data.polygons:
                    polygon.material_index = 0
        return [copy, other]

    def test_several_result_meshes_form_one_surface(self):
        expected = {}

        def change(copy):
            expected.update(self.islands(copy))
            return self.split(copy)

        self.result(change)
        self.apply(policy="UV", result_to_source=self.fit())
        self.assert_geometry_kept()
        self.assert_uvs(self.source.data.uv_layers.active, expected)

    def test_retexture_merges_materials_from_several_result_meshes(self):
        def change(copy):
            self.islands(copy)
            return self.split(copy, materials=(("Result A",), ("Result B", "Result A")))

        self.result(change)
        self.apply(policy="RETEXTURE", result_to_source=self.mapping)
        data = self.source.data
        names = [material.name.split(".")[0] for material in data.materials]
        self.assertEqual(names, ["Result A", "Result B"])
        for polygon in data.polygons:
            # Source faces with material 0 went to the first mesh, 1 to the second.
            self.assertEqual(polygon.material_index, polygon.index % 2)

    def test_session_applies_a_matched_uv_result_once(self):
        expected = {}
        self.result(lambda copy: expected.update(self.islands(copy)))
        record = self.ready_session()
        applied = self.deliver(self.verify(record), policy="UV", result_to_source=self.mapping)
        self.assertEqual(applied.record.state, self.storage.JobState.APPLIED)
        self.assert_uvs(self.source.data.uv_layers.active, expected)

    ready_session = MeshResultTests.ready_session
    verify = MeshResultTests.verify
    deliver = MeshResultTests.deliver

    def test_changed_geometry_fails_closed_with_a_reason(self):
        def moved(copy):
            copy.data.vertices[0].co.x += 0.01

        def extra(copy):
            mesh = bmesh.new()
            mesh.from_mesh(copy.data)
            corners = {_rounded(vertex.co): vertex for vertex in mesh.verts}
            mesh.faces.new([corners[(-1, -1, -1)], corners[(1, 1, -1)], corners[(1, 1, 1)]])
            mesh.to_mesh(copy.data)
            mesh.free()

        def missing(copy):
            mesh = bmesh.new()
            mesh.from_mesh(copy.data)
            mesh.faces.ensure_lookup_table()
            bmesh.ops.delete(mesh, geom=[mesh.faces[0]], context="FACES_ONLY")
            mesh.to_mesh(copy.data)
            mesh.free()

        def triangulated(copy):
            mesh = bmesh.new()
            mesh.from_mesh(copy.data)
            mesh.faces.ensure_lookup_table()
            bmesh.ops.triangulate(mesh, faces=[mesh.faces[0]])
            mesh.to_mesh(copy.data)
            mesh.free()
            return copy

        def inner_seam(copy):
            triangulated(copy)
            self.islands(copy)

        def inner_material(copy):
            triangulated(copy)
            first = next(p for p in copy.data.polygons if len(p.vertices) == 3)
            first.material_index = 1 - first.material_index

        cases = (
            ("UV", moved, "differs from the source at"),
            ("RETEXTURE", moved, "differs from the source at"),
            ("UV", extra, "1 face outside any single source face"),
            ("UV", missing, "missing 1 source face"),
            ("UV", inner_seam, "splits UV coordinates"),
            ("RETEXTURE", inner_material, "several materials inside 1 source face"),
        )
        for policy, change, reason in cases:
            with self.subTest(policy=policy, change=change.__name__):
                self.result(change)
                self.assert_unchanged(self.model._snapshot(), reason, policy=policy)

    def test_coincident_duplicate_source_faces_are_ambiguous(self):
        mesh = bmesh.new()
        mesh.from_mesh(self.source.data)
        mesh.faces.ensure_lookup_table()
        bmesh.ops.duplicate(mesh, geom=[mesh.faces[6]])
        mesh.to_mesh(self.source.data)
        mesh.free()
        self.source.data.update()
        self.recapture()
        self.result(lambda copy: None)
        self.assert_unchanged(self.model._snapshot(), "ambiguous", policy="UV")


class MatchedRigTests(unittest.TestCase):
    """A returned skin on an exported, triangulated copy of a transformed source."""

    setUp = MatchedResultTests.setUp
    tearDown = MeshResultTests.tearDown
    apply = MeshResultTests.apply
    recapture = MatchedResultTests.recapture
    result = MatchedResultTests.result
    assert_unchanged = MatchedResultTests.assert_unchanged
    assert_geometry_kept = MatchedResultTests.assert_geometry_kept

    def rig(self, copy, weights, move=None):
        world = self.source.matrix_world.copy()
        copy.parent = None
        copy.matrix_world = world
        armature = bpy.data.objects.new("Returned rig", bpy.data.armatures.new("Returned rig"))
        self.scene.collection.objects.link(armature)
        armature.location = world.translation
        with bpy.context.temp_override(active_object=armature, object=armature):
            bpy.context.view_layer.objects.active = armature
            bpy.ops.object.mode_set(mode="EDIT")
            root = armature.data.edit_bones.new("Root")
            root.head, root.tail = (0, 0, 0), (0, 0, 1)
            tip = armature.data.edit_bones.new("Tip")
            tip.head, tip.tail, tip.parent = (0, 0, 1), (0, 0, 2), root
            bpy.ops.object.mode_set(mode="OBJECT")
        bpy.context.view_layer.update()
        copy.parent = armature
        copy.matrix_world = world
        groups = [copy.vertex_groups.new(name=name) for name in ("Root", "Tip")]
        for vertex in copy.data.vertices:
            share = (vertex.co.x + 1) / 5
            groups[0].add([vertex.index], 1 - share, "REPLACE")
            groups[1].add([vertex.index], share, "REPLACE")
            # Files omit zero weights.
            weights[_rounded(vertex.co)] = {
                name: weight for name, weight in (("Root", 1 - share), ("Tip", share)) if weight > 0
            }
        copy.modifiers.new("Armature", "ARMATURE").object = armature
        if move:
            move(copy)
        return [copy, armature]

    def test_rig_attaches_triangulated_split_result_weights(self):
        weights = {}
        self.result(lambda copy: self.rig(copy, weights))
        material = list(self.source.data.materials)
        result = self.apply(policy="RIG", result_to_source=self.mapping)
        self.assertEqual(result.policy, "RIG")
        self.assert_geometry_kept()
        self.assertEqual(list(self.source.data.materials), material)
        self.assert_rest_pose()
        self.assertEqual(self.source.modifiers[0].object, result.rig)
        names = [group.name for group in self.source.vertex_groups]
        for vertex in self.source.data.vertices:
            actual = {names[group.group]: group.weight for group in vertex.groups}
            expected = weights[_rounded(vertex.co)]
            self.assertEqual(actual.keys(), expected.keys())
            for name, weight in expected.items():
                self.assertAlmostEqual(actual[name], weight, places=4)

    def test_rig_with_changed_geometry_fails_closed(self):
        def move(copy):
            copy.data.vertices[2].co.z += 0.05

        self.result(lambda copy: self.rig(copy, {}, move))
        self.assert_unchanged(self.model._snapshot(), "differs from the source at", policy="RIG")
        self.assertFalse(self.source.modifiers)
        self.assertFalse(self.source.vertex_groups)

    fit = MatchedResultTests.fit

    def assert_rest_pose(self):
        """At rest, the attached rig must leave every source vertex where it was."""
        self.scene.frame_set(0)
        bpy.context.view_layer.update()
        evaluated = self.source.evaluated_get(bpy.context.evaluated_depsgraph_get()).data
        for vertex, position in zip(evaluated.vertices, self.geometry, strict=True):
            for a, b in zip(vertex.co, position, strict=True):
                self.assertAlmostEqual(a, b, places=3)

    def test_rig_fit_scales_the_rig_group_onto_a_normalized_skin(self):
        weights = {}

        def normalized(copy):
            objects = self.rig(copy, weights)
            # A provider-style rig: the whole skinned character at half size, moved.
            armature = objects[1]
            armature.matrix_world = (
                Matrix.Translation((5, 0, -2)) @ Matrix.Scale(0.5, 4) @ armature.matrix_world
            )
            return objects

        self.result(normalized)
        self.assert_unchanged(self.model._snapshot(), "differs", policy="RIG")
        result = self.apply(policy="RIG", result_to_source=self.fit())
        self.assertEqual(result.fitted_from, "WORLD")
        fit = Matrix(result.mapping) @ self.mapping.inverted()
        self.assertAlmostEqual(fit.to_scale().x, 2, places=4)
        self.assert_geometry_kept()
        self.assert_rest_pose()

    def test_rig_refuses_an_unskinned_mesh_beside_the_skin_with_a_reason(self):
        weights = {}

        def helper(copy):
            objects = self.rig(copy, weights)
            extra = bpy.data.objects.new("Accessory", bpy.data.meshes.new("Accessory"))
            extra.data.from_pydata([(0, 0, 0), (0.1, 0, 0), (0, 0.1, 0)], [], [(0, 1, 2)])
            self.scene.collection.objects.link(extra)
            extra.parent = objects[1]
            return [*objects, extra]

        self.result(helper)
        self.assert_unchanged(self.model._snapshot(), "does not skin", policy="RIG")
        self.assertFalse(self.source.modifiers)

    def test_rig_replaces_an_existing_skin_from_a_normalized_triangulated_result(self):
        from helpers import skin_to_new_rig

        old_rig = skin_to_new_rig(self.scene, self.source, parent=False)
        old_state = _rig_state(old_rig)
        self.recapture()
        self.assertIsNotNone(self.target.skin)
        weights = {}

        def normalized(copy):
            # The upload carries no old skin; the provider returns its own at half size.
            copy.modifiers.clear()
            copy.vertex_groups.clear()
            objects = self.rig(copy, weights)
            armature = objects[1]
            armature.matrix_world = (
                Matrix.Translation((5, 0, -2)) @ Matrix.Scale(0.5, 4) @ armature.matrix_world
            )
            return objects

        self.result(normalized)
        result = self.apply(policy="RIG", result_to_source=self.fit())
        self.assertEqual(result.fitted_from, "WORLD")
        self.assert_geometry_kept()
        self.assertEqual([m.object for m in self.source.modifiers], [result.rig])
        self.assertEqual({g.name for g in self.source.vertex_groups}, {"Root", "Tip"})
        self.assertEqual(_rig_state(old_rig), old_state)
        self.assertEqual(result.original.modifiers[0].object, old_rig)
        self.assert_rest_pose()
