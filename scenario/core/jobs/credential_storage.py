# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Local API-key storage isolation, without claiming a server account identity."""

import hashlib
import hmac
import json
import os
import stat
import tempfile
from pathlib import Path

from ..api.sdk_adapter import API_URL, Credentials
from .store import JobScope, JobStore, StoreError

_HEADER = b"SCENARIO-LOCAL-SCOPE-v1\n"


def _read_key(path):
    # The parent remains caller-owned. O_NONBLOCK also prevents a replaced FIFO
    # from hanging startup; fstat validates the actual opened object.
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0)
    if path.is_symlink():
        raise StoreError("Local scope key must be a regular file; preserve it for recovery")
    with os.fdopen(os.open(path, flags), "rb") as source:
        if not stat.S_ISREG(os.fstat(source.fileno()).st_mode):
            raise StoreError("Local scope key must be a regular file; preserve it for recovery")
        data = source.read(len(_HEADER) + 33)
    if not data.startswith(_HEADER) or len(data) != len(_HEADER) + 32:
        raise StoreError("Local scope key is invalid; preserve it for recovery")
    return data[len(_HEADER) :]


def _scope_key(root, database):
    path = root / "scope.key"
    if not os.path.lexists(path):
        if os.path.lexists(database) and not os.path.lexists(path):
            raise StoreError("Local scope key is missing; preserve existing jobs for recovery")
        # Publish a complete key without replacing a competing process's key.
        # mkstemp requests 0600. The temporary name never becomes a job identity.
        descriptor, temporary = tempfile.mkstemp(prefix=".scope-", dir=root)
        try:
            with os.fdopen(descriptor, "wb") as output:
                output.write(_HEADER + os.urandom(32))
                output.flush()
                os.fsync(output.fileno())
            try:
                os.link(temporary, path)
            except FileExistsError:
                # Another process published scope.key; keep it and validate it below.
                pass
        finally:
            os.unlink(temporary)
    return _read_key(path)


def open_credential_store(root, credentials, *, service=API_URL, project_id=None, team_id=None):
    """Reopen this key pair's local jobs; never discover or select a remote tenant.

    The private root belongs under extension user data. Keep scope.key with the
    database in backups. This is isolation, not encryption or credential storage.
    """
    if not isinstance(credentials, Credentials) or credentials.bearer_token:
        raise ValueError("Local credential storage requires an explicit API-key pair")
    credentials.authorization()
    # Validate non-secret context before creating any files.
    JobScope(service, "local", project_id, team_id)
    try:
        root = Path(root).absolute()
        if root.is_symlink():
            raise StoreError("Local job storage must use a private directory")
        root.mkdir(mode=0o700, parents=True, exist_ok=True)
        root = root.resolve(strict=True)
        database = root / "jobs.sqlite3"
        key = _scope_key(root, database)
        payload = json.dumps(
            ["api-key-v1", service, credentials.api_key, credentials.api_secret],
            separators=(",", ":"),
        ).encode()
        identity = "local-key-" + hmac.new(key, payload, hashlib.sha256).hexdigest()
        return JobStore(database, JobScope(service, identity, project_id, team_id))
    except OSError:
        raise StoreError(
            "Local job storage is unavailable; preserve existing data for recovery"
        ) from None
