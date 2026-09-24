# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Published-release selection must retain compatibility without repairing old ZIPs."""

import copy
import hashlib
import importlib
import json
import zipfile
from pathlib import Path

import pytest


@pytest.fixture
def selector(monkeypatch):
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[2] / "tools"))
    return importlib.import_module("release_inventory")


class Releases:
    def __init__(self, directory):
        self.assets = directory / "assets"
        self.assets.mkdir()
        self.snapshot = directory / "releases.json"
        self.rows = []

    def add(self, version="1.0.0", *, minimum="5.0.0", maximum=None, platforms=None, extra=""):
        tag = f"blender-plugin-v{version}"
        directory = self.assets / tag
        directory.mkdir()
        name = f"scenario-{version}.zip"
        manifest = (
            'schema_version = "1.0.0"\nid = "scenario"\nname = "Fixture"\n'
            'tagline = "Synthetic repository fixture"\nmaintainer = "Fixture"\n'
            'type = "add-on"\nlicense = ["SPDX:GPL-3.0-or-later"]\n'
            f'version = "{version}"\nblender_version_min = "{minimum}"\n'
        )
        if maximum:
            manifest += f'blender_version_max = "{maximum}"\n'
        if platforms:
            manifest += "platforms = " + json.dumps(platforms) + "\n"
        with zipfile.ZipFile(directory / name, "w") as archive:
            archive.writestr("blender_manifest.toml", manifest + extra)
            archive.writestr("__init__.py", "def register(): pass\ndef unregister(): pass\n")
            archive.writestr("LICENSE", "Synthetic fixture notice\n")
        digest = hashlib.sha256((directory / name).read_bytes()).hexdigest()
        (directory / "SHA256SUMS").write_text(f"{digest}  {name}\n", encoding="ascii")
        url = "https://github.com/scenario-labs/blender-plugin/releases"
        row = {
            "tag_name": tag,
            "draft": False,
            "prerelease": False,
            "published_at": "2026-01-01T00:00:00Z",
            "html_url": f"{url}/tag/{tag}",
            "assets": [
                {
                    "name": asset,
                    "state": "uploaded",
                    "browser_download_url": f"{url}/download/{tag}/{asset}",
                    "size": (directory / asset).stat().st_size,
                }
                for asset in (name, "SHA256SUMS")
            ],
        }
        self.rows.append(row)
        return row, directory / name

    def save(self):
        # Multiple pages are part of the snapshot contract.
        self.snapshot.write_text(json.dumps([self.rows[:1], self.rows[1:]]), encoding="utf-8")
        return self.snapshot

    def prepare(self, selector, output, *, versions=None, platforms=None):
        return selector.prepare(
            self.save(),
            self.assets,
            output,
            versions or ["5.0.0", "5.1.0", "5.2.0"],
            platforms or ["linux-x64", "windows-x64", "macos-arm64"],
        )


def test_numeric_selection_and_retention_are_deterministic(selector, tmp_path):
    releases = Releases(tmp_path)
    _, old = releases.add("1.0.0", maximum="5.1.0")
    newest, new = releases.add("1.10.0", minimum="5.1.0")
    releases.add("1.9.0", minimum="5.1.0")
    # An older publication date must not win over the numeric release version.
    newest["published_at"] = "2020-01-01T00:00:00Z"
    first = releases.prepare(selector, tmp_path / "one")
    selected = json.loads(first.read_text())
    assert [row["version"] for row in selected["archives"]] == ["1.0.0", "1.10.0"]
    assert set(path.name for path in first.parent.iterdir()) == {
        "inventory.json",
        old.name,
        new.name,
    }
    assert (first.parent / old.name).read_bytes() == old.read_bytes()
    assert (first.parent / new.name).read_bytes() == new.read_bytes()
    releases.rows.reverse()
    second = releases.prepare(selector, tmp_path / "two")
    assert first.read_bytes() == second.read_bytes()
    repository = importlib.import_module("repository")
    assert repository.read_inventory(first) == selected
    assert not list(tmp_path.glob(".release-inventory-*"))


def test_disjoint_platforms_preserve_older_release(selector, tmp_path):
    releases = Releases(tmp_path)
    releases.add("1.0.0", platforms=["windows-x64"])
    releases.add("2.0.0", platforms=["linux-x64", "macos-arm64"])
    inventory = releases.prepare(selector, tmp_path / "selected")
    assert len(json.loads(inventory.read_text())["archives"]) == 2


def test_generated_platform_override_controls_selection(selector, tmp_path):
    releases = Releases(tmp_path)
    releases.add("1.0.0", platforms=["windows-x64"])
    releases.add(
        "2.0.0",
        platforms=["windows-x64", "linux-x64", "macos-arm64"],
        extra='[build.generated]\nplatforms = ["linux-x64", "macos-arm64"]\n',
    )
    inventory = releases.prepare(selector, tmp_path / "selected")
    assert len(json.loads(inventory.read_text())["archives"]) == 2


def test_draft_prerelease_and_prototype_tags_need_no_assets(selector, tmp_path):
    releases = Releases(tmp_path)
    row, _ = releases.add()
    for tag, flags in [
        ("v0.9.9", {}),
        ("blender-plugin-v9.0.0", {"draft": True}),
        ("blender-plugin-v10.0.0-rc.1", {"prerelease": True}),
    ]:
        releases.rows.append({**row, **flags, "tag_name": tag, "assets": []})
    inventory = releases.prepare(selector, tmp_path / "selected")
    assert [item["version"] for item in json.loads(inventory.read_text())["archives"]] == ["1.0.0"]


@pytest.mark.parametrize(
    "field,value",
    [
        ("tag_name", "blender-plugin-v1.0.0/../../other"),
        ("tag_name", "blender-plugin-v1.0.0-rc.1"),
        ("tag_name", "blender-plugin-v01.0.0"),
        ("draft", 0),
        ("prerelease", None),
        ("html_url", "https://github.com/other/repo/releases/tag/blender-plugin-v1.0.0"),
        ("published_at", None),
        ("published_at", "2026-01-01T00:00:00"),
        ("assets", []),
        ("assets", [None]),
    ],
)
def test_malformed_newest_release_never_falls_back(selector, tmp_path, field, value):
    releases = Releases(tmp_path)
    releases.add()
    newest, _ = releases.add("2.0.0")
    newest[field] = value
    with pytest.raises(ValueError):
        releases.prepare(selector, tmp_path / "selected")
    assert not (tmp_path / "selected").exists()


@pytest.mark.parametrize(
    "field,value",
    [
        ("name", "../scenario-2.0.0.zip"),
        ("state", "new"),
        ("browser_download_url", "https://example.invalid/scenario-2.0.0.zip"),
        ("size", 0),
        ("size", True),
        ("size", 256 * 1024 * 1024 + 1),
        ("size", 1),
    ],
)
def test_invalid_newest_asset_never_falls_back(selector, tmp_path, field, value):
    releases = Releases(tmp_path)
    releases.add()
    row, _ = releases.add("2.0.0")
    row["assets"][0][field] = value
    with pytest.raises(ValueError):
        releases.prepare(selector, tmp_path / "selected")
    assert not (tmp_path / "selected").exists()


@pytest.mark.parametrize("kind", ["release", "archive", "checksum"])
def test_duplicate_identities_rejected(selector, tmp_path, kind):
    releases = Releases(tmp_path)
    row, _ = releases.add()
    if kind == "release":
        releases.rows.append(copy.deepcopy(row))
    else:
        row["assets"].append(copy.deepcopy(row["assets"][kind == "checksum"]))
    with pytest.raises(ValueError, match="Duplicate|exactly one"):
        releases.prepare(selector, tmp_path / "selected")


@pytest.mark.parametrize("problem", ["hash", "size", "missing", "identity", "version", "sdk"])
def test_newest_local_asset_damage_never_falls_back(selector, tmp_path, problem):
    releases = Releases(tmp_path)
    releases.add()
    row, source = releases.add("2.0.0")
    if problem == "hash":
        raw = source.read_bytes()
        source.write_bytes(raw[:-1] + bytes([raw[-1] ^ 1]))
    elif problem == "size":
        source.write_bytes(source.read_bytes()[:-1])
    elif problem == "missing":
        source.unlink()
    else:
        with zipfile.ZipFile(source) as archive:
            files = {name: archive.read(name) for name in archive.namelist()}
        manifest = files["blender_manifest.toml"]
        if problem == "identity":
            manifest = manifest.replace(b'id = "scenario"', b'id = "other"')
        elif problem == "version":
            manifest = manifest.replace(b'version = "2.0.0"', b'version = "3.0.0"')
        else:
            manifest += b'wheels = ["./wheels/sdk-1.0.0-py3-none-any.whl"]\n'
        files["blender_manifest.toml"] = manifest
        with zipfile.ZipFile(source, "w") as archive:
            for name, raw in files.items():
                archive.writestr(name, raw)
        row["assets"][0]["size"] = source.stat().st_size
        digest = hashlib.sha256(source.read_bytes()).hexdigest()
        (source.parent / "SHA256SUMS").write_text(f"{digest}  {source.name}\n")
    with pytest.raises((ValueError, KeyError)):
        releases.prepare(selector, tmp_path / "selected")
    assert not (tmp_path / "selected").exists()


@pytest.mark.parametrize(
    "content",
    [
        "invalid",
        "0" * 64 + "  ../escape.zip\n",
        "0" * 64 + "  other.zip\n",
        "0" * 64 + "  SCENARIO-1.0.0.ZIP\n",
    ],
)
def test_checksum_content_is_bounded_and_unambiguous(selector, tmp_path, content):
    releases = Releases(tmp_path)
    row, source = releases.add()
    (source.parent / "SHA256SUMS").write_text(content)
    row["assets"][1]["size"] = len(content)
    with pytest.raises(ValueError):
        releases.prepare(selector, tmp_path / "selected")


def test_checksum_cannot_have_duplicate_casefolded_filenames(selector, tmp_path):
    releases = Releases(tmp_path)
    row, source = releases.add()
    checksum = source.parent / "SHA256SUMS"
    first = checksum.read_text()
    checksum.write_text(first + first.replace(source.name, source.name.upper()))
    row["assets"][1]["size"] = checksum.stat().st_size
    with pytest.raises(ValueError, match="duplicate"):
        releases.prepare(selector, tmp_path / "selected")


@pytest.mark.parametrize("target", ["root", "release", "archive", "checksum", "snapshot"])
def test_symlink_inputs_rejected(selector, tmp_path, target):
    releases = Releases(tmp_path)
    _, source = releases.add()
    snapshot = releases.save()
    path = {
        "root": releases.assets,
        "release": source.parent,
        "archive": source,
        "checksum": source.parent / "SHA256SUMS",
        "snapshot": snapshot,
    }[target]
    destination = tmp_path / "relocated"
    path.rename(destination)
    path.symlink_to(destination, target_is_directory=destination.is_dir())
    with pytest.raises(ValueError):
        selector.prepare(snapshot, releases.assets, tmp_path / "selected", ["5.0.0"], ["linux-x64"])


@pytest.mark.parametrize("rows", [[], [{"tag_name": "v0.9.9"}]])
def test_empty_adopted_channel_rejected(selector, tmp_path, rows):
    releases = Releases(tmp_path)
    releases.rows = rows
    with pytest.raises(ValueError, match="published stable"):
        releases.prepare(selector, tmp_path / "selected")


@pytest.mark.parametrize("value", [{}, [None], [{"tag_name": "blender-plugin-v1.0.0"}]])
def test_snapshot_requires_paginated_export(selector, tmp_path, value):
    path = tmp_path / "releases.json"
    path.write_text(json.dumps(value))
    with pytest.raises(ValueError, match="paginated"):
        selector.published_releases(path)


@pytest.mark.parametrize(
    "versions,platforms",
    [
        ([], ["linux-x64"]),
        (["5.0.0"], []),
        (["4.5.0"], ["linux-x64"]),
        (["5.0"], ["linux-x64"]),
        (["5.0.0"], ["../linux"]),
    ],
)
def test_targets_are_explicit_and_valid(selector, versions, platforms):
    with pytest.raises(ValueError):
        selector.select([], versions, platforms)


@pytest.mark.parametrize("restriction", ["version", "platform"])
def test_uncovered_matrix_cannot_produce_partial_inventory(selector, tmp_path, restriction):
    releases = Releases(tmp_path)
    releases.add(
        maximum="5.2.0" if restriction == "version" else None,
        platforms=["linux-x64"] if restriction == "platform" else None,
    )
    with pytest.raises(ValueError, match="every requested"):
        releases.prepare(selector, tmp_path / "selected")
    assert not (tmp_path / "selected").exists()


def test_selected_overlap_rejected_without_rewriting_old_manifests(selector, tmp_path):
    releases = Releases(tmp_path)
    _, old = releases.add()
    _, new = releases.add("2.0.0", minimum="5.1.0")
    before = [old.read_bytes(), new.read_bytes()]
    with pytest.raises(ValueError, match="overlapping"):
        releases.prepare(selector, tmp_path / "selected")
    assert [old.read_bytes(), new.read_bytes()] == before
    assert not (tmp_path / "selected").exists()


def test_existing_snapshot_preserved(selector, tmp_path):
    releases = Releases(tmp_path)
    releases.add()
    output = tmp_path / "selected"
    output.mkdir()
    (output / "sentinel").write_text("previous snapshot")
    with pytest.raises(ValueError, match="already exists"):
        releases.prepare(selector, output)
    assert (output / "sentinel").read_text() == "previous snapshot"


def test_copy_tampering_leaves_no_partial_inventory(selector, tmp_path, monkeypatch):
    releases = Releases(tmp_path)
    releases.add()
    monkeypatch.setattr(
        selector.shutil, "copyfile", lambda _, target: target.write_bytes(b"changed")
    )
    with pytest.raises(ValueError, match="SHA-256"):
        releases.prepare(selector, tmp_path / "selected")
    assert not (tmp_path / "selected").exists()
    assert not list(tmp_path.glob(".release-inventory-*"))


@pytest.mark.parametrize("kind", ["snapshot", "checksum", "checksum-size"])
def test_metadata_limits_checked_before_parsing(selector, tmp_path, kind):
    releases = Releases(tmp_path)
    row, source = releases.add()
    snapshot = releases.save()
    if kind == "snapshot":
        with snapshot.open("wb") as handle:
            handle.truncate(10 * selector.MAX_METADATA + 1)
    elif kind == "checksum":
        with (source.parent / "SHA256SUMS").open("wb") as handle:
            handle.truncate(selector.MAX_METADATA + 1)
    else:
        row["assets"][1]["size"] += 1
        releases.save()
    with pytest.raises(ValueError, match="bounded|size"):
        selector.prepare(snapshot, releases.assets, tmp_path / "selected", ["5.0.0"], ["linux-x64"])


def test_cli_reports_corrupt_snapshot_without_output(selector, tmp_path, monkeypatch, capsys):
    releases = Releases(tmp_path)
    releases.snapshot.write_bytes(b"invalid")
    monkeypatch.setattr(
        selector.sys,
        "argv",
        [
            "release_inventory.py",
            "--releases",
            str(releases.snapshot),
            "--assets",
            str(releases.assets),
            "--output",
            str(tmp_path / "selected"),
            "--blender-version",
            "5.0.0",
            "--platform",
            "linux-x64",
        ],
    )
    assert selector.main() == 1
    assert capsys.readouterr().err.startswith("Release inventory failed:")
    assert not (tmp_path / "selected").exists()
