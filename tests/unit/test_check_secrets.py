# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""The staged guard reports common leaks without exposing their contents."""

import os
import subprocess

import pytest

from tools import check_secrets as checker


@pytest.mark.parametrize(
    "path",
    [
        ".env",
        ".env.local",
        "nested/.env.probe",
        "cert.PEM",
        "private.key",
        "a.p12",
        "a.pfx",
        "credentials-prod.json",
        "service_account.json",
        "folder/service-account-old.json",
        "foo.blend",
        "foo.blend2",
        "userpref.blend",
        "dist/x.zip",
        "state/jobs.json",
        "x.exe",
        "x.dll",
        "x.so",
        "x.dylib",
        "x.bin",
        "x.o",
        "x.a",
        "x.class",
        "x.jar",
        "x.pyc",
        "x.pyo",
        "x.db",
        "x.sqlite",
        "x.sqlite3",
        "x.dump",
        "x.bak",
    ],
)
def test_forbidden_files(path):
    assert checker.forbidden_reason(path)


@pytest.mark.parametrize(
    "path",
    [
        ".env.example",
        "docs/.env.example",
        "tools/blank.blend",
        "tests/fixtures/jobs.json",
        "tests/fixtures/nested/jobs.json",
        "scenario/core/jobs.py",
        "image.png",
        "README.md",
    ],
)
def test_allowed_files(path):
    assert checker.forbidden_reason(path) is None


EXAMPLES = [
    ("scenario-key", "SCENARIO_TEST_API_KEY=" + "fake_value_12345678", "SCENARIO_TEST_API_KEY="),
    ("scenario-key", "SCENARIO_API_KEY=" + "fake_value_12345678", "SCENARIO_API_KEY="),
    (
        "scenario-key",
        '"SCENARIO_API_SECRET": "' + "fake_value_12345678" + '"',
        "SCENARIO_API_SECRET=abc",
    ),
    ("basic-auth", "Authorization: Basic " + "A" * 24, "Authorization: Basic <token>"),
    ("bearer", "Bearer " + "b" * 28, "Bearer <token>"),
    ("curl-user", "curl -u " + "username12:password12", "curl -u $KEY:$SECRET"),
    ("private-key", "-----BEGIN " + "RSA PRIVATE KEY-----", "PUBLIC KEY"),
    ("github-token", "ghp_" + "t" * 36, "ghp_placeholder"),
    ("github-token", "github_pat_" + "t" * 82, "github_pat_placeholder"),
    ("aws-key", "AKIA" + "A" * 16, "AKIAexample"),
    ("anthropic-key", "sk-ant-" + "a" * 24, "sk-ant-placeholder"),
    ("google-key", "AIza" + "A" * 35, "AIzaexample"),
    (
        "signed-url",
        "https://cdn.example/?" + "X-Amz-Signature=" + "fake",
        "https://cdn.example/file",
    ),
    ("password", "PASSWORD='" + "fake_password" + "'", "password=''"),
]


@pytest.mark.parametrize("pattern,positive,negative", EXAMPLES)
def test_patterns_and_redaction(pattern, positive, negative):
    findings = checker.scan_lines("example.txt", [(7, positive)])
    assert pattern in [finding.pattern for finding in findings]
    assert all(finding.line == 7 for finding in findings)
    assert all(positive not in str(finding) for finding in findings)
    assert checker.scan_lines("example.txt", [(8, negative)]) == []
    assert checker.scan_lines("example.txt", [(9, positive + " # secrets-allow")]) == []


def test_never_prints_line_with_multiple_sensitive_values():
    first, second = "first_fake_value_123", "second_fake_value_456"
    line = f"SCENARIO_API_KEY={first} unrelated={second}"
    output = "\n".join(map(str, checker.scan_lines("notes.txt", [(3, line)])))
    assert "scenario-key" in output
    assert first not in output
    assert second not in output


def test_scanner_and_own_test_examples_are_exempt():
    example = [(1, "Bearer " + "x" * 25)]
    assert checker.scan_lines("tools/check_secrets.py", example) == []
    assert checker.scan_lines("tests/unit/test_check_secrets.py", example) == []


def git(root, *args):
    return subprocess.run(["git", *args], cwd=root, capture_output=True, check=True).stdout


@pytest.fixture
def repo(tmp_path):
    git(tmp_path, "init", "--initial-branch", "test-hooks")
    git(tmp_path, "config", "user.name", "Test")
    git(tmp_path, "config", "user.email", "test@example.invalid")
    return tmp_path


def stage(root, path, content):
    file = root / path
    file.parent.mkdir(parents=True, exist_ok=True)
    file.write_bytes(content.encode() if isinstance(content, str) else content)
    git(root, "add", "--", path)
    return file


def test_uses_index_not_clean_worktree_and_reports_staged_line(repo, capsys):
    file = stage(repo, "notes.txt", "old\nunchanged\n")
    git(repo, "commit", "-m", "test: baseline")
    secret = "fake_staged_credential_123"
    stage(repo, "notes.txt", "old\nunchanged\nSCENARIO_API_KEY=" + secret + "\n")
    file.write_text("clean working tree\n")
    assert checker.main([], root=repo) == 1
    output = capsys.readouterr().out
    assert "'notes.txt':3 scenario-key" in output
    assert secret not in output
    assert file.read_text() == "clean working tree\n"


def test_ignores_deleted_existing_and_unstaged_content(repo, capsys):
    secret = "Bearer " + "x" * 28
    stage(repo, "notes.txt", secret + "\nkeep\nremove\n")
    git(repo, "commit", "-m", "test: preexisting content")
    file = stage(repo, "notes.txt", secret + "\nkeep\nnew clean line\n")
    file.write_text(secret + "\nSCENARIO_API_SECRET=" + "uncommitted_value_123" + "\n")
    (repo / ".env.local").write_text("not staged")
    assert checker.main([], root=repo) == 0
    assert capsys.readouterr().out == ""
    stage(repo, "notes.txt", "clean\n")
    assert checker.main([], root=repo) == 0


def test_literal_special_paths_and_explicit_selection(repo, capsys):
    names = ["space name.txt", "literal[1].txt", "-leading.txt"]
    if os.name != "nt":
        names.append("line\nbreak.txt")
    for name in names:
        stage(repo, name, "Bearer " + "x" * 26 + "\n")
    stage(repo, "clean.txt", "clean\n")
    assert checker.main(["clean.txt"], root=repo) == 0
    for name in names:
        assert checker.main(["--", name], root=repo) == 1
        output = capsys.readouterr().out
        assert repr(name) in output
        assert "x" * 26 not in output


@pytest.mark.skipif(os.name == "nt", reason="Windows filenames cannot contain a colon")
@pytest.mark.parametrize("prefix", ["0", "1", "2", "3"])
def test_stage_like_filename_reads_its_own_index_blob(repo, capsys, prefix):
    stage(repo, "notes.txt", b"\0binary counterpart\n")
    name = f"{prefix}:notes.txt"
    value = "fake_staged_credential_123"
    file = stage(repo, name, "SCENARIO_API_KEY=" + value + "\n")
    file.write_text("clean working tree\n")
    assert checker.main([], root=repo) == 1
    output = capsys.readouterr().out
    assert f"{name!r}:1 scenario-key" in output
    assert value not in output


def test_rename_to_forbidden_path_and_explicit_unstaged_probe(repo, capsys):
    stage(repo, "source.txt", "clean\n")
    git(repo, "commit", "-m", "test: baseline")
    git(repo, "mv", "source.txt", ".env.probe")
    assert checker.main([], root=repo) == 1
    assert "environment file" in capsys.readouterr().out
    assert checker.main(["nested/.env.local"], root=repo) == 1
    assert "environment file" in capsys.readouterr().out


def test_renamed_content_is_scanned_even_if_unchanged(repo, capsys):
    stage(repo, "old.txt", "Bearer " + "r" * 26 + "\n")
    git(repo, "commit", "-m", "test: baseline")
    git(repo, "mv", "old.txt", "new.txt")
    assert checker.main([], root=repo) == 1
    assert "'new.txt':1 bearer" in capsys.readouterr().out


def test_binary_and_media_content_ignored_but_forbidden_suffix_still_blocks(repo):
    value = b"Bearer " + b"b" * 26
    stage(repo, "binary.data", b"\0" + value)
    stage(repo, "image.png", value)
    assert checker.main([], root=repo) == 0
    stage(repo, "state.db", b"\0" + value)
    assert checker.main([], root=repo) == 1


def test_added_line_beginning_with_plus_is_not_a_diff_header(repo, capsys):
    stage(repo, "notes.txt", "++ Bearer " + "p" * 26 + "\n")
    assert checker.main([], root=repo) == 1
    assert "'notes.txt':1 bearer" in capsys.readouterr().out


def test_git_failure_fails_closed_without_git_stderr(tmp_path, capsys):
    assert checker.main([], root=tmp_path) == 2
    output = capsys.readouterr().out
    assert "no clean result" in output
    assert "fatal:" not in output
