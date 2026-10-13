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
        text = f"Quote {name}{value} to support"
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


def test_a_support_id_inside_a_removed_query_is_still_given():
    text = f"See https://status.example.com/incident?ref={SUPPORT_ID} for details"
    assert failures.reason(failed_job(text)) == (
        f"See https://status.example.com/incident for details (error id {SUPPORT_ID})"
    )


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
