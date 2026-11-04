# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Thank a draft release's pull request authors, as GitHub's generated notes list them."""

import json
import os
import re
import subprocess
import sys
import tempfile

HEADING = "### Contributors"
TAG_RE = re.compile(r"blender-plugin-v(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)")
SHA_RE = re.compile(r"[0-9a-fA-F]{40}")
AUTHOR_RE = re.compile(r" by @([A-Za-z0-9-]+(?:\[bot\])?) in https://\S+$")
FIRST_RE = re.compile(r"^\* @([A-Za-z0-9-]+) made their first contribution in https://\S+$")


def gh(*args):
    result = subprocess.run(["gh", *args], check=True, capture_output=True, text=True, timeout=60)
    return result.stdout


def gh_json(*args):
    return json.loads(gh(*args))


def contributors(notes):
    """Return the human authors and GitHub's first-contribution lines from generated notes."""
    authors, first = {}, []
    for line in notes.splitlines():
        line = line.strip()
        if match := AUTHOR_RE.search(line):
            login = match[1]
            if not login.endswith("[bot]"):
                authors.setdefault(login.lower(), login)
        elif FIRST_RE.match(line):
            first.append(line)
    return [authors[key] for key in sorted(authors)], first


def mention_list(logins):
    names = [f"@{login}" for login in logins]
    return names[0] if len(names) == 1 else f"{', '.join(names[:-1])} and {names[-1]}"


def with_contributors(body, notes):
    """Return the body with a Contributors section, or None when there is nothing to add."""
    if re.search(rf"^{re.escape(HEADING)}\s*$", body, re.M):
        return None
    logins, first = contributors(notes)
    if not logins:
        return None
    section = f"{HEADING}\n\nThanks to {mention_list(logins)}.\n"
    if first:
        section += "\n" + "\n".join(first) + "\n"
    return f"{body.rstrip()}\n\n{section}"


def update(repo, tag, sha, request=gh_json, run=gh):
    if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repo):
        raise ValueError("GH_REPO must identify an owner/repository")
    if not TAG_RE.fullmatch(tag) or not SHA_RE.fullmatch(sha):
        raise ValueError("TAG and RELEASE_SHA must be a stable release tag and a full commit SHA")
    draft = request("release", "view", tag, "--json", "body,isDraft,targetCommitish")
    if draft.get("isDraft") is not True or draft.get("targetCommitish", "").lower() != sha.lower():
        raise ValueError(f"{tag} is not the draft for {sha}")
    previous = request("api", f"repos/{repo}/releases/latest").get("tag_name", "")
    if not TAG_RE.fullmatch(previous) or previous == tag:
        raise ValueError("The latest published release has no earlier blender-plugin tag")
    notes = request(
        "api",
        "--method",
        "POST",
        f"repos/{repo}/releases/generate-notes",
        "-f",
        f"tag_name={tag}",
        "-f",
        f"target_commitish={sha}",
        "-f",
        f"previous_tag_name={previous}",
    ).get("body", "")
    body = with_contributors(draft.get("body") or "", notes)
    if body is None:
        return False
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", suffix=".md") as notes_file:
        notes_file.write(body)
        notes_file.flush()
        run("release", "edit", tag, "--notes-file", notes_file.name)
    return True


def main(environ=None, request=gh_json, run=gh):
    environ = os.environ if environ is None else environ
    try:
        changed = update(environ["GH_REPO"], environ["TAG"], environ["RELEASE_SHA"], request, run)
    except (KeyError, ValueError, AttributeError, OSError, subprocess.SubprocessError) as error:
        # Do not echo API responses or subprocess output, which may contain private data.
        message = str(error) if isinstance(error, ValueError) else type(error).__name__
        print(f"::error::Cannot list release contributors: {message}", file=sys.stderr)
        return 1
    print("Added the Contributors section" if changed else "No Contributors section to add")
    return 0


if __name__ == "__main__":
    sys.exit(main())
