# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Verified media observations for unpaid scoped composition preparation."""

from dataclasses import dataclass
from fractions import Fraction

from ..scene.film_finish import AudioDuration
from ..scene.film_plan import validate_film_plan
from .film_finishing import CompositionDraft, composition_sources, prepare_composition
from .local_render import RenderCancelled
from .media_probe import MediaInfo, MediaProbeError, probe_tool
from .store import JobOrigin, JobScope


@dataclass(frozen=True)
class VerifiedComposition:
    scope: JobScope
    origin: JobOrigin
    draft: CompositionDraft
    media: tuple[tuple[str, MediaInfo], ...]


def prepare_media(coordinator, recipe, *, production_id, mode, score_task_id, root, origin, cancel):
    """Use the coordinator's existing result/upload owners; no network or new store."""
    uploads = coordinator._uploads
    inspect_upload = uploads.inspect if uploads else None

    def current():
        with coordinator._request_guard(origin):
            if cancel.is_set():
                raise RenderCancelled("Film media inspection cancelled")

    current()
    with coordinator._request_guard(origin):
        sources = composition_sources(
            coordinator._store,
            recipe,
            production_id=production_id,
            mode=mode,
            score_task_id=score_task_id,
            inspect_upload=inspect_upload,
        )
    probe_tool()
    plan = validate_film_plan(recipe)
    kinds = {task["id"]: task["kind"] for task in plan["tasks"]}
    media, durations = {}, {}
    for source in sources:
        current()
        if kinds[source.task_id] == "upload":
            info = uploads.measure_media(
                source.request_id, expected_revision=source.revision, root=root, cancel=cancel
            )
        else:
            info = coordinator._results.measure_media(
                source.request_id,
                expected_revision=source.revision,
                asset_id=source.asset_id,
                root=root,
                cancel=cancel,
            )
        current()
        if info.kind != source.kind:
            raise MediaProbeError("The measured source has a different media kind")
        media[source.task_id] = info
        if source.kind == "audio":
            durations[source.task_id] = AudioDuration(source.scope, source.asset_id, info.duration)
    for shot in plan["shots"]:
        field = "video_task" if mode == "final" else "previs_task"
        task_id = shot.get(field, shot["id"] + ("-video" if mode == "final" else "-previs"))
        trim = round(shot["source_trim"] * plan["fps"]) if mode == "final" else 0
        if media[task_id].duration < Fraction(trim + shot["frames"], plan["fps"]):
            raise MediaProbeError(
                "A selected video does not cover its source trim and editorial cut"
            )
    with coordinator._request_guard(origin):
        if cancel.is_set():
            raise RenderCancelled("Film media inspection cancelled")
        draft = prepare_composition(
            coordinator._store,
            recipe,
            production_id=production_id,
            mode=mode,
            score_task_id=score_task_id,
            audio_durations=durations,
            inspect_upload=inspect_upload,
        )
        if draft.sources != sources:
            raise MediaProbeError("Film sources changed during inspection; prepare a fresh draft")
        return VerifiedComposition(coordinator.scope, origin, draft, tuple(media.items()))
