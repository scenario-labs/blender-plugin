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

The text comes from the service, so it is untrusted display text. One
pipeline (`clean`) prepares everything shown, and it is conservative by
default: when in doubt it redacts, and only a small explicit allowlist keeps
harmless names readable.

1. Line breaks are kept as clause ends; other control, format and space
   characters become spaces. Only the first MAX_INPUT characters are read.
2. Links keep their scheme, host and path, without credentials, query or
   fragment. `something:something@` userinfo reads `[redacted]@`: in a link
   (`scheme://` or `//`) only when it is in the authority, so an `@` in the
   path (`brick@2x.png`, `/@handle`) keeps the link; in any other token
   whatever precedes it. A query string left on a link without a scheme is
   dropped, and data URIs are removed.
3. Bearer and basic credentials and JSON web tokens read `[redacted]`.
4. A credential name is any `name:` or `name=`, quoted as in JSON or not, whose
   letters and digits contain `key`, `secret`, `token`, `password`, `passwd`,
   `pwd`, `auth`, `credential`, `signature`, `session` or `cookie`, or that has
   `sig` as a word, unless it is an allowlisted harmless name (`max_tokens`,
   `tokenizer`, `keyframe`, `keyword`, `author`...). Its whole value is
   redacted: a quoted value to its closing quote, where a backslash escapes a
   quote and a quote left open runs to the end of its line or of the text;
   otherwise everything up to the end of its clause (`, ; & ) ] }`, a quote, a
   line break, the next `name:` or the end). A value that starts with exactly
   a support id keeps that id, and the rest of its clause is redacted.
5. Any remaining run of 24 or more letters, digits and `+/_.-` (with `=`
   padding) is redacted when it looks like a secret (`_opaque`): one of its
   `/`- or `.`-separated parts is at least 12 characters long and mixes letters
   and digits, as base64, hex, JWT-like secrets and UUIDs do, or the whole run
   without its known ids still has 24 or more letters and digits, mixes them,
   and its words average 8 or more characters, as a secret split into
   all-letter and all-digit segments does. Known ids are a support id and a
   Scenario resource id: `model_`, `job_`, `asset_`, `team_`, `proj_`, `col_`,
   `workflow_`, `upload_` or `apiu_` and 20 to 24 letters and digits, or a
   public model's hyphenated lowercase slug; anything longer glued to a prefix
   is not one.

A support error id (lowercase `error_` and 6 to 64 letters and digits with a
capital or digit) is kept because support needs it. When `metadata.error` and
`metadata.hint` contain each other, ignoring case, spacing and final
punctuation, only the longer is shown. The joined text is cut to MAX_LENGTH at
a word boundary, so no marker, word or id is split, and when the cut drops the
first support id of the cleaned text it is appended. The id is only ever taken
from the cleaned text: an id that appeared only in removed content is not
shown.

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
# Line ends stay clause ends until the final whitespace collapse.
_LINE_ENDS = frozenset("\n\r\x0b\x0c\x1c\x1d\x1e\x85\u2028\u2029")
_TRAILING = ".,;:!?)]}'\""
_LINK = re.compile(r"(?i)\b[a-z][a-z0-9+.-]{0,31}://\S+")
_DATA = re.compile(r"(?i)\bdata:[a-z0-9.+-]+/[^\s,]*,\S*")
# A query string on a link without a scheme, such as `host/path?key=value`.
_QUERY = re.compile(r"(?<=[^\s?])\?[^\s?]*=\S*")
_SCHEME_CREDENTIAL = re.compile(r"(?i)\b(bearer|basic)\s+[A-Za-z0-9._~+/=-]{8,}")
_JWT = re.compile(r"\beyJ[A-Za-z0-9_-]{4,}\.[A-Za-z0-9_-]{4,}\.[A-Za-z0-9_-]{4,}")
# Any `name: value` or `name=value`, the name optionally closed by a quote as in JSON.
_NAME = re.compile(r"(?<![A-Za-z0-9_.-])([A-Za-z][A-Za-z0-9_.-]{0,63})[\"']?[ \t]*[:=][ \t]*")
# The next `name:` after a space ends an unquoted value.
_NEXT_NAME = re.compile(r" (?=[A-Za-z][A-Za-z0-9_.-]{0,63}[\"']?[ \t]*[:=])")
# A quoted value: a backslash escapes the next character, and a quote left open
# runs to the end of its line or of the text, so it is never left visible.
_QUOTED = re.compile(r"\"(?:[^\"\\\n]|\\.?)*(?:\"|(?=\n)|\Z)|'(?:[^'\\\n]|\\.?)*(?:'|(?=\n)|\Z)")
_CLAUSE_END = re.compile(r"[,;&)\]}\n\"']")
_CREDENTIAL_WORDS = (
    "key",
    "secret",
    "token",
    "password",
    "passwd",
    "pwd",
    "auth",
    "credential",
    "signature",
    "session",
    "cookie",
)
# Whole names, letters and digits only, that contain a credential word but are not one.
_HARMLESS_NAMES = frozenset(
    {
        "author",
        "authorid",
        "authorname",
        "authors",
        "inputtokens",
        "keyframe",
        "keyframes",
        "keyword",
        "keywords",
        "maxnewtokens",
        "maxtokens",
        "mintokens",
        "numtokens",
        "outputtokens",
        "tokencount",
        "tokenizer",
        "tokens",
        "totaltokens",
    }
)
_WORDS = re.compile(r"[A-Z]?[a-z]+|[A-Z]+(?![a-z])|[0-9]+")
# `=` only as trailing base64 padding, so `name=value` stays two parts.
_OPAQUE_RUN = re.compile(r"(?<![A-Za-z0-9+/=_.-])[A-Za-z0-9+/_.-]{24,}=*(?![A-Za-z0-9+/=_.-])")
_PARTS = re.compile(r"[/.]")
_WORD_BREAKS = re.compile(r"[/._+=-]+")
# Scenario resource identifiers, as recorded fixtures and job records show them:
# 20 to 24 letters and digits after the prefix, or a public model's lowercase
# slug of 2 to 9 hyphenated words of at most 16 characters. Anything longer
# glued to a prefix is not an identifier.
_RESOURCE_ID = re.compile(
    r"(?:model|job|asset|team|proj|col|workflow|upload|apiu)_[A-Za-z0-9]{20,24}"
    r"|model_(?=[a-z0-9-]{3,48}$)[a-z0-9]{1,16}(?:-[a-z0-9]{1,16}){1,8}"
)
# A link's start, with or without a scheme, before its authority.
_AUTHORITY_START = re.compile(r"[(\[<{\"']*(?:[A-Za-z][A-Za-z0-9+.-]{0,31}:)?//")
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


def _redact_userinfo(text):
    """Replace `something:something@` userinfo in every whitespace-separated token.

    In a link (`scheme://` or `//`), only an `@` in the authority, before the
    first `/` after `//`, ends userinfo, so `/@handle` or `brick@2x.png` in a
    path keeps the link. In any other token, the last `@` ends it, and
    everything before it, except opening brackets and quotes, is the userinfo
    when it has a colon. E-mail addresses have no colon there and stay readable.
    """

    def token(word):
        link = _AUTHORITY_START.match(word)
        if link is not None:
            start = link.end()
            path = word.find("/", start)
            at = word.rfind("@", start, len(word) if path < 0 else path)
            if at < 0 or ":" not in word[start:at]:
                return word
            return word[:start] + REDACTED + word[at:]
        at = word.rfind("@")
        if at <= 0 or ":" not in word[:at]:
            return word
        before = word[:at]
        lead = len(before) - len(before.lstrip("([<{\"'"))
        return before[:lead] + REDACTED + word[at:]

    return re.sub(r"[^\s]+", lambda match: token(match.group(0)), text)


def _credential_name(name):
    """Whether a `name:` or `name=` introduces a secret; conservative by default."""
    compact = re.sub(r"[^a-z0-9]", "", name.lower())
    if compact in _HARMLESS_NAMES:
        return False
    if any(word in compact for word in _CREDENTIAL_WORDS):
        return True
    return any(word.lower() == "sig" for word in _WORDS.findall(name))


def _clause_end(text, start):
    """End of an unquoted value: its clause delimiter, the next `name:` or the end."""
    end = len(text)
    for match in _CLAUSE_END.finditer(text, start):
        # The closing bracket of an earlier marker does not end the clause.
        if match.group() == "]" and any(
            text.startswith(marker, match.end() - len(marker))
            for marker in (REDACTED, LINK_REMOVED, DATA_REMOVED)
        ):
            continue
        end = match.start()
        break
    following = _NEXT_NAME.search(text, start, end)
    if following is not None:
        end = following.start()
    while end > start and text[end - 1] in " \t":
        end -= 1
    return end


def _redacted_value(value):
    """A credential value as shown: redacted, except a leading exact support id."""
    quote = value[0] if len(value) > 1 and value[0] in "\"'" and value[-1] == value[0] else ""
    inner = value[1:-1] if quote else value
    first, _, rest = inner.partition(" ")
    if not _SUPPORT_ID.fullmatch(_split_trailing(first)[0]):
        return REDACTED
    shown = f"{first} {REDACTED}" if rest.strip() else first
    return f"{quote}{shown}{quote}"


def _redact_named(text):
    """Replace the whole value after every credential name, left to right.

    A name that is not a credential's does not consume its value, so
    `note: password=x` still reaches `password`.
    """
    parts, position = [], 0
    while (match := _NAME.search(text, position)) is not None:
        parts.append(text[position : match.end()])
        position = match.end()
        if not _credential_name(match.group(1)):
            continue
        quoted = _QUOTED.match(text, position)
        end = quoted.end() if quoted is not None else _clause_end(text, position)
        if end > position:
            parts.append(_redacted_value(text[position:end]))
            position = end
    parts.append(text[position:])
    return "".join(parts)


def _mixed(part):
    return any(char.isalpha() for char in part) and any(char.isdigit() for char in part)


def _known_id(part):
    return bool(_SUPPORT_ID.fullmatch(part) or _RESOURCE_ID.fullmatch(part))


def _opaque(token):
    """Whether a 24+ character run looks like a secret rather than words and known ids.

    Either one of its `/`- or `.`-separated parts is 12+ characters and mixes
    letters and digits, or, without its known-id parts, the run still has 24+
    letters and digits, mixes them, and its words average 8 or more characters,
    as segments of a split secret do; hosts and paths are made of shorter words.
    """
    if _known_id(token):
        return False
    parts = [part for part in _PARTS.split(token) if not _known_id(part)]
    if any(len(part) >= 12 and _mixed(part) for part in parts):
        return True
    words = [word for part in parts for word in _WORD_BREAKS.split(part) if word]
    length = sum(len(word) for word in words)
    return length >= 24 and _mixed("".join(words)) and length >= 8 * len(words)


def _redact_opaque(text):
    """Redact long runs that look like secrets; see `_opaque`."""

    def run(match):
        return REDACTED if _opaque(match.group(0)) else match.group(0)

    return _OPAQUE_RUN.sub(run, text)


def _visible(value):
    """The first MAX_INPUT characters: line ends as newlines, other hidden ones as spaces."""
    return "".join(
        "\n" if char in _LINE_ENDS else " " if unicodedata.category(char) in _HIDDEN else char
        for char in value[:MAX_INPUT]
    )


def clean(value):
    """One service string as safe single-line text, unbounded; "" for anything else.

    This is the only path from service text to anything shown, the support id included.
    """
    if not isinstance(value, str):
        return ""
    text = _LINK.sub(_link, _visible(value))
    text = _redact_userinfo(text)
    text = _DATA.sub(DATA_REMOVED, text)
    text = _QUERY.sub(_drop_query, text)
    text = _SCHEME_CREDENTIAL.sub(lambda match: f"{match.group(1)} {REDACTED}", text)
    text = _JWT.sub(REDACTED, text)
    text = _redact_opaque(_redact_named(text))
    return " ".join(text.split())


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
