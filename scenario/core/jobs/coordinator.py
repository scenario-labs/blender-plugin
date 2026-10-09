# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Synchronous shared commands; workers/UI/MCP integration is a separate layer."""

import hashlib
import json
import logging
import math
import threading
import time
import uuid
from contextlib import contextmanager, nullcontext
from dataclasses import dataclass, field, replace
from enum import StrEnum
from pathlib import Path
from weakref import WeakKeyDictionary, WeakValueDictionary

from ..api.sdk_adapter import Estimate, SDKAdapter
from ..schema.forms import _fields, is_file_field
from . import local_render
from .film_finishing import (
    CompositionDraft,
    validate_composition_draft,
    validate_composition_sources,
)
from .film_media import VerifiedComposition
from .results import ResultCommands, ResultError, VerifiedResults
from .store import (
    CloudJobIntent,
    FilmTaskBinding,
    FilmUploadReference,
    JobIntent,
    JobMeshSource,
    JobOrigin,
    JobScope,
    JobState,
    JobStore,
    LocalApplicationState,
    StoreConflict,
    StoredJob,
    _identity,
)
from .uploads import UploadCommands, UploadError


class QuoteError(ValueError):
    """The current request no longer matches an active, unexpired quote."""


@dataclass(frozen=True, eq=False)
class OriginQuote:
    """An exact SDK estimate bound to the origin captured before estimation."""

    scope: JobScope
    origin: JobOrigin
    estimate: Estimate = field(repr=False)
    mesh_sources: tuple[JobMeshSource, ...] = ()
    film_task: FilmTaskBinding | None = None
    composition: CompositionDraft | None = field(default=None, repr=False)


@dataclass(frozen=True)
class FilmUploadResult:
    """A saved association delivered to this caller's current captured origin."""

    scope: JobScope
    origin: JobOrigin
    reference: FilmUploadReference

    def __post_init__(self):
        if (
            not isinstance(self.scope, JobScope)
            or not isinstance(self.origin, JobOrigin)
            or not isinstance(self.reference, FilmUploadReference)
            or self.reference.scope != self.scope
        ):
            raise ValueError("Film upload result must match its selected scope and origin")


@dataclass(frozen=True)
class LocalCaptureResult:
    scope: JobScope
    origin: JobOrigin
    source_origin: JobOrigin
    media: local_render.RenderedMedia


class SubmissionUncertain(RuntimeError):
    """Do not resend; inspect/reconcile the persisted request identity."""


@dataclass(frozen=True)
class PreparedJob:
    intent: JobIntent
    expires_at: float
    estimate: Estimate = field(repr=False)
    composition: CompositionDraft | None = field(default=None, repr=False)


class RecoveryError(RuntimeError):
    """Remote evidence is missing or inconsistent; preserve local state."""


class CancellationUncertain(RecoveryError):
    """Cancellation was claimed; poll the known ID instead of replaying it."""


class ApplicationError(RuntimeError):
    """Application admission failed; preserve the result for explicit review."""


@dataclass(frozen=True, eq=False)
class ApplicationClaim:
    """An owner-issued durable claim, not a Blender mutation or frozen file bytes."""

    record: StoredJob
    paths: tuple[Path, ...]
    local_application_id: str | None = None


def _local_outcome(state):
    return {
        JobState.APPLIED: LocalApplicationState.APPLIED,
        JobState.APPLY_FAILED: LocalApplicationState.FAILED,
    }[state]


class RecoveryAction(StrEnum):
    REVIEW_QUOTE = "review_quote"
    RECONCILE_UNKNOWN = "reconcile_unknown"
    POLL_REMOTE = "poll_remote"
    DOWNLOAD_RESULT = "download_result"
    REVIEW_DOWNLOAD = "review_download"
    REVIEW_APPLICATION = "review_application"
    FINISHED = "finished"


@dataclass(frozen=True)
class RecoveryItem:
    record: StoredJob
    action: RecoveryAction


@dataclass(frozen=True)
class RemoteSnapshot:
    record: StoredJob
    response_json: bytes = field(repr=False)

    @property
    def response(self):
        return json.loads(self.response_json)


_RECOVERY = {
    JobState.PREPARED: RecoveryAction.REVIEW_QUOTE,
    JobState.SUBMITTING: RecoveryAction.RECONCILE_UNKNOWN,
    JobState.UNCERTAIN: RecoveryAction.RECONCILE_UNKNOWN,
    JobState.REMOTE: RecoveryAction.POLL_REMOTE,
    JobState.CANCEL_REQUESTED: RecoveryAction.POLL_REMOTE,
    JobState.SUCCEEDED: RecoveryAction.DOWNLOAD_RESULT,
    JobState.DOWNLOADING: RecoveryAction.REVIEW_DOWNLOAD,
    JobState.DOWNLOAD_FAILED: RecoveryAction.REVIEW_DOWNLOAD,
    JobState.READY: RecoveryAction.REVIEW_APPLICATION,
    JobState.APPLYING: RecoveryAction.REVIEW_APPLICATION,
    JobState.APPLY_FAILED: RecoveryAction.REVIEW_APPLICATION,
    JobState.FAILED: RecoveryAction.FINISHED,
    JobState.CANCELED: RecoveryAction.FINISHED,
    JobState.APPLIED: RecoveryAction.FINISHED,
}


def _payload(value):
    if not isinstance(value, dict):
        raise QuoteError("The current payload must be a JSON object")
    try:
        return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)
    except (TypeError, ValueError):
        raise QuoteError("The current payload must contain finite JSON values") from None


class JobCoordinator:
    """One immutable selected connection/store; no automatic submission retry.

    Context switches deactivate the old coordinator. Already claimed work stays
    bound to its original scope/origin and may finish, without applying to Blender.
    Caller-supplied account/team IDs must come from the selected auth context.
    """

    def __init__(
        self,
        adapter: SDKAdapter,
        store: JobStore,
        *,
        quote_ttl=120.0,
        clock=time.monotonic,
        origin_guard=None,
        result_downloader=None,
        result_root=None,
        upload_store=None,
        upload_sources=None,
        part_uploader=None,
    ):
        if not isinstance(adapter, SDKAdapter) or not isinstance(store, JobStore):
            raise TypeError("Use the shared SDK adapter and job store")
        if (
            isinstance(quote_ttl, bool)
            or not isinstance(quote_ttl, (int, float))
            or not math.isfinite(quote_ttl)
            or quote_ttl <= 0
            or not callable(clock)
        ):
            raise ValueError("Use a positive finite quote lifetime and monotonic clock")
        if adapter.account_id is None:
            raise ValueError("JobCoordinator requires an explicit adapter account_id")
        scope = JobScope(adapter.base_url, adapter.account_id, adapter.project_id, adapter.team_id)
        if scope != store.scope:
            raise ValueError("Selected connection and job store scopes differ")
        if origin_guard is not None and not callable(origin_guard):
            raise TypeError("Origin guard must be a thread-safe context manager factory")
        self._origin_guard = origin_guard
        self._adapter = adapter
        self._store = store
        self._ttl = quote_ttl
        self._clock = clock
        self._active = True
        self._lock = threading.RLock()
        self._prepared = WeakValueDictionary()
        self._results = ResultCommands(
            adapter, store, self._result_guard, downloader=result_downloader, root=result_root
        )
        self._quotes = WeakValueDictionary()
        self._compositions = WeakValueDictionary()
        self._film_reviews = {}
        self._film_review_cleanup = set()
        self._film_review_cleanup_reported = set()
        self._bound_estimates = WeakKeyDictionary()
        self._verified_results = WeakValueDictionary()
        self._application_claims = WeakValueDictionary()
        self._application_receipts = WeakKeyDictionary()
        self._uploads = None
        upload_config = (upload_store, upload_sources, part_uploader)
        if any(value is not None for value in upload_config):
            if any(value is None for value in upload_config):
                raise TypeError("Configure upload store, sources and part uploader together")
            if upload_store.scope != self.scope:
                raise ValueError("Upload and job scopes must match")
            self._uploads = UploadCommands(
                adapter, upload_store, upload_sources, part_uploader, self._upload_guard
            )

    @contextmanager
    def _upload_guard(self, origin=None):
        with self._lock:
            if not self._active:
                raise UploadError("This upload context is inactive")
            if origin is None:
                yield
                return
            guard = self._origin_guard(origin) if self._origin_guard else nullcontext(True)
            with guard as current:
                if not current:
                    raise UploadError("Upload origin changed; review the saved request")
                yield

    def _upload_commands(self):
        if self._uploads is None:
            raise UploadError("Upload storage and transfer policy are not configured")
        return self._uploads

    def prepare_film_composition(
        self, recipe, *, production_id, mode, score_task_id, root, origin, cancel
    ):
        """Verify saved media and prepare an unpaid draft through this scoped owner."""
        from .film_media import prepare_media

        if not isinstance(origin, JobOrigin):
            raise QuoteError("Capture the composition origin before inspecting media")
        snapshot = json.loads(_payload(recipe))
        result = prepare_media(
            self,
            snapshot,
            production_id=production_id,
            mode=mode,
            score_task_id=score_task_id,
            root=root,
            origin=origin,
            cancel=cancel,
        )
        with self._request_guard(origin):
            if cancel.is_set():
                raise local_render.RenderCancelled("Film media inspection cancelled")
            self._compositions[id(result)] = result
            return result

    def prepare_film_review(
        self, recipe, *, production_id, mode, score_task_id, include_master, root, origin, cancel
    ):
        from . import film_review_media

        if not isinstance(origin, JobOrigin):
            raise ValueError("Capture the Film review origin before preparing media")
        with self._request_guard(origin):
            if len(self._film_reviews) + len(self._film_review_cleanup) >= 16:
                raise ValueError("Finish or discard an existing Film media review first")
        result = film_review_media.prepare(
            self,
            json.loads(_payload(recipe)),
            production_id=production_id,
            mode=mode,
            score_task_id=score_task_id,
            include_master=include_master,
            root=root,
            origin=origin,
            cancel=cancel,
        )
        try:
            with self._request_guard(origin):
                if cancel.is_set():
                    raise local_render.RenderCancelled("Film review preparation cancelled")
                if len(self._film_reviews) + len(self._film_review_cleanup) >= 16:
                    raise ValueError("Finish or discard an existing Film media review first")
                self._film_reviews[id(result)] = result
                return result
        except BaseException as error:
            self._discard_failed_film_review(result.directory, error)
            raise

    def _discard_failed_film_review(self, directory, error):
        """Keep failed preparation cleanup owned without masking its original error."""
        from .film_review_media import discard_directory

        with self._lock:
            self._film_review_cleanup.add(directory)
            try:
                discard_directory(directory)
            except OSError:
                error.add_note("Unused Film review media is retained for shutdown cleanup retry")
                self._report_film_review_cleanup(directory)
            else:
                self._film_review_cleanup.remove(directory)
                self._film_review_cleanup_reported.discard(directory)

    @property
    def film_review_cleanup_pending(self):
        with self._lock:
            return bool(self._film_reviews or self._film_review_cleanup)

    def _report_film_review_cleanup(self, directory):
        if directory not in self._film_review_cleanup_reported:
            # This local diagnostic names only our owned directory, never a
            # transport exception, credential or remote URL.
            logging.getLogger("scenario").warning(
                "Unused Film review media needs cleanup inspection: %s", directory
            )
            self._film_review_cleanup_reported.add(directory)

    def take_film_review(self, prepared, *, origin):
        """Consume owner-issued preparation once; the caller now owns its files."""
        from . import film_review_media

        with self._request_guard(origin):
            if (
                self._film_reviews.get(id(prepared)) is not prepared
                or prepared.scope != self.scope
                or prepared.origin != origin
            ):
                raise ValueError("Use this connection's unconsumed Film review")
            film_review_media.validate_sources(self, prepared)
            film_review_media.check_copies(prepared)
            del self._film_reviews[id(prepared)]
            return prepared

    def discard_film_review(self, prepared):
        from .film_review_media import discard

        with self._lock:
            if self._film_reviews.get(id(prepared)) is not prepared:
                raise ValueError("Use this connection's unconsumed Film review")
            discard(prepared)
            self._film_review_cleanup_reported.discard(prepared.directory)
            del self._film_reviews[id(prepared)]

    def cleanup_film_review(self, prepared, *, defer=False):
        """Own consumed, unused copies until deletion or joined shutdown cleanup.

        Defer deletion while the caller can still retry a rollback receipt.
        Scene-referenced media must never enter this cleanup ownership.
        """
        from .film_review_media import discard

        with self._lock:
            self._film_review_cleanup.add(prepared.directory)
            if defer:
                return
            try:
                discard(prepared)
            except OSError:
                self._report_film_review_cleanup(prepared.directory)
                raise
            self._film_review_cleanup.remove(prepared.directory)
            self._film_review_cleanup_reported.discard(prepared.directory)

    def render_local(self, spec, *, origin, source_origin, cancel):
        """Render local bytes outside locks; recheck both origins before and after."""

        def check():
            with self._lock:
                if not self._active:
                    raise local_render.RenderCancelled("The capture context is inactive")
                for value in (origin, source_origin):
                    guard = self._origin_guard(value) if self._origin_guard else nullcontext(True)
                    with guard as current:
                        if not isinstance(value, JobOrigin) or not current:
                            raise local_render.RenderCancelled("The capture scene changed")

        check()
        media = local_render.render(spec, cancel=cancel)
        check()
        return LocalCaptureResult(self.scope, origin, source_origin, media)

    def prepare_upload(
        self, source, *, origin, kind, content_type, mesh_source=None, expected_sha256=None
    ):
        return self._upload_commands().prepare(
            source,
            origin=origin,
            kind=kind,
            content_type=content_type,
            mesh_source=mesh_source,
            expected_sha256=expected_sha256,
        )

    def inspect_upload(self, request_id):
        """Read this active scope's saved upload without remote or source access."""
        return self._upload_commands().inspect(request_id)

    def upload_recovery_plan(self):
        """Return immutable recovery suggestions, never authorization to retry."""
        return self._upload_commands().recovery_plan()

    def initialize_upload(self, request_id, *, expected_revision):
        return self._upload_commands().initialize(request_id, expected_revision=expected_revision)

    def cancel_prepared_upload(self, request_id, *, expected_revision):
        return self._upload_commands().cancel_prepared(
            request_id, expected_revision=expected_revision
        )

    def transfer_upload_part(self, request_id, *, expected_revision):
        return self._upload_commands().transfer_part(
            request_id, expected_revision=expected_revision
        )

    def finalize_upload(self, request_id, *, expected_revision):
        return self._upload_commands().finalize(request_id, expected_revision=expected_revision)

    def refresh_upload(self, request_id, *, expected_revision):
        return self._upload_commands().refresh(request_id, expected_revision=expected_revision)

    def discard_upload_source(self, request_id, *, expected_revision):
        return self._upload_commands().discard_source(
            request_id, expected_revision=expected_revision
        )

    @property
    def scope(self):
        return self._store.scope

    @contextmanager
    def _result_guard(self):
        with self._lock:
            if not self._active:
                raise ResultError("This result context is inactive")
            yield

    def read_prompt_results(self, request_id, *, expected_revision):
        return self._results.read_prompts(request_id, expected_revision=expected_revision)

    def read_model_text(self, request_id, *, expected_revision, asset_id):
        return self._results.read_model_text(
            request_id, expected_revision=expected_revision, asset_id=asset_id
        )

    def load_results(self, request_id, *, expected_revision):
        return self._results.load_manifest(request_id, expected_revision=expected_revision)

    def download_results(self, request_id, *, expected_revision):
        return self._results.download(request_id, expected_revision=expected_revision)

    def recover_downloads(self, request_id, *, expected_revision):
        """Explicitly reconcile an interrupted download without network or scene work."""
        return self._results.recover_download(request_id, expected_revision=expected_revision)

    def verify_results(self, request_id, *, expected_revision):
        verified = self._results.verify_ready(request_id, expected_revision=expected_revision)
        with self._result_guard():
            self._verified_results[id(verified)] = verified
        return verified

    def claim_application(self, verified: VerifiedResults):
        """Claim verified results before a caller mutates the captured Blender target.

        File verification happens earlier, outside this lock. The application
        must bind the bytes it actually reads to the saved download receipts.
        """
        return self._claim_application(verified)

    def claim_recovered_application(self, verified: VerifiedResults, destination: JobOrigin):
        """Claim an explicitly approved destination without rewriting the job origin.

        The caller must capture and approve this destination before verification,
        then resolve it immediately before mutation. Recovery inspection or result
        download alone does not authorize this command.
        """
        if not isinstance(destination, JobOrigin):
            raise ApplicationError("Capture and approve a current application destination")
        return self._claim_application(verified, destination=destination)

    def claim_local_application(self, verified, destination, *, purpose, asset_ids):
        """Claim explicitly approved reuse without reopening the generation job.

        The caller must bind the purpose and selected asset IDs to its review,
        resolve the captured destination, and apply only those verified assets.
        No SDK request, download or scene mutation is performed here.
        """
        if not isinstance(destination, JobOrigin):
            raise ApplicationError("Capture and approve a current application destination")
        return self._claim_application(
            verified, destination=destination, local=(purpose, asset_ids)
        )

    def _claim_application(self, verified, *, destination=None, local=None):
        with self._lock:
            if (
                not self._active
                or not isinstance(verified, VerifiedResults)
                or self._verified_results.get(id(verified)) is not verified
            ):
                raise ApplicationError("Use current verified results from this owner")
            if self._origin_guard is None:
                raise ApplicationError("Configure an origin guard before applying results")
            record = verified.record
            eligible = (
                {JobState.APPLIED} if local is not None else {JobState.READY, JobState.APPLY_FAILED}
            )
            if record.state not in eligible:
                raise ApplicationError("This result is not eligible for application")
            destination = destination or record.intent.origin
            with self._origin_guard(destination) as current:
                if not current:
                    raise ApplicationError("Application origin changed; review the saved result")
                if self._store.get(record.intent.request_id) != record:
                    raise StoreConflict("Application result changed; verify it again")
                # A failed durable write can be uncertain. Never reuse this
                # verification ticket to infer that the claim did not commit.
                del self._verified_results[id(verified)]
                local_id = uuid.uuid4().hex if local is not None else None
                if local is not None:
                    claimed = self._store.claim_local_application(
                        record.intent.request_id,
                        expected_revision=record.revision,
                        application_id=local_id,
                        destination=destination,
                        purpose=local[0],
                        asset_ids=local[1],
                    )
                else:
                    claimed = self._store.transition(
                        record.intent.request_id,
                        expected_revision=record.revision,
                        state=JobState.APPLYING,
                        application_origin=destination,
                    )
                claim = ApplicationClaim(claimed, verified.paths, local_id)
                self._application_claims[id(claim)] = claim
                return claim

    def complete_application(self, claim: ApplicationClaim):
        """Persist a successful application once, even after origin invalidation."""
        return self._finish_application(claim, JobState.APPLIED)

    def fail_application(self, claim: ApplicationClaim):
        """Record only confirmed no-change/full rollback, never an uncertain mutation."""
        return self._finish_application(claim, JobState.APPLY_FAILED)

    def retry_application_receipt(self, claim: ApplicationClaim):
        """Retry only an already reported outcome; never repeat scene application.

        An exact saved successor acknowledges a commit whose response was lost.
        Claims and outcome evidence stay owner-local and cannot survive restart.
        """
        with self._lock:
            if not isinstance(claim, ApplicationClaim) or claim not in self._application_receipts:
                raise ApplicationError("Use an attempted application receipt from this owner")
            state = self._application_receipts[claim]
            if claim.local_application_id is None:
                expected = replace(claim.record, state=state, revision=claim.record.revision + 1)
            else:
                items = claim.record.local_applications
                expected = replace(
                    claim.record,
                    revision=claim.record.revision + 1,
                    local_applications=(
                        *items[:-1],
                        replace(items[-1], state=_local_outcome(state)),
                    ),
                )
            current = self._store.get(claim.record.intent.request_id)
            if current == expected:
                self._application_claims.pop(id(claim), None)
                return current
            if current != claim.record:
                raise StoreConflict("Application receipt changed; inspect saved state")
            return self._finish_application(claim, state)

    def _finish_application(self, claim, state):
        with self._lock:
            if (
                not isinstance(claim, ApplicationClaim)
                or self._application_claims.get(id(claim)) is not claim
            ):
                raise ApplicationError("Use an unfinished application claim from this owner")
            if self._application_receipts.get(claim, state) != state:
                raise ApplicationError("An attempted application outcome cannot be changed")
            self._application_receipts[claim] = state
            record = claim.record
            if self._store.get(record.intent.request_id) != record:
                raise StoreConflict("Application claim changed; inspect saved state")
            # Application itself may invalidate its origin or deactivate its
            # context. Its receipt still belongs only to the original store.
            if claim.local_application_id is None:
                finished = self._store.transition(
                    record.intent.request_id, expected_revision=record.revision, state=state
                )
            else:
                finished = self._store.finish_local_application(
                    record.intent.request_id,
                    expected_revision=record.revision,
                    application_id=claim.local_application_id,
                    state=_local_outcome(state),
                )
            del self._application_claims[id(claim)]
            return finished

    def deactivate(self):
        """Invalidate queued quotes without waiting for in-flight network calls."""
        with self._lock:
            self._active = False
            self._prepared.clear()
            self._quotes.clear()
            self._compositions.clear()
            self._verified_results.clear()

    def close(self):
        """Release the SDK client after the application owner has joined workers."""
        from .film_review_media import discard_directory

        self.deactivate()
        cleanup_failed = False
        try:
            for prepared in tuple(self._film_reviews.values()):
                try:
                    self.discard_film_review(prepared)
                except Exception:
                    cleanup_failed = True
                    self._report_film_review_cleanup(prepared.directory)
            for directory in tuple(self._film_review_cleanup):
                try:
                    discard_directory(directory)
                except OSError:
                    cleanup_failed = True
                    self._report_film_review_cleanup(directory)
                else:
                    self._film_review_cleanup.remove(directory)
                    self._film_review_cleanup_reported.discard(directory)
        finally:
            self._adapter.close()
        if cleanup_failed:
            raise RuntimeError("Unused Film review media needs cleanup inspection")

    @contextmanager
    def _request_guard(self, origin=None):
        with self._lock:
            if not self._active:
                raise QuoteError("This request context is inactive")
            if origin is None:
                yield
                return
            if not isinstance(origin, JobOrigin):
                raise QuoteError("Capture the request origin before estimation")
            guard = self._origin_guard(origin) if self._origin_guard else nullcontext(True)
            with guard as current:
                if not current:
                    raise QuoteError("Request origin changed; capture inputs and estimate again")
                yield

    def _read_metadata(self, method, *args, **kwargs):
        with self._request_guard():
            pass
        result = method(*args, **kwargs)
        with self._request_guard():
            return result

    def models(self, *, privacy="public", max_pages=100):
        return self._read_metadata(self._adapter.models, privacy=privacy, max_pages=max_pages)

    def workflows(self, *, privacy="private", max_pages=100):
        return self._read_metadata(self._adapter.workflows, privacy=privacy, max_pages=max_pages)

    def asset_page(self, **options):
        return self._read_metadata(self._adapter.asset_page, **options)

    def search_assets(self, query, **options):
        return self._read_metadata(self._adapter.search_assets, query, **options)

    def model(self, identifier):
        return self._metadata("model", identifier)

    def workflow(self, identifier):
        return self._metadata("workflow", identifier)

    def _metadata(self, operation, identifier):
        _identity(identifier)
        result = self._read_metadata(getattr(self._adapter, operation), identifier)
        if result.get("id") != identifier:
            raise QuoteError("Scenario returned another model or workflow identity")
        return result

    def _mesh_bindings(self, operation, metadata, payload):
        if self._uploads is None or operation not in {"model", "workflow"}:
            return ()
        fields = metadata.get("inputs" if operation == "model" else "inputs_definition")
        if fields is None:
            fields = metadata.get("parameters" if operation == "model" else "inputs")
        inputs = [
            spec
            for spec in _fields({"parameters": fields})
            if is_file_field(spec) and str(spec.get("kind", "")).lower() == "3d"
        ]
        if not inputs:
            return ()
        exports = {}
        bindings = []
        for spec in inputs:
            value = payload.get(spec["name"])
            values = (
                enumerate(value)
                if (spec["type"] == "file_array" or spec.get("array") is True)
                and isinstance(value, list)
                else ((None, value),)
            )
            for index, asset_id in values:
                try:
                    _identity(asset_id)
                except ValueError:
                    continue  # Unset or nonopaque inputs cannot match a saved asset identity.
                if asset_id not in exports:
                    if len(exports) >= 128:
                        raise QuoteError("Too many distinct 3D input assets")
                    exports[asset_id] = self._uploads.mesh_sources(asset_id)
                matching = exports[asset_id]
                if not matching:
                    continue  # External assets and ordinary uploads have no inferred source.
                if len(matching) != 1:
                    raise QuoteError(
                        "Several captured uploads identify this asset; review its source"
                    )
                if (index is not None and index >= 128) or len(bindings) >= 128:
                    raise QuoteError("Too many captured mesh inputs")
                record = matching[0]
                bindings.append(
                    JobMeshSource(
                        spec["name"],
                        index,
                        asset_id,
                        record.intent.request_id,
                        record.revision,
                        record.intent.origin,
                        record.intent.mesh_source,
                    )
                )
        return tuple(bindings)

    def _validate_mesh_bindings(self, bindings):
        for binding in bindings:
            record = self._upload_commands().inspect(binding.upload_id)
            if (
                record is None
                or record.state.value != "imported"
                or record.revision != binding.upload_revision
                or record.asset_id != binding.asset_id
                or record.intent.origin != binding.origin
                or record.intent.mesh_source != binding.mesh_source
            ):
                raise QuoteError("A captured input changed; inspect the upload and estimate again")

    def quote_model(self, identifier, parameters, *, origin):
        return self._quote("model", identifier, parameters, origin)

    def quote_film_task(self, recipe, *, production_id, task_id, origin):
        from .film_tasks import model_task_request

        with self._request_guard(origin):
            binding, model, parameters = model_task_request(
                self._store,
                recipe,
                production_id=production_id,
                task_id=task_id,
                inspect_upload=self._uploads.inspect if self._uploads else None,
            )
        return self._quote("model", model, parameters, origin, film_task=binding)

    def _validate_composition(self, draft, *, reserved=False):
        if draft is None:
            return None
        validate = validate_composition_sources if reserved else validate_composition_draft
        return validate(
            self._store, draft, inspect_upload=self._uploads.inspect if self._uploads else None
        )

    def quote_film_composition(self, verified, *, origin):
        """Quote only this owner's verified draft; never accept a supplied duration."""
        from .film_tasks import model_task_request

        with self._request_guard(origin):
            if (
                not isinstance(verified, VerifiedComposition)
                or self._compositions.get(id(verified)) is not verified
                or verified.scope != self.scope
                or verified.origin != origin
            ):
                raise QuoteError("Inspect composition media in this scene and connection first")
            draft = verified.draft
            recipe = self._validate_composition(draft)
            binding, model, parameters = model_task_request(
                self._store,
                recipe,
                production_id=draft.production_id,
                task_id=recipe.get(draft.mode + "_master_task", draft.mode + "-master"),
                inspect_upload=self._uploads.inspect if self._uploads else None,
            )
        return self._quote("model", model, parameters, origin, film_task=binding, composition=draft)

    def bind_film_upload(
        self, recipe, *, production_id, task_id, request_id, expected_revision, origin
    ):
        from .film_tasks import upload_task_reference

        if not isinstance(origin, JobOrigin):
            raise QuoteError("Capture the Film association origin before saving it")
        with self._request_guard(origin):
            reference = upload_task_reference(
                self._store,
                recipe,
                production_id=production_id,
                task_id=task_id,
                inspect_upload=self._upload_commands().inspect,
                request_id=request_id,
                expected_revision=expected_revision,
            )
            saved = self._store.bind_film_upload(reference)
            return FilmUploadResult(self.scope, origin, saved)

    def quote_workflow(self, identifier, parameters, *, origin):
        return self._quote("workflow", identifier, parameters, origin)

    def quote_prompt(self, parameters, *, origin):
        return self._quote("prompt", "prompt", parameters, origin)

    def quote_translate(self, parameters, *, origin):
        return self._quote("translate", "translate", parameters, origin)

    def _quote(
        self, operation, identifier, parameters, origin, *, film_task=None, composition=None
    ):
        if not isinstance(origin, JobOrigin):
            raise QuoteError("Capture the request origin before estimation")
        snapshot = json.loads(_payload(parameters))
        with self._request_guard(origin):
            pass
        record = {}
        if operation in {"prompt", "translate"}:
            estimate = getattr(self._adapter, f"estimate_{operation}")(snapshot)
        else:
            record = self._metadata(operation, identifier)
            with self._request_guard(origin):
                self._validate_composition(composition)
            estimate = getattr(self._adapter, f"estimate_{operation}")(record, snapshot)
        with self._request_guard(origin):
            self._validate_composition(composition)
            bindings = self._mesh_bindings(operation, record, estimate.payload)
            quote = OriginQuote(self.scope, origin, estimate, bindings, film_task, composition)
            self._quotes[id(quote)] = quote
            self._bound_estimates[estimate] = True
            return quote

    def prepare_quote(self, quote):
        """Persist one chosen quote without rebinding it to a newer scene revision."""
        if not isinstance(quote, OriginQuote):
            raise QuoteError("Use an unchanged quote issued by this context")
        # Adapter ownership takes its estimate lock. Never acquire it while
        # holding our lock: submission claims acquire them in the reverse order.
        if not self._adapter.owns_estimate(quote.estimate):
            raise QuoteError("Use a quote issued by the current active connection")
        with self._request_guard(quote.origin):
            if self._quotes.get(id(quote)) is not quote or quote.scope != self.scope:
                raise QuoteError("Use an unchanged quote issued by this context")
            self._validate_mesh_bindings(quote.mesh_sources)
            self._validate_composition(quote.composition)
            prepared = self._prepare(
                quote.estimate,
                quote.origin,
                mesh_sources=quote.mesh_sources,
                film_task=quote.film_task,
                composition=quote.composition,
            )
            del self._quotes[id(quote)]
            return prepared

    def prepare(self, estimate: Estimate, origin: JobOrigin):
        """Accept direct SDK estimates; bound quotes must use prepare_quote."""
        if not self._adapter.owns_estimate(estimate):
            raise QuoteError("Use a quote issued by the current active connection")
        with self._lock:
            if estimate in self._bound_estimates:
                raise QuoteError("Use prepare_quote for an estimate bound to an origin")
            return self._prepare(estimate, origin)

    def _prepare(
        self,
        estimate: Estimate,
        origin: JobOrigin,
        *,
        mesh_sources=(),
        film_task=None,
        composition=None,
    ):
        """Persist after ownership was checked outside the coordinator lock.

        Preparation does not reserve or consume an estimate. Submission rechecks
        ownership atomically with the durable claim and single-use consumption.
        """
        with self._lock:
            if not self._active:
                raise QuoteError("Use a quote issued by the current active connection")
            intent = JobIntent(
                request_id=uuid.uuid4().hex,
                scope=self.scope,
                origin=origin,
                operation=estimate.operation,
                target_id=estimate.target_id,
                payload_sha256=hashlib.sha256(estimate.payload_json).hexdigest(),
                quote_sha256=hashlib.sha256(estimate.response_json).hexdigest(),
                quote_cost=str(estimate.cost),
                mesh_sources=mesh_sources,
                film_task=film_task,
            )
            expires_at = estimate.issued_at + self._ttl
            now = self._clock()
            if not math.isfinite(now) or now < estimate.issued_at or now >= expires_at:
                raise QuoteError("Quote expired; request a fresh estimate")
            prepared = PreparedJob(intent, expires_at, estimate, composition)
            self._store.create(intent)
            self._prepared[id(prepared)] = prepared
            return prepared

    def submit(self, prepared, *, origin, operation, target_id, payload):
        """Explicit spending command; caller passes the current normalized request.

        Persistence errors propagate and stop dispatch. Once claimed, every lost
        or malformed response is uncertain, never an invitation to submit again.
        """
        current_payload = _payload(payload)
        claimed = False

        def claim():
            nonlocal claimed
            with self._lock:
                if not self._active or self._prepared.get(id(prepared)) is not prepared:
                    raise QuoteError("Prepared request is not owned by this active coordinator")
                now = self._clock()
                if (
                    not math.isfinite(now)
                    or now < prepared.estimate.issued_at
                    or now >= prepared.expires_at
                ):
                    raise QuoteError("Quote expired; request a fresh estimate")
                intent = prepared.intent
                if (
                    origin != intent.origin
                    or operation != intent.operation
                    or target_id != intent.target_id
                    or current_payload != _payload(prepared.estimate.payload)
                ):
                    raise QuoteError("Request or origin changed; request a fresh estimate")
                guard = self._origin_guard(origin) if self._origin_guard else nullcontext(True)
                with guard as current_origin:
                    if not current_origin:
                        raise QuoteError("Origin changed while queued; request a fresh estimate")
                    current = self._store.get(intent.request_id)
                    if (
                        current is None
                        or current.intent != intent
                        or current.state != JobState.PREPARED
                    ):
                        raise StoreConflict("Request is no longer prepared; do not resubmit")
                    self._validate_mesh_bindings(intent.mesh_sources)
                    self._validate_composition(prepared.composition, reserved=True)
                    self._store.transition(
                        intent.request_id,
                        expected_revision=current.revision,
                        state=JobState.SUBMITTING,
                    )
                    claimed = True

        if not isinstance(prepared, PreparedJob):
            raise QuoteError("Use a prepared request from this coordinator")
        try:
            receipt = self._adapter.submit_estimate(prepared.estimate, before_send=claim)
            # A receipt must also satisfy the exact persisted identity contract.
            # Validate inside the uncertainty boundary before storing its ID.
            _identity(receipt["jobId"])
        except Exception:
            if not claimed:
                raise
            current = self._store.get(prepared.intent.request_id)
            if current is not None and current.state == JobState.SUBMITTING:
                self._store.transition(
                    current.intent.request_id,
                    expected_revision=current.revision,
                    state=JobState.UNCERTAIN,
                )
            raise SubmissionUncertain(
                "Submission outcome is unknown; do not submit it again"
            ) from None
        # Network work is outside the lock: a context switch can deactivate this
        # coordinator, while the receipt still goes only to its original store.
        current = self._store.get(prepared.intent.request_id)
        if current is None or current.intent != prepared.intent:
            raise StoreConflict("Cannot attach receipt to a changed request")
        return self._store.transition(
            current.intent.request_id,
            expected_revision=current.revision,
            state=JobState.REMOTE,
            remote_job_id=receipt["jobId"],
        )

    def recovery_plan(self):
        """Inspect only this scope; never replay or guess that a worker is dead.

        In-flight records remain unchanged because another process might still
        own them. The application owner decides when explicit recovery is safe.
        """
        with self._lock:
            if not self._active:
                raise RecoveryError("This job context is inactive")
            return tuple(
                RecoveryItem(
                    record,
                    RecoveryAction.REVIEW_APPLICATION
                    if any(
                        item.state == LocalApplicationState.APPLYING
                        for item in record.local_applications
                    )
                    else _RECOVERY[record.state],
                )
                for record in self._store.records()
            )

    def cancel_prepared(self, request_id, *, expected_revision):
        """Cancel queued local intent only. This sends no remote cancel request."""
        with self._lock:
            if not self._active:
                raise RecoveryError("This job context is inactive")
            current = self._store.get(request_id)
            if current is None or current.state != JobState.PREPARED:
                raise StoreConflict("Only a prepared local request can be canceled here")
            return self._store.transition(
                request_id, expected_revision=expected_revision, state=JobState.CANCELED
            )

    def refresh_remote(self, request_id, *, expected_revision):
        """Poll a known ID and persist its terminal status; never submit/rebind."""
        with self._lock:
            if not self._active:
                raise RecoveryError("This job context is inactive")
            current = self._store.get(request_id)
            if (
                current is None
                or current.revision != expected_revision
                or current.state not in {JobState.REMOTE, JobState.CANCEL_REQUESTED}
                or current.remote_job_id is None
            ):
                raise StoreConflict("Only the current known remote job can be refreshed")
        response = self._adapter.job(current.remote_job_id)
        return self._observe_remote(current, response)

    def adopt_cloud_job(self, identifier, *, expected_model_id, origin):
        """Retrieve an explicitly selected completed model job, without submission."""
        _identity(identifier)
        _identity(expected_model_id)
        intent = CloudJobIntent(
            "cloud-" + hashlib.sha256(identifier.encode()).hexdigest(),
            self.scope,
            origin,
            expected_model_id,
        )
        # This read saves metadata, not a quote or application approval. Keep
        # its captured provenance even if the scene changes while it is queued.
        with self._request_guard():
            pass
        response = self._adapter.job(identifier)
        metadata = response.get("metadata")
        inputs = metadata.get("input") if isinstance(metadata, dict) else None
        assets = metadata.get("assetIds") if isinstance(metadata, dict) else None
        if (
            response.get("jobId") != identifier
            or response.get("status") != "success"
            or response.get("jobType") not in ("custom", "inference")
            or not isinstance(inputs, dict)
            or inputs.get("modelId") != expected_model_id
            or not isinstance(assets, list)
            or not 1 <= len(assets) <= 128
        ):
            raise RecoveryError("Scenario did not confirm the selected completed model job")
        try:
            for asset in assets:
                _identity(asset)
            if len(set(assets)) != len(assets):
                raise ValueError
        except ValueError:
            raise RecoveryError(
                "Scenario returned invalid completed-job asset identities"
            ) from None
        with self._request_guard():
            return self._store.adopt_cloud_job(intent, identifier)

    def _observe_remote(self, current, response):
        """Commit only retrieval evidence, never cancellation acknowledgements."""
        request_id = current.intent.request_id
        if response.get("jobId") != current.remote_job_id:
            raise RecoveryError("Scenario returned a different remote job identity")
        status = response.get("status")
        terminal = {
            "success": JobState.SUCCEEDED,
            "failure": JobState.FAILED,
            "canceled": JobState.CANCELED,
        }
        active = {"pending", "queued", "warming-up", "in-progress", "finalizing"}
        if not isinstance(status, str) or status not in active | terminal.keys():
            raise RecoveryError("Scenario returned an unrecognized job state")
        try:
            raw = json.dumps(response, allow_nan=False).encode()
        except (TypeError, ValueError):
            raise RecoveryError("Scenario returned invalid job result data") from None
        if status in terminal:
            try:
                updated = self._store.transition(
                    request_id, expected_revision=current.revision, state=terminal[status]
                )
            except StoreConflict:
                updated = self._store.get(request_id)
                if (
                    updated is None
                    or updated.intent != current.intent
                    or updated.remote_job_id != current.remote_job_id
                    or updated.state != terminal[status]
                ):
                    raise
        else:
            updated = self._store.get(request_id)
            if updated != current:
                raise StoreConflict("Job changed during polling; refresh the local record")
        return RemoteSnapshot(updated, raw)

    def cancel_remote(self, request_id, *, expected_revision):
        """Claim one known model-job cancellation durably, then retrieve its state.

        CANCEL_REQUESTED is never replayed or reset on restart. It remains
        pollable after a lost acknowledgement or a crash before sending.
        """
        with self._lock:
            if not self._active:
                raise RecoveryError("This job context is inactive")
            current = self._store.get(request_id)
            if current is not None and current.state == JobState.CANCEL_REQUESTED:
                raise StoreConflict("Cancellation already requested; refresh the known job")
            if (
                current is None
                or current.revision != expected_revision
                or current.state != JobState.REMOTE
                or current.remote_job_id is None
            ):
                raise StoreConflict("Only the current known remote job can be canceled")
            if current.intent.operation != "model":
                raise RecoveryError("Only model-job cancellation is supported")
        response = self._adapter.job(current.remote_job_id)
        snapshot = self._observe_remote(current, response)
        if snapshot.record.state != JobState.REMOTE:
            return snapshot
        # Captured model-generation records use custom. The pinned SDK also
        # enumerates inference; neither spelling is a general workflow cancel.
        if response.get("jobType") not in ("custom", "inference"):
            raise RecoveryError("Only a verified model-generation job can be canceled")
        # CAS persists the claim before the remote action across coordinator
        # instances/processes. No expiration can make an uncertain action replayable.
        with self._lock:
            if not self._active:
                raise RecoveryError("This job context is inactive")
            current = self._store.transition(
                request_id, expected_revision=current.revision, state=JobState.CANCEL_REQUESTED
            )
        try:
            self._adapter.cancel_inference(current.remote_job_id)
            response = self._adapter.job(current.remote_job_id)
        except Exception:
            raise CancellationUncertain(
                "Cancellation outcome is unknown; refresh the known job without repeating cancellation"
            ) from None
        return self._observe_remote(current, response)
