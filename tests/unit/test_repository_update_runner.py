# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Guard the native updater fixture's artifact, network and profile boundaries."""

import importlib
import json
import os
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture
def runner(monkeypatch):
    monkeypatch.syspath_prepend(str(ROOT / "tools"))
    return importlib.import_module("test_repository_update")


def test_fixture_archives_have_exact_replayable_inventory(runner, tmp_path):
    repository = importlib.import_module("repository")
    first, first_inventory = runner.fixture(tmp_path / "first", "1.0.0")
    second, second_inventory = runner.fixture(tmp_path / "second", "2.0.0")
    for path, inventory, version in [
        (first, first_inventory, "1.0.0"),
        (second, second_inventory, "2.0.0"),
    ]:
        value = repository.read_inventory(inventory)
        assert value["extension_id"] == "scenario"
        manifest, contents = repository.inspect_zip(path)
        assert manifest["version"] == version
        assert contents["LICENSE"] == repository.sha256(ROOT / "LICENSE")
        repository.verify_bytes(path, value["archives"][0])
    replay, _ = runner.fixture(tmp_path / "replay", "1.0.0")
    assert first.read_bytes() == replay.read_bytes()
    assert first.read_bytes() != second.read_bytes()


def test_loopback_server_serves_only_fixture_files_and_closes(runner, tmp_path):
    (tmp_path / "index.json").write_bytes(b'{"fixture": true}')
    (tmp_path / "scenario-1.0.0.zip").write_bytes(b"exact bytes")
    (tmp_path / "private").write_bytes(b"must not be served")
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    with runner.serve(tmp_path) as (server, url):
        assert server.server_address[0] == "127.0.0.1"
        with opener.open(url + "?blender_version=5.0.1", timeout=2) as response:
            assert response.read() == b'{"fixture": true}'
        archive_url = url.removesuffix("index.json") + "scenario-1.0.0.zip"
        with opener.open(archive_url, timeout=2) as response:
            assert response.read() == b"exact bytes"
        for path in ["private", "../private", "%2e%2e/private", ""]:
            with pytest.raises(urllib.error.HTTPError) as failure:
                opener.open(url.removesuffix("index.json") + path, timeout=2)
            assert failure.value.code == 404
            failure.value.close()
        assert server.requests == ["/index.json", "/scenario-1.0.0.zip"]
    assert server.socket.fileno() == -1


@pytest.mark.parametrize("marker", [False, True])
def test_probe_refuses_unmanaged_profiles_before_importing_blender(tmp_path, marker):
    environment = {
        key: value for key, value in os.environ.items() if not key.startswith("BLENDER_")
    }
    if marker:
        profile = tmp_path / "profile"
        profile.mkdir()
        environment["BLENDER_USER_RESOURCES"] = str(profile)
        (tmp_path / "repository-update.json").write_text(json.dumps({"profile": "other"}))
    result = subprocess.run(
        [sys.executable, str(ROOT / "tests/blender/repository_update.py")],
        env=environment,
        capture_output=True,
        text=True,
    )
    assert result.returncode != 0
    expected = "Refusing an unmanaged" if marker else "Use tools/test_repository_update.py"
    assert expected in result.stderr
    assert "No module named 'bpy'" not in result.stderr


def test_native_failure_retains_owned_evidence_without_touching_normal_profile(
    runner, tmp_path, monkeypatch
):
    normal = tmp_path / "normal"
    normal.mkdir()
    (normal / "preferences").write_text("existing")
    before = runner.profile_snapshot(normal)
    monkeypatch.setattr(runner, "normal_profile_root", lambda: normal)
    monkeypatch.setattr(runner, "find_blender", lambda _: "fixture-blender")
    monkeypatch.setenv("HTTP_PROXY", "http://proxy.invalid:8080")
    monkeypatch.setenv("https_proxy", "http://proxy.invalid:8080")

    def failed_step(session, name, _args):
        assert "HTTP_PROXY" not in session.env
        assert "https_proxy" not in session.env
        assert session.env["NO_PROXY"] == session.env["no_proxy"] == "127.0.0.1,localhost"
        if name == "probe":
            path = session.directory / "probe.log"
            path.write_text('SCENARIO_ENV={"version":[5,0,1],"blender":"5.0.1"}\n')
            return path
        raise subprocess.CalledProcessError(1, name)

    monkeypatch.setattr(runner.Session, "step", failed_step)
    arguments = SimpleNamespace(
        blender=None, artifacts=tmp_path / "artifacts", timeout=2, expected_version="5.0.1"
    )
    assert runner.run(arguments) == 1
    directory = next(arguments.artifacts.iterdir())
    report = json.loads((directory / "result.json").read_text())
    assert report["status"] == "failed"
    assert "first-validate" in report["error"]
    assert (directory / "profile").is_dir()
    assert runner.profile_snapshot(normal) == before


def test_expected_version_mismatch_stops_before_native_mutation(runner, tmp_path, monkeypatch):
    monkeypatch.setattr(runner, "normal_profile_root", lambda: tmp_path / "normal")
    monkeypatch.setattr(runner, "find_blender", lambda _: "fixture-blender")
    calls = []

    def step(session, name, _args):
        calls.append(name)
        path = session.directory / "probe.log"
        path.write_text('SCENARIO_ENV={"version":[5,0,1],"blender":"5.0.1"}\n')
        return path

    monkeypatch.setattr(runner.Session, "step", step)
    arguments = SimpleNamespace(
        blender=None, artifacts=tmp_path / "artifacts", timeout=2, expected_version="5.2.1"
    )
    assert runner.run(arguments) == 1
    assert calls == ["probe"]


def test_artifacts_cannot_be_written_into_the_normal_profile(runner, tmp_path, monkeypatch):
    normal = tmp_path / "normal"
    monkeypatch.setattr(runner, "normal_profile_root", lambda: normal)
    args = SimpleNamespace(artifacts=normal / "runs")
    with pytest.raises(ValueError, match="outside the normal"):
        runner.run(args)
    assert not normal.exists()


def test_update_failure_stops_server_and_preserves_only_owned_profile(
    runner, tmp_path, monkeypatch
):
    monkeypatch.setattr(runner, "normal_profile_root", lambda: tmp_path / "normal")
    monkeypatch.setattr(runner, "find_blender", lambda _: "fixture-blender")
    monkeypatch.setattr(runner, "verify_installed", lambda *_: None)

    def generate(_commands, _inventory, output):
        output.mkdir()
        return output

    def step(session, name, _args):
        if name == "probe":
            path = session.directory / "probe.log"
            path.write_text('SCENARIO_ENV={"version":[5,0,1],"blender":"5.0.1"}\n')
            return path
        if name == "update":
            raise subprocess.CalledProcessError(1, name)
        if name in {"configure", "install"}:
            return None
        raise AssertionError("Unexpected native step: " + name)

    monkeypatch.setattr(runner, "generate", generate)
    monkeypatch.setattr(runner.Session, "step", step)
    args = SimpleNamespace(
        blender=None, artifacts=tmp_path / "artifacts", timeout=2, expected_version="5.0.1"
    )
    assert runner.run(args) == 1
    directory = next(args.artifacts.iterdir())
    report = json.loads((directory / "result.json").read_text())
    assert report["status"] == "failed"
    assert report["server_stopped"] is True
    assert "update" in report["error"]
    assert (directory / "profile").is_dir()
    assert not (tmp_path / "normal").exists()


def test_exact_package_copy_preserves_all_bytes_and_inventory(runner, tmp_path):
    import zipfile

    archive, _ = runner.fixture(tmp_path / "source", "1.2.3")
    with zipfile.ZipFile(archive, "a") as package:
        package.writestr(
            "core/jobs/store.py", "# Synthetic adopted-layout marker for unit validation\n"
        )
    original = archive.read_bytes()
    copied, inventory, version = runner.package_artifact(tmp_path / "copied", archive)
    assert copied.read_bytes() == original == archive.read_bytes()
    assert version == "1.2.3"
    entry = json.loads(inventory.read_text())["archives"][0]
    assert entry["version"] == version
    assert entry["size"] == len(original)
    assert entry["sha256"] == runner.sha256(archive)


def test_package_mode_rejects_placeholder_and_incomplete_pair_before_install(runner, tmp_path):
    archive, _ = runner.fixture(tmp_path / "source", "1.0.0")
    with pytest.raises(ValueError, match="adopted Scenario"):
        runner.package_artifact(tmp_path / "copied", archive)
    assert not (tmp_path / "copied").exists()
    with pytest.raises(ValueError, match="both"):
        runner.run(SimpleNamespace(previous_zip=archive, candidate_zip=None))


def test_selected_archive_server_keeps_the_explicit_file_boundary(runner, tmp_path):
    (tmp_path / "scenario-0.9.9.zip").write_bytes(b"chosen")
    (tmp_path / "scenario-2.0.0.zip").write_bytes(b"unselected")
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    with runner.serve(tmp_path, ("scenario-0.9.9.zip",)) as (server, url):
        root = url.removesuffix("index.json")
        with opener.open(root + "scenario-0.9.9.zip", timeout=2) as response:
            assert response.read() == b"chosen"
        with pytest.raises(urllib.error.HTTPError) as failure:
            opener.open(root + "scenario-2.0.0.zip", timeout=2)
        assert failure.value.code == 404
        failure.value.close()
        assert server.requests == ["/scenario-0.9.9.zip"]
    with pytest.raises(ValueError, match="basenames"), runner.serve(tmp_path, ("../private.zip",)):
        pass


@pytest.mark.parametrize("marker", [False, True])
def test_package_probe_refuses_unmanaged_profiles_before_blender(tmp_path, marker):
    environment = {
        key: value for key, value in os.environ.items() if not key.startswith("BLENDER_")
    }
    if marker:
        profile = tmp_path / "profile"
        profile.mkdir()
        environment["BLENDER_USER_RESOURCES"] = str(profile)
        (tmp_path / "repository-update.json").write_text(json.dumps({"profile": "other"}))
    result = subprocess.run(
        [sys.executable, str(ROOT / "tests/blender/package_update.py")],
        env=environment,
        capture_output=True,
        text=True,
    )
    assert result.returncode != 0
    assert "No module named 'bpy'" not in result.stderr
    assert (
        "Refusing an unmanaged" if marker else "Use tools/test_repository_update.py"
    ) in result.stderr


@pytest.mark.parametrize("candidate_version", ["1.2.3", "1.2.2"])
def test_equal_version_or_downgrade_stops_before_repository_install(
    runner, tmp_path, monkeypatch, candidate_version
):
    import zipfile

    previous, _ = runner.fixture(tmp_path / "previous", "1.2.3")
    candidate, _ = runner.fixture(tmp_path / "candidate", candidate_version)
    for path in (previous, candidate):
        with zipfile.ZipFile(path, "a") as archive:
            archive.writestr("core/jobs/store.py", "# Adopted-layout unit fixture\n")
    monkeypatch.setattr(runner, "normal_profile_root", lambda: tmp_path / "normal")
    monkeypatch.setattr(runner, "find_blender", lambda _: "fixture-blender")
    calls = []

    def step(session, name, _args):
        calls.append(name)
        assert name == "probe"
        log = session.directory / "probe.log"
        log.write_text('SCENARIO_ENV={"version":[5,0,1],"blender":"5.0.1"}\n')
        return log

    monkeypatch.setattr(runner.Session, "step", step)
    args = SimpleNamespace(
        blender=None,
        artifacts=tmp_path / "artifacts",
        timeout=2,
        expected_version="5.0.1",
        previous_zip=previous,
        candidate_zip=candidate,
    )
    assert runner.run(args) == 1
    assert calls == ["probe"]
    report = json.loads(next(args.artifacts.glob("*/result.json")).read_text())
    assert "newer" in report["error"]
