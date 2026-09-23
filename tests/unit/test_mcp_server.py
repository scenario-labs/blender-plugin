# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Local MCP browser-origin and explicit bearer-token boundaries."""

import ast
from pathlib import Path

import pytest

from scenario.mcp import server


@pytest.mark.parametrize(
    "origin",
    [
        None,
        "http://127.0.0.1:39876",
        "http://localhost:9876",
        "http://LOCALHOST:9876",
        "http://[::1]:9876",
        "https://localhost",
    ],
)
def test_native_and_loopback_origins(origin):
    assert server.origin_allowed(origin)


@pytest.mark.parametrize(
    "origin",
    [
        "https://evil.example",
        "null",
        "",
        "127.0.0.1:9876",
        "http://127.0.0.1.evil.example",
        "ftp://localhost",
        "http://user@localhost",
        "http://localhost/path",
        "http://localhost?x=1",
        "http://localhost#fragment",
        "http://[::1",
        "http://localhost:65536",
        "http://localhost:bad",
        "http://localhost https://evil.example",
        " http://localhost",
        "http://local\nhost",
    ],
)
def test_non_origin_and_non_loopback_values_are_rejected(origin):
    assert not server.origin_allowed(origin)


@pytest.mark.parametrize(
    "header,token,expected",
    [
        ("Bearer tok", "tok", True),
        ("Bearer tok ", "tok", True),
        ("Basic tok", "tok", False),
        ("Bearer wrong", "tok", False),
        ("", "tok", False),
        ("Bearer tök", "tok", False),
        ("Bearer ", "", False),
    ],
)
def test_explicit_bearer_token(header, token, expected):
    assert server.token_matches(header, token) is expected


def test_server_cannot_start_without_an_explicit_token():
    with pytest.raises(ValueError, match="nonempty"):
        server.McpServer("127.0.0.1", 9876, "", None, {})


def test_no_insecure_temporary_path_calls():
    root = Path(__file__).resolve().parents[2] / "scenario"
    offenders = []
    for path in root.rglob("*.py"):
        for node in ast.walk(ast.parse(path.read_text())):
            if (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Attribute)
                and node.func.attr == "mktemp"
            ):
                offenders.append(str(path.relative_to(root)))
    assert offenders == []
