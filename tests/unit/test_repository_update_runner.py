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


def test_test_predecessor_rejects_absent_candidate(runner, tmp_path):
    for previous in (None, tmp_path / "old.zip"):
        with pytest.raises(ValueError, match="requires --candidate-zip"):
            runner.run(
                SimpleNamespace(previous_zip=previous, candidate_zip=None, test_predecessor=True)
            )
    archive, _ = runner.fixture(tmp_path / "old", "1.2.3")
    with pytest.raises(ValueError, match="matching version declaration"):
        runner.fixture_predecessor(tmp_path / "before", archive)


def _adopted(runner, directory, version, schema, *, owner=False):
    """A minimal adopted-layout package with its version, job-store schema and owners."""
    import zipfile

    directory.mkdir()
    fixture, _ = runner.fixture(directory / "fixture", version)
    archive = directory / f"scenario-{version}.zip"
    with zipfile.ZipFile(fixture) as source, zipfile.ZipFile(archive, "w") as package:
        for name in source.namelist():
            content = source.read(name)
            if name == "__init__.py":
                content = f'__version__ = "{version}"\n'.encode()
            package.writestr(name, content)
        package.writestr("core/jobs/store.py", f'"""Unit fixture."""\n\n_VERSION = {schema}\n')
        if owner:
            package.writestr("core/jobs/model_defaults.py", '"""Unit fixture."""\n')
    return archive


def test_store_schema_is_read_from_package_source_without_import(runner, tmp_path):
    import zipfile

    assert runner.store_schema(_adopted(runner, tmp_path / "nine", "1.0.0", 9)) == 9
    missing = _adopted(runner, tmp_path / "missing", "1.0.0", "unknown")
    with pytest.raises(ValueError, match="no schema version"):
        runner.store_schema(missing)
    archive, _ = runner.fixture(tmp_path / "absent", "1.0.0")
    with pytest.raises(ValueError, match="no shared job store"):
        runner.store_schema(archive)
    assert zipfile.is_zipfile(missing)


def test_lane_defaults_owner_is_detected_from_package_source(runner, tmp_path):
    assert not runner.model_defaults_owner(_adopted(runner, tmp_path / "ten", "1.0.0", 10))
    owned = _adopted(runner, tmp_path / "owned", "1.0.0", 10, owner=True)
    assert runner.model_defaults_owner(owned)
    archive, _ = runner.fixture(tmp_path / "absent", "1.0.0")
    assert not runner.model_defaults_owner(archive)


@pytest.mark.parametrize(
    ("schemas", "owner", "claimed"),
    [
        ((9, 10), True, True),
        ((10, 10), False, False),
        ((10, 10), True, True),
        ((8, 9), False, False),
        ((9, 10), True, False),
        ((10, 10), False, True),
    ],
)
def test_same_version_previous_code_becomes_the_test_predecessor(
    runner, tmp_path, monkeypatch, schemas, owner, claimed
):
    """An unreleased predecessor shares the candidate's version; only metadata changes.

    A candidate that ships the lane-defaults owner must report reading the seeded
    defaults through it, and a candidate without one cannot claim that it did.
    """
    import contextlib
    import zipfile

    previous = _adopted(runner, tmp_path / "previous", "1.2.3", schemas[0])
    candidate = _adopted(runner, tmp_path / "candidate", "1.2.3", schemas[1], owner=owner)
    monkeypatch.setattr(runner, "normal_profile_root", lambda: tmp_path / "normal")
    monkeypatch.setattr(runner, "find_blender", lambda _: "fixture-blender")
    monkeypatch.setattr(runner, "verify_installed", lambda *_: None)
    reports = {}

    def generate(_commands, _inventory, output):
        output.mkdir()
        return output

    database = None

    def step(session, name, args):
        nonlocal database
        if name == "probe":
            path = session.directory / "probe.log"
            path.write_text('SCENARIO_ENV={"version":[5,1,2],"blender":"5.1.2"}\n')
            return path
        if name in {"configure", "install"}:
            return None
        if name == "predecessor-reopen":
            assert "--factory-startup" in args
            package = session.directory / "first/scenario-0.0.0.zip"
            assert Path(args[args.index("--package") + 1]) == package
            assert Path(args[args.index("--database") + 1]) == database
            report = Path(args[args.index("--report") + 1])
            report.write_text(
                json.dumps({"predecessor_schema": schemas[0], "refused": "Unsupported"})
            )
            return None
        if name == "update":
            database = session.profile / "extensions/.user/update_fixture/shared-jobs/jobs.sqlite3"
            database.parent.mkdir(parents=True)
            database.write_bytes(b"upgraded store")
        before = session.directory / "first/scenario-0.0.0.zip"
        with zipfile.ZipFile(before) as package:
            assert f"_VERSION = {schemas[0]}" in package.read("core/jobs/store.py").decode()
        report = Path(args[args.index("--report") + 1])
        reports[name] = {
            "before": "0.0.0",
            "after": "1.2.3",
            "enabled": True,
            "state_preserved": True,
            "scene_preserved": True,
            "project_scope_preserved": True,
            "workflow_references_preserved": False,
            "service_requests": 0,
            "store_schema": {"before": schemas[0], "after": schemas[1]},
            "schema_10_state": "before-update"
            if schemas[0] >= 10
            else "after-upgrade"
            if schemas[1] >= 10
            else "unavailable",
            "model_defaults_preserved": claimed,
        }
        (session.directory / "expected-state.json").write_text('{"workflow": null}')
        report.write_text(json.dumps(reports[name]))
        return None

    class Server:
        requests = ["/index.json", "/scenario-0.0.0.zip", "/scenario-1.2.3.zip"]
        socket = SimpleNamespace(fileno=lambda: -1)

    @contextlib.contextmanager
    def serve(_repository, _archives):
        yield Server(), "http://127.0.0.1:9/index.json"

    monkeypatch.setattr(runner, "generate", generate)
    monkeypatch.setattr(runner, "serve", serve)
    monkeypatch.setattr(runner.Session, "step", step)
    monkeypatch.setattr(runner.Session, "cleanup", lambda _session: None)
    args = SimpleNamespace(
        blender=None,
        artifacts=tmp_path / "artifacts",
        timeout=2,
        expected_version="5.1.2",
        previous_zip=previous,
        candidate_zip=candidate,
        test_predecessor=True,
    )
    if claimed != owner:
        assert runner.run(args) == 1
        result = json.loads(next(args.artifacts.glob("*/result.json")).read_text())
        assert result["error"] == "Missing native update and enabled-state evidence"
        assert set(reports) == {"update"}
        return
    assert runner.run(args) == 0
    result = json.loads(next(args.artifacts.glob("*/result.json")).read_text())
    assert result["status"] == "passed"
    assert result["update"]["model_defaults_preserved"] is owner
    assert result["restart"]["model_defaults_preserved"] is owner
    assert result["predecessor_code"] == "previous-zip"
    assert result["previous_sha256"] == runner.sha256(previous)
    assert set(reports) == {"update", "restart"}
    assert result["update"]["store_schema"] == {"before": schemas[0], "after": schemas[1]}
    if schemas[0] < schemas[1]:
        assert result["predecessor_reopen"] == {
            "predecessor_schema": schemas[0],
            "refused": "Unsupported",
            "store_unchanged": True,
        }
    else:
        assert "predecessor_reopen" not in result


@pytest.mark.parametrize("damage", [None, "changed", "journal", "second-store"])
def test_predecessor_reopen_requires_one_unchanged_store(runner, tmp_path, damage):
    session = SimpleNamespace(profile=tmp_path / "profile", directory=tmp_path)
    database = session.profile / "extensions/.user/update_fixture/shared-jobs/jobs.sqlite3"
    database.parent.mkdir(parents=True)
    database.write_bytes(b"upgraded store")
    (database.parent / "scope.key").write_bytes(b"scope key")
    if damage == "second-store":
        other = session.profile / "elsewhere/shared-jobs/jobs.sqlite3"
        other.parent.mkdir(parents=True)
        other.write_bytes(b"other store")
    steps = []

    def step(name, args):
        steps.append((name, args))
        report = Path(args[args.index("--report") + 1])
        report.write_text(json.dumps({"predecessor_schema": 9, "refused": "Unsupported"}))
        if damage == "changed":
            database.write_bytes(b"rewritten by older code")
        elif damage == "journal":
            (database.parent / "jobs.sqlite3-journal").write_bytes(b"left behind")

    session.step = step
    package = tmp_path / "first/scenario-0.0.0.zip"
    if damage is None:
        assert runner.predecessor_reopen(session, package) == {
            "predecessor_schema": 9,
            "refused": "Unsupported",
            "store_unchanged": True,
        }
        name, args = steps[0]
        assert name == "predecessor-reopen" and "--factory-startup" in args
        assert args[args.index("--database") + 1] == str(database)
        assert args[args.index("--package") + 1] == str(package)
        return
    with pytest.raises(ValueError, match="one upgraded|changed the upgraded"):
        runner.predecessor_reopen(session, package)
    assert len(steps) == (0 if damage == "second-store" else 1)


def _predecessor_package(path, version):
    """The current storage code relabelled as an older schema, for offline mechanics only."""
    import zipfile

    with zipfile.ZipFile(path, "w") as package:
        package.writestr("__init__.py", (ROOT / "scenario/__init__.py").read_text())
        package.writestr("blender/ui.py", "raise RuntimeError('never imported')\n")
        for source in sorted((ROOT / "scenario/core").rglob("*.py")):
            text = source.read_text()
            if source.name == "store.py" and source.parent.name == "jobs":
                text = text.replace("\n_VERSION = 10\n", f"\n_VERSION = {version}\n")
                assert f"_VERSION = {version}" in text
            package.writestr(source.relative_to(ROOT / "scenario").as_posix(), text)
    return path


def test_predecessor_store_probe_refuses_newer_store_without_writing(tmp_path, monkeypatch):
    monkeypatch.syspath_prepend(str(ROOT / "tests/blender"))
    probe = importlib.import_module("predecessor_store")
    from scenario.core.jobs.store import JobScope, JobStore

    database = tmp_path / "shared-jobs/jobs.sqlite3"
    JobStore(database, JobScope("https://service.example.invalid/v1", "local-key-fixture"))
    before = database.read_bytes()
    older = _predecessor_package(tmp_path / "older.zip", 9)
    result = probe.reopen(older, database)
    assert result["predecessor_schema"] == 9 and probe.REFUSAL in result["refused"]
    assert database.read_bytes() == before
    assert sorted(path.name for path in database.parent.iterdir()) == ["jobs.sqlite3"]
    assert not any(name.startswith(probe.PACKAGE) for name in sys.modules)
    same = _predecessor_package(tmp_path / "same.zip", 10)
    with pytest.raises(RuntimeError, match="opened the upgraded"):
        probe.reopen(same, database)
    empty = tmp_path / "empty.zip"
    import zipfile

    with zipfile.ZipFile(empty, "w") as package:
        package.writestr("__init__.py", "")
    with pytest.raises(RuntimeError, match="no shared job store"):
        probe.reopen(empty, database)


def test_candidate_with_older_job_storage_stops_before_install(runner, tmp_path, monkeypatch):
    previous = _adopted(runner, tmp_path / "previous", "1.2.3", 10)
    candidate = _adopted(runner, tmp_path / "candidate", "1.2.3", 9)
    monkeypatch.setattr(runner, "normal_profile_root", lambda: tmp_path / "normal")
    monkeypatch.setattr(runner, "find_blender", lambda _: "fixture-blender")
    calls = []

    def step(session, name, _args):
        calls.append(name)
        path = session.directory / "probe.log"
        path.write_text('SCENARIO_ENV={"version":[5,1,2],"blender":"5.1.2"}\n')
        return path

    monkeypatch.setattr(runner.Session, "step", step)
    args = SimpleNamespace(
        blender=None,
        artifacts=tmp_path / "artifacts",
        timeout=2,
        expected_version="5.1.2",
        previous_zip=previous,
        candidate_zip=candidate,
        test_predecessor=True,
    )
    assert runner.run(args) == 1
    assert calls == ["probe"]
    report = json.loads(next(args.artifacts.glob("*/result.json")).read_text())
    assert "older" in report["error"]


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


def test_update_snapshot_adds_only_absent_film_and_result_fields(package_probe):
    from dataclasses import dataclass, field

    @dataclass
    class Record:
        intent: dict
        results: list = field(default_factory=list)

    old = Record({"request_id": "old"}, [{"asset": {"asset_id": "a"}, "receipt": None}])
    snapshot = package_probe.job_snapshot(old)
    assert snapshot["intent"] == {"request_id": "old", "film_task": None}
    assert snapshot["results"][0]["asset"] == {
        "asset_id": "a",
        "source": "asset",
        "projection": None,
    }
    binding = {"production_id": "production", "task_id": "take", "task_sha256": "a" * 64}
    bound = Record({"film_task": binding})
    assert package_probe.job_snapshot(bound)["intent"]["film_task"] == binding
    cloud = Record({"source": "cloud"})
    assert package_probe.job_snapshot(cloud)["intent"] == {"source": "cloud"}
    assert old.intent == {"request_id": "old"}
    assert old.results[0]["asset"] == {"asset_id": "a"}
    saved = {"asset_id": "b", "source": "original", "projection": "equirectangular"}
    current = Record({"request_id": "new"}, [{"asset": dict(saved), "receipt": None}])
    assert package_probe.job_snapshot(current)["results"][0]["asset"] == saved


def test_package_probe_seeds_and_detects_lost_schema_ten_state(package_probe, tmp_path):
    from contextlib import nullcontext
    from dataclasses import replace

    from scenario.core.jobs import store as jobs
    from scenario.core.jobs.results import ResultCommands
    from scenario.core.jobs.transfers import ResultDownloader, StoragePolicy

    scope = jobs.JobScope("https://fixture.invalid", "update-account", "project")
    path = tmp_path / "jobs.sqlite3"
    selected = jobs.JobStore(path, scope)
    other = jobs.JobStore(path, replace(scope, account_id="other-account"))
    (tmp_path / "results").mkdir()
    results = ResultCommands(
        SimpleNamespace(),
        selected,
        nullcontext,
        downloader=ResultDownloader(
            StoragePolicy(frozenset({"fixture.invalid"})), online_access=lambda: False
        ),
        root=tmp_path / "results",
    )
    assert package_probe.supports_schema_10()
    assert package_probe.trained_defaults_snapshot(selected, other) is None
    package_probe.seed_schema_10(selected, results, jobs.JobOrigin(*package_probe.ORIGIN))
    package_probe.check_schema_10(selected, results)
    snapshot = package_probe.trained_defaults_snapshot(selected, other)
    assert snapshot["image"]["default"]["picks"] == ({"model_id": "update-lora", "scale": 0.75},)
    assert snapshot["render_image"] == {"lane": "render_image", "revision": 2, "default": None}
    state = tmp_path / "state"
    (state / "shared-jobs").mkdir(parents=True)
    jobs.JobStore(state / "shared-jobs/jobs.sqlite3", scope)
    before = (state / "shared-jobs/jobs.sqlite3").read_bytes()
    assert package_probe.store_schema(SimpleNamespace(state_dir=state)) == 10
    assert (state / "shared-jobs/jobs.sqlite3").read_bytes() == before
    leaked = jobs.TrainedModelDefault("image", "custom", "update-private-model")
    other.set_trained_default(leaked, expected_revision=0)
    with pytest.raises(RuntimeError, match="credential scope"):
        package_probe.trained_defaults_snapshot(selected, other)
    selected.clear_trained_default("image", expected_revision=1)
    with pytest.raises(RuntimeError, match="trained-model default"):
        package_probe.check_schema_10(selected, results)
    assert package_probe.trained_defaults_snapshot(SimpleNamespace(), other) is None


def test_package_probe_reads_defaults_through_the_runtime_owner(package_probe, tmp_path):
    from contextlib import nullcontext
    from dataclasses import replace

    from scenario.core.jobs import store as jobs
    from scenario.core.jobs.model_defaults import DefaultsRetired, ModelDefaults
    from scenario.core.jobs.results import ResultCommands
    from scenario.core.jobs.transfers import ResultDownloader, StoragePolicy

    scope = jobs.JobScope("https://fixture.invalid", "update-account", "project")
    path = tmp_path / "jobs.sqlite3"
    selected = jobs.JobStore(path, scope)
    (tmp_path / "results").mkdir()
    results = ResultCommands(
        SimpleNamespace(),
        selected,
        nullcontext,
        downloader=ResultDownloader(
            StoragePolicy(frozenset({"fixture.invalid"})), online_access=lambda: False
        ),
        root=tmp_path / "results",
    )
    origin = jobs.JobOrigin(*package_probe.ORIGIN)
    owner = ModelDefaults(selected)
    assert package_probe.check_model_defaults(selected, None) is False
    with pytest.raises(RuntimeError, match="lost the saved default"):
        package_probe.check_model_defaults(selected, owner)
    retired = ModelDefaults(selected)
    retired.retire()
    with pytest.raises(DefaultsRetired):
        package_probe.seed_schema_10(selected, results, origin, retired)
    assert selected.trained_defaults() == ()
    package_probe.seed_schema_10(selected, results, origin, owner)
    package_probe.check_schema_10(selected, results)
    assert package_probe.check_model_defaults(selected, owner) is True
    for project in (None, "other-project"):
        foreign = ModelDefaults(jobs.JobStore(path, replace(scope, project_id=project)))
        with pytest.raises(RuntimeError, match="another credential or project scope"):
            package_probe.check_model_defaults(selected, foreign)
    stale = SimpleNamespace(
        scope=scope,
        lane=lambda lane: jobs.TrainedDefaultState(lane, 0),
        saved=selected.trained_defaults,
    )
    with pytest.raises(RuntimeError, match="differ from the saved store"):
        package_probe.check_model_defaults(selected, stale)


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


@pytest.mark.parametrize("project_id", [None, "", "update-other-project"])
def test_package_probe_rejects_lost_preference_or_runtime_project(package_probe, project_id):
    selected = SimpleNamespace(scope=SimpleNamespace(project_id=project_id))
    prefs = SimpleNamespace(project_id=package_probe.PROJECT_ID)
    with pytest.raises(RuntimeError, match="project preference or runtime scope"):
        package_probe.check_project_scope(None, prefs, selected)
    selected.scope.project_id = package_probe.PROJECT_ID
    prefs.project_id = project_id
    with pytest.raises(RuntimeError, match="project preference or runtime scope"):
        package_probe.check_project_scope(None, prefs, selected)


@pytest.mark.parametrize("other_project", [None, "update-other-project"])
@pytest.mark.parametrize("record_kind", ["job", "upload", "default", "cleared-default"])
def test_package_probe_detects_records_outside_saved_project(
    package_probe, tmp_path, other_project, record_kind
):
    from scenario.core.api.sdk_adapter import Credentials
    from scenario.core.jobs.credential_storage import open_credential_store
    from scenario.core.jobs.store import JobIntent, JobOrigin, TrainedModelDefault
    from scenario.core.jobs.upload_sources import UploadSources
    from scenario.core.jobs.upload_store import UploadStore

    paths = SimpleNamespace(state_dir=tmp_path)
    prefs = SimpleNamespace(
        project_id=package_probe.PROJECT_ID, api_key="fixture-key", api_secret="fixture-secret"
    )
    credentials = Credentials(prefs.api_key, prefs.api_secret)
    selected = open_credential_store(
        tmp_path / "shared-jobs", credentials, project_id=prefs.project_id
    )
    origin = JobOrigin("file", "scene", "revision")
    selected.create(
        JobIntent("selected", selected.scope, origin, "model", "model", "a" * 64, "b" * 64, "1")
    )
    (tmp_path / "shared-uploads").mkdir()
    selected.set_trained_default(
        TrainedModelDefault("image", "custom", "update-private-model"), expected_revision=0
    )
    package_probe.check_project_scope(paths, prefs, selected)
    other = open_credential_store(tmp_path / "shared-jobs", credentials, project_id=other_project)
    message = "job or upload project isolation"
    if record_kind == "job":
        other.create(
            JobIntent("escaped", other.scope, origin, "model", "model", "a" * 64, "b" * 64, "1")
        )
    elif record_kind.endswith("default"):
        message = "trained-model default project isolation"
        escaped = TrainedModelDefault("render_image", "custom", "update-private-model")
        other.set_trained_default(escaped, expected_revision=0)
        if record_kind == "cleared-default":
            # A cleared row still proves a write landed in the wrong project.
            other.clear_trained_default("render_image", expected_revision=1)
    else:
        source = tmp_path / "source.png"
        source.write_bytes(b"synthetic update reference")
        sources_root = tmp_path / "sources"
        sources_root.mkdir()
        intent = UploadSources(sources_root).stage(
            source,
            request_id="escaped",
            scope=other.scope,
            origin=origin,
            kind="image",
            content_type="image/png",
        )
        UploadStore(tmp_path / "shared-uploads/uploads.sqlite3", other.scope).create(intent)
    with pytest.raises(RuntimeError, match=message):
        package_probe.check_project_scope(paths, prefs, selected)
