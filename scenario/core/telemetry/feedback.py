# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Feedback the user writes and sends: the relay's checks and one send with its outcome. No bpy.

A rating, a message and an optional email become one POST to the relay's feedback endpoint.
build checks them exactly as the relay does, so the extension never sends what it would
refuse: the message and email are trimmed of the whitespace JavaScript trims, absent fields
are left out rather than null, and at least a rating or a message is required. submit waits
up to TIMEOUT, beyond the relay's own four-second deadline, sends once and turns the answer
into a short sentence for the user; a failure is never retried automatically. An answer that
leaves open whether the relay recorded the feedback says it may not have been sent: a retry
reuses the submission ID, by which PostHog groups survey responses. Nothing logged names the
message or the email.
"""

import logging
import re
import urllib.error
import uuid
from dataclasses import dataclass

from . import relay
from .usage import INSTALL_ID

log = logging.getLogger("scenario.feedback")

FEEDBACK_URL = relay.BASE_URL + "/feedback"
TIMEOUT = 10.0
MAX_MESSAGE = 5000  # code points, counted after trimming as the relay counts them
MAX_EMAIL = 254
RATINGS = range(1, 6)

# JavaScript's whitespace, which the relay's trim() removes and its \s matches: tab to
# carriage return, the space separators, the line and paragraph separators and U+FEFF.
# str.strip() and Python's \s differ: they add U+001C to U+001F and U+0085, not U+FEFF.
SPACE = "".join(
    map(
        chr,
        (0x9, 0xA, 0xB, 0xC, 0xD, 0x20, 0xA0, 0x1680, *range(0x2000, 0x200B), 0x2028, 0x2029)
        + (0x202F, 0x205F, 0x3000, 0xFEFF),
    )
)
_PART = "[^" + "".join(map(re.escape, SPACE)) + "@]+"
EMAIL = re.compile(_PART + "@" + _PART + r"\." + _PART)

NEEDS_CONTENT = "Add a rating or a message"
MESSAGE_TOO_LONG = f"The message is too long: {MAX_MESSAGE:,} characters at most"
EMAIL_TOO_LONG = f"The email address is too long: {MAX_EMAIL} characters at most"
EMAIL_INVALID = "Check the email address, for example name@example.com"
BAD_RATING = "Choose a rating from 1 to 5"


class FeedbackError(ValueError):
    """Feedback the relay would refuse; the text is a plain reason to show the user."""


@dataclass(frozen=True)
class Outcome:
    sent: bool
    text: str


SENT = Outcome(True, "Feedback sent, thank you")
UNAVAILABLE = Outcome(False, "Feedback is not available right now; try again later")
RATE_LIMITED = Outcome(False, "Too many messages; try again in a minute")
# Not sent: the request never reached the relay, or the relay refused it.
UNREACHABLE = Outcome(False, "Could not reach Scenario; check your connection and try again")
FAILED = Outcome(False, "Something went wrong; your feedback was not sent")
# Uncertain: the request went out, but no answer confirmed or refused it.
NO_ANSWER = Outcome(False, "No answer from Scenario; your feedback may not have been sent")
UNCONFIRMED = Outcome(False, "Something went wrong; your feedback may not have been sent")


def trim(text):
    """The text as the relay's trim() leaves it."""
    return text.strip(SPACE)


def _fields(rating, message, email):
    """The fields to send, or FeedbackError with the first reason the relay would refuse."""
    fields = {}
    if rating is not None:
        if type(rating) is not int or rating not in RATINGS:  # JSON true is not a rating
            raise FeedbackError(BAD_RATING)
        fields["rating"] = rating
    message = trim(message or "")
    if message:
        if len(message) > MAX_MESSAGE:
            raise FeedbackError(MESSAGE_TOO_LONG)
        fields["message"] = message
    email = trim(email or "")
    if email:
        if len(email) > MAX_EMAIL:
            raise FeedbackError(EMAIL_TOO_LONG)
        if not EMAIL.fullmatch(email):
            raise FeedbackError(EMAIL_INVALID)
        fields["email"] = email
    if "rating" not in fields and "message" not in fields:
        raise FeedbackError(NEEDS_CONTENT)
    return fields


def problem(rating=None, message="", email=""):
    """Why the relay would refuse this feedback, in plain words, or None when it can be sent."""
    try:
        _fields(rating, message, email)
    except FeedbackError as error:
        return str(error)
    return None


def build(rating=None, message="", email="", *, context=None, install_id=None, submission_id=None):
    """The relay's feedback body; raises FeedbackError when the relay would refuse it.

    `rating` is None or 1 to 5. A blank message or email is left out. `install_id` is the
    usage install ID, passed only while usage sharing is on; an unusable one is left out.
    Each body gets a new random submission ID unless one is given.
    """
    fields = _fields(rating, message, email)
    submission_id = uuid.uuid4().hex if submission_id is None else submission_id
    if not isinstance(submission_id, str) or not INSTALL_ID.fullmatch(submission_id):
        raise ValueError("submission_id must be 32 lowercase hexadecimal digits")
    payload = {"submission_id": submission_id}
    if isinstance(install_id, str) and INSTALL_ID.fullmatch(install_id):
        payload["install_id"] = install_id
    payload["context"] = relay.sanitize_context(context)
    payload.update(fields)
    return payload


def submit(payload, *, send=None, url=FEEDBACK_URL, timeout=TIMEOUT):
    """POST one feedback body once and return its Outcome; never raises, never retries.

    `send(url, payload, timeout)` defaults to relay.post_json, which returns the HTTP status
    and raises for a refusal or a failure. urllib raises URLError when it could not send the
    request (no address, no connection, TLS); a plain OSError such as a timeout or a reset
    connection comes while it waits for the answer, after the body went out. A refusal (4xx)
    was not recorded; a server error other than 503 or an unexpected answer may have been.
    """
    try:
        status = (send or relay.post_json)(url, payload, timeout)
    except urllib.error.HTTPError as error:  # before URLError, its base class
        status = error.code
    except urllib.error.URLError as error:
        log.info("Feedback not sent: %s", type(error.reason).__name__)
        return UNREACHABLE
    except OSError as error:
        log.info("Feedback may not have been sent: %s", type(error).__name__)
        return NO_ANSWER
    except ValueError as error:  # refused before sending: the body exceeds the relay's limit
        log.warning("Feedback not sent: %s", type(error).__name__)
        return FAILED
    except Exception as error:
        log.warning("Feedback may not have been sent: %s", type(error).__name__)
        return UNCONFIRMED
    if status == 202:
        return SENT
    log.info("Feedback not confirmed: HTTP %s", status)
    if status == 503:
        return UNAVAILABLE
    if status == 429:
        return RATE_LIMITED
    if isinstance(status, int) and 400 <= status < 500:
        return FAILED
    return UNCONFIRMED
