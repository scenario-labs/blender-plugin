# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Connect writes the scenario-blender entry into client configs in temporary homes."""

import datetime as dt
import json
import os
import stat
import tomllib

import pytest

from scenario.mcp import client_setup as setup

URL, TOKEN = "http://127.0.0.1:9876/mcp", "fixture-token-0123456789"
NOW = dt.datetime(2026, 10, 17, 9, 30, 0)
POSIX = os.name == "posix"


def by_key(home, **kwargs):
    kwargs.setdefault("environ", {})
    kwargs.setdefault("platform", "darwin")
    return {client.key: client for client in setup.clients(home, **kwargs)}


def connect(client, key=None):
    server = setup.entry(key or client.key, URL, TOKEN, "/blender/python3", "/ext/stdio_shim.py")
    return setup.write(client, server, URL, now=NOW)


def test_client_locations_follow_platform_and_environment(tmp_path):
    mac = by_key(tmp_path)
    assert mac["claude_code"].path == tmp_path / ".claude.json"
    assert mac["codex"].path == tmp_path / ".codex" / "config.toml"
    assert mac["cursor"].path == tmp_path / ".cursor" / "mcp.json"
    assert mac["claude_desktop"].path == (
        tmp_path / "Library" / "Application Support" / "Claude" / "claude_desktop_config.json"
    )
    custom = by_key(
        tmp_path,
        environ={"CODEX_HOME": str(tmp_path / "cx"), "XDG_CONFIG_HOME": str(tmp_path / "xdg")},
        platform="linux",
    )
    assert custom["codex"].path == tmp_path / "cx" / "config.toml"
    assert (
        custom["claude_desktop"].path == tmp_path / "xdg" / "Claude" / "claude_desktop_config.json"
    )
    windows = by_key(tmp_path, environ={"APPDATA": str(tmp_path / "roaming")}, platform="win32")
    assert windows["claude_desktop"].folder == tmp_path / "roaming" / "Claude"


def test_only_clients_that_have_run_are_detected_and_others_are_never_created(tmp_path):
    clients = by_key(tmp_path)
    assert not any(client.detected for client in clients.values())
    with pytest.raises(setup.SetupError, match="not found"):
        connect(clients["cursor"])
    assert list(tmp_path.iterdir()) == []
    (tmp_path / ".cursor").mkdir()
    (tmp_path / ".claude.json").write_text("{}")
    detected = {key for key, client in by_key(tmp_path).items() if client.detected}
    assert detected == {"cursor", "claude_code"}


def test_claude_code_entry_is_added_beside_other_servers_and_settings(tmp_path):
    path = tmp_path / ".claude.json"
    previous = {"numStartups": 3, "mcpServers": {"other": {"type": "stdio", "command": "x"}}}
    path.write_text(json.dumps(previous))
    if POSIX:
        path.chmod(0o600)
    written = connect(by_key(tmp_path)["claude_code"])
    data = json.loads(path.read_text())
    assert data["numStartups"] == 3
    assert data["mcpServers"]["other"] == previous["mcpServers"]["other"]
    assert data["mcpServers"]["scenario-blender"] == {
        "type": "http",
        "url": URL,
        "headers": {"Authorization": f"Bearer {TOKEN}"},
    }
    assert written.backup == tmp_path / ".claude.json.scenario-backup-20261017-093000"
    assert json.loads(written.backup.read_text()) == previous
    if POSIX:
        assert stat.S_IMODE(path.stat().st_mode) == 0o600
        assert stat.S_IMODE(written.backup.stat().st_mode) == 0o600


def test_connecting_again_replaces_the_entry_and_keeps_a_distinct_backup(tmp_path):
    (tmp_path / ".cursor").mkdir()
    cursor = by_key(tmp_path)["cursor"]
    first = connect(cursor)
    assert first.backup is None  # nothing to keep: the file is new
    data = json.loads(cursor.path.read_text())
    assert data == {
        "mcpServers": {
            "scenario-blender": {"url": URL, "headers": {"Authorization": f"Bearer {TOKEN}"}}
        }
    }
    second = connect(cursor)
    third = connect(cursor)
    assert second.backup != third.backup and second.backup.exists() and third.backup.exists()
    assert json.loads(cursor.path.read_text()) == data


def test_claude_desktop_entry_runs_the_stdio_shim(tmp_path):
    folder = tmp_path / "Library" / "Application Support" / "Claude"
    folder.mkdir(parents=True)
    connect(by_key(tmp_path)["claude_desktop"])
    entry = json.loads((folder / "claude_desktop_config.json").read_text())["mcpServers"][
        "scenario-blender"
    ]
    assert entry == {
        "command": "/blender/python3",
        "args": ["/ext/stdio_shim.py", "--url", URL, "--token", TOKEN],
    }


def test_codex_table_is_replaced_and_the_rest_of_the_file_kept_verbatim(tmp_path):
    folder = tmp_path / ".codex"
    folder.mkdir()
    original = (
        '# my settings\nmodel = "gpt-x"\n\n'
        '[mcp_servers.scenario-blender]\nurl = "http://127.0.0.1:1/mcp"\n'
        'bearer_token_env_var = "SCENARIO_BLENDER_TOKEN"\n\n'
        '[mcp_servers.scenario-blender.env]\nA = "1"\n\n'
        '[mcp_servers.other]\ncommand = "other"  # keep me\n'
    )
    (folder / "config.toml").write_text(original)
    written = connect(by_key(tmp_path)["codex"])
    text = (folder / "config.toml").read_text()
    data = tomllib.loads(text)
    assert data["model"] == "gpt-x"
    assert data["mcp_servers"]["other"] == {"command": "other"}
    assert data["mcp_servers"]["scenario-blender"] == {
        "url": URL,
        "http_headers": {"Authorization": f"Bearer {TOKEN}"},
    }
    assert text.startswith('# my settings\nmodel = "gpt-x"\n')
    assert 'command = "other"  # keep me' in text
    assert written.backup.read_text() == original


def test_codex_file_without_the_table_gets_it_appended(tmp_path):
    folder = tmp_path / ".codex"
    folder.mkdir()
    connect(by_key(tmp_path)["codex"])
    data = tomllib.loads((folder / "config.toml").read_text())
    assert list(data) == ["mcp_servers"]


@pytest.mark.parametrize(
    ("key", "name", "content", "message"),
    [
        ("cursor", ".cursor/mcp.json", "{ // comment\n}", "not valid JSON"),
        ("cursor", ".cursor/mcp.json", "[]", "not a JSON object"),
        ("cursor", ".cursor/mcp.json", '{"mcpServers": []}', "mcpServers value"),
        ("codex", ".codex/config.toml", "model = ", "not valid TOML"),
        (
            "codex",
            ".codex/config.toml",
            'mcp_servers = { scenario-blender = { url = "x" } }\n',
            "edit it by hand",
        ),
        (
            "codex",
            ".codex/config.toml",
            '[mcp_servers]\nscenario-blender.url = "x"\n',
            "edit it by hand",
        ),
    ],
)
def test_files_that_cannot_be_merged_safely_are_left_untouched(
    tmp_path, key, name, content, message
):
    path = tmp_path / name
    path.parent.mkdir()
    path.write_text(content)
    with pytest.raises(setup.SetupError, match=message):
        connect(by_key(tmp_path)[key])
    assert path.read_text() == content
    assert sorted(p.name for p in path.parent.iterdir()) == [path.name]


@pytest.mark.skipif(not POSIX, reason="symbolic links")
def test_a_linked_config_is_updated_where_it_lives(tmp_path):
    dotfiles = tmp_path / "dotfiles"
    dotfiles.mkdir()
    target = dotfiles / "claude.json"
    target.write_text("{}")
    (tmp_path / ".claude.json").symlink_to(target)
    connect(by_key(tmp_path)["claude_code"])
    assert (tmp_path / ".claude.json").is_symlink()
    assert "scenario-blender" in json.loads(target.read_text())["mcpServers"]
