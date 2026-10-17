# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Candidate cloud jobs for an unconfirmed submission, and the checks a link must pass.

No bpy, network or storage. Scenario documents no idempotency key or client
reference for paid submissions (SDK gap:
https://github.com/scenario-labs/scenario-sdk-python-staging/issues/11), so a
listing of similar jobs is never proof of which request created one. These
helpers only list candidates for a person to choose from; the coordinator
verifies the chosen job with a fresh retrieval before saving the link. Once the
service offers an idempotency key or client reference, an exact lookup should
replace this candidate list.
"""

from dataclasses import dataclass
from datetime import timedelta

from ..history import job_cost
from .store import JobState, StoredJob, parse_time

# Job types each saved operation produces, as `jobs.list` filters them.
JOB_TYPES = {
    "model": ("custom", "inference"),
    "workflow": ("workflow",),
    "prompt": ("generate-prompt", "image-prompt-editing"),
    "translate": ("translate",),
}
STATUSES = frozenset(
    {
        "pending",
        "queued",
        "warming-up",
        "in-progress",
        "finalizing",
        "success",
        "failure",
        "canceled",
    }
)
# A display window around a known claim time, wide enough for clock skew and a
# slow first response. It narrows the list; it is never correlation.
BEFORE_CLAIM = timedelta(minutes=10)
AFTER_CLAIM = timedelta(hours=1)
CANDIDATE_LIMIT = 20
PROMPT_EXCERPT = 120


class LinkRefused(ValueError):
    """The selected job cannot belong to this request; nothing was saved."""


@dataclass(frozen=True)
class CloudCandidate:
    """One listed cloud job a person may link; display data, never authority."""

    job_id: str
    job_type: str
    status: str
    created_at: str
    # Seconds from the saved claim to Scenario's creation time, when both are known.
    seconds_after_claim: float | None = None
    prompt: str = ""
    cost: str | None = None


@dataclass(frozen=True)
class CandidateLookup:
    """Candidates for one unconfirmed record at its listed revision.

    `complete` is false when the bounded listing stopped before the end of the
    service's history window, so an older job may be missing.
    """

    record: StoredJob
    candidates: tuple[CloudCandidate, ...]
    complete: bool


def query(record):
    """`recent_jobs` filters for the record's operation, or None when it has none."""
    intent = record.intent
    if intent.operation == "workflow":
        # The run and its steps share the workflow filter; only the run matches below.
        return {"workflow_id": intent.target_id}
    types = JOB_TYPES.get(intent.operation)
    return None if types is None else {"job_types": types}


def _workflow_ids(metadata):
    inputs = metadata.get("input")
    return [
        value
        for value in (
            metadata.get("workflowId"),
            inputs.get("workflowId") if isinstance(inputs, dict) else None,
        )
        if value is not None
    ]


def refusal(record, job):
    """Why this job cannot be the record's submission, or None when it may be."""
    intent = record.intent
    if not isinstance(job, dict) or not isinstance(job.get("jobId"), str):
        return "Scenario returned an unreadable job"
    if job.get("jobType") not in JOB_TYPES.get(intent.operation, ()):
        return "This cloud job is a different kind of generation"
    if job.get("status") not in STATUSES:
        return "Scenario returned an unrecognized job state"
    metadata = job.get("metadata")
    if not isinstance(metadata, dict):
        return "Scenario returned unreadable job metadata"
    if intent.operation == "model":
        inputs = metadata.get("input")
        if not isinstance(inputs, dict) or inputs.get("modelId") != intent.target_id:
            return "This cloud job used another model"
    elif intent.operation == "workflow":
        identities = _workflow_ids(metadata)
        if (
            not identities
            or any(value != intent.target_id for value in identities)
            or metadata.get("workflowJobId") is not None
        ):
            return "This cloud job is not a run of this workflow"
    owner = job.get("ownerId")
    project = intent.scope.project_id
    if project is not None and owner is not None and owner != project:
        return "This cloud job belongs to another project"
    claimed = parse_time(record.claimed_at)
    created = parse_time(job.get("createdAt"))
    if claimed is not None and created is not None and created < claimed - BEFORE_CLAIM:
        return "Scenario created this job before the request was sent"
    return None


def _excerpt(job):
    inputs = (job.get("metadata") or {}).get("input")
    prompt = inputs.get("prompt") if isinstance(inputs, dict) else None
    if not isinstance(prompt, str):
        return ""
    text = " ".join(prompt.split())
    return text if len(text) <= PROMPT_EXCERPT else text[: PROMPT_EXCERPT - 3] + "..."


def _cost(job):
    try:
        cost = job_cost(job)
    except (AttributeError, TypeError, ValueError):
        return None
    return None if cost is None else str(cost)


def lookup(record, rows, *, saved, complete):
    """Order matching, unsaved rows as candidates for `record`; never pick one."""
    if record.state not in {JobState.SUBMITTING, JobState.UNCERTAIN}:
        raise ValueError("Only an unconfirmed submission has cloud candidates")
    claimed = parse_time(record.claimed_at)
    found = []
    for row in rows:
        if refusal(record, row) is not None or row["jobId"] in saved:
            continue
        created = parse_time(row.get("createdAt"))
        delta = None
        if claimed is not None and created is not None:
            if not claimed - BEFORE_CLAIM <= created <= claimed + AFTER_CLAIM:
                continue
            delta = (created - claimed).total_seconds()
        found.append(
            (
                created,
                CloudCandidate(
                    row["jobId"],
                    row["jobType"],
                    row["status"],
                    row.get("createdAt") if isinstance(row.get("createdAt"), str) else "",
                    delta,
                    _excerpt(row),
                    _cost(row),
                ),
            )
        )
    if claimed is not None:
        found.sort(
            key=lambda item: (
                item[1].seconds_after_claim is None,
                abs(item[1].seconds_after_claim or 0.0),
                item[1].job_id,
            )
        )
    else:
        found.sort(key=lambda item: item[1].job_id)
        found.sort(key=lambda item: (item[0] is None, -(item[0].timestamp()) if item[0] else 0.0))
    return CandidateLookup(
        record, tuple(item[1] for item in found[:CANDIDATE_LIMIT]), bool(complete)
    )
