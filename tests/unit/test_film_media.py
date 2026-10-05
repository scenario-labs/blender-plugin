# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Saved file receipts and current origins gate unpaid Film composition drafts."""

import copy
import hashlib
import json
import threading
from fractions import Fraction
from pathlib import Path
from types import SimpleNamespace

import httpx
import pytest

from scenario.core.api.sdk_adapter import Credentials, SDKAdapter
from scenario.core.jobs import media_probe
from scenario.core.jobs.coordinator import JobCoordinator, QuoteError
from scenario.core.jobs.film_tasks import _task_context
from scenario.core.jobs.origins import OriginRevisions
from scenario.core.jobs.results import ResultError
from scenario.core.jobs.store import (
    JobIntent,
    JobScope,
    JobState,
    JobStore,
    ResultAsset,
    StoreConflict,
)
from scenario.core.jobs.transfers import (
    DownloadedResult,
    ResultDownloader,
    StoragePolicy,
    TransferError,
)
from scenario.core.jobs.upload_sources import UploadSources
from scenario.core.jobs.upload_store import UploadState, UploadStore
from scenario.core.jobs.upload_transfers import PartUploader
from scenario.core.jobs.workers import JobWorkers, WorkerError
from scenario.core.scene.film_scene_plan import local_plan


@pytest.fixture
def env(tmp_path, monkeypatch):
    scope = JobScope("https://fixture.invalid/v1", "account")
    revisions = OriginRevisions()
    e = SimpleNamespace(
        scope=scope,
        origin=revisions.capture("scene"),
        revisions=revisions,
        store=JobStore(tmp_path / "jobs.sqlite3", scope),
        uploads=UploadStore(tmp_path / "uploads.sqlite3", scope),
        probes=[],
        root=tmp_path,
        after_probe=None,
        video_seconds="4",
        audio_seconds="2",
    )
    source_root, result_root, probe_root = (tmp_path / p for p in ("sources", "results", "probes"))
    for directory in (source_root, result_root, probe_root):
        directory.mkdir(mode=0o700)
    e.sources, e.probe_root = UploadSources(source_root), probe_root
    policy = StoragePolicy(frozenset({"storage.invalid"}))
    adapter = SDKAdapter(
        Credentials("fixture", "secret"),
        online=lambda: False,
        base_url=scope.service,
        account_id=scope.account_id,
        transport=httpx.MockTransport(lambda request: pytest.fail("Media inspection used the SDK")),
    )
    e.owner = JobCoordinator(
        adapter,
        e.store,
        origin_guard=revisions.guard,
        upload_store=e.uploads,
        upload_sources=e.sources,
        part_uploader=PartUploader(policy, online_access=lambda: False),
        result_root=result_root,
        result_downloader=ResultDownloader(policy, online_access=lambda: False),
    )
    e.workers = JobWorkers(e.owner)
    e.recipe = {
        "title": "Composition",
        "fps": 30,
        "shots": [
            {"id": "shot", "title": "Shot", "duration": 4, "scene": local_plan("studio", "", 4)}
        ],
        "tasks": [
            {
                "id": "shot-video",
                "title": "Shot",
                "kind": "model",
                "model": "model",
                "parameters": {"prompt": "fixture"},
            },
            {"id": "score", "title": "Score", "kind": "upload"},
        ],
    }
    binding, *_ = _task_context(
        e.store, e.recipe, production_id="production", task_id="shot-video", kind="model"
    )
    row = e.store.create(
        JobIntent(
            "video", scope, e.origin, "model", "model", "a" * 64, "b" * 64, "1", film_task=binding
        )
    )
    for state in (JobState.SUBMITTING, JobState.REMOTE, JobState.SUCCEEDED):
        row = e.store.transition(
            "video",
            expected_revision=row.revision,
            state=state,
            remote_job_id="remote" if state == JobState.REMOTE else None,
        )
    row = e.store.set_results(
        "video",
        (ResultAsset("asset-video", "video.mp4", "video/mp4"),),
        expected_revision=row.revision,
    )
    row = e.store.transition("video", expected_revision=row.revision, state=JobState.DOWNLOADING)
    e.video = e.owner._results._directory(row) / "video.mp4"
    e.video.write_bytes(b"picture")
    receipt = DownloadedResult(e.video.name, 7, hashlib.sha256(b"picture").hexdigest())
    row = e.store.record_download("video", "asset-video", receipt, expected_revision=row.revision)
    e.store.transition("video", expected_revision=row.revision, state=JobState.READY)
    source = tmp_path / "score.wav"
    source.write_bytes(b"sound")
    intent = e.sources.stage(
        source,
        request_id="score",
        scope=scope,
        origin=e.origin,
        kind="audio",
        content_type="audio/wav",
    )
    row = e.uploads.create(intent)
    for state in (UploadState.INITIALIZING, UploadState.UPLOADING, UploadState.IMPORTED):
        row = e.uploads.transition(
            "score",
            expected_revision=row.revision,
            state=state,
            upload_id="upload" if state == UploadState.UPLOADING else None,
            asset_id="asset-score" if state == UploadState.IMPORTED else None,
        )
    e.owner.bind_film_upload(
        e.recipe,
        production_id="production",
        task_id="score",
        request_id="score",
        expected_revision=row.revision,
        origin=e.origin,
    )
    e.audio = e.sources._directory(scope, "score") / "source.bin"
    monkeypatch.setattr(media_probe, "probe_tool", lambda: tmp_path / "ffprobe")
    monkeypatch.setattr("scenario.core.jobs.film_media.probe_tool", lambda: tmp_path / "ffprobe")

    def probe(command, *, stdout, **options):
        e.probes.append((command, threading.current_thread()))
        content = Path(command[command.index("-i") + 1]).read_bytes()
        assert content in (b"picture", b"sound")
        stream = (
            {
                "codec_type": "video",
                "width": 64,
                "height": 64,
                "avg_frame_rate": "30/1",
                "duration": e.video_seconds,
            }
            if content == b"picture"
            else {"codec_type": "audio", "duration": e.audio_seconds}
        )
        stdout.write_text(json.dumps({"streams": [stream]}))
        if e.after_probe:
            e.after_probe()

    monkeypatch.setattr(media_probe, "_run", probe)
    yield e
    e.workers.shutdown()


def prepare(e):
    return e.workers.prepare_film_composition(
        e.recipe,
        production_id="production",
        mode="final",
        score_task_id="score",
        root=e.probe_root,
        origin=e.origin,
    )


def test_composition_measures_saved_bytes_off_thread_without_network_or_mutation(env):
    before = (copy.deepcopy(env.recipe), env.store.records(), env.uploads.records())
    result = prepare(env).result(3)
    assert result.scope == env.scope and result.origin == env.origin
    assert dict(result.media)["score"].duration == Fraction(2)
    assert dict(result.media)["shot-video"].sha256 == hashlib.sha256(b"picture").hexdigest()
    assert [
        layer["source"] for layer in result.draft.recipe["tasks"][-1]["parameters"]["layers"]
    ] == ["$shot-video", "$score", "$score"]
    assert before == (env.recipe, env.store.records(), env.uploads.records())
    assert all(thread in env.workers._threads for _, thread in env.probes)
    assert not tuple(env.probe_root.iterdir())
    # Completion releases local admission before waking a waiting caller.
    assert prepare(env).result(3) == result


@pytest.mark.parametrize("source", ["video", "audio"])
@pytest.mark.parametrize("mutation", ["changed", "missing"])
def test_changed_or_missing_saved_bytes_never_prepare_or_refetch(env, source, mutation):
    path = getattr(env, source)
    path.write_bytes(b"changed") if mutation == "changed" else path.unlink()
    records = (env.store.records(), env.uploads.records())
    with pytest.raises((media_probe.MediaProbeError, ResultError, TransferError)):
        prepare(env).result(3)
    assert records == (env.store.records(), env.uploads.records())
    assert not tuple(env.probe_root.iterdir())


@pytest.mark.parametrize("late", [False, True])
def test_scene_change_before_or_during_probe_rejects_completion(env, late):
    def invalidate():
        env.revisions.invalidate("scene")

    if late:
        env.after_probe = invalidate
    else:
        invalidate()
    with pytest.raises(QuoteError, match="origin changed"):
        prepare(env).result(3)
    assert len(env.probes) == int(late)


def test_saved_record_change_during_probe_invalidates_draft(env):
    def change():
        row = env.store.get("video")
        env.store.transition("video", expected_revision=row.revision, state=JobState.APPLYING)

    env.after_probe = change
    with pytest.raises(StoreConflict, match="changed"):
        prepare(env).result(3)


def test_a_short_picture_cannot_cover_the_cut_or_trim(env):
    env.video_seconds = "3.99"
    with pytest.raises(media_probe.MediaProbeError, match="editorial cut"):
        prepare(env).result(3)
    env.video_seconds = "4"
    env.recipe["shots"][0]["source_trim"] = 1 / 30
    with pytest.raises(media_probe.MediaProbeError, match="editorial cut"):
        prepare(env).result(3)


def test_explicit_empty_audio_does_not_require_score_bytes(env):
    env.recipe["audio_tracks"] = []
    env.audio.unlink()
    result = prepare(env).result(3)
    assert tuple(dict(result.media)) == ("shot-video",)


@pytest.mark.parametrize("retire", [False, True])
def test_cancel_or_retire_stops_media_and_shares_local_admission(env, monkeypatch, retire):
    entered = threading.Event()

    def waiting(command, *, cancel, **kwargs):
        entered.set()
        assert cancel.wait(3)
        raise media_probe.RenderCancelled("Cancelled")

    monkeypatch.setattr(media_probe, "_run", waiting)
    task = prepare(env)
    assert entered.wait(2)
    with pytest.raises(WorkerError, match="current local media"):
        prepare(env)
    env.workers.deactivate() if retire else env.workers.cancel_local(task)
    with pytest.raises(media_probe.RenderCancelled):
        task.result(3)
    assert not tuple(env.probe_root.iterdir())
