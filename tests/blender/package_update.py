# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Internal actual-package state probe; only the isolated update runner may invoke it."""

import argparse
import hashlib
import importlib
import json
import os
import socket
import sys
from contextlib import contextmanager, nullcontext
from dataclasses import asdict, replace
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
from repository_update import checked_repository, owned_profile

PACKAGE = "bl_ext.update_fixture.scenario"


def module(name):
    return importlib.import_module(f"{PACKAGE}.{name}")


def digest(data):
    return hashlib.sha256(data).hexdigest()


def windows_namespace(path):
    """Keep the probe's recursive inventory usable beyond legacy FindFirstFile limits."""
    if path.startswith("\\\\?\\"):
        return path
    if path.startswith("\\\\"):
        return "\\\\?\\UNC\\" + path[2:]
    return "\\\\?\\" + path


@contextmanager
def no_service_connections():
    """Native repository HTTP uses Blender; Python service traffic must stay absent."""
    attempts = []

    def reject(*_args, **_kwargs):
        attempts.append(True)
        raise RuntimeError("Scenario network access is forbidden during update acceptance")

    with (
        patch.object(socket.socket, "connect", reject),
        patch.object(socket.socket, "connect_ex", reject),
    ):
        yield attempts
    if attempts:
        raise RuntimeError("Extension attempted service traffic during update acceptance")


def stores():
    runtime = module("blender.runtime")
    paths = runtime.paths()
    selected = runtime.ensure_job_store()
    binding = module("core.jobs.credential_storage")
    api = module("core.api.sdk_adapter")
    other = binding.open_credential_store(
        paths.state_dir / "shared-jobs", api.Credentials("update-other-key", "update-other-secret")
    )
    upload_root = paths.state_dir / "shared-uploads"
    upload_root.mkdir(parents=True, exist_ok=True)
    source_root = upload_root / "sources"
    source_root.mkdir(exist_ok=True)
    uploads = module("core.jobs.upload_store").UploadStore(
        upload_root / "uploads.sqlite3", selected.scope
    )
    sources = module("core.jobs.upload_sources").UploadSources(source_root)
    result_root = paths.state_dir / "shared-results"
    result_root.mkdir(exist_ok=True)
    transfers = module("core.jobs.transfers")
    results = module("core.jobs.results").ResultCommands(
        SimpleNamespace(),
        selected,
        nullcontext,
        downloader=transfers.ResultDownloader(
            transfers.StoragePolicy(frozenset({"fixture.invalid"})), online_access=lambda: False
        ),
        root=result_root,
    )
    return paths, selected, other, uploads, sources, results


def seed_mesh_upload(profile, selected, uploads, sources, origin):
    """Persist an exact synthetic GLB and its local captured-source metadata."""
    jobs = module("core.jobs.store")
    provenance = module("core.jobs.mesh_source")
    states = module("core.jobs.upload_store")
    source = profile / "reference.glb"
    source.write_bytes(
        (
            Path(__file__).resolve().parents[1] / "fixtures/synthetic/static-triangle.glb"
        ).read_bytes()
    )
    metadata = provenance.MeshSource(
        digest(source.read_bytes()),
        (
            provenance.MeshSourceObject(
                origin.target_id,
                digest(b"synthetic source geometry"),
                ((1, 0, 0, 3), (0, 2, 0, 4), (0, 0, 1, 5), (0, 0, 0, 1)),
            ),
        ),
    )
    intent = sources.stage(
        source,
        request_id="upload-mesh",
        scope=selected.scope,
        origin=origin,
        kind="3d",
        content_type="model/gltf-binary",
        mesh_source=metadata,
    )
    record = uploads.create(intent)
    for state in (states.UploadState.INITIALIZING, states.UploadState.UPLOADING):
        record = uploads.transition(
            intent.request_id,
            expected_revision=record.revision,
            state=state,
            upload_id="update-mesh-upload" if state == states.UploadState.UPLOADING else None,
        )
    for index, part_hash in enumerate(intent.part_sha256, 1):
        record = uploads.claim_part(intent.request_id, expected_revision=record.revision)
        size = intent.part_bytes(index)
        record = uploads.record_part(
            intent.request_id,
            states.UploadedPart(index, size, part_hash),
            expected_revision=record.revision,
        )
    for state in (
        states.UploadState.FINALIZING,
        states.UploadState.PROCESSING,
        states.UploadState.IMPORTED,
    ):
        record = uploads.transition(
            intent.request_id,
            expected_revision=record.revision,
            state=state,
            asset_id="update-mesh-asset" if state == states.UploadState.IMPORTED else None,
        )
    return jobs.JobMeshSource(
        "mesh",
        None,
        record.asset_id,
        intent.request_id,
        record.revision,
        origin,
        metadata,
    )


def seed_local_applications(selected, record, origin):
    """Preserve successful, rolled-back and uncertain reuse independently of generation."""
    jobs = module("core.jobs.store")
    for name, state in (
        ("reuse-applied", jobs.LocalApplicationState.APPLIED),
        ("reuse-failed", jobs.LocalApplicationState.FAILED),
        ("reuse-unfinished", jobs.LocalApplicationState.APPLYING),
    ):
        record = selected.claim_local_application(
            record.intent.request_id,
            expected_revision=record.revision,
            application_id=name,
            destination=replace(origin, scene_id=name, target_id="target-" + name),
            purpose="images",
            asset_ids=tuple(item.asset.asset_id for item in record.results),
        )
        if state != jobs.LocalApplicationState.APPLYING:
            record = selected.finish_local_application(
                record.intent.request_id,
                expected_revision=record.revision,
                application_id=name,
                state=state,
            )


def check_mesh_bindings(selected, uploads):
    jobs = module("core.jobs.store")
    upload = uploads.get("upload-mesh")
    if upload is None or upload.state.value != "imported" or upload.intent.mesh_source is None:
        raise RuntimeError("Update lost the captured mesh upload")
    expected = jobs.JobMeshSource(
        "mesh",
        None,
        upload.asset_id,
        upload.intent.request_id,
        upload.revision,
        upload.intent.origin,
        upload.intent.mesh_source,
    )
    for request_id in ("ready", "applied"):
        if selected.get(request_id).intent.mesh_sources != (expected,):
            raise RuntimeError("Update lost or changed the captured generation input")


def check_local_applications(selected):
    """Update/restart must retain uncertainty and continue rejecting another claim."""
    jobs = module("core.jobs.store")
    record = selected.get("applied")
    if [item.state for item in record.local_applications] != [
        jobs.LocalApplicationState.APPLIED,
        jobs.LocalApplicationState.FAILED,
        jobs.LocalApplicationState.APPLYING,
    ]:
        raise RuntimeError("Update lost the local application history")
    try:
        selected.claim_local_application(
            "applied",
            expected_revision=record.revision,
            application_id="forbidden-replay",
            destination=record.intent.origin,
            purpose="images",
            asset_ids=tuple(item.asset.asset_id for item in record.results),
        )
    except jobs.StoreConflict:
        if selected.get("applied") != record:
            raise RuntimeError("Rejected reuse changed the saved job") from None
    else:
        raise RuntimeError("Update permitted replay of an unfinished local application")


def seed(profile):
    import bpy

    prefs = bpy.context.preferences.addons[PACKAGE].preferences
    prefs.credential_source = "PREFERENCES"
    prefs.api_key, prefs.api_secret = "update-fixture-key", "update-fixture-secret"
    prefs.output_dir = str(profile / "output")
    prefs.composer_enabled = False
    prefs.composer_offset_x, prefs.composer_offset_y = 23.0, 47.0
    prefs.composer_width = 640
    prefs.mcp_port, prefs.mcp_allow_python = 19876, False
    paths, selected, other, uploads, sources, results = stores()
    jobs = module("core.jobs.store")
    origin = jobs.JobOrigin("update-file", "update-scene", "update-revision", "update-target")
    mesh_binding = seed_mesh_upload(profile, selected, uploads, sources, origin)
    template = jobs.JobIntent(
        "prepared",
        selected.scope,
        origin,
        "model",
        "update-model",
        digest(b"fixture payload"),
        digest(b"fixture exact quote"),
        "0.1234567890123456789",
    )
    for desired in ("prepared", "uncertain", "remote", "download_failed", "ready", "applied"):
        record = selected.create(
            replace(
                template,
                request_id=desired,
                mesh_sources=(mesh_binding,) if desired in {"ready", "applied"} else (),
            )
        )

        def advance(state, **kwargs):
            nonlocal record
            record = selected.transition(
                record.intent.request_id,
                expected_revision=record.revision,
                state=jobs.JobState(state),
                **kwargs,
            )

        if desired == "prepared":
            continue
        advance("submitting")
        if desired == "uncertain":
            advance("uncertain")
            continue
        advance("remote", remote_job_id="remote-" + desired)
        if desired == "remote":
            continue
        advance("succeeded")
        data = b"offline preserved result bytes"
        asset = jobs.ResultAsset(
            "asset-" + desired, "result.png", "image/png", len(data), digest(data)
        )
        record = selected.set_results(desired, (asset,), expected_revision=record.revision)
        advance("downloading")
        if desired == "download_failed":
            advance("download_failed")
            continue
        directory = results._directory(record)
        (directory / asset.name).write_bytes(data)
        receipt = module("core.jobs.transfers").DownloadedResult(
            asset.name, len(data), digest(data)
        )
        record = selected.record_download(
            desired, asset.asset_id, receipt, expected_revision=record.revision
        )
        advance("ready")
        if desired == "applied":
            advance("applying", application_origin=replace(origin, scene_id="approved-other-scene"))
            advance("applied")
            seed_local_applications(selected, record, origin)
    other.create(replace(template, scope=other.scope, request_id="other-scope"))
    source = profile / "reference.png"
    source.write_bytes(b"offline preserved reference bytes")
    upload_states = module("core.jobs.upload_store").UploadState
    for desired in ("prepared", "initialization_uncertain", "imported"):
        intent = sources.stage(
            source,
            request_id="upload-" + desired,
            scope=selected.scope,
            origin=origin,
            kind="image",
            content_type="image/png",
        )
        record = uploads.create(intent)
        states = [] if desired == "prepared" else [upload_states.INITIALIZING]
        states += (
            [upload_states.INITIALIZATION_UNCERTAIN]
            if desired == "initialization_uncertain"
            else []
        )
        states += [upload_states.UPLOADING, upload_states.IMPORTED] if desired == "imported" else []
        for state in states:
            record = uploads.transition(
                intent.request_id,
                expected_revision=record.revision,
                state=state,
                upload_id="update-upload" if state == upload_states.UPLOADING else None,
                asset_id="update-asset" if state == upload_states.IMPORTED else None,
            )
    scene = bpy.context.scene
    scene.name = "Update acceptance scene"
    scene["update_fixture"] = "preserve scene data"
    lane = scene.scenario.lane_state("image")
    lane.prompt = "Preserve the adopted extension form"
    ref = lane.references.add()
    ref.param_name, ref.source, ref.asset_id = "image", "ASSET", "update-asset"
    ref.label = "Saved uploaded snapshot"
    ref["_scenario_reference_upload"] = "update-reference"
    ref["_scenario_reference_scope"] = module("blender.reference_form").scope_key(selected.scope)
    ref["_scenario_reference_request"] = "upload-imported"
    ref["_scenario_reference_asset"] = "update-asset"
    bpy.ops.wm.save_userpref()
    bpy.ops.wm.save_as_mainfile(filepath=str(profile / "state.blend"), check_existing=False)


def snapshot(profile):
    import bpy

    paths, selected, other, uploads, sources, results = stores()
    prefs = bpy.context.preferences.addons[PACKAGE].preferences
    if not paths.state_dir.resolve().is_relative_to(profile):
        raise RuntimeError("Scenario storage escaped the disposable profile")
    records = selected.records()
    if len(records) != 6 or selected.get("other-scope") is not None or len(other.records()) != 1:
        raise RuntimeError("Update lost durable records or credential isolation")
    check_mesh_bindings(selected, uploads)
    check_local_applications(selected)
    for record in records:
        if record.state.value == "ready":
            results.verify_ready(record.intent.request_id, expected_revision=record.revision)
        for item in record.results:
            if item.receipt:
                directory = results._directory(record, create=False)
                module("core.jobs.transfers").verify_download(
                    directory, item.receipt, max_bytes=1024
                )
    for upload in uploads.records():
        sources.verify(upload.intent)
    inventory_root = paths.state_dir.resolve()
    if os.name == "nt":
        # Blender 5.0/Python 3.11 can read verified result bytes yet fail to
        # enumerate their long directory via rglob. Use Win32's extended path
        # namespace for this test inventory; do not skip any stored file.
        inventory_root = Path(windows_namespace(str(inventory_root)))
    files = {
        str(path.relative_to(inventory_root)): digest(path.read_bytes())
        for path in inventory_root.rglob("*")
        if path.is_file()
        and path.suffix not in {".sqlite3"}
        and not path.name.endswith(("-wal", "-shm", ".lock"))
    }
    lane = bpy.context.scene.scenario.lane_state("image")
    scene = {
        "name": bpy.context.scene.name,
        "custom": bpy.context.scene.get("update_fixture"),
        "prompt": lane.prompt,
        "references": [
            {
                "source": r.source,
                "parameter": r.param_name,
                "asset": r.asset_id,
                "label": r.label,
                "markers": dict(r.items()),
            }
            for r in lane.references
        ],
    }
    values = {
        name: getattr(prefs, name)
        for name in (
            "credential_source",
            "output_dir",
            "composer_enabled",
            "composer_offset_x",
            "composer_offset_y",
            "composer_width",
            "mcp_port",
            "mcp_allow_python",
        )
    }
    values["credentials_digest"] = digest(json.dumps([prefs.api_key, prefs.api_secret]).encode())
    value = {
        "preferences": values,
        "jobs": [asdict(r) for r in records],
        "other_jobs": [asdict(r) for r in other.records()],
        "uploads": [asdict(r) for r in uploads.records()],
        "files": files,
        "scene": scene,
        "original_source": digest((profile / "reference.png").read_bytes()),
        "original_mesh_source": digest((profile / "reference.glb").read_bytes()),
    }
    return json.loads(json.dumps(value))


def check_version(profile, expected):
    import bpy

    if PACKAGE not in bpy.context.preferences.addons:
        raise RuntimeError("Scenario is no longer enabled")
    addon = importlib.import_module(PACKAGE)
    if Path(addon.__file__).resolve() != profile / "extensions/update_fixture/scenario/__init__.py":
        raise RuntimeError("Scenario loaded outside the disposable profile")
    if addon.__version__ != expected or not hasattr(bpy.types.Scene, "scenario"):
        raise RuntimeError("Updated package version or registered scene properties do not match")


def main():
    profile = owned_profile()
    import bpy

    parser = argparse.ArgumentParser()
    parser.add_argument("--url", required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--before", required=True)
    parser.add_argument("--after", required=True)
    parser.add_argument("--restart", action="store_true")
    args = parser.parse_args(sys.argv[sys.argv.index("--") + 1 :])
    checked_repository(profile, args.url, args.report)
    expected_path = profile.parent / "expected-state.json"
    with no_service_connections():
        if args.restart:
            check_version(profile, args.after)
            bpy.ops.wm.open_mainfile(filepath=str(profile / "state.blend"))
            if snapshot(profile) != json.loads(expected_path.read_text()):
                raise RuntimeError("Scenario state changed after restart")
        else:
            check_version(profile, args.before)
            seed(profile)
            expected = snapshot(profile)
            expected_path.write_text(json.dumps(expected, indent=2) + "\n")
            if bpy.ops.extensions.repo_sync_all() != {"FINISHED"}:
                raise RuntimeError("Native repository sync failed")
            if bpy.ops.extensions.package_upgrade_all() != {"FINISHED"}:
                raise RuntimeError("Native Scenario upgrade failed")
            check_version(profile, args.after)
            if snapshot(profile) != expected:
                raise RuntimeError("Scenario state changed during native update")
            bpy.ops.wm.save_userpref()
        args.report.write_text(
            json.dumps(
                {
                    "before": args.before,
                    "after": args.after,
                    "enabled": True,
                    "state_preserved": True,
                    "scene_preserved": True,
                    "service_requests": 0,
                }
            )
            + "\n"
        )


if __name__ == "__main__":
    main()
