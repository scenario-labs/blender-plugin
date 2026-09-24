# SPDX-License-Identifier: GPL-3.0-or-later

"""Regression tests for command compatibility and repository instruction limits."""

import importlib.util
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

SPEC = importlib.util.spec_from_file_location(
    "agent_validator", Path(__file__).with_name("validate-skills.py")
)
validator = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(validator)


class CommandValidationTests(unittest.TestCase):
    """Exercise broken user-facing behavior through the full validator."""

    def setUp(self) -> None:
        """Create a standalone command with explicit invocation and arguments."""
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        (self.root / "AGENTS.md").write_text("Repository instructions.\n")
        (self.root / "CLAUDE.md").symlink_to("AGENTS.md")
        self.folder = self.root / ".agents/skills/example"
        self.folder.mkdir(parents=True)
        self.skill = self.folder / "SKILL.md"
        self.original = (
            "---\nname: example\ndescription: Use when testing.\n"
            'argument-hint: "<number>"\ndisable-model-invocation: true\n'
            'metadata:\n  claude-command: "example"\n---\n\nRun the task: $ARGUMENTS\n'
        )
        self.skill.write_text(self.original)
        (self.folder / "agents").mkdir()
        self.policy = self.folder / "agents/openai.yaml"
        self.codex_config = (
            'interface:\n  short_description: "Run the example command"\n'
            '  default_prompt: "$example <number>"\n'
            "policy:\n  allow_implicit_invocation: false\n"
        )
        self.policy.write_text(self.codex_config)
        contracts = patch.dict(
            validator.COMMAND_CONTRACTS,
            {
                "example": {
                    "claude-command": "example",
                    "argument-hint": "<number>",
                    "explicit-only": True,
                    "codex-interface": True,
                }
            },
            clear=True,
        )
        contracts.start()
        self.addCleanup(contracts.stop)
        assert not validator.check(self.root, sync=True)

    def test_valid_sync_is_idempotent(self) -> None:
        """Preserve source content and links on repeated syncs."""
        assert not validator.check(self.root)
        assert not validator.check(self.root, sync=True)
        assert self.skill.read_text() == self.original

    def test_missing_or_changed_hints(self) -> None:
        """Reject loss of the command's original argument preview."""
        for value in ["", "argument-hint: wrong\n", "argument-hint: [number]\n"]:
            with self.subTest(value=value):
                self.skill.write_text(self.original.replace('argument-hint: "<number>"\n', value))
                assert validator.check(self.root)

    def test_claude_guard_requires_boolean_true(self) -> None:
        """A deleted, false or quoted guard must not enable automatic invocation."""
        for value in [
            "",
            "disable-model-invocation: false\n",
            'disable-model-invocation: "true"\n',
        ]:
            with self.subTest(value=value):
                self.skill.write_text(
                    self.original.replace("disable-model-invocation: true\n", value)
                )
                assert validator.check(self.root)

    def test_codex_guard_requires_boolean_false(self) -> None:
        """Reject absent, misplaced, malformed, quoted or enabled Codex guards."""
        for value in [
            "",
            "policy: {}\n",
            "policy: [",
            "policy: false\n",
            "policy:\n  allow_implicit_invocation: true\n",
            'policy:\n  allow_implicit_invocation: "false"\n',
            "interface:\n  allow_implicit_invocation: false\n",
        ]:
            with self.subTest(value=value):
                self.policy.write_text(value)
                assert validator.check(self.root)
        self.policy.unlink()
        assert validator.check(self.root)

    def test_both_guards_removed(self) -> None:
        """Prevent coupled deletions from silently redefining command behavior."""
        self.skill.write_text(self.original.replace("disable-model-invocation: true\n", ""))
        self.policy.unlink()
        assert validator.check(self.root)

    def test_codex_picker_metadata(self) -> None:
        """Detect missing, malformed or misrouted picker metadata."""
        for old, new in (
            ('  short_description: "Run the example command"\n', ""),
            ('"Run the example command"', '"  "'),
            ('"Run the example command"', "false"),
            ('  default_prompt: "$example <number>"\n', ""),
            ('"$example <number>"', '"$example-other <number>"'),
            ('"$example <number>"', "false"),
        ):
            with self.subTest(old=old, new=new):
                self.policy.write_text(self.codex_config.replace(old, new))
                assert validator.check(self.root)
        self.policy.write_text("interface: []\npolicy:\n  allow_implicit_invocation: false\n")
        assert validator.check(self.root)

    def test_implicit_command_still_requires_picker_metadata(self) -> None:
        """Picker checks also cover commands without an explicit-only guard."""
        validator.COMMAND_CONTRACTS["example"] = {"codex-interface": True}
        self.skill.write_text(
            self.original.replace('argument-hint: "<number>"\n', "").replace(
                "disable-model-invocation: true\n", ""
            )
        )
        self.policy.write_text(
            'interface:\n  short_description: "Run the example command"\n'
            '  default_prompt: "$example"\n'
        )
        assert not validator.check(self.root, sync=True)
        self.policy.unlink()
        assert validator.check(self.root)

    def test_missing_canonical_command(self) -> None:
        """Reject a deleted original, even when its compatibility link is removed."""
        self.skill.unlink()
        (self.root / ".claude/commands/example.md").unlink()
        assert validator.check(self.root, sync=True)

    def test_legacy_adapter(self) -> None:
        """Reject wrappers that create a second source for command behavior."""
        (self.folder / "agents/claude-command.md").write_text("Read SKILL.md")
        assert validator.check(self.root)

    def test_missing_frontmatter(self) -> None:
        """Reject originals without valid metadata."""
        for value in ["Read SKILL.md", "---\n[broken\n---\n", "---\n- item\n---\n"]:
            self.skill.write_text(value)
            assert validator.check(self.root)

    def test_direct_relative_links_follow_canonical_edits(self) -> None:
        """Both command platforms read the same original without a wrapper hop."""
        self.skill.write_text(
            self.original.replace(
                '  claude-command: "example"',
                '  claude-command: "example"\n  cursor-command: "nested/example"',
            )
        )
        assert not validator.check(self.root, sync=True)
        self.skill.write_text(self.skill.read_text() + "Updated instructions.\n")
        for agent, name in (("claude", "example"), ("cursor", "nested/example")):
            target = self.root / f".{agent}/commands/{name}.md"
            assert target.is_symlink()
            assert not target.readlink().is_absolute()
            assert target.readlink() == Path(os.path.relpath(self.skill, target.parent))
            assert target.read_text() == self.skill.read_text()
        assert not validator.check(self.root)

    def test_command_mapping_cannot_disappear(self) -> None:
        """Deleting or renaming a contract's command must not silently pass sync."""
        for value in ["", '  claude-command: "renamed"\n']:
            self.skill.write_text(self.original.replace('  claude-command: "example"\n', value))
            assert validator.check(self.root, sync=True)

    def test_standard_metadata_is_still_validated(self) -> None:
        """Local command exceptions must not weaken standard skill metadata."""
        for old, new in (
            ("name: example", "name: wrong"),
            ("description: Use when testing.", "description: false"),
            ("description: Use when testing.", "description: ''"),
            ("metadata:", "unknown-field: true\nmetadata:"),
            ('claude-command: "example"', "claude-command: false"),
        ):
            with self.subTest(new=new):
                self.skill.write_text(self.original.replace(old, new))
                assert validator.check(self.root)

    def test_native_skills_remain_strict(self) -> None:
        """Only registered commands accept the two Claude extension fields."""
        folder = self.root / ".agents/skills/native-example"
        folder.mkdir()
        skill = folder / "SKILL.md"
        content = "---\nname: native-example\ndescription: Native skill.\n---\nInstructions.\n"
        skill.write_text(content)
        assert not validator.check(self.root, sync=True)
        assert (self.root / ".claude/skills/native-example").resolve() == folder.resolve()
        for extension in ("argument-hint: value", "disable-model-invocation: true"):
            skill.write_text(
                content.replace(
                    "description: Native skill.", extension + "\ndescription: Native skill."
                )
            )
            assert validator.check(self.root)

    def test_regular_commands_are_preserved(self) -> None:
        """Sync refuses to overwrite a user's regular command file."""
        target = self.root / ".claude/commands/example.md"
        target.unlink()
        target.write_text("User content")
        assert validator.check(self.root, sync=True)
        assert target.read_text() == "User content"

    def test_dangling_links_are_repaired(self) -> None:
        """Check detects a broken link and sync restores its target."""
        target = self.root / ".claude/commands/example.md"
        target.unlink()
        target.symlink_to("missing.md")
        assert validator.check(self.root)
        assert not validator.check(self.root, sync=True)
        assert target.resolve() == self.skill.resolve()

    def test_canonical_frontmatter_and_symlinks(self) -> None:
        """Reject originals without frontmatter or replaced by file symlinks."""
        original = self.skill.read_text()
        self.skill.write_text("Instructions without frontmatter")
        assert validator.check(self.root)
        other = self.root / "source.md"
        other.write_text(original)
        self.skill.unlink()
        self.skill.symlink_to(other)
        assert validator.check(self.root)

    def test_instruction_budget(self) -> None:
        """Measure UTF-8 bytes and honor the repository's configured allowance."""
        rulebook = self.root / "AGENTS.md"
        rulebook.write_text("é" * 16384, encoding="utf-8")
        assert not validator.check(self.root)
        rulebook.write_text("é" * 16385, encoding="utf-8")
        assert validator.check(self.root)
        config = self.root / ".codex/config.toml"
        config.parent.mkdir()
        config.write_text("project_doc_max_bytes = 65536\n")
        assert not validator.check(self.root)
