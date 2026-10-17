# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Exercise house-rule failures against temporary source trees and the actual checkout."""

import importlib.util
import json
import re
import subprocess
import sys
import tomllib
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location("check_rules", ROOT / "tools/check_rules.py")
rules = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = rules
SPEC.loader.exec_module(rules)
SHA = "0123456789abcdef" * 2 + "01234567"
ACTIONS = ["actions-pinned"]
# Built from the checker's own parts so this file's licence scan sees no second header.
HEADER = f"# {rules._COPYRIGHT_TAG} 2026 Scenario Inc.\n# {rules._LICENCE_TAG}\n"


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
    assert rules.run(ACTIONS, [path], tmp_path) == []


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
    assert rules.run(ACTIONS, [path], tmp_path) == []


def test_only_actions_published_as_a_major_tag_take_a_major_comment(tmp_path):
    path = workflow(
        tmp_path,
        f"  - uses: google/clusterfuzzlite/actions/build_fuzzers@{SHA} # v1\n"
        f"  - uses: google/clusterfuzzlite/actions/run_fuzzers@{SHA} # 1\n"
        f"  - uses: google/clusterfuzzlite-fork/actions/run@{SHA} # v1\n",
    )
    assert [item.line for item in rules.run(ACTIONS, [path], tmp_path)] == [2, 3]


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
    found = rules.run(ACTIONS, [path], tmp_path)
    assert found
    assert found[0].line == 1


def test_composite_actions_are_checked_but_unrelated_yaml_is_not(tmp_path):
    composite = workflow(tmp_path, "    - uses: owner/repo@v1\n", ".github/actions/a/action.yaml")
    unrelated = workflow(tmp_path, "uses: example\n", "tests/fixtures/data.yaml")
    found = rules.run(ACTIONS, [unrelated, composite], tmp_path)
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
    found = rules.run(ACTIONS, [path], tmp_path)
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
    found = rules.run(ACTIONS, [path], tmp_path)
    assert [item.line for item in found] == [8]


def test_missing_or_symlink_workflow_fails(tmp_path):
    path = workflow(tmp_path, "name: Original\n")
    path.unlink()
    assert rules.run(ACTIONS, [path], tmp_path)
    path.symlink_to(tmp_path / "missing")
    assert rules.run(ACTIONS, [path], tmp_path)


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
    assert capsys.readouterr().out.split() == sorted(rules.RULES)
    assert rules.main(["--rule", "actions-pinned", str(path)]) == 1
    assert ".github/workflows/fixture.yml:1: actions-pinned:" in capsys.readouterr().out
    path.write_text(HEADER + f"uses: owner/repo@{SHA} # v1.2.3\n", encoding="utf-8")
    assert rules.main([str(path)]) == 0
    with pytest.raises(SystemExit) as error:
        rules.main(["--rule", "unimplemented"])
    assert error.value.code == 2


def test_repository_passes_every_rule():
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


def write(root, name, content):
    path = root / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return path


def found(rule, root, *paths):
    return [(item.path, item.line) for item in rules.run([rule], list(paths), root)]


def test_spdx_requires_both_lines_near_the_top_of_source_files(tmp_path):
    missing = write(tmp_path, "tools/missing.py", "VALUE = 1\n")
    shebang = write(tmp_path, "tools/run.sh", "#!/bin/sh\n" + HEADER + "echo ok\n")
    html = write(tmp_path, "docs/page.html", HEADER.replace("# ", "<!-- ").replace("\n", " -->\n"))
    late = write(tmp_path, "Makefile", "\n" * 10 + HEADER)
    licence_only = write(tmp_path, "a.toml", HEADER.splitlines()[1] + "\n")
    prose = write(tmp_path, "docs/notes.md", "No header needed: REUSE.toml covers Markdown.\n")
    lock = write(tmp_path, "pnpm-lock.yaml", "lockfileVersion: '9.0'\n")
    assert found("spdx", tmp_path, missing, shebang, html, late, licence_only, prose, lock) == [
        ("Makefile", 1),
        ("a.toml", 1),
        ("tools/missing.py", 1),
    ]


def test_spdx_skips_vendored_skills_recorded_in_the_skills_lock(tmp_path):
    write(
        tmp_path,
        "skills-lock.json",
        json.dumps({"skills": {"shared": {"skillPath": ".agents/skills/shared/SKILL.md"}}}),
    )
    vendored = write(tmp_path, ".agents/skills/shared/agents/openai.yaml", "interface: {}\n")
    local = write(tmp_path, ".agents/skills/local/agents/openai.yaml", "interface: {}\n")
    assert found("spdx", tmp_path, vendored, local) == [
        (".agents/skills/local/agents/openai.yaml", 1)
    ]


def test_em_dash_reports_each_line_and_skips_licence_texts_and_binaries(tmp_path):
    dash = chr(0x2014)
    text = write(tmp_path, "docs/a.md", f"fine\nbad {dash} line\nalso{dash}\n")
    licence = write(tmp_path, "LICENSES/X.txt", dash)
    binary = tmp_path / "docs/b.bin"
    binary.write_bytes(b"\0" + dash.encode())
    assert found("em-dash", tmp_path, text, licence, binary) == [("docs/a.md", 2), ("docs/a.md", 3)]


def test_bpy_boundary_covers_core_and_non_blender_mcp_modules(tmp_path):
    nested = write(tmp_path, "scenario/core/x.py", "def f():\n    import bpy\n")
    dotted = write(tmp_path, "scenario/core/jobs/y.py", "from mathutils.geometry import x\n")
    dynamic = write(
        tmp_path, "scenario/mcp/server.py", "import importlib\nimportlib.import_module('gpu')\n"
    )
    allowed_mcp = write(tmp_path, "scenario/mcp/tools_blender.py", "import bpy\n")
    glue = write(tmp_path, "scenario/blender/z.py", "import bpy\n")
    broken = write(tmp_path, "scenario/core/broken.py", "def (\n")
    assert found("bpy-boundary", tmp_path, nested, dotted, dynamic, allowed_mcp, glue, broken) == [
        ("scenario/core/broken.py", 1),
        ("scenario/core/jobs/y.py", 1),
        ("scenario/core/x.py", 2),
        ("scenario/mcp/server.py", 2),
    ]


def sdk_tree(root):
    lock = {"wheels": [{"package": "scenario-sdk"}, {"package": "pydantic-core"}]}
    write(root, "scenario/sdk-wheel-lock.json", json.dumps(lock))
    write(root, "scenario/blender_manifest.toml", 'version = "1.0.0"\nwheels = ["x.whl"]\n')


def test_approved_dependencies_accept_the_pinned_bundle_and_reject_others(tmp_path):
    sdk_tree(tmp_path)
    approved = write(
        tmp_path,
        "scenario/core/api/sdk_adapter.py",
        "import json\nimport bpy\nimport numpy\nimport scenario_sdk\n"
        "import pydantic_core\nfrom . import x\nfrom scenario.core import y\n",
    )
    unrelated = write(tmp_path, "scenario/core/jobs/x.py", "import json\nimport requests\n")
    tool = write(tmp_path, "tools/dev.py", "import requests\n")
    assert found("approved-dependencies", tmp_path, approved, unrelated, tool) == [
        ("scenario/core/jobs/x.py", 2)
    ]


def test_sdk_and_its_client_are_imported_only_by_the_shared_adapter(tmp_path):
    adapter = write(tmp_path, "scenario/core/api/sdk_adapter.py", "import httpx\n")
    extensions = write(tmp_path, "scenario/core/api/sdk_extensions.py", "import httpx\n")
    direct = write(
        tmp_path, "scenario/core/jobs/x.py", "def f():\n    from scenario_sdk import X\n"
    )
    storage = write(tmp_path, "scenario/core/jobs/y.py", "import http.client\n")
    assert found("sdk-adapter", tmp_path, adapter, extensions, direct, storage) == [
        ("scenario/core/jobs/x.py", 2)
    ]


def test_public_content_reports_pattern_numbers_without_matched_text(tmp_path):
    write(tmp_path, rules.DENYLIST, "# comment\n\nfixture-word-[0-9]+\n(\n")
    leaked = write(tmp_path, "docs/a.md", "clean\nsee fixture-word-42 here\n")
    denylist = tmp_path / rules.DENYLIST
    violations = rules.run(["public-content"], [leaked, denylist], tmp_path)
    assert [(item.path, item.line, item.message) for item in violations] == [
        ("docs/a.md", 2, "matches public-content denylist pattern 3"),
        (rules.DENYLIST, 4, "invalid pattern"),
    ]
    assert "fixture-word-42" not in "\n".join(map(str, violations))


def test_version_literal_is_limited_to_release_files(tmp_path):
    write(tmp_path, rules.MANIFEST, 'version = "1.2.3"\n')
    readme = write(
        tmp_path,
        "README.md",
        "Install 1.2.3.\nTag v1.2.3\nOther 11.2.3, 1.2.30 and 1.2.3.4\n",
    )
    changelog = write(tmp_path, "CHANGELOG.md", "## 1.2.3\n")
    record = write(tmp_path, "docs/maintenance/release-plan.md", "1.2.3 acceptance\n")
    sample = write(tmp_path, "tests/site/index.test.ts", 'publish(["1.2.2", "1.2.3"]);\n')
    manifest = tmp_path / rules.MANIFEST
    assert found("version-literal", tmp_path, readme, changelog, record, sample, manifest) == [
        ("README.md", 1),
        ("README.md", 2),
    ]


def test_snapshot_directories_are_rejected(tmp_path):
    paths = [
        tmp_path / name
        for name in (
            "versions/a.md",
            "tests/fixtures/smoke/archive/b.json",
            "archive/c.py",
            "docs/archive.md",
            "docs/archived/d.md",
            "tools/versions.py",
        )
    ]
    assert found("no-snapshot-dirs", tmp_path, *paths) == [
        ("archive/c.py", 1),
        ("tests/fixtures/smoke/archive/b.json", 1),
        ("versions/a.md", 1),
    ]


def test_cli_reports_explicit_file_outside_the_checkout(tmp_path):
    path = tmp_path / "x.md"
    path.write_text(f"a {chr(0x2014)} b\n", encoding="utf-8")
    result = subprocess.run(
        [sys.executable, str(ROOT / "tools/check_rules.py"), str(path)],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 1
    assert result.stdout.startswith(f"{path}:1: em-dash:")


def test_reuse_metadata_and_denylist_are_well_formed():
    assert (ROOT / "LICENSES/GPL-3.0-or-later.txt").read_bytes() == (ROOT / "LICENSE").read_bytes()
    reuse = tomllib.loads((ROOT / "REUSE.toml").read_text(encoding="utf-8"))
    assert reuse["version"] == 1
    texts = {path.stem for path in (ROOT / "LICENSES").iterdir()}
    used = {item["SPDX-License-Identifier"] for item in reuse["annotations"]}
    assert used == texts
    lines = (ROOT / rules.DENYLIST).read_text(encoding="utf-8").splitlines()
    assert lines[:2] == HEADER.splitlines()
    for line in lines:
        if line.strip() and not line.startswith("#"):
            re.compile(line)
