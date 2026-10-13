# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Scenario's reason for a failed shared remote job, shown only when it is plain text. No bpy.

Polling retrieves each known job with SDK 2.2.0 `jobs.retrieve` through
`SDKAdapter.job` (`jobs.with_raw_response.retrieve`). For a job whose `status`
is `failure`, the SDK and the API reference document two optional strings in
`Job.metadata`: `error` ("Eventual error for the job") and `hint` ("Actionable
hint for the user explaining what went wrong and how to resolve it"). The
coordinator validates the job ID and commits that status as the saved `failed`
state; this module only reads the retrieval that observed it.

The text comes from the service, so it is untrusted. Nothing is rewritten or
redacted: each part is either shown as it is or replaced by a fixed sentence,
through an allowlist gate made of plain string operations. After reading at
most MAX_INPUT characters and turning control, format and space characters into
single spaces, a part is showable only when:

- every character is a letter, a digit, a space or one of `. , ; : ' " ( ) - !
  ? / % _`, and the part contains no `//`;
- every space-separated token, without surrounding punctuation, is an exact
  support id, a Scenario resource id, a word of letters with inner hyphens or
  apostrophes shorter than 32 characters, or any other token shorter than 12
  characters that switches between letters and digits at most twice;
- a `/` only joins two tokens shorter than 12 characters that each pass these
  same rules;
- no token contains a credential word (`key`, `secret`, `token`, `password`,
  `passwd`, `pwd`, `auth`, `credential`, `signature`, `session`, `cookie`, or
  `sig` alone), also with its separators removed (`tok/en`, `pass_word`) or
  digits standing for letters (`tok3n`), except a few harmless words such as
  `keyframe` or `author`.

A part that is not showable reads NOT_SHOWN, and nothing is taken from it. When
`metadata.error` and `metadata.hint` contain each other, ignoring case, spacing
and final punctuation, only the longer is shown; when no part is showable, the
reason is UNREADABLE. The joined text is cut to MAX_LENGTH at a word boundary,
never inside a support id, and when the cut drops the first support id of the
shown text, it is appended. Like remote progress, a reason is bound to the
record that produced it, kept in memory by its owner and never persisted.
"""

import unicodedata
from dataclasses import dataclass

from .store import JobState

# The documented `Job.metadata` strings, in display order.
FIELDS = ("error", "hint")
MAX_LENGTH = 400
# Only this much of each value is read.
MAX_INPUT = 4096
NOT_SHOWN = "Scenario reported more details that are not shown here."
UNREADABLE = "Scenario reported a failure without a readable reason."

_HIDDEN = frozenset({"Cc", "Cf", "Cs", "Zl", "Zp", "Zs"})
_PUNCTUATION = ".,;:'\"()-!?/%_"
# Punctuation around a token; a `/` stays part of it, so `/path` is never a word.
_SURROUNDING = _PUNCTUATION.replace("/", "")
_SHORT = 12
_WORD = 32
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
# Digits written for letters, as in `tok3n` or `s3ss10n`.
_LOOKALIKES = str.maketrans("013457", "oieast")
# Ordinary words that contain a credential word but are not one.
_HARMLESS_WORDS = frozenset(
    {
        "author",
        "authored",
        "authors",
        "keyboard",
        "keyframe",
        "keyframes",
        "keyword",
        "keywords",
    }
)
# Scenario resource identifiers, as recorded fixtures and job records show them.
_RESOURCE_PREFIXES = ("model", "job", "asset", "team", "proj", "col", "workflow", "upload", "apiu")
_RESOURCE_LENGTH = range(20, 25)
# A public model's slug: 2 to 9 lowercase hyphenated words of at most 16 characters.
_SLUG_WORDS = range(2, 10)
_SLUG_WORD = range(1, 17)
_SUPPORT_LENGTH = range(6, 65)


@dataclass(frozen=True)
class RemoteFailure:
    """Scenario's shown reason for one failed job, bound to the record that observed it."""

    remote_job_id: str
    revision: int
    reason: str


def _ascii_alnum(text):
    return text.isascii() and text.isalnum()


def _is_support_id(token):
    """`error_` and 6 to 64 ASCII letters and digits, with a capital or a digit."""
    rest = token[6:] if token.startswith("error_") else ""
    return (
        len(rest) in _SUPPORT_LENGTH
        and _ascii_alnum(rest)
        and any(char.isupper() or char.isdigit() for char in rest)
    )


def _is_resource_id(token):
    """A resource prefix and 20 to 24 ASCII letters and digits, or a public model slug."""
    prefix, separator, rest = token.partition("_")
    if not separator or prefix not in _RESOURCE_PREFIXES:
        return False
    if len(rest) in _RESOURCE_LENGTH and _ascii_alnum(rest):
        return True
    words = rest.split("-")
    return (
        prefix == "model"
        and len(rest) <= 48
        and len(words) in _SLUG_WORDS
        and all(len(word) in _SLUG_WORD and _ascii_alnum(word) for word in words)
        and rest == rest.lower()
    )


def support_id(text):
    """The first exact support id among the space-separated tokens of ``text``, or None."""
    if not isinstance(text, str):
        return None
    for token in text.split():
        core = token.strip(_SURROUNDING)
        if _is_support_id(core):
            return core
    return None


def _normalize(value):
    """The first MAX_INPUT characters in NFC, hidden characters as single spaces."""
    text = unicodedata.normalize("NFC", value[:MAX_INPUT])
    return " ".join(
        "".join(" " if unicodedata.category(char) in _HIDDEN else char for char in text).split()
    )


def _allowed(char):
    return char == " " or char.isalpha() or char.isdecimal() or char in _PUNCTUATION


def _switches(token):
    """How many times a token switches between letters and digits."""
    kinds = [char.isdecimal() for char in token if char.isalpha() or char.isdecimal()]
    return sum(1 for before, after in zip(kinds, kinds[1:], strict=False) if before != after)


def _plain_word(word):
    """Letters, with hyphens or apostrophes only between them, shorter than 32 characters."""
    letters = word.replace("-", "").replace("'", "")
    return len(word) < _WORD and letters.isalpha() and word[0].isalpha() and word[-1].isalpha()


def _credential(token):
    """Whether a token holds a credential word.

    The token is read as written and with every separator removed, so a word
    split as `tok/en`, `tok_en` or `pass/word` is found, and each form also
    with digits read as the letters they stand for (`tok3n`). A token that is
    a harmless word in either form (`keyframe`, `key-frame`) is not one.
    """
    lowered = token.lower()
    joined = "".join(char for char in lowered if char.isalnum())
    if lowered in _HARMLESS_WORDS or joined in _HARMLESS_WORDS:
        return False
    for form in (lowered, joined):
        for spelling in (form, form.translate(_LOOKALIKES)):
            if spelling == "sig" or any(word in spelling for word in _CREDENTIAL_WORDS):
                return True
    return False


def _showable_token(core):
    if _is_support_id(core) or _is_resource_id(core):
        return True
    if _credential(core):
        return False
    if "/" in core:
        # A pair's sides are short tokens that each pass these same rules.
        sides = core.split("/")
        return len(sides) == 2 and all(
            0 < len(side) < _SHORT and _showable_token(side) for side in sides
        )
    if _plain_word(core):
        return True
    return len(core) < _SHORT and _switches(core) <= 2


def _showable(text):
    """Whether one normalized part is plain text that may be shown as it is."""
    if "//" in text or not all(_allowed(char) for char in text):
        return False
    for token in text.split():
        core = token.strip(_SURROUNDING)
        if core and not _showable_token(core):
            return False
    return True


def _cut(text, room):
    """At most ``room`` characters of ``text``, ending at a word boundary.

    A cut inside a support id moves before it. Otherwise a cut inside a word
    moves back to the last space when that keeps at least half the room; only
    a single word longer than that is split.
    """
    if len(text) <= room:
        return text
    end = room
    start = text.rfind(" ", 0, end) + 1
    stop = text.find(" ", end)
    stop = len(text) if stop < 0 else stop
    if start < end < stop and _is_support_id(text[start:stop].strip(_SURROUNDING)):
        end = start
    if text[end] != " ":
        space = text.rfind(" ", 0, end)
        if space >= room // 2:
            end = space
    return text[:end].rstrip()


def _bound(text):
    """Cut shown ``text`` to MAX_LENGTH with an ellipsis, keeping its first support id."""
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
    """The reason shown for a failed job response, or None when Scenario gave none.

    ``response`` is one decoded `GET /jobs/{jobId}` job record. Only a
    `failure` status has a reason: its `metadata.error`, then its
    `metadata.hint`, each shown when plain text and replaced by NOT_SHOWN
    otherwise; when one shown part contains the other, only the longer is
    kept, and when no part is showable the reason is UNREADABLE. Missing,
    blank and non-text values give no part.
    """
    if not isinstance(response, dict) or response.get("status") != "failure":
        return None
    metadata = response.get("metadata")
    if not isinstance(metadata, dict):
        return None
    values = [metadata.get(name) for name in FIELDS]
    texts = [_normalize(value) if isinstance(value, str) else "" for value in values]
    texts = [text for text in texts if text]
    if not texts:
        return None
    shown = [text if _showable(text) else None for text in texts]
    if all(text is None for text in shown):
        return UNREADABLE
    if len(shown) == 2 and None not in shown:
        error, hint = shown
        if _same(hint) in _same(error):
            shown = [error]
        elif _same(error) in _same(hint):
            shown = [hint]
    parts = [NOT_SHOWN if text is None else text for text in shown]
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
