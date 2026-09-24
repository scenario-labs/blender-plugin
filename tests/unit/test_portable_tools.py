# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Artifact selection, download verification and disposable tool profiles."""

import importlib
import io
import tarfile
import zipfile
from pathlib import Path

import pytest


@pytest.fixture
def tools(monkeypatch):
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[2] / "tools"))
    return importlib.import_module("build"), importlib.import_module("fetch_blender")


def test_build_selects_manifest_zip_and_does_not_copy_a_stale_newer_zip(
    tools, tmp_path, monkeypatch
):
    build, _ = tools

    def stage(source, destination):
        destination.mkdir(parents=True)
        (destination / "fixture.whl").write_bytes(b"staged wheel")
        return destination

    monkeypatch.setattr(build, "prepare_source", stage)
    monkeypatch.setattr(build, "validate_bundle", lambda candidate: None)
    output = tmp_path / "output"
    output.mkdir()
    stale = output / "scenario-99.0.0.zip"
    stale.write_text("stale")
    session = build.Session(Path("blender"), tmp_path / "artifacts")
    steps = []

    def step(name, args):
        steps.append((name, args))
        if name == "build":
            candidate = Path(args[args.index("--output-filepath") + 1])
            with zipfile.ZipFile(candidate, "w") as archive:
                for name in ("blender_manifest.toml", "LICENSE", "__init__.py"):
                    archive.write(build.ROOT / "scenario" / name, name)

    session.step = step
    candidate = build.build(session, output)
    assert candidate != stale
    assert steps[-1] == (
        "validate",
        ["--command", "extension", "validate", str(session.directory / candidate.name)],
    )
    assert stale.read_text() == "stale"
    assert (session.temporary / "source/fixture.whl").is_file()
    session.cleanup()
    assert session.directory.exists()
    assert not session.profile.exists()
    assert not session.temporary.exists()
    assert (session.directory / candidate.name).is_file()


def test_sessions_never_reuse_inherited_profiles(tools, monkeypatch, tmp_path):
    build, _ = tools
    normal = tmp_path / "normal"
    normal.mkdir()
    monkeypatch.setenv("BLENDER_USER_RESOURCES", str(normal))
    monkeypatch.setenv("SCENARIO_TEST_API_KEY", "private")
    first = build.Session(Path("blender"), tmp_path)
    second = build.Session(Path("blender"), tmp_path)
    assert first.profile != second.profile != normal
    assert "SCENARIO_TEST_API_KEY" not in first.env
    first.cleanup()
    assert second.profile.is_dir() and normal.is_dir()


def make_tar(path, name="blender-5.0.1-linux-x64/blender", content=b"binary"):
    with tarfile.open(path, "w:xz") as archive:
        entry = tarfile.TarInfo(name)
        entry.size = len(content)
        entry.mode = 0o755
        archive.addfile(entry, io.BytesIO(content))


def test_fetch_verifies_cached_archive_and_reextracts_modified_install(
    tools, monkeypatch, tmp_path
):
    _, fetch = tools
    source = tmp_path / "source.tar.xz"
    make_tar(source)
    digest = fetch.sha256(source)
    downloads = []

    def download(url, destination):
        downloads.append(url)
        destination.write_bytes(source.read_bytes())

    monkeypatch.setattr(fetch, "download", download)
    first = fetch.fetch("5.0.1", tmp_path / "cache", digest)
    first.write_bytes(b"modified")
    second = fetch.fetch("5.0.1", tmp_path / "cache", digest)
    assert second == first
    assert second.read_bytes() == b"binary"
    assert len(list((tmp_path / "cache").glob("5.0.1-*"))) == 1
    assert len(downloads) == 1
    archive = next((tmp_path / "cache").glob("*.tar.xz.*"))
    archive.write_bytes(b"corrupt")
    fetch.fetch("5.0.1", tmp_path / "cache", digest)
    assert len(downloads) == 2


def test_fetch_rejects_wrong_checksum_before_extraction(tools, monkeypatch, tmp_path):
    _, fetch = tools
    monkeypatch.setattr(fetch, "download", lambda url, path: path.write_bytes(b"bad"))
    with pytest.raises(ValueError, match="SHA-256 mismatch"):
        fetch.fetch("5.0.1", tmp_path, "0" * 64)
    assert list(tmp_path.iterdir()) == []


def test_fetch_rejects_tar_path_escape(tools, monkeypatch, tmp_path):
    _, fetch = tools
    source = tmp_path / "source.tar.xz"
    make_tar(source, "../../escaped")
    monkeypatch.setattr(fetch, "download", lambda url, path: path.write_bytes(source.read_bytes()))
    with pytest.raises(tarfile.TarError):
        fetch.fetch("5.0.1", tmp_path / "cache", fetch.sha256(source))
    assert not (tmp_path / "escaped").exists()


def test_official_checksum_requires_exact_filename(tools):
    _, fetch = tools
    digest = "a" * 64
    assert fetch.checksum(f"{digest} *blender.tar.xz", "blender.tar.xz") == digest
    with pytest.raises(ValueError):
        fetch.checksum(f"{digest} other.tar.xz", "blender.tar.xz")


def test_download_identifies_the_tool_to_the_official_server(tools, monkeypatch, tmp_path):
    _, fetch = tools
    requests = []

    def open_url(request, timeout):
        requests.append((request, timeout))
        return io.BytesIO(b"archive bytes")

    monkeypatch.setattr(fetch.urllib.request, "urlopen", open_url)
    destination = tmp_path / "download"
    fetch.download("https://download.blender.org/release/example", destination)
    assert destination.read_bytes() == b"archive bytes"
    assert requests[0][0].get_header("User-agent") == "scenario-blender-tools/1.0"
    assert requests[0][1] == 120


@pytest.mark.parametrize("expected", [None, ""])
def test_missing_or_empty_checksum_uses_official_lookup(tools, monkeypatch, tmp_path, expected):
    _, fetch = tools
    source = tmp_path / "source.tar.xz"
    make_tar(source)
    digest = fetch.sha256(source)
    downloads = []

    def download(url, destination):
        downloads.append(url)
        if url.endswith(".sha256"):
            destination.write_text(f"{digest}  blender-5.0.1-linux-x64.tar.xz\n")
        else:
            destination.write_bytes(source.read_bytes())

    monkeypatch.setattr(fetch, "download", download)
    assert fetch.fetch("5.0.1", tmp_path / "cache", expected).read_bytes() == b"binary"
    assert downloads[0].endswith("blender-5.0.1.sha256")
    assert len(downloads) == 2


def test_failed_extraction_preserves_previous_installation(tools, monkeypatch, tmp_path):
    _, fetch = tools
    source = tmp_path / "source.tar.xz"
    make_tar(source)
    digest = fetch.sha256(source)
    monkeypatch.setattr(fetch, "download", lambda url, path: path.write_bytes(source.read_bytes()))
    binary = fetch.fetch("5.0.1", tmp_path / "cache", digest)

    def fail(*args, **kwargs):
        raise tarfile.ReadError("fixture extraction failure")

    monkeypatch.setattr(fetch.tarfile.TarFile, "extractall", fail)
    with pytest.raises(tarfile.ReadError, match="fixture extraction failure"):
        fetch.fetch("5.0.1", tmp_path / "cache", digest)
    assert binary.read_bytes() == b"binary"
    assert len(list((tmp_path / "cache").glob("5.0.1-*"))) == 1
    assert not list((tmp_path / "cache").glob("fetch-*"))
    assert not list((tmp_path / "cache").glob("*.lock"))


def test_fetch_does_not_replace_unmanaged_directories(tools, monkeypatch, tmp_path):
    _, fetch = tools
    source = tmp_path / "source.tar.xz"
    make_tar(source)
    digest = fetch.sha256(source)
    installation = tmp_path / "cache" / f"5.0.1-{digest}"
    installation.mkdir(parents=True)
    sentinel = installation / "keep"
    sentinel.write_text("user file")
    monkeypatch.setattr(fetch, "download", lambda url, path: path.write_bytes(source.read_bytes()))
    with pytest.raises(ValueError, match="unmanaged installation"):
        fetch.fetch("5.0.1", tmp_path / "cache", digest)
    assert sentinel.read_text() == "user file"


def test_fetch_refuses_concurrent_installation_changes(tools, tmp_path):
    _, fetch = tools
    with fetch.installation_lock(tmp_path, "5.0.1"):
        with pytest.raises(ValueError, match="Cache lock exists"):
            fetch.fetch("5.0.1", tmp_path, "a" * 64)
    assert not (tmp_path / ".fetch-5.0.1.lock").exists()


def test_failed_publication_restores_previous_installation(tools, monkeypatch, tmp_path):
    _, fetch = tools
    source = tmp_path / "source.tar.xz"
    make_tar(source)
    digest = fetch.sha256(source)
    monkeypatch.setattr(fetch, "download", lambda url, path: path.write_bytes(source.read_bytes()))
    binary = fetch.fetch("5.0.1", tmp_path / "cache", digest)
    rename = Path.rename

    def fail_publication(path, target):
        if path.name == "installation":
            raise OSError("fixture publication failure")
        return rename(path, target)

    monkeypatch.setattr(Path, "rename", fail_publication)
    with pytest.raises(OSError, match="fixture publication failure"):
        fetch.fetch("5.0.1", tmp_path / "cache", digest)
    assert binary.read_bytes() == b"binary"
    assert len(list((tmp_path / "cache").glob("5.0.1-*"))) == 1
    assert not list((tmp_path / "cache").glob("fetch-*"))


def test_windows_fetch_verifies_reuses_and_reextracts_zip(tools, monkeypatch, tmp_path):
    _, fetch = tools
    source = tmp_path / "source.zip"
    with zipfile.ZipFile(source, "w") as archive:
        archive.writestr("blender-5.0.1-windows-x64/blender.exe", b"windows binary")
    digest = fetch.sha256(source)
    downloads = []

    def download(url, destination):
        downloads.append(url)
        destination.write_bytes(source.read_bytes())

    monkeypatch.setattr(fetch, "download", download)
    binary = fetch.fetch("5.0.1", tmp_path / "cache", digest, platform_name="windows-x64")
    assert binary.name == "blender.exe"
    binary.write_bytes(b"modified")
    assert (
        fetch.fetch("5.0.1", tmp_path / "cache", digest, platform_name="windows-x64").read_bytes()
        == b"windows binary"
    )
    assert downloads == [
        "https://download.blender.org/release/Blender5.0/blender-5.0.1-windows-x64.zip"
    ]


@pytest.mark.parametrize("member", ["../escaped", "/absolute", "C:/absolute", "a\\b", "dir./file"])
def test_windows_fetch_rejects_unsafe_members(tools, monkeypatch, tmp_path, member):
    _, fetch = tools
    source = tmp_path / "source.zip"
    with zipfile.ZipFile(source, "w") as archive:
        archive.writestr("blender-5.0.1-windows-x64/blender.exe", b"binary")
        archive.writestr(member, b"unsafe")
    monkeypatch.setattr(fetch, "download", lambda url, path: path.write_bytes(source.read_bytes()))
    with pytest.raises(ValueError, match="Unsafe or ambiguous"):
        fetch.fetch("5.0.1", tmp_path / "cache", fetch.sha256(source), platform_name="windows-x64")
    assert not list((tmp_path / "cache").glob("5.0.1-*"))
    assert not list((tmp_path / "cache").glob("*.lock"))


def test_windows_fetch_rejects_case_aliases(tools, monkeypatch, tmp_path):
    _, fetch = tools
    source = tmp_path / "source.zip"
    with zipfile.ZipFile(source, "w") as archive:
        archive.writestr("blender-5.0.1-windows-x64/blender.exe", b"binary")
        archive.writestr("blender-5.0.1-windows-x64/BLENDER.EXE", b"different")
    monkeypatch.setattr(fetch, "download", lambda url, path: path.write_bytes(source.read_bytes()))
    with pytest.raises(ValueError, match="Unsafe or ambiguous"):
        fetch.fetch("5.0.1", tmp_path / "cache", fetch.sha256(source), platform_name="windows-x64")


def test_windows_missing_executable_preserves_previous_installation(tools, tmp_path):
    _, fetch = tools
    installation = tmp_path / "installed"
    installation.mkdir()
    (installation / ".scenario-fetch.json").write_text('{"sha256": "fixture"}')
    (installation / "keep").write_bytes(b"old binary")
    source = tmp_path / "source.zip"
    with zipfile.ZipFile(source, "w") as archive:
        archive.writestr("other-file", b"wrong layout")
    with pytest.raises(ValueError, match="expected Blender executable"):
        fetch.install_archive(source, installation, tmp_path, "fixture", "5.0.1", "windows-x64")
    assert (installation / "keep").read_bytes() == b"old binary"
