# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Offline release verification orchestration; gh owns cryptographic verification."""

import copy
import importlib
import json
import subprocess
from pathlib import Path
from types import SimpleNamespace

import pytest

from tests.unit.test_release_inventory import Releases

COMMIT = "a" * 40
TAG_OBJECT = "b" * 40


@pytest.fixture
def verifier(monkeypatch):
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[2] / "tools"))
    return importlib.import_module("verify_release_inventory")


class GitHubFixture:
    def __init__(self, releases):
        self.releases = releases
        self.verified = []
        self.reads = []
        self.on_verify = lambda path, commit: None
        for index, row in enumerate(releases.rows, 1):
            row["id"] = index
            for offset, asset in enumerate(row["assets"]):
                asset["id"] = index * 10 + offset
                asset["updated_at"] = row["published_at"]

    def read(self, endpoint):
        self.reads.append(endpoint)
        if endpoint.startswith("releases/tags/"):
            tag = endpoint.removeprefix("releases/tags/")
            return copy.deepcopy(next(row for row in self.releases.rows if row["tag_name"] == tag))
        if endpoint.startswith("git/ref/tags/"):
            tag = endpoint.removeprefix("git/ref/tags/")
            return {"ref": f"refs/tags/{tag}", "object": {"type": "commit", "sha": COMMIT}}
        raise AssertionError(endpoint)

    def checksum(self, asset):
        row = next(row for row in self.releases.rows if asset in row["assets"])
        return (self.releases.assets / row["tag_name"] / "SHA256SUMS").read_bytes()

    def verify(self, path, commit):
        self.verified.append((path.name, commit))
        self.on_verify(path, commit)


def inventory(verifier, tmp_path, *, history=False):
    releases = Releases(tmp_path)
    releases.add("1.0.0", maximum="5.1.0" if history else None)
    if history:
        releases.add("2.0.0", minimum="5.1.0")
    github = GitHubFixture(releases)
    selector = importlib.import_module("release_inventory")
    selected = releases.prepare(selector, tmp_path / "selected")
    return selected, github


def test_verified_snapshot_preserves_compatible_history_and_exact_zip_bytes(verifier, tmp_path):
    source, github = inventory(verifier, tmp_path, history=True)
    result = verifier.verify(source, tmp_path / "verified", github=github)
    assert result.read_bytes() == source.read_bytes()
    for original in source.parent.glob("*.zip"):
        assert (result.parent / original.name).read_bytes() == original.read_bytes()
    proof = json.loads((result.parent / "provenance.json").read_text())
    assert proof["repository"] == "scenario-labs/blender-plugin"
    assert proof["workflow"] == verifier.WORKFLOW
    assert [r["tag"] for r in proof["releases"]] == [
        "blender-plugin-v1.0.0",
        "blender-plugin-v2.0.0",
    ]
    assert all(row["commit"] == COMMIT for row in proof["releases"])
    assert github.verified == [
        ("SHA256SUMS", COMMIT),
        ("scenario-1.0.0.zip", COMMIT),
        ("SHA256SUMS", COMMIT),
        ("scenario-2.0.0.zip", COMMIT),
    ]
    assert github.reads.count("git/ref/tags/blender-plugin-v1.0.0") == 2
    assert not list(tmp_path.glob(".verify-releases-*"))


@pytest.mark.parametrize("name", ["SHA256SUMS", "scenario-1.0.0.zip"])
def test_either_rejected_attestation_leaves_no_partial_snapshot(verifier, tmp_path, name):
    source, github = inventory(verifier, tmp_path)
    original = source.read_bytes()

    def reject(path, commit):
        if path.name == name:
            raise ValueError("Rejected attestation")

    github.on_verify = reject
    with pytest.raises(ValueError, match="Rejected"):
        verifier.verify(source, tmp_path / "verified", github=github)
    assert not (tmp_path / "verified").exists()
    assert not list(tmp_path.glob(".verify-releases-*"))
    assert source.read_bytes() == original


@pytest.mark.parametrize("change", ["draft", "prerelease", "other-repo", "size", "checksum"])
def test_invalid_published_metadata_or_checksum_cannot_authorize_local_zip(
    verifier, tmp_path, change
):
    source, github = inventory(verifier, tmp_path)
    row = github.releases.rows[0]
    if change in {"draft", "prerelease"}:
        row[change] = True
    elif change == "other-repo":
        row["html_url"] = "https://github.com/other/repo/releases/tag/blender-plugin-v1.0.0"
    elif change == "size":
        row["assets"][0]["size"] += 1
    else:
        path = github.releases.assets / row["tag_name"] / "SHA256SUMS"
        data = path.read_text()
        path.write_text("0" * 64 + data[64:])
    with pytest.raises(ValueError):
        verifier.verify(source, tmp_path / "verified", github=github)
    assert not github.verified
    assert not (tmp_path / "verified").exists()


@pytest.mark.parametrize("change", ["tag", "asset", "withdrawn", "local-bytes"])
def test_changes_during_provenance_checks_fail_closed(verifier, tmp_path, change):
    source, github = inventory(verifier, tmp_path, history=True)
    original_read = github.read

    def mutate(path, commit):
        if path.name != "scenario-2.0.0.zip":
            return
        if change == "tag":

            def moved(endpoint):
                result = original_read(endpoint)
                if endpoint == "git/ref/tags/blender-plugin-v1.0.0":
                    result["object"]["sha"] = "c" * 40
                return result

            github.read = moved
        elif change == "asset":
            github.releases.rows[0]["assets"][0]["id"] += 100
        elif change == "withdrawn":
            github.releases.rows[0]["draft"] = True
        else:
            path.write_bytes(b"changed")

    github.on_verify = mutate
    with pytest.raises(ValueError):
        verifier.verify(source, tmp_path / "verified", github=github)
    assert not (tmp_path / "verified").exists()


def test_existing_or_concurrently_created_destination_is_preserved(verifier, tmp_path):
    source, github = inventory(verifier, tmp_path)
    output = tmp_path / "verified"
    output.mkdir()
    marker = output / "keep"
    marker.write_text("unchanged")
    with pytest.raises(ValueError, match="already exists"):
        verifier.verify(source, output, github=github)
    assert not github.reads
    assert marker.read_text() == "unchanged"
    other = tmp_path / "concurrent"
    github.on_verify = lambda path, commit: other.mkdir(exist_ok=True)
    with pytest.raises(ValueError, match="appeared"):
        verifier.verify(source, other, github=github)
    assert other.is_dir() and not list(other.iterdir())


@pytest.mark.parametrize("kind", ["tree", "cycle", "bad-sha", "wrong-ref", "wrong-tag"])
def test_invalid_tag_resolution_is_rejected(verifier, kind):
    def read(endpoint):
        if endpoint.startswith("git/ref/"):
            return {
                "ref": "refs/tags/other"
                if kind == "wrong-ref"
                else "refs/tags/blender-plugin-v1.0.0",
                "object": {
                    "type": "tree" if kind == "tree" else "tag",
                    "sha": "bad" if kind == "bad-sha" else TAG_OBJECT,
                },
            }
        return {
            "sha": COMMIT if kind == "wrong-tag" else TAG_OBJECT,
            "object": {"type": "tag", "sha": TAG_OBJECT},
        }

    with pytest.raises(ValueError):
        verifier.tag_commit(SimpleNamespace(read=read), "blender-plugin-v1.0.0")


def test_annotated_tag_resolves_to_its_commit(verifier):
    replies = iter(
        [
            {
                "ref": "refs/tags/blender-plugin-v1.0.0",
                "object": {"type": "tag", "sha": TAG_OBJECT},
            },
            {"sha": TAG_OBJECT, "object": {"type": "commit", "sha": COMMIT}},
        ]
    )
    assert (
        verifier.tag_commit(
            SimpleNamespace(read=lambda endpoint: next(replies)), "blender-plugin-v1.0.0"
        )
        == COMMIT
    )


def test_gh_verification_pins_source_and_signer_without_exposing_environment(
    verifier, monkeypatch, tmp_path
):
    calls = []
    monkeypatch.setenv("SCENARIO_TEST_API_SECRET", "synthetic-private-value")
    monkeypatch.setenv("GH_DEBUG", "api")

    def run(command, **kwargs):
        calls.append(command)
        assert "SCENARIO_TEST_API_SECRET" not in kwargs["env"]
        assert "GH_DEBUG" not in kwargs["env"]
        assert kwargs["env"]["GH_PROMPT_DISABLED"] == "1"
        assert kwargs["timeout"] == 180
        assert kwargs["stderr"] == subprocess.DEVNULL
        kwargs["stdout"].write(b'[{"verificationResult": {"statement": {}}}]')
        return SimpleNamespace(returncode=0)

    monkeypatch.setattr(verifier.subprocess, "run", run)
    verifier.GitHub().verify(tmp_path / "package.zip", COMMIT)
    command = calls[0]
    for flag, expected in {
        "--repo": verifier.REPOSITORY,
        "--signer-workflow": verifier.WORKFLOW,
        "--source-digest": COMMIT,
        "--signer-digest": COMMIT,
        "--source-ref": "refs/heads/main",
        "--predicate-type": verifier.PREDICATE,
        "--hostname": "github.com",
    }.items():
        assert command[command.index(flag) + 1] == expected
    assert "--deny-self-hosted-runners" in command


@pytest.mark.parametrize("mode", ["failure", "timeout", "empty", "oversize", "no-attestations"])
def test_gh_failures_and_invalid_results_are_sanitized(verifier, monkeypatch, mode):
    def run(command, **kwargs):
        if mode == "timeout":
            raise subprocess.TimeoutExpired("private command", 180, output=b"private output")
        kwargs["stdout"].write({"oversize": b"x" * 9, "no-attestations": b"[]"}.get(mode, b""))
        return SimpleNamespace(returncode=1 if mode == "failure" else 0)

    monkeypatch.setattr(verifier.subprocess, "run", run)
    with pytest.raises(ValueError) as error:
        if mode == "no-attestations":
            verifier.GitHub().verify(Path("fixture.zip"), COMMIT)
        else:
            verifier.GitHub().run(["api", "fixture"], limit=8)
    assert "private" not in str(error.value)


@pytest.mark.parametrize("kind", ["changed-zip", "foreign-id", "bad-name", "symlink"])
def test_bad_local_inputs_make_no_github_requests(verifier, tmp_path, kind):
    source, github = inventory(verifier, tmp_path)
    data = json.loads(source.read_text())
    if kind == "changed-zip":
        (source.parent / data["archives"][0]["file"]).write_bytes(b"changed")
    elif kind == "foreign-id":
        data["extension_id"] = "other"
        source.write_text(json.dumps(data))
    elif kind == "bad-name":
        data["archives"][0]["file"] = "other.zip"
        source.write_text(json.dumps(data))
    else:
        link = tmp_path / "linked.json"
        try:
            link.symlink_to(source)
        except OSError:
            pytest.skip("Symlink creation unavailable")
        source = link
    with pytest.raises(ValueError):
        verifier.verify(source, tmp_path / "verified", github=github)
    assert not github.reads
    assert not (tmp_path / "verified").exists()


def test_excessive_tag_nesting_is_bounded(verifier):
    calls = []

    def read(endpoint):
        calls.append(endpoint)
        digest = f"{len(calls):040x}"
        if len(calls) == 1:
            return {
                "ref": "refs/tags/blender-plugin-v1.0.0",
                "object": {"type": "tag", "sha": digest},
            }
        return {"sha": endpoint.rsplit("/", 1)[-1], "object": {"type": "tag", "sha": digest}}

    with pytest.raises(ValueError, match="nesting"):
        verifier.tag_commit(SimpleNamespace(read=read), "blender-plugin-v1.0.0")
    assert len(calls) == 9


@pytest.mark.parametrize("identifier", [None, True, 0, -1, "12"])
def test_checksum_requires_an_unambiguous_asset_id(verifier, monkeypatch, identifier):
    github = verifier.GitHub()
    monkeypatch.setattr(github, "run", lambda args, limit: pytest.fail("Unexpected read"))
    with pytest.raises(ValueError, match="asset id"):
        github.checksum({"id": identifier})


def test_cli_failure_omits_private_diagnostics(verifier, monkeypatch, capsys):
    monkeypatch.setattr(
        "sys.argv",
        ["verify_release_inventory.py", "--inventory", "missing.json", "--output", "unused"],
    )

    def reject(*args, **kwargs):
        raise ValueError("synthetic private diagnostic")

    monkeypatch.setattr(verifier, "verify", reject)
    assert verifier.main() == 1
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "Release verification failed" in captured.err
    assert "private" not in captured.err
