# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Write the schema 9 job-store fixture with the predecessor's own storage code.

The committed `tests/fixtures/synthetic/jobs-schema9.sql` was produced by
extracting `scenario/` from commit b57c398f (the last schema 9 main revision) and
running this script against it. It uses only that code's public store API, so
the upgrade tests rebuild a database the previous release candidate really wrote.
The fixture is the SQL dump of that database plus its two header pragmas, because
the repository does not commit database files:

    git archive b57c398f scenario | tar -x -C <empty directory>
    uv run --locked --no-env-file python tools/make_job_store_fixture.py \
        --source <empty directory> --output <new directory>/jobs-schema9.sql
    cmp <new directory>/jobs-schema9.sql tests/fixtures/synthetic/jobs-schema9.sql

The output must be a new file; delete the committed fixture first only to replace it.

All identities are synthetic. No Scenario request, credential or Blender is used.
"""

import argparse
import hashlib
import importlib
import sqlite3
import sys
import tempfile
from contextlib import closing
from dataclasses import replace
from pathlib import Path

SERVICE = "https://service.example.invalid/v1"
HEADER = (
    "-- SPDX-FileCopyrightText: 2026 Scenario Inc.\n"
    "-- SPDX-License-Identifier: GPL-3.0-or-later\n"
    "-- Schema 9 job store written by tools/make_job_store_fixture.py with the\n"
    "-- predecessor's storage code; see tests/fixtures/README.md. Synthetic data only.\n"
)


def digest(value):
    return hashlib.sha256(value.encode()).hexdigest()


def load(source):
    """Import storage from the selected tree only, never the current checkout."""
    source = source.resolve(strict=True)
    if not (source / "scenario/core/jobs/store.py").is_file():
        raise ValueError("Select a directory containing an extracted scenario package")
    sys.path.insert(0, str(source))
    modules = {
        name: importlib.import_module(f"scenario.core.jobs.{name}")
        for name in ("store", "mesh_source", "transfers")
    }
    for module in modules.values():
        if not Path(module.__file__).resolve().is_relative_to(source):
            raise ValueError("Storage was imported from outside the selected source")
    if modules["store"]._VERSION != 9:
        raise ValueError("This fixture records schema 9 only")
    return modules


def advance(store, record, *states, **kwargs):
    for state in states:
        extra = kwargs if state.value == "remote" else {}
        record = store.transition(
            record.intent.request_id, expected_revision=record.revision, state=state, **extra
        )
    return record


def deliver(store, jobs, transfers, record, assets, *, receipts=None):
    """Bind a manifest, then save receipts for the selected assets (default: all)."""
    record = store.set_results(record.intent.request_id, assets, expected_revision=record.revision)
    record = advance(store, record, jobs.JobState.DOWNLOADING)
    for asset in assets:
        if receipts is not None and asset.asset_id not in receipts:
            continue
        size = asset.expected_size if asset.expected_size is not None else 11
        receipt = transfers.DownloadedResult(asset.name, size, asset.expected_sha256 or "c" * 64)
        record = store.record_download(
            record.intent.request_id, asset.asset_id, receipt, expected_revision=record.revision
        )
    return record


def write(modules, output):
    jobs, mesh, transfers = modules["store"], modules["mesh_source"], modules["transfers"]
    state = jobs.JobState
    selected = jobs.JobScope(SERVICE, "local-key-fixture-selected", "fixture-project")
    other = jobs.JobScope(SERVICE, "local-key-fixture-other")
    store = jobs.JobStore(output, selected)
    origin = jobs.JobOrigin("fixture-file", "fixture-scene", "fixture-revision", "fixture-target")
    source = mesh.MeshSource(
        digest("fixture mesh export"),
        (
            mesh.MeshSourceObject(
                "fixture-target",
                digest("fixture geometry"),
                ((1, 0, 0, 2), (0, 1, 0, 3), (0, 0, 1, 4), (0, 0, 0, 1)),
            ),
        ),
    )
    binding = jobs.JobMeshSource(
        "mesh", None, "fixture-mesh-asset", "fixture-mesh-upload", 9, origin, source
    )
    template = jobs.JobIntent(
        "template",
        selected,
        origin,
        "model",
        "model_fixture",
        digest("fixture payload"),
        digest("fixture exact quote"),
        "0.1234567890123456789",
    )

    def create(name, **changes):
        return store.create(replace(template, request_id=name, **changes))

    png = jobs.ResultAsset("asset-png", "000-png.png", "image/png", 5, "1" * 64, "normal")
    exr = jobs.ResultAsset("asset-exr", "001-exr.bin", "image/x-exr", 7, "2" * 64)
    jpeg = jobs.ResultAsset("asset-jpeg", "002-jpeg.jpg", "image/jpeg", 9, "3" * 64)
    glb = jobs.ResultAsset("asset-glb", "000-glb.glb", "model/gltf-binary", 13, "4" * 64)

    create("a-prepared")
    advance(store, create("b-uncertain", operation="workflow"), state.SUBMITTING, state.UNCERTAIN)
    advance(store, create("c-translate", operation="translate"), state.SUBMITTING)
    advance(
        store,
        create("d-prompt", operation="prompt"),
        state.SUBMITTING,
        state.REMOTE,
        remote_job_id="remote-d",
    )
    advance(
        store,
        create("e-cancel-requested"),
        state.SUBMITTING,
        state.REMOTE,
        state.CANCEL_REQUESTED,
        remote_job_id="remote-e",
    )
    advance(store, create("f-canceled"), state.CANCELED)
    advance(
        store,
        create("g-failed"),
        state.SUBMITTING,
        state.REMOTE,
        state.FAILED,
        remote_job_id="remote-g",
    )
    succeeded = advance(
        store,
        create("h-manifest"),
        state.SUBMITTING,
        state.REMOTE,
        state.SUCCEEDED,
        remote_job_id="remote-h",
    )
    store.set_results("h-manifest", (jpeg,), expected_revision=succeeded.revision)
    partial = advance(
        store,
        create("i-download-failed"),
        state.SUBMITTING,
        state.REMOTE,
        state.SUCCEEDED,
        remote_job_id="remote-i",
    )
    partial = deliver(store, jobs, transfers, partial, (png, exr), receipts={"asset-png"})
    advance(store, partial, state.DOWNLOAD_FAILED)
    ready = advance(
        store,
        create("j-ready", mesh_sources=(binding,)),
        state.SUBMITTING,
        state.REMOTE,
        state.SUCCEEDED,
        remote_job_id="remote-j",
    )
    advance(store, deliver(store, jobs, transfers, ready, (png, exr, jpeg)), state.READY)
    failed = advance(
        store,
        create("k-apply-failed"),
        state.SUBMITTING,
        state.REMOTE,
        state.SUCCEEDED,
        remote_job_id="remote-k",
    )
    failed = advance(store, deliver(store, jobs, transfers, failed, (glb,)), state.READY)
    failed = store.transition(
        "k-apply-failed",
        expected_revision=failed.revision,
        state=state.APPLYING,
        application_origin=replace(origin, scene_id="approved-scene"),
    )
    advance(store, failed, state.APPLY_FAILED)
    applied = advance(
        store,
        create("l-applied"),
        state.SUBMITTING,
        state.REMOTE,
        state.SUCCEEDED,
        remote_job_id="remote-l",
    )
    applied = advance(store, deliver(store, jobs, transfers, applied, (png, jpeg)), state.READY)
    applied = advance(store, applied, state.APPLYING, state.APPLIED)
    for name, outcome in (
        ("reuse-applied", jobs.LocalApplicationState.APPLIED),
        ("reuse-failed", jobs.LocalApplicationState.FAILED),
        ("reuse-unfinished", None),
    ):
        applied = store.claim_local_application(
            "l-applied",
            expected_revision=applied.revision,
            application_id=name,
            destination=replace(origin, scene_id=name),
            purpose="world" if name == "reuse-failed" else "images",
            asset_ids=("asset-png",),
        )
        if outcome is not None:
            applied = store.finish_local_application(
                "l-applied",
                expected_revision=applied.revision,
                application_id=name,
                state=outcome,
            )
    film = jobs.FilmTaskBinding("fixture-production", "take-one", digest("recipe"), digest("take"))
    advance(
        store,
        create("m-film", film_task=film),
        state.SUBMITTING,
        state.REMOTE,
        remote_job_id="remote-m",
    )
    store.bind_film_upload(
        jobs.FilmUploadReference(
            selected,
            replace(film, task_id="upload-one", task_sha256=digest("upload")),
            "fixture-upload-request",
            7,
            "fixture-upload-asset",
            digest("fixture upload source"),
            "image",
        )
    )
    cloud = store.adopt_cloud_job(
        jobs.CloudJobIntent("n-cloud", selected, replace(origin, target_id=None), "model_fixture"),
        "remote-n",
    )
    advance(store, deliver(store, jobs, transfers, cloud, (jpeg,)), state.READY)
    elsewhere = jobs.JobStore(output, other)
    elsewhere.create(replace(template, request_id="a-prepared", scope=other))


def dump(database):
    """Return the database as replayable SQL, including its identity pragmas."""
    with closing(sqlite3.connect(database)) as connection:
        version = connection.execute("PRAGMA user_version").fetchone()[0]
        application = connection.execute("PRAGMA application_id").fetchone()[0]
        statements = list(connection.iterdump())
    return (
        HEADER
        + "".join(statement + "\n" for statement in statements)
        + f"PRAGMA application_id={application};\nPRAGMA user_version={version};\n"
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists() or args.output.suffix != ".sql":
        parser.error("--output must be a new .sql file")
    modules = load(args.source)
    with tempfile.TemporaryDirectory() as directory:
        database = Path(directory) / "jobs.sqlite3"
        write(modules, database)
        text = dump(database)
    with args.output.open("x", encoding="utf-8", newline="\n") as output:
        output.write(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
