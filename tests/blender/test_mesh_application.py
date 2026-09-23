# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Local mesh fixtures exercise the installed synchronous application boundary."""

import unittest
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch

import bpy
from helpers import submodule
from mathutils import Matrix


class MeshApplicationTests(unittest.TestCase):
    def setUp(self):
        self.module = submodule("blender.mesh_application")
        self.previous = bpy.context.scene
        self.scene = bpy.data.scenes.new("Mesh application fixture")
        bpy.context.window.scene = self.scene
        self.original_objects = set(bpy.data.objects)
        self.original_meshes = set(bpy.data.meshes)
        self.original_materials = set(bpy.data.materials)
        self.original_collections = set(bpy.data.collections)
        self.receipts = []
        self.source = self.mesh("Source")
        self.result = self.mesh("Result")
        self.source_material = bpy.data.materials.new("Source material")
        self.result_material = bpy.data.materials.new("Result material")
        self.source.data.materials.append(self.source_material)
        self.result.data.materials.append(self.result_material)
        self.uv(self.source, "Source UV", 0.0)
        self.uv(self.result, "Result UV", 0.25)
        bpy.context.view_layer.update()

    def tearDown(self):
        for receipt in self.receipts:
            if not receipt._closed:
                receipt.accept()
        bpy.context.window.scene = self.previous
        for obj in set(bpy.data.objects) - self.original_objects:
            bpy.data.objects.remove(obj, do_unlink=True)
        bpy.data.scenes.remove(self.scene)
        for collection in set(bpy.data.collections) - self.original_collections:
            bpy.data.collections.remove(collection)
        for mesh in set(bpy.data.meshes) - self.original_meshes:
            bpy.data.meshes.remove(mesh)
        for material in set(bpy.data.materials) - self.original_materials:
            bpy.data.materials.remove(material)

    def mesh(self, name):
        mesh = bpy.data.meshes.new(name)
        mesh.from_pydata([(0, 0, 0), (1, 0, 0), (1, 1, 0), (0, 1, 0)], [], [(0, 1, 2, 3)])
        mesh.update()
        obj = bpy.data.objects.new(name, mesh)
        self.scene.collection.objects.link(obj)
        return obj

    @staticmethod
    def uv(obj, name, offset):
        layer = obj.data.uv_layers.new(name=name)
        for index, loop in enumerate(layer.data):
            loop.uv = (offset + index * 0.125, offset)
        return layer

    def apply(self, **kwargs):
        options = dict(policy="REMESH", result_to_source=Matrix.Identity(4))
        options.update(kwargs)
        receipt = self.module.apply_mesh(self.scene, self.source, self.result, **options)
        self.receipts.append(receipt)
        return receipt

    def test_remesh_preserves_object_context_and_shared_data(self):
        parent = bpy.data.objects.new("Parent", None)
        self.scene.collection.objects.link(parent)
        parent.location = (3, 4, 5)
        self.source.parent = parent
        self.source.location = (2, -3, 1)
        self.source.rotation_euler = (0.2, 0.3, 0.4)
        self.source.scale = (2, 3, 4)
        self.source["user_property"] = "retained"
        collection = bpy.data.collections.new("Second collection")
        self.scene.collection.children.link(collection)
        collection.objects.link(self.source)
        alias = bpy.data.objects.new("Shared mesh", self.source.data)
        self.scene.collection.objects.link(alias)
        alias.select_set(True)
        self.result.select_set(True)
        bpy.context.view_layer.objects.active = alias
        bpy.context.view_layer.update()
        before = self.source.data
        result_data = self.result.data
        state = (
            self.source.name,
            self.source.matrix_world.copy(),
            self.source.matrix_local.copy(),
            self.source.matrix_parent_inverse.copy(),
            self.source.parent,
            tuple(self.source.users_collection),
            tuple(bpy.context.selected_objects),
        )
        self.result.data.vertices[0].co.z = 2
        receipt = self.apply()
        self.assertIs(self.source, receipt.source)
        self.assertIsNot(self.source.data, result_data)
        self.assertIs(alias.data, before)
        self.assertIs(self.result.data, result_data)
        self.assertEqual(self.source.data.vertices[0].co.z, 2)
        self.assertIs(self.source.data.materials[0], self.result_material)
        self.assertEqual(self.source.data.uv_layers[0].name, "Result UV")
        self.assertEqual(self.source["user_property"], "retained")
        self.assertEqual(
            state,
            (
                self.source.name,
                self.source.matrix_world,
                self.source.matrix_local,
                self.source.matrix_parent_inverse,
                self.source.parent,
                tuple(self.source.users_collection),
                tuple(bpy.context.selected_objects),
            ),
        )
        self.assertIs(bpy.context.view_layer.objects.active, alias)

    def test_rollback_restores_original_pointer_and_keeps_imported_result(self):
        before = self.source.data
        result = self.result.data
        objects_before = set(bpy.data.objects)
        meshes_before = set(bpy.data.meshes)
        receipt = self.apply()
        receipt.rollback()
        self.assertIs(self.source.data, before)
        self.assertIs(self.result.data, result)
        self.assertEqual(set(bpy.data.objects), objects_before)
        self.assertEqual(set(bpy.data.meshes), meshes_before)
        with self.assertRaises(self.module.MeshApplicationError):
            receipt.rollback()

    def test_keep_original_is_user_owned_and_survives_rollback(self):
        parent = bpy.data.objects.new("Parent", None)
        self.scene.collection.objects.link(parent)
        self.source.parent = parent
        self.source.location = (4, 5, 6)
        bpy.context.view_layer.update()
        before = self.source.data
        receipt = self.apply(keep_original=True)
        original = receipt.original
        self.assertIs(original.data, before)
        self.assertEqual(original.parent, parent)
        self.assertEqual(original.matrix_world, self.source.matrix_world)
        self.assertEqual(original.users_collection, self.source.users_collection)
        self.assertNotEqual(original.name, self.source.name)
        receipt.rollback()
        self.assertIs(original.data, self.source.data)
        self.assertIn(original, tuple(bpy.data.objects))

    def test_uv_replaces_only_active_coordinates_and_preserves_materials_attributes(self):
        extra = self.uv(self.source, "Other UV", 0.5)
        self.source.data.uv_layers.active_index = 0
        saved_extra = tuple(tuple(loop.uv) for loop in extra.data)
        weight = self.source.data.attributes.new("Fixture weight", "FLOAT", "POINT")
        weight.data[0].value = 0.75
        before = self.source.data
        self.apply(policy="UV")
        self.assertIsNot(self.source.data, before)
        self.assertIs(self.source.data.materials[0], self.source_material)
        self.assertEqual(self.source.data.uv_layers[0].name, "Source UV")
        self.assertEqual(
            tuple(tuple(loop.uv) for loop in self.source.data.uv_layers[0].data),
            tuple(tuple(loop.uv) for loop in self.result.data.uv_layers[0].data),
        )
        self.assertEqual(
            tuple(tuple(loop.uv) for loop in self.source.data.uv_layers[1].data), saved_extra
        )
        self.assertEqual(self.source.data.attributes["Fixture weight"].data[0].value, 0.75)
        self.assertEqual(before.uv_layers[0].data[0].uv.x, 0.0)

    def test_uv_rejects_changed_positions_or_ambiguous_layers_before_mutation(self):
        before = self.source.data
        self.result.data.vertices[0].co.x = 0.01
        with self.assertRaises(self.module.MeshApplicationError):
            self.apply(policy="UV")
        self.assertIs(self.source.data, before)
        self.result.data.vertices[0].co.x = 0.0
        self.uv(self.result, "Ambiguous", 0.5)
        with self.assertRaises(self.module.MeshApplicationError):
            self.apply(policy="UV")
        self.assertIs(self.source.data, before)

    def test_uv_rejects_changed_indexed_topology(self):
        self.result.data.clear_geometry()
        self.result.data.from_pydata(
            [(0, 0, 0), (1, 0, 0), (1, 1, 0), (0, 1, 0)], [], [(3, 2, 1, 0)]
        )
        with self.assertRaises(self.module.MeshApplicationError):
            self.apply(policy="UV")

    def test_explicit_mapping_bakes_result_coordinates_without_moving_object(self):
        before = self.source.matrix_world.copy()
        self.apply(result_to_source=Matrix.Translation((2, 3, 4)))
        self.assertEqual(tuple(self.source.data.vertices[0].co), (2, 3, 4))
        self.assertEqual(self.source.matrix_world, before)
        self.assertEqual(tuple(self.result.data.vertices[0].co), (0, 0, 0))

    def test_unsupported_rig_animation_shape_keys_and_overrides_fail_closed(self):
        for target in (self.source, self.result):
            for kind in ("modifier", "constraint", "group", "animation", "shape", "override"):
                with self.subTest(target=target.name, kind=kind):
                    before = self.source.data
                    if kind == "modifier":
                        item = target.modifiers.new("Fixture", "ARMATURE")
                    elif kind == "constraint":
                        item = target.constraints.new("COPY_LOCATION")
                    elif kind == "group":
                        item = target.vertex_groups.new(name="Fixture")
                    elif kind == "animation":
                        target.animation_data_create()
                    elif kind == "shape":
                        target.shape_key_add(name="Basis")
                    else:
                        target.material_slots[0].link = "OBJECT"
                    with self.assertRaises(self.module.MeshApplicationError):
                        self.apply()
                    self.assertIs(self.source.data, before)
                    if kind == "modifier":
                        target.modifiers.remove(item)
                    elif kind == "constraint":
                        target.constraints.remove(item)
                    elif kind == "group":
                        target.vertex_groups.remove(item)
                    elif kind == "animation":
                        target.animation_data_clear()
                    elif kind == "shape":
                        target.shape_key_clear()
                    else:
                        target.material_slots[0].link = "DATA"

    def test_failed_publication_restores_source_and_removes_staging(self):
        before = self.source.data
        objects_before, meshes_before = set(bpy.data.objects), set(bpy.data.meshes)

        def failing(source, staged):
            source.data = staged
            raise RuntimeError("Fixture publication failure")

        with patch.object(self.module, "_publish", side_effect=failing):
            with self.assertRaisesRegex(RuntimeError, "publication failure"):
                self.apply(keep_original=True)
        self.assertIs(self.source.data, before)
        self.assertEqual(set(bpy.data.objects), objects_before)
        self.assertEqual(set(bpy.data.meshes), meshes_before)

    def test_rollback_refuses_in_place_geometry_uv_or_material_edits(self):
        for kind in ("geometry", "uv", "material", "attribute"):
            with self.subTest(kind=kind):
                before = self.source.data
                receipt = self.apply()
                applied = self.source.data
                if kind == "geometry":
                    applied.vertices[0].co.x += 1
                elif kind == "uv":
                    applied.uv_layers[0].data[0].uv.x += 0.5
                elif kind == "material":
                    applied.materials[0] = self.source_material
                else:
                    attribute = applied.attributes.new("User edit", "FLOAT", "POINT")
                    attribute.data[0].value = 1.0
                with self.assertRaisesRegex(self.module.MeshApplicationError, "Mesh data changed"):
                    receipt.rollback()
                self.assertIs(self.source.data, applied)
                self.source.data = before
                receipt.accept()

    def test_accept_discards_unused_original_without_accumulating_meshes(self):
        objects_before = set(bpy.data.objects)
        mesh_count = len(bpy.data.meshes)
        result = self.result.data
        for _ in range(3):
            receipt = self.apply()
            receipt.accept()
            self.assertEqual(set(bpy.data.objects), objects_before)
            self.assertEqual(len(bpy.data.meshes), mesh_count)
            self.assertIs(self.result.data, result)

    def test_accept_preserves_original_with_shared_or_explicit_ownership(self):
        for kind in ("shared", "keep_original", "fake_user"):
            with self.subTest(kind=kind):
                before = self.source.data
                if kind == "shared":
                    other = bpy.data.objects.new("Shared original", before)
                    self.scene.collection.objects.link(other)
                elif kind == "fake_user":
                    before.use_fake_user = True
                receipt = self.apply(keep_original=kind == "keep_original")
                receipt.accept()
                self.assertIn(before, tuple(bpy.data.meshes))
                if kind == "keep_original":
                    self.assertIs(receipt.original.data, before)

    def test_accept_preserves_original_edited_since_application(self):
        for kind in ("geometry", "metadata", "rename", "unsupported_attribute"):
            with self.subTest(kind=kind):
                before = self.source.data
                receipt = self.apply()
                if kind == "geometry":
                    before.vertices[0].co.x += 1
                elif kind == "metadata":
                    before["user_metadata"] = "retain"
                elif kind == "rename":
                    before.name = "User retained original"
                else:
                    before.attributes.new("User text", "STRING", "POINT")
                receipt.accept()
                self.assertIn(before, tuple(bpy.data.meshes))

    def test_rollback_refuses_structural_edits_and_allows_retry_after_removal(self):
        before = self.source.data
        receipt = self.apply()
        applied = self.source.data
        modifier = self.source.modifiers.new("Preview", "SUBSURF")
        with self.assertRaisesRegex(self.module.MeshApplicationError, "Target structure changed"):
            receipt.rollback()
        self.assertIs(self.source.data, applied)
        self.assertFalse(receipt._closed)
        self.source.modifiers.remove(modifier)
        applied["user_metadata"] = "retain"
        with self.assertRaisesRegex(self.module.MeshApplicationError, "Target structure changed"):
            receipt.rollback()
        self.assertEqual(applied["user_metadata"], "retain")
        self.assertIs(self.source.data, applied)
        del applied["user_metadata"]
        receipt.rollback()
        self.assertIs(self.source.data, before)

    def test_rollback_refuses_replaced_target_and_changed_original(self):
        before = self.source.data
        receipt = self.apply()
        applied = self.source.data
        self.source.data = self.result.data
        with self.assertRaisesRegex(self.module.MeshApplicationError, "replaced"):
            receipt.rollback()
        self.source.data = applied
        before.vertices[0].co.x += 1
        with self.assertRaisesRegex(self.module.MeshApplicationError, "Mesh data changed"):
            receipt.rollback()
        self.assertIs(self.source.data, applied)

    def test_accept_releases_private_holder_without_deleting_user_adopted_holder(self):
        receipt = self.apply()
        holder = receipt._holder
        self.scene.collection.objects.link(holder)
        receipt.accept()
        self.assertIn(holder, tuple(bpy.data.objects))
        with self.assertRaises(self.module.MeshApplicationError):
            receipt.accept()

    def test_rollback_does_not_delete_applied_mesh_used_by_another_object(self):
        receipt = self.apply()
        applied = self.source.data
        other = bpy.data.objects.new("Adopted result", applied)
        self.scene.collection.objects.link(other)
        receipt.rollback()
        self.assertIs(other.data, applied)
        self.assertIn(applied, tuple(bpy.data.meshes))

    def test_worker_thread_is_rejected_before_blender_access(self):
        with ThreadPoolExecutor(max_workers=1) as pool:
            task = pool.submit(
                self.module.apply_mesh,
                None,
                None,
                None,
                policy="REMESH",
                result_to_source=Matrix.Identity(4),
            )
            with self.assertRaisesRegex(self.module.MeshApplicationError, "main thread"):
                task.result(5)

    def test_invalid_policy_mapping_and_component_budget_leave_source_unchanged(self):
        before = self.source.data
        for options in (
            dict(policy="RIG"),
            dict(keep_original=1),
            dict(result_to_source=Matrix.Scale(0, 4)),
            dict(result_to_source=[[float("nan")] * 4] * 4),
        ):
            with self.subTest(options=options):
                with self.assertRaises(self.module.MeshApplicationError):
                    self.apply(**options)
                self.assertIs(self.source.data, before)
        with patch.object(self.module, "MAX_COMPONENTS", 1):
            with self.assertRaises(self.module.MeshApplicationError):
                self.apply()
        self.assertIs(self.source.data, before)

    def test_missing_scene_membership_and_same_mesh_fail_closed(self):
        self.scene.collection.objects.unlink(self.result)
        with self.assertRaises(self.module.MeshApplicationError):
            self.apply()
        self.scene.collection.objects.link(self.result)
        self.result.data = self.source.data
        with self.assertRaises(self.module.MeshApplicationError):
            self.apply()

    def test_unsupported_generic_attributes_and_custom_mesh_properties_fail_closed(self):
        attribute = self.result.data.attributes.new("Unsupported", "STRING", "POINT")
        with self.assertRaises(self.module.MeshApplicationError):
            self.apply()
        self.result.data.attributes.remove(attribute)
        self.source.data["user_metadata"] = "preserve"
        with self.assertRaises(self.module.MeshApplicationError):
            self.apply()

    def test_rollback_restores_clamped_active_material_selection(self):
        self.source.data.materials.append(self.result_material)
        self.source.active_material_index = 1
        receipt = self.apply()
        self.assertEqual(self.source.active_material_index, 0)
        receipt.rollback()
        self.assertEqual(self.source.active_material_index, 1)

    def test_changed_holder_settings_or_modifiers_are_never_deleted(self):
        for kind in ("modifier", "parent", "display"):
            with self.subTest(kind=kind):
                receipt = self.apply()
                holder = receipt._holder
                if kind == "modifier":
                    holder.modifiers.new("User modifier", "SUBSURF")
                elif kind == "parent":
                    holder.parent = self.source
                else:
                    holder.display_type = "WIRE"
                receipt.accept()
                self.assertIn(holder, tuple(bpy.data.objects))
