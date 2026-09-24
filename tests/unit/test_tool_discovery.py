# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Portable executable and optional font discovery without Blender or Pillow."""

import glob
import importlib.util
import os
import subprocess
import sys
import tomllib
from pathlib import Path
from types import SimpleNamespace

import pytest

from tools import blender_env

ROOT = Path(__file__).resolve().parents[2]


def executable(path):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("discovery fixture, never executed")
    path.chmod(0o755)
    return path


@pytest.fixture
def discovery(tmp_path, monkeypatch):
    roots = {
        "/Applications": tmp_path / "applications",
        "/snap": tmp_path / "snap",
        "/usr": tmp_path / "usr",
        "/opt": tmp_path / "opt",
        "C:/Program Files/Blender Foundation": tmp_path / "windows",
    }

    def local_path(value):
        path = Path(value)
        text = path.as_posix()
        for prefix, destination in roots.items():
            if text == prefix or text.startswith(prefix + "/"):
                return destination / text[len(prefix) :].lstrip("/")
        return path

    monkeypatch.setattr(blender_env, "Path", local_path)
    monkeypatch.setattr(blender_env, "ROOT", tmp_path / "repository")
    monkeypatch.setattr(blender_env.shutil, "which", lambda _: None)
    monkeypatch.delenv("BLENDER", raising=False)
    return roots


@pytest.mark.parametrize(
    "system,older,newer",
    [
        (
            "Darwin",
            "/Applications/Blender 5.9.app/Contents/MacOS/Blender",
            "/Applications/Blender 5.10/Blender.app/Contents/MacOS/Blender",
        ),
        (
            "Darwin",
            "/Applications/Blender 5.9/Blender.app/Contents/MacOS/Blender",
            "/Applications/Blender 5.10.app/Contents/MacOS/Blender",
        ),
        ("Linux", "/opt/blender-5.9.1/blender", "/opt/blender-5.10.0/blender"),
        (
            "Windows",
            "C:/Program Files/Blender Foundation/Blender 5.9/blender.exe",
            "C:/Program Files/Blender Foundation/Blender 5.10/blender.exe",
        ),
    ],
)
def test_versioned_platform_installations_use_numeric_order(
    discovery, monkeypatch, system, older, newer
):
    monkeypatch.setattr(blender_env.platform, "system", lambda: system)
    executable(blender_env.Path(older))
    expected = executable(blender_env.Path(newer))
    assert blender_env.find_blender() == expected.resolve()


def test_standard_mac_app_remains_preferred_over_versioned_copies(discovery, monkeypatch):
    monkeypatch.setattr(blender_env.platform, "system", lambda: "Darwin")
    executable(blender_env.Path("/Applications/Blender 5.10.app/Contents/MacOS/Blender"))
    expected = executable(blender_env.Path("/Applications/Blender.app/Contents/MacOS/Blender"))
    assert blender_env.find_blender() == expected.resolve()


def test_linux_usr_bin_is_available_when_path_does_not_include_it(discovery, monkeypatch):
    monkeypatch.setattr(blender_env.platform, "system", lambda: "Linux")
    expected = executable(blender_env.Path("/usr/bin/blender"))
    assert blender_env.find_blender() == expected.resolve()


@pytest.mark.parametrize("system", ["Linux", "Windows", "Darwin"])
def test_cache_selects_newest_matching_platform_and_skips_non_directories(
    discovery, monkeypatch, system
):
    monkeypatch.setattr(blender_env.platform, "system", lambda: system)
    cache = blender_env.ROOT / ".blender"
    names = {
        "Linux": "blender-{version}-linux-x64/blender",
        "Windows": "blender-{version}-windows-x64/blender.exe",
        "Darwin": "Blender.app/Contents/MacOS/Blender",
    }
    for version in ("5.9.1", "5.10.0"):
        expected = executable(cache / f"{version}-fixture" / names[system].format(version=version))
    other = "Windows" if system == "Linux" else "Linux"
    executable(cache / "99.0.0-other-platform" / names[other].format(version="99.0.0"))
    (cache / "100.0.0-archive").write_bytes(b"not an installation")
    assert blender_env.find_blender() == expected.resolve()


@pytest.mark.parametrize("system,filename", [("Linux", "blender"), ("Windows", "blender.exe")])
def test_flat_manual_cache_layout_remains_supported(discovery, monkeypatch, system, filename):
    monkeypatch.setattr(blender_env.platform, "system", lambda: system)
    expected = executable(blender_env.ROOT / ".blender/5.10.0" / filename)
    assert blender_env.find_blender() == expected.resolve()


def test_path_selection_still_precedes_platform_and_cache(discovery, monkeypatch, tmp_path):
    monkeypatch.setattr(blender_env.platform, "system", lambda: "Linux")
    executable(blender_env.Path("/usr/bin/blender"))
    expected = executable(tmp_path / "chosen via PATH")
    monkeypatch.setattr(blender_env.shutil, "which", lambda _: str(expected))
    assert blender_env.find_blender() == expected.resolve()


def test_missing_all_discovery_locations_reports_configuration_help(discovery, monkeypatch):
    monkeypatch.setattr(blender_env.platform, "system", lambda: "Linux")
    with pytest.raises(ValueError, match="set BLENDER="):
        blender_env.find_blender()


@pytest.mark.parametrize("option", ["--version", "--manifest-version"])
def test_manifest_version_cli_needs_no_blender(option, tmp_path):
    expected = tomllib.loads((ROOT / "scenario/blender_manifest.toml").read_text())["version"]
    result = subprocess.run(
        [sys.executable, str(ROOT / "tools/blender_env.py"), option],
        env=dict(os.environ, BLENDER=str(tmp_path / "missing")),
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == expected
    assert result.stderr == ""


@pytest.mark.parametrize("manifest", ["broken TOML", "", "version = 42", 'version = ""'])
def test_manifest_version_rejects_invalid_metadata(tmp_path, monkeypatch, manifest):
    (tmp_path / "scenario").mkdir()
    (tmp_path / "scenario/blender_manifest.toml").write_text(manifest)
    monkeypatch.setattr(blender_env, "ROOT", tmp_path)
    with pytest.raises(ValueError):
        blender_env.manifest_version()


@pytest.mark.parametrize(
    "layout",
    ["windows", "system-linux", "cached-flat", "cached-linux", "cached-windows", "missing"],
)
def test_optional_font_discovery_covers_system_and_fetched_layouts(tmp_path, monkeypatch, layout):
    locations = {
        "windows": tmp_path / "Windows/Fonts/DejaVuSans.ttf",
        "system-linux": tmp_path / "system/Inter.woff2",
        "cached-flat": tmp_path / ".blender/5.10.0/5.10/datafiles/fonts/Inter.woff2",
        "cached-linux": tmp_path
        / ".blender/5.10.0-hash/blender-5.10.0-linux-x64/5.10/datafiles/fonts/Inter.woff2",
        "cached-windows": tmp_path
        / ".blender/5.10.0-windows-x64-hash/blender-5.10.0-windows-x64/5.10/datafiles/fonts/Inter.woff2",
    }
    expected = locations.get(layout)
    if expected is not None:
        expected.parent.mkdir(parents=True)
        expected.write_bytes(b"font-discovery fixture")
    monkeypatch.setenv("WINDIR", str(tmp_path / "Windows"))
    original_glob = glob.glob

    def local_glob(pattern):
        if pattern == "/usr/share/blender/*/datafiles/fonts/*.woff2":
            return [str(expected)] if layout == "system-linux" else []
        return original_glob(pattern)

    monkeypatch.setattr(glob, "glob", local_glob)

    def load_font(path, size):
        if expected is None or Path(path) != expected:
            raise OSError("Unavailable font")
        assert size == 100

    # Only discovery is under test. Pillow rendering is unchanged and optional;
    # this stub prevents installing it or rendering/modifying any icon assets.
    monkeypatch.setitem(
        sys.modules,
        "PIL",
        SimpleNamespace(Image=None, ImageDraw=None, ImageFont=SimpleNamespace(truetype=load_font)),
    )
    spec = importlib.util.spec_from_file_location(
        "icon_discovery_subject", ROOT / "tools/make_icons.py"
    )
    module = importlib.util.module_from_spec(spec)
    module.__file__ = str(tmp_path / "tools/make_icons.py")
    spec.loader.exec_module(module)
    assert module.find_font() == (str(expected) if expected is not None else None)
