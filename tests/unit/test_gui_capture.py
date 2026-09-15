# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Capture evidence cannot mask failed GUI setup or a changed installed package."""

import importlib
import json
import subprocess
import zipfile
from pathlib import Path
from types import SimpleNamespace

import pytest


@pytest.mark.parametrize(
    "failure",
    [None, "setup", "missing_png", "changed_install", "version", "online", "timeout", "minimum"],
)
def test_capture_evidence_and_cleanup(tmp_path, monkeypatch, failure):
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[2] / "tools"))
    capture = importlib.import_module("capture_gui")
    monkeypatch.setattr(capture, "find_blender", lambda _: Path("blender"))
    normal = tmp_path / "normal"
    normal.mkdir()
    (normal / "keep").write_text("normal profile")
    monkeypatch.setattr(capture, "normal_profile_root", lambda: normal)
    monkeypatch.setenv("SCENARIO_API_KEY", "must-not-be-inherited")
    candidate = tmp_path / "input.zip"
    with zipfile.ZipFile(candidate, "w") as archive:
        archive.writestr(
            "blender_manifest.toml", 'id="scenario"\nversion="0.9.9"\nblender_version_min="5.0.0"'
        )
        archive.writestr("LICENSE", "fixture")
        archive.writestr("__init__.py", "# installed fixture")
    monkeypatch.setattr(capture, "validate", lambda session, path: capture.inspect_zip(path)[0])
    calls = []

    def step(session, name, command):
        calls.append(name)
        assert session.env["BLENDER_USER_RESOURCES"] == str(session.profile)
        assert "SCENARIO_API_KEY" not in session.env
        assert "--offline-mode" in command
        if name == "prepare":
            log = session.directory / "prepare.log"
            version = [4, 3, 2] if failure == "minimum" else [5, 0, 1]
            log.write_text("CAPTURE_VERSION=" + json.dumps(version))
            return log
        installed = session.profile / "extensions/user_default/scenario"
        if name == "install":
            with zipfile.ZipFile(candidate) as archive:
                archive.extractall(installed)
        if name == "capture":
            assert session.env["SCENARIO_GUI_PROBE"] == "1"
            if failure == "timeout":
                raise subprocess.TimeoutExpired("fixture GUI", 10)
            evidence = {
                "status": "failed" if failure == "setup" else "captured",
                "blender_version": [5, 1, 2] if failure == "version" else [5, 0, 1],
                "online_access": failure == "online",
            }
            (session.directory / "gui.json").write_text(json.dumps(evidence))
            if failure != "missing_png":
                (session.directory / "plugin.png").write_bytes(b"\x89PNG\r\n\x1a\nfixture")
            if failure == "changed_install":
                (installed / "__init__.py").write_text("# changed")

    monkeypatch.setattr(capture.Session, "step", step)
    args = SimpleNamespace(
        blender=None,
        output=tmp_path / "captures",
        timeout=20,
        zip=candidate,
        view="sidebar",
        lane="image",
        fixture="form",
        delay=8,
        label="fixture milestone",
    )
    assert capture.capture(args) == (1 if failure else 0)
    directory = next(args.output.iterdir())
    report = json.loads((directory / "report.json").read_text())
    assert report["status"] == ("failed" if failure else "captured")
    assert report["label"] == "fixture milestone"
    assert (directory / "profile").exists() == bool(failure)
    assert (normal / "keep").read_text() == "normal profile"
    if failure == "minimum":
        assert calls == ["prepare"]
    if not failure:
        assert report["normal_profile_unchanged"]
        assert report["zip_sha256"] == capture.sha256(candidate)
        assert report["png_sha256"] == capture.sha256(directory / "plugin.png")
