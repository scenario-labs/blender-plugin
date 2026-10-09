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
PROJECT_ID = "update-fixture-project"
ORIGIN = ("update-file", "update-scene", "update-revision", "update-target")


def module(name):
    return importlib.import_module(f"{PACKAGE}.{name}")


def digest(data):
    return hashlib.sha256(data).hexdigest()


def film_binding(task_id):
    jobs = module("core.jobs.store")
    if not hasattr(jobs, "FilmTaskBinding"):
        return None
    return jobs.FilmTaskBinding(
        "update-production", task_id, digest(b"fixture recipe"), digest(task_id.encode())
    )


def seed_film_upload(selected, uploads):
    jobs = module("core.jobs.store")
    if not hasattr(jobs, "FilmUploadReference"):
        return
    upload = uploads.get("upload-mesh")
    selected.bind_film_upload(
        jobs.FilmUploadReference(
            selected.scope,
            film_binding("captured-reference"),
            upload.intent.request_id,
            upload.revision,
            upload.asset_id,
            upload.intent.file_sha256,
            upload.intent.kind,
        )
    )


def job_snapshot(record):
    value = asdict(record)
    if value["intent"].get("source") != "cloud":
        value["intent"].setdefault("film_task", None)
    for item in value["results"]:
        # Schema 10 gives earlier results the asset's own file and no projection.
        item["asset"].setdefault("source", "asset")
        item["asset"].setdefault("projection", None)
    return value


DEFAULT_LANES = ("image", "render_image")
BASE_JOBS = frozenset(("prepared", "uncertain", "remote", "download_failed", "ready", "applied"))


def supports_schema_10():
    """Lane defaults and declared originals arrived together in job schema 10."""
    jobs = module("core.jobs.store")
    fields = getattr(jobs.ResultAsset, "__dataclass_fields__", {})
    return hasattr(jobs, "TrainedModelDefault") and {"source", "projection"} <= set(fields)


def store_schema(paths):
    """Read the job database version without opening or upgrading it."""
    import sqlite3

    database = paths.state_dir / "shared-jobs" / "jobs.sqlite3"
    connection = sqlite3.connect(database.as_uri() + "?mode=ro", uri=True)
    try:
        return connection.execute("PRAGMA user_version").fetchone()[0]
    finally:
        connection.close()


def trained_defaults_snapshot(selected, other):
    """Lane defaults live in their own table; an untouched lane matches older packages."""
    if not hasattr(selected, "trained_default"):
        return None
    states = {lane: selected.trained_default(lane) for lane in DEFAULT_LANES}
    if (
        any(other.trained_default(lane).revision for lane in DEFAULT_LANES)
        or other.trained_defaults()
    ):
        raise RuntimeError("Trained-model defaults escaped their credential scope")
    if not any(state.revision for state in states.values()):
        return None
    return {lane: asdict(state) for lane, state in states.items()}


def model_defaults_owner():
    """The installed runtime's lane-defaults owner; older packages have only the store."""
    runtime = module("blender.runtime")
    if not hasattr(runtime, "ensure_model_defaults"):
        return None
    return runtime.ensure_model_defaults()


def check_model_defaults(selected, owner):
    """Read the saved lanes through the runtime owner that UI and MCP callers use."""
    if owner is None:
        return False
    if owner.scope != selected.scope:
        raise RuntimeError("Runtime lane defaults use another credential or project scope")
    stored = {lane: selected.trained_default(lane) for lane in DEFAULT_LANES}
    read = {lane: owner.lane(lane) for lane in DEFAULT_LANES}
    if read != stored or owner.saved() != selected.trained_defaults():
        raise RuntimeError("Runtime lane defaults differ from the saved store")
    if not owner.saved():
        raise RuntimeError("Runtime lane defaults lost the saved default")
    return True


def seed_schema_10(selected, results, origin, owner=None):
    """Save a declared EXR original with its projection, plus a saved and a cleared default.

    Defaults go through the runtime owner when the package has one, as a user's would.
    """
    jobs = module("core.jobs.store")
    transfers = module("core.jobs.transfers")
    save = owner.save if owner is not None else selected.set_trained_default
    clear = owner.clear if owner is not None else selected.clear_trained_default
    default = jobs.TrainedModelDefault(
        "image", "stack", "update-base-model", (jobs.TrainedModelPick("update-lora", 0.75),)
    )
    save(default, expected_revision=0)
    custom = jobs.TrainedModelDefault("render_image", "custom", "update-private-model")
    saved = save(custom, expected_revision=0)
    clear("render_image", expected_revision=saved.revision)
    record = selected.create(
        jobs.JobIntent(
            "panorama",
            selected.scope,
            origin,
            "model",
            "update-skybox-model",
            digest(b"fixture panorama payload"),
            digest(b"fixture panorama quote"),
            "2.5",
        )
    )
    for state, extra in (
        ("submitting", {}),
        ("remote", {"remote_job_id": "remote-panorama"}),
        ("succeeded", {}),
    ):
        record = selected.transition(
            "panorama", expected_revision=record.revision, state=jobs.JobState(state), **extra
        )
    asset = jobs.ResultAsset(
        "asset-panorama",
        "000-panorama.exr",
        "image/aces",
        source="original",
        projection="equirectangular",
    )
    record = selected.set_results("panorama", (asset,), expected_revision=record.revision)
    record = selected.transition(
        "panorama", expected_revision=record.revision, state=jobs.JobState.DOWNLOADING
    )
    data = b"offline preserved EXR original bytes"
    (results._directory(record) / asset.name).write_bytes(data)
    receipt = transfers.DownloadedResult(asset.name, len(data), digest(data))
    record = selected.record_download(
        "panorama", asset.asset_id, receipt, expected_revision=record.revision
    )
    selected.transition("panorama", expected_revision=record.revision, state=jobs.JobState.READY)


def check_schema_10(selected, results):
    """The saved original and lane default must stay exact; the cleared lane stays cleared."""
    record = selected.get("panorama")
    asset = record.results[0].asset
    if (record.state.value, asset.source, asset.projection, asset.media_type) != (
        "ready",
        "original",
        "equirectangular",
        "image/aces",
    ) or asset.expected_size is not None:
        raise RuntimeError("Update lost the saved original or its projection")
    results.verify_ready("panorama", expected_revision=record.revision)
    image, render = (selected.trained_default(lane) for lane in DEFAULT_LANES)
    if image.default is None or image.default.picks[0].scale != 0.75:
        raise RuntimeError("Update lost the saved trained-model default")
    if render.default is not None or render.revision != 2:
        raise RuntimeError("Update lost the cleared default's revision")


def film_upload_snapshot(selected, other):
    """Film upload associations live outside job/upload record serialization."""
    if not hasattr(selected, "film_upload"):
        return None
    identity = ("update-production", "captured-reference")
    reference = selected.film_upload(*identity)
    if other.film_upload(*identity) is not None:
        raise RuntimeError("Film upload escaped its credential scope")
    return asdict(reference) if reference is not None else None


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
        paths.state_dir / "shared-jobs",
        api.Credentials("update-other-key", "update-other-secret"),
        project_id=PROJECT_ID,
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


def workflow_form(scene):
    form = getattr(scene, "scenario_workflow", None)
    if form is None:
        return None
    fields = form.bl_rna.properties["inputs"].fixed_type.properties
    return form if "asset_scope" in fields and "asset_value" in fields else None


def seed_workflow(scene, selected):
    form = workflow_form(scene)
    if form is None:
        return
    controls = module("blender.workflow_controls")
    controls.load_form(
        form,
        {
            "id": "update-workflow",
            "name": "Preserved workflow",
            "inputs": [
                {"name": "prompt", "type": "string", "default": "Preserve Café 雪"},
                {"name": "image", "type": "file", "kind": "image"},
                {"name": "images", "type": "file_array", "kind": "image", "minItems": 2},
            ],
        },
    )
    scope = module("blender.reference_form").scope_key(selected.scope)
    for name, value in {
        "image": "update-workflow-image",
        "images": ["update-workflow-first", "update-workflow-second"],
    }.items():
        item = form.inputs[name]
        item.text = value if isinstance(value, str) else controls._json(value)
        item.enabled = True
        item.asset_scope = scope
        item.asset_value = controls._json(value)


def workflow_snapshot(scene, other=None):
    form = workflow_form(scene)
    if form is None or not form.loaded_id:
        return None
    controls = module("blender.workflow_controls")
    values = controls.parameters(form)
    if other is not None:
        runtime = module("blender.runtime")
        with patch.object(runtime.state, "job_store", other):
            try:
                controls.parameters(form)
            except ValueError:
                pass
            else:
                raise RuntimeError("Workflow references escaped their selected connection")
    return {"signature": controls.signature(form), "parameters": values}


def seed(profile):
    import bpy

    prefs = bpy.context.preferences.addons[PACKAGE].preferences
    prefs.credential_source = "PREFERENCES"
    prefs.api_key, prefs.api_secret = "update-fixture-key", "update-fixture-secret"
    prefs.project_id = PROJECT_ID
    prefs.output_dir = str(profile / "output")
    prefs.composer_enabled = False
    prefs.composer_offset_x, prefs.composer_offset_y = 23.0, 47.0
    prefs.composer_width = 640
    prefs.mcp_port, prefs.mcp_allow_python = 19876, False
    paths, selected, other, uploads, sources, results = stores()
    jobs = module("core.jobs.store")
    origin = jobs.JobOrigin(*ORIGIN)
    mesh_binding = seed_mesh_upload(profile, selected, uploads, sources, origin)
    seed_film_upload(selected, uploads)
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
        intent = replace(
            template,
            request_id=desired,
            mesh_sources=(mesh_binding,) if desired in {"ready", "applied"} else (),
        )
        binding = film_binding(desired)
        if binding is not None:
            intent = replace(intent, film_task=binding)
        record = selected.create(intent)

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
            "asset-" + desired,
            "result.png",
            "image/png",
            len(data),
            digest(data),
            texture_role="base",
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
    if supports_schema_10():
        seed_schema_10(selected, results, origin, model_defaults_owner())
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
    seed_workflow(scene, selected)
    bpy.ops.wm.save_userpref()
    bpy.ops.wm.save_as_mainfile(filepath=str(profile / "state.blend"), check_existing=False)


def check_project_scope(paths, prefs, selected, *, scene=None):
    """A saved override must still select its original jobs after update/restart."""
    if prefs.project_id != PROJECT_ID or selected.scope.project_id != PROJECT_ID:
        raise RuntimeError("Update lost the selected project preference or runtime scope")
    binding = module("core.jobs.credential_storage")
    credentials = module("core.api.sdk_adapter").Credentials(prefs.api_key, prefs.api_secret)
    for project_id in (None, "update-other-project"):
        other = binding.open_credential_store(
            paths.state_dir / "shared-jobs", credentials, project_id=project_id
        )
        uploads = module("core.jobs.upload_store").UploadStore(
            paths.state_dir / "shared-uploads/uploads.sqlite3", other.scope
        )
        film_upload_snapshot(selected, other)
        if scene is not None:
            workflow_snapshot(scene, other)
        if other.records() or uploads.records():
            raise RuntimeError("Update lost job or upload project isolation")
        if hasattr(other, "trained_defaults") and (
            other.trained_defaults()
            or any(other.trained_default(lane).revision for lane in DEFAULT_LANES)
        ):
            raise RuntimeError("Update lost trained-model default project isolation")


def snapshot(profile):
    import bpy

    paths, selected, other, uploads, sources, results = stores()
    prefs = bpy.context.preferences.addons[PACKAGE].preferences
    if not paths.state_dir.resolve().is_relative_to(profile):
        raise RuntimeError("Scenario storage escaped the disposable profile")
    check_project_scope(paths, prefs, selected, scene=bpy.context.scene)
    records = selected.records()
    names = {record.intent.request_id for record in records}
    if (
        names - {"panorama"} != BASE_JOBS
        or selected.get("other-scope") is not None
        or len(other.records()) != 1
    ):
        raise RuntimeError("Update lost durable records or credential isolation")
    check_mesh_bindings(selected, uploads)
    check_local_applications(selected)
    if "panorama" in names:
        check_schema_10(selected, results)
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
            "project_id",
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
        "jobs": [job_snapshot(r) for r in records],
        "other_jobs": [job_snapshot(r) for r in other.records()],
        "uploads": [asdict(r) for r in uploads.records()],
        "film_upload": film_upload_snapshot(selected, other),
        "trained_defaults": trained_defaults_snapshot(selected, other),
        "files": files,
        "scene": scene,
        "workflow": workflow_snapshot(bpy.context.scene, other),
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
    evidence_path = profile.parent / "update-evidence.json"
    with no_service_connections():
        if args.restart:
            check_version(profile, args.after)
            bpy.ops.wm.open_mainfile(filepath=str(profile / "state.blend"))
            expected = json.loads(expected_path.read_text())
            if snapshot(profile) != expected:
                raise RuntimeError("Scenario state changed after restart")
            evidence = json.loads(evidence_path.read_text())
            if store_schema(module("blender.runtime").paths()) != evidence["store_schema"]["after"]:
                raise RuntimeError("Job storage version changed after restart")
            selected = module("blender.runtime").ensure_job_store()
            preserved = check_model_defaults(selected, model_defaults_owner())
            if preserved != evidence["model_defaults_preserved"]:
                raise RuntimeError("Runtime lane defaults changed after restart")
        else:
            check_version(profile, args.before)
            seed(profile)
            expected = snapshot(profile)
            expected_path.write_text(json.dumps(expected, indent=2) + "\n")
            before_schema = store_schema(module("blender.runtime").paths())
            seeded = "before-update" if expected["trained_defaults"] is not None else None
            if bpy.ops.extensions.repo_sync_all() != {"FINISHED"}:
                raise RuntimeError("Native repository sync failed")
            if bpy.ops.extensions.package_upgrade_all() != {"FINISHED"}:
                raise RuntimeError("Native Scenario upgrade failed")
            check_version(profile, args.after)
            # The first post-update store access performs any schema upgrade.
            if snapshot(profile) != expected:
                raise RuntimeError("Scenario state changed during native update")
            after_schema = store_schema(module("blender.runtime").paths())
            if seeded is None and supports_schema_10():
                # Write schema 10 state into the upgraded store; restart must keep it.
                _, selected, _, _, _, results = stores()
                origin = module("core.jobs.store").JobOrigin(*ORIGIN)
                seed_schema_10(selected, results, origin, model_defaults_owner())
                expected = snapshot(profile)
                expected_path.write_text(json.dumps(expected, indent=2) + "\n")
                seeded = "after-upgrade"
            selected = module("blender.runtime").ensure_job_store()
            evidence = {
                "store_schema": {"before": before_schema, "after": after_schema},
                "schema_10_state": seeded or "unavailable",
                "model_defaults_preserved": check_model_defaults(selected, model_defaults_owner()),
            }
            evidence_path.write_text(json.dumps(evidence) + "\n")
            bpy.ops.wm.save_userpref()
        args.report.write_text(
            json.dumps(
                {
                    "before": args.before,
                    "after": args.after,
                    "enabled": True,
                    "state_preserved": True,
                    "scene_preserved": True,
                    "project_scope_preserved": True,
                    "workflow_references_preserved": expected["workflow"] is not None,
                    "service_requests": 0,
                    **evidence,
                }
            )
            + "\n"
        )


if __name__ == "__main__":
    main()
