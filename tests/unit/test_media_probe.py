# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Receipt copies, bounded offline probe metadata and owned child cleanup."""

import hashlib
import json
import subprocess
import sys
import threading
from fractions import Fraction
from pathlib import Path

import pytest

import scenario.core.jobs.local_render as process_owner
from scenario.core.jobs import media_probe as probe
from scenario.core.jobs.transfers import DownloadedResult


def audio_metadata(**extra):
    return {
        "streams": [{"codec_type": "audio", "duration_ts": 48001, "time_base": "1/48000", **extra}]
    }


def file_receipt(tmp_path):
    path = tmp_path / "saved.wav"
    path.write_bytes(b"saved media fixture")
    return path, DownloadedResult(
        path.name, path.stat().st_size, hashlib.sha256(path.read_bytes()).hexdigest()
    )


@pytest.fixture
def fixture(tmp_path, monkeypatch):
    path, receipt = file_receipt(tmp_path)
    root = tmp_path / "scratch"
    root.mkdir()
    calls = []
    monkeypatch.setattr(probe, "probe_tool", lambda: Path("/synthetic/ffprobe"))

    def run(command, *, stdout, **options):
        calls.append((command, options))
        copied = Path(command[command.index("-i") + 1])
        assert copied.read_bytes() == path.read_bytes()
        stdout.write_text(json.dumps(audio_metadata()))

    monkeypatch.setattr(probe, "_run", run)
    return path, receipt, root, calls


def test_only_verified_private_copy_reaches_forced_offline_demuxer(fixture, monkeypatch):
    path, receipt, root, calls = fixture
    monkeypatch.setenv("SCENARIO_SDK_API_KEY", "synthetic-ambient")
    monkeypatch.setenv("HTTPS_PROXY", "synthetic-proxy")
    result = probe.measure(path, receipt, "audio/wav", root=root)
    assert result.duration == Fraction(48001, 48000)
    assert (result.sha256, result.size) == (receipt.sha256, receipt.size)
    command, options = calls[0]
    assert command[command.index("-protocol_whitelist") + 1] == "file"
    assert command[command.index("-f") + 1] == "wav"
    assert "SCENARIO_SDK_API_KEY" not in options["env"] and "HTTPS_PROXY" not in options["env"]
    assert str(path) not in command
    assert list(root.iterdir()) == [] and path.read_bytes() == b"saved media fixture"


@pytest.mark.parametrize("media_type", ["audio/m4a", "audio/mp4"])
def test_m4a_upload_and_container_types_use_the_same_verified_demuxer(fixture, media_type):
    path, receipt, root, calls = fixture
    result = probe.measure(path, receipt, media_type, root=root)
    assert result.kind == "audio"
    assert result.duration == Fraction(48001, 48000)
    assert (result.sha256, result.size) == (receipt.sha256, receipt.size)
    command, _ = calls[0]
    assert command[command.index("-f") + 1] == "mov"
    assert Path(command[command.index("-i") + 1]).suffix == ".m4a"
    assert list(root.iterdir()) == [] and path.read_bytes() == b"saved media fixture"


@pytest.mark.parametrize("change", ["bytes", "size", "symlink", "missing"])
def test_changed_unavailable_or_linked_sources_never_reach_probe(fixture, change):
    path, receipt, root, calls = fixture
    if change == "bytes":
        path.write_bytes(b"other media fixture")
    elif change == "size":
        path.write_bytes(b"changed")
    elif change == "symlink":
        other = path.with_name("other.wav")
        path.rename(other)
        path.symlink_to(other)
    else:
        path.unlink()
    with pytest.raises(probe.MediaProbeError):
        probe.measure(path, receipt, "audio/wav", root=root)
    assert not calls and list(root.iterdir()) == []


def test_missing_tool_and_precancel_leave_source_and_storage_untouched(fixture, monkeypatch):
    path, receipt, root, calls = fixture
    monkeypatch.setattr(
        probe, "probe_tool", lambda: (_ for _ in ()).throw(probe.MediaProbeError("Missing ffprobe"))
    )
    with pytest.raises(probe.MediaProbeError):
        probe.measure(path, receipt, "audio/wav", root=root)
    cancel = threading.Event()
    cancel.set()
    with pytest.raises(process_owner.RenderCancelled):
        probe.measure(path, receipt, "audio/wav", root=root, cancel=cancel)
    assert not calls and list(root.iterdir()) == [] and path.exists()


def test_missing_ffprobe_never_downloads_or_selects_a_fallback(monkeypatch):
    monkeypatch.setattr(probe.shutil, "which", lambda name: None)
    with pytest.raises(probe.MediaProbeError, match="Install ffprobe"):
        probe.probe_tool()


@pytest.mark.parametrize(
    "metadata",
    [
        {},
        {"streams": []},
        {"streams": [{"codec_type": "audio", "duration": "NaN"}]},
        {"streams": [{"codec_type": "audio", "duration": "-1"}]},
        {"streams": [{"codec_type": "audio", "duration": "90000"}]},
        {
            "streams": [
                {"codec_type": "audio", "duration": "1"},
                {"codec_type": "audio", "duration": "1"},
            ]
        },
        {
            "streams": [
                {"codec_type": "audio", "duration": "1"},
                {"codec_type": "video", "duration": "1"},
            ]
        },
        {"streams": [{"codec_type": "audio", "duration_ts": False, "time_base": "1/30"}]},
    ],
)
def test_invalid_or_ambiguous_metadata_is_not_a_measured_duration(metadata, tmp_path):
    _, receipt = file_receipt(tmp_path)
    with pytest.raises(probe.MediaProbeError):
        probe._metadata(json.dumps(metadata), "audio", receipt)


def test_video_requires_its_own_stream_duration_when_audio_is_present(tmp_path):
    _, receipt = file_receipt(tmp_path)
    picture = {"codec_type": "video", "width": 128, "height": 128, "avg_frame_rate": "30000/1001"}
    audio = {"codec_type": "audio", "duration": "8"}
    value = {"streams": [picture, audio], "format": {"duration": "8"}}
    with pytest.raises(probe.MediaProbeError):
        probe._metadata(json.dumps(value), "video", receipt)
    picture["tags"] = {"DURATION": "00:00:04.004000000"}
    result = probe._metadata(json.dumps(value), "video", receipt)
    assert result.duration == Fraction(1001, 250) and result.audio_duration == 8
    assert result.frame_rate == Fraction(30000, 1001)


@pytest.mark.parametrize(
    "rate", [{}, {"avg_frame_rate": None}, {"avg_frame_rate": "0/0"}, {"avg_frame_rate": "N/A"}]
)
def test_unknown_video_frame_rate_preserves_duration_without_guessing(tmp_path, rate):
    _, receipt = file_receipt(tmp_path)
    picture = {
        "codec_type": "video",
        "width": 128,
        "height": 128,
        "tags": {"DURATION": "00:00:04.004000000"},
        **rate,
    }
    result = probe._metadata(json.dumps({"streams": [picture]}), "video", receipt)
    assert result.duration == Fraction(1001, 250)
    assert result.frame_rate is None
    del picture["tags"]
    with pytest.raises(probe.MediaProbeError):
        probe._metadata(json.dumps({"streams": [picture]}), "video", receipt)


@pytest.mark.parametrize("rate", [False, -1, "-30/1", "0/1", "241/1", "30/0", "invalid"])
def test_invalid_reported_video_frame_rate_is_not_treated_as_unknown(tmp_path, rate):
    _, receipt = file_receipt(tmp_path)
    picture = {
        "codec_type": "video",
        "width": 128,
        "height": 128,
        "duration": "4",
        "avg_frame_rate": rate,
    }
    with pytest.raises(probe.MediaProbeError):
        probe._metadata(json.dumps({"streams": [picture]}), "video", receipt)


def test_audio_cover_art_does_not_become_an_ambiguous_video(tmp_path):
    _, receipt = file_receipt(tmp_path)
    value = audio_metadata()
    value["streams"].append({"codec_type": "video", "disposition": {"attached_pic": 1}})
    assert probe._metadata(json.dumps(value), "audio", receipt).duration == Fraction(48001, 48000)


@pytest.mark.parametrize("kind", ["oversized", "malformed", "exception"])
def test_invalid_probe_output_and_failures_remove_owned_copies(fixture, monkeypatch, kind):
    path, receipt, root, _ = fixture

    def run(command, *, stdout, **options):
        if kind == "exception":
            raise OSError("private diagnostic")
        stdout.write_text("x" * 65537 if kind == "oversized" else "{invalid")

    monkeypatch.setattr(probe, "_run", run)
    with pytest.raises(probe.MediaProbeError) as error:
        probe.measure(path, receipt, "audio/wav", root=root)
    assert (
        "private diagnostic" not in str(error.value)
        and list(root.iterdir()) == []
        and path.exists()
    )


@pytest.mark.parametrize("reason", ["timeout", "cancel"])
def test_real_owned_probe_child_is_reaped_on_timeout_or_cancel(tmp_path, monkeypatch, reason):
    path, receipt = file_receipt(tmp_path)
    root = tmp_path / "scratch"
    root.mkdir()
    monkeypatch.setattr(probe, "probe_tool", lambda: Path(sys.executable))
    actual = subprocess.Popen
    spawned = []
    cancel = threading.Event()
    timer = None

    def launch(command, **options):
        nonlocal timer
        child = actual([sys.executable, "-c", "import time; time.sleep(60)"], **options)
        spawned.append(child)
        if reason == "cancel":
            timer = threading.Timer(0.2, cancel.set)
            timer.start()
        return child

    monkeypatch.setattr(process_owner.subprocess, "Popen", launch)
    try:
        expected = process_owner.RenderCancelled if reason == "cancel" else probe.MediaProbeError
        with pytest.raises(expected):
            probe.measure(
                path,
                receipt,
                "audio/wav",
                root=root,
                cancel=cancel,
                timeout=0.5 if reason == "timeout" else 5,
            )
    finally:
        if timer:
            timer.cancel()
            timer.join()
    assert len(spawned) == 1 and spawned[0].poll() is not None
    assert list(root.iterdir()) == [] and path.exists()


def test_mp4_disables_external_tracks(fixture, monkeypatch):
    path, receipt, root, calls = fixture

    def run(command, *, stdout, **options):
        calls.append(command)
        stdout.write_text(
            json.dumps(
                {
                    "streams": [
                        {
                            "codec_type": "video",
                            "duration_ts": 30,
                            "time_base": "1/30",
                            "width": 128,
                            "height": 128,
                            "avg_frame_rate": "30/1",
                        }
                    ]
                }
            )
        )

    monkeypatch.setattr(probe, "_run", run)
    assert probe.measure(path, receipt, "video/mp4", root=root).duration == 1
    command = calls[0]
    assert command[command.index("-enable_drefs") + 1] == "0"
    assert command[command.index("-use_absolute_path") + 1] == "0"
