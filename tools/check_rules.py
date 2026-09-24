# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Run the implemented offline house rules; this is not a general YAML validator."""

import argparse
import os
import re
import subprocess
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
_USES = re.compile(r"^\s*(?:-\s*)?(?:uses|'uses'|\"uses\")\s*:\s*(.*)$")
_SCALAR = re.compile(r"(?:'([^'\r\n]*)'|\"([^\"\\\r\n]*)\"|([^\s'\"#]+))(?:\s+(#.*))?\s*$")
_REMOTE = re.compile(r"[\w.-]+/[\w.-]+(?:/[\w./-]+)?@[0-9a-f]{40}", re.ASCII)
_RELEASE = re.compile(r"#\s*v?\d+\.\d+\.\d+(?:[-+][\w.-]+)?(?:\s|$)", re.ASCII)
_BLOCK = re.compile(r":\s*[|>](?:[1-9][+-]?|[+-][1-9]?)?\s*(?:#.*)?$")
_FLOW = re.compile(r"^\s*(?:-\s*)?(?:(?:[\w.-]+|'[^']+'|\"[^\"]+\"):\s*)?[\[{]")
_FLOW_USES = re.compile(r"(?:^|[{,])\s*(?:uses|'uses'|\"uses\")\s*:")


@dataclass(frozen=True, order=True)
class Violation:
    path: str
    line: int
    rule: str
    message: str

    def __str__(self):
        return f"{self.path}:{self.line}: {self.rule}: {self.message}"


def tracked_files(root):
    """Use Git's NUL-delimited inventory, with an archive-checkout fallback."""
    try:
        result = subprocess.run(
            ["git", "ls-files", "-z"], cwd=root, check=True, capture_output=True
        )
    except (FileNotFoundError, subprocess.CalledProcessError):
        skipped = {".git", ".venv", "__pycache__", ".blender-profile", "dist", "workdir"}
        files = []
        for folder, directories, names in os.walk(root, followlinks=False):
            directories[:] = sorted(name for name in directories if name not in skipped)
            files.extend(Path(folder) / name for name in sorted(names))
        return files
    return [root / os.fsdecode(name) for name in result.stdout.split(b"\0") if name]


def action_file(path, root):
    try:
        relative = path.absolute().relative_to(root.absolute())
    except ValueError:
        return False
    return (
        relative.parent == Path(".github/workflows") and relative.suffix in {".yml", ".yaml"}
    ) or (
        relative.parts[:2] == (".github", "actions")
        and relative.name in {"action.yml", "action.yaml"}
    )


def actions_pinned(files, root):
    """Require one-line uses declarations with immutable remote pins and release comments."""
    violations = []
    for path in files:
        if not action_file(path, root):
            continue
        display = path.relative_to(root).as_posix() if path.is_relative_to(root) else str(path)
        if path.is_symlink():
            violations.append(Violation(display, 1, "actions-pinned", "Use a regular action file"))
            continue
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except (OSError, UnicodeError):
            violations.append(Violation(display, 1, "actions-pinned", "Cannot read action file"))
            continue
        block_indent = None
        for number, line in enumerate(lines, 1):
            stripped = line.lstrip()
            if not stripped or stripped.startswith("#"):
                continue
            indent = len(line) - len(stripped)
            if block_indent is not None:
                if indent > block_indent:
                    continue  # Shell/script block contents are not action declarations.
                block_indent = None
            match = _USES.match(line)
            if match:
                scalar = _SCALAR.fullmatch(match[1])
                if scalar is None:
                    message = (
                        "Use a single-line plain or quoted uses value and trailing release comment"
                    )
                else:
                    reference = next(value for value in scalar.groups()[:3] if value is not None)
                    comment = scalar[4] or ""
                    if reference.startswith(("./", "docker://")):
                        continue
                    if _REMOTE.fullmatch(reference) and _RELEASE.match(comment):
                        continue
                    message = "Pin the remote action/workflow to a full 40-hex SHA with a # vX.Y.Z comment"
                violations.append(Violation(display, number, "actions-pinned", message))
            elif _FLOW.match(line) and _FLOW_USES.search(line):
                violations.append(
                    Violation(
                        display,
                        number,
                        "actions-pinned",
                        "Write uses on its own line; flow-style action declarations are unsupported",
                    )
                )
            elif _BLOCK.search(line):
                block_indent = indent + (2 if stripped.startswith("- ") else 0)
    return violations


RULES: dict[str, Callable[[list[Path], Path], list[Violation]]] = {
    "actions-pinned": actions_pinned,
}


def run(rules, files, root):
    return sorted(violation for name in rules for violation in RULES[name](files, root))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("files", nargs="*", type=Path)
    parser.add_argument("--rule", action="append", choices=sorted(RULES))
    parser.add_argument("--list", action="store_true", help="List implemented rules")
    args = parser.parse_args(argv)
    if args.list:
        print("\n".join(sorted(RULES)))
        return 0
    files = [path.absolute() for path in args.files] if args.files else tracked_files(ROOT)
    violations = run(args.rule or RULES, files, ROOT)
    for violation in violations:
        print(violation)
    return 1 if violations else 0


if __name__ == "__main__":
    raise SystemExit(main())
