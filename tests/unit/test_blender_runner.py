# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Offline tests for the native runner's isolation and artifact boundaries."""

import importlib.util
import json
import os
import subprocess
import sys
import zipfile
from pathlib import Path
from types import SimpleNamespace

import pytest

from tools import blender_env

ROOT = Path(__file__).resolve().parents[2]


def archive(path, extra=None):
    with zipfile.ZipFile(path, "w") as z:
        z.writestr("blender_manifest.toml", 'id = "scenario"\nversion = "0.9.9"\n')
        z.writestr("__init__.py", "# fixture")
        z.writestr("LICENSE", "fixture license")
        if extra:
            z.writestr(*extra)
    return path


def test_environment_discards_credentials_and_blender_overrides(tmp_path):
    original = {
        "PATH": "/usr/bin",
        "SCENARIO_TEST_API_KEY": "private",
        "SCENARIO_API_SECRET": "private",
        "BLENDER_USER_SCRIPTS": "/real/scripts",
        "BLENDER_USER_RESOURCES": "/real/profile",
        "PYTHONPATH": "/source",
    }
    env = blender_env.isolated_environment(tmp_path / "profile", tmp_path / "tmp", original)
    assert env["PATH"] == original["PATH"]
    assert env["BLENDER_USER_RESOURCES"] == str(tmp_path / "profile")
    assert env["TMPDIR"] == str(tmp_path / "tmp")
    assert "PYTHONPATH" not in env
    assert "BLENDER_USER_SCRIPTS" not in env
    assert not any(k.startswith("SCENARIO_") for k in env)
    assert original["BLENDER_USER_RESOURCES"] == "/real/profile"


def test_explicit_blender_is_authoritative(tmp_path, monkeypatch):
    binary = tmp_path / "Blender with spaces"
    binary.write_text("fixture")
    binary.chmod(0o755)
    monkeypatch.setenv("BLENDER", str(binary))
    assert blender_env.find_blender() == binary
    with pytest.raises(ValueError, match="Blender not found"):
        blender_env.find_blender(str(tmp_path / "missing"))


@pytest.mark.parametrize("change", ["modified", "missing", "extra", "symlink"])
def test_installed_files_must_match_candidate(tmp_path, change):
    zip_path = archive(tmp_path / "candidate.zip")
    installed = tmp_path / "installed"
    with zipfile.ZipFile(zip_path) as z:
        z.extractall(installed)
    blender_env.verify_installed(zip_path, installed)
    if change == "modified":
        (installed / "__init__.py").write_text("stale")
    elif change == "missing":
        (installed / "LICENSE").unlink()
    elif change == "extra":
        (installed / "stale.py").write_text("old")
    else:
        (installed / "link.py").symlink_to(installed / "__init__.py")
    with pytest.raises(ValueError):
        blender_env.verify_installed(zip_path, installed)


@pytest.mark.parametrize("name", ["../escape", "/absolute", "C:/outside", "dir\\escape"])
def test_unsafe_archives_are_rejected(tmp_path, name):
    with pytest.raises(ValueError, match="Unsafe"):
        blender_env.inspect_zip(archive(tmp_path / "bad.zip", (name, "payload")))


def test_duplicate_zip_members_are_rejected(tmp_path):
    with pytest.warns(UserWarning, match="Duplicate"):
        path = archive(tmp_path / "duplicate.zip", ("__init__.py", "second"))
    with pytest.raises(ValueError, match="duplicate"):
        blender_env.inspect_zip(path)


def test_unmanaged_test_execution_is_refused_without_blender_import():
    env = {k: v for k, v in os.environ.items() if not k.startswith("BLENDER_")}
    result = subprocess.run(
        [sys.executable, str(ROOT / "tests/blender/run_all.py")],
        env=env,
        capture_output=True,
        text=True,
    )
    assert result.returncode != 0
    assert "use make test-blender" in result.stderr
    assert "No module named 'bpy'" not in result.stderr


def test_normal_profile_snapshot_detects_writes(tmp_path):
    before = blender_env.profile_snapshot(tmp_path)
    (tmp_path / "userpref.blend").write_bytes(b"fixture")
    assert blender_env.profile_snapshot(tmp_path) != before


@pytest.fixture
def runner(monkeypatch):
    monkeypatch.syspath_prepend(str(ROOT / "tools"))
    spec = importlib.util.spec_from_file_location(
        "runner_test_subject", ROOT / "tools/test_blender.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_failed_blender_exit_is_preserved_and_existing_profiles_survive(
    tmp_path, monkeypatch, runner
):
    old_profile = tmp_path / "existing-profile"
    old_profile.mkdir()
    sentinel = old_profile / "keep"
    sentinel.write_text("user state")
    monkeypatch.setenv("BLENDER_USER_RESOURCES", str(old_profile))
    monkeypatch.setattr(runner, "find_blender", lambda _: Path("blender"))
    monkeypatch.setattr(runner, "normal_profile_root", lambda: old_profile)

    def failure(*args, **kwargs):
        assert kwargs["env"]["BLENDER_USER_RESOURCES"] != str(old_profile)
        raise subprocess.CalledProcessError(7, "fixture-failure")

    monkeypatch.setattr(runner, "run_step", failure)
    args = SimpleNamespace(
        blender=None,
        artifacts=tmp_path / "artifacts",
        suite="baseline",
        timeout=2,
        keep_profile=False,
    )
    assert runner.run(args) == 7
    assert sentinel.read_text() == "user state"
    report = json.loads(next(args.artifacts.glob("run-*/result.json")).read_text())
    assert report["status"] == "failed"
    assert "exited 7" in report["error"]
    assert next(args.artifacts.glob("run-*/profile")).is_dir()


def test_native_guard_blocks_source_fallback_and_external_network():
    code = """
import runpy, sys, socket
module = runpy.run_path(sys.argv[1])
sys.meta_path.insert(0, module["NoSourceImports"]())
try:
    import scenario.core.config
except ImportError as error:
    assert "Source-checkout" in str(error)
else:
    raise AssertionError("source checkout was accepted")
violations = module["install_network_guard"]()
# Test audit events without making any actual network connection.
with socket.socket() as sock:
    sys.audit("socket.connect", sock, ("127.0.0.1", 1234))
    try:
        sys.audit("socket.connect", sock, ("203.0.113.1", 443))
    except RuntimeError as error:
        assert "External network" in str(error)
    else:
        raise AssertionError("external connection was accepted")
assert violations == ["socket.connect"]
"""
    result = subprocess.run(
        [sys.executable, "-c", code, str(ROOT / "tests/blender/run_all.py")],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
