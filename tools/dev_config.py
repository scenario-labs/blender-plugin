# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Explicit live-tool configuration. uv owns dotenv loading; never log values."""

import os
from dataclasses import dataclass, field

from scenario.core.config import Credentials
from scenario.mcp.cli import resolve_cli_token


@dataclass(frozen=True)
class LiveSettings:
    credentials: Credentials = field(repr=False)
    project_id: str | None = field(default=None, repr=False)


def live_settings(environ=None):
    environ = os.environ if environ is None else environ
    credentials = Credentials(
        (environ.get("SCENARIO_TEST_API_KEY") or "").strip(),
        (environ.get("SCENARIO_TEST_API_SECRET") or "").strip(),
    )
    if not credentials.valid:
        raise SystemExit(
            "no test credentials: export SCENARIO_TEST_API_KEY and SCENARIO_TEST_API_SECRET, "
            "or copy .env.example to .env.local and run with uv run --locked --env-file .env.local"
        )
    project_id = (environ.get("SCENARIO_TEST_PROJECT_ID") or "").strip() or None
    return LiveSettings(credentials, project_id)


def local_mcp_token(environ=None):
    """The local Blender MCP bearer token, separate from Scenario credentials."""
    environ = os.environ if environ is None else environ
    token = (environ.get("SCENARIO_BLENDER_TOKEN") or "").strip()
    if not token:
        raise SystemExit(
            "no local MCP token: set SCENARIO_BLENDER_TOKEN in .env.local to the token "
            "in Blender's Codex setup (Scenario > Agents (MCP))"
        )
    try:
        resolve_cli_token(token)
    except ValueError as error:
        raise SystemExit(f"malformed local MCP token: {error}") from None
    return token
