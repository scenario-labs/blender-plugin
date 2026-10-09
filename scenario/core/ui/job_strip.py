# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Status model of the compact composer's job strip. No bpy.

The strip summarizes one shared saved job for the scene and lane the composer
shows: a status line, a tone and, while the service reports it, a determinate
progress fraction. It also picks which saved-job actions appear as chips.
It owns no job, approval or worker and grants nothing. A chip only names a
saved-job action descriptor; that descriptor's operator rechecks the context,
saved revision and destination and opens its own confirmation or review.

Remote statuses and progress use the vocabulary of the pinned Scenario Python
SDK 2.2.0 job retrieval (`Job.status`, and `Job.progress` between 0 and 1).
The saved local state stays authoritative: a remote observation only refines
the wording of a job that is still remote.
"""

import math
import re
from dataclasses import dataclass

from .composer_layout import INSPECT_CHIP

ACTIVE_REMOTE_STATUSES = ("pending", "queued", "warming-up", "in-progress", "finalizing")
TERMINAL_REMOTE_STATUSES = ("success", "failure", "canceled")
REMOTE_STATUSES = ACTIVE_REMOTE_STATUSES + TERMINAL_REMOTE_STATUSES
TONES = ("active", "ready", "done", "review", "error")
INSPECT_LABEL = "Inspect"
CHOOSE_CHIP = "choose"  # several result actions: the chip opens the job card to pick one

_REMOTE_TEXT = {
    "pending": "Queued",
    "queued": "Queued",
    "warming-up": "Starting",
    "in-progress": "Generating",
    "finalizing": "Finalizing",
}
_STATE_TEXT = {
    "prepared": ("Preparing submission", "active"),
    "submitting": ("Submitting...", "active"),
    "uncertain": ("Submission unconfirmed; do not resubmit", "review"),
    "remote": ("Submitted", "active"),
    "cancel_requested": ("Cancelling...", "active"),
    "succeeded": ("Downloading results", "active"),
    "downloading": ("Downloading results", "active"),
    "download_failed": ("Download failed", "review"),
    "ready": ("Ready to apply", "ready"),
    "applying": ("Applying...", "active"),
    "apply_failed": ("Application needs review", "review"),
    "applied": ("Applied", "done"),
    "failed": ("Generation failed", "error"),
    "canceled": ("Canceled", "done"),
}
# A projection error replaces the state wording, except where that wording
# already says more. The projection notes an unconfirmed outcome on every
# submitting or uncertain record, so both keep their own wording; terminal
# failure or cancellation keeps its own tone. Inspect shows the full error.
_OWN_WORDING = frozenset({"submitting", "uncertain", "failed", "canceled"})
_REMOTE_STATES = frozenset({"remote", "cancel_requested"})
_NETWORK_STATES = _REMOTE_STATES | {"succeeded", "downloading", "download_failed"}
_INSPECT_ONLY = frozenset({"submitting", "uncertain"})
_DOWNLOAD_STATES = frozenset({"succeeded", "downloading", "download_failed"})
_DOWNLOAD_RECOVERY = frozenset({"resume", "recover_download"})
_CHIP_GROUPS = frozenset({"receipt", "cancel", "recover", "apply"})
# An apply-group action that does not reuse the job's results: it puts back
# the World a panorama replaced, so it is neither counted nor named as reuse.
_NOT_REUSE = frozenset({"restore_world"})
_NUMBER = re.compile(r" \(\d+\)$")


@dataclass(frozen=True)
class StripStatus:
    """What the strip says about a job.

    The text always states the status, so the tone colour is never the only
    signal. `fraction` fills a determinate bar only while an in-progress job
    reports from 1% to under 100%, as its text does; any other active status
    draws an indeterminate bar.
    """

    text: str
    tone: str
    fraction: float | None = None

    @property
    def indeterminate(self):
        return self.tone == "active" and self.fraction is None


@dataclass(frozen=True)
class StripChip:
    key: str
    label: str


def known_remote_status(value):
    """A job status from the SDK vocabulary, else None."""
    return value if isinstance(value, str) and value in REMOTE_STATUSES else None


def known_progress(value):
    """Remote progress in [0, 1], or None when it is unknown.

    A missing, boolean, non-numeric, non-finite or out-of-range value is
    unknown, never 0: some providers report no progress at all.
    """
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    # Compare before converting: float() raises OverflowError for an integer
    # too large for a float, such as a long literal in a decoded response.
    # The comparison is also false for NaN and both infinities.
    if not 0 <= value <= 1:
        return None
    return float(value)


def progress_percent(value):
    """The whole percent reached, from 1 to 99; otherwise None (indeterminate).

    Below 1% the bar would look stuck. A job still in progress at 1 has not
    finished: completion is a later status (finalizing, then success), so it
    reads as plain progress rather than 100% beside an active bar.
    """
    value = known_progress(value)
    if value is None or value >= 1.0:
        return None
    # The epsilon keeps binary fractions such as 0.29 from flooring to 28; the
    # cap keeps a value just under 1 from reaching 100 through that epsilon.
    percent = min(math.floor(value * 100 + 1e-9), 99)
    return percent if percent >= 1 else None


def _message(error):
    return error.strip() if isinstance(error, str) else ""


def strip_status(
    saved_state,
    *,
    remote_status=None,
    progress=None,
    error=None,
    automatic=False,
    in_flight=False,
    online=True,
    stale=False,
):
    """Status line, tone and progress fraction for one saved job view.

    `saved_state` is the stored job state. `remote_status` and `progress`
    refine a remote job only; `stale` marks an observation older than the
    scheduled poll allows. `automatic` is true when a ready result imports
    without further review. Without online access, states waiting on the
    network say so instead of looking current.

    `in_flight` is true only while this session still holds the submission
    task for the request; the caller reads it from the job owner's live
    submissions (`request_id in ModelJobs.submissions`). A submitting record
    without one did not save its outcome, for example when the uncertain
    transition could not be stored or Blender quit mid-send, so it reads as
    unconfirmed instead of as a send in progress.
    """
    state = saved_state if saved_state in _STATE_TEXT else None
    if state == "submitting" and not in_flight:
        state = "uncertain"
    message = _message(error)
    if message and state not in _OWN_WORDING:
        return StripStatus(message, "review")
    if state is None:
        return StripStatus("Checking status", "active")
    text, tone = _STATE_TEXT[state]
    fraction = None
    if state == "ready" and automatic:
        text, tone = "Importing...", "active"
    elif state == "remote":
        status = known_remote_status(remote_status)
        text = _REMOTE_TEXT.get(status, text)
        percent = progress_percent(progress) if status == "in-progress" else None
        if percent is not None:
            text, fraction = f"{text} {percent}%", known_progress(progress)
    if not online and state in _NETWORK_STATES:
        text += " (offline)"
    elif stale and state in _REMOTE_STATES:
        text += " (last known)"
    return StripStatus(text, tone, fraction)


def strip_chips(actions, saved_state, *, automatic=False, error=None):
    """Chips for one job view, left to right: at most one primary action, then Inspect.

    `actions` are the view's saved-job action descriptors (key, action, group,
    label, operator), in drawing order. Only descriptors with an operator in a
    claim-backed group can become a chip; status rows never do. A submission
    in flight or unconfirmed offers only Inspect. So does a ready result that
    imports automatically (`automatic`, as for strip_status) without a paused
    `error`: it reads "Importing...", and its saved actions can still be listed
    for a poll before that import is under way. The primary chip is, in order:
    a receipt retry, a cancellation, download recovery while results are not
    local, the single apply action (without its asset number), or a choice
    between several, counting only the actions that reuse an applied job.
    """
    inspect = StripChip(INSPECT_CHIP, INSPECT_LABEL)
    if saved_state in _INSPECT_ONLY:
        return (inspect,)
    if saved_state == "ready" and automatic and not _message(error):
        return (inspect,)
    controls = [item for item in actions if item.operator and item.group in _CHIP_GROUPS]
    primary = _primary(controls, saved_state)
    return (inspect,) if primary is None else (primary, inspect)


def _primary(controls, saved_state):
    for group in ("receipt", "cancel"):
        for item in controls:
            if item.group == group:
                return StripChip(item.key, item.label)
    if saved_state in _DOWNLOAD_STATES:
        for item in controls:
            if item.action in _DOWNLOAD_RECOVERY:
                return StripChip(item.key, item.label)
    apply = [item for item in controls if item.group == "apply"]
    if len(apply) == 1:
        return StripChip(apply[0].key, _NUMBER.sub("", apply[0].label))
    if apply:
        reuse = [item for item in apply if item.action not in _NOT_REUSE]
        if saved_state == "applied" and reuse:
            return StripChip(CHOOSE_CHIP, f"Reuse... ({len(reuse)})")
        return StripChip(CHOOSE_CHIP, f"Apply... ({len(apply)})")
    return None


def strip_signature(request_id, revision, chips):
    """What a click on the strip acted on: compare the drawn and current values before dispatch."""
    return (request_id, revision, tuple((chip.key, chip.label) for chip in chips))


def strip_line(title, status, price="", more=0):
    """One line: title, status, display price and the count of other jobs for this lane."""
    parts = [part for part in (title, status, price) if part]
    if more > 0:
        parts.append(f"+{more} more")
    return " · ".join(parts)
