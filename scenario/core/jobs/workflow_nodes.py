# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Waiting workflow approval and selection steps read from a retrieved job. No bpy.

Polling already retrieves each known workflow job with SDK `jobs.retrieve`
through `SDKAdapter.job`. A workflow job stays `in-progress` while a
`user-approval` or `user-selection` node of its `metadata.flow` is
`processing`: Scenario then waits for one decision, which
`SDKAdapter.workflow_decision` sends. This module only projects those nodes
into bounded, immutable steps; it sends and stores nothing.

Signed asset URLs in the flow are never copied. `review_id` hashes every
projected field with the remote job ID, so a decision is bound to the exact
step a person reviewed.
"""

import hashlib
import json
from dataclasses import asdict, dataclass, replace

from .store import _identity

# Waiting step types and the decisions their documented endpoints accept.
STEP_ACTIONS = {
    "user-approval": ("approve", "reject"),
    "user-selection": ("select", "reject"),
}
MAX_FLOW_NODES = 2048
MAX_ITEMS = 50
MAX_ITEM_LENGTH = 4096
MAX_REVIEW_ASSETS = 50
MAX_DEPENDENCIES = 64
MAX_NODE_ID = 1024
# Upper bound on references read from one flow, so a hostile response cannot
# make the projection walk an unbounded nested input structure.
_REFERENCE_BUDGET = 100_000
# The API reference's default and largest pick counts for a selection step.
DEFAULT_MINIMUM, DEFAULT_MAXIMUM = 1, 100
# Nodes whose run count can grow with the items a selection passes on: a
# ForEach loop, or a nested workflow whose own loops this flow does not show.
LOOPING = frozenset({"for-each", "workflow"})
_ARRAY_KINDS = {"file_array": "asset", "string_array": "text"}
# Why a step offers only rejection (or nothing, without a sendable node ID).
BLOCKED = {
    "loop": (
        "This selection feeds a ForEach loop or a nested workflow, which the approved "
        "price may not cover, so choosing items is blocked here. Rejecting the step "
        "stops the workflow."
    ),
    "unsupported": (
        "This selection cannot be reviewed here: its candidates or limits are missing, "
        "too many or unreadable. Rejecting the step stops the workflow."
    ),
    "unidentified": (
        "This step's node ID is unreadable or not unique, so no decision can be sent "
        "for it from here."
    ),
}


class StepError(ValueError):
    """The job or decision does not match a readable waiting step; nothing was sent."""


@dataclass(frozen=True)
class PendingStep:
    """One waiting approval or selection step, without URLs.

    `items` are a selection's frozen candidates: asset IDs for a `file_array`
    input (`item_kind` "asset") or texts for a `string_array` input ("text").
    `minimum` and `maximum` bound the pick count as declared. `actions` lists
    the decisions this extension may send. `blocked` names why choosing is
    unavailable: "loop" or "unsupported" leave rejection, while "unidentified"
    (an unreadable or repeated node ID) leaves no decision at all.
    """

    node_id: str
    node_type: str
    iteration_index: int | None
    loop_node_id: str | None
    depends_on: tuple
    review_asset_ids: tuple
    review_asset_total: int
    items: tuple
    item_kind: str | None
    minimum: int | None
    maximum: int | None
    actions: tuple
    blocked: str
    review_id: str = ""

    def summary(self):
        """JSON-ready fields shared by status reports; no URL is ever present."""
        return {
            "node_id": self.node_id,
            "type": self.node_type,
            "iteration_index": self.iteration_index,
            "loop_node_id": self.loop_node_id,
            "depends_on": list(self.depends_on),
            "review_asset_ids": list(self.review_asset_ids),
            "review_asset_total": self.review_asset_total,
            "items": list(self.items),
            "item_kind": self.item_kind,
            "min": self.minimum,
            "max": self.maximum,
            "actions": list(self.actions),
            "blocked": self.blocked or None,
            "review_id": self.review_id,
        }


def _node_id(value):
    """Mirror the adapter's body-only node ID rule, so a projected ID is sendable."""
    return (
        isinstance(value, str)
        and bool(value)
        and value.strip() == value
        and len(value) <= MAX_NODE_ID
        and value.isprintable()
    )


def _asset_id(value):
    try:
        _identity(value)
    except ValueError:
        return False
    return True


def _whole(value, default):
    """A JSON integer (or integral float), the default when absent, else None."""
    if value is None:
        return default
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    if isinstance(value, float):
        if not value.is_integer():
            return None
        value = int(value)
    return value


def _references(node, budget):
    """Upstream node IDs of one flow node, or None when its references are unreadable."""
    found = set()
    depends = node.get("dependsOn")
    if depends is not None:
        if not isinstance(depends, list) or not all(isinstance(item, str) for item in depends):
            return None
        found.update(depends)
    inputs = node.get("inputs")
    if inputs is None:
        return found
    if not isinstance(inputs, list):
        return None
    pending = list(inputs)
    while pending:
        budget[0] -= 1
        if budget[0] < 0:
            return None
        item = pending.pop()
        if not isinstance(item, dict):
            return None
        ref = item.get("ref")
        if ref is not None:
            if not isinstance(ref, dict):
                return None
            target = ref.get("node")
            if target is not None:
                if not isinstance(target, str):
                    return None
                found.add(target)
            conditional = ref.get("conditional")
            if conditional is not None:
                if not isinstance(conditional, list) or not all(
                    isinstance(value, str) for value in conditional
                ):
                    return None
                found.update(conditional)
        if item.get("type") == "inputs_array" and item.get("items") is not None:
            groups = item["items"]
            if not isinstance(groups, list) or not all(isinstance(g, list) for g in groups):
                return None
            for group in groups:
                pending.extend(group)
    return found


class _Flow:
    """Node index and downstream edges of one retrieved flow."""

    def __init__(self, nodes):
        self.by_id = {}
        self.children = {}
        self.unreadable = False
        budget = [_REFERENCE_BUDGET]
        for node in nodes:
            self.by_id.setdefault(node["id"], []).append(node)
        for node in nodes:
            references = _references(node, budget)
            if references is None:
                self.unreadable = True
                continue
            for reference in references:
                self.children.setdefault(reference, set()).add(node["id"])
        self.looping = any(node["type"] in LOOPING for node in nodes)

    def feeds_loop(self, node_id):
        """Whether anything that reads this node, directly or not, may loop over it.

        Unreadable references anywhere in a flow that has a loop count as
        feeding it, so a parsing gap never unblocks a selection.
        """
        if self.unreadable and self.looping:
            return True
        seen, queue = {node_id}, [node_id]
        while queue:
            for child in self.children.get(queue.pop(), ()):
                if child in seen:
                    continue
                if any(node["type"] in LOOPING for node in self.by_id.get(child, ())):
                    return True
                seen.add(child)
                queue.append(child)
        return False

    def review_assets(self, depends_on):
        assets = []
        for dependency in depends_on:
            for node in self.by_id.get(dependency, ()):
                values = node.get("assets")
                if not isinstance(values, list):
                    continue
                for value in values:
                    asset = value.get("assetId") if isinstance(value, dict) else None
                    if _asset_id(asset) and asset not in assets:
                        assets.append(asset)
        return assets


def _selection(node):
    """Return (items, item_kind, minimum, maximum, readable) for a selection node."""
    inputs = node.get("inputs")
    arrays = (
        [item for item in inputs if isinstance(item, dict) and item.get("type") in _ARRAY_KINDS]
        if isinstance(inputs, list)
        else []
    )
    if len(arrays) != 1:
        return (), None, None, None, False
    array = arrays[0]
    kind = _ARRAY_KINDS[array["type"]]
    minimum = _whole(array.get("min"), DEFAULT_MINIMUM)
    maximum = _whole(array.get("max"), DEFAULT_MAXIMUM)
    readable = (
        minimum is not None
        and maximum is not None
        and DEFAULT_MINIMUM <= minimum <= maximum <= DEFAULT_MAXIMUM
    )
    values = node.get("items")
    items = ()
    if (
        isinstance(values, list)
        and 0 < len(values) <= MAX_ITEMS
        and all(isinstance(value, str) and len(value) <= MAX_ITEM_LENGTH for value in values)
        and (kind != "asset" or all(_asset_id(value) for value in values))
    ):
        try:
            for value in values:
                value.encode("utf-8")
        except UnicodeEncodeError:
            pass
        else:
            items = tuple(values)
    readable = readable and bool(items) and minimum <= len(items)
    return items, kind, minimum, maximum, readable


def _step(node, flow, duplicate):
    node_id = node["id"]
    node_type = node["type"]
    iteration = _whole(node.get("iterationIndex"), None)
    loop = node.get("loopNodeId")
    depends = node.get("dependsOn")
    depends_on = (
        tuple(value for value in depends if _node_id(value))[:MAX_DEPENDENCIES]
        if isinstance(depends, list)
        else ()
    )
    blocked = ""
    items, kind, minimum, maximum = (), None, None, None
    assets = []
    if node_type == "user-approval":
        assets = flow.review_assets(depends_on)
    else:
        items, kind, minimum, maximum, readable = _selection(node)
        if not readable:
            blocked = "unsupported"
        elif flow.feeds_loop(node_id):
            blocked = "loop"
    sendable = _node_id(node_id) and not duplicate
    if not sendable:
        blocked, actions = "unidentified", ()
    elif blocked:
        actions = ("reject",)
    else:
        actions = STEP_ACTIONS[node_type]
    return PendingStep(
        node_id=node_id if sendable else node_id[:MAX_NODE_ID],
        node_type=node_type,
        iteration_index=iteration if iteration is not None and iteration >= 0 else None,
        loop_node_id=loop if _node_id(loop) else None,
        depends_on=depends_on,
        review_asset_ids=tuple(assets[:MAX_REVIEW_ASSETS]),
        review_asset_total=len(assets),
        items=items,
        item_kind=kind,
        minimum=minimum,
        maximum=maximum,
        actions=actions,
        blocked=blocked,
    )


def review_id(step, remote_job_id):
    """SHA-256 of the canonical projected fields and the remote job ID."""
    fields = asdict(replace(step, review_id=""))
    canonical = json.dumps(
        {"remote_job_id": remote_job_id, **fields}, sort_keys=True, separators=(",", ":")
    )
    return hashlib.sha256(canonical.encode()).hexdigest()


def _metadata_workflow(metadata, workflow_id):
    inputs = metadata.get("input")
    for value in (
        metadata.get("workflowId"),
        inputs.get("workflowId") if isinstance(inputs, dict) else None,
    ):
        if isinstance(value, str) and value != workflow_id:
            raise StepError("Scenario returned another workflow's job")


def pending_steps(job, *, remote_job_id, workflow_id):
    """Project the waiting steps of one retrieved workflow job, in flow order.

    Raises StepError when the response is not this workflow's job or its flow
    is malformed. A job without a flow, or with no `processing` approval or
    selection node, has no waiting step.
    """
    if not isinstance(job, dict) or job.get("jobId") != remote_job_id:
        raise StepError("Scenario returned another job")
    if job.get("jobType") != "workflow":
        raise StepError("Scenario did not report a workflow job")
    metadata = job.get("metadata")
    if metadata is None:
        return ()
    if not isinstance(metadata, dict):
        raise StepError("Scenario returned unreadable workflow metadata")
    _metadata_workflow(metadata, workflow_id)
    flow = metadata.get("flow")
    if flow is None:
        return ()
    if not isinstance(flow, list) or len(flow) > MAX_FLOW_NODES:
        raise StepError("Scenario returned an unreadable workflow flow")
    for node in flow:
        if not isinstance(node, dict) or not all(
            isinstance(node.get(key), str) for key in ("id", "type", "status")
        ):
            raise StepError("Scenario returned an unreadable workflow flow")
    waiting = [
        node for node in flow if node["status"] == "processing" and node["type"] in STEP_ACTIONS
    ]
    if not waiting:
        return ()
    graph = _Flow(flow)
    counts = {}
    for node in waiting:
        counts[node["id"]] = counts.get(node["id"], 0) + 1
    steps = []
    for node in waiting:
        step = _step(node, graph, counts[node["id"]] > 1)
        steps.append(replace(step, review_id=review_id(step, remote_job_id)))
    return tuple(steps)


def validate_selection(step, indices):
    """Return the ordered picks when they fit the step's candidates and bounds."""
    if not isinstance(indices, (list, tuple)):
        raise StepError("Selected items must be a list of indices")
    picks = tuple(indices)
    if any(type(value) is not int for value in picks):
        raise StepError("Selected items must be integer indices")
    if len(set(picks)) != len(picks):
        raise StepError("Select each item at most once")
    if any(not 0 <= value < len(step.items) for value in picks):
        raise StepError("Select only listed candidates")
    upper = min(step.maximum, len(step.items))
    if not step.minimum <= len(picks) <= upper:
        if step.minimum == upper:
            raise StepError(f"Select exactly {upper} item{'s' if upper != 1 else ''}")
        raise StepError(f"Select {step.minimum} to {upper} items")
    return picks


def validate_decision(step, action, selected_indices=None):
    """Check one decision against a projected step; return the picks for a selection."""
    if not isinstance(action, str) or action not in step.actions:
        if step.blocked and action in STEP_ACTIONS.get(step.node_type, ()):
            raise StepError(BLOCKED[step.blocked])
        raise StepError("Choose a decision this workflow step accepts")
    if action != "select":
        if selected_indices is not None:
            raise StepError("Only a selection sends selected items")
        return None
    return validate_selection(step, selected_indices)
