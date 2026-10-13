# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Scenario's reason for a failed shared remote job, cleaned for display. No bpy.

Polling retrieves each known job with SDK 2.2.0 `jobs.retrieve` through
`SDKAdapter.job` (`jobs.with_raw_response.retrieve`). For a job whose `status`
is `failure`, the SDK and the API reference document two optional strings in
`Job.metadata`: `error` ("Eventual error for the job") and `hint` ("Actionable
hint for the user explaining what went wrong and how to resolve it"). The
coordinator validates the job ID and commits that status as the saved `failed`
state; this module only reads the retrieval that observed it.

The text comes from the service, so it is untrusted display text. Control,
format and line characters become single spaces. Links keep their scheme, host
and path but lose credentials, query and fragment, and a query string left on
a link without a scheme is dropped. Data URIs, bearer and basic credentials,
JSON web tokens and values after credential names (`password:`, `api_key=`,
`token=` and similar) are replaced; a value after a credential name that is
exactly a support id, quoted or not, is kept. The result is bounded to
MAX_LENGTH, and a support error id (`error_` followed by letters and digits) is
always kept, appended when cutting or link cleaning would lose it, because
support needs it. Text inside a redacted credential is never appended back.
Like remote progress, a reason is bound to the record that produced it, kept
in memory by its owner and never persisted.
"""

import re
import unicodedata
from dataclasses import dataclass
from urllib.parse import urlsplit

from .store import JobState

# The documented `Job.metadata` strings, in display order.
FIELDS = ("error", "hint")
MAX_LENGTH = 400
# Only this much of each value is read, for its text and for its support id.
MAX_INPUT = 4096
REDACTED = "[redacted]"
LINK_REMOVED = "[link removed]"
DATA_REMOVED = "[data removed]"

_HIDDEN = frozenset({"Cc", "Cf", "Cs", "Zl", "Zp", "Zs"})
_SPACES = re.compile(r" {2,}")
_TRAILING = ".,;:!?)]}'\""
_LINK = re.compile(r"(?i)\b[a-z][a-z0-9+.-]{0,31}://\S+")
_DATA = re.compile(r"(?i)\bdata:[a-z0-9.+-]+/[^\s,]*,\S*")
# A query string on a link without a scheme, such as `host/path?key=value`.
_QUERY = re.compile(r"(?<=[^\s?])\?[^\s?]*=\S*")
_SCHEME_CREDENTIAL = re.compile(r"(?i)\b(bearer|basic)\s+[A-Za-z0-9._~+/=-]{8,}")
_JWT = re.compile(r"\beyJ[A-Za-z0-9_-]{4,}\.[A-Za-z0-9_-]{4,}\.[A-Za-z0-9_-]{4,}")
_NAMED_CREDENTIAL = re.compile(
    r"(?i)(?<![A-Za-z0-9])("
    r"(?:x-)?(?:api[_-]?key|api[_-]?secret|client[_-]?secret|secret|access[_-]?token|"
    r"refresh[_-]?token|token|password|passwd|authorization|signature|credentials?|cookie|"
    r"session[_-]?id))"
    r"(\s*[:=]\s*)(\"[^\"]*\"|'[^']*'|[^\s,;&]+)"
)
# Scenario-style identifier: `error_` and letters and digits with at least one
# capital or digit, so words such as error_code are not mistaken for one.
_SUPPORT_ID = re.compile(
    r"(?<![A-Za-z0-9_])error_(?=[a-z0-9]*[A-Z0-9])[A-Za-z0-9]{6,64}(?![A-Za-z0-9_])"
)


@dataclass(frozen=True)
class RemoteFailure:
    """Scenario's cleaned reason for one failed job, bound to the record that observed it."""

    remote_job_id: str
    revision: int
    reason: str


def support_id(text):
    """The first support error id in ``text``, or None."""
    if not isinstance(text, str):
        return None
    match = _SUPPORT_ID.search(text)
    return match.group(0) if match else None


def _split_trailing(token):
    kept = token.rstrip(_TRAILING)
    return kept, token[len(kept) :]


def _link(match):
    url, tail = _split_trailing(match.group(0))
    try:
        parts = urlsplit(url)
        host, port = parts.hostname, parts.port
    except ValueError:
        return LINK_REMOVED + tail
    if not host:
        return LINK_REMOVED + tail
    if ":" in host:
        host = f"[{host}]"
    netloc = host if port is None else f"{host}:{port}"
    return f"{parts.scheme.lower()}://{netloc}{parts.path}{tail}"


def _drop_query(match):
    return _split_trailing(match.group(0))[1]


def _named_credential(match):
    """Redact a value after a credential name unless it is exactly a support id.

    The id may be quoted or followed by punctuation; anything else shaped like
    one (another case, length or character) is redacted like any value.
    """
    value = match.group(3)
    if len(value) > 1 and value[0] in "\"'" and value[-1] == value[0]:
        value = value[1:-1]
    if _SUPPORT_ID.fullmatch(_split_trailing(value)[0]):
        return match.group(0)
    return match.group(1) + match.group(2) + REDACTED


def _visible(value):
    """The first MAX_INPUT characters, with hidden and line characters as spaces."""
    return "".join(
        " " if unicodedata.category(char) in _HIDDEN else char for char in value[:MAX_INPUT]
    )


def _redact_credentials(text):
    text = _SCHEME_CREDENTIAL.sub(lambda match: f"{match.group(1)} {REDACTED}", text)
    text = _JWT.sub(REDACTED, text)
    return _NAMED_CREDENTIAL.sub(_named_credential, text)


def clean(value):
    """One service string as safe single-line text, unbounded; "" for anything else."""
    if not isinstance(value, str):
        return ""
    text = _LINK.sub(_link, _visible(value))
    text = _DATA.sub(DATA_REMOVED, text)
    text = _QUERY.sub(_drop_query, text)
    return _SPACES.sub(" ", _redact_credentials(text)).strip()


def _kept_support_id(value):
    """The support id to keep from one service string, or None.

    Links stay in place, so an id in a query string that cleaning drops is
    still found; an id-shaped part of a redacted credential or data URI is not.
    """
    if not isinstance(value, str):
        return None
    return support_id(_redact_credentials(_DATA.sub(DATA_REMOVED, _visible(value))))


def _bound(text, support):
    """Cut ``text`` to MAX_LENGTH with an ellipsis, always keeping ``support``."""
    if support is not None and support in text:
        if len(text) <= MAX_LENGTH:
            return text
        kept = text[: MAX_LENGTH - 1].rstrip()
        if support in kept:
            return kept + "…"
    suffix = f" (error id {support})" if support is not None else ""
    if len(text) + len(suffix) <= MAX_LENGTH:
        return text + suffix
    return text[: MAX_LENGTH - len(suffix) - 1].rstrip() + "…" + suffix


def reason(response):
    """Scenario's cleaned reason for a failed job response, or None.

    ``response`` is one decoded `GET /jobs/{jobId}` job record. Only a
    `failure` status has a reason: its `metadata.error`, then its
    `metadata.hint` when that adds something. Other types are ignored.
    """
    if not isinstance(response, dict) or response.get("status") != "failure":
        return None
    metadata = response.get("metadata")
    if not isinstance(metadata, dict):
        return None
    values = [metadata.get(name) for name in FIELDS]
    parts = []
    for part in (clean(value) for value in values):
        if part and not any(part in earlier for earlier in parts):
            parts.append(part)
    if not parts:
        return None
    if len(parts) > 1 and parts[0][-1] not in ".!?":
        parts[0] += "."
    support = next((found for found in map(_kept_support_id, values) if found), None)
    return _bound(" ".join(parts), support)


def observe(snapshot):
    """Interpret one coordinator RemoteSnapshot of a failed job, else return None.

    Only a snapshot whose saved record is `failed`, for the same remote job ID
    as the response, yields a reading; the coordinator committed that state
    from this same response.
    """
    record = snapshot.record
    if record.state != JobState.FAILED or record.remote_job_id is None:
        return None
    response = snapshot.response
    if not isinstance(response, dict) or response.get("jobId") != record.remote_job_id:
        return None
    text = reason(response)
    if text is None:
        return None
    return RemoteFailure(record.remote_job_id, record.revision, text)
