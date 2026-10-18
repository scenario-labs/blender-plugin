# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Quote-bound Blockout plans on the application-owned SDK job session."""

import json
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path

import bpy

from ..core.api.errors import ScenarioError
from ..core.jobs.coordinator import DuplicateRequestError
from ..core.jobs.store import JobState
from ..core.jobs.upload_store import UploadState
from ..core.scene import blockout
from . import file_state

MODEL = "model_scenario-llm"
CANCELED = "Blockout request canceled; nothing was sent to Scenario"
BUSY = {"QUOTING", "SUBMITTING", "POLLING", "LISTING", "READING"}
AUTO_QUOTE_DELAY = 0.7  # seconds the design inputs stay unchanged before an automatic price
# Measured per plan in October 2026; shown as an expectation, never used to bind anything.
MINUTES = {"best": "about 3 min", "fast": "under a minute"}


def binding(scene):
    """Every input a quote depends on; the stored plan stays last (saved-plan reviews read it)."""
    props = scene.scenario_blockout
    return (
        props.prompt,
        props.refine,
        props.density,
        props.tier,
        props.image_path,
        props.image_asset_id,
        props.image_scope,
        props.plan_json,
    )


def _design_inputs(snapshot):
    """The inputs of a new design, without the refinement text and the stored plan."""
    return tuple(value for index, value in enumerate(snapshot) if index not in {1, 7})


def parse_complete_plan(text):
    return blockout.parse_complete_plan(text)


class PlanUnusable(ScenarioError):
    """The paid job finished but its answer holds no complete plan; never retried automatically."""


def unusable_reason(text):
    snippet = " ".join(str(text or "").split())[:60]
    answer = (
        f"The model's answer is not a usable plan ({snippet}...)."
        if snippet
        else ("The model returned an empty answer, not a plan.")
    )
    return answer + " The job was charged; try again or switch model."


def _model_parameters(tier):
    """Resolve the tier against the cached live Scenario LLM model list, else the fallback."""
    from . import generation

    schema = generation.schema_for(MODEL)
    if schema is None:
        return blockout.model_parameters(tier)
    model, thinking = schema.by_name("model"), schema.by_name("thinkingLevel")
    return blockout.model_parameters(
        tier,
        model.allowed_values if model is not None else None,
        thinking.allowed_values if thinking is not None else None,
    )


def _scope_key(scope):
    from .reference_form import scope_key

    return scope_key(scope)


@dataclass
class BlockoutAction:
    identifier: str
    scene: object = field(repr=False)
    action: str
    binding: tuple = field(repr=False)
    task: object = field(repr=False)
    phase: str = "QUOTING"
    quote: object = field(default=None, repr=False)
    request_id: str = ""
    cost: str = ""
    error: str = ""
    next_poll: float = 0.0
    model: str = ""
    tier: str = ""


@dataclass
class ImageUpload:
    scene: object = field(repr=False)
    path: str
    ticket: object = field(repr=False)
    error: str = ""


class BlockoutJobs:
    """Own only presentation handles; the session owns workers and durable jobs."""

    def __init__(self, session, store, *, online=lambda: True):
        from .blockout_recovery import BlockoutRecovery

        self.session, self.store, self._online = session, store, online
        self.actions = {}
        self.recovery = BlockoutRecovery(session, store)
        self.uploads = {}  # scene session UID -> the reference image upload in progress
        self._seen = None  # (scene, design inputs, first seen) for the automatic price
        self._schema_requested = False

    def current(self, scene):
        return next(
            (item for item in reversed(tuple(self.actions.values())) if item.scene == scene), None
        )

    def _binding(self, item, scene):
        if (
            not self.session.active
            or item.scene != scene
            or scene not in tuple(bpy.data.scenes)
            or binding(scene) != item.binding
        ):
            raise ScenarioError(0, "The Blockout inputs or scene changed; request a new price")
        return scene.scenario_blockout

    def _reclaim_finished(self):
        for item in tuple(self.actions.values()):
            if item.task is not None or item.phase not in {"DONE", "ERROR"}:
                continue
            if item.request_id:
                record = self.store.get(item.request_id)
                # An ERROR presentation can still guard uncertain spending.
                # Retire only confirmed finished jobs, retaining durable history.
                if record is None or record.state not in {
                    JobState.SUCCEEDED,
                    JobState.FAILED,
                    JobState.CANCELED,
                    JobState.DOWNLOAD_FAILED,
                    JobState.READY,
                    JobState.APPLY_FAILED,
                    JobState.APPLIED,
                }:
                    continue
            self.actions.pop(item.identifier)
            return

    def quote(self, scene, action):
        if action not in {"DESIGN", "REFINE"}:
            raise ScenarioError(0, "Choose Design or Refine")
        current = self.current(scene)
        if current is not None and current.phase in BUSY:
            raise ScenarioError(0, "A Blockout plan is already running")
        if current is not None and current.request_id:
            record = self.store.get(current.request_id)
            if record is not None and record.state in {JobState.SUBMITTING, JobState.UNCERTAIN}:
                raise ScenarioError(0, "Inspect the uncertain saved Blockout job before continuing")
        snapshot = binding(scene)
        prompt, refine, density, tier, image_path, image_asset, image_scope, previous = snapshot
        if image_path and not image_asset:
            raise ScenarioError(0, "Upload the reference image before requesting a price")
        if image_asset and image_scope != _scope_key(self.session.scope):
            raise ScenarioError(0, "Upload the reference image again for this connection")
        text = prompt if action == "DESIGN" else refine
        if not (text.strip() or (action == "DESIGN" and image_asset)) or not self._online():
            raise ScenarioError(
                0, "Write the requested plan or refinement and enable online access"
            )
        original = None
        if action == "REFINE":
            try:
                original = parse_complete_plan(previous)
            except (ValueError, RecursionError):
                raise ScenarioError(
                    0, "Design or recover a complete Blockout plan before refining it"
                ) from None
        instruction = blockout.instruction(
            text, density, previous=original, image=bool(image_asset)
        )
        try:
            model = _model_parameters(tier)
        except ValueError as error:
            raise ScenarioError(0, str(error)) from None
        parameters = {"instruction": instruction, "numOutputs": 1, **model}
        if image_asset:
            parameters["images"] = [image_asset]
        if current is not None:
            self.actions.pop(current.identifier)
        if len(self.actions) >= 32:
            self._reclaim_finished()
        if len(self.actions) >= 32:
            raise ScenarioError(0, "Finish an existing Blockout action first")
        if scene == bpy.context.scene:
            bpy.context.view_layer.update()
        origin = self.session.capture(scene)
        task = self.session.quote_model(MODEL, parameters, origin=origin)
        item = BlockoutAction(uuid.uuid4().hex, scene, action, snapshot, task)
        item.model, item.tier = model["model"], tier
        self.actions[item.identifier] = item
        return item

    def auto_quote(self, scene, now):
        """Price a new design once its inputs settle, so the button carries the exact cost.

        Main thread, from the maintenance pump, only while the Blockout tab is visible. A
        quote is free. It never replaces a running action, a refinement quote or a design
        whose inputs did not change, so an error or a finished plan stays on screen.
        """
        snapshot = binding(scene)
        design = _design_inputs(snapshot)
        prompt, image_path, image_asset = snapshot[0], snapshot[4], snapshot[5]
        if not (prompt.strip() or image_asset) or (image_path and not image_asset):
            self._seen = None
            return False
        seen = (scene, design)
        if self._seen is None or self._seen[:2] != seen:
            self._seen = (*seen, now)
            return False
        if now - self._seen[2] < AUTO_QUOTE_DELAY:
            return False
        current = self.current(scene)
        if current is not None and (
            current.phase in BUSY or _design_inputs(current.binding) == design
        ):
            return False
        from . import generation

        if generation.schema_for(MODEL) is None:
            # Read the live model list once so the tier picks the newest model; a failed
            # read leaves the fixed fallback, which the exact quote still checks.
            if not self._schema_requested:
                self._schema_requested = True
                generation.request_model(MODEL, mark_dirty=False)
                return False
            if generation.is_loading(MODEL):
                return False
        try:
            self.quote(scene, "DESIGN")
        except Exception:
            # An uncertain saved job, a busy session or a changed connection: wait for an
            # input change; the panel's Get price button reports the reason.
            self._seen = (*seen, float("inf"))
            return False
        return True

    def upload_image(self, scene):
        """Upload the chosen reference image once; the pump stores its asset when imported."""
        from . import runtime
        from .reference_uploads import note_chosen_file

        props = scene.scenario_blockout
        path = props.image_path
        if not path:
            raise ScenarioError(0, "Choose a reference image first")
        key = scene.session_uid
        pending = self.uploads.get(key)
        if pending is not None and not pending.error and pending.ticket.error is None:
            raise ScenarioError(0, "The reference image is already uploading")
        note_chosen_file(path)
        ticket = runtime.ensure_reference_uploads().start(
            scene, str(Path(bpy.path.abspath(path))), kind="image", external=True
        )
        self.uploads[key] = ImageUpload(scene, path, ticket)
        return ticket

    def upload_state(self, scene):
        """'', 'UPLOADING' or the reason the upload stopped, for drawing."""
        pending = self.uploads.get(scene.session_uid)
        if pending is None:
            return ""
        return pending.error or pending.ticket.error or "UPLOADING"

    def _deliver_uploads(self):
        for key, pending in tuple(self.uploads.items()):
            ticket = pending.ticket
            if pending.error or ticket.error:
                continue
            try:
                props = pending.scene.scenario_blockout
            except ReferenceError:
                self.uploads.pop(key)
                continue
            if props.image_path != pending.path:
                self.uploads.pop(key)  # another image was chosen; this upload is not used
                continue
            record = ticket.record
            if record is None or pending.scene != bpy.context.scene:
                continue
            if record.state in {UploadState.FAILED, UploadState.CANCELED, UploadState.ABANDONED}:
                pending.error = "Upload finished without an asset; inspect saved uploads"
                continue
            if record.state != UploadState.IMPORTED:
                continue
            try:
                self.session.validate_destination(record.intent.origin)
            except Exception:
                pending.error = "The scene changed; choose the reference image again"
                continue
            props.image_asset_id = record.asset_id
            props.image_scope = _scope_key(self.session.scope)
            self.uploads.pop(key)
            # Delivered by maintenance, after the upload operator has returned.
            file_state.mark_modified("Scenario Blockout reference image")

    def approve(self, identifier, scene, *, approved_cost):
        item = self.actions.get(identifier)
        if item is None or item.phase != "READY" or item.quote is None:
            raise ScenarioError(
                0, "Use a fresh Blockout quote; inspect existing jobs before continuing"
            )
        self._binding(item, scene)
        if approved_cost != item.cost or not self._online():
            raise ScenarioError(0, "Approve the unchanged exact price while online")
        item.phase, item.error = "ERROR", "Submission needs review; inspect saved jobs"
        prepared = self.session.prepare_quote(item.quote)
        item.request_id = prepared.intent.request_id
        estimate = item.quote.estimate
        item.task = self.session.submit(
            prepared,
            operation=estimate.operation,
            target_id=estimate.target_id,
            payload=estimate.payload,
        )
        item.phase, item.error = "SUBMITTING", ""
        return item

    def _completion(self, item):
        completions = self.session.drain(task=item.task)
        if not completions:
            raise ScenarioError(0, "Blockout command completion is unavailable")
        if completions[0].error is not None:
            raise completions[0].error
        return completions[0]

    def _apply_plan(self, item, result, scene, _target):
        if result.record.intent.request_id != item.request_id:
            raise ScenarioError(0, "The returned plan does not match this action")
        props = self._binding(item, scene)
        try:
            elements = parse_complete_plan(result.text)
        except (ValueError, RecursionError):
            raise PlanUnusable(0, unusable_reason(result.text)) from None
        props.plan_json = json.dumps(elements)
        # Delivered by maintenance, after the approval operator has returned.
        file_state.mark_modified("Scenario Blockout plan")
        # Geometry is a separate explicit local action, never a late worker callback.

    def poll(self):
        if not self.session.active:
            return
        self.recovery.poll()
        self._deliver_uploads()
        for item in tuple(self.actions.values()):
            if item.phase not in BUSY:
                continue
            try:
                if item.task is not None:
                    if not item.task.done():
                        continue
                    completion = self._completion(item)
                    item.task = None
                    if item.phase == "QUOTING":
                        self._binding(item, item.scene)
                        item.quote = self.session.deliver(completion, lambda value, *_: value)
                        item.cost, item.phase = str(item.quote.estimate.cost), "READY"
                        continue
                    if item.phase == "READING":
                        self.session.deliver(
                            completion,
                            lambda result, scene, target, item=item: self._apply_plan(
                                item, result, scene, target
                            ),
                        )
                        item.phase = "DONE"
                        continue
                    if item.phase == "LISTING":
                        record = completion.result
                        if (
                            len(record.results) != 1
                            or record.results[0].asset.media_type != "text/plain"
                        ):
                            raise ScenarioError(0, "Choose a single plain-text Blockout result")
                        item.task = self.session.read_model_text(
                            item.request_id,
                            expected_revision=record.revision,
                            asset_id=record.results[0].asset.asset_id,
                        )
                        item.phase = "READING"
                        continue
                    if item.phase == "POLLING":
                        item.next_poll = time.monotonic() + 2
                record = self.store.get(item.request_id)
                if record is None:
                    raise ScenarioError(0, "The saved Blockout job is unavailable")
                if record.state == JobState.REMOTE:
                    item.phase = "POLLING"
                    if time.monotonic() >= item.next_poll and self._online():
                        # A periodic poll reads once: SDK read retries would hold
                        # one of the shared job workers for minutes in an outage.
                        item.task = self.session.refresh_remote(
                            item.request_id, expected_revision=record.revision, automatic=True
                        )
                elif record.state == JobState.SUCCEEDED:
                    if self._online():
                        item.phase = "LISTING"
                        item.task = self.session.load_results(
                            item.request_id, expected_revision=record.revision
                        )
                else:
                    raise ScenarioError(
                        0, "Inspect the saved Blockout job; do not repeat an uncertain submission"
                    )
            except Exception as error:
                item.task, item.phase = None, "ERROR"
                item.error = (
                    error.reason
                    if isinstance(error, PlanUnusable)
                    else self._stopped(item.request_id)
                    if item.request_id
                    else str(error)
                    if isinstance(error, DuplicateRequestError)
                    else "Blockout price unavailable or inputs changed; request a new price"
                )

    def _stopped(self, request_id):
        # Local cancellation makes a queued submission fail its stored-state
        # check before dispatch; a remote job ID means Scenario saw the request.
        try:
            record = self.store.get(request_id)
        except Exception:
            record = None
        if record is not None and record.state == JobState.CANCELED and not record.remote_job_id:
            return CANCELED
        return "Blockout stopped; inspect the saved job"
