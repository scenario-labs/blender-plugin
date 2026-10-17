# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Saved-job action descriptors shared by native result surfaces. No bpy.

`ModelJobs.actions()` alone decides which explicit follow-ups a saved job
offers, and MCP `job_status` reports the same action names. `describe()` turns
one projected job view into ordered descriptors: label, icon, operator and the
operator properties. The sidebar Jobs and Generations panels, Studio pages that
reuse them, and later the compact composer, draw and dispatch these descriptors
instead of keeping their own branches.

A descriptor grants nothing. Its operator rechecks its context token and saved
revision or review, and opens its own confirmation or destination review where
one applies.
Availability is expressed by presence: every offered operator descriptor is
enabled. A descriptor without an operator is a status row, never a control.

Results whose saved metadata declares a 360 projection add a label row and, for
each downloaded LDR panorama, a **Make HDRI** form prefill. A prefill is not a
saved-job action: it changes no saved job, quotes nothing and only opens the
Environment form, so MCP lists no matching action.

A running workflow job also gets rows from its owner's in-memory step
projection (`WorkflowSteps`): one review control per waiting step, the decision
being sent, the last decision's error, or why it cannot be canceled.

Read-only playback controls (Play video, Play in Blender, Play audio, Stop
audio, Waveform and Open in system player) are not job actions: they never
change the job, the scene or spending. They follow the view's saved state,
downloaded media types and the audio its owner plays instead of
``ModelJobs.actions``, and MCP ``job_status`` does not report them; no MCP tool
launches a desktop player or plays audio.
"""

import textwrap
from collections.abc import Collection, Mapping
from dataclasses import dataclass, field

from .costs import format_cu

RECOVER_OPERATOR = "scenario.recover_job"
REVIEW_OPERATOR = "scenario.review_workflow_step"

LABELS = {
    "refresh": "Refresh status",
    "resume": "Resume download",
    "cancel": "Cancel generation",
    "cancel_prepared": "Cancel prepared job",
    "recover_download": "Check interrupted download",
    "stop_download": "Stop download",
    "retry_receipt": "Save import receipt",
    "import_images": "Import saved images",
    "restore_world": "Restore previous World",
    "apply_material": "Apply saved material",
    "recover_blockout": "Read saved Blockout plan",
    "mark_reviewed": "Mark reviewed",
    "find_cloud_job": "Find in cloud history",
    "link_cloud_job": "Choose cloud job...",
    "read_prompt_text": "Read prompt text",
}

# Actions the native recovery operator dispatches, with their groups, in its
# enum order. All but cancel_prepared use ModelJobs.control, the command behind
# MCP recover_local_job; cancel_prepared shares MCP cancel_prepared_job's command.
RECOVERY_GROUPS = {
    "refresh": "recover",
    "resume": "recover",
    "cancel": "cancel",
    "cancel_prepared": "cancel",
    "recover_download": "recover",
    "stop_download": "cancel",
    "retry_receipt": "receipt",
    "mark_reviewed": "recover",
    "find_cloud_job": "recover",
    "read_prompt_text": "recover",
}
RECOVERY_ACTIONS = tuple(RECOVERY_GROUPS)
# Recovery actions only the user takes in Blender. Marking an unconfirmed request
# reviewed lets an identical one through, and linking a cloud job to it settles
# which job it created, so MCP neither lists nor accepts either.
# MCP reads saved prompt text with its own read_prompt_result tool instead.
NATIVE_ONLY = frozenset({"mark_reviewed", "link_cloud_job", "read_prompt_text"})
COPY_OPERATOR = "scenario.copy_text"
# Characters of a read prompt text shown above its Copy control.
PROMPT_PREVIEW = 160
# Opens the native candidate choice for an unconfirmed submission.
LINK_OPERATOR = "scenario.link_cloud_job"
# Status rows offered as ModelJobs actions; their decisions use their own commands.
STATUS_ACTIONS = {
    "review_step": ("Workflow waits for your decision", "INFO"),
}
# Width of wrapped multi-row notes; sidebar labels clip instead of wrapping.
NOTE_WIDTH = 36
# Scenario has no workflow cancellation endpoint; rejecting a waiting step stops one.
RUNNING_WORKFLOW = (
    "Scenario cannot cancel a running workflow step; it finishes or pauses at its next "
    "approval or selection."
)
# Rows about a workflow decision rather than an action; draw_pending shows them too.
DECISION_ROWS = frozenset({"decision_sending", "decision_error"})
# One saved result, applied without per-asset choice.
SINGLE_APPLY = {
    "import_images": "scenario.import_saved_images",
    "apply_material": "scenario.apply_saved_material",
}
# Offered alone on an applied job, these do not reuse its results.
NOT_REUSE = frozenset({"restore_world", "retry_receipt"})
# The Render Video first-frame review; ModelJobs projects its accepted assets.
FIRST_FRAME_OPERATOR = "scenario.use_saved_first_frame"
# Display names of the saved model formats `import_model` can offer.
MODEL_FORMATS = {
    "glb": "GLB",
    "gltf": "glTF",
    "fbx": "FBX",
    "obj": "OBJ",
    "ply": "PLY",
    "spz": "SPZ",
    "splat": ".splat",
}
# Formats that are always Gaussian splats; a PLY can hold a mesh or splats.
SPLAT_FORMATS = frozenset({"spz", "splat"})
# Saved 360 results by range ("ldr" or "hdr"); LDR is never called HDR.
PANORAMA_LABELS = {
    frozenset({"ldr"}): "360 panorama (LDR)",
    frozenset({"hdr"}): "360 HDR environment (OpenEXR)",
    frozenset({"ldr", "hdr"}): "360 panorama and HDR environment",
}
HDRI_OPERATOR = "scenario.panorama_to_hdri"
# Saved states whose downloaded results can feed another Environment form.
PREFILL_STATES = frozenset({"ready", "applied", "apply_failed"})
# Saved states whose downloaded results can be played; an interrupted
# application is included because playback never touches the scene.
PLAYBACK_STATES = frozenset({"ready", "applying", "apply_failed", "applied"})
PLAYBACK_OPERATOR = "scenario.play_saved_media"
WAVEFORM_OPERATOR = "scenario.preview_saved_waveform"
# Saved audio played inside Blender, in an owned offline process, and its Stop.
AUDIO_OPERATOR = "scenario.play_saved_audio"
STOP_AUDIO_OPERATOR = "scenario.stop_saved_audio"


@dataclass(frozen=True, eq=False)
class ResultTypes:
    """Saved media types each application accepts; owned by the Blender modules.

    `model` is the GLB type that saved mesh edits accept. New-group model
    imports come from the view's classified import units instead. It holds a
    mapping, so it compares and hashes by identity.
    """

    model: str
    media: Mapping[str, str]  # media type -> "video" or "audio" strip kind
    world: Collection[str]
    # media type -> "video" or "audio" for a private player copy and waveform.
    playback: Mapping[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class WorkflowSteps:
    """One workflow job's in-memory step projection, supplied by its owner for drawing.

    `steps` are the waiting steps (`workflow_nodes.PendingStep`, read by
    attribute) projected for saved `revision`; they are described only while it
    equals the view's saved revision. `deciding` is True while a decision is
    queued or being sent, and `error` is the last decision's text.
    """

    revision: int | None = None
    steps: tuple = ()
    deciding: bool = False
    error: str = ""


@dataclass(frozen=True)
class SavedJobAction:
    """One saved-job control, or a status row when `operator` is None.

    `key` is unique within one view. `action` is the ModelJobs and MCP action
    name, a native playback control name, or empty for a row about the whole
    view and for a form prefill. `group` is recover, cancel, apply, receipt,
    decide, prefill, playback or status. `properties` are the operator's
    property name/value pairs, set exactly as listed. Consecutive descriptors
    with the same non-empty `row` share one row.
    """

    key: str
    action: str
    group: str
    label: str
    icon: str = "NONE"
    operator: str | None = None
    properties: tuple = ()
    row: str = ""


STATUS_WORDS = {
    "pending": "queued",
    "queued": "queued",
    "warming-up": "starting",
    "in-progress": "generating",
    "finalizing": "finalizing",
    "success": "finished",
    "failure": "failed",
    "canceled": "canceled",
}


def _duration(seconds):
    magnitude = abs(seconds)
    if magnitude < 60:
        text = f"{magnitude:.1f} s".replace(".0 s", " s")
    elif magnitude < 3600:
        text = f"{round(magnitude / 60)} min"
    else:
        text = f"{magnitude / 3600:.1f} h"
    return f"{text} after sending" if seconds >= 0 else f"{text} before sending"


def candidate_text(candidate):
    """The (title, detail) lines describing one listed cloud job; display only.

    `candidate` is a `reconcile.CloudCandidate` as a dict, as `ModelJobs`
    projects it. Nothing here suggests the job is this request's.
    """
    seconds = candidate.get("seconds_after_claim")
    if seconds is not None:
        when = "Created " + _duration(seconds)
    elif candidate.get("created_at"):
        when = "Created " + candidate["created_at"][:16].replace("T", " ") + " UTC"
    else:
        when = "Creation time unknown"
    parts = [when, STATUS_WORDS.get(candidate.get("status"), "unknown state")]
    if candidate.get("cost") is not None:
        try:
            parts.append(f"{format_cu(candidate['cost'])} CU")
        except (ArithmeticError, ValueError):
            # An unreadable cost is named as such, never shown as 0.
            parts.append("cost unavailable")
    prompt = candidate.get("prompt") or "No prompt text"
    return ", ".join(parts), prompt


def _status(key, action, label, icon):
    return SavedJobAction(key, action, "status", label, icon)


def _note(key, text, icon):
    """Status rows wrapping one message; only the first row carries the icon."""
    return tuple(
        _status(key if index == 0 else f"{key}:{index}", "", line, icon if index == 0 else "NONE")
        for index, line in enumerate(textwrap.wrap(text, NOTE_WIDTH))
    )


def step_label(step):
    """A waiting step's review control text: what deciding it asks for."""
    if step.node_type == "user-approval":
        text = "Review approval"
    elif step.blocked:
        text = "Review blocked selection"
    else:
        upper = min(step.maximum, len(step.items))
        count = str(upper) if step.minimum == upper else f"{step.minimum} to {upper}"
        text = f"Choose {count} of {len(step.items)}"
    if step.iteration_index is not None:
        text += f" (loop index {step.iteration_index})"
    return text


def _review_steps(steps, job):
    """One review control per waiting step; a step without decisions is a status row."""
    items = []
    for index, step in enumerate(steps):
        key = f"review_step:{index}"
        if not step.actions:
            items.append(_status(key, "review_step", "This step cannot be decided here", "ERROR"))
            continue
        items.append(
            SavedJobAction(
                key,
                "review_step",
                "decide",
                step_label(step),
                operator=REVIEW_OPERATOR,
                properties=(*job, ("node_id", step.node_id), ("review_id", step.review_id)),
            )
        )
    return tuple(items)


def _per_asset(view, action, operator, label, accepts, job, extra=()):
    """One control per accepted saved asset; numbering counts every saved asset."""
    return tuple(
        SavedJobAction(
            f"{action}:{asset_id}",
            action,
            "apply",
            label(index, view.asset_types.get(asset_id)),
            operator=operator,
            properties=(*job, ("asset_id", asset_id), *extra),
        )
        for index, asset_id in enumerate(view.asset_ids, 1)
        if accepts(view.asset_types.get(asset_id))
    )


def _blockout(review, job):
    action = "recover_blockout"
    if review is not None and review.task is not None:
        return (_status(f"{action}:reading", action, "Reading saved plan...", "TIME"),)
    if review is not None and review.phase == "READY":
        use = SavedJobAction(
            f"{action}:use",
            action,
            "apply",
            "Use saved Blockout plan",
            operator="scenario.use_saved_blockout",
            properties=(job[0], ("review_id", review.identifier)),
        )
        return (use,)
    read = SavedJobAction(
        action,
        action,
        "recover",
        LABELS[action],
        operator="scenario.read_saved_blockout",
        properties=job,
    )
    if review is not None and review.phase == "ERROR":
        error = _status(
            f"{action}:error", action, "Plan needs review; check job and destination", "ERROR"
        )
        return (error, read)
    return (read,)


def _import_units(view, action, job):
    """One control per importable unit, in classified order; the first is primary.

    `view.meta["import_units"]` holds (key, format, primary) rows that ModelJobs
    projects from the saved manifest. Numbering counts every saved asset.
    """
    numbers = {asset_id: index for index, asset_id in enumerate(view.asset_ids, 1)}
    items = []
    for key, fmt, primary in view.meta.get("import_units", ()):
        if key not in numbers or fmt not in MODEL_FORMATS:
            continue
        name = MODEL_FORMATS[fmt]
        if fmt in SPLAT_FORMATS:
            label = f"Import splats: {name}" if primary else f"Import alternate splats: {name}"
        else:
            label = f"Import {name} model" if primary else f"Import alternate: {name}"
        items.append(
            SavedJobAction(
                f"{action}:{key}",
                action,
                "apply",
                f"{label} ({numbers[key]})",
                operator="scenario.import_saved_model",
                properties=(*job, ("asset_id", key)),
            )
        )
    return tuple(items)


def _describe_action(action, view, job, result_types, review, workflow=None):
    def is_model(media_type):
        return media_type == result_types.model

    if action == "recover_blockout":
        return _blockout(review, job)
    if action == "review_step":
        row = _status(action, action, *STATUS_ACTIONS[action])
        if workflow is None or workflow.revision != dict(job)["expected_revision"]:
            return (row,)
        return (row, *_review_steps(workflow.steps, job))
    if action in STATUS_ACTIONS:
        return (_status(action, action, *STATUS_ACTIONS[action]),)
    if action == "link_cloud_job":
        return (
            SavedJobAction(
                action, action, "recover", LABELS[action], operator=LINK_OPERATOR, properties=job
            ),
        )
    if action in SINGLE_APPLY:
        operator = SINGLE_APPLY[action]
        return (
            SavedJobAction(
                action, action, "apply", LABELS[action], operator=operator, properties=job
            ),
        )
    if action == "restore_world":
        properties = (*job, ("asset_id", ""), ("purpose", "restore_world"))
        operator = "scenario.apply_saved_world"
        return (
            SavedJobAction(
                action, action, "apply", LABELS[action], operator=operator, properties=properties
            ),
        )
    if action == "apply_world":
        # The projection lists World candidates without material maps, which share their
        # media types, or images whose header shows they are not 2:1. Numbering counts
        # every saved asset, as the import buttons do.
        candidates = frozenset(view.meta.get("world_assets", ()))
        return tuple(
            SavedJobAction(
                f"{action}:{asset_id}",
                action,
                "apply",
                f"Set panorama as World ({index})",
                operator="scenario.apply_saved_world",
                properties=(*job, ("asset_id", asset_id), ("purpose", "world")),
            )
            for index, asset_id in enumerate(view.asset_ids, 1)
            if asset_id in candidates and view.asset_types.get(asset_id) in result_types.world
        )
    if action in {"apply_mesh", "apply_mesh_source"}:
        source = action == "apply_mesh_source"
        text = "Apply to captured source" if source else "Apply mesh edit"
        alternate = "Apply alternate to captured source" if source else "Apply alternate mesh edit"
        # Only GLBs apply in place; an alternate unit is named like its import.
        alternates = {
            index
            for index, asset_id in enumerate(view.asset_ids, 1)
            if (asset_id, "glb", False) in view.meta.get("import_units", ())
        }
        return _per_asset(
            view,
            action,
            "scenario.apply_saved_mesh",
            lambda index, _: (
                f"{alternate}: GLB ({index})" if index in alternates else f"{text} ({index})"
            ),
            is_model,
            job,
            (("original_source", source),),
        )
    if action == "import_model":
        return _import_units(view, action, job)
    if action == "import_media":
        return _per_asset(
            view,
            action,
            "scenario.import_saved_media",
            lambda index, media_type: f"Add {result_types.media[media_type]} strip ({index})",
            lambda media_type: media_type in result_types.media,
            job,
        )
    if action == "use_first_frame":
        # Eligibility needs texture roles and receipts, so the owner projects
        # the accepted asset IDs; numbering still counts every saved asset.
        accepted = frozenset(view.meta.get("first_frame_assets", ()))
        return tuple(
            SavedJobAction(
                f"{action}:{asset_id}",
                action,
                "apply",
                f"Use as video first frame ({index})",
                operator=FIRST_FRAME_OPERATOR,
                properties=(*job, ("asset_id", asset_id)),
            )
            for index, asset_id in enumerate(view.asset_ids, 1)
            if asset_id in accepted
        )
    if action not in RECOVERY_GROUPS:
        raise ValueError(f"No saved-job control describes action {action!r}")
    return (
        SavedJobAction(
            action,
            action,
            RECOVERY_GROUPS[action],
            LABELS[action],
            operator=RECOVER_OPERATOR,
            properties=(*job, ("action", action)),
        ),
    )


def _prompt_texts(view):
    """A finished prompt job's text read into memory: a preview and a Copy control each."""
    texts = view.meta.get("prompt_texts", ())
    items = []
    for index, text in enumerate(texts, 1):
        preview = " ".join(text.split())
        if len(preview) > PROMPT_PREVIEW:
            preview = preview[: PROMPT_PREVIEW - 3] + "..."
        items.extend(_note(f"prompt_text:{index}", preview or "(empty text)", "TEXT"))
        label = "Copy prompt text" if len(texts) == 1 else f"Copy prompt text ({index})"
        items.append(
            SavedJobAction(
                f"copy_prompt:{index}",
                "",
                "recover",
                label,
                "COPYDOWN",
                operator=COPY_OPERATOR,
                properties=(("text", text), ("what", "prompt text")),
            )
        )
    return items


def _panorama_label(view):
    kinds = frozenset(view.meta.get("panoramas", {}).values())
    label = PANORAMA_LABELS.get(kinds)
    return (_status("panorama", "", label, "WORLD"),) if label else ()


def _hdri_prefills(view, job):
    """One Make HDRI prefill per downloaded LDR 360 result, numbered among them."""
    if view.meta.get("saved_state") not in PREFILL_STATES:
        return ()
    return tuple(
        SavedJobAction(
            f"make_hdri:{asset_id}",
            "",
            "prefill",
            f"Make HDRI ({index})",
            operator=HDRI_OPERATOR,
            properties=(*job, ("asset_id", asset_id)),
        )
        for index, asset_id in enumerate(view.meta.get("panorama_inputs", ()), 1)
    )


def _video_playback(asset_id, index, asset, row):
    return (
        SavedJobAction(
            f"play:{asset_id}",
            "play",
            "playback",
            f"Play video ({index})",
            operator=PLAYBACK_OPERATOR,
            properties=(*asset, ("player", "SYSTEM")),
            row=row,
        ),
        SavedJobAction(
            f"play_in_blender:{asset_id}",
            "play_in_blender",
            "playback",
            f"Play in Blender ({index})",
            operator=PLAYBACK_OPERATOR,
            properties=(*asset, ("player", "BLENDER")),
            row=row,
        ),
    )


def _audio_playback(asset_id, index, asset, row, playing):
    """Play audio or Stop audio and Waveform in one row, the system player in the next.

    Stop names the playing asset but no revision: it stops that asset's audio
    whatever the saved job's state.
    """
    if playing:
        toggle = SavedJobAction(
            f"stop_audio:{asset_id}",
            "stop_audio",
            "playback",
            f"Stop audio ({index})",
            operator=STOP_AUDIO_OPERATOR,
            properties=tuple(item for item in asset if item[0] != "expected_revision"),
            row=row,
        )
    else:
        toggle = SavedJobAction(
            f"play:{asset_id}",
            "play",
            "playback",
            f"Play audio ({index})",
            operator=AUDIO_OPERATOR,
            properties=asset,
            row=row,
        )
    return (
        toggle,
        SavedJobAction(
            f"waveform:{asset_id}",
            "waveform",
            "playback",
            f"Waveform ({index})",
            operator=WAVEFORM_OPERATOR,
            properties=asset,
            row=row,
        ),
        SavedJobAction(
            f"system_player:{asset_id}",
            "system_player",
            "playback",
            f"Open in system player ({index})",
            operator=PLAYBACK_OPERATOR,
            properties=(*asset, ("player", "SYSTEM")),
            row=f"system:{asset_id}",
        ),
    )


def _playback(view, job, result_types, listening):
    """One row per downloaded video result, two per audio result.

    A video row has Play video, which opens the system player, and Play in
    Blender. An audio row has Play audio, which plays inside Blender, or Stop
    audio while `listening` names that asset, and Waveform; the next row opens
    the system player. Numbering counts every saved asset, like per-asset
    applications.
    """
    items = []
    for index, asset_id in enumerate(view.asset_ids, 1):
        kind = result_types.playback.get(view.asset_types.get(asset_id))
        if kind is None:
            continue
        asset = (*job, ("asset_id", asset_id))
        row = f"playback:{asset_id}"
        if kind == "video":
            items.extend(_video_playback(asset_id, index, asset, row))
        else:
            items.extend(_audio_playback(asset_id, index, asset, row, listening == asset_id))
    return items


def describe(
    view, context_id, result_types, blockout_review=None, workflow_steps=None, listening=None
):
    """Return one projected view's saved-job controls in drawing order.

    Reads only the in-memory view, the supplied Blockout review for the current
    scene, the supplied workflow step projection and `listening`, the asset ID
    whose audio this view's owner plays or prepares to play; it performs no I/O
    and changes nothing. A view that is not a shared job, or has no saved
    revision yet, offers nothing. Playback controls follow the job actions and
    precede the closing status rows.
    """
    meta = view.meta
    if not meta.get("shared_job") or "saved_revision" not in meta:
        return ()
    actions = tuple(meta.get("recovery_actions", ()))
    state = meta.get("saved_state")
    job = (
        ("context_id", context_id),
        ("request_id", view.local_id),
        ("expected_revision", meta["saved_revision"]),
    )
    running = getattr(view, "kind", None) == "workflow" and state == "remote"
    workflow = workflow_steps if running else None
    deciding = workflow is not None and workflow.deciding
    items = []
    if state == "applied" and any(action not in NOT_REUSE for action in actions):
        items.append(_status("reuse", "", "Reuse saved results", "FILE_REFRESH"))
    if deciding:
        items.append(_status("decision_sending", "", "Sending your decision...", "TIME"))
    if workflow is not None and workflow.error:
        items.extend(_note("decision_error", workflow.error, "ERROR"))
    items.extend(_panorama_label(view))
    if meta.get("cloud_lookup"):
        # Unconfirmed submissions: the read-only cloud lookup's progress or outcome.
        items.extend(
            _note("cloud_lookup", meta["cloud_lookup"], meta.get("cloud_lookup_icon", "INFO"))
        )
    for action in actions:
        items.extend(_describe_action(action, view, job, result_types, blockout_review, workflow))
    items.extend(_hdri_prefills(view, job))
    items.extend(_prompt_texts(view))
    if state in PLAYBACK_STATES:
        items.extend(_playback(view, job, result_types, listening))
    # Session-local notes about the last import, such as splat thinning.
    for index, text in enumerate(meta.get("import_notices", ())):
        items.append(_status(f"import_notice:{index}", "", text, "INFO"))
    waiting = "review_step" in actions or (
        workflow is not None and workflow.revision == meta["saved_revision"] and workflow.steps
    )
    if running and not deciding and not waiting:
        # No button: no request can stop a running step.
        items.extend(_note("workflow_running", RUNNING_WORKFLOW, "INFO"))
    if state in ("ready", "apply_failed"):
        items.append(
            _status("awaiting_review", "", "Downloaded result awaits application review", "INFO")
        )
    return tuple(items)
