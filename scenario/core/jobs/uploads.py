# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Explicit upload commands on the shared SDK, store and worker owner."""

import math
import time
import uuid
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum

from .store import StoreConflict, StoreError
from .upload_sources import UploadSources
from .upload_store import StoredUpload, UploadState, UploadStore
from .upload_transfers import PartUploader


class UploadError(RuntimeError):
    """Sanitized upload failure; inspect durable progress before further actions."""


class UploadMutationUncertain(UploadError):
    """A claimed initialization, part or completion may have reached the service."""


class UploadRecoveryAction(StrEnum):
    REVIEW_SOURCE = "review_source"
    RECONCILE_UNKNOWN = "reconcile_unknown"
    REVIEW_TRANSFER = "review_transfer"
    POLL_REMOTE = "poll_remote"
    FINISHED = "finished"


@dataclass(frozen=True)
class UploadRecoveryItem:
    """An inspection snapshot, not permission to initialize, send or retry."""

    record: StoredUpload
    action: UploadRecoveryAction


_RECOVERY = {
    UploadState.PREPARED: UploadRecoveryAction.REVIEW_SOURCE,
    UploadState.INITIALIZING: UploadRecoveryAction.RECONCILE_UNKNOWN,
    UploadState.INITIALIZATION_UNCERTAIN: UploadRecoveryAction.RECONCILE_UNKNOWN,
    UploadState.UPLOADING: UploadRecoveryAction.REVIEW_TRANSFER,
    UploadState.PART_UNCERTAIN: UploadRecoveryAction.POLL_REMOTE,
    UploadState.FINALIZING: UploadRecoveryAction.POLL_REMOTE,
    UploadState.FINALIZATION_UNCERTAIN: UploadRecoveryAction.POLL_REMOTE,
    UploadState.PROCESSING: UploadRecoveryAction.POLL_REMOTE,
    UploadState.IMPORTED: UploadRecoveryAction.FINISHED,
    UploadState.FAILED: UploadRecoveryAction.FINISHED,
    UploadState.CANCELED: UploadRecoveryAction.FINISHED,
}


def _integer(value, expected):
    return not isinstance(value, bool) and isinstance(value, (int, float)) and value == expected


class UploadCommands:
    """Shares its coordinator's adapter, active guard and bounded worker queue."""

    def __init__(self, adapter, store, sources, uploader, guard, *, clock=time.time):
        if (
            not isinstance(store, UploadStore)
            or not isinstance(sources, UploadSources)
            or not isinstance(uploader, PartUploader)
        ):
            raise TypeError("Configure the scoped upload store, sources and part uploader")
        if sources.max_part_bytes > uploader.policy.max_bytes:
            raise ValueError("Upload source parts exceed the storage transfer limit")
        self._adapter, self._store, self._sources = adapter, store, sources
        self._uploader, self._guard, self._clock = uploader, guard, clock

    def inspect(self, request_id):
        """Read one immutable scoped record, or None; never fetch remote status."""
        with self._guard():
            return self._store.get(request_id)

    def recovery_plan(self):
        """Inspect saved progress without writes, file verification or dispatch.

        A missing receipt does not prove an active worker is dead or bytes were
        rejected. Known uploads can be polled; an unknown ID cannot be guessed.
        """
        with self._guard():
            return tuple(
                UploadRecoveryItem(
                    record,
                    UploadRecoveryAction.POLL_REMOTE
                    if record.active_part is not None
                    else _RECOVERY[record.state],
                )
                for record in self._store.records()
            )

    def _current(self, request_id, revision, states):
        with self._guard():
            current = self._store.get(request_id)
            if (
                type(revision) is not int
                or current is None
                or current.revision != revision
                or current.state not in states
            ):
                raise StoreConflict("Upload changed or cannot perform this action; reload it")
            return current

    def _transition(self, current, state, **kwargs):
        return self._store.transition(
            current.intent.request_id, expected_revision=current.revision, state=state, **kwargs
        )

    def prepare(self, source, *, origin, kind, content_type):
        # SDK model uploads produce model identities, not asset references.
        if kind == "model":
            raise UploadError("Model import needs its own result lifecycle")
        with self._guard():
            pass
        try:
            intent = self._sources.stage(
                source,
                request_id=uuid.uuid4().hex,
                scope=self._store.scope,
                origin=origin,
                kind=kind,
                content_type=content_type,
            )
        except Exception:
            raise UploadError("Could not prepare a stable upload source") from None
        with self._guard():
            return self._store.create(intent)

    def initialize(self, request_id, *, expected_revision):
        current = self._current(request_id, expected_revision, {UploadState.PREPARED})
        try:
            self._sources.verify(current.intent)
        except Exception:
            raise UploadError("Staged upload is unavailable or changed") from None
        with self._guard():
            current = self._transition(current, UploadState.INITIALIZING)
        try:
            intent = current.intent
            response = self._adapter.create_upload(
                kind=intent.kind,
                file_name=intent.file_name,
                content_type=intent.content_type,
                file_size=intent.file_size,
                parts=len(intent.part_sha256),
            )
            # Persist the returned remote identity before inspecting any transfer instructions.
            current = self._transition(current, UploadState.UPLOADING, upload_id=response.get("id"))
        except StoreError:
            raise
        except Exception:
            self._transition(current, UploadState.INITIALIZATION_UNCERTAIN)
            raise UploadMutationUncertain(
                "Upload initialization is uncertain; do not recreate it"
            ) from None
        return self._observe(current, response)

    def _part_url(self, current, response, number):
        intent = current.intent
        if (
            response.get("id") != current.upload_id
            or response.get("status") != "pending"
            or response.get("source") != "multipart"
            or response.get("kind") != intent.kind
            or response.get("fileName") != intent.file_name
            or response.get("contentType") != intent.content_type
            or not _integer(response.get("fileSize"), intent.file_size)
            or not _integer(response.get("partsCount"), len(intent.part_sha256))
        ):
            raise UploadError("Remote upload does not match the saved source and transfer state")
        parts = response.get("parts")
        if not isinstance(parts, list) or len(parts) != len(intent.part_sha256):
            raise UploadError("Remote upload has an incomplete part plan")
        chosen = None
        for expected, part in enumerate(parts, 1):
            if not isinstance(part, dict) or not _integer(part.get("number"), expected):
                raise UploadError("Remote upload has an invalid part sequence")
            if expected == number:
                chosen = part
        try:
            expires = chosen.get("expires")
            if not isinstance(expires, str):
                raise ValueError
            expiry = datetime.fromisoformat(expires.replace("Z", "+00:00"))
            now = self._clock()
            if expiry.tzinfo is None or not math.isfinite(now) or expiry.timestamp() <= now + 30:
                raise ValueError
            url = chosen.get("url")
            self._uploader.policy.destination(url)
        except Exception:
            raise UploadError("Upload part destination is invalid or expires too soon") from None
        return url

    def transfer_part(self, request_id, *, expected_revision):
        current = self._current(request_id, expected_revision, {UploadState.UPLOADING})
        if current.active_part is not None or len(current.receipts) == len(
            current.intent.part_sha256
        ):
            raise StoreConflict("No unclaimed upload part is available")
        number = len(current.receipts) + 1
        try:
            response = self._adapter.upload(current.upload_id)
            data = self._sources.part(current.intent, number)
            url = self._part_url(current, response, number)
        except Exception:
            raise UploadError("Could not verify the next upload part; no bytes sent") from None
        with self._guard():
            current = self._store.claim_part(request_id, expected_revision=current.revision)
        try:
            receipt = self._uploader.upload(
                url,
                data,
                number=number,
                content_type=current.intent.content_type,
                expected_sha256=current.intent.part_sha256[number - 1],
            )
        except Exception:
            self._transition(current, UploadState.PART_UNCERTAIN)
            raise UploadMutationUncertain(
                "Upload part is uncertain; do not send it again"
            ) from None
        # A persistence failure leaves the in-flight claim intact, even after an acknowledged PUT.
        return self._store.record_part(request_id, receipt, expected_revision=current.revision)

    def finalize(self, request_id, *, expected_revision):
        current = self._current(request_id, expected_revision, {UploadState.UPLOADING})
        with self._guard():
            current = self._transition(current, UploadState.FINALIZING)
        try:
            response = self._adapter.complete_upload(current.upload_id)
            updated = self._observe(current, response)
            if updated == current:
                raise UploadError("Completion was not confirmed")
            return updated
        except StoreError:
            raise
        except Exception:
            self._transition(current, UploadState.FINALIZATION_UNCERTAIN)
            raise UploadMutationUncertain(
                "Upload completion is uncertain; retrieve its status"
            ) from None

    def refresh(self, request_id, *, expected_revision):
        current = self._current(
            request_id,
            expected_revision,
            {
                UploadState.UPLOADING,
                UploadState.PART_UNCERTAIN,
                UploadState.FINALIZING,
                UploadState.FINALIZATION_UNCERTAIN,
                UploadState.PROCESSING,
            },
        )
        try:
            response = self._adapter.upload(current.upload_id)
        except Exception:
            raise UploadError("Could not retrieve the known upload") from None
        return self._observe(current, response)

    def _observe(self, current, response):
        if (
            response.get("id") != current.upload_id
            or response.get("kind") != current.intent.kind
            or response.get("source") != "multipart"
        ):
            raise UploadError("Scenario returned another upload identity or kind")
        status = response.get("status")
        target = {
            "complete": UploadState.PROCESSING,
            "validating": UploadState.PROCESSING,
            "validated": UploadState.PROCESSING,
            "imported": UploadState.IMPORTED,
            "failed": UploadState.FAILED,
        }.get(status)
        if status != "pending" and target is None:
            raise UploadError("Scenario returned an unrecognized upload state")
        if target is None or target == current.state:
            if self._store.get(current.intent.request_id) != current:
                raise StoreConflict("Upload changed during retrieval; reload it")
            return current
        try:
            return self._transition(
                current,
                target,
                asset_id=response.get("entityId") if target == UploadState.IMPORTED else None,
            )
        except ValueError:
            raise UploadError("Scenario returned an invalid imported asset identity") from None
