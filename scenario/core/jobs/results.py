# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Scoped result commands using SDK metadata and credential-free storage transfer."""

import hashlib
import os
import tempfile
from dataclasses import asdict, dataclass, field, replace
from pathlib import Path

from ..config import ext_for_mime
from ..scene import splats
from .result_metadata import REWRITTEN_MESH_TYPES, texture_role
from .store import JobState, ResultAsset, StoreConflict, StoredJob, StoreError, _identity, _json
from .transfers import ResultDownloader, TransferError, _root
from .upload_sources import _open, _stamp


class ResultError(RuntimeError):
    """Sanitized result failure; review saved progress, never regenerate implicitly."""


@dataclass(frozen=True)
class VerifiedResults:
    record: StoredJob
    paths: tuple[Path, ...]


MAX_PROMPT_BYTES = 65536


@dataclass(frozen=True)
class PromptResults:
    """Read-only recovered text; no Blender mutation or spending authorization."""

    record: StoredJob
    prompts: tuple[str, ...] = field(repr=False)


@dataclass(frozen=True)
class ModelTextResult:
    """One explicitly selected text asset; retrieval never applies or resubmits it."""

    record: StoredJob
    asset_id: str
    text: str = field(repr=False)


@dataclass(frozen=True, eq=False)
class PreparedModelImport:
    """Worker-side preparation of one saved model result for a later reviewed import.

    `splat` is the decoded point snapshot of an SPZ, .splat or Gaussian PLY result.
    A mesh PLY (a non-empty first vertex element with scalar x, y and z and no
    splat properties) has no snapshot; `ply_mesh` routes it to a reviewed mesh
    importer. Preparation never claims or mutates a scene; a claim still consumes
    the owner-registered `verified` ticket once.
    """

    verified: VerifiedResults
    asset_id: str
    media_type: str
    options: splats.SplatOptions
    splat: splats.SplatData | None = field(default=None, repr=False)

    @property
    def ply_mesh(self):
        return self.splat is None


class _ReceiptReader:
    """Hash exactly the bytes a decoder reads from one receipt-bound file."""

    def __init__(self, source, receipt, cancel):
        self._source, self._receipt, self._cancel = source, receipt, cancel
        self._digest, self._size = hashlib.sha256(), 0

    def read(self, size):
        data = self._source.read(min(size, self._receipt.size - self._size + 1))
        self._size += len(data)
        if self._size > self._receipt.size:
            raise ResultError("The saved result changed while it was prepared; verify it again")
        self._digest.update(data)
        return data

    def matches(self):
        """Hash the unread remainder, then compare with the saved receipt."""
        while self.read(1 << 20):
            if self._cancel.is_set():
                raise splats.SplatCancelled("Splat preparation cancelled")
        return self._size == self._receipt.size and self._digest.hexdigest() == self._receipt.sha256


def _prompt_text(value):
    if not isinstance(value, str) or not value.strip():
        raise ResultError("Scenario returned no usable prompt text")
    try:
        valid = len(value.encode("utf-8")) <= MAX_PROMPT_BYTES
    except UnicodeError:
        valid = False
    if not valid or any(ord(char) < 32 and char not in "\n\r\t" for char in value):
        raise ResultError("Scenario returned invalid or oversized prompt text")
    return value


def _prompt_asset_id(value):
    value = value.strip()
    return value.startswith("asset_") and not any(char.isspace() for char in value)


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
        return ResultAsset(
            identifier, name, record.get("mimeType"), int(size), texture_role=texture_role(record)
        )
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

    def read_prompts(self, request_id, *, expected_revision):
        """Recover the known successful job's full text, never a paid fallback."""
        current = self._current(request_id, expected_revision, {JobState.SUCCEEDED})
        if current.intent.operation not in {"prompt", "translate"}:
            raise ResultError("Choose a completed Prompt Spark job")
        translation = current.intent.operation == "translate"
        job = self._request(self._adapter.job, current.remote_job_id)
        expected_types = (
            ("translate",) if translation else ("generate-prompt", "image-prompt-editing")
        )
        if (
            job.get("jobId") != current.remote_job_id
            or job.get("status") != "success"
            or job.get("jobType") not in expected_types
        ):
            raise ResultError("Scenario did not confirm this successful Prompt Spark job")
        metadata = job.get("metadata")
        output = metadata.get("output") if isinstance(metadata, dict) else None
        values = None
        if isinstance(output, dict):
            values = [output.get("translation")] if translation else output.get("prompts")
        if not isinstance(values, list) or not 1 <= len(values) <= 5:
            raise ResultError("Scenario returned no bounded prompt result list")
        prompts = []
        for value in values:
            text = _prompt_text(value)
            if _prompt_asset_id(text):
                text = text.strip()
                try:
                    _identity(text)
                except ValueError:
                    raise ResultError(
                        "Scenario returned an invalid prompt asset identity"
                    ) from None
                text = self._read_text_asset(text)
            prompts.append(text)
        with self._guard():
            if self._store.get(request_id) != current:
                raise StoreConflict("Prompt result changed; reload before acting")
            return PromptResults(current, tuple(prompts))

    def read_model_text(self, request_id, *, expected_revision, asset_id):
        """Read complete text from an explicitly selected successful model output."""
        current = self._current(
            request_id,
            expected_revision,
            {
                JobState.SUCCEEDED,
                JobState.DOWNLOAD_FAILED,
                JobState.READY,
                JobState.APPLY_FAILED,
                JobState.APPLIED,
            },
        )
        if current.intent.operation != "model":
            raise ResultError("Choose a completed model job")
        try:
            _identity(asset_id)
        except ValueError:
            raise ResultError("Choose a valid result asset identity") from None
        job = self._request(self._adapter.job, current.remote_job_id)
        if job.get("jobId") != current.remote_job_id or job.get("status") != "success":
            raise ResultError("Scenario did not confirm this successful model job")
        metadata = job.get("metadata")
        identifiers = metadata.get("assetIds") if isinstance(metadata, dict) else None
        if not isinstance(identifiers, list) or not 1 <= len(identifiers) <= 128:
            raise ResultError("The model job has no supported bounded asset result list")
        try:
            for identifier in identifiers:
                _identity(identifier)
            if len(set(identifiers)) != len(identifiers) or asset_id not in identifiers:
                raise ValueError
            if current.results and asset_id not in {
                item.asset.asset_id for item in current.results
            }:
                raise ValueError
        except ValueError:
            raise ResultError("The selected text asset does not match this saved job") from None
        text = self._read_text_asset(asset_id)
        with self._guard():
            if self._store.get(request_id) != current:
                raise StoreConflict("Model result changed; reload before acting")
            return ModelTextResult(current, asset_id, text)

    def _read_text_asset(self, identifier):
        asset = self._request(self._adapter.asset, identifier)
        if (
            asset.get("id") != identifier
            or asset.get("status") != "success"
            or asset.get("kind") != "text"
            or asset.get("mimeType") != "text/plain"
        ):
            raise ResultError("Scenario returned an unavailable or unsupported text asset")
        props = asset.get("properties")
        if not isinstance(props, dict):
            raise ResultError("Scenario returned no text asset properties")
        if props.get("hasFullPreview") is True:
            text = _prompt_text(props.get("preview"))
        else:
            size = props.get("size")
            if (
                type(size) not in {int, float}
                or not 0 < size <= MAX_PROMPT_BYTES
                or int(size) != size
            ):
                raise ResultError("Scenario returned an invalid or oversized text asset")
            size = int(size)
            if self._downloader is None:
                raise ResultError("Text result storage has not been configured")
            # Dedicated private staging never reuses names from the remote asset.
            # Context-managed cleanup runs on success, failure and control exceptions.
            try:
                with tempfile.TemporaryDirectory(
                    prefix=".scenario-prompt-", dir=_root(self._root)
                ) as temporary:
                    directory = Path(temporary)
                    with self._guard():
                        pass
                    receipt = self._downloader.download(
                        asset.get("url"),
                        root=directory,
                        name="prompt.txt",
                        expected_size=size,
                        max_bytes=MAX_PROMPT_BYTES,
                    )
                    path = self._downloader.verify(directory, receipt)
                    with path.open("rb") as source:
                        data = source.read(MAX_PROMPT_BYTES + 1)
                    if (
                        len(data) != receipt.size
                        or hashlib.sha256(data).hexdigest() != receipt.sha256
                    ):
                        raise ResultError("Text result changed while reading")
                    text = _prompt_text(data.decode("utf-8"))
            except Exception:
                raise ResultError(
                    "Full text could not be read; retry retrieval without generating again"
                ) from None
        if _prompt_asset_id(text.strip()):
            raise ResultError("Scenario returned an asset reference instead of prompt text")
        return text

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
        with self._store.result_transfer_lock(request_id):
            return self._download(request_id, expected_revision=expected_revision)

    def _download(self, request_id, *, expected_revision):
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
                fresh = _asset(response, item.asset.asset_id, item.asset.name)
                rewritten_mesh = item.asset.media_type in REWRITTEN_MESH_TYPES
                if rewritten_mesh:
                    # Legacy ingestion rewrote file references without updating
                    # properties.size; identity/type/digest checks remain exact.
                    fresh = replace(fresh, expected_size=item.asset.expected_size)
                if item.asset.texture_role is None:
                    # Legacy/unclassified results keep unknown semantics. A later
                    # response may not grant a new material role to saved bytes.
                    fresh = replace(fresh, texture_role=None)
                if fresh != item.asset:
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
                    **({"allow_size_mismatch": True} if rewritten_mesh else {}),
                )
                self._downloader.verify(directory, receipt)
                current = self._store.record_download(
                    request_id,
                    item.asset.asset_id,
                    receipt,
                    expected_revision=current.revision,
                    **({"allow_mesh_size_correction": True} if rewritten_mesh else {}),
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

    def recover_download(self, request_id, *, expected_revision):
        """Inspect an interrupted transfer offline, never retry it or apply a result."""
        with self._store.result_transfer_lock(request_id):
            current = self._current(request_id, expected_revision, {JobState.DOWNLOADING})
            if self._downloader is None:
                raise ResultError("Result storage has not been configured")
            try:
                directory = self._directory(current, create=False)
                for item in current.results:
                    with self._guard():
                        pass
                    if item.receipt is not None:
                        self._downloader.verify(directory, item.receipt)
                    elif (directory / item.asset.name).exists() or (
                        directory / item.asset.name
                    ).is_symlink():
                        # A crash may have published bytes without committing their
                        # receipt. Size alone is not proof of trusted result content.
                        raise ResultError("Unreceipted result file requires explicit review")
            except StoreError:
                raise
            except Exception:
                raise ResultError(
                    "Interrupted result files need review; missing, changed or unreceipted files "
                    "cannot be recovered"
                ) from None
            state = (
                JobState.READY
                if all(item.receipt is not None for item in current.results)
                else JobState.DOWNLOAD_FAILED
            )
            with self._guard():
                return self._store.transition(
                    request_id, expected_revision=current.revision, state=state
                )

    def measure_media(self, request_id, *, expected_revision, asset_id, root, cancel):
        """Inspect one downloaded receipt on a worker without applying or fetching it."""
        from .media_probe import measure

        pending_download = {JobState.SUCCEEDED, JobState.DOWNLOADING, JobState.DOWNLOAD_FAILED}
        current = self._current(
            request_id,
            expected_revision,
            {JobState.READY, JobState.APPLY_FAILED, JobState.APPLIED} | pending_download,
        )
        if current.state in pending_download:
            raise ResultError("Download the selected model result before inspecting its media")
        verified = self.verify_ready(request_id, expected_revision=expected_revision)
        chosen = [
            (item, path)
            for item, path in zip(verified.record.results, verified.paths, strict=True)
            if item.asset.asset_id == asset_id
        ]
        if len(chosen) != 1:
            raise ResultError("Choose one saved media result")
        item, path = chosen[0]
        result = measure(path, item.receipt, item.asset.media_type, root=root, cancel=cancel)
        with self._guard():
            if self._store.get(request_id) != verified.record:
                raise StoreConflict("Result changed during media inspection")
        return result

    def prepare_model_import(self, request_id, *, expected_revision, asset_id, options, cancel):
        """Verify every saved receipt, then decode one selected splat on a worker.

        The selected file is hashed while it is decoded. The snapshot is discarded
        unless its bytes equal the saved receipt and the job is unchanged. This
        never downloads, refreshes metadata, claims an application or uses bpy.
        Cancellation is checked before each receipt is hashed and between chunks.
        """
        if not isinstance(options, splats.SplatOptions):
            raise TypeError("Use reviewed splat options")
        pending_download = {JobState.SUCCEEDED, JobState.DOWNLOADING, JobState.DOWNLOAD_FAILED}
        current = self._current(
            request_id,
            expected_revision,
            {JobState.READY, JobState.APPLY_FAILED, JobState.APPLIED} | pending_download,
        )
        if current.state in pending_download:
            raise ResultError("Download the selected model result before importing it")
        verified = self.verify_ready(request_id, expected_revision=expected_revision, cancel=cancel)
        chosen = [
            (item, path)
            for item, path in zip(verified.record.results, verified.paths, strict=True)
            if item.asset.asset_id == asset_id
        ]
        if len(chosen) != 1:
            raise ResultError("Choose one saved model result")
        item, path = chosen[0]
        if item.asset.media_type not in splats.MEDIA_FORMATS:
            raise ResultError("Choose a saved SPZ, PLY or .splat result")
        splat = self._decode_receipt(path, item, options, cancel)
        with self._guard():
            if self._store.get(request_id) != verified.record:
                raise StoreConflict("Result changed during model import preparation")
        return PreparedModelImport(verified, asset_id, item.asset.media_type, options, splat)

    def _decode_receipt(self, path, item, options, cancel):
        receipt = item.receipt
        try:
            source, before = _open(path)
        except (OSError, TransferError):
            raise ResultError("Saved result files could not be verified") from None
        failure = None
        with source:
            try:
                if before.st_size != receipt.size:
                    raise ResultError(
                        "The saved result changed while it was prepared; verify it again"
                    )
                reader = _ReceiptReader(source, receipt, cancel)
                try:
                    splat = splats.decode(
                        reader,
                        item.asset.media_type,
                        options=options,
                        size=receipt.size,
                        cancel=cancel,
                    )
                except splats.SplatError as error:
                    # Report a changed file before a decoder message about its bytes.
                    failure, splat = str(error), None
                unchanged = reader.matches() and _stamp(before) == _stamp(os.fstat(source.fileno()))
            except OSError:
                raise ResultError("The saved result could not be read") from None
        if not unchanged:
            raise ResultError("The saved result changed while it was prepared; verify it again")
        if failure is not None:
            raise ResultError(failure)
        return splat

    def verify_ready(self, request_id, *, expected_revision, cancel=None):
        """Rehash every saved receipt; a set `cancel` stops before the next receipt."""
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
                if cancel is not None and cancel.is_set():
                    raise splats.SplatCancelled("Splat preparation cancelled")
                paths.append(self._downloader.verify(directory, item.receipt))
            # Stale verification cannot authorize a subsequent application.
            if self._store.get(request_id) != current:
                raise StoreConflict("Result job changed during verification")
            return VerifiedResults(current, tuple(paths))
        except (StoreError, splats.SplatCancelled):
            raise
        except Exception:
            raise ResultError("Saved result files could not be verified") from None
