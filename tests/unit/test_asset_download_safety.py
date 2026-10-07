# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Offline checks for credential-free model-thumbnail downloads."""

from unittest.mock import Mock

import pytest
from fakes import FakeTransport

from scenario.core.api import assets
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
        assets.download_file(url, tmp_path / "new" / "asset.png", transport=transport, sleep=sleep)
    network.assert_not_called()
    transport.request.assert_not_called()
    sleep.assert_not_called()
    assert not list(tmp_path.iterdir())


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


def test_download_file_retries_after_a_network_error(tmp_path):
    from scenario.core.api.errors import NetworkError

    class Flaky:
        def __init__(self):
            self.calls = 0

        def request(self, method, url, headers, body, timeout=None):
            self.calls += 1
            if self.calls == 1:
                raise NetworkError(0, "network: Remote end closed connection without response")
            return 200, {}, b"glb bytes"

    flaky = Flaky()
    sleeps = []
    dest = assets.download_file(
        "https://cdn/x.glb", tmp_path / "x.glb", transport=flaky, sleep=sleeps.append
    )
    assert dest.read_bytes() == b"glb bytes" and flaky.calls == 2 and sleeps == [1.0]


def test_download_file_gives_up_after_retries(tmp_path):
    import pytest as _pytest

    from scenario.core.api.errors import NetworkError

    class Dead:
        def request(self, *a, **k):
            raise NetworkError(0, "network: down")

    with _pytest.raises(NetworkError):
        assets.download_file(
            "https://cdn/x.glb",
            tmp_path / "x.glb",
            transport=Dead(),
            retries=2,
            sleep=lambda s: None,
        )


def test_thumbnail_bytes_use_versioned_identity_without_credentials(monkeypatch, tmp_path):
    import io

    from scenario import __version__

    requests = []

    def respond(request, *, timeout):
        requests.append(request)
        return io.BytesIO(b"thumbnail-bytes")

    monkeypatch.setattr(assets.urllib.request, "urlopen", respond)
    url = "https://cdn.example/thumbnail.png?signature=synthetic"
    destination = assets.download_file(url, tmp_path / "thumbnail.png")
    assert destination.read_bytes() == b"thumbnail-bytes"
    assert len(requests) == 1
    assert requests[0].full_url == url
    assert requests[0].get_header("User-agent") == f"ScenarioBlender/{__version__}"
    assert requests[0].get_header("Authorization") is None
