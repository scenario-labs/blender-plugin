# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Exercise the real optional hooks in disposable repositories, never this checkout."""

import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture
def hook_repo(tmp_path):
    env = os.environ | {
        "PRE_COMMIT_HOME": str(tmp_path / "cache"),
        # Reuse the already-locked test environment without downloading tools.
        "UV_PROJECT_ENVIRONMENT": sys.prefix,
        "UV_PYTHON": sys.executable,
        "UV_OFFLINE": "1",
    }
    repo = tmp_path / "repo"
    repo.mkdir()
    for name in (".pre-commit-config.yaml", "pyproject.toml", "uv.lock", ".python-version"):
        shutil.copyfile(ROOT / name, repo / name)
    (repo / "tools").mkdir()
    for name in ("check_secrets.py", "check_rules.py"):
        shutil.copyfile(ROOT / "tools" / name, repo / "tools" / name)

    def run(*args):
        return subprocess.run(args, cwd=repo, env=env, capture_output=True, text=True)

    assert run("git", "init", "--initial-branch", "test-hooks").returncode == 0
    assert run("git", "config", "user.name", "Test").returncode == 0
    assert run("git", "config", "user.email", "test@example.invalid").returncode == 0
    assert run("git", "add", ".").returncode == 0
    assert run("git", "commit", "-m", "test: baseline").returncode == 0
    return repo, run


def test_installed_hooks_reject_invalid_message_and_accept_changed_files(hook_repo):
    repo, run = hook_repo
    result = run(
        sys.executable,
        "-m",
        "pre_commit",
        "install",
        "--hook-type",
        "pre-commit",
        "--hook-type",
        "commit-msg",
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "pre_commit" in (repo / ".git/hooks/pre-commit").read_text()
    assert "pre_commit" in (repo / ".git/hooks/commit-msg").read_text()
    (repo / "example.py").write_text('VALUE = "example"\n')
    assert run("git", "add", "example.py").returncode == 0
    invalid = run("git", "commit", "-m", "update stuff")
    assert invalid.returncode != 0
    assert "check Conventional Commit type" in invalid.stdout + invalid.stderr
    valid = run("git", "commit", "-m", "feat(ui): add a thing")
    assert valid.returncode == 0, valid.stdout + valid.stderr
    message = repo / "merge-message"
    message.write_text("Merge branch 'main' into feat/x\n")
    merge = run(
        sys.executable,
        "-m",
        "pre_commit",
        "run",
        "conventional-pre-commit",
        "--hook-stage",
        "commit-msg",
        "--commit-msg-filename",
        str(message),
    )
    assert merge.returncode == 0, merge.stdout + merge.stderr
    assert run("git", "checkout", "-b", "main").returncode == 0
    blocked = run(sys.executable, "-m", "pre_commit", "run", "no-commit-to-branch")
    assert blocked.returncode == 1


def test_hooks_block_staged_secret_forbidden_path_and_mutable_action(hook_repo):
    repo, run = hook_repo
    fake = "fake_credential_123456789"
    (repo / "notes.txt").write_text("SCENARIO_API_KEY=" + fake + "\n")
    (repo / ".env.probe").touch()
    assert run("git", "add", ".env.probe", "notes.txt").returncode == 0
    result = run(sys.executable, "-m", "pre_commit", "run", "check-secrets")
    assert result.returncode == 1
    assert "environment file" in result.stdout
    assert "scenario-key" in result.stdout
    assert fake not in result.stdout + result.stderr
    action = repo / ".github/workflows/example.yml"
    action.parent.mkdir(parents=True)
    action.write_text(
        "jobs:\n  example:\n    uses: owner/repo/.github/workflows/example.yml@main\n"
    )
    assert run("git", "add", ".github").returncode == 0
    result = run(sys.executable, "-m", "pre_commit", "run", "house-rules")
    assert result.returncode == 1
    assert "actions-pinned" in result.stdout


def test_format_hook_scopes_changes_and_fixture_bytes_are_preserved(hook_repo):
    repo, run = hook_repo
    (repo / "old.py").write_text("legacy=  1\n")
    assert run("git", "add", "old.py").returncode == 0
    assert run("git", "commit", "-m", "test: old formatting debt").returncode == 0
    (repo / "changed.py").write_text("value=  2\n")
    fixture = repo / "tests/fixtures/example.json"
    fixture.parent.mkdir(parents=True)
    fixture.write_bytes(b'{"value":1}  ')
    assert run("git", "add", "changed.py", "tests").returncode == 0
    result = run(sys.executable, "-m", "pre_commit", "run", "ruff-format")
    assert result.returncode == 1  # The framework reports files changed by a hook.
    assert (repo / "changed.py").read_text() == "value = 2\n"
    assert (repo / "old.py").read_text() == "legacy=  1\n"
    for hook in ("end-of-file-fixer", "trailing-whitespace"):
        result = run(sys.executable, "-m", "pre_commit", "run", hook)
        assert result.returncode == 0, result.stdout + result.stderr
    assert fixture.read_bytes() == b'{"value":1}  '
