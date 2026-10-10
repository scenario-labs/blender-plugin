# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Review asset stills of waiting workflow steps on the shared preview lane, offline."""

import os
import threading
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace

import pytest

from scenario.core.jobs import result_previews as previews
from scenario.core.jobs import workflow_nodes
from scenario.core.jobs.preview_scheduler import ResultPreviewScheduler
from scenario.core.jobs.results import ResultError
from scenario.core.jobs.store import JobIntent, JobState
from scenario.core.jobs.transfers import TransferError
from scenario.core.jobs.workers import JobWorkers
from tests.unit.test_preview_scheduler import Clock, drive
from tests.unit.test_result_previews import (
    CDN,
    GIF,
    JPEG,
    MP4,
    ORIGIN,
    SCOPE,
    asset_record,
    cache_bytes,
    env,  # noqa: F401 - shared fixture
    png,
    ready_job,
    webp,
    work_directories,
)

STILL = previews.STILL
State = previews.PreviewState


def waiting_job(service, request_id="request", remote="remote-workflow"):
    """Persist a `remote` workflow job, as a job paused at a waiting step is saved."""
    store = service.store
    current = store.create(
        JobIntent(request_id, SCOPE, ORIGIN, "workflow", "workflow", "a" * 64, "b" * 64, "1.0")
    )
    current = store.transition(
        request_id, expected_revision=current.revision, state=JobState.SUBMITTING
    )
    return store.transition(
        request_id, expected_revision=current.revision, state=JobState.REMOTE, remote_job_id=remote
    )


def image(asset_id, *, media_type="image/png", **properties):
    record = asset_record(asset_id, media_type)
    if properties:
        record["properties"] = properties
    return record


def review_work(service, request_id, asset_ids, **options):
    targets = service.coordinator.review_preview_targets(request_id, asset_ids)
    return [previews.PreviewWork(target, (STILL,), **options) for target in targets]


def run(service, items):
    return service.coordinator.prepare_result_previews(
        items, root=service.cache, cancel=threading.Event()
    )


def still(batch, index=0):
    return batch.outcomes[index].renditions[0]


def own_url(asset_id):
    return f"{CDN}/{asset_id}?Signature=result-secret"


# Projection and sources.


def test_preview_assets_are_an_approvals_results_or_an_asset_selections_candidates():
    flow = {
        "jobId": "job",
        "jobType": "workflow",
        "metadata": {
            "flow": [
                {
                    "id": "render",
                    "type": "model",
                    "status": "success",
                    "assets": [{"assetId": "asset-render", "url": "https://x/y?Signature=s"}],
                },
                {
                    "id": "check",
                    "type": "user-approval",
                    "status": "processing",
                    "dependsOn": ["render"],
                },
                {
                    "id": "pick",
                    "type": "user-selection",
                    "status": "processing",
                    "items": ["asset-a", "asset-b"],
                    "inputs": [{"name": "c", "type": "file_array", "min": 1, "max": 1}],
                },
                {
                    "id": "words",
                    "type": "user-selection",
                    "status": "processing",
                    "items": ["one", "two"],
                    "inputs": [{"name": "t", "type": "string_array", "min": 1, "max": 1}],
                },
            ]
        },
    }
    steps = workflow_nodes.pending_steps(flow, remote_job_id="job", workflow_id="workflow")
    assert [workflow_nodes.preview_assets(step) for step in steps] == [
        ("asset-render",),
        ("asset-a", "asset-b"),
        (),
    ]


def test_review_sources_prefer_the_bounded_image_then_the_server_thumbnail():
    target = previews.PreviewTarget.for_review(SCOPE, "request", "remote", "asset-a")
    record = image("asset-a", size=1024, width=640, height=480)
    assert previews.review_sources(record, target) == {STILL: ("asset-a", own_url("asset-a"))}
    # Undeclared properties do not block the bounded transfer.
    assert previews.review_sources(image("asset-a"), target) == {
        STILL: ("asset-a", own_url("asset-a"))
    }
    thumbnail = f"{CDN}/thumb.webp?Signature=thumb-secret"
    for large in (
        {"size": previews.STILL_MAX_BYTES + 1},
        {"width": previews.STILL_MAX_EDGE + 1, "height": 10},
    ):
        record = image("asset-a", **large)
        with pytest.raises(previews.PreviewError, match="open it in Scenario"):
            previews.review_sources(record, target)
        record["thumbnail"] = {"assetId": "asset-thumb", "url": thumbnail}
        assert previews.review_sources(record, target) == {STILL: ("asset-thumb", thumbnail)}
    # Other kinds use the server thumbnail, and wait for one that is not there yet.
    video = asset_record("asset-a", "video/mp4")
    assert previews.review_sources(video, target) == {}
    video["thumbnail"] = {"assetId": "asset-thumb", "url": thumbnail}
    assert previews.review_sources(video, target) == {STILL: ("asset-thumb", thumbnail)}
    for bad in (
        asset_record("asset-other", "image/png"),
        {**asset_record("asset-a", "video/mp4"), "thumbnail": "not-an-object"},
        {**asset_record("asset-a", "video/mp4"), "thumbnail": {"assetId": "x/y", "url": "u"}},
        "not-a-record",
    ):
        with pytest.raises(previews.PreviewError):
            previews.review_sources(bad, target)


def test_review_keys_bind_scope_request_remote_job_and_asset():
    key = previews.ReviewKey.for_step(SCOPE, "request", "remote", "asset-a")
    variants = {
        previews.ReviewKey.for_step(
            replace(SCOPE, project_id="other"), "request", "remote", "asset-a"
        ),
        previews.ReviewKey.for_step(SCOPE, "another", "remote", "asset-a"),
        previews.ReviewKey.for_step(SCOPE, "request", "remote-2", "asset-a"),
        previews.ReviewKey.for_step(SCOPE, "request", "remote", "asset-b"),
    }
    assert len({key.name, *(variant.name for variant in variants)}) == 5
    assert key.scope == previews.scope_digest(SCOPE)
    for bad in (("x", "y" * 64, "z" * 64, "asset"), (key.scope, key.request, key.job, "a/b")):
        with pytest.raises(ValueError):
            previews.ReviewKey(*bad)


def test_review_targets_need_a_remote_workflow_job_and_bounded_distinct_assets(env):  # noqa: F811 - pytest injects the shared fixture
    waiting_job(env)
    targets = env.coordinator.review_preview_targets("request", ["asset-a", "asset-b"])
    assert [(t.asset_id, t.kind, t.media_type, t.receipt) for t in targets] == [
        ("asset-a", previews.REVIEW, "", None),
        ("asset-b", previews.REVIEW, "", None),
    ]
    assert targets[0].key == previews.ReviewKey.for_step(
        SCOPE, "request", "remote-workflow", "asset-a"
    )
    too_many = [f"asset-{index}" for index in range(previews.REVIEW_ASSET_LIMIT + 1)]
    for assets in ([], ["asset-a", "asset-a"], ["bad/asset"], too_many, None):
        with pytest.raises(ResultError):
            env.coordinator.review_preview_targets("request", assets)
    ready_job(env, "model-job", [("asset-m", "image/png", png(2, 2))])
    for request_id in ("model-job", "missing"):
        with pytest.raises(ResultError, match="waits for a decision"):
            env.coordinator.review_preview_targets(request_id, ["asset-a"])
    assert env.calls == []


# The lane.


def test_review_image_is_fetched_once_verified_cached_and_reused_without_urls(env):  # noqa: F811 - pytest injects the shared fixture
    waiting_job(env)
    env.assets["asset-a"] = image("asset-a", size=100)
    env.assets["asset-b"] = image("asset-b", media_type="image/webp")
    env.downloader.files[own_url("asset-a")] = JPEG
    env.downloader.files[own_url("asset-b")] = webp(20, 10)
    batch = run(env, review_work(env, "request", ["asset-a", "asset-b"]))
    first, second = still(batch), still(batch, 1)
    assert first.state == second.state == State.READY
    assert first.preview.media_type == "image/jpeg" and first.preview.path.read_bytes() == JPEG
    assert (first.preview.width, first.preview.height) == (32, 24)
    assert (second.preview.width, second.preview.height) == (20, 10)
    assert first.preview.path.is_relative_to(env.cache)
    # One bulk metadata read for both assets on the lane, one transfer each.
    assert [call[:2] for call in env.calls] == [("POST", "/v1/assets/get-bulk")]
    assert [url for url, _ in env.downloader.calls] == [own_url("asset-a"), own_url("asset-b")]
    stored = cache_bytes(env.cache)
    assert b"Signature" not in stored and b"https" not in stored
    assert work_directories(env) == []
    again = run(env, review_work(env, "request", ["asset-a"]))
    assert still(again).preview == first.preview
    assert len(env.calls) == 1 and len(env.downloader.calls) == 2


def test_review_previews_refuse_unsafe_hosts_formats_sizes_and_changed_jobs(env):  # noqa: F811 - pytest injects the shared fixture
    waiting_job(env)
    env.assets["asset-host"] = {**image("asset-host"), "url": "https://evil.example.invalid/a.png"}
    env.assets["asset-gif"] = image("asset-gif")
    env.downloader.files[own_url("asset-gif")] = GIF
    env.assets["asset-big"] = image("asset-big", size=previews.STILL_MAX_BYTES + 1)
    env.assets["asset-huge"] = image("asset-huge")
    env.downloader.files[own_url("asset-huge")] = png(previews.STILL_MAX_EDGE + 1, 1)
    names = ["asset-host", "asset-gif", "asset-big", "asset-huge"]
    batch = run(env, review_work(env, "request", names))
    states = {name: still(batch, index) for index, name in enumerate(names)}
    # A rejected host is a transfer that did not complete: polled again, then failed.
    assert states["asset-host"].state == State.PENDING
    assert states["asset-gif"].state == State.FAILED
    assert "unsupported format" in states["asset-gif"].reason
    assert states["asset-big"].state == State.FAILED
    assert "open it in Scenario" in states["asset-big"].reason
    assert states["asset-huge"].state == State.FAILED
    assert [url for url, _ in env.downloader.calls] == [own_url("asset-gif"), own_url("asset-huge")]
    final = run(env, review_work(env, "request", ["asset-host"], final=True))
    assert still(final).state == State.FAILED
    for value in (*states.values(), still(final)):
        assert "Signature" not in (value.reason or "") and "https" not in (value.reason or "")
    assert work_directories(env) == []
    # The job left `remote`: nothing is fetched for a step that no longer waits.
    record = env.store.get("request")
    env.store.transition("request", expected_revision=record.revision, state=JobState.CANCELED)
    stale = previews.PreviewTarget.for_review(SCOPE, "request", "remote-workflow", "asset-gif")
    before = (len(env.calls), len(env.downloader.calls))
    gone = run(env, [previews.PreviewWork(stale, (STILL,))])
    assert still(gone).state == State.FAILED and "no longer waiting" in still(gone).reason
    assert (len(env.calls), len(env.downloader.calls)) == before


def test_review_previews_wait_offline_without_any_request(env):  # noqa: F811 - pytest injects the shared fixture
    waiting_job(env)
    env.assets["asset-a"] = image("asset-a")
    env.online = False
    batch = run(env, review_work(env, "request", ["asset-a"]))
    assert still(batch).state == State.OFFLINE
    assert env.calls == [] and env.downloader.calls == []


def test_cached_still_is_checked_again_before_decoding(env):  # noqa: F811 - pytest injects the shared fixture
    waiting_job(env)
    env.assets["asset-a"] = image("asset-a")
    env.downloader.files[own_url("asset-a")] = png(4, 3)
    preview = still(run(env, review_work(env, "request", ["asset-a"]))).preview
    assert previews.check_still(preview) == preview.path
    os.chmod(preview.path, 0o600)
    data = preview.path.read_bytes()
    preview.path.write_bytes(data[:-1] + bytes([data[-1] ^ 1]))
    with pytest.raises(previews.PreviewError, match="changed"):
        previews.check_still(preview)
    preview.path.unlink()
    preview.path.symlink_to(Path(env.cache) / "elsewhere.png")
    with pytest.raises(previews.PreviewError):
        previews.check_still(preview)
    for bad in (None, replace(preview, rendition=previews.CLIP), replace(preview, path=None)):
        with pytest.raises(previews.PreviewError):
            previews.check_still(bad)


# The scheduler.


@pytest.fixture
def lane(env):  # noqa: F811 - pytest injects the shared fixture
    clock = Clock()
    workers = JobWorkers(env.coordinator, workers=1)
    scheduler = ResultPreviewScheduler(workers, env.coordinator, env.cache, clock=clock)
    yield SimpleNamespace(env=env, clock=clock, scheduler=scheduler)
    workers.deactivate()
    workers.shutdown()


def review_state(lane, asset_id):
    return lane.scheduler.status("request", asset_id, review=True).get(STILL)


def test_transient_review_transfer_failures_are_retried_within_the_window(lane):
    service, clock, scheduler = lane.env, lane.clock, lane.scheduler
    waiting_job(service)
    service.assets["asset-a"] = image("asset-a")
    failures = [2]
    download = service.downloader.download

    def flaky(url, **options):
        if failures[0]:
            failures[0] -= 1
            service.downloader.calls.append((url, threading.current_thread()))
            raise TransferError("Storage request did not return a complete result")
        return download(url, **options)

    service.downloader.download = flaky
    service.downloader.files[own_url("asset-a")] = JPEG
    (status,) = scheduler.request_review("request", ["asset-a"])
    assert status.kind == previews.REVIEW and status.get(STILL).state == State.QUEUED
    for _ in range(40):
        drive(scheduler)
        if review_state(lane, "asset-a").state == State.READY:
            break
        clock.now += 1
    ready = review_state(lane, "asset-a")
    assert ready.state == State.READY and ready.preview.path.read_bytes() == JPEG
    assert len(service.downloader.calls) == 3
    assert {thread.name for _, thread in service.downloader.calls} == {"ScenarioPreview"}
    assert {thread.name for *_, thread in service.calls} == {"ScenarioPreview"}


def test_missing_thumbnail_is_polled_then_missing_until_an_explicit_retry(lane):
    service, clock, scheduler = lane.env, lane.clock, lane.scheduler
    waiting_job(service)
    service.assets["asset-v"] = asset_record("asset-v", "video/mp4")
    scheduler.request_review("request", ["asset-v"])
    for _ in range(320):
        drive(scheduler)
        clock.now += 1
    assert review_state(lane, "asset-v").state == State.MISSING
    polls = len(service.calls)
    drive(scheduler)
    assert len(service.calls) == polls
    url = f"{CDN}/video-still.png"
    service.assets["asset-v"]["thumbnail"] = {"assetId": "asset-v-thumb", "url": url}
    service.downloader.files[url] = png(4, 2)
    with pytest.raises(previews.PreviewError):
        scheduler.retry("request", "asset-v")  # A saved result's entry, not this one.
    assert scheduler.retry("request", "asset-v", review=True).get(STILL).state == State.QUEUED
    drive(scheduler)
    assert review_state(lane, "asset-v").state == State.READY


def test_a_review_retry_fetches_a_ready_still_again_only_when_its_cached_file_is_lost(lane):
    # The Blender owner relies on this when the pump finds a ready still's
    # cached file gone or changed before decoding, or Blender cannot decode it.
    service, scheduler = lane.env, lane.scheduler
    waiting_job(service)
    service.assets["asset-a"] = image("asset-a")
    service.downloader.files[own_url("asset-a")] = JPEG
    scheduler.request_review("request", ["asset-a"])
    drive(scheduler)
    ready = review_state(lane, "asset-a")
    assert ready.state == State.READY
    # A retry of an intact entry verifies it again on the lane and reuses it.
    calls = (len(service.calls), len(service.downloader.calls))
    assert scheduler.retry("request", "asset-a", review=True).get(STILL).state == State.QUEUED
    drive(scheduler)
    assert review_state(lane, "asset-a") == ready
    assert (len(service.calls), len(service.downloader.calls)) == calls
    ready.preview.path.unlink()
    with pytest.raises(previews.PreviewError, match="unavailable; use Retry"):
        previews.check_still(ready.preview)
    # Requesting again keeps the ready state and fetches nothing.
    scheduler.request_review("request", ["asset-a"])
    drive(scheduler)
    assert review_state(lane, "asset-a") == ready
    assert (len(service.calls), len(service.downloader.calls)) == calls
    # The lost file fails the lane's cache verification, so a retry fetches it
    # again: one metadata read and one transfer.
    assert scheduler.retry("request", "asset-a", review=True).get(STILL).state == State.QUEUED
    drive(scheduler)
    again = review_state(lane, "asset-a")
    assert again.state == State.READY
    assert previews.check_still(again.preview) == again.preview.path
    assert again.preview.path.read_bytes() == JPEG
    assert (len(service.calls), len(service.downloader.calls)) == (calls[0] + 1, calls[1] + 1)


def test_review_and_saved_result_entries_of_one_asset_never_share_state(lane):
    service, scheduler = lane.env, lane.scheduler
    ready_job(service, "request", [("asset-a", "video/mp4", MP4)])
    still_url = f"{CDN}/result-still.jpg"
    service.assets["asset-a"] = asset_record("asset-a", "video/mp4", thumbnail=still_url)
    service.downloader.files[still_url] = JPEG
    scheduler.request("request")
    drive(scheduler)
    result = scheduler.status("request", "asset-a")
    assert result.kind == "video" and result.get(STILL).state == State.READY
    assert scheduler.status("request", "asset-a", review=True) is None
    # Review targets need a remote workflow job; this saved result is not one.
    with pytest.raises(ResultError):
        scheduler.request_review("request", ["asset-a"])
    assert scheduler.status("request", "asset-a") == result
