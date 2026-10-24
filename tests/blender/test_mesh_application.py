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
        # Left visible at the same transform it would cover the edited mesh.
        self.assertTrue(original.hide_get())
        self.assertTrue(original.hide_render)
        self.assertFalse(self.source.hide_get())
        receipt.rollback()
        self.assertIs(original.data, self.source.data)
        self.assertIn(original, tuple(bpy.data.objects))

    def test_keep_original_in_a_collection_excluded_from_one_view_layer_is_still_hidden(self):
        collection = bpy.data.collections.new("Excluded elsewhere")
        self.scene.collection.children.link(collection)
        collection.objects.link(self.source)
        self.scene.collection.objects.unlink(self.source)
        other = self.scene.view_layers.new("Other layer")
        other.layer_collection.children[collection.name].exclude = True
        receipt = self.apply(keep_original=True)
        self.assertTrue(receipt.original.hide_render)
        self.assertTrue(receipt.original.hide_get())

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

    def test_uv_accepts_rounding_and_a_triangulated_reordered_result(self):
        self.result.data.vertices[0].co.x = 1e-6
        receipt = self.apply(policy="UV")
        self.assertIsNotNone(receipt.surface.match)
        self.receipts.remove(receipt)
        receipt.rollback()
        self.result.data.clear_geometry()
        for layer in tuple(self.result.data.uv_layers):
            self.result.data.uv_layers.remove(layer)
        self.result.data.from_pydata(
            [(1, 1, 0), (0, 1, 0), (0, 0, 0), (1, 0, 0)], [], [(0, 1, 2), (2, 3, 0)]
        )
        layer = self.result.data.uv_layers.new(name="Result UV")
        uv = {0: (0.75, 0.75), 1: (0.25, 0.75), 2: (0.25, 0.25), 3: (0.75, 0.25)}
        for loop in self.result.data.loops:
            layer.data[loop.index].uv = uv[loop.vertex_index]
        self.apply(policy="UV")
        expected = [(0.25, 0.25), (0.75, 0.25), (0.75, 0.75), (0.25, 0.75)]
        self.assertEqual([tuple(item.uv) for item in self.source.data.uv_layers[0].data], expected)

    def test_split_results_share_one_component_bound(self):
        other = self.mesh("Second result")
        sizes = [self.module._components(obj.data) for obj in (self.result, other)]
        with patch.object(self.module, "MAX_COMPONENTS", sum(sizes) - 1):
            with self.assertRaisesRegex(self.module.MeshApplicationError, "component limit"):
                self.module.match_surface(
                    self.source, (self.result, other), Matrix.Identity(4), "UV"
                )

    def fit_request(self):
        bases = (("WORLD", self.source.matrix_world.inverted()), ("LOCAL", Matrix()))
        return self.module.FitRequest(
            tuple((label, tuple(tuple(row) for row in matrix)) for label, matrix in bases)
        )

    def card(self, scale, *, loose):
        """Give source and result one double-sided card the correspondence refuses.

        Its coincident back face is ambiguous and loose geometry has no corners,
        so only the exact indexed-topology path can accept this result.
        """
        quad = [(0, 0, 0), (1, 0, 0), (1, 1, 0), (0, 1, 0)]
        extra = [(2, 2, 0), (3, 0, 0), (3, 1, 0)] if loose else []
        back = tuple(index + len(quad) + len(extra) for index in (3, 2, 1, 0))
        for obj, factor, material, name, offset in (
            (self.source, 1.0, self.source_material, "Source UV", 0.0),
            (self.result, scale, self.result_material, "Result UV", 0.25),
        ):
            data = bpy.data.meshes.new(f"{obj.name} card")
            data.from_pydata(
                [tuple(factor * value for value in co) for co in quad + extra + quad],
                [(5, 6)] if loose else [],
                [(0, 1, 2, 3), back],
            )
            data.update()
            data.materials.append(material)
            obj.data = data
            self.uv(obj, name, offset)
        bpy.context.view_layer.update()

    def test_fit_accepts_exact_topology_the_correspondence_refuses(self):
        for scale, loose in ((1.0, True), (2.0, False)):
            for policy in ("UV", "RETEXTURE"):
                with self.subTest(scale=scale, policy=policy):
                    self.card(scale, loose=loose)
                    expected = [tuple(loop.uv) for loop in self.result.data.uv_layers[0].data]
                    receipt = self.apply(policy=policy, result_to_source=self.fit_request())
                    surface = receipt.surface
                    self.assertIsNone(surface.match)
                    self.assertEqual((surface.fitted_from, surface.scale), ("WORLD", 1 / scale))
                    self.assertEqual(
                        [tuple(loop.uv) for loop in self.source.data.uv_layers.active.data],
                        expected,
                    )
                    self.receipts.remove(receipt)
                    receipt.rollback()

    def test_fit_matches_once_when_both_bases_fit_alike(self):
        correspondence = submodule("core.scene.mesh_correspondence")
        self.source.location = (2, 3, 4)
        self.source.scale = (2, 2, 2)
        bpy.context.view_layer.update()
        self.result.data.clear_geometry()
        for layer in tuple(self.result.data.uv_layers):
            self.result.data.uv_layers.remove(layer)
        self.result.data.from_pydata(
            [(1, 1, 0), (0, 1, 0), (0, 0, 0), (1, 0, 0)], [], [(0, 1, 2), (2, 3, 0)]
        )
        layer = self.result.data.uv_layers.new(name="Result UV")
        for loop in self.result.data.loops:
            layer.data[loop.index].uv = (0.25, loop.vertex_index / 4)
        match = correspondence.match
        with patch.object(correspondence, "match", side_effect=match) as matched:
            receipt = self.apply(policy="UV", result_to_source=self.fit_request())
        self.assertEqual(matched.call_count, 1)
        self.assertEqual(receipt.surface.fitted_from, "WORLD")

    def test_uv_rejects_changed_indexed_topology(self):
        self.result.data.clear_geometry()
        self.result.data.from_pydata(
            [(0, 0, 0), (1, 0, 0), (1, 1, 0), (0, 1, 0)], [], [(3, 2, 1, 0)]
        )
        with self.assertRaises(self.module.MeshApplicationError):
            self.apply(policy="UV")

    def test_retexture_preserves_geometry_attributes_context_and_shared_original(self):
        attribute = self.source.data.attributes.new("Keep weight", "FLOAT", "POINT")
        attribute.data[0].value = 0.75
        self.source.data.polygons[0].use_smooth = True
        self.source.data.edges[0].use_seam = True
        before = self.source.data
        alias = bpy.data.objects.new("Shared original", before)
        self.scene.collection.objects.link(alias)
        self.source.location = (2, 3, 4)
        bpy.context.view_layer.update()
        transform = self.source.matrix_world.copy()
        geometry = [tuple(vertex.co) for vertex in before.vertices]
        receipt = self.apply(policy="RETEXTURE", keep_original=True)
        self.assertEqual([tuple(vertex.co) for vertex in self.source.data.vertices], geometry)
        self.assertEqual(self.source.matrix_world, transform)
        self.assertEqual(self.source.data.attributes["Keep weight"].data[0].value, 0.75)
        self.assertTrue(self.source.data.polygons[0].use_smooth)
        self.assertTrue(self.source.data.edges[0].use_seam)
        self.assertEqual(list(self.source.data.materials), [self.result_material])
        self.assertEqual(self.source.data.uv_layers[0].name, "Result UV")
        self.assertEqual(list(before.materials), [self.source_material])
        self.assertIs(alias.data, before)
        self.assertIs(receipt.original.data, before)
        receipt.rollback()
        self.assertIs(self.source.data, before)
        self.assertIs(receipt.original.data, before)

    def test_retexture_adopts_all_named_uv_roles_and_face_materials(self):
        self.uv(self.result, "Second UV", 0.5)
        self.result.data.uv_layers.active_index = 1
        self.result.data.uv_layers[1].active_render = True
        self.result.data.uv_layers[1].active_clone = True
        self.result.data.materials.append(self.source_material)
        self.result.data.polygons[0].material_index = 1
        self.apply(policy="RETEXTURE")
        self.assertEqual(list(self.source.data.materials), list(self.result.data.materials))
        self.assertEqual(self.source.data.polygons[0].material_index, 1)
        self.assertEqual(self.source.data.uv_layers.active_index, 1)
        for actual, expected in zip(
            self.source.data.uv_layers, self.result.data.uv_layers, strict=True
        ):
            self.assertEqual(
                (actual.name, actual.active_render, actual.active_clone),
                (expected.name, expected.active_render, expected.active_clone),
            )
            self.assertEqual(
                [tuple(item.uv) for item in actual.data], [tuple(item.uv) for item in expected.data]
            )

    def test_retexture_rejects_attribute_name_collision_without_mutation(self):
        self.source.data.attributes.new("Result UV", "FLOAT", "POINT")
        before = self.source.data
        meshes = set(bpy.data.meshes)
        with self.assertRaisesRegex(self.module.MeshApplicationError, "conflict"):
            self.apply(policy="RETEXTURE")
        self.assertIs(self.source.data, before)
        self.assertEqual(set(bpy.data.meshes), meshes)

    def test_retexture_rejects_missing_materials_uvs_and_invalid_face_assignments(self):
        before = self.source.data
        for kind in ("materials", "uvs", "face"):
            with self.subTest(kind=kind):
                if kind == "materials":
                    self.result.data.materials.clear()
                elif kind == "uvs":
                    self.result.data.uv_layers.remove(self.result.data.uv_layers[0])
                else:
                    self.result.data.polygons[0].material_index = 4
                meshes = set(bpy.data.meshes)
                with self.assertRaises(self.module.MeshApplicationError):
                    self.apply(policy="RETEXTURE")
                self.assertIs(self.source.data, before)
                self.assertEqual(set(bpy.data.meshes), meshes)
                if kind == "materials":
                    self.result.data.materials.append(self.result_material)
                elif kind == "uvs":
                    self.uv(self.result, "Result UV", 0.25)

    def test_retexture_rejects_geometry_change_and_reindexed_faces(self):
        before = self.source.data
        self.result.data.vertices[0].co.x = 0.01
        with self.assertRaisesRegex(
            self.module.MeshApplicationError, "does not match the source mesh"
        ):
            self.apply(policy="RETEXTURE")
        self.assertIs(self.source.data, before)
        self.result.data.clear_geometry()
        self.result.data.from_pydata(
            [(0, 0, 0), (1, 0, 0), (1, 1, 0), (0, 1, 0)], [], [(3, 2, 1, 0)]
        )
        with self.assertRaisesRegex(
            self.module.MeshApplicationError, "does not match the source mesh"
        ):
            self.apply(policy="RETEXTURE")
        self.assertIs(self.source.data, before)

    def test_retexture_rollback_refuses_later_uv_edit(self):
        receipt = self.apply(policy="RETEXTURE")
        applied = self.source.data
        applied.uv_layers[0].data[0].uv.x += 0.5
        with self.assertRaisesRegex(self.module.MeshApplicationError, "Mesh data changed"):
            receipt.rollback()
        self.assertIs(self.source.data, applied)

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
        with self.assertRaisesRegex(self.module.MeshApplicationError, "Mesh data changed"):
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

    def test_unsupported_generic_attributes_and_data_references_fail_closed(self):
        before = self.source.data
        attribute = self.result.data.attributes.new("Unsupported", "STRING", "POINT")
        with self.assertRaises(self.module.MeshApplicationError):
            self.apply()
        self.result.data.attributes.remove(attribute)
        self.source.data["user_reference"] = self.result_material
        with self.assertRaisesRegex(self.module.MeshApplicationError, "reference data"):
            self.apply()
        self.assertIs(self.source.data, before)

    def test_edits_keep_the_source_custom_mesh_properties_never_a_results(self):
        # Blender's glTF importer turns mesh extras into custom properties.
        self.source.data["name"] = "provider mesh"
        self.source.data["user_weight"] = 0.5
        self.source.data.id_properties_ui("user_weight").update(min=0.0, max=2.0)
        self.source.data["user_group"] = {"tags": [1, 2]}
        self.result.data["name"] = "result mesh"
        self.result.data["result_only"] = True
        expected = self.module._properties(self.source.data)
        for policy in ("REMESH", "UV", "RETEXTURE"):
            with self.subTest(policy=policy):
                before = self.source.data
                if policy != "REMESH":
                    # The result must be the source's surface, with one UV layer.
                    self.result.data = before.copy()
                    self.result.data["name"] = "result mesh"
                    self.result.data["result_only"] = True
                receipt = self.apply(policy=policy)
                applied = self.source.data
                self.assertIsNot(applied, before)
                self.assertEqual(self.module._properties(applied), expected)
                self.assertEqual(applied.id_properties_ui("user_weight").as_dict()["max"], 2.0)
                self.assertNotIn("result_only", applied)
                # Properties are guarded like geometry: a later change needs review.
                applied["user_added"] = 1
                with self.assertRaisesRegex(self.module.MeshApplicationError, "Mesh data changed"):
                    receipt.rollback()
                del applied["user_added"]
                receipt.rollback()
                self.assertIs(self.source.data, before)

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
