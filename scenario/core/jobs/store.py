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
import stat
from contextlib import contextmanager
from dataclasses import asdict, dataclass, replace
from decimal import Decimal, InvalidOperation
from enum import StrEnum
from pathlib import Path
from urllib.parse import urlsplit

from .transfers import DownloadedResult, TransferError, validate_result_name

_VERSION = 2
_APPLICATION_ID = 0x53434A42


class StoreError(RuntimeError):
    """Persistence failed; callers must stop before dispatching or applying."""


def _regular_database(path):
    """Recheck each connection; the caller must still own the parent directory."""
    try:
        regular = stat.S_ISREG(path.lstat().st_mode)
    except OSError:
        raise StoreError("Storage path is unavailable; preserve it for recovery") from None
    if not regular:
        raise StoreError("Storage must be a regular local file")


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
    CANCEL_REQUESTED = "cancel_requested"
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
    JobState.REMOTE: {
        JobState.CANCEL_REQUESTED,
        JobState.SUCCEEDED,
        JobState.FAILED,
        JobState.CANCELED,
    },
    JobState.CANCEL_REQUESTED: {JobState.SUCCEEDED, JobState.FAILED, JobState.CANCELED},
    JobState.SUCCEEDED: {JobState.DOWNLOADING},
    JobState.DOWNLOADING: {JobState.READY, JobState.DOWNLOAD_FAILED},
    JobState.DOWNLOAD_FAILED: {JobState.DOWNLOADING},
    JobState.READY: {JobState.APPLYING},
    JobState.APPLYING: {JobState.APPLIED, JobState.APPLY_FAILED},
    JobState.APPLY_FAILED: {JobState.APPLYING},
}


@dataclass(frozen=True)
class ResultAsset:
    """Immutable URL-free metadata from the scoped remote job/asset response."""

    asset_id: str
    name: str
    media_type: str
    expected_size: int | None = None
    expected_sha256: str | None = None

    def __post_init__(self):
        _identity(self.asset_id)
        try:
            validate_result_name(self.name)
        except TransferError:
            raise ValueError("Use a portable result filename") from None
        if not isinstance(self.media_type, str) or not re.fullmatch(
            r"[a-z0-9][a-z0-9.+-]{0,63}/[a-z0-9][a-z0-9.+-]{0,63}", self.media_type
        ):
            raise ValueError("Use a normalized media type")
        if self.expected_size is not None and (
            type(self.expected_size) is not int or not 0 <= self.expected_size <= 2**63 - 1
        ):
            raise ValueError("Invalid expected result size")
        if self.expected_sha256 is not None and (
            not isinstance(self.expected_sha256, str)
            or not re.fullmatch(r"[a-f0-9]{64}", self.expected_sha256)
        ):
            raise ValueError("Invalid expected result digest")


@dataclass(frozen=True)
class StoredResult:
    asset: ResultAsset
    receipt: DownloadedResult | None = None

    def __post_init__(self):
        if not isinstance(self.asset, ResultAsset):
            raise ValueError("Result asset metadata is required")
        if self.receipt is not None:
            if not isinstance(self.receipt, DownloadedResult):
                raise ValueError("A verified download receipt is required")
            if (
                self.receipt.name != self.asset.name
                or self.asset.expected_size not in (None, self.receipt.size)
                or self.asset.expected_sha256 not in (None, self.receipt.sha256)
            ):
                raise ValueError("Download receipt does not match the result manifest")


def _validate_results(results):
    if (
        not isinstance(results, tuple)
        or len(results) > 128
        or not all(isinstance(item, StoredResult) for item in results)
    ):
        raise ValueError("Use a bounded immutable result manifest")
    if len({item.asset.asset_id for item in results}) != len(results) or len(
        {item.asset.name.casefold() for item in results}
    ) != len(results):
        raise ValueError("Result asset identities and filenames must be unique")


@dataclass(frozen=True)
class StoredJob:
    intent: JobIntent
    state: JobState = JobState.PREPARED
    revision: int = 0
    remote_job_id: str | None = None
    results: tuple[StoredResult, ...] = ()


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
            "results",
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
        raw_results = value.pop("results")
        if not isinstance(raw_results, list) or len(raw_results) > 128:
            raise ValueError
        results = []
        for item in raw_results:
            if not isinstance(item, dict) or set(item) != {"asset", "receipt"}:
                raise ValueError
            if set(item["asset"]) != set(ResultAsset.__dataclass_fields__):
                raise ValueError
            receipt = item["receipt"]
            if receipt is not None:
                if set(receipt) != set(DownloadedResult.__dataclass_fields__):
                    raise ValueError
                receipt = DownloadedResult(**receipt)
            results.append(StoredResult(ResultAsset(**item["asset"]), receipt))
        results = tuple(results)
        _validate_results(results)
        record = StoredJob(intent=JobIntent(**intent), results=results, **value)
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
        has_results = state in {
            JobState.SUCCEEDED,
            JobState.DOWNLOADING,
            JobState.DOWNLOAD_FAILED,
            JobState.READY,
            JobState.APPLYING,
            JobState.APPLY_FAILED,
            JobState.APPLIED,
        }
        needs_results = has_results and state != JobState.SUCCEEDED
        needs_receipts = state in {
            JobState.READY,
            JobState.APPLYING,
            JobState.APPLY_FAILED,
            JobState.APPLIED,
        }
        if (
            (record.results and not has_results)
            or (needs_results and not record.results)
            or (needs_receipts and any(item.receipt is None for item in record.results))
        ):
            raise ValueError
        if state == JobState.SUCCEEDED and any(item.receipt for item in record.results):
            raise ValueError
        return replace(record, state=state)
    except (ValueError, TypeError, KeyError, AttributeError, TransferError):
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
            _regular_database(self._path)
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
            if state == JobState.DOWNLOADING and not previous.results:
                raise ValueError("Persist the result manifest before downloading")
            if state == JobState.READY and any(item.receipt is None for item in previous.results):
                raise ValueError("Every result needs a verified download receipt")
            updated = replace(
                previous, state=state, revision=previous.revision + 1, remote_job_id=remote
            )
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

    def _update_results(self, request_id, expected_revision, update):
        _identity(request_id)
        if type(expected_revision) is not int or expected_revision < 0:
            raise ValueError("A nonnegative expected revision is required")
        with self._connection(write=True) as connection:
            previous = self._read(connection, request_id)
            if previous is None or previous.revision != expected_revision:
                raise StoreConflict("Job is missing or changed; reload before acting")
            results = update(previous)
            _validate_results(results)
            updated = replace(previous, results=results, revision=previous.revision + 1)
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

    def set_results(self, request_id, assets, *, expected_revision):
        """Bind a trusted scoped result manifest once, before any file transfer."""
        if not isinstance(assets, tuple) or not 1 <= len(assets) <= 128:
            raise ValueError("A nonempty immutable asset manifest is required")
        results = tuple(StoredResult(asset) for asset in assets)
        _validate_results(results)

        def update(previous):
            if previous.state != JobState.SUCCEEDED or previous.results:
                raise ValueError("Only a successful job without a manifest accepts result metadata")
            return results

        return self._update_results(request_id, expected_revision, update)

    def record_download(self, request_id, asset_id, receipt, *, expected_revision):
        """Save one immutable verified receipt; a failure never authorizes generation."""
        _identity(asset_id)
        if not isinstance(receipt, DownloadedResult):
            raise ValueError("A verified download receipt is required")

        def update(previous):
            if previous.state != JobState.DOWNLOADING:
                raise ValueError("Claim downloading before recording a result")
            found = next(
                (item for item in previous.results if item.asset.asset_id == asset_id), None
            )
            if found is None or found.receipt is not None:
                raise ValueError("Result is absent or already has a receipt")
            recorded = StoredResult(found.asset, receipt)
            return tuple(recorded if item is found else item for item in previous.results)

        return self._update_results(request_id, expected_revision, update)
