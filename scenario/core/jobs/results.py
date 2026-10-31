# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Scoped result commands using SDK metadata and credential-free storage transfer."""

import hashlib
import os
import re
import stat
import tempfile
import threading
from dataclasses import asdict, dataclass, field, replace
from pathlib import Path

from ..api.sdk_adapter import AdapterError
from ..config import ext_for_mime
from ..scene import splats
from ..scene.model_formats import MATERIAL_MEDIA_TYPES, ModelFormat, model_format
from ..scene.panorama import MAX_FILE_BYTES, world_candidate
from . import playback, result_files
from . import result_previews as previews
from .result_metadata import (
    REWRITTEN_MESH_TYPES,
    original_media_type,
    panorama_projection,
    texture_role,
)
from .store import JobState, ResultAsset, StoreConflict, StoredJob, StoreError, _identity, _json
from .transfers import (
    PartialDownload,
    ResultDownloader,
    TransferError,
    TransferInterrupted,
    _root,
)
from .upload_sources import _open, _stamp

# Originals carry no size metadata, so the World file limit bounds each transfer,
# EXR or WAV (128 MiB is about 11 minutes of 48 kHz 16-bit stereo audio).
MAX_ORIGINAL_BYTES = MAX_FILE_BYTES


# A failed storage transfer is tried again after these waits, each time with a
# fresh signed URL from the SDK; three attempts in all before download_failed.
DOWNLOAD_RETRY_DELAYS = (1.0, 3.0)
DOWNLOAD_ATTEMPTS = len(DOWNLOAD_RETRY_DELAYS) + 1


class ResultError(RuntimeError):
    """Sanitized result failure; review saved progress, never regenerate implicitly."""


class DownloadCanceled(ResultError):
    """The download's cancel event stopped it; no receipt or partial file was saved."""


class _Canceled(Exception):
    """The download's cancel event was set; it ends without a receipt."""


@dataclass(frozen=True)
class VerifiedResults:
    record: StoredJob
    paths: tuple[Path | None, ...]


MAX_PROMPT_BYTES = 65536
# Read-only previews accept interrupted applications: they never touch the scene.
PREVIEW_STATES = frozenset(
    {JobState.READY, JobState.APPLYING, JobState.APPLY_FAILED, JobState.APPLIED}
)
PREVIEW_METADATA_CHUNK = 100
# Leading bytes of a saved image read for its declared size in the World offer,
# the bound the preview lane uses for a still's declared layout. A JPEG frame
# header or an OpenEXR header beyond them reads as undeclared.
WORLD_HEADER_BYTES = previews.LOCAL_HEADER_BYTES


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


def _unverified_state(path, receipt):
    """Why a saved file failed verification: unavailable when it could not be read.

    The verifier reports a read failure like a mismatch. A regular file of the
    receipt's size that cannot be read is unavailable and checked again later;
    anything else, including bytes that match through an unsafe path, is changed.
    """
    try:
        info = os.lstat(path)
        if not stat.S_ISREG(info.st_mode) or info.st_size != receipt.size:
            return result_files.CHANGED
        flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_BINARY", 0)
        flags |= getattr(os, "O_NONBLOCK", 0)
        digest = hashlib.sha256()
        with os.fdopen(os.open(path, flags), "rb") as source:
            while chunk := source.read(1 << 20):
                digest.update(chunk)
    except OSError:
        return result_files.UNAVAILABLE
    return result_files.CHANGED


def _directory_keys(record):
    """Include all scope components and request identity, not just asset names."""
    return (
        hashlib.sha256(_json(asdict(record.intent.scope)).encode()).hexdigest(),
        hashlib.sha256(record.intent.request_id.encode()).hexdigest(),
    )


def _download_url(record, source):
    """Select the documented destination for the saved file, never a fallback."""
    url = record.get("originalFileUrl" if source == "original" else "url")
    if not isinstance(url, str) or not url:
        raise ResultError("Scenario returned no result download destination")
    return url


def _reviewing(record):
    """Whether a saved record is a `remote` workflow job whose steps may wait."""
    return (
        record is not None
        and record.intent.operation == "workflow"
        and record.state == JobState.REMOTE
        and record.remote_job_id is not None
    )


def _changed(target):
    if target.kind == previews.REVIEW:
        return "This workflow job is no longer waiting; review its step again"
    return "This saved result changed; preview it again"


def _job_parents(records):
    """Asset ID -> the other result of this job it was generated from (`metadata.parentId`).

    `records` maps each of the job's asset IDs to its retrieved asset. A parent
    outside the job, such as an input asset, the asset itself or any other value is
    left out, and so is every asset on a parent cycle: lineage never refuses a manifest.
    """
    parents = {}
    for identifier, record in records.items():
        metadata = record.get("metadata")
        parent = metadata.get("parentId") if isinstance(metadata, dict) else None
        if isinstance(parent, str) and parent != identifier and parent in records:
            parents[identifier] = parent
    cyclic = set()
    for identifier in parents:
        current, steps = parents.get(identifier), 0
        while current is not None and current != identifier and steps < len(parents):
            current, steps = parents.get(current), steps + 1
        if current == identifier:
            cyclic.add(identifier)
    return {key: value for key, value in parents.items() if key not in cyclic}


def _on_demand(assets):
    """Mark the OBJ, MTL and texture maps Scenario derives from a GLB result of the job.

    They hold the GLB's mesh and maps again, in other files; the GLB imports with its
    maps embedded, so they wait for an explicit fetch. Lineage decides, never a
    filename: a copy names the GLB as its parent. When another result descends from
    a copy, every file downloads with the job.
    """
    glbs = {asset.asset_id for asset in assets if model_format(asset.media_type) == ModelFormat.GLB}
    copies = {
        asset.asset_id
        for asset in assets
        if asset.parent_id in glbs
        and (
            model_format(asset.media_type) == ModelFormat.OBJ
            or asset.media_type in MATERIAL_MEDIA_TYPES
            or asset.texture_role is not None
        )
    }
    if any(asset.parent_id in copies for asset in assets):
        return assets
    return [replace(asset, on_demand=asset.asset_id in copies) for asset in assets]


def _asset(record, identifier, name, *, source=None):
    """Describe the file to save; a saved manifest passes its own source when refreshing."""
    if record.get("id") != identifier or record.get("status") != "success":
        raise ResultError("Scenario returned an unavailable or different result asset")
    original = original_media_type(record)
    if source is None:
        source = "original" if original is not None else "asset"
    if source == "original":
        if original is None:
            raise ResultError("Scenario no longer declares the saved original result file")
        # The asset's size describes its preview; the original has no size metadata.
        _download_url(record, source)
        media_type, size = original, None
    else:
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
        media_type, size = record.get("mimeType"), int(size)
    try:
        return ResultAsset(
            identifier,
            name,
            media_type,
            size,
            texture_role=texture_role(record),
            source=source,
            projection=panorama_projection(record),
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
        # (request_id, asset_id) -> result_files.FileCheck: the identity of each
        # file this session verified against its receipt. Memory only, so a
        # restarted session checks its files again; see verified_files.
        self._verified_files = {}
        self._verified_lock = threading.Lock()

    def _file_path(self, record, receipt):
        """Where a receipt's file is saved, for display; verification resolves it safely."""
        return os.fspath(Path(self._root, *_directory_keys(record), receipt.name))

    def _verify_saved(self, record, directory, asset_id, receipt):
        """Verify one receipt and remember the file's identity as this session hashed it."""
        path = self._file_path(record, receipt)
        before = result_files.file_stamp(path)
        verified = self._downloader.verify(directory, receipt)
        if before is not None and result_files.file_stamp(path) == before:
            check = result_files.FileCheck(receipt.sha256, result_files.VERIFIED, path, before)
            key = (record.intent.request_id, asset_id)
            with self._verified_lock:
                # Newest last; beyond the limit the oldest is forgotten and its
                # file is simply checked again by a worker when asked.
                self._verified_files.pop(key, None)
                self._verified_files[key] = check
                while len(self._verified_files) > result_files.VERIFIED_LIMIT:
                    del self._verified_files[next(iter(self._verified_files))]
        return verified

    def verified_files(self, request_id):
        """(asset_id, FileCheck) pairs this session verified for a job; reads no file."""
        with self._verified_lock:
            return tuple(
                (asset_id, check)
                for (owner, asset_id), check in self._verified_files.items()
                if owner == request_id
            )

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

    def _request(self, method, identifier, **options):
        with self._guard():
            pass
        try:
            return method(identifier, **options)
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
        saved = {item.asset.asset_id for item in current.results}
        try:
            for identifier in identifiers:
                _identity(identifier)
            if len(set(identifiers)) != len(identifiers) or (saved and asset_id not in saved):
                raise ValueError
            # Scenario can replace a finished model job's output list minutes after
            # success (seen with model_scenario-llm). The output this job saved stays
            # readable when its own asset record names this job as its parent.
            replaced = asset_id not in identifiers
            if replaced and asset_id not in saved:
                raise ValueError
        except ValueError:
            raise ResultError("The selected text asset does not match this saved job") from None
        text = self._read_text_asset(asset_id, job_id=current.remote_job_id if replaced else None)
        with self._guard():
            if self._store.get(request_id) != current:
                raise StoreConflict("Model result changed; reload before acting")
            return ModelTextResult(current, asset_id, text)

    def _read_text_asset(self, identifier, *, job_id=None):
        asset = self._request(self._adapter.asset, identifier, original_assets=True)
        if (
            asset.get("id") != identifier
            or asset.get("status") != "success"
            or asset.get("kind") != "text"
            or asset.get("mimeType") != "text/plain"
        ):
            raise ResultError("Scenario returned an unavailable or unsupported text asset")
        metadata = asset.get("metadata")
        if job_id is not None and (
            not isinstance(metadata, dict) or metadata.get("parentJobId") != job_id
        ):
            raise ResultError("The selected text asset does not match this saved job")
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
        assets, records = [], {}
        for index, identifier in enumerate(identifiers):
            # Downloads need the untransformed bytes that mimeType and size describe.
            record = self._request(self._adapter.asset, identifier, original_assets=True)
            # Provider filenames/URL paths never choose local storage paths.
            mime = original_media_type(record) or record.get("mimeType")
            suffix = ext_for_mime(mime) if isinstance(mime, str) else "bin"
            name = f"{index:03d}-{hashlib.sha256(identifier.encode()).hexdigest()[:24]}.{suffix}"
            assets.append(_asset(record, identifier, name))
            records[identifier] = record
        parents = _job_parents(records)
        assets = _on_demand(
            [replace(asset, parent_id=parents.get(asset.asset_id)) for asset in assets]
        )
        with self._guard():
            return self._store.set_results(
                request_id, tuple(assets), expected_revision=current.revision
            )

    def _directory(self, record, *, create=True):
        if self._root is None:
            raise ResultError("Result storage has not been configured")
        root = _root(self._root)
        for key in _directory_keys(record):
            child = root / key
            if create:
                child.mkdir(mode=0o700, exist_ok=True)
            root = _root(child)
        return root

    def download(self, request_id, *, expected_revision, cancel=None):
        """Download every unfinished result but on-demand copies; ``cancel`` stops without a receipt."""
        if cancel is not None and not callable(getattr(cancel, "is_set", None)):
            raise ResultError("Use a cancellation event")
        with self._store.result_transfer_lock(request_id):
            return self._download(request_id, expected_revision=expected_revision, cancel=cancel)

    def _download(self, request_id, *, expected_revision, cancel):
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
                    self._verify_saved(current, directory, item.asset.asset_id, item.receipt)
                    continue
                if item.asset.on_demand:
                    continue
                receipt = self._transfer(item, directory, cancel)
                self._verify_saved(current, directory, item.asset.asset_id, receipt)
                current = self._store.record_download(
                    request_id,
                    item.asset.asset_id,
                    receipt,
                    expected_revision=current.revision,
                    **(
                        {"allow_mesh_size_correction": True}
                        if item.asset.media_type in REWRITTEN_MESH_TYPES
                        else {}
                    ),
                )
            return self._store.transition(
                request_id, expected_revision=current.revision, state=JobState.READY
            )
        except StoreError:
            # Preserve an uncertain disk write. Never claim failure was saved.
            raise
        except Exception as error:
            self._store.transition(
                request_id, expected_revision=current.revision, state=JobState.DOWNLOAD_FAILED
            )
            if isinstance(error, _Canceled):
                raise DownloadCanceled(
                    "Result download was canceled; no partial file was saved and Resume "
                    "starts it again"
                ) from None
            raise ResultError(
                "Result download did not complete; review saved files before retrying"
            ) from None

    def fetch(self, request_id, *, expected_revision, asset_ids, cancel=None):
        """Download on-demand copies of a completed job; ``cancel`` stops without a receipt.

        The job keeps its state: each verified copy saves its receipt, and a failure
        or a stop leaves the rest to fetch again. Copies already saved are verified.
        """
        if cancel is not None and not callable(getattr(cancel, "is_set", None)):
            raise ResultError("Use a cancellation event")
        try:
            selected = tuple(_identity(value) for value in asset_ids)
        except (TypeError, ValueError):
            raise ResultError("Choose on-demand copies of this job") from None
        with self._store.result_transfer_lock(request_id):
            current = self._current(
                request_id,
                expected_revision,
                {JobState.READY, JobState.APPLY_FAILED, JobState.APPLIED},
            )
            chosen = [item for item in current.results if item.asset.asset_id in selected]
            if (
                not selected
                or len(set(selected)) != len(selected)
                or len(chosen) != len(selected)
                or not all(item.asset.on_demand for item in chosen)
            ):
                raise ResultError("Choose on-demand copies of this job")
            if self._downloader is None:
                raise ResultError("Result storage has not been configured")
            try:
                directory = self._directory(current)
            except (OSError, ValueError, TransferError):
                raise ResultError("Could not prepare private result storage") from None
            try:
                for item in chosen:
                    with self._guard():
                        pass
                    if item.receipt is not None:
                        self._verify_saved(current, directory, item.asset.asset_id, item.receipt)
                        continue
                    # A copy saved without its receipt (Blender quit, or another process
                    # changed the job first) was never trusted: fetch it again over it.
                    orphan = directory / item.asset.name
                    if orphan.is_symlink() or orphan.exists():
                        orphan.unlink()
                    receipt = self._transfer(item, directory, cancel)
                    self._verify_saved(current, directory, item.asset.asset_id, receipt)
                    with self._guard():
                        # A copy's receipt only adds a saved file: record it on the
                        # latest revision, which the store checks still accepts it.
                        latest = self._store.get(request_id) or current
                        current = self._store.record_fetch(
                            request_id,
                            item.asset.asset_id,
                            receipt,
                            expected_revision=latest.revision,
                            **(
                                {"allow_mesh_size_correction": True}
                                if item.asset.media_type in REWRITTEN_MESH_TYPES
                                else {}
                            ),
                        )
                return current
            except StoreError:
                # Preserve an uncertain disk write. Never claim failure was saved.
                raise
            except _Canceled:
                raise DownloadCanceled(
                    "The download was stopped; no partial file was saved and choosing the "
                    "result again starts it again"
                ) from None
            except Exception:
                raise ResultError(
                    "The files this result needs did not download; try again"
                ) from None

    def _fresh_asset(self, item):
        """Read the asset again for a new signed URL; its saved description must hold."""
        response = self._request(self._adapter.asset, item.asset.asset_id, original_assets=True)
        # The saved manifest chose the file; a manifest saved before the
        # extension accepted an original keeps the asset file.
        fresh = _asset(response, item.asset.asset_id, item.asset.name, source=item.asset.source)
        if item.asset.media_type in REWRITTEN_MESH_TYPES:
            # Legacy ingestion rewrote file references without updating
            # properties.size; identity/type/digest checks remain exact.
            fresh = replace(fresh, expected_size=item.asset.expected_size)
        if item.asset.texture_role is None:
            # Legacy/unclassified results keep unknown semantics. A later
            # response may not grant a new material role to saved bytes.
            fresh = replace(fresh, texture_role=None)
        if item.asset.projection is None:
            # Likewise, a later response cannot relabel saved bytes as 360.
            fresh = replace(fresh, projection=None)
        # Lineage, and the fetch it decided, are kept as saved; they never refuse a download.
        fresh = replace(fresh, parent_id=item.asset.parent_id, on_demand=item.asset.on_demand)
        if fresh != item.asset:
            raise ResultError("Result metadata changed after the manifest was saved")
        return _download_url(response, item.asset.source)

    def _transfer(self, item, directory, cancel):
        """At most DOWNLOAD_ATTEMPTS storage attempts, each with a fresh signed URL.

        Only a retryable transport failure, or an SDK read failure while
        refreshing the URL, is tried again. A strong ETag lets the next attempt
        resume the staged bytes; nothing partial outlives this. Only an
        interruption caused by the set cancel event reports cancellation.
        """
        waiter = cancel if cancel is not None else threading.Event()
        options = {}
        if item.asset.media_type in REWRITTEN_MESH_TYPES:
            options["allow_size_mismatch"] = True
        if item.asset.source == "original":
            options["max_bytes"] = MAX_ORIGINAL_BYTES
        partial = PartialDownload()
        attempt = 0
        try:
            while True:
                if attempt and waiter.wait(DOWNLOAD_RETRY_DELAYS[attempt - 1]):
                    raise _Canceled()
                with self._guard():
                    pass
                try:
                    url = self._fresh_asset(item)
                except AdapterError:
                    # A transient SDK read failure costs one attempt; a changed
                    # manifest (ResultError) still stops at once.
                    attempt += 1
                    if attempt == DOWNLOAD_ATTEMPTS:
                        raise
                    continue
                try:
                    return self._downloader.download(
                        url,
                        root=directory,
                        name=item.asset.name,
                        expected_size=item.asset.expected_size,
                        expected_sha256=item.asset.expected_sha256,
                        cancel=cancel,
                        partial=partial,
                        **options,
                    )
                except TransferError as error:
                    if (
                        isinstance(error, TransferInterrupted)
                        and cancel is not None
                        and cancel.is_set()
                    ):
                        raise _Canceled() from None
                    attempt += 1
                    if not error.retryable or attempt == DOWNLOAD_ATTEMPTS:
                        raise
        finally:
            partial.discard()

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
                        self._verify_saved(current, directory, item.asset.asset_id, item.receipt)
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
                if all(item.receipt is not None or item.asset.on_demand for item in current.results)
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
        if path is None:
            raise ResultError("Download the selected result before inspecting its media")
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
        """Rehash every saved receipt; a set `cancel` stops before the next receipt.

        An on-demand copy not fetched yet has no path.
        """
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
                if item.receipt is None and item.asset.on_demand:
                    paths.append(None)
                    continue
                paths.append(
                    self._verify_saved(current, directory, item.asset.asset_id, item.receipt)
                )
            # Stale verification cannot authorize a subsequent application.
            if self._store.get(request_id) != current:
                raise StoreConflict("Result job changed during verification")
            return VerifiedResults(current, tuple(paths))
        except (StoreError, splats.SplatCancelled):
            raise
        except Exception:
            raise ResultError("Saved result files could not be verified") from None

    def preview_targets(self, request_id, asset_ids=None):
        """Receipt-bound preview targets of one saved job, without file or network access."""
        selected = None
        if asset_ids is not None:
            try:
                selected = tuple(_identity(value) for value in asset_ids)
            except (TypeError, ValueError):
                raise ResultError("Choose saved result assets from this job") from None
        with self._guard():
            record = self._store.get(request_id)
        if record is None or record.state not in PREVIEW_STATES:
            raise ResultError("Download the saved result before previewing it")
        known = {item.asset.asset_id for item in record.results}
        if selected is not None and (
            not selected or len(set(selected)) != len(selected) or not set(selected) <= known
        ):
            raise ResultError("Choose saved result assets from this job")
        return tuple(
            previews.PreviewTarget(
                request_id,
                item.asset.asset_id,
                item.asset.media_type,
                previews.preview_kind(item.asset.media_type),
                previews.PreviewKey.for_result(self._store.scope, request_id, item),
                item.receipt,
            )
            for item in record.results
            if item.receipt is not None and (selected is None or item.asset.asset_id in selected)
        )

    def review_targets(self, request_id, asset_ids):
        """Preview targets for assets a saved workflow job's waiting step lists.

        Reads the scoped store only. The job must be a `remote` workflow job
        with a known remote ID; the caller, which owns the step projection,
        supplies the step's asset IDs. Each target binds the scope, request,
        remote job and asset, and is fetched from Scenario, never from results.
        """
        try:
            selected = tuple(_identity(value) for value in asset_ids)
        except (TypeError, ValueError):
            raise ResultError("Choose the review assets of a waiting workflow step") from None
        if not 1 <= len(selected) <= previews.REVIEW_ASSET_LIMIT or len(set(selected)) != len(
            selected
        ):
            raise ResultError("Choose the review assets of a waiting workflow step")
        with self._guard():
            record = self._store.get(request_id)
        if not _reviewing(record):
            raise ResultError("Previews need a saved workflow job that waits for a decision")
        return tuple(
            previews.PreviewTarget.for_review(
                self._store.scope, request_id, record.remote_job_id, asset_id
            )
            for asset_id in selected
        )

    def _preview_record(self, target):
        """The current saved record if it still holds the target's exact receipt.

        A review target instead needs the same `remote` workflow job.
        """
        with self._guard():
            record = self._store.get(target.request_id)
        if target.kind == previews.REVIEW:
            if not _reviewing(record) or target != previews.PreviewTarget.for_review(
                self._store.scope, target.request_id, record.remote_job_id, target.asset_id
            ):
                return None
            return record
        if record is None or record.state not in PREVIEW_STATES:
            return None
        for item in record.results:
            if (
                item.asset.asset_id == target.asset_id
                and item.asset.media_type == target.media_type
                and item.receipt == target.receipt
            ):
                return record
        return None

    def _preview_check(self, cancel):
        with self._guard():
            if cancel.is_set():
                raise previews.PreviewCanceled("Preview preparation was canceled")

    def _preview_local(self, cache, item, rendition, record, cancel):
        """Resolve one rendition from the cache or a local decode request; None needs Scenario."""
        state, target = previews.PreviewState, item.target
        if record is None:
            return previews.RenditionOutcome(rendition, state.FAILED, reason=_changed(target))
        if not previews.supports(target.kind, rendition):
            return previews.RenditionOutcome(
                rendition, state.UNSUPPORTED, reason="No preview is available for this format"
            )
        if item.force:
            cache.forget(target.key, rendition)
        cached = cache.read(target.key, rendition)
        if isinstance(cached, previews.CachedPreview):
            return previews.RenditionOutcome(rendition, state.READY, preview=cached)
        if isinstance(cached, previews.MissingPreview):
            return previews.RenditionOutcome(
                rendition,
                state.MISSING,
                reason="Scenario has no preview for this result; use Retry",
            )
        if not previews.is_local(target.kind, rendition):
            return None
        try:
            source = self._directory(record, create=False) / target.receipt.name
            request = previews.prepare_decode(cache, target, rendition, source, cancel)
        except previews.PreviewCanceled:
            raise
        except previews.PreviewError as error:
            return previews.RenditionOutcome(rendition, state.FAILED, reason=str(error))
        except (ResultError, TransferError, OSError, ValueError):
            return previews.RenditionOutcome(
                rendition, state.FAILED, reason="Saved result files are unavailable"
            )
        return previews.RenditionOutcome(rendition, state.DECODE, request=request)

    def _preview_metadata(self, identifiers):
        """Bulk reads for every batch size, so an absent asset has one meaning.

        A deleted or unavailable asset is omitted from ``get_bulk`` whether the
        batch holds one target or many; it is then polled like a late preview
        and marked missing at the window's end, never failed by batch size.
        """
        records = {}
        for start in range(0, len(identifiers), PREVIEW_METADATA_CHUNK):
            chunk = identifiers[start : start + PREVIEW_METADATA_CHUNK]
            with self._guard():
                pass
            try:
                records.update(self._adapter.bulk_assets(chunk))
            except ValueError:
                raise ResultError("Scenario preview metadata could not be retrieved") from None
        return records

    def _preview_remote(self, cache, work, remote, outcomes, cancel):
        """Read server preview metadata once per batch, then fetch available renditions."""
        state = previews.PreviewState

        def settle(index, rendition, value, **details):
            outcomes[index][rendition] = previews.RenditionOutcome(rendition, value, **details)

        if not self._adapter.network_allowed():
            for index, rendition in remote:
                settle(index, rendition, state.OFFLINE, reason="Online access is disabled")
            return
        identifiers = tuple(dict.fromkeys(work[index].target.asset_id for index, _ in remote))
        try:
            records = self._preview_metadata(identifiers)
        except (AdapterError, ResultError):
            for index, rendition in remote:
                settle(
                    index,
                    rendition,
                    state.FAILED if work[index].final else state.PENDING,
                    reason="Scenario preview metadata could not be read",
                )
            return
        sources = {}
        for index, rendition in remote:
            self._preview_check(cancel)
            item = work[index]
            try:
                if index not in sources:
                    record = records.get(item.target.asset_id)
                    sources[index] = (
                        {}
                        if record is None
                        else previews.review_sources(record, item.target)
                        if item.target.kind == previews.REVIEW
                        else previews.server_sources(record, item.target)
                    )
                source = sources[index].get(rendition)
                if source is not None and not self._adapter.network_allowed():
                    settle(index, rendition, state.OFFLINE, reason="Online access is disabled")
                elif source is not None:
                    preview = previews.fetch(
                        cache, self._downloader, item.target, rendition, source, cancel
                    )
                    settle(index, rendition, state.READY, preview=preview)
                elif item.final:
                    cache.mark_missing(item.target.key, rendition)
                    settle(
                        index,
                        rendition,
                        state.MISSING,
                        reason="Scenario has no preview for this result; use Retry",
                    )
                else:
                    settle(
                        index,
                        rendition,
                        state.PENDING,
                        reason="Waiting for Scenario to prepare the preview",
                    )
            except previews.PreviewCanceled:
                raise
            except previews.PreviewUnavailable:
                # Storage can redirect elsewhere or fail before it serves a new
                # preview, so an incomplete transfer polls again like a late one.
                if not self._adapter.network_allowed():
                    settle(index, rendition, state.OFFLINE, reason="Online access is disabled")
                elif item.final:
                    settle(
                        index,
                        rendition,
                        state.FAILED,
                        reason="The preview download did not complete; use Retry",
                    )
                else:
                    settle(
                        index,
                        rendition,
                        state.PENDING,
                        reason="The preview download did not complete; retrying",
                    )
            except previews.PreviewError as error:
                settle(index, rendition, state.FAILED, reason=str(error))

    def _maintain_previews(self, cache):
        cache.sweep()
        cache.evict()

    def maintain_previews(self, *, root, cancel):
        """Sweep abandoned work and evict beyond the cache budget; no job read or network."""
        self._preview_check(cancel)
        self._maintain_previews(previews.PreviewCache(root))

    def prepare_previews(self, work, *, root, cancel, maintain=False):
        """Resolve preview renditions on the preview lane; never generate, apply or spend.

        Verified cache entries are reused. Images and audio get decode requests
        holding a private copy rehashed against the saved receipt. Server stills
        and clips read SDK asset metadata once per batch with ``get_bulk``, then
        use the bounded result downloader and its storage hosts; a transfer that
        does not complete stays pending until the batch is ``final``. The caller
        owns returned decode requests and must finish or discard them.
        """
        if self._downloader is None:
            raise ResultError("Result storage has not been configured")
        work = tuple(work)
        if not 1 <= len(work) <= 128 or not all(
            isinstance(item, previews.PreviewWork) for item in work
        ):
            raise ValueError("Use a bounded preview batch")
        cache = previews.PreviewCache(root)
        if maintain:
            self._maintain_previews(cache)
        outcomes = [{} for _ in work]
        try:
            remote = []
            for index, item in enumerate(work):
                self._preview_check(cancel)
                record = self._preview_record(item.target)
                for rendition in item.renditions:
                    outcome = self._preview_local(cache, item, rendition, record, cancel)
                    if outcome is None:
                        remote.append((index, rendition))
                    else:
                        outcomes[index][rendition] = outcome
            if remote:
                self._preview_remote(cache, work, remote, outcomes, cancel)
            changed = previews.RenditionOutcome
            for index, item in enumerate(work):
                if self._preview_record(item.target) is None:
                    for rendition, outcome in tuple(outcomes[index].items()):
                        if outcome.request is not None:
                            cache.discard(outcome.request.directory)
                        outcomes[index][rendition] = changed(
                            rendition, previews.PreviewState.FAILED, reason=_changed(item.target)
                        )
            return previews.PreviewBatch(
                self._store.scope,
                tuple(
                    previews.PreviewOutcome(
                        item.target, tuple(outcomes[index][r] for r in item.renditions)
                    )
                    for index, item in enumerate(work)
                ),
            )
        except BaseException:
            for result in outcomes:
                for outcome in result.values():
                    if outcome.request is not None:
                        cache.discard(outcome.request.directory)
            raise

    def playback_copy(
        self,
        request_id,
        *,
        expected_revision,
        asset_id,
        root,
        cancel,
        reuse=None,
        discard=(),
        keep=(),
    ):
        """Copy one downloaded video or audio receipt privately for a desktop player.

        Preview-lane work that never fetches, generates, applies or writes the
        job store. ``discard`` names copies the owner evicted and ``keep`` the
        ones it still uses; both are handled first, and stale others are swept,
        even when the request is then refused. An unchanged ``reuse``
        copy of the same receipt is returned instead of copying again. The copy
        is then rechecked at receipt level: an unrelated revision, such as a
        concurrent strip application, keeps it, while a changed receipt discards it.
        """
        # Evicted and stale copies go first, even if this request is refused.
        root = playback.playback_root(root)
        for directory in discard:
            playback.discard(root, directory)
        playback.sweep(root, keep=keep)
        current = self._current(request_id, expected_revision, PREVIEW_STATES)
        chosen = [
            item
            for item in current.results
            if item.asset.asset_id == asset_id
            and item.receipt is not None
            and playback.kind(item.asset.media_type) is not None
        ]
        if len(chosen) != 1:
            raise ResultError("Choose one downloaded saved video or audio result")
        item = chosen[0]
        target = previews.PreviewTarget(
            request_id,
            asset_id,
            item.asset.media_type,
            playback.kind(item.asset.media_type),
            previews.PreviewKey.for_result(self._store.scope, request_id, item),
            item.receipt,
        )
        if (
            isinstance(reuse, playback.PlaybackCopy)
            and reuse.key == target.key
            and playback.unchanged(reuse)
        ):
            copy = reuse
        else:
            try:
                source = self._directory(current, create=False) / item.receipt.name
            except (ResultError, TransferError, OSError):
                raise ResultError("Saved result files are unavailable") from None
            copy = playback.make_copy(root, target, source, cancel)
        with self._guard():
            latest = self._store.get(request_id)
        if (
            latest is None
            or latest.state not in PREVIEW_STATES
            or not any(
                result.asset.asset_id == asset_id
                and result.asset.media_type == item.asset.media_type
                and result.receipt == item.receipt
                for result in latest.results
            )
        ):
            if copy is not reuse:
                playback.discard(root, copy.directory)
            raise StoreConflict("Result changed during playback preparation")
        return copy

    def world_sizes(self, targets, *, cancel):
        """Declared pixel sizes of saved World candidates, read from their file headers.

        Preview-lane work for the World offer only. Each target is a
        (request_id, asset_id, sha256) triple naming one downloaded result; the
        answer appends (width, height), or None when the job no longer holds
        that receipt as a World candidate, its file cannot be read or its first
        ``WORLD_HEADER_BYTES`` declare no size. It reads only those bytes: it
        never hashes, fetches, applies or writes the job store, and World
        application still checks the actual file. One check takes at most the
        preview scheduler's ``BATCH_LIMIT`` targets, so it holds the single
        preview lane no longer than a preview batch does.
        """
        # Imported here: the scheduler imports the workers, which import this module.
        from .preview_scheduler import BATCH_LIMIT

        try:
            targets = tuple(
                (_identity(request_id), _identity(asset_id), sha256)
                for request_id, asset_id, sha256 in targets
            )
        except (TypeError, ValueError):
            raise ResultError("Choose saved World candidates to measure") from None
        if not 1 <= len(targets) <= BATCH_LIMIT or not all(
            isinstance(sha256, str) and re.fullmatch(r"[a-f0-9]{64}", sha256)
            for *_, sha256 in targets
        ):
            raise ResultError("Choose saved World candidates to measure")
        sizes = []
        for target in targets:
            if cancel.is_set():
                raise previews.PreviewCanceled("The World size check was canceled")
            sizes.append((*target, self._world_size(*target)))
        return tuple(sizes)

    def check_files(self, targets, *, cancel):
        """Rehash downloaded results of ready jobs for status display; see result_files.

        Preview-lane work. Each target is a (request_id, asset_id, sha256)
        triple; the answer appends a ``FileCheck`` (unavailable when the file
        changed while it was hashed), or None when this scope's store no longer
        holds that receipt in a ready job. It never fetches, applies or writes
        the job store.
        """
        # Imported here: the scheduler imports the workers, which import this module.
        from .preview_scheduler import BATCH_LIMIT

        try:
            targets = tuple(
                (_identity(request_id), _identity(asset_id), sha256)
                for request_id, asset_id, sha256 in targets
            )
        except (TypeError, ValueError):
            raise ResultError("Choose saved results to check") from None
        if not 1 <= len(targets) <= BATCH_LIMIT or not all(
            isinstance(sha256, str) and re.fullmatch(r"[a-f0-9]{64}", sha256)
            for *_, sha256 in targets
        ):
            raise ResultError("Choose saved results to check")
        if self._root is None or self._downloader is None:
            raise ResultError("Result storage has not been configured")
        checks = []
        for target in targets:
            if cancel.is_set():
                raise previews.PreviewCanceled("The result file check was canceled")
            checks.append((*target, self._check_file(*target)))
        return tuple(checks)

    def _check_file(self, request_id, asset_id, sha256):
        with self._guard():
            record = self._store.get(request_id)
        if record is None or record.state not in result_files.READY_STATES:
            return None
        receipt = next(
            (
                item.receipt
                for item in record.results
                if item.asset.asset_id == asset_id
                and item.receipt is not None
                and item.receipt.sha256 == sha256
            ),
            None,
        )
        if receipt is None:
            return None
        path = self._file_path(record, receipt)
        before = result_files.file_stamp(path)
        if before is None:
            return result_files.FileCheck(sha256, result_files.MISSING, path, None)
        try:
            self._downloader.verify(self._directory(record, create=False), receipt)
            state = result_files.VERIFIED
        except Exception:
            state = _unverified_state(path, receipt)
        if result_files.file_stamp(path) != before:
            # Changed while it was hashed: retried after a delay, not on every poll.
            return result_files.FileCheck(sha256, result_files.UNAVAILABLE, path)
        return result_files.FileCheck(sha256, state, path, before)

    def _world_size(self, request_id, asset_id, sha256):
        with self._guard():
            record = self._store.get(request_id)
        if record is None or record.state not in PREVIEW_STATES:
            return None
        item = next(
            (
                item
                for item in record.results
                if item.asset.asset_id == asset_id
                and item.receipt is not None
                and item.receipt.sha256 == sha256
                and world_candidate(item.asset.media_type, item.asset.texture_role)
            ),
            None,
        )
        if item is None:
            return None
        try:
            source, _ = _open(self._directory(record, create=False) / item.receipt.name)
            with source:
                head = source.read(WORLD_HEADER_BYTES)
        except (OSError, ResultError, TransferError):
            return None
        return previews.local_image_size(head)

    def _owned_preview(self, request):
        if not isinstance(request, previews.DecodeRequest) or request.key.scope != (
            previews.scope_digest(self._store.scope)
        ):
            raise ResultError("Use a preview request issued for this connection")

    def finish_preview(self, request, *, root, envelope=None):
        """Validate Blender's decoded still or audio envelope and cache it."""
        self._owned_preview(request)
        with self._guard():
            pass
        return previews.finish_decode(previews.PreviewCache(root), request, envelope=envelope)

    def decode_preview(self, request, *, root, waveform, cancel):
        """Decode an owned audio envelope request in an offline Blender child and cache it."""
        self._owned_preview(request)
        with self._guard():
            pass
        return previews.decode_envelope(previews.PreviewCache(root), request, waveform, cancel)

    def discard_preview(self, request, *, root):
        """Remove an unused decode request's private copy without caching anything."""
        self._owned_preview(request)
        previews.PreviewCache(root).discard(request.directory)
