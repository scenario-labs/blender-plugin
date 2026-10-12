# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Waiting workflow approval and selection steps read from a retrieved job. No bpy.

Polling already retrieves each known workflow job with SDK `jobs.retrieve`
through `SDKAdapter.job`. A workflow job stays `in-progress` while a
`user-approval` or `user-selection` node of its `metadata.flow` is
`processing`: Scenario then waits for one decision, which
`SDKAdapter.workflow_decision` sends. This module only projects those nodes
into bounded, immutable steps; it sends and stores nothing.

A retrieved job's flow may omit the links between nodes: live jobs list
`inputs` only on `user-selection` nodes and no `dependsOn` at all. The
workflow definition (SDK `workflows.retrieve` through `SDKAdapter.workflow`)
carries them; `definition_links` reads them, and `pending_steps` uses them only
when the definition describes the job exactly. Missing or untrusted links never
unblock a selection in a flow that may loop.

Signed asset URLs in the flow are never copied. `review_id` hashes every
projected field with the remote job ID, so a decision is bound to the exact
step a person reviewed.
"""

import hashlib
import json
import re
from dataclasses import asdict, dataclass, replace
from datetime import datetime

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
# Flow node types the API reference lists. Any other type may loop too, so it
# blocks a selection like LOOPING: an unknown type never unblocks choosing items.
DOCUMENTED_TYPES = frozenset(
    {
        "custom-model",
        "for-each",
        "generate-prompt",
        "list",
        "logic",
        "model",
        "remove-background",
        "transform",
        "user-approval",
        "user-selection",
        "workflow",
    }
)
_ARRAY_KINDS = {"file_array": "asset", "string_array": "text"}
# A ForEach copy of a loop body node, as live job flows name them.
_COPY = re.compile(r"(.+)__iter__(0|[1-9][0-9]{0,5})")
# Why a step offers only rejection (or nothing, without a sendable node ID).
BLOCKED = {
    "loop": (
        "This selection feeds a ForEach loop, a nested workflow or a step type this "
        "extension does not know, which the approved price may not cover, so choosing "
        "items is blocked here. Rejecting the step stops the workflow."
    ),
    "unverified": (
        "This extension could not read how this workflow's steps connect, and the "
        "workflow contains a ForEach loop, a nested workflow or a step type this "
        "extension does not know. The selection may feed it, which the approved price "
        "may not cover, so choosing items is blocked here. Rejecting the step stops "
        "the workflow."
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
    unavailable: "loop", "unverified" (unknown links in a flow that may loop)
    or "unsupported" leave rejection, while "unidentified" (an unreadable or
    repeated node ID) leaves no decision at all. `depends_on` lists at most
    MAX_DEPENDENCIES IDs, but the review assets come from every dependency.
    `links_complete` is False when some node's links are unknown, so
    `depends_on` and the review assets may be incomplete.
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
    links_complete: bool
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
            "links_complete": self.links_complete,
            "review_id": self.review_id,
        }


@dataclass(frozen=True)
class FlowLinks:
    """Node links read from one workflow definition, without values or URLs.

    `nodes` holds (node ID, type, upstream node IDs, `dependsOn`) per
    definition node, `loop_bodies` the IDs ForEach nodes clone per item, and
    `updated_at` the definition's `updatedAt`.
    """

    workflow_id: str
    updated_at: str
    nodes: tuple
    loop_bodies: frozenset


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


def _depends(node):
    """A node's `dependsOn` IDs, () when absent, None when unreadable."""
    depends = node.get("dependsOn")
    if depends is None:
        return ()
    if not isinstance(depends, list) or not all(isinstance(item, str) for item in depends):
        return None
    return tuple(depends)


def _input_references(inputs, budget):
    """Node IDs a node's `inputs` reference, none when absent, None when unreadable."""
    found = set()
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


def _may_loop(kind):
    """A ForEach loop, a nested workflow or a node type the API reference does not list."""
    return kind in LOOPING or kind not in DOCUMENTED_TYPES


def _timestamp(value):
    """A timezone-aware time from an ISO 8601 string, else None."""
    if not isinstance(value, str) or len(value) > 64:
        return None
    try:
        moment = datetime.fromisoformat(value)
    except ValueError:
        return None
    return moment if moment.tzinfo is not None else None


def definition_links(workflow, *, workflow_id):
    """Read the node links of one retrieved workflow definition; keep no values or URLs.

    `workflow` is the record `SDKAdapter.workflow` returns (SDK
    `workflows.retrieve`). In a definition, a node without `dependsOn` or
    `inputs` reads no other node. Raises StepError when the record is not this
    workflow's, or its flow, links or `updatedAt` are unreadable.
    """
    if not isinstance(workflow, dict) or workflow.get("id") != workflow_id:
        raise StepError("Scenario returned another workflow")
    flow = workflow.get("flow")
    updated = workflow.get("updatedAt")
    if (
        _timestamp(updated) is None
        or not isinstance(flow, list)
        or not 0 < len(flow) <= MAX_FLOW_NODES
    ):
        raise StepError("Scenario returned an unreadable workflow definition")
    budget = [_REFERENCE_BUDGET]
    entries, bodies = {}, set()
    for node in flow:
        if (
            not isinstance(node, dict)
            or not isinstance(node.get("id"), str)
            or not isinstance(node.get("type"), str)
            or node["id"] in entries
        ):
            raise StepError("Scenario returned an unreadable workflow definition")
        depends = _depends(node)
        inputs = _input_references(node.get("inputs"), budget)
        body = node.get("loopBodyNodeIds")
        if (
            depends is None
            or inputs is None
            or (
                body is not None
                and (not isinstance(body, list) or not all(isinstance(item, str) for item in body))
            )
        ):
            raise StepError("Scenario returned unreadable workflow step links")
        bodies.update(body or ())
        entries[node["id"]] = (node["id"], node["type"], tuple(sorted(inputs)), depends)
    return FlowLinks(workflow_id, updated, tuple(entries.values()), frozenset(bodies))


def waiting(job):
    """Whether a retrieved job lists a `processing` approval or selection node; never raises."""
    metadata = job.get("metadata") if isinstance(job, dict) else None
    flow = metadata.get("flow") if isinstance(metadata, dict) else None
    return isinstance(flow, list) and any(
        isinstance(node, dict)
        and node.get("status") == "processing"
        and isinstance(node.get("type"), str)
        and node["type"] in STEP_ACTIONS
        for node in flow[:MAX_FLOW_NODES]
    )


def _described(links, job, flow, workflow_id):
    """Map the job's ForEach copies to their templates when `links` describe it, else None.

    The definition must be this workflow's, unchanged since the job was
    created, list the job's nodes with the same types and agree with every
    link the job flow shows itself. Any other job node must be a copy of a
    loop body node of the same type.
    """
    if links is None or links.workflow_id != workflow_id:
        return None
    created, updated = _timestamp(job.get("createdAt")), _timestamp(links.updated_at)
    if created is None or updated is None or updated > created:
        return None
    known = {entry[0]: entry for entry in links.nodes}
    budget = [_REFERENCE_BUDGET]
    templates, present = {}, set()
    for node in flow:
        node_id, kind = node["id"], node["type"]
        entry = known.get(node_id)
        if entry is not None:
            if entry[1] != kind:
                return None
            if node.get("dependsOn") is not None:
                depends = _depends(node)
                if depends is None or set(depends) != set(entry[3]):
                    return None
            if node.get("inputs") is not None:
                if _input_references(node["inputs"], budget) != set(entry[2]):
                    return None
            present.add(node_id)
            continue
        copy = _COPY.fullmatch(node_id)
        template = known.get(copy[1]) if copy is not None else None
        if template is None or template[1] != kind or copy[1] not in links.loop_bodies:
            return None
        templates[node_id] = copy[1]
    return templates if present == known.keys() else None


class _Flow:
    """Node index and downstream edges of one retrieved flow.

    Edges come from the workflow definition when it describes the job, else
    from the job flow, where a node with neither `dependsOn` nor `inputs` has
    unknown links. Assets are always read from the job.
    """

    def __init__(self, job, nodes, workflow_id, links):
        self.by_id = {}
        for node in nodes:
            self.by_id.setdefault(node["id"], []).append(node)
        self.kinds, self.children, self.depends = {}, {}, {}
        self.unknown = False
        templates = _described(links, job, nodes, workflow_id)
        if templates is None:
            self.templates = {}
            budget = [_REFERENCE_BUDGET]
            entries = []
            for node in nodes:
                references = None
                if node.get("dependsOn") is not None or node.get("inputs") is not None:
                    depends = _depends(node)
                    inputs = _input_references(node.get("inputs"), budget)
                    if depends is not None and inputs is not None:
                        references = inputs.union(depends)
                entries.append((node["id"], node["type"], references))
        else:
            self.templates = templates
            entries = [(entry[0], entry[1], {*entry[2], *entry[3]}) for entry in links.nodes]
            self.depends = {entry[0]: entry[3] for entry in links.nodes}
        for node_id, kind, references in entries:
            self.kinds.setdefault(node_id, set()).add(kind)
            if references is None:
                self.unknown = True
                continue
            for reference in references:
                self.children.setdefault(reference, set()).add(node_id)
        self.looping = any(_may_loop(kind) for kinds in self.kinds.values() for kind in kinds)

    def loop_block(self, node_id):
        """Why choosing this node's items is blocked by loops, or "" when it is not.

        "loop" when anything reading the node, directly or not, may loop over
        it. Otherwise "unverified" when some node's links are unknown in a flow
        with a loop, a nested workflow or an undocumented node type, so a
        parsing gap never unblocks a selection.
        """
        start = self.templates.get(node_id, node_id)
        seen, queue = {start}, [start]
        while queue:
            for child in self.children.get(queue.pop(), ()):
                if child in seen:
                    continue
                if any(_may_loop(kind) for kind in self.kinds.get(child, ())):
                    return "loop"
                seen.add(child)
                queue.append(child)
        return "unverified" if self.unknown and self.looping else ""

    def dependencies(self, node):
        """The step's `dependsOn` and the definition's, without repeats.

        In a ForEach copy, a dependency's copy from the same iteration replaces
        the dependency, so an approval reviews its own iteration's results.
        """
        node_id = node["id"]
        template = self.templates.get(node_id)
        values = list(_depends(node) or ())
        values.extend(self.depends.get(template or node_id, ()))
        if template is not None:
            suffix = "__iter__" + _COPY.fullmatch(node_id)[2]
            values = [value + suffix if value + suffix in self.by_id else value for value in values]
        # A dict keeps the first occurrences in order and finds repeats in
        # constant time, so a long hostile list is read once.
        return tuple(dict.fromkeys(value for value in values if _node_id(value)))

    def review_assets(self, depends_on):
        assets = {}
        for dependency in depends_on:
            for node in self.by_id.get(dependency, ()):
                values = node.get("assets")
                if not isinstance(values, list):
                    continue
                for value in values:
                    asset = value.get("assetId") if isinstance(value, dict) else None
                    if _asset_id(asset):
                        assets[asset] = None
        return list(assets)


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
    depends_on = flow.dependencies(node)
    blocked = ""
    items, kind, minimum, maximum = (), None, None, None
    assets = []
    if node_type == "user-approval":
        assets = flow.review_assets(depends_on)
    else:
        items, kind, minimum, maximum, readable = _selection(node)
        blocked = flow.loop_block(node_id) if readable else "unsupported"
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
        depends_on=depends_on[:MAX_DEPENDENCIES],
        review_asset_ids=tuple(assets[:MAX_REVIEW_ASSETS]),
        review_asset_total=len(assets),
        items=items,
        item_kind=kind,
        minimum=minimum,
        maximum=maximum,
        actions=actions,
        blocked=blocked,
        links_complete=not flow.unknown,
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


def pending_steps(job, *, remote_job_id, workflow_id, links=None):
    """Project the waiting steps of one retrieved workflow job, in flow order.

    `links` are this workflow's `definition_links`, or None when its definition
    was not read. They replace the job flow's own links only when they
    describe this job exactly; otherwise unknown links block choosing items in
    a flow that may loop. Raises StepError when the response is not this
    workflow's job or its flow is malformed. A job without a flow, or with no
    `processing` approval or selection node, has no waiting step.
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
    paused = [
        node for node in flow if node["status"] == "processing" and node["type"] in STEP_ACTIONS
    ]
    if not paused:
        return ()
    graph = _Flow(job, flow, workflow_id, links)
    counts = {}
    for node in paused:
        counts[node["id"]] = counts.get(node["id"], 0) + 1
    steps = []
    for node in paused:
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
