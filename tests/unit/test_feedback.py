# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""User-sent feedback: the relay's checks mirrored and each outcome mapped. No sockets."""

import json
import logging
import ssl
import urllib.error

import pytest

from scenario.core.telemetry import feedback, relay

ID = "0123456789abcdef0123456789abcdef"
SUBMISSION = "fedcba9876543210fedcba9876543210"
CONTEXT = {"extension_version": "1.2.3", "blender_version": "5.0.1", "os": "macos", "arch": "arm64"}
# Every key the relay accepts at the top level; anything else is a 400.
RELAY_KEYS = {"submission_id", "install_id", "context", "rating", "message", "email"}
JS_SPACE = (
    "\t\n\v\f\r \u00a0\u1680\u2000\u2001\u2002\u2003\u2004\u2005\u2006\u2007\u2008\u2009"
    "\u200a\u2028\u2029\u202f\u205f\u3000\ufeff"
)


def build(**fields):
    fields.setdefault("submission_id", SUBMISSION)
    return feedback.build(**fields)


class Sends:
    """A fake transport: records each call, then answers with a status or raises."""

    def __init__(self, answer=202):
        self.answer, self.calls = answer, []

    def __call__(self, url, payload, timeout):
        self.calls.append((url, json.loads(json.dumps(payload)), timeout))
        if isinstance(self.answer, BaseException):
            raise self.answer
        return self.answer


def refusal(status):
    return urllib.error.HTTPError("https://relay.invalid/feedback", status, "refused", {}, None)


# -- the body -------------------------------------------------------------------
def test_only_given_fields_are_sent_never_null():
    assert build(rating=4) == {"submission_id": SUBMISSION, "context": {}, "rating": 4}
    assert build(message="Great") == {
        "submission_id": SUBMISSION,
        "context": {},
        "message": "Great",
    }
    payload = build(
        rating=5, message="Love it", email="me@example.com", context=CONTEXT, install_id=ID
    )
    assert list(payload) == [
        "submission_id",
        "install_id",
        "context",
        "rating",
        "message",
        "email",
    ]
    assert payload["context"] == CONTEXT and set(payload) == RELAY_KEYS
    assert None not in payload.values()


def test_the_install_id_is_sent_only_when_given_and_well_formed():
    assert "install_id" not in build(rating=3)
    assert "install_id" not in build(rating=3, install_id=None)
    assert build(rating=3, install_id=ID)["install_id"] == ID
    for unusable in ("", ID.upper(), ID[:-1], ID + "0", 42):
        assert "install_id" not in build(rating=3, install_id=unusable)


def test_each_body_gets_a_new_random_submission_id():
    first = feedback.build(rating=1)["submission_id"]
    second = feedback.build(rating=1)["submission_id"]
    assert feedback.INSTALL_ID.fullmatch(first) and feedback.INSTALL_ID.fullmatch(second)
    assert first != second
    for invalid in ("", SUBMISSION.upper(), SUBMISSION[:-1], 7):
        with pytest.raises(ValueError):
            feedback.build(rating=1, submission_id=invalid)


def test_the_context_keeps_only_fields_the_relay_accepts():
    payload = build(
        rating=2, context={**CONTEXT, "blender_version": "5.0", "hostname": "studio", "os": None}
    )
    assert payload["context"] == {"extension_version": "1.2.3", "arch": "arm64"}
    assert build(rating=2, context=None)["context"] == {}


@pytest.mark.parametrize("rating", [1, 2, 3, 4, 5])
def test_ratings_one_to_five_are_sent(rating):
    assert build(rating=rating)["rating"] == rating


@pytest.mark.parametrize("rating", [0, 6, -1, True, False, 3.0, "3"])
def test_other_ratings_are_refused(rating):
    with pytest.raises(feedback.FeedbackError) as refused:
        build(rating=rating, message="text")
    assert str(refused.value) == feedback.BAD_RATING


def test_a_rating_or_a_message_is_required():
    for fields in ({}, {"message": ""}, {"message": JS_SPACE}, {"email": "me@example.com"}):
        with pytest.raises(feedback.FeedbackError) as refused:
            build(**fields)
        assert str(refused.value) == feedback.NEEDS_CONTENT
        assert feedback.problem(**fields) == feedback.NEEDS_CONTENT
    assert feedback.problem(rating=3) is None
    assert feedback.problem(message="x") is None
    assert build(rating=3, message=JS_SPACE) == {
        "submission_id": SUBMISSION,
        "context": {},
        "rating": 3,
    }


def test_the_message_is_trimmed_as_javascript_trims_it():
    assert build(message=f"{JS_SPACE}  Two\nlines \t{JS_SPACE}")["message"] == "Two\nlines"
    # Python's strip() would remove these, but the relay's trim() keeps them.
    assert build(message="\x1chello\x85")["message"] == "\x1chello\x85"
    assert build(message="\x85")["message"] == "\x85"
    assert "\x85".strip() == ""  # why str.strip() is not used


def test_the_message_limit_counts_code_points_after_trimming():
    assert build(message="a" * feedback.MAX_MESSAGE)["message"] == "a" * 5000
    astral = "\U0001f600" * feedback.MAX_MESSAGE  # one code point, two UTF-16 units each
    assert build(message=f"  {astral}\n")["message"] == astral
    for too_long in ("a" * 5001, astral + "a"):
        with pytest.raises(feedback.FeedbackError) as refused:
            build(rating=5, message=too_long)
        assert (
            str(refused.value)
            == feedback.MESSAGE_TOO_LONG
            == ("The message is too long: 5,000 characters at most")
        )


@pytest.mark.parametrize(
    "email",
    [
        "me@example.com",
        "first.last+tag@sub.example.co.uk",
        "a@b.c",
        "a@b.c.d",
        "name@d\u00e9j\u00e0.fr",
        "x\x85y@example.com",  # not whitespace for the relay
    ],
)
def test_emails_the_relay_accepts_are_sent(email):
    assert build(rating=4, email=email)["email"] == email


@pytest.mark.parametrize(
    "email",
    [
        "me",
        "me@example",
        "@example.com",
        "me@.com",
        "me@example.",
        "me@@example.com",
        "me@exa@mple.com",
        "m e@example.com",
        "me@exam\u00a0ple.com",
        "me@exam\ufeffple.com",  # whitespace for the relay, not for Python's \s
        "me@example.com\nother",
    ],
)
def test_emails_the_relay_refuses_are_not_sent(email):
    with pytest.raises(feedback.FeedbackError) as refused:
        build(rating=4, email=email)
    assert str(refused.value) == feedback.EMAIL_INVALID
    assert feedback.problem(rating=4, email=email) == feedback.EMAIL_INVALID


def test_the_email_is_trimmed_optional_and_at_most_254_characters():
    assert build(rating=4, email=f"{JS_SPACE}me@example.com\n")["email"] == "me@example.com"
    for blank in ("", JS_SPACE, None):
        assert "email" not in build(rating=4, email=blank)
    longest = "a" * (feedback.MAX_EMAIL - len("@example.com")) + "@example.com"
    assert len(longest) == 254 and build(rating=4, email=longest)["email"] == longest
    with pytest.raises(feedback.FeedbackError) as refused:
        build(rating=4, email="a" + longest)
    assert str(refused.value) == feedback.EMAIL_TOO_LONG


def test_the_largest_body_fits_the_relay_limit():
    payload = build(
        rating=5,
        message="\U0001f600" * feedback.MAX_MESSAGE,
        email="\U0001f600" * 250 + "@a.b",
        context=CONTEXT,
        install_id=ID,
    )
    assert len(json.dumps(payload, separators=(",", ":"))) < relay.MAX_BODY


# -- the send -------------------------------------------------------------------
class Response:
    status = 202

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


def test_the_posted_body_is_exactly_the_relay_shape():
    seen = []

    def opener(request, timeout, context):
        seen.append((request, timeout))
        return Response()

    payload = build(rating=4, message=" Nice ", context={**CONTEXT, "arch": None})
    outcome = feedback.submit(
        payload,
        send=lambda url, body, timeout: relay.post_json(url, body, timeout, opener=opener),
    )
    assert outcome == feedback.SENT and outcome.sent
    [(request, timeout)] = seen
    assert timeout == feedback.TIMEOUT == 10.0
    assert request.full_url == feedback.FEEDBACK_URL
    assert feedback.FEEDBACK_URL == "https://blender.scenario.com/telemetry/v1/feedback"
    assert request.data == (
        b'{"submission_id":"fedcba9876543210fedcba9876543210",'
        b'"context":{"extension_version":"1.2.3","blender_version":"5.0.1","os":"macos"},'
        b'"rating":4,"message":"Nice"}'
    )
    assert request.get_header("Content-type") == "application/json"
    assert request.get_header("User-agent").startswith("ScenarioBlender/")


def test_the_default_transport_is_the_relay_post(monkeypatch):
    sends = Sends()
    monkeypatch.setattr(relay, "post_json", sends)
    assert feedback.submit(build(rating=1)) == feedback.SENT
    [(url, payload, timeout)] = sends.calls
    assert (url, timeout) == (feedback.FEEDBACK_URL, 10.0) and payload["rating"] == 1


@pytest.mark.parametrize(
    ("answer", "outcome"),
    [
        (202, feedback.SENT),
        (200, feedback.FAILED),
        (204, feedback.FAILED),
        (refusal(503), feedback.UNAVAILABLE),
        (refusal(429), feedback.RATE_LIMITED),
        (refusal(400), feedback.FAILED),
        (refusal(404), feedback.FAILED),
        (refusal(405), feedback.FAILED),
        (refusal(413), feedback.FAILED),
        (refusal(415), feedback.FAILED),
        (refusal(500), feedback.FAILED),
        (refusal(502), feedback.FAILED),
        (urllib.error.URLError("name resolution failed"), feedback.UNREACHABLE),
        (TimeoutError("timed out"), feedback.UNREACHABLE),
        (ConnectionRefusedError("refused"), feedback.UNREACHABLE),
        (ConnectionResetError("reset"), feedback.UNREACHABLE),
        (ssl.SSLError("certificate verify failed"), feedback.UNREACHABLE),
        (OSError("network is unreachable"), feedback.UNREACHABLE),
        (ValueError("telemetry body exceeds the relay's limit"), feedback.FAILED),
        (RuntimeError("unexpected"), feedback.FAILED),
    ],
)
def test_each_answer_maps_to_one_short_sentence_after_one_try(answer, outcome, caplog):
    sends = Sends(answer)
    secret = "private words"
    payload = build(rating=2, message=secret, email="reply@example.com")
    with caplog.at_level(logging.DEBUG, logger="scenario.feedback"):
        assert feedback.submit(payload, send=sends, url="https://relay.invalid/feedback") is outcome
    assert len(sends.calls) == 1  # never retried
    assert sends.calls[0][2] == feedback.TIMEOUT
    for private in (secret, "reply@example.com", "relay.invalid"):
        assert private not in caplog.text


def test_outcome_sentences_are_short_plain_and_distinct():
    outcomes = (
        feedback.SENT,
        feedback.UNAVAILABLE,
        feedback.RATE_LIMITED,
        feedback.UNREACHABLE,
        feedback.FAILED,
    )
    assert [outcome.sent for outcome in outcomes] == [True, False, False, False, False]
    texts = [outcome.text for outcome in outcomes]
    assert len(set(texts)) == len(texts)
    for text in texts:
        assert len(text) <= 80  # the sidebar's status line shows 80 characters
        assert "HTTP" not in text and "relay" not in text.lower() and not text.endswith(".")
    assert feedback.UNAVAILABLE.text.startswith("Feedback is not available right now")
    assert feedback.RATE_LIMITED.text.startswith("Too many messages")
    assert feedback.UNREACHABLE.text.startswith("Could not reach Scenario")
    assert feedback.FAILED.text.startswith("Something went wrong")
