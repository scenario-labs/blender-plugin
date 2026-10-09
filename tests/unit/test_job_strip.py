# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Status wording, progress and chip choice of the compact composer's job strip."""

import typing
from dataclasses import dataclass

import pytest
from scenario_sdk.types.job_retrieve_response import Job

from scenario.core.jobs.store import JobState
from scenario.core.ui import job_strip as js


@dataclass(frozen=True)
class Action:
    """The fields of a saved-job action descriptor that the strip reads."""

    key: str
    action: str
    group: str
    label: str
    operator: str | None = "scenario.recover_job"


REFRESH = Action("refresh", "refresh", "recover", "Refresh status")
RESUME = Action("resume", "resume", "recover", "Resume download")
RECOVER_DOWNLOAD = Action(
    "recover_download", "recover_download", "recover", "Check interrupted download"
)
CANCEL = Action("cancel", "cancel", "cancel", "Cancel generation")
CANCEL_PREPARED = Action("cancel_prepared", "cancel_prepared", "cancel", "Cancel prepared job")
RECEIPT = Action("retry_receipt", "retry_receipt", "receipt", "Save import receipt")
READ_BLOCKOUT = Action(
    "recover_blockout", "recover_blockout", "recover", "Read saved Blockout plan"
)
IMAGES = Action(
    "import_images", "import_images", "apply", "Import saved images", "scenario.import_saved_images"
)
MATERIAL = Action(
    "apply_material",
    "apply_material",
    "apply",
    "Apply saved material",
    "scenario.apply_saved_material",
)
MODEL_1 = Action(
    "import_model:a1", "import_model", "apply", "Import model (1)", "scenario.import_saved_model"
)
MODEL_2 = Action(
    "import_model:a2", "import_model", "apply", "Import model (2)", "scenario.import_saved_model"
)
WORLD = Action(
    "apply_world:a1",
    "apply_world",
    "apply",
    "Set panorama as World (1)",
    "scenario.apply_saved_world",
)
RESTORE_WORLD = Action(
    "restore_world",
    "restore_world",
    "apply",
    "Restore previous World",
    "scenario.apply_saved_world",
)
REUSE_ROW = Action("reuse", "", "status", "Reuse saved results", None)
REVIEW_ROW = Action(
    "awaiting_review", "", "status", "Downloaded result awaits application review", None
)
INSPECT = js.StripChip("inspect", "Inspect")


def test_remote_vocabulary_is_the_pinned_sdk_job_status():
    sdk = typing.get_args(Job.model_fields["status"].annotation)
    assert set(js.REMOTE_STATUSES) == set(sdk) and len(js.REMOTE_STATUSES) == len(sdk)
    assert not set(js.ACTIVE_REMOTE_STATUSES) & set(js.TERMINAL_REMOTE_STATUSES)
    assert js.known_remote_status("warming-up") == "warming-up"
    for value in (None, "running", "In-Progress", 3):
        assert js.known_remote_status(value) is None


TABLE = [
    ("prepared", {}, "Preparing submission", "active", None),
    ("submitting", {"in_flight": True}, "Submitting...", "active", None),
    ("submitting", {}, "Submission unconfirmed; do not resubmit", "review", None),
    ("uncertain", {}, "Submission unconfirmed; do not resubmit", "review", None),
    ("remote", {}, "Submitted", "active", None),
    ("remote", {"remote_status": "pending"}, "Queued", "active", None),
    ("remote", {"remote_status": "queued"}, "Queued", "active", None),
    ("remote", {"remote_status": "warming-up"}, "Starting", "active", None),
    ("remote", {"remote_status": "in-progress"}, "Generating", "active", None),
    (
        "remote",
        {"remote_status": "in-progress", "progress": 0.42},
        "Generating 42%",
        "active",
        0.42,
    ),
    ("remote", {"remote_status": "in-progress", "progress": 1}, "Generating", "active", None),
    ("remote", {"remote_status": "finalizing", "progress": 0.99}, "Finalizing", "active", None),
    ("remote", {"remote_status": "queued", "progress": 0.5}, "Queued", "active", None),
    ("remote", {"remote_status": "success"}, "Submitted", "active", None),
    ("remote", {"remote_status": "running"}, "Submitted", "active", None),
    (
        "cancel_requested",
        {"remote_status": "in-progress", "progress": 0.5},
        "Cancelling...",
        "active",
        None,
    ),
    ("succeeded", {}, "Downloading results", "active", None),
    ("downloading", {}, "Downloading results", "active", None),
    ("download_failed", {}, "Download failed", "review", None),
    ("ready", {}, "Ready to apply", "ready", None),
    ("ready", {"automatic": True}, "Importing...", "active", None),
    ("applying", {}, "Applying...", "active", None),
    ("apply_failed", {}, "Application needs review", "review", None),
    ("applied", {}, "Applied", "done", None),
    ("applied", {"automatic": True}, "Applied", "done", None),
    ("failed", {}, "Generation failed", "error", None),
    ("canceled", {}, "Canceled", "done", None),
    (None, {}, "Checking status", "active", None),
    ("not-a-state", {}, "Checking status", "active", None),
]


@pytest.mark.parametrize(("state", "kwargs", "text", "tone", "fraction"), TABLE)
def test_status_wording_tone_and_fraction(state, kwargs, text, tone, fraction):
    status = js.strip_status(state, **kwargs)
    assert status == js.StripStatus(text, tone, fraction)
    assert status.tone in js.TONES
    assert status.indeterminate == (tone == "active" and fraction is None)


def test_every_saved_job_state_has_its_own_wording():
    unknown = js.strip_status(None)
    for state in JobState:
        assert js.strip_status(state.value) != unknown, state
        assert js.strip_status(state.value, in_flight=True) != unknown, state


def test_a_submitting_record_without_a_live_send_reads_unconfirmed():
    # The uncertain transition runs only when the send raises; a failed write or a
    # quit mid-send leaves the record submitting with no task behind it.
    stalled = js.strip_status("submitting", in_flight=False)
    assert stalled == js.strip_status("uncertain") and not stalled.indeterminate
    sending = js.strip_status("submitting", in_flight=True)
    assert sending == js.StripStatus("Submitting...", "active") and sending.indeterminate
    for state in ("prepared", "uncertain", "remote", "ready", "applied"):
        assert js.strip_status(state, in_flight=True) == js.strip_status(state)


@pytest.mark.parametrize(
    "value", [None, True, False, "0.5", [0.5], float("nan"), float("inf"), -0.01, 1.01]
)
def test_unknown_progress_is_indeterminate_never_zero(value):
    assert js.known_progress(value) is None and js.progress_percent(value) is None
    status = js.strip_status("remote", remote_status="in-progress", progress=value)
    assert status == js.StripStatus("Generating", "active") and status.indeterminate


def test_percent_appears_only_from_one_to_ninety_nine():
    assert js.known_progress(0) == 0.0 and js.progress_percent(0) is None
    assert js.progress_percent(0.004) is None
    assert js.progress_percent(0.01) == 1
    assert js.progress_percent(0.29) == 29  # not floored to 28 by binary rounding
    assert js.progress_percent(0.999) == 99
    assert js.progress_percent(0.999999999995) == 99  # the epsilon never reaches 100
    assert js.known_progress(1.0) == 1.0 and js.progress_percent(1.0) is None
    started = js.strip_status("remote", remote_status="in-progress", progress=0.004)
    assert started == js.StripStatus("Generating", "active")
    almost = js.strip_status("remote", remote_status="in-progress", progress=0.999999999995)
    assert almost == js.StripStatus("Generating 99%", "active", 0.999999999995)
    # still in progress at 1: completion is a later status, so no 100% beside an active bar
    done = js.strip_status("remote", remote_status="in-progress", progress=1.0)
    assert done == js.StripStatus("Generating", "active") and done.indeterminate


@pytest.mark.parametrize(
    "state", ["remote", "cancel_requested", "succeeded", "downloading", "download_failed"]
)
def test_offline_states_waiting_on_the_network_say_so(state):
    assert js.strip_status(state, online=False).text == js.strip_status(state).text + " (offline)"


@pytest.mark.parametrize(
    "state",
    [
        "prepared",
        "submitting",
        "uncertain",
        "ready",
        "applying",
        "apply_failed",
        "applied",
        "failed",
        "canceled",
    ],
)
def test_local_states_ignore_offline_and_stale(state):
    assert js.strip_status(state, online=False, stale=True) == js.strip_status(state)


def test_stale_observations_read_as_last_known_and_offline_wins():
    stale = js.strip_status("remote", remote_status="in-progress", progress=0.42, stale=True)
    assert stale == js.StripStatus("Generating 42% (last known)", "active", 0.42)
    assert js.strip_status("cancel_requested", stale=True).text == "Cancelling... (last known)"
    assert js.strip_status("downloading", stale=True).text == "Downloading results"
    offline = js.strip_status(
        "remote", remote_status="in-progress", progress=0.42, online=False, stale=True
    )
    assert offline == js.StripStatus("Generating 42% (offline)", "active", 0.42)


@pytest.mark.parametrize(
    "state",
    [
        "prepared",
        "remote",
        "cancel_requested",
        "succeeded",
        "downloading",
        "download_failed",
        "ready",
        "applying",
        "apply_failed",
        "applied",
        None,
    ],
)
def test_a_paused_error_replaces_the_wording_for_review(state):
    status = js.strip_status(
        state,
        error="  Result delivery stopped; review the saved job before retrying\n",
        remote_status="in-progress",
        progress=0.5,
        automatic=True,
        online=False,
    )
    assert status == js.StripStatus(
        "Result delivery stopped; review the saved job before retrying", "review"
    )


@pytest.mark.parametrize("state", ["submitting", "uncertain", "failed", "canceled"])
@pytest.mark.parametrize("in_flight", [False, True])
def test_states_with_their_own_wording_keep_it_over_an_error(state, in_flight):
    note = "Submission outcome is not confirmed; do not submit it again"
    assert js.strip_status(state, error=note, in_flight=in_flight) == js.strip_status(
        state, in_flight=in_flight
    )


def test_blank_or_non_text_errors_are_ignored():
    for error in ("", "   ", None, 0):
        assert js.strip_status("ready", error=error) == js.StripStatus("Ready to apply", "ready")


@pytest.mark.parametrize(
    ("state", "actions", "primary"),
    [
        ("remote", (REFRESH, RESUME, CANCEL), CANCEL),
        ("cancel_requested", (REFRESH, RESUME), None),
        ("prepared", (CANCEL_PREPARED,), CANCEL_PREPARED),
        ("succeeded", (RESUME,), RESUME),
        ("downloading", (RECOVER_DOWNLOAD,), RECOVER_DOWNLOAD),
        ("download_failed", (RESUME,), RESUME),
        ("applied", (CANCEL, RECEIPT), RECEIPT),
        ("ready", (IMAGES, REVIEW_ROW), IMAGES),
        ("ready", (READ_BLOCKOUT,), None),
        ("failed", (), None),
        ("canceled", (), None),
        ("ready", (REVIEW_ROW,), None),
    ],
)
def test_primary_chip_priority(state, actions, primary):
    chips = js.strip_chips(actions, state)
    expected = (
        (INSPECT,) if primary is None else (js.StripChip(primary.key, primary.label), INSPECT)
    )
    assert chips == expected


def test_refresh_is_never_primary_because_the_pump_polls():
    for state in ("remote", "cancel_requested", "succeeded", "download_failed", "ready"):
        assert js.strip_chips((REFRESH,), state) == (INSPECT,)


@pytest.mark.parametrize("state", ["submitting", "uncertain"])
def test_an_unconfirmed_submission_offers_only_inspect(state):
    assert js.strip_chips((RECEIPT, CANCEL, RESUME, IMAGES, MODEL_1), state) == (INSPECT,)


def test_one_apply_action_is_named_without_its_asset_number():
    assert js.strip_chips((MODEL_1,), "ready") == (
        js.StripChip("import_model:a1", "Import model"),
        INSPECT,
    )
    # numbering counts every saved asset, so the only model can be the second one
    assert js.strip_chips((MODEL_2, REVIEW_ROW), "apply_failed") == (
        js.StripChip("import_model:a2", "Import model"),
        INSPECT,
    )
    assert js.strip_chips((MATERIAL,), "ready")[0].label == "Apply saved material"


def test_several_apply_actions_offer_one_choice():
    ready = js.strip_chips((MODEL_1, MODEL_2, MATERIAL, REVIEW_ROW), "ready")
    assert ready == (js.StripChip("choose", "Apply... (3)"), INSPECT)
    applied = js.strip_chips((REUSE_ROW, IMAGES, MATERIAL), "applied")
    assert applied == (js.StripChip("choose", "Reuse... (2)"), INSPECT)


def test_restoring_the_world_is_not_counted_as_reuse():
    panorama = js.strip_chips((REUSE_ROW, IMAGES, WORLD, RESTORE_WORLD), "applied")
    assert panorama == (js.StripChip("choose", "Reuse... (2)"), INSPECT)
    one = js.strip_chips((REUSE_ROW, WORLD, RESTORE_WORLD), "applied")
    assert one == (js.StripChip("choose", "Reuse... (1)"), INSPECT)
    alone = js.strip_chips((RESTORE_WORLD,), "applied")
    assert alone == (js.StripChip("restore_world", "Restore previous World"), INSPECT)


def test_an_automatic_import_offers_only_inspect_until_it_pauses():
    actions = (IMAGES, WORLD, REVIEW_ROW)
    assert js.strip_status("ready", automatic=True).text == "Importing..."
    assert js.strip_chips(actions, "ready", automatic=True) == (INSPECT,)
    assert js.strip_chips(actions, "ready", automatic=True, error="  ") == (INSPECT,)
    paused = "Image import needs receipt recovery; do not import again"
    assert js.strip_chips(actions, "ready", automatic=True, error=paused) == js.strip_chips(
        actions, "ready"
    )
    assert js.strip_chips(actions, "ready")[0].key == "choose"
    for state in ("applied", "apply_failed"):
        assert js.strip_chips(actions, state, automatic=True) == js.strip_chips(actions, state)


def test_only_claim_backed_descriptors_with_an_operator_become_chips():
    rowless = Action("import_images", "import_images", "apply", "Import saved images", None)
    other = Action("legacy", "legacy", "legacy", "Add as plane", "scenario.add_plane")
    assert js.strip_chips((rowless, other, REUSE_ROW), "ready") == (INSPECT,)


def test_signature_follows_the_request_revision_and_visible_chips():
    chips = js.strip_chips((CANCEL,), "remote")
    signature = js.strip_signature("request-1", 4, chips)
    assert signature == js.strip_signature(
        "request-1", 4, js.strip_chips((REFRESH, RESUME, CANCEL), "remote")
    )
    assert signature != js.strip_signature("request-2", 4, chips)
    assert signature != js.strip_signature("request-1", 5, chips)
    assert signature != js.strip_signature("request-1", 4, (INSPECT,))
    relabeled = (js.StripChip("cancel", "Cancel prepared job"), INSPECT)
    assert signature != js.strip_signature("request-1", 4, relabeled)
    assert hash(signature) == hash(js.strip_signature("request-1", 4, chips))


def test_strip_line_joins_the_parts_that_are_present():
    line = js.strip_line("A red fox", "Generating 42%", "1.5 CU", 2)
    assert line == "A red fox · Generating 42% · 1.5 CU · +2 more"
    assert js.strip_line("A red fox", "Queued") == "A red fox · Queued"
    assert js.strip_line("", "Applied", "", 0) == "Applied"
