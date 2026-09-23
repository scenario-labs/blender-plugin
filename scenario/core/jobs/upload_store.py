# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Scoped durable upload intent and mutation claims, without network or file reads."""

import hashlib
import json
import os
import re
import sqlite3
from contextlib import contextmanager
from dataclasses import asdict, dataclass, replace
from enum import StrEnum
from pathlib import Path

from .store import (
    JobOrigin,
    JobScope,
    StoreConflict,
    StoreError,
    _identity,
    _json,
    _regular_database,
)
from .upload_transfers import UploadedPart

_APPLICATION_ID = 0x53435550
_VERSION = 1


def _digest(value):
    if not isinstance(value, str) or not re.fullmatch(r"[a-f0-9]{64}", value):
        raise ValueError("Use a SHA256 source identity")


@dataclass(frozen=True)
class UploadIntent:
    request_id: str
    scope: JobScope
    origin: JobOrigin
    kind: str
    file_name: str
    content_type: str
    file_size: int
    file_sha256: str
    part_size: int
    part_sha256: tuple[str, ...]

    def __post_init__(self):
        _identity(self.request_id)
        if not isinstance(self.scope, JobScope) or not isinstance(self.origin, JobOrigin):
            raise ValueError("Upload scope and origin are required")
        if not isinstance(self.kind, str) or self.kind not in {
            "3d",
            "asset",
            "audio",
            "avatar",
            "image",
            "model",
            "text",
            "video",
        }:
            raise ValueError("Use a supported upload kind")
        if (
            not isinstance(self.file_name, str)
            or not self.file_name.strip()
            or len(self.file_name) > 256
            or self.file_name in {".", ".."}
            or any(c in self.file_name for c in "/\\:")
            or any(ord(c) < 32 or ord(c) == 127 for c in self.file_name)
        ):
            raise ValueError("Use a bounded source basename without paths")
        if not isinstance(self.content_type, str) or not re.fullmatch(
            r"[A-Za-z0-9!#$&^_.+-]{1,64}/[A-Za-z0-9!#$&^_.+-]{1,64}", self.content_type
        ):
            raise ValueError("Use a bare upload MIME type")
        if type(self.file_size) is not int or not 1 <= self.file_size <= 2**63 - 1:
            raise ValueError("Use a positive upload file size")
        if type(self.part_size) is not int or not 1 <= self.part_size <= self.file_size:
            raise ValueError("Use a positive part size no larger than the file")
        count = (self.file_size + self.part_size - 1) // self.part_size
        if (
            not isinstance(self.part_sha256, tuple)
            or len(self.part_sha256) != count
            or count > 10000
        ):
            raise ValueError("Use the complete bounded part digest list")
        _digest(self.file_sha256)
        for digest in self.part_sha256:
            _digest(digest)

    def part_bytes(self, number):
        if type(number) is not int or not 1 <= number <= len(self.part_sha256):
            raise ValueError("Part number is outside this upload")
        return min(self.part_size, self.file_size - (number - 1) * self.part_size)


class UploadState(StrEnum):
    PREPARED = "prepared"
    INITIALIZING = "initializing"
    INITIALIZATION_UNCERTAIN = "initialization_uncertain"
    UPLOADING = "uploading"
    PART_UNCERTAIN = "part_uncertain"
    FINALIZING = "finalizing"
    FINALIZATION_UNCERTAIN = "finalization_uncertain"
    PROCESSING = "processing"
    IMPORTED = "imported"
    FAILED = "failed"
    CANCELED = "canceled"


_OBSERVATIONS = {UploadState.PROCESSING, UploadState.IMPORTED, UploadState.FAILED}
_TRANSITIONS = {
    UploadState.PREPARED: {UploadState.INITIALIZING, UploadState.CANCELED},
    UploadState.INITIALIZING: {UploadState.INITIALIZATION_UNCERTAIN, UploadState.UPLOADING},
    UploadState.UPLOADING: {UploadState.PART_UNCERTAIN, UploadState.FINALIZING} | _OBSERVATIONS,
    UploadState.PART_UNCERTAIN: _OBSERVATIONS,
    UploadState.FINALIZING: {UploadState.FINALIZATION_UNCERTAIN} | _OBSERVATIONS,
    UploadState.FINALIZATION_UNCERTAIN: _OBSERVATIONS,
    UploadState.PROCESSING: {UploadState.IMPORTED, UploadState.FAILED},
}


@dataclass(frozen=True)
class StoredUpload:
    intent: UploadIntent
    state: UploadState = UploadState.PREPARED
    revision: int = 0
    upload_id: str | None = None
    asset_id: str | None = None
    active_part: int | None = None
    receipts: tuple[UploadedPart, ...] = ()


def _validate(record):
    if not isinstance(record.intent, UploadIntent) or not isinstance(record.state, UploadState):
        raise ValueError("Upload intent and state are required")
    if type(record.revision) is not int or record.revision < 0:
        raise ValueError("Invalid upload revision")
    local = record.state in {
        UploadState.PREPARED,
        UploadState.INITIALIZING,
        UploadState.INITIALIZATION_UNCERTAIN,
        UploadState.CANCELED,
    }
    if local:
        if record.upload_id is not None or record.receipts or record.active_part is not None:
            raise ValueError("Local upload intent cannot have remote progress")
    else:
        _identity(record.upload_id)
    if record.state == UploadState.IMPORTED:
        _identity(record.asset_id)
    elif record.asset_id is not None:
        raise ValueError("Only an imported upload can bind an asset")
    if not isinstance(record.receipts, tuple) or len(record.receipts) > len(
        record.intent.part_sha256
    ):
        raise ValueError("Invalid upload receipts")
    for number, receipt in enumerate(record.receipts, 1):
        if (
            not isinstance(receipt, UploadedPart)
            or type(receipt.number) is not int
            or receipt.number != number
            or type(receipt.size) is not int
            or receipt.size != record.intent.part_bytes(number)
            or receipt.sha256 != record.intent.part_sha256[number - 1]
        ):
            raise ValueError("Upload receipt does not match its saved part")
    if record.active_part is not None:
        if (
            record.state not in {UploadState.UPLOADING, UploadState.PART_UNCERTAIN}
            or type(record.active_part) is not int
            or record.active_part != len(record.receipts) + 1
            or record.active_part > len(record.intent.part_sha256)
        ):
            raise ValueError("Invalid active upload part")
    elif record.state == UploadState.PART_UNCERTAIN:
        raise ValueError("Uncertain part identity must be preserved")
    if record.state in {UploadState.FINALIZING, UploadState.FINALIZATION_UNCERTAIN} and (
        len(record.receipts) != len(record.intent.part_sha256) or record.active_part is not None
    ):
        raise ValueError("Finalize only after all part receipts are saved")
    return record


def _decode(raw, scope):
    try:
        value = json.loads(raw)
        if not isinstance(value, dict) or set(value) != set(StoredUpload.__dataclass_fields__):
            raise ValueError
        intent = value.pop("intent")
        for fields, cls in (
            (intent, UploadIntent),
            (intent["scope"], JobScope),
            (intent["origin"], JobOrigin),
        ):
            if not isinstance(fields, dict) or set(fields) != set(cls.__dataclass_fields__):
                raise ValueError
        intent["scope"] = JobScope(**intent["scope"])
        intent["origin"] = JobOrigin(**intent["origin"])
        if not isinstance(intent["part_sha256"], list):
            raise ValueError
        intent["part_sha256"] = tuple(intent["part_sha256"])
        raw_receipts = value.pop("receipts")
        if not isinstance(raw_receipts, list) or len(raw_receipts) > 10000:
            raise ValueError
        for receipt in raw_receipts:
            if not isinstance(receipt, dict) or set(receipt) != set(
                UploadedPart.__dataclass_fields__
            ):
                raise ValueError
        record = StoredUpload(
            UploadIntent(**intent),
            receipts=tuple(UploadedPart(**r) for r in raw_receipts),
            **{**value, "state": UploadState(value["state"])},
        )
        if record.intent.scope != scope:
            raise ValueError
        return _validate(record)
    except (ValueError, TypeError, KeyError, AttributeError):
        raise StoreError("Stored upload is invalid; preserve its database for recovery") from None


class UploadStore:
    """Application-owned upload database; claims never execute or resume work."""

    def __init__(self, path, scope: JobScope):
        if not isinstance(scope, JobScope):
            raise ValueError("An upload scope is required")
        self._path, self._scope = Path(path).absolute(), scope
        self._key = hashlib.sha256(_json(asdict(scope)).encode()).hexdigest()
        try:
            self._path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
            if self._path.is_symlink():
                raise StoreError("Upload storage must be a regular local file")
            try:
                descriptor = os.open(self._path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
            except FileExistsError:
                pass
            else:
                os.close(descriptor)
            with self._connection(write=True, initialize=True) as connection:
                version = connection.execute("PRAGMA user_version").fetchone()[0]
                app = connection.execute("PRAGMA application_id").fetchone()[0]
                tables = connection.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                ).fetchall()
                if version == app == 0 and not tables:
                    connection.execute(
                        "CREATE TABLE uploads (scope TEXT NOT NULL, request_id TEXT NOT NULL, "
                        "revision INTEGER NOT NULL, record TEXT NOT NULL, PRIMARY KEY (scope, request_id))"
                    )
                    connection.execute(f"PRAGMA application_id={_APPLICATION_ID}")
                    connection.execute(f"PRAGMA user_version={_VERSION}")
                else:
                    self._check_version(connection)
        except OSError:
            raise StoreError("Could not initialize upload storage") from None

    @property
    def scope(self):
        return self._scope

    @staticmethod
    def _check_version(connection):
        if (
            connection.execute("PRAGMA user_version").fetchone()[0] != _VERSION
            or connection.execute("PRAGMA application_id").fetchone()[0] != _APPLICATION_ID
        ):
            raise StoreError("Unsupported upload storage format; preserve it for recovery")

    @contextmanager
    def _connection(self, *, write=False, initialize=False):
        connection = None
        try:
            _regular_database(self._path)
            connection = sqlite3.connect(
                self._path.as_uri() + "?mode=rw", uri=True, timeout=2.0, isolation_level=None
            )
            connection.execute("PRAGMA synchronous=FULL")
            connection.execute("BEGIN IMMEDIATE" if write else "BEGIN")
            if not initialize:
                self._check_version(connection)
            yield connection
            connection.commit()
        except sqlite3.Error:
            raise StoreError("Upload persistence failed; do not send or finalize") from None
        finally:
            if connection is not None:
                connection.close()

    def _read(self, connection, request_id):
        row = connection.execute(
            "SELECT revision, record FROM uploads WHERE scope=? AND request_id=?",
            (self._key, request_id),
        ).fetchone()
        if row is None:
            return None
        record = _decode(row[1], self.scope)
        if record.revision != row[0] or record.intent.request_id != request_id:
            raise StoreError("Stored upload identity or revision is inconsistent")
        return record

    def get(self, request_id):
        _identity(request_id)
        with self._connection() as connection:
            return self._read(connection, request_id)

    def records(self):
        with self._connection() as connection:
            rows = connection.execute(
                "SELECT request_id FROM uploads WHERE scope=? ORDER BY request_id", (self._key,)
            ).fetchall()
            return tuple(self._read(connection, row[0]) for row in rows)

    def create(self, intent):
        if not isinstance(intent, UploadIntent) or intent.scope != self.scope:
            raise ValueError("Upload intent belongs to another scope")
        record = _validate(StoredUpload(intent))
        with self._connection(write=True) as connection:
            if self._read(connection, intent.request_id) is not None:
                raise StoreConflict("Upload request already exists; do not recreate")
            connection.execute(
                "INSERT INTO uploads VALUES (?, ?, ?, ?)",
                (self._key, intent.request_id, 0, _json(asdict(record))),
            )
        return record

    def _change(self, request_id, expected_revision, change):
        _identity(request_id)
        if type(expected_revision) is not int or expected_revision < 0:
            raise ValueError("Use a nonnegative upload revision")
        with self._connection(write=True) as connection:
            previous = self._read(connection, request_id)
            if previous is None or previous.revision != expected_revision:
                raise StoreConflict("Upload is missing or changed; reload before acting")
            updated = _validate(replace(change(previous), revision=previous.revision + 1))
            connection.execute(
                "UPDATE uploads SET revision=?, record=? WHERE scope=? AND request_id=? AND revision=?",
                (
                    updated.revision,
                    _json(asdict(updated)),
                    self._key,
                    request_id,
                    expected_revision,
                ),
            )
        return updated

    def transition(self, request_id, *, expected_revision, state, upload_id=None, asset_id=None):
        if not isinstance(state, UploadState):
            raise ValueError("Use a supported upload state")
        if upload_id is not None:
            _identity(upload_id)
        if asset_id is not None:
            _identity(asset_id)

        def change(previous):
            if state not in _TRANSITIONS.get(previous.state, set()):
                raise ValueError("This upload transition is not allowed")
            if upload_id is not None and not (
                previous.state == UploadState.INITIALIZING and state == UploadState.UPLOADING
            ):
                raise ValueError("Only initialization can bind a remote upload")
            if asset_id is not None and state != UploadState.IMPORTED:
                raise ValueError("Only an authoritative imported observation can bind an asset")
            return replace(
                previous,
                state=state,
                upload_id=previous.upload_id or upload_id,
                asset_id=asset_id,
                active_part=previous.active_part if state == UploadState.PART_UNCERTAIN else None,
            )

        return self._change(request_id, expected_revision, change)

    def claim_part(self, request_id, *, expected_revision):
        def change(previous):
            if previous.state != UploadState.UPLOADING or previous.active_part is not None:
                raise StoreConflict("An upload part is already claimed or cannot be sent")
            if len(previous.receipts) == len(previous.intent.part_sha256):
                raise ValueError("All parts already have receipts")
            return replace(previous, active_part=len(previous.receipts) + 1)

        return self._change(request_id, expected_revision, change)

    def record_part(self, request_id, receipt, *, expected_revision):
        def change(previous):
            if (
                previous.state != UploadState.UPLOADING
                or not isinstance(receipt, UploadedPart)
                or previous.active_part != receipt.number
            ):
                raise StoreConflict("Receipt does not identify the active upload part")
            return replace(previous, active_part=None, receipts=previous.receipts + (receipt,))

        return self._change(request_id, expected_revision, change)
