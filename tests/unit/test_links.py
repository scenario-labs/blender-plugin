# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Repository input selection and scoped scheduled link reporting, offline."""

import os
import subprocess
import sys
from pathlib import Path

import pytest

from tools import link_inventory, report_ci_failure, report_link_failure


def repository(path):
    subprocess.run(["git", "init", "-q", str(path)], check=True)
    (path / ".gitignore").write_text("workdir/\n")
    subprocess.run(["git", "add", ".gitignore"], cwd=path, check=True)
    return path


def symlink(link, target):
    try:
        link.symlink_to(target)
    except OSError:
        pytest.skip("Symlinks unavailable on this host")


def test_inventory_deduplicates_adapters_and_excludes_private_and_history(tmp_path):
    root = repository(tmp_path)
    (root / "README.md").write_text("[public](https://example.org)")
    (root / "draft with spaces.md").write_text("proposed doc")
    (root / "workdir").mkdir()
    (root / "workdir/private.md").write_text("private content")
    (root / "docs/engineering").mkdir(parents=True)
    (root / "docs/engineering/history.md").write_text("historical")
    (root / ".claude").mkdir()
    symlink(root / ".claude/CLAUDE.md", "../README.md")
    subprocess.run(["git", "add", "README.md", ".claude", "docs"], cwd=root, check=True)
    assert link_inventory.markdown_inputs(root) == ["./README.md", "./draft with spaces.md"]


@pytest.mark.parametrize("destination", ["outside", "ignored"])
def test_inventory_rejects_adapter_to_unowned_content(tmp_path, destination):
    root = repository(tmp_path / "repo")
    target = tmp_path / "outside.md"
    if destination == "ignored":
        (root / "workdir").mkdir()
        target = root / "workdir/private.md"
    target.write_text("must not scan")
    symlink(root / "adapter.md", target)
    with pytest.raises(ValueError, match="outside the proposed file inventory"):
        link_inventory.markdown_inputs(root)


def test_inventory_rejects_missing_tracked_input(tmp_path):
    root = repository(tmp_path)
    source = root / "README.md"
    source.write_text("content")
    subprocess.run(["git", "add", "README.md"], cwd=root, check=True)
    source.unlink()
    with pytest.raises(FileNotFoundError):
        link_inventory.markdown_inputs(root)


def test_inventory_rejects_markdown_adapter_to_non_markdown_file(tmp_path):
    root = repository(tmp_path)
    target = root / "settings.toml"
    target.write_text('url = "https://example.org/service"\n')
    symlink(root / "adapter.md", target.name)
    subprocess.run(["git", "add", "settings.toml", "adapter.md"], cwd=root, check=True)
    with pytest.raises(ValueError, match="target is not Markdown"):
        link_inventory.markdown_inputs(root)


def test_inventory_rejects_empty_checkout(tmp_path):
    with pytest.raises(ValueError, match="No Markdown inputs"):
        link_inventory.markdown_inputs(repository(tmp_path))


@pytest.mark.skipif(os.name == "nt", reason="Windows rejects control characters in filenames")
@pytest.mark.parametrize("name", ["two\nlines.md", "two\rlines.md"])
def test_inventory_rejects_ambiguous_line_inputs(tmp_path, name):
    root = repository(tmp_path)
    (root / name).write_text("content")
    with pytest.raises(ValueError, match="one lychee input-list line"):
        link_inventory.markdown_inputs(root)


def test_inventory_cli_is_repeatable_and_ignores_its_private_output(tmp_path):
    root = repository(tmp_path)
    (root / "README.md").write_text("content")
    output = root / "workdir/link-check/inputs.txt"
    command = [sys.executable, str(Path(link_inventory.__file__)), "--output", str(output)]
    for _ in range(2):
        result = subprocess.run(command, cwd=root, capture_output=True, text=True)
        assert result.returncode == 0, result.stderr
        assert output.read_text() == "./README.md\n"
        (output.parent / "report.md").write_text("generated report is private")


def arguments(report):
    return [
        "--repository",
        "example/extension",
        "--run-url",
        "https://github.com/example/extension/actions/runs/42",
        "--report",
        str(report),
    ]


def test_link_reporter_deduplicates_in_documentation_scope(monkeypatch, tmp_path):
    report = tmp_path / "report.md"
    report.write_text("[301] https://example.org/moved\n")
    issues = []
    calls = []

    def github(endpoint, *args, payload=None):
        calls.append((endpoint, args, payload))
        if payload is None:
            assert "labels=area:docs" in args
            return [[], issues]
        if not endpoint.endswith("/comments"):
            issues.append({"number": 7, "title": payload["title"]})
        return {}

    monkeypatch.setattr(report_ci_failure, "github", github)
    assert report_link_failure.main(arguments(report)) == 0
    assert report_link_failure.main(arguments(report)) == 0
    writes = [(endpoint, payload) for endpoint, _, payload in calls if payload]
    assert [endpoint for endpoint, _ in writes] == [
        "repos/example/extension/issues",
        "repos/example/extension/issues/7/comments",
    ]
    assert writes[0][1]["labels"] == ["documentation", "area:docs"]
    assert report.read_text() in writes[1][1]["body"]
    assert "actions/runs/42" in writes[1][1]["body"]


@pytest.mark.parametrize("mode", ["missing", "large"])
def test_report_retains_diagnostic_when_missing_or_truncated(monkeypatch, tmp_path, mode):
    report = tmp_path / "report.md"
    if mode == "large":
        report.write_text("x" * 60000)
    captured = []
    monkeypatch.setattr(report_link_failure, "report_failure", lambda *a, **k: captured.append(a))
    assert report_link_failure.main(arguments(report)) == 0
    body = captured[0][2]
    assert "actions/runs/42" in body
    assert len(body) < 65536
    assert ("No report was produced" if mode == "missing" else "Report truncated") in body


def test_report_error_is_not_retried_or_echoed(monkeypatch, tmp_path, capsys):
    calls = []

    def fail(*args, **kwargs):
        calls.append(args)
        raise subprocess.CalledProcessError(1, "gh", stderr="private response")

    monkeypatch.setattr(report_link_failure, "report_failure", fail)
    assert report_link_failure.main(arguments(tmp_path / "missing")) == 1
    assert len(calls) == 1
    assert "private response" not in capsys.readouterr().err


def test_report_rejects_unrelated_run_before_writing(monkeypatch, tmp_path):
    calls = []
    monkeypatch.setattr(report_link_failure, "report_failure", lambda *a, **k: calls.append(a))
    args = arguments(tmp_path / "missing")
    args[args.index("--run-url") + 1] = "https://github.com/other/repo/actions/runs/42"
    with pytest.raises(SystemExit, match="2"):
        report_link_failure.main(args)
    assert not calls


def test_report_scope_must_be_among_creation_labels(monkeypatch):
    calls = []
    monkeypatch.setattr(report_ci_failure, "github", lambda *a, **k: calls.append(a))
    with pytest.raises(ValueError, match="scope label"):
        report_ci_failure.report_failure("example/repo", "title", "body", ["area:docs"])
    assert not calls
