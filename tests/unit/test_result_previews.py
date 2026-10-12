# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Receipt-bound result previews through the real SDK adapter, offline and unpaid."""

import hashlib
import io
import json
import os
import shutil
import struct
import threading
import time
import wave
import zlib
from contextlib import contextmanager
from dataclasses import replace
from pathlib import Path, PurePosixPath, PureWindowsPath
from types import SimpleNamespace

import httpx
import pytest

from scenario.core.api.sdk_adapter import Credentials, SDKAdapter
from scenario.core.audio_waveform import EnvelopeBuilder, WaveformCanceled, WaveformError
from scenario.core.jobs import result_previews as previews
from scenario.core.jobs import transfers
from scenario.core.jobs.coordinator import JobCoordinator
from scenario.core.jobs.result_metadata import TEXTURE_ROLES, texture_role
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


def jpeg(width, height):
    """A minimal baseline JPEG: SOI, a JFIF APP0 segment, SOF0 and EOI."""
    app0 = b"\xff\xe0\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00"
    frame = struct.pack(">HH", height, width) + b"\x03\x01\x11\x00\x02\x11\x01\x03\x11\x01"
    return b"\xff\xd8" + app0 + b"\xff\xc0\x00\x11\x08" + frame + b"\xff\xd9"


def webp(width, height, kind=b"VP8 "):
    """A WebP container whose first chunk declares the given canvas."""
    if kind == b"VP8 ":
        payload = b"\x00\x00\x00\x9d\x01\x2a" + struct.pack("<HH", width, height)
    elif kind == b"VP8L":
        payload = b"\x2f" + struct.pack("<I", (width - 1) | (height - 1) << 14)
    else:
        payload = (
            b"\x00" * 4 + (width - 1).to_bytes(3, "little") + (height - 1).to_bytes(3, "little")
        )
    payload += b"\x00" * 10
    chunk = kind + struct.pack("<I", len(payload)) + payload
    return b"RIFF" + struct.pack("<I", 4 + len(chunk)) + b"WEBP" + chunk


JPEG = jpeg(32, 24)
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


@contextmanager
def preview_env(tmp_path):
    """An offline store, coordinator and fake downloader; other test modules reuse it."""
    store = JobStore(tmp_path / "jobs.sqlite3", SCOPE)
    results = tmp_path / "results"
    cache = tmp_path / "previews"
    results.mkdir()
    cache.mkdir()
    state = SimpleNamespace(assets={}, calls=[], online=True, gate=None, status=None)

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
        if state.status is not None:
            return httpx.Response(state.status, json={"error": "fixture"})
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

    with SDKAdapter(
        Credentials("key", "secret"),
        online=lambda: state.online,
        base_url=SCOPE.service,
        account_id=SCOPE.account_id,
        project_id=SCOPE.project_id,
        transport=httpx.MockTransport(respond),
    ) as adapter:
        downloader = FakeDownloader()
        coordinator = JobCoordinator(
            adapter, store, result_root=results, result_downloader=downloader
        )
        state.store, state.coordinator, state.downloader = store, coordinator, downloader
        state.cache, state.results = cache, results
        yield state


@pytest.fixture
def env(tmp_path):
    with preview_env(tmp_path) as state:
        yield state


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
    # A saved ACES-labelled OpenEXR original is not previewed yet, as in image import.
    for value in ("model/mtl", "text/plain", "image/gif", "image/aces", None):
        assert previews.preview_kind(value) is None
    assert previews.renditions("image") == (STILL,)
    assert previews.renditions("audio") == (STILL, ENVELOPE)
    assert previews.renditions("3d") == (STILL,)
    assert previews.renditions("video", clip=True) == (STILL, CLIP)
    assert previews.renditions(None) == ()
    assert previews.is_local("image", STILL) and previews.is_local("audio", ENVELOPE)
    assert not previews.is_local("video", STILL)


def test_every_texture_role_has_a_caption_label():
    # A role without a label would caption its map with the kind's "Image".
    assert set(previews.ROLE_LABEL) == TEXTURE_ROLES
    assert all(isinstance(label, str) and label for label in previews.ROLE_LABEL.values())
    record = {"mimeType": "image/png", "metadata": {"type": "3d-texture-roughness"}}
    assert previews.ROLE_LABEL[texture_role(record)] == "Roughness"


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
    assert (result.preview.width, result.preview.height) == (32, 24)
    assert result.preview.path.is_relative_to(env.cache)
    assert batch.scope == SCOPE
    # One target still uses get_bulk, so absent assets mean the same at any size.
    assert [call[:2] for call in env.calls] == [("POST", "/v1/assets/get-bulk")]
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
    env.downloader.files[url] = webp(16, 9)
    retried = outcome(run(env, work(env, "request", [STILL], force=True)))
    assert retried.state == State.READY and retried.preview.media_type == "image/webp"
    assert (retried.preview.width, retried.preview.height) == (16, 9)


def test_metadata_failure_is_pending_then_failed_at_window_end(env):
    ready_job(env, "request", [("asset-video", "video/mp4", MP4)])
    env.status = 503
    first = outcome(run(env, work(env, "request", [STILL])))
    assert first.state == State.PENDING and "metadata" in first.reason
    final = outcome(run(env, work(env, "request", [STILL], final=True)))
    assert final.state == State.FAILED
    assert previews.PreviewCache(env.cache).read(final_key(env), STILL) is None


def final_key(env, asset_id="asset-video"):
    return env.coordinator.result_preview_targets("request", [asset_id])[0].key


def png_header(width, height):
    """Only a PNG signature, checked IHDR and IEND: the dimensions a file declares."""
    header = struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0)
    ihdr = b"IHDR" + header
    return (
        b"\x89PNG\r\n\x1a\n"
        + struct.pack(">I", len(header))
        + ihdr
        + struct.pack(">I", zlib.crc32(ihdr))
        + b"\x00\x00\x00\x00IEND\xaeB`\x82"
    )


def exr_attribute(name, kind, value):
    return name + b"\x00" + kind + b"\x00" + struct.pack("<i", len(value)) + value


def exr_channels(*names):
    """A ``chlist`` value: half channels, linear flag, reserved bytes, sampling 1."""
    return b"".join(name + b"\x00" + struct.pack("<iB3xii", 1, 0, 1, 1) for name in names) + b"\x00"


def exr(
    width,
    height,
    *,
    display=None,
    window_type=b"box2i",
    end=True,
    version=2,
    channels=(b"R", b"G", b"B", b"A"),
    extra=b"",
):
    """An OpenEXR header declaring channels, a data window and optionally a display window."""
    data = b"\x76\x2f\x31\x01" + struct.pack("<I", version)
    if channels is not None:
        data += exr_attribute(b"channels", b"chlist", exr_channels(*channels))
    data += exr_attribute(b"compression", b"compression", b"\x00")
    data += exr_attribute(
        b"dataWindow", window_type, struct.pack("<iiii", 0, 0, width - 1, height - 1)
    )
    if display is not None:
        data += exr_attribute(
            b"displayWindow", b"box2i", struct.pack("<iiii", 0, 0, display[0] - 1, display[1] - 1)
        )
    return data + extra + (b"\x00" + b"\x00" * 64 if end else b"")


@pytest.mark.parametrize(
    "data,size",
    [
        (exr(4096, 2048), (4096, 2048)),
        (exr(64, 32, display=(128, 16)), (128, 32)),
        (exr(64, 32, version=0x202), (64, 32)),
        (exr(64, 32, window_type=b"box2f"), None),
        (exr(64, 32, end=False), None),
        (png_header(9, 4), (9, 4)),
        (jpeg(640, 480), (640, 480)),
        (b"\x76\x2f\x31\x01", None),
    ],
)
def test_local_image_size_reads_declared_dimensions(data, size):
    assert previews.local_image_size(data) == size


@pytest.mark.parametrize(
    "data",
    [
        # Blender sizes every part by the first one and crashed on a larger later part.
        exr(16, 16, version=0x1002),
        exr(16, 16, version=0x802),
        exr(16, 16, version=0x2002),
        exr(16, 16, version=1),
        # Layered channels load as a multilayer image with no single picture.
        exr(16, 16, channels=(b"diffuse.R", b"diffuse.G", b"diffuse.B")),
        exr(16, 16, channels=None),
        exr(16, 16, channels=()),
        exr(16, 16, extra=exr_attribute(b"channels", b"chlist", exr_channels(b"Y"))),
        exr(16, 16, channels=None, extra=exr_attribute(b"channels", b"chlist", b"R\x00\x01\x00")),
        exr(16, 16, extra=exr_attribute(b"dataWindow", b"box2i", bytes(16))),
        exr(16, 16, extra=exr_attribute(b"type", b"string", b"deepscanline")),
        exr(16, 16, extra=exr_attribute(b"type", b"string", b"multipart")),
    ],
    ids=[
        "multi-part",
        "deep",
        "unknown-flag",
        "version-1",
        "layered",
        "no-channels",
        "empty-channels",
        "duplicate-channels",
        "truncated-channels",
        "duplicate-window",
        "deep-type",
        "unknown-type",
    ],
)
def test_openexr_files_that_are_not_one_single_part_image_read_as_undeclared(data):
    assert previews.local_image_layout(data) is None
    assert previews.local_image_size(data) is None


def test_openexr_channels_bound_the_decoded_samples():
    names = tuple(b"C%d" % index for index in range(64))
    assert previews.local_image_layout(exr(64, 32, channels=(b"Y",))) == (64, 32, 4)
    assert previews.local_image_layout(exr(2048, 2048, channels=names)) == (2048, 2048, 64)
    assert previews.local_image_layout(
        exr(64, 32, extra=exr_attribute(b"type", b"string", b"tiledimage"))
    ) == (64, 32, 4)
    assert previews.bounded_local_image(8192, 4096, 4)
    assert previews.bounded_local_image(2048, 1024, 64)
    assert not previews.bounded_local_image(2048, 2048, 64)
    assert not previews.bounded_local_image(64, 32, "4")


@pytest.mark.parametrize(
    "media_type,data,reason",
    [
        ("image/png", png_header(previews.LOCAL_IMAGE_MAX_EDGE + 1, 1), "too large"),
        ("image/png", png_header(8192, 4097), "too large"),
        ("image/x-exr", exr(9000, 8), "too large"),
        (
            "image/x-exr",
            exr(2048, 2048, channels=tuple(b"C%d" % i for i in range(64))),
            "too large",
        ),
        ("image/x-exr", exr(64, 32, end=False), "readable dimensions"),
        ("image/x-exr", exr(16, 16, version=0x1002), "readable dimensions"),
        ("image/x-exr", exr(16, 16, channels=(b"layer.R",)), "readable dimensions"),
        ("image/jpeg", jpeg(4, 4).replace(b"\xff\xc0", b"\xff\xe1"), "readable dimensions"),
        ("image/webp", webp(4, 4)[:24], "readable dimensions"),
    ],
)
def test_local_image_dimensions_bound_the_main_thread_decode(env, media_type, data, reason):
    ready_job(env, "request", [("asset-image", media_type, data)])
    result = outcome(run(env, work(env, "request", [STILL])))
    assert result.state == State.FAILED and reason in result.reason
    assert result.request is None and work_directories(env) == []


@pytest.mark.parametrize(
    "media_type,data",
    [("image/png", png_header(8192, 4096)), ("image/x-exr", exr(4096, 2048, display=(4096, 2048)))],
)
def test_bounded_local_images_get_a_decode_request(env, media_type, data):
    ready_job(env, "request", [("asset-image", media_type, data)])
    result = outcome(run(env, work(env, "request", [STILL])))
    assert result.state == State.DECODE and result.request.source.read_bytes() == data
    env.coordinator.discard_result_preview(result.request, root=env.cache)
    assert work_directories(env) == []


@pytest.mark.parametrize("count", [1, 2])
def test_absent_asset_is_classified_the_same_for_one_or_several_targets(env, count):
    assets = [("asset-video", "video/mp4", MP4), ("asset-model", "model/gltf-binary", GLB)]
    ready_job(env, "request", assets[:count])
    if count == 2:
        url = f"{CDN}/model.png"
        env.assets["asset-model"] = asset_record("asset-model", "model/gltf-binary", thumbnail=url)
        env.downloader.files[url] = png(4, 4)
    # The server omits the deleted asset-video in both cases.
    pending = outcome(run(env, work(env, "request", [STILL])))
    assert pending.state == State.PENDING and "Waiting" in pending.reason
    final = run(env, work(env, "request", [STILL], final=True))
    assert outcome(final).state == State.MISSING
    assert isinstance(
        previews.PreviewCache(env.cache).read(final_key(env), STILL), previews.MissingPreview
    )
    assert {call[:2] for call in env.calls} == {("POST", "/v1/assets/get-bulk")}
    if count == 2:
        assert outcome(final, 1).state == State.READY


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


@pytest.mark.parametrize("failing", ["fdopen", "fstat"])
def test_open_regular_closes_its_descriptor_when_opening_fails(tmp_path, monkeypatch, failing):
    path = tmp_path / "still.png"
    path.write_bytes(png(1, 1))
    opened, real_open = [], os.open

    def tracking_open(*args, **kwargs):
        opened.append(real_open(*args, **kwargs))
        return opened[-1]

    def failure(*args, **kwargs):
        raise ValueError(f"fixture {failing} failure")

    monkeypatch.setattr(previews.os, "open", tracking_open)
    monkeypatch.setattr(previews.os, failing, failure)
    closed = False
    try:
        with pytest.raises(ValueError, match="fixture") as caught:
            previews._open_regular(path)
        monkeypatch.undo()
        (descriptor,) = opened
        # The kept traceback keeps any file object alive, so garbage collection
        # cannot close the descriptor in place of _open_regular.
        with pytest.raises(OSError):
            os.fstat(descriptor)
        closed = True
        assert caught.traceback
    finally:
        monkeypatch.undo()
        # Only a failed check leaves a descriptor open; close it after the
        # failure is recorded. A closed number may already be reused.
        for leaked in () if closed else opened:
            try:
                os.close(leaked)
            except OSError:
                pass  # Closed by _open_regular after all.


@pytest.mark.skipif(os.name != "posix", reason="Respells POSIX roots to model Windows")
def test_cache_paths_keep_the_canonical_root_spelling(env, monkeypatch):
    """On Windows ``_root`` returns the extended ``\\\\?\\`` spelling of the same root.

    Model that portably: every canonical root becomes ``/../<root>``, the same
    directory spelled differently, and calling ``_root`` again keeps it, as
    with ``\\\\?\\``. Python 3.12+ ``mkdtemp`` would normalize such a spelling.
    """
    plain = transfers._root

    def respelled(root):
        path = Path(os.path.normpath(root))
        plain(path)
        return Path("/..", *path.parts[1:])

    monkeypatch.setattr(transfers, "_root", respelled)
    monkeypatch.setattr(previews, "_root", respelled)
    ready_job(
        env,
        "request",
        [
            ("asset-video", "video/mp4", MP4),
            ("asset-image", "image/png", png(8, 4)),
            ("asset-other", "image/png", png(4, 4)),
        ],
    )
    still = f"{CDN}/thumb.jpg?Signature=preview-secret"
    env.assets["asset-video"] = asset_record("asset-video", "video/mp4", thumbnail=still)
    env.downloader.files[still] = JPEG
    root = previews.PreviewCache(env.cache).root
    assert root.parts[1] == ".." and root.resolve() == env.cache.resolve()
    batch = run(env, work(env, "request", [STILL]))
    cached = outcome(batch, 0).preview
    assert cached.path.read_bytes() == JPEG
    # The Windows CI expectation: relative to the canonical root, not the raw one.
    assert cached.path.is_relative_to(root) and not cached.path.is_relative_to(env.cache)
    image, other = outcome(batch, 1).request, outcome(batch, 2).request
    for request in (image, other):
        assert request.directory.parent == root / "work"
        assert request.source.parent == request.output.parent == request.directory
    assert len(work_directories(env)) == 2  # The still's staging directory is gone.
    image.output.write_bytes(png(4, 2))
    published = env.coordinator.finish_result_preview(
        image, root=env.cache, cancel=threading.Event()
    )
    assert published.path.is_relative_to(root) and (published.width, published.height) == (4, 2)
    env.coordinator.discard_result_preview(other, root=env.cache)
    assert work_directories(env) == []


@pytest.mark.parametrize(
    "path, root, inside",
    [
        # Windows: the cache's extended spelling below the configured root.
        (r"\\?\D:\cache\result-previews\v1\s\k\still.png", r"D:\cache\result-previews", True),
        (r"\\?\d:\Cache\Result-Previews\v1\still.png", r"D:\cache\result-previews", True),
        (r"\\?\D:\cache\result-previews\v1\still.png", r"\\?\D:\cache\result-previews", True),
        (r"D:\cache\result-previews\v1\still.png", r"D:\cache\result-previews", True),
        (r"\\?\UNC\host\share\previews\v1\still.png", r"\\host\share\previews", True),
        (r"\\?\D:\cache\other\still.png", r"D:\cache\result-previews", False),
        (r"\\?\D:\cache\result-previews-x\still.png", r"D:\cache\result-previews", False),
        (r"\\?\E:\cache\result-previews\still.png", r"D:\cache\result-previews", False),
        (r"\\?\UNC\host\other\previews\still.png", r"\\host\share\previews", False),
        (r"\\.\D:\cache\result-previews\still.png", r"D:\cache\result-previews", False),
    ],
)
def test_windows_cache_paths_are_in_the_configured_root(path, root, inside):
    """Adapted from a Windows CI failure: no icon was ever built from a ready still.

    The cache returns ``\\\\?\\D:\\...`` paths while the scheduler holds ``D:\\...``,
    which pathlib's ``is_relative_to`` never relates.
    """
    path, root = PureWindowsPath(path), PureWindowsPath(root)
    assert previews.in_cache(path, root) is inside
    if inside and str(path).startswith("\\\\?\\") and not str(root).startswith("\\\\?\\"):
        assert not path.is_relative_to(root)  # The check the icon step used before.


@pytest.mark.parametrize(
    "path, inside",
    [
        ("/cache/result-previews/v1/s/k/still.png", True),
        ("/cache/result-previews", True),
        ("/cache/result-previews-x/still.png", False),
        ("/cache/other/still.png", False),
    ],
)
def test_posix_cache_paths_compare_unchanged(path, inside):
    root = PurePosixPath("/cache/result-previews")
    assert previews.in_cache(PurePosixPath(path), root) is inside


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
        (f"{CDN}/thumb.gif", GIF, "unsupported"),
        (f"{CDN}/wide.png", png(previews.STILL_MAX_EDGE + 1, 1), "larger"),
        (f"{CDN}/tall.jpg", jpeg(16, previews.STILL_MAX_EDGE + 1), "larger"),
        (f"{CDN}/lossy.webp", webp(previews.STILL_MAX_EDGE + 1, 8), "larger"),
        (f"{CDN}/lossless.webp", webp(8, previews.STILL_MAX_EDGE + 1, b"VP8L"), "larger"),
        (f"{CDN}/canvas.webp", webp(20000, 20000, b"VP8X"), "larger"),
        (f"{CDN}/frameless.jpg", jpeg(4, 4).replace(b"\xff\xc0", b"\xff\xe1"), "dimensions"),
        (f"{CDN}/empty.jpg", jpeg(0, 4), "dimensions"),
    ],
)
def test_unsupported_formats_and_pixel_sizes_fail_without_caching(env, thumbnail, data, reason):
    ready_job(env, "request", [("asset-video", "video/mp4", MP4)])
    env.assets["asset-video"] = asset_record("asset-video", "video/mp4", thumbnail=thumbnail)
    env.downloader.files[thumbnail] = data
    result = outcome(run(env, work(env, "request", [STILL])))
    assert result.state == State.FAILED and reason in result.reason
    assert "https" not in result.reason and "Signature" not in result.reason
    assert list(env.cache.rglob("still.*")) == []
    assert work_directories(env) == []


@pytest.mark.parametrize(
    "thumbnail,data",
    [
        ("https://other.example.invalid/thumb.png?Signature=s", png(2, 2)),
        (f"{CDN}/huge.png?Signature=s", b"\x89PNG\r\n\x1a\n" + b"\x00" * previews.STILL_MAX_BYTES),
        (f"{CDN}/redirected.png?Signature=s", None),
    ],
    ids=["untrusted-host", "oversized", "cross-host-redirect"],
)
def test_incomplete_transfers_stay_pending_until_the_window_ends(env, monkeypatch, thumbnail, data):
    ready_job(env, "request", [("asset-video", "video/mp4", MP4)])
    env.assets["asset-video"] = asset_record("asset-video", "video/mp4", thumbnail=thumbnail)
    if data is None:

        def download(url, **kwargs):
            # The real downloader's answer to a redirect to another host.
            raise TransferError("Storage redirect destination rejected")

        monkeypatch.setattr(env.downloader, "download", download)
    else:
        env.downloader.files[thumbnail] = data
    first = outcome(run(env, work(env, "request", [STILL])))
    assert first.state == State.PENDING and "retrying" in first.reason
    final = outcome(run(env, work(env, "request", [STILL], final=True)))
    assert final.state == State.FAILED and "Retry" in final.reason
    for result in (first, final):
        assert "https" not in result.reason and "Signature" not in result.reason
    assert previews.PreviewCache(env.cache).read(final_key(env), STILL) is None
    assert list(env.cache.rglob("still.*")) == [] and work_directories(env) == []


def test_preview_bytes_that_fail_their_receipt_fail_at_once(env, monkeypatch):
    ready_job(env, "request", [("asset-video", "video/mp4", MP4)])
    url = f"{CDN}/thumb.jpg"
    env.assets["asset-video"] = asset_record("asset-video", "video/mp4", thumbnail=url)
    env.downloader.files[url] = JPEG

    def verify(root, receipt):
        raise TransferError("Result does not match its receipt")

    monkeypatch.setattr(env.downloader, "verify", verify)
    result = outcome(run(env, work(env, "request", [STILL])))
    assert result.state == State.FAILED and "receipt" in result.reason
    assert list(env.cache.rglob("still.*")) == [] and work_directories(env) == []


def test_transfer_stopped_by_revoked_online_access_reports_offline(env, monkeypatch):
    ready_job(env, "request", [("asset-video", "video/mp4", MP4)])
    url = f"{CDN}/thumb.jpg"
    env.assets["asset-video"] = asset_record("asset-video", "video/mp4", thumbnail=url)

    def download(url, **kwargs):
        env.online = False
        raise TransferError("Storage transfer interrupted")

    monkeypatch.setattr(env.downloader, "download", download)
    result = outcome(run(env, work(env, "request", [STILL], final=True)))
    assert result.state == State.OFFLINE and work_directories(env) == []


@pytest.mark.parametrize(
    "change,first",
    [
        ({"mimeType": "video/webm"}, State.FAILED),
        # The adapter rejects an unrequested bulk row as an unreadable response.
        ({"id": "asset-other"}, State.PENDING),
        ({"thumbnail": "https://cdn.cloud.scenario.com/x"}, State.FAILED),
        ({"thumbnail": {"assetId": "bad/id", "url": f"{CDN}/x"}}, State.FAILED),
    ],
)
def test_changed_or_malformed_metadata_fails(env, change, first):
    ready_job(env, "request", [("asset-video", "video/mp4", MP4)])
    env.assets["asset-video"] = {**asset_record("asset-video", "video/mp4"), **change}
    assert outcome(run(env, work(env, "request", [STILL]))).state == first
    final = outcome(run(env, work(env, "request", [STILL], final=True)))
    assert final.state == State.FAILED and env.downloader.calls == []


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
    with pytest.raises(previews.PreviewCanceled):
        env.coordinator.maintain_result_previews(root=env.cache, cancel=canceled)
    items = work(env, "request", [STILL])
    env.coordinator.deactivate()
    with pytest.raises(ResultError, match="inactive"):
        run(env, items)
    with pytest.raises(ResultError, match="inactive"):
        env.coordinator.maintain_result_previews(root=env.cache, cancel=threading.Event())
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
            width=32,
            height=24,
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


@pytest.mark.parametrize("failure", ["whole", "partial"])
def test_eviction_counts_only_freed_bytes_when_an_entry_cannot_be_removed(
    env, monkeypatch, failure
):
    cache = previews.PreviewCache(env.cache)
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
            width=32,
            height=24,
        )
        cache.discard(staged.parent)
        stamp = time.time() - 1000 + index
        for path in preview.path.parent.iterdir():
            os.utime(path, (stamp, stamp))
        entries.append((key, preview))
    locked = entries[0][1].path.parent
    remove = shutil.rmtree

    def rmtree(path, ignore_errors=False):
        # Windows can refuse to delete a file another process keeps open.
        if Path(path) != locked:
            return remove(path, ignore_errors=ignore_errors)
        if failure == "partial":
            for item in Path(path).iterdir():
                if item != entries[0][1].path:
                    item.unlink()
        return None

    monkeypatch.setattr(previews.shutil, "rmtree", rmtree)
    cache.evict(max_bytes=len(JPEG) * 2 + 1024)
    # The locked entry still uses its bytes, so the next oldest one goes instead.
    assert entries[0][1].path.exists()
    assert cache.read(entries[1][0], STILL) is None
    assert cache.read(entries[2][0], STILL) == entries[2][1]


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
        width=32,
        height=24,
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
        width=2,
        height=2,
    )
    assert again == published and published.path.read_bytes() == JPEG


@pytest.mark.parametrize(
    "rendition,details",
    [
        (STILL, {}),
        (STILL, {"width": previews.STILL_MAX_EDGE + 1, "height": 1}),
        (STILL, {"width": 2.0, "height": 2}),
        (CLIP, {"width": 2, "height": 2}),
    ],
)
def test_publish_requires_bounded_still_dimensions(env, rendition, details):
    cache = previews.PreviewCache(env.cache)
    key = previews.PreviewKey("a" * 64, "b" * 64, "asset", "video/mp4", "c" * 64, 1)
    staged = cache.workspace() / "staged"
    data = JPEG if rendition == STILL else MP4
    staged.write_bytes(data)
    with pytest.raises(previews.PreviewError, match="dimensions"):
        cache.publish(
            key,
            rendition,
            staged,
            media_type="image/jpeg" if rendition == STILL else "video/mp4",
            size=len(data),
            sha256=hashlib.sha256(data).hexdigest(),
            **details,
        )
    assert not (env.cache / "v1").exists()


def test_cached_still_without_bounded_dimensions_is_a_miss(env):
    ready_job(env, "request", [("asset-video", "video/mp4", MP4)])
    url = f"{CDN}/thumb.jpg"
    env.assets["asset-video"] = asset_record("asset-video", "video/mp4", thumbnail=url)
    env.downloader.files[url] = JPEG
    target = env.coordinator.result_preview_targets("request")[0]
    preview = outcome(run(env, [previews.PreviewWork(target, (STILL,))])).preview
    sidecar = preview.path.parent / "still.json"
    value = json.loads(sidecar.read_text())
    value["width"] = previews.STILL_MAX_EDGE + 1
    sidecar.write_text(json.dumps(value))
    assert previews.PreviewCache(env.cache).read(target.key, STILL) is None


@pytest.mark.parametrize(
    "data,size",
    [
        (png(7, 5), (7, 5)),
        (jpeg(640, 480), (640, 480)),
        (b"\xff\xd8\xff\xff\xe0\x00\x04\x00\x00\xff\xd0" + jpeg(9, 3)[2:], (9, 3)),
        (webp(31, 17), (31, 17)),
        (webp(31, 17, b"VP8L"), (31, 17)),
        (webp(4096, 2048, b"VP8X"), (4096, 2048)),
        (png(7, 5)[:30], None),
        (b"\xff\xd8\xff\xda\x00\x08" + b"\x00" * 16, None),
        (b"\xff\xd8\xff\xc0\x00\x01" + b"\x00" * 16, None),
        (webp(4, 4)[:24], None),
        (GIF, None),
    ],
)
def test_still_size_reads_declared_header_dimensions(data, size):
    assert previews.still_size(data) == size


def test_deleted_cache_root_is_recreated_between_batches(env):
    ready_job(env, "request", [("asset-video", "video/mp4", MP4)])
    url = f"{CDN}/thumb.jpg"
    env.assets["asset-video"] = asset_record("asset-video", "video/mp4", thumbnail=url)
    env.downloader.files[url] = JPEG
    assert outcome(run(env, work(env, "request", [STILL]))).state == State.READY
    shutil.rmtree(env.cache)
    again = outcome(run(env, work(env, "request", [STILL])))
    assert again.state == State.READY and again.preview.path.read_bytes() == JPEG
    assert len(env.downloader.calls) == 2
    if os.name == "posix":
        assert env.cache.stat().st_mode & 0o777 == 0o700
    # Only the root itself is recreated; its parent must still exist.
    with pytest.raises(previews.PreviewError, match="unavailable"):
        previews.PreviewCache(env.cache.parent / "absent" / "previews")
    assert not (env.cache.parent / "absent").exists()


def test_canceled_preview_transfer_stops_without_caching(env, monkeypatch):
    ready_job(env, "request", [("asset-video", "video/mp4", MP4)])
    url = f"{CDN}/clip.mp4"
    env.assets["asset-video"] = asset_record("asset-video", "video/mp4", preview=url)
    cancel, seen = threading.Event(), []

    def download(url, *, root, name, max_bytes=None, cancel=None):
        # Retirement sets the lane's event; the real downloader stops at its next check.
        seen.append(cancel)
        cancel.set()
        raise TransferError("Storage transfer interrupted")

    monkeypatch.setattr(env.downloader, "download", download)
    with pytest.raises(previews.PreviewCanceled):
        run(env, work(env, "request", [CLIP]), cancel=cancel)
    assert seen == [cancel]
    assert work_directories(env) == [] and list(env.cache.rglob("clip.*")) == []


class FakeDecode:
    """Stands in for the offline Blender decoder; records what the lane passed."""

    def __init__(self, monkeypatch, *, error=None):
        self.calls, self.error = [], error
        monkeypatch.setattr(previews.audio_decode, "decode", self)

    def __call__(self, source, directory, spec, *, cancel, max_seconds, bins):
        self.calls.append((source, directory, spec, max_seconds, bins, source.read_bytes()))
        if self.error is not None:
            raise self.error
        builder = EnvelopeBuilder(8000, 1, max_seconds=max_seconds)
        builder.add([0.5, -0.25] * 400)
        return builder.finish(bins)


def envelope_request(env):
    ready_job(env, "request", [("asset-sound", "audio/mpeg", b"ID3" + b"\x00" * 64)])
    return outcome(run(env, work(env, "request", [ENVELOPE])), 0, ENVELOPE).request


def test_offline_decode_caches_the_envelope_by_receipt_and_removes_the_copy(env, monkeypatch):
    decoder = FakeDecode(monkeypatch)
    request = envelope_request(env)
    spec = object()
    cached = env.coordinator.decode_result_preview(
        request, root=env.cache, waveform=spec, cancel=threading.Event()
    )
    ((source, directory, passed, seconds, bins, data),) = decoder.calls
    assert source == request.source and source.name == "source.mp3"
    assert directory == request.directory and passed is spec
    assert (seconds, bins) == (request.max_seconds, request.bins)
    assert data == b"ID3" + b"\x00" * 64
    assert cached.rendition == ENVELOPE and cached.envelope.overall_peak == 0.5
    assert work_directories(env) == []
    reread = outcome(run(env, work(env, "request", [ENVELOPE])), 0, ENVELOPE)
    assert reread.state == State.READY and reread.preview.envelope == cached.envelope
    assert len(decoder.calls) == 1


@pytest.mark.parametrize(
    "error,expected,reason",
    [
        (WaveformError("Blender could not decode this audio"), previews.PreviewError, "decode"),
        (WaveformCanceled("Waveform preview canceled"), previews.PreviewCanceled, "canceled"),
    ],
)
def test_offline_decode_failures_cache_nothing(env, monkeypatch, error, expected, reason):
    FakeDecode(monkeypatch, error=error)
    request = envelope_request(env)
    with pytest.raises(expected, match=reason):
        env.coordinator.decode_result_preview(
            request, root=env.cache, waveform=object(), cancel=threading.Event()
        )
    assert work_directories(env) == []
    retry = outcome(run(env, work(env, "request", [ENVELOPE])), 0, ENVELOPE)
    assert retry.state == State.DECODE
    env.coordinator.discard_result_preview(retry.request, root=env.cache)


def test_offline_decode_rejects_canceled_and_foreign_requests(env, monkeypatch):
    decoder = FakeDecode(monkeypatch)
    request = envelope_request(env)
    cancel = threading.Event()
    cancel.set()
    with pytest.raises(previews.PreviewCanceled):
        env.coordinator.decode_result_preview(
            request, root=env.cache, waveform=object(), cancel=cancel
        )
    assert work_directories(env) == []
    ready_job(env, "image", [("asset-image", "image/png", png(4, 4))])
    still = outcome(run(env, work(env, "image", [STILL])), 0, STILL).request
    with pytest.raises(previews.PreviewError, match="audio decode request"):
        env.coordinator.decode_result_preview(
            still, root=env.cache, waveform=object(), cancel=threading.Event()
        )
    foreign = replace(still, key=replace(still.key, scope="0" * 64))
    with pytest.raises(ResultError, match="connection"):
        env.coordinator.decode_result_preview(
            foreign, root=env.cache, waveform=object(), cancel=threading.Event()
        )
    assert decoder.calls == []
