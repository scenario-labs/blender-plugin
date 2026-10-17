# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""The local MCP bearer token, saved once so client setups survive a Blender restart. No bpy.

The token lives in one file readable by the user only, inside the extension's
user data folder. It authorizes local agents only; it is not a Scenario credential.
"""

import os
import secrets
import stat

TOKEN_FILE = "mcp-token"
_MAX_BYTES = 256


def valid(token):
    """Printable ASCII without spaces, as Authorization headers carry it."""
    return (
        isinstance(token, str)
        and 16 <= len(token) <= 200
        and all(33 <= ord(c) <= 126 for c in token)
    )


def _path(directory):
    os.makedirs(directory, mode=0o700, exist_ok=True)
    return os.path.join(os.fspath(directory), TOKEN_FILE)


def _read(path):
    """The saved token, or None when the file is missing or holds no valid token."""
    if os.path.islink(path):
        raise OSError(f"{TOKEN_FILE} must be a regular file, not a link; remove it to start over")
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0)
    try:
        descriptor = os.open(path, flags)
    except FileNotFoundError:
        return None
    with os.fdopen(descriptor, "rb") as source:
        info = os.fstat(source.fileno())
        if not stat.S_ISREG(info.st_mode):
            raise OSError(f"{TOKEN_FILE} must be a regular file; remove it to start over")
        if os.name == "posix" and info.st_mode & 0o077:
            os.fchmod(source.fileno(), 0o600)  # an older or copied file: make it private
        data = source.read(_MAX_BYTES + 1)
    try:
        token = data.decode("ascii").strip()
    except UnicodeDecodeError:
        return None
    return token if valid(token) and len(data) <= _MAX_BYTES else None


def _write(path, token):
    """Write the token privately and replace the old file in one step."""
    temporary = f"{path}.{secrets.token_hex(4)}.tmp"
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0)
    descriptor = os.open(temporary, flags, 0o600)
    try:
        with os.fdopen(descriptor, "wb") as target:
            target.write(token.encode("ascii") + b"\n")
            target.flush()
            os.fsync(target.fileno())
        os.replace(temporary, path)
    except BaseException:
        try:
            os.unlink(temporary)
        except OSError:
            pass  # best effort: the original failure is the one to report
        raise


def load_or_create(directory):
    """The saved token; a new one is generated and saved when none is valid."""
    path = _path(directory)
    token = _read(path)
    if token is None:
        token = secrets.token_urlsafe(24)
        _write(path, token)
    return token


def replace(directory):
    """Save and return a new token; setups holding the previous one stop working."""
    path = _path(directory)
    _read(path)  # refuse a link or special file rather than replacing it
    token = secrets.token_urlsafe(24)
    _write(path, token)
    return token
