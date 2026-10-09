# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Offline audio decoder process ownership and output checks, with a fixture child."""

import array
import json
import os
import sys
import threading
from pathlib import Path
from types import SimpleNamespace

import pytest

from scenario.core.audio_waveform import EnvelopeBuilder, WaveformCanceled, WaveformError
from scenario.core.jobs import audio_decode
from scenario.core.jobs.local_render import LocalRenderError, RenderCancelled
from tests.unit.test_audio_waveform import blocks, tone

RATE = 8000


@pytest.fixture
def spec(tmp_path):
    worker = tmp_path / "waveform_worker.py"
    worker.write_text("# fixture", encoding="utf-8")
    return audio_decode.WaveformSpec(Path(sys.executable).resolve(), worker)


@pytest.fixture
def workspace(tmp_path):
    directory = tmp_path / "private"
    directory.mkdir(mode=0o700)
    source = directory / "source.mp3"
    source.write_bytes(b"synthetic encoded audio")
    return directory, source


class Child:
    """Stands in for the offline Blender process: reads its request, writes outputs."""

    def __init__(self, samples=None, channels=1, *, error=None, header=None, data=None):
        self.samples = tone(RATE, 0.25, 0.5) if samples is None else samples
        self.channels, self.error = channels, error
        self.header, self.data = header or {}, data
        self.calls, self.raise_after = [], None

    def __call__(self, command, *, log, env, timeout, cancel, stdout=None):
        request = json.loads(Path(command[-1]).read_text(encoding="utf-8"))
        self.calls.append((command, env, timeout, request, log.parent))
        log.write_text("fixture decoder log")
        output = Path(request["output"])
        if self.error is not None:
            (output / "error.json").write_text(json.dumps({"format": 1, "error": self.error}))
            raise LocalRenderError("Local media process failed; inspect its retained log")
        if self.raise_after is not None:
            raise self.raise_after
        sums, peaks, frames = blocks(self.samples, RATE, self.channels)
        values = array.array(
            "d", [value for pair in zip(sums, peaks, strict=True) for value in pair]
        )
        (output / "blocks.bin").write_bytes(
            self.data if self.data is not None else values.tobytes()
        )
        header = {
            "format": 1,
            "sample_rate": RATE,
            "channels": self.channels,
            "frames": frames,
            "block": RATE // 100,
            **self.header,
        }
        (output / "envelope.json").write_text(json.dumps(header))


def install(monkeypatch, child):
    monkeypatch.setattr(audio_decode, "_run", child)
    return child


def decode(spec, workspace, **options):
    directory, source = workspace
    return audio_decode.decode(source, directory, spec, cancel=threading.Event(), **options)


def test_child_runs_offline_isolated_and_its_blocks_fold_like_samples(monkeypatch, spec, workspace):
    monkeypatch.setenv("SCENARIO_API_SECRET", "synthetic-secret")
    monkeypatch.setenv("PYTHONPATH", "/synthetic/path")
    monkeypatch.setenv("HTTPS_PROXY", "http://proxy.invalid")
    samples = tone(RATE, 0.5, 0.4, channels=2)
    child = install(monkeypatch, Child(samples, channels=2))
    result = decode(spec, workspace, bins=32)
    expected = EnvelopeBuilder(RATE, 2)
    expected.add(samples)
    assert result == expected.finish(bins=32)
    ((command, env, timeout, request, work),) = child.calls
    directory, source = workspace
    assert command[:10] == [
        str(spec.binary),
        "--offline-mode",
        "--factory-startup",
        "--disable-autoexec",
        "--background",
        "-noaudio",
        "--python-exit-code",
        "1",
        "--python",
        str(spec.worker),
    ]
    assert command[10] == "--" and Path(command[11]).parent == work
    assert work.parent == directory and work.name.startswith("decode-")
    assert request == {
        "format": 1,
        "source": str(source),
        "output": str(work / "output"),
        "max_seconds": 600,
        "max_samples": audio_decode.MAX_DECODED_SAMPLES,
    }
    assert timeout == audio_decode.DECODE_TIMEOUT
    assert not any(key.upper().startswith(("SCENARIO_", "PYTHONPATH")) for key in env)
    assert "HTTPS_PROXY" not in env
    assert env["BLENDER_USER_RESOURCES"] == str(work / "profile")
    assert env["TMPDIR"] == str(work / "tmp")
    assert list(directory.iterdir()) == [source]


@pytest.mark.parametrize(
    "code,message",
    [
        ("unreadable", "could not decode"),
        ("unsupported", "not supported"),
        ("empty", "no samples"),
        ("too_long", "duration limit"),
        ("invalid_samples", "invalid audio samples"),
        ("/private/path detail", "could not decode"),
        (["unhashable"], "could not decode"),
    ],
)
def test_child_failures_map_to_fixed_sanitized_reasons(monkeypatch, spec, workspace, code, message):
    install(monkeypatch, Child(error=code))
    with pytest.raises(WaveformError, match=message) as error:
        decode(spec, workspace)
    assert "private" not in str(error.value) and "log" not in str(error.value)
    directory, source = workspace
    assert list(directory.iterdir()) == [source]


def test_a_failed_child_without_a_report_is_unreadable(monkeypatch, spec, workspace):
    child = install(monkeypatch, Child())
    child.raise_after = LocalRenderError("Local media process failed; inspect its retained log")
    with pytest.raises(WaveformError, match="could not decode"):
        decode(spec, workspace)


def test_timeout_cancellation_and_cleanup(monkeypatch, spec, workspace):
    directory, source = workspace
    clock = iter([100.0, 100.0 + audio_decode.DECODE_TIMEOUT])
    monkeypatch.setattr(audio_decode, "time", SimpleNamespace(monotonic=lambda: next(clock)))
    child = install(monkeypatch, Child())
    child.raise_after = LocalRenderError("Local capture timed out; inspect retained frames")
    with pytest.raises(WaveformError, match="timed out"):
        decode(spec, workspace)
    monkeypatch.setattr(audio_decode, "time", SimpleNamespace(monotonic=lambda: 100.0))
    child.raise_after = RenderCancelled("Local capture cancelled")
    with pytest.raises(WaveformCanceled):
        decode(spec, workspace)
    assert list(directory.iterdir()) == [source]
    cancel = threading.Event()
    cancel.set()
    with pytest.raises(WaveformCanceled):
        audio_decode.decode(source, directory, spec, cancel=cancel)
    assert len(child.calls) == 2


def test_cancellation_during_a_successful_child_publishes_nothing(monkeypatch, spec, workspace):
    directory, source = workspace
    cancel = threading.Event()
    child = install(monkeypatch, Child())

    def run(command, **options):
        child(command, **options)
        cancel.set()

    monkeypatch.setattr(audio_decode, "_run", run)
    with pytest.raises(WaveformCanceled):
        audio_decode.decode(source, directory, spec, cancel=cancel)
    assert list(directory.iterdir()) == [source]


def frames_of(samples):
    return blocks(samples, RATE, 1)[2]


@pytest.mark.parametrize(
    "header,data",
    [
        ({"extra": 1}, None),
        ({"format": 2}, None),
        ({"format": True}, None),
        ({"sample_rate": 8000.0}, None),
        ({"block": 81}, None),
        ({"channels": 9}, None),
        ({"sample_rate": 0}, None),
        ({"frames": 0}, None),
        ({"frames": 8000 * 600 + 1}, None),
        ({}, b""),
        ({}, b"\x00" * 16),
        ({}, array.array("d", [float("nan"), 0.5] * 25).tobytes()),
        ({}, array.array("d", [80.0, 0.5] * 25).tobytes()),  # Louder RMS than its peak.
    ],
    ids=[
        "extra-key",
        "format",
        "boolean-format",
        "float-rate",
        "block",
        "channels",
        "rate",
        "no-frames",
        "too-many-frames",
        "no-blocks",
        "short-blocks",
        "nan",
        "rms-above-peak",
    ],
)
def test_invalid_child_output_is_rejected(monkeypatch, spec, workspace, header, data):
    install(monkeypatch, Child(header=header, data=data))
    with pytest.raises(WaveformError, match="invalid waveform"):
        decode(spec, workspace)
    directory, source = workspace
    assert list(directory.iterdir()) == [source]


def test_decoded_sample_and_duration_limits_bind_the_output(monkeypatch, spec, workspace):
    samples = tone(RATE, 0.25, 0.5)
    install(monkeypatch, Child(samples))
    small = audio_decode.WaveformSpec(spec.binary, spec.worker, max_samples=frames_of(samples) - 1)
    with pytest.raises(WaveformError, match="invalid waveform"):
        decode(small, workspace)
    child = install(monkeypatch, Child(tone(RATE, 1.5, 0.5)))
    with pytest.raises(WaveformError, match="invalid waveform"):
        decode(spec, workspace, max_seconds=1)
    assert child.calls[0][3]["max_seconds"] == 1


def test_missing_executable_or_storage_fails_before_any_process(monkeypatch, spec, workspace):
    child = install(monkeypatch, Child())
    missing = audio_decode.WaveformSpec(spec.binary.parent / "missing-blender", spec.worker)
    with pytest.raises(WaveformError, match="executable"):
        decode(missing, workspace)
    directory, source = workspace
    with pytest.raises(WaveformError, match="storage"):
        audio_decode.decode(source, directory / "absent", spec, cancel=threading.Event())
    with pytest.raises(TypeError):
        audio_decode.decode(source, directory, None)
    with pytest.raises(ValueError):
        audio_decode.decode(source, directory, spec, max_seconds=601)
    with pytest.raises(ValueError):
        audio_decode.decode(source, directory, spec, bins=0)
    assert child.calls == []


@pytest.mark.parametrize(
    "options",
    [
        {"binary": Path("relative-blender")},
        {"worker": "not-a-path"},
        {"timeout": 0},
        {"timeout": float("inf")},
        {"timeout": True},
        {"timeout": 601},
        {"max_samples": 0},
        {"max_samples": audio_decode.MAX_DECODED_SAMPLES + 1},
    ],
)
def test_spec_is_validated(spec, options):
    values = {"binary": spec.binary, "worker": spec.worker, **options}
    with pytest.raises(ValueError):
        audio_decode.WaveformSpec(**values)


def test_source_stamp_accepts_only_bounded_regular_files(tmp_path, monkeypatch):
    path = tmp_path / "sound.wav"
    path.write_bytes(b"synthetic")
    first = audio_decode.source_stamp(path)
    assert first == audio_decode.source_stamp(str(path))
    path.write_bytes(b"synthetic changed")
    assert audio_decode.source_stamp(path) != first
    with pytest.raises(WaveformError, match="missing"):
        audio_decode.source_stamp(tmp_path / "absent.wav")
    with pytest.raises(WaveformError, match="regular"):
        audio_decode.source_stamp(tmp_path)
    empty = tmp_path / "empty.wav"
    empty.write_bytes(b"")
    with pytest.raises(WaveformError, match="256 MiB"):
        audio_decode.source_stamp(empty)
    monkeypatch.setattr(audio_decode, "SOURCE_MAX_BYTES", 4)
    with pytest.raises(WaveformError, match="256 MiB"):
        audio_decode.source_stamp(path)
    link = tmp_path / "link.wav"
    try:
        link.symlink_to(path)
    except OSError:
        pytest.skip("Symlink creation is unavailable")
    with pytest.raises(WaveformError, match="regular"):
        audio_decode.source_stamp(link)
    if os.name != "nt":
        fifo = tmp_path / "fifo.wav"
        os.mkfifo(fifo)
        with pytest.raises(WaveformError, match="regular"):
            audio_decode.source_stamp(fifo)


def test_sweep_removes_only_stale_decode_directories(tmp_path):
    stale, fresh, other = tmp_path / "decode-old", tmp_path / "decode-new", tmp_path / "keep-old"
    for path in (stale, fresh, other):
        path.mkdir()
        (path / "decode.log").write_text("fixture")
    old = 1_000_000.0
    for path in (stale, other):
        os.utime(path, (old, old))
    os.utime(fresh, (old + audio_decode.STALE_SECONDS, old + audio_decode.STALE_SECONDS))
    target = tmp_path / "target"
    target.mkdir()
    link = tmp_path / "decode-link"
    try:
        link.symlink_to(target, target_is_directory=True)
    except OSError:
        link = None
    audio_decode.sweep(tmp_path, now=old + audio_decode.STALE_SECONDS + 1)
    assert not stale.exists() and fresh.is_dir() and other.is_dir() and target.is_dir()
    if link is not None:
        assert link.is_symlink()
    audio_decode.sweep(tmp_path / "absent")
