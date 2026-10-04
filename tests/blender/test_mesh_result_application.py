# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Receipt-bound static mesh replacement and durable session outcomes."""

import hashlib
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest.mock import patch

import bpy
from helpers import FIXTURES, submodule
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
