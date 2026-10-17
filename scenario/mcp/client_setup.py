# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Write the scenario-blender entry into an MCP client's own configuration file. No bpy.

Only the scenario-blender entry is added or replaced; every other server and
setting is kept. The previous file is copied beside it first, and the new one
replaces it in one step. A file that cannot be parsed, or whose entry cannot be
replaced safely, is left untouched.
"""

import datetime as dt
import json
import os
import secrets
import shutil
import stat
import sys
import tomllib
from dataclasses import dataclass
from pathlib import Path

SERVER_NAME = "scenario-blender"


class SetupError(Exception):
    """The client configuration was left as it was."""


@dataclass(frozen=True)
class Client:
    key: str
    label: str
    path: Path
    folder: Path  # the client's own folder: present only once the client has run
    fmt: str  # "json" or "toml"
    reload_hint: str

    @property
    def detected(self):
        return self.path.is_file() or self.folder.is_dir()


def clients(home, environ=None, platform=None):
    """Every supported client and where its user configuration lives on this system."""
    home = Path(home)
    environ = os.environ if environ is None else environ
    platform = sys.platform if platform is None else platform
    codex = Path(environ.get("CODEX_HOME") or home / ".codex")
    if platform == "darwin":
        desktop = home / "Library" / "Application Support" / "Claude"
    elif platform.startswith("win"):
        desktop = Path(environ.get("APPDATA") or home / "AppData" / "Roaming") / "Claude"
    else:
        desktop = Path(environ.get("XDG_CONFIG_HOME") or home / ".config") / "Claude"
    return (
        Client(
            "claude_code",
            "Claude Code",
            home / ".claude.json",
            home / ".claude",
            "json",
            "run /mcp or start a new session",
        ),
        Client(
            "codex",
            "Codex",
            codex / "config.toml",
            codex,
            "toml",
            "start a new Codex session",
        ),
        Client(
            "cursor",
            "Cursor",
            home / ".cursor" / "mcp.json",
            home / ".cursor",
            "json",
            "restart Cursor",
        ),
        Client(
            "claude_desktop",
            "Claude Desktop",
            desktop / "claude_desktop_config.json",
            desktop,
            "json",
            "restart Claude Desktop",
        ),
    )


def entry(key, url, python=None, shim=None):
    """The server entry in the client's own format."""
    if key == "claude_code":
        return {"type": "http", "url": url}
    if key in ("cursor", "codex"):
        return {"url": url}
    if key == "claude_desktop":
        # Claude Desktop starts local servers over stdio; the bundled shim relays to HTTP.
        return {"command": python, "args": [shim, "--url", url]}
    raise ValueError(f"Unknown client {key!r}")


def merge_json(text, server):
    """The file with mcpServers.scenario-blender set to server, other keys kept in order."""
    try:
        data = json.loads(text) if text.strip() else {}
    except json.JSONDecodeError as error:
        raise SetupError(f"not valid JSON (line {error.lineno}); fix or edit it by hand") from None
    if not isinstance(data, dict):
        raise SetupError("its top level is not a JSON object")
    servers = data.setdefault("mcpServers", {})
    if not isinstance(servers, dict):
        raise SetupError("its mcpServers value is not an object")
    servers[SERVER_NAME] = server
    return json.dumps(data, indent=2, ensure_ascii=False) + "\n"


def _toml_string(value):
    return json.dumps(value, ensure_ascii=False)  # a TOML basic string for these values


def _table_name(line):
    """The table a [header] line opens, as a tuple of keys, or None."""
    stripped = line.strip()
    if not stripped.startswith("[") or stripped.startswith("[["):
        return None
    try:
        header = stripped[: stripped.index("]") + 1]
        probe = tomllib.loads(f"{header}\n")
    except (ValueError, tomllib.TOMLDecodeError):
        return None
    keys = []
    while isinstance(probe, dict) and len(probe) == 1:
        key, probe = next(iter(probe.items()))
        keys.append(key)
    return tuple(keys)


def merge_toml(text, server):
    """The file with [mcp_servers.scenario-blender] replaced by server, other text unchanged."""
    try:
        before = tomllib.loads(text)
    except tomllib.TOMLDecodeError as error:
        raise SetupError(f"not valid TOML ({error}); fix or edit it by hand") from None
    servers = before.get("mcp_servers", {})
    if not isinstance(servers, dict):
        raise SetupError("its mcp_servers value is not a table")
    ours = ("mcp_servers", SERVER_NAME)
    kept, skipping = [], False
    for line in text.splitlines(keepends=True):
        name = _table_name(line)
        if name is not None:
            skipping = name[:2] == ours
        if not skipping:
            kept.append(line)
    body = "".join(kept).rstrip("\n")
    block = f"[mcp_servers.{SERVER_NAME}]\nurl = {_toml_string(server['url'])}\n"
    result = (body + "\n\n" if body else "") + block
    try:
        after = tomllib.loads(result)
    except tomllib.TOMLDecodeError:
        after = None
    expected = dict(before)
    expected["mcp_servers"] = dict(servers, **{SERVER_NAME: server})
    if after != expected:
        raise SetupError(
            f"its {SERVER_NAME} entry is not a plain [mcp_servers.{SERVER_NAME}] table; "
            "edit it by hand"
        )
    return result


@dataclass(frozen=True)
class Written:
    client: Client
    path: Path
    backup: Path | None
    url: str


def _write_atomic(path, data, mode):
    temporary = path.with_name(f".{path.name}.{secrets.token_hex(4)}.tmp")
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0)
    descriptor = os.open(temporary, flags, mode)
    try:
        with os.fdopen(descriptor, "wb") as target:
            target.write(data)
            target.flush()
            os.fsync(target.fileno())
        if os.name == "posix":
            os.chmod(temporary, mode)  # the umask may have narrowed it
        os.replace(temporary, path)
    except BaseException:
        try:
            os.unlink(temporary)
        except OSError:
            pass  # best effort: the original failure is the one to report
        raise


def write(client, server, url, now=None):
    """Add or replace the entry in the client's file, keeping a copy of the previous file."""
    if not client.detected:
        raise SetupError(f"{client.label} was not found on this computer")
    # A linked configuration (a dotfiles repository, for example) is updated where it lives.
    path = Path(os.path.realpath(client.path))
    try:
        original = path.read_bytes() if path.exists() else None
    except OSError as error:
        raise SetupError(f"could not read it ({error.strerror or error})") from None
    if original is not None and not path.is_file():
        raise SetupError("it is not a regular file")
    try:
        text = original.decode("utf-8-sig") if original is not None else ""
    except UnicodeDecodeError:
        raise SetupError("it is not UTF-8 text") from None
    merged = merge_toml(text, server) if client.fmt == "toml" else merge_json(text, server)
    backup = None
    mode = 0o600
    if original is not None:
        mode = stat.S_IMODE(path.stat().st_mode)
        stamp = (now or dt.datetime.now()).strftime("%Y%m%d-%H%M%S")
        backup = path.with_name(f"{path.name}.scenario-backup-{stamp}")
        if backup.exists():
            backup = path.with_name(f"{backup.name}-{secrets.token_hex(2)}")
        shutil.copy2(path, backup)  # keeps the previous file's permissions
    else:
        path.parent.mkdir(parents=True, exist_ok=True)
    _write_atomic(path, merged.encode("utf-8"), mode)
    return Written(client, path, backup, url)
