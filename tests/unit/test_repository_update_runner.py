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


def test_test_predecessor_changes_only_matching_version_metadata(runner, tmp_path):
    import zipfile

    candidate, _ = runner.fixture(tmp_path / "candidate", "1.2.3")
    clean = tmp_path / "candidate.zip"
    with zipfile.ZipFile(candidate) as source, zipfile.ZipFile(clean, "w") as target:
        for name in source.namelist():
            content = source.read(name)
            if name == "__init__.py":
                content = b'__version__ = "1.2.3"  # keep this comment\n'
            target.writestr(name, content)
    original = clean.read_bytes()
    before, inventory, version = runner.fixture_predecessor(tmp_path / "before", clean)
    assert version == "0.0.0"
    assert clean.read_bytes() == original
    with zipfile.ZipFile(clean) as source, zipfile.ZipFile(before) as target:
        assert source.namelist() == target.namelist()
        for name in source.namelist():
            expected = source.read(name)
            if name in ("blender_manifest.toml", "__init__.py"):
                expected = expected.replace(b'"1.2.3"', b'"0.0.0"')
            assert target.read(name) == expected
    assert json.loads(inventory.read_text())["archives"][0]["sha256"] == runner.sha256(before)


def test_test_predecessor_rejects_ambiguous_or_absent_selection(runner, tmp_path):
    for previous, candidate in [(None, None), (tmp_path / "old.zip", tmp_path / "new.zip")]:
        with pytest.raises(ValueError, match="excludes"):
            runner.run(
                SimpleNamespace(
                    previous_zip=previous, candidate_zip=candidate, test_predecessor=True
                )
            )
    archive, _ = runner.fixture(tmp_path / "old", "1.2.3")
    with pytest.raises(ValueError, match="matching version declaration"):
        runner.fixture_predecessor(tmp_path / "before", archive)


def test_probe_inventory_uses_extended_windows_drive_and_unc_paths(monkeypatch):
    monkeypatch.syspath_prepend(str(ROOT / "tests/blender"))
    probe = importlib.import_module("package_update")
    assert probe.windows_namespace("C:\\profile\\state") == "\\\\?\\C:\\profile\\state"
    assert probe.windows_namespace("\\\\server\\share\\state") == "\\\\?\\UNC\\server\\share\\state"
    extended = "\\\\?\\C:\\profile\\state"
    assert probe.windows_namespace(extended) == extended


@pytest.fixture
def package_probe(monkeypatch):
    monkeypatch.syspath_prepend(str(ROOT / "tests/blender"))
    probe = importlib.import_module("package_update")
    monkeypatch.setattr(probe, "module", lambda name: importlib.import_module("scenario." + name))
    return probe


def test_update_snapshot_adds_only_absent_film_field(package_probe):
    from dataclasses import dataclass

    @dataclass
    class Record:
        intent: dict

    old = Record({"request_id": "old"})
    assert package_probe.job_snapshot(old)["intent"] == {
        "request_id": "old",
        "film_task": None,
    }
    binding = {"production_id": "production", "task_id": "take", "task_sha256": "a" * 64}
    bound = Record({"film_task": binding})
    assert package_probe.job_snapshot(bound)["intent"]["film_task"] == binding
    cloud = Record({"source": "cloud"})
    assert package_probe.job_snapshot(cloud)["intent"] == {"source": "cloud"}
    assert old.intent == {"request_id": "old"}


def test_update_snapshot_includes_separate_film_upload_and_rejects_scope_leak(package_probe):
    from dataclasses import dataclass, replace

    @dataclass(frozen=True)
    class Reference:
        film_task: dict
        upload_request_id: str
        upload_revision: int
        asset_id: str
        file_sha256: str
        kind: str

    saved = Reference({"task_id": "captured-reference"}, "upload-mesh", 7, "asset", "a" * 64, "3d")

    def store(reference):
        def read(production, task):
            assert (production, task) == ("update-production", "captured-reference")
            return reference

        return SimpleNamespace(film_upload=read)

    expected = package_probe.film_upload_snapshot(store(saved), store(None))
    assert expected["file_sha256"] == saved.file_sha256
    assert expected["film_task"] == saved.film_task
    for changed in (None, replace(saved, upload_revision=8), replace(saved, asset_id="other")):
        assert package_probe.film_upload_snapshot(store(changed), store(None)) != expected
    with pytest.raises(RuntimeError, match="credential scope"):
        package_probe.film_upload_snapshot(store(saved), store(saved))
    assert package_probe.film_upload_snapshot(SimpleNamespace(), SimpleNamespace()) is None


def test_package_probe_seeds_exact_mesh_upload_and_detects_lost_binding(package_probe, tmp_path):
    from dataclasses import replace

    from scenario.core.jobs import store as jobs
    from scenario.core.jobs.upload_sources import UploadSources
    from scenario.core.jobs.upload_store import UploadState, UploadStore

    scope = jobs.JobScope("https://fixture.invalid", "update-account")
    selected = jobs.JobStore(tmp_path / "jobs.sqlite3", scope)
    uploads = UploadStore(tmp_path / "uploads.sqlite3", scope)
    (tmp_path / "sources").mkdir()
    sources = UploadSources(tmp_path / "sources", part_bytes=128)
    origin = jobs.JobOrigin("file", "scene", "revision", "target")
    binding = package_probe.seed_mesh_upload(tmp_path, selected, uploads, sources, origin)
    upload = uploads.get("upload-mesh")
    assert upload.state == UploadState.IMPORTED
    assert len(upload.receipts) > 1
    sources.verify(upload.intent)
    assert binding.mesh_source.file_sha256 == package_probe.digest(
        (tmp_path / "reference.glb").read_bytes()
    )
    for name in ("ready", "applied"):
        selected.create(
            jobs.JobIntent(
                name,
                scope,
                origin,
                "model",
                "fixture-model",
                "a" * 64,
                "b" * 64,
                "0.1234567890123456789",
                (binding,),
            )
        )
    package_probe.check_mesh_bindings(selected, uploads)
    missing = replace(
        selected.get("ready"), intent=replace(selected.get("ready").intent, mesh_sources=())
    )
    damaged = SimpleNamespace(get=lambda name: missing if name == "ready" else selected.get(name))
    with pytest.raises(RuntimeError, match="captured generation input"):
        package_probe.check_mesh_bindings(damaged, uploads)


def test_package_probe_detects_lost_uncertainty_or_allowed_replay(
    package_probe, tmp_path, monkeypatch
):
    from dataclasses import replace

    from scenario.core.jobs import store as jobs
    from scenario.core.jobs.transfers import DownloadedResult

    scope = jobs.JobScope("https://fixture.invalid", "update-account")
    selected = jobs.JobStore(tmp_path / "jobs.sqlite3", scope)
    origin = jobs.JobOrigin("file", "scene", "revision", "target")
    intent = jobs.JobIntent(
        "applied", scope, origin, "model", "fixture-model", "a" * 64, "b" * 64, "1"
    )
    record = selected.create(intent)
    for state in (jobs.JobState.SUBMITTING, jobs.JobState.REMOTE, jobs.JobState.SUCCEEDED):
        record = selected.transition(
            "applied",
            expected_revision=record.revision,
            state=state,
            **({"remote_job_id": "remote"} if state == jobs.JobState.REMOTE else {}),
        )
    record = selected.set_results(
        "applied",
        (jobs.ResultAsset("asset", "result.png", "image/png"),),
        expected_revision=record.revision,
    )
    record = selected.transition(
        "applied", expected_revision=record.revision, state=jobs.JobState.DOWNLOADING
    )
    record = selected.record_download(
        "applied",
        "asset",
        DownloadedResult("result.png", 1, "a" * 64),
        expected_revision=record.revision,
    )
    for state in (jobs.JobState.READY, jobs.JobState.APPLYING, jobs.JobState.APPLIED):
        record = selected.transition("applied", expected_revision=record.revision, state=state)
    package_probe.seed_local_applications(selected, record, origin)
    expected = selected.get("applied")
    package_probe.check_local_applications(selected)
    assert selected.get("applied") == expected
    lost = SimpleNamespace(
        get=lambda _: replace(expected, local_applications=expected.local_applications[:-1])
    )
    with pytest.raises(RuntimeError, match="local application history"):
        package_probe.check_local_applications(lost)
    monkeypatch.setattr(selected, "claim_local_application", lambda *a, **kw: expected)
    with pytest.raises(RuntimeError, match="permitted replay"):
        package_probe.check_local_applications(selected)
