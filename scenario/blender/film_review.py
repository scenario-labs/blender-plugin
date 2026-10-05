# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Transactional Film review assembly from scoped, measured saved media.

Adapted from Emmanuel de Maistre's Scenario Studio film_finish.py. The caller
owns current source selection, measured metadata, origin checks and approval.
This primitive does not discover jobs, download, spend or grant an application
claim. Independent receipt-checked copies keep strips usable after source cleanup.
"""

import hashlib
import json
import math
import shutil
import tempfile
import threading
from dataclasses import dataclass, field
from fractions import Fraction
from pathlib import Path

import bpy

from ..core.jobs import media_probe
from ..core.jobs.store import JobScope, StoredResult, _identity, _json
from ..core.scene.film_finish import required_sources
from ..core.scene.film_plan import (
    audio_segments,
    continuity_audit,
    effective_audio_tracks,
    require_plan_scope,
    validate_film_plan,
)
from .film_scene import _main_thread

MAX_TOTAL_BYTES = 2 * 1024**3
MAX_STRIPS = 2000


class FilmReviewError(RuntimeError):
    """The build failed and its new scene/data/files were rolled back."""


@dataclass(frozen=True)
class ReviewSource:
    scope: JobScope
    result: StoredResult
    path: Path = field(repr=False)
    media: media_probe.MediaInfo


@dataclass(frozen=True)
class ReviewScene:
    scene: object = field(repr=False)
    directory: Path = field(repr=False)
    paths: tuple[Path, ...] = field(repr=False)
    frames: int
    fps: int
    shots: int
    audio_segments: int
    master_imported: bool


def _source(value, scope, kind):
    if not isinstance(value, ReviewSource) or value.scope != scope:
        raise ValueError("Select measured saved Film media in the current scope")
    item, info, path = value.result, value.media, value.path
    if not isinstance(item, StoredResult) or not isinstance(info, media_probe.MediaInfo):
        raise ValueError("Use saved receipts and measured media metadata")
    receipt = item.receipt
    if (
        receipt is None
        or item.asset.media_type not in media_probe.FORMATS
        or media_probe.FORMATS[item.asset.media_type][0] != kind
        or info.kind != kind
        or not isinstance(path, Path)
        or not path.is_absolute()
        or path.name != receipt.name
        or not 0 < receipt.size <= media_probe.MAX_BYTES
        or info.sha256 != receipt.sha256
        or info.size != receipt.size
        or not isinstance(info.duration, Fraction)
        or not 0 < info.duration <= 86400
        or (
            info.audio_duration is not None
            and (
                not isinstance(info.audio_duration, Fraction)
                or not 0 < info.audio_duration <= 86400
            )
        )
    ):
        raise ValueError("Saved Film media and its measurement must match the exact receipt")
    if kind == "video" and (
        not isinstance(info.frame_rate, Fraction)
        or not 0 < info.frame_rate <= 240
        or any(type(n) is not int or not 1 <= n <= 16384 for n in (info.width, info.height))
    ):
        raise ValueError("Use measured video dimensions and frame rate")
    return value


def _picture(value, fps, frames, trim):
    # The direct strip API preserves source frame indexing, not elapsed time
    # across differing rates. Never stretch a short source into an accepted cut.
    if value.media.frame_rate != fps:
        raise ValueError("Match saved video frame rate to the Film cut before native assembly")
    if value.media.duration < Fraction(trim + frames, fps):
        raise ValueError("Saved video does not cover its source trim and editorial cut")


def _plan(recipe, scope, sources, mode, score_task_id, master):
    plan = validate_film_plan(recipe)
    require_plan_scope(plan, scope)
    roles = required_sources(recipe, mode=mode, score_task_id=score_task_id)
    if not isinstance(sources, dict) or set(sources) != set(roles):
        raise ValueError("Select exactly the declared picture and audio source tasks")
    for task, kind in roles.items():
        _source(sources[task], scope, kind)
    pictures, audio = [], []
    field = "video_task" if mode == "final" else "previs_task"
    for shot in plan["shots"]:
        task = shot.get(field, shot["id"] + ("-video" if mode == "final" else "-previs"))
        trim = round(shot["source_trim"] * plan["fps"]) if mode == "final" else 0
        _picture(sources[task], plan["fps"], shot["frames"], trim)
        pictures.append((shot, task, trim))
    if mode == "final":
        for channel, track in enumerate(effective_audio_tracks(plan, score_task_id), 3):
            duration = sources[track["task"]].media.duration * plan["fps"]
            frames = math.floor(duration) if track["loop"] else math.ceil(duration)
            for segment in audio_segments(track, plan["fps"], frames):
                audio.append((channel, track, segment))
    if len(pictures) * 2 + len(audio) + (2 if master else 0) > MAX_STRIPS:
        raise ValueError("Keep the native Film review within 2000 picture and sound strips")
    if master is not None:
        _source(master, scope, "video")
        _picture(master, plan["fps"], plan["total_frames"], 0)
    total = sum(source.result.receipt.size for source in sources.values())
    if master is not None:
        total += master.result.receipt.size
    if total > MAX_TOTAL_BYTES:
        raise ValueError("Keep saved media for one native Film review within 2 GiB")
    return plan, pictures, audio


def _snapshot():
    return {name: set(getattr(bpy.data, name)) for name in ("scenes", "sounds")}


def _rollback(before):
    for scene in set(bpy.data.scenes) - before["scenes"]:
        bpy.data.scenes.remove(scene)
    for sound in set(bpy.data.sounds) - before["sounds"]:
        if sound.users:
            raise RuntimeError("Film review cleanup needs inspection")
        bpy.data.sounds.remove(sound)
    if _snapshot() != before:
        raise RuntimeError("Film review cleanup needs inspection")


def _place(strip, start, frames, trim, channel):
    if strip.frame_duration < trim + frames:
        raise ValueError("Decoded source is shorter than the reviewed cut")
    strip.frame_start = start - trim
    strip.frame_offset_start = trim
    strip.frame_final_duration = frames
    strip.channel = channel
    if (strip.frame_final_start, strip.frame_final_end) != (start, start + frames):
        raise ValueError("Blender did not preserve the reviewed editorial range")


def _movie(editor, source, path, name, start, frames, trim, channel, *, muted=False):
    strip = editor.strips.new_movie(name, str(path), channel, start, fit_method="FILL")
    if (
        not strip.elements
        or (strip.elements[0].orig_width, strip.elements[0].orig_height)
        != (source.media.width, source.media.height)
        or not math.isclose(strip.fps, float(source.media.frame_rate), abs_tol=0.0001)
    ):
        raise ValueError("Decoded movie differs from the reviewed dimensions or frame rate")
    _place(strip, start, frames, trim, channel)
    strip.mute = muted
    strip["scenario_asset"] = source.result.asset.asset_id
    return strip


def _sound(editor, source, path, name, start, frames, trim, channel, volume, *, muted=False):
    strip = editor.strips.new_sound(name, str(path), channel, start)
    if strip.sound is None:
        raise ValueError("Blender could not decode the reviewed audio")
    _place(strip, start, frames, trim, channel)
    strip.volume = volume
    strip.mute = muted
    strip["scenario_asset"] = source.result.asset.asset_id
    return strip


def build_review_scene(
    recipe, *, scope, production_id, sources, mode="final", score_task_id="score", master=None
):
    """Build a new independent sequence, preserving every existing scene and selection.

    The caller supplies current scoped receipts and their measured metadata. This
    synchronous, bounded primitive rehashes independent file copies before native
    decoding; shared workers/approval must be wired before exposing an entry point.
    Successful copies persist under extension user storage, never the package.
    """
    _main_thread()
    if not isinstance(scope, JobScope):
        raise ValueError("Select the current saved-job scope")
    _identity(production_id)
    plan, pictures, audio = _plan(recipe, scope, sources, mode, score_task_id, master)
    package = __package__.rsplit(".", 1)[0]
    root = Path(bpy.utils.extension_path_user(package, path="film-review", create=True))
    before = _snapshot()
    directory = Path(tempfile.mkdtemp(prefix="review-", dir=root))
    try:
        paths = {}
        all_sources = list(sources.items()) + ([(None, master)] if master is not None else [])
        for index, (task, source) in enumerate(all_sources):
            suffix = media_probe.FORMATS[source.result.asset.media_type][1]
            target = directory / (str(index) + suffix)
            media_probe._snapshot(source.path, source.result.receipt, target, threading.Event())
            paths[task] = target
        review = bpy.data.scenes.new(plan["title"] + " / " + mode.title() + " Review")
        review.render.fps, review.render.fps_base = plan["fps"], 1.0
        review.render.resolution_x, review.render.resolution_y = 1920, 1080
        review.render.resolution_percentage = 100
        review.frame_start, review.frame_end = 1, plan["total_frames"]
        review.render.use_sequencer = True
        review.view_settings.view_transform, review.view_settings.look = "Standard", "None"
        review.view_settings.exposure, review.view_settings.gamma = 0, 1
        review["scenario_film"] = plan["title"]
        review["scenario_sequence_kind"] = "downloaded_" + mode + "_review"
        review["scenario_production_id"] = production_id
        review["scenario_recipe_sha256"] = hashlib.sha256(_json(recipe).encode()).hexdigest()
        review["scenario_continuity_audit"] = json.dumps(continuity_audit(plan))
        editor = review.sequence_editor_create()
        for shot, task, trim in pictures:
            source = sources[task]
            _movie(
                editor,
                source,
                paths[task],
                shot["id"] + " / picture",
                shot["start_frame"],
                shot["frames"],
                trim,
                1,
            )
            if source.media.audio_duration is not None:
                frames = min(
                    shot["frames"], math.ceil(source.media.audio_duration * plan["fps"]) - trim
                )
                if frames > 0:
                    _sound(
                        editor,
                        source,
                        paths[task],
                        shot["id"] + " / native audio",
                        shot["start_frame"],
                        frames,
                        trim,
                        2,
                        shot["native_audio_volume"] if mode == "final" else 1.0,
                    )
            review.timeline_markers.new(shot["title"], frame=shot["start_frame"])
        mix = []
        for index, (channel, track, segment) in enumerate(audio):
            task = track["task"]
            _sound(
                editor,
                sources[task],
                paths[task],
                track["id"] + " / " + str(index + 1),
                1 + round(segment["start"] * plan["fps"]),
                round((segment["end"] - segment["start"]) * plan["fps"]),
                round(segment["trim_start"] * plan["fps"]),
                channel,
                segment["volume"],
            )
            mix.append({"id": track["id"], "task": task, **segment})
        review["scenario_audio_mix"] = json.dumps(mix)
        if master is not None:
            channel = max([10, *(item[0] + 1 for item in audio)])
            _movie(
                editor,
                master,
                paths[None],
                "Scenario master / muted alternate",
                1,
                plan["total_frames"],
                0,
                channel,
                muted=True,
            )
            if master.media.audio_duration is not None:
                frames = min(
                    plan["total_frames"], math.ceil(master.media.audio_duration * plan["fps"])
                )
                _sound(
                    editor,
                    master,
                    paths[None],
                    "Scenario master audio / muted alternate",
                    1,
                    frames,
                    0,
                    channel + 1,
                    1.0,
                    muted=True,
                )
        # New inactive scenes need synchronized layer data before library copies
        # on Blender 5.2. Update only this scene, keeping the working scene selected.
        for layer in review.view_layers:
            layer.update()
        return ReviewScene(
            review,
            directory,
            tuple(paths.values()),
            plan["total_frames"],
            plan["fps"],
            len(pictures),
            len(audio),
            master is not None,
        )
    except Exception:
        # Keep snapshots if rollback itself fails: partial strips may reference them.
        _rollback(before)
        shutil.rmtree(directory)
        raise FilmReviewError(
            "Could not build the Film review; saved source media is preserved"
        ) from None
