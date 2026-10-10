# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Merge the cloud job list with local job records for the Generations panel. No bpy."""

from dataclasses import dataclass, field
from decimal import Decimal

TERMINAL = frozenset({"success", "failure", "canceled"})
NESTING_LIMIT = 4


@dataclass
class HistoryEntry:
    job_id: str
    kind: str
    model_id: str
    prompt: str
    status: str
    created_at: str
    cu_cost: float = None
    asset_ids: list = field(default_factory=list)
    local_files: list = field(default_factory=list)
    local_request_ids: tuple[str, ...] = ()
    workflow_id: str = ""
    # Malformed billing, or a finished workflow run whose step charges could not all be read.
    cost_unavailable: bool = False
    # The workflow run this step belongs to; its cost is part of that total.
    workflow_job_id: str = ""

    @property
    def is_success(self):
        return self.status in ("success", "succeeded", "completed")


def _amount(value):
    """A finite CU amount; numeric strings stay accepted as before."""
    if isinstance(value, bool) or not isinstance(value, (int, float, str)):
        raise ValueError("Scenario returned an invalid job cost")
    try:
        amount = Decimal(str(value).strip())
    except ArithmeticError:
        raise ValueError("Scenario returned an invalid job cost") from None
    if not amount.is_finite():
        raise ValueError("Scenario returned an invalid job cost")
    return amount


def job_cost(job):
    """One job's documented charge: billing.cuCost plus its cuCostDetails add-ons.

    Returns None without billing or cuCost; malformed values raise ValueError.
    Add-ons such as quality-gate read 0 after a refund, while cuCost keeps the
    main action's original charge.
    """
    billing = job.get("billing")
    if billing is None or billing.get("cuCost") is None:
        return None
    total = _amount(billing["cuCost"])
    details = billing.get("cuCostDetails")
    details = {} if details is None else details
    if not isinstance(details, dict):
        raise ValueError("Scenario returned invalid job cost details")
    for value in details.values():
        if value is not None:
            total += _amount(value)
    return total


def _step_cost(row):
    try:
        return job_cost(row)
    except (AttributeError, TypeError, ValueError):
        return None  # A separately read step cannot fail the listed page.


def _identity(value):
    return value if isinstance(value, str) and value and "/" not in value else None


def _metadata(row):
    value = row.get("metadata") if isinstance(row, dict) else None
    return value if isinstance(value, dict) else {}


def _step_ids(job, children):
    """Started steps named by the run's flow, then steps that name the run."""
    flow = _metadata(job).get("flow")
    ids = [
        node.get("jobId")
        for node in (flow if isinstance(flow, list) else ())
        if isinstance(node, dict) and _identity(node.get("jobId"))
    ]
    return list(dict.fromkeys(ids + children.get(job.get("jobId"), [])))


def _parents(rows):
    children = {}
    for row in rows:
        parent = _identity(_metadata(row).get("workflowJobId"))
        if parent and _identity(row.get("jobId")):
            children.setdefault(parent, []).append(row["jobId"])
    return children


def missing_workflow_steps(jobs, limit=24, *, attempted=()):
    """Step job IDs that finished workflow runs name but `jobs` does not contain.

    At most `limit` IDs, chosen by whole run, fewest first, so one large loop
    cannot starve the other runs. A run that does not fit, or names an
    `attempted` step still absent, gets no reads: it could not be priced.
    """
    jobs = [row for row in jobs if isinstance(row, dict)]
    known = {row.get("jobId") for row in jobs}
    attempted = set(attempted)
    children = _parents(jobs)
    needs = []
    for job in jobs:
        status = job.get("status")
        if job.get("jobType") != "workflow" or str(status or "").lower() not in TERMINAL:
            continue
        need = [identifier for identifier in _step_ids(job, children) if identifier not in known]
        if need and attempted.isdisjoint(need):
            needs.append(need)
    missing = []
    for need in sorted(needs, key=len):  # Stable: page order among equal needs.
        new = [identifier for identifier in need if identifier not in missing]
        if len(missing) + len(new) <= limit:
            missing.extend(new)
    return missing


def workflow_cost(job, rows, children, _path=()):
    """A finished run's own charge plus each step's; None if any is unknown.

    Steps that are themselves workflow runs are summed recursively, to a bound.
    """
    identifier = job.get("jobId")
    if identifier in _path or len(_path) >= NESTING_LIMIT:
        return None
    total = _step_cost(job)
    for step in _step_ids(job, children):
        row = rows.get(step)
        if total is None or row is None:
            return None
        if row.get("jobType") == "workflow":
            cost = workflow_cost(row, rows, children, (*_path, identifier))
        else:
            cost = _step_cost(row)
        total = None if cost is None else total + cost
    return total


def is_prompt_asset(value):
    """The jobs list replaces the prompt text by the id of a text asset once the job is archived."""
    return isinstance(value, str) and value.startswith("asset_")


def prompt_asset_ids(jobs):
    ids = []
    for job in jobs:
        value = ((job.get("metadata") or {}).get("input") or {}).get("prompt")
        if is_prompt_asset(value) and value not in ids:
            ids.append(value)
    return ids


def resolve_prompts(jobs, texts):
    """Replace prompt asset ids by their text where `texts` (asset_id -> text) knows them."""
    for job in jobs:
        inp = (job.get("metadata") or {}).get("input") or {}
        value = inp.get("prompt")
        if is_prompt_asset(value) and value in texts:
            inp["prompt"] = texts[value]
    return jobs


def entries_from_jobs(jobs, local_records, kinds=None, *, shared_records=(), related=()):
    """History rows for model jobs and workflow runs.

    `related` holds step jobs read separately to price workflow runs; they
    complete totals without becoming rows themselves.
    """
    kinds = kinds or {}
    local_by_job = {r.job_id: r for r in local_records if r.job_id}
    shared_by_job = {}
    for record in shared_records:
        if record.remote_job_id:
            shared_by_job.setdefault(record.remote_job_id, []).append(record.intent.request_id)
    rows = {row.get("jobId"): row for row in (*related, *jobs) if isinstance(row, dict)}
    children = _parents(rows.values())
    entries = []
    for job in jobs:
        job_type = job.get("jobType")
        if job_type not in ("custom", "workflow"):
            continue
        workflow = job_type == "workflow"
        meta = job.get("metadata") or {}
        inp = meta.get("input") or {}
        job_id = job.get("jobId") or job.get("id")
        shared = tuple(shared_by_job.get(job_id, ()))
        # An old unscoped cache must never supply files or bypass saved-result approval.
        local = None if shared else local_by_job.get(job_id)
        model_id = "" if workflow else inp.get("modelId") or (local.model_id if local else "")
        status = (job.get("status") or "").lower()
        try:
            cost, malformed = job_cost(job), False
        except (AttributeError, TypeError, ValueError):
            cost, malformed = None, True  # Only this row's cost becomes unavailable.
        if workflow:
            # A running workflow has not charged every step yet.
            cost = workflow_cost(job, rows, children) if status in TERMINAL else None
        prompt = inp.get("prompt")
        if is_prompt_asset(prompt):
            prompt = local.meta.get("prompt") if local else ""
        entries.append(
            HistoryEntry(
                job_id=job_id,
                kind="workflow"
                if workflow
                else local.kind
                if local
                else kinds.get(model_id, "image"),
                model_id=model_id,
                prompt=str(prompt or (local.meta.get("prompt") if local else "") or ""),
                status=status,
                created_at=job.get("createdAt") or "",
                cu_cost=None if cost is None else float(cost),
                asset_ids=list(meta.get("assetIds") or []),
                local_files=list(local.files) if local else [],
                local_request_ids=shared,
                workflow_id=str(meta.get("workflowId") or "") if workflow else "",
                cost_unavailable=cost is None and (malformed or (workflow and status in TERMINAL)),
                workflow_job_id=_identity(meta.get("workflowJobId")) or "",
            )
        )
    entries.sort(key=lambda e: e.created_at, reverse=True)
    return entries
