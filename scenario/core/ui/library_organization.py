# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Display text and request mapping for native Library organization.

Pure and bpy-free, so the native Library stays a thin renderer. Review cards are
built only from the shared ``review_payload`` projection, which omits URLs,
owner IDs and service text. Names and tags are untrusted labels: they are
clipped and wrapped for narrow views, never interpreted.
"""

import textwrap

from ..jobs.organization import NOTICE, Operation, normalize_name, parse_tags

WIDTH = 48
NO_COLLECTION = "NONE"

# Native dialog choices: (identifier, label, description) for an EnumProperty.
ACTIONS = (
    ("ADD", "Add to collection", "Add this asset to a loaded collection"),
    ("REMOVE", "Remove from collection", "Remove this asset from a loaded collection"),
    ("ADD_TAGS", "Add tags", "Add comma-separated tags to this asset"),
    ("REMOVE_TAGS", "Remove tags", "Remove comma-separated tags from this asset"),
    (
        "CREATE",
        "New collection and add",
        "Create a collection with an unused exact name, then add this asset",
    ),
)

OPERATION_LABELS = {
    Operation.ADD_TO_COLLECTION.value: "Add to collection",
    Operation.REMOVE_FROM_COLLECTION.value: "Remove from collection",
    Operation.UPDATE_TAGS.value: "Change tags",
    Operation.CREATE_COLLECTION.value: "New collection and add",
}
OUTCOME_LABELS = {
    "VERIFIED": "Verified",
    "REJECTED": "Refused",
    "UNCONFIRMED": "Unconfirmed: refresh to inspect",
    "NOT_SENT": "Not sent",
    "UNVERIFIED": "Not verified: refresh to inspect",
}
RESULT_LABELS = {
    "VERIFIED": ("Verified by reading back", "CHECKMARK"),
    "PARTIAL": ("Partly applied", "ERROR"),
    "UNCONFIRMED": ("Unconfirmed", "ERROR"),
    "REJECTED": ("Refused", "ERROR"),
}
TERMINAL_PHASES = frozenset(
    {"UNCHANGED", "REJECTED", "FINISHED", "NOT_SENT", "DISCARDED", "EXPIRED", "UNAVAILABLE"}
)
# Library holds one review at a time, so a full shared pool means local MCP
# reviews fill it; name that cause instead of a review this card cannot show.
REVIEWS_FULL = (
    "Too many organization reviews are open, including a connected agent's. Retry after "
    "they are applied or discarded; unapplied reviews expire after 10 minutes"
)


def clip(text, width=WIDTH):
    """Shorten one display label to ``width`` characters with an ellipsis."""
    text = str(text)
    return text if len(text) <= width else text[: max(0, width - 1)] + "…"


def label_summary(prefix, values, *, more=0, width=WIDTH):
    """Join labels after ``prefix`` and count the ones that do not fit as "+N".

    ``more`` adds labels that cannot be named, such as unloaded collections.
    """
    values = [str(value) for value in values]
    if not values:
        return f"{prefix}+{more}" if more else ""
    shown = []
    for value in values:
        hidden = len(values) - len(shown) - 1 + more
        text = prefix + ", ".join([*shown, value]) + (f" +{hidden}" if hidden else "")
        if len(text) > width:
            break
        shown.append(value)
    if not shown:
        hidden = len(values) - 1 + more
        suffix = f" +{hidden}" if hidden else ""
        return prefix + clip(values[0], max(1, width - len(prefix) - len(suffix))) + suffix
    hidden = len(values) - len(shown) + more
    return prefix + ", ".join(shown) + (f" +{hidden}" if hidden else "")


def tags_summary(tags, width=WIDTH):
    return label_summary("Tags: ", tags, width=width) if tags else "No tags"


def membership_summary(collection_ids, names, width=WIDTH):
    """Count memberships and name the collections that are loaded."""
    count = len(collection_ids)
    if not count:
        return "In no collections"
    noun = "collection" if count == 1 else "collections"
    known = [names[identifier] for identifier in collection_ids if names.get(identifier)]
    if not known:
        return f"In {count} {noun}"
    return label_summary(f"In {count} {noun}: ", known, more=count - len(known), width=width)


def connection_label(project_id):
    """Name the selected scope the way Studio's Connection page does."""
    return clip("Project: " + (project_id or "API key default scope"))


def request_arguments(action, asset_id, *, collection_id="", collection_name="", tags=""):
    """Map one native dialog choice to shared prepare arguments.

    Raises ValueError with UI-safe text; validation is the shared contract's.
    """
    if action in {"ADD", "REMOVE"}:
        if not collection_id or collection_id == NO_COLLECTION:
            raise ValueError("Load collections in Library and choose one")
        operation = (
            Operation.ADD_TO_COLLECTION if action == "ADD" else Operation.REMOVE_FROM_COLLECTION
        )
        return operation.value, {"asset_ids": [asset_id], "collection_id": collection_id}
    if action in {"ADD_TAGS", "REMOVE_TAGS"}:
        values = list(parse_tags(tags))
        if not values:
            raise ValueError("Enter at least one tag, separated by commas")
        key = "add_tags" if action == "ADD_TAGS" else "remove_tags"
        return Operation.UPDATE_TAGS.value, {"asset_ids": [asset_id], key: values}
    if action == "CREATE":
        name = normalize_name(collection_name)
        return Operation.CREATE_COLLECTION.value, {
            "asset_ids": [asset_id],
            "collection_name": name,
        }
    raise ValueError("Choose an organization action")


def dialog_problem(action, *, has_collections, collection_id, collection_name, tags):
    """Explain why OK would be refused, without flagging a field not yet typed."""
    if action in {"ADD", "REMOVE"} and not has_collections:
        return "Load collections in Library first, then organize again"
    if action in {"ADD_TAGS", "REMOVE_TAGS"} and not tags.strip():
        return ""
    if action == "CREATE" and not collection_name.strip():
        return ""
    try:
        request_arguments(
            action,
            "asset",
            collection_id=collection_id,
            collection_name=collection_name,
            tags=tags,
        )
    except ValueError as error:
        return str(error)
    return ""


def card_actions(phase):
    """Buttons a review card offers: Apply/Discard when READY, Dismiss when terminal."""
    if phase == "READY":
        return ("APPLY", "DISCARD")
    if phase in TERMINAL_PHASES:
        return ("DISMISS",)
    return ()


def _wrapped(lines, text, icon="NONE", width=WIDTH):
    for index, line in enumerate(textwrap.wrap(str(text), width) or [""]):
        lines.append((line, icon if index == 0 else ("BLANK1" if icon != "NONE" else "NONE")))


def _target(payload, names):
    operation = payload.get("operation")
    if operation in {
        Operation.ADD_TO_COLLECTION.value,
        Operation.REMOVE_FROM_COLLECTION.value,
    }:
        identifier = payload.get("collection_id")
        name = payload.get("collection_name") or names.get(identifier) or identifier
        return ["Collection: " + clip(name, WIDTH - 12)]
    if operation == Operation.CREATE_COLLECTION.value:
        return ["New collection: " + clip(payload.get("collection_name") or "", WIDTH - 16)]
    parts = []
    if payload.get("add_tags"):
        parts.append(label_summary("Add tags: ", payload["add_tags"]))
    if payload.get("remove_tags"):
        parts.append(label_summary("Remove tags: ", payload["remove_tags"]))
    return parts


def _asset_change(payload, row):
    change = row.get("change") or {}
    operation = payload.get("operation")
    if operation == Operation.UPDATE_TAGS.value:
        now = tags_summary(row.get("tags") or ())
        parts = []
        if change.get("add_tags"):
            parts.append(label_summary("add ", change["add_tags"], width=WIDTH - 8))
        if change.get("remove_tags"):
            parts.append(label_summary("remove ", change["remove_tags"], width=WIDTH - 8))
        return "Now: " + now, ("Change: " + "; ".join(parts)) if parts else "No change"
    if operation == Operation.CREATE_COLLECTION.value:
        return "Now: not in the new collection", "Change: add to the new collection"
    member = row.get("in_collection")
    now = "Now: in this collection" if member else "Now: not in this collection"
    membership = change.get("membership")
    if membership == "add":
        return now, "Change: add to the collection"
    if membership == "remove":
        return now, "Change: remove from the collection"
    return now, "No change"


def review_lines(payload, *, names=None, width=WIDTH):
    """(text, icon) lines for a review card, each at most ``width`` characters."""
    names = names or {}
    lines = []
    phase = payload.get("phase", "UNAVAILABLE")
    operation = payload.get("operation")
    if operation in OPERATION_LABELS:
        lines.append((OPERATION_LABELS[operation], "NONE"))
        if "project_id" in payload:
            lines.append((connection_label(payload.get("project_id")), "NONE"))
        for text in _target(payload, names):
            _wrapped(lines, text, width=width)
    assets = {row["asset_id"]: row for row in payload.get("assets") or ()}
    message = payload.get("message") or ""
    if phase == "PREPARING":
        _wrapped(lines, "Reading the current state; nothing has been sent", "TIME", width)
    elif phase == "READY":
        for row in assets.values():
            _wrapped(lines, clip(row.get("name") or row["asset_id"], width), "DOT", width)
            for text in _asset_change(payload, row):
                _wrapped(lines, text, width=width)
        count = payload.get("request_count") or 0
        noun = "request" if count == 1 else "requests"
        _wrapped(lines, f"Apply sends {count} {noun} once, with no retry", "INFO", width)
        expires = payload.get("expires_in")
        if expires is not None:
            minutes = max(1, -(-int(expires) // 60))
            _wrapped(lines, f"This review expires in {minutes} min", "TIME", width)
        _wrapped(lines, NOTICE, "INFO", width)
    elif phase == "APPLYING":
        _wrapped(
            lines,
            "Applying once; the verified result appears here. Nothing is resent automatically",
            "TIME",
            width,
        )
    elif phase == "FINISHED" and payload.get("result"):
        result = payload["result"]
        label, icon = RESULT_LABELS.get(result.get("state"), ("Unconfirmed", "ERROR"))
        _wrapped(lines, "Result: " + label, icon, width)
        if result.get("create_outcome"):
            text = OUTCOME_LABELS.get(result["create_outcome"], result["create_outcome"])
            if result.get("create_status"):
                text += f" (HTTP {result['create_status']})"
            _wrapped(lines, "New collection: " + text, width=width)
        for outcome in result.get("outcomes") or ():
            row = assets.get(outcome["asset_id"]) or {}
            name = clip(row.get("name") or outcome["asset_id"], width - 2)
            text = OUTCOME_LABELS.get(outcome["state"], outcome["state"])
            if outcome.get("status"):
                text += f" (HTTP {outcome['status']})"
            _wrapped(lines, name, "DOT", width)
            _wrapped(lines, text, width=width)
            if outcome.get("tags") is not None and operation == Operation.UPDATE_TAGS.value:
                _wrapped(lines, "Read back: " + tags_summary(outcome["tags"]), width=width)
        if message:
            _wrapped(lines, message, "INFO", width)
    else:
        icon = "INFO" if phase in {"UNCHANGED", "DISCARDED"} else "ERROR"
        _wrapped(lines, message or "This review is no longer available", icon, width)
        if phase == "NOT_SENT":
            _wrapped(lines, "Nothing was sent; prepare the change again when ready", "INFO", width)
        existing = payload.get("existing_collection_ids") or ()
        if existing:
            known = [names.get(identifier) or identifier for identifier in existing]
            _wrapped(lines, label_summary("Existing: ", known), width=width)
    return lines
