# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Scoped SDK reads and exact estimates for the consolidated runtime.

No bpy imports, ambient credentials, redirects, automatic retries or paid
dispatch. The shared job runtime must persist intent before adding dispatch.
SDK imports are lazy so package registration does not start client work.
"""

import copy
import json
import math
from collections.abc import Callable
from dataclasses import dataclass, field
from decimal import Decimal
from types import SimpleNamespace
from urllib.parse import urlsplit

from ..schema.forms import prepare_run
from ..schema.params import parse_schema, validate
from .client import user_agent_string

API_URL = "https://api.cloud.scenario.com/v1"


class AdapterError(RuntimeError):
    """Safe text for UI/worker boundaries; never include response bodies or URLs."""


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


def _identifier(value):
    if not isinstance(value, str) or not value or value in {".", ".."} or value.strip() != value:
        raise ValueError("A nonempty identifier is required")
    if any(char in value for char in "/\\?#%") or any(ord(char) < 33 for char in value):
        raise ValueError("Identifier contains unsupported characters")
    return value


def _prepare(identifier, fields, parameters, ui_config=None):
    """Combine adopted value validation with retained conditional/one-of rules."""
    if isinstance(fields, dict):
        fields = [dict(value, name=name) for name, value in fields.items()]
    if not isinstance(fields, list) or not all(isinstance(value, dict) for value in fields):
        raise ValueError("A current input schema is required")
    fields = copy.deepcopy(fields)
    names = [value.get("name") for value in fields]
    if any(not isinstance(name, str) or not name for name in names) or len(set(names)) != len(
        names
    ):
        raise ValueError("Input names must be unique nonempty strings")
    parsed = parse_schema(SimpleNamespace(parameters=fields, ui_config=ui_config or {}))
    # Retain the canonical relaxation for a file required only without a prompt.
    # Conditional presence checks run after Studio's type/default validation.
    for value, spec in zip(fields, parsed.specs, strict=True):
        value["required"] = spec.required_always
    target, payload = prepare_run(identifier, {"parameters": fields}, parameters)
    errors = validate(parsed.specs, payload, parsed.one_of)
    if errors:
        raise ValueError("; ".join(errors))
    return target, payload


def _client(credentials, base_url, timeout, transport):
    import httpx
    from scenario_sdk import Scenario

    authorization = credentials.authorization()

    class SelectedAccount(Scenario):
        @property
        def default_headers(self):
            # Public SDK hook: use only adapter-owned headers. SDK 2.1.0 otherwise
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
        self._project_id = _identifier(project_id) if project_id is not None else None
        self._online = online
        self._scope = object()
        self._closed = False
        self._sdk = _client(credentials, base_url, timeout, transport)

    @property
    def project_id(self):
        return self._project_id

    def close(self):
        self._closed = True
        self._sdk.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()

    def _request(self, method, *args, **kwargs):
        from scenario_sdk import APIConnectionError, APIStatusError

        if self._closed:
            raise AdapterError("Scenario client is closed")
        if not self._online():
            raise AdapterError("Online access is disabled")
        if self.project_id is not None:
            kwargs["project_id"] = self.project_id
        try:
            response = method(*args, **kwargs)
            return response.read()
        except APIStatusError as error:
            raise AdapterError(f"Scenario request failed (HTTP {error.status_code})") from None
        except APIConnectionError:
            raise AdapterError("Could not reach Scenario") from None

    def _retrieve(self, resource, identifier, wrapper):
        method = getattr(self._sdk, resource).with_raw_response.retrieve
        value = _json(self._request(method, _identifier(identifier)))
        record = value.get(wrapper)
        if not isinstance(record, dict):
            raise AdapterError(f"Scenario returned no {wrapper} record")
        return record

    def model(self, identifier):
        return self._retrieve("models", identifier, "model")

    def workflow(self, identifier):
        return self._retrieve("workflows", identifier, "workflow")

    def asset(self, identifier):
        return self._retrieve("assets", identifier, "asset")

    def job(self, identifier):
        return self._retrieve("jobs", identifier, "job")

    def _catalog(self, resource, privacy, max_pages):
        if privacy not in {"public", "private"}:
            raise ValueError("Choose public or private catalog visibility")
        if not isinstance(max_pages, int) or isinstance(max_pages, bool) or max_pages < 1:
            raise ValueError("Page limit must be a positive integer")
        result, identifiers, tokens = [], set(), set()
        options = {"privacy": privacy, "page_size": 100}
        if resource == "models":
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
        target, payload = _prepare(identifier, fields, parameters, model.get("uiConfig"))
        return self._estimate("model", target, payload)

    def estimate_workflow(self, workflow, parameters):
        identifier = _identifier(workflow.get("id"))
        fields = workflow.get("inputs_definition")
        if fields is None:
            fields = workflow.get("inputs")
        target, payload = _prepare(identifier, fields, parameters)
        return self._estimate("workflow", target, payload)

    def _estimate(self, operation, identifier, payload):
        try:
            payload_json = json.dumps(payload, ensure_ascii=False, allow_nan=False).encode()
        except (TypeError, ValueError):
            raise ValueError("Parameters must contain finite JSON values") from None
        method = (
            self._sdk.generate.with_raw_response.run_model
            if operation == "model"
            else self._sdk.workflows.with_raw_response.run
        )
        raw = self._request(method, identifier, body=json.loads(payload_json), dry_run=True)
        result = _json(raw, exact=True)
        cost = result.get("creativeUnitsCost")
        if isinstance(cost, bool) or not isinstance(cost, (int, Decimal)) or cost < 0:
            raise AdapterError("Scenario returned no valid exact estimate")
        return Estimate(
            operation, identifier, self.project_id, Decimal(cost), payload_json, raw, self._scope
        )

    def owns_estimate(self, estimate):
        return isinstance(estimate, Estimate) and estimate.scope is self._scope
