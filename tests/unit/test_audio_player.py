# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Offline audio player process ownership and its standalone worker, with fakes, never audible.

The installed native tests start real Blender children; these check the parent's
phases, deadlines, cleanup and environment with a fake process, and the worker's
request, decode, output and lifeline logic with a fake audio module.
"""

import importlib.util
import json
import os
import subprocess
import sys
import threading
import time
from pathlib import Path
from types import SimpleNamespace

import pytest

from scenario.core.jobs import audio_player

ROOT = Path(__file__).resolve().parents[2]
WORKER_PATH = ROOT / "scenario/blender/audio_player_worker.py"
_SPEC = importlib.util.spec_from_file_location("audio_player_worker_under_test", WORKER_PATH)
worker = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(worker)


class Clock:
    def __init__(self):
        self.now = 100.0

    def __call__(self):
        return self.now


class Stdin:
    def __init__(self):
        self.closed = False

    def close(self):
        self.closed = True


class FakeProcess:
    """Stands in for the child: the test sets its exit code; signals are recorded."""

    def __init__(self, command, **options):
        self.command, self.options = command, options
        self.stdin = Stdin()
        self.code, self.signals = None, []
        self.exit_on = {"terminate"}

    def poll(self):
        return self.code

    def terminate(self):
        self.signals.append("terminate")
        if "terminate" in self.exit_on:
            self.code = -15

    def kill(self):
        self.signals.append("kill")
        self.code = -9

    def wait(self, timeout=None):
        if self.code is None:
            raise subprocess.TimeoutExpired("blender", timeout)
        return self.code


@pytest.fixture
def spec(tmp_path):
    worker_file = tmp_path / "audio_player_worker.py"
    worker_file.write_text("# fixture", encoding="utf-8")
    return audio_player.PlayerSpec(Path(sys.executable).resolve(), worker_file, "CoreAudio")


@pytest.fixture
def copy(tmp_path):
    directory = tmp_path / "copies"
    directory.mkdir(mode=0o700)
    source = directory / "media.wav"
    source.write_bytes(b"synthetic private copy")
    return source


def launch(tmp_path, copy, spec, clock=None, **process):
    started = []

    def popen(command, **options):
        child = FakeProcess(command, **options)
        for name, value in process.items():
            setattr(child, name, value)
        started.append(child)
        return child

    player = audio_player.start(copy, tmp_path / "players", spec, popen=popen, clock=clock)
    (child,) = started
    return player, child


def report(player, name, value):
    output = player.directory / "output"
    (output / name).write_text(json.dumps(value), encoding="utf-8")


def test_the_child_runs_offline_isolated_with_a_lifeline_and_no_credentials(
    tmp_path, copy, spec, monkeypatch
):
    for name in ("SCENARIO_API_KEY", "BLENDER_USER_SCRIPTS", "PYTHONPATH", "HTTPS_PROXY"):
        monkeypatch.setenv(name, "inherited")
    monkeypatch.setenv("XDG_RUNTIME_DIR", "kept")
    player, child = launch(tmp_path, copy, spec)
    command = child.command
    assert command[0] == str(spec.binary)
    for flag in ("--offline-mode", "--factory-startup", "--disable-autoexec", "--background"):
        assert flag in command
    # Blender opens no output of its own; the worker opens only the named one.
    assert "-noaudio" in command
    assert command[command.index("--python") + 1] == str(spec.worker)
    request = json.loads(Path(command[-1]).read_text(encoding="utf-8"))
    assert request == {
        "format": 1,
        "source": str(copy),
        "output": str(player.directory / "output"),
        "device": "CoreAudio",
        "max_seconds": 600,
    }
    assert player.directory.name.startswith("listen-")
    assert player.directory.parent == (tmp_path / "players").resolve()
    if os.name != "nt":
        assert player.directory.parent.stat().st_mode & 0o777 == 0o700
        assert Path(command[-1]).stat().st_mode & 0o777 == 0o600
    options = child.options
    assert options["stdin"] is subprocess.PIPE
    assert options["stdout"] is subprocess.DEVNULL
    assert options["stderr"] is subprocess.DEVNULL
    assert options["cwd"] == str(player.directory)
    env = options["env"]
    assert env["BLENDER_USER_RESOURCES"] == str(player.directory / "profile")
    assert env["TMPDIR"] == str(player.directory / "tmp")
    assert env["XDG_RUNTIME_DIR"] == "kept"
    for name in ("SCENARIO_API_KEY", "BLENDER_USER_SCRIPTS", "PYTHONPATH", "HTTPS_PROXY"):
        assert name not in env
    assert player.phase == audio_player.STARTING and player.active


def test_playing_then_ending_follows_the_childs_report_and_exit(tmp_path, copy, spec):
    clock = Clock()
    player, child = launch(tmp_path, copy, spec, clock)
    assert player.poll() is False
    report(player, "playing.json", {"format": 1, "seconds": 2.5})
    assert player.poll() is True
    assert (player.phase, player.seconds) == (audio_player.PLAYING, 2.5)
    assert player.poll() is False
    child.code = 0
    assert player.poll() is True
    assert (player.phase, player.reason) == (audio_player.ENDED, "")
    assert not player.active
    assert child.stdin.closed
    assert player.release() is True
    assert not player.directory.exists()


def test_a_child_still_running_after_its_reported_duration_is_stopped(tmp_path, copy, spec):
    clock = Clock()
    player, child = launch(tmp_path, copy, spec, clock, exit_on=set())
    report(player, "playing.json", {"format": 1, "seconds": 2.0})
    player.poll()
    clock.now += 2.0 + audio_player.END_GRACE - 0.01
    assert player.poll() is False
    clock.now += 0.02
    assert player.poll() is True
    assert player.phase == audio_player.ENDED
    assert child.signals == ["terminate"]
    assert player.release() is False  # Still running: its directory stays.
    clock.now += audio_player.STOP_GRACE
    player.poll()
    assert child.signals == ["terminate", "kill"]
    assert player.release() is True


@pytest.mark.parametrize(
    ("value", "seconds"),
    [
        ({"format": 1, "seconds": None}, None),
        ({"format": 1, "seconds": -1}, None),
        ({"format": 1, "seconds": 9000}, 600.0),
        ({"format": 1, "seconds": True}, None),
    ],
)
def test_reported_durations_are_bounded_by_the_limit(tmp_path, copy, spec, value, seconds):
    clock = Clock()
    player, child = launch(tmp_path, copy, spec, clock, exit_on=set())
    report(player, "playing.json", value)
    player.poll()
    assert (player.phase, player.seconds) == (audio_player.PLAYING, seconds)
    clock.now += (seconds or 600) + audio_player.END_GRACE
    player.poll()
    assert player.phase == audio_player.ENDED


@pytest.mark.parametrize(
    ("code", "message"),
    [
        ("unreadable", "Blender could not decode this audio"),
        ("unsupported", "This audio's sample rate or channel count is not supported"),
        ("empty", "This audio contains no samples"),
        ("too_long", "This audio is longer than Blender plays here; open it in the system player"),
        ("device", "Blender could not play through the audio output chosen in Preferences"),
        ("other", "Blender could not play this audio"),
        (7, "Blender could not play this audio"),
    ],
)
def test_child_failures_map_to_fixed_sanitized_reasons(tmp_path, copy, spec, code, message):
    player, child = launch(tmp_path, copy, spec)
    report(player, "error.json", {"format": 1, "error": code})
    child.code = 1
    assert player.poll() is True
    assert (player.phase, player.reason) == (audio_player.FAILED, message)


@pytest.mark.parametrize("payload", [None, "not json", "x" * 400, {"format": 2, "error": "empty"}])
def test_a_failed_child_without_a_valid_report_has_a_generic_reason(tmp_path, copy, spec, payload):
    player, child = launch(tmp_path, copy, spec)
    path = player.directory / "output" / "error.json"
    if isinstance(payload, str):
        path.write_text(payload, encoding="utf-8")
    elif payload is not None:
        path.write_text(json.dumps(payload), encoding="utf-8")
    child.code = 1
    player.poll()
    assert player.reason == "Blender could not play this audio"


def test_a_child_that_crashes_while_playing_fails(tmp_path, copy, spec):
    player, child = launch(tmp_path, copy, spec)
    report(player, "playing.json", {"format": 1, "seconds": 1})
    player.poll()
    child.code = -11
    player.poll()
    assert (player.phase, player.reason) == (
        audio_player.FAILED,
        "Blender could not play this audio",
    )


def test_a_child_that_never_reports_fails_at_its_start_timeout(tmp_path, copy, spec):
    clock = Clock()
    player, child = launch(tmp_path, copy, spec, clock)
    clock.now += audio_player.START_TIMEOUT - 0.01
    assert player.poll() is False
    clock.now += 0.02
    assert player.poll() is True
    assert player.phase == audio_player.FAILED
    assert "did not start in time" in player.reason
    assert child.signals == ["terminate"] and child.stdin.closed


def test_stop_closes_the_lifeline_terminates_once_and_kills_after_the_grace(tmp_path, copy, spec):
    clock = Clock()
    player, child = launch(tmp_path, copy, spec, clock, exit_on=set())
    player.stop()
    assert (player.phase, player.active) == (audio_player.STOPPED, False)
    assert child.stdin.closed and child.signals == ["terminate"]
    player.stop()
    assert child.signals == ["terminate"]
    # A late report never revives a stopped player.
    report(player, "playing.json", {"format": 1, "seconds": 1})
    assert player.poll() is False
    assert player.phase == audio_player.STOPPED
    clock.now += audio_player.STOP_GRACE
    player.poll()
    assert child.signals == ["terminate", "kill"]
    assert player.release() is True
    assert not player.directory.exists()


def test_wait_is_bounded_and_kills_a_child_that_ignores_termination(tmp_path, copy, spec):
    player, child = launch(tmp_path, copy, spec, exit_on=set())
    assert player.wait(timeout=0.01) is True
    assert child.signals == ["terminate", "kill"]
    assert player.phase == audio_player.STOPPED
    assert player.release() is True


def test_a_failed_launch_or_missing_tools_leave_nothing(tmp_path, copy, spec):
    def refuse(command, **options):
        raise OSError("no executable")

    with pytest.raises(audio_player.AudioPlayerError, match="could not start"):
        audio_player.start(copy, tmp_path / "players", spec, popen=refuse)
    assert list((tmp_path / "players").iterdir()) == []
    missing = audio_player.PlayerSpec(tmp_path / "absent", spec.worker, "CoreAudio")
    with pytest.raises(audio_player.AudioPlayerError, match="executable"):
        audio_player.start(copy, tmp_path / "other", missing, popen=refuse)
    assert not (tmp_path / "other").exists()
    with pytest.raises(audio_player.AudioPlayerError, match="absolute"):
        audio_player.start("media.wav", tmp_path / "players", spec, popen=refuse)
    with pytest.raises(TypeError):
        audio_player.start(copy, tmp_path / "players", object(), popen=refuse)


def test_release_never_removes_a_directory_outside_its_root(tmp_path, copy, spec):
    player, child = launch(tmp_path, copy, spec)
    child.code = 0
    outside = tmp_path / "listen-outside"
    outside.mkdir()
    player.directory = outside
    assert player.release() is True
    assert outside.exists()


def test_sweep_removes_only_stale_unkept_player_directories(tmp_path):
    root = tmp_path / "players"
    root.mkdir()
    names = ("listen-stale", "listen-kept", "listen-young", "play-other", "unrelated")
    for name in names:
        (root / name).mkdir()
        (root / name / "file").write_bytes(b"x")
    old = time.time() - audio_player.STALE_SECONDS - 60
    for name in ("listen-stale", "listen-kept", "play-other", "unrelated"):
        os.utime(root / name, (old, old))
    audio_player.sweep(root, keep=[root / "listen-kept"])
    assert sorted(path.name for path in root.iterdir()) == [
        "listen-kept",
        "listen-young",
        "play-other",
        "unrelated",
    ]
    audio_player.sweep(tmp_path / "absent")  # A missing root is not an error.


@pytest.mark.parametrize(
    "options",
    [
        {"binary": Path("blender")},
        {"worker": Path("worker.py")},
        {"device": ""},
        {"device": "x" * 65},
        {"device": "Core\nAudio"},
        {"device": None},
        {"start_timeout": 0},
        {"start_timeout": float("inf")},
        {"start_timeout": True},
        {"max_seconds": 601},
        {"max_seconds": 0},
        {"max_seconds": 1.5},
    ],
)
def test_spec_is_validated(spec, options):
    values = {
        "binary": spec.binary,
        "worker": spec.worker,
        "device": spec.device,
        "start_timeout": spec.start_timeout,
        "max_seconds": spec.max_seconds,
        **options,
    }
    with pytest.raises(ValueError):
        audio_player.PlayerSpec(**values)


# -- the standalone worker, with a fake audio module ----------------------------


class AudError(Exception):
    pass


class Sound:
    def __init__(self, path=None, *, specs=(8000.0, 1), length=8000, frames=2000, fail=None):
        self.path, self._specs, self._length = path, specs, length
        self.frames, self.fail, self.limits = frames, fail, []

    @property
    def specs(self):
        if self.fail == "open":
            raise AudError("The file couldn't be read with any installed file reader.")
        return self._specs

    @property
    def length(self):
        return self._length

    def limit(self, start, end):
        self.limits.append((start, end))
        return self

    def data(self):
        if self.fail == "decode":
            raise AudError("decode")
        return SimpleNamespace(ndim=2, shape=(self.frames, int(self._specs[1])))


class Handle:
    def __init__(self, seconds, status=1):
        self.started, self.seconds = time.monotonic(), seconds
        self.initial, self.stopped = status, False

    @property
    def status(self):
        if self.initial != 1 or self.stopped or time.monotonic() - self.started >= self.seconds:
            return 0 if self.initial == 1 else self.initial
        return 1

    def stop(self):
        self.stopped = True
        return True


class Aud:
    """The subset of Blender's aud module the worker uses."""

    STATUS_INVALID, STATUS_PLAYING = 0, 1
    error = AudError

    def __init__(self, sound=None, *, seconds=0.05, status=1, device_error=False):
        self.sound = sound or Sound()
        self.seconds, self.status, self.device_error = seconds, status, device_error
        self.devices, self.handles = [], []

    def Sound(self, path):
        self.sound.path = path
        return self.sound

    def Device(self, name):
        if self.device_error:
            raise AudError("Unsupported device type!")
        self.devices.append(name)
        aud = self

        class Device:
            def play(self, sound):
                aud.handles.append(Handle(aud.seconds, aud.status))
                return aud.handles[-1]

        return Device()


@pytest.mark.parametrize(
    ("sound", "code"),
    [
        (Sound(fail="open"), "unreadable"),
        (Sound(fail="decode"), "unreadable"),
        (Sound(specs=(44100.5, 2)), "unsupported"),
        (Sound(specs=(float("nan"), 2)), "unsupported"),
        (Sound(specs=(384000.0, 2)), "unsupported"),
        (Sound(specs=(48000.0, 9)), "unsupported"),
        (Sound(length=8000 * 601), "too_long"),
        (Sound(frames=0), "empty"),
    ],
)
def test_worker_refuses_audio_before_opening_an_output(sound, code):
    aud = Aud(sound)
    with pytest.raises(worker.PlayFailure) as failure:
        worker.prepare(Path("/private/media.wav"), 600, aud)
    assert failure.value.code == code
    assert aud.devices == []


def test_worker_limits_playback_and_reports_the_declared_duration():
    sound = Sound(specs=(8000.0, 2), length=12000)
    limited, seconds = worker.prepare(Path("/private/media.wav"), 600, Aud(sound))
    assert seconds == 1.5
    assert sound.limits == [(0, worker.HEAD_SECONDS), (0, 600)]
    assert limited is sound
    # A container that declares no length still stops at the limit.
    assert worker.prepare(Path("/private/media.ogg"), 600, Aud(Sound(length=-1)))[1] is None


def test_worker_plays_on_the_named_output_until_the_sound_ends():
    aud, started = Aud(seconds=0.05), []
    worker.play(Sound(), "CoreAudio", threading.Event(), aud, lambda: started.append(True))
    assert aud.devices == ["CoreAudio"] and started == [True]
    assert aud.handles[0].stopped


def test_worker_stops_when_its_lifeline_ends():
    aud, stop = Aud(seconds=60), threading.Event()
    read, write = os.pipe()
    try:
        worker.lifeline(stop, read)
        threading.Timer(0.1, os.close, (write,)).start()
        began = time.monotonic()
        worker.play(Sound(), "CoreAudio", stop, aud, lambda: None)
        assert time.monotonic() - began < 5
        assert stop.is_set() and aud.handles[0].stopped
    finally:
        os.close(read)


def test_worker_never_opens_an_output_once_stopped():
    aud, stop = Aud(), threading.Event()
    stop.set()
    worker.play(Sound(), "CoreAudio", stop, aud, lambda: pytest.fail("started"))
    assert aud.devices == []


@pytest.mark.parametrize("aud", [Aud(device_error=True), Aud(status=0)])
def test_worker_reports_an_output_that_cannot_play(aud):
    with pytest.raises(worker.PlayFailure) as failure:
        worker.play(Sound(), "None", threading.Event(), aud, lambda: pytest.fail("started"))
    assert failure.value.code == "device"


def write_request(tmp_path, **changes):
    output = tmp_path / "output"
    output.mkdir(exist_ok=True)
    value = {
        "format": 1,
        "source": str(tmp_path / "media.wav"),
        "output": str(output),
        "device": "CoreAudio",
        "max_seconds": 600,
        **changes,
    }
    path = tmp_path / "request.json"
    path.write_text(json.dumps(value), encoding="utf-8")
    return path, output


@pytest.mark.parametrize(
    "changes",
    [
        {"format": 2},
        {"source": "media.wav"},
        {"device": ""},
        {"device": "x" * 65},
        {"max_seconds": 0},
        {"max_seconds": "600"},
        {"extra": True},
    ],
)
def test_worker_refuses_requests_it_does_not_own(tmp_path, changes):
    path, _ = write_request(tmp_path, **changes)
    with pytest.raises(ValueError):
        worker._request(path)


def test_worker_main_reports_playback_or_a_fixed_failure_code(tmp_path, monkeypatch):
    monkeypatch.setattr(worker, "lifeline", lambda stop: None)
    path, output = write_request(tmp_path)
    monkeypatch.setattr(sys, "argv", ["blender", "--python", "worker.py", "--", str(path)])
    monkeypatch.setitem(sys.modules, "aud", Aud(Sound(length=4000), seconds=0.01))
    worker.main()
    assert json.loads((output / "playing.json").read_text()) == {"format": 1, "seconds": 0.5}
    assert sorted(item.name for item in output.iterdir()) == ["playing.json"]
    failed = tmp_path / "failed"
    failed.mkdir()
    path, output = write_request(failed)
    monkeypatch.setattr(sys, "argv", ["blender", "--python", "worker.py", "--", str(path)])
    monkeypatch.setitem(sys.modules, "aud", Aud(Sound(fail="open")))
    with pytest.raises(worker.PlayFailure):
        worker.main()
    assert json.loads((output / "error.json").read_text()) == {"format": 1, "error": "unreadable"}
