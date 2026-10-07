# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Main-thread model generation commands shared by UI and local MCP."""

import json
import threading
import time
import uuid
from dataclasses import asdict, dataclass, field, replace

import bpy
from mathutils import Matrix

from ..core.api.catalog import GENERATION_LANES, LANE_KIND
from ..core.api.errors import ScenarioError
from ..core.jobs.records import JobRecord
from ..core.jobs.store import JobOrigin, JobState, LocalApplicationState, StoredJob, _identity
from .job_session import (
    ImageResultUncertain,
    MaterialResultUncertain,
    MediaResultUncertain,
    ModelResultUncertain,
    WorldResultUncertain,
)
from .material_application import MaterialApplicationError, capture_target, selected_maps
from .material_application import validate_target as validate_material_target
from .media_application import MEDIA_TYPES
from .mesh_application import MeshApplicationError
from .mesh_application import capture_target as capture_mesh_target
from .mesh_application import validate_target as validate_mesh_target
from .mesh_result_application import MeshEditApplication, MeshResultApplicationError
from .mesh_result_application import validate_request as validate_mesh_request
from .model_application import MODEL_MEDIA_TYPE
from .model_application import validate_destination as validate_model_destination
from .world_application import PanoramaError, WorldApplicationError


def _snapshot(body):
    return json.dumps(body, sort_keys=True, separators=(",", ":"), allow_nan=False)


def _remember(cache, request_id, values, collection):
    """Retain live session outputs across reuse and deduplicate receipt retries."""
    live = tuple(collection)
    cache[request_id] = tuple(
        dict.fromkeys(value for value in (*cache.get(request_id, ()), *values) if value in live)
    )


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


@dataclass
class CloudRecovery:
    job_id: str
    model_id: str
    task: object = field(repr=False)
    owner: object = field(repr=False)
    record: StoredJob | None = None
    error: str = ""
    pending: bool = True


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


@dataclass(frozen=True)
class WorldApplicationApproval:
    identifier: str
    record: StoredJob
    destination: JobOrigin
    scene_name: str
    scene: object = field(repr=False)
    previous: object = field(repr=False)
    asset_id: str
    restore: bool = False
    kind: str = "world"


@dataclass(frozen=True)
class MaterialApplicationApproval:
    identifier: str
    record: StoredJob
    destination: JobOrigin
    scene_name: str
    target_name: str
    target: object = field(repr=False)
    roles: tuple
    kind: str = "material"


@dataclass(frozen=True)
class MeshApplicationApproval:
    identifier: str
    record: StoredJob
    destination: JobOrigin
    scene_name: str
    target_name: str
    asset_id: str
    target: object = field(repr=False)
    policy: str
    placement: str
    mapping: tuple
    keep_original: bool
    original_source: bool = False
    kind: str = "mesh_edit"


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
        self._objects = {}
        self._world_destinations = {}
        self._worlds = {}
        self._material_destinations = {}
        self._materials = {}
        self._mesh_destinations = {}
        self._mesh_edits = {}
        self.cloud_reads = {}
        self._cloud_read_owner = object()

    def recover_cloud(self, job_id, model_id, scene):
        """Save one selected cloud job for explicit recovery, never automatic import."""
        _identity(job_id)
        _identity(model_id)
        self._poll_cloud_reads()
        existing = self.cloud_reads.get(job_id)
        if existing is not None and existing.pending:
            if existing.model_id != model_id:
                raise ScenarioError(0, "This cloud job already has a different model read pending")
            return existing
        if len(self.cloud_reads) >= 16 and job_id not in self.cloud_reads:
            for key, item in tuple(self.cloud_reads.items()):
                if not item.pending:
                    del self.cloud_reads[key]
                    break
            else:
                raise ScenarioError(0, "Wait for a cloud recovery read to finish")
        task = self.session.adopt_cloud_job(job_id, expected_model_id=model_id, scene=scene)
        item = CloudRecovery(job_id, model_id, task, self._cloud_read_owner)
        self.cloud_reads[job_id] = item
        return item

    def _poll_cloud_reads(self):
        if not self.session.active:
            return
        for item in self.cloud_reads.values():
            if not item.pending or not item.task.done():
                continue
            item.pending = False
            try:
                completions = self.session.drain(task=item.task)
                if not completions:
                    raise RuntimeError("Missing cloud read completion")
                record = self.session.deliver_cloud_read(completions[0])
                item.record = record
                self._view(record)
            except Exception:
                item.error = "Could not read this cloud job; inspect saved jobs or retry the read"

    def finish_cloud(self, item):
        # Completed results can leave the bounded UI cache while a deferred MCP
        # caller still owns its handle. Cache membership is not request ownership.
        if (
            not self.session.active
            or not isinstance(item, CloudRecovery)
            or item.owner is not self._cloud_read_owner
        ):
            raise ScenarioError(0, "The cloud recovery context changed; inspect saved jobs")
        self._poll_cloud_reads()
        if item.pending or item.error:
            raise ScenarioError(0, item.error or "The cloud job read is still running")
        return item.record

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
        return self._submit_quote(ticket.quote, lane=lane, kind=LANE_KIND[lane], meta=meta)

    def submit_film(self, quote, *, approved_cost):
        """Dispatch an owned Film approval through the ordinary saved-job lifecycle."""
        if quote.film_task is None or approved_cost != str(quote.estimate.cost):
            raise ScenarioError(0, "Approve a Film task's unchanged exact price")
        return self._submit_quote(quote, lane="film", kind="film")

    def _submit_quote(self, quote, *, lane, kind, meta=None):
        estimate = quote.estimate
        model_id = estimate.target_id
        prepared = self.session.prepare_quote(quote)
        view = JobRecord(
            local_id=prepared.intent.request_id,
            lane=lane,
            kind=kind,
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
        self._prune_worlds()
        if not self.session.active:
            return
        self._poll_cloud_reads()
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
            world = self._world_destinations.pop(request_id, None)
            material = self._material_destinations.pop(request_id, None)
            mesh = self._mesh_destinations.pop(request_id, None)
            try:
                completions = self.session.drain(task=task)
                if not completions:
                    raise RuntimeError("Missing owned result completion")
                completion = completions[0]
                if completion.error is not None:
                    raise completion.error
                if command == "verify_mesh_edit":
                    applied = self.session.apply_recovered_mesh(
                        completion,
                        destination=mesh.destination,
                        asset_id=mesh.asset_id,
                        target=mesh.target,
                        policy=mesh.policy,
                        result_to_source=mesh.mapping,
                        keep_original=mesh.keep_original,
                    )
                    self._remember_model_application(request_id, applied.application)
                    self._paused.discard(request_id)
                elif command == "verify_material":
                    applied = self.session.apply_recovered_material(
                        completion, destination=material.destination, target=material.target
                    )
                    _remember(
                        self._materials,
                        request_id,
                        (applied.application.material,),
                        bpy.data.materials,
                    )
                    self._paused.discard(request_id)
                elif command == "verify_world":
                    self._validate_world(world)
                    applied = self.session.apply_recovered_world(
                        completion, destination=world.destination, asset_id=world.asset_id
                    )
                    self._remember_world(request_id, world.destination, applied.application)
                    self._paused.discard(request_id)
                elif command == "verify_model":
                    applied = self.session.apply_recovered_model(
                        completion,
                        destination=model.destination,
                        asset_id=model.asset_id,
                        cursor=model.cursor,
                    )
                    _remember(
                        self._objects, request_id, applied.application.objects, bpy.data.objects
                    )
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
                    _remember(self._images, request_id, result.images, bpy.data.images)
                    self._paused.discard(request_id)
                self._next_poll[request_id] = time.monotonic() + 2.0
            except MaterialResultUncertain as error:
                if error.application is not None:
                    self._receipts[request_id] = error
                    _remember(
                        self._materials,
                        request_id,
                        (error.application.material,),
                        bpy.data.materials,
                    )
                self._pause(request_id, "Material assignment needs recovery; do not apply again")
            except MaterialApplicationError:
                self._pause(
                    request_id,
                    "Material application stopped; inspect saved maps and mesh destination",
                )
            except WorldResultUncertain as error:
                if error.application is not None:
                    self._receipts[request_id] = error
                    self._remember_world(request_id, world.destination, error.application)
                self._pause(
                    request_id, "World assignment needs receipt recovery; do not apply again"
                )
            except (PanoramaError, WorldApplicationError):
                self._pause(
                    request_id,
                    "World import needs a supported, unchanged 2:1 PNG/EXR panorama; inspect the saved result",
                )
            except ModelResultUncertain as error:
                if error.application is not None:
                    self._receipts[request_id] = error
                    self._remember_model_application(request_id, error.application)
                self._pause(
                    request_id, "Model application needs receipt recovery; do not apply again"
                )
            except (MeshApplicationError, MeshResultApplicationError):
                self._pause(
                    request_id,
                    "Mesh application stopped; inspect the saved GLB, source and edit policy",
                )
            except MediaResultUncertain as error:
                if error.application is not None:
                    self._receipts[request_id] = error
                self._pause(
                    request_id, "Media insertion needs receipt recovery; do not insert again"
                )
            except ImageResultUncertain as error:
                if error.images:
                    self._receipts[request_id] = error
                    _remember(self._images, request_id, error.images, bpy.data.images)
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
            elif any(
                item.state == LocalApplicationState.APPLYING for item in record.local_applications
            ):
                view.error = "Local application outcome is unconfirmed; inspect the scene and do not repeat it"
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
                cu_cost=float(record.intent.quote_cost)
                if record.intent.quote_cost is not None
                else None,
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
        if request_id in self._receipts:
            return ("retry_receipt",)
        if any(item.state == LocalApplicationState.APPLYING for item in record.local_applications):
            return ()
        reusable = state in (JobState.READY, JobState.APPLY_FAILED) or (
            state == JobState.APPLIED and len(record.local_applications) < 128
        )
        if record.intent.operation in {"prompt", "translate"}:
            return ("refresh",) if state == JobState.REMOTE else ()
        from .blockout_recovery import available as blockout_available

        if blockout_available(record):
            return ("recover_blockout",)
        actions = []
        if state in (JobState.REMOTE, JobState.CANCEL_REQUESTED):
            actions += ["refresh", "resume"]
        elif state in (JobState.SUCCEEDED, JobState.DOWNLOAD_FAILED):
            actions.append("resume")
        elif state == JobState.DOWNLOADING:
            actions.append("recover_download")
        elif reusable and all(
            item.asset.media_type in {"image/png", "image/exr", "image/x-exr"}
            for item in record.results
        ):
            actions.append("import_images")
        if reusable and any(item.asset.media_type in MEDIA_TYPES for item in record.results):
            actions.append("import_media")
        if state == JobState.REMOTE and record.intent.operation == "model":
            actions.append("cancel")
        if reusable and any(item.asset.media_type == MODEL_MEDIA_TYPE for item in record.results):
            actions.extend(("import_model", "apply_mesh"))
            if (
                len(record.intent.mesh_sources) == 1
                and len(record.intent.mesh_sources[0].mesh_source.objects) == 1
            ):
                actions.append("apply_mesh_source")
        if reusable and any(
            item.asset.media_type in {"image/png", "image/exr", "image/x-exr"}
            for item in record.results
        ):
            actions.append("apply_world")
        if reusable:
            try:
                selected_maps(record)
            except MaterialApplicationError:
                pass
            else:
                actions.append("apply_material")
        if state == JobState.APPLIED and any(
            self.session.has_scene(scene_id) for scene_id in self._worlds.get(request_id, {})
        ):
            actions.append("restore_world")
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
            or action
            in {
                "import_images",
                "import_media",
                "import_model",
                "apply_world",
                "restore_world",
                "apply_material",
                "apply_mesh",
                "apply_mesh_source",
                "recover_blockout",
            }
        ):
            raise ScenarioError(0, "The saved job or available action changed; inspect it again")
        view = self._view(record)
        if action == "retry_receipt":
            pending = self._receipts[request_id]
            if isinstance(pending, MaterialResultUncertain):
                outcome = self.session.retry_material_receipt(pending)
                _remember(
                    self._materials, request_id, (outcome.application.material,), bpy.data.materials
                )
            elif isinstance(pending, WorldResultUncertain):
                # The original scene handle was retained before persistence failed.
                self.session.retry_world_receipt(pending)
            elif isinstance(pending, ModelResultUncertain):
                outcome = self.session.retry_model_receipt(pending)
                self._remember_model_application(request_id, outcome.application)
            elif isinstance(pending, MediaResultUncertain):
                self.session.retry_media_receipt(pending)
            else:
                outcome = self.session.retry_image_receipt(pending)
                _remember(self._images, request_id, outcome.images, bpy.data.images)
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
            raise ScenarioError(0, "Choose one supported saved GLB asset")
        if len(self._application_approvals) >= 128:
            raise ScenarioError(0, "Complete or cancel an existing application review first")
        if scene != bpy.context.scene:
            raise ScenarioError(0, "Select the destination scene before reviewing insertion")
        bpy.context.view_layer.update()
        validate_model_destination(scene, tuple(scene.cursor.location))
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

    def _remember_model_application(self, request_id, application):
        if isinstance(application, MeshEditApplication):
            previous = self._mesh_edits.get(request_id)
            if previous is None or previous[1] is not application:
                self._mesh_edits[request_id] = (self.session.history_revision, application)
            # Receipt-only retry must keep the original history revision.
        else:
            _remember(self._objects, request_id, application.objects, bpy.data.objects)

    @staticmethod
    def _mesh_options(target, policy, placement, keep_original):
        if placement not in {"WORLD", "LOCAL"}:
            raise ScenarioError(0, "Choose scene or object-local result coordinates")
        validate_mesh_target(target)
        try:
            mapping = (
                target.obj.matrix_world.inverted() if placement == "WORLD" else Matrix.Identity(4)
            )
        except ValueError:
            raise ScenarioError(0, "The target transform cannot map scene coordinates") from None
        mapping = validate_mesh_request(
            target, policy=policy, result_to_source=mapping, keep_original=keep_original
        )
        return tuple(tuple(row) for row in mapping)

    def prepare_mesh_application(
        self,
        request_id,
        expected_revision,
        scene,
        obj,
        asset_id,
        *,
        policy="REMESH",
        placement="WORLD",
        keep_original=True,
        original_source=False,
        review_placement=False,
    ):
        record = self.store.get(request_id)
        if (
            type(expected_revision) is not int
            or record is None
            or record.revision != expected_revision
            or "apply_mesh" not in self.actions(record)
            or len(self._application_approvals) >= 128
        ):
            raise ScenarioError(0, "Inspect the saved mesh and finish existing reviews first")
        if not any(
            item.asset.asset_id == asset_id and item.asset.media_type == MODEL_MEDIA_TYPE
            for item in record.results
        ):
            raise ScenarioError(0, "Choose one saved static GLB result")
        if type(original_source) is not bool:
            raise ScenarioError(0, "Choose whether to use the captured source")
        if original_source:
            if len(record.intent.mesh_sources) != 1:
                raise ScenarioError(0, "Choose a job with exactly one captured mesh input")
            target = self.session.mesh_source_target(record.intent.mesh_sources[0])
            scene, obj = target.scene, target.obj
        else:
            target = capture_mesh_target(scene, obj)
        # Native review chooses its displayed default from the resolved target,
        # which can differ from the selected object. Explicit MCP options stay strict.
        if review_placement and placement == "WORLD" and target.obj.matrix_world.determinant() <= 0:
            placement = "LOCAL"
        mapping = self._mesh_options(target, policy, placement, keep_original)
        ticket = MeshApplicationApproval(
            uuid.uuid4().hex,
            record,
            self.session.capture(scene, obj),
            scene.name,
            obj.name,
            asset_id,
            target,
            policy,
            placement,
            mapping,
            keep_original,
            original_source,
        )
        self._application_approvals[ticket.identifier] = ticket
        return ticket

    def revise_mesh_application(self, identifier, *, policy, placement, keep_original):
        """Change reviewed options without recapturing or retargeting the source."""
        ticket = self._application_approvals.get(identifier)
        if not isinstance(ticket, MeshApplicationApproval):
            raise ScenarioError(0, "Use an unconsumed mesh destination review")
        mapping = self._mesh_options(ticket.target, policy, placement, keep_original)
        self.session.validate_destination(ticket.destination)
        if self.store.get(ticket.record.intent.request_id) != ticket.record:
            raise ScenarioError(0, "The saved mesh changed; start a fresh review")
        if (policy, placement, keep_original) == (
            ticket.policy,
            ticket.placement,
            ticket.keep_original,
        ):
            return ticket
        revised = replace(
            ticket,
            identifier=uuid.uuid4().hex,
            policy=policy,
            placement=placement,
            mapping=mapping,
            keep_original=keep_original,
        )
        del self._application_approvals[identifier]
        self._application_approvals[revised.identifier] = revised
        return revised

    def _apply_saved_mesh(self, ticket):
        self._application_approvals.pop(ticket.identifier)
        record = self.store.get(ticket.record.intent.request_id)
        if record != ticket.record or "apply_mesh" not in self.actions(record):
            raise ScenarioError(0, "The saved mesh changed; inspect it again")
        validate_mesh_request(
            ticket.target,
            policy=ticket.policy,
            result_to_source=ticket.mapping,
            keep_original=ticket.keep_original,
        )
        self.session.validate_destination(ticket.destination)
        request_id = record.intent.request_id
        task = self.session.verify_results(request_id, expected_revision=record.revision)
        self._mesh_destinations[request_id] = ticket
        self._commands[request_id] = ("verify_mesh_edit", task)
        self._automatic_application.discard(request_id)
        self._paused.add(request_id)
        view = self._view(record)
        view.meta["recovery_actions"], view.error = (), None
        return request_id, task

    def prepare_material_application(self, request_id, expected_revision, scene, obj):
        record = self.store.get(request_id)
        if (
            type(expected_revision) is not int
            or record is None
            or record.revision != expected_revision
            or "apply_material" not in self.actions(record)
            or len(self._application_approvals) >= 128
        ):
            raise ScenarioError(0, "Inspect the saved material and finish existing reviews first")
        bpy.context.view_layer.update()
        target = capture_target(scene, obj)
        roles = selected_maps(record)
        ticket = MaterialApplicationApproval(
            uuid.uuid4().hex,
            record,
            self.session.capture(scene, obj),
            scene.name,
            obj.name,
            target,
            tuple(roles),
        )
        self._application_approvals[ticket.identifier] = ticket
        return ticket

    def _apply_saved_material(self, ticket):
        self._application_approvals.pop(ticket.identifier)
        record = self.store.get(ticket.record.intent.request_id)
        if record != ticket.record or "apply_material" not in self.actions(record):
            raise ScenarioError(0, "The saved material changed; inspect it again")
        self.session.validate_destination(ticket.destination)
        validate_material_target(ticket.target)
        request_id = record.intent.request_id
        task = self.session.verify_results(request_id, expected_revision=record.revision)
        self._material_destinations[request_id] = ticket
        self._commands[request_id] = ("verify_material", task)
        self._automatic_application.discard(request_id)
        self._paused.add(request_id)
        view = self._view(record)
        view.meta["recovery_actions"], view.error = (), None
        return request_id, task

    def _remember_world(self, request_id, destination, application):
        self._worlds.setdefault(request_id, {})[destination.scene_id] = application

    def _prune_worlds(self):
        for request_id, worlds in tuple(self._worlds.items()):
            for scene_id in tuple(worlds):
                if not self.session.has_scene(scene_id):
                    del worlds[scene_id]
            if not worlds:
                del self._worlds[request_id]

    def _world_application(self, request_id, destination):
        application = self._worlds.get(request_id, {}).get(destination.scene_id)
        if application is None or not self.session.has_scene(destination.scene_id):
            raise ScenarioError(0, "Select the scene whose previous World should be restored")
        return application

    def prepare_world_application(
        self, request_id, expected_revision, scene, asset_id, *, restore=False
    ):
        record = self.store.get(request_id)
        action = "restore_world" if restore else "apply_world"
        if (
            type(expected_revision) is not int
            or record is None
            or record.revision != expected_revision
            or action not in self.actions(record)
        ):
            raise ScenarioError(0, "Inspect the current saved World result again")
        if scene != bpy.context.scene or len(self._application_approvals) >= 128:
            raise ScenarioError(0, "Choose the destination and finish existing reviews first")
        bpy.context.view_layer.update()
        destination = self.session.capture(scene)
        if restore:
            self._world_application(request_id, destination)
        elif not any(
            item.asset.asset_id == asset_id
            and item.asset.media_type in {"image/png", "image/exr", "image/x-exr"}
            for item in record.results
        ):
            raise ScenarioError(0, "Choose one saved PNG or EXR panorama")
        ticket = WorldApplicationApproval(
            uuid.uuid4().hex,
            record,
            destination,
            scene.name,
            scene,
            scene.world,
            asset_id or "",
            restore,
        )
        self._application_approvals[ticket.identifier] = ticket
        return ticket

    def _validate_world(self, ticket):
        self.session.validate_destination(ticket.destination)
        if ticket.scene.world != ticket.previous:
            raise ScenarioError(0, "The scene World changed; approve its replacement again")

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
        if isinstance(ticket, MeshApplicationApproval):
            return self._apply_saved_mesh(ticket)
        if isinstance(ticket, MaterialApplicationApproval):
            return self._apply_saved_material(ticket)
        if not isinstance(
            ticket, (MediaApplicationApproval, ModelApplicationApproval, WorldApplicationApproval)
        ):
            return self.apply_saved_images(identifier)
        self._application_approvals.pop(identifier)
        if not self.session.active:
            raise ScenarioError(0, "Review the current connection and media destination again")
        record = self.store.get(ticket.record.intent.request_id)
        is_model = isinstance(ticket, ModelApplicationApproval)
        is_world = isinstance(ticket, WorldApplicationApproval)
        action = (
            ("restore_world" if ticket.restore else "apply_world")
            if is_world
            else ("import_model" if is_model else "import_media")
        )
        if record != ticket.record or action not in self.actions(record):
            raise ScenarioError(0, "The saved result changed; inspect the job again")
        if is_world:
            self._validate_world(ticket)
        elif is_model:
            self.session.validate_destination(ticket.destination, cursor=ticket.cursor)
        else:
            self.session.validate_destination(ticket.destination, frame=ticket.frame)
        request_id = record.intent.request_id
        if is_world and ticket.restore:
            self._world_application(request_id, ticket.destination).restore()
            worlds = self._worlds[request_id]
            del worlds[ticket.destination.scene_id]
            if not worlds:
                del self._worlds[request_id]
            self._view(record).error = None
            return request_id, None
        task = self.session.verify_results(request_id, expected_revision=record.revision)
        if is_world:
            self._world_destinations[request_id] = ticket
        elif is_model:
            self._model_destinations[request_id] = ticket
        else:
            self._media_destinations[request_id] = ticket
        self._commands[request_id] = (
            "verify_world" if is_world else "verify_model" if is_model else "verify_media",
            task,
        )
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

    def _mesh_status(self, request_id):
        saved = self._mesh_edits.get(request_id)
        if saved is None:
            return None
        revision, application = saved
        if revision != self.session.history_revision:
            # History can replace RNA wrappers, even when object names survive.
            # Retire this transient status; never rebind it by name after redo.
            return None
        objects = tuple(bpy.data.objects)
        return {
            "target": application.source.name if application.source in objects else None,
            "original": application.original.name if application.original in objects else None,
            "policy": application.policy,
            "undo_available": application.undo_available,
            "parts": tuple(part.name for part in application.parts if part in objects),
            "rig": application.rig.name if application.rig in objects else None,
        }

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
            "mesh_sources": [asdict(source) for source in record.intent.mesh_sources],
            "cu_cost": float(record.intent.quote_cost)
            if record.intent.quote_cost is not None
            else None,
            "cu_cost_exact": record.intent.quote_cost,
            "source": getattr(record.intent, "source", "generation"),
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
            "local_applications": [
                {
                    "application_id": item.application_id,
                    "source_revision": item.source_revision,
                    "purpose": item.purpose,
                    "asset_ids": list(item.asset_ids),
                    "state": item.state.value,
                    "destination": {
                        "file_id": item.destination.file_id,
                        "scene_id": item.destination.scene_id,
                        "target_id": item.destination.target_id,
                        "revision": item.destination.revision,
                    },
                }
                for item in record.local_applications
            ],
            "delivery_paused": record.intent.request_id in self._paused,
            "actions": self.actions(record),
            "error": self.views[record.intent.request_id].error
            if record.intent.request_id in self.views
            else None,
            "mesh_edit": self._mesh_status(record.intent.request_id),
            "objects": [
                obj.name
                for obj in self._objects.get(record.intent.request_id, ())
                if obj in tuple(bpy.data.objects)
            ],
            "materials": [
                material.name
                for material in self._materials.get(record.intent.request_id, ())
                if material in tuple(bpy.data.materials)
            ],
            "images": [
                image.name
                for image in self._images.get(record.intent.request_id, ())
                if image in tuple(bpy.data.images)
            ],
            "note": "Saved job state; active jobs advance without repeating generation. "
            "Restarted or paused jobs require explicit recovery.",
        }
