# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Declared sizes of saved World candidates for the World offer, offline and unpaid."""

import hashlib
import struct
import threading

import pytest

from scenario.core.jobs.preview_scheduler import BATCH_LIMIT
from scenario.core.jobs.result_previews import LOCAL_HEADER_BYTES, PreviewCanceled
from scenario.core.jobs.results import WORLD_HEADER_BYTES, ResultError
from scenario.core.jobs.store import JobIntent, JobState, ResultAsset
from scenario.core.jobs.transfers import DownloadedResult
from scenario.core.jobs.workers import JobWorkers
from tests.unit.test_playback import assert_offline
from tests.unit.test_result_previews import ORIGIN, SCOPE, exr, jpeg, png, preview_env


def digest(data):
    return hashlib.sha256(data).hexdigest()


def saved(service, assets, request_id="request"):
    """A READY job whose receipts match private local bytes; assets are (asset, bytes)."""
    store = service.store
    current = store.create(
        JobIntent(request_id, SCOPE, ORIGIN, "model", "model", "a" * 64, "b" * 64, "1.0")
    )
    for state in (JobState.SUBMITTING, JobState.REMOTE, JobState.SUCCEEDED):
        current = store.transition(
            request_id,
            expected_revision=current.revision,
            state=state,
            remote_job_id="remote" if state == JobState.REMOTE else None,
        )
    manifest = tuple(asset for asset, _ in assets)
    current = store.set_results(request_id, manifest, expected_revision=current.revision)
    current = store.transition(
        request_id, expected_revision=current.revision, state=JobState.DOWNLOADING
    )
    directory = service.coordinator._results._directory(current)
    for asset, data in assets:
        (directory / asset.name).write_bytes(data)
        receipt = DownloadedResult(asset.name, len(data), digest(data))
        current = store.record_download(
            request_id, asset.asset_id, receipt, expected_revision=current.revision
        )
    record = store.transition(request_id, expected_revision=current.revision, state=JobState.READY)
    return record, directory


def image(asset_id, media_type, data, *, role=None):
    suffix = {"image/png": "png", "image/jpeg": "jpg", "image/webp": "webp"}.get(media_type, "exr")
    return ResultAsset(asset_id, f"{asset_id}.{suffix}", media_type, len(data), texture_role=role)


def targets_of(record, *asset_ids):
    items = {item.asset.asset_id: item for item in record.results}
    return tuple(
        (record.intent.request_id, asset_id, items[asset_id].receipt.sha256)
        for asset_id in asset_ids
    )


def measure(service, targets, cancel=None):
    return service.coordinator.world_sizes(tuple(targets), cancel=cancel or threading.Event())


FILLER = b"\xff\xef" + struct.pack(">H", 0xFFFF) + b"\x00" * 0xFFFD


def padded_jpeg(width, height, segments):
    """A JPEG whose frame header follows that many full APP15 segments."""
    return b"\xff\xd8" + FILLER * segments + jpeg(width, height)[2:]


@pytest.fixture
def env(tmp_path):
    with preview_env(tmp_path) as state:
        yield state


def test_each_candidate_reports_the_size_its_header_declares(env):
    files = {
        "sky": ("image/png", png(8, 4)),
        "square": ("image/png", png(4, 4)),
        "wide": ("image/jpeg", jpeg(16, 9)),
        "hdr": ("image/x-exr", exr(64, 32)),
        "aces": ("image/aces", exr(48, 48)),
    }
    record, _ = saved(env, [(image(key, kind, data), data) for key, (kind, data) in files.items()])
    targets = targets_of(record, *files)
    assert measure(env, targets) == tuple(
        (*target, size)
        for target, size in zip(targets, [(8, 4), (4, 4), (16, 9), (64, 32), (48, 48)], strict=True)
    )
    # A header read for display: no network, no hashing receipt, no store change.
    assert env.store.get("request") == record
    assert_offline(env)


def test_stale_or_ineligible_targets_have_no_size(env):
    sky, albedo, still = png(8, 4), png(16, 8), png(8, 4)
    record, _ = saved(
        env,
        [
            (image("sky", "image/png", sky), sky),
            (image("albedo", "image/png", albedo, role="albedo"), albedo),
            (image("still", "image/webp", still), still),
        ],
    )
    request_id = record.intent.request_id
    stale = (request_id, "sky", digest(b"another download"))
    targets = (
        stale,
        *targets_of(record, "albedo", "still"),
        (request_id, "missing", digest(sky)),
        ("other-request", "sky", digest(sky)),
    )
    assert [size for *_, size in measure(env, targets)] == [None] * 5


def test_unreadable_or_undeclared_headers_have_no_size(env):
    # Its frame header starts beyond the bytes the World offer reads.
    far = padded_jpeg(32, 16, WORLD_HEADER_BYTES // len(FILLER) + 1)
    short = png(8, 4)[:20]
    gone = png(8, 4)
    record, directory = saved(
        env,
        [
            (image("far", "image/jpeg", far), far),
            (image("short", "image/png", short), short),
            (image("gone", "image/png", gone), gone),
        ],
    )
    (directory / "gone.png").unlink()
    targets = targets_of(record, "far", "short", "gone")
    assert [size for *_, size in measure(env, targets)] == [None, None, None]
    # Within the bound the same frame header is read.
    near = padded_jpeg(32, 16, WORLD_HEADER_BYTES // len(FILLER) - 1)
    record, _ = saved(env, [(image("near", "image/jpeg", near), near)], request_id="near-request")
    assert measure(env, targets_of(record, "near"))[0][-1] == (32, 16)
    assert WORLD_HEADER_BYTES == LOCAL_HEADER_BYTES


def test_one_check_reads_at_most_one_preview_batch(env):
    # A full preview batch is accepted; the targets beyond it are refused above.
    data = png(8, 4)
    record, _ = saved(env, [(image("sky", "image/png", data), data)])
    targets = targets_of(record, "sky") * BATCH_LIMIT
    assert [size for *_, size in measure(env, targets)] == [(8, 4)] * BATCH_LIMIT


@pytest.mark.parametrize(
    "targets",
    [
        (),
        (("request", "sky"),),
        (("request", "sky", "not-a-digest"),),
        (("request", "", "a" * 64),),
        (("request", "sky", "a" * 64),) * (BATCH_LIMIT + 1),
        None,
    ],
)
def test_targets_are_validated_before_any_read(env, targets):
    with pytest.raises(ResultError, match="World candidates"):
        env.coordinator.world_sizes(targets, cancel=threading.Event())


def test_a_canceled_check_stops_before_the_next_read(env):
    data = png(8, 4)
    record, _ = saved(env, [(image("sky", "image/png", data), data)])
    cancel = threading.Event()
    cancel.set()
    with pytest.raises(PreviewCanceled):
        measure(env, targets_of(record, "sky"), cancel)


def test_world_sizes_run_on_the_preview_lane(env, monkeypatch):
    data = png(8, 4)
    record, _ = saved(env, [(image("sky", "image/png", data), data)])
    threads, original = [], env.coordinator.world_sizes

    def recorded(*args, **kwargs):
        threads.append(threading.current_thread().name)
        return original(*args, **kwargs)

    monkeypatch.setattr(env.coordinator, "world_sizes", recorded)
    workers = JobWorkers(env.coordinator, workers=1)
    try:
        result = workers.world_sizes(targets_of(record, "sky")).result(timeout=5)
    finally:
        workers.deactivate()
        workers.shutdown()
    assert threads == ["ScenarioPreview"]
    assert result == ((*targets_of(record, "sky")[0], (8, 4)),)
    assert_offline(env)
