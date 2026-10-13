# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Trained LoRAs and compositions in the picker and the generation forms (#97, main thread).

The selected connection's private trained list and public LoRAs load with the
catalog. Base-model descriptions, which declare the LoRA inputs, are read only
when the picker shows its Trained chip, in lane order and once per connection.
A lane keeps its choice as scope-tagged slots; every request rebuilds the LoRA
inputs from the base's REST schema with trained_routes.apply, the same function
local MCP and the quote check use. trained_section draws the choice with its
strengths, and trained_defaults keeps the explicit per-scope project defaults.
"""

import math
from dataclasses import dataclass

import bpy
from bpy.props import IntProperty, StringProperty

from ..core.api import catalog, trained_offers
from ..core.api.errors import ScenarioError
from ..core.api.trained_routes import LoraSlot, Pick, RouteError, apply
from ..core.schema.forms import lora_component, record_schema
from ..core.ui import capability_status
from . import props, runtime
from .reference_form import scope_key

SCOPE = "_scenario_trained_scope"
LANES = ("image", "render_image")
# Trained models run; only their acceptance is pending, so the line must not read as a refusal.
EXPERIMENTAL = capability_status.label("LoRAs and compositions")
LOADING = "Loading trained models"
OTHER_SCOPE = "A trained model was chosen for another connection or project; choose it again"
KIND_LABELS = {catalog.TRAINED_LORA: "LoRA", catalog.TRAINED_COMPOSITION: "Composition"}
_hidden = {}  # model_id -> (record, names): LoRA inputs the form must not draw as text
_slots = {}  # model_id -> (record, LoraSlot or None): the LoRA slot a base declares


def trained_lane(lane):
    """The form a trained choice lands in: Image, or Render Image when chosen from it."""
    return lane if lane in LANES else "image"


def kind_label(kind):
    return KIND_LABELS.get(kind, "Trained model")


def kind_text(record, kind):
    """The kind's label, such as LoRA or Private composition when the connection owns it."""
    label = kind_label(kind)
    if not is_private(record):
        return label
    return f"Private {label if label == 'LoRA' else label.lower()}"


def is_private(record):
    """Whether a record belongs to the selected connection rather than the public catalog."""
    return getattr(record, "privacy", "") in ("private", "unlisted") or (
        getattr(record, "id", None) in runtime.state.trained_private
    )


# -- catalog loading -----------------------------------------------------------------
def clear():
    """Forget trained records and base-read progress of a retired connection."""
    state = runtime.state
    state.trained_pairs = []
    state.trained_records = {}
    state.trained_private = set()
    state.trained_loading = False
    state.trained_loaded = False
    state.trained_error = ""
    state.trained_scans = {}
    state.trained_defaults = None
    _hidden.clear()
    _slots.clear()
    from . import trained_defaults

    trained_defaults.forget()


def request(manager, connection):
    """Queue one read of the private trained list; a failure never blocks public lanes."""
    state = runtime.state
    if state.trained_loading:
        return False
    state.trained_loading = True
    # An explicit refresh may retry base descriptions that failed before.
    for scan in state.trained_scans.values():
        if not scan["pending"]:
            scan["attempted"].clear()
    manager.fetch_trained(connection)
    return True


def on_catalog(pairs, private=()):
    """Deliver the trained list; base reads then start for a picker already on Trained."""
    state = runtime.state
    state.trained_pairs = list(pairs)
    state.trained_records = {record.id: record for _kind, record in state.trained_pairs}
    state.trained_private = set(private)
    state.trained_loading = False
    state.trained_loaded = True
    state.trained_error = ""
    _rearm_selections()
    from . import model_picker

    if model_picker.trained_view_open():  # never for a closed dialog's leftover chip
        request_bases(model_picker._ctx["lane"])
    _refresh_picker()


def on_catalog_failed(reason):
    state = runtime.state
    state.trained_loading = False
    state.trained_error = str(reason) or "Could not read trained models"
    _rearm_selections()
    _refresh_picker()


def _rearm_selections():
    """Reprice lanes whose trained choice waited for this list; quoted forms stay quoted.

    A choice adopted from an earlier version's text field (adopt_typed) or
    restored before the list arrived (restore) shows its ID until then; every
    choice the list names takes its listed kind and name, and only a LoRA keeps
    the strength it was restored with.
    """
    state = runtime.state
    kinds = {record.id: kind for kind, record in state.trained_pairs}
    for scene in bpy.data.scenes:
        if not hasattr(scene, "scenario"):
            continue
        for lane in props.GENERATION_LANES:
            lane_state = scene.scenario.lane_state(lane)
            for slot in lane_state.trained:
                kind = kinds.get(slot.model_id)
                if kind not in catalog.USABLE_TRAINED_KINDS:
                    continue
                name = state.trained_records[slot.model_id].name
                if (slot.kind, slot.name) != (kind, name):
                    slot.kind, slot.name = kind, name
                    if kind != catalog.TRAINED_LORA:
                        slot.has_scale = False  # a composition applies its own strengths
            if len(lane_state.trained) and lane_state.estimate_state in ("UNAVAILABLE", "IDLE"):
                props.mark_estimate_dirty(lane_state)


def _refresh_picker():
    from . import model_picker

    model_picker.refresh_trained()


def _scan(lane):
    return runtime.state.trained_scans.setdefault(
        lane,
        {
            "pending": False,
            "checked": 0,
            "total": 0,
            "failed": 0,
            "error": "",
            "ids": (),  # the running scan's models, in read order
            "attempted": set(),  # models a scan reached; only a refresh reads them again
        },
    )


def request_bases(lane):
    """Read the descriptions of this lane's base models that are still unknown.

    Runs only for a picker showing trained models, never on catalog refresh.
    Descriptions are cached per connection, so each base is read at most once
    unless an explicit refresh retries failures. Models a stopped scan never
    reached are read by the next call. Returns whether reads are pending.
    """
    lane = trained_lane(lane)
    runtime.sync_catalog_context()  # may retire the connection and its scans first
    state = runtime.state
    scan = _scan(lane)
    if scan["pending"]:
        return True
    if not state.trained_loaded and not state.trained_loading and runtime.online():
        # The Trained chip retries a failed private list read; it never runs on its own.
        try:
            request(runtime.ensure_manager(), runtime.ensure_catalog())
        except ScenarioError as err:
            state.trained_error = err.reason
        return False
    if not state.trained_loaded or not any(
        kind in catalog.USABLE_TRAINED_KINDS for kind, _record in state.trained_pairs
    ):
        return False
    if not runtime.online():
        scan["error"] = "Online access is disabled; base models cannot be checked"
        return False
    try:
        manager = runtime.ensure_manager()
        connection = runtime.ensure_catalog()
    except ScenarioError as err:
        scan["error"] = err.reason
        return False
    ids = trained_offers.base_candidates(lane, list(state.records.values()), scan["attempted"])
    if not ids:
        return False
    scan.update(pending=True, checked=0, total=len(ids), failed=0, error="", ids=tuple(ids))
    manager.fetch_base_schemas(connection, lane, ids)
    return True


def on_bases(payload):
    from . import generation

    scan = _scan(payload["lane"])
    if payload["detailed"]:
        generation.set_models(payload["detailed"], {}, mark_dirty=False)
    # Only the models this scan reached count as attempted: when three failures in a
    # row stop it, the next Trained chip reads the rest.
    scan["attempted"].update(scan["ids"][: payload["checked"]])
    scan.update(
        checked=payload["checked"],
        total=payload["total"],
        failed=payload["failed"],
        error=payload["error"],
        pending=not payload["done"],
    )
    _refresh_picker()


def stop_scan(payload, reason):
    """End a lane's scan whose progress could not be applied; a refresh lets the chip retry it."""
    lane = payload.get("lane") if isinstance(payload, dict) else None
    scan = runtime.state.trained_scans.get(trained_lane(lane)) if isinstance(lane, str) else None
    if scan is not None:
        scan.update(pending=False, error=reason)


def scan_status(lane):
    """A read-only line about base descriptions for the picker, or ""."""
    scan = runtime.state.trained_scans.get(trained_lane(lane))
    if scan is None:
        return ""
    if scan["pending"]:
        return f"Checking base models for LoRA inputs: {scan['checked']} of {scan['total']}"
    if scan["error"]:
        return f"Could not check every base model: {scan['error']}"
    return ""


def bases(lane):
    """Detailed base models of the lane that declare a LoRA slot, curated first."""
    return trained_offers.lora_bases(trained_lane(lane), list(runtime.state.records.values()))


def offers(lane):
    """Picker rows for the lane: every listed trained model, available ones first."""
    state = runtime.state
    scan = state.trained_scans.get(trained_lane(lane))
    if scan is None or scan["pending"]:
        unknown = "Checking base models for LoRA inputs..."
    elif scan["error"]:
        unknown = "Base models could not be checked; choose Trained again to retry."
    else:
        unknown = ""
    return trained_offers.offers(state.trained_pairs, bases(lane), unknown=unknown)


# -- lane selections ---------------------------------------------------------------
def current_scope():
    store = runtime.state.job_store
    return None if store is None else scope_key(store.scope)


def scope_error(lane_state):
    """Saved trained choices may only be used in the connection that chose them."""
    if not len(lane_state.trained):
        return None
    scope = current_scope()
    if scope is None or any(slot.get(SCOPE) != scope for slot in lane_state.trained):
        return OTHER_SCOPE
    return None


def slot_scale(slot):
    """The strength a slot sends: rounded, so 32-bit storage never changes the payload."""
    if slot.kind != catalog.TRAINED_LORA or not slot.has_scale:
        return None
    return round(float(slot.scale), trained_offers.STRENGTH_DIGITS)


def picks(lane_state):
    """The lane's choice as picks; a strength is sent only for a LoRA with a control."""
    return tuple(Pick(slot.model_id, slot_scale(slot)) for slot in lane_state.trained)


def apply_to(lane_state, record, body):
    """(body, "") with the lane's trained choice written into the base's LoRA inputs.

    Returns (body, reason) unchanged when the choice cannot run: another scope,
    trained models not loaded, or a route the base's current schema refuses.
    """
    if not len(lane_state.trained):
        return body, ""
    error = scope_error(lane_state)
    if error:
        return body, error
    state = runtime.state
    if not state.trained_loaded:
        if state.trained_error:
            return body, f"Could not load trained models: {state.trained_error}"
        return body, LOADING
    try:
        return apply(record.raw, picks(lane_state), state.trained_records, body), ""
    except RouteError as err:
        return body, str(err)
    except ValueError:
        return body, "Refresh the model; its LoRA inputs could not be read."


def _resolved(chosen, slot, *, visible_start=True):
    """Give every LoRA with a strength control a bounded strength.

    A new choice without one starts at the control's visible value: the LoRA's
    own declared strength, otherwise the web app's default (trained_offers.strength).
    With visible_start=False (a saved job), a LoRA saved without a strength keeps
    none unless the base declares a default, the strength the service applied, so
    the price asks for one (#376).
    """
    records = runtime.state.trained_records
    resolved = []
    for model_id, kind, scale in chosen:
        value = None
        strength = trained_offers.strength(slot, records.get(model_id))
        if kind == catalog.TRAINED_LORA and strength is not None:
            if scale is not None:
                value = strength.clamp(scale)
            elif visible_start:
                value = strength.initial
            elif slot.scale_default is not None:
                value = strength.clamp(slot.scale_default)
        resolved.append((model_id, kind, value))
    return resolved


def write_slots(lane_state, lane, chosen, slot, scope, *, seed=False):
    """Replace the lane's slots with `chosen` (already resolved) for this base slot.

    A LoRA gets a strength control only when it has a strength and the slot
    declares bounds; one without a strength sends the slot's declared default.
    `seed` stores each strength within its bounds without the RNA update, for a
    choice the user did not make in this scene (a project default applied
    automatically): that update would tag the scene and make every origin
    captured in it stale. The caller then re-arms the price.
    """
    strength = trained_offers.strength(slot)
    lane_state.trained.clear()
    for model_id, kind, scale in chosen:
        record = runtime.state.trained_records.get(model_id)
        item = lane_state.trained.add()
        item.model_id, item.kind, item.lane = model_id, kind, lane
        item.name = record.name if record is not None else model_id
        if scale is not None and strength is not None:
            item.fmin, item.fmax = strength.minimum, strength.maximum
            item.has_scale = True
            if seed:
                item["scale"] = strength.clamp(scale)
            else:
                item.scale = scale
        item[SCOPE] = scope


def choose(context, lane, offer, base_id, scale=None):
    """Run `offer` through the chosen base in `lane`; returns the lane it landed in.

    The whole new selection is checked with trained_routes.apply before the
    form changes. Raises ScenarioError with the reason, changing nothing.
    """
    from . import generation, model_picker

    lane = trained_lane(lane)
    if offer is None or not offer.available:
        raise ScenarioError(0, offer.reason if offer is not None else "Choose a trained model")
    base = next((item for item in offer.bases if item.id == base_id), None)
    if base is None:
        raise ScenarioError(0, "Choose the base model to run it with")
    scope = current_scope()
    if scope is None:
        raise ScenarioError(0, "Connect to Scenario before choosing a trained model")
    scene = context.scene
    lane_state = scene.scenario.lane_state(lane)
    same = lane_state.model_id == base.id and scope_error(lane_state) is None
    current = [(slot.model_id, slot.kind, slot_scale(slot)) for slot in lane_state.trained]
    chosen = _resolved(
        trained_offers.merged(current, (offer.id, offer.kind, scale), same_base=same), base.slot
    )
    try:
        apply(
            base.record.raw,
            [Pick(model_id, value) for model_id, _kind, value in chosen],
            runtime.state.trained_records,
        )
    except RouteError as err:
        raise ScenarioError(0, str(err)) from None
    model_picker._show_lane(scene, lane, base.record)
    lane_state.model_key = base.id
    if base.id in [item[0] for item in runtime.enum_items(("models", lane))]:
        if lane_state.model_id != base.id:
            lane_state.model_id = base.id  # its update callback runs on_model_changed
    else:
        generation.request_model(base.id)
    write_slots(lane_state, lane, chosen, base.slot, scope)
    props.mark_estimate_dirty(lane_state)
    return lane


def restore(lane_state, lane, record, payload):
    """Rebuild the lane's choice from a saved payload; returns how many models it could not restore.

    Called by Reload parameters: the form gets exactly the job's LoRAs and
    composition when they are still listed, and nothing from the former form.
    A LoRA the job sent without a strength gets none here either. Models in
    inputs the base's current schema cannot describe count as not restored.

    Before the trained list is loaded (still loading, or its read failed), no
    pick can be checked, so every pick is kept under its ID: a composition from
    the model ID input as a composition without a strength, LoRAs from the stack
    without a kind. The price waits with the list's reason, and
    _rearm_selections gives the picks the list names their listed kind and
    name. A pick it does not name stays and blocks the price with its reason.
    """
    lane_state.trained.clear()
    props.mark_estimate_dirty(lane_state)
    saved = len(trained_offers.saved_ids(record.raw, payload))
    try:
        slot = LoraSlot.from_record(record.raw)
    except ValueError:
        slot = None
    wanted = trained_offers.picks_from_payload(slot, payload) if slot is not None else ()
    named = max(saved, len(wanted))
    scope = current_scope()
    if not wanted or scope is None:
        return named
    state = runtime.state
    if state.trained_loaded:
        kinds = {item.id: kind for kind, item in state.trained_pairs}
        chosen = _resolved(
            [
                (pick.model_id, kinds[pick.model_id], pick.scale)
                for pick in wanted
                if kinds.get(pick.model_id) in catalog.USABLE_TRAINED_KINDS
            ],
            slot,
            visible_start=False,
        )
    else:
        # The model ID input carries only a composition, which applies its own
        # strengths: it waits as one, without the base's default strength. The
        # stack's picks are resolved as LoRAs, the only kind with a strength.
        if slot.model_id_input and payload.get(slot.model_id_input) == wanted[0].model_id:
            chosen = [(wanted[0].model_id, catalog.TRAINED_COMPOSITION, None)]
        else:
            resolved = _resolved(
                [(pick.model_id, catalog.TRAINED_LORA, pick.scale) for pick in wanted],
                slot,
                visible_start=False,
            )
            chosen = [(model_id, "", scale) for model_id, _kind, scale in resolved]
    write_slots(lane_state, trained_lane(lane), chosen, slot, scope)
    return named - len(chosen)


def adopt_typed(lane_state, item):
    """Keep a trained model ID an earlier version saved in a LoRA text field (#97).

    Called by params_ui.sync_params before it drops a form value for one of the
    base's LoRA inputs, which are no longer drawn as text. When the form has no
    trained choice yet, an enabled ID typed into the model input becomes that
    choice instead of disappearing silently from the request: it runs when it
    is listed and the base accepts it, otherwise it blocks the price with the
    reason, and the Model row offers its remove button. A choice saved without
    a connection gets no scope tag and must be chosen again. sync_params prices
    the form again, so a price error saved with the file gives way to the
    current reason. Returns whether a choice was added.
    """
    value = item.str_value.strip()
    if item.ptype != "model" or not item.enabled or not value or len(lane_state.trained):
        return False
    state = runtime.state
    kinds = {record.id: kind for kind, record in state.trained_pairs}
    kind = kinds.get(value, "")
    slot = lane_state.trained.add()
    slot.model_id, slot.lane = value, props.lane_of(lane_state)
    slot.kind = kind if kind in catalog.USABLE_TRAINED_KINDS else ""
    slot.name = state.trained_records[value].name if slot.kind else value
    slot[SCOPE] = current_scope() or ""
    return True


def hidden_inputs(model_id):
    """Names of the LoRA inputs a model declares; the form never draws them as text."""
    record = runtime.state.records.get(model_id)
    if record is None:
        return frozenset()
    cached = _hidden.get(model_id)
    if cached is not None and cached[0] is record:
        return cached[1]
    try:
        component = lora_component(record_schema("model", record.raw))
    except ValueError:
        component = None
    names = frozenset(component.names) if component is not None else frozenset()
    _hidden[model_id] = (record, names)
    return names


def base_slot(model_id):
    """The LoRA slot a described base model declares, or None (read-only, cached per record)."""
    record = runtime.state.records.get(model_id)
    if record is None or not record.parameters:
        return None
    cached = _slots.get(model_id)
    if cached is not None and cached[0] is record:
        return cached[1]
    try:
        slot = LoraSlot.from_record(record.raw)
    except ValueError:
        slot = None
    _slots[model_id] = (record, slot)
    return slot


def base_strength(model_id):
    """The LoRA strength control a described base model declares, or None (read-only).

    Its range is the base's; for where one LoRA's strength starts, use lora_strength.
    """
    slot = base_slot(model_id)
    return trained_offers.strength(slot) if slot is not None else None


def lora_strength(model_id, lora_id):
    """One LoRA's strength control on a described base model, or None (read-only).

    It starts where a newly chosen LoRA does in the picker: at the LoRA's own
    declared strength, otherwise the Scenario web app's default, within the
    base's declared range (trained_offers.strength).
    """
    slot = base_slot(model_id)
    if slot is None:
        return None
    return trained_offers.strength(slot, runtime.state.trained_records.get(lora_id))


def _same_range(slot, strength):
    """Whether a slot holds this range already; its 32-bit bounds never read back 1.2 exactly."""
    return math.isclose(slot.fmin, strength.minimum, rel_tol=1e-6, abs_tol=1e-9) and (
        math.isclose(slot.fmax, strength.maximum, rel_tol=1e-6, abs_tol=1e-9)
    )


def sync_bounds(lane_state):
    """Give each LoRA strength control the range its base declares now (main thread, not draw).

    Called when the base's description is (re)loaded or the base changes. Every
    strength control counts, including one Reload gave a LoRA before the trained
    list named its kind (restore); a composition never has one. A strength
    outside a narrowed range is kept, not changed silently: the request then
    refuses it with the range until the user edits it. A changed range reprices
    the form, so a background catalog refresh never leaves a price standing for
    a strength the request now refuses.

    A base that takes LoRAs but declares no range drops each control, as
    write_slots gives none on that base: the LoRA then sends the base's declared
    default, which the section shows, and the price is re-armed. A base not
    described yet, or without LoRA inputs, changes nothing.
    """
    strength = base_strength(lane_state.model_id)
    controls = [
        slot
        for slot in lane_state.trained
        if slot.has_scale and slot.kind != catalog.TRAINED_COMPOSITION
    ]
    if strength is None:
        if base_slot(lane_state.model_id) is None:
            return
        for slot in controls:
            slot.has_scale = False  # a plain property: no update tags the scene
        changed = bool(controls)
    else:
        changed = False
        for slot in controls:
            if not _same_range(slot, strength):
                slot.fmin, slot.fmax = strength.minimum, strength.maximum
                changed = True
    if changed:
        props.mark_estimate_dirty(lane_state)


def set_strength(lane_state, index):
    """Give a LoRA without a strength the start a newly chosen one gets (#97).

    That is its own declared strength, otherwise the Scenario web app's default,
    within the base's declared range (lora_strength).

    An explicit action: a strength is never added to a request silently. Raises
    ScenarioError when the base declares no strength range.
    """
    if not 0 <= index < len(lane_state.trained):
        raise ScenarioError(0, "Choose a LoRA of this form")
    slot = lane_state.trained[index]
    if slot.kind != catalog.TRAINED_LORA:
        raise ScenarioError(0, "Only a LoRA takes a strength; a composition applies its own")
    strength = lora_strength(lane_state.model_id, slot.model_id)
    if strength is None:
        raise ScenarioError(0, "This base model declares no strength range for its LoRAs")
    slot.fmin, slot.fmax = strength.minimum, strength.maximum
    slot.has_scale = True
    slot.scale = strength.initial  # its update callback invalidates the price
    props.mark_estimate_dirty(lane_state)


def selection_error(lane_state):
    """Why the lane's trained choice cannot run now, or "" (read-only, safe in draw)."""
    if not len(lane_state.trained):
        return ""
    record = runtime.state.records.get(lane_state.model_id)
    if record is None or not record.parameters:
        return ""  # the form already explains a model without its description
    return apply_to(lane_state, record, {})[1]


# -- explicit choices from local MCP ----------------------------------------------------
def listed_reason():
    """Why the trained list cannot check a choice yet, or "" once it is loaded (main thread).

    A list this connection never requested is requested now; a failed read is
    not repeated here; the picker's Trained chip, a refresh or list_models
    with the trained source reads it again, as the native forms do.
    """
    from . import generation

    generation.process_catalog_events()
    state = runtime.state
    if state.trained_loaded:
        return ""
    if state.trained_loading:
        return "Trained models are still loading; call again in a few seconds."
    if state.trained_error:
        return f"Could not load trained models: {state.trained_error}"
    if not runtime.online():
        return "Online access is disabled; trained models cannot be listed."
    try:
        request(runtime.ensure_manager(), runtime.ensure_catalog())
    except ScenarioError as err:
        return err.reason
    return "Trained models are still loading; call again in a few seconds."


@dataclass(frozen=True)
class Requested:
    """The trained models a request names in a base's LoRA inputs (local MCP)."""

    picks: tuple
    composition: bool  # named in the composition input, so it must be a composition


def split_parameters(record, parameters):
    """(other parameters, Requested or None) for parameters naming the base's LoRA inputs.

    Local MCP passes the inputs model_schema reports (for example `loras` and
    `lorasScale`); they are read strictly and later rebuilt by apply_picks, the
    trained_routes.apply the forms use. None means the request names none of
    them, or the base declares no valid LoRA slot (form preparation then
    checks those values as before). Raises RouteError.
    """
    slot = base_slot(record.id)
    if slot is None or not set(slot.inputs) & set(parameters):
        return parameters, None
    picks = trained_offers.requested_picks(slot, parameters)
    composition = bool(picks) and bool(slot.model_id_input and parameters.get(slot.model_id_input))
    others = {k: v for k, v in parameters.items() if k not in slot.inputs}
    return others, Requested(picks, composition)


NO_STRENGTH_RANGE = (
    "This base model declares no strength range for its LoRAs; omit the strengths to "
    "use its declared default"
)


def _strengths_drawable(slot, picks):
    """Explicit strengths need the range a form's strength field shows; raises otherwise."""
    if any(pick.scale is not None for pick in picks) and trained_offers.strength(slot) is None:
        raise RouteError(NO_STRENGTH_RANGE)


def apply_picks(record, requested, body):
    """`body` with the requested picks written into the base's LoRA inputs, as a form's are.

    Raises ScenarioError while the trained list is not loaded, and RouteError
    for a choice the base's current schema refuses, before any request. A LoRA
    named in the composition input, or a composition named in the stack input,
    is refused, as the service and the quote check refuse it, rather than moved
    into the input apply would route it to.
    """
    picks = requested.picks
    if picks:
        reason = listed_reason()
        if reason:
            raise ScenarioError(0, reason)
    slot = LoraSlot.from_record(record.raw)
    misplaced = trained_offers.placement_error(
        slot, picks, runtime.state.trained_records, composition=requested.composition
    )
    if misplaced:
        raise RouteError(misplaced)
    result = apply(record.raw, picks, runtime.state.trained_records, body)
    _strengths_drawable(slot, picks)
    return result


def started(chosen, slot):
    """`chosen` with each LoRA named without a strength starting where a picker choice does.

    On a base that declares a strength range, that is the LoRA's own declared
    strength, otherwise the Scenario web app's default, within the range
    (trained_offers.strength), so an explicit choice gives the payload the
    picker gives. Explicit strengths are kept as given, for apply to check, and
    a base without a range keeps none: its declared default fills it, as in a form.
    """
    records = runtime.state.trained_records
    result = []
    for model_id, kind, scale in chosen:
        if kind == catalog.TRAINED_LORA and scale is None and slot is not None:
            strength = trained_offers.strength(slot, records.get(model_id))
            if strength is not None:
                scale = strength.initial
        result.append((model_id, kind, scale))
    return result


def checked_choice(record, picks):
    """(model_id, kind, scale) for explicit picks the base runs now; raises before any change.

    The same rules as a picker choice: listed LoRAs or one composition,
    trained_routes.apply, and a strength only where the base declares a range.
    A LoRA named without a strength starts where the picker starts it (started).
    No picks always passes, so a choice a new base refuses can be removed.
    """
    if not picks:
        return []
    slot = base_slot(record.id)
    if slot is None:
        raise ScenarioError(0, "This model does not accept LoRAs or compositions")
    if current_scope() is None:
        raise ScenarioError(0, "Connect to Scenario before choosing a trained model")
    reason = listed_reason()
    if reason:
        raise ScenarioError(0, reason)
    kinds = {item.id: kind for kind, item in runtime.state.trained_pairs}
    chosen = []
    for pick in picks:
        kind = kinds.get(pick.model_id)
        if kind not in catalog.USABLE_TRAINED_KINDS:
            raise ScenarioError(0, "Refresh trained models; a selected model is no longer listed.")
        chosen.append((pick.model_id, kind, pick.scale))
    chosen = started(chosen, slot)
    picks = [Pick(model_id, scale) for model_id, _kind, scale in chosen]
    try:
        apply(record.raw, picks, runtime.state.trained_records)
        _strengths_drawable(slot, picks)
    except RouteError as err:
        raise ScenarioError(0, str(err)) from None
    return chosen


def replace_choice(lane_state, lane, chosen):
    """Replace the form's trained choice with checked_choice's result (main thread)."""
    scope = current_scope()
    if scope is None:
        raise ScenarioError(0, "Connect to Scenario before choosing a trained model")
    slot = base_slot(lane_state.model_id)
    if chosen and slot is None:
        raise ScenarioError(0, "This model does not accept LoRAs or compositions")
    if chosen:
        write_slots(lane_state, lane, chosen, slot, scope)
    else:
        lane_state.trained.clear()
    props.mark_estimate_dirty(lane_state)


def payload_meta(record, body):
    """Job-view entries for the trained models a request body runs, like selection_meta."""
    slot = base_slot(record.id)
    if slot is None:
        return []
    kinds = {item.id: kind for kind, item in runtime.state.trained_pairs}
    entries = []
    for pick in trained_offers.picks_from_payload(slot, body):
        listed = runtime.state.trained_records.get(pick.model_id)
        entries.append(
            {
                "model_id": pick.model_id,
                "name": listed.name if listed is not None and listed.name else pick.model_id,
                "kind": kinds.get(pick.model_id, ""),
                "strength": pick.scale,
            }
        )
    return entries


def slot_name(slot):
    return slot.name or slot.model_id or "Trained model"


def selection_label(lane_state, base_name):
    """The label "Base · LoRA (+n)" for the lane's choice, or the base name alone."""
    return trained_offers.selection_label(base_name, [slot_name(s) for s in lane_state.trained])


def sent_strength(lane_state, slot):
    """The strength a slot sends, as trained_routes.apply resolves it (read-only, safe in draw).

    A LoRA sends its own strength (slot_scale), otherwise the declared default of
    the lane's base. None for a composition, which applies its own strengths, and
    for a LoRA that cannot send one: no declared default, a base not described
    yet, or a model the trained list has not named.
    """
    scale = slot_scale(slot)
    if scale is not None or slot.kind != catalog.TRAINED_LORA:
        return scale
    base = base_slot(lane_state.model_id)
    default = base.scale_default if base is not None else None
    return None if default is None else float(default)


def selection_meta(lane_state):
    """The chosen trained models for job views: IDs, names, kinds and the strength each sent."""
    return [
        {
            "model_id": slot.model_id,
            "name": slot_name(slot),
            "kind": slot.kind,
            "strength": sent_strength(lane_state, slot),
        }
        for slot in lane_state.trained
    ]


class SCENARIO_OT_trained_remove(bpy.types.Operator):
    bl_idname = "scenario.trained_remove"
    bl_label = "Remove trained model"
    bl_description = "Remove this LoRA or composition from the form; the base model stays"
    bl_options = {"INTERNAL"}
    lane: StringProperty(default="image")
    index: IntProperty(default=-1)

    def execute(self, context):
        lane_state = context.scene.scenario.lane_state(self.lane)
        if lane_state is None:
            return {"CANCELLED"}
        if self.index < 0:
            lane_state.trained.clear()
        elif self.index < len(lane_state.trained):
            lane_state.trained.remove(self.index)
        else:
            return {"CANCELLED"}
        props.mark_estimate_dirty(lane_state)
        return {"FINISHED"}


CLASSES = (SCENARIO_OT_trained_remove,)


def register():
    for cls in CLASSES:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(CLASSES):
        try:
            bpy.utils.unregister_class(cls)
        except RuntimeError:
            pass  # already unregistered (a partial registration or tests swapping the module)
