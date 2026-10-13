# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Installed ffmpeg/ffprobe lookup: PATH first, then fixed folders, never the working directory.

Blender opened from the macOS Dock or Finder gets launchd's PATH, which lacks
Homebrew and MacPorts. These fakes stand in for the standard folders.
"""

import os
import shutil
import subprocess
from pathlib import Path
from types import SimpleNamespace

import pytest

from scenario.core.jobs import installed_tools as tools
from scenario.core.jobs import local_render, media_probe

DOCK_PATH = "/usr/bin:/bin:/usr/sbin:/sbin"
posix = pytest.mark.skipif(os.name == "nt", reason="Fake tools use POSIX permission bits")


def tool(directory, name="ffprobe", *, mode=0o755):
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / name
    path.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
    path.chmod(mode)
    return path


@pytest.fixture
def folders(tmp_path, monkeypatch):
    """Empty PATH folder and fake standard folders; nothing runs and PATH stays Dock-like."""
    path, brew, ports = tmp_path / "path", tmp_path / "brew", tmp_path / "ports"
    path.mkdir()
    monkeypatch.setenv("PATH", str(path))
    monkeypatch.setattr(tools, "_platform", lambda: "darwin")
    monkeypatch.setattr(
        tools,
        "DIRECTORIES",
        {"darwin": (str(tmp_path / "absent"), str(brew), str(ports)), "linux": (str(brew),)},
    )

    def never(*args, **kwargs):
        raise AssertionError("Lookup must not run a process")

    monkeypatch.setattr(subprocess, "Popen", never)
    return path, brew, ports


@posix
def test_found_on_path_first(folders):
    path, brew, _ = folders
    expected = tool(path)
    tool(brew)
    assert tools.find("ffprobe") == expected.resolve()


@posix
def test_found_only_in_a_standard_folder_with_a_dock_path(folders, monkeypatch):
    _, brew, ports = folders
    monkeypatch.setenv("PATH", DOCK_PATH)
    tool(ports)
    expected = tool(brew)
    before = dict(os.environ)
    found = tools.find("ffprobe")
    assert found == expected.resolve() and found.is_absolute()
    assert dict(os.environ) == before  # PATH is never extended for children.


@posix
def test_homebrew_symlink_resolves_to_its_absolute_target(folders, tmp_path):
    _, brew, _ = folders
    target = tool(tmp_path / "Cellar" / "ffmpeg" / "bin")
    brew.mkdir()
    (brew / "ffprobe").symlink_to(Path("..") / "Cellar" / "ffmpeg" / "bin" / "ffprobe")
    assert tools.find("ffprobe") == target.resolve()


@posix
def test_non_executable_files_and_folders_are_ignored(folders):
    path, brew, ports = folders
    tool(path, mode=0o644)
    tool(brew, mode=0o644)
    (ports / "ffprobe").mkdir(parents=True)
    assert tools.find("ffprobe") is None


@posix
def test_working_directory_and_relative_path_entries_are_never_searched(
    folders, tmp_path, monkeypatch
):
    work = tmp_path / "work"
    tool(work)
    tool(work / "bin")
    monkeypatch.chdir(work)
    monkeypatch.setenv("PATH", os.pathsep.join(["", ".", "bin"]))
    assert tools.find("ffprobe") is None


@posix
def test_unset_path_still_checks_standard_folders(folders, monkeypatch):
    _, brew, _ = folders
    monkeypatch.delenv("PATH")
    expected = tool(brew)
    assert tools.find("ffprobe") == expected.resolve()


@pytest.mark.parametrize("name", ["", "bin/ffprobe", "../ffprobe", "/usr/bin/ffprobe"])
def test_only_bare_tool_names_are_accepted(name):
    with pytest.raises(ValueError):
        tools.find(name)


@posix
def test_windows_uses_path_only(folders, monkeypatch):
    path, brew, _ = folders
    monkeypatch.setattr(tools, "_platform", lambda: "win32")
    tool(brew)
    assert tools.find("ffprobe") is None
    expected = tool(path)
    assert tools.find("ffprobe") == expected.resolve()
    message = tools.missing(["ffprobe"], "before inspecting Film media")
    assert message == "Install ffprobe before inspecting Film media: not found on PATH."


def windows_which(monkeypatch, *, needs_curdir=True):
    """Run CPython's own win32 branch of shutil.which on this host.

    Python 3.11 (Blender 5.0) always searches the working directory first on
    Windows, even with an explicit path. Python 3.13 (Blender 5.1 and 5.2) does
    so when NeedCurrentDirectoryForExePath is true, which is the default unless
    NoDefaultCurrentDirectoryInExePath is set. A working-directory match is
    returned as a relative path and ends the search.
    """
    monkeypatch.setattr(tools, "_platform", lambda: "win32")
    monkeypatch.setenv("PATHEXT", ".EXE")
    monkeypatch.setattr(shutil, "sys", SimpleNamespace(platform="win32"))
    needs = SimpleNamespace(NeedCurrentDirectoryForExePath=lambda cmd: needs_curdir)
    monkeypatch.setattr(shutil, "_winapi", needs, raising=False)


@posix
@pytest.mark.parametrize("needs_curdir", [True, False])
def test_windows_working_directory_match_does_not_hide_the_path_tool(
    folders, tmp_path, monkeypatch, needs_curdir
):
    path, _, _ = folders
    work = tmp_path / "work"
    tool(work, "ffprobe.EXE")  # For example beside the open .blend file.
    expected = tool(path, "ffprobe.EXE")
    monkeypatch.setenv("PATH", os.pathsep.join([str(tmp_path / "empty"), "bin", str(path)]))
    monkeypatch.chdir(work)
    windows_which(monkeypatch, needs_curdir=needs_curdir)
    assert tools.find("ffprobe") == expected.resolve()


@posix
def test_windows_never_returns_a_working_directory_match(folders, tmp_path, monkeypatch):
    path, brew, _ = folders
    work = tmp_path / "work"
    tool(work, "ffprobe.EXE")
    tool(work / "bin", "ffprobe.EXE")
    tool(brew, "ffprobe.EXE")
    monkeypatch.setenv("PATH", os.pathsep.join([str(path), "bin", "."]))
    monkeypatch.chdir(work)
    windows_which(monkeypatch)
    assert tools.find("ffprobe") is None


def test_missing_message_names_tools_folders_and_the_dock_hint(monkeypatch):
    monkeypatch.setattr(tools, "_platform", lambda: "darwin")
    assert tools.missing(["ffprobe"], "before inspecting Film media") == (
        "Install ffprobe before inspecting Film media: not found on PATH or in"
        " /opt/homebrew/bin, /usr/local/bin or /opt/local/bin. Apps opened from the"
        " Dock or Finder do not inherit the shell PATH."
    )
    monkeypatch.setattr(tools, "_platform", lambda: "linux")
    assert tools.missing(["ffmpeg", "ffprobe"], "for MP4 capture") == (
        "Install ffmpeg and ffprobe for MP4 capture: not found on PATH or in"
        " /usr/local/bin or /usr/bin."
    )


@posix
def test_film_media_inspection_finds_a_standard_folder_tool(folders, monkeypatch):
    _, brew, _ = folders
    monkeypatch.setenv("PATH", DOCK_PATH)
    with pytest.raises(media_probe.MediaProbeError) as missing:
        media_probe.probe_tool()
    assert str(missing.value).startswith("Install ffprobe before inspecting Film media:")
    assert str(brew) in str(missing.value) and "Dock" in str(missing.value)
    expected = tool(brew)
    assert media_probe.probe_tool() == expected.resolve()


@posix
def test_mp4_capture_names_only_the_missing_tool(folders, monkeypatch):
    _, brew, _ = folders
    monkeypatch.setenv("PATH", DOCK_PATH)
    ffmpeg = tool(brew, "ffmpeg")
    with pytest.raises(local_render.LocalRenderError) as missing:
        local_render.media_tools()
    message = str(missing.value)
    assert message.startswith("Install ffprobe for MP4 capture:")
    assert "ffmpeg" not in message and message.endswith("Still capture remains available.")
    ffprobe = tool(brew)
    assert local_render.media_tools() == (ffmpeg.resolve(), ffprobe.resolve())
