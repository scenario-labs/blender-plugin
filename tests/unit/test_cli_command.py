# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Explicit local MCP credentials and safe startup reporting."""

from pathlib import Path

import pytest

from scenario.mcp.cli import CLI_COMMAND, cli_banner, resolve_cli_token


def test_cli_registration_and_current_docs_agree():
    root = Path(__file__).resolve().parents[2]
    assert CLI_COMMAND.isidentifier()
    for path in ("README.md", "docs/USER_GUIDE.md"):
        text = (root / path).read_text()
        assert f"--command {CLI_COMMAND}" in text
        assert "--command scenario-mcp" not in text


def test_explicit_cli_token_wins_and_supplied_tokens_never_appear_in_banner():
    for argument, env, expected in [
        ("a", {"SCENARIO_BLENDER_TOKEN": "env"}, "a"),
        (None, {"SCENARIO_BLENDER_TOKEN": "environment-secret"}, "environment-secret"),
    ]:
        token, generated = resolve_cli_token(argument, env)
        assert token == expected
        assert not generated
        assert cli_banner("http://127.0.0.1:9876/mcp", token, generated).endswith(
            "(token provided; hidden)"
        )


def test_absent_credentials_generate_distinct_bootstrap_tokens():
    first, generated = resolve_cli_token(None, {})
    second, _ = resolve_cli_token(None, {})
    assert generated and first != second and len(first) >= 32
    assert first in cli_banner("http://127.0.0.1:9876/mcp", first, generated)


@pytest.mark.parametrize("token", ["", " ", "with space", "line\nbreak", "tök", "\x7f"])
def test_invalid_explicit_credentials_are_rejected(token):
    with pytest.raises(ValueError):
        resolve_cli_token(token, {"SCENARIO_BLENDER_TOKEN": "valid"})
    with pytest.raises(ValueError):
        resolve_cli_token(None, {"SCENARIO_BLENDER_TOKEN": token})
