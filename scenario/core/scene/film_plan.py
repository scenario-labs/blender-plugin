# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Data-only film recipes, editorial timing and explicit reference contracts."""

from __future__ import annotations

import copy
import json
import math
import re
from dataclasses import dataclass
from typing import Any

from ..jobs.store import JobScope, _identity
from .film_scene_plan import _keys, _label, _number, _vector, validate_scene_plan


def identifier(value: Any, label: str = "Identifier") -> str:
    if not isinstance(value, str) or not re.fullmatch(r"[a-zA-Z0-9][a-zA-Z0-9_-]{0,95}", value):
        raise ValueError(f"{label} must contain only letters, numbers, hyphens and underscores.")
    return value


def _text(value: Any, label: str, maximum: int = 12000) -> str:
    if not isinstance(value, str) or len(value) > maximum:
        raise ValueError(f"{label} must be text of at most {maximum} characters.")
    value = value.replace("\u2014", ", ").strip()
    if len(value) > maximum:
        raise ValueError(f"{label} must be text of at most {maximum} characters.")
    return value


def frame_time(value: Any, label: str, fps: int, low: float, high: float) -> float:
    """Validate an editorial time and normalize it to the exact frame boundary."""
    number = _number(value, label, low, high)
    frames = round(number * fps)
    if abs(frames / fps - number) > 1e-6:
        raise ValueError(f"{label} must land on a whole frame.")
    return frames / fps


def _continuity(raw: Any) -> dict:
    raw = _keys(raw, {"entry", "exit", "intentional_changes"}, "Continuity", set())
    result = {}
    for field in ("entry", "exit"):
        values = raw.get(field, {})
        if not isinstance(values, dict) or len(values) > 100:
            raise ValueError("Continuity states need at most 100 named values.")
        result[field] = {
            identifier(key, "Continuity state key"): _label(value, "Continuity state")
            for key, value in values.items()
        }
    changes = raw.get("intentional_changes", [])
    if not isinstance(changes, list) or len(changes) > 100:
        raise ValueError("Intentional changes must list at most 100 state keys.")
    result["intentional_changes"] = list(
        dict.fromkeys(identifier(key, "Intentional state change") for key in changes)
    )
    if set(result["intentional_changes"]) - set(result["entry"]):
        raise ValueError("Intentional changes must name a state in this shot's entry.")
    return result


def continuity_audit(plan: dict) -> dict:
    """Compare adjacent declared states, without claiming visual verification.

    The entering shot owns intentional changes at its incoming cut. A change
    inside a shot is represented by that shot's distinct entry and exit states.
    """
    mismatches, intentional = [], []
    comparisons = 0
    shots = plan.get("shots", [])
    for previous, current in zip(shots, shots[1:], strict=False):
        before = previous.get("continuity", {}).get("exit", {})
        spec = current.get("continuity", {})
        after = spec.get("entry", {})
        for key in sorted(before.keys() & after.keys()):
            comparisons += 1
            if before[key] == after[key]:
                continue
            row = {
                "previous_shot": previous["id"],
                "shot": current["id"],
                "key": key,
                "exit": before[key],
                "entry": after[key],
            }
            target = intentional if key in spec.get("intentional_changes", []) else mismatches
            target.append(row)
    return {
        "kind": "declared_state_adjacency",
        "visual_verification": False,
        "compared_states": comparisons,
        "mismatches": mismatches,
        "intentional_changes": intentional,
        "ok": not mismatches,
    }


def validate_audio_tracks(raw: Any, fps: int, duration: float) -> list[dict]:
    """Validate finite, frame-aligned editorial tracks and absolute duck gains."""
    if not isinstance(raw, list) or len(raw) > 100:
        raise ValueError("Use a list of at most 100 audio tracks.")
    tracks, used = [], set()
    for item in raw:
        item = _keys(
            item,
            {"id", "task", "kind", "start", "end", "trim_start", "volume", "loop", "duck"},
            "Audio track",
            {"id", "task", "kind", "start", "end"},
        )
        tid = identifier(item["id"], "Audio track ID")
        if tid in used:
            raise ValueError("Audio track IDs must be unique.")
        used.add(tid)
        if not isinstance(item["kind"], str) or item["kind"] not in {"dialogue", "sfx", "music"}:
            raise ValueError("Audio track kind must be dialogue, sfx or music.")
        start = frame_time(item["start"], "Audio start", fps, 0, duration)
        end = frame_time(item["end"], "Audio end", fps, 0, duration)
        if end <= start:
            raise ValueError("Audio end must follow its start.")
        loop = item.get("loop", False)
        if not isinstance(loop, bool):
            raise ValueError("Audio loop must be true or false.")
        track = {
            "id": tid,
            "task": identifier(item["task"], "Audio task"),
            "kind": item["kind"],
            "start": start,
            "end": end,
            "trim_start": frame_time(item.get("trim_start", 0), "Audio trim", fps, 0, 900),
            "volume": _number(item.get("volume", 1), "Audio volume", 0, 2),
            "loop": loop,
        }
        ducks = item.get("duck", [])
        if not isinstance(ducks, list) or len(ducks) > 100:
            raise ValueError("Use at most 100 music duck intervals.")
        if "duck" in item and item["kind"] != "music":
            raise ValueError("Only music tracks support duck intervals.")
        if item["kind"] == "music":
            track["duck"] = []
        for duck in ducks:
            duck = _keys(duck, {"start", "end", "volume"}, "Music duck", {"start", "end", "volume"})
            a = frame_time(duck["start"], "Duck start", fps, start, end)
            b = frame_time(duck["end"], "Duck end", fps, start, end)
            if b <= a:
                raise ValueError("Duck end must follow its start.")
            track["duck"].append(
                {"start": a, "end": b, "volume": _number(duck["volume"], "Duck volume", 0, 2)}
            )
        normalized_ducks = track.get("duck", [])
        normalized_ducks.sort(key=lambda value: value["start"])
        if any(
            a["end"] > b["start"]
            for a, b in zip(normalized_ducks, normalized_ducks[1:], strict=False)
        ):
            raise ValueError("Music duck intervals must not overlap.")
        tracks.append(track)
    return tracks


def effective_audio_tracks(plan: dict, score_task_id: str = "score") -> list[dict]:
    """Keep the legacy looping score only when the new track list is omitted."""
    if "audio_tracks" in plan:
        return validate_audio_tracks(plan["audio_tracks"], plan["fps"], plan["duration"])
    return [
        {
            "id": "score",
            "task": score_task_id,
            "kind": "music",
            "start": 0,
            "end": plan["duration"],
            "trim_start": 0,
            "volume": 0.4,
            "loop": True,
            "duck": [],
        }
    ]


def audio_segments(track: dict, fps: int, source_frames: int | None = None) -> list[dict]:
    """Split constant gains and, when known, whole-source loops on frame boundaries."""
    start, end = round(track["start"] * fps), round(track["end"] * fps)
    trim = round(track.get("trim_start", 0) * fps)
    boundaries = {start, end}
    ducks = track.get("duck", [])
    for duck in ducks:
        boundaries.update((round(duck["start"] * fps), round(duck["end"] * fps)))
    looping = track.get("loop", False)
    if source_frames is not None:
        if source_frames < 1:
            raise ValueError("Audio source must contain at least one editorial frame.")
        if not looping and trim + end - start > source_frames:
            raise ValueError(
                f"Audio track {track['id']} extends beyond its source. Shorten it or enable loop."
            )
        if looping:
            boundary = start + source_frames - trim % source_frames
            while boundary < end:
                boundaries.add(boundary)
                if len(boundaries) > 1000:
                    raise ValueError("Audio track needs more than 1000 loop/duck segments.")
                boundary += source_frames
    points = sorted(boundaries)
    segments = []
    for a, b in zip(points, points[1:], strict=False):
        volume = track.get("volume", 1)
        for duck in ducks:
            if round(duck["start"] * fps) <= a < round(duck["end"] * fps):
                volume = duck["volume"]
                break
        offset = trim + a - start
        if looping and source_frames:
            offset %= source_frames
        segments.append(
            {
                "start": a / fps,
                "end": b / fps,
                "trim_start": offset / fps,
                "volume": volume,
                "loop": looping and source_frames is None,
            }
        )
    return segments


def _keys_for_motion(raw: dict, duration: float) -> list[dict]:
    values = raw.get("keyframes", [])
    if not isinstance(values, list) or len(values) > 200:
        raise ValueError("Use at most 200 motion keyframes per object.")
    result, last = [], -1.0
    for key in values:
        key = _keys(key, {"time", "location", "rotation", "scale"}, "Motion keyframe", {"time"})
        t = _number(key["time"], "Keyframe time", 0, duration)
        if t <= last:
            raise ValueError("Motion keyframes must have strictly increasing times.")
        last = t
        normalized = {"time": t}
        for field in ("location", "rotation", "scale"):
            if field in key:
                normalized[field] = _vector(
                    key[field], field, 0.001 if field == "scale" else -1000, 1000
                )
        if len(normalized) == 1:
            raise ValueError("A motion keyframe needs a transform.")
        result.append(normalized)
    return result


def validate_film_plan(raw: dict) -> dict:
    """Validate the whole recipe before the first Blender mutation or cloud job."""
    try:
        return _validate_film_plan(raw)
    except RecursionError:
        raise ValueError("Film recipe nesting is too deep") from None


def _validate_film_plan(raw: dict) -> dict:
    try:
        encoded = json.dumps(raw, allow_nan=False, ensure_ascii=False).encode("utf-8")
    except (TypeError, ValueError, RecursionError):
        raise ValueError("Film recipe must contain finite JSON data") from None
    if len(encoded) > 2_000_000:
        raise ValueError("Film recipe exceeds the 2 MB limit.")
    raw = _keys(
        raw,
        {
            "title",
            "project_id",
            "fps",
            "style",
            "story",
            "tags",
            "heroes",
            "shots",
            "tasks",
            "previs_master_task",
            "final_master_task",
            "audio_tracks",
        },
        "Film",
        {"title", "shots"},
    )
    plan = {
        "title": _label(raw["title"], "Film title"),
        "project_id": (_identity(raw["project_id"]) if raw.get("project_id") is not None else None),
        "fps": int(_number(raw.get("fps", 24), "Frame rate", 24, 60)),
        "style": _text(raw.get("style", ""), "Style"),
        "story": _text(raw.get("story", ""), "Story"),
        "tags": [],
        "heroes": {},
        "shots": [],
        "tasks": [],
    }
    if plan["fps"] != raw.get("fps", 24):
        raise ValueError("Frame rate must be a whole number.")
    for kind in ("previs", "final"):
        field = kind + "_master_task"
        plan[field] = identifier(raw.get(field, kind + "-master"), "Approved master take")
    tags = raw.get("tags", [])
    if not isinstance(tags, list) or len(tags) > 30:
        raise ValueError("Use a list of at most 30 searchable tags.")
    plan["tags"] = list(dict.fromkeys(_label(t, "Tag") for t in tags))
    heroes = raw.get("heroes", {})
    if not isinstance(heroes, dict) or len(heroes) > 20:
        raise ValueError("Use at most 20 named heroes.")
    for key, hero in heroes.items():
        identifier(key, "Hero")
        hero = _keys(
            hero,
            {
                "name",
                "description",
                "mesh",
                "reference",
                "height",
                "width",
                "rotation",
                "material_from",
            },
            "Hero",
            {"name", "description", "mesh", "reference"},
        )
        val = {
            "name": _label(hero["name"], "Hero name"),
            "description": _text(hero["description"], "Hero identity", 4000),
            "mesh": identifier(hero["mesh"]),
            "reference": identifier(hero["reference"]),
            "rotation": _vector(hero.get("rotation", [0, 0, 0]), "Hero rotation", -360, 360),
        }
        if "width" in hero and "height" in hero:
            raise ValueError(
                "Choose either width or height, not both, to preserve hero proportions."
            )
        for dimension in ("height", "width"):
            if dimension in hero:
                val[dimension] = _number(hero[dimension], dimension, 0.01, 200)
        if "material_from" in hero:
            val["material_from"] = identifier(hero["material_from"])
        plan["heroes"][key] = val
    shots = raw["shots"]
    if not isinstance(shots, list) or not 1 <= len(shots) <= 50:
        raise ValueError("Film needs between one and fifty shots.")
    used, cursor = set(), 1
    for item in shots:
        shot = _keys(
            item,
            {
                "id",
                "title",
                "duration",
                "scene",
                "actors",
                "placeholders",
                "action",
                "entry",
                "exit",
                "motion",
                "notes",
                "target_keyframes",
                "style_task",
                "previs_task",
                "video_task",
                "source_trim",
                "source_duration",
                "native_audio_volume",
                "dialogue",
                "continuity",
            },
            "Shot",
            {"id", "title", "duration", "scene"},
        )
        sid = identifier(shot["id"], "Shot ID")
        if sid in used:
            raise ValueError("Shot IDs must be unique.")
        used.add(sid)
        duration = frame_time(shot["duration"], "Shot duration", plan["fps"], 1, 30)
        frames = round(duration * plan["fps"])
        trim = frame_time(shot.get("source_trim", 0), "Source trim", plan["fps"], 0, 29)
        if trim + duration > 30 + 1e-6:
            raise ValueError("Shot source_trim plus duration cannot exceed 30 seconds.")
        source_duration = _number(
            shot.get("source_duration", max(4, math.ceil(trim + duration))),
            "Source duration",
            4,
            30,
        )
        if source_duration != int(source_duration):
            raise ValueError("Source duration must be a whole number of seconds for Seedance.")
        if trim + duration > source_duration + 1e-6:
            raise ValueError("Source duration must cover source trim plus editorial duration.")
        scene = validate_scene_plan(shot["scene"])
        scene["camera"]["duration"] = duration
        val = {
            "id": sid,
            "title": _label(shot["title"], "Shot title"),
            "duration": duration,
            "source_trim": trim,
            "source_duration": int(source_duration),
            "native_audio_volume": _number(
                shot.get("native_audio_volume", 1), "Native audio volume", 0, 2
            ),
            "start_frame": cursor,
            "end_frame": cursor + frames - 1,
            "frames": frames,
            "scene": scene,
            "actors": [],
            "motion": [],
            "placeholders": {},
            "target_keyframes": _keys_for_motion(
                {"keyframes": shot.get("target_keyframes", [])}, duration
            ),
        }
        cursor += frames
        for field in ("action", "entry", "exit", "notes"):
            val[field] = _text(shot.get(field, ""), field, 5000)
        if "continuity" in shot:
            val["continuity"] = _continuity(shot["continuity"])
        if "dialogue" in shot:
            dialogue = _keys(
                shot["dialogue"],
                {"text", "speaker", "task", "offset"},
                "Dialogue",
                {"text", "speaker", "task", "offset"},
            )
            text = _text(dialogue["text"], "Dialogue text", 4000)
            if not text:
                raise ValueError("Dialogue text cannot be empty.")
            val["dialogue"] = {
                "text": text,
                "speaker": _label(dialogue["speaker"], "Dialogue speaker"),
                "task": identifier(dialogue["task"], "Dialogue task"),
                "offset": frame_time(
                    dialogue["offset"], "Dialogue offset", plan["fps"], 0, duration
                ),
            }
            if val["dialogue"]["offset"] >= duration:
                raise ValueError("Dialogue offset must be inside the editorial shot.")
        for kind in ("style", "previs", "video"):
            field = kind + "_task"
            if field not in shot and len(sid) + len(kind) + 1 > 96:
                raise ValueError(
                    f"Shot ID is too long to default {field}; "
                    f"set an explicit {field} of at most 96 characters."
                )
            val[field] = identifier(shot.get(field, sid + "-" + kind), "Approved take")
        placeholders = shot.get("placeholders", {})
        if not isinstance(placeholders, dict) or len(placeholders) > 150:
            raise ValueError("Placeholder legend must map names to intended finished objects.")
        for name, meaning in placeholders.items():
            name = _label(name, "Placeholder")
            if name in val["placeholders"]:
                raise ValueError("Placeholder names must be unique after trimming whitespace.")
            val["placeholders"][name] = _text(meaning, "Interpretation", 2000)
        actors = shot.get("actors", [])
        if not isinstance(actors, list) or len(actors) > 30:
            raise ValueError("Use at most thirty actors per shot.")
        for actor in actors:
            actor = _keys(
                actor,
                {
                    "hero",
                    "name",
                    "location",
                    "rotation",
                    "scale",
                    "keyframes",
                    "action",
                    "action_speed",
                    "phase",
                    "action_until",
                },
                "Actor",
                {"hero", "location"},
            )
            if not isinstance(actor["hero"], str) or actor["hero"] not in plan["heroes"]:
                raise ValueError("Every actor must refer to a named hero.")
            normalized = {
                "hero": actor["hero"],
                "name": _label(actor.get("name", actor["hero"]), "Actor name"),
                "location": _vector(actor["location"], "Actor location"),
                "rotation": _vector(actor.get("rotation", [0, 0, 0]), "Actor rotation", -360, 360),
                "scale": _number(actor.get("scale", 1), "Actor scale", 0.01, 100),
                "action": _text(actor.get("action", "hold"), "Action", 30),
                "action_speed": _number(actor.get("action_speed", 1), "Action speed", 0.1, 5),
                "phase": _number(actor.get("phase", 0), "Action phase", 0, 1),
                "action_until": _number(
                    actor.get("action_until", duration), "Action stop", 0, duration
                ),
                "keyframes": _keys_for_motion(actor, duration),
            }
            if normalized["action"] not in {"hold", "loop"}:
                raise ValueError("Imported action mode must be hold or loop.")
            val["actors"].append(normalized)
        motion = shot.get("motion", [])
        if not isinstance(motion, list) or len(motion) > 150:
            raise ValueError("Use at most 150 animated placeholders.")
        names = {o["name"] for o in scene["objects"]}
        for moving in motion:
            moving = _keys(
                moving, {"object", "keyframes"}, "Placeholder motion", {"object", "keyframes"}
            )
            if not isinstance(moving["object"], str) or moving["object"] not in names:
                raise ValueError("Animated placeholder must exist in the scene plan.")
            val["motion"].append(
                {"object": moving["object"], "keyframes": _keys_for_motion(moving, duration)}
            )
        plan["shots"].append(val)
    plan["total_frames"] = cursor - 1
    plan["duration"] = (cursor - 1) / plan["fps"]
    if plan["duration"] > 900:
        raise ValueError("A film recipe is limited to fifteen minutes.")
    if "audio_tracks" in raw:
        plan["audio_tracks"] = validate_audio_tracks(
            raw["audio_tracks"], plan["fps"], plan["duration"]
        )
    plan["continuity_audit"] = continuity_audit(plan)
    tasks = raw.get("tasks", [])
    if not isinstance(tasks, list) or len(tasks) > 300:
        raise ValueError("Use at most 300 production tasks.")
    used = set()
    for task in tasks:
        task = _keys(
            task,
            {"id", "title", "kind", "model", "parameters", "collection", "tags"},
            "Task",
            {"id", "title", "kind"},
        )
        tid = identifier(task["id"], "Task ID")
        if tid in used:
            raise ValueError("Task IDs must be unique.")
        used.add(tid)
        if not isinstance(task["kind"], str) or task["kind"] not in {"upload", "model"}:
            raise ValueError("Tasks support upload or model generation.")
        value = copy.deepcopy(task)
        value["title"] = _label(task["title"], "Task title")
        value["collection"] = _label(task.get("collection", "Production"), "Collection")
        tags = task.get("tags", [])
        if not isinstance(tags, list) or len(tags) > 30:
            raise ValueError("Use a list of at most 30 task tags")
        value["tags"] = list(dict.fromkeys(_label(t, "Task tag") for t in tags))
        if task["kind"] == "model":
            identifier(task.get("model"), "Model")
            if not isinstance(task.get("parameters"), dict):
                raise ValueError("Model task requires a parameter object.")
        plan["tasks"].append(value)
    return plan


@dataclass(frozen=True)
class TaskAssets:
    """An ordered observation from scoped saved output, never recipe-supplied identity."""

    scope: JobScope
    asset_ids: tuple[str, ...]

    def __post_init__(self):
        if (
            not isinstance(self.scope, JobScope)
            or not isinstance(self.asset_ids, tuple)
            or not 1 <= len(self.asset_ids) <= 128
        ):
            raise ValueError("Use scoped, ordered saved task assets")
        for asset_id in self.asset_ids:
            _identity(asset_id)
        if len(set(self.asset_ids)) != len(self.asset_ids):
            raise ValueError("Saved task assets must be unique")


def require_plan_scope(plan: dict, scope: JobScope) -> None:
    """An explicit recipe project must match the selected override; never discover one."""
    if not isinstance(scope, JobScope):
        raise ValueError("Select the credential-bound job scope")
    if plan.get("project_id") is not None and plan["project_id"] != scope.project_id:
        raise ValueError("The recipe project differs from the selected project override")


def resolve_references(value: Any, records: dict[str, TaskAssets], *, scope: JobScope) -> Any:
    """Resolve $task[:index] only from saved outputs in the exact selected scope.

    The caller obtains TaskAssets from its scoped saved jobs/uploads. This helper
    neither reads storage nor certifies completion of a caller-supplied observation.
    """
    if not isinstance(scope, JobScope):
        raise ValueError("Select the credential-bound job scope")
    try:
        return _resolve_references(value, records, scope=scope)
    except RecursionError:
        raise ValueError("Task reference nesting is too deep") from None


def _resolve_references(value: Any, records: dict[str, TaskAssets], *, scope: JobScope) -> Any:
    if isinstance(value, dict):
        return {key: _resolve_references(item, records, scope=scope) for key, item in value.items()}
    if isinstance(value, list):
        return [_resolve_references(item, records, scope=scope) for item in value]
    if isinstance(value, str) and value.startswith("$"):
        match = re.fullmatch(r"\$([a-zA-Z0-9][a-zA-Z0-9_-]{0,95})(?::(0|[1-9][0-9]{0,2}))?", value)
        if match is None:
            raise ValueError("Use a task reference with an optional nonnegative output index")
        try:
            record = records[match[1]]
            if not isinstance(record, TaskAssets) or record.scope != scope:
                raise ValueError
            return record.asset_ids[int(match[2] or 0)]
        except (KeyError, IndexError, ValueError, TypeError):
            raise ValueError("Reference is not ready in the selected production scope") from None
    return copy.deepcopy(value)


def shot_prompt(plan: dict, shot: dict, hero_order: list[str], style_reference: bool = True) -> str:
    """Bind typed heroes and interpretable geometry to the exact media order."""
    parts = [
        f"CINEMATIC SHOT {shot['id']}: {shot['title']}. {shot.get('source_duration', shot['duration']):g} seconds, one continuous take.",
        "@video1 is the Blender previs for this exact shot. Use its camera movement, timing, subject trajectories, screen direction and spatial layout as the directing reference. Produce a finished cinematic shot in the WORLD AND STYLE specified below; that direction defines the visual medium and treatment.",
        "HERO ASSETS: preserve the following distinct designed assets, their identity, proportions, silhouette, surface panels and color placement. The textured heroes in @video1 are final designs, never proxies to redesign.",
    ]
    for index, key in enumerate(hero_order, 1):
        hero = plan["heroes"][key]
        parts.append(f"@image{index} defines {hero['name']}: {hero['description']}.")
    if style_reference:
        parts.append(
            f"@image{len(hero_order) + 1} is the approved finished-look keyframe for this shot. Apply its architecture, lighting, materials and atmosphere to the environment while retaining the hero identities above and the movement from @video1."
        )
    parts.append(
        "PLACEHOLDERS TO INTERPRET: colored, simple untextured geometry in @video1 describes spatial volumes and action staging. Replace these volumes with convincing finished objects, preserving their intended positions and approximate dimensions. Their diagnostic colors are planning guides, not the final materials."
    )
    parts.extend(f"{name}: {meaning}." for name, meaning in shot["placeholders"].items())
    parts.append(
        f"EDITORIAL WINDOW: source seconds {shot.get('source_trim', 0):g} to "
        f"{shot.get('source_trim', 0) + shot['duration']:g} form the {shot['duration']:g}-second cut. "
        "Place the directed action and state changes inside this window; any remaining source time is a natural hold."
    )
    continuity = shot.get("continuity", {})
    for field in ("entry", "exit"):
        if continuity.get(field):
            parts.append(
                f"DECLARED {field.upper()} OBJECT STATES: "
                + "; ".join(f"{key}={value}" for key, value in sorted(continuity[field].items()))
                + "."
            )
    if continuity.get("intentional_changes"):
        parts.append(
            "INTENTIONAL INCOMING CUT CHANGES: "
            + ", ".join(continuity["intentional_changes"])
            + "."
        )
    if shot.get("dialogue"):
        dialogue = shot["dialogue"]
        parts.append(
            f"DIALOGUE: {dialogue['speaker']} says exactly {json.dumps(dialogue['text'], ensure_ascii=False)}. "
            f"Use @audio1 as the voice, delivery and performance synchronization reference. Speech begins at source second "
            f"{shot.get('source_trim', 0) + dialogue['offset']:g} "
            f"({dialogue['offset']:g} seconds into the editorial cut). Do not paraphrase or add speech."
        )
    parts.extend(
        [
            "WORLD AND STYLE: " + plan["style"],
            "ENTRY STATE: " + shot["entry"],
            "ACTION AND TIMING: " + shot["action"],
            "EXIT STATE: " + shot["exit"],
            "POSE, CONTACT AND SHOT NOTES: " + shot.get("notes", ""),
            "SOUND: synchronized diegetic sound only: footsteps, mechanical motion, wind and energy sounds appropriate to visible events. No music, no score, no narrator. Keep the ending sound natural for an editorial cut.",
            "One camera take with no inserted shots, title cards, captions, labels, watermarks, split screen or reference-board graphics. Natural anatomy, stable solid objects, purposeful physical contact and coherent light. Do not reproduce the flat proxy colors as finished surfaces.",
        ]
    )
    return "\n\n".join(parts)
