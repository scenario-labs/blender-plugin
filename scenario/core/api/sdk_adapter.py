# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Scoped SDK reads and exact estimates for the consolidated runtime.

No bpy imports, ambient credentials, redirects or automatic retries. Paid
dispatch requires an issued estimate and a durable claim callback.
SDK imports are lazy so package registration does not start client work.
"""

import copy
import json
import math
import re
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from decimal import Decimal
from urllib.parse import urlsplit
from weakref import WeakValueDictionary

from ..schema.forms import prepare_run
from .sdk_extensions import SDKResourceExtensions
from .user_agent import user_agent_string

API_URL = "https://api.cloud.scenario.com/v1"
# The API reference states no get-bulk batch limit; stay small until a capture
# establishes one, and bound each call so a refresh cannot fan out reads.
MODEL_BULK_CHUNK = 50
MODEL_BULK_LIMIT = 200


class AdapterError(RuntimeError):
    """Safe text for UI/worker boundaries; never include response bodies or URLs."""


class AdapterUnavailable(AdapterError):
    """The selected credentials or project cannot read a known model (HTTP 403 or 404)."""

    def __init__(self, status):
        self.status = status
        super().__init__(
            f"This model is not available to the selected credentials or project (HTTP {status})"
        )


def _unavailable_on_denial(method):
    """Raise AdapterUnavailable for HTTP 403/404 from one known-record read.

    The SDK raises inside the call, before the adapter's generic status mapping;
    other failures keep that mapping.
    """
    from scenario_sdk import APIStatusError

    def call(*args, **kwargs):
        try:
            return method(*args, **kwargs)
        except APIStatusError as error:
            if error.status_code in (403, 404):
                raise AdapterUnavailable(error.status_code) from None
            raise

    return call


@dataclass(frozen=True)
class Credentials:
    api_key: str = field(default="", repr=False)
    api_secret: str = field(default="", repr=False)
    bearer_token: str = field(default="", repr=False)

    def authorization(self):
        import base64

        basic = bool(self.api_key and self.api_secret)
        partial = bool(self.api_key) != bool(self.api_secret)
        if partial or basic == bool(self.bearer_token):
            raise ValueError("Select one complete API-key pair or one bearer token")
        values = (self.api_key, self.api_secret, self.bearer_token)
        if any(not isinstance(value, str) or not value.isascii() for value in values):
            raise ValueError("Credentials must be ASCII strings")
        if any(any(ord(char) < 33 or ord(char) == 127 for char in value) for value in values):
            raise ValueError("Credentials cannot contain whitespace or control characters")
        if basic:
            if ":" in self.api_key:
                raise ValueError("API keys cannot contain a colon")
            encoded = base64.b64encode(f"{self.api_key}:{self.api_secret}".encode()).decode()
            return f"Basic {encoded}"
        return f"Bearer {self.bearer_token}"


@dataclass(frozen=True)
class Estimate:
    """Immutable payload/response bytes; dict access returns a fresh copy."""

    operation: str
    target_id: str
    project_id: str | None
    cost: Decimal
    payload_json: bytes = field(repr=False)
    response_json: bytes = field(repr=False)
    scope: object = field(repr=False)
    issued_at: float = field(repr=False)

    @property
    def payload(self):
        return json.loads(self.payload_json)

    @property
    def details(self):
        return _json(self.response_json, exact=True)


def _reject_constant(value):
    raise ValueError("Non-finite JSON number")


def _json(raw, *, exact=False):
    try:
        result = json.loads(
            raw, parse_float=Decimal if exact else float, parse_constant=_reject_constant
        )
    except (ValueError, UnicodeError):
        raise AdapterError("Scenario returned invalid JSON") from None
    if not isinstance(result, dict):
        raise AdapterError("Scenario returned an unexpected response")
    return result


def _status_text(status, *, project):
    """Short first sentence that survives clipped status lines, then fixed guidance.

    The guidance is credential-source neutral (saved or environment keys). Never
    include response bodies, URLs, identifiers or credentials.
    """
    if status == 401:
        return "Key or secret rejected (HTTP 401). Check the selected API key and secret."
    if status == 403 and project:
        return (
            "Access denied (HTTP 403). Check the selected API key and secret, and that the "
            "Project ID belongs to this key, or clear it to use the key's default scope."
        )
    if status == 403:
        return "Access denied (HTTP 403). Check the selected API key and secret."
    if status == 429:
        return "Too many requests (HTTP 429). Try again shortly."
    return f"Scenario request failed (HTTP {status})"


def _identifier(value):
    if not isinstance(value, str) or not value or value in {".", ".."} or value.strip() != value:
        raise ValueError("A nonempty identifier is required")
    if any(char in value for char in "/\\?#%") or any(ord(char) < 33 for char in value):
        raise ValueError("Identifier contains unsupported characters")
    return value


def _upload_identifier(value):
    """Keep upload and asset-option identities safe for paths and future storage."""
    value = _identifier(value)
    if len(value) > 256 or any(char.isspace() or ord(char) == 127 for char in value):
        raise ValueError("Upload identifiers must be at most 256 characters without whitespace")
    return value


def _upload_record(raw, identifier=None):
    record = _json(raw).get("upload")
    if not isinstance(record, dict):
        raise AdapterError("Scenario returned no upload record")
    try:
        actual = _upload_identifier(record.get("id"))
    except ValueError:
        raise AdapterError("Scenario returned an invalid upload identity") from None
    if identifier is not None and actual != identifier:
        raise AdapterError("Scenario returned a different upload identity")
    status = record.get("status")
    if not isinstance(status, str) or not status.strip():
        raise AdapterError("Scenario returned no upload status")
    # Preserve future statuses, transfer instructions and fields verbatim. This
    # is metadata, not a validated transfer plan or proof of completed import.
    return record


def _prepare(identifier, fields, parameters):
    """Use the shared pure form preparation and conditional requirements."""
    return prepare_run(identifier, {"parameters": fields}, parameters)


def _client(credentials, base_url, timeout, transport):
    import httpx
    from scenario_sdk import Scenario

    authorization = credentials.authorization()

    class SelectedAccount(Scenario):
        @property
        def default_headers(self):
            # Public SDK hook: use only adapter-owned headers. SDK 2.2.0 otherwise
            # merges SCENARIO_CUSTOM_HEADERS and prefers Basic over Bearer.
            # https://github.com/scenario-labs/scenario-sdk-python/issues/26
            # Remove after upstream offers verified environment-isolated config.
            # This changes configuration, not endpoint routing; no raw API fallback.
            return {
                "Authorization": authorization,
                "Accept": "application/json",
                "Content-Type": "application/json",
                "User-Agent": user_agent_string(),
            }

    http = httpx.Client(
        transport=transport, follow_redirects=False, trust_env=False, timeout=timeout
    )
    try:
        return SelectedAccount(
            api_key=credentials.api_key,
            api_secret=credentials.api_secret,
            bearer_auth=credentials.bearer_token,
            base_url=base_url,
            max_retries=0,
            timeout=timeout,
            http_client=http,
        )
    except Exception:
        http.close()
        raise


def model_identifiers(values):
    """Unique model identifiers in request order; ValueError for any the adapter rejects.

    Callers that share pending reads by identifier check a request here first,
    so an invalid identifier fails only the request that contains it.
    """
    if isinstance(values, (str, bytes)) or not isinstance(values, (list, tuple)):
        raise ValueError("Use a list of model identifiers")
    return list(dict.fromkeys(_identifier(value) for value in values))


class SDKAdapter:
    """One selected account/project and owned HTTP pool; close after worker use.

    The caller supplies its online-access predicate. Blender callers must bind
    this to their actual online permission, not a saved startup preference.
    """

    def __init__(
        self,
        credentials: Credentials,
        *,
        online: Callable[[], bool],
        project_id=None,
        account_id=None,
        team_id=None,
        base_url=API_URL,
        timeout=45.0,
        transport=None,
    ):
        url = urlsplit(base_url)
        if (
            url.scheme != "https"
            or not url.hostname
            or url.username
            or url.password
            or url.query
            or url.fragment
        ):
            raise ValueError("Use an HTTPS API base URL without credentials, query or fragment")
        if not callable(online):
            raise TypeError("An online-access predicate is required")
        if isinstance(timeout, bool) or not math.isfinite(timeout) or timeout <= 0:
            raise ValueError("Timeout must be finite and positive")
        self._base_url = base_url.rstrip("/")
        self._account_id = _identifier(account_id) if account_id is not None else None
        self._team_id = _identifier(team_id) if team_id is not None else None
        self._estimates = WeakValueDictionary()
        self._estimate_lock = threading.RLock()
        self._project_id = _identifier(project_id) if project_id is not None else None
        self._online = online
        self._scope = object()
        self._closed = False
        self._sdk = _client(credentials, base_url, timeout, transport)
        self._extensions = SDKResourceExtensions(self._sdk)

    @property
    def project_id(self):
        return self._project_id

    @property
    def base_url(self):
        return self._base_url

    @property
    def account_id(self):
        return self._account_id

    @property
    def team_id(self):
        return self._team_id

    def close(self):
        with self._estimate_lock:
            self._estimates.clear()
            self._closed = True
        self._sdk.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()

    def _request(self, method, *args, **kwargs):
        if self.project_id is not None:
            kwargs["project_id"] = self.project_id
        return self._unscoped_request(method, *args, **kwargs)

    def _unscoped_request(self, method, *args, **kwargs):
        from scenario_sdk import APIConnectionError, APIStatusError

        if self._closed:
            raise AdapterError("Scenario client is closed")
        if not self._online():
            raise AdapterError("Online access is disabled")
        try:
            response = method(*args, **kwargs)
            return response.read()
        except APIStatusError as error:
            # Only a request that carried the override can blame the Project ID.
            project = kwargs.get("project_id") is not None
            raise AdapterError(_status_text(error.status_code, project=project)) from None
        except APIConnectionError:
            raise AdapterError("Could not reach Scenario") from None

    def _discovery(self, method, wrapper, *args):
        value = _json(self._unscoped_request(method, *args))
        records = value.get(wrapper)
        if not isinstance(records, list):
            raise AdapterError(f"Scenario returned no {wrapper} list")
        for record in records:
            try:
                _identifier(record.get("id") if isinstance(record, dict) else None)
            except ValueError:
                raise AdapterError(f"Scenario returned an invalid {wrapper} identity") from None
        return value

    def teams(self):
        """Return one unscoped discovery response, without selecting a team.

        Optional metadata discovery; API-key operations need no team/project
        selection. This list does not establish a key's default project.
        """
        return self._discovery(self._extensions.teams, "teams")

    def projects(self, team_id):
        """Return one team's discovery response, ignoring the selected project."""
        return self._discovery(self._extensions.projects, "projects", _identifier(team_id))

    def _retrieve(self, resource, identifier, wrapper, *, unavailable=False):
        method = getattr(self._sdk, resource).with_raw_response.retrieve
        if unavailable:
            method = _unavailable_on_denial(method)
        value = _json(self._request(method, _identifier(identifier)))
        record = value.get(wrapper)
        if not isinstance(record, dict):
            raise AdapterError(f"Scenario returned no {wrapper} record")
        return record

    def model(self, identifier):
        """Read one model record; HTTP 403/404 raise AdapterUnavailable."""
        return self._retrieve("models", identifier, "model", unavailable=True)

    def models_bulk(self, identifiers, *, chunk=MODEL_BULK_CHUNK):
        """Read known models with the SDK's `models.get_bulk`, in bounded requests.

        Returns {id: record} in request order for the records Scenario returned.
        Omitted IDs stay absent: the API reference does not say whether a
        missing or inaccessible ID is omitted or fails the request. Bulk records
        are discovery data: the reference directs `inputs` readers to GET
        /models/{modelId}, so read the model before building a form or quote.
        Every chunk carries the selected project and rechecks online permission;
        any failure returns nothing rather than a partial result.
        """
        if type(chunk) is not int or not 1 <= chunk <= MODEL_BULK_CHUNK:
            raise ValueError(f"Bulk model chunks hold 1 to {MODEL_BULK_CHUNK} identifiers")
        requested = model_identifiers(identifiers)
        if len(requested) > MODEL_BULK_LIMIT:
            raise ValueError(f"Read at most {MODEL_BULK_LIMIT} models at once")
        records = {}
        for start in range(0, len(requested), chunk):
            batch = requested[start : start + chunk]
            page = _json(
                self._request(self._sdk.models.with_raw_response.get_bulk, model_ids=batch)
            )
            rows = page.get("models")
            if not isinstance(rows, list):
                raise AdapterError("Scenario returned an invalid bulk model list")
            for row in rows:
                try:
                    identifier = _identifier(row.get("id") if isinstance(row, dict) else None)
                except ValueError:
                    raise AdapterError("Scenario returned an invalid model record") from None
                if identifier not in batch:
                    raise AdapterError("Scenario returned a model that was not requested")
                if identifier in records and records[identifier] != row:
                    raise AdapterError("Scenario returned conflicting model records; refresh")
                records[identifier] = row
        return {
            identifier: records[identifier] for identifier in requested if identifier in records
        }

    def workflow(self, identifier):
        return self._retrieve("workflows", identifier, "workflow")

    def asset(self, identifier):
        return self._retrieve("assets", identifier, "asset")

    def network_allowed(self):
        """Read the caller's online permission without contacting Scenario."""
        return not self._closed and bool(self._online())

    def bulk_assets(self, identifiers):
        """Read up to 100 known asset records in the selected scope with one SDK request.

        SDK 2.2.0 ``assets.with_raw_response.get_bulk`` documents a 200-ID limit;
        callers chunk by 100. Assets the server omits are absent from the
        result, never inferred. This is a read without retries or side effects.
        """
        identifiers = tuple(identifiers)
        if not 1 <= len(identifiers) <= 100 or len(set(identifiers)) != len(identifiers):
            raise ValueError("Choose from 1 to 100 distinct asset identities")
        for identifier in identifiers:
            _identifier(identifier)
        page = _json(
            self._request(self._sdk.assets.with_raw_response.get_bulk, asset_ids=list(identifiers))
        )
        rows = page.get("assets")
        if not isinstance(rows, list) or len(rows) > len(identifiers):
            raise AdapterError("Scenario returned an invalid asset list")
        records = {}
        for row in rows:
            identifier = row.get("id") if isinstance(row, dict) else None
            if identifier not in identifiers:
                raise AdapterError("Scenario returned an unrequested asset record")
            if identifier in records and records[identifier] != row:
                raise AdapterError("Scenario returned conflicting asset records")
            records[identifier] = row
        return records

    @staticmethod
    def _asset_rows(rows, limit):
        if not isinstance(rows, list) or len(rows) > limit:
            raise AdapterError("Scenario returned an invalid asset page")
        records = {}
        for row in rows:
            try:
                identifier = _identifier(row.get("id") if isinstance(row, dict) else None)
            except ValueError:
                raise AdapterError("Scenario returned an invalid asset record") from None
            if identifier in records and records[identifier] != row:
                raise AdapterError(
                    "Scenario returned conflicting asset records; refresh the library"
                )
            records[identifier] = row
        return list(records.values())

    def asset_page(self, *, public=False, page_size=40, pagination_token=None, collection_id=None):
        """Read one SDK asset page in the selected scope, without automatic traversal."""
        if type(public) is not bool or type(page_size) is not int or not 1 <= page_size <= 100:
            raise ValueError("Choose public/owned assets and a page size from 1 to 100")
        options = {"page_size": page_size}
        if public:
            options["privacy"] = "public"
        if pagination_token is not None:
            if not isinstance(pagination_token, str) or not pagination_token:
                raise ValueError("Use a nonempty asset cursor")
            options["pagination_token"] = pagination_token
        if collection_id is not None:
            options["collection_id"] = _identifier(collection_id)
        page = _json(self._request(self._sdk.assets.with_raw_response.list, **options))
        rows = self._asset_rows(page.get("assets"), page_size)
        token = page.get("nextPaginationToken")
        if token not in (None, "") and (not isinstance(token, str) or token == pagination_token):
            raise AdapterError("Scenario repeated or returned an invalid asset cursor")
        return {"assets": rows, "next_pagination_token": token or None}

    def search_assets(self, query, *, public=False, limit=40, offset=0):
        """Use the public SDK search method with explicit body-based pagination."""
        if not isinstance(query, str) or not query.strip() or len(query) > 4096:
            raise ValueError("Use a nonempty asset search of at most 4096 characters")
        if (
            type(public) is not bool
            or type(limit) is not int
            or not 1 <= limit <= 100
            or type(offset) is not int
            or offset < 0
        ):
            raise ValueError(
                "Choose public/owned assets, a limit from 1 to 100 and nonnegative offset"
            )
        page = _json(
            self._request(
                self._sdk.search.with_raw_response.asset_search,
                query=query,
                public=public,
                limit=limit,
                offset=offset,
            )
        )
        hits = page.get("hits")
        rows = self._asset_rows(hits, limit)
        total = page.get("estimatedTotalHits")
        returned_offset = page.get("offset")
        if (total is not None and (type(total) is not int or total < 0)) or (
            returned_offset is not None
            and (type(returned_offset) is not int or returned_offset != offset)
        ):
            raise AdapterError("Scenario returned invalid asset search pagination")
        end = offset + len(hits)
        more = bool(hits) and (end < total if total is not None else len(hits) == limit)
        return {"assets": rows, "estimated_total": total, "next_offset": end if more else None}

    def job(self, identifier):
        return self._retrieve("jobs", identifier, "job")

    def cancel_inference(self, identifier):
        """Request cancellation once; the coordinator verifies inference eligibility.

        This acknowledgement is not authoritative terminal-state evidence. Poll
        the known job afterwards, including after an uncertain request outcome.
        """
        identifier = _identifier(identifier)
        method = self._sdk.jobs.with_raw_response.trigger_action
        response = _json(self._request(method, identifier, action="cancel"))
        job = response.get("job")
        if not isinstance(job, dict) or job.get("jobId") != identifier:
            raise AdapterError("Scenario returned no matching cancellation acknowledgement")
        return job

    def create_upload(self, *, kind, file_name, content_type, file_size, parts, asset_options=None):
        """Initialize multipart metadata once; never read or transfer local bytes.

        Errors after dispatch may mean the server created an upload. Callers
        must preserve known identity and reconcile, not recreate automatically.
        """
        if not isinstance(kind, str) or kind not in {
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
            not isinstance(file_name, str)
            or not file_name.strip()
            or file_name in {".", ".."}
            or any(char in file_name for char in "/\\:")
            or any(ord(char) < 32 or ord(char) == 127 for char in file_name)
        ):
            raise ValueError("Use a file basename without paths or control characters")
        if not isinstance(content_type, str) or not re.fullmatch(
            r"[A-Za-z0-9!#$&^_.+-]+/[A-Za-z0-9!#$&^_.+-]+", content_type
        ):
            raise ValueError("Use a MIME type without parameters or control characters")
        if type(file_size) is not int or file_size < 0:
            raise ValueError("Upload file size must be a nonnegative integer byte count")
        if type(parts) is not int or parts < 1:
            raise ValueError("Upload part count must be a positive integer")
        options = {}
        if asset_options is not None:
            if kind == "model":
                raise ValueError("Model uploads do not support asset options")
            if not isinstance(asset_options, dict) or set(asset_options) - {
                "collection_ids",
                "parent_id",
                "hide",
            }:
                raise ValueError("Use supported SDK asset option names")
            copied = copy.deepcopy(asset_options)
            if "collection_ids" in copied:
                if not isinstance(copied["collection_ids"], list):
                    raise ValueError("Upload collections must be a list of identifiers")
                for value in copied["collection_ids"]:
                    _upload_identifier(value)
            if "parent_id" in copied:
                _upload_identifier(copied["parent_id"])
            if "hide" in copied and type(copied["hide"]) is not bool:
                raise ValueError("Upload visibility must be a boolean")
            options["asset_options"] = copied
        return _upload_record(
            self._request(
                self._sdk.uploads.with_raw_response.create,
                kind=kind,
                file_name=file_name,
                content_type=content_type,
                file_size=file_size,
                parts=parts,
                **options,
            )
        )

    def upload(self, identifier):
        """Retrieve one known upload in the selected project without side effects."""
        identifier = _upload_identifier(identifier)
        return _upload_record(
            self._request(self._sdk.uploads.with_raw_response.retrieve, identifier), identifier
        )

    def complete_upload(self, identifier):
        """Explicitly request completion once; an acknowledgement may be validating.

        The caller must establish that its parts were transferred. This adapter
        does not infer transfer success, poll, retry, or claim asset import.
        """
        identifier = _upload_identifier(identifier)
        return _upload_record(
            self._request(
                self._sdk.uploads.with_raw_response.trigger_action, identifier, action="complete"
            ),
            identifier,
        )

    def job_page(self, *, page_size=50, pagination_token=None):
        """One history page with inputs/results, using an opaque service cursor."""
        if type(page_size) is not int or not 1 <= page_size <= 200:
            raise ValueError("Job page size must be between 1 and 200")
        options = {"page_size": page_size, "hide_results": False}
        if pagination_token is not None:
            if not isinstance(pagination_token, str) or not pagination_token:
                raise ValueError("A nonempty job cursor is required")
            options["pagination_token"] = pagination_token
        page = _json(self._request(self._sdk.jobs.with_raw_response.list, **options))
        rows = page.get("jobs")
        if not isinstance(rows, list):
            raise AdapterError("Scenario returned an invalid job page")
        records = {}
        for row in rows:
            try:
                identifier = _identifier(row.get("jobId") if isinstance(row, dict) else None)
            except ValueError:
                raise AdapterError("Scenario returned an invalid job record") from None
            if identifier in records and records[identifier] != row:
                raise AdapterError("Scenario returned conflicting job records; refresh history")
            records[identifier] = row
        token = page.get("nextPaginationToken")
        if token not in (None, "") and (not isinstance(token, str) or token == pagination_token):
            raise AdapterError("Scenario repeated or returned an invalid job cursor")
        return {**page, "jobs": list(records.values())}

    def jobs(
        self,
        *,
        author_id=None,
        workflow_id=None,
        job_type=None,
        status=None,
        hide_results=True,
        page_size=100,
        max_pages=100,
    ):
        """Return scoped discovery candidates, never proof of submission identity.

        Fail instead of returning a partial history. Callers must retrieve a
        known job again before relying on its state; listing is not a snapshot.
        """
        for value in (page_size, max_pages):
            if not isinstance(value, int) or isinstance(value, bool) or value < 1:
                raise ValueError("Page size and limit must be positive integers")
        if page_size > 200:
            raise ValueError("Job page size cannot exceed 200")
        statuses = {
            "pending",
            "queued",
            "warming-up",
            "in-progress",
            "success",
            "failure",
            "canceled",
            "finalizing",
        }
        if status is not None and (not isinstance(status, str) or status not in statuses):
            raise ValueError("Choose a supported job status")
        if not isinstance(hide_results, bool):
            raise ValueError("Result visibility must be a boolean")
        options = {"page_size": page_size, "hide_results": hide_results}
        for key, value in (
            ("author_id", author_id),
            ("workflow_id", workflow_id),
            ("type", job_type),
        ):
            if value is not None:
                options[key] = _identifier(value)
        if status is not None:
            options["status"] = status
        records, tokens = {}, set()
        for _ in range(max_pages):
            page = _json(self._request(self._sdk.jobs.with_raw_response.list, **options))
            rows = page.get("jobs")
            if not isinstance(rows, list):
                raise AdapterError("Scenario returned an invalid job page")
            for row in rows:
                try:
                    identifier = _identifier(row.get("jobId") if isinstance(row, dict) else None)
                except ValueError:
                    raise AdapterError("Scenario returned an invalid job record") from None
                if identifier in records and records[identifier] != row:
                    raise AdapterError("Scenario returned conflicting job records; refresh history")
                records[identifier] = row
            token = page.get("nextPaginationToken")
            if token is None or token == "":
                return list(records.values())
            if not isinstance(token, str) or token in tokens:
                raise AdapterError("Scenario repeated or returned an invalid job cursor")
            tokens.add(token)
            options["pagination_token"] = token
        raise AdapterError("Scenario job history exceeded the page limit")

    def _catalog(self, resource, privacy, max_pages):
        if privacy not in {"public", "private"}:
            raise ValueError("Choose public or private catalog visibility")
        if not isinstance(max_pages, int) or isinstance(max_pages, bool) or max_pages < 1:
            raise ValueError("Page limit must be a positive integer")
        result, identifiers, tokens = [], set(), set()
        options = {"privacy": privacy, "page_size": 100}
        if resource == "models" and privacy == "private":
            options["status"] = "trained"
        method = getattr(self._sdk, resource).with_raw_response.list
        for _ in range(max_pages):
            page = _json(self._request(method, **options))
            rows = page.get(resource)
            if not isinstance(rows, list):
                raise AdapterError("Scenario returned an invalid catalog page")
            for row in rows:
                if not isinstance(row, dict) or not isinstance(row.get("id"), str) or not row["id"]:
                    raise AdapterError("Scenario returned an invalid catalog record")
                if row["id"] not in identifiers:
                    identifiers.add(row["id"])
                    result.append(row)
            token = page.get("nextPaginationToken")
            if token is None or token == "":
                return result
            if not isinstance(token, str) or token in tokens:
                raise AdapterError("Scenario repeated a catalog cursor")
            tokens.add(token)
            options["pagination_token"] = token
        raise AdapterError("Scenario catalog exceeded the page limit")

    def model_page(self, *, privacy="public", page_size=100, pagination_token=None):
        """Read one bounded model page, preserving the response wrapper and cursor."""
        if privacy not in {"public", "private"}:
            raise ValueError("Choose public or private catalog visibility")
        if type(page_size) is not int or not 1 <= page_size <= 500:
            raise ValueError("Model page size must be an integer from 1 to 500")
        options = {"privacy": privacy, "page_size": page_size}
        if pagination_token is not None:
            if not isinstance(pagination_token, str) or not pagination_token:
                raise ValueError("Model cursor must be a nonempty string")
            options["pagination_token"] = pagination_token
        if privacy == "private":
            options["status"] = "trained"
        page = _json(self._request(self._sdk.models.with_raw_response.list, **options))
        rows = page.get("models")
        if not isinstance(rows, list):
            raise AdapterError("Scenario returned an invalid catalog page")
        if any(
            not isinstance(row, dict) or not isinstance(row.get("id"), str) or not row["id"]
            for row in rows
        ):
            raise AdapterError("Scenario returned an invalid catalog record")
        token = page.get("nextPaginationToken")
        if token is not None and not isinstance(token, str):
            raise AdapterError("Scenario returned an invalid catalog cursor")
        return page

    def models(self, *, privacy="public", max_pages=100):
        return self._catalog("models", privacy, max_pages)

    def workflows(self, *, privacy="private", max_pages=100):
        return self._catalog("workflows", privacy, max_pages)

    def estimate_model(self, model, parameters):
        if model.get("type") != "custom" or model.get("parentModelId") or model.get("runs_as"):
            raise ValueError("Trained-model routing requires a verified REST schema contract")
        identifier = _identifier(model.get("id"))
        fields = model.get("inputs")
        if fields is None:
            fields = model.get("parameters")
        target, payload = _prepare(identifier, fields, parameters)
        return self._estimate("model", target, payload)

    def estimate_workflow(self, workflow, parameters):
        identifier = _identifier(workflow.get("id"))
        fields = workflow.get("inputs_definition")
        if fields is None:
            fields = workflow.get("inputs")
        target, payload = _prepare(identifier, fields, parameters)
        return self._estimate("workflow", target, payload)

    def estimate_prompt(self, parameters):
        """Quote a bounded Prompt Spark request through the public SDK method.

        This initial contract accepts mode, prompt, modelId, images and numResults.
        Scope and dry-run flags are adapter-owned, never payload fields.
        """
        if not isinstance(parameters, dict) or parameters.keys() - {
            "mode",
            "prompt",
            "modelId",
            "images",
            "numResults",
        }:
            raise ValueError("Unsupported Prompt Spark parameters")
        payload = copy.deepcopy(parameters)
        mode = payload.get("mode")
        if not isinstance(mode, str) or mode not in {
            "completion",
            "contextual",
            "contextual-v2",
            "image-editing",
            "inventive",
            "structured",
        }:
            raise ValueError("Choose a supported Prompt Spark mode")
        count = payload.setdefault("numResults", 1)
        if type(count) is not int or not 1 <= count <= 5:
            raise ValueError("Prompt result count must be an integer from 1 to 5")
        if "prompt" in payload and not isinstance(payload["prompt"], str):
            raise ValueError("Prompt must be text")
        if "modelId" in payload:
            _identifier(payload["modelId"])
        if "images" in payload:
            images = payload["images"]
            limit = 15 if mode == "contextual-v2" else 5
            if (
                not isinstance(images, list)
                or len(images) > limit
                or any(not isinstance(item, str) or not item.strip() for item in images)
            ):
                raise ValueError("Choose valid Prompt Spark image references within the mode limit")
        return self._estimate("prompt", "prompt", payload)

    def estimate_translate(self, parameters):
        """Quote English translation through the SDK, without a model fallback."""
        if (
            not isinstance(parameters, dict)
            or set(parameters) != {"prompt"}
            or not isinstance(parameters["prompt"], str)
            or not parameters["prompt"].strip()
        ):
            raise ValueError("Provide only the nonempty prompt to translate")
        return self._estimate("translate", "translate", dict(parameters))

    def _dispatch_generation(self, operation, identifier, payload, *, dry_run=False):
        options = {"dry_run": "true"} if dry_run else {}
        if operation == "translate":
            return self._request(
                self._sdk.generate.with_raw_response.translate, **payload, **options
            )
        if operation == "prompt":
            names = {"modelId": "model_id", "numResults": "num_results"}
            options.update({names.get(key, key): value for key, value in payload.items()})
            return self._request(self._sdk.generate.with_raw_response.prompt, **options)
        if operation == "model":
            method = self._sdk.generate.with_raw_response.run_model
        elif operation == "workflow":
            method = self._sdk.workflows.with_raw_response.run
        else:
            raise ValueError("Unsupported generation operation")
        return self._request(method, identifier, body=payload, **options)

    def _estimate(self, operation, identifier, payload):
        try:
            payload_json = json.dumps(payload, ensure_ascii=False, allow_nan=False).encode()
        except (TypeError, ValueError):
            raise ValueError("Parameters must contain finite JSON values") from None
        raw = self._dispatch_generation(
            operation, identifier, json.loads(payload_json), dry_run=True
        )
        result = _json(raw, exact=True)
        cost = result.get("creativeUnitsCost")
        if isinstance(cost, bool) or not isinstance(cost, (int, Decimal)) or cost < 0:
            raise AdapterError("Scenario returned no valid exact estimate")
        estimate = Estimate(
            operation,
            identifier,
            self.project_id,
            Decimal(cost),
            payload_json,
            raw,
            self._scope,
            time.monotonic(),
        )
        with self._estimate_lock:
            self._estimates[id(estimate)] = estimate
        return estimate

    def owns_estimate(self, estimate):
        with self._estimate_lock:
            return (
                not self._closed
                and isinstance(estimate, Estimate)
                and self._estimates.get(id(estimate)) is estimate
            )

    def submit_estimate(self, estimate, *, before_send):
        """Coordinator-only dispatch: commit intent in before_send or raise.

        Claim and consume an issued quote once, including across coordinators.
        The hook orders persistence; it does not grant spending authorization.
        """
        with self._estimate_lock:
            if not self.owns_estimate(estimate):
                raise ValueError("Use an unchanged, unused estimate issued by this active client")
            if not callable(before_send):
                raise TypeError("A durable submission claim callback is required")
            if not self._online():
                raise AdapterError("Online access is disabled")
            before_send()
            del self._estimates[id(estimate)]
        raw = self._dispatch_generation(estimate.operation, estimate.target_id, estimate.payload)
        job = _json(raw).get("job")
        if not isinstance(job, dict):
            raise AdapterError("Scenario returned no submission receipt")
        try:
            _identifier(job.get("jobId"))
        except ValueError:
            raise AdapterError("Scenario returned no valid remote job identity") from None
        return job
