# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Offline documentation navigation, evidence and source-drift checks.

Each canonical document has one OKF evidence record that names its sources and
the main commit it was last reviewed against. Drift is what Git reports as
changed since that commit. This checker never rewrites reviews, fetches URLs,
executes examples or calls a model.
"""

import argparse
import datetime as dt
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from urllib.parse import unquote, urlsplit

COVERAGE = {"source-reviewed", "inherited", "historical", "navigation", "policy"}
COMMIT = re.compile(r"[0-9a-f]{40}\Z")
RECORD_ID = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*\Z")
EVIDENCE_KEYS = {"path", "coverage", "reviewed_at", "reviewed_revision", "limits", "sources"}
MAX_LIMIT_WORDS = 60
SHOWN_DRIFT = 5


def git(root, *args):
    return subprocess.check_output(["git", "-C", str(root), *args], text=True)


def files(root):
    """Include proposed files but exclude ignored private notes and build output."""
    return set(
        git(root, "ls-files", "-z", "--cached", "--others", "--exclude-standard").split("\0")
    ) - {""}


def safe_path(root, relative):
    if not isinstance(relative, str) or not relative or Path(relative).is_absolute():
        raise ValueError("expected a repository-relative path")
    path = root / relative
    try:
        resolved = path.resolve()
    except RuntimeError as exc:
        raise ValueError(f"cannot resolve repository path: {relative}") from exc
    if not resolved.is_relative_to(root.resolve()):
        raise ValueError(f"path escapes repository: {relative}")
    return path


def unfenced(text):
    """Remove fenced examples from navigation and heading discovery."""
    lines = []
    fence = None
    for line in text.splitlines():
        match = re.match(r"^\s*(`{3,}|~{3,})", line)
        if match:
            marker = match[1]
            if fence is None:
                fence = marker
            elif marker[0] == fence[0] and len(marker) >= len(fence):
                fence = None
            continue
        if fence is None:
            lines.append(line)
    return "\n".join(lines)


def prose(text):
    return re.sub(r"(`+).*?\1", "", unfenced(text))


def anchors(text):
    text = unfenced(text)
    counts = {}
    result = set(re.findall(r'(?:id|name)=["\']([^"\']+)["\']', text))
    # Retain heading code contents: GitHub includes them in the fragment.
    for match in re.finditer(r"^#{1,6}\s+(.+?)\s*#*\s*$", text, re.M):
        title = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", match[1])
        title = re.sub(r"<[^>]+>", "", title).lower()
        slug = re.sub(r"[^\w\- ]", "", title).replace(" ", "-")
        count = counts.get(slug, 0)
        result.add(f"{slug}-{count}" if count else slug)
        counts[slug] = count + 1
    return result


def destinations(text):
    text = prose(text)
    # Inline links/images and reference definitions. Destinations with spaces
    # must use <...>; nested parentheses in bare paths are outside this subset.
    pattern = r"\]\(\s*(<[^>]+>|[^\s)]+)(?:\s+[^)]*)?\)|^\s*\[[^\]]+\]:\s*(<[^>]+>|\S+)"
    return [next(x for x in match if x).strip("<>") for match in re.findall(pattern, text, re.M)]


def undefined_references(text):
    text = prose(text)
    definitions = {
        " ".join(label.lower().split()) for label in re.findall(r"^\s*\[([^\]]+)\]:", text, re.M)
    }
    # Only lint standalone reference pairs. Attached indexing expressions and
    # escaped opening brackets are ordinary prose in this supported subset.
    pattern = r"(?<![\w\]\\)])\[([^\]]+)\]\[([^\]]*)\]"
    return [
        reference or label
        for label, reference in re.findall(pattern, text)
        if " ".join((reference or label).lower().split()) not in definitions
    ]


def navigation(root, known, paths, errors, bodies=None):
    graph = {}
    for relative in sorted(paths):
        graph[relative] = set()
        try:
            path = safe_path(root, relative)
            if path.resolve().relative_to(root).as_posix() not in known:
                raise ValueError("document resolves to an ignored or untracked file")
            content = bodies[relative] if bodies and relative in bodies else path.read_text()
        except (OSError, ValueError) as exc:
            errors.append(f"{relative}: {exc}")
            continue
        errors.extend(
            f"{relative}: undefined reference link: {label}"
            for label in undefined_references(content)
        )
        for link in destinations(content):
            try:
                parsed = urlsplit(link)
                if parsed.scheme or parsed.netloc:
                    continue
                destination = unquote(parsed.path)
                if destination.startswith("/"):
                    raise ValueError(
                        f"unsupported root-relative link: {link}; use a document-relative link"
                    )
                target = (
                    safe_path(root, str(Path(relative).parent / destination))
                    if destination
                    else path
                )
                if not target.exists():
                    raise ValueError(f"missing link target: {link}")
                # Normalize without resolving symlinks for Git's tracked names.
                name = Path(os.path.normpath(target)).relative_to(root).as_posix()
                resolved = target.resolve().relative_to(root).as_posix()
                if target.is_file() and (name not in known or resolved not in known):
                    raise ValueError(f"link target is ignored or untracked: {link}")
                if target.is_dir() and not any(p.startswith(name.rstrip("/") + "/") for p in known):
                    raise ValueError(f"link directory has no tracked content: {link}")
                if target.suffix == ".md" and target.is_file():
                    graph[relative].add(name)
                    if parsed.fragment and unquote(parsed.fragment) not in anchors(
                        target.read_text()
                    ):
                        raise ValueError(f"missing Markdown anchor: {link}")
            except (OSError, ValueError) as exc:
                errors.append(f"{relative}: {exc}")
    return graph


def changed_files(root, base):
    merge_base = git(root, "merge-base", "HEAD", base).strip()
    # Diff against the worktree includes committed, staged, unstaged and deleted
    # paths; untracked nonignored additions are collected separately.
    changed = set(git(root, "diff", "--name-only", "-z", merge_base, "--").split("\0"))
    changed.update(git(root, "ls-files", "--others", "--exclude-standard", "-z").split("\0"))
    return sorted(changed - {""})


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def invalid_constant(value):
    raise ValueError(f"invalid JSON constant: {value}")


def parse_record(text):
    """Read our JSON-as-YAML OKF frontmatter subset, preserving extension keys.

    This is a repository profile, not a general YAML or OKF validator. JSON
    provides unambiguous dates and hashes without executing tags or aliases.
    """
    lines = text.splitlines(keepends=True)
    if not lines or lines[0].strip() != "---":
        raise ValueError("expected JSON frontmatter between --- delimiters")
    end = next((i for i in range(1, len(lines)) if lines[i].strip() == "---"), None)
    if end is None:
        raise ValueError("missing closing frontmatter delimiter")
    metadata = json.loads(
        "".join(lines[1:end]), object_pairs_hook=unique_object, parse_constant=invalid_constant
    )
    if not isinstance(metadata, dict):
        raise ValueError("frontmatter must be an object")
    return metadata, "".join(lines[end + 1 :])


def record_directory(root, relative):
    """Require a real, canonical subdirectory of docs, never a symlink alias."""
    if (
        not isinstance(relative, str)
        or not relative.startswith("docs/")
        or "\\" in relative
        or any(part in ("", ".", "..") for part in relative.split("/"))
    ):
        raise ValueError("records.root must be a canonical subdirectory of docs")
    path = safe_path(root, relative)
    if path.resolve() != path:
        raise ValueError("record directory must not contain symlinks")
    return path


def load_registry(root, known, errors):
    registry = safe_path(root, "docs/knowledge.json")
    if registry.resolve().relative_to(root).as_posix() not in known:
        raise ValueError("registry resolves to an ignored or untracked file")
    profile = json.loads(
        registry.read_text(), object_pairs_hook=unique_object, parse_constant=invalid_constant
    )
    if not isinstance(profile, dict) or profile.get("version") != 3:
        raise ValueError("expected knowledge registry version 3")
    if set(profile) != {"version", "index", "records"}:
        raise ValueError("version 3 config contains only version, index and records")
    config = profile["records"]
    if not isinstance(config, dict) or set(config) != {"root", "format"}:
        raise ValueError("records must contain root and format")
    if config["format"] != "okf-json":
        raise ValueError("records.format must be okf-json")
    record_directory(root, config["root"])
    prefix = config["root"] + "/"
    names = sorted(p for p in known if p.startswith(prefix) and p.endswith(".md"))
    if not names:
        raise ValueError("no evidence records discovered")
    entries, bodies = [], {}
    for name in names:
        bodies[name] = ""
        try:
            if "/" in name[len(prefix) :]:
                raise ValueError(f"evidence record must sit directly under {config['root']}")
            path = safe_path(root, name)
            if path.resolve() != path or not path.is_file():
                raise ValueError("evidence record must be a regular file without symlinks")
            metadata, bodies[name] = parse_record(path.read_text())
            if metadata.get("type") != "Evidence":
                raise ValueError("record type must be Evidence")
            record_id = metadata.get("id")
            if not isinstance(record_id, str) or not RECORD_ID.fullmatch(record_id):
                raise ValueError("id must be a lowercase hyphenated name")
            if record_id != Path(name).stem:
                raise ValueError("id must match the record file name")
            entry = metadata.get("evidence")
            if not isinstance(entry, dict) or not isinstance(entry.get("path"), str):
                raise ValueError("evidence must contain a document path string")
            unknown = sorted(set(entry) - EVIDENCE_KEYS)
            if unknown:
                raise ValueError("unsupported evidence fields: " + ", ".join(unknown))
            entries.append((name, entry))
        except (OSError, ValueError) as exc:
            errors.append(f"{name}: {exc}")
    return profile, entries, bodies


def review_base(root, revision, base, comparison):
    if not isinstance(revision, str) or not COMMIT.fullmatch(revision):
        raise ValueError("reviewed_revision must be a full Git commit")
    git(root, "cat-file", "-e", revision + "^{commit}")
    if comparison is not None:
        try:
            git(root, "merge-base", "--is-ancestor", revision, comparison)
        except subprocess.CalledProcessError as exc:
            if exc.returncode != 1:
                raise
            raise ValueError(
                f"reviewed_revision must be reachable from comparison base {base!r}; "
                "refresh/select the canonical repository's main ref, then record a durable "
                "main review base, not an unmerged or pre-squash PR commit"
            ) from exc


def changed_since(root, revision):
    """Committed, staged, unstaged and deleted paths since a reviewed commit."""
    return set(git(root, "diff", "--name-only", "-z", revision, "--").split("\0")) - {""}


def check_sources(root, known, entry, changed, documents):
    """Return changed and removed sources since review; raise on structural problems.

    Canonical documents never drift: only the release refresh edits them after
    review, so counting them would keep every refreshed record drifted.
    """
    sources = entry.get("sources")
    if (
        not isinstance(sources, list)
        or not sources
        or not all(isinstance(source, str) for source in sources)
    ):
        raise ValueError("sources must be a nonempty list of repository paths")
    if sources != sorted(set(sources)):
        raise ValueError("sources must be sorted and unique")
    drifted, removed = [], []
    for source in sources:
        path = safe_path(root, source)
        if not path.exists() and not path.is_symlink() and source in changed:
            drifted.append(source)
            removed.append(source)
            continue
        if (
            source not in known
            or not path.is_file()
            or path.resolve().relative_to(root).as_posix() not in known
        ):
            raise ValueError(f"missing or ignored source: {source}")
        if source in changed and source not in documents:
            drifted.append(source)
    return drifted, removed


def audit(root, base=None, today=None):
    root = root.resolve()
    today = today or dt.datetime.now(dt.UTC).date()
    report = {
        "errors": [],
        "warnings": [],
        "documents": [],
        "drift": [],
        "changed": [],
        "impacted": [],
    }
    errors, warnings = report["errors"], report["warnings"]
    known = files(root)
    try:
        profile, entries, bodies = load_registry(root, known, errors)
        comparison = None
        if base is not None:
            comparison = git(
                root, "rev-parse", "--verify", "--end-of-options", base + "^{commit}"
            ).strip()
    except (OSError, ValueError, subprocess.CalledProcessError) as exc:
        errors.append(f"docs/knowledge.json: {exc}")
        return report
    expected = {
        p
        for p in known
        if p.startswith("docs/") and p.endswith(".md") and p not in bodies and (root / p).exists()
    }
    expected.update({"README.md", "AGENTS.md", "CONTRIBUTING.md"})
    expected.update(p for p in known if p.startswith(".claude/rules/") and p.endswith(".md"))
    documents = expected | {entry["path"] for _, entry in entries} | set(bodies)
    registered = set()
    sources_by_doc = {}
    changes = {}
    for record, entry in entries:
        relative = entry["path"]
        label = f"{relative} [{record}]"
        if relative in registered:
            errors.append(f"duplicate document: {relative}")
            continue
        registered.add(relative)
        try:
            path = safe_path(root, relative)
            if (
                relative not in known
                or not path.is_file()
                or path.suffix != ".md"
                or relative in bodies
            ):
                raise ValueError("document must be a nonignored Markdown file")
            if entry.get("coverage") not in COVERAGE:
                raise ValueError("invalid coverage")
            limits = entry.get("limits")
            if not isinstance(limits, str) or not limits.strip():
                raise ValueError("coverage limits must be explicit")
            if len(limits.split()) > MAX_LIMIT_WORDS:
                raise ValueError(
                    f"limits must be at most {MAX_LIMIT_WORDS} words, not {len(limits.split())}"
                )
            reviewed = dt.date.fromisoformat(entry.get("reviewed_at", ""))
            if reviewed > today:
                raise ValueError("reviewed_at is in the future")
            revision = entry.get("reviewed_revision")
            if revision not in changes:
                review_base(root, revision, base, comparison)
                changes[revision] = changed_since(root, revision)
            drifted, removed = check_sources(root, known, entry, changes[revision], documents)
            sources_by_doc[relative] = set(entry["sources"]) | {record}
        except (OSError, ValueError, TypeError, subprocess.CalledProcessError) as exc:
            errors.append(f"{label}: {exc}")
            continue
        if drifted:
            report["drift"].append(
                {
                    "path": relative,
                    "record": record,
                    "reviewed_revision": revision,
                    "sources": drifted,
                    "removed": removed,
                }
            )
            shown = ", ".join(
                f"{source} (removed)" if source in removed else source
                for source in drifted[:SHOWN_DRIFT]
            )
            more = len(drifted) - SHOWN_DRIFT
            warnings.append(
                f"{label}: {len(drifted)} of {len(entry['sources'])} sources changed since review: "
                + shown
                + (f" and {more} more" if more > 0 else "")
            )
    report["documents"] = sorted(registered)
    errors.extend(f"document missing from registry: {p}" for p in sorted(expected - registered))
    graph = navigation(root, known, expected | registered | set(bodies), errors, bodies)
    index = profile.get("index")
    if not isinstance(index, str) or index not in registered:
        errors.append("index must name a registered Markdown document")
    else:
        reachable, pending = set(), [index]
        while pending:
            node = pending.pop()
            if node not in reachable:
                reachable.add(node)
                pending.extend(graph.get(node, set()) - reachable)
        errors.extend(
            f"document unreachable from index: {p}" for p in sorted(registered - reachable)
        )
    if base:
        report["changed"] = changed_files(root, comparison)
        changed = set(report["changed"])
        report["impacted"] = sorted(
            p for p, sources in sources_by_doc.items() if sources & changed or p in changed
        )
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument(
        "--base",
        help="require reviewed revisions on this ref and report branch/worktree impact against it",
    )
    parser.add_argument("--json", action="store_true", help="emit a machine-readable report")
    args = parser.parse_args()
    try:
        report = audit(args.root, args.base)
    except (OSError, ValueError, subprocess.CalledProcessError) as exc:
        print(f"knowledge check failed: {exc}", file=sys.stderr)
        return 1
    if args.json:
        print(json.dumps(report, indent=2))
    else:
        for key in ("errors", "warnings"):
            for message in report[key]:
                print(f"{key[:-1].upper()}: {message}")
        print(
            f"Knowledge: {len(report['documents'])} documents, {len(report['errors'])} errors, "
            f"{len(report['drift'])} with source drift"
        )
        if args.base:
            print("Impacted documents: " + ", ".join(report["impacted"]))
    return bool(report["errors"])


if __name__ == "__main__":
    raise SystemExit(main())
