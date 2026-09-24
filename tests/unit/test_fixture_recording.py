# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Record through the real pinned SDK with synthetic transport and local files."""

import datetime as dt
import json
from pathlib import Path
from types import SimpleNamespace

import httpx
import pytest

from scenario.core.api.sdk_adapter import SDKAdapter
from tools import record_fixtures as recorder


@pytest.fixture
def recording(tmp_path, monkeypatch):
    monkeypatch.setattr(recorder, "FIXTURES", tmp_path)
    monkeypatch.setattr(recorder, "MODEL_IDS", ["model_fixture"])
    monkeypatch.setattr(
        recorder,
        "live_settings",
        lambda: SimpleNamespace(
            credentials=SimpleNamespace(key="fixture-key", secret="fixture-secret"),
            project_id="fixture-project",
        ),
    )
    monkeypatch.setenv("SCENARIO_SDK_API_KEY", "ambient-key")
    monkeypatch.setenv("SCENARIO_SDK_API_SECRET", "ambient-secret")
    monkeypatch.setenv("SCENARIO_BASE_URL", "https://ambient.invalid")
    requests, clients = [], []
    model = {"id": "model_fixture", "ownerId": "synthetic-owner", "futureField": True}
    page = {"models": [model], "nextPaginationToken": "opaque+/= cursor", "futurePage": 42}

    def install(*, fail=None):
        def handle(request):
            requests.append(request)
            assert request.method == "GET"
            assert request.url.params["projectId"] == "fixture-project"
            assert request.headers["Authorization"] == "Basic Zml4dHVyZS1rZXk6Zml4dHVyZS1zZWNyZXQ="
            if fail == request.url.path:
                return httpx.Response(500, json={"error": "private-response"})
            return httpx.Response(
                200, json=page if request.url.path == "/v1/models" else {"model": model}
            )

        def create(*args, **kwargs):
            client = SDKAdapter(
                *args,
                **kwargs,
                base_url="https://service.example.invalid/v1",
                transport=httpx.MockTransport(handle),
            )
            clients.append(client)
            return client

        monkeypatch.setattr(recorder, "SDKAdapter", create)

    install()
    return SimpleNamespace(
        root=tmp_path, model=model, page=page, requests=requests, clients=clients, install=install
    )


def test_records_exact_selected_reads_scrubs_and_writes_truthful_provenance(recording, capsys):
    assert recorder.main([]) == 0
    assert [r.url.path for r in recording.requests] == ["/v1/models/model_fixture", "/v1/models"]
    assert dict(recording.requests[-1].url.params) == {
        "projectId": "fixture-project",
        "privacy": "public",
        "pageSize": "5",
    }
    assert json.loads((recording.root / "models/model_fixture.json").read_text()) == {
        "model": recorder.scrub(recording.model)
    }
    assert json.loads((recording.root / "models_list_page1.json").read_text()) == recorder.scrub(
        recording.page
    )
    provenance = json.loads((recording.root / "PROVENANCE.json").read_text())
    assert provenance["recordedAt"] == dt.datetime.now(dt.UTC).date().isoformat()
    assert provenance["sdkVersion"] == "2.1.0"
    assert provenance["files"] == {
        "models/model_fixture.json": "GET /models/model_fixture",
        "models_list_page1.json": "GET /models?privacy=public&pageSize=5",
    }
    assert "account" not in provenance
    assert not list(recording.root.glob(".recording-*"))
    assert all(client._closed for client in recording.clients)
    text = capsys.readouterr().out + json.dumps(provenance)
    assert "synthetic-owner" not in text and "fixture-project" not in text


@pytest.mark.parametrize("endpoint", ["/v1/models/model_fixture", "/v1/models"])
def test_failed_read_makes_one_attempt_and_preserves_previous_files(recording, endpoint, capsys):
    (recording.root / "models").mkdir()
    old = {
        "models/model_fixture.json": b"old model",
        "models_list_page1.json": b"old page",
        "PROVENANCE.json": b"old provenance",
    }
    for relative, content in old.items():
        (recording.root / relative).write_bytes(content)
    recording.install(fail=endpoint)
    assert recorder.main([]) == 1
    assert sum(r.url.path == endpoint for r in recording.requests) == 1
    assert {relative: (recording.root / relative).read_bytes() for relative in old} == old
    assert all(client._closed for client in recording.clients)
    assert "private-response" not in capsys.readouterr().err


def test_wrong_model_identity_fails_before_writes(recording):
    recording.model["id"] = "model_wrong"
    assert recorder.main([]) == 1
    assert list(recording.root.iterdir()) == []


def test_failed_publication_removes_old_provenance_and_cleans_staging(recording, monkeypatch):
    (recording.root / "PROVENANCE.json").write_text("old provenance")
    replace = recorder.os.replace

    def fail_page(source, destination):
        if Path(destination).name == "models_list_page1.json":
            raise OSError("private-path")
        return replace(source, destination)

    monkeypatch.setattr(recorder.os, "replace", fail_page)
    assert recorder.main([]) == 1
    assert not (recording.root / "PROVENANCE.json").exists()
    assert not list(recording.root.glob(".recording-*"))
    assert (
        json.loads((recording.root / "models/model_fixture.json").read_text())["model"]["ownerId"]
        == recorder.PLACEHOLDERS["ownerId"]
    )


def test_model_inventory_matches_all_committed_model_records():
    root = Path(__file__).resolve().parents[1] / "fixtures/models"
    assert sorted(recorder.MODEL_IDS) == sorted(path.stem for path in root.glob("*.json"))
    assert len(set(recorder.MODEL_IDS)) == len(recorder.MODEL_IDS)


def test_symlinked_output_is_refused_before_network(recording):
    (recording.root / "PROVENANCE.json").symlink_to(recording.root / "absent")
    assert recorder.main([]) == 1
    assert recording.requests == []
