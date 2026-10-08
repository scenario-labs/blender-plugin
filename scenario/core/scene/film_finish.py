# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Unpaid Film composition planning from explicitly scoped source observations.

Adapted from Emmanuel de Maistre's Scenario Studio film_finish.py. This module
performs no service calls, file reads, scene changes or generation approval.
"""

import copy
import math
from dataclasses import dataclass
from fractions import Fraction

from ..jobs.store import JobScope, _identity
from .film_plan import (
    TaskAssets,
    audio_segments,
    effective_audio_tracks,
    identifier,
    require_plan_scope,
    validate_film_plan,
)


@dataclass(frozen=True)
class AudioDuration:
    """Caller-measured exact seconds, bound to one saved asset.

    The runtime must verify the underlying saved bytes before supplying this
    observation. Constructing it is not decoding or receipt verification.
    Fraction preserves sample/rate or decimal probe precision until the cut
    chooses floor for a repeating source and ceil for a finite final frame.
    """

    scope: JobScope
    asset_id: str
    seconds: Fraction

    def __post_init__(self):
        if not isinstance(self.scope, JobScope):
            raise ValueError("Measure audio in the selected saved scope")
        _identity(self.asset_id)
        if not isinstance(self.seconds, Fraction) or not 0 < self.seconds <= 86400:
            raise ValueError("Use a positive exact audio duration of at most one day")


def _asset(records, task_id, scope):
    observed = records.get(task_id)
    if (
        not isinstance(observed, TaskAssets)
        or observed.scope != scope
        or len(observed.asset_ids) != 1
    ):
        raise ValueError("Each composition source needs exactly one asset in the selected scope")
    return observed.asset_ids[0]


def required_sources(recipe, *, mode="final", score_task_id="score"):
    """List exact declared source-task roles without reading or trusting outputs."""
    if mode not in {"final", "previs"}:
        raise ValueError("Choose final or previs composition")
    plan = validate_film_plan(recipe)
    sources = {}
    field = "video_task" if mode == "final" else "previs_task"
    for shot in plan["shots"]:
        task_id = shot.get(field, shot["id"] + ("-video" if mode == "final" else "-previs"))
        sources[task_id] = "video"
    if mode == "final":
        for track in effective_audio_tracks(plan, identifier(score_task_id, "Score task")):
            if sources.get(track["task"], "audio") != "audio":
                raise ValueError("Picture and audio tracks need distinct typed source tasks")
            sources[track["task"]] = "audio"
    tasks = {item["id"] for item in plan["tasks"]}
    if not sources.keys() <= tasks:
        raise ValueError("Composition sources must be declared recipe tasks")
    return sources


def compose_task(
    recipe, records, *, scope, audio_durations=None, mode="final", score_task_id="score"
):
    """Build one unpaid task without mutating the recipe or reserving a saved take.

    Saved-job/upload owners supply records; recipe-supplied account/project fields
    cannot certify source ownership. This helper does not establish source media
    type, job completion, current schema support or live provider acceptance.
    """
    if mode not in {"final", "previs"}:
        raise ValueError("Choose final or previs composition")
    if not isinstance(records, dict):
        raise ValueError("Use scoped saved source observations")
    audio_durations = {} if audio_durations is None else audio_durations
    if not isinstance(audio_durations, dict):
        raise ValueError("Use asset-bound audio measurements")
    plan = validate_film_plan(recipe)
    require_plan_scope(plan, scope)
    required_sources(recipe, mode=mode, score_task_id=score_task_id)
    master = plan[mode + "_master_task"]
    tasks = {item["id"]: item for item in plan["tasks"]}
    if master in tasks:
        raise ValueError("Choose a new master task name; existing recipe tasks are preserved")

    def source(task_id):
        identifier(task_id, "Composition source task")
        if task_id not in tasks:
            raise ValueError("Composition sources must be declared recipe tasks")
        return _asset(records, task_id, scope)

    layers = []
    for shot in plan["shots"]:
        field = "video_task" if mode == "final" else "previs_task"
        task_id = shot.get(field, shot["id"] + ("-video" if mode == "final" else "-previs"))
        source(task_id)
        layers.append(
            {
                "source": "$" + task_id,
                "type": "video",
                "startTime": (shot["start_frame"] - 1) / plan["fps"],
                "endTime": shot["end_frame"] / plan["fps"],
                "trimStart": shot["source_trim"] if mode == "final" else 0,
                "width": "1920",
                "height": "1080",
                "fit": "cover",
                "mute": False,
                "volume": shot["native_audio_volume"] if mode == "final" else 1.0,
            }
        )
    if mode == "final":
        for track in effective_audio_tracks(plan, identifier(score_task_id, "Score task")):
            asset_id = source(track["task"])
            observed = audio_durations.get(track["task"])
            if (
                not isinstance(observed, AudioDuration)
                or observed.scope != scope
                or observed.asset_id != asset_id
            ):
                raise ValueError("Measure each selected audio asset in the current scope")
            exact_frames = observed.seconds * plan["fps"]
            frames = math.floor(exact_frames) if track["loop"] else math.ceil(exact_frames)
            for segment in audio_segments(track, plan["fps"], frames):
                layers.append(
                    {
                        "source": "$" + track["task"],
                        "type": "audio",
                        "startTime": segment["start"],
                        "endTime": segment["end"],
                        "trimStart": segment["trim_start"],
                        "loop": False,
                        "mute": False,
                        "volume": segment["volume"],
                    }
                )
                if len(layers) > 50:
                    raise ValueError(
                        "The composition exceeds 50 video/audio layers, including score loops "
                        "and duck segments. Reduce the shot count or audio segments."
                    )
    suffix = " / Final master" if mode == "final" else " / Previs review"
    return {
        "id": master,
        "title": plan["title"][: 120 - len(suffix)] + suffix,
        "kind": "model",
        "model": "model_scenario-compose-video",
        "collection": "Final" if mode == "final" else "Previs",
        "tags": [mode, "master" if mode == "final" else "review", "1080p"],
        "parameters": {
            "layers": layers,
            "canvasMode": "custom",
            "canvasWidth": 1920,
            "canvasHeight": 1080,
            "durationMode": "custom",
            "duration": plan["duration"],
            "fps": plan["fps"],
            "videoOutputFormat": "mp4",
            "compressionLevel": 23,
        },
    }


def compose_recipe(recipe, records, *, scope, **options):
    """Return a separate recipe draft; callers must explicitly review/install it."""
    task = compose_task(recipe, records, scope=scope, **options)
    result = copy.deepcopy(recipe)
    result.setdefault("tasks", []).append(task)
    validate_film_plan(result)
    return result
