# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Explicit local MCP credentials and safe startup reporting."""

import tomllib
from pathlib import Path

import pytest

from scenario.mcp.cli import CLI_COMMAND, cli_banner, resolve_cli_token
from tools.dev_config import local_mcp_token

ROOT = Path(__file__).resolve().parents[2]


def test_cli_registration_and_current_docs_agree():
    assert CLI_COMMAND.isidentifier()
    for path in ("README.md", "docs/USER_GUIDE.md"):
        text = (ROOT / path).read_text()
        assert f"--command {CLI_COMMAND}" in text
        assert "--command scenario-mcp" not in text


def test_clients_cli_and_repository_codex_helper_share_one_token_variable():
    variable = "SCENARIO_BLENDER_TOKEN"
    assert resolve_cli_token(None, {variable: "shared-name"}) == ("shared-name", False)
    assert local_mcp_token({variable: "shared-name"}) == "shared-name"
    docs = (ROOT / "docs/MCP.md").read_text()
    snippet = (ROOT / "scenario/blender/mcp_service.py").read_text()
    for text in (docs, snippet):
        assert f"--bearer-token-env-var {variable}" in text
        assert f"export {variable}=" in text
    assert f'bearer_token_env_var = "{variable}"' in docs
    assert f"\n# {variable}=\n" in (ROOT / ".env.example").read_text()


def test_repository_codex_entry_loads_the_token_through_the_helper_and_stays_disabled():
    config = tomllib.loads((ROOT / ".codex/config.toml").read_text())
    server = config["mcp_servers"]["scenario-blender"]
    assert server["enabled"] is False
    # A bearer_token_env_var would take precedence over the helper's Authorization header.
    assert "bearer_token_env_var" not in server
    helper = server["http_headers_helper"]
    assert helper == "uv run --locked --env-file .env.local python -m tools.codex_mcp_auth"
    assert helper in (ROOT / "docs/MCP.md").read_text()


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
