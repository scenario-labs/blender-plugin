# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Exercise knowledge checks with real temporary Git repositories, offline."""

import datetime as dt
import json
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

from tools import check_knowledge as knowledge

TODAY = dt.date(2026, 9, 23)
DOCUMENTS = {
    "docs/index.md": "docs-index",
    "docs/guide.md": "docs-guide",
    "README.md": "readme",
    "AGENTS.md": "agents",
    "CONTRIBUTING.md": "contributing",
}
GUIDE = "docs/knowledge/docs-guide.md"


def git(root, *args):
    return subprocess.check_output(["git", "-C", str(root), *args], text=True).strip()


def write(root, path, text):
    dest = root / path
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(text)
    return dest


def save(root, profile):
    write(root, "docs/knowledge.json", json.dumps(profile))


def save_record(root, name, metadata, body="\nEvidence.\n"):
    return write(root, name, "---\n" + json.dumps(metadata, indent=2) + "\n---\n" + body)


def edit(repo, name=GUIDE, body="\nEvidence.\n", **fields):
    root, records = repo
    records[name]["evidence"].update(fields)
    save_record(root, name, records[name], body)


def commit(root, message):
    git(root, "add", "-A")
    git(root, "commit", "-qm", message)
    return git(root, "rev-parse", "HEAD")


@pytest.fixture
def repo(tmp_path):
    git(tmp_path, "init", "-b", "main")
    git(tmp_path, "config", "user.name", "Knowledge test")
    git(tmp_path, "config", "user.email", "test@example.invalid")
    write(tmp_path, ".gitignore", ".private/\n")
    write(tmp_path, "source.py", "value = 1\n")
    write(
        tmp_path,
        "docs/index.md",
        "# Index\n\n[Guide](guide.md#api-value)\n[README](../README.md)\n[Rules](../AGENTS.md)\n[Contribute](../CONTRIBUTING.md)\n",
    )
    write(tmp_path, "docs/guide.md", "# Guide\n\n## API `value`\n[Source](../source.py)\n")
    for path in ("README.md", "AGENTS.md", "CONTRIBUTING.md"):
        write(tmp_path, path, "# Entry\n")
    revision = commit(tmp_path, "test: initial sources")
    records = {}
    for path, record_id in DOCUMENTS.items():
        name = f"docs/knowledge/{record_id}.md"
        records[name] = {
            "type": "Evidence",
            "id": record_id,
            "evidence": {
                "path": path,
                "coverage": "source-reviewed",
                "reviewed_at": TODAY.isoformat(),
                "reviewed_revision": revision,
                "limits": "Synthetic source inspection only.",
                "sources": ["source.py"],
            },
        }
        save_record(tmp_path, name, records[name])
    save(
        tmp_path,
        {
            "version": 3,
            "index": "docs/index.md",
            "records": {"root": "docs/knowledge", "format": "okf-json"},
        },
    )
    commit(tmp_path, "docs: record knowledge")
    return tmp_path, records


def audit(repo, **kwargs):
    return knowledge.audit(repo[0], today=TODAY, **kwargs)


def test_valid_and_read_only(repo):
    root, _ = repo
    before = git(root, "status", "--porcelain"), (root / GUIDE).read_bytes()
    report = audit(repo)
    assert report["errors"] == []
    assert report["warnings"] == []
    assert report["drift"] == []
    assert report["documents"] == sorted(DOCUMENTS)
    assert (git(root, "status", "--porcelain"), (root / GUIDE).read_bytes()) == before


@pytest.mark.parametrize("local_offset,utc_hour", [(-12, 0), (14, 23)])
def test_default_clock_uses_utc_across_local_midnight(repo, monkeypatch, local_offset, utc_hour):
    root, _ = repo
    instant = dt.datetime.combine(TODAY, dt.time(utc_hour, 30), tzinfo=dt.UTC)
    local_zone = dt.timezone(dt.timedelta(hours=local_offset))
    assert instant.astimezone(local_zone).date() != TODAY

    class Clock(dt.datetime):
        @classmethod
        def now(cls, tz=None):
            return instant.astimezone(tz or local_zone)

    monkeypatch.setattr(knowledge, "dt", SimpleNamespace(date=dt.date, datetime=Clock, UTC=dt.UTC))
    assert knowledge.audit(root)["errors"] == []
    edit(repo, reviewed_at=(TODAY + dt.timedelta(days=1)).isoformat())
    assert any("reviewed_at is in the future" in error for error in knowledge.audit(root)["errors"])


def test_old_review_without_source_changes_is_not_a_warning(repo):
    edit(repo, reviewed_at="2025-01-01")
    assert audit(repo)["warnings"] == []


def test_drift_is_one_warning_per_document(repo):
    root, _ = repo
    write(root, "source.py", "value = 2\n")
    report = audit(repo)
    assert report["errors"] == []
    assert len(report["warnings"]) == len(DOCUMENTS)
    assert (
        f"docs/guide.md [{GUIDE}]: 1 of 1 sources changed since review: source.py"
        in (report["warnings"])
    )
    assert {item["path"] for item in report["drift"]} == set(DOCUMENTS)
    assert all(item["sources"] == ["source.py"] for item in report["drift"])


def test_drift_includes_committed_staged_and_removed_sources(repo):
    root, _ = repo
    for name in ("a.py", "b.py", "c.py"):
        write(root, name, "value = 1\n")
    revision = commit(root, "test: more sources")
    edit(repo, reviewed_revision=revision, sources=["a.py", "b.py", "c.py", "source.py"])
    commit(root, "docs: review more sources")
    write(root, "a.py", "value = 2\n")
    commit(root, "test: committed change")
    write(root, "b.py", "value = 2\n")
    git(root, "add", "b.py")
    (root / "c.py").unlink()
    report = audit(repo)
    assert report["errors"] == []
    guide = next(item for item in report["drift"] if item["path"] == "docs/guide.md")
    assert guide["sources"] == ["a.py", "b.py", "c.py (removed)"]


def test_long_drift_lists_are_shortened_in_text_but_complete_in_json(repo):
    root, _ = repo
    names = [f"s{number}.py" for number in range(7)]
    for name in names:
        write(root, name, "value = 1\n")
    revision = commit(root, "test: many sources")
    edit(repo, reviewed_revision=revision, sources=sorted(names))
    for name in names:
        write(root, name, "value = 2\n")
    report = audit(repo)
    warning = next(w for w in report["warnings"] if w.startswith("docs/guide.md"))
    assert warning.endswith("s0.py, s1.py, s2.py, s3.py, s4.py and 2 more")
    guide = next(item for item in report["drift"] if item["path"] == "docs/guide.md")
    assert guide["sources"] == sorted(names)


def test_refresh_to_a_newer_main_commit_clears_drift(repo):
    root, _ = repo
    write(root, "source.py", "value = 2\n")
    revision = commit(root, "test: change source")
    assert len(audit(repo)["warnings"]) == len(DOCUMENTS)
    edit(repo, reviewed_revision=revision)
    warnings = audit(repo)["warnings"]
    assert len(warnings) == len(DOCUMENTS) - 1
    assert not any(w.startswith("docs/guide.md") for w in warnings)


def test_feature_branches_merge_without_touching_records(repo):
    root, _ = repo
    write(root, "other.py", "other = 1\n")
    revision = commit(root, "test: add other source")
    edit(repo, reviewed_revision=revision, sources=["other.py", "source.py"])
    commit(root, "docs: review other source")
    git(root, "checkout", "-qb", "left")
    write(root, "source.py", "value = 2\n")
    write(root, "docs/guide.md", "# Guide\n\n## API `value`\n[Source](../source.py)\nLeft.\n")
    commit(root, "feat: left")
    git(root, "checkout", "-q", "main")
    write(root, "other.py", "other = 2\n")
    commit(root, "feat: right")
    git(root, "merge", "-q", "left", "--no-edit")
    report = audit(repo)
    assert report["errors"] == []
    guide = next(item for item in report["drift"] if item["path"] == "docs/guide.md")
    assert guide["sources"] == ["other.py", "source.py"]


@pytest.mark.parametrize(
    "sources,diagnostic",
    [
        ([], "nonempty list"),
        ({"source.py": "0" * 64}, "nonempty list"),
        ("source.py", "nonempty list"),
        ([3], "nonempty list"),
        (["source.py", "README.md"], "sorted and unique"),
        (["source.py", "source.py"], "sorted and unique"),
        (["never-existed.py"], "missing or ignored source"),
        (["docs"], "missing or ignored source"),
    ],
)
def test_bad_sources_are_errors(repo, sources, diagnostic):
    edit(repo, sources=sources)
    errors = audit(repo)["errors"]
    assert len(errors) == 1
    assert diagnostic in errors[0]


def test_limits_are_capped(repo):
    edit(repo, limits=" ".join(["word"] * knowledge.MAX_LIMIT_WORDS))
    assert audit(repo)["errors"] == []
    edit(repo, limits=" ".join(["word"] * (knowledge.MAX_LIMIT_WORDS + 1)))
    errors = audit(repo)["errors"]
    assert len(errors) == 1
    assert f"at most {knowledge.MAX_LIMIT_WORDS} words, not 61" in errors[0]


@pytest.mark.parametrize(
    "field,value,diagnostic",
    [
        ("coverage", {}, "unhashable"),
        ("coverage", "verified", "invalid coverage"),
        ("limits", "", "limits must be explicit"),
        ("reviewed_at", "tomorrow", "Invalid isoformat"),
        ("reviewed_at", "2099-01-01", "in the future"),
        ("reviewed_revision", "main", "full Git commit"),
        ("reviewed_revision", "0" * 40, "returned non-zero"),
        ("path", "../outside.md", "escapes repository"),
        ("path", "source.py", "nonignored Markdown"),
        ("base_revision", "0" * 40, "unsupported evidence fields: base_revision"),
        ("scope", "overview", "unsupported evidence fields: scope"),
    ],
)
def test_bad_evidence_preserves_other_navigation_checks(repo, field, value, diagnostic):
    edit(repo, body="\n[Broken](missing.md)\n", **{field: value})
    errors = audit(repo)["errors"]
    assert any(diagnostic in error for error in errors), errors
    assert any("missing link target" in error for error in errors)


@pytest.mark.parametrize("squashed", [False, True])
def test_comparison_rejects_cached_pr_base_before_and_after_squash(repo, squashed):
    root, _ = repo
    git(root, "checkout", "-qb", "parent")
    write(root, "source.py", "value = 2\n")
    parent = commit(root, "test: parent change")
    git(root, "checkout", "-q", "main")
    if squashed:
        git(root, "merge", "--squash", "parent")
        commit(root, "test: squash parent")
        git(root, "branch", "-D", "parent")
    git(root, "update-ref", "refs/remotes/origin/main", git(root, "rev-parse", "main"))
    edit(repo, reviewed_revision=parent)

    # Existence alone passes even after the branch disappears; the PR commit is
    # not part of the durable main history fetched by fresh checkouts.
    assert git(root, "cat-file", "-t", parent) == "commit"
    assert audit(repo)["errors"] == []
    result = subprocess.run(
        [
            sys.executable,
            str(Path(knowledge.__file__).resolve()),
            "--root",
            str(root),
            "--base",
            "origin/main",
            "--json",
        ],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 1
    errors = json.loads(result.stdout)["errors"]
    assert len(errors) == 1
    assert "reviewed_revision must be reachable from comparison base 'origin/main'" in errors[0]


def test_missing_comparison_ref_fails_without_changing_standalone_behavior(repo):
    assert audit(repo)["errors"] == []
    errors = audit(repo, base="origin/missing")["errors"]
    assert len(errors) == 1
    assert "origin/missing" in errors[0]


def test_stale_fork_ref_rejects_but_selected_current_upstream_ref_passes(repo):
    root, _ = repo
    git(root, "update-ref", "refs/remotes/origin/main", git(root, "rev-parse", "main"))
    write(root, "upstream.py", "new = True\n")
    current = commit(root, "test: advance canonical main")
    git(root, "update-ref", "refs/remotes/upstream/main", current)
    git(root, "checkout", "-qb", "feature")
    edit(repo, reviewed_revision=current)
    git(root, "checkout", "--detach")
    before = git(root, "show-ref"), git(root, "status", "--porcelain")

    # Only local objects/refs are needed: no configured remote or credentials.
    assert git(root, "remote") == ""
    stale = audit(repo, base="origin/main")
    assert len(stale["errors"]) == 1
    assert "refresh/select the canonical repository's main ref" in stale["errors"][0]
    report = audit(repo, base="upstream/main")
    assert report["errors"] == []
    assert report["warnings"] == []
    assert report["changed"] == [GUIDE]
    assert report["impacted"] == ["docs/guide.md"]
    assert (git(root, "show-ref"), git(root, "status", "--porcelain")) == before


def test_merge_base_includes_branch_and_worktree_not_unrelated_base_changes(repo):
    root, _ = repo
    git(root, "checkout", "-qb", "feature")
    write(root, "source.py", "value = 2\n")
    commit(root, "test: branch change")
    git(root, "checkout", "-q", "main")
    write(root, "base-only.py", "base = True\n")
    commit(root, "test: advance base")
    git(root, "checkout", "-q", "feature")
    write(root, "staged.py", "staged = True\n")
    git(root, "add", "staged.py")
    write(root, "README.md", "# Unstaged\n")
    (root / "AGENTS.md").unlink()
    write(root, "new.py", "new = True\n")
    write(root, ".private/ignored.py", "private = True\n")
    report = audit(repo, base="main")
    assert set(report["changed"]) == {"source.py", "staged.py", "README.md", "AGENTS.md", "new.py"}
    assert "docs/guide.md" in report["impacted"]


def test_markdown_fragments_reference_links_and_code_examples(repo):
    root, _ = repo
    guide = "# Guide\n## API `value`\n## API `value`\n[Again](#api-value-1)\n[By ref][source]\n[source]: ../source.py\n```md\n[Not a link](missing.md)\n```\n`[Nor this](missing.md)`\n"
    write(root, "docs/guide.md", guide)
    assert audit(repo)["errors"] == []
    write(root, "docs/guide.md", guide + "[Bad fragment](#no-such-heading)\n")
    assert any("missing Markdown anchor" in e for e in audit(repo)["errors"])


def test_ignored_private_note_is_not_read(repo):
    root, _ = repo
    write(root, ".private/note.md", "not public")
    write(root, "docs/guide.md", "# Guide\n## API value\n[Private](../.private/note.md)\n")
    edit(repo, sources=[".private/note.md"])
    errors = audit(repo)["errors"]
    assert any("missing or ignored source" in e for e in errors)
    assert any("ignored or untracked" in e for e in errors)


def test_escaping_symlink_rejected_for_links_and_sources(repo, tmp_path_factory):
    root, _ = repo
    outside = tmp_path_factory.mktemp("outside") / "secret.md"
    outside.write_text("private text")
    (root / "escape.md").symlink_to(outside)
    write(root, "docs/guide.md", "# Guide\n## API value\n[Escape](../escape.md)\n")
    edit(repo, sources=["escape.md"])
    assert sum("escapes repository" in e for e in audit(repo)["errors"]) == 2


def test_symlink_cannot_make_ignored_file_public_evidence(repo):
    root, _ = repo
    secret = write(root, ".private/note.md", "private text")
    (root / "alias.md").symlink_to(secret)
    git(root, "add", "alias.md")
    write(root, "docs/guide.md", "# Guide\n## API value\n[Alias](../alias.md)\n")
    edit(repo, sources=["alias.md"])
    errors = audit(repo)["errors"]
    assert any("ignored source" in e for e in errors)
    assert any("ignored or untracked" in e for e in errors)


def test_fenced_heading_is_not_a_valid_fragment(repo):
    write(repo[0], "docs/guide.md", "# Guide\n## API value\n```md\n# Hidden\n```\n[Bad](#hidden)\n")
    assert any("missing Markdown anchor" in e for e in audit(repo)["errors"])


def test_undefined_reference_and_encoded_space_links(repo):
    root, _ = repo
    write(root, "source file.txt", "public text")
    write(
        root,
        "docs/guide.md",
        "# Guide\n## API value\n[Space](../source%20file.txt)\n[Angle](<../source file.txt>)\n[Missing][unknown]\n",
    )
    errors = audit(repo)["errors"]
    assert len(errors) == 1
    assert "undefined reference" in errors[0]


@pytest.mark.parametrize("destination", ["/README.md", "%2FREADME.md"])
def test_root_relative_link_has_actionable_error_and_audit_continues(repo, destination):
    write(
        repo[0],
        "docs/guide.md",
        f"# Guide\n## API value\n[Root]({destination})\n[Missing](missing.md)\n",
    )
    errors = audit(repo)["errors"]
    assert len(errors) == 2
    assert any(
        f"unsupported root-relative link: {destination}; use a document-relative link" in error
        for error in errors
    )
    assert any("missing link target: missing.md" in error for error in errors)


def test_indexing_prose_is_not_an_undefined_reference(repo):
    write(
        repo[0],
        "docs/guide.md",
        "# Guide\n## API value\n"
        "Inspect config[env][key], results[0][1], matrix[i][j][k] and lookup()[a][b].\n"
        r"An escaped \[label][ref] is text too."
        "\n[Source][known]\n[known]: ../source.py\n"
        "A real missing reference still fails: ([Broken][missing]).\n",
    )
    assert audit(repo)["errors"] == ["docs/guide.md: undefined reference link: missing"]


def test_record_bodies_are_link_checked_without_their_own_evidence(repo):
    edit(repo, body="\n[Guide](../guide.md#api-value)\n")
    assert audit(repo)["errors"] == []
    edit(repo, body="\n[Broken](../guide.md#missing-heading)\n")
    assert any("missing Markdown anchor" in e for e in audit(repo)["errors"])


def test_duplicate_missing_and_unreachable_documents(repo):
    root, records = repo
    duplicate = dict(records[GUIDE], id="docs-guide-copy")
    save_record(root, "docs/knowledge/docs-guide-copy.md", duplicate)
    orphan = dict(records[GUIDE], id="docs-orphan")
    orphan["evidence"] = dict(orphan["evidence"], path="docs/orphan.md")
    save_record(root, "docs/knowledge/docs-orphan.md", orphan)
    write(root, "docs/orphan.md", "# Orphan\n")
    write(root, "docs/unregistered.md", "# Unregistered\n")
    errors = audit(repo)["errors"]
    assert "duplicate document: docs/guide.md" in errors
    assert "document missing from registry: docs/unregistered.md" in errors
    assert "document unreachable from index: docs/orphan.md" in errors


@pytest.mark.parametrize(
    "record_id,diagnostic",
    [
        ("", "lowercase hyphenated"),
        ("../escape", "lowercase hyphenated"),
        ("Uppercase", "lowercase hyphenated"),
        ("dotted.topic", "lowercase hyphenated"),
        ({}, "lowercase hyphenated"),
        ("docs-other", "match the record file name"),
    ],
)
def test_record_id_is_its_file_name(repo, record_id, diagnostic):
    root, records = repo
    records[GUIDE]["id"] = record_id
    save_record(root, GUIDE, records[GUIDE])
    errors = audit(repo)["errors"]
    assert any(diagnostic in e for e in errors)
    assert "document missing from registry: docs/guide.md" in errors


def test_nested_topic_records_from_older_branches_are_rejected(repo):
    root, records = repo
    save_record(root, "docs/knowledge/docs-guide/overview.md", records[GUIDE])
    errors = audit(repo)["errors"]
    assert errors == [
        "docs/knowledge/docs-guide/overview.md: evidence record must sit directly under docs/knowledge"
    ]


def test_duplicate_json_key_is_rejected(repo):
    root, _ = repo
    path = root / GUIDE
    path.write_text(
        path.read_text().replace('"type": "Evidence",', '"type": "Evidence", "type": "Evidence",')
    )
    assert any("duplicate JSON key: type" in e for e in audit(repo)["errors"])


@pytest.mark.parametrize(
    "profile,diagnostic",
    [
        ({"version": 2}, "version 3"),
        ({"version": "3"}, "version 3"),
        ({"documents": []}, "contains only"),
        ({"records": {"root": "docs/knowledge", "format": "yaml"}}, "okf-json"),
        ({"records": {"root": "docs/knowledge"}}, "root and format"),
        ({"records": {"root": "docs/empty", "format": "okf-json"}}, "no evidence records"),
    ],
)
def test_bad_registry_is_a_structured_error(repo, profile, diagnostic):
    root, _ = repo
    (root / "docs/empty").mkdir()
    config = {
        "version": 3,
        "index": "docs/index.md",
        "records": {"root": "docs/knowledge", "format": "okf-json"},
    }
    save(root, config | profile)
    errors = audit(repo)["errors"]
    assert len(errors) == 1
    assert diagnostic in errors[0]


@pytest.mark.parametrize(
    "directory",
    [
        "docs",
        "docs/../outside",
        "../outside",
        "docs//records",
        "docs/./records",
        "docs\\records",
        "/tmp/records",
    ],
)
def test_bad_discovery_directory_is_rejected(repo, directory):
    root, _ = repo
    save(
        root,
        {
            "version": 3,
            "index": "docs/index.md",
            "records": {"root": directory, "format": "okf-json"},
        },
    )
    assert any("canonical subdirectory" in e for e in audit(repo)["errors"])


@pytest.mark.parametrize(
    "kind",
    [
        "symlink",
        "outside-symlink",
        "directory-symlink",
        "ignored",
        "bad-frontmatter",
        "self-evidence",
    ],
)
def test_records_cannot_escape_or_hide_registration(repo, tmp_path_factory, kind):
    root, records = repo
    path = root / GUIDE
    if kind in ("symlink", "outside-symlink"):
        target = (
            (root / "alias.md")
            if kind == "symlink"
            else tmp_path_factory.mktemp("outside") / "secret.md"
        )
        target.write_bytes(path.read_bytes())
        path.unlink()
        path.symlink_to(target)
    elif kind == "directory-symlink":
        (root / "docs/knowledge").rename(root / "records")
        (root / "docs/knowledge").symlink_to(root / "records", target_is_directory=True)
    elif kind == "ignored":
        git(root, "rm", "-q", "--cached", GUIDE)
        write(root, ".gitignore", f".private/\n{GUIDE}\n")
    elif kind == "bad-frontmatter":
        path.write_text("---\nnot JSON\n---\n# Evidence\n")
    else:
        edit(repo, path=GUIDE)
    errors = audit(repo)["errors"]
    assert errors
    if kind == "ignored":
        assert "document missing from registry: docs/guide.md" in errors


def test_circular_record_symlink_returns_errors_instead_of_crashing(repo):
    root, _ = repo
    path = root / GUIDE
    path.unlink()
    path.symlink_to(path.name)
    errors = audit(repo)["errors"]
    # Python 3.11 resolve raises on a loop; 3.13 non-strict resolve leaves it
    # unresolved and the regular-file guard rejects it. Both must name it.
    assert any(
        error.startswith(f"{GUIDE}:")
        and ("cannot resolve repository path" in error or "regular file without symlinks" in error)
        for error in errors
    )


@pytest.mark.parametrize(
    "text",
    ["{}", "---\n{}", "---\n[]\n---", '---\n{"extra": NaN}\n---', "---\ntype: Evidence\n---"],
)
def test_frontmatter_profile_rejects_malformed_or_non_json(text):
    with pytest.raises(ValueError):
        knowledge.parse_record(text)


def test_bad_json_registry_is_a_structured_error(repo):
    write(repo[0], "docs/knowledge.json", "{")
    errors = audit(repo)["errors"]
    assert len(errors) == 1
    assert errors[0].startswith("docs/knowledge.json:")
