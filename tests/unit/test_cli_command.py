# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Headless local MCP command, its startup banner and the client setups."""

import re
import tomllib
from pathlib import Path

from scenario.mcp.cli import CLI_COMMAND, cli_banner

ROOT = Path(__file__).resolve().parents[2]
URL = "http://127.0.0.1:9876/mcp"


def test_cli_registration_and_current_docs_agree():
    assert CLI_COMMAND.isidentifier()
    for path in ("README.md", "docs/USER_GUIDE.md"):
        text = (ROOT / path).read_text()
        assert f"--command {CLI_COMMAND}" in text
        assert "--command scenario-mcp" not in text


def test_banner_names_the_url():
    assert cli_banner(URL) == f"scenario-blender MCP server on {URL}"


def test_client_setups_carry_no_credential():
    service = (ROOT / "scenario/blender/mcp_service.py").read_text()
    snippets = service.split("def client_configs", 1)[1].split("\ndef ", 1)[0]
    docs = (ROOT / "docs/MCP.md").read_text().split("## Client setup", 1)[1].split("\n## ", 1)[0]
    for text in (snippets, docs):
        assert not re.search(r"(?i)authorization|bearer|--token|token_env", text)
    assert f"codex mcp add scenario-blender --url {URL}" in docs


def test_repository_codex_entry_names_only_the_server_and_stays_disabled():
    config = tomllib.loads((ROOT / ".codex/config.toml").read_text())
    server = config["mcp_servers"]["scenario-blender"]
    assert server == {"url": URL, "enabled": False, "required": False}
