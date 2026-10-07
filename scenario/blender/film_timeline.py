# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Explicit editable timeline approval over local shots in the selected job session."""

import json
import uuid
from dataclasses import dataclass, field

import bpy

from . import film_jobs, film_scene
from .film_application import _main_thread


@dataclass(frozen=True)
class _Source:
    scene: object = field(repr=False)
    camera: object = field(repr=False)
    origin: object
    shot_id: str
    binding: tuple = field(repr=False)


@dataclass(eq=False)
class _Review:
    identifier: str
    scene: object = field(repr=False)
    binding: tuple = field(repr=False)
    origin: object
    sources: dict = field(repr=False)
    plan: dict = field(repr=False)
    phase: str = "READY"
    result: object = field(default=None, repr=False)
    error: str = ""


class FilmTimelineCommands:
    """Bounded local references, with no job claim, service operation or persistence."""

    def __init__(self, session):
        self.session = session
        self._sources = {}
        self._reviews = {}

    def _destination(self, scene, binding):
        if not self.session.active:
            raise RuntimeError("The Film connection changed")
        try:
            valid = (
                scene == bpy.context.scene
                and scene in tuple(bpy.data.scenes)
                and not scene.library
                and not scene.override_library
                and film_jobs.snapshot(scene) == binding
            )
        except ReferenceError:
            valid = False
        if not valid:
            raise ValueError("The Film recipe scene changed; inspect it again")

    def inspect(self, scene):
        _main_thread()
        binding = film_jobs.snapshot(scene)
        self._destination(scene, binding)
        plan, digest = film_scene.timeline_recipe(json.loads(binding[1]), binding[0])
        sources, rows = {}, []
        for shot in plan["shots"]:
            choices = []
            for candidate in bpy.data.scenes:
                if not film_scene.matching_shot(
                    candidate, production_id=binding[0], digest=digest, shot=shot, fps=plan["fps"]
                ):
                    continue
                if len(sources) >= 256:
                    raise ValueError("Keep at most 256 matching local shot scenes for inspection")
                identifier = uuid.uuid4().hex
                sources[identifier] = _Source(
                    candidate,
                    candidate.camera,
                    self.session.capture(candidate),
                    shot["id"],
                    binding,
                )
                choices.append({"source_id": identifier, "scene": candidate.name})
            rows.append(
                {
                    "shot_id": shot["id"],
                    "title": shot["title"],
                    "start_frame": shot["start_frame"],
                    "frames": shot["frames"],
                    "choices": choices,
                }
            )
        # A fresh explicit inspection invalidates prior choices, never prepared reviews.
        self._sources = sources
        return {
            "production_id": binding[0],
            "fps": plan["fps"],
            "total_frames": plan["total_frames"],
            "shots": rows,
        }

    def _check_sources(self, binding, sources):
        plan, digest = film_scene.timeline_recipe(json.loads(binding[1]), binding[0])
        if set(sources) != {shot["id"] for shot in plan["shots"]}:
            raise ValueError("Select one local scene for every Film shot")
        for shot in plan["shots"]:
            source = sources[shot["id"]]
            try:
                changed = (
                    source.binding != binding
                    or source.shot_id != shot["id"]
                    or not self.session._origins.current(source.origin)
                    or not film_scene.matching_shot(
                        source.scene,
                        production_id=binding[0],
                        digest=digest,
                        shot=shot,
                        fps=plan["fps"],
                    )
                    or source.scene.camera != source.camera
                )
            except ReferenceError:
                # Blender may invalidate captured RNA before revision delivery.
                changed = True
            if changed:
                raise ValueError("A selected Film shot changed; inspect its scene again")
        return plan

    def prepare(self, scene, *, selections):
        _main_thread()
        film_scene._main_thread()
        binding = film_jobs.snapshot(scene)
        self._destination(scene, binding)
        for review in self._reviews.values():
            try:
                uncertain = review.scene == scene and review.phase == "UNCERTAIN"
            except ReferenceError:
                uncertain = False
            if uncertain:
                raise ValueError("Inspect and dismiss the uncertain timeline review first")
        if not isinstance(selections, dict):
            raise ValueError("Select a source ID for every shot")
        try:
            sources = {shot: self._sources[identifier] for shot, identifier in selections.items()}
        except (KeyError, TypeError):
            raise ValueError("Use source IDs from the current Film timeline inspection") from None
        plan = self._check_sources(binding, sources)
        if len(self._reviews) >= 16:
            expired = next(
                (
                    key
                    for key, item in self._reviews.items()
                    if item.phase in {"BUILT", "ERROR", "DISCARDED"}
                ),
                None,
            )
            if expired is None:
                raise ValueError("Finish or discard an existing timeline review first")
            del self._reviews[expired]
        review = _Review(
            uuid.uuid4().hex, scene, binding, self.session.capture(scene), sources, plan
        )
        self._reviews[review.identifier] = review
        return self.status(review.identifier)

    def current(self, scene):
        """Keep unresolved uncertainty visible ahead of newer local reviews."""
        _main_thread()
        latest = None
        for item in reversed(tuple(self._reviews.values())):
            try:
                if item.scene == scene:
                    if item.phase == "UNCERTAIN":
                        return self.status(item.identifier)
                    if latest is None:
                        latest = item.identifier
            except ReferenceError:
                # Deleted RNA cannot provide a review for the current scene.
                continue
        return self.status(latest) if latest is not None else None

    def status(self, identifier):
        _main_thread()
        item = self._reviews.get(identifier)
        if item is None:
            raise ValueError("The Film timeline review is unavailable")
        name = ""
        if item.result is not None:
            try:
                name = item.result.name
            except ReferenceError:
                # The review remains inspectable after the built scene is deleted.
                name = ""
        return {
            "review_id": identifier,
            "phase": item.phase,
            "scene": name,
            "shot_count": len(item.sources),
            "fps": item.plan["fps"],
            "total_frames": item.plan["total_frames"],
            "error": item.error,
        }

    def discard(self, identifier, *, inspected=False):
        _main_thread()
        item = self._reviews.get(identifier)
        if item is None or item.phase not in {"READY", "ERROR", "UNCERTAIN"}:
            raise ValueError("Discard an unbuilt timeline review")
        if item.phase == "UNCERTAIN" and inspected is not True:
            raise ValueError("Inspect partial timeline data before dismissing the review")
        item.phase = "DISCARDED"
        return self.status(identifier)

    def approve(self, identifier):
        _main_thread()
        film_scene._main_thread()
        item = self._reviews.get(identifier)
        if item is None or item.phase != "READY":
            raise ValueError("Approve a fresh ready Film timeline review")
        current = self.current(item.scene)
        if current and current["phase"] == "UNCERTAIN":
            raise ValueError("Inspect and dismiss the uncertain timeline review first")
        self._destination(item.scene, item.binding)
        self.session.validate_destination(item.origin)
        self._check_sources(item.binding, item.sources)
        shots = {
            shot: film_scene.ShotScene(source.scene, source.camera, None, {}, ())
            for shot, source in item.sources.items()
        }
        before = film_scene._snapshot()
        item.phase = "BUILDING"
        try:
            item.result = film_scene.build_timeline(
                json.loads(item.binding[1]), production_id=item.binding[0], shots=shots
            )
        except Exception:
            item.phase = "ERROR" if film_scene._snapshot() == before else "UNCERTAIN"
            item.error = (
                "Timeline build rolled back; review the local shots again"
                if item.phase == "ERROR"
                else "Timeline cleanup needs inspection; do not repeat the build"
            )
        else:
            item.phase = "BUILT"
        return self.status(identifier)

    def close(self):
        _main_thread()
        self._sources.clear()
        self._reviews.clear()
