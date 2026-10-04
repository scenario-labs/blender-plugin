# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Explicit, bounded saved-plan reads and local destination approvals."""

import json
import uuid
from dataclasses import dataclass, field

from ..core.api.errors import ScenarioError
from ..core.jobs.store import JobState
from .blockout_jobs import MODEL, binding, parse_complete_plan

READABLE = {
    JobState.SUCCEEDED,
    JobState.DOWNLOAD_FAILED,
    JobState.READY,
    JobState.APPLY_FAILED,
    JobState.APPLIED,
}


def available(record):
    return (
        record.intent.operation == "model"
        and record.intent.target_id == MODEL
        and record.state in READABLE
        and record.remote_job_id is not None
    )


@dataclass
class PlanReview:
    identifier: str
    request_id: str
    revision: int
    scene: object = field(repr=False)
    destination: object = field(repr=False)
    binding: tuple = field(repr=False)
    task: object = field(repr=False)
    phase: str
    plan: str = field(default="", repr=False)
    elements: int = 0
    groups: int = 0
    error: str = ""


class BlockoutRecovery:
    """Keep text in memory; reuse the selected session for all service work."""

    def __init__(self, session, store):
        self.session, self.store = session, store
        self.reviews = {}

    def current(self, request_id, scene):
        for review in reversed(tuple(self.reviews.values())):
            try:
                # Reading the name rejects invalid wrappers even if equality
                # itself does not raise after deletion or Undo.
                if review.request_id == request_id and review.scene.name and review.scene == scene:
                    return review
            except ReferenceError:
                continue
        return None

    def _record(self, request_id, revision):
        if not self.session.active:
            raise ScenarioError(0, "The saved-plan context changed")
        record = self.store.get(request_id)
        if (
            type(revision) is not int
            or record is None
            or record.revision != revision
            or not available(record)
        ):
            raise ScenarioError(0, "The saved plan changed; inspect saved jobs again")
        return record

    def _destination(self, review):
        self.session.validate_destination(review.destination)
        if binding(review.scene) != review.binding:
            raise ScenarioError(0, "The destination plan or inputs changed; review again")

    def _read(self, record):
        if len(record.results) != 1 or record.results[0].asset.media_type != "text/plain":
            raise ScenarioError(0, "Choose a saved job with one complete plain-text plan")
        return self.session.read_model_text(
            record.intent.request_id,
            expected_revision=record.revision,
            asset_id=record.results[0].asset.asset_id,
        )

    def prepare(self, request_id, revision, scene):
        record = self._record(request_id, revision)
        old = self.current(request_id, scene)
        if old is not None:
            if old.task is not None:
                raise ScenarioError(0, "The saved plan is already being read")
            self.discard(old.identifier)
        if len(self.reviews) >= 16:
            raise ScenarioError(0, "Finish or discard an existing saved-plan review")
        # Finish pending dependency changes before capturing this new destination.
        import bpy

        if scene != bpy.context.scene:
            raise ScenarioError(0, "Select the destination scene before reviewing")
        bpy.context.view_layer.update()
        destination, snapshot = self.session.capture(scene), binding(scene)
        listing = not record.results
        task = (
            self.session.load_results(request_id, expected_revision=revision)
            if listing
            else self._read(record)
        )
        review = PlanReview(
            uuid.uuid4().hex,
            request_id,
            revision,
            scene,
            destination,
            snapshot,
            task,
            "LISTING" if listing else "READING",
        )
        self.reviews[review.identifier] = review
        return review

    def poll(self):
        for review in tuple(self.reviews.values()):
            if review.task is None or not review.task.done():
                continue
            try:
                outcomes = self.session.drain(task=review.task)
                review.task = None
                if not outcomes or outcomes[0].error is not None:
                    raise ScenarioError(0, "The complete saved plan could not be read")
                self._destination(review)
                result = outcomes[0].result
                record = result if review.phase == "LISTING" else result.record
                self._record(review.request_id, record.revision)
                review.revision = record.revision
                if review.phase == "LISTING":
                    review.task, review.phase = self._read(record), "READING"
                    continue
                if record.intent.request_id != review.request_id:
                    raise ScenarioError(0, "The saved plan does not match this review")
                elements = parse_complete_plan(result.text)
                review.plan = json.dumps(elements)
                review.elements = len(elements)
                review.groups = len({element["group"] for element in elements})
                review.phase = "READY"
            except Exception:
                review.task, review.phase = None, "ERROR"
                review.error = "Could not review this plan; inspect the saved job and destination"

    def status(self, identifier):
        review = self.reviews.get(identifier)
        if review is None:
            raise ScenarioError(0, "Use a current saved-plan review")
        try:
            scene_name = review.scene.name
            phase, error = review.phase, review.error
        except ReferenceError:
            scene_name, phase = "Unavailable", "ERROR"
            error = "The destination scene was removed; read the plan for a new destination"
        return {
            "review_id": review.identifier,
            "state": phase.lower(),
            "scene": scene_name,
            "elements": review.elements,
            "groups": review.groups,
            "replaces_plan": bool(review.binding[-1]),
            "error": error,
        }

    def discard(self, identifier):
        review = self.reviews.get(identifier)
        if review is not None and review.task is None:
            self.reviews.pop(identifier)

    def apply(self, identifier):
        review = self.reviews.get(identifier)
        if review is None or review.phase != "READY":
            raise ScenarioError(0, "Read and review the complete saved plan before using it")
        self._record(review.request_id, review.revision)
        self._destination(review)
        # Consume before mutating. A repeated approval never reapplies an old plan.
        self.reviews.pop(identifier)
        review.scene.scenario_blockout.plan_json = review.plan
        return {"scene": review.scene.name, "elements": review.elements, "geometry_changed": False}
