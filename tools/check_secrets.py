# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Check forbidden paths and added staged lines without printing matched content.

This is a local guard for common accidental leaks, not a complete secret scanner.
Explicit filenames restrict the staged scan; with no filenames all staged additions,
copies and modifications are checked. Ignored or unstaged content is never read.
"""

import argparse
import os
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

_PATTERNS = {
    "scenario-key": r"SCENARIO_(?:TEST_)?API_(?:KEY|SECRET)[\"']?\s*[=:]\s*[\"']?[A-Za-z0-9_-]{12,}",
    "basic-auth": r"Authorization:\s*Basic\s+[A-Za-z0-9+/=]{20,}",
    "bearer": r"Bearer\s+[A-Za-z0-9_.-]{24,}",
    "curl-user": r"(?:^|\s)-u\s+[A-Za-z0-9_-]{8,}:[A-Za-z0-9_-]{8,}",
    "private-key": r"-----BEGIN [A-Z ]*PRIVATE KEY-----",
    "github-token": r"(?:ghp|gho)_[A-Za-z0-9]{36}|github_pat_[A-Za-z0-9_]{82}",
    "aws-key": r"AKIA[0-9A-Z]{16}",
    "anthropic-key": r"sk-ant-[A-Za-z0-9_-]{20,}",
    "google-key": r"AIza[0-9A-Za-z_-]{35}",
    "signed-url": r"(?:Key-Pair-Id|X-Amz-Signature|X-Amz-Credential)=",
    "password": r"(?i)password[\"']?\s*[:=]\s*[\"'][^\"']{8,}",
}
PATTERNS = {name: re.compile(pattern) for name, pattern in _PATTERNS.items()}
_HUNK = re.compile(rb"^@@ -\d+(?:,\d+)? \+(\d+)(?:,\d+)? @@")
_MEDIA = {
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".webp",
    ".ico",
    ".exr",
    ".hdr",
    ".ttf",
    ".otf",
    ".woff",
    ".woff2",
    ".mp3",
    ".wav",
    ".ogg",
    ".mp4",
    ".webm",
}
_SELF = {"tools/check_secrets.py", "tests/unit/test_check_secrets.py"}


@dataclass(frozen=True)
class Finding:
    path: str
    line: int
    pattern: str

    def __str__(self):
        # Omit the entire line, not just the first matching value: a line can
        # contain a second secret which a preview would otherwise disclose.
        return f"BLOCKED: {self.path!r}:{self.line} {self.pattern} [content redacted]"


def forbidden_reason(path):
    """Return the forbidden-file category, or None for an allowed relative path."""
    path = PurePosixPath(str(path).replace("\\", "/"))
    name = path.name.lower()
    value = path.as_posix().lower()
    if name == ".env" or (name.startswith(".env.") and name != ".env.example"):
        return "environment file"
    if path.suffix.lower() in {".pem", ".key", ".p12", ".pfx"}:
        return "private key or certificate container"
    if re.fullmatch(r"(?:credentials.*|service[-_]account.*)\.json", name):
        return "credential file"
    if re.search(r"\.blend\d*$", name) and value != "tools/blank.blend":
        return "Blender scene or preferences"
    if name == "jobs.json" and not value.startswith("tests/fixtures/"):
        return "local job registry"
    if path.suffix.lower() in {
        ".zip",
        ".exe",
        ".dll",
        ".so",
        ".dylib",
        ".bin",
        ".o",
        ".a",
        ".class",
        ".jar",
        ".pyc",
        ".pyo",
        ".db",
        ".sqlite",
        ".sqlite3",
        ".dump",
        ".bak",
    }:
        return "archive, executable or database"
    return None


def scan_lines(path, lines):
    """Scan (new-file line number, text) pairs; deliberately allowed examples pass."""
    if path in _SELF:
        return []
    return [
        Finding(path, number, name)
        for number, line in lines
        if "secrets-allow" not in line
        for name, pattern in PATTERNS.items()
        if pattern.search(line)
    ]


def _git(root, *args):
    return subprocess.run(
        ["git", "--literal-pathspecs", *args], cwd=root, check=True, capture_output=True
    ).stdout


def added_lines(diff):
    """Yield added text with its actual staged-file line number from a zero-context diff."""
    number = None
    for line in diff.splitlines():
        hunk = _HUNK.match(line)
        if hunk:
            number = int(hunk[1])
        elif number is not None and line.startswith(b"+"):
            yield number, line[1:].decode("utf-8", errors="replace")
            number += 1
        elif number is not None and line.startswith(b" "):
            number += 1


def main(argv=None, *, root=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("files", nargs="*", help="repository-relative filenames")
    args = parser.parse_args(argv)
    try:
        root = (
            Path(root)
            if root is not None
            else Path(os.fsdecode(_git(Path.cwd(), "rev-parse", "--show-toplevel")).strip())
        )
        staged = {
            os.fsdecode(path)
            for path in _git(
                root, "diff", "--cached", "--name-only", "-z", "--no-renames", "--diff-filter=ACM"
            ).split(b"\0")
            if path
        }
        files = sorted(set(args.files) if args.files else staged)
        blocked = False
        for path in files:
            relative = PurePosixPath(path.replace("\\", "/"))
            if relative.is_absolute() or ".." in relative.parts:
                print(f"BLOCKED file: {path!r} (expected a repository-relative filename)")
                blocked = True
                continue
            reason = forbidden_reason(path)
            if reason:
                print(f"BLOCKED file: {path!r} ({reason})")
                blocked = True
                continue
            if path not in staged or path in _SELF or relative.suffix.lower() in _MEDIA:
                continue
            content = _git(root, "show", f":{path}")
            if b"\0" in content[:8192]:
                continue
            diff = _git(
                root,
                "diff",
                "--cached",
                "--no-ext-diff",
                "--no-textconv",
                "--no-renames",
                "--unified=0",
                "--",
                path,
            )
            findings = scan_lines(path, added_lines(diff))
            for finding in findings:
                print(finding)
            blocked |= bool(findings)
        if blocked:
            print(
                "Remove sensitive content from the index before committing. Review any deliberate exception."
            )
        return int(blocked)
    except (OSError, subprocess.CalledProcessError):
        # Git output may include source content or configured helper output.
        print("Secret check could not read the Git index; no clean result is available.")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
