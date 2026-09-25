# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Exercise knowledge checks with real temporary Git repositories, offline."""

import datetime as dt
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

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


@pytest.mark.parametrize("local_offset,utc_hour", [(-12, 0), (14, 23)])
def test_default_clock_uses_utc_across_local_midnight(repo, monkeypatch, local_offset, utc_hour):
    root, profile = repo
    instant = dt.datetime.combine(TODAY, dt.time(utc_hour, 30), tzinfo=dt.UTC)
    local_zone = dt.timezone(dt.timedelta(hours=local_offset))
    assert instant.astimezone(local_zone).date() != TODAY

    class LocalDate(dt.date):
        @classmethod
        def today(cls):
            return instant.astimezone(local_zone).date()

    class Clock(dt.datetime):
        @classmethod
        def now(cls, tz=None):
            return instant.astimezone(tz or local_zone)

    monkeypatch.setattr(
        knowledge, "dt", SimpleNamespace(date=LocalDate, datetime=Clock, UTC=dt.UTC)
    )
    assert knowledge.audit(root)["errors"] == []
    profile["documents"][0]["reviewed_at"] = (TODAY + dt.timedelta(days=1)).isoformat()
    save(root, profile)
    assert any("reviewed_at is in the future" in error for error in knowledge.audit(root)["errors"])
    profile["documents"][0]["reviewed_at"] = (TODAY - dt.timedelta(days=45)).isoformat()
    save(root, profile)
    assert knowledge.audit(root)["warnings"] == []
    profile["documents"][0]["reviewed_at"] = (TODAY - dt.timedelta(days=46)).isoformat()
    save(root, profile)
    assert any("older than 45 days" in warning for warning in knowledge.audit(root)["warnings"])


@pytest.mark.parametrize("squashed", [False, True])
def test_comparison_rejects_cached_pr_base_before_and_after_squash(repo, squashed):
    root, profile = repo
    git(root, "checkout", "-qb", "parent")
    write(root, "source.py", "value = 2\n")
    git(root, "add", "source.py")
    git(root, "commit", "-qm", "test: parent change")
    parent = git(root, "rev-parse", "HEAD")
    if squashed:
        git(root, "checkout", "main")
        git(root, "merge", "--squash", "parent")
        git(root, "commit", "-qm", "test: squash parent")
        git(root, "branch", "-D", "parent")
    git(root, "update-ref", "refs/remotes/origin/main", git(root, "rev-parse", "main"))
    profile["base_revision"] = parent
    save(root, profile)

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
    assert len(json.loads(result.stdout)["errors"]) == 1
    assert "base_revision must be reachable from comparison base 'origin/main'" in result.stdout


def test_durable_base_allows_stacked_source_evidence_in_detached_checkout(repo):
    root, profile = repo
    main = git(root, "rev-parse", "main")
    git(root, "update-ref", "refs/remotes/origin/main", main)
    git(root, "checkout", "-qb", "parent")
    write(root, "source.py", "value = 2\n")
    git(root, "add", "source.py")
    git(root, "commit", "-qm", "test: parent change")
    git(root, "checkout", "-qb", "child")
    write(root, "source.py", "value = 3\n")
    profile["base_revision"] = main
    for entry in profile["documents"]:
        entry["sources"]["source.py"] = hashlib.sha256(
            (root / "source.py").read_bytes()
        ).hexdigest()
    save(root, profile)
    git(root, "add", ".")
    git(root, "commit", "-qm", "docs: inspect stacked source")
    git(root, "checkout", "--detach")
    before = (
        git(root, "show-ref"),
        git(root, "status", "--porcelain"),
        (root / "docs/knowledge.json").read_bytes(),
    )

    # Only local objects/refs are needed: no configured remote or credentials.
    assert git(root, "remote") == ""
    report = knowledge.audit(root, base="origin/main", today=TODAY)
    assert report["errors"] == []
    assert report["warnings"] == []
    assert set(report["changed"]) == {"source.py", "docs/knowledge.json"}
    assert set(report["impacted"]) == {entry["path"] for entry in profile["documents"]}
    assert (
        git(root, "show-ref"),
        git(root, "status", "--porcelain"),
        (root / "docs/knowledge.json").read_bytes(),
    ) == before


def test_missing_comparison_ref_fails_without_changing_standalone_behavior(repo):
    assert audit(repo)["errors"] == []
    errors = knowledge.audit(repo[0], base="origin/missing", today=TODAY)["errors"]
    assert len(errors) == 1
    assert "origin/missing" in errors[0]


def test_stale_fork_ref_rejects_but_selected_current_upstream_ref_passes(repo):
    root, profile = repo
    git(root, "update-ref", "refs/remotes/origin/main", git(root, "rev-parse", "main"))
    write(root, "upstream.py", "new = True\n")
    git(root, "add", "upstream.py")
    git(root, "commit", "-qm", "test: advance canonical main")
    current = git(root, "rev-parse", "HEAD")
    git(root, "update-ref", "refs/remotes/upstream/main", current)
    git(root, "checkout", "-qb", "feature")
    profile["base_revision"] = current
    save(root, profile)

    stale = knowledge.audit(root, base="origin/main", today=TODAY)
    assert len(stale["errors"]) == 1
    assert "refresh/select the canonical repository's main ref" in stale["errors"][0]
    current_report = knowledge.audit(root, base="upstream/main", today=TODAY)
    assert current_report["errors"] == []
    assert current_report["warnings"] == []
    assert current_report["changed"] == ["docs/knowledge.json"]
    assert git(root, "rev-parse", "origin/main") != current


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


def save_topic(root, name, metadata, body="# Evidence\n"):
    return write(root, name, "---\n" + json.dumps(metadata, indent=2) + "\n---\n" + body)


def split_profile(root, profile, directory="docs/knowledge"):
    records = {}
    for number, entry in enumerate(profile["documents"]):
        name = f"{directory}/record-{number}.md"
        records[name] = {
            "type": "Evidence",
            "id": f"record-{number}",
            "evidence": dict(
                entry, scope="inherited-baseline", base_revision=profile["base_revision"]
            ),
            "migration": {"note": "Mechanical split; no fresh review or human verification."},
        }
        save_topic(root, name, records[name])
    save(
        root,
        {
            "version": 2,
            "index": profile["index"],
            "records": {"root": directory, "format": "okf-json"},
        },
    )
    return records


@pytest.fixture
def topics(repo):
    root, profile = repo
    records = split_profile(root, profile)
    git(root, "add", ".")
    git(root, "commit", "-qm", "docs: split evidence concepts")
    return root, records


def test_topic_migration_preserves_stale_evidence_and_read_only_report(repo):
    root, profile = repo
    profile["documents"][0]["reviewed_at"] = "2026-01-01"
    profile["documents"][1]["sources"]["source.py"] = "1" * 64
    save(root, profile)
    old = audit(repo)
    records = split_profile(root, profile)
    before = {name: (root / name).read_bytes() for name in records}
    report = audit(repo)
    assert report["errors"] == []
    assert report["documents"] == old["documents"]
    assert [re.sub(r" \[record-\d+\]", "", w) for w in report["warnings"]] == old["warnings"]
    assert len(report["topics"]) == len(old["documents"])
    assert {name: (root / name).read_bytes() for name in records} == before
    for entry, metadata in zip(profile["documents"], records.values(), strict=True):
        assert all(metadata["evidence"][key] == value for key, value in entry.items())
        assert "verified" not in metadata


def test_multiple_topics_aggregate_impact_without_replacing_sources(topics):
    root, records = topics
    write(root, "second.py", "separate = True\n")
    metadata = dict(records["docs/knowledge/record-1.md"], id="guide.second")
    metadata["evidence"] = dict(
        metadata["evidence"], scope="second", sources={"second.py": "1" * 64}
    )
    save_topic(root, "docs/knowledge/nested/second.md", metadata)
    git(root, "add", ".")
    git(root, "commit", "-qm", "docs: second topic")
    write(root, "source.py", "changed = True\n")
    write(root, "second.py", "changed = True\n")
    report = knowledge.audit(root, base="main", today=TODAY)
    assert not report["errors"]
    assert report["documents"].count("docs/guide.md") == 1
    assert report["impacted"].count("docs/guide.md") == 1
    assert "guide.second" in report["impacted_topics"]
    assert "record-1" in report["impacted_topics"]
    assert any(
        "docs/guide.md [guide.second]: source changed: second.py" == w for w in report["warnings"]
    )
    assert any(
        "docs/guide.md [record-1]: source changed: source.py" == w for w in report["warnings"]
    )


def test_topic_metadata_edit_impacts_own_document_only(topics):
    root, records = topics
    name = "docs/knowledge/record-1.md"
    records[name]["evidence"]["limits"] = "Scoped follow-up, not human approval."
    save_topic(root, name, records[name])
    report = knowledge.audit(root, base="main", today=TODAY)
    assert report["errors"] == []
    assert report["impacted"] == ["docs/guide.md"]
    assert report["impacted_topics"] == ["record-1"]


@pytest.mark.parametrize("kind", ["id", "scope", "json-key"])
def test_duplicate_topic_ownership_cannot_silently_win(topics, kind):
    root, records = topics
    metadata = dict(records["docs/knowledge/record-1.md"])
    if kind == "scope":
        metadata["id"] = "different-id"
    name = "docs/knowledge/duplicate.md"
    path = save_topic(root, name, metadata)
    if kind == "json-key":
        path.write_text(
            path.read_text().replace(
                '"type": "Evidence",', '"type": "Evidence", "type": "Evidence",'
            )
        )
    errors = knowledge.audit(root, today=TODAY)["errors"]
    assert any("duplicate" in e for e in errors)


@pytest.mark.parametrize("topic", ["", "../escape", "Uppercase", "two words", "trailing.", {}, 3])
def test_invalid_topic_id_is_structured_error(topics, topic):
    root, records = topics
    name = "docs/knowledge/record-1.md"
    records[name]["id"] = topic
    save_topic(root, name, records[name])
    assert any("id must be" in e for e in knowledge.audit(root, today=TODAY)["errors"])


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
    root, profile = repo
    save(
        root,
        {
            "version": 2,
            "index": profile["index"],
            "records": {"root": directory, "format": "okf-json"},
        },
    )
    assert any("canonical subdirectory" in e for e in audit(repo)["errors"])


def test_configurable_discovery_and_concept_links_do_not_require_recursive_evidence(repo):
    root, profile = repo
    records = split_profile(root, profile, "docs/evidence")
    name = "docs/evidence/record-1.md"
    records[name]["description"] = "Metadata example [not a body link](missing.md)"
    save_topic(root, name, records[name], "# Evidence\n[Guide](../guide.md#api-value)\n")
    assert audit(repo)["errors"] == []
    save_topic(root, name, records[name], "# Evidence\n[Missing](../missing.md)\n")
    assert any("missing link target" in e for e in audit(repo)["errors"])


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
def test_records_cannot_escape_or_hide_registration(topics, tmp_path_factory, kind):
    root, records = topics
    name = "docs/knowledge/record-1.md"
    path = root / name
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
        git(root, "rm", "--cached", name)
        write(root, ".gitignore", ".private/\ndocs/knowledge/record-1.md\n")
    elif kind == "bad-frontmatter":
        path.write_text("---\nnot JSON\n---\n# Evidence\n")
    else:
        records[name]["evidence"]["path"] = name
        save_topic(root, name, records[name])
    errors = knowledge.audit(root, today=TODAY)["errors"]
    assert errors
    if kind == "ignored":
        assert "document missing from registry: docs/guide.md" in errors


def test_legacy_and_topic_ownership_cannot_mix(repo):
    root, profile = repo
    split_profile(root, profile)
    save(root, profile)
    assert any("cannot coexist" in e for e in audit(repo)["errors"])
    split_profile(root, profile)
    config = json.loads((root / "docs/knowledge.json").read_text())
    config["documents"] = profile["documents"]
    save(root, config)
    assert any("contains only" in e for e in audit(repo)["errors"])


@pytest.mark.parametrize("squashed", [False, True])
def test_each_topic_requires_durable_base_when_comparison_is_requested(topics, squashed):
    root, records = topics
    git(root, "checkout", "-qb", "parent")
    write(root, "parent.py", "changed = True\n")
    git(root, "add", ".")
    git(root, "commit", "-qm", "test: parent")
    parent = git(root, "rev-parse", "HEAD")
    git(root, "checkout", "main")
    if squashed:
        git(root, "merge", "--squash", "parent")
        git(root, "commit", "-qm", "test: squash parent")
        git(root, "branch", "-D", "parent")
    name = "docs/knowledge/record-1.md"
    records[name]["evidence"]["base_revision"] = parent
    save_topic(root, name, records[name])
    assert knowledge.audit(root, today=TODAY)["errors"] == []
    report = knowledge.audit(root, base="main", today=TODAY)
    assert len(report["errors"]) == 1
    assert "docs/guide.md [record-1]: base_revision must be reachable" in report["errors"][0]


def test_unrelated_topic_branches_merge_without_umbrella_edits(topics):
    root, records = topics
    config = (root / "docs/knowledge.json").read_bytes()
    second = dict(records["docs/knowledge/record-1.md"], id="guide.independent")
    second["evidence"] = dict(second["evidence"], scope="independent")
    save_topic(root, "docs/knowledge/independent.md", second)
    git(root, "add", ".")
    git(root, "commit", "-qm", "docs: independent topic on same guide")
    git(root, "checkout", "-qb", "feature")
    name = "docs/knowledge/record-1.md"
    records[name]["evidence"]["limits"] = "Guide evidence update."
    records[name]["evidence"]["reviewed_at"] = "2026-09-22"
    records[name]["evidence"]["sources"] = {"source.py": "1" * 64}
    save_topic(root, name, records[name])
    git(root, "add", ".")
    git(root, "commit", "-qm", "docs: guide topic")
    git(root, "checkout", "main")
    name = "docs/knowledge/independent.md"
    second["evidence"]["limits"] = "Independent guide evidence update."
    save_topic(root, name, second)
    git(root, "add", ".")
    git(root, "commit", "-qm", "docs: independent guide topic")
    git(root, "merge", "feature", "--no-edit")
    assert knowledge.audit(root, base="main", today=TODAY)["errors"] == []
    assert "Guide evidence update." in (root / "docs/knowledge/record-1.md").read_text()
    independent, _ = knowledge.parse_record((root / "docs/knowledge/independent.md").read_text())
    first, _ = knowledge.parse_record((root / "docs/knowledge/record-1.md").read_text())
    assert independent == second
    assert independent["evidence"]["reviewed_at"] == TODAY.isoformat()
    assert independent["evidence"]["sources"]["source.py"] != "1" * 64
    assert first["evidence"]["reviewed_at"] == "2026-09-22"
    assert first["evidence"]["sources"] == {"source.py": "1" * 64}
    assert (root / "docs/knowledge.json").read_bytes() == config


@pytest.mark.parametrize("same_file", [True, False])
def test_conflicting_claims_still_require_review(topics, same_file):
    root, records = topics
    original = records["docs/knowledge/record-1.md"]
    git(root, "checkout", "-qb", "feature")
    left = dict(original, id=original["id"] if same_file else "overlap-left")
    left["evidence"] = dict(
        original["evidence"],
        limits="Left claim.",
        scope="inherited-baseline" if same_file else "new-scope",
    )
    save_topic(root, "docs/knowledge/record-1.md" if same_file else "docs/knowledge/left.md", left)
    git(root, "add", ".")
    git(root, "commit", "-qm", "docs: left claim")
    git(root, "checkout", "main")
    right = dict(original, id=original["id"] if same_file else "overlap-right")
    right["evidence"] = dict(
        original["evidence"],
        limits="Right claim.",
        scope="inherited-baseline" if same_file else "new-scope",
    )
    save_topic(
        root, "docs/knowledge/record-1.md" if same_file else "docs/knowledge/right.md", right
    )
    git(root, "add", ".")
    git(root, "commit", "-qm", "docs: right claim")
    result = subprocess.run(
        ["git", "-C", str(root), "merge", "feature", "--no-edit"], capture_output=True, text=True
    )
    if same_file:
        assert result.returncode == 1
        assert "CONFLICT" in result.stdout
    else:
        assert result.returncode == 0
        assert any(
            "duplicate document/scope" in e for e in knowledge.audit(root, today=TODAY)["errors"]
        )


@pytest.mark.parametrize(
    "field,value,diagnostic",
    [
        ("coverage", {}, "unhashable"),
        ("coverage", "verified", "invalid coverage"),
        ("scope", "", "scope must be"),
        ("scope", "first\rsecond", "scope must be"),
        ("sources", {}, "nonempty path-to-SHA256"),
        ("sources", {"source.py": "bad"}, "invalid SHA256"),
        ("reviewed_at", "2099-01-01", "in the future"),
        ("base_revision", "main", "full Git commit"),
        ("path", "../outside.md", "escapes repository"),
    ],
)
def test_bad_topic_evidence_preserves_other_navigation_checks(topics, field, value, diagnostic):
    root, records = topics
    name = "docs/knowledge/record-1.md"
    records[name]["evidence"][field] = value
    save_topic(root, name, records[name], "# Evidence\n[Broken](missing.md)\n")
    errors = knowledge.audit(root, today=TODAY)["errors"]
    assert any(diagnostic in error for error in errors)
    assert any("missing link target" in error for error in errors)


def test_missing_topic_source_and_record_anchor_are_errors(topics):
    root, records = topics
    name = "docs/knowledge/record-1.md"
    save_topic(root, name, records[name], "# Evidence\n[Broken](../guide.md#missing-heading)\n")
    (root / "source.py").unlink()
    errors = knowledge.audit(root, today=TODAY)["errors"]
    assert any("missing or ignored source" in error for error in errors)
    assert any("missing Markdown anchor" in error for error in errors)


def test_circular_record_symlink_returns_errors_instead_of_crashing(topics):
    root, _ = topics
    path = root / "docs/knowledge/record-1.md"
    path.unlink()
    path.symlink_to(path.name)
    errors = knowledge.audit(root, today=TODAY)["errors"]
    # Python 3.11 resolve raises on a loop; 3.13 non-strict resolve leaves it
    # unresolved and the regular-file guard rejects it. Both must name it.
    assert any(
        error.startswith("docs/knowledge/record-1.md:")
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


def test_topic_ancestry_handles_detached_work_and_explicit_comparison_refs(topics):
    root, records = topics
    old_main = git(root, "rev-parse", "main")
    git(root, "update-ref", "refs/remotes/origin/main", old_main)
    write(root, "upstream.py", "upstream = True\n")
    git(root, "add", ".")
    git(root, "commit", "-qm", "test: advance upstream")
    current = git(root, "rev-parse", "HEAD")
    git(root, "update-ref", "refs/remotes/upstream/main", current)
    git(root, "checkout", "-qb", "child")
    name = "docs/knowledge/record-1.md"
    records[name]["evidence"]["base_revision"] = current
    save_topic(root, name, records[name])
    git(root, "add", ".")
    git(root, "commit", "-qm", "docs: reviewed child")
    git(root, "checkout", "--detach")
    before = git(root, "show-ref"), git(root, "status", "--porcelain")
    assert knowledge.audit(root, today=TODAY)["errors"] == []
    stale = knowledge.audit(root, base="origin/main", today=TODAY)
    assert len(stale["errors"]) == 1
    assert "refresh/select the canonical" in stale["errors"][0]
    missing = knowledge.audit(root, base="origin/missing", today=TODAY)
    assert len(missing["errors"]) == 1
    current_report = knowledge.audit(root, base="upstream/main", today=TODAY)
    assert current_report["errors"] == []
    assert current_report["changed"] == [name]
    assert current_report["impacted"] == ["docs/guide.md"]
    assert (git(root, "show-ref"), git(root, "status", "--porcelain")) == before
