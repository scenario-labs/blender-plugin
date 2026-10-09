# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Worker-side splat preparation binds decoded bytes to saved receipts and one claim."""

import hashlib
import struct
import threading
from dataclasses import asdict
from types import SimpleNamespace

import httpx
import pytest
from splat_files import ply_bytes, splat_record, splat_row, spz_payload

from scenario.core.api.sdk_adapter import Credentials, SDKAdapter
from scenario.core.jobs import results
from scenario.core.jobs.coordinator import ApplicationError, JobCoordinator
from scenario.core.jobs.origins import OriginRevisions
from scenario.core.jobs.results import ResultError
from scenario.core.jobs.store import (
    JobIntent,
    JobScope,
    JobState,
    JobStore,
    ResultAsset,
    StoreConflict,
    _json,
)
from scenario.core.jobs.transfers import DownloadedResult, ResultDownloader, StoragePolicy
from scenario.core.jobs.workers import JobWorkers, WorkerError
from scenario.core.scene import splats
from scenario.core.scene.splats import SplatCancelled, SplatOptions

SCOPE = JobScope("https://service.example.invalid/v1", "account", "project", "team")
OPTIONS = SplatOptions(1000, "OPENGL")
ASSETS = {
    "asset-spz": ("model/spz", "spz", spz_payload(30, version=3)),
    "asset-ply": ("model/ply", "ply", ply_bytes([splat_row(i) for i in range(5)])),
    "asset-mesh": (
        "application/x-ply",
        "ply",
        ply_bytes([{"x": 1.0}], properties=[("x", "float"), ("y", "float"), ("z", "float")]),
    ),
    "asset-splat": (
        "model/splat",
        "splat",
        b"".join(splat_record((i, 0, 0), (0.1, 0.1, 0.1), (9, 9, 9, 9)) for i in range(4)),
    ),
    "asset-v4": ("model/spz", "spz", b"NGSP" + struct.pack("<II", 4, 1) + bytes(56)),
    "asset-glb": ("model/gltf-binary", "glb", b"glTF" + bytes(16)),
}


def _ready(store, request_id, origin, assets):
    record = store.create(
        JobIntent(request_id, SCOPE, origin, "model", "model", "a" * 64, "b" * 64, "1.0")
    )
    for state in (JobState.SUBMITTING, JobState.REMOTE, JobState.SUCCEEDED):
        record = store.transition(
            request_id,
            expected_revision=record.revision,
            state=state,
            remote_job_id="remote-" + request_id if state == JobState.REMOTE else None,
        )
    if not assets:
        return record
    record = store.set_results(request_id, tuple(assets), expected_revision=record.revision)
    record = store.transition(
        request_id, expected_revision=record.revision, state=JobState.DOWNLOADING
    )
    for asset in assets:
        receipt = DownloadedResult(asset.name, asset.expected_size, asset.expected_sha256)
        record = store.record_download(
            request_id, asset.asset_id, receipt, expected_revision=record.revision
        )
    return store.transition(request_id, expected_revision=record.revision, state=JobState.READY)


@pytest.fixture
def env(tmp_path):
    origins = OriginRevisions()
    origin = origins.capture("scene", "target")
    store = JobStore(tmp_path / "jobs.sqlite3", SCOPE)
    root = tmp_path / "results"
    directory = root / hashlib.sha256(_json(asdict(SCOPE)).encode()).hexdigest()
    directory /= hashlib.sha256(b"request").hexdigest()
    directory.mkdir(parents=True)
    assets, paths = [], {}
    for index, (asset_id, (media_type, suffix, data)) in enumerate(ASSETS.items()):
        name = f"{index:03d}-{hashlib.sha256(asset_id.encode()).hexdigest()[:24]}.{suffix}"
        digest = hashlib.sha256(data).hexdigest()
        assets.append(ResultAsset(asset_id, name, media_type, len(data), digest))
        paths[asset_id] = directory / name
        paths[asset_id].write_bytes(data)
    ready = _ready(store, "request", origin, assets)
    pending = _ready(store, "pending", origin, ())
    requests = []

    def deny(request):
        requests.append(request)
        pytest.fail("Splat preparation must never contact a service")

    adapter = SDKAdapter(
        Credentials("fixture-key", "fixture-secret"),
        base_url=SCOPE.service,
        account_id=SCOPE.account_id,
        project_id=SCOPE.project_id,
        team_id=SCOPE.team_id,
        online=lambda: False,
        transport=httpx.MockTransport(deny),
    )
    coordinator = JobCoordinator(
        adapter,
        store,
        origin_guard=origins.guard,
        result_root=root,
        result_downloader=ResultDownloader(
            StoragePolicy(frozenset({"storage.example.invalid"})), online_access=lambda: False
        ),
    )
    yield SimpleNamespace(
        coordinator=coordinator, store=store, ready=ready, pending=pending, paths=paths
    )
    coordinator.close()
    assert requests == []


def prepare(env, asset_id="asset-spz", *, cancel=None, options=OPTIONS, revision=None):
    return env.coordinator.prepare_model_import(
        "request",
        expected_revision=env.ready.revision if revision is None else revision,
        asset_id=asset_id,
        options=options,
        cancel=cancel or threading.Event(),
    )


def registered(env):
    return len(env.coordinator._verified_results)


@pytest.mark.parametrize(
    "asset_id, fmt, kept",
    [("asset-spz", "spz", 30), ("asset-ply", "ply", 5), ("asset-splat", "splat", 4)],
)
def test_each_splat_format_yields_a_snapshot_bound_to_current_receipts(env, asset_id, fmt, kept):
    prepared = prepare(env, asset_id)
    assert (prepared.splat.format, prepared.splat.kept, prepared.ply_mesh) == (fmt, kept, False)
    assert prepared.asset_id == asset_id and prepared.options == OPTIONS
    assert prepared.media_type == ASSETS[asset_id][0]
    assert prepared.verified.record == env.ready == env.store.get("request")
    assert all(path.exists() for path in prepared.verified.paths)
    assert "SplatData" not in repr(prepared)


def test_ply_without_gaussian_properties_routes_to_a_mesh_importer(env):
    prepared = prepare(env, "asset-mesh")
    assert prepared.ply_mesh and prepared.splat is None
    assert registered(env) == 1


def test_preparation_registers_one_single_use_claim_ticket(env):
    prepared = prepare(env)
    claim = env.coordinator.claim_application(prepared.verified)
    assert claim.record.state == JobState.APPLYING
    with pytest.raises(ApplicationError):
        env.coordinator.claim_application(prepared.verified)
    env.coordinator.fail_application(claim)


def test_retired_owner_invalidates_an_unclaimed_preparation(env):
    prepared = prepare(env)
    env.coordinator.deactivate()
    with pytest.raises(ApplicationError):
        env.coordinator.claim_application(prepared.verified)
    with pytest.raises(ResultError, match="inactive"):
        prepare(env)


@pytest.mark.parametrize(
    "asset_id, message",
    [
        ("asset-glb", "SPZ, PLY or .splat"),
        ("asset-unknown", "Choose one saved model result"),
        ("asset-v4", r"v4 \(ZSTD\)"),
    ],
)
def test_unsupported_assets_fail_without_registration_or_changes(env, asset_id, message):
    before = {key: path.read_bytes() for key, path in env.paths.items()}
    with pytest.raises(ResultError, match=message):
        prepare(env, asset_id)
    assert registered(env) == 0
    assert env.store.get("request") == env.ready
    assert {key: path.read_bytes() for key, path in env.paths.items()} == before


def test_pending_downloads_and_stale_revisions_are_rejected(env):
    with pytest.raises(ResultError, match="Download"):
        env.coordinator.prepare_model_import(
            "pending",
            expected_revision=env.pending.revision,
            asset_id="asset-spz",
            options=OPTIONS,
            cancel=threading.Event(),
        )
    with pytest.raises(StoreConflict):
        prepare(env, revision=env.ready.revision + 1)
    assert registered(env) == 0


def _change_after_open(monkeypatch, path, change):
    original = results._open

    def opened(target):
        source = original(target)
        if target == path:
            change(path)
        return source

    monkeypatch.setattr(results, "_open", opened)


def _overwrite(offset):
    def change(path):
        with path.open("r+b") as handle:
            handle.seek(offset, 2 if offset < 0 else 0)
            value = handle.read(1)
            handle.seek(-1, 1)
            handle.write(bytes([value[0] ^ 0xFF]))

    return change


@pytest.mark.parametrize(
    "change",
    [
        _overwrite(-1),  # gzip trailer: decodable, but no longer the saved bytes
        _overwrite(12),  # compressed header: undecodable, still reported as changed
        lambda path: path.open("ab").write(b"extra"),
    ],
)
def test_bytes_changed_after_verification_discard_the_snapshot(env, monkeypatch, change):
    _change_after_open(monkeypatch, env.paths["asset-spz"], change)
    with pytest.raises(ResultError, match="changed while it was prepared"):
        prepare(env)
    assert registered(env) == 0


def test_replaced_or_missing_files_fail_before_decoding(env, monkeypatch):
    path = env.paths["asset-spz"]
    original = results.ResultCommands.verify_ready

    def verify_then_remove(self, *args, **kwargs):
        verified = original(self, *args, **kwargs)
        path.unlink()
        return verified

    monkeypatch.setattr(results.ResultCommands, "verify_ready", verify_then_remove)
    with pytest.raises(ResultError, match="could not be verified"):
        prepare(env)


def test_record_change_during_decoding_raises_store_conflict(env, monkeypatch):
    original = splats.decode

    def decode_and_change(*args, **kwargs):
        result = original(*args, **kwargs)
        env.store.transition(
            "request", expected_revision=env.ready.revision, state=JobState.APPLYING
        )
        return result

    monkeypatch.setattr(splats, "decode", decode_and_change)
    with pytest.raises(StoreConflict):
        prepare(env)
    assert registered(env) == 0


@pytest.mark.parametrize("during", [False, True])
def test_cancellation_never_registers_a_preparation(env, monkeypatch, during):
    cancel = threading.Event()
    if during:
        original = splats.decode

        def decode_then_cancel(*args, **kwargs):
            result = original(*args, **kwargs)
            cancel.set()
            return result

        monkeypatch.setattr(splats, "decode", decode_then_cancel)
    else:
        cancel.set()
    with pytest.raises(SplatCancelled):
        prepare(env, cancel=cancel)
    assert registered(env) == 0


def test_options_must_be_reviewed_before_queueing(env):
    with pytest.raises(TypeError):
        prepare(env, options={"max_points": 10, "axes": "OPENGL"})
    workers = JobWorkers(env.coordinator, workers=1)
    try:
        with pytest.raises(TypeError):
            workers.prepare_model_import(
                "request", expected_revision=env.ready.revision, asset_id="asset-spz", options=None
            )
    finally:
        workers.shutdown()


def test_workers_decode_off_the_calling_thread(env, monkeypatch):
    threads = []
    original = splats.decode

    def record_thread(*args, **kwargs):
        threads.append(threading.current_thread())
        return original(*args, **kwargs)

    monkeypatch.setattr(splats, "decode", record_thread)
    workers = JobWorkers(env.coordinator, workers=1)
    try:
        task = workers.prepare_model_import(
            "request", expected_revision=env.ready.revision, asset_id="asset-ply", options=OPTIONS
        )
        prepared = task.result(timeout=10)
    finally:
        workers.shutdown()
    assert prepared.splat.format == "ply"
    assert threads and threads[0] is not threading.current_thread()


def test_worker_cancellation_uses_the_single_local_operation_slot(env, monkeypatch):
    started = threading.Event()
    original = splats.decode

    def wait_for_cancel(*args, cancel, **kwargs):
        started.set()
        assert cancel.wait(10)
        return original(*args, cancel=cancel, **kwargs)

    monkeypatch.setattr(splats, "decode", wait_for_cancel)
    workers = JobWorkers(env.coordinator, workers=2)
    try:
        task = workers.prepare_model_import(
            "request", expected_revision=env.ready.revision, asset_id="asset-spz", options=OPTIONS
        )
        assert started.wait(10)
        with pytest.raises(WorkerError, match="local media operation"):
            workers.prepare_model_import(
                "request",
                expected_revision=env.ready.revision,
                asset_id="asset-splat",
                options=OPTIONS,
            )
        workers.cancel_local(task)
        with pytest.raises(SplatCancelled):
            task.result(timeout=10)
    finally:
        workers.shutdown()
    assert registered(env) == 0
