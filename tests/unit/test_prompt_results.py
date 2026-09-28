# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Recover full prompt text using SDK reads, without submissions or partial previews."""

import hashlib
import json
from dataclasses import replace

import httpx
import pytest

from scenario.core.api.sdk_adapter import Credentials, SDKAdapter
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
        "type": {"kind": "text"},
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
        return httpx.Response(200, json={"asset": asset})

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
        {"type": {"kind": "image"}},
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
