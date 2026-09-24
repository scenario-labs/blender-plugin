# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Live native diagnostics preserve process status and owned log artifacts."""

import importlib
import io
import os
import subprocess
import sys
import threading
from pathlib import Path

import pytest

from tools import blender_env


def step(tmp_path, script, **kwargs):
    return blender_env.run_step(
        Path(sys.executable),
        ["-c", script],
        env=dict(os.environ),
        directory=tmp_path,
        name="probe",
        timeout=kwargs.pop("timeout", 10),
        **kwargs,
    )


def test_output_is_forwarded_before_child_finishes_and_utf8_chunks_are_preserved(
    tmp_path, monkeypatch
):
    released = tmp_path / "released"

    class Sink(io.StringIO):
        def write(self, text):
            if "ready" in text:
                released.touch()
            return super().write(text)

    terminal, combined = Sink(), io.StringIO()
    monkeypatch.setattr(sys, "stdout", terminal)
    script = """
import os, time
from pathlib import Path
print('ready', flush=True)
deadline = time.monotonic() + 5
while not Path('released').exists():
    assert time.monotonic() < deadline, 'output was not streamed while child was alive'
    time.sleep(0.01)
os.write(1, bytes([0xe2]))
time.sleep(0.05)
os.write(1, bytes([0x82, 0xac]) + b' done\\n')
os.write(2, b'stderr diagnostic\\r')
time.sleep(0.05)
os.write(2, b'\\n')
"""
    log = step(tmp_path, script, stream=True, log_output=combined)
    expected = "ready\n€ done\nstderr diagnostic\n"
    assert log.read_text() == expected
    assert expected in terminal.getvalue()
    assert combined.getvalue() == "\n[probe]\n" + expected
    assert released.is_file()
    assert not any(thread.name == "blender-output-probe" for thread in threading.enumerate())


def test_nonstreaming_call_keeps_existing_log_only_behavior(tmp_path, capsys):
    log = step(tmp_path, "print('private phase output')")
    assert log.read_text() == "private phase output\n"
    assert "private phase output" not in capsys.readouterr().out


def test_completion_between_temporary_eof_and_event_check_retains_final_bytes():
    stopped, errors = threading.Event(), []

    class RacingSource(io.BytesIO):
        def read(self, size):
            if not stopped.is_set():
                # The read observed temporary EOF, then the child appended and
                # exited before the reader could sample its completion event.
                self.write(b"final diagnostic\n")
                self.seek(0)
                stopped.set()
                return b""
            return super().read(size)

    class LogPath:
        def open(self, mode):
            assert mode == "rb"
            return RacingSource()

    destination = io.StringIO()
    blender_env._forward_log(LogPath(), stopped, [destination], errors)
    assert destination.getvalue() == "final diagnostic\n"
    assert errors == []


def test_failed_child_keeps_its_status_and_full_diagnostics(tmp_path, capsys):
    combined = io.StringIO()
    with pytest.raises(subprocess.CalledProcessError) as error:
        step(
            tmp_path,
            "import sys; print('failure detail', flush=True); sys.exit(7)",
            stream=True,
            log_output=combined,
        )
    assert error.value.returncode == 7
    assert "failure detail" in capsys.readouterr().out
    assert combined.getvalue().endswith("failure detail\n")
    assert (tmp_path / "probe.log").read_text() == "failure detail\n"


def test_timeout_retains_output_and_stops_reader(tmp_path):
    combined = io.StringIO()
    with pytest.raises(subprocess.TimeoutExpired):
        step(
            tmp_path,
            "import time; print('waiting', flush=True); time.sleep(30)",
            timeout=1,
            log_output=combined,
        )
    assert "waiting" in combined.getvalue()
    assert not any(thread.name == "blender-output-probe" for thread in threading.enumerate())
    # The child has been reaped, so the diagnostic file is removable on Windows too.
    (tmp_path / "probe.log").unlink()


@pytest.mark.parametrize("code", [0, 7])
def test_forwarding_error_keeps_phase_log_and_does_not_hide_child_failure(tmp_path, code):
    class BrokenSink:
        def write(self, text):
            if "retained detail" in text:
                raise OSError("fixture destination failure")

        def flush(self):
            pass

    expected = OSError if code == 0 else subprocess.CalledProcessError
    with pytest.raises(expected) as error:
        step(
            tmp_path,
            f"import sys; print('retained detail', flush=True); sys.exit({code})",
            log_output=BrokenSink(),
        )
    if code:
        assert error.value.returncode == 7
    else:
        assert "phase log retained" in str(error.value)
    assert (tmp_path / "probe.log").read_text() == "retained detail\n"


@pytest.fixture
def runner(monkeypatch, tmp_path):
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[2] / "tools"))
    module = importlib.import_module("test_blender")
    monkeypatch.setattr(module, "normal_profile_root", lambda: tmp_path / "normal")
    return module


def test_log_cli_closes_file_and_preserves_failure_status(runner, tmp_path, monkeypatch):
    destination = tmp_path / "logs/native.log"
    monkeypatch.setattr(sys, "argv", ["test_blender.py", "--log", str(destination)])
    opened = []

    def run(args):
        opened.append(args.log_output)
        args.log_output.write("native diagnostic\n")
        return 7

    monkeypatch.setattr(runner, "run", run)
    assert runner.main() == 7
    assert destination.read_text() == "native diagnostic\n"
    assert opened[0].closed


@pytest.mark.parametrize("location", ["existing", "normal-profile"])
def test_log_admission_cannot_overwrite_or_touch_normal_profile(
    runner, tmp_path, monkeypatch, location
):
    destination = tmp_path / ("existing.log" if location == "existing" else "normal/run.log")
    if location == "existing":
        destination.write_bytes(b"preserved")
    monkeypatch.setattr(sys, "argv", ["test_blender.py", "--log", str(destination)])
    monkeypatch.setattr(runner, "run", lambda args: pytest.fail("must not start Blender"))
    assert runner.main() == 1
    if location == "existing":
        assert destination.read_bytes() == b"preserved"
    else:
        assert not destination.parent.exists()


def test_log_cli_closes_file_on_control_failure(runner, tmp_path, monkeypatch):
    monkeypatch.setattr(sys, "argv", ["test_blender.py", "--log", str(tmp_path / "run.log")])
    opened = []

    def run(args):
        opened.append(args.log_output)
        raise KeyboardInterrupt

    monkeypatch.setattr(runner, "run", run)
    with pytest.raises(KeyboardInterrupt):
        runner.main()
    assert opened[0].closed
