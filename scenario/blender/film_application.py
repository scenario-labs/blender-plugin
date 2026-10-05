# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Scoped Film shot reviews over the existing session, workers and application claims."""

import json
import threading
import uuid
from dataclasses import dataclass, field

import bpy

from ..core.jobs.film_sources import select_shot_sources, shot_records
from ..core.jobs.results import VerifiedResults
from . import film_scene


def _main_thread():
    if threading.current_thread() is not threading.main_thread():
        raise RuntimeError("Use Film shot commands on Blender's main thread")


def _binding(scene):
    return scene.scenario_film.production_id, scene.scenario_film.recipe_json


@dataclass(eq=False)
class _Review:
    identifier: str
    scene: object = field(repr=False)
    binding: tuple = field(repr=False)
    origin: object
    shot_id: str
    selections_json: str = field(repr=False)
    sources: tuple = field(repr=False)
    phase: str = "VERIFYING"
    task: object = field(default=None, repr=False)
    completions: dict = field(default_factory=dict, repr=False)
    application: object = field(default=None, repr=False)
    receipts: list = field(default_factory=list, repr=False)
    records: dict = field(default_factory=dict, repr=False)
    unknown: bool = False
    error: str = ""


class FilmShotCommands:
    """Bounded presentation/receipt handles; no additional client, worker pool or store."""

    def __init__(self, session, store):
        self.session, self.store = session, store
        self._reviews = {}

    def inspect(self, scene, *, shot_id):
        _main_thread()
        if not self.session.active:
            raise RuntimeError("The Film connection changed")
        production, raw = _binding(scene)
        records = shot_records(
            self.store, json.loads(raw), production_id=production, shot_id=shot_id
        )
        return [
            {
                "hero_id": hero,
                "request_id": record.intent.request_id,
                "revision": record.revision,
                "assets": [
                    {"asset_id": item.asset.asset_id, "name": item.asset.name}
                    for item in record.results
                    if item.asset.media_type == "model/gltf-binary" and item.receipt
                ],
            }
            for hero, record in records
        ]

    def _check(self, review, *, selected=True):
        if not self.session.active:
            raise RuntimeError("The Film connection changed")
        if selected:
            self.session.validate_destination(review.origin)
        elif not self.session._origins.current(review.origin):
            raise ValueError("The Film destination changed; prepare a new review")
        try:
            valid = (
                (not selected or review.scene == bpy.context.scene)
                and review.scene in tuple(bpy.data.scenes)
                and not review.scene.library
                and not review.scene.override_library
                and _binding(review.scene) == review.binding
            )
        except ReferenceError:
            valid = False
        if not valid:
            raise ValueError("The Film production, recipe or scene changed; prepare a new review")

    def _sources(self, review):
        return select_shot_sources(
            self.store,
            json.loads(review.binding[1]),
            production_id=review.binding[0],
            shot_id=review.shot_id,
            selections=json.loads(review.selections_json),
        )

    def prepare(self, scene, *, shot_id, selections):
        _main_thread()
        film_scene._main_thread()
        if scene != bpy.context.scene or scene.library or scene.override_library:
            raise ValueError("Choose the current local Film recipe scene")
        self.poll()
        if len(self._reviews) >= 16:
            expired = next(
                (
                    key
                    for key, value in self._reviews.items()
                    if value.phase in {"ERROR", "DISCARDED", "BUILT"} and value.task is None
                ),
                None,
            )
            if expired is None:
                raise RuntimeError("Finish or discard an existing Film shot review first")
            del self._reviews[expired]
        binding = _binding(scene)
        for existing in self._reviews.values():
            try:
                duplicate = existing.scene == scene and existing.shot_id == shot_id
            except ReferenceError:
                duplicate = False
            if duplicate and existing.phase in {"VERIFYING", "READY", "UNCERTAIN"}:
                raise RuntimeError("Finish, discard or inspect the existing shot review")
        bpy.context.view_layer.update()
        review = _Review(
            uuid.uuid4().hex,
            scene,
            binding,
            self.session.capture(scene),
            shot_id,
            json.dumps(selections, sort_keys=True, allow_nan=False),
            (),
        )
        self._check(review)
        review.sources = self._sources(review)
        self._reviews[review.identifier] = review
        try:
            self._advance(review)
        except Exception:
            del self._reviews[review.identifier]
            raise
        return self.status(review.identifier)

    def _advance(self, review):
        self._check(review)
        if self._sources(review) != review.sources:
            raise ValueError("Film hero outputs changed; inspect them again")
        for source in review.sources:
            request_id = source.record.intent.request_id
            if request_id not in review.completions:
                # Serial admission also handles a shot with more heroes than worker slots.
                review.task = self.session.verify_results(
                    request_id, expected_revision=source.record.revision
                )
                return
        review.phase = "READY"

    def poll(self):
        _main_thread()
        for review in self._reviews.values():
            if review.phase in {"READY", "VERIFYING"}:
                try:
                    self._check(review, selected=False)
                    if review.scene != bpy.context.scene:
                        # Keep completed work queued for its unchanged source context.
                        continue
                except Exception:
                    review.phase, review.error = "ERROR", "Film recipe, scene or connection changed"
                    review.completions.clear()
            if review.task is not None and review.task.done():
                completions = self.session.drain(task=review.task)
                review.task = None
                if review.phase == "VERIFYING":
                    try:
                        if len(completions) != 1 or completions[0].error is not None:
                            raise ValueError("Saved Film model verification failed")
                        completion = completions[0]
                        if not isinstance(completion.result, VerifiedResults):
                            raise ValueError("Use verified Film model results")
                        record = completion.result.record
                        if not any(source.record == record for source in review.sources):
                            raise ValueError("Film verification returned a different saved job")
                        review.completions[record.intent.request_id] = completion
                        self._advance(review)
                    except Exception:
                        review.phase, review.error = (
                            "ERROR",
                            "Film shot or saved files changed; prepare a new review",
                        )
                        review.completions.clear()

    def status(self, identifier):
        _main_thread()
        review = self._reviews.get(identifier)
        if review is None:
            raise ValueError("The Film shot review is unavailable")
        scene_name = ""
        if review.application is not None:
            try:
                scene_name = review.application.scene.name
            except ReferenceError:
                pass
        return {
            "review_id": identifier,
            "shot_id": review.shot_id,
            "phase": review.phase,
            "hero_count": len(review.sources),
            "scene": scene_name,
            "error": review.error,
            "receipt_retry_available": bool(review.receipts),
            "inspection_required": review.unknown,
        }

    def discard(self, identifier):
        _main_thread()
        review = self._reviews.get(identifier)
        if review is None or review.phase not in {"VERIFYING", "READY", "ERROR"}:
            raise ValueError("Discard only an unsubmitted Film shot review")
        review.phase = "DISCARDED"
        review.completions.clear()
        return self.status(identifier)

    def _finish_claims(self, review, claims, *, success):
        command = (
            self.session._coordinator.complete_application
            if success
            else self.session._coordinator.fail_application
        )
        for claim in claims:
            try:
                saved = command(claim)
                review.records[saved.intent.request_id] = saved
            except Exception:
                # The coordinator retains the attempted outcome for acknowledgement-only retry.
                review.receipts.append(claim)

    def dismiss_uncertain(self, identifier, *, inspected):
        """Retire an inspected review without changing jobs, receipts or scene data."""
        _main_thread()
        review = self._reviews.get(identifier)
        if review is None or review.phase != "UNCERTAIN":
            raise ValueError("Dismiss only an uncertain Film shot review")
        if inspected is not True:
            raise ValueError("Confirm inspection of the scene and saved jobs first")
        if review.receipts:
            raise ValueError("Save the known Film application receipts before dismissal")
        review.phase = "DISCARDED"
        review.completions.clear()
        return self.status(identifier)

    def approve(self, identifier):
        _main_thread()
        review = self._reviews.get(identifier)
        if review is None or review.phase != "READY":
            raise ValueError("Prepare and approve a fresh ready Film shot review")
        self._check(review)
        film_scene._main_thread()
        if self._sources(review) != review.sources:
            raise ValueError("Film hero outputs changed; inspect them again")
        heroes, groups = {}, {}
        for source in review.sources:
            request_id = source.record.intent.request_id
            completion = review.completions.get(request_id)
            if (
                completion is None
                or self.session._issued.get(id(completion)) is not completion
                or completion.result.record != source.record
            ):
                raise ValueError("Use this session's unconsumed Film verification")
            verified = completion.result
            pairs = list(zip(verified.record.results, verified.paths, strict=True))
            path = next(path for item, path in pairs if item == source.result)
            film_scene.model_application._read(source.result, path, static_only=False)
            heroes[source.hero_id] = film_scene.HeroSource(source.result, path)
            groups.setdefault(request_id, set()).add(source.result.asset.asset_id)
        # Consume the whole review before any durable claim or Blender mutation.
        review.phase = "BUILDING"
        for completion in review.completions.values():
            del self.session._issued[id(completion)]
        claims = []
        try:
            for request_id, assets in groups.items():
                verified = review.completions[request_id].result
                claims.append(
                    self.session._claim_saved_application(
                        verified, review.origin, "model", tuple(sorted(assets))
                    )
                )
        except Exception:
            review.unknown = True
            self._finish_claims(review, claims, success=False)
            review.phase, review.error = (
                "UNCERTAIN",
                "Film claim needs saved-job inspection; no scene was built",
            )
            review.completions.clear()
            return self.status(identifier)
        review.completions.clear()
        before = film_scene._snapshot()
        try:
            self._check(review)
            review.application = film_scene.build_shot(
                json.loads(review.binding[1]),
                production_id=review.binding[0],
                shot_id=review.shot_id,
                heroes=heroes,
            )
        except Exception:
            if film_scene._snapshot() == before and bpy.context.scene == review.scene:
                self._finish_claims(review, claims, success=False)
                review.phase = "UNCERTAIN" if review.receipts else "ERROR"
                review.error = "Film build failed and rolled back; inspect saved jobs"
            else:
                review.unknown = True
                review.phase, review.error = (
                    "UNCERTAIN",
                    "Film cleanup needs inspection; do not build again",
                )
            return self.status(identifier)
        self._finish_claims(review, claims, success=True)
        review.phase = "UNCERTAIN" if review.receipts else "BUILT"
        review.error = (
            "Film receipt needs recovery; the shot already exists" if review.receipts else ""
        )
        return self.status(identifier)

    def retry_receipts(self, identifier):
        """Persist only already attempted outcomes; never invoke the scene builder."""
        _main_thread()
        review = self._reviews.get(identifier)
        if review is None or review.phase != "UNCERTAIN" or not review.receipts:
            raise ValueError("No known Film application receipts are available to retry")
        for claim in tuple(review.receipts):
            try:
                saved = self.session._coordinator.retry_application_receipt(claim)
            except Exception:
                continue
            review.records[saved.intent.request_id] = saved
            review.receipts.remove(claim)
        if not review.receipts and not review.unknown:
            review.phase = "BUILT" if review.application is not None else "ERROR"
            review.error = "" if review.application is not None else "Film build rolled back"
        return self.status(identifier)

    def close(self):
        _main_thread()
        self._reviews.clear()
