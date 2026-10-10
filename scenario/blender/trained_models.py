# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Trained LoRAs and compositions in the picker and the generation forms (#97, main thread).

The selected connection's private trained list and public LoRAs load with the
catalog. Base-model descriptions, which declare the LoRA inputs, are read only
when the picker shows its Trained chip, in lane order and once per connection.
A lane keeps its choice as scope-tagged slots; every request rebuilds the LoRA
inputs from the base's REST schema with trained_routes.apply, the same function
local MCP and the quote check use.
"""

import bpy
from bpy.props import IntProperty, StringProperty

from ..core.api import catalog, trained_offers
from ..core.api.errors import ScenarioError
from ..core.api.trained_routes import LoraSlot, Pick, RouteError, apply
from ..core.schema.forms import lora_component, record_schema
from . import props, runtime
from .reference_form import scope_key

SCOPE = "_scenario_trained_scope"
LANES = ("image", "render_image")
EXPERIMENTAL = "Experimental: LoRAs and compositions not accepted"
LOADING = "Loading trained models"
OTHER_SCOPE = "A trained model was chosen for another connection or project; choose it again"
KIND_LABELS = {catalog.TRAINED_LORA: "LoRA", catalog.TRAINED_COMPOSITION: "Composition"}
_hidden = {}  # model_id -> (record, names): LoRA inputs the form must not draw as text


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
    _hidden.clear()


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

    if model_picker.is_trained_view() and model_picker._ctx["lane"]:
        request_bases(model_picker._ctx["lane"])
    _refresh_picker()


def on_catalog_failed(reason):
    state = runtime.state
    state.trained_loading = False
    state.trained_error = str(reason) or "Could not read trained models"
    _rearm_selections()
    _refresh_picker()


def _rearm_selections():
    """Reprice lanes whose trained choice waited for this list; quoted forms stay quoted."""
    for scene in bpy.data.scenes:
        if not hasattr(scene, "scenario"):
            continue
        for lane in props.GENERATION_LANES:
            lane_state = scene.scenario.lane_state(lane)
            if len(lane_state.trained) and lane_state.estimate_state in ("UNAVAILABLE", "IDLE"):
                props.mark_estimate_dirty(lane_state)


def _refresh_picker():
    from . import model_picker

    model_picker.refresh_trained()


def _scan(lane):
    return runtime.state.trained_scans.setdefault(
        lane,
        {"pending": False, "checked": 0, "total": 0, "failed": 0, "error": "", "attempted": set()},
    )


def request_bases(lane):
    """Read the descriptions of this lane's base models that are still unknown.

    Runs only for a picker showing trained models, never on catalog refresh.
    Descriptions are cached per connection, so each base is read at most once
    unless an explicit refresh retries failures. Returns whether reads are pending.
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
    scan.update(pending=True, checked=0, total=len(ids), failed=0, error="")
    scan["attempted"].update(ids)
    manager.fetch_base_schemas(connection, lane, ids)
    return True


def on_bases(payload):
    from . import generation

    scan = _scan(payload["lane"])
    if payload["detailed"]:
        generation.set_models(payload["detailed"], {}, mark_dirty=False)
    scan.update(
        checked=payload["checked"],
        total=payload["total"],
        failed=payload["failed"],
        error=payload["error"],
        pending=not payload["done"],
    )
    _refresh_picker()


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


def _resolved(chosen, slot):
    """Give every LoRA with a strength control a concrete, bounded strength."""
    strength = trained_offers.strength(slot)
    return [
        (
            model_id,
            kind,
            strength.clamp(strength.initial if scale is None else scale)
            if kind == catalog.TRAINED_LORA and strength is not None
            else None,
        )
        for model_id, kind, scale in chosen
    ]


def _write(lane_state, lane, chosen, slot, scope):
    """Replace the lane's slots with `chosen` (already resolved) for this base slot."""
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
    _write(lane_state, lane, chosen, base.slot, scope)
    props.mark_estimate_dirty(lane_state)
    return lane


def restore(lane_state, lane, record, payload):
    """Rebuild the lane's choice from a saved payload; returns how many models were skipped.

    Called by Reload parameters: the form gets exactly the job's LoRAs and
    composition when they are still listed, and nothing from the former form.
    """
    lane_state.trained.clear()
    props.mark_estimate_dirty(lane_state)
    try:
        slot = LoraSlot.from_record(record.raw)
    except ValueError:
        slot = None
    wanted = trained_offers.picks_from_payload(slot, payload) if slot is not None else ()
    scope = current_scope()
    if not wanted or scope is None:
        return len(wanted)
    kinds = {item.id: kind for kind, item in runtime.state.trained_pairs}
    chosen = [
        (pick.model_id, kinds[pick.model_id], pick.scale)
        for pick in wanted
        if kinds.get(pick.model_id) in catalog.USABLE_TRAINED_KINDS
    ]
    _write(lane_state, trained_lane(lane), _resolved(chosen, slot), slot, scope)
    return len(wanted) - len(chosen)


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


# -- drawing (read-only) ---------------------------------------------------------------
def selection_text(slot):
    name = slot.name or "Trained model"
    if slot.kind == catalog.TRAINED_COMPOSITION:
        return f"{name} (composition)"
    if slot.has_scale:
        return f"{name} (strength {round(slot.scale, trained_offers.STRENGTH_DIGITS):g})"
    return name


def draw_selection(layout, lane_state, lane):
    """The lane's trained choice under its Model button, each with a remove button."""
    if not len(lane_state.trained):
        return
    col = layout.column(align=True)
    for index, slot in enumerate(lane_state.trained):
        row = col.row(align=True)
        icon = "GROUP" if slot.kind == catalog.TRAINED_COMPOSITION else "SHADERFX"
        row.label(text=selection_text(slot), icon=icon)
        op = row.operator("scenario.trained_remove", text="", icon="X")
        op.lane, op.index = lane, index
    col.label(text=EXPERIMENTAL, icon="EXPERIMENTAL")


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
            pass
