# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Main-thread model generation commands shared by UI and local MCP."""

import json
import threading
import time
import uuid
from dataclasses import dataclass, field

import bpy

from ..core.api.catalog import GENERATION_LANES, LANE_KIND
from ..core.api.errors import ScenarioError
from ..core.jobs.records import JobRecord
from ..core.jobs.store import JobOrigin, JobState, StoredJob
from .job_session import ImageResultUncertain, MediaResultUncertain, ModelResultUncertain
from .media_application import MEDIA_TYPES
from .model_application import MODEL_MEDIA_TYPE


def _snapshot(body):
    return json.dumps(body, sort_keys=True, separators=(",", ":"), allow_nan=False)


@dataclass
class ModelQuote:
    identifier: str
    model_id: str
    scene: object = field(repr=False)
    inputs: str = field(repr=False)
    task: object = field(repr=False)
    lane: str = "image"
    quote: object = field(default=None, repr=False)
    used: bool = False


@dataclass(frozen=True)
class ImageApplicationApproval:
    identifier: str
    record: StoredJob
    destination: JobOrigin
    scene_name: str


@dataclass(frozen=True)
class MediaApplicationApproval:
    identifier: str
    record: StoredJob
    destination: JobOrigin
    scene_name: str
    asset_id: str
    frame: int
    kind: str


@dataclass(frozen=True)
class ModelApplicationApproval:
    identifier: str
    record: StoredJob
    destination: JobOrigin
    scene_name: str
    asset_id: str
    cursor: tuple
    kind: str = "model"


class ModelJobs:
    """Own ephemeral quotes and display projections, never another job engine."""

    def __init__(self, session, store, *, online=lambda: True):
        self.session = session
        self.store = store
        self.quotes = {}
        self.submissions = {}
        self.views = {}
        self._online = online
        self._commands = {}
        self._next_poll = {}
        self._paused = set()
        self._images = {}
        self._receipts = {}
        self._automatic_application = set()
        self._application_approvals = {}
        self._application_destinations = {}
        self._media_destinations = {}
        self._model_destinations = {}
        self._models = {}

    def quote(self, scene, model_id, body, *, lane="image"):
        if lane not in GENERATION_LANES:
            raise ScenarioError(0, "Choose a supported generation lane")
        snapshot = _snapshot(body)
        if scene == bpy.context.scene:
            # Operators flush pending dependency updates before execute(). Do
            # that before capturing the quote's revision, not at paid dispatch.
            bpy.context.view_layer.update()
        if len(self.quotes) >= 128:
            for key, old in tuple(self.quotes.items()):
                if old.used and old.task.done():
                    self.session.drain(task=old.task)
                    del self.quotes[key]
                    break
            else:
                raise ScenarioError(
                    0, "Too many retained estimates; use an existing quote before requesting more"
                )
        origin = self.session.capture(scene)
        task = self.session.quote_model(model_id, json.loads(snapshot), origin=origin)
        quote = ModelQuote(uuid.uuid4().hex, model_id, scene, snapshot, task, lane=lane)
        self.quotes[quote.identifier] = quote
        return quote

    def finish_quote(self, ticket):
        if self.quotes.get(ticket.identifier) is not ticket or not self.session.active:
            raise ScenarioError(0, "The estimate context changed; estimate again")
        if ticket.quote is None:
            completions = self.session.drain(task=ticket.task)
            if not completions:
                raise ScenarioError(0, "The estimate is still running")
            ticket.quote = self.session.deliver(completions[0], lambda value, *_: value)
        return ticket.quote.estimate

    def require_quote(self, quote_id):
        ticket = self.quotes.get(quote_id) if isinstance(quote_id, str) else None
        if ticket is None or ticket.used:
            raise ScenarioError(0, "Use a fresh, unsubmitted estimate; inspect existing jobs first")
        return ticket

    def submit(self, quote_id, scene, model_id, body, *, approved_cost, meta=None, lane="image"):
        ticket = self.require_quote(quote_id)
        estimate = self.finish_quote(ticket)
        if (
            ticket.scene != scene
            or ticket.lane != lane
            or ticket.model_id != model_id
            or ticket.inputs != _snapshot(body)
            or approved_cost != str(estimate.cost)
        ):
            raise ScenarioError(0, "The request or approved cost changed; estimate again")
        # Consumption precedes persistence: an error may occur after a committed
        # write. A second click must never prepare another intent from this quote.
        ticket.used = True
        prepared = self.session.prepare_quote(ticket.quote)
        view = JobRecord(
            local_id=prepared.intent.request_id,
            lane=lane,
            kind=LANE_KIND[lane],
            model_id=model_id,
            body=estimate.payload,
            status="prepared",
            cu_cost=float(estimate.cost),
            created_at=time.time(),
            meta=dict(meta or {}),
        )
        self.views[view.local_id] = view
        view.meta["shared_job"] = True
        if lane == "image":
            self._automatic_application.add(view.local_id)
        try:
            task = self.session.submit(
                prepared, operation="model", target_id=model_id, payload=estimate.payload
            )
        except Exception:
            view.error = "Submission could not be queued; inspect the saved job before continuing"
            raise
        self.submissions[view.local_id] = task
        return view

    def poll(self):
        """Advance owned jobs through existing commands; never replay paid work."""
        if not self.session.active:
            return
        for request_id, task in tuple(self.submissions.items()):
            if task.done():
                outcomes = self.session.drain(task=task)
                if outcomes and outcomes[0].error is not None:
                    self.views[
                        request_id
                    ].error = "Submission did not complete; inspect the saved job before continuing"
                    self._paused.add(request_id)
                del self.submissions[request_id]
        for request_id, (command, task) in tuple(self._commands.items()):
            if not task.done():
                continue
            del self._commands[request_id]
            destination = self._application_destinations.pop(request_id, None)
            media = self._media_destinations.pop(request_id, None)
            model = self._model_destinations.pop(request_id, None)
            try:
                completions = self.session.drain(task=task)
                if not completions:
                    raise RuntimeError("Missing owned result completion")
                completion = completions[0]
                if completion.error is not None:
                    raise completion.error
                if command == "verify_model":
                    applied = self.session.apply_recovered_model(
                        completion,
                        destination=model.destination,
                        asset_id=model.asset_id,
                        cursor=model.cursor,
                    )
                    self._models[request_id] = applied.application
                    self._paused.discard(request_id)
                elif command == "verify_media":
                    self.session.apply_recovered_media(
                        completion,
                        destination=media.destination,
                        asset_id=media.asset_id,
                        frame=media.frame,
                    )
                    self._paused.discard(request_id)
                elif command == "verify_results":
                    self.views[request_id].files = [str(p) for p in completion.result.paths]
                    result = (
                        self.session.apply_images(completion)
                        if destination is None
                        else self.session.apply_recovered_images(
                            completion, destination=destination
                        )
                    )
                    self._images[request_id] = result.images
                    self._paused.discard(request_id)
                self._next_poll[request_id] = time.monotonic() + 2.0
            except ModelResultUncertain as error:
                if error.application is not None:
                    self._receipts[request_id] = error
                    self._models[request_id] = error.application
                self._pause(request_id, "Model import needs receipt recovery; do not import again")
            except MediaResultUncertain as error:
                if error.application is not None:
                    self._receipts[request_id] = error
                self._pause(
                    request_id, "Media insertion needs receipt recovery; do not insert again"
                )
            except ImageResultUncertain as error:
                if error.images:
                    self._receipts[request_id] = error
                self._pause(request_id, "Image import needs receipt recovery; do not import again")
            except Exception:
                self._pause(
                    request_id,
                    "Result delivery stopped; review the saved job before retrying",
                )
        for request_id, view in self.views.items():
            record = self.store.get(request_id)
            if record is None:
                raise ScenarioError(
                    0, "The saved job is unavailable; preserve storage for recovery"
                )
            view.job_id = record.remote_job_id
            view.status = {
                JobState.REMOTE: "in-progress",
                JobState.APPLIED: "success",
            }.get(record.state, record.state.value)
            view.asset_ids = [item.asset.asset_id for item in record.results]
            view.asset_types = {
                item.asset.asset_id: item.asset.media_type for item in record.results
            }
            view.meta["saved_revision"] = record.revision
            view.meta["saved_state"] = record.state.value
            view.meta["recovery_actions"] = self.actions(record)
            if record.state in (JobState.SUBMITTING, JobState.UNCERTAIN):
                view.error = "Submission outcome is not confirmed; do not submit it again"
            elif request_id not in self._paused:
                view.error = None
            if (
                request_id in self._paused
                or request_id in self.submissions
                or request_id in self._commands
            ):
                continue
            command = None
            if record.state in (JobState.REMOTE, JobState.CANCEL_REQUESTED):
                if self._online() and time.monotonic() >= self._next_poll.get(request_id, 0):
                    command = "refresh_remote"
            elif record.state == JobState.SUCCEEDED and self._online():
                command = "download_results"
            elif record.state == JobState.READY and request_id in self._automatic_application:
                command = "verify_results"
            if command:
                try:
                    task = getattr(self.session, command)(
                        request_id, expected_revision=record.revision
                    )
                    self._commands[request_id] = (command, task)
                except Exception:
                    self._pause(request_id, "Result delivery could not start; inspect saved jobs")

    def _pause(self, request_id, message):
        self._paused.add(request_id)
        self.views[request_id].error = message

    def inspect(self):
        """Attach saved display projections without resuming or applying old work."""
        for record in self.store.records():
            self._view(record)
        self.poll()
        return tuple(self.views.values())

    def _view(self, record):
        request_id = record.intent.request_id
        if request_id not in self.views:
            self.views[request_id] = JobRecord(
                local_id=request_id,
                lane="model",
                kind="model",
                model_id=record.intent.target_id,
                body={},
                cu_cost=float(record.intent.quote_cost),
                meta={"shared_job": True, "prompt": "Recovered model job"},
            )
            self._paused.add(request_id)
        return self.views[request_id]

    def actions(self, record):
        """Return available explicit controls, without changing saved state."""
        request_id = record.intent.request_id
        if request_id in self._commands or request_id in self.submissions:
            return ()
        state = record.state
        actions = []
        if state in (JobState.REMOTE, JobState.CANCEL_REQUESTED):
            actions += ["refresh", "resume"]
        elif state in (JobState.SUCCEEDED, JobState.DOWNLOAD_FAILED):
            actions.append("resume")
        elif state == JobState.DOWNLOADING:
            actions.append("recover_download")
        elif state in (JobState.READY, JobState.APPLY_FAILED) and all(
            item.asset.media_type in {"image/png", "image/exr", "image/x-exr"}
            for item in record.results
        ):
            actions.append("import_images")
        if state in (JobState.READY, JobState.APPLY_FAILED) and any(
            item.asset.media_type in MEDIA_TYPES for item in record.results
        ):
            actions.append("import_media")
        if state == JobState.REMOTE and record.intent.operation == "model":
            actions.append("cancel")
        if state in (JobState.READY, JobState.APPLY_FAILED) and any(
            item.asset.media_type == MODEL_MEDIA_TYPE for item in record.results
        ):
            actions.append("import_model")
        if request_id in self._receipts:
            actions.append("retry_receipt")
        return tuple(actions)

    def control(self, request_id, expected_revision, action):
        """Explicit recovery never reconstructs a quote or approves another import."""
        record = self.store.get(request_id)
        if (
            type(expected_revision) is not int
            or record is None
            or record.revision != expected_revision
            or action not in self.actions(record)
            or action in {"import_images", "import_media", "import_model"}
        ):
            raise ScenarioError(0, "The saved job or available action changed; inspect it again")
        view = self._view(record)
        if action == "retry_receipt":
            pending = self._receipts[request_id]
            if isinstance(pending, ModelResultUncertain):
                outcome = self.session.retry_model_receipt(pending)
                self._models[request_id] = outcome.application
            elif isinstance(pending, MediaResultUncertain):
                self.session.retry_media_receipt(pending)
            else:
                outcome = self.session.retry_image_receipt(pending)
                self._images[request_id] = outcome.images
            del self._receipts[request_id]
            self._paused.discard(request_id)
            view.error = None
            return None
        command = {
            "refresh": "refresh_remote",
            "cancel": "cancel_remote",
            "recover_download": "recover_downloads",
            "resume": "refresh_remote"
            if record.state in (JobState.REMOTE, JobState.CANCEL_REQUESTED)
            else "download_results",
        }[action]
        if command != "recover_downloads" and not self._online():
            raise ScenarioError(0, "Allow Online Access before contacting Scenario")
        task = getattr(self.session, command)(request_id, expected_revision=expected_revision)
        self._commands[request_id] = (command, task)
        view.meta["recovery_actions"] = ()
        self._automatic_application.discard(request_id)
        view.error = None
        if action in ("resume", "cancel"):
            self._paused.discard(request_id)
        else:
            self._paused.add(request_id)
        return task

    def prepare_image_application(self, request_id, expected_revision, scene):
        """Capture a reviewable destination without verification, import or network."""
        record = self.store.get(request_id)
        if (
            type(expected_revision) is not int
            or record is None
            or record.revision != expected_revision
            or "import_images" not in self.actions(record)
        ):
            raise ScenarioError(0, "The saved images changed; inspect the job again")
        if len(self._application_approvals) >= 128:
            raise ScenarioError(
                0, "Too many pending import approvals; complete or cancel one first"
            )
        if scene != bpy.context.scene:
            raise ScenarioError(0, "Select the destination scene before reviewing the import")
        bpy.context.view_layer.update()
        ticket = ImageApplicationApproval(
            uuid.uuid4().hex, record, self.session.capture(scene), scene.name
        )
        self._application_approvals[ticket.identifier] = ticket
        return ticket

    def discard_image_application(self, identifier):
        self._application_approvals.pop(identifier, None)

    def apply_saved_images(self, identifier):
        """Consume explicit approval once; verification finishes on the existing pool."""
        ticket = (
            self._application_approvals.pop(identifier, None)
            if isinstance(identifier, str)
            else None
        )
        if ticket is None or not self.session.active:
            raise ScenarioError(0, "Review and approve the saved image destination again")
        record = self.store.get(ticket.record.intent.request_id)
        if record != ticket.record or "import_images" not in self.actions(record):
            raise ScenarioError(0, "The saved images changed; inspect the job again")
        # Validate the approved destination before queuing and again immediately
        # before claiming application. Never recapture a changed scene here.
        self.session.validate_destination(ticket.destination)
        request_id = record.intent.request_id
        task = self.session.verify_results(request_id, expected_revision=record.revision)
        self._application_destinations[request_id] = ticket.destination
        self._commands[request_id] = ("verify_results", task)
        self._automatic_application.discard(request_id)
        self._paused.add(request_id)
        view = self._view(record)
        view.meta["recovery_actions"] = ()
        view.error = None
        return request_id, task

    def prepare_media_application(self, request_id, expected_revision, scene, asset_id):
        record = self.store.get(request_id)
        if (
            type(expected_revision) is not int
            or record is None
            or record.revision != expected_revision
            or "import_media" not in self.actions(record)
        ):
            raise ScenarioError(0, "The saved media changed; inspect the job again")
        selected = [
            item
            for item in record.results
            if item.asset.asset_id == asset_id and item.asset.media_type in MEDIA_TYPES
        ]
        if len(selected) != 1:
            raise ScenarioError(0, "Choose one supported saved video or sound asset")
        if len(self._application_approvals) >= 128:
            raise ScenarioError(0, "Complete or cancel an existing application review first")
        if scene != bpy.context.scene:
            raise ScenarioError(0, "Select the destination scene before reviewing insertion")
        bpy.context.view_layer.update()
        ticket = MediaApplicationApproval(
            uuid.uuid4().hex,
            record,
            self.session.capture(scene),
            scene.name,
            asset_id,
            scene.frame_current,
            MEDIA_TYPES[selected[0].asset.media_type][0],
        )
        self._application_approvals[ticket.identifier] = ticket
        return ticket

    def prepare_model_application(self, request_id, expected_revision, scene, asset_id):
        record = self.store.get(request_id)
        if (
            type(expected_revision) is not int
            or record is None
            or record.revision != expected_revision
            or "import_model" not in self.actions(record)
        ):
            raise ScenarioError(0, "The saved model changed; inspect the job again")
        selected = [
            item
            for item in record.results
            if item.asset.asset_id == asset_id and item.asset.media_type == MODEL_MEDIA_TYPE
        ]
        if len(selected) != 1:
            raise ScenarioError(0, "Choose one supported saved static GLB asset")
        if len(self._application_approvals) >= 128:
            raise ScenarioError(0, "Complete or cancel an existing application review first")
        if scene != bpy.context.scene:
            raise ScenarioError(0, "Select the destination scene before reviewing insertion")
        bpy.context.view_layer.update()
        ticket = ModelApplicationApproval(
            uuid.uuid4().hex,
            record,
            self.session.capture(scene),
            scene.name,
            asset_id,
            tuple(scene.cursor.location),
        )
        self._application_approvals[ticket.identifier] = ticket
        return ticket

    def prepare_asset_application(self, request_id, expected_revision, scene, asset_id):
        record = self.store.get(request_id)
        if record is not None and any(
            item.asset.asset_id == asset_id and item.asset.media_type == MODEL_MEDIA_TYPE
            for item in record.results
        ):
            return self.prepare_model_application(request_id, expected_revision, scene, asset_id)
        return self.prepare_media_application(request_id, expected_revision, scene, asset_id)

    def apply_saved_result(self, identifier):
        ticket = (
            self._application_approvals.get(identifier) if isinstance(identifier, str) else None
        )
        if not isinstance(ticket, (MediaApplicationApproval, ModelApplicationApproval)):
            return self.apply_saved_images(identifier)
        self._application_approvals.pop(identifier)
        if not self.session.active:
            raise ScenarioError(0, "Review the current connection and media destination again")
        record = self.store.get(ticket.record.intent.request_id)
        is_model = isinstance(ticket, ModelApplicationApproval)
        action = "import_model" if is_model else "import_media"
        if record != ticket.record or action not in self.actions(record):
            raise ScenarioError(0, "The saved result changed; inspect the job again")
        if is_model:
            self.session.validate_destination(ticket.destination, cursor=ticket.cursor)
        else:
            self.session.validate_destination(ticket.destination, frame=ticket.frame)
        request_id = record.intent.request_id
        task = self.session.verify_results(request_id, expected_revision=record.revision)
        if is_model:
            self._model_destinations[request_id] = ticket
        else:
            self._media_destinations[request_id] = ticket
        self._commands[request_id] = ("verify_model" if is_model else "verify_media", task)
        self._automatic_application.discard(request_id)
        self._paused.add(request_id)
        view = self._view(record)
        view.meta["recovery_actions"], view.error = (), None
        return request_id, task

    def wait(self, request_id, timeout, *, stopped=lambda: False):
        """Wait on an HTTP worker using only saved state; the main thread advances jobs."""
        deadline = time.monotonic() + timeout
        sleeper = threading.Event()
        while self.session.active:
            if stopped():
                raise ScenarioError(0, "The job wait stopped; generation was not cancelled")
            record = self.store.get(request_id)
            if record is None:
                raise ScenarioError(0, "Saved job is unavailable")
            if (
                request_id in self._paused
                or record.state
                in (
                    JobState.UNCERTAIN,
                    JobState.FAILED,
                    JobState.CANCELED,
                    JobState.DOWNLOAD_FAILED,
                    JobState.APPLY_FAILED,
                    JobState.APPLIED,
                )
                or (
                    record.state == JobState.READY and request_id not in self._automatic_application
                )
            ):
                return
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                return
            sleeper.wait(min(0.1, remaining))
        raise ScenarioError(0, "The job context changed while waiting; inspect saved jobs again")

    def status(self, reference):
        self.poll()
        matches = [
            record
            for record in self.store.records()
            if reference in (record.intent.request_id, record.remote_job_id)
        ]
        if len(matches) != 1:
            return None
        record = matches[0]
        return {
            "local_id": record.intent.request_id,
            "job_id": record.remote_job_id,
            "status": record.state.value,
            "revision": record.revision,
            "cu_cost": float(record.intent.quote_cost),
            "cu_cost_exact": record.intent.quote_cost,
            "kind": self.views[record.intent.request_id].kind
            if record.intent.request_id in self.views
            else "model",
            "files": list(self.views[record.intent.request_id].files)
            if record.intent.request_id in self.views
            else [],
            "results": [
                {
                    "asset_id": item.asset.asset_id,
                    "name": item.asset.name,
                    "media_type": item.asset.media_type,
                    "size": item.asset.expected_size,
                    "downloaded": item.receipt is not None,
                }
                for item in record.results
            ],
            "delivery_paused": record.intent.request_id in self._paused,
            "actions": self.actions(record),
            "error": self.views[record.intent.request_id].error
            if record.intent.request_id in self.views
            else None,
            "objects": [
                obj.name
                for obj in getattr(self._models.get(record.intent.request_id), "objects", ())
                if obj in tuple(bpy.data.objects)
            ],
            "images": [
                image.name
                for image in self._images.get(record.intent.request_id, ())
                if image in tuple(bpy.data.images)
            ],
            "note": "Saved job state; active jobs advance without repeating generation. "
            "Restarted or paused jobs require explicit recovery.",
        }
