# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Offline checks for the active prototype's signed content downloads."""

import io
from unittest.mock import Mock

import pytest
from fakes import FakeTransport

from scenario.core.api import assets, llm
from scenario.core.api.client import ScenarioClient
from scenario.core.api.errors import ScenarioError


@pytest.mark.parametrize(
    "url",
    [
        "http://cdn.example/a.txt",
        "ftp://cdn.example/a.txt",
        "file:///tmp/a.txt",
        "https:///a.txt",
        "https://[broken/a.txt?signature=secret",
        "https://cdn.example:invalid/a.txt",
        "https://user:password@cdn.example/a.txt",
        "\nhttps://cdn.example/a.txt",
        None,
    ],
)
def test_invalid_destination_fails_before_network_files_or_retries(url, tmp_path, monkeypatch):
    network = Mock(side_effect=AssertionError("network must not be called"))
    monkeypatch.setattr(assets.urllib.request, "urlopen", network)
    transport, sleep = Mock(), Mock()
    with pytest.raises(ScenarioError, match="refusing non-https asset URL"):
        assets.fetch_url_text(url)
    with pytest.raises(ScenarioError, match="refusing non-https asset URL"):
        assets.download_file(url, tmp_path / "new" / "asset.png", transport=transport, sleep=sleep)
    network.assert_not_called()
    transport.request.assert_not_called()
    sleep.assert_not_called()
    assert not list(tmp_path.iterdir())


class Response(io.BytesIO):
    def __init__(self, body):
        super().__init__(body)
        self.requested_sizes = []
        self.bytes_read = 0

    def read(self, size=-1):
        assert size > 0, "unbounded reads are forbidden"
        self.requested_sizes.append(size)
        data = super().read(size)
        self.bytes_read += len(data)
        return data


@pytest.mark.parametrize("size", [0, 512, 1024, 1025, 4096])
def test_text_limit_including_exact_boundary(size, monkeypatch):
    response = Response(b"a" * size)
    network = Mock(return_value=response)
    monkeypatch.setattr(assets.urllib.request, "urlopen", network)
    url = "https://cdn.example/a.txt?signature=private#fragment"
    if size > 1024:
        with pytest.raises(ScenarioError, match="larger than 1024 bytes") as caught:
            assets.fetch_url_text(url, max_bytes=1024)
        assert "https://cdn.example/a.txt" in str(caught.value)
        assert "private" not in str(caught.value)
        assert "fragment" not in str(caught.value)
    else:
        assert assets.fetch_url_text(url, max_bytes=1024) == "a" * size
    assert response.closed
    assert response.bytes_read == min(size, 1025)
    request = network.call_args.args[0]
    assert request.full_url == url
    assert request.get_header("User-agent") == assets.user_agent_string()
    assert request.get_header("Authorization") is None


def test_text_decodes_after_all_chunks_and_replaces_invalid_utf8(monkeypatch):
    body = b"a" * (64 * 1024 - 1) + "é".encode() + b"\xff"
    response = Response(body)
    monkeypatch.setattr(assets.urllib.request, "urlopen", lambda *a, **k: response)
    assert assets.fetch_url_text("https://cdn.example/a.txt") == "a" * (64 * 1024 - 1) + "é�"
    assert max(response.requested_sizes) == 64 * 1024


@pytest.mark.parametrize("max_bytes", [0, -1, True, 1.5, None])
def test_invalid_text_limit_does_not_open_connection(max_bytes, monkeypatch):
    network = Mock()
    monkeypatch.setattr(assets.urllib.request, "urlopen", network)
    with pytest.raises(ValueError, match="positive integer"):
        assets.fetch_url_text("https://cdn.example/a.txt", max_bytes=max_bytes)
    network.assert_not_called()


@pytest.mark.parametrize("status", [404, 503])
def test_download_error_omits_signed_query_and_fragment(status, tmp_path):
    transport = FakeTransport().queue(status, b"")
    url = "https://cdn.example/a.png?X-Amz-Signature=private#fragment"
    with pytest.raises(ScenarioError) as caught:
        assets.download_file(url, tmp_path / "a.png", transport=transport, retries=0)
    assert "https://cdn.example/a.png" in str(caught.value)
    assert "X-Amz-Signature" not in str(caught.value)
    assert "private" not in str(caught.value)
    assert "fragment" not in str(caught.value)
    assert transport.calls[0]["url"] == url


@pytest.mark.parametrize("oversized", [False, True])
def test_text_asset_falls_back_to_preview_on_refused_or_oversized_content(oversized, monkeypatch):
    url = "https://cdn.example/a.txt" if oversized else "http://cdn.example/a.txt"
    transport = (
        FakeTransport()
        .queue(
            200,
            {
                "job": {
                    "jobId": "job_text",
                    "status": "success",
                    "metadata": {"assetIds": ["asset_text"]},
                }
            },
        )
        .queue(
            200,
            {
                "asset": {
                    "url": url,
                    "metadata": {"preview": "short answer", "hasFullPreview": False},
                }
            },
        )
    )
    response = Response(b"a" * 1025)
    monkeypatch.setattr(assets.urllib.request, "urlopen", lambda *a, **k: response)
    if oversized:
        original = assets.fetch_url_text
        monkeypatch.setattr(assets, "fetch_url_text", lambda url: original(url, max_bytes=1024))
    client = ScenarioClient("synthetic", "synthetic", transport=transport)
    assert llm.run_text(client, "synthetic instruction") == "short answer"
