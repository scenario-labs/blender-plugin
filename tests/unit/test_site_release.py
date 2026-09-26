# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Publication discovery must not publish stale or unverified inventories."""

import importlib
import json
from pathlib import Path

import pytest

from tests.unit.test_release_inventory import Releases
from tests.unit.test_release_provenance import GitHubFixture


@pytest.fixture
def publisher(monkeypatch):
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[2] / "tools"))
    return importlib.import_module("prepare_site_release")


class DiscoveryFixture(GitHubFixture):
    def __init__(self, releases):
        super().__init__(releases)
        self.discoveries = 0
        self.on_discover = lambda: None
        self.downloads = []

    def run(self, arguments, limit=None):
        if "--paginate" in arguments:
            assert "--slurp" in arguments
            self.discoveries += 1
            self.on_discover()
            return json.dumps([self.releases.rows]).encode()
        identifier = int(arguments[1].rsplit("/", 1)[1])
        for release in self.releases.rows:
            for asset in release["assets"]:
                if asset["id"] == identifier:
                    self.downloads.append(asset["name"])
                    return (self.releases.assets / release["tag_name"] / asset["name"]).read_bytes()
        raise AssertionError(arguments)


def fixture(tmp_path):
    releases = Releases(tmp_path)
    releases.add("1.0.0", maximum="5.1.0")
    releases.add("2.0.0", minimum="5.1.0")
    return DiscoveryFixture(releases)


def test_discovery_verification_and_final_check_retain_exact_history(publisher, tmp_path):
    github = fixture(tmp_path)
    output = tmp_path / "verified"
    result = publisher.prepare_current(output, github=github)
    assert [row["version"] for row in json.loads(result.read_text())["archives"]] == [
        "1.0.0",
        "2.0.0",
    ]
    assert github.discoveries == 2
    for release in github.releases.rows:
        for asset in release["assets"]:
            if asset["name"].endswith(".zip"):
                assert (output / asset["name"]).read_bytes() == (
                    github.releases.assets / release["tag_name"] / asset["name"]
                ).read_bytes()
    publisher.check_current(output, github=github)
    assert github.discoveries == 3
    assert len(github.verified) == 8


def test_release_published_during_build_prevents_stale_deploy(publisher, tmp_path):
    github = fixture(tmp_path)
    output = tmp_path / "verified"
    publisher.prepare_current(output, github=github)
    github.releases.add("3.0.0", minimum="5.1.0")
    with pytest.raises(ValueError, match="changed after"):
        publisher.check_current(output, github=github)


def test_race_during_download_does_not_expose_partial_output(publisher, tmp_path):
    github = fixture(tmp_path)

    def change():
        if github.discoveries == 2:
            github.releases.add("3.0.0", minimum="5.1.0")

    github.on_discover = change
    with pytest.raises(ValueError, match="changed"):
        publisher.prepare_current(tmp_path / "verified", github=github)
    assert not (tmp_path / "verified").exists()


@pytest.mark.parametrize("problem", ["empty", "drafts", "unverified", "corrupt", "withdrawn"])
def test_invalid_releases_cannot_replace_deployment(publisher, tmp_path, problem):
    github = fixture(tmp_path)
    if problem == "empty":
        github.releases.rows.clear()
    elif problem == "drafts":
        for row in github.releases.rows:
            row["draft"] = True
    elif problem == "unverified":

        def reject(*_):
            raise ValueError("Invalid attestation")

        github.verify = reject
    elif problem == "corrupt":
        archive = github.releases.assets / "blender-plugin-v2.0.0/scenario-2.0.0.zip"
        archive.write_bytes(b"bad")
    else:
        github.on_verify = lambda *_: github.releases.rows[0].update(draft=True)
    with pytest.raises(ValueError):
        publisher.prepare_current(tmp_path / "verified", github=github)
    assert not (tmp_path / "verified").exists()


def test_failed_deployment_can_repeat_from_unchanged_release_bytes(publisher, tmp_path):
    github = fixture(tmp_path)
    first = publisher.prepare_current(tmp_path / "first", github=github)
    second = publisher.prepare_current(tmp_path / "retry", github=github)
    assert first.read_bytes() == second.read_bytes()
    assert set(github.downloads) == {"scenario-1.0.0.zip", "scenario-2.0.0.zip", "SHA256SUMS"}


def test_bootstrap_requires_explicit_opt_in_and_publishes_no_inventory(publisher, tmp_path):
    github = DiscoveryFixture(Releases(tmp_path))
    output = tmp_path / "verified"
    with pytest.raises(ValueError):
        publisher.prepare_current(output, github=github)
    assert publisher.prepare_current(output, github=github, allow_bootstrap=True) is None
    assert set(p.name for p in output.iterdir()) == {"publication.json"}
    assert not github.downloads
    publisher.check_current(output, github=github)
    github.releases.add("1.0.0")
    with pytest.raises(ValueError, match="changed after"):
        publisher.check_current(output, github=github)


@pytest.mark.parametrize("problem", ["draft", "prerelease", "assets"])
def test_bootstrap_cannot_hide_unready_adopted_releases(publisher, tmp_path, problem):
    github = fixture(tmp_path)
    for row in github.releases.rows:
        if problem == "assets":
            row["assets"] = []
        else:
            row[problem] = True
    with pytest.raises(ValueError):
        publisher.prepare_current(tmp_path / "verified", github=github, allow_bootstrap=True)
    assert not (tmp_path / "verified").exists()
