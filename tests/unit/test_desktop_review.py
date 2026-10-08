# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Desktop review must identify its process and preserve the normal profile."""

import importlib
import json
import plistlib
import subprocess
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import pytest


@pytest.fixture
def review(monkeypatch):
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[2] / "tools"))
    return importlib.import_module("desktop_review")


def test_environment_does_not_inherit_credentials_or_paths(review, tmp_path, monkeypatch):
    monkeypatch.setenv("SCENARIO_API_SECRET", "fixture-only")
    monkeypatch.setenv("PYTHONPATH", "/untrusted")
    monkeypatch.setenv("BLENDER_USER_CONFIG", "/normal")
    session = review.Session(None, tmp_path)
    env = review.review_environment(session)
    assert "SCENARIO_API_SECRET" not in env
    assert "PYTHONPATH" not in env
    assert Path(env["HOME"]).is_relative_to(session.directory)
    assert env["BLENDER_USER_CONFIG"] == str(session.profile / "config")
    assert env["SCENARIO_GUI_PROBE"] == "1"


def test_copy_keeps_real_executable_and_does_not_modify_source(review, tmp_path, monkeypatch):
    source = tmp_path / "Blender.app"
    binary = source / "Contents/MacOS/Blender"
    binary.parent.mkdir(parents=True)
    binary.write_bytes(b"native executable fixture")
    plist = source / "Contents/Info.plist"
    original = plistlib.dumps(
        {
            "CFBundleExecutable": "Blender",
            "CFBundleIdentifier": "original",
            "CFBundleDocumentTypes": ["blend"],
            "UTExportedTypeDeclarations": ["blend"],
        }
    )
    plist.write_bytes(original)
    sign = Mock()
    monkeypatch.setattr(review.subprocess, "run", sign)
    output = tmp_path / "artifacts"
    output.mkdir()
    copied, bundle_id = review.copy_application(binary, output, {"HOME": "isolated"}, "abc")
    info = plistlib.loads((copied.parent.parent / "Info.plist").read_bytes())
    assert copied.read_bytes() == binary.read_bytes()
    assert plist.read_bytes() == original
    assert info["CFBundleExecutable"] == copied.name
    assert info["CFBundleIdentifier"] == bundle_id != "original"
    assert info["LSEnvironment"] == {"HOME": "isolated"}
    assert "CFBundleDocumentTypes" not in info
    assert "UTExportedTypeDeclarations" not in info
    assert sign.call_args.args[0][-1] == str(copied.parent.parent.parent)
    with pytest.raises(ValueError, match="inside a macOS"):
        review.copy_application(tmp_path / "plain-binary", output, {}, "def")


@pytest.mark.parametrize(
    "failure",
    [
        None,
        "pid",
        "online",
        "network",
        "missing",
        "exit",
        "timeout",
        "normal",
        "install",
        "cleanup-timeout",
        "cleanup-oserror",
    ],
)
def test_review_rejects_invalid_evidence_and_reaps_child(review, tmp_path, monkeypatch, failure):
    monkeypatch.setattr(review.platform, "system", lambda: "Darwin")
    normal = tmp_path / "normal"
    normal.mkdir()
    (normal / "keep").write_text("original")
    monkeypatch.setattr(review, "normal_profile_root", lambda: normal)
    monkeypatch.setattr(review, "find_blender", lambda _: Path("Blender"))
    monkeypatch.setattr(review, "copy_application", lambda *args: (Path("Blender"), "unique"))
    monkeypatch.setattr(review, "validate", lambda *args: {"id": "scenario", "version": "0.9.9"})
    verifies = Mock()
    monkeypatch.setattr(review, "verify_installed", verifies)
    if failure == "install":
        verifies.side_effect = ValueError("changed installed bytes")
    monkeypatch.setattr(review.Session, "step", lambda *args: None)
    candidate = tmp_path / "input.zip"
    candidate.write_bytes(b"fixture archive")
    child = Mock(pid=42)
    child.poll.return_value = None

    def launch(command, **kwargs):
        directory = kwargs["cwd"]
        assert kwargs["env"]["BLENDER_USER_CONFIG"] == str(directory / "profile/config")
        assert "--offline-mode" in command
        assert "--enable-event-simulate" not in command
        assert "--disable-autoexec" in command
        ready = {
            "pid": 7 if failure == "pid" else 42,
            "online_access": failure == "online",
            "blender_version": [5, 1, 2],
        }
        if failure != "missing":
            (directory / "ready.json").write_text(json.dumps(ready))
        (directory / "observed.json").write_text(
            json.dumps(
                {
                    **ready,
                    "network_violations": ["socket.connect"] if failure == "network" else [],
                }
            )
        )
        if failure == "normal":
            (normal / "keep").write_text("modified")
        return child

    def wait(timeout):
        if failure in ("cleanup-timeout", "cleanup-oserror"):
            raise subprocess.TimeoutExpired("Blender", timeout)
        if failure == "timeout" and timeout > 10:
            raise subprocess.TimeoutExpired("Blender", timeout)
        child.poll.return_value = 3 if failure == "exit" else 0
        return child.poll.return_value

    child.wait.side_effect = wait
    if failure == "cleanup-oserror":
        child.kill.side_effect = OSError("Could not signal owned child")
    monkeypatch.setattr(review.subprocess, "Popen", launch)
    args = SimpleNamespace(
        blender=None, artifacts=tmp_path / "out", zip=candidate, timeout=60, duration=5
    )
    assert review.run_review(args) == (0 if failure is None else 1)
    report = json.loads(next(args.artifacts.glob("desktop-*/report.json")).read_text())
    assert report["interaction_acceptance"] == "not_assessed"
    assert report["status"] == ("finished" if failure is None else "failed")
    assert report["normal_profile_unchanged"] is (failure != "normal")
    if failure == "timeout":
        child.terminate.assert_called_once()
    if failure == "install":
        child.wait.assert_not_called()
    if failure in ("cleanup-timeout", "cleanup-oserror"):
        assert report["cleanup_error"]
        assert child.poll() is None
        child.kill.assert_called()


def test_refuses_normal_profile_output_and_other_platforms(review, tmp_path, monkeypatch):
    monkeypatch.setattr(review, "normal_profile_root", lambda: tmp_path)
    monkeypatch.setattr(review.platform, "system", lambda: "Darwin")
    args = SimpleNamespace(artifacts=tmp_path / "nested")
    assert review.run_review(args) == 1
    assert not args.artifacts.exists()
    monkeypatch.setattr(review.platform, "system", lambda: "Linux")
    assert review.run_review(args) == 1


def test_stubborn_owned_child_is_killed_and_reaped(review):
    child = Mock()
    child.poll.return_value = None
    child.wait.side_effect = [subprocess.TimeoutExpired("Blender", 10), 0]
    review.stop_child(child)
    child.terminate.assert_called_once()
    child.kill.assert_called_once()
    assert child.wait.call_count == 2


@pytest.mark.parametrize("failure", [None, "profile", "extension", "online"])
def test_blender_observer_checks_identity_before_claiming_ready(
    review, tmp_path, monkeypatch, failure
):
    import runpy
    import sys

    profile = tmp_path / "profile"
    installed = profile / "extensions/user_default/scenario"
    fixture = tmp_path / "review.blend"
    (tmp_path / "review.json").write_text(
        json.dumps(
            {
                "profile": str(profile),
                "installed": str(installed),
                "fixture": str(fixture),
                "duration": 5,
            }
        )
    )
    register = Mock()
    fake_bpy = SimpleNamespace(
        utils=SimpleNamespace(
            user_resource=lambda _: str(tmp_path if failure == "profile" else profile / "config")
        ),
        app=SimpleNamespace(
            online_access=failure == "online",
            version=(5, 1, 2),
            timers=SimpleNamespace(register=register),
        ),
        data=SimpleNamespace(filepath=str(fixture)),
    )
    monkeypatch.setitem(sys.modules, "bpy", fake_bpy)
    monkeypatch.setitem(
        sys.modules,
        "bl_ext.user_default.scenario",
        SimpleNamespace(
            __file__=str((tmp_path if failure == "extension" else installed) / "__init__.py")
        ),
    )
    monkeypatch.setattr(sys, "argv", ["blender", "--", str(tmp_path), "observe"])
    monkeypatch.setattr(sys, "addaudithook", Mock())
    scene = runpy.run_path(str(review.SCENE_SCRIPT))
    if failure:
        with pytest.raises(RuntimeError):
            scene["main"]()
        assert not (tmp_path / "ready.json").exists()
        register.assert_not_called()
    else:
        scene["main"]()
        assert json.loads((tmp_path / "ready.json").read_text())["online_access"] is False
        register.assert_called_once()


def test_refuses_output_inside_source_application(review, tmp_path, monkeypatch):
    source = tmp_path / "Blender.app"
    monkeypatch.setattr(review.platform, "system", lambda: "Darwin")
    monkeypatch.setattr(review, "normal_profile_root", lambda: tmp_path / "normal")
    monkeypatch.setattr(review, "find_blender", lambda _: source / "Contents/MacOS/Blender")
    args = SimpleNamespace(blender=None, artifacts=source / "nested")
    assert review.run_review(args) == 1
    assert not source.exists()
