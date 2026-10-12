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
"""

from collections.abc import Collection, Mapping
from dataclasses import dataclass

RECOVER_OPERATOR = "scenario.recover_job"

LABELS = {
    "refresh": "Refresh status",
    "resume": "Resume download",
    "cancel": "Cancel generation",
    "cancel_prepared": "Cancel prepared job",
    "recover_download": "Check interrupted download",
    "retry_receipt": "Save import receipt",
    "import_images": "Import saved images",
    "restore_world": "Restore previous World",
    "apply_material": "Apply saved material",
    "recover_blockout": "Read saved Blockout plan",
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
    "retry_receipt": "receipt",
}
RECOVERY_ACTIONS = tuple(RECOVERY_GROUPS)
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


@dataclass(frozen=True)
class SavedJobAction:
    """One saved-job control, or a status row when `operator` is None.

    `key` is unique within one view. `action` is the ModelJobs and MCP action
    name, or empty for a row about the whole view. `group` is recover, cancel,
    apply, receipt or status. `properties` are the operator's property
    name/value pairs, set exactly as listed.
    """

    key: str
    action: str
    group: str
    label: str
    icon: str = "NONE"
    operator: str | None = None
    properties: tuple = ()


def _status(key, action, label, icon):
    return SavedJobAction(key, action, "status", label, icon)


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


def _describe_action(action, view, job, result_types, review):
    def is_model(media_type):
        return media_type == result_types.model

    if action == "recover_blockout":
        return _blockout(review, job)
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
        # media types. Numbering counts every saved asset, as the import buttons do.
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
        return _per_asset(
            view,
            action,
            "scenario.apply_saved_mesh",
            lambda index, _: f"{text} ({index})",
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


def describe(view, context_id, result_types, blockout_review=None):
    """Return one projected view's saved-job controls in drawing order.

    Reads only the in-memory view and the supplied Blockout review for the
    current scene; it performs no I/O and changes nothing. A view that is not a
    shared job, or has no saved revision yet, offers nothing.
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
    items = []
    if state == "applied" and any(action not in NOT_REUSE for action in actions):
        items.append(_status("reuse", "", "Reuse saved results", "FILE_REFRESH"))
    for action in actions:
        items.extend(_describe_action(action, view, job, result_types, blockout_review))
    # Session-local notes about the last import, such as splat thinning.
    for index, text in enumerate(meta.get("import_notices", ())):
        items.append(_status(f"import_notice:{index}", "", text, "INFO"))
    if state in ("ready", "apply_failed"):
        items.append(
            _status("awaiting_review", "", "Downloaded result awaits application review", "INFO")
        )
    return tuple(items)
