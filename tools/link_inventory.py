# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Write a lychee input list from tracked and nonignored authored Markdown."""

import argparse
import os
import subprocess
import sys
from pathlib import Path


def markdown_inputs(root):
    """Resolve repository adapters once; never scan ignored or external targets."""
    root = Path(root).resolve()
    result = subprocess.run(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard", "-z"],
        cwd=root,
        capture_output=True,
        check=True,
    )
    inventory = {root / os.fsdecode(name) for name in result.stdout.split(b"\0") if name}
    inputs = set()
    for path in inventory:
        relative = path.relative_to(root)
        if path.suffix.lower() != ".md":
            continue
        target = path.resolve(strict=True)
        if not target.is_relative_to(root) or target not in inventory or not target.is_file():
            raise ValueError(f"Markdown target is outside the proposed file inventory: {relative}")
        if target.suffix.lower() != ".md":
            raise ValueError(f"Markdown adapter target is not Markdown: {relative}")
        relative = target.relative_to(root)
        # Release automation owns root CHANGELOG.md, including GitHub issue/PR
        # links that redirect by design. Do not weaken authored-link checks.
        if relative == Path("CHANGELOG.md"):
            continue
        name = relative.as_posix()
        if "\n" in name or "\r" in name:
            raise ValueError("Markdown filenames must fit one lychee input-list line")
        inputs.add("./" + name)
    if not inputs:
        raise ValueError("No Markdown inputs found")
    return sorted(inputs)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        inputs = markdown_inputs(Path.cwd())
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text("\n".join(inputs) + "\n", encoding="utf-8")
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        print(f"Link inventory failed: {error}", file=sys.stderr)
        return 1
    print(f"Selected {len(inputs)} Markdown inputs.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
