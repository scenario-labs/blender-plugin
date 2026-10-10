# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Preview polling windows and the dedicated lane, with real workers and no network."""

import os
import threading
from concurrent import futures
from functools import partial
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from scenario.core.jobs import preview_scheduler, transfers
from scenario.core.jobs import result_previews as previews
from scenario.core.jobs.coordinator import RemoteSnapshot
from scenario.core.jobs.preview_scheduler import ResultPreviewScheduler
from scenario.core.jobs.store import JobIntent, JobState
from scenario.core.jobs.transfers import ResultDownloader
from scenario.core.jobs.workers import JobWorkers
from tests.unit.test_result_previews import (
    CDN,
    GLB,
    JPEG,
    MP4,
    ORIGIN,
    SCOPE,
    asset_record,
    env,  # noqa: F401 - shared fixture
    png,
    ready_job,
    wav,
    work_directories,
)
from tests.unit.test_result_transfers import Response

STILL, CLIP, ENVELOPE = previews.STILL, previews.CLIP, previews.ENVELOPE
State = previews.PreviewState


class Clock:
    def __init__(self):
        self.now = 1000.0

    def __call__(self):
        return self.now


@pytest.fixture
def lane(env):  # noqa: F811 - pytest injects the shared fixture
    clock = Clock()
    workers = JobWorkers(env.coordinator, workers=1)
    scheduler = ResultPreviewScheduler(workers, env.coordinator, env.cache, clock=clock)
    yield SimpleNamespace(env=env, clock=clock, workers=workers, scheduler=scheduler)
    workers.deactivate()
    workers.shutdown()


def drive(scheduler):
    """Pump until no lane batch, maintenance pass or publication remains in flight."""
    scheduler.pump()
    for _ in range(50):
        pending = (scheduler._task, scheduler._maintenance, *scheduler._publishing)
        tasks = [task for task in pending if task is not None]
        tasks += [task for task, _ in scheduler._discards if task is not None]
        if not tasks:
            return
        futures.wait([task._future for task in tasks], timeout=5)
        scheduler.pump()
    pytest.fail("Preview lane did not settle")


def state(lane, asset_id, rendition=STILL):
    return lane.scheduler.status("request", asset_id).get(rendition)


def test_late_thumbnail_polling_backs_off_within_a_bounded_window(lane):
    service, clock, scheduler = lane.env, lane.clock, lane.scheduler
    ready_job(service, "request", [("asset-model", "model/gltf-binary", GLB)])
    service.assets["asset-model"] = asset_record("asset-model", "model/gltf-binary")
    (status,) = scheduler.request("request")
    assert status.get(STILL).state == State.QUEUED and status.kind == "3d"
    start, polls = clock.now, []
    for _ in range(420):
        before = len(service.calls)
        drive(scheduler)
        if len(service.calls) > before:
            polls.append(clock.now - start)
        clock.now += 1
    assert polls == [0, 5, 15, 35, 75, 135, 195, 255, 300]
    assert {thread.name for *_, thread in service.calls} == {"ScenarioPreview"}
    assert state(lane, "asset-model").state == State.MISSING
    url = f"{CDN}/model-still.jpg"
    service.assets["asset-model"] = asset_record("asset-model", "model/gltf-binary", thumbnail=url)
    service.downloader.files[url] = JPEG
    assert scheduler.retry("request", "asset-model").get(STILL).state == State.QUEUED
    drive(scheduler)
    ready = state(lane, "asset-model")
    assert ready.state == State.READY and ready.preview.path.read_bytes() == JPEG


def test_available_thumbnail_and_requested_clip_need_one_poll(lane):
    service, scheduler = lane.env, lane.scheduler
    ready_job(service, "request", [("asset-video", "video/mp4", MP4)])
    still, clip = f"{CDN}/still.png", f"{CDN}/clip.mp4"
    service.assets["asset-video"] = asset_record(
        "asset-video", "video/mp4", thumbnail=still, preview=clip
    )
    service.downloader.files.update({still: png(4, 2), clip: MP4})
    scheduler.request("request", clip=True)
    drive(scheduler)
    assert state(lane, "asset-video").state == state(lane, "asset-video", CLIP).state == State.READY
    lane.clock.now += 1000
    drive(scheduler)
    assert len(service.calls) == 1 and len(service.downloader.calls) == 2


def _storage(service, monkeypatch, *responses):
    """The real downloader over a mocked HTTPS connection answering ``responses`` in turn."""
    connection = Mock()
    connection.getresponse.side_effect = responses
    monkeypatch.setattr(transfers.http.client, "HTTPSConnection", Mock(return_value=connection))
    monkeypatch.setattr(
        service.downloader, "download", partial(ResultDownloader.download, service.downloader)
    )
    return connection


def _redirect():
    # A first request for a new preview can redirect off the configured host.
    return Response(b"", status=302, headers={"Location": "https://images.example.invalid/t"})


def test_cross_host_redirect_is_polled_again_until_storage_serves_the_still(lane, monkeypatch):
    service, clock, scheduler = lane.env, lane.clock, lane.scheduler
    ready_job(service, "request", [("asset-video", "video/mp4", MP4)])
    url = f"{CDN}/still.jpg?Signature=preview-secret"
    service.assets["asset-video"] = asset_record("asset-video", "video/mp4", thumbnail=url)
    connection = _storage(service, monkeypatch, _redirect(), Response(JPEG))
    scheduler.request("request")
    drive(scheduler)
    first = state(lane, "asset-video")
    assert first.state == State.PENDING and "retrying" in first.reason
    assert "https" not in first.reason and "Signature" not in first.reason
    assert work_directories(service) == []
    clock.now += 4
    drive(scheduler)
    assert len(service.calls) == 1  # The backoff holds the next poll.
    clock.now += 1
    drive(scheduler)
    ready = state(lane, "asset-video")
    assert ready.state == State.READY and ready.preview.path.read_bytes() == JPEG
    assert len(service.calls) == 2 and connection.request.call_count == 2
    # Only the configured storage host was contacted; the redirect was not followed.
    assert {call.args[0] for call in transfers.http.client.HTTPSConnection.call_args_list} == {
        "cdn.cloud.scenario.com"
    }


def test_persistent_transfer_failure_settles_failed_at_the_window_end(lane, monkeypatch):
    service, clock, scheduler = lane.env, lane.clock, lane.scheduler
    ready_job(service, "request", [("asset-model", "model/gltf-binary", GLB)])
    url = f"{CDN}/model.png?Signature=preview-secret"
    service.assets["asset-model"] = asset_record("asset-model", "model/gltf-binary", thumbnail=url)
    connection = _storage(service, monkeypatch)
    connection.getresponse.side_effect = _redirect
    scheduler.request("request")
    start, polls = clock.now, []
    for _ in range(420):
        before = len(service.calls)
        drive(scheduler)
        if len(service.calls) > before:
            polls.append(clock.now - start)
        clock.now += 1
    assert polls == [0, 5, 15, 35, 75, 135, 195, 255, 300]
    assert connection.request.call_count == len(polls)
    failed = state(lane, "asset-model")
    assert failed.state == State.FAILED and "Retry" in failed.reason
    assert list(service.cache.rglob("still.*")) == [] and work_directories(service) == []
    # No missing marker was written: an explicit retry fetches again at once.
    connection.getresponse.side_effect = [Response(png(4, 4))]
    assert scheduler.retry("request", "asset-model").get(STILL).state == State.QUEUED
    drive(scheduler)
    assert state(lane, "asset-model").state == State.READY


def test_idle_scheduler_evicts_previews_written_after_the_last_pass(lane, monkeypatch):
    service, clock, scheduler = lane.env, lane.clock, lane.scheduler
    assets = [(f"asset-{index}", "video/mp4", MP4) for index in range(2)]
    ready_job(service, "request", assets)
    for name, _, _ in assets:
        url = f"{CDN}/{name}.jpg"
        service.assets[name] = asset_record(name, "video/mp4", thumbnail=url)
        service.downloader.files[url] = JPEG
    scheduler.request("request")
    # The first batch maintained the cache before it wrote both stills.
    drive(scheduler)
    ready = [state(lane, name).preview for name, _, _ in assets]
    assert all(preview is not None for preview in ready)
    for age, preview in zip((2000, 1000), ready, strict=True):
        stamp = os.path.getmtime(preview.path) - age
        for path in preview.path.parent.iterdir():
            os.utime(path, (stamp, stamp))
    # A budget that holds exactly one entry, so the cache is now over it.
    budget = sum(path.stat().st_size for path in ready[1].path.parent.iterdir())
    original, passes = previews.PreviewCache.evict, []

    def evict(cache, **options):
        passes.append(threading.current_thread().name)
        return original(cache, max_bytes=budget, **options)

    monkeypatch.setattr(previews.PreviewCache, "evict", evict)
    calls, downloads = len(service.calls), len(service.downloader.calls)
    clock.now += preview_scheduler.MAINTAIN_SECONDS - 1
    drive(scheduler)
    assert passes == []  # Throttled: the last pass ran less than ten minutes ago.
    clock.now += 1
    drive(scheduler)
    # No batch was due; a maintenance-only lane command evicted the oldest entry.
    assert passes == ["ScenarioPreview"]
    assert not ready[0].path.exists() and ready[1].path.exists()
    assert (len(service.calls), len(service.downloader.calls)) == (calls, downloads)
    clock.now += preview_scheduler.MAINTAIN_SECONDS
    drive(scheduler)
    assert passes == ["ScenarioPreview"]  # Nothing was written since that pass.


def test_offline_time_does_not_consume_the_window(lane):
    service, clock, scheduler = lane.env, lane.clock, lane.scheduler
    ready_job(service, "request", [("asset-video", "video/mp4", MP4)])
    service.assets["asset-video"] = asset_record("asset-video", "video/mp4")
    service.online = False
    scheduler.request("request")
    for _ in range(600):
        drive(scheduler)
        clock.now += 1
    assert state(lane, "asset-video").state == State.OFFLINE and service.calls == []
    service.online = True
    for _ in range(100):
        drive(scheduler)
        clock.now += 1
    assert state(lane, "asset-video").state == State.PENDING and len(service.calls) == 5


def test_offline_pause_resumes_the_window_instead_of_restarting_it(lane):
    service, clock, scheduler = lane.env, lane.clock, lane.scheduler
    ready_job(service, "request", [("asset-video", "video/mp4", MP4)])
    service.assets["asset-video"] = asset_record("asset-video", "video/mp4")
    scheduler.request("request")
    for _ in range(20):
        drive(scheduler)
        clock.now += 1
    assert len(service.calls) == 3  # Online polls at 0, 5 and 15 seconds.
    service.online = False
    for _ in range(600):
        drive(scheduler)
        clock.now += 1
    # The poll due at 35 seconds found no access: 35 seconds of the window are used.
    assert state(lane, "asset-video").state == State.OFFLINE and len(service.calls) == 3
    service.online, resumed = True, clock.now
    while state(lane, "asset-video").state != State.MISSING:
        assert clock.now - resumed < 300, "The resumed window did not end"
        drive(scheduler)
        clock.now += 1
    assert clock.now - 1 - resumed == 300 - 35
    assert len(service.calls) == 9


def _gated(service):
    entered, release = threading.Event(), threading.Event()

    def gate():
        entered.set()
        assert release.wait(5), "Test did not release the preview lane"

    service.gate = gate
    return entered, release


def test_decode_limited_audio_envelope_is_sent_once_decodes_free(lane):
    service, clock, scheduler = lane.env, lane.clock, lane.scheduler
    images = [(f"asset-{index}", "image/png", png(4, 4)) for index in range(4)]
    ready_job(service, "request", [*images, ("asset-sound", "audio/wav", wav())])
    url = f"{CDN}/sound.png"
    service.assets["asset-sound"] = asset_record("asset-sound", "audio/wav", thumbnail=url)
    service.downloader.files[url] = png(4, 4)
    scheduler.request("request")
    drive(scheduler)
    assert state(lane, "asset-sound").state == State.READY
    assert state(lane, "asset-sound", ENVELOPE).state == State.QUEUED
    assert len(scheduler.decode_requests()) == 4
    for request in scheduler.decode_requests():
        request.output.write_bytes(png(2, 2))
        scheduler.finish_decode(request)
    drive(scheduler)
    assert state(lane, "asset-sound", ENVELOPE).state == State.DECODE
    (request,) = scheduler.decode_requests()
    assert request.rendition == ENVELOPE and request.source.name == "source.wav"
    assert len(service.calls) == 1  # The envelope is local; the still is not polled again.
    clock.now += 400
    drive(scheduler)
    assert len(service.calls) == 1


def test_clip_requested_during_an_inflight_still_poll_is_fetched(lane):
    service, scheduler = lane.env, lane.scheduler
    ready_job(service, "request", [("asset-video", "video/mp4", MP4)])
    still, clip = f"{CDN}/still.png", f"{CDN}/clip.mp4"
    service.assets["asset-video"] = asset_record(
        "asset-video", "video/mp4", thumbnail=still, preview=clip
    )
    service.downloader.files.update({still: png(4, 2), clip: MP4})
    entered, release = _gated(service)
    scheduler.request("request")
    scheduler.pump()
    assert entered.wait(2)
    (status,) = scheduler.request("request", clip=True)
    assert status.get(CLIP).state == State.QUEUED
    service.gate = None
    release.set()
    drive(scheduler)
    assert state(lane, "asset-video").state == state(lane, "asset-video", CLIP).state == State.READY
    assert len(service.calls) == 2 and len(service.downloader.calls) == 2


def test_clip_requested_after_the_still_window_ended_gets_a_full_window(lane):
    service, clock, scheduler = lane.env, lane.clock, lane.scheduler
    ready_job(service, "request", [("asset-video", "video/mp4", MP4)])
    service.assets["asset-video"] = asset_record("asset-video", "video/mp4")
    scheduler.request("request")
    for _ in range(320):
        drive(scheduler)
        clock.now += 1
    assert state(lane, "asset-video").state == State.MISSING and len(service.calls) == 9
    clock.now += 100
    (status,) = scheduler.request("request", clip=True)
    assert status.get(CLIP).state == State.QUEUED
    start, polls = clock.now, []
    for _ in range(420):
        before = len(service.calls)
        drive(scheduler)
        if len(service.calls) > before:
            polls.append(clock.now - start)
        clock.now += 1
    # The clip's first poll is not its last: it gets the full backoff and window.
    assert polls == [0, 5, 15, 35, 75, 135, 195, 255, 300]
    assert state(lane, "asset-video", CLIP).state == State.MISSING
    assert state(lane, "asset-video").state == State.MISSING


@pytest.mark.parametrize("fault", [None, 503], ids=["no-preview", "metadata-failure"])
def test_clip_requested_during_the_still_final_poll_shares_the_new_window(lane, fault):
    service, clock, scheduler = lane.env, lane.clock, lane.scheduler
    ready_job(service, "request", [("asset-video", "video/mp4", MP4)])
    service.assets["asset-video"] = asset_record("asset-video", "video/mp4")
    scheduler.request("request")
    for _ in range(300):
        drive(scheduler)
        clock.now += 1
    # Eight polls used the window; the final one is due now, at its end.
    assert len(service.calls) == 8 and state(lane, "asset-video").state == State.PENDING
    entered, release = _gated(service)
    service.status = fault
    scheduler.pump()
    assert entered.wait(2)
    scheduler.request("request", clip=True)
    service.gate = None
    release.set()
    drive(scheduler)
    # The overtaken final poll settles nothing: the still polls again with the
    # clip at once, with the missing marker it wrote cleared.
    assert len(service.calls) == 10
    assert state(lane, "asset-video").state == state(lane, "asset-video", CLIP).state
    assert state(lane, "asset-video").state == State.PENDING
    service.status, start, polls = None, clock.now, []
    url = f"{CDN}/video-still.jpg"
    service.downloader.files[url] = JPEG
    for _ in range(320):
        clock.now += 1
        if clock.now - start == 100:
            service.assets["asset-video"] = asset_record("asset-video", "video/mp4", thumbnail=url)
        before = len(service.calls)
        drive(scheduler)
        if len(service.calls) > before:
            polls.append(clock.now - start)
    assert polls == [5, 15, 35, 75, 135, 195, 255, 300]
    assert state(lane, "asset-video").state == State.READY
    assert state(lane, "asset-video", CLIP).state == State.MISSING


def test_retry_during_an_inflight_batch_applies_when_it_returns(lane):
    service, scheduler = lane.env, lane.scheduler
    ready_job(service, "request", [("asset-model", "model/gltf-binary", GLB)])
    service.assets["asset-model"] = asset_record("asset-model", "model/gltf-binary")
    entered, release = _gated(service)
    scheduler.request("request")
    scheduler.pump()
    assert entered.wait(2)
    assert scheduler.retry("request", "asset-model").get(STILL).state == State.QUEUED
    service.gate = None
    release.set()
    drive(scheduler)
    # The late "pending" outcome did not absorb the retry: a forced poll followed
    # at once, without waiting for the five-second backoff.
    assert len(service.calls) == 2
    assert state(lane, "asset-model").state == State.PENDING
    assert scheduler.retry("request", "asset-model").get(STILL).state == State.QUEUED
    drive(scheduler)
    assert len(service.calls) == 3


def _sound(lane, *, discard=True, others=()):
    """An audio result whose still keeps polling while its envelope has settled failed.

    With ``discard`` false, the envelope's decode request stays outstanding.
    """
    service, scheduler = lane.env, lane.scheduler
    ready_job(service, "request", [("asset-sound", "audio/wav", wav()), *others])
    service.assets["asset-sound"] = asset_record("asset-sound", "audio/wav")
    scheduler.request("request", asset_ids=["asset-sound"])
    drive(scheduler)
    (request,) = scheduler.decode_requests()
    if discard:
        scheduler.discard_decode(request, reason="Blender cannot decode this sound")
        drive(scheduler)
        assert state(lane, "asset-sound", ENVELOPE).state == State.FAILED
    return request


def _queued(snapshot):
    return {snapshot.get(rendition).state for rendition in (STILL, ENVELOPE)} == {State.QUEUED}


def test_retry_during_an_inflight_batch_reports_queued_at_once(lane):
    service, clock, scheduler = lane.env, lane.clock, lane.scheduler
    _sound(lane)
    assert state(lane, "asset-sound").state == State.PENDING
    entered, release = _gated(service)
    clock.now += 5
    scheduler.pump()
    assert entered.wait(2)  # The still's next poll is on the lane.
    # The failed envelope is fetched again too: neither read reports the old failure.
    assert _queued(scheduler.retry("request", "asset-sound"))
    assert _queued(scheduler.status("request", "asset-sound"))
    service.gate = None
    release.set()
    drive(scheduler)
    # The retry ran once the batch returned: a forced poll and a new decode request.
    assert len(service.calls) == 3
    assert state(lane, "asset-sound", ENVELOPE).state == State.DECODE


@pytest.mark.parametrize("outcome", [State.READY, State.MISSING, State.FAILED])
def test_late_outcome_of_a_batch_overtaken_by_retry_never_reads_settled(lane, monkeypatch, outcome):
    service, clock = lane.env, lane.clock
    # A five-second window makes the still's second poll its final one.
    scheduler = lane.scheduler = ResultPreviewScheduler(
        lane.workers, service.coordinator, service.cache, clock=clock, window=5, delays=(5,)
    )
    _sound(lane)
    url = f"{CDN}/sound-still.jpg"
    if outcome != State.MISSING:
        service.assets["asset-sound"] = asset_record("asset-sound", "audio/wav", thumbnail=url)
        service.downloader.files[url] = JPEG if outcome == State.READY else b"not an image"
    applied, original = [], scheduler._apply_batch

    def apply(task, batch, now):
        original(task, batch, now)
        applied.append(scheduler.status("request", "asset-sound").get(STILL).state)

    monkeypatch.setattr(scheduler, "_apply_batch", apply)
    entered, release = _gated(service)
    clock.now += 5
    scheduler.pump()
    assert entered.wait(2)
    task = scheduler._task
    observed = [scheduler.retry("request", "asset-sound")]
    service.gate = None
    release.set()
    futures.wait([task._future], timeout=5)
    assert task.done()
    observed.append(scheduler.status("request", "asset-sound"))  # Returned, not collected.
    scheduler.pump()
    observed.append(scheduler.status("request", "asset-sound"))
    # The late outcome was applied and replaced by the restart within one pump.
    assert applied == [outcome] and scheduler._task not in (None, task)
    assert all(_queued(snapshot) for snapshot in observed)
    drive(scheduler)
    # The restart reads the cached still, or polls again in a new window.
    settled = {State.READY: State.READY, State.MISSING: State.PENDING, State.FAILED: State.FAILED}
    assert state(lane, "asset-sound").state == settled[outcome]
    assert len(service.calls) == (2 if outcome == State.READY else 3)
    assert state(lane, "asset-sound", ENVELOPE).state == State.DECODE


def test_retry_during_an_offline_poll_reports_queued_and_stays_offline(lane):
    service, clock, scheduler = lane.env, lane.clock, lane.scheduler
    service.online = False
    _sound(lane)
    assert state(lane, "asset-sound").state == State.OFFLINE
    clock.now += preview_scheduler.OFFLINE_DELAY
    scheduler.pump()
    assert scheduler._task is not None  # The offline still's next check is on the lane.
    assert _queued(scheduler.retry("request", "asset-sound"))
    assert _queued(scheduler.status("request", "asset-sound"))
    drive(scheduler)
    assert state(lane, "asset-sound").state == State.OFFLINE
    assert state(lane, "asset-sound", ENVELOPE).state == State.DECODE
    assert service.calls == [] and service.downloader.calls == []


def test_retry_during_an_inflight_batch_withdraws_an_outstanding_decode(lane):
    clock, scheduler = lane.clock, lane.scheduler
    request = _sound(lane, discard=False)
    clock.now += 5
    scheduler.pump()
    assert scheduler._task is not None
    assert _queued(scheduler.retry("request", "asset-sound"))
    # A decode of the withdrawn copy can no longer publish over the queued retry.
    assert scheduler.decode_requests() == ()
    with pytest.raises(previews.PreviewError, match="outstanding"):
        scheduler.finish_decode(request)
    drive(scheduler)
    (fresh,) = scheduler.decode_requests()
    assert fresh is not request and not request.directory.exists()
    assert state(lane, "asset-sound", ENVELOPE).state == State.DECODE


def test_eviction_keeps_a_result_whose_retry_waits_for_its_batch(lane, monkeypatch):
    service, clock, scheduler = lane.env, lane.clock, lane.scheduler
    monkeypatch.setattr(preview_scheduler, "ENTRY_LIMIT", 2)
    notes = [(f"asset-note-{index}", "text/plain", b"plain words") for index in range(2)]
    _sound(lane, others=notes)
    scheduler.request("request", asset_ids=["asset-note-0"])
    clock.now += 5
    scheduler.pump()
    assert _queued(scheduler.retry("request", "asset-sound"))
    # Making room evicts only the settled note, never the result awaiting its batch.
    scheduler.request("request", asset_ids=["asset-note-1"])
    assert scheduler.status("request", "asset-note-0") is None
    assert _queued(scheduler.status("request", "asset-sound"))
    drive(scheduler)
    assert len(service.calls) == 3
    assert state(lane, "asset-sound", ENVELOPE).state == State.DECODE


def test_preview_lane_never_delays_job_refresh(lane):
    service, scheduler, workers = lane.env, lane.scheduler, lane.workers
    ready_job(service, "request", [("asset-video", "video/mp4", MP4)])
    service.assets["asset-video"] = asset_record("asset-video", "video/mp4")
    remote = service.store.create(
        JobIntent("busy", SCOPE, ORIGIN, "model", "model", "a" * 64, "b" * 64, "1.0")
    )
    for value in (JobState.SUBMITTING, JobState.REMOTE):
        remote = service.store.transition(
            "busy",
            expected_revision=remote.revision,
            state=value,
            remote_job_id="remote-busy" if value == JobState.REMOTE else None,
        )
    entered, release = threading.Event(), threading.Event()

    def gate():
        entered.set()
        assert release.wait(5), "Test did not release the preview lane"

    service.gate = gate
    scheduler.request("request")
    scheduler.pump()
    assert entered.wait(2)
    snapshot = workers.refresh_remote("busy", expected_revision=remote.revision).result(2)
    assert isinstance(snapshot, RemoteSnapshot) and not scheduler._task.done()
    release.set()
    drive(scheduler)
    assert state(lane, "asset-video").state == State.PENDING


def test_decode_requests_are_bounded_published_and_expired(lane):
    service, clock, scheduler = lane.env, lane.clock, lane.scheduler
    ready_job(
        service, "request", [(f"asset-{index}", "image/png", png(4, 4)) for index in range(6)]
    )
    scheduler.request("request")
    drive(scheduler)
    requests = scheduler.decode_requests()
    assert len(requests) == 4 and service.calls == []
    queued = [
        status for status in scheduler.request("request") if status.get(STILL).state == State.QUEUED
    ]
    assert len(queued) == 2
    first = requests[0]
    first.output.write_bytes(png(2, 2))
    scheduler.finish_decode(first)
    with pytest.raises(previews.PreviewError, match="outstanding"):
        scheduler.finish_decode(first)
    drive(scheduler)
    assert state(lane, first.key.asset_id).state == State.READY
    assert len(scheduler.decode_requests()) == 4
    clock.now += 121
    drive(scheduler)
    expired = [
        status for status in scheduler.request("request") if status.get(STILL).state == State.FAILED
    ]
    assert len(expired) == 4 and "Retry" in expired[0].get(STILL).reason
    drive(scheduler)
    assert len(work_directories(service)) == len(scheduler.decode_requests()) == 1


def test_discarded_decode_fails_and_foreign_requests_are_rejected(lane):
    service, scheduler = lane.env, lane.scheduler
    ready_job(service, "request", [("asset-image", "image/png", png(4, 4))])
    scheduler.request("request")
    drive(scheduler)
    (request,) = scheduler.decode_requests()
    forged = previews.DecodeRequest(
        request.key, STILL, "image/png", request.source, request.output, request.directory
    )
    with pytest.raises(previews.PreviewError, match="outstanding"):
        scheduler.finish_decode(forged)
    scheduler.discard_decode(request, reason="Blender cannot open this image")
    drive(scheduler)
    assert state(lane, "asset-image").reason == "Blender cannot open this image"
    assert work_directories(service) == []
    errors = []
    thread = threading.Thread(target=lambda: errors.append(_call(scheduler.request, "request")))
    thread.start()
    thread.join()
    assert isinstance(errors[0], RuntimeError)


def _call(function, *args):
    try:
        function(*args)
    except Exception as error:
        return error
    return None


def test_unsupported_results_need_no_lane_work(lane):
    service, scheduler = lane.env, lane.scheduler
    ready_job(service, "request", [("asset-text", "text/plain", b"plain words")])
    (status,) = scheduler.request("request")
    assert status.get(STILL).state == State.UNSUPPORTED and status.kind is None
    assert not scheduler.pump() and scheduler._task is None


def test_close_cancels_lane_and_release_removes_private_copies(lane):
    service, scheduler, workers = lane.env, lane.scheduler, lane.workers
    ready_job(
        service, "request", [("asset-a", "image/png", png(4, 4)), ("asset-b", "audio/wav", b"")]
    )
    scheduler.request("request", asset_ids=["asset-a"])
    drive(scheduler)
    assert len(work_directories(service)) == 1
    scheduler.close()
    assert not scheduler.pump()
    with pytest.raises(previews.PreviewError, match="closed"):
        scheduler.request("request")
    workers.deactivate()
    workers.shutdown()
    scheduler.release()
    assert work_directories(service) == []
    assert scheduler.status("request", "asset-a") is None


def test_stored_lane_control_exception_never_reaches_the_owner_thread(lane, monkeypatch):
    service, scheduler = lane.env, lane.scheduler
    ready_job(service, "request", [("asset-video", "video/mp4", MP4)])
    reported = threading.Event()
    monkeypatch.setattr(threading, "excepthook", lambda args: reported.set())

    def interrupt(*args, **kwargs):
        raise KeyboardInterrupt("fixture lane interruption")

    monkeypatch.setattr(service.coordinator, "prepare_result_previews", interrupt)
    scheduler.request("request")
    drive(scheduler)
    assert reported.wait(2)
    current = state(lane, "asset-video")
    assert current.state == State.PENDING and "retrying" in current.reason
    lane.clock.now += 60
    assert scheduler.pump() is False  # The retired lane rejects work; nothing is raised.


def test_retry_keeps_a_decoded_preview_that_is_being_published(lane):
    service, scheduler = lane.env, lane.scheduler
    ready_job(service, "request", [("asset-image", "image/png", png(4, 4))])
    scheduler.request("request")
    drive(scheduler)
    (request,) = scheduler.decode_requests()
    request.output.write_bytes(png(2, 2))
    scheduler.finish_decode(request)
    assert scheduler.retry("request", "asset-image").get(STILL).state == State.DECODE
    drive(scheduler)
    assert state(lane, "asset-image").state == State.READY
    assert scheduler.decode_requests() == ()
