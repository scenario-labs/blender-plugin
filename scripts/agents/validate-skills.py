# /// script
# requires-python = ">=3.11"
# dependencies = [
#   "PyYAML==6.0.2",
#   "skills-ref @ git+https://github.com/agentskills/agentskills.git@69ef37e9424c0a7ea9dd2293b559e43ec8176379#subdirectory=skills-ref",
# ]
# ///
# SPDX-License-Identifier: GPL-3.0-or-later

"""Validate canonical skills and check or repair agent compatibility links."""

from __future__ import annotations

import argparse
import os
import re
import sys
import tomllib
import unittest
from pathlib import Path

import yaml
from skills_ref import read_properties, validate

# Existing command behavior is independent of editable skill metadata: deleting
# a hint or invocation guard must fail validation rather than redefine it.
COMMAND_CONTRACTS: dict[str, dict] = {
    "blender-download-artifacts": {
        "argument-hint": "<prnumber>",
        "explicit-only": True,
        "codex-interface": True,
    },
    "blender-pr-summary": {"codex-interface": True},
    "blender-squash-message": {"codex-interface": True},
}


def check_instruction_budget(root: Path) -> list[str]:
    """Prevent canonical repository instructions from exceeding Codex's limit."""
    config_path = root / ".codex/config.toml"
    config = tomllib.loads(config_path.read_text()) if config_path.is_file() else {}
    limit = config.get("project_doc_max_bytes", 32768)
    if type(limit) is not int or limit <= 0:
        return ["project_doc_max_bytes must be a positive integer"]
    rulebook = root / "AGENTS.md"
    if rulebook.is_file() and rulebook.stat().st_size > limit:
        return [f"AGENTS.md exceeds project_doc_max_bytes ({limit} bytes)"]
    return []


def check_codex_policy(folder: Path, *, explicit: bool, required_interface: bool) -> list[str]:
    """Validate Codex picker metadata and explicit-only command guards."""
    config_path = folder / "agents/openai.yaml"
    if not explicit and not required_interface and not config_path.exists():
        return []
    config = yaml.safe_load(config_path.read_text())
    policy = config.get("policy", {}) if isinstance(config, dict) else None
    if not isinstance(policy, dict):
        return [f"{folder.name}: openai.yaml policy must be a mapping"]
    implicit = policy.get("allow_implicit_invocation", True)
    if type(implicit) is not bool or (explicit and implicit is not False):
        return [f"{folder.name}: invalid allow_implicit_invocation guard"]
    if required_interface:
        interface = config.get("interface")
        if not isinstance(interface, dict):
            return [f"{folder.name}: openai.yaml interface must be a mapping"]
        description = interface.get("short_description")
        prompt = interface.get("default_prompt")
        errors = []
        if not isinstance(description, str) or not description.strip():
            errors.append(f"{folder.name}: a Codex picker description is required")
        if not isinstance(prompt, str) or not re.search(
            rf"\${re.escape(folder.name)}(?![\w-])", prompt
        ):
            errors.append(f"{folder.name}: default_prompt must invoke ${folder.name}")
        return errors
    return []


def check_command_behavior(folder: Path) -> list[str]:
    """Check adapter arguments and preserve explicit invocation on both agents."""
    contract = COMMAND_CONTRACTS.get(folder.name, {})
    adapter = folder / "agents/claude-command.md"
    errors: list[str] = []
    explicit = contract.get("explicit-only", False)
    try:
        if contract.get("argument-hint") or explicit or adapter.exists():
            if adapter.is_symlink() or not adapter.is_file():
                return [f"{folder.name}: expected a regular Claude command adapter"]
            content = adapter.read_text()
            parts = content.split("---", 2)
            if not content.startswith("---\n") or len(parts) != 3:
                return [f"{folder.name}: adapter needs YAML frontmatter"]
            metadata = yaml.safe_load(parts[1])
            if not isinstance(metadata, dict):
                return [f"{folder.name}: adapter frontmatter must be a mapping"]
            description = metadata.get("description")
            if not isinstance(description, str) or not description.strip():
                errors.append(f"{folder.name}: adapter needs a description")
            hint = contract.get("argument-hint")
            if hint and metadata.get("argument-hint") != hint:
                errors.append(f"{folder.name}: argument-hint must be {hint}")
            guard = metadata.get("disable-model-invocation", False)
            if type(guard) is not bool or (explicit and guard is not True):
                errors.append(f"{folder.name}: invalid disable-model-invocation guard")
            explicit = explicit or guard is True
            reference = f".agents/skills/{folder.name}/SKILL.md"
            if reference not in parts[2] or "Arguments: $ARGUMENTS" not in parts[2]:
                errors.append(f"{folder.name}: adapter must forward instructions and arguments")
        errors.extend(
            check_codex_policy(
                folder,
                explicit=explicit,
                required_interface=contract.get("codex-interface", False),
            )
        )
    except (OSError, yaml.YAMLError) as error:
        errors.append(f"{folder.name}: invalid command configuration: {error}")
    return errors


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
        problems.extend(check_command_behavior(folder))
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
    errors.extend(check_instruction_budget(root))
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
    options = parser.add_mutually_exclusive_group()
    options.add_argument("--test", action="store_true", help="Run validator regression tests")
    options.add_argument("--sync", action="store_true", help="Create or repair compatibility links")
    args = parser.parse_args()
    if args.test:
        suite = unittest.defaultTestLoader.discover(
            str(Path(__file__).parent), pattern="test_validate_skills.py"
        )
        raise SystemExit(not unittest.TextTestRunner(verbosity=2).run(suite).wasSuccessful())
    failures = check(Path(__file__).resolve().parents[2], sync=args.sync)
    sys.stdout.write(
        "\n".join(
            failures or ["Canonical agent instructions, skills and compatibility links are valid."]
        )
        + "\n"
    )
    raise SystemExit(bool(failures))
