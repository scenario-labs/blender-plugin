# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Read and clean Scenario's reason for a failed job without Blender or network access.

No captured failed-job response exists under tests/fixtures. The failed record
below is synthetic: the recorded Patina `GET /jobs/{jobId}` reply with the
documented `failure` status and `metadata.error` / `metadata.hint` strings of
the pinned SDK's `JobMetadata`, and it must validate as that SDK's response.
"""

import copy
import json
import time
import typing
from pathlib import Path
from types import SimpleNamespace

import pytest
from scenario_sdk.types.job_retrieve_response import JobMetadata, JobRetrieveResponse

from scenario.core.jobs import failures
from scenario.core.jobs.store import JobState

RECORDED = Path(__file__).parents[1] / "fixtures" / "patina-copper-512" / "job.json"
SUPPORT_ID = "error_Q7fK2mXv9LpR4tNc8WbZ3hYd"
INTERNAL = f"An internal error occurred. Please contact support and provide this id: {SUPPORT_ID}"


def failed_job(error=INTERNAL, hint=None, *, status="failure"):
    """The recorded job reply, as Scenario reports a failure for it."""
    job = copy.deepcopy(json.loads(RECORDED.read_text(encoding="utf-8"))["job"])
    job["status"] = status
    job["progress"] = 0.1
    job["statusHistory"].append({"status": status, "date": "2026-08-28T07:38:37.989Z"})
    job["metadata"].pop("assetIds")
    for key, value in (("error", error), ("hint", hint)):
        if value is not None:
            job["metadata"][key] = value
    return job


def snapshot(response, *, state=JobState.FAILED, remote_job_id=None, revision=4):
    remote = response.get("jobId") if remote_job_id is None else remote_job_id
    record = SimpleNamespace(state=state, remote_job_id=remote, revision=revision)
    return SimpleNamespace(record=record, response=response)


def test_the_pinned_sdk_documents_both_failure_strings():
    for name in ("error", "hint"):
        field = JobMetadata.model_fields[name]
        assert field.annotation == typing.Optional[str]  # noqa: UP045 - the SDK's own spelling
        assert field.default is None
    assert failures.FIELDS == ("error", "hint")


def test_synthetic_failed_job_follows_the_sdk_contract_and_yields_its_message():
    job = failed_job()
    parsed = JobRetrieveResponse.model_validate({"job": job}).job
    assert (parsed.status, parsed.metadata.error) == ("failure", INTERNAL)
    assert failures.reason(job) == INTERNAL


def test_an_actionable_hint_follows_the_error_as_one_sentence():
    hint = "Reduce the mesh below 30,000 faces, then try again."
    job = failed_job("Input mesh is too dense", hint)
    assert JobRetrieveResponse.model_validate({"job": job}).job.metadata.hint == hint
    assert failures.reason(job) == f"Input mesh is too dense. {hint}"
    assert failures.reason(failed_job("Input mesh is too dense!", hint)).startswith(
        "Input mesh is too dense! Reduce"
    )


def test_a_hint_alone_or_repeated_is_shown_once():
    assert failures.reason(failed_job(None, "Try a smaller image.")) == "Try a smaller image."
    assert failures.reason(failed_job("Try a smaller image.", " Try a smaller image. ")) == (
        "Try a smaller image."
    )


@pytest.mark.parametrize(
    ("error", "hint", "expected"),
    [
        # The hint extends the error: only the longer text is shown.
        (
            "Input mesh is too dense",
            "Input mesh is too dense. Reduce it below 30,000 faces.",
            "Input mesh is too dense. Reduce it below 30,000 faces.",
        ),
        # The error already says what the hint repeats, in another case and punctuation.
        (
            "Input mesh is too dense. Reduce it below 30,000 faces.",
            "input mesh is too dense!",
            "Input mesh is too dense. Reduce it below 30,000 faces.",
        ),
        # Repeated whitespace does not hide a repeat.
        (
            "Input  mesh is too dense",
            "Input mesh is too\tdense, retry",
            "Input mesh is too dense, retry",
        ),
    ],
)
def test_an_error_and_hint_that_contain_each_other_are_shown_once(error, hint, expected):
    assert failures.reason(failed_job(error, hint)) == expected


@pytest.mark.parametrize(
    "status",
    ["success", "canceled", "in-progress", "queued", "pending", "warming-up", "finalizing", None],
)
def test_only_a_failure_status_has_a_reason(status):
    job = failed_job(status=status) if status else {**failed_job(), "status": None}
    assert failures.reason(job) is None


@pytest.mark.parametrize(
    "value", [None, "", "   \n\t", 0, 3.5, True, ["message"], {"message": "nested"}]
)
def test_missing_blank_or_non_text_values_give_no_reason(value):
    job = failed_job()
    job["metadata"]["error"] = value
    assert failures.reason(job) is None
    assert failures.reason({**job, "metadata": "not an object"}) is None
    assert failures.reason("not a job") is None


def test_control_format_and_line_characters_become_single_spaces():
    text = "Model\nfailed:\r\n\tinput\x00rejected retry‮ later​ now"
    assert failures.reason(failed_job(text)) == ("Model failed: input rejected retry later now")


def test_links_keep_their_place_but_lose_credentials_query_and_fragment():
    text = (
        "Download failed for https://user:pass@cdn.example.com:8443/a/b.png?X-Amz-Signature=abc"  # secrets-allow: synthetic fixture
        "&X-Amz-Credential=def#frag. See https://docs.example.com/errors/mesh, "  # secrets-allow: synthetic fixture
        "or (cdn.example.com/c.glb?Key-Pair-Id=K&Policy=P) and data:image/png;base64,iVBORw0KGgo="  # secrets-allow: synthetic fixture
    )
    cleaned = failures.reason(failed_job(text))
    assert cleaned == (
        "Download failed for https://cdn.example.com:8443/a/b.png. "
        "See https://docs.example.com/errors/mesh, or (cdn.example.com/c.glb) and "
        f"{failures.DATA_REMOVED}"
    )
    for leak in ("user", "pass", "Signature", "Credential", "frag", "Key-Pair", "Policy", "iVBOR"):
        assert leak not in cleaned


def test_unparseable_links_are_removed():
    cleaned = failures.reason(failed_job("Bad host https://[::1/x?token=t here"))
    assert cleaned == f"Bad host {failures.LINK_REMOVED} here"


@pytest.mark.parametrize(
    ("text", "secret"),
    [
        ('Rejected {"apiKey": "sk-abc123456"}', "sk-abc123456"),
        ("Rejected {'client_secret':'cs-abc123456'}", "cs-abc123456"),
        ("Rejected aws_secret_access_key=abc123456 for the bucket", "abc123456"),
        ("Rejected X-Goog-Signature=abc123456&X-Goog-Date=1", "abc123456"),
        ("Rejected github_token: abc123456", "abc123456"),
        ("Rejected Authorization: token abc123456", "abc123456"),
        ("Rejected Proxy-Authorization: Digest abc123456", "abc123456"),
        ("Rejected note: password=abc123456", "abc123456"),
        ("Rejected https://host/p;jsessionid=abc123456", "abc123456"),
        ("Mirror user:abc123456@cdn.example.com/a failed", "abc123456"),
        ("Mirror (user:abc123456@cdn.example.com/a) failed", "abc123456"),
    ],
)
def test_credentials_in_other_shapes_are_replaced(text, secret):
    cleaned = failures.reason(failed_job(text))
    assert secret not in cleaned, cleaned
    assert cleaned.startswith(text.split(" ")[0])


def test_names_that_only_contain_a_credential_word_keep_their_value():
    text = "Requested max_tokens: 4096 exceeds the limit; tokenizer: v2"
    assert failures.reason(failed_job(text)) == text


def test_credential_shaped_values_are_replaced():
    bearer = "Bearer " + "abcdefghijklmnop" * 2
    jwt = "eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.c2lnbmF0dXJlX3ZhbHVl"
    text = (
        f"Authorization: {bearer}; api_key=sk_abc123456 apiSecret: 'two words' "
        f"token={jwt} password: hunter2hunter2 sessionId=s3ss10n"
    )
    cleaned = failures.reason(failed_job(text))
    for secret in ("abcdefghijklmnop", "sk_abc123456", "two words", "eyJ", "hunter2", "s3ss10n"):
        assert secret not in cleaned
    assert "api_key=[redacted]" in cleaned and "password: [redacted]" in cleaned
    assert cleaned.count(failures.REDACTED) >= 6


def test_ordinary_words_and_the_support_id_survive_cleaning():
    text = f"Token limit reached for this model. Provide this token: {SUPPORT_ID}"
    assert failures.reason(failed_job(text)) == text


@pytest.mark.parametrize(
    "value",
    [
        "error_abcDEF123",
        '"error_abcDEF123"',
        "'error_abcDEF123'",
        "error_abcDEF123.",
        '"error_abcDEF123").',
    ],
)
def test_a_genuine_support_id_after_a_credential_name_is_kept_as_written(value):
    for name in ("token=", "token: ", "API_KEY="):
        for text in (f"Quote {name}{value}", f"Quote {name}{value}, then retry"):
            assert failures.reason(failed_job(text)) == text


def test_words_after_a_support_id_in_a_credential_clause_are_redacted():
    text = "Quote token=error_abcDEF123 sEcr3tKey99, then retry"
    assert failures.reason(failed_job(text)) == (
        f"Quote token=error_abcDEF123 {failures.REDACTED}, then retry"
    )


# Every leak raised in review so far, and the shapes the conservative design targets:
# (text, secrets that must not appear in the reason).
ADVERSARIAL = [
    # Look-alike support ids after a credential name.
    ("Rejected api_key=ERROR_realSecretToken123 now", ["realSecret"]),
    ("Rejected api_key=Error_realSecretToken123", ["realSecret"]),
    # An id-shaped password in a link's userinfo is not appended back.
    ("See https://user:error_AbcDEF123secret@host.example/path", ["AbcDEF123secret", "error_"]),
    # *_key names.
    ("Signing failed: secret_key=abc123", ["abc123"]),
    ("Signing failed: master_key: abc123", ["abc123"]),
    ("Signing failed: signing_key=abc123", ["abc123"]),
    ("Signing failed: client_key=abc123", ["abc123"]),
    ("Signing failed: session_key=abc123", ["abc123"]),
    ("Signing failed: SecretKey=abc123", ["abc123"]),
    # A whole multi-word value, up to the end of its clause.
    ("Rejected token: Signed sEcr3tKey99", ["sEcr3tKey99", "Signed"]),
    ("Rejected github_token: Signed sEcr3tKey99, retry", ["sEcr3tKey99"]),
    ("Rejected x-api-key = Custom sEcr3tKey99; retry", ["sEcr3tKey99"]),
    ("Rejected auth: Digest sEcr3tKey99", ["sEcr3tKey99"]),
    ("Rejected sig=sEcr3tKey99&next=1", ["sEcr3tKey99"]),
    ("Rejected pwd: hunter2 hunter3", ["hunter2", "hunter3"]),
    ("Rejected cookie: a=1; b=2", ["a=1"]),
    ('Rejected {"credentials": "one two three"}', ["one two three"]),
    ("Rejected password: line one\nnext line kept", ["line one", "one"]),
    # Userinfo glued after any character, with or without a scheme.
    ("Mirror path/user:pAss123@host.example failed", ["pAss123"]),
    ("Mirror x:user:pAss123@host.example failed", ["pAss123"]),
    ("Mirror (x)user:pAss123@host.example failed", ["pAss123"]),
    ("Mirror [x]user:pAss123@host.example failed", ["pAss123"]),
    ("Mirror <x>user:pAss123@host.example failed", ["pAss123"]),
    ("Mirror a@user:pAss123@host.example failed", ["pAss123"]),
    ("Mirror user:pAss123@ host.example failed", ["pAss123"]),
    # Opaque 24+ character tokens that mix letters and digits.
    ("Signed with dGhpcyBpcyBhIHNlY3JldCB2YWx1ZQ== today", ["dGhpcyBpcy"]),
    ("Digest 0123456789abcdef0123456789abcdef01234567 rejected", ["0123456789abcdef"]),
    ("Session aBcDeF123456gHiJkL789012.mNoPqR345678sTuVwX901234.x", ["aBcDeF123456"]),
    ("Upload to /bucket/aBcDeF123456gHiJkL789012/x.png failed", ["aBcDeF123456"]),
]


@pytest.mark.parametrize(("text", "secrets"), ADVERSARIAL)
def test_adversarial_reasons_never_show_a_secret(text, secrets):
    for error, hint in ((text, None), (None, text), ("Rejected", text)):
        cleaned = failures.reason(failed_job(error, hint))
        for secret in secrets:
            assert secret not in cleaned, cleaned
        assert text not in cleaned, cleaned


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("password: line one\nnext line kept", "password: [redacted] next line kept"),
        ("token: abc def, retry later", "token: [redacted], retry later"),
        ("token: abc def; retry", "token: [redacted]; retry"),
        ("(token: abc def) retry", "(token: [redacted]) retry"),
        ('{"apiKey": "a b", "model": "x"}', '{"apiKey": [redacted], "model": "x"}'),
        (
            "api_key=sk1 apiSecret: 'two words' model: x",
            "api_key=[redacted] apiSecret: [redacted] model: x",
        ),
        ("secret: dGVzdA== now", "secret: [redacted]"),
    ],
)
def test_a_credential_value_runs_to_the_end_of_its_clause(text, expected):
    assert failures.reason(failed_job(text)) == expected


# Ordinary text stays readable: the live error, the prototype-era message, sizes,
# dates, links, e-mail addresses and Scenario resource ids.
READABLE = [
    "An internal error occurred. Please contact support and provide this id: " + SUPPORT_ID,
    "The model file is too large for processing. Try reducing the resolution or "
    "simplifying the geometry of your input, then retry the generation. "
    "[Error ID: error_Uq14k1SGmKWhPfv4HZ4hyZRN]",
    "Input image is 8192 x 8192 pixels; the maximum is 4096 x 4096.",
    "Model model_tencent-uv-unwrapping could not read asset asset_4Aufp4GxmMozUQUL36d5C6Jr "
    "for job job_KWxxsnSdVXDFZRMsoCvLTmKY in proj_FIXTURE00000000000000000.",
    "authorId: apiu_FIXTURE0000000000000000 has no access to workflow_aBcDeF123456gHiJkL789012",
    "Requested max_tokens: 4096 exceeds the limit; tokenizer: v2",
    "Keyframe 24 is missing; keyframes: 1-48 were expected.",
    "Retry after 2026-10-13T00:20:58Z; see https://docs.scenario.com/api/python/resources/jobs",
    "Contact support@scenario.com with the id.",
    "Model design: v2 (signal level 3), keyword: fox",
    "Token limit reached for this model; try a shorter prompt.",
]


@pytest.mark.parametrize("text", READABLE)
def test_ordinary_reasons_stay_readable(text):
    assert failures.reason(failed_job(text)) == text


@pytest.mark.parametrize(
    "value",
    [
        "ERROR_realSecretToken123",
        "Error_realSecretToken123",
        "error_realsecrettoken",  # lowercase only: not a support id
        "error_ab1",  # too short
        "error_realSecret-Token123",
        "tok.error_realSecretToken123.x",  # an id-shaped part of a secret is not appended
        '"ERROR_realSecretToken123"',
        "error_" + "A" * 65,  # too long
    ],
)
def test_values_that_only_look_like_a_support_id_are_redacted(value):
    cleaned = failures.reason(failed_job(f"Rejected api_key={value} now"))
    assert cleaned.startswith(f"Rejected api_key={failures.REDACTED}")
    assert "realSecret" not in cleaned and "realsecret" not in cleaned
    assert "AAAAAAAA" not in cleaned


def test_long_reasons_are_bounded_and_keep_the_support_id():
    head = "The provider rejected the request. " * 40
    cleaned = failures.reason(failed_job(head + INTERNAL))
    assert len(cleaned) <= failures.MAX_LENGTH
    assert cleaned.startswith("The provider rejected the request.")
    assert cleaned.endswith(f"… (error id {SUPPORT_ID})")
    # An id already inside the kept text is not repeated.
    early = failures.reason(failed_job(INTERNAL + " " + head))
    assert len(early) <= failures.MAX_LENGTH and early.count(SUPPORT_ID) == 1
    assert early.startswith(INTERNAL) and early.endswith("…")


def test_an_id_only_in_removed_content_is_never_brought_back():
    # The support id comes from the cleaned text alone: a query, userinfo, data
    # URI or credential that cleaning removed never returns as "(error id ...)".
    for text in (
        f"See https://status.example.com/incident?ref={SUPPORT_ID} for details",
        f"See https://user:{SUPPORT_ID}secret@cdn.example.com/a.png for details",
        f"See https://user:{SUPPORT_ID}@cdn.example.com/a.png for details",
        f"See cdn.example.com/a?ref={SUPPORT_ID} for details",
        f"See user:{SUPPORT_ID}@cdn.example.com/a for details",
    ):
        cleaned = failures.reason(failed_job(text + " " + "x" * 500))
        assert "error_" not in cleaned and "error id" not in cleaned, cleaned
        assert failures.reason(failed_job(text)).endswith(" for details"), text


def test_the_live_double_space_before_the_id_reads_as_one():
    text = "An internal error occurred. Please contact support and provide this id:  " + SUPPORT_ID
    assert failures.reason(failed_job(text)) == INTERNAL


@pytest.mark.parametrize("marker", ["[redacted]", "[link removed]", "[data removed]"])
@pytest.mark.parametrize("offset", range(-12, 4))
def test_cutting_never_splits_a_marker_word_or_the_support_id(marker, offset):
    source = {
        "[redacted]": "password: hunter2hunter2",
        "[link removed]": "https://[::1/x",
        "[data removed]": "data:image/png;base64,iVBORw0KGgo=",
    }[marker]
    words = "word " * 200
    text = words[: failures.MAX_LENGTH + offset - len(marker)] + source + " tail " + INTERNAL
    full = failures.clean(text)
    cleaned = failures.reason(failed_job(text))
    assert len(cleaned) <= failures.MAX_LENGTH
    body = cleaned.split("…")[0]
    # The cut ends at a word boundary of the cleaned text, so a marker is whole or absent.
    assert full.startswith(body) and full[len(body)] == " ", body[-30:]
    assert body.count("[") == body.count("]")
    # The id is given once, after the ellipsis.
    assert cleaned.endswith(f"… (error id {SUPPORT_ID})") and cleaned.count(SUPPORT_ID) == 1


def test_a_cut_inside_one_long_word_still_ends_with_an_ellipsis():
    cleaned = failures.reason(failed_job("x" * 1000))
    assert cleaned == "x" * (failures.MAX_LENGTH - 1) + "…"


def test_lowercase_words_after_error_are_not_support_ids():
    assert failures.support_id("error_occurred and error_code") is None
    assert failures.support_id(f"x {SUPPORT_ID} y") == SUPPORT_ID


def test_huge_values_are_bounded_quickly():
    hostile = ("a.b-" * 50_000) + "token=" + ("x" * 50_000) + "\n" * 10_000
    started = time.perf_counter()
    cleaned = failures.reason(failed_job(hostile, hostile))
    assert time.perf_counter() - started < 2
    assert len(cleaned) <= failures.MAX_LENGTH


def test_observe_binds_the_reason_to_the_failed_record_that_produced_it():
    job = failed_job()
    reading = failures.observe(snapshot(job))
    assert reading == failures.RemoteFailure(job["jobId"], 4, INTERNAL)
    assert not hasattr(reading, "response")


@pytest.mark.parametrize(
    ("state", "remote_job_id", "status"),
    [
        (JobState.REMOTE, None, "failure"),
        (JobState.CANCEL_REQUESTED, None, "failure"),
        (JobState.CANCELED, None, "failure"),
        (JobState.FAILED, "job_another", "failure"),
        (JobState.FAILED, None, "canceled"),
    ],
)
def test_observe_ignores_unbound_or_unfailed_snapshots(state, remote_job_id, status):
    job = failed_job(status=status)
    assert failures.observe(snapshot(job, state=state, remote_job_id=remote_job_id)) is None


def test_observe_without_a_reason_is_none():
    assert failures.observe(snapshot(failed_job(error=None))) is None
