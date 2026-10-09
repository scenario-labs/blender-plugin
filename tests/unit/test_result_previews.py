# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Receipt-bound result previews through the real SDK adapter, offline and unpaid."""

import hashlib
import io
import json
import os
import struct
import threading
import time
import wave
import zlib
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace

import httpx
import pytest

from scenario.core.api.sdk_adapter import Credentials, SDKAdapter
from scenario.core.audio_waveform import EnvelopeBuilder
from scenario.core.jobs import result_previews as previews
from scenario.core.jobs.coordinator import JobCoordinator
from scenario.core.jobs.results import ResultError
from scenario.core.jobs.store import (
    JobIntent,
    JobOrigin,
    JobScope,
    JobState,
    JobStore,
    ResultAsset,
)
from scenario.core.jobs.transfers import (
    DownloadedResult,
    ResultDownloader,
    StoragePolicy,
    TransferError,
)

SCOPE = JobScope("https://service.example.invalid/v1", "account", "project")
ORIGIN = JobOrigin("file", "scene", "revision", "target")
CDN = "https://cdn.cloud.scenario.com"
STILL, CLIP, ENVELOPE = previews.STILL, previews.CLIP, previews.ENVELOPE
State = previews.PreviewState


def png(width, height):
    rows = b"".join(b"\x00" + b"\x80\x40\x20\xff" * width for _ in range(height))

    def chunk(kind, data):
        return (
            struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data))
        )

    header = struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0)
    return (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", header)
        + chunk(b"IDAT", zlib.compress(rows))
        + chunk(b"IEND", b"")
    )


def wav(frames=800, rate=8000):
    stream = io.BytesIO()
    with wave.open(stream, "wb") as sound:
        sound.setnchannels(1)
        sound.setsampwidth(2)
        sound.setframerate(rate)
        sound.writeframes(b"\x00\x10" * frames)
    return stream.getvalue()


JPEG = b"\xff\xd8\xff\xe0\x00\x10JFIF\x00" + b"\x00" * 64
MP4 = b"\x00\x00\x00\x18ftypisom\x00\x00\x02\x00isomiso2" + b"\x00" * 64
GLB = b"glTF\x02\x00\x00\x00" + b"\x00" * 64
GIF = b"GIF89a" + b"\x00" * 64


class FakeDownloader(ResultDownloader):
    """The real host policy and verification, with offline bytes per URL."""

    def __init__(self):
        super().__init__(
            StoragePolicy(frozenset({"cdn.cloud.scenario.com"})), online_access=lambda: True
        )
        self.files, self.calls = {}, []

    def download(self, url, *, root, name, max_bytes=None, **kwargs):
        self._policy.destination(url)
        self.calls.append((url, threading.current_thread()))
        data = self.files[url]
        if max_bytes is not None and len(data) > max_bytes:
            raise TransferError("Storage response exceeds the byte limit")
        with (Path(root) / name).open("xb") as output:
            output.write(data)
        return DownloadedResult(name, len(data), hashlib.sha256(data).hexdigest())


def asset_record(asset_id, media_type, *, thumbnail=None, preview=None):
    record = {
        "id": asset_id,
        "status": "success",
        "mimeType": media_type,
        "url": f"{CDN}/{asset_id}?Signature=result-secret",
    }
    if thumbnail is not None:
        record["thumbnail"] = {"assetId": f"{asset_id}-thumb", "url": thumbnail}
    if preview is not None:
        record["preview"] = {"assetId": f"{asset_id}-preview", "url": preview}
    return record


@pytest.fixture
def env(tmp_path):
    store = JobStore(tmp_path / "jobs.sqlite3", SCOPE)
    results = tmp_path / "results"
    cache = tmp_path / "previews"
    results.mkdir()
    cache.mkdir()
    state = SimpleNamespace(assets={}, calls=[], online=True, gate=None)

    def respond(request):
        assert request.url.params["projectId"] == "project"
        if request.method == "GET" and request.url.path.startswith("/v1/jobs/"):
            # Remote refresh on a job worker; never part of a preview batch.
            identifier = request.url.path.rsplit("/", 1)[-1]
            return httpx.Response(
                200, json={"job": {"jobId": identifier, "status": "in-progress", "progress": 0.5}}
            )
        state.calls.append((request.method, request.url.path, threading.current_thread()))
        if state.gate is not None:
            state.gate()
        if request.method == "POST" and request.url.path == "/v1/assets/get-bulk":
            identifiers = json.loads(request.content)["assetIds"]
            rows = [state.assets[name] for name in identifiers if name in state.assets]
            return httpx.Response(200, json={"assets": rows})
        if request.method == "GET" and request.url.path.startswith("/v1/assets/"):
            name = request.url.path.rsplit("/", 1)[-1]
            if name not in state.assets:
                return httpx.Response(404, json={"error": "missing"})
            return httpx.Response(200, json={"asset": state.assets[name]})
        pytest.fail(f"Unexpected preview request {request.method} {request.url.path}")

    adapter = SDKAdapter(
        Credentials("key", "secret"),
        online=lambda: state.online,
        base_url=SCOPE.service,
        account_id=SCOPE.account_id,
        project_id=SCOPE.project_id,
        transport=httpx.MockTransport(respond),
    )
    downloader = FakeDownloader()
    coordinator = JobCoordinator(adapter, store, result_root=results, result_downloader=downloader)
    state.store, state.coordinator, state.downloader = store, coordinator, downloader
    state.cache, state.results = cache, results
    yield state
    adapter.close()


def ready_job(env, request_id, assets):
    """Persist a READY job whose receipts match private local bytes."""
    store = env.store
    current = store.create(
        JobIntent(request_id, SCOPE, ORIGIN, "model", "model", "a" * 64, "b" * 64, "1.0")
    )
    for state in (JobState.SUBMITTING, JobState.REMOTE, JobState.SUCCEEDED):
        current = store.transition(
            request_id,
            expected_revision=current.revision,
            state=state,
            remote_job_id=f"remote-{request_id}" if state == JobState.REMOTE else None,
        )
    manifest = tuple(
        ResultAsset(asset_id, f"{index:03d}-{asset_id}.bin", media_type, len(data))
        for index, (asset_id, media_type, data) in enumerate(assets)
    )
    current = store.set_results(request_id, manifest, expected_revision=current.revision)
    current = store.transition(
        request_id, expected_revision=current.revision, state=JobState.DOWNLOADING
    )
    directory = env.coordinator._results._directory(current)
    for item, (_, _, data) in zip(manifest, assets, strict=True):
        (directory / item.name).write_bytes(data)
        receipt = DownloadedResult(item.name, len(data), hashlib.sha256(data).hexdigest())
        current = store.record_download(
            request_id, item.asset_id, receipt, expected_revision=current.revision
        )
    return store.transition(request_id, expected_revision=current.revision, state=JobState.READY)


def work(env, request_id, renditions, *, asset_ids=None, **options):
    targets = env.coordinator.result_preview_targets(request_id, asset_ids)
    return [previews.PreviewWork(target, tuple(renditions), **options) for target in targets]


def run(env, items, *, cancel=None):
    return env.coordinator.prepare_result_previews(
        items, root=env.cache, cancel=cancel or threading.Event()
    )


def outcome(batch, index=0, rendition=STILL):
    return dict((item.rendition, item) for item in batch.outcomes[index].renditions)[rendition]


def cache_bytes(root):
    return b"".join(path.read_bytes() for path in Path(root).rglob("*") if path.is_file())


def work_directories(env):
    work = env.cache / "work"
    return sorted(work.iterdir()) if work.exists() else []


def test_preview_kinds_and_default_renditions():
    assert previews.preview_kind("image/png") == "image"
    assert previews.preview_kind("image/x-exr") == "image"
    assert previews.preview_kind("audio/mpeg") == "audio"
    assert previews.preview_kind("video/webm") == "video"
    assert previews.preview_kind("model/gltf-binary") == "3d"
    assert previews.preview_kind("application/x-ply") == "3d"
    for value in ("model/mtl", "text/plain", "image/gif", None):
        assert previews.preview_kind(value) is None
    assert previews.renditions("image") == (STILL,)
    assert previews.renditions("audio") == (STILL, ENVELOPE)
    assert previews.renditions("3d") == (STILL,)
    assert previews.renditions("video", clip=True) == (STILL, CLIP)
    assert previews.renditions(None) == ()
    assert previews.is_local("image", STILL) and previews.is_local("audio", ENVELOPE)
    assert not previews.is_local("video", STILL)


def test_key_binds_scope_request_asset_and_receipt(env):
    record = ready_job(env, "request", [("asset-video", "video/mp4", MP4)])
    item = record.results[0]
    key = previews.PreviewKey.for_result(SCOPE, "request", item)
    assert key == previews.PreviewKey.for_result(SCOPE, "request", item)
    directory = env.coordinator._results._directory(record, create=False)
    assert key.scope == directory.parent.name
    variants = {
        previews.PreviewKey.for_result(replace(SCOPE, project_id="other"), "request", item),
        previews.PreviewKey.for_result(SCOPE, "another", item),
        previews.PreviewKey.for_result(
            SCOPE,
            "request",
            replace(item, receipt=replace(item.receipt, sha256="f" * 64)),
        ),
    }
    assert len({key.name, *(variant.name for variant in variants)}) == 4
    with pytest.raises(ValueError):
        previews.PreviewKey.for_result(SCOPE, "request", replace(item, receipt=None))


def test_server_still_is_verified_cached_and_reused_without_urls(env):
    ready_job(env, "request", [("asset-video", "video/mp4", MP4)])
    still = f"{CDN}/thumb.jpg?Signature=preview-secret"
    env.assets["asset-video"] = asset_record(
        "asset-video", "video/mp4", thumbnail=still, preview=f"{CDN}/clip.mp4?Signature=s"
    )
    env.downloader.files[still] = JPEG
    batch = run(env, work(env, "request", [STILL]))
    result = outcome(batch)
    assert result.state == State.READY and result.preview.media_type == "image/jpeg"
    assert result.preview.path.read_bytes() == JPEG
    assert result.preview.path.is_relative_to(env.cache)
    assert batch.scope == SCOPE
    assert [call[:2] for call in env.calls] == [("GET", "/v1/assets/asset-video")]
    assert len(env.downloader.calls) == 1  # The clip was not requested.
    stored = cache_bytes(env.cache)
    assert b"Signature" not in stored and b"https" not in stored
    assert work_directories(env) == []
    again = run(env, work(env, "request", [STILL]))
    assert outcome(again).state == State.READY and outcome(again).preview == result.preview
    assert len(env.calls) == 1 and len(env.downloader.calls) == 1


def test_bulk_metadata_serves_every_asset_in_one_sdk_request(env):
    ready_job(
        env,
        "request",
        [
            ("asset-model", "model/gltf-binary", GLB),
            ("asset-video", "video/mp4", MP4),
            ("asset-sound", "audio/wav", wav()),
        ],
    )
    for name, kind in (
        ("asset-model", "model/gltf-binary"),
        ("asset-video", "video/mp4"),
        ("asset-sound", "audio/wav"),
    ):
        env.assets[name] = asset_record(
            name, kind, thumbnail=f"{CDN}/{name}.png?Signature=x", preview=f"{CDN}/{name}.mp4"
        )
        env.downloader.files[f"{CDN}/{name}.png?Signature=x"] = png(4, 3)
        env.downloader.files[f"{CDN}/{name}.mp4"] = MP4
    targets = env.coordinator.result_preview_targets("request")
    items = [
        previews.PreviewWork(targets[0], (STILL, CLIP)),
        previews.PreviewWork(targets[1], (STILL,)),
        previews.PreviewWork(targets[2], (STILL,)),
    ]
    batch = run(env, items)
    assert [call[:2] for call in env.calls] == [("POST", "/v1/assets/get-bulk")]
    assert outcome(batch, 0, CLIP).state == State.READY
    assert outcome(batch, 0, CLIP).preview.media_type == "video/mp4"
    assert all(outcome(batch, index).state == State.READY for index in range(3))
    assert len(env.downloader.calls) == 4


def test_late_thumbnail_is_pending_then_missing_until_forced_retry(env):
    ready_job(env, "request", [("asset-model", "model/gltf-binary", GLB)])
    env.assets["asset-model"] = asset_record("asset-model", "model/gltf-binary")
    pending = outcome(run(env, work(env, "request", [STILL])))
    assert pending.state == State.PENDING and "Waiting" in pending.reason
    missing = outcome(run(env, work(env, "request", [STILL], final=True)))
    assert missing.state == State.MISSING
    calls = len(env.calls)
    # The marker survives in the cache: no further metadata polling.
    assert outcome(run(env, work(env, "request", [STILL]))).state == State.MISSING
    assert len(env.calls) == calls
    url = f"{CDN}/late.webp"
    env.assets["asset-model"] = asset_record("asset-model", "model/gltf-binary", thumbnail=url)
    env.downloader.files[url] = b"RIFF\x10\x00\x00\x00WEBPVP8 " + b"\x00" * 32
    retried = outcome(run(env, work(env, "request", [STILL], force=True)))
    assert retried.state == State.READY and retried.preview.media_type == "image/webp"


def test_metadata_failure_is_pending_then_failed_at_window_end(env):
    ready_job(env, "request", [("asset-video", "video/mp4", MP4)])
    first = outcome(run(env, work(env, "request", [STILL])))  # Retrieve returns 404.
    assert first.state == State.PENDING and "metadata" in first.reason
    final = outcome(run(env, work(env, "request", [STILL], final=True)))
    assert final.state == State.FAILED


def test_offline_preview_serves_cache_and_local_work_without_network(env):
    image = png(8, 8)
    ready_job(
        env,
        "request",
        [("asset-image", "image/png", image), ("asset-video", "video/mp4", MP4)],
    )
    env.online = False
    batch = run(env, work(env, "request", [STILL]))
    assert outcome(batch, 0).state == State.DECODE
    assert outcome(batch, 1).state == State.OFFLINE
    assert env.calls == [] and env.downloader.calls == []
    env.coordinator.discard_result_preview(outcome(batch, 0).request, root=env.cache)


def test_image_results_issue_a_private_verified_decode_request(env):
    image = png(640, 320)
    record = ready_job(env, "request", [("asset-image", "image/png", image)])
    batch = run(env, work(env, "request", [STILL]))
    result = outcome(batch)
    assert result.state == State.DECODE and env.calls == [] and env.downloader.calls == []
    request = result.request
    saved = env.coordinator._results._directory(record, create=False)
    assert request.source.read_bytes() == image and request.source.name == "source.png"
    assert not request.source.is_relative_to(saved)
    assert request.directory.is_relative_to(env.cache / "work")
    assert request.max_edge == previews.PREVIEW_EDGE and request.output.parent == request.directory
    if os.name == "posix":
        assert request.directory.stat().st_mode & 0o777 == 0o700
    request.output.write_bytes(png(256, 128))
    cached = env.coordinator.finish_result_preview(
        request, root=env.cache, cancel=threading.Event()
    )
    assert (cached.media_type, cached.width, cached.height) == ("image/png", 256, 128)
    assert not request.directory.exists()
    again = outcome(run(env, work(env, "request", [STILL])))
    assert again.state == State.READY and again.preview.path.read_bytes() == png(256, 128)


@pytest.mark.parametrize(
    "output",
    [png(300, 10), b"not a png", png(1, 1)[:20]],
)
def test_decoded_still_is_bounded_and_always_discarded(env, output):
    ready_job(env, "request", [("asset-image", "image/jpeg", JPEG)])
    request = outcome(run(env, work(env, "request", [STILL]))).request
    request.output.write_bytes(output)
    with pytest.raises(previews.PreviewError):
        env.coordinator.finish_result_preview(request, root=env.cache, cancel=threading.Event())
    assert not request.directory.exists()
    assert outcome(run(env, work(env, "request", [STILL]))).state == State.DECODE


def test_tampered_saved_result_fails_before_any_private_copy_remains(env):
    record = ready_job(env, "request", [("asset-image", "image/png", png(4, 4))])
    directory = env.coordinator._results._directory(record, create=False)
    (directory / record.results[0].asset.name).write_bytes(png(5, 4))
    result = outcome(run(env, work(env, "request", [STILL])))
    assert result.state == State.FAILED and "receipt" in result.reason
    assert work_directories(env) == []


def test_audio_still_and_envelope_use_server_and_local_paths(env):
    ready_job(env, "request", [("asset-sound", "audio/wav", wav())])
    env.assets["asset-sound"] = asset_record("asset-sound", "audio/wav")
    batch = run(env, work(env, "request", [STILL, ENVELOPE]))
    assert outcome(batch, 0, STILL).state == State.PENDING
    request = outcome(batch, 0, ENVELOPE).request
    assert request.source.name == "source.wav" and request.output is None
    with wave.open(str(request.source), "rb") as sound:
        frames = sound.readframes(sound.getnframes())
    builder = EnvelopeBuilder(8000, 1)
    builder.add([value / 32768 for value in struct.unpack(f"<{len(frames) // 2}h", frames)])
    envelope = builder.finish(bins=32)
    with pytest.raises(previews.PreviewError, match="envelope"):
        env.coordinator.finish_result_preview(request, root=env.cache, cancel=threading.Event())
    request = outcome(run(env, work(env, "request", [ENVELOPE])), 0, ENVELOPE).request
    cached = env.coordinator.finish_result_preview(
        request, root=env.cache, cancel=threading.Event(), envelope=envelope
    )
    assert cached.envelope == envelope
    reread = outcome(run(env, work(env, "request", [ENVELOPE])), 0, ENVELOPE)
    assert reread.state == State.READY and reread.preview.envelope == envelope


@pytest.mark.parametrize(
    "thumbnail,data,reason",
    [
        ("https://other.example.invalid/thumb.png", png(2, 2), "download"),
        (f"{CDN}/thumb.gif", GIF, "unsupported"),
        (f"{CDN}/huge.png", b"\x89PNG\r\n\x1a\n" + b"\x00" * previews.STILL_MAX_BYTES, "download"),
    ],
)
def test_untrusted_hosts_formats_and_sizes_fail_without_caching(env, thumbnail, data, reason):
    ready_job(env, "request", [("asset-video", "video/mp4", MP4)])
    env.assets["asset-video"] = asset_record("asset-video", "video/mp4", thumbnail=thumbnail)
    env.downloader.files[thumbnail] = data
    result = outcome(run(env, work(env, "request", [STILL])))
    assert result.state == State.FAILED and reason in result.reason
    assert "https" not in result.reason and "Signature" not in result.reason
    assert list(env.cache.rglob("still.*")) == []
    assert work_directories(env) == []


@pytest.mark.parametrize(
    "change",
    [
        {"mimeType": "video/webm"},
        {"id": "asset-other"},
        {"thumbnail": "https://cdn.cloud.scenario.com/x"},
        {"thumbnail": {"assetId": "bad/id", "url": f"{CDN}/x"}},
    ],
)
def test_changed_or_malformed_metadata_fails(env, change):
    ready_job(env, "request", [("asset-video", "video/mp4", MP4)])
    env.assets["asset-video"] = {**asset_record("asset-video", "video/mp4"), **change}
    result = outcome(run(env, work(env, "request", [STILL])))
    assert result.state == State.FAILED and env.downloader.calls == []


def test_receipt_and_scope_binding_reject_changed_targets(env):
    ready_job(env, "request", [("asset-image", "image/png", png(4, 4))])
    target = env.coordinator.result_preview_targets("request")[0]
    forged = replace(target, receipt=replace(target.receipt, sha256="0" * 64))
    result = outcome(run(env, [previews.PreviewWork(forged, (STILL,))]))
    assert result.state == State.FAILED and "changed" in result.reason
    request = outcome(run(env, work(env, "request", [STILL]))).request
    foreign = replace(request.key, scope="1" * 64)
    with pytest.raises(ResultError, match="connection"):
        env.coordinator.finish_result_preview(
            previews.DecodeRequest(
                foreign, STILL, "image/png", request.source, request.output, request.directory
            ),
            root=env.cache,
            cancel=threading.Event(),
        )
    env.coordinator.discard_result_preview(request, root=env.cache)
    assert work_directories(env) == []


def test_targets_require_saved_receipts_and_known_assets(env):
    ready_job(env, "request", [("asset-video", "video/mp4", MP4)])
    with pytest.raises(ResultError, match="Choose"):
        env.coordinator.result_preview_targets("request", ["asset-other"])
    with pytest.raises(ResultError, match="Choose"):
        env.coordinator.result_preview_targets("request", ["bad/id"])
    with pytest.raises(ResultError, match="Download"):
        env.coordinator.result_preview_targets("unknown")
    target = env.coordinator.result_preview_targets("request", ["asset-video"])[0]
    assert target.kind == "video" and target.receipt.size == len(MP4)
    assert "receipt" not in repr(target)


def test_cancellation_and_retirement_leave_no_private_copies(env):
    ready_job(env, "request", [("asset-image", "image/png", png(4, 4))])
    canceled = threading.Event()
    canceled.set()
    with pytest.raises(previews.PreviewCanceled):
        run(env, work(env, "request", [STILL]), cancel=canceled)
    items = work(env, "request", [STILL])
    env.coordinator.deactivate()
    with pytest.raises(ResultError, match="inactive"):
        run(env, items)
    assert work_directories(env) == []


def test_cache_misses_tampered_symlinked_and_foreign_entries(env):
    ready_job(env, "request", [("asset-video", "video/mp4", MP4)])
    url = f"{CDN}/thumb.jpg"
    env.assets["asset-video"] = asset_record("asset-video", "video/mp4", thumbnail=url)
    env.downloader.files[url] = JPEG
    target = env.coordinator.result_preview_targets("request")[0]
    preview = outcome(run(env, [previews.PreviewWork(target, (STILL,))])).preview
    cache = previews.PreviewCache(env.cache)
    assert cache.read(target.key, STILL) == preview
    assert cache.read(replace(target.key, scope="2" * 64), STILL) is None
    os.chmod(preview.path, 0o600)
    preview.path.write_bytes(JPEG + b"tampered")
    assert cache.read(target.key, STILL) is None
    refreshed = outcome(run(env, [previews.PreviewWork(target, (STILL,))]))
    assert refreshed.state == State.READY and len(env.downloader.calls) == 2
    entry = preview.path.parent
    moved = entry.with_name("moved")
    entry.rename(moved)
    entry.symlink_to(moved, target_is_directory=True)
    assert cache.read(target.key, STILL) is None


def test_eviction_and_sweep_remove_only_owned_stale_entries(env, tmp_path):
    cache = previews.PreviewCache(env.cache)
    work = cache.workspace()
    stale = cache.workspace()
    old = time.time() - previews.WORK_STALE_SECONDS - 10
    os.utime(stale, (old, old))
    foreign = env.cache / "work" / "keep-me"
    foreign.mkdir()
    os.utime(foreign, (old, old))
    cache.sweep()
    assert work.exists() and not stale.exists() and foreign.exists()
    entries = []
    for index in range(3):
        key = previews.PreviewKey("a" * 64, "b" * 64, f"asset-{index}", "video/mp4", "c" * 64, 1)
        staged = cache.workspace() / "file"
        staged.write_bytes(JPEG)
        preview = cache.publish(
            key,
            STILL,
            staged,
            media_type="image/jpeg",
            size=len(JPEG),
            sha256=hashlib.sha256(JPEG).hexdigest(),
        )
        cache.discard(staged.parent)
        stamp = time.time() - 1000 + index
        for path in preview.path.parent.iterdir():
            os.utime(path, (stamp, stamp))
        entries.append((key, preview))
    unrelated = env.cache / "v1" / ("a" * 64) / "not-an-entry"
    unrelated.mkdir()
    cache.evict(max_bytes=len(JPEG) * 2 + 1024)
    assert cache.read(entries[0][0], STILL) is None
    assert all(cache.read(key, STILL) == preview for key, preview in entries[1:])
    assert unrelated.exists()


def test_publish_keeps_an_existing_valid_entry(env):
    cache = previews.PreviewCache(env.cache)
    key = previews.PreviewKey("a" * 64, "b" * 64, "asset", "video/mp4", "c" * 64, 1)
    first = cache.workspace() / "first"
    first.write_bytes(JPEG)
    published = cache.publish(
        key,
        STILL,
        first,
        media_type="image/jpeg",
        size=len(JPEG),
        sha256=hashlib.sha256(JPEG).hexdigest(),
    )
    second = cache.workspace() / "second"
    second.write_bytes(png(2, 2))
    again = cache.publish(
        key,
        STILL,
        second,
        media_type="image/png",
        size=len(png(2, 2)),
        sha256=hashlib.sha256(png(2, 2)).hexdigest(),
    )
    assert again == published and published.path.read_bytes() == JPEG
