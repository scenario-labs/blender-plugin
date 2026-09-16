# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Atomic scoped intent storage for the shared runtime being adopted under #65.

No dispatch, network, Blender access or prototype migration. Callers provide an
extension-user-data path and stable, non-secret scope/origin identities.
"""

import hashlib
import json
import os
import re
import sqlite3
from contextlib import contextmanager
from dataclasses import asdict, dataclass
from decimal import Decimal, InvalidOperation
from enum import StrEnum
from pathlib import Path
from urllib.parse import urlsplit

_VERSION = 1
_APPLICATION_ID = 0x53434A42


class StoreError(RuntimeError):
    """Persistence failed; callers must stop before dispatching or applying."""


class StoreConflict(StoreError):
    """A request already exists, or another caller changed its revision."""


def _identity(value):
    if (
        not isinstance(value, str)
        or not value
        or len(value) > 256
        or any(char.isspace() or ord(char) < 32 for char in value)
        or any(char in value for char in "/\\?#")
    ):
        raise ValueError("Use a nonempty opaque identity, not a path, URL or credential")
    return value


@dataclass(frozen=True)
class JobScope:
    service: str
    account_id: str
    project_id: str | None = None
    team_id: str | None = None

    def __post_init__(self):
        if (
            not isinstance(self.service, str)
            or len(self.service) > 2048
            or any(char.isspace() or ord(char) < 32 for char in self.service)
        ):
            raise ValueError("Use a valid API base URL")
        url = urlsplit(self.service)
        if (
            url.scheme != "https"
            or not url.hostname
            or url.username
            or url.password
            or url.query
            or url.fragment
            or self.service != self.service.rstrip("/")
        ):
            raise ValueError("Use an HTTPS API base URL without secrets or a trailing slash")
        _identity(self.account_id)
        for value in (self.project_id, self.team_id):
            if value is not None:
                _identity(value)


@dataclass(frozen=True)
class JobOrigin:
    file_id: str
    scene_id: str
    revision: str
    target_id: str | None = None

    def __post_init__(self):
        for value in (self.file_id, self.scene_id, self.revision):
            _identity(value)
        if self.target_id is not None:
            _identity(self.target_id)


@dataclass(frozen=True)
class JobIntent:
    request_id: str
    scope: JobScope
    origin: JobOrigin
    operation: str
    target_id: str
    payload_sha256: str
    quote_sha256: str
    quote_cost: str

    def __post_init__(self):
        _identity(self.request_id)
        _identity(self.target_id)
        if not isinstance(self.scope, JobScope) or not isinstance(self.origin, JobOrigin):
            raise ValueError("A scope and origin are required")
        if not isinstance(self.operation, str) or self.operation not in {"model", "workflow"}:
            raise ValueError("Choose a model or workflow operation")
        for value in (self.payload_sha256, self.quote_sha256):
            if not isinstance(value, str) or not re.fullmatch(r"[0-9a-f]{64}", value):
                raise ValueError("Request and quote require SHA-256 identities")
        try:
            if not isinstance(self.quote_cost, str) or len(self.quote_cost) > 128:
                raise ValueError
            cost = Decimal(self.quote_cost)
            if not cost.is_finite() or cost < 0:
                raise ValueError
        except (ValueError, InvalidOperation):
            raise ValueError(
                "Quote cost must be an exact finite nonnegative decimal string"
            ) from None


class JobState(StrEnum):
    PREPARED = "prepared"
    SUBMITTING = "submitting"
    UNCERTAIN = "uncertain"
    REMOTE = "remote"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELED = "canceled"
    DOWNLOADING = "downloading"
    DOWNLOAD_FAILED = "download_failed"
    READY = "ready"
    APPLYING = "applying"
    APPLY_FAILED = "apply_failed"
    APPLIED = "applied"


_TRANSITIONS = {
    JobState.PREPARED: {JobState.SUBMITTING, JobState.CANCELED},
    JobState.SUBMITTING: {JobState.UNCERTAIN, JobState.REMOTE},
    JobState.UNCERTAIN: {JobState.REMOTE},
    JobState.REMOTE: {JobState.SUCCEEDED, JobState.FAILED, JobState.CANCELED},
    JobState.SUCCEEDED: {JobState.DOWNLOADING},
    JobState.DOWNLOADING: {JobState.READY, JobState.DOWNLOAD_FAILED},
    JobState.DOWNLOAD_FAILED: {JobState.DOWNLOADING},
    JobState.READY: {JobState.APPLYING},
    JobState.APPLYING: {JobState.APPLIED, JobState.APPLY_FAILED},
    JobState.APPLY_FAILED: {JobState.APPLYING},
}


@dataclass(frozen=True)
class StoredJob:
    intent: JobIntent
    state: JobState = JobState.PREPARED
    revision: int = 0
    remote_job_id: str | None = None


def _json(value):
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False
    )


def _decode(raw, scope):
    try:
        value = json.loads(raw)
        # Never let dataclass defaults turn a truncated in-flight record into
        # a fresh prepared request. Versioned records require every stored key.
        if not isinstance(value, dict) or set(value) != {
            "intent",
            "state",
            "revision",
            "remote_job_id",
        }:
            raise ValueError
        intent = value.pop("intent")
        for fields, cls in (
            (intent, JobIntent),
            (intent["scope"], JobScope),
            (intent["origin"], JobOrigin),
        ):
            if not isinstance(fields, dict) or set(fields) != set(cls.__dataclass_fields__):
                raise ValueError
        intent["scope"] = JobScope(**intent["scope"])
        intent["origin"] = JobOrigin(**intent["origin"])
        record = StoredJob(intent=JobIntent(**intent), **value)
        state = JobState(record.state)
        if record.intent.scope != scope or type(record.revision) is not int or record.revision < 0:
            raise ValueError
        if record.remote_job_id is not None:
            _identity(record.remote_job_id)
        needs_remote = state not in {
            JobState.PREPARED,
            JobState.SUBMITTING,
            JobState.UNCERTAIN,
            JobState.CANCELED,
        }
        if needs_remote and record.remote_job_id is None:
            raise ValueError
        if (
            state in {JobState.PREPARED, JobState.SUBMITTING, JobState.UNCERTAIN}
            and record.remote_job_id is not None
        ):
            raise ValueError
        return StoredJob(record.intent, state, record.revision, record.remote_job_id)
    except (ValueError, TypeError, KeyError, AttributeError):
        raise StoreError("Stored job data is invalid; preserve the database for recovery") from None


class JobStore:
    """SQLite transactions serialize writers across threads and Blender processes.

    Each operation opens its own connection. The immutable scope participates in
    every key and query. Revision checks reject stale callbacks; intents and known
    remote IDs cannot be replaced. This is storage, not a second job executor.
    """

    def __init__(self, path, scope: JobScope):
        if not isinstance(scope, JobScope):
            raise ValueError("A job scope is required")
        self._path = Path(path).absolute()
        self._scope = scope
        self._key = hashlib.sha256(_json(asdict(scope)).encode()).hexdigest()
        try:
            self._path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
            if self._path.is_symlink():
                raise StoreError("The job database must be a regular local file")
            try:
                descriptor = os.open(self._path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
            except FileExistsError:
                pass
            else:
                os.close(descriptor)
            with self._connection(write=True, initialize=True) as connection:
                version = connection.execute("PRAGMA user_version").fetchone()[0]
                application = connection.execute("PRAGMA application_id").fetchone()[0]
                tables = connection.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                ).fetchall()
                if version == 0 and application == 0 and not tables:
                    connection.execute(
                        "CREATE TABLE jobs (scope TEXT NOT NULL, request_id TEXT NOT NULL, "
                        "revision INTEGER NOT NULL, record TEXT NOT NULL, "
                        "PRIMARY KEY (scope, request_id))"
                    )
                    connection.execute(f"PRAGMA application_id = {_APPLICATION_ID}")
                    connection.execute(f"PRAGMA user_version = {_VERSION}")
                else:
                    self._check_version(connection)
        except OSError:
            raise StoreError("Could not initialize job storage") from None

    @property
    def scope(self):
        return self._scope

    @staticmethod
    def _check_version(connection):
        version = connection.execute("PRAGMA user_version").fetchone()[0]
        application = connection.execute("PRAGMA application_id").fetchone()[0]
        if version != _VERSION or application != _APPLICATION_ID:
            raise StoreError("Unsupported job database format; preserve it for recovery")

    @contextmanager
    def _connection(self, *, write=False, initialize=False):
        connection = None
        try:
            # mode=rw prevents a removed database from silently becoming empty.
            connection = sqlite3.connect(
                self._path.as_uri() + "?mode=rw", uri=True, timeout=2.0, isolation_level=None
            )
            connection.execute("PRAGMA synchronous = FULL")
            connection.execute("BEGIN IMMEDIATE" if write else "BEGIN")
            if not initialize:
                self._check_version(connection)
            yield connection
            connection.commit()
        except sqlite3.Error:
            raise StoreError("Job storage failed; do not dispatch or apply the operation") from None
        finally:
            if connection is not None:
                connection.close()  # Rolls back any uncommitted transaction.

    def _read(self, connection, request_id):
        row = connection.execute(
            "SELECT revision, record FROM jobs WHERE scope=? AND request_id=?",
            (self._key, request_id),
        ).fetchone()
        if row is None:
            return None
        record = _decode(row[1], self.scope)
        if record.intent.request_id != request_id or record.revision != row[0]:
            raise StoreError("Stored job identity or revision is inconsistent")
        return record

    def get(self, request_id):
        _identity(request_id)
        with self._connection() as connection:
            return self._read(connection, request_id)

    def records(self):
        with self._connection() as connection:
            identifiers = connection.execute(
                "SELECT request_id FROM jobs WHERE scope=? ORDER BY request_id", (self._key,)
            ).fetchall()
            return tuple(self._read(connection, row[0]) for row in identifiers)

    def create(self, intent: JobIntent):
        if not isinstance(intent, JobIntent) or intent.scope != self.scope:
            raise ValueError("Intent belongs to another scope")
        record = StoredJob(intent)
        with self._connection(write=True) as connection:
            if self._read(connection, intent.request_id) is not None:
                raise StoreConflict("Request identity already exists; do not resubmit")
            connection.execute(
                "INSERT INTO jobs VALUES (?, ?, ?, ?)",
                (self._key, intent.request_id, 0, _json(asdict(record))),
            )
        return record

    def transition(self, request_id, *, expected_revision, state: JobState, remote_job_id=None):
        _identity(request_id)
        if type(expected_revision) is not int or expected_revision < 0:
            raise ValueError("A nonnegative expected revision is required")
        if not isinstance(state, JobState):
            raise ValueError("A supported job state is required")
        if remote_job_id is not None:
            _identity(remote_job_id)
        with self._connection(write=True) as connection:
            previous = self._read(connection, request_id)
            if previous is None or previous.revision != expected_revision:
                raise StoreConflict("Job is missing or changed; reload before acting")
            if state not in _TRANSITIONS.get(previous.state, set()):
                raise ValueError("This job transition is not allowed")
            if remote_job_id is not None and previous.remote_job_id not in {None, remote_job_id}:
                raise ValueError("A known remote job identity cannot change")
            remote = previous.remote_job_id or remote_job_id
            if state == JobState.REMOTE and remote is None:
                raise ValueError("Reconciliation requires an authoritative remote job identity")
            if previous.remote_job_id is None and state != JobState.REMOTE and remote is not None:
                raise ValueError("Only remote acknowledgement can bind a remote job identity")
            updated = StoredJob(previous.intent, state, previous.revision + 1, remote)
            connection.execute(
                "UPDATE jobs SET revision=?, record=? WHERE scope=? AND request_id=? AND revision=?",
                (
                    updated.revision,
                    _json(asdict(updated)),
                    self._key,
                    request_id,
                    expected_revision,
                ),
            )
        return updated
