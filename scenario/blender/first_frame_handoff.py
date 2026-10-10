# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Hand one verified saved image result to the Render Video first frame.

Main thread only. The handoff reuses the saved result's own Scenario asset ID,
so nothing is uploaded, generated or spent. It binds a form slot; it is not a
scene application, so the saved job keeps its state and gains no claim.

No local file path reaches the form or the saved blend: the slot keeps the
asset ID, the existing scope/asset/kind markers and provenance (request ID,
asset ID and receipt digest). A reader can use that provenance to find the
saved job again in the same credential scope. Provenance never authorizes a
quote; `reference_form.scope_error` still decides where the asset may be used.
"""

import hashlib
import json
import logging
import os
import stat
import threading
from dataclasses import dataclass, field
from pathlib import Path

from ..core.api.errors import ScenarioError
from ..core.jobs.result_metadata import IMAGE_SIGNATURE_TYPES, image_signature_matches
from ..core.jobs.store import JobOrigin, ResultAsset, StoredJob
from ..core.scene.panorama import MAX_FILE_BYTES
from . import generation, props, reference_form, render_lanes, render_references, runtime

_log = logging.getLogger("scenario.jobs")

LANE = "render_video"
# Still images the shared reference upload policy also accepts; EXR is excluded.
FIRST_FRAME_TYPES = IMAGE_SIGNATURE_TYPES
# Normal, height and other non-colour maps are never a first frame.
_COLOUR_ROLES = (None, "base")
RESULT = reference_form._RESULT
STOPPED = "First-frame handoff stopped; review the saved image and Render Video form again"


class FirstFrameHandoffError(RuntimeError):
    """The handoff was refused or rolled back; the form and saved job are unchanged."""

    def __init__(self, reason):
        super().__init__(reason)
        self.reason = reason


@dataclass(frozen=True)
class FirstFrameTarget:
    """The reviewed Render Video destination; `key` must be unchanged at binding."""

    form_key: str
    model_id: str
    param_name: str
    previous_path: str
    previous_enabled: bool
    model_label: str = field(default="", compare=False)
    input_label: str = field(default="", compare=False)
    # `first_frame`, or `reference_image` when the model cannot take an exact
    # first frame with the clip; `note` says so in user words.
    sent_as: str = field(default="first_frame", compare=False)
    reason: str = field(default=None, compare=False)
    note: str = field(default=None, compare=False)

    @property
    def key(self):
        return (
            self.form_key,
            self.model_id,
            self.param_name,
            self.previous_path,
            self.previous_enabled,
        )


@dataclass(frozen=True)
class FirstFrameApproval:
    identifier: str
    record: StoredJob
    destination: JobOrigin
    scene_name: str
    scene: object = field(repr=False)
    asset: ResultAsset
    sha256: str
    target: FirstFrameTarget
    kind: str = "video_first_frame"


@dataclass(frozen=True)
class FirstFrameBinding:
    scene_name: str
    asset_id: str
    param_name: str
    undo_recorded: bool


def _main_thread():
    if threading.current_thread() is not threading.main_thread():
        raise FirstFrameHandoffError("Hand off first frames on Blender's main thread")


def eligible_assets(record):
    """Downloaded PNG, JPEG or WebP colour results; pure policy without I/O."""
    if record.intent.operation in {"prompt", "translate"}:
        return ()
    return tuple(
        item
        for item in record.results
        if item.receipt is not None
        and item.asset.media_type in FIRST_FRAME_TYPES
        and item.asset.texture_role in _COLOUR_ROLES
    )


def _schema(lane):
    """The loaded model schema; reviewing never starts a catalog read."""
    if not lane.model_id or lane.model_id == "NONE":
        raise ScenarioError(0, "Choose a Render Video model first")
    schema = generation.schema_for(lane.model_id)
    if schema is None:
        raise ScenarioError(0, "Load the Render Video model in its form first")
    return schema


def target(scene):
    """Check the Render Video form can take one more first frame; never mutate it."""
    lane = scene.scenario.lane_state(LANE)
    schema = _schema(lane)
    spec = render_references.target(LANE, schema, render_references.FIRST_FRAME)
    if spec is None or reference_form.input_kind(lane, spec.name) != "image":
        raise ScenarioError(0, "Choose a Render Video model with an image input")
    if render_references.slot(lane, render_references.FIRST_FRAME):
        # Any existing slot, including a pending or uncertain upload marker.
        raise ScenarioError(0, "Remove the current Render Video first frame first")
    used = sum(ref.param_name == spec.name for ref in lane.references)
    limit = 1 if spec.ptype == "file" else spec.max_length
    if limit and used >= limit:
        raise ScenarioError(0, f"Remove a reference from {spec.label or spec.name} first")
    record = runtime.state.records.get(lane.model_id)
    route = render_lanes.first_frame_route(schema) or {}
    return FirstFrameTarget(
        reference_form._destination_key(scene, LANE),
        lane.model_id,
        spec.name,
        lane.first_frame_path,
        bool(lane.use_first_frame),
        record.name if record is not None else lane.model_id,
        spec.label or spec.name,
        route.get("sent_as", "first_frame"),
        route.get("reason"),
        route.get("note"),
    )


def provenance(ref):
    """The saved result a slot was handed from, or None when absent or edited."""
    try:
        value = json.loads(ref.get(RESULT, ""))
    except (TypeError, ValueError):
        return None
    if (
        not isinstance(value, dict)
        or set(value) != {"request_id", "asset_id", "sha256"}
        or not all(isinstance(item, str) and item for item in value.values())
        or ref.source != "ASSET"
        or value["asset_id"] != ref.asset_id
    ):
        return None
    return value


def saved_source(store, ref):
    """Find the slot's saved result again in this store, by request, asset and digest.

    Returns the stored result only when the current credential scope still holds
    the same verified download; None otherwise. Reads the store, never the file.
    """
    source = provenance(ref)
    if source is None or store is None:
        return None
    try:
        record = store.get(source["request_id"])
    except Exception:
        return None
    if record is None:
        return None
    for item in record.results:
        if (
            item.asset.asset_id == source["asset_id"]
            and item.receipt is not None
            and item.receipt.sha256 == source["sha256"]
        ):
            return item
    return None


def _check_file(item, path):
    """Rehash the receipt-bound file and check its image container; read-only."""
    receipt, path = item.receipt, Path(path)
    if (
        receipt is None
        or path.name != receipt.name
        or not 0 < receipt.size <= MAX_FILE_BYTES
        or path.is_symlink()
    ):
        raise FirstFrameHandoffError("Use a downloaded saved image within the size limit")
    flags = (
        os.O_RDONLY
        | getattr(os, "O_NOFOLLOW", 0)
        | getattr(os, "O_NONBLOCK", 0)
        | getattr(os, "O_BINARY", 0)
    )
    digest, size, head = hashlib.sha256(), 0, b""
    try:
        with os.fdopen(os.open(path, flags), "rb") as source:
            if not stat.S_ISREG(os.fstat(source.fileno()).st_mode):
                raise FirstFrameHandoffError("The saved image is not a regular file")
            while chunk := source.read(min(1024 * 1024, receipt.size - size + 1)):
                if not head:
                    head = chunk[:16]
                size += len(chunk)
                if size > receipt.size:
                    break
                digest.update(chunk)
    except OSError:
        raise FirstFrameHandoffError("The saved image could not be read") from None
    if size != receipt.size or digest.hexdigest() != receipt.sha256:
        raise FirstFrameHandoffError("The saved image no longer matches its receipt")
    if not image_signature_matches(head, item.asset.media_type):
        raise FirstFrameHandoffError("Image contents do not match the saved media type")


def _record_undo():
    from .mesh_result_application import _undo_enabled, _undo_push

    if not _undo_enabled():
        return False
    try:
        _undo_push("Scenario video first frame")
    except Exception:
        # The binding is complete; a missing history step never repeats it.
        _log.warning("First frame bound, but Blender undo could not be recorded")
        return False
    return True


def bind(session, completion, ticket):
    """Bind one verified saved image to the approved, unchanged Render Video form."""
    _main_thread()
    from .job_session import OriginUnavailable

    if not isinstance(ticket, FirstFrameApproval):
        raise FirstFrameHandoffError(STOPPED)
    try:
        scene, item, path = session.verified_result(
            completion, destination=ticket.destination, asset_id=ticket.asset.asset_id
        )
    except OriginUnavailable:
        raise FirstFrameHandoffError(
            "The scene changed; review the saved image for the first frame again"
        ) from None
    if (
        scene != ticket.scene
        or completion.result.record != ticket.record
        or item.asset != ticket.asset
        or item.receipt is None
        or item.receipt.sha256 != ticket.sha256
    ):
        raise FirstFrameHandoffError("The saved image changed; inspect the job again")
    _check_file(item, path)
    try:
        current = target(scene)
    except ScenarioError as error:
        raise FirstFrameHandoffError(error.reason) from None
    if current.key != ticket.target.key:
        raise FirstFrameHandoffError("The Render Video form changed; review the first frame again")
    lane = scene.scenario.lane_state(LANE)
    previous = (lane.first_frame_path, lane.use_first_frame)
    count = len(lane.references)
    try:
        ref = lane.references.add()
        ref.param_name = current.param_name
        ref[render_references.ROLE] = render_references.FIRST_FRAME
        ref.source, ref.asset_id, ref.filepath = "ASSET", item.asset.asset_id, ""
        ref.label = f"First frame: {item.asset.name} (saved result)"
        ref[reference_form._SCOPE] = reference_form.scope_key(session.scope)
        ref[reference_form._ASSET] = item.asset.asset_id
        ref[reference_form._KIND] = "image"
        ref[RESULT] = json.dumps(
            {
                "request_id": ticket.record.intent.request_id,
                "asset_id": item.asset.asset_id,
                "sha256": ticket.sha256,
            },
            sort_keys=True,
            separators=(",", ":"),
        )
        # The asset replaces any chosen local file, so no path is kept.
        lane.first_frame_path = ""
        lane.use_first_frame = True
        props.mark_estimate_dirty(lane)
    except Exception:
        while len(lane.references) > count:
            lane.references.remove(len(lane.references) - 1)
        lane.first_frame_path, lane.use_first_frame = previous
        raise FirstFrameHandoffError(STOPPED) from None
    return FirstFrameBinding(
        ticket.scene_name, item.asset.asset_id, current.param_name, _record_undo()
    )
