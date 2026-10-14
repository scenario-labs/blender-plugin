# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Verified local files of saved results for local MCP job_status, offline and unpaid."""

import hashlib
import os
import threading
from pathlib import Path

import httpx
import pytest

from scenario.core.api.sdk_adapter import Credentials, SDKAdapter
from scenario.core.jobs import result_files
from scenario.core.jobs.coordinator import JobCoordinator
from scenario.core.jobs.preview_scheduler import BATCH_LIMIT
from scenario.core.jobs.result_files import (
    CHANGED,
    CHECKING,
    MISSING,
    NOT_DOWNLOADED,
    NOT_READY,
    UNAVAILABLE,
    VERIFIED,
    ResultFiles,
)
from scenario.core.jobs.result_previews import PreviewCanceled
from scenario.core.jobs.results import ResultError, _asset
from scenario.core.jobs.store import JobIntent, JobScope, JobState, JobStore, ResultAsset
from scenario.core.jobs.transfers import DownloadedResult
from scenario.core.jobs.workers import JobWorkers
from tests.unit.test_playback import assert_offline
from tests.unit.test_result_previews import (
    CDN,
    MP4,
    ORIGIN,
    SCOPE,
    FakeDownloader,
    asset_record,
    png,
    preview_env,
    ready_job,
)

WAV = b"RIFF" + b"\x00" * 40
GLB = b"glTF" + b"\x02\x00\x00\x00" + b"\x00" * 24
TEXT = b"plain words"


@pytest.fixture
def env(tmp_path):
    with preview_env(tmp_path) as state:
        state.tmp_path = tmp_path
        yield state


class Done:
    """A finished worker task, as the main-thread pump sees it."""

    def __init__(self, run):
        try:
            self._value, self._error = run(), None
        except Exception as error:
            self._value, self._error = None, error

    def done(self):
        return True

    def result(self, timeout=None):
        if self._error is not None:
            raise self._error
        return self._value


def checker(coordinator, queued=None):
    """Run each queued batch at once on the caller's thread, like a drained preview lane."""

    def queue(targets):
        if queued is not None:
            queued.append(tuple(targets))
        return Done(lambda: coordinator.result_files(tuple(targets), cancel=threading.Event()))

    return queue


def settle(files, coordinator, record):
    """One status read, then the pump that finishes its check, then the next status read."""
    files.watch(record.intent.request_id)
    files.project(record)
    files.start(checker(coordinator), files.unchecked(record))
    files.finish()
    return files.project(record)


def states(rows):
    return [(row.asset_id, row.state) for row in rows]


def listed(rows):
    return [row.file for row in rows if row.file is not None]


def every_kind(env, request_id="request"):
    return ready_job(
        env,
        request_id,
        [
            ("clip", "video/mp4", MP4),
            ("still", "image/png", png(8, 8)),
            ("sound", "audio/wav", WAV),
            ("mesh", "model/gltf-binary", GLB),
            ("notes", "text/plain", TEXT),
        ],
    )


def directory_of(env, record):
    return env.coordinator._results._directory(record, create=False)


def test_every_downloaded_result_is_listed_once_its_bytes_are_verified(env):
    record = every_kind(env)
    files = ResultFiles()
    files.watch("request")
    first = files.project(record)
    # Nothing is listed before a worker has rehashed it against its receipt.
    assert states(first) == [(item.asset.asset_id, CHECKING) for item in record.results]
    assert listed(first) == [] and files.pending(record)
    rows = settle(files, env.coordinator, record)
    directory = directory_of(env, record)
    assert states(rows) == [(item.asset.asset_id, VERIFIED) for item in record.results]
    # Video, image, audio, 3D and text alike, in result order.
    assert listed(rows) == [str(directory / item.asset.name) for item in record.results]
    assert all(Path(path).read_bytes() for path in listed(rows))
    assert not files.pending(record) and files.unchecked(record) == ()
    # A display check: no network, no download and no store change.
    assert env.store.get("request") == record
    assert_offline(env)


def test_a_job_saved_before_a_restart_lists_its_files_from_a_fresh_store(env):
    record = every_kind(env)
    expected = [str(directory_of(env, record) / item.asset.name) for item in record.results]

    def offline(request):
        raise AssertionError(f"Unexpected request {request.method} {request.url.path}")

    # A restarted Blender: new store connection, coordinator and session memory.
    store = JobStore(env.tmp_path / "jobs.sqlite3", SCOPE)
    with SDKAdapter(
        Credentials("key", "secret"),
        online=lambda: True,
        base_url=SCOPE.service,
        account_id=SCOPE.account_id,
        project_id=SCOPE.project_id,
        transport=httpx.MockTransport(offline),
    ) as adapter:
        downloader = FakeDownloader()
        coordinator = JobCoordinator(
            adapter, store, result_root=env.results, result_downloader=downloader
        )
        saved = store.get("request")
        assert saved == record
        rows = settle(ResultFiles(), coordinator, saved)
    assert states(rows) == [(item.asset.asset_id, VERIFIED) for item in record.results]
    assert listed(rows) == expected
    assert downloader.calls == []


def test_missing_partial_or_changed_files_are_never_listed(env):
    record = ready_job(
        env,
        "request",
        [
            ("gone", "video/mp4", MP4),
            ("partial", "image/png", png(8, 8)),
            ("changed", "audio/wav", WAV),
            ("linked", "model/gltf-binary", GLB),
            ("kept", "image/png", png(4, 4)),
        ],
    )
    directory = directory_of(env, record)
    names = {item.asset.asset_id: directory / item.asset.name for item in record.results}
    names["gone"].unlink()
    names["partial"].write_bytes(png(8, 8)[:-4])
    names["changed"].write_bytes(WAV[:-1] + b"\x01")
    copy = env.tmp_path / "copy.glb"
    copy.write_bytes(GLB)
    names["linked"].unlink()
    names["linked"].symlink_to(copy)
    rows = settle(ResultFiles(), env.coordinator, record)
    assert states(rows) == [
        ("gone", MISSING),
        ("partial", CHANGED),
        ("changed", CHANGED),
        ("linked", CHANGED),
        ("kept", VERIFIED),
    ]
    assert listed(rows) == [str(names["kept"])]
    assert all(row.file is None for row in rows if row.state != VERIFIED)


def replace(path, data):
    """Publish new bytes under the same name, as an editor or a copy would."""
    staged = path.with_name(path.name + ".new")
    staged.write_bytes(data)
    os.replace(staged, path)


def test_a_file_changed_after_its_check_is_checked_again_before_it_is_listed(env):
    record = ready_job(env, "request", [("clip", "video/mp4", MP4)])
    path = directory_of(env, record) / record.results[0].asset.name
    files = ResultFiles()
    assert listed(settle(files, env.coordinator, record)) == [str(path)]
    replace(path, MP4[::-1])
    # The next status read notices the new identity before listing it again.
    assert states(files.project(record)) == [("clip", CHECKING)]
    assert files.pending(record)
    assert states(settle(files, env.coordinator, record)) == [("clip", CHANGED)]
    path.unlink()
    assert states(files.project(record)) == [("clip", CHECKING)]
    assert states(settle(files, env.coordinator, record)) == [("clip", MISSING)]
    # A settled outcome is not checked again while the file stays as it was.
    assert files.unchecked(record) == ()
    replace(path, MP4)
    assert listed(settle(files, env.coordinator, record)) == [str(path)]


def test_a_removed_job_directory_reports_its_files_missing(env):
    record = ready_job(env, "request", [("clip", "video/mp4", MP4)])
    directory = directory_of(env, record)
    for child in directory.iterdir():
        child.unlink()
    directory.rmdir()
    rows = settle(ResultFiles(), env.coordinator, record)
    assert states(rows) == [("clip", MISSING)] and listed(rows) == []


def downloading(env, request_id="partial"):
    """A job whose first result is saved while the second is still downloading."""
    store = env.store
    current = store.create(
        JobIntent(request_id, SCOPE, ORIGIN, "model", "model", "a" * 64, "b" * 64, "1.0")
    )
    for state in (JobState.SUBMITTING, JobState.REMOTE, JobState.SUCCEEDED):
        current = store.transition(
            request_id,
            expected_revision=current.revision,
            state=state,
            remote_job_id="remote-partial" if state == JobState.REMOTE else None,
        )
    manifest = (
        ResultAsset("first", "000-first.mp4", "video/mp4", len(MP4)),
        ResultAsset("second", "001-second.mp4", "video/mp4", len(MP4)),
    )
    current = store.set_results(request_id, manifest, expected_revision=current.revision)
    current = store.transition(
        request_id, expected_revision=current.revision, state=JobState.DOWNLOADING
    )
    (env.coordinator._results._directory(current) / "000-first.mp4").write_bytes(MP4)
    receipt = DownloadedResult("000-first.mp4", len(MP4), hashlib.sha256(MP4).hexdigest())
    return store.record_download(request_id, "first", receipt, expected_revision=current.revision)


def test_only_ready_jobs_have_their_files_checked(env):
    record = downloading(env)
    files = ResultFiles()
    files.watch("partial")
    assert states(files.project(record)) == [("first", NOT_READY), ("second", NOT_DOWNLOADED)]
    assert files.unchecked(record) == () and not files.pending(record)
    # A worker asked anyway rechecks the saved state and settles nothing.
    target = ("partial", "first", record.results[0].receipt.sha256)
    assert env.coordinator.result_files((target,), cancel=threading.Event()) == ((*target, None),)


def test_checks_stay_in_their_credential_scope(env):
    record = ready_job(env, "request", [("clip", "video/mp4", MP4)])
    target = ("request", "clip", record.results[0].receipt.sha256)
    other = JobStore(env.tmp_path / "jobs.sqlite3", JobScope(SCOPE.service, "account", "other"))
    with SDKAdapter(
        Credentials("key", "secret"),
        online=lambda: True,
        base_url=SCOPE.service,
        account_id="account",
        project_id="other",
        transport=httpx.MockTransport(lambda request: pytest.fail("No request expected")),
    ) as adapter:
        coordinator = JobCoordinator(
            adapter, other, result_root=env.results, result_downloader=FakeDownloader()
        )
        # Another project's store does not know the job, so nothing is verified.
        assert coordinator.result_files((target,), cancel=threading.Event()) == ((*target, None),)
    # A stale receipt digest or an unknown asset is never verified either.
    stale = ("request", "clip", hashlib.sha256(b"older").hexdigest())
    unknown = ("request", "other", target[2])
    assert env.coordinator.result_files((stale, unknown), cancel=threading.Event()) == (
        (*stale, None),
        (*unknown, None),
    )


def test_a_file_changing_while_it_is_checked_is_checked_again(env, monkeypatch):
    record = ready_job(env, "request", [("clip", "video/mp4", MP4)])
    path = directory_of(env, record) / record.results[0].asset.name
    verify = env.downloader.verify

    def racing(root, receipt):
        value = verify(root, receipt)
        replace(path, MP4)
        return value

    monkeypatch.setattr(env.downloader, "verify", racing)
    files = ResultFiles()
    rows = settle(files, env.coordinator, record)
    assert states(rows) == [("clip", CHECKING)] and files.pending(record)
    assert files.unchecked(record) == (("request", "clip", record.results[0].receipt.sha256),)


def test_a_failed_check_reports_unavailable_until_status_asks_again(env):
    record = ready_job(env, "request", [("clip", "video/mp4", MP4)])
    files = ResultFiles()
    files.watch("request")

    def failing(targets):
        return Done(lambda: (_ for _ in ()).throw(ResultError("inactive")))

    files.start(failing, files.unchecked(record))
    files.finish()
    assert states(files.project(record)) == [("clip", UNAVAILABLE)]
    # The pump does not retry it on its own; an explicit status read does.
    assert files.unchecked(record) == () and not files.pending(record)
    files.retry_unavailable(record)
    assert states(files.project(record)) == [("clip", CHECKING)]
    assert listed(settle(files, env.coordinator, record)) == [
        str(directory_of(env, record) / record.results[0].asset.name)
    ]


def test_one_bounded_check_runs_at_a_time(env):
    record = ready_job(env, "request", [("clip", "video/mp4", MP4)])
    files = ResultFiles()
    files.watch("request")
    queued = []

    class Waiting:
        def done(self):
            return False

    files.start(lambda targets: queued.append(targets) or Waiting(), files.unchecked(record))
    # In flight: pending, nothing new queued and the target is not unchecked.
    assert files.pending(record) and files.unchecked(record) == ()
    files.start(lambda targets: queued.append(targets) or Waiting(), (("x", "y", "a" * 64),))
    files.finish()
    assert len(queued) == 1
    many = tuple(("request", f"asset{index}", "a" * 64) for index in range(BATCH_LIMIT + 3))
    batches = []
    ResultFiles().start(lambda targets: batches.append(targets) or Waiting(), many)
    assert batches == [many[:BATCH_LIMIT]]


@pytest.mark.parametrize(
    "targets",
    [
        (),
        (("request", "clip"),),
        (("request", "clip", "not-a-digest"),),
        (("request", "", "a" * 64),),
        (("request", "clip", "a" * 64),) * (BATCH_LIMIT + 1),
        None,
    ],
)
def test_targets_are_validated_before_any_read(env, targets):
    with pytest.raises(ResultError, match="saved results"):
        env.coordinator.result_files(targets, cancel=threading.Event())


def test_a_canceled_check_stops_before_the_next_file(env):
    record = ready_job(env, "request", [("clip", "video/mp4", MP4)])
    cancel = threading.Event()
    cancel.set()
    with pytest.raises(PreviewCanceled):
        env.coordinator.result_files(
            (("request", "clip", record.results[0].receipt.sha256),), cancel=cancel
        )


def test_file_checks_run_on_the_preview_lane(env, monkeypatch):
    record = ready_job(env, "request", [("clip", "video/mp4", MP4)])
    target = ("request", "clip", record.results[0].receipt.sha256)
    threads, original = [], env.coordinator.result_files

    def recorded(*args, **kwargs):
        threads.append(threading.current_thread().name)
        return original(*args, **kwargs)

    monkeypatch.setattr(env.coordinator, "result_files", recorded)
    workers = JobWorkers(env.coordinator, workers=1)
    try:
        ((*echo, check),) = workers.result_files((target,)).result(timeout=5)
    finally:
        workers.deactivate()
        workers.shutdown()
    assert threads == ["ScenarioPreview"]
    assert tuple(echo) == target and check.state == VERIFIED
    assert check.path == str(directory_of(env, record) / record.results[0].asset.name)
    assert_offline(env)


def test_rows_never_carry_urls_or_remote_metadata(env):
    record = every_kind(env)
    rows = settle(ResultFiles(), env.coordinator, record)
    for row in rows:
        assert set(vars(row)) == {"asset_id", "file", "state"}
        assert "http" not in str(row.file) and "Signature" not in str(row.file)
    assert result_files.READY_STATES == frozenset(
        {JobState.READY, JobState.APPLYING, JobState.APPLY_FAILED, JobState.APPLIED}
    )


def succeeded(env, request_id, assets):
    """A finished job whose manifest is saved and whose files are not downloaded yet."""
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
    manifest = []
    for index, (asset_id, media_type, data) in enumerate(assets):
        record = {**asset_record(asset_id, media_type), "properties": {"size": len(data)}}
        env.assets[asset_id] = record
        env.downloader.files[f"{CDN}/{asset_id}?Signature=result-secret"] = data
        manifest.append(_asset(record, asset_id, f"{index:03d}-{asset_id}.bin"))
    return store.set_results(request_id, tuple(manifest), expected_revision=current.revision)


def seeded_rows(files, coordinator, record):
    """A status read: watch, seed what this session verified, then project."""
    files.watch(record.intent.request_id)
    files.seed(record, coordinator.verified_files(record.intent.request_id))
    return files.project(record)


def test_files_this_session_downloaded_are_listed_on_the_first_read(env):
    saved = succeeded(env, "fresh", [("clip", "video/mp4", MP4), ("sound", "audio/wav", WAV)])
    record = env.coordinator.download_results("fresh", expected_revision=saved.revision)
    assert record.state == JobState.READY
    files = ResultFiles()
    rows = seeded_rows(files, env.coordinator, record)
    directory = directory_of(env, record)
    # The download already hashed these bytes: no worker check is needed.
    assert states(rows) == [("clip", VERIFIED), ("sound", VERIFIED)]
    assert listed(rows) == [str(directory / item.asset.name) for item in record.results]
    assert not files.pending(record) and files.unchecked(record) == ()
    # The verification memory holds no URL, only receipts and local identities.
    assert "Signature" not in repr(env.coordinator.verified_files("fresh"))


def test_files_an_automatic_import_verified_are_listed_on_the_first_read(env):
    record = ready_job(env, "imported", [("still", "image/png", png(8, 8))])
    env.coordinator.verify_results("imported", expected_revision=record.revision)
    rows = seeded_rows(ResultFiles(), env.coordinator, record)
    assert states(rows) == [("still", VERIFIED)]
    assert listed(rows) == [str(directory_of(env, record) / record.results[0].asset.name)]


def test_a_restarted_session_does_not_reuse_another_session_verification(env):
    saved = succeeded(env, "fresh", [("clip", "video/mp4", MP4)])
    record = env.coordinator.download_results("fresh", expected_revision=saved.revision)
    store = JobStore(env.tmp_path / "jobs.sqlite3", SCOPE)
    with SDKAdapter(
        Credentials("key", "secret"),
        online=lambda: True,
        base_url=SCOPE.service,
        account_id=SCOPE.account_id,
        project_id=SCOPE.project_id,
        transport=httpx.MockTransport(lambda request: pytest.fail("No request expected")),
    ) as adapter:
        coordinator = JobCoordinator(
            adapter, store, result_root=env.results, result_downloader=FakeDownloader()
        )
        assert coordinator.verified_files("fresh") == ()
        files = ResultFiles()
        assert states(seeded_rows(files, coordinator, record)) == [("clip", CHECKING)]
        assert listed(settle(files, coordinator, record)) == [
            str(directory_of(env, record) / record.results[0].asset.name)
        ]


def test_a_file_changed_after_this_session_verified_it_is_checked_again(env):
    saved = succeeded(env, "fresh", [("clip", "video/mp4", MP4)])
    record = env.coordinator.download_results("fresh", expected_revision=saved.revision)
    path = directory_of(env, record) / record.results[0].asset.name
    files = ResultFiles()
    assert listed(seeded_rows(files, env.coordinator, record)) == [str(path)]
    replace(path, MP4[::-1])
    # The same verification is never applied again to the changed file.
    assert states(seeded_rows(files, env.coordinator, record)) == [("clip", CHECKING)]
    assert files.unchecked(record) == (("fresh", "clip", record.results[0].receipt.sha256),)
    assert states(settle(files, env.coordinator, record)) == [("clip", CHANGED)]
    assert states(seeded_rows(files, env.coordinator, record)) == [("clip", CHANGED)]


def test_a_verification_of_another_receipt_is_not_used(env):
    record = ready_job(env, "request", [("clip", "video/mp4", MP4)])
    path = str(directory_of(env, record) / record.results[0].asset.name)
    other = result_files.FileCheck(
        hashlib.sha256(b"older").hexdigest(), VERIFIED, path, result_files.file_stamp(path)
    )
    files = ResultFiles()
    files.watch("request")
    files.seed(record, (("clip", other), ("unknown", other)))
    assert states(files.project(record)) == [("clip", CHECKING)]
