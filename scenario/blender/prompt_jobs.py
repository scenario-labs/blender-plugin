# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Main-thread prompt preparation and approval on the existing JobSession pool."""

import time
import uuid
from dataclasses import dataclass, field

import bpy

from ..core.api.errors import ScenarioError
from ..core.jobs.store import JobState
from . import file_state

LABELS = {"GENERATE": "New prompt", "REWRITE": "Rewrite", "TRANSLATE": "Translate"}
BUSY = {"QUOTING", "SUBMITTING", "POLLING", "READING"}


@dataclass
class PromptAction:
    identifier: str
    scene: object = field(repr=False)
    lane: str
    action: str
    original_text: str = field(repr=False)
    model_id: str
    task: object = field(repr=False)
    preparation_key: str = field(default="", repr=False)
    phase: str = "QUOTING"
    quote: object = field(default=None, repr=False)
    request_id: str = ""
    cost: str = ""
    error: str = ""
    next_poll: float = 0.0
    # The submission's outcome was unconfirmed when this action stopped; once
    # the user links its cloud job and it finishes, the action reads its text.
    unconfirmed: bool = False


class PromptJobs:
    """Keep UI handles only; jobs, workers and persistence belong to the session."""

    def __init__(self, session, store, *, online=lambda: True):
        self.session, self.store, self._online = session, store, online
        self.actions = {}

    def current(self, scene, lane):
        return next(
            (
                item
                for item in reversed(tuple(self.actions.values()))
                if item.scene == scene and item.lane == lane
            ),
            None,
        )

    def _binding(self, item, scene):
        if not self.session.active or item.scene != scene or scene not in tuple(bpy.data.scenes):
            raise ScenarioError(0, "The prompt context changed; request a new price")
        lane = scene.scenario.lane_state(item.lane)
        if lane is None or lane.prompt != item.original_text or lane.model_id != item.model_id:
            raise ScenarioError(0, "The prompt or model changed; request a new price")
        if item.preparation_key:
            from .render_prompt_jobs import parameters

            _, key = parameters(scene, item.lane)
            if key != item.preparation_key:
                raise ScenarioError(0, "The render references changed; request a new prompt price")
        return lane

    def quote(self, scene, lane, action):
        if action not in LABELS:
            raise ScenarioError(0, "Choose a supported prompt action")
        current = self.current(scene, lane)
        if current is not None and current.phase in BUSY:
            raise ScenarioError(0, "A prompt action is already running for this field")
        if current is not None and current.request_id:
            saved = self.store.get(current.request_id)
            if saved is not None and saved.state in {JobState.SUBMITTING, JobState.UNCERTAIN}:
                raise ScenarioError(
                    0,
                    "Find the unconfirmed prompt job's cloud job in Jobs, or mark it "
                    "reviewed there, before another generation",
                )
        target = scene.scenario.lane_state(lane)
        if target is None:
            raise ScenarioError(0, "Choose a valid prompt field")
        prompt, model_id = target.prompt, target.model_id
        if action in {"REWRITE", "TRANSLATE"} and not prompt.strip():
            raise ScenarioError(0, "Write a prompt first")
        if not self._online():
            raise ScenarioError(0, "Online access is disabled")
        if current is not None and current.phase not in BUSY:
            self.actions.pop(current.identifier)
        if len(self.actions) >= 128:
            raise ScenarioError(
                0, "Too many retained prompt actions; finish an existing action first"
            )
        if scene == bpy.context.scene:
            bpy.context.view_layer.update()
        origin = self.session.capture(scene)
        preparation_key = ""
        if action == "TRANSLATE":
            task = self.session.quote_translate({"prompt": prompt}, origin=origin)
        elif lane in {"render_image", "render_video"}:
            from .render_prompt_jobs import parameters as render_parameters

            parameters, preparation_key = render_parameters(scene, lane)
            task = self.session.quote_prompt(parameters, origin=origin)
        else:
            has_model = model_id not in {"", "NONE"}
            parameters = {
                "mode": "contextual-v2"
                if has_model
                else ("completion" if action == "REWRITE" else "structured"),
                "numResults": 1,
            }
            if has_model:
                parameters["modelId"] = model_id
            if prompt.strip():
                parameters["prompt"] = prompt
            task = self.session.quote_prompt(parameters, origin=origin)
        item = PromptAction(uuid.uuid4().hex, scene, lane, action, prompt, model_id, task)
        item.preparation_key = preparation_key
        self.actions[item.identifier] = item
        return item

    def approve(self, identifier, scene, *, approved_cost):
        item = self.actions.get(identifier)
        if item is None or item.phase != "READY" or item.quote is None:
            raise ScenarioError(
                0, "Use a fresh prompt price; inspect any existing job before continuing"
            )
        self._binding(item, scene)
        if approved_cost != item.cost or not self._online():
            raise ScenarioError(0, "Approve the unchanged exact price while online")
        # Consume the displayed approval before any possibly uncertain persistence.
        item.phase = "ERROR"
        item.error = "Submission needs review; inspect the saved job before continuing"
        from .props import mark_estimate_dirty

        mark_estimate_dirty(scene.scenario.lane_state(item.lane))
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
        outcomes = self.session.drain(task=item.task)
        if not outcomes:
            raise ScenarioError(0, "The prompt command completion is unavailable")
        if outcomes[0].error is not None:
            raise outcomes[0].error
        return outcomes[0]

    def _apply(self, item, result, scene, _target):
        if result.record.intent.request_id != item.request_id or len(result.prompts) != 1:
            raise ScenarioError(0, "The returned prompt does not match this action")
        lane = self._binding(item, scene)
        lane.prompt = result.prompts[0]
        # Delivered by maintenance, after the approval operator has returned.
        file_state.mark_modified("Scenario prompt")

    def _resume_linked(self, item):
        """Read a linked job's text into the unchanged field once Scenario finishes it."""
        if item.phase != "ERROR" or not item.unconfirmed or item.task is not None:
            return
        try:
            record = self.store.get(item.request_id)
        except Exception:
            return
        if record is None or record.state in {JobState.SUBMITTING, JobState.UNCERTAIN}:
            return
        if record.state == JobState.REMOTE:
            item.error = "Linked cloud job is still running; its text follows when it finishes"
            return
        if record.state == JobState.SUCCEEDED and not self._online():
            # Keep waiting: the text is read once Online Access is allowed again.
            item.error = "Linked cloud job finished; allow Online Access to read its text"
            return
        item.unconfirmed = False
        if record.state != JobState.SUCCEEDED:
            item.error = "Prompt action stopped; inspect the saved job"
            return
        try:
            self._binding(item, item.scene)
            item.task = self.session.read_prompt_results(
                item.request_id, expected_revision=record.revision
            )
        except Exception:
            item.error = "The prompt changed; read the linked job's text from Jobs"
            return
        item.phase, item.error = "READING", ""

    def poll(self):
        if not self.session.active:
            return
        for item in tuple(self.actions.values()):
            if item.request_id:
                self._resume_linked(item)
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
                        item.cost = str(item.quote.estimate.cost)
                        item.phase = "READY"
                        continue
                    if item.phase == "READING":
                        self.session.deliver(
                            completion,
                            lambda result, scene, target, item=item: self._apply(
                                item, result, scene, target
                            ),
                        )
                        item.phase = "DONE"
                        continue
                    if item.phase == "POLLING":
                        item.next_poll = time.monotonic() + 2.0
                record = self.store.get(item.request_id)
                if record is None:
                    raise ScenarioError(0, "The saved prompt job is unavailable")
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
                        item.phase = "READING"
                        item.task = self.session.read_prompt_results(
                            item.request_id, expected_revision=record.revision
                        )
                else:
                    raise ScenarioError(
                        0, "The prompt job needs inspection; do not repeat an uncertain submission"
                    )
            except Exception:
                item.task = None
                item.phase = "ERROR"
                item.error = (
                    self._stopped(item.request_id)
                    if item.request_id
                    else "Prompt price unavailable or inputs changed; request a new price"
                )
                if item.request_id:
                    try:
                        saved = self.store.get(item.request_id)
                    except Exception:
                        saved = None
                    item.unconfirmed = saved is not None and saved.state in {
                        JobState.SUBMITTING,
                        JobState.UNCERTAIN,
                    }
                    if item.unconfirmed:
                        item.error = (
                            "Submission unconfirmed; find its cloud job in Jobs, "
                            "never send it again"
                        )

    def _stopped(self, request_id):
        # Local cancellation makes a queued submission fail its stored-state
        # check before dispatch; a remote job ID means Scenario saw the request.
        try:
            record = self.store.get(request_id)
        except Exception:
            record = None
        if record is not None and record.state == JobState.CANCELED and not record.remote_job_id:
            return "Prompt request canceled; nothing was sent to Scenario"
        return "Prompt action stopped; inspect the saved job"
