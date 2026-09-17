# /// script
# requires-python = ">=3.11"
# dependencies = [
#   "skills-ref @ git+https://github.com/agentskills/agentskills.git@69ef37e9424c0a7ea9dd2293b559e43ec8176379#subdirectory=skills-ref",
# ]
# ///
# SPDX-License-Identifier: GPL-3.0-or-later

"""Validate canonical skills and check or repair agent compatibility links."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from skills_ref import read_properties, validate


def skill_links(root: Path, folder: Path) -> dict[Path, Path]:
    """Resolve tool entry points from validated skill metadata."""
    metadata = read_properties(folder).metadata or {}
    links: dict[Path, Path] = {}
    for agent in ("claude", "cursor"):
        name = metadata.get(f"{agent}-command")
        if not name:
            continue
        path = Path(name)
        if path.is_absolute() or ".." in path.parts or not name.strip():
            message = f"{folder.name}: invalid {agent}-command path"
            raise ValueError(message)
        target = root / f".{agent}/commands/{name}.md"
        adapter = folder / "agents/claude-command.md"
        links[target] = adapter if agent == "claude" and adapter.is_file() else folder / "SKILL.md"
    if metadata.get("claude-command") and metadata.get("cursor-command"):
        links[root / f".cursor/commands/{metadata['cursor-command']}.md"] = (
            root / f".claude/commands/{metadata['claude-command']}.md"
        )
    return links or {root / ".claude/skills" / folder.name: folder}


def collect_links(root: Path) -> tuple[dict[Path, Path], list[str]]:
    """Reject invalid originals before deriving compatibility links."""
    errors: list[str] = []
    rulebook = root / "AGENTS.md"
    claude = root / "CLAUDE.md"
    if not claude.exists() and not claude.is_symlink():
        claude = root / ".claude/CLAUDE.md"
    if rulebook.is_symlink() or not rulebook.is_file():
        errors.append("AGENTS.md must be a regular canonical file")
    expected = {claude: rulebook}
    skills = root / ".agents/skills"
    for folder in sorted(skills.iterdir()) if skills.is_dir() else []:
        entry = folder / "SKILL.md"
        if folder.is_symlink() or not folder.is_dir() or entry.is_symlink() or not entry.is_file():
            errors.append(f"{folder.name}: expected a real skill directory and SKILL.md")
            continue
        problems = validate(folder)
        errors.extend(f"{folder.name}: {problem}" for problem in problems)
        if problems:
            continue
        try:
            links = skill_links(root, folder)
        except ValueError as error:
            errors.append(str(error))
            continue
        errors.extend(
            f"Duplicate command mapping: {path.relative_to(root)}"
            for path in links.keys() & expected.keys()
        )
        expected.update(links)
    return expected, errors


def check_link(root: Path, target: Path, source: Path, *, sync: bool) -> list[str]:
    """Repair only symlinks; handwritten compatibility files are never overwritten."""
    relative = os.path.relpath(source, target.parent)
    if target.is_symlink() and str(target.readlink()) == relative and target.exists():
        return []
    if target.exists() and not target.is_symlink():
        return [f"{target.relative_to(root)}: refusing to overwrite a regular file or directory"]
    if sync and source.exists():
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.is_symlink():
            target.unlink()
        target.symlink_to(relative)
        return []
    return [f"{target.relative_to(root)}: expected symlink to {relative}"]


def check(root: Path, *, sync: bool = False) -> list[str]:
    """Validate skills, canonical rulebook ownership and every compatibility entry."""
    expected, errors = collect_links(root)
    if errors:
        return errors
    for target, source in expected.items():
        errors.extend(check_link(root, target, source, sync=sync))
    for agent in ("claude", "cursor"):
        commands = root / f".{agent}/commands"
        entries = commands.rglob("*.md") if commands.is_dir() else []
        errors.extend(
            f"{path.relative_to(root)}: no canonical command mapping"
            for path in entries
            if path not in expected
        )
    native = root / ".claude/skills"
    entries = native.iterdir() if native.is_dir() else []
    errors.extend(
        f"{path.relative_to(root)}: no canonical skill mapping"
        for path in entries
        if path not in expected
    )
    return errors


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sync", action="store_true", help="Create or repair compatibility links")
    args = parser.parse_args()
    failures = check(Path(__file__).resolve().parents[2], sync=args.sync)
    sys.stdout.write(
        "\n".join(
            failures or ["Canonical agent instructions, skills and compatibility links are valid."]
        )
        + "\n"
    )
    raise SystemExit(bool(failures))
