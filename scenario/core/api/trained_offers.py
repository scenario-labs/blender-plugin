# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Trained models a generation lane can offer, and how a choice changes its selection (#97).

Pure functions over REST records: no SDK client, network or bpy. A LoRA or
composition is offered through each base model of the lane whose own detail
record declares a slot that runs it (see trained_routes). List rows and bulk
summaries carry no schema, so a base counts only once its details were read;
callers read those details lazily and in lane order (base_candidates).
"""

import math
from dataclasses import dataclass

from . import catalog
from .trained_routes import ROUTE_STACK, LoraSlot, Pick, RouteError, _type_text

__all__ = [
    "DEFAULT_STRENGTH",
    "MAX_BASE_READS",
    "MAX_PICKS",
    "Base",
    "Offer",
    "Strength",
    "base_candidates",
    "concepts",
    "declared_strength",
    "describe_offer",
    "describe_slot",
    "lora_bases",
    "merged",
    "no_inputs_reason",
    "offers",
    "picks_from_list",
    "picks_from_payload",
    "placement_error",
    "requested_picks",
    "runs",
    "saved_ids",
    "selection_label",
    "starting_strength",
    "strength",
    "strength_value",
]

# Visible starting strength of a newly chosen LoRA, and of a reset strength field,
# when the trained model declares none: the Scenario web app's default. It is kept
# within the base's declared range, and the user sees and can change it before any
# price; it is never added silently.
DEFAULT_STRENGTH = 0.75
# Base model descriptions one lane may read to find LoRA slots, per connection.
MAX_BASE_READS = 400
# Strength resolution sent to the service. Blender stores 32-bit floats, so 0.8
# reads back as 0.800000011920929; rounding keeps equal choices byte-identical.
STRENGTH_DIGITS = 4
# Trained models one explicit choice may name: the job store's bound for a saved default.
MAX_PICKS = 16
UNSUPPORTED = "Not available in Blender: no base model runs this type."


@dataclass(frozen=True)
class Strength:
    """The strength control a LoRA gets on one base: declared bounds and a starting value."""

    minimum: float
    maximum: float
    step: float | None
    initial: float

    def clamp(self, value):
        return round(min(max(float(value), self.minimum), self.maximum), STRENGTH_DIGITS)


def strength(slot, record=None):
    """The LoRA strength control of a slot, or None when its scale input declares no bounds.

    It starts at the strength the trained `record` declares for itself, otherwise
    at DEFAULT_STRENGTH, as the Scenario web app does, clamped to the base's
    declared range. A base's declared default does not change the start; it only
    fills a strength a request omits (trained_routes.apply).
    """
    low, high = slot.scale_min, slot.scale_max
    if low is None or high is None or low > high:
        return None
    initial = min(max(starting_strength(record), low), high)
    return Strength(
        float(low), float(high), slot.scale_step, round(float(initial), STRENGTH_DIGITS)
    )


def runs(slot, record):
    """(route kind, "") when the slot runs this trained record, else (None, reason).

    A LoRA also needs a strength: declared bounds for a control, or a declared
    default. Without either, the request could only be refused later.
    """
    route, reason = slot.route(record)
    if route == ROUTE_STACK and strength(slot) is None and slot.scale_default is None:
        return None, f"{slot.scale_label} declares no strength range."
    return route, reason


@dataclass(frozen=True)
class Base:
    """A detailed lane base model and the LoRA slot its schema declares."""

    record: catalog.ModelRecord
    slot: LoraSlot

    @property
    def id(self):
        return self.record.id


def lora_bases(lane, records):
    """Detailed lane models, curated first, whose schema declares a valid LoRA slot.

    Records without details (list rows) and malformed slots are skipped: a
    changed schema must not offer a route the quote would refuse.
    """
    bases = []
    for record in catalog.models_for_lane(lane, records):
        if not record.parameters:
            continue
        try:
            slot = LoraSlot.from_record(record.raw)
        except ValueError:
            continue
        if slot is not None:
            bases.append(Base(record, slot))
    return bases


def base_candidates(lane, records, attempted=(), limit=MAX_BASE_READS):
    """IDs of lane models whose details are unknown, in lane order, not yet attempted."""
    skipped = set(attempted)
    return [
        record.id
        for record in catalog.models_for_lane(lane, records)
        if not record.parameters and record.id not in skipped
    ][: max(0, int(limit))]


@dataclass(frozen=True)
class Offer:
    """One trained model in the picker: the bases that run it, or why none does."""

    record: catalog.ModelRecord
    kind: str
    bases: tuple
    reason: str

    @property
    def id(self):
        return self.record.id

    @property
    def available(self):
        return bool(self.bases)


def offers(pairs, bases, *, unknown=""):
    """Picker rows for (kind, record) pairs, available first, otherwise in listing order.

    Private plain custom models are ordinary runnable models, not LoRAs or
    compositions, so they are not offered here. Other trained types are listed
    as unavailable with a reason. `unknown` explains a LoRA or composition no
    checked base runs while base details are still loading or could not load.
    """
    rows = []
    for kind, record in pairs:
        if kind == catalog.PRIVATE_CUSTOM:
            continue
        if kind not in catalog.USABLE_TRAINED_KINDS:
            rows.append(Offer(record, kind, (), UNSUPPORTED))
            continue
        compatible = tuple(base for base in bases if runs(base.slot, record.raw)[0])
        reason = ""
        if not compatible:
            if record.raw.get("status") != "trained":
                reason = "This model is not trained and ready to use."
            elif unknown:
                reason = unknown
            else:
                reason = f"No base model in this form accepts {_type_text(record.raw.get('type'))} models."
        rows.append(Offer(record, kind, compatible, reason))
    return sorted(rows, key=lambda offer: not offer.available)


def merged(current, choice, *, same_base):
    """The trained selection after choosing one model, as (model_id, kind, scale) tuples.

    Choosing through another base model, choosing a composition, or choosing a
    LoRA while a composition is selected replaces the selection: a composition
    runs alone. Choosing a LoRA already selected changes its strength in place;
    another LoRA is added after the current ones.
    """
    model_id, kind, _scale = choice
    current = list(current) if same_base else []
    if kind == catalog.TRAINED_COMPOSITION or any(
        item[1] == catalog.TRAINED_COMPOSITION for item in current
    ):
        return [tuple(choice)]
    for index, item in enumerate(current):
        if item[0] == model_id:
            current[index] = tuple(choice)
            return current
    return [*current, tuple(choice)]


LABEL_SEPARATOR = " · "


def selection_label(base_name, names):
    """A base model and its trained choice in one short label: "Base · LoRA (+n)".

    `names` lists the chosen LoRAs or the composition in form order; the first
    one is named and the others are counted, so a compact chip stays compact.
    """
    names = [name for name in names if name]
    if not names:
        return base_name
    extra = f" (+{len(names) - 1})" if len(names) > 1 else ""
    return f"{base_name}{LABEL_SEPARATOR}{names[0]}{extra}"


def concepts(record):
    """(model_id, scale) pairs a composition record lists, malformed entries skipped."""
    raw = record.raw if isinstance(record, catalog.ModelRecord) else record
    values = raw.get("concepts") if isinstance(raw, dict) else None
    pairs = []
    for concept in values if isinstance(values, list) else ():
        if isinstance(concept, dict) and isinstance(concept.get("modelId"), str):
            scale = concept.get("scale")
            pairs.append(
                (
                    concept["modelId"],
                    scale
                    if isinstance(scale, (int, float)) and not isinstance(scale, bool)
                    else None,
                )
            )
    return pairs


def starting_strength(record=None):
    """Where a LoRA's strength starts before any base range applies.

    The strength the trained `record` declares for itself, otherwise
    DEFAULT_STRENGTH, as the Scenario web app does. strength() clamps it to a
    base's declared range; a reset strength field without that range is bounded
    by the range it kept.
    """
    declared = declared_strength(record) if record is not None else None
    return DEFAULT_STRENGTH if declared is None else declared


def declared_strength(record):
    """The strength a trained model declares for itself, or None.

    That is the scale of the first entry of its concepts, when the record
    carries one: a published LoRA lists itself there with its strength.
    """
    pairs = concepts(record)
    scale = pairs[0][1] if pairs else None
    if scale is None or not math.isfinite(scale):
        return None
    return float(scale)


def picks_from_payload(slot, payload):
    """Picks a saved payload names in this slot: one composition, or LoRAs with their strengths.

    Returns () when the payload names none, or values this slot cannot describe
    (misaligned strengths, a model ID and a stack together).
    """
    if not isinstance(payload, dict):
        return ()
    component = slot.component
    composition = payload.get(component.model_id_input) if component.model_id_input else None
    loras = payload.get(component.model_input)
    scales = payload.get(component.scale_input)
    if isinstance(composition, str) and composition:
        return () if loras else (Pick(composition),)
    if not isinstance(loras, list) or not loras:
        return ()
    if any(not isinstance(item, str) or not item for item in loras):
        return ()
    if scales is None:
        return tuple(Pick(item) for item in loras)
    if (
        not isinstance(scales, list)
        or len(scales) != len(loras)
        or any(isinstance(value, bool) or not isinstance(value, (int, float)) for value in scales)
    ):
        return ()
    return tuple(Pick(item, float(value)) for item, value in zip(loras, scales, strict=True))


def saved_ids(raw, payload):
    """Model IDs a saved payload holds in the LoRA inputs a base record names, read leniently.

    Unlike picks_from_payload, this needs no valid slot: a restore can still
    count the trained models of a job whose base's LoRA inputs changed since.
    """
    ui = raw.get("uiConfig") if isinstance(raw, dict) else None
    component = ui.get("lorasComponent") if isinstance(ui, dict) else None
    if not isinstance(component, dict) or not isinstance(payload, dict):
        return []
    ids = []
    for key in ("modelIdInput", "modelInput"):
        name = component.get(key)
        value = payload.get(name) if isinstance(name, str) and name else None
        for item in value if isinstance(value, list) else [value]:
            if isinstance(item, str) and item and item not in ids:
                ids.append(item)
    return ids


# -- explicit choices from local MCP -------------------------------------------------
def strength_value(value, label="Strength"):
    """A LoRA strength as the native forms send it: finite, at most STRENGTH_DIGITS decimals.

    The forms round every strength to STRENGTH_DIGITS, so a more precise value
    could only reach the service through another surface. It is refused rather
    than rounded silently; equal choices then give equal payloads everywhere.
    """
    if isinstance(value, bool) or not isinstance(value, int | float):
        raise RouteError(f"{label}: enter a number for each strength.")
    try:
        value = float(value)
    except OverflowError:
        raise RouteError(f"{label}: enter a finite strength.") from None
    if not math.isfinite(value):
        raise RouteError(f"{label}: enter a finite strength.")
    if round(value, STRENGTH_DIGITS) != value:
        raise RouteError(f"{label}: use at most {STRENGTH_DIGITS} decimal places.")
    return value


def _empty(value):
    return value is None or value == "" or value == []


def requested_picks(slot, parameters):
    """The picks a request names in this slot's inputs, in order; () when it names none.

    Local MCP passes a base model's own LoRA inputs as parameters (for example
    `loras` and `lorasScale`, or `modelId` for a composition). They are read
    strictly here, then rebuilt with trained_routes.apply like a form's choice:
    one composition alone, or LoRA IDs with one strength each in the same
    order. A LoRA without a strength keeps None, which apply resolves to the
    scale input's declared default or refuses. Raises RouteError.
    """
    component = slot.component
    composition = parameters.get(component.model_id_input) if component.model_id_input else None
    loras = parameters.get(component.model_input)
    scales = parameters.get(component.scale_input)
    if not _empty(composition):
        if not isinstance(composition, str):
            raise RouteError(f"{slot.model_id_label}: enter one composition model ID.")
        if not _empty(loras):
            raise RouteError("Use a composition on its own; it already combines its LoRAs.")
        if not _empty(scales):
            raise RouteError("A composition applies its own strengths; remove the strength.")
        return (Pick(composition),)
    if _empty(loras):
        if not _empty(scales):
            raise RouteError(
                f"{slot.scale_label}: send strengths only with LoRAs in {slot.model_label}."
            )
        return ()
    if (
        not isinstance(loras, list)
        or len(loras) > MAX_PICKS
        or any(not isinstance(item, str) or not item for item in loras)
    ):
        raise RouteError(f"{slot.model_label}: give a list of at most {MAX_PICKS} LoRA model IDs.")
    if scales is None:
        return tuple(Pick(item) for item in loras)
    if not isinstance(scales, list) or len(scales) != len(loras):
        raise RouteError(f"{slot.scale_label}: give one strength per LoRA, in the same order.")
    return tuple(
        Pick(item, strength_value(value, slot.scale_label))
        for item, value in zip(loras, scales, strict=True)
    )


def placement_error(slot, picks, records, *, composition):
    """Why a request names a listed trained model in the other LoRA input, or "".

    trained_routes.apply routes each pick by its kind, which suits a form's
    choice. A request names its input, and the service refuses a LoRA in a
    composition-only position and a composition in the stack input (#374), as
    the quote check does. So a model in the wrong input is refused, never moved.
    `records` maps listed IDs to records; `composition` says the picks came from
    the composition input. An unlisted pick is left to apply, which refuses it.
    """
    for index, pick in enumerate(picks, 1):
        record = records.get(pick.model_id)
        kind = catalog.trained_kind(record) if record is not None else None
        if composition and kind == catalog.TRAINED_LORA:
            return (
                f"{slot.model_id_label} is a LoRA. Add it to {slot.model_label} with a strength "
                "instead."
            )
        if not composition and kind == catalog.TRAINED_COMPOSITION:
            hint = (
                f" Use it alone in {slot.model_id_label}, without a strength."
                if slot.model_id_input and record.type in slot.model_id_types
                else ""
            )
            return (
                f"{slot.model_label} [{index}] is a composition; {slot.model_label} accepts "
                f"{', '.join(slot.model_types)}.{hint}"
            )
    return ""


def no_inputs_reason(kind):
    """The final reason a model whose record declares no inputs cannot be the target.

    `kind` is catalog.trained_kind of its record. A LoRA or composition has no
    inputs of its own and runs only through a base model's LoRA inputs. Reading
    the description again returns the same record, so this answer never waits.
    """
    if kind == catalog.TRAINED_LORA:
        return (
            "This model is a LoRA: it has no inputs of its own and runs only through a base "
            "model that accepts LoRAs"
        )
    if kind == catalog.TRAINED_COMPOSITION:
        return (
            "This model is a composition: it has no inputs of its own and runs only through a "
            "base model that accepts compositions"
        )
    return "This model declares no inputs, so it cannot run; choose another"


def picks_from_list(items):
    """Picks from `[{"model_id": ..., "scale": ...}]`, as render_form and model_defaults take them.

    `scale` is optional (null or absent means none). Unknown fields, empty IDs
    and imprecise strengths are refused, never coerced. Raises RouteError.
    """
    if not isinstance(items, list) or len(items) > MAX_PICKS:
        raise RouteError(f"Give at most {MAX_PICKS} trained models as a list.")
    picks = []
    for item in items:
        if (
            not isinstance(item, dict)
            or not {"model_id"} <= set(item) <= {"model_id", "scale"}
            or not isinstance(item["model_id"], str)
            or not item["model_id"]
        ):
            raise RouteError("Give each trained model as model_id and an optional scale.")
        scale = item.get("scale")
        picks.append(Pick(item["model_id"], None if scale is None else strength_value(scale)))
    return tuple(picks)


def describe_slot(slot):
    """A base model's LoRA inputs and their declared bounds as plain JSON values."""
    component = slot.component
    declared = slot.scale_min is not None and slot.scale_max is not None
    return {
        "model_input": component.model_input,
        "scale_input": component.scale_input,
        "model_id_input": component.model_id_input,
        "model_types": list(slot.model_types),
        "model_id_types": list(slot.model_id_types),
        "min_items": slot.min_items,
        "max_items": slot.max_items,
        "scale_range": [slot.scale_min, slot.scale_max] if declared else None,
        "scale_step": slot.scale_step,
        "scale_default": slot.scale_default,
    }


def _route_entry(base, record, default):
    route, _reason = runs(base.slot, record.raw)
    slot = base.slot
    entry = {"route": route, "model_id": base.id, "name": base.record.name}
    if route == ROUTE_STACK:
        # Where the picker starts this LoRA on this base; the base's declared
        # default only fills a strength a request omits.
        control = strength(slot, record)
        entry.update(
            model_input=slot.component.model_input,
            scale_input=slot.component.scale_input,
            scale_range=[slot.scale_min, slot.scale_max] if control is not None else None,
            scale_step=slot.scale_step,
            start_scale=control.initial if control is not None else None,
            default_scale=slot.scale_default,
            min_items=slot.min_items,
            max_items=slot.max_items,
        )
    else:
        entry["model_input"] = slot.component.model_id_input
    if default is not None and default.base_model_id == base.id:
        entry["default"] = True
    return entry


def describe_offer(offer, *, private=False, default=None):
    """One trained model as local MCP lists it, from the same Offer the picker draws.

    `routes` names every base model that runs it in the lane and the inputs
    that carry it; a LoRA's `start_scale` is where the picker starts its
    strength on that base. `default` is the lane's saved default (a TrainedModelDefault
    or None); rows and routes it uses are marked. Nothing here is a quote.
    """
    record = offer.record
    names = default is not None and any(pick.model_id == offer.id for pick in default.picks)
    row = {
        "id": offer.id,
        "name": record.name,
        "kind": offer.kind,
        "type": _type_text(record.type),
        "private": bool(private),
        "available": offer.available,
        "routes": [_route_entry(base, record, default if names else None) for base in offer.bases],
    }
    if not offer.available:
        row["reason"] = offer.reason
    if offer.kind == catalog.TRAINED_COMPOSITION:
        row["concepts"] = [
            {"model_id": model_id, "scale": scale} for model_id, scale in concepts(record)
        ]
    if names:
        row["default"] = True
    return row
