# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Process lifetime and CLI contracts for the generic offline Blender command."""

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from tools import blender_env


@pytest.fixture
def command(tmp_path, monkeypatch):
    artifacts = tmp_path / "commands"
    normal = tmp_path / "normal-profile"
    normal.mkdir()
    marker = normal / "userpref.blend"
    marker.write_bytes(b"untouched")
    monkeypatch.setattr(blender_env, "normal_profile_root", lambda: normal)
    monkeypatch.setattr(blender_env, "find_blender", lambda explicit=None: Path(sys.executable))
    monkeypatch.setenv("BLENDER_USER_RESOURCES", str(normal))
    monkeypatch.setenv("BLENDER_USER_SCRIPTS", str(normal / "scripts"))
    monkeypatch.setenv("SCENARIO_API_SECRET", "fixture-only")
    monkeypatch.setenv("PYTHONPATH", str(normal / "python"))
    return artifacts, marker


def test_real_child_uses_private_environment_cwd_and_storage_until_exit(command, monkeypatch):
    artifacts, marker = command
    monkeypatch.chdir(artifacts.parent)
    (artifacts.parent / "relative-input.txt").write_text("relative input")
    real_run = subprocess.run
    observed = []

    def child(argv, **kwargs):
        assert argv[1] == "--offline-mode"
        # Python stands in for Blender; remove only its Blender-specific flag.
        result = real_run([argv[0], *argv[2:]], capture_output=True, text=True, **kwargs)
        observed.append(json.loads(result.stdout))
        return result

    monkeypatch.setattr(blender_env.subprocess, "run", child)
    script = """
import json, os
from pathlib import Path
profile = Path(os.environ['BLENDER_USER_RESOURCES'])
temporary = Path(os.environ['TMPDIR'])
assert profile.is_dir() and temporary.is_dir()
assert Path('relative-input.txt').read_text() == 'relative input'
assert not any(k.startswith('SCENARIO_') for k in os.environ)
assert 'BLENDER_USER_SCRIPTS' not in os.environ and 'PYTHONPATH' not in os.environ
(profile / 'userpref.blend').write_bytes(b'owned')
print(json.dumps({'profile': str(profile), 'temporary': str(temporary)}))
"""
    result = blender_env.run(["-c", script], artifacts=artifacts)
    assert result.returncode == 0
    assert len(observed) == 1
    assert not Path(observed[0]["profile"]).exists()
    assert not Path(observed[0]["temporary"]).exists()
    assert list(artifacts.iterdir()) == []
    assert marker.read_bytes() == b"untouched"
    assert os.environ["BLENDER_USER_RESOURCES"] == str(marker.parent)


@pytest.mark.parametrize("failure", ["exit", "timeout", "interrupt", "spawn"])
def test_failure_cleanup_preserves_original_error_and_unrelated_profile(
    command, monkeypatch, failure
):
    artifacts, marker = command
    failures = {
        "exit": subprocess.CalledProcessError(9, "fixture"),
        "timeout": subprocess.TimeoutExpired("fixture", 1),
        "interrupt": KeyboardInterrupt(),
        "spawn": OSError("fixture launch failed"),
    }
    error = failures[failure]
    observed = []

    def child(argv, **kwargs):
        profile = Path(kwargs["env"]["BLENDER_USER_RESOURCES"])
        assert profile.is_dir()
        assert kwargs["check"] is True
        observed.append(profile)
        raise error

    monkeypatch.setattr(blender_env.subprocess, "run", child)
    with pytest.raises(type(error)) as caught:
        blender_env.run(["--background"], artifacts=artifacts)
    assert caught.value is error
    assert observed and not observed[0].exists()
    assert marker.read_bytes() == b"untouched"


def test_real_timeout_reaps_child_before_removing_its_profile(command, monkeypatch):
    artifacts, _ = command
    real_run = subprocess.run

    def child(argv, **kwargs):
        return real_run([argv[0], *argv[2:]], **kwargs)

    monkeypatch.setattr(blender_env.subprocess, "run", child)
    with pytest.raises(subprocess.TimeoutExpired):
        blender_env.run(["-c", "import time; time.sleep(10)"], artifacts=artifacts, timeout=0.1)
    assert list(artifacts.iterdir()) == []


@pytest.mark.parametrize(
    ("args", "kwargs", "message"),
    [
        ([], {}, "Supply Blender arguments"),
        ("--background", {}, "sequence"),
        ([None], {}, "Supply Blender arguments"),
        (["--online-mode"], {}, "offline"),
        (["--online-mode=true"], {}, "offline"),
        (["--background"], {"isolated": False}, "Normal-profile"),
        (["--background"], {"timeout": 0}, "Timeout"),
        (["--background"], {"timeout": float("nan")}, "Timeout"),
        (["--background"], {"timeout": float("inf")}, "Timeout"),
    ],
)
def test_invalid_requests_fail_before_profile_allocation(command, args, kwargs, message):
    artifacts, marker = command
    with pytest.raises(ValueError, match=message):
        blender_env.run(args, artifacts=artifacts, **kwargs)
    assert not artifacts.exists()
    assert marker.read_bytes() == b"untouched"


def test_cannot_allocate_artifacts_inside_normal_profile(command):
    _, marker = command
    with pytest.raises(ValueError, match="outside the normal"):
        blender_env.run(["--background"], artifacts=marker.parent / "commands")
    assert list(marker.parent.iterdir()) == [marker]


def test_script_arguments_are_forwarded_exactly_without_parsing_or_shell(command, monkeypatch):
    artifacts, _ = command
    args = ["--python", "path with spaces.py", "--", "--online-mode", "literal;$value"]

    def child(argv, **kwargs):
        assert argv == [sys.executable, "--offline-mode", *args]
        assert "shell" not in kwargs and "cwd" not in kwargs
        assert kwargs["check"] is False
        return subprocess.CompletedProcess(argv, 7)

    monkeypatch.setattr(blender_env.subprocess, "run", child)
    assert blender_env.run(args, artifacts=artifacts, check=False).returncode == 7
    assert list(artifacts.iterdir()) == []


@pytest.mark.parametrize(("code", "expected"), [(0, 0), (7, 7), (-15, 143)])
def test_cli_preserves_child_status_and_forwards_explicit_selection(monkeypatch, code, expected):
    monkeypatch.setattr(sys, "argv", ["blender_env.py", "run", "--blender", "chosen", "--", "-b"])

    def run(args, **kwargs):
        assert args == ["-b"]
        assert kwargs["blender"] == "chosen" and kwargs["check"] is False
        return subprocess.CompletedProcess(args, code)

    monkeypatch.setattr(blender_env, "run", run)
    assert blender_env.main() == expected


@pytest.mark.parametrize(
    ("error", "expected"),
    [(subprocess.TimeoutExpired("fixture", 1), 124), (KeyboardInterrupt(), 130)],
)
def test_cli_reports_timeout_and_interrupt_without_command_disclosure(
    monkeypatch, capsys, error, expected
):
    monkeypatch.setattr(sys, "argv", ["blender_env.py", "run", "--", "-b"])

    def run(*args, **kwargs):
        raise error

    monkeypatch.setattr(blender_env, "run", run)
    assert blender_env.main() == expected
    output = capsys.readouterr()
    assert "fixture" not in output.err and "Traceback" not in output.err


@pytest.mark.parametrize("args", [["run"], ["--version", "run", "--", "-b"]])
def test_cli_rejects_ambiguous_or_empty_run(monkeypatch, args):
    monkeypatch.setattr(sys, "argv", ["blender_env.py", *args])
    with pytest.raises(SystemExit) as caught:
        blender_env.main()
    assert caught.value.code == 2
