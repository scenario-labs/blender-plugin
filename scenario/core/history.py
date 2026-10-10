# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Merge the cloud job list with local job records for the Generations panel. No bpy."""

from dataclasses import dataclass, field

# A row neither saved results nor the model catalog describe. Never guess image.
UNKNOWN_KIND = "unknown"
_MESH_MEDIA_TYPES = frozenset({"application/x-ply"})


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

    @property
    def is_success(self):
        return self.status in ("success", "succeeded", "completed")


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


def result_kind(assets):
    """The kind that saved result media types establish, or None.

    A mesh, clip or sound outranks the preview images and maps that accompany
    it. Images carrying documented PBR map roles beyond a base color form a
    material; other images are an image result.
    """
    media = {asset.media_type for asset in assets}
    image_roles = {item.texture_role for item in assets if item.media_type.startswith("image/")}
    if any(item.startswith("model/") or item in _MESH_MEDIA_TYPES for item in media):
        return "3d"
    for kind in ("video", "audio"):
        if any(item.startswith(kind + "/") for item in media):
            return kind
    if image_roles - {None, "base"}:
        return "material"
    return "image" if image_roles else None


def entries_from_jobs(jobs, local_records, kinds=None, *, shared_records=()):
    """Project cloud model jobs into history rows, newest first.

    `kinds` maps model IDs to catalog kinds. A row's kind comes from its legacy
    record, then its saved result media, then the catalog, else UNKNOWN_KIND.
    """
    kinds = kinds or {}
    local_by_job = {r.job_id: r for r in local_records if r.job_id}
    shared_by_job = {}
    saved_assets = {}
    for record in shared_records:
        if record.remote_job_id:
            shared_by_job.setdefault(record.remote_job_id, []).append(record.intent.request_id)
            saved_assets.setdefault(record.remote_job_id, []).extend(
                item.asset for item in record.results
            )
    entries = []
    for job in jobs:
        if job.get("jobType") != "custom":
            continue
        meta = job.get("metadata") or {}
        inp = meta.get("input") or {}
        job_id = job.get("jobId") or job.get("id")
        shared = tuple(shared_by_job.get(job_id, ()))
        # An old unscoped cache must never supply files or bypass saved-result approval.
        local = None if shared else local_by_job.get(job_id)
        model_id = inp.get("modelId") or (local.model_id if local else "")
        billing = job.get("billing") or {}
        prompt = inp.get("prompt")
        if is_prompt_asset(prompt):
            prompt = local.meta.get("prompt") if local else ""
        kind = (
            local.kind
            if local
            else result_kind(saved_assets.get(job_id, ())) or kinds.get(model_id) or UNKNOWN_KIND
        )
        entries.append(
            HistoryEntry(
                job_id=job_id,
                kind=kind,
                model_id=model_id,
                prompt=str(prompt or (local.meta.get("prompt") if local else "") or ""),
                status=(job.get("status") or "").lower(),
                created_at=job.get("createdAt") or "",
                cu_cost=float(billing["cuCost"]) if billing.get("cuCost") is not None else None,
                asset_ids=list(meta.get("assetIds") or []),
                local_files=list(local.files) if local else [],
                local_request_ids=shared,
            )
        )
    entries.sort(key=lambda e: e.created_at, reverse=True)
    return entries
