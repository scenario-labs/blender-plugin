# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Show Scenario's reason for a failed job only when it is plain text; no Blender or network.

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
# The live error's shape, with its double space before the id, and a live hint.
LIVE_ERROR = (
    "An internal error occurred. Please contact support and provide this id:  " + SUPPORT_ID
)
LIVE_HINT = (
    "The generation took too long to complete. Try retrying with a lower resolution, "
    + "shorter duration, or simpler prompt settings, then submit again."
)
GENERIC = (failures.UNREADABLE, "Rejected. " + failures.NOT_SHOWN)


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


def test_the_live_error_and_hint_are_shown_in_full():
    assert failures.reason(failed_job(LIVE_ERROR)) == INTERNAL
    assert failures.reason(failed_job(None, LIVE_HINT)) == LIVE_HINT
    assert failures.reason(failed_job(LIVE_ERROR, LIVE_HINT)) == f"{INTERNAL}. {LIVE_HINT}"


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
    assert failures.reason(failed_job(text)) == "Model failed: input rejected retry later now"


def test_a_part_that_is_not_plain_text_is_replaced_and_nothing_is_taken_from_it():
    hidden = f"See https://status.example.com/incident?ref={SUPPORT_ID} for details"
    assert failures.reason(failed_job(hidden)) == failures.UNREADABLE
    assert failures.reason(failed_job("Rejected", hidden)) == "Rejected. " + failures.NOT_SHOWN
    assert failures.reason(failed_job(hidden, "Try again later.")) == (
        f"{failures.NOT_SHOWN} Try again later."
    )
    for error, hint in ((hidden, None), ("Rejected", hidden), (hidden, hidden)):
        assert "error_" not in failures.reason(failed_job(error, hint))


# Every leak raised in review so far, the five of the last round, and shapes the
# gate targets: (text, secrets that must not appear in the reason). Each of
# them is not plain text, so it is replaced by a fixed sentence.
ADVERSARIAL = [
    # Look-alike support ids after a credential name.
    ("Rejected api_key=ERROR_realSecretToken123 now", ["realSecret"]),
    ("Rejected api_key=Error_realSecretToken123", ["realSecret"]),
    ("Rejected api_key=error_realsecrettoken now", ["realsecret"]),
    ("Rejected api_key=error_ab1 now", ["error_ab1"]),
    ("Rejected api_key=tok.error_realSecretToken123.x now", ["realSecret"]),
    ('Rejected api_key="ERROR_realSecretToken123" now', ["realSecret"]),
    # Ids that appeared only inside removed content.
    ("See https://user:error_AbcDEF123secret@host.example/path", ["AbcDEF123secret", "error_"]),
    (f"See https://status.example.com/incident?ref={SUPPORT_ID} now", [SUPPORT_ID]),
    (f"See user:{SUPPORT_ID}@cdn.example.com/a for details", [SUPPORT_ID]),
    # Links, queries, fragments and data URIs.
    (
        "Download failed for https://user:pass@cdn.example.com:8443/a/b.png?X-Amz-Signature=abc",  # secrets-allow
        ["user:pass", "Signature", "abc"],
    ),
    ("See cdn.example.com/c?Key-Pair-Id=K&Policy=P", ["Key-Pair-Id"]),  # secrets-allow
    ("Image data:image/png;base64,iVBORw0KGgo= rejected", ["iVBORw0KGgo"]),
    ("Bad host https://[::1/x?token=t here", ["token=t"]),
    # Credential names and values in every earlier shape.
    ("Signing failed: secret_key=abc123", ["abc123"]),
    ("Signing failed: master_key: abc123", ["abc123"]),
    ("Signing failed: signing_key=abc123", ["abc123"]),
    ("Signing failed: client_key=abc123", ["abc123"]),
    ("Signing failed: session_key=abc123", ["abc123"]),
    ("Signing failed: SecretKey=abc123", ["abc123"]),
    ('Rejected {"apiKey": "sk-abc123456"}', ["sk-abc123456"]),
    ("Rejected {'client_secret':'cs-abc123456'}", ["cs-abc123456"]),
    ("Rejected aws_secret_access_key=abc123456 for the bucket", ["abc123456"]),
    ("Rejected X-Goog-Signature=abc123456&X-Goog-Date=1", ["abc123456"]),
    ("Rejected github_token: abc123456", ["abc123456"]),
    ("Rejected Authorization: token abc123456", ["abc123456"]),
    ("Rejected Proxy-Authorization: Digest abc123456", ["abc123456"]),
    ("Rejected note: password=abc123456", ["abc123456"]),
    ("Rejected https://host/p;jsessionid=abc123456", ["abc123456"]),
    ("Rejected Authorization: Bearer abcdefghijklmnop", ["abcdefghijklmnop"]),
    ("Rejected token=eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxMjM0In0.c2lnbmF0dXJl", ["eyJ"]),
    ("Rejected token: Signed sEcr3tKey99", ["sEcr3tKey99", "Signed"]),
    ("Rejected github_token: Signed sEcr3tKey99, retry", ["sEcr3tKey99"]),
    ("Rejected x-api-key = Custom sEcr3tKey99; retry", ["sEcr3tKey99"]),
    ("Rejected auth: Digest sEcr3tKey99", ["sEcr3tKey99"]),
    ("Rejected sig=sEcr3tKey99&next=1", ["sEcr3tKey99"]),
    ("Rejected sig: sEcr3tKey99", ["sEcr3tKey99"]),
    ("Rejected pwd: hunter2 hunter3", ["hunter2", "hunter3"]),
    ("Rejected cookie: a=1; b=2", ["a=1"]),
    ('Rejected {"credentials": "one two three"}', ["one two three"]),
    ("Rejected password: line one\nnext line kept", ["line one"]),
    ("Quote token=error_abcDEF123 sEcr3tKey99, then retry", ["sEcr3tKey99"]),
    # Userinfo glued after any character, with or without a scheme.
    ("Mirror path/user:pAss123@host.example failed", ["pAss123"]),
    ("Mirror x:user:pAss123@host.example failed", ["pAss123"]),
    ("Mirror (x)user:pAss123@host.example failed", ["pAss123"]),
    ("Mirror [x]user:pAss123@host.example failed", ["pAss123"]),
    ("Mirror <x>user:pAss123@host.example failed", ["pAss123"]),
    ("Mirror a@user:pAss123@host.example failed", ["pAss123"]),
    ("Mirror user:pAss123@ host.example failed", ["pAss123"]),
    ("Mirror //user:pAss123@host.example/x failed", ["pAss123"]),
    # Long tokens that mix letters and digits, whole or in segments.
    ("Signed with dGhpcyBpcyBhIHNlY3JldCB2YWx1ZQ== today", ["dGhpcyBpcy"]),
    ("Digest 0123456789abcdef0123456789abcdef01234567 rejected", ["0123456789abcdef"]),
    ("Session aBcDeF123456gHiJkL789012.mNoPqR345678sTuVwX901234.x", ["aBcDeF123456"]),
    ("Upload to /bucket/aBcDeF123456gHiJkL789012/x.png failed", ["aBcDeF123456"]),
    ("Key abcdefghijkl.123456789012.mnopqrstuvwx used", ["abcdefghijkl", "123456789012"]),
    ("Key ABCDEFGHIJKLMNOP/1234567890123456 used", ["ABCDEFGHIJKLMNOP"]),
    ("Request 3f2a9c1e-8b7d-4e6f-a5c3-1d2e3f4a5b6c failed", ["3f2a9c1e"]),
    ("Signed with s3ss10n now", ["s3ss10n"]),
    # Unterminated and escaped quotes in a credential value.
    ('Rejected token: "secret value never closed', ["secret value", "never closed"]),
    ("Rejected password: 'hunter2 hunter3", ["hunter2", "hunter3"]),  # secrets-allow
    ('Rejected token: "abc\\"def secret" retry', ["def", "secret"]),
    ("Rejected secret='abc\\'xyz secret' retry", ["xyz"]),
    ('Rejected token: "line one\\\nline two', ["line one"]),
    # A secret glued to a resource-id prefix, or longer than any resource id.
    ("Glued job_KWxxsnSdVXDFZRMsoCvLTmKYsEcr3tKey99abc here", ["sEcr3tKey99"]),
    ("Glued asset_a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6 here", ["a1b2c3d4e5f6a1b2"]),
    ("Glued model_abcdef0123456789abcdef0123456789abcd here", ["abcdef0123456789"]),
    ("Glued model_a-abcdef0123456789abcdef0123456789 here", ["abcdef0123456789"]),
    # The five of the last review round.
    ('Rejected "\\' + "!\\" * 40, ["!\\!\\"]),
    ("Rejected '\\" + "&\\" * 40, ["&\\&\\"]),
    ("Fetch https://host.example/data/user:pAss123@file failed", ["pAss123"]),
    ("Key ab12cde.fg34hij.kl56mno.pq78rst used", ["ab12cde", "pq78rst"]),
    ("Copy //cdn.internal/old/user:S3cr3tPass99@ backup.internal", ["S3cr3tPass99"]),
]


@pytest.mark.parametrize(("text", "secrets"), ADVERSARIAL)
def test_adversarial_reasons_show_only_a_fixed_sentence(text, secrets):
    for error, hint in ((text, None), (None, text), ("Rejected", text), (text, text)):
        shown = failures.reason(failed_job(error, hint))
        assert shown in GENERIC, shown
        for secret in secrets:
            assert secret not in shown, shown


# Ordinary text stays readable: sizes, dates, percentages, model names, links
# between two words, e-mail-free prose and Scenario resource ids.
READABLE = [
    INTERNAL,
    LIVE_HINT,
    "Input image is 8192 x 8192 pixels; the maximum is 4096 x 4096.",
    "Upscale to 4096x4096 is not supported for GPT Image 2; use 2048x2048 or less.",
    "Seedance 2.5 accepts videos of 5 to 10 seconds at 720p or 1080p.",
    "The generation used 95% of its time budget on 2026-10-13 at 00:20:58.",
    (
        "Model model_tencent-uv-unwrapping could not read asset asset_4Aufp4GxmMozUQUL36d5C6Jr "
        + "for job job_KWxxsnSdVXDFZRMsoCvLTmKY in proj_FIXTURE00000000000000000."
    ),
    "Model model_hunyuan-world-image-to-skybox is unavailable (workflow_aBcDeF123456gHiJkL789012).",
    "Retry after 5 minutes (rate limit: 10 requests per minute).",
    "The input/output ratio is too high; keyframes 1-48 were expected.",
    "Internationalization of text-to-video prompts isn't supported yet!",
    "La génération a échoué : réessayez avec une résolution plus basse.",
    'The prompt "a red fox" was rejected by the content filter.',
    "Rendering at x86_64 speed reached 3.5 fps on the H3 model.",
]


@pytest.mark.parametrize("text", READABLE)
def test_ordinary_reasons_stay_readable(text):
    assert failures.reason(failed_job(text)) == text
    assert failures.reason(failed_job(None, text)) == text


@pytest.mark.parametrize(
    ("token", "showable"),
    [
        ("and/or", True),
        ("input/output", True),
        ("a/b/c", False),
        ("/path", False),
        ("averyveryverylongword/b", False),
        ("Internationalization", True),
        ("text-to-video", True),
        ("abcdefghijklmnopqrstuvwxyzabcdef", False),  # letters, 32 or more
        ("4096x4096", True),
        ("a1b2", False),
        ("model_patina-material", True),
        ("model_" + "x" * 30, False),
        ("keyframe", True),
        ("monkey", False),
        ("sig", False),
        ("design", True),
        (SUPPORT_ID, True),
        ("error_occurred", False),
    ],
)
def test_token_rules(token, showable):
    shown = failures.reason(failed_job(f"Check {token} now"))
    assert (shown == f"Check {token} now") is showable, shown


def test_long_reasons_are_bounded_and_keep_the_support_id():
    head = "The provider rejected the request. " * 40
    shown = failures.reason(failed_job(head + INTERNAL))
    assert len(shown) <= failures.MAX_LENGTH
    assert shown.startswith("The provider rejected the request.")
    assert shown.endswith(f"… (error id {SUPPORT_ID})")
    # An id already inside the kept text is not repeated.
    early = failures.reason(failed_job(INTERNAL + " " + head))
    assert len(early) <= failures.MAX_LENGTH and early.count(SUPPORT_ID) == 1
    assert early.startswith(INTERNAL) and early.endswith("…")


@pytest.mark.parametrize("offset", range(-12, 4))
def test_cutting_never_splits_a_word_or_the_support_id(offset):
    words = "word " * 200
    text = words[: failures.MAX_LENGTH + offset].rstrip() + " " + SUPPORT_ID + " tail " + INTERNAL
    full = " ".join(text.split())
    shown = failures.reason(failed_job(text))
    assert len(shown) <= failures.MAX_LENGTH
    body = shown.split("…")[0]
    assert full.startswith(body) and full[len(body)] == " ", body[-30:]
    assert shown.count(SUPPORT_ID) == 1


def test_lowercase_words_after_error_are_not_support_ids():
    assert failures.support_id("error_occurred and error_code") is None
    assert failures.support_id(f"x {SUPPORT_ID}. y") == SUPPORT_ID
    assert failures.support_id(None) is None


@pytest.mark.parametrize(
    "hostile",
    [
        '"\\' + "!\\" * 50_000,
        "'\\" + "&\\" * 50_000,
        "a:" * 50_000 + "@",
        "a.b-" * 50_000 + "token=" + "x" * 50_000,
        "x " * 100_000,
        "é" * 100_000,
    ],
)
def test_pathological_inputs_finish_in_linear_time(hostile):
    started = time.perf_counter()
    shown = failures.reason(failed_job(hostile, hostile))
    assert time.perf_counter() - started < 0.5
    assert len(shown) <= failures.MAX_LENGTH


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
