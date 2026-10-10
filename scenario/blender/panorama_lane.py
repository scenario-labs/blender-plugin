# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Native Environment lane: panorama references and the Make HDRI form prefill.

A panorama-kind input (the Flux restyle image, the HDRI and upscale source)
accepts only two references. A saved result chosen with **Use saved panorama**
must still be a downloaded LDR 360 result of the selected scope whose saved
metadata declares an equirectangular projection; build_request rechecks it
against storage with the same check as local MCP. A local file must pass the
bounded 2:1 PNG/JPEG preflight before upload, and the upload is bound to the
checked bytes. Neither path quotes or submits: the form keeps its exact-quote
and approval flow, and results stay saved until an explicit World approval.
"""

import hashlib
from pathlib import Path

import bpy
from bpy.props import EnumProperty, IntProperty, StringProperty

from ..core.api.errors import ScenarioError
from ..core.scene import panorama, panorama_contract
from . import props, runtime

# Reference markers. A saved 360 result keeps its projection; an uploaded file
# keeps the size its preflight measured.
PROJECTION = "_scenario_reference_projection"
PANORAMA_SIZE = "_scenario_reference_panorama"
MARKERS = (PROJECTION, PANORAMA_SIZE)
_CHOICES = {}  # keeps dynamic enum items alive for Blender
_CANDIDATE_LIMIT = 50  # bounds the dialog; saved jobs have no creation order to rank by


def contract(lane_state):
    """The Environment contract of this form's model, or None outside the lane."""
    if props.lane_of(lane_state) != "panorama":
        return None
    return panorama_contract.contract_for(lane_state.model_id)


def is_panorama_input(lane_state, param_name):
    """Whether this input takes a 360 panorama rather than an ordinary image."""
    current = contract(lane_state)
    rule = panorama_contract.reference_rule(current, param_name) if current else None
    return rule is not None and rule.kind == panorama_contract.PANORAMA


def preflight_file(path):
    """Check a local panorama file before upload; return its info and SHA-256.

    The upload is then bound to these exact bytes, so a file edited after the
    check fails staging instead of sending unchecked bytes.
    """
    path = Path(path)
    try:
        size = path.stat().st_size
    except OSError:
        raise ScenarioError(0, "Choose a readable panorama file") from None
    if not 1 <= size <= panorama.MAX_FILE_BYTES:
        raise ScenarioError(0, "Choose a panorama file within the 128 MiB limit")
    try:
        data = path.read_bytes()
    except OSError:
        raise ScenarioError(0, "Choose a readable panorama file") from None
    try:
        info = panorama.inspect_panorama(data)
    except panorama.PanoramaError as error:
        raise ScenarioError(0, f"This file is not a usable 360 panorama: {error}") from None
    if info.hdr_capable:
        raise ScenarioError(0, "Use a 2:1 PNG or JPEG panorama; an OpenEXR file is already HDR")
    return info, hashlib.sha256(data).hexdigest()


def native_refs(lane_state, references):
    """Panorama references of the form that the contract may accept, by asset ID.

    Saved results are rechecked against the selected scope's storage now;
    checked uploads carry their measured size. Other asset IDs are left out, so
    the contract refuses them. Callers run scope_error first.
    """
    from . import history

    saved, refs = set(), {}
    for ref in references:
        if (
            ref.source != "ASSET"
            or not ref.asset_id
            or not is_panorama_input(lane_state, ref.param_name)
        ):
            continue
        if ref.get(PROJECTION) == "equirectangular":
            saved.add(ref.asset_id)
        elif isinstance(size := ref.get(PANORAMA_SIZE), str):
            width, _, height = size.partition("x")
            if width.isdigit() and height.isdigit():
                refs[ref.asset_id] = panorama_contract.PanoramaRef(
                    ref.asset_id, width=int(width), height=int(height)
                )
    if saved:
        refs.update(panorama_contract.saved_panorama_refs(history.saved_records(), saved))
    return refs


def candidates():
    """Saved, downloaded LDR 360 results of the selected scope, in storage order."""
    from . import history

    found = []
    for record in history.saved_records():
        for item in record.results:
            if panorama_contract.is_ldr_panorama(item):
                found.append((record, item))
    return found[:_CANDIDATE_LIMIT]


def _saved_item(request_id, asset_id):
    store = runtime.ensure_job_store()
    record = store.get(request_id)
    item = next(
        (
            entry
            for entry in (record.results if record is not None else ())
            if entry.asset.asset_id == asset_id
        ),
        None,
    )
    if item is None or not panorama_contract.is_ldr_panorama(item):
        raise ScenarioError(
            0, "Choose a saved, downloaded 360 panorama result from this account and project"
        )
    return store, record, item


def attach_saved(scene, param_name, request_id, asset_id):
    """Attach one verified saved 360 result to a panorama input; it never quotes."""
    from .reference_form import _ASSET, _KIND, _SCOPE, scope_key

    lane_state = scene.scenario.lane_state("panorama")
    if not is_panorama_input(lane_state, param_name):
        raise ScenarioError(0, "Choose a model input that takes a saved 360 panorama")
    store, record, item = _saved_item(request_id, asset_id)
    for index in range(len(lane_state.references) - 1, -1, -1):
        if lane_state.references[index].param_name == param_name:
            lane_state.references.remove(index)
    ref = lane_state.references.add()
    model = runtime.state.records.get(record.intent.target_id)
    ref.param_name, ref.source, ref.asset_id = param_name, "ASSET", asset_id
    ref.label = f"360 panorama: {item.asset.name}" + (f" ({model.name})" if model else "")
    ref[_SCOPE] = scope_key(store.scope)
    ref[_ASSET] = asset_id
    ref[_KIND] = "image"
    ref[PROJECTION] = "equirectangular"
    props.mark_estimate_dirty(lane_state)
    return ref


def prefill_hdri(context, context_id, request_id, asset_id):
    """Open the Environment HDRI form on one saved LDR 360 result; no quote or submission."""
    from . import generation

    if context_id != runtime.state.job_context_id:
        raise ScenarioError(0, "The connection changed; inspect saved jobs again")
    _saved_item(request_id, asset_id)
    hdri = next(
        (
            record
            for record in generation.panorama_models(
                panorama_contract.HDRI, list(runtime.state.records.values())
            )
        ),
        None,
    )
    if hdri is None:
        raise ScenarioError(0, "The HDRI model is not in the loaded catalog; refresh models")
    rule = next(
        rule
        for rule in panorama_contract.contract_for(hdri.id).references
        if rule.kind == panorama_contract.PANORAMA
    )
    scene = context.scene
    scenario = scene.scenario
    scenario.lane = "panorama"
    generation.select_panorama_mode(context, panorama_contract.HDRI)
    lane_state = scenario.panorama
    lane_state.model_key = hdri.id
    if lane_state.model_id != hdri.id:
        lane_state.model_id = hdri.id
    return attach_saved(scene, rule.param, request_id, asset_id)


def _choice_items(self, context):
    return _CHOICES.get("items") or [("NONE", "No saved panorama", "")]


class SCENARIO_OT_use_saved_panorama(bpy.types.Operator):
    bl_idname = "scenario.use_saved_panorama"
    bl_label = "Use saved panorama"
    bl_description = (
        "Choose a saved, downloaded 360 panorama result of this connection for this input"
    )
    bl_options = {"UNDO"}
    param_name: StringProperty(options={"HIDDEN"})
    choice: EnumProperty(name="Saved panorama", items=_choice_items)

    def invoke(self, context, event):
        try:
            found = candidates()
        except ScenarioError as error:
            self.report({"ERROR"}, error.reason)
            return {"CANCELLED"}
        if not found:
            self.report(
                {"INFO"}, "No saved, downloaded 360 panorama in this connection; generate one first"
            )
            return {"CANCELLED"}
        items = []
        for index, (record, item) in enumerate(found):
            model = runtime.state.records.get(record.intent.target_id)
            name = model.name if model is not None else record.intent.target_id
            items.append(
                (
                    f"{record.intent.request_id}:{item.asset.asset_id}",
                    f"{item.asset.name} ({name})",
                    f"Saved 360 panorama result {item.asset.asset_id}",
                    "WORLD",
                    index,
                )
            )
        _CHOICES["items"] = items
        self.choice = items[0][0]
        return context.window_manager.invoke_props_dialog(self, width=480)

    def draw(self, context):
        layout = self.layout
        layout.label(text="Saved, downloaded 360 panoramas of this connection", icon="WORLD")
        layout.props_enum(self, "choice")
        layout.label(text="The next generation requires a fresh price and approval.")

    def execute(self, context):
        request_id, _, asset_id = self.choice.partition(":")
        try:
            attach_saved(context.scene, self.param_name, request_id, asset_id)
        except ScenarioError as error:
            self.report({"ERROR"}, error.reason)
            return {"CANCELLED"}
        except Exception:
            self.report({"ERROR"}, "Could not use the saved panorama; inspect saved jobs")
            return {"CANCELLED"}
        runtime.set_message("Saved panorama attached; request a fresh price before generating")
        return {"FINISHED"}


class SCENARIO_OT_panorama_to_hdri(bpy.types.Operator):
    bl_idname = "scenario.panorama_to_hdri"
    bl_label = "Make HDRI"
    bl_description = (
        "Open the Environment HDRI form with this saved 360 panorama; pricing and "
        "generation stay separate"
    )
    bl_options = {"UNDO"}
    context_id: StringProperty(options={"HIDDEN"})
    request_id: StringProperty(options={"HIDDEN"})
    expected_revision: IntProperty(min=0, options={"HIDDEN"})
    asset_id: StringProperty(options={"HIDDEN"})

    def execute(self, context):
        try:
            prefill_hdri(context, self.context_id, self.request_id, self.asset_id)
        except ScenarioError as error:
            self.report({"ERROR"}, error.reason)
            return {"CANCELLED"}
        except Exception:
            self.report({"ERROR"}, "Could not prepare the HDRI form; inspect saved jobs")
            return {"CANCELLED"}
        runtime.set_message("HDRI form ready; review its price before generating")
        return {"FINISHED"}


CLASSES = (SCENARIO_OT_use_saved_panorama, SCENARIO_OT_panorama_to_hdri)


def register():
    for cls in CLASSES:
        bpy.utils.register_class(cls)


def unregister():
    _CHOICES.clear()
    for cls in reversed(CLASSES):
        bpy.utils.unregister_class(cls)
