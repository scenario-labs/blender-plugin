# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
import base64

import pytest
from fakes import FakeTransport

from scenario.core.api.client import ScenarioClient
from scenario.core.api.errors import NetworkError, ScenarioError


def make(transport, **kw):
    sleeps = []
    client = ScenarioClient("api_key", "secret", transport=transport, sleep=sleeps.append, **kw)
    return client, sleeps


def test_get_sends_basic_auth_and_query():
    t = FakeTransport().queue(200, {"models": []})
    client, _ = make(t)
    out = client.get("/models", query={"pageSize": 1, "privacy": "public"})
    assert out == {"models": []}
    call = t.calls[0]
    expected = "Basic " + base64.b64encode(b"api_key:secret").decode()
    assert call["headers"]["Authorization"] == expected
    assert call["method"] == "GET"
    assert call["url"] == "https://api.cloud.scenario.com/v1/models?pageSize=1&privacy=public"
    assert call["body"] is None


def test_post_sends_json_body_and_content_type():
    t = FakeTransport().queue(200, {"job": {"jobId": "job_1"}})
    client, _ = make(t)
    client.post("/generate/custom/model_x", json_body={"prompt": "hi", "numOutputs": 1})
    call = t.calls[0]
    assert call["headers"]["Content-Type"] == "application/json"
    assert t.last_json() == {"prompt": "hi", "numOutputs": 1}


def test_dry_run_status_269_is_success():
    t = FakeTransport().queue(269, {"creativeUnitsCost": 7.25})
    client, _ = make(t)
    assert (
        client.post("/generate/custom/m", query={"dryRun": "true"}, json_body={})[
            "creativeUnitsCost"
        ]
        == 7.25
    )
    assert t.calls[0]["url"].endswith("?dryRun=true")


def test_error_maps_reason_and_trace_id():
    t = FakeTransport().queue(400, {"reason": "Input prompt is required", "trace_id": "tr_1"})
    client, _ = make(t)
    with pytest.raises(ScenarioError) as exc:
        client.post("/generate/custom/m", json_body={})
    assert exc.value.status == 400
    assert exc.value.reason == "Input prompt is required"
    assert exc.value.trace_id == "tr_1"
    assert exc.value.path == "/generate/custom/m"


def test_403_message_field_is_used_as_reason():
    t = FakeTransport().queue(403, {"message": "API Keys cannot access protected resources"})
    client, _ = make(t)
    with pytest.raises(ScenarioError) as exc:
        client.get("/me")
    assert "protected resources" in exc.value.reason


def test_retries_on_503_then_succeeds():
    t = FakeTransport().queue(503, {"message": "busy"}).queue(200, {"ok": True})
    client, sleeps = make(t)
    assert client.get("/models") == {"ok": True}
    assert len(t.calls) == 2
    assert sleeps == [1.0]


def test_429_uses_remaining_seconds_capped():
    t = (
        FakeTransport()
        .queue(429, {"reason": "cooldown", "remainingSeconds": 900})
        .queue(200, {"ok": True})
    )
    client, sleeps = make(t)
    client.get("/models")
    assert sleeps == [30.0]


def test_network_error_after_retries():
    t = FakeTransport()
    t.raise_network = 10
    client, sleeps = make(t, max_retries=2)
    with pytest.raises(NetworkError):
        client.get("/models")
    assert len(t.calls) == 3
    assert sleeps == [1.0, 2.0]


def test_non_json_body_becomes_reason_text():
    t = FakeTransport().queue(502, b"<html>Bad gateway</html>")
    client, _ = make(t, max_retries=0)
    with pytest.raises(ScenarioError) as exc:
        client.get("/models")
    assert "Bad gateway" in exc.value.reason


# -- one version source (release-please owns scenario/__init__.py) ----------


def test_default_user_agent_carries_the_package_version():
    from scenario import __version__

    t = FakeTransport().queue(200, {"models": []})
    client, _ = make(t)
    client.get("/models")
    assert t.calls[0]["headers"]["User-Agent"] == f"ScenarioBlender/{__version__}"


def test_asset_helpers_send_the_same_user_agent(monkeypatch, tmp_path):
    import urllib.request

    from scenario import __version__
    from scenario.core.api import assets

    seen = []

    class FakeResponse:
        def __init__(self, payload):
            self._payload = payload

        def getheader(self, name, default=None):
            return default

        def read(self, *args):
            out, self._payload = self._payload, b""
            return out

        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

    def fake_urlopen(req, timeout=None):
        seen.append(req.get_header("User-agent"))
        return FakeResponse(b"payload")

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
    assets.fetch_url_text("https://cdn.example/asset.txt")
    assets.download_file("https://cdn.example/asset.bin", tmp_path / "asset.bin")
    assert seen == [f"ScenarioBlender/{__version__}"] * 2


def test_no_version_literal_is_left_in_the_api_sources():
    import pathlib
    import re

    root = pathlib.Path(__file__).resolve().parents[2] / "scenario" / "core" / "api"
    for name in ("client.py", "assets.py"):
        text = (root / name).read_text()
        assert not re.search(r"ScenarioBlender/\d", text), f"{name} carries a hard-coded version"
        assert '"ScenarioBlender"' not in text, f"{name} sends a User-Agent without a version"


@pytest.mark.parametrize("project", [None, "", "  ", " selected-project "])
def test_optional_project_scopes_service_requests_without_changing_payload(project):
    import json
    from urllib.parse import parse_qs, urlsplit

    t = FakeTransport()
    selected = (project or "").strip() or None
    client, _ = make(t, project_id=project)
    for method, path, query, body in [
        ("GET", "/models", {"pageSize": 5}, None),
        ("GET", "/models/model_x", {}, None),
        ("POST", "/generate/custom/model_x", {"dryRun": "true"}, {"prompt": "fixture"}),
        ("POST", "/generate/custom/model_x", {}, {"prompt": "fixture"}),
        ("GET", "/jobs/job_x", {}, None),
        ("GET", "/assets/asset_x", {}, None),
        ("POST", "/assets", {}, {"image": "fixture"}),
        ("POST", "/uploads", {}, {"fileName": "fixture"}),
        ("POST", "/uploads/upload_x/action", {}, {"action": "complete"}),
    ]:
        t.queue(200, {})
        original_query = dict(query)
        client.request(method, path, query=query, json_body=body)
        call = t.calls[-1]
        expected = {k: [str(v)] for k, v in query.items()}
        if selected:
            expected["projectId"] = [selected]
        assert parse_qs(urlsplit(call["url"]).query) == expected
        assert query == original_query
        assert (json.loads(call["body"]) if body is not None else None) == body


def test_client_project_scope_is_not_overridden_by_call_query():
    from urllib.parse import parse_qs, urlsplit

    client, _ = make(FakeTransport(), project_id="selected")
    assert parse_qs(urlsplit(client.url("/jobs/job_x", {"projectId": "other"})).query) == {
        "projectId": ["selected"]
    }
