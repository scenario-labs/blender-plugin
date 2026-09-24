# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Scoped result commands using SDK metadata and credential-free storage transfer."""

import hashlib
from dataclasses import asdict, dataclass
from pathlib import Path

from ..config import ext_for_mime
from .store import JobState, ResultAsset, StoreConflict, StoredJob, StoreError, _identity, _json
from .transfers import ResultDownloader, TransferError, _root


class ResultError(RuntimeError):
    """Sanitized result failure; review saved progress, never regenerate implicitly."""


@dataclass(frozen=True)
class VerifiedResults:
    record: StoredJob
    paths: tuple[Path, ...]


def _asset(record, identifier, name):
    if record.get("id") != identifier or record.get("status") != "success":
        raise ResultError("Scenario returned an unavailable or different result asset")
    properties = record.get("properties")
    if not isinstance(properties, dict):
        raise ResultError("Scenario returned no result size")
    size = properties.get("size")
    if (
        isinstance(size, bool)
        or not isinstance(size, (int, float))
        or not 0 <= size <= 2**53
        or int(size) != size
    ):
        raise ResultError("Scenario returned an invalid result size")
    try:
        return ResultAsset(identifier, name, record.get("mimeType"), int(size))
    except ValueError:
        raise ResultError("Scenario returned invalid result metadata") from None


class ResultCommands:
    """Owned by the shared coordinator; never opens another client or worker pool."""

    def __init__(self, adapter, store, guard, *, downloader=None, root=None):
        if downloader is not None and not isinstance(downloader, ResultDownloader):
            raise TypeError("Use the bounded result downloader")
        if (downloader is None) != (root is None):
            raise ValueError("Configure both private result root and storage downloader")
        self._adapter, self._store, self._guard = adapter, store, guard
        self._downloader = downloader
        self._root = _root(root) if root is not None else None

    def _current(self, request_id, revision, states):
        with self._guard():
            current = self._store.get(request_id)
            if (
                type(revision) is not int
                or current is None
                or current.revision != revision
                or current.state not in states
                or current.remote_job_id is None
            ):
                raise StoreConflict("Result job is missing or changed; reload before acting")
            return current

    def _request(self, method, identifier):
        with self._guard():
            pass
        try:
            return method(identifier)
        except ValueError:
            raise ResultError("Scenario result metadata could not be retrieved") from None

    def load_manifest(self, request_id, *, expected_revision):
        current = self._current(request_id, expected_revision, {JobState.SUCCEEDED})
        if current.results:
            return current
        job = self._request(self._adapter.job, current.remote_job_id)
        if job.get("jobId") != current.remote_job_id or job.get("status") != "success":
            raise ResultError("Scenario did not confirm this successful result job")
        metadata = job.get("metadata")
        identifiers = metadata.get("assetIds") if isinstance(metadata, dict) else None
        if not isinstance(identifiers, list) or not 1 <= len(identifiers) <= 128:
            raise ResultError("The job has no supported bounded asset result list")
        try:
            for identifier in identifiers:
                _identity(identifier)
            if len(set(identifiers)) != len(identifiers):
                raise ValueError
        except ValueError:
            raise ResultError("Scenario returned invalid result asset identities") from None
        assets = []
        for index, identifier in enumerate(identifiers):
            record = self._request(self._adapter.asset, identifier)
            # Provider filenames/URL paths never choose local storage paths.
            suffix = (
                ext_for_mime(record.get("mimeType"))
                if isinstance(record.get("mimeType"), str)
                else "bin"
            )
            name = f"{index:03d}-{hashlib.sha256(identifier.encode()).hexdigest()[:24]}.{suffix}"
            assets.append(_asset(record, identifier, name))
        with self._guard():
            return self._store.set_results(
                request_id, tuple(assets), expected_revision=current.revision
            )

    def _directory(self, record, *, create=True):
        if self._root is None:
            raise ResultError("Result storage has not been configured")
        root = _root(self._root)
        # Include all scope components and request identity, not just asset names.
        keys = (
            hashlib.sha256(_json(asdict(record.intent.scope)).encode()).hexdigest(),
            hashlib.sha256(record.intent.request_id.encode()).hexdigest(),
        )
        for key in keys:
            child = root / key
            if create:
                child.mkdir(mode=0o700, exist_ok=True)
            root = _root(child)
        return root

    def download(self, request_id, *, expected_revision):
        current = self._current(
            request_id, expected_revision, {JobState.SUCCEEDED, JobState.DOWNLOAD_FAILED}
        )
        if self._downloader is None:
            raise ResultError("Result storage has not been configured")
        if not current.results:
            current = self.load_manifest(request_id, expected_revision=current.revision)
        try:
            directory = self._directory(current)
        except (OSError, ValueError, TransferError):
            raise ResultError("Could not prepare private result storage") from None
        with self._guard():
            current = self._store.transition(
                request_id, expected_revision=current.revision, state=JobState.DOWNLOADING
            )
        try:
            for item in current.results:
                with self._guard():
                    pass
                if item.receipt is not None:
                    self._downloader.verify(directory, item.receipt)
                    continue
                response = self._request(self._adapter.asset, item.asset.asset_id)
                if _asset(response, item.asset.asset_id, item.asset.name) != item.asset:
                    raise ResultError("Result metadata changed after the manifest was saved")
                url = response.get("url")
                if not isinstance(url, str) or not url:
                    raise ResultError("Scenario returned no result download destination")
                receipt = self._downloader.download(
                    url,
                    root=directory,
                    name=item.asset.name,
                    expected_size=item.asset.expected_size,
                    expected_sha256=item.asset.expected_sha256,
                )
                self._downloader.verify(directory, receipt)
                current = self._store.record_download(
                    request_id, item.asset.asset_id, receipt, expected_revision=current.revision
                )
            return self._store.transition(
                request_id, expected_revision=current.revision, state=JobState.READY
            )
        except StoreError:
            # Preserve an uncertain disk write. Never claim failure was saved.
            raise
        except Exception:
            self._store.transition(
                request_id, expected_revision=current.revision, state=JobState.DOWNLOAD_FAILED
            )
            raise ResultError(
                "Result download did not complete; review saved files before retrying"
            ) from None

    def verify_ready(self, request_id, *, expected_revision):
        current = self._current(
            request_id, expected_revision, {JobState.READY, JobState.APPLY_FAILED, JobState.APPLIED}
        )
        if self._downloader is None:
            raise ResultError("Result storage has not been configured")
        try:
            directory = self._directory(current, create=False)
            paths = []
            for item in current.results:
                with self._guard():
                    pass
                paths.append(self._downloader.verify(directory, item.receipt))
            # Stale verification cannot authorize a subsequent application.
            if self._store.get(request_id) != current:
                raise StoreConflict("Result job changed during verification")
            return VerifiedResults(current, tuple(paths))
        except StoreError:
            raise
        except Exception:
            raise ResultError("Saved result files could not be verified") from None
