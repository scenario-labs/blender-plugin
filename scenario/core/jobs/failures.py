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

The text comes from the service, so it is untrusted display text, and one
pipeline (`clean`) prepares everything shown. Control, format and line
characters become single spaces. Links keep their scheme, host and path but
lose credentials, query and fragment; `user:password@` before a host without a
scheme is dropped, as is a query string left on such a link. Data URIs, bearer
and basic credentials, JSON web tokens, an Authorization value with its scheme
word, and the value after any name ending in a credential word (`password`,
`api_key`, `"apiKey"`, `aws_secret_access_key`, `X-Amz-Signature`, `token` and
similar, quoted or not) are replaced. A value after such a name that is exactly
a support id (lowercase `error_` and 6 to 64 letters and digits with a capital
or digit), quoted or not, is kept, because support needs it.

When `metadata.error` and `metadata.hint` contain each other, ignoring case,
spacing and final punctuation, only the longer is shown. The joined text is cut
to MAX_LENGTH at a word boundary, so no marker, word or id is split, and when
the cut drops the first support id of the cleaned text it is appended. The id
is only ever taken from the cleaned text: an id that appeared only in removed
content, such as a link's query or userinfo, is not shown.

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
# `user:password@` starting a token before a host, on a link without a scheme.
_USERINFO = re.compile(r"(?<![^\s(\[<\"'])[^\s/@:()\[\]<>\"']+:[^\s/@]+@(?=[A-Za-z0-9])")
_SCHEME_CREDENTIAL = re.compile(r"(?i)\b(bearer|basic)\s+[A-Za-z0-9._~+/=-]{8,}")
_JWT = re.compile(r"\beyJ[A-Za-z0-9_-]{4,}\.[A-Za-z0-9_-]{4,}\.[A-Za-z0-9_-]{4,}")
_VALUE = r"(\"[^\"]*\"|'[^']*'|[^\s,;&]+)"
# An Authorization header's whole value, including its scheme word (token, Digest...).
_AUTHORIZATION = re.compile(
    r"(?i)(?<![A-Za-z0-9])((?:proxy-)?authorization[\"']?\s*[:=]\s*)"
    r"(?:[A-Za-z][A-Za-z0-9-]*\s+)?" + _VALUE
)
# Any `name: value` or `name=value`, the name optionally closed by a quote as in JSON.
_NAME = re.compile(r"(?<![A-Za-z0-9_.-])([A-Za-z][A-Za-z0-9_.-]{0,63})[\"']?\s*[:=]\s*")
_VALUE_AT = re.compile(_VALUE)
# A name is a credential when, lowercased without separators, it ends with one of
# these, as in film_case_study's key filter, plus session and signed-URL key ids.
_CREDENTIAL_WORDS = (
    "apikey",
    "apisecret",
    "accesskey",
    "privatekey",
    "secret",
    "password",
    "passwd",
    "credential",
    "credentials",
    "authorization",
    "token",
    "cookie",
    "signature",
    "sessionid",
    "keypairid",
)
_MARKERS = re.compile("|".join(map(re.escape, (REDACTED, LINK_REMOVED, DATA_REMOVED))))
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


def _exact_support_id(value):
    """Whether a credential value is exactly a support id, quoted or before punctuation.

    Anything else shaped like one (another case, length or character) is not.
    """
    if len(value) > 1 and value[0] in "\"'" and value[-1] == value[0]:
        value = value[1:-1]
    return _SUPPORT_ID.fullmatch(_split_trailing(value)[0]) is not None


def _redact_named(text):
    """Replace the value after every name ending in a credential word.

    Names are read left to right without consuming the value of a name that is
    not a credential, so `note: password=x` still reaches `password`.
    """
    parts, position = [], 0
    while (match := _NAME.search(text, position)) is not None:
        name = re.sub(r"[^a-z0-9]", "", match.group(1).lower())
        value = _VALUE_AT.match(text, match.end()) if name.endswith(_CREDENTIAL_WORDS) else None
        parts.append(text[position : match.end()])
        position = match.end()
        if value is not None:
            parts.append(value.group(0) if _exact_support_id(value.group(0)) else REDACTED)
            position = value.end()
    parts.append(text[position:])
    return "".join(parts)


def _visible(value):
    """The first MAX_INPUT characters, with hidden and line characters as spaces."""
    return "".join(
        " " if unicodedata.category(char) in _HIDDEN else char for char in value[:MAX_INPUT]
    )


def clean(value):
    """One service string as safe single-line text, unbounded; "" for anything else.

    This is the only path from service text to anything shown, the support id included.
    """
    if not isinstance(value, str):
        return ""
    text = _LINK.sub(_link, _visible(value))
    text = _USERINFO.sub("", text)
    text = _DATA.sub(DATA_REMOVED, text)
    text = _QUERY.sub(_drop_query, text)
    text = _AUTHORIZATION.sub(lambda match: match.group(1) + REDACTED, text)
    text = _SCHEME_CREDENTIAL.sub(lambda match: f"{match.group(1)} {REDACTED}", text)
    text = _JWT.sub(REDACTED, text)
    return _SPACES.sub(" ", _redact_named(text)).strip()


def _cut(text, room):
    """At most ``room`` characters of cleaned ``text``, ending at a word boundary.

    A cut inside a marker or support id moves before it. Otherwise a cut inside
    a word moves back to the last space when that keeps at least half the room;
    only a single word longer than that is split.
    """
    if len(text) <= room:
        return text
    end = room
    for match in (*_MARKERS.finditer(text), *_SUPPORT_ID.finditer(text)):
        if match.start() < end < match.end():
            end = match.start()
    if text[end] != " ":
        space = text.rfind(" ", 0, end)
        if space >= room // 2:
            end = space
    return text[:end].rstrip()


def _bound(text):
    """Cut cleaned ``text`` to MAX_LENGTH with an ellipsis, keeping its first support id."""
    if len(text) <= MAX_LENGTH:
        return text
    kept = _cut(text, MAX_LENGTH - 1)
    support = support_id(text)
    if support is None or support in kept:
        return kept + "…"
    suffix = f" (error id {support})"
    return _cut(text, MAX_LENGTH - len(suffix) - 1) + "…" + suffix


def _same(text):
    """Comparison form: case-folded, single-spaced, without final punctuation."""
    return " ".join(text.casefold().split()).rstrip(".!?;:, ")


def reason(response):
    """Scenario's cleaned reason for a failed job response, or None.

    ``response`` is one decoded `GET /jobs/{jobId}` job record. Only a
    `failure` status has a reason: its `metadata.error`, then its
    `metadata.hint`, or only the longer when one contains the other. Other
    types are ignored.
    """
    if not isinstance(response, dict) or response.get("status") != "failure":
        return None
    metadata = response.get("metadata")
    if not isinstance(metadata, dict):
        return None
    error, hint = (clean(metadata.get(name)) for name in FIELDS)
    # When one contains the other, only the longer says everything.
    if error and hint and _same(hint) in _same(error):
        hint = ""
    elif error and hint and _same(error) in _same(hint):
        error = ""
    parts = [part for part in (error, hint) if part]
    if not parts:
        return None
    if len(parts) > 1 and parts[0][-1] not in ".!?":
        parts[0] += "."
    return _bound(" ".join(parts))


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
