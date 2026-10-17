# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Codex headers helper: only the local MCP token, from uv dotenv loading, with dummy values."""

import http.client
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from scenario.mcp import protocol, server
from tools import codex_mcp_auth

ROOT = Path(__file__).resolve().parents[2]


def helper_env(**values):
    env = {
        k: v
        for k, v in os.environ.items()
        if not k.startswith(("SCENARIO_", "UV_ENV", "UV_NO_ENV"))
    }
    env.update(values)
    return env


def run_helper(dotenv, env, *args):
    # uv exports UV, its own path, to the commands it runs; keep the pinned uv.
    command = [os.environ.get("UV", "uv"), "run", "--locked", "--offline"]
    command += ["--python", sys.executable, "--env-file", str(dotenv)]
    command += ["python", "-m", "tools.codex_mcp_auth", *args]
    return subprocess.run(command, cwd=ROOT, env=env, capture_output=True, text=True)


def header(result):
    assert result.returncode == 0, result.stderr
    assert result.stdout.count("\n") == 1
    return json.loads(result.stdout)


def test_header_carries_only_the_local_mcp_token(capsys):
    environ = {"SCENARIO_BLENDER_TOKEN": " dummy-token ", "SCENARIO_TEST_API_KEY": "unrelated"}
    codex_mcp_auth.main([], environ)
    out, err = capsys.readouterr()
    assert json.loads(out) == {"Authorization": "Bearer dummy-token"}
    assert err == ""


@pytest.mark.parametrize(
    "environ", [{}, {"SCENARIO_BLENDER_TOKEN": ""}, {"SCENARIO_BLENDER_TOKEN": " "}]
)
def test_missing_or_empty_token_prints_no_header(environ, capsys):
    with pytest.raises(SystemExit, match="^no local MCP token: set SCENARIO_BLENDER_TOKEN"):
        codex_mcp_auth.main([], environ)
    assert capsys.readouterr().out == ""


@pytest.mark.parametrize(
    "token", ["dummy token", "Bearer dummy-token", "dummy\ntoken", "dümmy", "dummy\x7f"]
)
def test_malformed_token_is_refused_without_echoing_it(token, capsys):
    with pytest.raises(SystemExit) as error:
        codex_mcp_auth.main([], {"SCENARIO_BLENDER_TOKEN": token})
    assert str(error.value).startswith("malformed local MCP token:")
    assert "dummy" not in str(error.value) and "dümmy" not in str(error.value)
    assert capsys.readouterr().out == ""


def test_check_validates_without_printing_the_token(capsys):
    codex_mcp_auth.main(["--check"], {"SCENARIO_BLENDER_TOKEN": "dummy-token"})
    assert "dummy-token" not in capsys.readouterr().out


def test_dotenv_supplies_the_token_and_exported_values_take_precedence(tmp_path):
    dotenv = tmp_path / ".env.local"
    dotenv.write_text("SCENARIO_TEST_API_KEY=unrelated-key\nSCENARIO_BLENDER_TOKEN=file-token\n")
    assert header(run_helper(dotenv, helper_env())) == {"Authorization": "Bearer file-token"}
    exported = run_helper(dotenv, helper_env(SCENARIO_BLENDER_TOKEN="exported-token"))
    assert header(exported) == {"Authorization": "Bearer exported-token"}
    # As with every uv dotenv command, an exported empty value hides the file's value.
    empty = run_helper(dotenv, helper_env(SCENARIO_BLENDER_TOKEN=""))
    assert (empty.returncode, empty.stdout) == (1, "")
    assert empty.stderr.startswith("no local MCP token:")
    absent = run_helper(tmp_path / "absent.env", helper_env())
    assert absent.returncode != 0 and absent.stdout == ""
    for result in (exported, empty, absent):
        assert "file-token" not in result.stdout + result.stderr
        assert "unrelated-key" not in result.stdout + result.stderr


def test_stale_token_is_refused_until_dotenv_holds_the_restarted_session(tmp_path):
    """Codex reruns the helper after a 401 and retries only when the header changed."""
    dotenv = tmp_path / ".env.local"
    dotenv.write_text("SCENARIO_BLENDER_TOKEN=first-session\n")
    stale = header(run_helper(dotenv, helper_env()))
    mcp = server.McpServer(
        "127.0.0.1", 0, "second-session", protocol.Registry(), {"name": "fixture", "version": "0"}
    )
    mcp.start()
    try:
        port = mcp._httpd.server_port  # Port 0 asks the OS for a free one.

        def status(headers):
            connection = http.client.HTTPConnection("127.0.0.1", port, timeout=5)
            body = json.dumps({"jsonrpc": "2.0", "id": 1, "method": "tools/list"})
            connection.request(
                "POST", "/mcp", body, {"Content-Type": "application/json", **headers}
            )
            response = connection.getresponse()
            response.read()
            connection.close()
            return response.status

        assert status(stale) == 401
        assert header(run_helper(dotenv, helper_env())) == stale
        dotenv.write_text("SCENARIO_BLENDER_TOKEN=second-session\n")
        rotated = header(run_helper(dotenv, helper_env()))
        assert rotated == {"Authorization": "Bearer second-session"}
        assert status(rotated) == 200
    finally:
        mcp.stop()
