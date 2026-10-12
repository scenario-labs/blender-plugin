# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Explicit per-scope project defaults of the Image and Render Image forms (#97, main thread).

A default names a base model and its LoRAs (with strengths) or one composition.
It is saved only by Save and cleared only by Clear, through the runtime's
ModelDefaults owner of the selected credentials and optional Project ID, and
only over the revision the user saw in that same selection. Saving or clearing
changes no form and no payload.

A form with no explicit choice in this scope (no model chosen, no trained model)
takes the saved default: the pump applies it once the base description and the
trained list are loaded and trained_routes.apply accepts it. Until then, or when
it cannot run, the form's price is blocked with the reason; it never falls back
to the base model alone. Use applies the default to a form that already has a
choice. Applying always reprices the form; the quote still reads every model
fresh. Applying automatically writes the form without RNA updates, so origins
captured in its scene stay current (#387). Use assigns through RNA, whose
update tags the scene and makes those origins stale, only a different base
model and each LoRA strength; a composition on the form's current base changes
only the trained list.
"""

from dataclasses import dataclass, field

import bpy

from ..core.api import catalog, trained_offers
from ..core.api.errors import ScenarioError
from ..core.api.trained_routes import Pick, RouteError, apply
from ..core.jobs.store import StoreError, TrainedModelDefault, TrainedModelPick
from . import props, runtime, trained_models

LANES = trained_models.LANES
ROUTES = ("stack", "composition")
UNAVAILABLE = (
    "Project default {label} is unavailable: choose a model or clear the default. {reason}"
)
WAITING = "Applying the project default {label}: {reason}"
UNREADABLE = "Could not read the project default: {reason} Choose a model to continue."
# Price errors written from the texts above; a form they no longer block is priced again.
BLOCKING = (
    "Project default ",
    "Applying the project default ",
    "Could not read the project default",
)


@dataclass(frozen=True)
class Cache:
    """Saved lane states of one selection, read through its owner."""

    context: str  # the owner's context_id: writes must come from this same selection
    lanes: dict = field(default_factory=dict)  # lane -> TrainedDefaultState
    errors: dict = field(default_factory=dict)  # lane -> why its stored default is unreadable


@dataclass(frozen=True)
class Resolution:
    """What a saved default does in a form now: runs, waits for a read, or cannot run."""

    label: str
    base: trained_offers.Base | None = None
    chosen: tuple = ()  # (model_id, kind, scale) in form order, when it runs
    waiting: str = ""
    reason: str = ""

    @property
    def ready(self):
        return self.base is not None and not self.waiting and not self.reason

    @property
    def text(self):
        if self.reason:
            return UNAVAILABLE.format(label=self.label, reason=_sentence(self.reason))
        if self.waiting:
            return WAITING.format(label=self.label, reason=self.waiting)
        return ""


def _sentence(text):
    text = str(text).strip()
    return text if text.endswith((".", "!", "?")) else f"{text}."


_reads = {}  # base model id -> the owner context_id that already read its description


def forget():
    """Drop the cached defaults and description reads of a retired or refreshed connection."""
    runtime.state.trained_defaults = None
    _reads.clear()


# -- reading -------------------------------------------------------------------------
def cached():
    """The defaults read for the current selection, or None (read-only, safe in draw)."""
    cache = runtime.state.trained_defaults
    owner = runtime.state.model_defaults
    if cache is None or owner is None or not owner.active or cache.context != owner.context_id:
        return None
    return cache


def load(*, force=False):
    """Read the selected scope's lane defaults once per selection (main thread, never in draw).

    Raises ScenarioError when no connection is selected. A stored default that
    cannot be decoded is reported for its lane and preserved, never reset.
    """
    owner = runtime.ensure_model_defaults()
    cache = runtime.state.trained_defaults
    if not force and cache is not None and cache.context == owner.context_id:
        return cache
    lanes, errors = {}, {}
    for lane in LANES:
        try:
            lanes[lane] = owner.lane(lane)
        except StoreError as err:
            errors[lane] = _sentence(err)
    cache = Cache(owner.context_id, lanes, errors)
    runtime.state.trained_defaults = cache
    return cache


def saved(cache, lane):
    state = cache.lanes.get(lane) if cache is not None else None
    return state.default if state is not None else None


def revision(cache, lane):
    state = cache.lanes.get(lane) if cache is not None else None
    return state.revision if state is not None else 0


def label(default):
    """The default as "Base · LoRA (+n)", with the names the catalog knows and IDs otherwise."""
    state = runtime.state
    base = state.records.get(default.base_model_id)
    names = []
    for pick in default.picks:
        record = state.trained_records.get(pick.model_id)
        names.append(record.name if record is not None and record.name else pick.model_id)
    return trained_offers.selection_label(
        base.name if base is not None and base.name else default.base_model_id, names
    )


def _base_waiting(base_id, read):
    """Why a base without its description cannot be checked yet, or the reason it never will.

    A default starts at most one description read per base and selection: a read
    that delivers no inputs is not repeated by every pump tick.
    """
    from . import generation

    failure = runtime.state.model_errors.get(base_id)
    if failure:
        return "", failure
    if generation.is_loading(base_id):
        return "loading its base model.", ""
    if not runtime.online():
        return "online access is disabled.", ""
    owner = runtime.state.model_defaults
    context = owner.context_id if owner is not None else None
    if context is not None and _reads.get(base_id) == context:
        return "", "Its base model's description declares no inputs."
    if read:
        _reads[base_id] = context
        generation.request_model(base_id, mark_dirty=False)
    return "loading its base model.", ""


def _listed(model_id, lane):
    """Whether the form's own model list offers this model (read-only, safe in draw)."""
    return model_id in {item[0] for item in runtime.enum_items(("models", lane))}


def resolve(default, lane, *, read=False):
    """How `default` runs in `lane` now, checked with trained_routes.apply like any choice.

    `read` (never in draw) starts the base's description read when it is missing.
    """
    state = runtime.state
    text = label(default)
    if default.route not in ROUTES:
        return Resolution(text, reason="Blender runs LoRA and composition defaults only.")
    record = state.records.get(default.base_model_id)
    if record is None:
        if state.catalog_loaded:
            return Resolution(text, reason="Its base model is not in the model list.")
        return Resolution(text, waiting="loading models.")
    if not catalog.models_for_lane(lane, [record]):
        return Resolution(text, reason="Its base model does not run in this form.")
    if not _listed(record.id, lane):
        # A default only lands on a base the form can select, never under another one.
        if state.catalog_loaded:
            return Resolution(text, reason="Its base model is not in this form's model list.")
        return Resolution(text, waiting="loading models.")
    if not record.parameters:
        waiting, reason = _base_waiting(record.id, read)
        return Resolution(text, waiting=waiting, reason=reason)
    slot = trained_models.base_slot(record.id)
    if slot is None:
        return Resolution(text, reason="Its base model does not accept LoRAs or compositions.")
    if not state.trained_loaded:
        if state.trained_error:
            return Resolution(text, reason=f"Could not load trained models: {state.trained_error}")
        return Resolution(text, waiting="loading trained models.")
    kinds = {item.id: kind for kind, item in state.trained_pairs}
    chosen = []
    for pick in default.picks:
        kind = kinds.get(pick.model_id)
        if kind not in catalog.USABLE_TRAINED_KINDS:
            return Resolution(text, reason="A trained model it names is no longer listed.")
        chosen.append((pick.model_id, kind, pick.scale))
    composition = [kind for _id, kind, _scale in chosen] == [catalog.TRAINED_COMPOSITION]
    if composition != (default.route == "composition"):
        return Resolution(text, reason="A trained model it names changed kind.")
    strength = trained_offers.strength(slot)
    if any(
        kind == catalog.TRAINED_LORA and scale is not None and strength is None
        for _id, kind, scale in chosen
    ):
        return Resolution(text, reason="Its base model no longer declares a strength range.")
    try:
        picks = [Pick(model_id, scale) for model_id, _kind, scale in chosen]
        apply(record.raw, picks, state.trained_records)
    except RouteError as err:
        return Resolution(text, reason=str(err))
    except ValueError:
        return Resolution(text, reason="Its base model's LoRA inputs could not be read.")
    return Resolution(text, trained_offers.Base(record, slot), tuple(chosen))


def governs(lane_state):
    """Whether the saved default decides this form: no model and no trained model chosen."""
    return (
        props.lane_of(lane_state) in LANES
        and not lane_state.model_key
        and not len(lane_state.trained)
    )


def matches(lane_state, default):
    """Whether the form already holds exactly this default in the current scope (read-only)."""
    if default is None or lane_state.model_id != default.base_model_id:
        return False
    if trained_models.scope_error(lane_state) is not None:
        return False
    current = [(slot.model_id, trained_models.slot_scale(slot)) for slot in lane_state.trained]
    return current == [(pick.model_id, pick.scale) for pick in default.picks]


def blocking_reason(lane_state):
    """Why a form the saved default governs cannot be priced now, or "" (main thread, not draw).

    The default is applied by apply_pending; this only explains the wait or the
    failure, so a governed form never prices its base model alone.
    """
    if not governs(lane_state) or runtime.state.catalog is None:
        return ""  # without a selected connection there is no scope, default or model schema
    lane = props.lane_of(lane_state)
    try:
        cache = load()
    except ScenarioError:
        return ""
    if lane in cache.errors:
        return UNREADABLE.format(reason=cache.errors[lane])
    default = saved(cache, lane)
    if default is None:
        return ""
    resolution = resolve(default, lane)
    if resolution.ready:
        return WAITING.format(label=resolution.label, reason="applying it to the form.")
    return resolution.text


# -- applying --------------------------------------------------------------------------
def _apply(lane_state, lane, resolution, *, seed=False):
    """Write a resolved default into the form: base model, then its trained choice.

    Use is an explicit selection: it assigns a different base model and each
    LoRA strength through RNA, as the picker does, so only those tag the scene;
    the trained list itself has no update. A default applied automatically
    (`seed`) is not an edit of the scene: as catalog seeding does (#387), it
    stores the model index and strengths without their RNA updates, which would
    tag the scene and make every origin captured in it stale, then syncs the
    form and re-arms its price itself. Either way the form is repriced.
    """
    scope = trained_models.current_scope()
    if scope is None:
        raise ScenarioError(0, "Connect to Scenario before using a project default")
    base = resolution.base
    if not _listed(base.id, lane):
        raise ScenarioError(0, "Its base model is not in this form's model list")
    lane_state.model_key = base.id
    if lane_state.model_id != base.id:
        if seed:
            from . import generation

            # Each model enum value is its 3-tuple item's index, as in restore_model_key.
            models = [item[0] for item in runtime.enum_items(("models", lane))]
            lane_state["model_id"] = models.index(base.id)
            generation.on_model_changed(bpy.context, lane_state)  # what the update would run
        else:
            lane_state.model_id = base.id  # its update callback runs on_model_changed
    trained_models.write_slots(lane_state, lane, resolution.chosen, base.slot, scope, seed=seed)
    props.mark_estimate_dirty(lane_state)


def use(lane_state, lane):
    """Apply the saved default to this form now (explicit Use). Returns its label.

    Raises ScenarioError with the reason when it is still loading or cannot run;
    the form then keeps its current choice.
    """
    runtime.sync_catalog_context()
    cache = load()
    if lane in cache.errors:
        raise ScenarioError(0, UNREADABLE.format(reason=cache.errors[lane]))
    default = saved(cache, lane)
    if default is None:
        raise ScenarioError(0, "No project default is saved for this form")
    resolution = resolve(default, lane, read=True)
    if not resolution.ready:
        raise ScenarioError(0, resolution.text)
    _apply(lane_state, lane, resolution)
    return resolution.label


def apply_pending(scenes=None):
    """Give every form the default governs its saved default (main thread pump, never in draw).

    A form whose default still waits or cannot run keeps no choice, and its
    price is requested again whenever its blocking reason changes or ends, so
    the price line always shows the current reason. Returns whether any form
    changed.
    """
    if runtime.state.catalog is None:
        return False  # nothing is selected; selecting is the catalog request's job
    try:
        cache = load()
    except ScenarioError:
        return False
    changed = False
    for scene in bpy.data.scenes if scenes is None else scenes:
        if getattr(scene, "library", None) is not None or not hasattr(scene, "scenario"):
            continue
        for lane in LANES:
            lane_state = scene.scenario.lane_state(lane)
            if not governs(lane_state):
                continue
            text = ""
            default = saved(cache, lane)
            if lane in cache.errors:
                text = UNREADABLE.format(reason=cache.errors[lane])
            elif default is not None:
                resolution = resolve(default, lane, read=True)
                if resolution.ready:
                    try:
                        _apply(lane_state, lane, resolution, seed=True)
                    except ScenarioError:
                        continue
                    changed = True
                    continue
                text = resolution.text
            changed |= _rearm(lane_state, text)
    return changed


def _rearm(lane_state, text):
    """Reprice a governed form whose price does not show its current blocking reason.

    A form being priced is left alone; the estimate pump prices only the visible
    lane, so a hidden form waits as PENDING without repeated requests.
    """
    state = lane_state.estimate_state
    if state == "PENDING":
        return False
    if text:
        stale = state in ("IDLE", "READY") or lane_state.estimate_error != text
    else:
        stale = state in ("UNAVAILABLE", "ERROR") and lane_state.estimate_error.startswith(BLOCKING)
    if stale:
        props.mark_estimate_dirty(lane_state)
    return stale


# -- saving and clearing -----------------------------------------------------------------
def selection_default(lane_state, lane):
    """The form's current choice as a default to save; refuses one that cannot run now."""
    if lane not in LANES:
        raise ScenarioError(0, "Project defaults are kept for the Image and Render Image forms")
    if not len(lane_state.trained):
        raise ScenarioError(0, "Choose a LoRA or composition before saving a project default")
    error = trained_models.scope_error(lane_state)
    if error:
        raise ScenarioError(0, error)
    record = runtime.state.records.get(lane_state.model_id)
    if record is None or not record.parameters:
        raise ScenarioError(0, "Wait for the model description to load")
    _body, reason = trained_models.apply_to(lane_state, record, {})
    if reason:
        raise ScenarioError(0, reason)
    kinds = [slot.kind for slot in lane_state.trained]
    if any(kind not in catalog.USABLE_TRAINED_KINDS for kind in kinds):
        raise ScenarioError(0, "Wait for trained models to load")
    route = "composition" if kinds == [catalog.TRAINED_COMPOSITION] else "stack"
    picks = tuple(
        TrainedModelPick(slot.model_id, trained_models.slot_scale(slot))
        for slot in lane_state.trained
    )
    try:
        return TrainedModelDefault(lane, route, lane_state.model_id, picks)
    except ValueError as err:
        raise ScenarioError(0, str(err)) from None


def _write(lane, context_id, expected_revision, write):
    """Run one owner write; on any refusal reread the defaults so the next draw is current."""
    if not context_id or type(expected_revision) is not int or expected_revision < 0:
        _reload()
        raise ScenarioError(0, "Review the project default again before changing it")
    try:
        updated = write()
    except ScenarioError:
        _reload()
        raise
    except (StoreError, ValueError) as err:  # a stale revision, a retired owner or a bad row
        _reload()
        raise ScenarioError(0, f"{_sentence(err)} Review the project default again.") from None
    cache = cached()
    if cache is None or cache.context != context_id:
        _reload()
    else:
        runtime.state.trained_defaults = Cache(
            cache.context, {**cache.lanes, lane: updated}, cache.errors
        )
    return updated


def _reload():
    try:
        load(force=True)
    except ScenarioError:
        runtime.state.trained_defaults = None


def save(lane_state, lane, context_id, expected_revision):
    """Save the form's choice as the lane default the user reviewed (context and revision).

    The saving form keeps its choice and its price; forms the default governs
    (other scenes without an explicit choice) take it at once.
    """
    default = selection_default(lane_state, lane)
    updated = _write(
        lane,
        context_id,
        expected_revision,
        lambda: runtime.save_model_default(
            context_id, default, expected_revision=expected_revision
        ),
    )
    apply_pending()
    return updated


def clear(lane, context_id, expected_revision):
    """Clear the lane default the user reviewed; forms it was blocking are repriced."""
    updated = _write(
        lane,
        context_id,
        expected_revision,
        lambda: runtime.clear_model_default(context_id, lane, expected_revision=expected_revision),
    )
    apply_pending()
    return updated


# -- drawing (read-only) ---------------------------------------------------------------
@dataclass(frozen=True)
class View:
    loaded: bool
    context: str = ""
    revision: int = 0
    default: TrainedModelDefault | None = None
    label: str = ""
    status: str = ""  # waiting or unavailable text, "" when the default runs
    unavailable: bool = False
    error: str = ""  # the stored default cannot be read
    in_use: bool = False
    can_save: bool = False


def view(lane_state, lane):
    """What the form's project-default row shows; reads cached state only (safe in draw)."""
    cache = cached()
    if cache is None or lane not in LANES:
        return View(False)
    error = cache.errors.get(lane, "")
    default = saved(cache, lane)
    try:
        candidate = selection_default(lane_state, lane)
    except ScenarioError:
        candidate = None
    status, unavailable, text = "", False, ""
    if default is not None:
        resolution = resolve(default, lane)
        text = resolution.label
        unavailable = bool(resolution.reason)
        # Only a form the default governs waits for it; any form may learn it cannot run.
        status = resolution.text if unavailable or governs(lane_state) else ""
    return View(
        True,
        cache.context,
        revision(cache, lane),
        default,
        text,
        status,
        unavailable,
        error,
        matches(lane_state, default),
        candidate is not None and candidate != default and not error,
    )
