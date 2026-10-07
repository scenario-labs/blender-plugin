# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Local rendering process ownership, exact outputs and optional-tool boundaries."""

import json
import os
import struct
import subprocess
import sys
import threading
import time
from dataclasses import replace
from pathlib import Path, PurePosixPath, PureWindowsPath

import pytest

from scenario.core.jobs import local_render as render


@pytest.mark.parametrize(
    "source,expected",
    [
        (PureWindowsPath(r"\\?\C:\private\snapshot.blend"), r"C:\private\snapshot.blend"),
        (
            PureWindowsPath(r"\\?\UNC\server\share\snapshot.blend"),
            r"\\server\share\snapshot.blend",
        ),
        (PureWindowsPath(r"C:\private\snapshot.blend"), r"C:\private\snapshot.blend"),
        (PurePosixPath("/private/snapshot.blend"), "/private/snapshot.blend"),
    ],
)
def test_blender_paths_preserve_drive_unc_and_posix_identity(source, expected):
    assert render.blender_path(source) == expected


@pytest.mark.parametrize("part", ["a" * 256, "\U0001f3ac" * 128])
def test_blender_paths_reject_windows_overflow_in_utf16_units(part):
    with pytest.raises(render.LocalRenderError, match="shorter absolute paths"):
        render.blender_path(PureWindowsPath("C:/") / part)


@pytest.fixture
def spec(tmp_path):
    (tmp_path / "snapshot.blend").write_bytes(b"synthetic snapshot")
    worker = tmp_path / "render_worker.py"
    worker.write_text("# fixture", encoding="utf-8")
    return render.RenderSpec(
        tmp_path,
        Path(sys.executable).resolve(),
        worker,
        "Fixture scene",
        render.digest(tmp_path / "snapshot.blend"),
        4,
        7,
        30,
        64,
        64,
    )


def png(path, width=64, height=64):
    path.write_bytes(b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR" + struct.pack(">II", width, height))


def fixture_runner(monkeypatch, spec, *, missing=False, wrong_rate=False):
    calls = []
    monkeypatch.setattr(
        render, "media_tools", lambda: (Path("/fixture/ffmpeg"), Path("/fixture/ffprobe"))
    )

    def run(command, *, log, env, timeout, cancel, stdout=None):
        calls.append((command, env))
        log.write_text("fixture")
        if "--background" in command:
            for index in range(1, spec.frames + (0 if missing else 1)):
                png(spec.directory / "frames" / f"Frame-{index:06d}.png", spec.width, spec.height)
        elif stdout is None:
            Path(command[-1]).write_bytes(b"fixture encoded media")
        else:
            stdout.write_text(
                json.dumps(
                    {
                        "streams": [
                            {
                                "width": spec.width,
                                "height": spec.height,
                                "nb_read_frames": str(spec.frames),
                                "avg_frame_rate": "25/1" if wrong_rate else "30/1",
                            }
                        ]
                    }
                )
            )

    monkeypatch.setattr(render, "_run", run)
    return calls


def test_video_uses_exact_snapshot_frames_and_isolated_processes(monkeypatch, spec):
    monkeypatch.setenv("SCENARIO_API_KEY", "synthetic-key")
    monkeypatch.setenv("BLENDER_USER_RESOURCES", "/normal-profile")
    monkeypatch.setenv("PYTHONPATH", "/ambient-python")
    calls = fixture_runner(monkeypatch, spec)
    result = render.render(spec)
    assert (result.frames, result.width, result.height, result.fps) == (4, 64, 64, 30)
    assert result.content_type == "video/mp4"
    assert result.sha256 == render.digest(result.path)
    assert len(calls) == 3
    command, env = calls[0]
    assert (
        "--offline-mode" in command
        and "--factory-startup" in command
        and "--disable-autoexec" in command
    )
    assert "SCENARIO_API_KEY" not in env and "PYTHONPATH" not in env
    assert str(spec.directory) in env["BLENDER_USER_RESOURCES"]
    assert not Path(env["BLENDER_USER_RESOURCES"]).exists()
    assert not list(spec.directory.glob("worker-*"))
    assert "-n" in calls[1][0] and "-an" in calls[1][0]
    assert (spec.directory / "frames/Frame-000004.png").is_file()
    with pytest.raises(FileExistsError):
        render.render(spec)


def test_still_does_not_require_ffmpeg_or_ffprobe(monkeypatch, spec):
    spec = replace(spec, kind="STILL", frame_end=spec.frame_start)
    calls = fixture_runner(monkeypatch, spec)
    monkeypatch.setattr(render, "media_tools", lambda: pytest.fail("Still checked media tools"))
    result = render.render(spec)
    assert len(calls) == 1
    assert result.content_type == "image/png"
    assert result.frames == 1


@pytest.mark.parametrize("frames,accepted", [(32, True), (1, False)])
def test_large_video_uses_capture_bound_and_retains_rejected_output(
    monkeypatch, spec, frames, accepted
):
    spec = replace(spec, width=4096, height=4096, frame_end=spec.frame_start + frames - 1)
    calls = fixture_runner(monkeypatch, spec)
    original = render._run
    output = spec.directory / "capture.mp4"
    size = 1024**3 + 1

    def large_encode(command, **kwargs):
        original(command, **kwargs)
        if command[0].endswith("ffmpeg"):
            # A sparse file exercises real size checks and streaming hashing
            # without allocating a gigabyte buffer or invoking a media encoder.
            with output.open("r+b") as stream:
                stream.truncate(size)

    monkeypatch.setattr(render, "_run", large_encode)
    if accepted:
        result = render.render(spec)
        assert result.path == output and result.size == size
        assert len(result.sha256) == 64
        assert result.frames == frames
    else:
        with pytest.raises(render.LocalRenderError, match="size policy"):
            render.render(spec)
    assert len(calls) == 3  # Rendering, encoding and probe validation all completed.
    assert output.stat().st_size == size
    assert len(list((spec.directory / "frames").glob("*.png"))) == frames
    assert not list(spec.directory.glob("worker-*"))
    # Snapshot hashing keeps its independent 1 GiB policy.
    with pytest.raises(render.LocalRenderError, match="size policy"):
        render.digest(output)


def test_missing_encoder_fails_before_process_or_admission(monkeypatch, spec):
    monkeypatch.setattr(render.shutil, "which", lambda _: None)
    monkeypatch.setattr(render, "_run", lambda *a, **k: pytest.fail("Render started"))
    with pytest.raises(render.LocalRenderError, match="ffmpeg and ffprobe"):
        render.render(spec)
    assert not (spec.directory / "started.json").exists()


def test_tampered_snapshot_never_starts(monkeypatch, spec):
    fixture_runner(monkeypatch, spec)
    (spec.directory / "snapshot.blend").write_bytes(b"modified")
    with pytest.raises(render.LocalRenderError, match="snapshot changed"):
        render.render(spec)
    assert not (spec.directory / "started.json").exists()


@pytest.mark.parametrize("missing,wrong_rate", [(True, False), (False, True)])
def test_invalid_outputs_retain_frames_and_remove_private_profile(
    monkeypatch, spec, missing, wrong_rate
):
    fixture_runner(monkeypatch, spec, missing=missing, wrong_rate=wrong_rate)
    with pytest.raises(render.LocalRenderError):
        render.render(spec)
    assert (spec.directory / "frames/Frame-000001.png").exists()
    assert not list(spec.directory.glob("worker-*"))


def test_encoder_failure_preserves_usable_frame_sequence(monkeypatch, spec):
    calls = fixture_runner(monkeypatch, spec)
    original = render._run

    def fail(command, **kwargs):
        if command[0].endswith("ffmpeg"):
            raise render.LocalRenderError("Encoding failed")
        return original(command, **kwargs)

    monkeypatch.setattr(render, "_run", fail)
    with pytest.raises(render.LocalRenderError, match="Encoding failed"):
        render.render(spec)
    assert len(calls) == 1
    assert len(list((spec.directory / "frames").glob("*.png"))) == spec.frames
    assert not list(spec.directory.glob("worker-*"))


@pytest.mark.parametrize(
    "change",
    [
        {"frame_start": True},
        {"frame_end": 2000},
        {"width": 65},
        {"height": 0},
        {"kind": "AUDIO"},
        {"kind": "STILL"},
        {"fps": float("nan")},
        {"timeout": 0},
        {"encode_timeout": float("inf")},
        {"color_type": "UNKNOWN"},
    ],
)
def test_invalid_spec_rejected_before_work(spec, change):
    with pytest.raises(ValueError):
        replace(spec, **change)


@pytest.mark.parametrize("cancelled", [False, True])
def test_actual_child_is_reaped_on_timeout_or_cancellation(monkeypatch, tmp_path, cancelled):
    children = []
    original = subprocess.Popen
    event = threading.Event()
    timer = threading.Timer(0.1, event.set) if cancelled else None

    def record(*args, **kwargs):
        child = original(*args, **kwargs)
        children.append(child)
        if timer:
            timer.start()
        return child

    monkeypatch.setattr(render.subprocess, "Popen", record)
    started = time.monotonic()
    try:
        with pytest.raises(render.LocalRenderError, match="cancelled|timed out"):
            render._run(
                [sys.executable, "-c", "import time; time.sleep(60)"],
                log=tmp_path / "child.log",
                env=dict(os.environ),
                timeout=5 if cancelled else 0.1,
                cancel=event,
            )
    finally:
        if timer:
            timer.join()
    assert time.monotonic() - started < 5
    assert len(children) == 1 and children[0].poll() is not None


def test_pre_cancelled_command_does_not_spawn(monkeypatch, tmp_path):
    event = threading.Event()
    event.set()
    monkeypatch.setattr(render.subprocess, "Popen", lambda *a, **k: pytest.fail("Spawned child"))
    with pytest.raises(render.RenderCancelled):
        render._run(["ignored"], log=tmp_path / "cancel.log", env={}, timeout=1, cancel=event)


def test_real_child_failure_is_reported_with_retained_log(tmp_path):
    with pytest.raises(render.LocalRenderError, match="process failed"):
        render._run(
            [sys.executable, "-c", "print('fixture failure'); raise SystemExit(3)"],
            log=tmp_path / "failure.log",
            env=dict(os.environ),
            timeout=5,
            cancel=threading.Event(),
        )
    assert "fixture failure" in (tmp_path / "failure.log").read_text()
