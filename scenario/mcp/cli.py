# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Pure helpers for explicit local MCP CLI credentials (not Scenario API auth)."""

import os
import secrets

CLI_COMMAND = "scenario_blender"


def resolve_cli_token(argument=None, environ=None):
    """Explicit flag wins over environment; only absent inputs generate a token."""
    environ = os.environ if environ is None else environ
    token = argument if argument is not None else environ.get("SCENARIO_BLENDER_TOKEN")
    generated = token is None
    if generated:
        token = secrets.token_urlsafe(24)
    if not isinstance(token, str) or not token or any(not 33 <= ord(c) <= 126 for c in token):
        raise ValueError("The local MCP token must be nonempty printable ASCII without spaces")
    return token, generated


def cli_banner(url, token, generated):
    """Only newly generated credentials need bootstrap display; mask supplied ones."""
    shown = token if generated else "provided; hidden"
    return f"scenario-blender MCP server on {url} (token {shown})"
