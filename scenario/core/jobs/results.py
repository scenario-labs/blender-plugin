# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Scoped result commands using SDK metadata and credential-free storage transfer."""

import hashlib
import tempfile
from dataclasses import asdict, dataclass, field, replace
from pathlib import Path

from ..api.sdk_adapter import AdapterError
from ..config import ext_for_mime
from . import result_previews as previews
from .result_metadata import REWRITTEN_MESH_TYPES, texture_role
from .store import JobState, ResultAsset, StoreConflict, StoredJob, StoreError, _identity, _json
from .transfers import ResultDownloader, TransferError, _root


class ResultError(RuntimeError):
    """Sanitized result failure; review saved progress, never regenerate implicitly."""


@dataclass(frozen=True)
class VerifiedResults:
    record: StoredJob
    paths: tuple[Path, ...]


MAX_PROMPT_BYTES = 65536
# Read-only previews accept interrupted applications: they never touch the scene.
PREVIEW_STATES = frozenset(
    {JobState.READY, JobState.APPLYING, JobState.APPLY_FAILED, JobState.APPLIED}
)
PREVIEW_METADATA_CHUNK = 100


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

    def _preview_record(self, target):
        """The current saved record if it still holds the target's exact receipt."""
        with self._guard():
            record = self._store.get(target.request_id)
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
            return previews.RenditionOutcome(
                rendition, state.FAILED, reason="This saved result changed; preview it again"
            )
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
                    found = {} if record is None else previews.server_sources(record, item.target)
                    sources[index] = found
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
            except previews.PreviewError as error:
                settle(index, rendition, state.FAILED, reason=str(error))

    def prepare_previews(self, work, *, root, cancel, maintain=False):
        """Resolve preview renditions on the preview lane; never generate, apply or spend.

        Verified cache entries are reused. Images and audio get decode requests
        holding a private copy rehashed against the saved receipt. Server stills
        and clips read SDK asset metadata once per batch with ``get_bulk``, then
        use the bounded result downloader and its storage hosts. The caller owns returned decode
        requests and must finish or discard them.
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
            cache.sweep()
            cache.evict()
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
                            rendition,
                            previews.PreviewState.FAILED,
                            reason="This saved result changed; preview it again",
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

    def discard_preview(self, request, *, root):
        """Remove an unused decode request's private copy without caching anything."""
        self._owned_preview(request)
        previews.PreviewCache(root).discard(request.directory)
