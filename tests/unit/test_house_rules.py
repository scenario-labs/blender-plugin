# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Exercise house-rule failures against temporary source trees and the actual checkout."""

import importlib.util
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location("check_rules", ROOT / "tools/check_rules.py")
rules = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = rules
SPEC.loader.exec_module(rules)
SHA = "0123456789abcdef" * 2 + "01234567"


def workflow(root, content, name=".github/workflows/fixture.yml"):
    path = root / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return path


def test_actions_report_mutable_and_undocumented_pins_by_line(tmp_path):
    path = workflow(
        tmp_path,
        f"  - uses: actions/checkout@{SHA} # v7.0.1\n"
        "  - uses: actions/checkout@v7 # v7.0.1\n"
        f"  - uses: actions/checkout@{SHA}\n",
    )
    found = rules.run(["actions-pinned"], [path], tmp_path)
    assert [item.line for item in found] == [2, 3]
    assert all(item.path == ".github/workflows/fixture.yml" for item in found)
    assert all(item.rule == "actions-pinned" for item in found)


@pytest.mark.parametrize("quote", ["", "'", '"'])
@pytest.mark.parametrize("suffix", [".yml", ".yaml"])
def test_supported_quoted_references_and_keys(tmp_path, quote, suffix):
    path = workflow(
        tmp_path,
        f"  - {quote}uses{quote}: {quote}owner/repo/nested/action@{SHA}{quote}  # v1.2.3\n"
        f"    uses: {quote}owner/repo/.github/workflows/ci.yml@{SHA}{quote} # 1.2.3\n",
        name=".github/workflows/quoted" + suffix,
    )
    assert rules.run(rules.RULES, [path], tmp_path) == []


@pytest.mark.parametrize("block", ["run: |", "run : |"])
def test_local_reusable_actions_docker_comments_and_script_literals_are_not_remote(tmp_path, block):
    path = workflow(
        tmp_path,
        "# uses: actions/checkout@v7\n"
        "  - uses: './.github/actions/local'\n"
        '    uses: "./.github/workflows/local.yml"\n'
        "  - uses: docker://alpine:3\n"
        f"  - {block}\n"
        "      uses: literal script content\n"
        "      # A script comment does not end its block\n"
        "      uses: another script literal\n"
        f"  - uses: owner/repo@{SHA} # v1.2.3\n",
    )
    assert rules.run(rules.RULES, [path], tmp_path) == []


@pytest.mark.parametrize(
    "declaration",
    [
        "uses: owner/repo@main # v1.2.3",
        "uses: owner/repo@abcdef # v1.2.3",
        f"uses: owner/repo@{SHA.upper()} # v1.2.3",
        f"uses: owner/repo@{SHA} # v1",
        f"uses: 'owner/repo@{SHA} # v1.2.3'",
        f'uses: "owner/repo@{SHA}" # documentation only',
        "uses: |\n  owner/repo@main",
        "uses: >-\n  owner/repo@main",
        "uses:\n  owner/repo@main",
        'uses: "owner/repo@main\n  "',
        "uses: *remote",
        "uses: &remote owner/repo@main",
        "{uses: owner/repo@main}",
        "{name: example, uses: owner/repo@main}",
        'steps: [{"uses": owner/repo@main}]',
        '"steps": [{"uses": owner/repo@main}]',
        'steps : [{"uses": owner/repo@main}]',
    ],
)
def test_mutable_or_unsupported_declarations_fail_instead_of_being_skipped(tmp_path, declaration):
    path = workflow(tmp_path, declaration + "\n")
    found = rules.run(rules.RULES, [path], tmp_path)
    assert found
    assert found[0].line == 1


def test_composite_actions_are_checked_but_unrelated_yaml_is_not(tmp_path):
    composite = workflow(tmp_path, "    - uses: owner/repo@v1\n", ".github/actions/a/action.yaml")
    unrelated = workflow(tmp_path, "uses: example\n", "tests/fixtures/data.yaml")
    found = rules.run(rules.RULES, [unrelated, composite], tmp_path)
    assert [item.path for item in found] == [".github/actions/a/action.yaml"]


def test_block_marker_in_a_comment_does_not_hide_nested_actions(tmp_path):
    path = workflow(
        tmp_path,
        "on: pull_request\n"
        "jobs:\n"
        "  check:\n"
        "    runs-on: ubuntu-latest\n"
        "    steps: # A shell example could contain run: |\n"
        "      - uses: owner/repo@main\n",
    )
    found = rules.run(rules.RULES, [path], tmp_path)
    assert [item.line for item in found] == [6]


@pytest.mark.parametrize("dash_spaces", [1, 2, 4])
def test_block_scalar_with_spaced_list_dash_does_not_hide_sibling_action(tmp_path, dash_spaces):
    key_column = 7 + dash_spaces
    path = workflow(
        tmp_path,
        "on: pull_request\n"
        "jobs:\n"
        "  check:\n"
        "    runs-on: ubuntu-latest\n"
        "    steps:\n"
        + "      -"
        + " " * dash_spaces
        + "name: |\n"
        + " " * (key_column + 2)
        + "Fixture step\n"
        + " " * key_column
        + "uses: actions/checkout@main\n",
    )
    found = rules.run(rules.RULES, [path], tmp_path)
    assert [item.line for item in found] == [8]


def test_missing_or_symlink_workflow_fails(tmp_path):
    path = workflow(tmp_path, "name: Original\n")
    path.unlink()
    assert rules.run(rules.RULES, [path], tmp_path)
    path.symlink_to(tmp_path / "missing")
    assert rules.run(rules.RULES, [path], tmp_path)


def test_git_inventory_retains_spaces_and_newlines(tmp_path):
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    path = workflow(tmp_path, "name: Fixture\n", ".github/workflows/spaces and\nnewline.yml")
    subprocess.run(["git", "-C", str(tmp_path), "add", "."], check=True)
    assert rules.tracked_files(tmp_path) == [path]


def test_default_scan_includes_proposed_actions_but_not_ignored_files(
    tmp_path, monkeypatch, capsys
):
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    tracked = workflow(tmp_path, f"uses: owner/repo@{SHA} # v1.2.3\n")
    subprocess.run(["git", "-C", str(tmp_path), "add", "."], check=True)
    proposed = workflow(tmp_path, "uses: owner/repo@main\n", ".github/actions/new/action.yml")
    ignored = workflow(tmp_path, "uses: ignored/repo@main\n", ".github/workflows/ignored.yml")
    (tmp_path / ".gitignore").write_text("ignored.yml\n", encoding="utf-8")
    files = rules.tracked_files(tmp_path)
    assert tracked in files and proposed in files and ignored not in files
    monkeypatch.setattr(rules, "ROOT", tmp_path)
    assert rules.main([]) == 1
    assert ".github/actions/new/action.yml:1: actions-pinned:" in capsys.readouterr().out


def test_archive_inventory_fallback_omits_generated_directories(tmp_path):
    path = workflow(tmp_path, "name: Fixture\n")
    workflow(tmp_path, "uses: ignore\n", ".venv/cached.yml")
    workflow(tmp_path, "uses: ignore\n", "dist/cached.yml")
    assert rules.tracked_files(tmp_path) == [path]


def test_cli_filter_listing_and_failure_exit(tmp_path, monkeypatch, capsys):
    path = workflow(tmp_path, "uses: owner/repo@v1\n")
    monkeypatch.setattr(rules, "ROOT", tmp_path)
    assert rules.main(["--list"]) == 0
    assert capsys.readouterr().out == "actions-pinned\n"
    assert rules.main(["--rule", "actions-pinned", str(path)]) == 1
    assert ".github/workflows/fixture.yml:1: actions-pinned:" in capsys.readouterr().out
    path.write_text(f"uses: owner/repo@{SHA} # v1.2.3\n", encoding="utf-8")
    assert rules.main([str(path)]) == 0
    with pytest.raises(SystemExit) as error:
        rules.main(["--rule", "unimplemented"])
    assert error.value.code == 2


def test_repository_actions_are_pinned():
    found = rules.run(rules.RULES, rules.tracked_files(ROOT), ROOT)
    assert not found, "\n".join(map(str, found))
    result = subprocess.run(
        [sys.executable, str(ROOT / "tools/check_rules.py")],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_cli_process_fails_for_explicit_untracked_workflow(tmp_path):
    script = tmp_path / "tools/check_rules.py"
    script.parent.mkdir()
    script.write_bytes((ROOT / "tools/check_rules.py").read_bytes())
    path = workflow(tmp_path, "uses: owner/repo@v1\n")
    result = subprocess.run(
        [sys.executable, str(script), str(path)], cwd=tmp_path, capture_output=True, text=True
    )
    assert result.returncode == 1
    assert ".github/workflows/fixture.yml:1: actions-pinned:" in result.stdout
