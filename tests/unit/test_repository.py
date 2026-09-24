# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Exact release-inventory verification without rebuilding or publishing archives."""

import copy
import importlib
import json
import subprocess
import tomllib
import zipfile
from pathlib import Path

import pytest


@pytest.fixture
def repository(monkeypatch):
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[2] / "tools"))
    return importlib.import_module("repository")


def archive(
    directory,
    name="first.zip",
    *,
    version="1.0.0",
    minimum="5.0.0",
    maximum="5.1.0",
    platforms=None,
):
    manifest = (
        'schema_version = "1.0.0"\nid = "fixture"\nname = "Fixture"\n'
        'tagline = "Synthetic repository fixture"\nmaintainer = "Fixture"\n'
        'type = "add-on"\nlicense = ["SPDX:GPL-3.0-or-later"]\n'
        f'version = "{version}"\nblender_version_min = "{minimum}"\n'
    )
    if maximum:
        manifest += f'blender_version_max = "{maximum}"\n'
    if platforms:
        manifest += "platforms = " + json.dumps(platforms) + "\n"
    path = directory / name
    with zipfile.ZipFile(path, "w") as bundle:
        bundle.writestr("blender_manifest.toml", manifest)
        bundle.writestr("__init__.py", "def register(): pass\ndef unregister(): pass\n")
        bundle.writestr("LICENSE", "Synthetic fixture notice\n")
    return path


def inventory(repository, directory, paths):
    rows = []
    for path in paths:
        with zipfile.ZipFile(path) as bundle:
            manifest = tomllib.loads(bundle.read("blender_manifest.toml").decode())
        rows.append(
            {
                "file": path.name,
                "version": manifest["version"],
                "sha256": repository.sha256(path),
                "size": path.stat().st_size,
            }
        )
    value = {"schema_version": 1, "extension_id": "fixture", "archives": rows}
    path = directory / "inventory.json"
    path.write_text(json.dumps(value))
    return path


class NativeSession:
    """Represent the native command boundary; tampering exercises output verification."""

    def __init__(self, mutate=None, fail_validation=False):
        self.calls = []
        self.mutate = mutate
        self.fail_validation = fail_validation

    def step(self, name, args):
        self.calls.append((name, args))
        assert args[:3] == ["--offline-mode", "--command", "extension"]
        if args[3] == "validate":
            if self.fail_validation:
                raise subprocess.CalledProcessError(1, args)
            return
        assert args[3:5] == ["server-generate", "--repo-dir"]
        directory = Path(args[5])
        rows = []
        for path in sorted(directory.glob("*.zip"), reverse=True):
            import hashlib

            with zipfile.ZipFile(path) as bundle:
                manifest = tomllib.loads(bundle.read("blender_manifest.toml").decode())
            rows.append(
                {
                    **manifest,
                    "archive_url": "./" + path.name,
                    "archive_size": path.stat().st_size,
                    "archive_hash": "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest(),
                }
            )
        value = {"version": "v1", "blocklist": [], "data": rows}
        if self.mutate:
            self.mutate(value, directory)
        (directory / "index.json").write_text(json.dumps(value))


def test_all_selected_versions_retained_and_outputs_deterministic(repository, tmp_path):
    first = archive(tmp_path)
    second = archive(tmp_path, "second.zip", version="2.0.0", minimum="5.1.0", maximum=None)
    archive(tmp_path, "unselected.zip", version="99.0.0")
    selected = inventory(repository, tmp_path, [second, first])
    before = {path.name: path.read_bytes() for path in (first, second)}
    session = NativeSession()
    output = repository.generate(session, selected, tmp_path / "one")
    assert len(session.calls) == 3
    assert {path.name for path in output.iterdir()} == {
        "first.zip",
        "second.zip",
        "index.json",
        "inventory.json",
        "index.html",
    }
    index = json.loads((output / "index.json").read_text())
    assert [row["version"] for row in index["data"]] == ["1.0.0", "2.0.0"]
    for name, raw in before.items():
        assert (output / name).read_bytes() == (tmp_path / name).read_bytes() == raw
    replay = repository.generate(NativeSession(), output / "inventory.json", tmp_path / "two")
    assert {path.name: path.read_bytes() for path in replay.iterdir()} == {
        path.name: path.read_bytes() for path in output.iterdir()
    }
    assert not list(tmp_path.glob(".repository-*"))


@pytest.mark.parametrize(
    "field,value",
    [
        ("file", "../escape.zip"),
        ("file", "/absolute.zip"),
        ("file", "hidden%20name.zip"),
        ("size", 0),
        ("size", True),
        ("sha256", "bad"),
        ("version", "1.0.0-rc.1"),
        ("version", "1.0.0+build"),
    ],
)
def test_invalid_inventory_rejected_before_native_work(repository, tmp_path, field, value):
    selected = inventory(repository, tmp_path, [archive(tmp_path)])
    data = json.loads(selected.read_text())
    data["archives"][0][field] = value
    selected.write_text(json.dumps(data))
    session = NativeSession()
    with pytest.raises(ValueError):
        repository.generate(session, selected, tmp_path / "output")
    assert session.calls == []
    assert not (tmp_path / "output").exists()


@pytest.mark.parametrize(
    "problem",
    ["missing", "empty", "hash", "identity", "version", "duplicate", "no-archives", "symlink"],
)
def test_input_mismatch_cannot_produce_repository(repository, tmp_path, problem):
    path = archive(tmp_path)
    selected = inventory(repository, tmp_path, [path])
    data = json.loads(selected.read_text())
    if problem == "missing":
        path.unlink()
    elif problem == "empty":
        path.write_bytes(b"")
    elif problem == "hash":
        data["archives"][0]["sha256"] = "0" * 64
    elif problem == "identity":
        data["extension_id"] = "other"
    elif problem == "version":
        data["archives"][0]["version"] = "2.0.0"
    elif problem == "duplicate":
        data["archives"].append(copy.deepcopy(data["archives"][0]))
    elif problem == "no-archives":
        data["archives"] = []
    elif problem == "symlink":
        target = path.with_suffix(".source")
        path.rename(target)
        path.symlink_to(target)
    selected.write_text(json.dumps(data))
    with pytest.raises(ValueError):
        repository.generate(NativeSession(), selected, tmp_path / "output")
    assert not (tmp_path / "output").exists()
    assert not list(tmp_path.glob(".repository-*"))


def test_unverified_sdk_bundle_rejected_before_native_work(repository, tmp_path):
    path = archive(tmp_path)
    with zipfile.ZipFile(path) as bundle:
        contents = {name: bundle.read(name) for name in bundle.namelist()}
    contents["blender_manifest.toml"] += b'wheels = ["./wheels/sdk-1.0.0-py3-none-any.whl"]\n'
    with zipfile.ZipFile(path, "w") as bundle:
        for name, content in contents.items():
            bundle.writestr(name, content)
    selected = inventory(repository, tmp_path, [path])
    session = NativeSession()
    with pytest.raises(KeyError, match="sdk-wheel-lock.json"):
        repository.generate(session, selected, tmp_path / "output")
    assert session.calls == []
    assert not (tmp_path / "output").exists()


@pytest.mark.parametrize(
    "field,value",
    [
        ("archive_url", "https://example.invalid/first.zip"),
        ("archive_url", "./../first.zip"),
        ("archive_url", "./first.zip?token=fixture"),
        ("archive_size", 1),
        ("archive_hash", "sha256:" + "0" * 64),
        ("id", "other"),
        ("version", "2.0.0"),
        ("blender_version_min", "4.0.0"),
        ("blender_version_max", "9.0.0"),
        ("platforms", ["windows-x64"]),
        ("python_versions", ["3.13"]),
    ],
)
def test_native_index_metadata_must_match_exact_archive(repository, tmp_path, field, value):
    selected = inventory(repository, tmp_path, [archive(tmp_path)])
    session = NativeSession(lambda index, _: index["data"][0].update({field: value}))
    with pytest.raises(ValueError):
        repository.generate(session, selected, tmp_path / "output")
    assert not (tmp_path / "output").exists()


@pytest.mark.parametrize("problem", ["missing", "extra", "mutated-zip", "native-failure"])
def test_native_failures_leave_no_partial_output(repository, tmp_path, problem):
    source = archive(tmp_path)
    selected = inventory(repository, tmp_path, [source])
    original = source.read_bytes()

    def mutate(index, directory):
        if problem == "missing":
            index["data"].clear()
        elif problem == "extra":
            index["data"].append(index["data"][0])
        elif problem == "mutated-zip":
            (directory / source.name).write_bytes(b"changed")

    with pytest.raises((ValueError, subprocess.CalledProcessError)):
        repository.generate(
            NativeSession(mutate, problem == "native-failure"), selected, tmp_path / "output"
        )
    assert source.read_bytes() == original
    assert not (tmp_path / "output").exists()
    assert not list(tmp_path.glob(".repository-*"))


def test_existing_repository_is_never_replaced(repository, tmp_path):
    selected = inventory(repository, tmp_path, [archive(tmp_path)])
    output = tmp_path / "output"
    output.mkdir()
    sentinel = output / "keep"
    sentinel.write_text("previous repository")
    session = NativeSession()
    with pytest.raises(ValueError, match="already exists"):
        repository.generate(session, selected, output)
    assert sentinel.read_text() == "previous repository" and session.calls == []


@pytest.mark.parametrize("platforms", [None, ["linux-x64"]])
def test_overlapping_compatibility_is_rejected(repository, tmp_path, platforms):
    first = archive(tmp_path, platforms=["linux-x64"])
    second = archive(tmp_path, "second.zip", version="2.0.0", platforms=platforms)
    selected = inventory(repository, tmp_path, [first, second])
    with pytest.raises(ValueError, match="overlapping"):
        repository.generate(NativeSession(), selected, tmp_path / "output")


def test_disjoint_platform_archives_are_both_retained(repository, tmp_path):
    first = archive(tmp_path, platforms=["linux-x64"])
    second = archive(tmp_path, "second.zip", platforms=["windows-x64"])
    selected = inventory(repository, tmp_path, [first, second])
    output = repository.generate(NativeSession(), selected, tmp_path / "output")
    assert len(json.loads((output / "index.json").read_text())["data"]) == 2


def test_python_compatibility_uses_binary_tags_without_universal_override(repository):
    assert repository.python_versions(
        [
            "./wheels/pure-1.0.0-py3-none-any.whl",
            "./wheels/core-1.0.0-cp311-cp311-win_amd64.whl",
            "./wheels/core-1.0.0-cp313-cp313-win_amd64.whl",
        ]
    ) == ["3.11", "3.13"]
    assert repository.python_versions(["old-1.0.0-cp39-abi3-win_amd64.whl"]) == ["3"]
