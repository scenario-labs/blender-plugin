# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Trained-model routes derived from base-model REST schemas (#97).

Pure functions over REST records: no SDK client, network or bpy. A LoRA or
composition has no runnable schema of its own; it runs through a base model
whose `uiConfig.lorasComponent` and input `modelTypes` accept its REST `type`.
Nothing is inferred from names, remote-MCP metadata or a hard-coded type table.

The zero-spend capture under tests/fixtures/models/trained proves two kinds:

- stack: LoRA IDs in `modelInput` with one strength each in `scaleInput`;
- composition: one composition ID in `modelIdInput`, applied with the
  strengths of its own concepts.

The service rejects a trained ID as the generation target, so there is no
direct route. It also accepts a single LoRA in `modelIdInput`, but then applies
a strength nobody chose; this module asks for that LoRA in the stack instead.
"""

from collections.abc import Callable, Iterable, Mapping
from copy import deepcopy
from dataclasses import dataclass

from ..schema.forms import (
    LoraComponent,
    RouteError,
    _fields,
    _finite_number,
    _label,
    _model_identity,
    lora_component,
    record_schema,
)
from . import catalog
from .sdk_adapter import AdapterUnavailable

__all__ = [
    "MAX_REFERENCE_READS",
    "ROUTE_COMPOSITION",
    "ROUTE_STACK",
    "LoraSlot",
    "Pick",
    "Reference",
    "RouteError",
    "apply",
    "check_references",
    "compatibility",
    "compatible_bases",
    "model_references",
]

ROUTE_STACK = "stack"
ROUTE_COMPOSITION = "composition"
# Fresh reads one quote may make for referenced models and composition concepts.
MAX_REFERENCE_READS = 16
_STATUSES = {"new", "training", "trained", "failed", "deleted"}


def _raw(record):
    """A REST record dict from a dict or a catalog.ModelRecord."""
    raw = record.raw if isinstance(record, catalog.ModelRecord) else record
    if not isinstance(raw, dict):
        raise RouteError("Refresh the model list; a model record is malformed.")
    return raw


def _types(field):
    """Declared `modelTypes` as a tuple of nonempty strings, or None if malformed."""
    value = field.get("modelTypes")
    if value is None:
        return ()
    if not isinstance(value, list) or any(not isinstance(item, str) or not item for item in value):
        return None
    return tuple(value)


def _type_text(value):
    """A REST type for safe display: short ASCII identifiers only."""
    if (
        isinstance(value, str)
        and 0 < len(value) <= 64
        and all(char.isascii() and (char.isalnum() or char in ".-_") for char in value)
    ):
        return value
    return "unsupported"


def _bound(field, *names):
    for name in names:
        value = field.get(name)
        if _finite_number(value):
            return value
    return None


def _count(field, *names):
    value = _bound(field, *names)
    return int(value) if value is not None and value >= 0 and value == int(value) else None


@dataclass(frozen=True)
class LoraSlot:
    """The LoRA inputs one base schema declares, with their REST bounds."""

    component: LoraComponent
    model_label: str
    scale_label: str
    model_id_label: str | None
    model_types: tuple[str, ...]
    model_id_types: tuple[str, ...]
    min_items: int
    max_items: int | None
    scale_min: float | None
    scale_max: float | None
    scale_step: float | None
    scale_default: float | None

    @classmethod
    def from_schema(cls, schema):
        """Return the schema's slot, None without a lorasComponent, RouteError if malformed.

        The stack input must declare its accepted `modelTypes`; without them
        no LoRA could be checked before quoting.
        """
        component = lora_component(schema)
        if component is None:
            return None
        fields = {field["name"]: field for field in _fields(schema)}
        model = fields[component.model_input]
        scale = fields[component.scale_input]
        model_types = _types(model)
        model_id = fields.get(component.model_id_input) if component.model_id_input else None
        model_id_types = _types(model_id) if model_id is not None else ()
        if not model_types or model_id_types is None:
            raise RouteError(
                "This model's LoRA inputs changed or are malformed. Refresh the model and "
                "choose its LoRAs again."
            )
        return cls(
            component,
            _label(model),
            _label(scale),
            _label(model_id) if model_id is not None else None,
            model_types,
            model_id_types,
            _count(model, "minLength", "min_length", "minItems") or 0,
            _count(model, "maxLength", "max_length", "maxItems"),
            _bound(scale, "min", "minimum"),
            _bound(scale, "max", "maximum"),
            _bound(scale, "step"),
            _bound(scale, "default"),
        )

    @classmethod
    def from_record(cls, record, operation="model"):
        """The slot of one REST model (or workflow) record."""
        return cls.from_schema(record_schema(operation, _raw(record)))

    @property
    def inputs(self):
        return self.component.names

    def route(self, trained):
        """(route kind, "") for a usable trained record, else (None, reason)."""
        raw = _raw(trained)
        kind = catalog.trained_kind(catalog.ModelRecord.from_api(raw))
        if raw.get("status") != "trained":
            return None, "This model is not trained and ready to use."
        model_type = raw.get("type")
        if kind == catalog.TRAINED_LORA:
            if model_type in self.model_types:
                return ROUTE_STACK, ""
            return None, (
                f"{self.model_label} accepts {', '.join(self.model_types)} models, "
                f"not {_type_text(model_type)}."
            )
        if kind == catalog.TRAINED_COMPOSITION:
            if self.model_id_input and model_type in self.model_id_types:
                return ROUTE_COMPOSITION, ""
            return None, "This model does not accept compositions of this type."
        return None, "Only LoRAs and compositions run through a base model."

    @property
    def model_id_input(self):
        return self.component.model_id_input


def compatibility(lane, base, trained):
    """(route kind, "") when `trained` can run on `base` in `lane`, else (None, reason).

    `base` must be a detail record: list rows and bulk summaries carry no
    `uiConfig` or `inputs`, so they never show a slot.
    """
    record = catalog.ModelRecord.from_api(_raw(base))
    if lane not in record.lanes:
        return None, "This base model does not run in this lane."
    if catalog.trained_kind(record) not in (None, catalog.PRIVATE_CUSTOM):
        return None, "Choose a base model, not a trained model."
    try:
        slot = LoraSlot.from_record(record.raw)
    except ValueError as error:
        return None, str(error)
    if slot is None:
        return None, "This base model does not accept LoRAs or compositions."
    return slot.route(trained)


def compatible_bases(lane, trained, bases):
    """Every detail record in `bases` that runs `trained` in `lane`, curated first.

    Several bases can be compatible; callers must let the user choose, never
    pick one silently.
    """
    records = [
        record if isinstance(record, catalog.ModelRecord) else catalog.ModelRecord.from_api(record)
        for record in bases
    ]
    return [
        record
        for record in catalog.models_for_lane(lane, records)
        if compatibility(lane, record, trained)[0] is not None
    ]


@dataclass(frozen=True)
class Pick:
    """One trained model in a selection; `scale` is the chosen LoRA strength."""

    model_id: str
    scale: float | None = None


def apply(base, picks, trained_records, parameters=None, *, operation="model"):
    """Return `parameters` with `picks` written into the base's LoRA inputs.

    The base's LoRA inputs are cleared first, so equal selections over equal
    parameters give equal payloads whichever surface builds them. A composition
    runs alone through `modelIdInput` with its own concept strengths; LoRAs
    are stacked with one strength each, the scale input's declared default
    when a pick has none. `trained_records` maps IDs to the listed records.
    """
    slot = LoraSlot.from_record(base, operation)
    if slot is None:
        raise RouteError("This model does not accept LoRAs or compositions.")
    result = deepcopy(dict(parameters or {}))
    for name in slot.inputs:
        result.pop(name, None)
    picks = tuple(picks)
    if not picks:
        return result
    if any(
        not isinstance(pick, Pick) or not isinstance(pick.model_id, str) or not pick.model_id
        for pick in picks
    ):
        raise RouteError("Choose trained models from the model list.")
    identifiers = [pick.model_id for pick in picks]
    if len(set(identifiers)) != len(identifiers):
        raise RouteError(f"{slot.model_label}: choose each LoRA once.")
    kinds = []
    for pick in picks:
        record = (
            trained_records.get(pick.model_id) if isinstance(trained_records, Mapping) else None
        )
        if record is None:
            raise RouteError("Refresh trained models; a selected model is no longer listed.")
        kind, reason = slot.route(record)
        if kind is None:
            raise RouteError(reason)
        kinds.append(kind)
    if ROUTE_COMPOSITION in kinds:
        if len(picks) != 1:
            raise RouteError("Use a composition on its own; it already combines its LoRAs.")
        if picks[0].scale is not None:
            raise RouteError("A composition applies its own strengths; remove the strength.")
        result[slot.model_id_input] = picks[0].model_id
        return result
    if slot.max_items is not None and len(picks) > slot.max_items:
        raise RouteError(f"{slot.model_label}: use at most {slot.max_items} LoRAs.")
    if len(picks) < slot.min_items:
        raise RouteError(f"{slot.model_label}: use at least {slot.min_items} LoRAs.")
    scales = []
    for pick in picks:
        scale = slot.scale_default if pick.scale is None else pick.scale
        if scale is None:
            raise RouteError(f"{slot.scale_label}: provide a strength for each LoRA.")
        if not _finite_number(scale):
            raise RouteError(f"{slot.scale_label}: enter a finite strength.")
        if (slot.scale_min is not None and scale < slot.scale_min) or (
            slot.scale_max is not None and scale > slot.scale_max
        ):
            raise RouteError(
                f"{slot.scale_label}: use a strength from {slot.scale_min:g} to {slot.scale_max:g}."
                if slot.scale_min is not None and slot.scale_max is not None
                else f"{slot.scale_label}: this strength is out of range."
            )
        scales.append(float(scale))
    result[slot.component.model_input] = identifiers
    result[slot.component.scale_input] = scales
    return result


@dataclass(frozen=True)
class Reference:
    """One model ID a payload names in a `model` or `model_array` input.

    `model_types` is empty when the input accepts any type and None when its
    declared `modelTypes` is malformed.
    """

    input: str
    label: str
    index: int | None
    model_id: str
    model_types: tuple[str, ...] | None

    @property
    def where(self):
        return self.label if self.index is None else f"{self.label} [{self.index}]"


def model_references(schema, payload, names=None):
    """Model IDs in the payload's `model` and `model_array` inputs, in input order.

    `names` limits the result to inputs the caller set; values from schema
    defaults are the service's own. Malformed values are skipped: form
    preparation reports them.
    """
    references = []
    for field in _fields(schema):
        name, kind = field["name"], field.get("type")
        if kind not in {"model", "model_array"} or (names is not None and name not in names):
            continue
        value = payload.get(name) if isinstance(payload, dict) else None
        types = _types(field)
        label = _label(field)
        if kind == "model" and isinstance(value, str) and value:
            references.append(Reference(name, label, None, value, types))
        elif kind == "model_array" and isinstance(value, list):
            references.extend(
                Reference(name, label, index, item, types)
                for index, item in enumerate(value, 1)
                if isinstance(item, str) and item
            )
    return references


class _Unavailable(Exception):
    def __init__(self, status):
        self.status = status


def check_references(
    schema,
    payload,
    read: Callable[[str], dict],
    *,
    names: Iterable[str] | None = None,
    limit=MAX_REFERENCE_READS,
):
    """Check every referenced model against fresh records before any quote.

    `read(model_id)` returns the current REST record in the selected scope and
    raises AdapterUnavailable for HTTP 403 or 404. Each model is read once,
    composition concepts included, at most `limit` reads in total. Raises
    RouteError, with input labels and positions only, when a model is
    unavailable, not trained, of a type the input does not accept, a LoRA in
    the composition input, or a composition whose concept LoRAs the stack
    input would not accept. Returns the records read, by ID.
    """
    references = model_references(schema, payload, None if names is None else set(names))
    if not references:
        return {}
    slot = LoraSlot.from_schema(schema)
    for reference in references:
        if reference.model_types is None:
            raise RouteError(
                f"{reference.label}: the model types this input accepts changed or are "
                "malformed. Refresh the model and try again."
            )
    records = {}

    def fetch(model_id, too_many=None):
        if model_id in records:
            return records[model_id]
        if len(records) >= limit:
            raise RouteError(
                too_many or f"Too many models to check (at most {limit}); remove some LoRAs."
            )
        try:
            record = read(model_id)
        except AdapterUnavailable as error:
            raise _Unavailable(error.status) from None
        if not isinstance(record, dict) or record.get("id") != model_id:
            raise RouteError("Scenario returned another model; refresh and try again.")
        records[model_id] = record
        return record

    def status_error(record, subject):
        status = record.get("status")
        if status == "trained":
            return None
        shown = status if status in _STATUSES else "unknown"
        return RouteError(f"{subject} is not ready to use (status: {shown}).")

    for reference in references:
        where = reference.where
        try:
            _model_identity(reference.model_id)
        except ValueError:
            raise RouteError(f"{where}: enter a valid model ID.") from None
        try:
            record = fetch(reference.model_id)
        except _Unavailable as error:
            raise RouteError(
                f"{where} is not available to the selected credentials or project "
                f"(HTTP {error.status}). Remove it or choose another model."
            ) from None
        failure = status_error(record, where)
        if failure:
            raise failure
        model_type = record.get("type")
        if reference.model_types and model_type not in reference.model_types:
            raise RouteError(
                f"{where} is a {_type_text(model_type)} model; {reference.label} accepts "
                f"{', '.join(reference.model_types)}."
            )
        if slot is None or reference.input != slot.model_id_input:
            continue
        kind = catalog.trained_kind(catalog.ModelRecord.from_api(record))
        if kind == catalog.TRAINED_LORA:
            raise RouteError(
                f"{where} is a LoRA. Add it to {slot.model_label} with a strength instead."
            )
        if kind != catalog.TRAINED_COMPOSITION:
            continue
        concepts = record.get("concepts")
        if (
            not isinstance(concepts, list)
            or not concepts
            or any(not isinstance(concept, dict) for concept in concepts)
        ):
            raise RouteError(f"{where} lists no LoRAs to apply; choose another composition.")
        for concept in concepts:
            identifier = concept.get("modelId")
            try:
                _model_identity(identifier)
            except ValueError:
                raise RouteError(
                    f"{where} lists a malformed LoRA; choose another composition."
                ) from None
            try:
                concept_record = fetch(
                    identifier,
                    f"{where} combines too many LoRAs to check (at most {limit}); "
                    "choose another composition.",
                )
            except _Unavailable as error:
                raise RouteError(
                    f"{where} uses a LoRA that is not available to the selected credentials "
                    f"or project (HTTP {error.status}). Choose another composition."
                ) from None
            failure = status_error(concept_record, f"A LoRA in {where}")
            if failure:
                raise failure
            concept_type = concept_record.get("type")
            if concept_type not in slot.model_types:
                raise RouteError(
                    f"{where} combines {_type_text(concept_type)} LoRAs; "
                    f"{slot.model_label} accepts {', '.join(slot.model_types)}."
                )
    return records
