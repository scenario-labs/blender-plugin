# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Recover full prompt text using SDK reads, without submissions or partial previews."""

import hashlib
import json
from dataclasses import replace

import httpx
import pytest

from scenario.core.api.sdk_adapter import AdapterError, Credentials, SDKAdapter
from scenario.core.jobs.coordinator import JobCoordinator
from scenario.core.jobs.results import MAX_PROMPT_BYTES, ResultError
from scenario.core.jobs.store import (
    JobIntent,
    JobOrigin,
    JobScope,
    JobState,
    JobStore,
    StoreConflict,
)
from scenario.core.jobs.transfers import DownloadedResult, ResultDownloader, StoragePolicy


@pytest.fixture
def setup(tmp_path):
    scope = JobScope("https://service.example.invalid/v1", "account", "project")
    store = JobStore(tmp_path / "jobs.sqlite3", scope)
    intent = JobIntent(
        "request",
        scope,
        JobOrigin("file", "scene", "revision"),
        "prompt",
        "prompt",
        "a" * 64,
        "b" * 64,
        "1.25",
    )
    current = store.create(intent)
    for state in (JobState.SUBMITTING, JobState.REMOTE, JobState.SUCCEEDED):
        current = store.transition(
            "request",
            expected_revision=current.revision,
            state=state,
            remote_job_id="remote" if state == JobState.REMOTE else None,
        )
    job = {
        "jobId": "remote",
        "status": "success",
        "jobType": "generate-prompt",
        "metadata": {"output": {"prompts": ["A copper teapot.\nSoft light."]}},
    }
    asset = {
        "id": "asset_text",
        "status": "success",
        "kind": "text",
        "mimeType": "text/plain",
        "properties": {"hasFullPreview": True, "preview": "Full prompt"},
    }
    calls = []
    after_request = []

    def handler(request):
        assert request.method == "GET"
        assert dict(request.url.params) == {"projectId": "project"}
        calls.append(request.url.path)
        if after_request:
            after_request.pop()()
        if request.url.path == "/v1/jobs/remote":
            return httpx.Response(200, content=json.dumps({"job": job}).encode())
        assert request.url.path == "/v1/assets/asset_text"
        return httpx.Response(200, content=json.dumps({"asset": asset}).encode())

    adapter = SDKAdapter(
        Credentials("key", "secret"),
        base_url=scope.service,
        account_id=scope.account_id,
        project_id=scope.project_id,
        online=lambda: True,
        transport=httpx.MockTransport(handler),
    )
    root = tmp_path / "results"
    root.mkdir()
    downloader = ResultDownloader(
        StoragePolicy(frozenset({"storage.example.invalid"})), online_access=lambda: True
    )
    coordinator = JobCoordinator(adapter, store, result_downloader=downloader, result_root=root)
    yield coordinator, store, current, job, asset, calls, downloader, root, after_request, adapter
    adapter.close()


def read(fixture):
    coordinator, _, record, *_ = fixture
    return coordinator.read_prompt_results("request", expected_revision=record.revision)


def test_restart_recovers_verbatim_text_and_never_persists_it(setup, tmp_path):
    _, store, record, job, _, calls, _, _, _, adapter = setup
    restarted = JobCoordinator(adapter, JobStore(tmp_path / "jobs.sqlite3", store.scope))
    result = restarted.read_prompt_results("request", expected_revision=record.revision)
    assert result.prompts == tuple(job["metadata"]["output"]["prompts"])
    assert "teapot" not in repr(result)
    assert store.get("request") == record
    assert calls == ["/v1/jobs/remote"]
    assert b"teapot" not in (tmp_path / "jobs.sqlite3").read_bytes()


@pytest.mark.parametrize(
    "prompts",
    [
        [],
        [""],
        [" "],
        [None],
        [{"text": "bad"}],
        ["x"] * 6,
        ["x" * (MAX_PROMPT_BYTES + 1)],
        ["x\x00y"],
        ["\ud800"],
    ],
)
def test_malformed_prompt_results_are_rejected(setup, prompts):
    setup[3]["metadata"]["output"]["prompts"] = prompts
    with pytest.raises(ResultError):
        read(setup)
    assert len(setup[5]) == 1


@pytest.mark.parametrize(
    "changed",
    [
        {"jobId": "other"},
        {"status": "in-progress"},
        {"jobType": []},
        {"jobType": "custom"},
        {"metadata": None},
    ],
)
def test_job_identity_status_and_type_are_authoritative(setup, changed):
    setup[3].update(changed)
    with pytest.raises(ResultError):
        read(setup)


def test_full_asset_preview_is_allowed_only_when_explicitly_complete(setup):
    setup[3]["metadata"]["output"]["prompts"] = [" asset_text "]
    assert read(setup).prompts == ("Full prompt",)
    assert setup[5] == ["/v1/jobs/remote", "/v1/assets/asset_text"]


@pytest.mark.parametrize(
    "changed",
    [
        {"id": "other"},
        {"status": "pending"},
        {"kind": "image"},
        {"mimeType": "application/json"},
        {"properties": {"hasFullPreview": True, "preview": "asset_loop"}},
        {"properties": {"hasFullPreview": 1, "preview": "truncated"}},
    ],
)
def test_asset_metadata_cannot_pass_as_complete_text(setup, changed):
    setup[3]["metadata"]["output"]["prompts"] = ["asset_text"]
    setup[4].update(changed)
    with pytest.raises(ResultError):
        read(setup)
    assert not list(setup[7].iterdir())


@pytest.mark.parametrize("failure", [None, "download", "decode", "changed"])
def test_partial_preview_downloads_complete_bounded_text_and_cleans_up(setup, monkeypatch, failure):
    setup[3]["metadata"]["output"]["prompts"] = ["asset_text"]
    data = b"Full text\nfrom storage" if failure != "decode" else b"\xff"
    setup[4].update(
        url="https://storage.example.invalid/text?private=fixture",
        properties={"hasFullPreview": False, "preview": "truncated", "size": len(data)},
    )
    directories = []

    def download(url, *, root, name, expected_size, max_bytes):
        directories.append(root)
        assert max_bytes == MAX_PROMPT_BYTES and expected_size == len(data)
        if failure == "download":
            raise RuntimeError("private signed URL")
        (root / name).write_bytes(data)
        return DownloadedResult(name, len(data), hashlib.sha256(data).hexdigest())

    monkeypatch.setattr(setup[6], "download", download)
    if failure == "changed":

        def change(root, receipt):
            path = root / receipt.name
            path.write_bytes(b"X" * len(data))
            return path

        monkeypatch.setattr(setup[6], "verify", change)
    if failure:
        with pytest.raises(ResultError) as error:
            read(setup)
        assert "private" not in str(error.value)
    else:
        assert read(setup).prompts == (data.decode(),)
    assert directories and all(not path.exists() for path in directories)
    assert not list(setup[7].iterdir())
    assert setup[1].get("request") == setup[2]


def test_wrong_revision_and_context_retirement_reject_results(setup):
    with pytest.raises(StoreConflict):
        setup[0].read_prompt_results("request", expected_revision=0)
    assert not setup[5]
    setup[8].append(setup[0].deactivate)
    with pytest.raises(Exception, match="inactive"):
        read(setup)
    assert len(setup[5]) == 1


def test_non_prompt_jobs_are_rejected_before_service_access(setup, tmp_path):
    other = JobStore(tmp_path / "other.sqlite3", setup[1].scope)
    record = other.create(replace(setup[2].intent, operation="model"))
    for state in (JobState.SUBMITTING, JobState.REMOTE, JobState.SUCCEEDED):
        record = other.transition(
            "request",
            expected_revision=record.revision,
            state=state,
            remote_job_id="remote" if state == JobState.REMOTE else None,
        )
    with pytest.raises(ResultError, match="Prompt Spark"):
        JobCoordinator(setup[-1], other).read_prompt_results(
            "request", expected_revision=record.revision
        )
    assert not setup[5]


def test_translation_recovers_its_own_job_output_contract(setup, tmp_path):
    other = JobStore(tmp_path / "translation.sqlite3", setup[1].scope)
    record = other.create(replace(setup[2].intent, operation="translate", target_id="translate"))
    for state in (JobState.SUBMITTING, JobState.REMOTE, JobState.SUCCEEDED):
        record = other.transition(
            "request",
            expected_revision=record.revision,
            state=state,
            remote_job_id="remote" if state == JobState.REMOTE else None,
        )
    setup[3].update(jobType="translate", metadata={"output": {"translation": "A copper teapot"}})
    owner = JobCoordinator(setup[-1], other)
    assert owner.read_prompt_results("request", expected_revision=record.revision).prompts == (
        "A copper teapot",
    )
    setup[3]["jobType"] = "generate-prompt"
    with pytest.raises(ResultError):
        owner.read_prompt_results("request", expected_revision=record.revision)


@pytest.fixture
def model(setup, tmp_path):
    """Exercise model text with the same real SDK transport and scoped storage."""
    store = JobStore(tmp_path / "model.sqlite3", setup[1].scope)
    record = store.create(replace(setup[2].intent, operation="model", target_id="model_text"))
    for state in (JobState.SUBMITTING, JobState.REMOTE, JobState.SUCCEEDED):
        record = store.transition(
            "request",
            expected_revision=record.revision,
            state=state,
            remote_job_id="remote" if state == JobState.REMOTE else None,
        )
    setup[3].update(jobType="custom", metadata={"assetIds": ["asset_text"]})
    owner = JobCoordinator(setup[-1], store, result_downloader=setup[6], result_root=setup[7])
    return owner, store, record, setup


def model_text(model):
    owner, _, record, _ = model
    return owner.read_model_text(
        "request", expected_revision=record.revision, asset_id="asset_text"
    )


def test_model_text_survives_restart_without_mutating_or_persisting_output(model, tmp_path):
    owner, store, record, setup = model
    restarted = JobCoordinator(setup[-1], JobStore(tmp_path / "model.sqlite3", store.scope))
    result = restarted.read_model_text(
        "request", expected_revision=record.revision, asset_id="asset_text"
    )
    assert result.text == "Full prompt" and result.asset_id == "asset_text"
    assert result.record == record and store.get("request") == record
    assert "Full prompt" not in repr(result)
    assert b"Full prompt" not in (tmp_path / "model.sqlite3").read_bytes()
    assert setup[5] == ["/v1/jobs/remote", "/v1/assets/asset_text"]


@pytest.mark.parametrize(
    "identifiers", [None, [], ["other"], ["asset_text"] * 2, [None], [{}], ["x"] * 129]
)
def test_model_text_rejects_missing_duplicate_or_mismatched_remote_outputs(model, identifiers):
    model[3][3]["metadata"]["assetIds"] = identifiers
    with pytest.raises(ResultError):
        model_text(model)
    assert model[3][5] == ["/v1/jobs/remote"]


@pytest.mark.parametrize("changed", [{"jobId": "other"}, {"status": "pending"}, {"metadata": None}])
def test_model_text_rechecks_successful_remote_identity(model, changed):
    model[3][3].update(changed)
    with pytest.raises(ResultError):
        model_text(model)
    assert model[3][5] == ["/v1/jobs/remote"]


def test_model_text_requires_saved_model_intent_and_current_revision(model, setup):
    with pytest.raises(ResultError, match="model job"):
        setup[0].read_model_text(
            "request", expected_revision=setup[2].revision, asset_id="asset_text"
        )
    with pytest.raises(StoreConflict):
        model[0].read_model_text("request", expected_revision=0, asset_id="asset_text")
    with pytest.raises(ResultError):
        model[0].read_model_text("request", expected_revision=model[2].revision, asset_id={})
    assert not setup[5]


@pytest.mark.parametrize(
    "changed",
    [
        {"kind": "image", "type": {"kind": "text"}},
        {"kind": None, "type": {"kind": "text"}},
        {"mimeType": "application/json"},
        {"id": "other"},
        {"status": "pending"},
        {"properties": {"hasFullPreview": True, "preview": ""}},
        {"properties": {"hasFullPreview": True, "preview": "x" * (MAX_PROMPT_BYTES + 1)}},
    ],
)
def test_model_text_rejects_incompatible_assets_without_partial_text(model, changed):
    model[3][4].update(changed)
    with pytest.raises(ResultError):
        model_text(model)
    assert model[1].get("request") == model[2]


@pytest.mark.parametrize("failure", [None, "download", "decode", "changed"])
def test_model_text_reads_full_body_never_partial_preview_and_cleans_up(
    model, monkeypatch, failure
):
    setup = model[3]
    data = b'[ {"name": "Complete element"} ]' if failure != "decode" else b"\xff"
    setup[4].update(
        url="https://storage.example.invalid/plan?private=fixture",
        properties={"hasFullPreview": False, "preview": "truncated", "size": float(len(data))},
    )
    directories = []

    def download(url, *, root, name, expected_size, max_bytes):
        directories.append(root)
        assert expected_size == len(data) and max_bytes == MAX_PROMPT_BYTES
        if failure == "download":
            raise RuntimeError("private transfer detail")
        (root / name).write_bytes(data)
        return DownloadedResult(name, len(data), hashlib.sha256(data).hexdigest())

    monkeypatch.setattr(setup[6], "download", download)
    if failure == "changed":

        def change(root, receipt):
            path = root / receipt.name
            path.write_bytes(b"X" * len(data))
            return path

        monkeypatch.setattr(setup[6], "verify", change)
    if failure:
        with pytest.raises(ResultError) as error:
            model_text(model)
        assert "private" not in str(error.value)
    else:
        assert model_text(model).text == data.decode()
    assert directories and all(not path.exists() for path in directories)
    assert not list(setup[7].iterdir())
    assert model[1].get("request") == model[2]


def test_model_text_checks_manifest_and_races_before_delivery(model):
    from scenario.core.jobs.store import ResultAsset

    owner, store, record, setup = model
    current = store.set_results(
        "request",
        (ResultAsset("other", "other.txt", "text/plain", 1),),
        expected_revision=record.revision,
    )
    with pytest.raises(ResultError):
        owner.read_model_text("request", expected_revision=current.revision, asset_id="asset_text")
    assert setup[5] == ["/v1/jobs/remote"]


def test_model_text_rejects_context_retirement_during_network_read(model):
    model[3][8].append(model[0].deactivate)
    with pytest.raises(Exception, match="inactive"):
        model_text(model)
    assert model[3][5] == ["/v1/jobs/remote"]


def test_model_text_rejects_revision_changed_during_network_read(model):
    from scenario.core.jobs.store import ResultAsset

    owner, store, record, setup = model
    setup[8].append(
        lambda: store.set_results(
            "request",
            (ResultAsset("asset_text", "text.txt", "text/plain", 1),),
            expected_revision=record.revision,
        )
    )
    with pytest.raises(StoreConflict):
        model_text(model)


def test_model_text_runs_on_shared_worker_queue(model):
    import threading

    from scenario.core.jobs.workers import JobWorkers

    owner, _, record, setup = model
    threads = []
    setup[8].append(lambda: threads.append(threading.current_thread()))
    workers = JobWorkers(owner)
    try:
        task = workers.read_model_text(
            "request", expected_revision=record.revision, asset_id="asset_text"
        )
        assert task.result(5).text == "Full prompt"
        assert threads and threads[0] is not threading.main_thread()
    finally:
        workers.shutdown()


@pytest.mark.parametrize(
    "size", [True, 0, -1, 1.5, float("inf"), float("nan"), "10", MAX_PROMPT_BYTES + 1]
)
def test_model_text_rejects_unbounded_or_invalid_full_body_size(model, size):
    model[3][4]["properties"] = {"hasFullPreview": False, "preview": "partial", "size": size}
    with pytest.raises((ResultError, AdapterError)):
        model_text(model)
    assert not list(model[3][7].iterdir())


def test_model_text_can_recover_after_failed_binary_download(model):
    from scenario.core.jobs.store import ResultAsset

    owner, store, record, setup = model
    record = store.set_results(
        "request",
        (ResultAsset("asset_text", "text.txt", "text/plain", 11),),
        expected_revision=record.revision,
    )
    for state in (JobState.DOWNLOADING, JobState.DOWNLOAD_FAILED):
        record = store.transition("request", expected_revision=record.revision, state=state)
    result = owner.read_model_text(
        "request", expected_revision=record.revision, asset_id="asset_text"
    )
    assert result.text == "Full prompt"
    assert result.record == record and store.get("request") == record
