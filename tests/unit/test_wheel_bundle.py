# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Pinned dependency closure, tamper rejection and build-only wheel staging."""

import copy
import io
import json
import socket
import tomllib
import zipfile
from pathlib import Path

import pytest

from tools import wheel_bundle as bundle

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    def deny(*args, **kwargs):
        pytest.fail("Bundle unit tests must not download anything")

    monkeypatch.setattr(socket.socket, "connect", deny)
    monkeypatch.setattr(socket, "create_connection", deny)


@pytest.fixture
def fixture(tmp_path):
    data = io.BytesIO()
    notice = "fixture-1.0.dist-info/licenses/LICENSE"
    with zipfile.ZipFile(data, "w") as archive:
        archive.writestr("fixture/__init__.py", "# fixture")
        archive.writestr(notice, b"fixture license")
    raw = data.getvalue()
    wheel = {
        "package": "fixture",
        "version": "1.0",
        "filename": "fixture-1.0-py3-none-any.whl",
        "url": "https://files.pythonhosted.org/packages/fixture-1.0-py3-none-any.whl",
        "sha256": bundle.digest(raw),
        "licenses": [{"path": notice, "sha256": bundle.digest(b"fixture license")}],
    }
    lock = {"schema_version": 1, "platforms": ["linux-x64"], "wheels": [wheel]}
    source = tmp_path / "scenario"
    source.mkdir()
    (source / "sdk-wheel-lock.json").write_text(json.dumps(lock))
    (source / "blender_manifest.toml").write_text(
        'id = "scenario"\nplatforms = ["linux-x64"]\nwheels = ["./wheels/fixture-1.0-py3-none-any.whl"]\n'
    )
    (source / "__init__.py").write_text("# fixture")
    return source, wheel, raw


def test_runtime_lock_is_exact_sdk_closure_and_matches_uv_artifacts():
    lock = json.loads((ROOT / "scenario/sdk-wheel-lock.json").read_text())
    manifest = tomllib.loads((ROOT / "scenario/blender_manifest.toml").read_text())
    bundle.validate_lock(lock, manifest)
    packages = {p["name"]: p for p in tomllib.loads((ROOT / "uv.lock").read_text())["package"]}
    required = set()

    def visit(name):
        if name not in required:
            required.add(name)
            for dependency in packages[name].get("dependencies", []):
                visit(dependency["name"])

    visit("scenario-sdk")
    assert {wheel["package"] for wheel in lock["wheels"]} == required
    for wheel in lock["wheels"]:
        package = packages[wheel["package"]]
        assert wheel["version"] == package["version"]
        assert any(
            item["url"] == wheel["url"] and item["hash"] == "sha256:" + wheel["sha256"]
            for item in package["wheels"]
        )
    binaries = [
        wheel["filename"] for wheel in lock["wheels"] if wheel["package"] == "pydantic-core"
    ]
    assert len(binaries) == 8
    for python in ("cp311", "cp313"):
        for platform in (
            "macosx_10_12_x86_64",
            "macosx_11_0_arm64",
            "manylinux_2_17_x86_64.manylinux2014_x86_64",
            "win_amd64",
        ):
            assert sum(f"-{python}-{python}-{platform}.whl" in name for name in binaries) == 1


def test_stage_contains_verified_wheels_and_exact_notices_without_mutating_source(
    fixture, tmp_path, monkeypatch
):
    source, wheel, raw = fixture
    calls = []

    def download(url, path):
        calls.append(url)
        path.write_bytes(raw)

    monkeypatch.setattr(bundle, "_download", download)
    cache = tmp_path / "cache"
    stage = bundle.prepare_source(source, tmp_path / "stage", cache=cache)
    assert not (source / "wheels").exists()
    assert (stage / "wheels" / wheel["filename"]).read_bytes() == raw
    assert (
        stage / bundle.license_destination(wheel, wheel["licenses"][0])
    ).read_bytes() == b"fixture license"
    bundle.prepare_source(source, tmp_path / "again", cache=cache, offline=True)
    assert len(calls) == 1
    candidate = tmp_path / "candidate.zip"
    with zipfile.ZipFile(candidate, "w") as archive:
        for path in stage.rglob("*"):
            if path.is_file():
                archive.write(path, path.relative_to(stage))
    bundle.validate_bundle(candidate)


@pytest.mark.parametrize("offline", [False, True])
def test_corrupt_cache_is_never_bundled(fixture, tmp_path, monkeypatch, offline):
    source, wheel, raw = fixture
    cache = tmp_path / "cache"
    cache.mkdir()
    (cache / wheel["filename"]).write_bytes(b"corrupt")
    monkeypatch.setattr(bundle, "_download", lambda url, path: path.write_bytes(b"wrong hash"))
    with pytest.raises(ValueError, match="corrupt|SHA-256"):
        bundle.prepare_source(source, tmp_path / "stage", cache=cache, offline=offline)
    assert not (tmp_path / "stage").exists()
    assert not list(cache.glob("wheel-*"))


@pytest.mark.parametrize("mutation", ["manifest", "license", "url", "filename", "duplicate"])
def test_lock_rejects_unsafe_or_inconsistent_inputs(fixture, tmp_path, mutation):
    source, wheel, raw = fixture
    lock = json.loads((source / bundle.LOCK_NAME).read_text())
    manifest = tomllib.loads((source / "blender_manifest.toml").read_text())
    if mutation == "manifest":
        manifest["wheels"] = []
    elif mutation == "license":
        lock["wheels"][0]["licenses"][0]["path"] = "../../LICENSE"
    elif mutation == "url":
        lock["wheels"][0]["url"] = "http://other.invalid/" + wheel["filename"]
    elif mutation == "filename":
        lock["wheels"][0]["filename"] = "../bad.whl"
    else:
        lock["wheels"].append(copy.deepcopy(wheel))
    with pytest.raises(ValueError):
        bundle.validate_lock(lock, manifest)


def test_notice_hash_is_checked_inside_an_intact_wheel(fixture):
    _, wheel, raw = fixture
    wheel["licenses"][0]["sha256"] = "0" * 64
    with pytest.raises(ValueError, match="license"):
        bundle.wheel_notices(wheel, raw)


@pytest.mark.parametrize("mutation", ["wheel", "notice", "extra"])
def test_zip_verification_rejects_tampered_wheels_or_notices(
    fixture, tmp_path, monkeypatch, mutation
):
    source, wheel, raw = fixture
    monkeypatch.setattr(bundle, "_download", lambda url, path: path.write_bytes(raw))
    stage = bundle.prepare_source(source, tmp_path / "stage", cache=tmp_path / "cache")
    if mutation == "wheel":
        (stage / "wheels" / wheel["filename"]).write_bytes(b"corrupt")
    elif mutation == "notice":
        (stage / bundle.license_destination(wheel, wheel["licenses"][0])).write_bytes(b"different")
    else:
        (stage / "wheels/extra.whl").write_bytes(b"extra")
    candidate = tmp_path / "candidate.zip"
    with zipfile.ZipFile(candidate, "w") as archive:
        for path in stage.rglob("*"):
            if path.is_file():
                archive.write(path, path.relative_to(stage))
    with pytest.raises(ValueError):
        bundle.validate_bundle(candidate)


@pytest.mark.parametrize("failure", ["timeout", "reset", "503", "partial"])
def test_transient_download_restarts_and_publishes_only_verified_bytes(
    fixture, tmp_path, monkeypatch, failure
):
    _, wheel, raw = fixture
    attempts, sleeps = [], []

    class Interrupted(io.BytesIO):
        def read(self, size=-1):
            if self.tell():
                raise bundle.http.client.IncompleteRead(b"partial")
            return super().read(3)

    def open_url(request, timeout):
        attempts.append(request.full_url)
        if len(attempts) < 3:
            if failure == "partial":
                return Interrupted(b"interrupted response")
            if failure == "503":
                raise bundle.urllib.error.HTTPError(request.full_url, 503, "unavailable", {}, None)
            if failure == "reset":
                raise ConnectionResetError("reset")
            raise bundle.urllib.error.URLError(TimeoutError("timeout"))
        return io.BytesIO(raw)

    monkeypatch.setattr(bundle.urllib.request, "urlopen", open_url)
    monkeypatch.setattr(bundle.time, "sleep", sleeps.append)
    cache = tmp_path / "cache"
    path = bundle.cached_wheel(wheel, cache)
    assert path.read_bytes() == raw
    assert attempts == [wheel["url"]] * 3
    assert sleeps == [1, 2]
    assert list(cache.iterdir()) == [path]


@pytest.mark.parametrize(
    "failure,expected_attempts", [("timeout", 3), ("404", 1), ("hash", 1), ("size", 1)]
)
def test_failed_download_is_bounded_and_never_published(
    fixture, tmp_path, monkeypatch, failure, expected_attempts
):
    _, wheel, _ = fixture
    attempts, sleeps = [], []

    def open_url(request, timeout):
        attempts.append(request.full_url)
        if failure == "timeout":
            raise TimeoutError("timeout")
        if failure == "404":
            raise bundle.urllib.error.HTTPError(request.full_url, 404, "missing", {}, None)
        return io.BytesIO(b"bad bytes")

    if failure == "size":
        monkeypatch.setattr(bundle.zip_limits, "MAX_MEMBER_BYTES", 4)
    monkeypatch.setattr(bundle.urllib.request, "urlopen", open_url)
    monkeypatch.setattr(bundle.time, "sleep", sleeps.append)
    cache = tmp_path / "cache"
    with pytest.raises((TimeoutError, bundle.urllib.error.HTTPError, ValueError)):
        bundle.cached_wheel(wheel, cache)
    assert len(attempts) == expected_attempts
    assert sleeps == ([1, 2] if expected_attempts == 3 else [])
    assert list(cache.iterdir()) == []


@pytest.mark.parametrize(
    "limit,value", [("MAX_MEMBERS", 1), ("MAX_MEMBER_BYTES", 512), ("MAX_TOTAL_BYTES", 20)]
)
@pytest.mark.parametrize("target", ["inspection", "bundle", "wheel"])
def test_expansion_limits_reject_before_any_payload_read(
    fixture, tmp_path, monkeypatch, limit, value, target
):
    from tools import blender_env

    _, wheel, _ = fixture
    data = io.BytesIO()
    with zipfile.ZipFile(data, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("blender_manifest.toml", 'id = "scenario"\n')
        archive.writestr("payload", b"x" * 4096)
    raw = data.getvalue()
    candidate = tmp_path / "oversized.zip"
    candidate.write_bytes(raw)
    wheel["sha256"] = bundle.digest(raw)
    monkeypatch.setattr(bundle.zip_limits, limit, value)

    def no_read(*args, **kwargs):
        pytest.fail("Archive payload read before resource-limit check")

    monkeypatch.setattr(zipfile.ZipFile, "open", no_read)
    with pytest.raises(ValueError, match="exceeds limit"):
        if target == "inspection":
            blender_env.inspect_zip(candidate)
        elif target == "bundle":
            bundle.validate_bundle(candidate)
        else:
            bundle.wheel_notices(wheel, raw)


def test_hash_valid_notice_still_obeys_smaller_notice_limit(fixture, monkeypatch):
    _, wheel, raw = fixture
    monkeypatch.setattr(bundle.zip_limits, "MAX_NOTICE_BYTES", 4)
    with pytest.raises(ValueError, match="member size exceeds limit"):
        bundle.wheel_notices(wheel, raw)


@pytest.mark.parametrize("target", ["inspection", "bundle"])
def test_metadata_obeys_smaller_limit(tmp_path, monkeypatch, target):
    from tools import blender_env

    candidate = tmp_path / "metadata.zip"
    with zipfile.ZipFile(candidate, "w") as archive:
        archive.writestr("blender_manifest.toml", 'id = "scenario"\n')
    monkeypatch.setattr(bundle.zip_limits, "MAX_METADATA_BYTES", 4)
    with pytest.raises(ValueError, match="member size exceeds limit"):
        (blender_env.inspect_zip if target == "inspection" else bundle.validate_bundle)(candidate)
