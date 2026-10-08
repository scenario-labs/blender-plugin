# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Shared workers retain exact Film copies until consumption, discard or retirement."""

import copy
import hashlib
import threading
from dataclasses import replace
from pathlib import Path

import pytest
from test_film_media import env as env

from scenario.core.jobs import film_review_media
from scenario.core.jobs.coordinator import QuoteError
from scenario.core.jobs.film_tasks import _task_context
from scenario.core.jobs.local_render import RenderCancelled
from scenario.core.jobs.media_probe import MediaProbeError
from scenario.core.jobs.store import JobIntent, JobState, ResultAsset
from scenario.core.jobs.transfers import DownloadedResult, TransferError
from scenario.core.jobs.workers import WorkerError
from scenario.core.scene.film_finish import AudioDuration, compose_recipe
from scenario.core.scene.film_plan import TaskAssets


def prepare(e, **options):
    return e.workers.prepare_film_review(
        e.recipe,
        production_id="production",
        mode="final",
        score_task_id="score",
        include_master=options.get("include_master", False),
        root=e.probe_root,
        origin=e.origin,
    )


def test_worker_copies_and_measures_without_mutating_jobs_or_recipe(env):
    before = copy.deepcopy(env.recipe), env.store.records(), env.uploads.records()
    prepared = prepare(env).result(3)
    assert prepared.scope == env.scope and prepared.origin == env.origin
    assert [source.path.read_bytes() for _, source in prepared.files] == [b"picture", b"sound"]
    assert [source.result.receipt.name for _, source in prepared.files] == ["0.mp4", "1.wav"]
    assert all(thread is not threading.main_thread() for _, thread in env.probes)
    assert before == (env.recipe, env.store.records(), env.uploads.records())
    env.video.unlink()
    env.audio.unlink()
    film_review_media.check_copies(prepared)
    assert env.owner.take_film_review(prepared, origin=env.origin) is prepared
    with pytest.raises(ValueError, match="unconsumed"):
        env.owner.take_film_review(prepared, origin=env.origin)
    env.workers.shutdown()
    assert prepared.directory.exists()
    film_review_media.discard(prepared)


def test_discard_and_retirement_remove_only_unconsumed_copies(env):
    first = prepare(env).result(3)
    env.owner.discard_film_review(first)
    assert not first.directory.exists()
    with pytest.raises(ValueError, match="unconsumed"):
        env.owner.take_film_review(first, origin=env.origin)
    second = prepare(env).result(3)
    env.workers.shutdown()
    assert not second.directory.exists()
    assert env.video.exists() and env.audio.exists()


def test_copied_ticket_and_changed_origin_cannot_transfer_ownership(env):
    prepared = prepare(env).result(3)
    with pytest.raises(ValueError, match="unconsumed"):
        env.owner.take_film_review(replace(prepared), origin=env.origin)
    env.revisions.invalidate("scene")
    with pytest.raises(QuoteError):
        env.owner.take_film_review(prepared, origin=env.origin)
    assert prepared.directory.exists()


def test_changed_record_blocks_even_when_independent_copies_survive(env):
    prepared = prepare(env).result(3)
    record = env.store.get("video")
    env.store.transition("video", expected_revision=record.revision, state=JobState.APPLYING)
    with pytest.raises(ValueError, match="sources changed"):
        env.owner.take_film_review(prepared, origin=env.origin)


@pytest.mark.parametrize("change", ["bytes", "replace", "missing", "symlink"])
def test_changed_private_copy_never_reaches_native_ownership(env, change):
    prepared = prepare(env).result(3)
    path = prepared.files[0][1].path
    if change == "bytes":
        path.write_bytes(b"changed")
    else:
        path.unlink()
        if change == "replace":
            path.write_bytes(b"picture")
        elif change == "symlink":
            path.symlink_to(env.video)
    with pytest.raises((ValueError, OSError, TransferError)):
        env.owner.take_film_review(prepared, origin=env.origin)
    assert env.owner._film_reviews[id(prepared)] is prepared


@pytest.mark.parametrize("failure", ["origin", "cancel", "probe", "rate", "duration", "budget"])
def test_failed_preparation_cleans_new_files_and_preserves_originals(env, monkeypatch, failure):
    entered, release = threading.Event(), threading.Event()
    if failure == "origin":
        env.after_probe = lambda: env.revisions.invalidate("scene")
    elif failure == "probe":

        def fail():
            raise ValueError("fixture failure")

        env.after_probe = fail
    elif failure == "rate":
        env.recipe["fps"] = 24
    elif failure == "duration":
        env.video_seconds = "1"
    elif failure == "budget":
        monkeypatch.setattr(film_review_media, "MAX_TOTAL_BYTES", 8)
    else:

        def hold():
            entered.set()
            assert release.wait(3)

        env.after_probe = hold
    task = prepare(env)
    if failure == "cancel":
        assert entered.wait(3)
        with pytest.raises(WorkerError):
            prepare(env)
        env.workers.cancel_local(task)
        release.set()
    with pytest.raises((ValueError, RenderCancelled, QuoteError, MediaProbeError)):
        task.result(3)
    assert not list(env.probe_root.iterdir())
    assert not env.owner._film_reviews
    assert env.video.exists() and env.audio.exists()


@pytest.mark.parametrize("failure", ["probe", "cancel", "origin", "admission"])
def test_failed_cleanup_preserves_original_error_and_retries_at_joined_shutdown(
    env, monkeypatch, caplog, failure
):
    entered, release = threading.Event(), threading.Event()
    original_remove = film_review_media.shutil.rmtree
    original_prepare = film_review_media.prepare

    def denied(path, *args, **kwargs):
        if Path(path).parent == env.probe_root and Path(path).name.startswith("review-"):
            raise PermissionError("fixture cleanup denied")
        return original_remove(path, *args, **kwargs)

    def probe_failure():
        raise MediaProbeError("fixture probe failed")

    def hold():
        entered.set()
        assert release.wait(3)

    def lose_admission(*args, **kwargs):
        prepared = original_prepare(*args, **kwargs)
        env.revisions.invalidate("scene")
        return prepared

    if failure == "probe":
        env.after_probe = probe_failure
        expected = MediaProbeError
    elif failure == "cancel":
        env.after_probe = hold
        expected = RenderCancelled
    else:
        expected = QuoteError
        if failure == "origin":
            env.after_probe = lambda: env.revisions.invalidate("scene")
    with monkeypatch.context() as patch:
        patch.setattr(film_review_media.shutil, "rmtree", denied)
        if failure == "admission":
            patch.setattr(film_review_media, "prepare", lose_admission)
        task = prepare(env)
        if failure == "cancel":
            assert entered.wait(3)
            env.workers.cancel_local(task)
            release.set()
        with pytest.raises(expected) as caught:
            task.result(3)
        assert "retained for shutdown cleanup retry" in caught.value.__notes__[0]
        if failure == "probe":
            assert str(caught.value) == "fixture probe failed"
        (directory,) = env.owner._film_review_cleanup
        assert directory.exists() and list(directory.iterdir())
        assert not env.owner._film_reviews
        with pytest.raises(RuntimeError, match="cleanup inspection"):
            env.workers.shutdown()
        assert directory in env.owner._film_review_cleanup
        messages = [
            record.getMessage()
            for record in caplog.records
            if record.getMessage().startswith("Unused Film review media needs cleanup inspection:")
        ]
        assert messages == [f"Unused Film review media needs cleanup inspection: {directory}"]
    env.workers.shutdown()
    assert not directory.exists() and not env.owner._film_review_cleanup
    assert env.video.exists() and env.audio.exists()


def test_failed_cleanup_counts_toward_the_retained_review_limit(env, monkeypatch):
    remove = film_review_media.shutil.rmtree

    def denied(path, *args, **kwargs):
        if Path(path).parent == env.probe_root and Path(path).name.startswith("review-"):
            raise PermissionError("fixture cleanup denied")
        return remove(path, *args, **kwargs)

    def fail():
        raise MediaProbeError("fixture probe failed")

    env.after_probe = fail
    with monkeypatch.context() as patch:
        patch.setattr(film_review_media.shutil, "rmtree", denied)
        with pytest.raises(MediaProbeError):
            prepare(env).result(3)
    env.after_probe = None
    for _ in range(15):
        prepare(env).result(3)
    with pytest.raises(ValueError, match="Finish or discard"):
        prepare(env).result(3)
    assert len(list(env.probe_root.iterdir())) == 16
    env.workers.shutdown()
    assert not list(env.probe_root.iterdir())


def test_shutdown_cancels_live_preparation_before_removing_its_files(env):
    entered, release = threading.Event(), threading.Event()

    def hold():
        entered.set()
        assert release.wait(3)

    env.after_probe = hold
    task = prepare(env)
    assert entered.wait(3)
    env.workers.deactivate()
    release.set()
    with pytest.raises((RenderCancelled, QuoteError)):
        task.result(3)
    env.workers.shutdown()
    assert not list(env.probe_root.iterdir())


def test_private_copy_change_during_probe_is_rejected(env):
    def change():
        next(env.probe_root.glob("review-*/*mp4")).write_bytes(b"changed")

    env.after_probe = change
    with pytest.raises(ValueError, match="during inspection"):
        prepare(env).result(3)
    assert not list(env.probe_root.iterdir())


@pytest.mark.parametrize("model", ["model_scenario-compose-video", "wrong-model"])
def test_explicit_matching_master_is_copied_and_rechecked(env, model):
    prepared = prepare(env).result(3)
    observations = prepared.observations
    info = dict(prepared.files)["score"].media
    draft = compose_recipe(
        env.recipe,
        {s.task_id: TaskAssets(s.scope, (s.asset_id,)) for s in observations},
        scope=env.scope,
        audio_durations={"score": AudioDuration(env.scope, "asset-score", info.duration)},
    )
    binding, *_ = _task_context(
        env.store, draft, production_id="production", task_id="final-master", kind="model"
    )
    row = env.store.create(
        JobIntent(
            "master",
            env.scope,
            env.origin,
            "model",
            model,
            "a" * 64,
            "b" * 64,
            "1",
            film_task=binding,
        )
    )
    for state in (JobState.SUBMITTING, JobState.REMOTE, JobState.SUCCEEDED):
        row = env.store.transition(
            "master",
            expected_revision=row.revision,
            state=state,
            remote_job_id="remote-master" if state == JobState.REMOTE else None,
        )
    row = env.store.set_results(
        "master",
        (ResultAsset("master-asset", "master.mp4", "video/mp4"),),
        expected_revision=row.revision,
    )
    row = env.store.transition("master", expected_revision=row.revision, state=JobState.DOWNLOADING)
    path = env.owner._results._directory(row) / "master.mp4"
    path.write_bytes(b"picture")
    receipt = DownloadedResult(path.name, 7, hashlib.sha256(b"picture").hexdigest())
    row = env.store.record_download(
        "master", "master-asset", receipt, expected_revision=row.revision
    )
    env.store.transition("master", expected_revision=row.revision, state=JobState.READY)
    if model == "wrong-model":
        with pytest.raises(ValueError, match="master"):
            prepare(env, include_master=True).result(3)
        assert list(env.probe_root.iterdir()) == [prepared.directory]
        return
    result = prepare(env, include_master=True).result(3)
    assert result.master_task == "final-master" and len(result.files) == 3
    env.owner.take_film_review(result, origin=env.origin)
    film_review_media.discard(result)


def test_missing_master_does_not_leave_partial_copies(env):
    with pytest.raises(ValueError, match="master"):
        prepare(env, include_master=True).result(3)
    assert not list(env.probe_root.iterdir())


def test_preparation_capacity_releases_only_explicitly_discarded_tickets(env):
    tickets = [prepare(env).result(3) for _ in range(16)]
    with pytest.raises(ValueError, match="discard"):
        prepare(env).result(3)
    assert len(list(env.probe_root.iterdir())) == 16
    env.owner.discard_film_review(tickets[0])
    replacement = prepare(env).result(3)
    assert replacement.directory.exists() and len(env.owner._film_reviews) == 16


def test_missing_origin_rejects_before_copying(env):
    with pytest.raises(ValueError, match="origin"):
        env.owner.prepare_film_review(
            env.recipe,
            production_id="production",
            mode="final",
            score_task_id="score",
            include_master=False,
            root=env.probe_root,
            origin=None,
            cancel=threading.Event(),
        )
    assert not list(env.probe_root.iterdir())
