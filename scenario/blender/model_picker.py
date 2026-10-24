# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Model picker: Scenario's "Choose a Model" dialog inside Blender.

Modality tabs (Image, Video, Audio, 3D) with Scenario's icons, the category chips of the web app per tab (Generate,
Edit, Upscale... / Speech, Music, SFX... / Splat, Remesh, Retexture...), a search field, the list with thumbnails and
the description of the highlighted model. Deprecated models never show, and LoRAs and compositions show only under
the Image tab's Trained chip, each with the base models that run it (#97). Picking a model from another tab than the
lane's moves the scene to that modality's lane. The native dropdown stays as a small fallback button.

Layout: the tabs and the chips are compact centred groups (each button as wide as its icon and word, the group in the
middle of the dialog, like Scenario's "Choose a Model" and the lane tabs of the sidebar); the search field, the list and
the highlighted model's box stay full width."""

import logging
import textwrap
import threading
from weakref import WeakKeyDictionary

import bpy
from bpy.props import (
    BoolProperty,
    CollectionProperty,
    EnumProperty,
    FloatProperty,
    IntProperty,
    StringProperty,
)

from ..core.api import model_filter, trained_offers
from ..core.api.assets import download_file
from ..core.api.catalog import TRAINED_COMPOSITION, TRAINED_LORA
from ..core.api.errors import ScenarioError
from ..core.ui import capability_status
from . import generation, icons, props, runtime, trained_models

log = logging.getLogger("scenario.picker")

# Thumbnails fetched per refilter: the rows a user can scroll to before typing again.
THUMB_LIMIT = 40
CHIPS_PER_ROW = 6  # more category chips than this wrap onto two centred rows
LIST_ROWS = 10  # list rows when the window has room for the whole dialog
MIN_LIST_ROWS = 2
UNIT = 20  # one interface row in pixels at a UI scale of 1
# The dialog's height without its list rows, in interface rows: title, tabs, chips,
# search, the list frame, the highlighted model's box and the OK/Cancel row.
DIALOG_ROWS = 19
RECENT_FILE = "recent_models.json"
TRAINED = model_filter.TRAINED_CATEGORY
# The picker strength's RNA default, which Blender's Reset to Default Value assigns:
# the form's strength fields use the same value. No base declares it: its update
# replaces it with the highlighted LoRA's starting strength (trained_offers.strength).
STRENGTH_RESET = props.STRENGTH_RESET
_ctx = {
    "lane": "",
    "records": [],
    "current": "",
    "material_only": False,
    "panorama_only": False,
    "offers": {},  # model_id -> trained_offers.Offer of the rows under the Trained chip
    "strength": None,  # the highlighted LoRA's strength control on the chosen base
    "choice": None,  # (offer id, base id) the highlighted row runs with, kept across list rebuilds
    "open": False,  # whether the picker dialog is open; only then may list deliveries read bases
}
_pending_thumbs = set()
_pending_lock = threading.Lock()
# Worker-safe mirror of Blender's online access for thumbnails when no catalog is selected. Only the main thread sets
# or clears it, each time the picker asks for a thumbnail; download workers read it without touching bpy.
_online_access = threading.Event()
# Set by a download worker once a thumbnail is cached; the pump then refreshes the open dialog once.
_thumbs_arrived = threading.Event()
# The open dialog's popup region, keyed weakly by its operator like Studio's popups. Only a change in what the dialog
# shows refreshes it (refresh_dialog), never a pump tick: Blender rebuilds a refreshed dialog, and its OK and Cancel
# buttons refer to the block they were built in, so they never match their rebuilt copies. A highlight or press on OK
# is then dropped and the click cancelled, which made OK need several clicks while the pump refreshed it every tick.
_dialogs = WeakKeyDictionary()
_enum_cache = {}  # keeps enum item tuples alive for Blender


# -- thumbnails ---------------------------------------------------------------
def _thumb_path(model_id):
    return runtime.paths().cache_dir / "thumbs" / f"{model_id}.jpg"


def _scoped_thumb_path(model_id, scope):
    """A private model's thumbnail lives under its connection's scope, never the shared cache."""
    return runtime.paths().cache_dir / "thumbs" / "scoped" / scope[:32] / f"{model_id}.jpg"


def thumbnail_scope(record):
    """The scope key a private record's thumbnail is cached under, "" for public records."""
    if record is None or not trained_models.is_private(record):
        return ""
    return trained_models.current_scope() or ""


def _record_thumb_path(record, scope):
    return _scoped_thumb_path(record.id, scope) if scope else _thumb_path(record.id)


def _download_permission():
    """Main thread only: the worker-safe predicate a thumbnail download checks just before connecting.

    The selected catalog's permission Event follows Blender's online access on every pump tick and clears when that
    catalog retires. Without a catalog, the module Event mirrored here from runtime.online() stands in."""
    if runtime.online():
        _online_access.set()
    else:
        _online_access.clear()
    allowed = getattr(runtime.state.catalog, "network_allowed", None)
    return allowed if callable(allowed) else _online_access.is_set


def _fetch_thumbnail(url, path, model_id, allowed, key=None):
    try:
        # Online access may have been withdrawn since the row asked; a later refilter retries.
        if allowed():
            download_file(url, path, timeout=30, retries=1)
            _thumbs_arrived.set()  # the pump shows it in an open dialog
    except Exception as err:  # a missing thumbnail is cosmetic; never surface it as a job error
        # The error type only: transfer messages can carry the signed thumbnail URL.
        log.debug("thumbnail %s failed: %s", model_id, type(err).__name__)
    finally:
        with _pending_lock:
            _pending_thumbs.discard(key or model_id)


def ensure_thumbnail(record):
    """Start a background download of the model thumbnail when it is not cached yet and Blender allows online access.
    The worker rechecks the captured permission just before connecting, not during the transfer or its retry.
    Returns True when cached; a cached thumbnail still shows offline."""
    if record is None:
        return False
    scope = thumbnail_scope(record)
    if trained_models.is_private(record) and not scope:
        return False  # no selected connection to keep a private thumbnail apart
    path = _record_thumb_path(record, scope)
    if path.exists():
        return True
    url = model_filter.thumbnail_url(record)
    if not url:
        return False
    allowed = _download_permission()
    if not runtime.online() or not allowed():
        return False  # the row keeps its modality icon; a later refilter retries once online
    key = f"{scope}:{record.id}" if scope else record.id
    with _pending_lock:
        if key in _pending_thumbs:
            return False
        _pending_thumbs.add(key)
    threading.Thread(
        target=_fetch_thumbnail,
        args=(url, path, record.id, allowed, key),
        name=f"scenario-thumb-{record.id}",
        daemon=True,
    ).start()
    return False


def thumbnail_icon(model_id, scope=""):
    """icon_id of a cached thumbnail, 0 when there is none. Only reads a file that already exists (draw-safe).

    A private model passes the scope its thumbnail was cached under."""
    path = _scoped_thumb_path(model_id, scope) if scope else _thumb_path(model_id)
    if not path.exists():
        return 0
    previews = runtime.previews()
    key = f"thumb:{scope[:32]}:{model_id}" if scope else f"thumb:{model_id}"
    if key not in previews:
        try:
            previews.load(key, str(path), "IMAGE")
        except (KeyError, RuntimeError):
            return 0
    return previews[key].icon_id


# -- taxonomy helpers -----------------------------------------------------------------
def modality_for_lane(lane):
    return model_filter.LANE_MODALITY.get(lane, "image")


def candidate_records(modality):
    """Every visible catalog model of a modality (LoRAs and deprecated out), plus the lane lists (curated first)."""
    records = [
        r
        for r in runtime.state.records.values()
        if model_filter.visible(r) and model_filter.modality_of(r) == modality
    ]
    seen = {r.id for r in records}
    for lane, lane_modality in model_filter.LANE_MODALITY.items():
        if lane_modality != modality:
            continue
        for record in runtime.state.lane_models.get(lane) or []:
            if record.id not in seen and model_filter.visible(record):
                records.append(record)
                seen.add(record.id)
    return records


def _recent():
    return model_filter.RecentModels(runtime.paths().state_dir / RECENT_FILE)


def _modality_items(self, context):
    key = "modalities"
    items = _enum_cache.get(key)
    if items is None:
        items = []
        for index, (ident, label, icon_name) in enumerate(model_filter.MODALITIES):
            value = icons.icon(icon_name)
            items.append(
                (
                    ident,
                    label,
                    f"{label} models",
                    value if value else icons.builtin(icon_name),
                    index,
                )
            )
        _enum_cache[key] = items
    return items


def _category_items(self, context):
    wm = getattr(context, "window_manager", None) or bpy.context.window_manager
    modality = getattr(wm, "scenario_picker_modality", "image") or "image"
    key = ("categories", modality)
    items = _enum_cache.get(key)
    if items is None:
        items = [
            (ident, label, f"{label} models", "NONE", index)
            for index, (ident, label) in enumerate(model_filter.category_items(modality))
        ]
        _enum_cache[key] = items
    return items


def _offer_note(offer):
    """The row's short note: how the trained model runs here, or why it does not."""
    if not offer.available:
        return offer.reason
    kind = trained_models.kind_text(offer.record, offer.kind)
    return f"{kind} via {', '.join(base.record.name for base in offer.bases)}"


def _refilter_trained(wm):
    """Trained rows for the lane the choice lands in: available ones first, then why others cannot run."""
    lane = trained_models.trained_lane(_ctx["lane"])
    rows = [
        offer
        for offer in trained_models.offers(lane)
        if model_filter.matches(offer.record, wm.scenario_picker_query)
    ]
    _ctx["offers"] = {offer.id: offer for offer in rows}
    lane_state = _lane_selection()
    chosen = lane_state.trained if lane_state is not None else ()
    highlighted = chosen[0].model_id if len(chosen) else ""
    items = wm.scenario_picker_items
    # Keep a highlighted trained row; a base model row left by another chip (prepare
    # passes through All) gives way to the form's current choice.
    if 0 <= wm.scenario_picker_index < len(items) and items[wm.scenario_picker_index].kind:
        highlighted = items[wm.scenario_picker_index].model_id
    items.clear()
    index = 0
    for position, offer in enumerate(rows):
        item = items.add()
        item.model_id, item.name = offer.id, offer.record.name
        item.description = _offer_note(offer)
        item.modality, item.kind = "image", offer.kind
        item.available = offer.available
        item.scope = thumbnail_scope(offer.record)
        if offer.id == highlighted:
            index = position
    wm.scenario_picker_index = index  # its update chooses the base and strength to show
    for offer in rows[:THUMB_LIMIT]:
        ensure_thumbnail(offer.record)
    return [offer.record for offer in rows]


def is_trained_view(wm=None):
    wm = wm or bpy.context.window_manager
    return (
        wm is not None
        and not _ctx["material_only"]
        and getattr(wm, "scenario_picker_category", "") == TRAINED
    )


def trained_view_open(wm=None):
    """Whether an open picker dialog shows the Trained chip.

    The chip stays selected on the window manager after the dialog closes, so
    list deliveries ask this before they start base-description reads.
    """
    return _ctx["open"] and bool(_ctx["lane"]) and is_trained_view(wm)


def refresh_dialog():
    """Rebuild the open dialog because what it shows changed (main thread, not draw).

    The dialog is a temporary popup region that an area redraw misses. Never call
    this on a timer: each rebuild drops a highlight or press on OK (see _dialogs).
    Returns whether a dialog was tagged.
    """
    if not _ctx["open"]:
        return False
    tagged = False
    for operator, region in list(_dialogs.items()):
        try:
            region.tag_refresh_ui()
            tagged = True
        except ReferenceError:
            _dialogs.pop(operator, None)
    return tagged


def refresh_thumbnails():
    """Main thread, once per pump tick: refresh the open dialog once new thumbnails are cached."""
    if not _thumbs_arrived.is_set():
        return False
    # A thumbnail cached after this clear sets it again and is shown on a later tick.
    _thumbs_arrived.clear()
    return refresh_dialog()


def refresh_trained():
    """Rebuild trained rows when their records or base descriptions change (main thread, not draw)."""
    wm = bpy.context.window_manager
    if trained_view_open(wm):
        refilter(wm)
        refresh_dialog()


def refilter(wm):
    """Rebuild the picker rows from the tab, chip and query; keeps the highlighted model when it survives."""
    if is_trained_view(wm):
        return _refilter_trained(wm)
    _ctx["offers"] = {}
    modality = wm.scenario_picker_modality
    category = wm.scenario_picker_category
    if _ctx["material_only"] or _ctx["panorama_only"]:
        filtered = [r for r in _ctx["records"] if model_filter.matches(r, wm.scenario_picker_query)]
    else:
        filtered = model_filter.filter_records(
            _ctx["records"],
            modality,
            category,
            wm.scenario_picker_query,
            _recent().ids(_ctx["lane"]),
        )
    highlighted = _ctx["current"]
    items = wm.scenario_picker_items
    if 0 <= wm.scenario_picker_index < len(items):
        highlighted = items[wm.scenario_picker_index].model_id or highlighted
    items.clear()
    index = 0
    for position, record in enumerate(filtered):
        item = items.add()
        item.model_id, item.name = record.id, record.name
        item.description = record.short_description or ""
        item.modality = model_filter.modality_of(record) or "image"
        item.kind, item.available, item.scope = "", True, ""
        if record.id == highlighted:
            index = position
    wm.scenario_picker_index = index
    for record in filtered[:THUMB_LIMIT]:
        ensure_thumbnail(record)
    return filtered


def _on_modality_change(self, context):
    # A lane's own list (Materials, the Environment mode's contract models) is not the tab's catalog.
    if not (_ctx["material_only"] or _ctx["panorama_only"]):
        _ctx["records"] = candidate_records(self.scenario_picker_modality)
    _enum_cache.pop(("categories", self.scenario_picker_modality), None)
    self.scenario_picker_category = "all"  # its update refilters


def _on_filter_change(self, context):
    refilter(self)


def _on_category_change(self, context):
    if self.scenario_picker_category == TRAINED and not _ctx["material_only"]:
        # Base descriptions are read only now, never on a catalog refresh.
        trained_models.request_bases(_ctx["lane"] or "image")
    refilter(self)


def highlighted_offer(wm=None):
    """The highlighted trained row's offer, or None (read-only)."""
    wm = wm or bpy.context.window_manager
    items = wm.scenario_picker_items
    if not is_trained_view(wm) or not 0 <= wm.scenario_picker_index < len(items):
        return None
    return _ctx["offers"].get(items[wm.scenario_picker_index].model_id)


def _lane_selection():
    """The lane state a trained choice lands in, or None."""
    scene = bpy.context.scene
    if scene is None:
        return None
    return scene.scenario.lane_state(trained_models.trained_lane(_ctx["lane"]))


def _default_base(offer):
    """The lane's own base when it runs the offer, the only base, or none: never a silent pick."""
    lane_state = _lane_selection()
    current = lane_state.model_id if lane_state is not None else ""
    ids = [base.id for base in offer.bases]
    if current in ids:
        return current
    return ids[0] if len(ids) == 1 else "NONE"


def _base_items(self, context):
    offer = highlighted_offer(self)
    if offer is None or not offer.bases:
        return _enum_cache.setdefault("bases:none", [("NONE", "No base model", "", 0)])
    key = ("bases", offer.id, tuple(base.id for base in offer.bases))
    items = _enum_cache.get(key)
    if items is None:
        items = [
            (base.id, base.record.name, base.record.short_description or "", index + 1)
            for index, base in enumerate(offer.bases)
        ]
        if len(items) > 1:
            items.insert(0, ("NONE", "Choose a base model", "Choose the model it runs with", 0))
        _enum_cache[key] = items
    return items


def chosen_base(wm=None):
    """The base the highlighted offer would run with, or None until one is chosen."""
    wm = wm or bpy.context.window_manager
    offer = highlighted_offer(wm)
    if offer is None:
        return None
    try:
        base_id = wm.scenario_picker_base
    except (TypeError, ValueError):
        return None
    return next((base for base in offer.bases if base.id == base_id), None)


def _current_scale(offer, base):
    """The strength this LoRA already has on this base in the lane, else None."""
    lane_state = _lane_selection()
    if lane_state is None or lane_state.model_id != base.id:
        return None
    slot = next((slot for slot in lane_state.trained if slot.model_id == offer.id), None)
    return trained_models.slot_scale(slot) if slot is not None else None


def _on_base_change(self, context):
    offer, base = highlighted_offer(self), chosen_base(self)
    record = offer.record if offer is not None else None
    strength = trained_offers.strength(base.slot, record) if base is not None else None
    _ctx["strength"] = strength
    _ctx["choice"] = (offer.id, base.id) if offer is not None and base is not None else None
    if offer is None or strength is None or offer.kind != TRAINED_LORA:
        return
    current = _current_scale(offer, base)
    self.scenario_picker_strength = strength.initial if current is None else current


def _on_highlight(self, context):
    offer = highlighted_offer(self)
    if offer is None:
        _ctx["strength"] = None
        _ctx["choice"] = None
        return
    kept = _ctx["choice"]
    try:
        if kept is not None and kept[0] == offer.id and kept[1] in {b.id for b in offer.bases}:
            # The same row after its list was rebuilt (base reads, the trained list):
            # keep the user's base and strength. The enum stores a position that new
            # bases can shift, so name the base again.
            value = self.scenario_picker_strength
            self.scenario_picker_base = kept[1]
            if offer.kind == TRAINED_LORA and _ctx["strength"] is not None:
                self.scenario_picker_strength = value  # its update keeps it within range
            return
        self.scenario_picker_base = _default_base(offer)  # its update sets the strength
    except TypeError:
        _ctx["strength"] = None
        _ctx["choice"] = None


def _on_strength_change(self, context):
    strength = _ctx.get("strength")
    if strength is None:
        return
    if self.scenario_picker_strength == STRENGTH_RESET:
        # A reset starts again from the LoRA's own strength or the web app's default.
        self.scenario_picker_strength = strength.initial
        return
    value = strength.clamp(self.scenario_picker_strength)
    if abs(value - self.scenario_picker_strength) > 1e-6:
        self.scenario_picker_strength = value


def prepare(context, lane, category="all"):
    """Open the picker on the lane's modality tab with the lane's model highlighted."""
    scene = context.scene
    lane = lane or scene.scenario.lane
    lane_state = scene.scenario.lane_state(lane)
    wm = context.window_manager
    _ctx["lane"] = lane
    _ctx["open"] = True  # execute() and cancel() close it
    _ctx["choice"] = None  # a new dialog starts from the form's base and strength
    _ctx["current"] = (
        (lane_state.model_key or lane_state.model_id) if lane_state is not None else ""
    )
    _ctx["material_only"] = lane == "material"
    # The Environment lane lists only the verified contract models of its mode.
    _ctx["panorama_only"] = lane == "panorama"
    modality = modality_for_lane(lane)
    if _ctx["material_only"]:
        # The Materials lane list: PATINA, then Scenario Texture, then other texture models.
        _ctx["records"] = list(runtime.state.lane_models.get("material") or [])
    elif _ctx["panorama_only"]:
        _ctx["records"] = generation.panorama_models(
            scene.scenario.panorama_mode, list(runtime.state.records.values())
        )
    else:
        _ctx["records"] = candidate_records(modality)
    wm.scenario_picker_index = -1
    if wm.scenario_picker_modality != modality:
        wm.scenario_picker_modality = modality  # update: records unless curated, refilter
    elif wm.scenario_picker_category != "all":
        wm.scenario_picker_category = "all"
    if category == TRAINED and not _ctx["material_only"] and modality == "image":
        wm.scenario_picker_category = TRAINED  # its update requests base descriptions
    if wm.scenario_picker_query:
        wm.scenario_picker_query = ""  # update callback refilters
    else:
        refilter(wm)
    return wm.scenario_picker_items


def _target_lane(scene, record, lane):
    """The lane a chosen model belongs to: the current lane when the modality matches, else the modality's base lane
    (3D-to-3D models go to the Edit 3D lane / mode)."""
    modality = model_filter.modality_of(record)
    caps = set(record.capabilities)
    if modality == "3d" and "3d23d" in caps and "txt23d" not in caps and "img23d" not in caps:
        return "edit3d"
    if modality_for_lane(lane) == modality and not (lane == "edit3d" and "3d23d" not in caps):
        return lane
    return model_filter.BASE_LANE.get(modality, lane)


def _enum_has(struct, prop_name, value):
    try:
        items = {item.identifier for item in struct.bl_rna.properties[prop_name].enum_items}
    except (KeyError, AttributeError):
        return False
    if items:
        return value in items
    # a dynamic enum (items callback, like the lane tabs with their icons) reports no RNA items: probe with an assignment
    try:
        current = getattr(struct, prop_name)
        setattr(struct, prop_name, value)
        ok = getattr(struct, prop_name) == value
        if ok and current != value:
            setattr(struct, prop_name, current)
        return ok
    except TypeError:
        return False


def _show_lane(scene, target, record):
    """Make the target lane visible: switch the tab; for 3D pick the input mode the model needs."""
    scenario = scene.scenario
    if _enum_has(scenario, "lane", target):
        if scenario.lane != target:
            scenario.lane = target
    elif target == "edit3d" and _enum_has(scenario, "lane", "3d"):
        scenario.lane = "3d"
        if _enum_has(scenario, "three_d_mode", "EDIT"):
            scenario.three_d_mode = "EDIT"
    if target == "3d":
        caps = set(record.capabilities)
        if "txt23d" in caps and "img23d" not in caps:
            mode = "TEXT"
        elif any(h in (record.id + record.name).lower() for h in ("multi", "multiview")):
            mode = "MULTI"
        else:
            mode = "IMAGE"
        if _enum_has(scenario, "three_d_mode", mode) and scenario.three_d_mode != mode:
            scenario.three_d_mode = mode


def apply_choice(context, lane, index=None):
    """Make the highlighted (or `index`) row the model of the lane it belongs to. Returns (model_id, lane) or (None, None)."""
    wm = context.window_manager
    items = wm.scenario_picker_items
    index = wm.scenario_picker_index if index is None else index
    if not (0 <= index < len(items)):
        return None, None
    model_id = items[index].model_id
    record = next(
        (r for r in _ctx["records"] if r.id == model_id), None
    ) or runtime.state.records.get(model_id)
    lane = lane or _ctx["lane"] or context.scene.scenario.lane
    scene = context.scene
    target = _target_lane(scene, record, lane) if record is not None else lane
    lane_state = scene.scenario.lane_state(target) or scene.scenario.lane_state(lane)
    if lane_state is None:
        return None, None
    if record is not None:
        _show_lane(scene, target, record)
    lane_state.model_key = model_id
    valid = [item[0] for item in runtime.enum_items(("models", target))]
    if model_id in valid:
        if lane_state.model_id != model_id:
            lane_state.model_id = model_id  # the update callback runs on_model_changed
        else:
            generation.on_model_changed(context, lane_state)
    else:
        generation.request_model(model_id)
        runtime.set_message(
            f"{record.name if record else model_id} chosen; its list entry appears once the schema is loaded"
        )
    _recent().touch(lane, model_id)
    if target != lane:
        _recent().touch(target, model_id)
    return model_id, target


def highlighted_record():
    wm = bpy.context.window_manager
    items = wm.scenario_picker_items
    if 0 <= wm.scenario_picker_index < len(items):
        model_id = items[wm.scenario_picker_index].model_id
        offer = _ctx["offers"].get(model_id) if is_trained_view(wm) else None
        if offer is not None:
            return offer.record
        return next(
            (r for r in _ctx["records"] if r.id == model_id), None
        ) or runtime.state.records.get(model_id)
    return None


def trained_effect(offer, base):
    """What choosing the offer through this base does to the lane's trained choice (read-only)."""
    lane_state = _lane_selection()
    if lane_state is None or base is None:
        return ""
    current = list(lane_state.trained)
    others = [slot for slot in current if slot.model_id != offer.id]
    same = lane_state.model_id == base.id and trained_models.scope_error(lane_state) is None
    if not current:
        return ""
    if (
        not same
        or offer.kind == TRAINED_COMPOSITION
        or any(slot.kind == TRAINED_COMPOSITION for slot in current)
    ):
        if len(current) == 1 and current[0].model_id == offer.id and same:
            return ""
        count = len(current)
        return f"Replaces the {count} trained model{'s' if count != 1 else ''} chosen in this form"
    if len(others) < len(current):
        return "Changes the strength of this LoRA in the form"
    count = len(others)
    return f"Adds to the {count} LoRA{'s' if count != 1 else ''} chosen in this form"


def apply_trained_choice(context, lane):
    """Run the highlighted trained model through the chosen base. Returns (model_id, lane)."""
    wm = context.window_manager
    offer = highlighted_offer(wm)
    if offer is None:
        return None, None
    base = chosen_base(wm)
    scale = wm.scenario_picker_strength if offer.kind == TRAINED_LORA else None
    if scale == STRENGTH_RESET:
        scale = None  # never set for this base: the choice starts at the LoRA's starting strength
    target = trained_models.choose(
        context, lane or _ctx["lane"], offer, base.id if base else "", scale
    )
    return offer.id, target


def category_labels(record):
    labels = dict(model_filter.category_items(model_filter.modality_of(record)))
    return ", ".join(labels.get(c, c) for c in sorted(model_filter.categories_of(record)))


# -- dialog layout --------------------------------------------------------------------
def list_rows(context):
    """List rows that keep the whole dialog, OK and Cancel included, inside the window.

    Blender keeps a dialog within its window but never shrinks it, so at a large
    UI scale a ten-row list would push OK and Cancel off-screen. The window height
    is in pixels; the system UI scale includes the display density.
    """
    window = getattr(context, "window", None)
    if window is None or not window.height:
        return LIST_ROWS
    scale = context.preferences.system.ui_scale or 1.0
    rows = int(window.height / scale / UNIT) - DIALOG_ROWS
    return max(MIN_LIST_ROWS, min(LIST_ROWS, rows))


def chip_rows(chips, per_row=CHIPS_PER_ROW):
    """The category chips as one row, or two balanced rows when there are more than `per_row` (Video has 8, Image
    with its Trained chip and 3D have 9, Audio 5)."""
    chips = list(chips)
    if len(chips) <= per_row:
        return [chips]
    half = (len(chips) + 1) // 2
    return [chips[:half], chips[half:]]


def _centered_cells(parent, struct, prop, values):
    """A continuous full-width segmented control: equal cells, no gaps, each with the enum item's icon and label."""
    from .panels import equal_segments

    equal_segments(parent, struct, prop, values)


def draw_filters(layout, wm):
    """Modality tabs and category chips as justified rows with the icon glued to its label and the pair centred in
    each cell. The tab icon comes from the enum item itself (Scenario's PNG, or the built-in fallback when headless)."""
    col = layout.column()
    _centered_cells(
        col,
        wm,
        "scenario_picker_modality",
        [ident for ident, _label, _icon in model_filter.MODALITIES],
    )
    col.separator()
    chips = col.column(align=True)
    for chip_row in chip_rows(model_filter.category_items(wm.scenario_picker_modality)):
        _centered_cells(
            chips, wm, "scenario_picker_category", [ident for ident, _label in chip_row]
        )


def draw_trained(layout, wm, offer):
    """The highlighted trained model: its kind, base, strength and effect on the form (read-only)."""
    box = layout.box()
    row = box.row()
    icon_id = thumbnail_icon(offer.id, thumbnail_scope(offer.record))
    if icon_id:
        row.template_icon(icon_value=icon_id, scale=5.0)
    col = row.column(align=True)
    col.label(text=offer.record.name, **icons.kwargs("image"))
    col.label(text=trained_models.kind_text(offer.record, offer.kind))
    if not offer.available:
        col.label(text=offer.reason, icon="ERROR")
    else:
        if len(offer.bases) > 1:
            col.prop(wm, "scenario_picker_base", text="Run with")
        else:
            col.label(text=f"Runs with {offer.bases[0].record.name}")
        base = chosen_base(wm)
        strength = trained_offers.strength(base.slot) if base is not None else None
        if offer.kind == TRAINED_LORA and strength is not None:
            col.prop(
                wm,
                "scenario_picker_strength",
                text=f"Strength ({strength.minimum:g} to {strength.maximum:g})",
            )
        elif offer.kind == TRAINED_COMPOSITION:
            count = len(trained_offers.concepts(offer.record))
            col.label(
                text=f"Combines {count} LoRA{'s' if count != 1 else ''} with their own strengths"
            )
        effect = trained_effect(offer, base)
        if effect:
            col.label(text=effect, icon="INFO")
    status = trained_models.scan_status(_ctx["lane"])
    if status:
        col.label(text=status, icon="SORTTIME")
    col.label(text=trained_models.EXPERIMENTAL, icon="EXPERIMENTAL")
    muted = col.row()
    muted.enabled = False
    muted.label(text=offer.id)


# -- Blender classes ----------------------------------------------------------------
class ScenarioPickerItem(bpy.types.PropertyGroup):
    model_id: StringProperty()
    name: StringProperty()
    description: StringProperty()
    modality: StringProperty(default="image")
    kind: StringProperty()  # lora, composition or another trained kind under the Trained chip
    available: BoolProperty(default=True)
    scope: StringProperty()  # the private thumbnail's connection scope


class SCENARIO_UL_models(bpy.types.UIList):
    bl_idname = "SCENARIO_UL_models"

    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        row = layout.row(align=True)
        row.active = item.available  # a trained model no base runs here stays readable, greyed
        icon_id = thumbnail_icon(item.model_id, item.scope)
        if icon_id:
            row.template_icon(icon_value=icon_id, scale=1.0)
        else:
            row.label(text="", **icons.kwargs(item.modality))
        row.label(text=item.name)
        if item.description:
            muted = row.row(align=True)
            muted.enabled = False
            muted.alignment = "RIGHT"
            muted.label(text=item.description[:44] + ("..." if len(item.description) > 44 else ""))

    def draw_filter(self, context, layout):
        pass  # search and chips live above the list


class SCENARIO_OT_pick_model(bpy.types.Operator):
    bl_idname = "scenario.pick_model"
    bl_label = "Choose a model"
    bl_description = "Search the Scenario catalog by modality and category and pick the model"
    bl_options = {"INTERNAL"}
    lane: StringProperty()
    category: StringProperty(default="all")

    def invoke(self, context, event):
        prepare(context, self.lane, self.category)
        self._rows = list_rows(context)
        return context.window_manager.invoke_props_dialog(self, width=620)

    def draw(self, context):
        # Base descriptions and thumbnails keep arriving while the dialog is open; their
        # deliveries refresh it through refresh_dialog, never every pump tick.
        region = getattr(context, "region_popup", None)
        if region is not None:
            _dialogs[self] = region
        wm = context.window_manager
        layout = self.layout
        layout.separator()  # breathing room under the title, as in the composer
        if _ctx["material_only"]:
            header = layout.row()
            header.alignment = "CENTER"
            header.label(text="Materials: texture and PBR models", icon="MATERIAL")
        elif _ctx["panorama_only"]:
            header = layout.row()
            header.alignment = "CENTER"
            header.label(text="Environment: verified panorama models of this mode", icon="WORLD")
        else:
            draw_filters(layout, wm)
        layout.separator()
        layout.prop(
            wm, "scenario_picker_query", text="", icon="VIEWZOOM", placeholder="Search models"
        )
        layout.template_list(
            "SCENARIO_UL_models",
            "",
            wm,
            "scenario_picker_items",
            wm,
            "scenario_picker_index",
            rows=getattr(self, "_rows", LIST_ROWS),
        )
        if is_trained_view(wm):
            if not wm.scenario_picker_items:
                state = runtime.state
                text = (
                    f"Could not load trained models: {state.trained_error}"
                    if state.trained_error
                    else "No trained model matches"
                    if state.trained_loaded
                    else "Trained models are still loading"
                )
                layout.label(text=text, icon="INFO")
            offer = highlighted_offer(wm)
            if offer is not None:
                draw_trained(layout, wm, offer)
            elif trained_models.scan_status(_ctx["lane"]):
                layout.label(text=trained_models.scan_status(_ctx["lane"]), icon="SORTTIME")
            return
        if not wm.scenario_picker_items:
            layout.label(
                text="No model matches" if _ctx["records"] else "Models are still loading",
                icon="INFO",
            )
        record = highlighted_record()
        if record is None:
            return
        box = layout.box()
        row = box.row()
        icon_id = thumbnail_icon(record.id)
        if icon_id:
            row.template_icon(icon_value=icon_id, scale=5.0)
        col = row.column(align=True)
        col.label(text=record.name, **icons.kwargs(model_filter.modality_of(record) or "image"))
        cats = category_labels(record)
        if cats:
            col.label(text=cats)
        status = capability_status.model_status(record.capabilities)
        if status:
            col.label(text=status, icon="EXPERIMENTAL")
        for line in textwrap.wrap(record.short_description or "", 70)[:3]:
            col.label(text=line)
        muted = col.row()
        muted.enabled = False
        muted.label(text=record.id)

    def cancel(self, context):
        _ctx["open"] = False
        _dialogs.clear()  # one picker dialog at a time shares _ctx

    def execute(self, context):
        _ctx["open"] = False  # OK closes the dialog, whether or not the choice applies
        _dialogs.clear()
        if is_trained_view(context.window_manager):
            try:
                model_id, target = apply_trained_choice(context, self.lane)
            except ScenarioError as err:
                self.report({"WARNING"}, err.reason)
                return {"CANCELLED"}
            if model_id is None:
                self.report({"WARNING"}, "No trained model highlighted")
                return {"CANCELLED"}
            record = runtime.state.trained_records.get(model_id)
            where = "" if target == (self.lane or target) else f" (in {target.replace('_', ' ')})"
            self.report({"INFO"}, f"Trained model: {record.name if record else model_id}{where}")
            return {"FINISHED"}
        model_id, target = apply_choice(context, self.lane)
        if model_id is None:
            self.report({"WARNING"}, "No model highlighted")
            return {"CANCELLED"}
        record = runtime.state.records.get(model_id)
        where = "" if target == (self.lane or target) else f" (in {target.replace('_', ' ')})"
        self.report({"INFO"}, f"Model: {record.name if record else model_id}{where}")
        return {"FINISHED"}


def draw_model_row(layout, lane_state, lane):
    """A "Model" section (like Clip to render / Camera path): a header, then a wide button opening the picker
    (its icon next to the model name, followed by a trained choice as on the composer's chip) and the native
    dropdown at the right as a fallback. A model offering an unaccepted capability adds its read-only experimental
    status below. The Image and Render Image forms then show their "Trained models" section: the chosen LoRAs with
    strengths, Add and the project default."""
    box = layout.box()
    box.label(text="Model", icon="NODE_MATERIAL")
    record = runtime.state.records.get(lane_state.model_id)
    if record is not None:
        # "Base · LoRA (+n)", the composer chip's label, read from the form's slots only.
        label = trained_models.selection_label(lane_state, record.name)
        icon_kwargs = icons.kwargs(model_filter.modality_of(record) or modality_for_lane(lane))
    else:
        label = "Choose a model..." if runtime.state.catalog_loaded else "Loading models..."
        icon_kwargs = {"icon": "VIEWZOOM"}
    row = box.row(align=True)
    area = row.split(factor=0.9, align=True)
    area.operator("scenario.pick_model", text=label, **icon_kwargs).lane = lane
    area.prop(lane_state, "model_id", text="", icon_only=True)
    status = capability_status.model_status(record.capabilities) if record is not None else ""
    if status:
        box.label(text=status, icon="EXPERIMENTAL")
    from . import trained_section

    trained_section.draw(layout, lane_state, lane)


CLASSES = (ScenarioPickerItem, SCENARIO_UL_models, SCENARIO_OT_pick_model)


def register():
    for cls in CLASSES:
        bpy.utils.register_class(cls)
    _enum_cache.clear()
    wm = bpy.types.WindowManager
    wm.scenario_picker_items = CollectionProperty(type=ScenarioPickerItem)
    wm.scenario_picker_index = IntProperty(default=0, update=_on_highlight)
    wm.scenario_picker_query = StringProperty(
        name="Search",
        description="Filter models by name, description, tag or id",
        options={"TEXTEDIT_UPDATE"},
        update=_on_filter_change,
    )
    wm.scenario_picker_modality = EnumProperty(
        name="Modality", items=_modality_items, update=_on_modality_change
    )
    wm.scenario_picker_category = EnumProperty(
        name="Category", items=_category_items, update=_on_category_change
    )
    wm.scenario_picker_base = EnumProperty(
        name="Run with",
        description="The base model this LoRA or composition runs with",
        items=_base_items,
        update=_on_base_change,
    )
    wm.scenario_picker_strength = FloatProperty(
        name="Strength",
        description="LoRA strength, within the range the base model declares",
        default=STRENGTH_RESET,
        precision=2,
        step=5,
        update=_on_strength_change,
    )


def unregister():
    wm = bpy.types.WindowManager
    for name in (
        "scenario_picker_strength",
        "scenario_picker_base",
        "scenario_picker_category",
        "scenario_picker_modality",
        "scenario_picker_query",
        "scenario_picker_index",
        "scenario_picker_items",
    ):
        if hasattr(wm, name):
            delattr(wm, name)
    _dialogs.clear()
    for cls in reversed(CLASSES):
        try:
            bpy.utils.unregister_class(cls)
        except RuntimeError:
            pass  # already unregistered (tests swap the module in place)
    _enum_cache.clear()
