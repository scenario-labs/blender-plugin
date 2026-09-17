# SPDX-License-Identifier: GPL-3.0-or-later

"""Regression tests for command compatibility and repository instruction limits."""

import importlib.util
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
        self.skill.write_text(
            "---\nname: example\ndescription: Use when testing.\n"
            'metadata:\n  claude-command: "example"\n---\n\nRun the task.\n'
        )
        (self.folder / "agents").mkdir()
        self.adapter = self.folder / "agents/claude-command.md"
        self.original = (
            '---\ndescription: Test command\nargument-hint: "<number>"\n'
            "disable-model-invocation: true\n---\n\n"
            "Read .agents/skills/example/SKILL.md.\nArguments: $ARGUMENTS\n"
        )
        self.adapter.write_text(self.original)
        self.policy = self.folder / "agents/openai.yaml"
        self.policy.write_text("policy:\n  allow_implicit_invocation: false\n")
        contracts = patch.dict(
            validator.COMMAND_CONTRACTS,
            {"example": {"argument-hint": "<number>", "explicit-only": True}},
            clear=True,
        )
        contracts.start()
        self.addCleanup(contracts.stop)
        assert not validator.check(self.root, sync=True)

    def test_valid_sync_is_idempotent(self) -> None:
        """Preserve source content and links on repeated syncs."""
        assert not validator.check(self.root)
        assert not validator.check(self.root, sync=True)
        assert self.adapter.read_text() == self.original

    def test_missing_or_changed_hints(self) -> None:
        """Reject loss of the command's original argument preview."""
        for value in ["", "argument-hint: wrong\n", "argument-hint: [number]\n"]:
            with self.subTest(value=value):
                self.adapter.write_text(self.original.replace('argument-hint: "<number>"\n', value))
                assert validator.check(self.root)

    def test_claude_guard_requires_boolean_true(self) -> None:
        """A deleted, false or quoted guard must not enable automatic invocation."""
        for value in [
            "",
            "disable-model-invocation: false\n",
            'disable-model-invocation: "true"\n',
        ]:
            with self.subTest(value=value):
                self.adapter.write_text(
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
        self.adapter.write_text(self.original.replace("disable-model-invocation: true\n", ""))
        self.policy.unlink()
        assert validator.check(self.root)

    def test_missing_adapter(self) -> None:
        """Do not fall back to SKILL.md when an adapter is required."""
        self.adapter.unlink()
        assert validator.check(self.root, sync=True)

    def test_missing_frontmatter(self) -> None:
        """Reject handwritten adapters without valid metadata."""
        for value in ["Read SKILL.md", "---\n[broken\n---\n", "---\n- item\n---\n"]:
            self.adapter.write_text(value)
            assert validator.check(self.root)

    def test_forwarding(self) -> None:
        """Require the correct canonical source and invocation arguments."""
        for old in [".agents/skills/example/SKILL.md", "Arguments: $ARGUMENTS"]:
            self.adapter.write_text(self.original.replace(old, "wrong"))
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
        assert target.resolve() == self.adapter.resolve()

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
