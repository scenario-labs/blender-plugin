# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Exercise knowledge checks with real temporary Git repositories, offline."""

import datetime as dt
import hashlib
import json
import subprocess

import pytest

from tools import check_knowledge as knowledge

TODAY = dt.date(2026, 9, 23)


def git(root, *args):
    return subprocess.check_output(["git", "-C", str(root), *args], text=True).strip()


def write(root, path, text):
    dest = root / path
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(text)
    return dest


def save(root, profile):
    write(root, "docs/knowledge.json", json.dumps(profile))


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
    git(tmp_path, "add", ".")
    git(tmp_path, "commit", "-qm", "test: initial sources")
    profile = {
        "version": 1,
        "index": "docs/index.md",
        "base_revision": git(tmp_path, "rev-parse", "HEAD"),
        "documents": [
            {
                "path": path,
                "coverage": "source-reviewed",
                "reviewed_at": TODAY.isoformat(),
                "limits": "Synthetic source inspection only.",
                "sources": {
                    "source.py": hashlib.sha256((tmp_path / "source.py").read_bytes()).hexdigest()
                },
            }
            for path in (
                "docs/index.md",
                "docs/guide.md",
                "README.md",
                "AGENTS.md",
                "CONTRIBUTING.md",
            )
        ],
    }
    save(tmp_path, profile)
    git(tmp_path, "add", ".")
    git(tmp_path, "commit", "-qm", "docs: register knowledge")
    return tmp_path, profile


def audit(repo):
    return knowledge.audit(repo[0], today=TODAY)


def test_valid_and_read_only(repo):
    before = (repo[0] / "docs/knowledge.json").read_bytes()
    assert audit(repo)["errors"] == []
    assert audit(repo)["warnings"] == []
    assert (repo[0] / "docs/knowledge.json").read_bytes() == before


def test_drift_warns_without_refreshing_evidence(repo):
    root, _ = repo
    write(root, "source.py", "value = 2\n")
    report = audit(repo)
    assert not report["errors"]
    assert len(report["warnings"]) == 5
    assert all("source changed" in item for item in report["warnings"])


def test_deleted_source_is_error(repo):
    (repo[0] / "source.py").unlink()
    assert any("missing or ignored source" in e for e in audit(repo)["errors"])


@pytest.mark.parametrize(
    "field,value",
    [
        ("coverage", "verified"),
        ("coverage", {}),
        ("sources", []),
        ("sources", {}),
        ("limits", ""),
        ("reviewed_at", "tomorrow"),
        ("reviewed_at", "2099-01-01"),
    ],
)
def test_bad_entry_does_not_hide_other_document_errors(repo, field, value):
    root, profile = repo
    profile["documents"][0][field] = value
    save(root, profile)
    write(root, "docs/guide.md", "# Guide\n[Broken](missing.md)\n")
    errors = audit(repo)["errors"]
    assert any("docs/index.md:" in e for e in errors)
    assert any("missing link target" in e for e in errors)


def test_bad_json_and_bad_revision_return_structured_errors(repo):
    root, profile = repo
    write(root, "docs/knowledge.json", "{")
    assert audit(repo)["errors"]
    profile["base_revision"] = "0" * 40
    save(root, profile)
    assert audit(repo)["errors"]


def test_duplicate_missing_registry_and_unreachable_document(repo):
    root, profile = repo
    profile["documents"].append(dict(profile["documents"][0]))
    entry = dict(profile["documents"][0], path="docs/orphan.md")
    profile["documents"].append(entry)
    save(root, profile)
    write(root, "docs/orphan.md", "# Orphan\n")
    write(root, "docs/unregistered.md", "# Unregistered\n")
    errors = audit(repo)["errors"]
    assert any("duplicate document" in e for e in errors)
    assert any("missing from registry" in e for e in errors)
    assert any("unreachable" in e for e in errors)


def test_markdown_fragments_reference_links_and_code_examples(repo):
    root, _ = repo
    guide = "# Guide\n## API `value`\n## API `value`\n[Again](#api-value-1)\n[By ref][source]\n[source]: ../source.py\n```md\n[Not a link](missing.md)\n```\n`[Nor this](missing.md)`\n"
    write(root, "docs/guide.md", guide)
    assert audit(repo)["errors"] == []
    write(root, "docs/guide.md", guide + "[Bad fragment](#no-such-heading)\n")
    assert any("missing Markdown anchor" in e for e in audit(repo)["errors"])


def test_ignored_private_note_is_not_read(repo):
    root, profile = repo
    write(root, ".private/note.md", "not public")
    write(root, "docs/guide.md", "# Guide\n## API value\n[Private](../.private/note.md)\n")
    profile["documents"][0]["sources"] = {".private/note.md": "0" * 64}
    save(root, profile)
    errors = audit(repo)["errors"]
    assert any("missing or ignored source" in e for e in errors)
    assert any("ignored or untracked" in e for e in errors)


def test_escaping_symlink_rejected_for_links_and_sources(repo, tmp_path_factory):
    root, profile = repo
    outside = tmp_path_factory.mktemp("outside") / "secret.md"
    outside.write_text("private text")
    (root / "escape.md").symlink_to(outside)
    write(root, "docs/guide.md", "# Guide\n## API value\n[Escape](../escape.md)\n")
    profile["documents"][0]["sources"] = {"escape.md": "0" * 64}
    save(root, profile)
    assert sum("escapes repository" in e for e in audit(repo)["errors"]) == 2


def test_stale_date_is_warning(repo):
    root, profile = repo
    profile["documents"][0]["reviewed_at"] = "2026-01-01"
    save(root, profile)
    assert any("older than 45 days" in w for w in audit(repo)["warnings"])


def test_merge_base_includes_branch_and_worktree_not_unrelated_base_changes(repo):
    root, _ = repo
    git(root, "checkout", "-qb", "feature")
    write(root, "source.py", "value = 2\n")
    git(root, "add", "source.py")
    git(root, "commit", "-qm", "test: branch change")
    git(root, "checkout", "main")
    write(root, "base-only.py", "base = True\n")
    git(root, "add", ".")
    git(root, "commit", "-qm", "test: advance base")
    git(root, "checkout", "feature")
    write(root, "staged.py", "staged = True\n")
    git(root, "add", "staged.py")
    write(root, "README.md", "# Unstaged\n")
    (root / "AGENTS.md").unlink()
    write(root, "new.py", "new = True\n")
    write(root, ".private/ignored.py", "private = True\n")
    report = knowledge.audit(root, base="main", today=TODAY)
    assert set(report["changed"]) == {"source.py", "staged.py", "README.md", "AGENTS.md", "new.py"}
    assert "docs/guide.md" in report["impacted"]


def test_symlink_cannot_make_ignored_file_public_evidence(repo):
    root, profile = repo
    secret = write(root, ".private/note.md", "private text")
    (root / "alias.md").symlink_to(secret)
    write(root, "docs/guide.md", "# Guide\n## API value\n[Alias](../alias.md)\n")
    profile["documents"][0]["sources"] = {"alias.md": "0" * 64}
    save(root, profile)
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
