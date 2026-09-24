# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Verified DMG publication and cleanup, with disk operations replaced offline."""

import importlib
import shutil
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest


@pytest.fixture
def dmg(monkeypatch, tmp_path):
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[2] / "tools"))
    fetch = importlib.import_module("fetch_blender")
    archive = tmp_path / "official.dmg"
    archive.write_bytes(b"verified disk image fixture")
    state = SimpleNamespace(
        fetch=fetch,
        archive=archive,
        digest=fetch.sha256(archive),
        downloads=[],
        commands=[],
        mounts=[],
        populate=None,
        detach_errors=0,
    )

    def populate(mount):
        binary = mount / "Blender.app/Contents/MacOS/Blender"
        binary.parent.mkdir(parents=True)
        binary.write_bytes(b"official binary")
        binary.chmod(0o755)
        (mount / "Applications").symlink_to(tmp_path / "not-copied", target_is_directory=True)

    state.populate = populate

    def download(url, destination):
        state.downloads.append(url)
        if url.endswith(".sha256"):
            destination.write_text(f"{state.digest}  blender-5.1.2-macos-arm64.dmg\n")
        else:
            destination.write_bytes(archive.read_bytes())

    def run(command, **kwargs):
        state.commands.append(command)
        assert kwargs == {"check": True, "capture_output": True, "timeout": 120}
        assert command[0] == "/usr/bin/hdiutil"
        if command[1] == "attach":
            assert {"-readonly", "-nobrowse", "-noautoopen"}.issubset(command)
            mount = Path(command[command.index("-mountpoint") + 1])
            state.mounts.append(mount)
            assert mount.is_dir()
            assert fetch.sha256(Path(command[-1])) == state.digest
            state.populate(mount)
        else:
            assert command[1] == "detach"
            mount = Path(command[-1])
            assert mount == state.mounts[-1]
            if state.detach_errors:
                state.detach_errors -= 1
                diagnostic = b"forced detach refused" if "-force" in command else b"resource busy"
                raise subprocess.CalledProcessError(1, command, stderr=diagnostic)
            # A real detach reveals the empty directory below the mounted volume.
            for child in mount.iterdir():
                if child.is_symlink() or not child.is_dir():
                    child.unlink()
                else:
                    shutil.rmtree(child)
        return subprocess.CompletedProcess(command, 0)

    monkeypatch.setattr(fetch, "download", download)
    monkeypatch.setattr(fetch.subprocess, "run", run)
    yield state
    # The OS-refuses-detach test deliberately leaves its private mount intact.
    for mount in state.mounts:
        if mount.exists():
            shutil.rmtree(mount)


def test_verified_dmg_is_reused_and_modified_installation_replaced(dmg, tmp_path):
    cache = tmp_path / "cache"
    binary = dmg.fetch.fetch("5.1.2", cache, platform_name="macos-arm64")
    assert binary.read_bytes() == b"official binary"
    assert binary.stat().st_mode & 0o111
    assert not list(cache.rglob("Applications"))
    binary.write_bytes(b"modified installation")
    assert dmg.fetch.fetch("5.1.2", cache, dmg.digest, platform_name="macos-arm64") == binary
    assert binary.read_bytes() == b"official binary"
    assert dmg.downloads == [
        "https://download.blender.org/release/Blender5.1/blender-5.1.2.sha256",
        "https://download.blender.org/release/Blender5.1/blender-5.1.2-macos-arm64.dmg",
    ]
    assert len(dmg.mounts) == 2 and dmg.mounts[0] != dmg.mounts[1]
    assert all(not mount.exists() for mount in dmg.mounts)
    assert not list(cache.glob("fetch-*"))
    assert not list(cache.glob(".fetch-*.lock"))


def test_corrupt_cached_dmg_is_downloaded_again_before_mount(dmg, tmp_path):
    cache = tmp_path / "cache"
    dmg.fetch.fetch("5.1.2", cache, dmg.digest, platform_name="macos-arm64")
    next(cache.glob("*.dmg.*")).write_bytes(b"corrupt")
    dmg.fetch.fetch("5.1.2", cache, dmg.digest, platform_name="macos-arm64")
    assert len(dmg.downloads) == 2


def test_bad_checksum_never_mounts(dmg, tmp_path):
    with pytest.raises(ValueError, match="SHA-256 mismatch"):
        dmg.fetch.fetch("5.1.2", tmp_path / "cache", "0" * 64, platform_name="macos-arm64")
    assert dmg.commands == []
    assert list((tmp_path / "cache").iterdir()) == []


@pytest.mark.parametrize("failure", ["copy", "missing-app", "missing-binary", "external-binary"])
def test_failed_extraction_detaches_and_preserves_previous_installation(
    dmg, tmp_path, monkeypatch, failure
):
    cache = tmp_path / "cache"
    binary = dmg.fetch.fetch("5.1.2", cache, dmg.digest, platform_name="macos-arm64")
    original_populate = dmg.populate

    def populate(mount):
        original_populate(mount)
        app = mount / "Blender.app"
        if failure == "missing-app":
            shutil.rmtree(app)
        else:
            executable = app / "Contents/MacOS/Blender"
            executable.unlink()
            if failure == "external-binary":
                executable.symlink_to(binary)

    if failure == "copy":

        def fail_copy(*args, **kwargs):
            raise OSError("copy interrupted")

        monkeypatch.setattr(dmg.fetch.shutil, "copytree", fail_copy)
    else:
        dmg.populate = populate
    with pytest.raises((OSError, ValueError)):
        dmg.fetch.fetch("5.1.2", cache, dmg.digest, platform_name="macos-arm64")
    assert binary.read_bytes() == b"official binary"
    assert all(not mount.exists() for mount in dmg.mounts)
    assert dmg.commands[-1][1] == "detach"
    assert not list(cache.glob("fetch-*"))


def test_symlink_app_is_not_followed(dmg, tmp_path):
    outside = tmp_path / "outside"
    outside.mkdir()
    dmg.populate = lambda mount: (mount / "Blender.app").symlink_to(
        outside, target_is_directory=True
    )
    with pytest.raises(ValueError, match="did not contain Blender.app"):
        dmg.fetch.fetch("5.1.2", tmp_path / "cache", dmg.digest, platform_name="macos-arm64")
    assert outside.is_dir()
    assert all(not mount.exists() for mount in dmg.mounts)


def test_internal_app_symlink_is_preserved(dmg, tmp_path):
    original_populate = dmg.populate

    def populate(mount):
        original_populate(mount)
        contents = mount / "Blender.app/Contents"
        (contents / "alias").symlink_to("MacOS", target_is_directory=True)

    dmg.populate = populate
    binary = dmg.fetch.fetch("5.1.2", tmp_path / "cache", dmg.digest, platform_name="macos-arm64")
    alias = binary.parent.parent / "alias"
    assert alias.is_symlink()
    assert (alias / "Blender").read_bytes() == b"official binary"


def test_busy_mount_retries_force_detach_before_publication(dmg, tmp_path):
    dmg.detach_errors = 1
    binary = dmg.fetch.fetch("5.1.2", tmp_path / "cache", dmg.digest, platform_name="macos-arm64")
    assert binary.is_file()
    assert dmg.commands[-2][1:] == ["detach", str(dmg.mounts[0])]
    assert dmg.commands[-1][1:] == ["detach", "-force", str(dmg.mounts[0])]
    assert not dmg.mounts[0].exists()


def test_os_refusing_detach_cannot_publish_or_recursively_clean_mounted_volume(dmg, tmp_path):
    dmg.detach_errors = 2
    cache = tmp_path / "cache"
    with pytest.raises(subprocess.CalledProcessError):
        dmg.fetch.fetch("5.1.2", cache, dmg.digest, platform_name="macos-arm64")
    mount = dmg.mounts[0]
    assert (mount / "Blender.app/Contents/MacOS/Blender").read_bytes() == b"official binary"
    assert not list(cache.glob("5.1.2-*"))
    assert not list(cache.glob("fetch-*"))


@pytest.mark.parametrize("failure", ["copy", "missing-app", "partial-attach", "interrupt"])
def test_cleanup_failure_preserves_original_error_and_disk_diagnostics(
    dmg, tmp_path, monkeypatch, failure
):
    dmg.detach_errors = 2
    expected = OSError("copy ran out of space")
    if failure == "missing-app":
        dmg.populate = lambda mount: None
        error_type = ValueError
    elif failure == "partial-attach":
        original_run = dmg.fetch.subprocess.run

        def run(command, **kwargs):
            result = original_run(command, **kwargs)
            if command[1] == "attach":
                raise subprocess.CalledProcessError(7, command, stderr=b"attachment interrupted")
            return result

        monkeypatch.setattr(dmg.fetch.subprocess, "run", run)
        monkeypatch.setattr(Path, "is_mount", lambda path: path in dmg.mounts)
        error_type = subprocess.CalledProcessError
    else:
        if failure == "interrupt":
            expected = KeyboardInterrupt("copy interrupted")

        def fail_copy(*args, **kwargs):
            raise expected

        monkeypatch.setattr(dmg.fetch.shutil, "copytree", fail_copy)
        error_type = type(expected)
    cache = tmp_path / "cache"
    with pytest.raises(error_type) as caught:
        dmg.fetch.fetch("5.1.2", cache, dmg.digest, platform_name="macos-arm64")
    if failure in {"copy", "interrupt"}:
        assert caught.value is expected
    elif failure == "partial-attach":
        assert caught.value.returncode == 7
    else:
        assert "did not contain Blender.app" in str(caught.value)
    message = dmg.fetch.error_message(caught.value)
    assert "Disk image cleanup failed:" in message
    assert "resource busy" in message
    assert "forced detach refused" in message
    assert str(dmg.mounts[0]) in message
    assert dmg.mounts[0].exists()
    assert not list(cache.glob("5.1.2-*"))
    assert not list(cache.glob("fetch-*"))


@pytest.mark.parametrize("failure", ["attach", "detach", "timeout"])
def test_cli_includes_captured_hdiutil_diagnostics(dmg, tmp_path, monkeypatch, capsys, failure):
    monkeypatch.setattr(dmg.fetch.platform, "system", lambda: "Darwin")
    monkeypatch.setattr(dmg.fetch.platform, "machine", lambda: "arm64")
    monkeypatch.setattr(
        sys, "argv", ["fetch_blender.py", "--version", "5.1.2", "--cache", str(tmp_path / "cache")]
    )
    if failure == "detach":
        dmg.detach_errors = 2
        diagnostic = "forced detach refused"
    else:
        diagnostic = "image not recognized" if failure == "attach" else "attachment stalled"

        def run(command, **kwargs):
            dmg.mounts.append(Path(command[command.index("-mountpoint") + 1]))
            if failure == "timeout":
                raise subprocess.TimeoutExpired(command, 120, stderr=diagnostic.encode())
            raise subprocess.CalledProcessError(1, command, stderr=diagnostic.encode())

        monkeypatch.setattr(dmg.fetch.subprocess, "run", run)
    assert dmg.fetch.main() == 1
    result = capsys.readouterr()
    assert result.out == ""
    assert "Download failed:" in result.err
    assert diagnostic in result.err
    if failure == "detach":
        assert "resource busy" in result.err
    assert "Traceback" not in result.err


@pytest.mark.parametrize(
    ("system", "machine", "expected"),
    [
        ("Darwin", "arm64", "macos-arm64"),
        ("Darwin", "aarch64", "macos-arm64"),
        ("Linux", "x86_64", "linux-x64"),
        ("Windows", "AMD64", "windows-x64"),
    ],
)
def test_cli_selects_supported_platform(dmg, monkeypatch, tmp_path, system, machine, expected):
    calls = []
    monkeypatch.setattr(dmg.fetch.platform, "system", lambda: system)
    monkeypatch.setattr(dmg.fetch.platform, "machine", lambda: machine)
    monkeypatch.setattr(dmg.fetch, "fetch", lambda *args, **kwargs: calls.append((args, kwargs)))
    monkeypatch.setattr(
        sys, "argv", ["fetch_blender.py", "--version", "5.1.2", "--cache", str(tmp_path)]
    )
    assert dmg.fetch.main() == 0
    assert calls == [(("5.1.2", tmp_path, None), {"platform_name": expected})]


@pytest.mark.parametrize(("system", "machine"), [("Darwin", "x86_64"), ("Linux", "arm64")])
def test_cli_unsupported_host_fails_before_download(dmg, monkeypatch, system, machine, capsys):
    monkeypatch.setattr(dmg.fetch.platform, "system", lambda: system)
    monkeypatch.setattr(dmg.fetch.platform, "machine", lambda: machine)
    monkeypatch.setattr(sys, "argv", ["fetch_blender.py", "--version", "5.1.2"])
    with pytest.raises(SystemExit) as error:
        dmg.fetch.main()
    assert error.value.code == 2
    assert "install Blender and set BLENDER" in capsys.readouterr().err
    assert dmg.downloads == dmg.commands == []


@pytest.mark.parametrize("partial", [False, True])
def test_attach_failure_cleans_only_its_private_mount(dmg, tmp_path, monkeypatch, partial):
    original_run = dmg.fetch.subprocess.run

    def run(command, **kwargs):
        if command[1] == "attach":
            mount = Path(command[command.index("-mountpoint") + 1])
            if partial:
                original_run(command, **kwargs)
            else:
                dmg.mounts.append(mount)
            raise subprocess.CalledProcessError(1, command)
        return original_run(command, **kwargs)

    monkeypatch.setattr(dmg.fetch.subprocess, "run", run)
    monkeypatch.setattr(Path, "is_mount", lambda path: partial and path in dmg.mounts)
    with pytest.raises(subprocess.CalledProcessError):
        dmg.fetch.fetch("5.1.2", tmp_path / "cache", dmg.digest, platform_name="macos-arm64")
    assert all(not mount.exists() for mount in dmg.mounts)
    assert bool(dmg.commands) == partial


def test_cli_reports_disk_command_failure_without_traceback(dmg, monkeypatch, capsys):
    monkeypatch.setattr(dmg.fetch.platform, "system", lambda: "Darwin")
    monkeypatch.setattr(dmg.fetch.platform, "machine", lambda: "arm64")
    monkeypatch.setattr(sys, "argv", ["fetch_blender.py", "--version", "5.1.2"])

    def fail(*args, **kwargs):
        raise subprocess.TimeoutExpired(["/usr/bin/hdiutil", "attach"], 120)

    monkeypatch.setattr(dmg.fetch, "fetch", fail)
    assert dmg.fetch.main() == 1
    error = capsys.readouterr().err
    assert "Download failed:" in error and "timed out" in error
    assert "Traceback" not in error
