# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Prompt to Blockout: the Scenario LLM designs a structured greybox (rich primitives, categories, groups) that the
builder places in the viewport, colour-coded and organised into sub-collections, to refine or replace with generated
assets. The design runs off the main thread (LLM); the build runs on the main thread from the stored plan."""

import json
import textwrap
from math import radians

import bmesh
import bpy
from bpy.props import StringProperty

from ..core.api.errors import ScenarioError
from ..core.scene import blockout as core
from ..core.scene import blockout_view as core_view
from . import blockout_view as view
from . import runtime

COLLECTION = "Blockout"
MARK = "scenario_blockout"
_MESHES = {}


# -- primitive meshes (shared unit shapes in a 1 m cube; per-object scale gives the metre size) -----------------------
def _hand_mesh(name, verts, faces):
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(verts, [], faces)
    mesh.update()
    return mesh


def _bmesh_mesh(name, build):
    mesh = bpy.data.meshes.new(name)
    bm = bmesh.new()
    build(bm)
    bm.to_mesh(mesh)
    bm.free()
    mesh.update()
    return mesh


def _build_box():
    verts = [
        (-0.5, -0.5, -0.5),
        (0.5, -0.5, -0.5),
        (0.5, 0.5, -0.5),
        (-0.5, 0.5, -0.5),
        (-0.5, -0.5, 0.5),
        (0.5, -0.5, 0.5),
        (0.5, 0.5, 0.5),
        (-0.5, 0.5, 0.5),
    ]
    faces = [(0, 1, 2, 3), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)]
    return _hand_mesh("Scenario Blockout box", verts, faces)


def _build_wedge():
    # a ramp / lean-to roof rising from -x (low) to +x (high)
    verts = [
        (-0.5, -0.5, -0.5),
        (0.5, -0.5, -0.5),
        (0.5, 0.5, -0.5),
        (-0.5, 0.5, -0.5),
        (0.5, -0.5, 0.5),
        (0.5, 0.5, 0.5),
    ]
    faces = [(0, 1, 2, 3), (1, 4, 5, 2), (0, 4, 1), (3, 2, 5), (0, 3, 5, 4)]
    return _hand_mesh("Scenario Blockout wedge", verts, faces)


def _mesh_for(primitive):
    mesh = _MESHES.get(primitive)
    try:
        if mesh is not None and mesh.name in bpy.data.meshes:
            return mesh
    except ReferenceError:
        pass  # the cached mesh was removed (e.g. a fresh file); rebuild it
    if primitive == "wedge":
        mesh = _build_wedge()
    elif primitive == "cylinder":
        mesh = _bmesh_mesh(
            "Scenario Blockout cylinder",
            lambda bm: bmesh.ops.create_cone(
                bm, cap_ends=True, cap_tris=False, segments=24, radius1=0.5, radius2=0.5, depth=1.0
            ),
        )
    elif primitive == "cone":
        mesh = _bmesh_mesh(
            "Scenario Blockout cone",
            lambda bm: bmesh.ops.create_cone(
                bm, cap_ends=True, cap_tris=False, segments=24, radius1=0.5, radius2=0.0, depth=1.0
            ),
        )
    elif primitive == "sphere":
        mesh = _bmesh_mesh(
            "Scenario Blockout sphere",
            lambda bm: bmesh.ops.create_uvsphere(bm, u_segments=20, v_segments=12, radius=0.5),
        )
    else:  # box and plane share the cube (a plane is just a thin box)
        mesh = _build_box()
    _MESHES[primitive] = mesh
    return mesh


# -- collections ------------------------------------------------------------------------------------------------------
def _sub_collection(name, parent):
    coll = bpy.data.collections.new(name)
    coll[MARK] = True
    parent.children.link(coll)
    return coll


def _owned_tree(scene):
    root = scene.scenario_blockout.built_collection
    if root is None:
        return None
    collections = {root, *root.children_recursive}
    parents = tuple(bpy.data.collections) + tuple(item.collection for item in bpy.data.scenes)
    if root not in tuple(scene.collection.children):
        raise ValueError("The Blockout collection moved; inspect it before rebuilding")
    for coll in collections:
        if coll.get(MARK) is not True:
            raise ValueError(
                "The Blockout contains another collection; preserve it before rebuilding"
            )
        allowed = {scene.collection} if coll == root else collections
        if any(coll in tuple(parent.children) and parent not in allowed for parent in parents):
            raise ValueError("The Blockout collection is shared; make it local before rebuilding")
        for obj in coll.objects:
            if MARK not in obj or any(owner not in collections for owner in obj.users_collection):
                raise ValueError(
                    "The Blockout contains unrelated or shared objects; preserve them first"
                )
    return root


def _remove_tree(root):
    collections = (root, *tuple(root.children_recursive))
    objects = {obj for coll in collections for obj in coll.objects}
    for obj in objects:
        bpy.data.objects.remove(obj, do_unlink=True)
    for coll in reversed(collections):
        bpy.data.collections.remove(coll)
    return len(objects)


def clear_blockout(scene):
    """Clear only this scene's explicitly owned, unshared generated collection."""
    root = _owned_tree(scene)
    removed = _remove_tree(root) if root is not None else 0
    view.purge_unused_materials()
    return removed


def _colour_the_viewport():
    """Show the per-object greybox colours: switch every 3D viewport's solid shading to colour by object."""
    for window in bpy.context.window_manager.windows:
        for area in window.screen.areas:
            if area.type == "VIEW_3D":
                area.spaces.active.shading.color_type = "OBJECT"


class Built(list):
    """The objects a build created; `added` names the camera and light it added to the scene."""

    added = ()


def _dress(scene, elements, staging):
    """Stage the group colours and materials, then the camera and sun the scene lacks.

    Returns ({group: (RGBA, material)}, names of what was added). Nothing here touches data the user owns.
    """
    colours = core_view.group_colours(elements, view.kept_colours(core_view.group_order(elements)))
    materials = view.group_materials(colours, staging)
    bounds = core_view.plan_bounds(elements)
    added = []
    if bounds is not None and view.lacks_camera(scene):
        view.add_camera(scene, *bounds, staging)
        added.append("camera")
    if bounds is not None and view.lacks_light(scene):
        view.add_sun(scene, *bounds, staging)
        added.append("sun light")
    return {group: (colours[group], materials[group]) for group in colours}, added


def build_blockout(context, elements, *, dress=True):
    """Stage a complete local build before replacing only this scene's owned tree.

    With `dress`, each top-level group gets its own muted colour and shared material, and a camera framing
    the blockout and a sun are added when the scene has none. A failed build removes everything it created.
    """
    scene = context.scene
    old = _owned_tree(scene)
    root = _sub_collection(COLLECTION, scene.collection)
    staging = view.Staging()
    groups, created, looks, added = {}, Built(), {}, []
    try:
        if dress:
            looks, added = _dress(scene, elements, staging)
        for el in elements:
            group = el.get("group") or COLLECTION
            category = el.get("category") or core.DEFAULT_CATEGORY
            if group == COLLECTION:
                gcoll = root
            else:
                gcoll = groups.get(group)
                if gcoll is None:
                    gcoll = _sub_collection(group, root)
                    groups[group] = gcoll
            obj = bpy.data.objects.new(
                el.get("name") or "Block", _mesh_for(el.get("primitive") or "box")
            )
            created.append(obj)
            gcoll.objects.link(obj)
            obj.location = el.get("position") or (0.0, 0.0, 0.0)
            obj.scale = el.get("size") or (1.0, 1.0, 1.0)
            obj.rotation_euler = (0.0, 0.0, radians(el.get("rotation", 0.0) or 0.0))
            if dress:
                colour, material = looks[core_view.group_name(el)]
                view.assign_material(obj, material)
            else:
                r, g, b = core.CATEGORIES.get(category, core.CATEGORIES[core.DEFAULT_CATEGORY])[1]
                colour = (r, g, b, 1.0)
            obj.color = colour
            obj[MARK] = category
            obj.display_type = "SOLID"
    except BaseException:
        try:
            _remove_tree(root)
        finally:
            staging.discard()
        raise
    # All decoding and creation succeeded before touching the old collection.
    # After publication starts, never destroy the staged replacement on failure.
    scene.scenario_blockout.built_collection = root
    if old is not None:
        _remove_tree(old)
    view.purge_unused_materials()
    root.name = COLLECTION
    for name, coll in groups.items():
        coll.name = name
    for obj, element in zip(created, elements, strict=True):
        obj.name = element.get("name") or "Block"
    created.added = tuple(added)
    if created and not bpy.app.background:
        _colour_the_viewport()
    return created


# -- state ------------------------------------------------------------------------------------------------------------
def _store(scene, elements):
    scene.scenario_blockout.plan_json = json.dumps(elements)


def stored_plan(scene):
    try:
        data = json.loads(scene.scenario_blockout.plan_json or "[]")
    except ValueError:
        return []
    return data if isinstance(data, list) else []


def on_blockout_plan(payload):
    """Ignore retired unbound events; the selected JobSession delivers plans."""


def _design(context, prompt, previous=None):
    runtime.ensure_blockout_jobs().quote(
        context.scene, "REFINE" if previous is not None else "DESIGN"
    )


class SCENARIO_OT_blockout_approve(bpy.types.Operator):
    bl_idname = "scenario.blockout_approve"
    bl_label = "Generate Blockout plan"
    bl_description = (
        "Approve the displayed exact price once and prepare a plan without changing geometry"
    )
    quote_id: StringProperty(options={"SKIP_SAVE"})
    approved_cost: StringProperty(options={"SKIP_SAVE"})

    @classmethod
    def poll(cls, context):
        from .operators import _network_poll

        return _network_poll(cls, context)

    def invoke(self, context, event):
        """Above the "Confirm generations above" preference, name the model and exact price first."""
        from ..core.ui.costs import confirms_spend, spend_confirmation
        from .generation import confirm_threshold

        jobs = runtime.state.blockout_jobs
        item = jobs.actions.get(self.quote_id) if jobs is not None else None
        # A stale or changed quote is refused by execute, without a dialog.
        if (
            item is None
            or item.phase != "READY"
            or item.cost != self.approved_cost
            or not confirms_spend(item.cost, confirm_threshold())
        ):
            return self.execute(context)
        title, message = spend_confirmation(core.model_label(item.model), item.cost)
        return context.window_manager.invoke_confirm(
            self, event, title=title, message=message, confirm_text="Generate"
        )

    def execute(self, context):
        try:
            runtime.ensure_blockout_jobs().approve(
                self.quote_id, context.scene, approved_cost=self.approved_cost
            )
        except Exception:
            self.report(
                {"WARNING"},
                "Blockout approval is stale or could not be submitted; inspect saved jobs",
            )
            return {"CANCELLED"}
        return {"FINISHED"}


def _wrapped(layout, text, icon, width=36):
    for index, line in enumerate(textwrap.wrap(text, width)):
        layout.label(text=line, icon=icon if index == 0 else "NONE")


def draw_status(layout, scene):
    """The current action: its exact-price approval, progress or outcome. Never mutates."""
    from ..core.ui.costs import format_cu
    from .blockout_jobs import CANCELED, MINUTES, binding

    jobs = runtime.state.blockout_jobs
    item = jobs.current(scene) if jobs is not None else None
    if item is None:
        return
    model = core.model_label(item.model)
    if item.phase == "READY":
        if binding(scene) != item.binding:
            return  # A changed input makes this price stale; the panel offers a new one.
        row = layout.row()
        row.scale_y = 1.4
        verb = "Generate blockout" if item.action == "DESIGN" else "Refine blockout"
        op = row.operator(
            "scenario.blockout_approve",
            text=f"{verb} ({format_cu(item.cost)} CU)",
            icon="PLAY",
        )
        op.quote_id, op.approved_cost = item.identifier, item.cost
        layout.label(text=f"{model}, {MINUTES.get(item.tier, 'a few minutes')}", icon="INFO")
    elif item.phase == "QUOTING":
        layout.label(text="Getting the price...", icon="TIME")
    elif item.phase in {"SUBMITTING", "POLLING", "LISTING", "READING"}:
        _wrapped(
            layout,
            f"{model} is designing the plan, {MINUTES.get(item.tier, 'a few minutes')}...",
            "TIME",
        )
    elif item.phase == "DONE":
        layout.label(text="Plan ready: build it below", icon="CHECKMARK")
    elif item.phase == "ERROR":
        if item.error == CANCELED:
            # A local cancellation sent nothing: there is no saved job to review.
            _wrapped(layout, CANCELED, "INFO", 32)
            return
        layout.label(text="Blockout needs review", icon="ERROR")
        if item.error:
            _wrapped(layout, item.error, "NONE")
        if item.request_id:
            layout.operator(
                "scenario.inspect_saved_jobs", text="Inspect saved jobs", icon="VIEWZOOM"
            )
        else:
            layout.label(text="Check inputs and request a new price")


def needs_price(scene, action="DESIGN"):
    """Whether the panel should offer a price request for `action`: no current, unchanged quote."""
    from .blockout_jobs import BUSY, binding

    jobs = runtime.state.blockout_jobs
    item = jobs.current(scene) if jobs is not None else None
    if item is None:
        return True
    if item.phase in BUSY:
        return False
    return not (item.phase == "READY" and item.action == action and binding(scene) == item.binding)


def draw_price(layout, scene):
    """What stands in for Generate blockout while the design has no current price. Never mutates.

    The pump prices settled inputs by itself, so the normal path shows a short wait and then
    the priced button. A request by hand stays for a new plan from unchanged inputs and for
    a failed automatic price, whose reason is shown.
    """
    from . import model_jobs
    from .blockout_jobs import _design_inputs, binding

    if not needs_price(scene):
        return
    props = scene.scenario_blockout
    if props.image_path and not props.image_asset_id:
        return  # The Upload button above comes first.
    if not (props.prompt.strip() or props.image_asset_id):
        layout.label(text="Describe a scene to see its price", icon="INFO")
        return
    jobs = runtime.state.blockout_jobs
    item = jobs.current(scene) if jobs is not None else None
    if item is not None and _design_inputs(item.binding) == _design_inputs(binding(scene)):
        # A finished plan, an error or a refinement for these inputs stays on screen.
        text = "Try again" if item.phase == "ERROR" and not item.request_id else "New plan"
        layout.operator("scenario.blockout_design", text=text, icon="FILE_REFRESH")
        return
    reason = jobs.auto_price_error(scene) if jobs is not None else ""
    if reason:
        _wrapped(layout, reason, "ERROR")
        layout.operator("scenario.blockout_design", text="Try again", icon="FILE_REFRESH")
    elif (
        model_jobs.automatic_estimates_stopped()
        or not runtime.online()
        or not runtime.credentials().valid
    ):
        layout.operator("scenario.blockout_design", text="Get price", icon="FILE_REFRESH")
    else:
        layout.label(text="Getting the price...", icon="TIME")


def running_plans(shown=()):
    """Blockout plans Scenario is designing, as Jobs rows; `shown` lists saved jobs drawn already."""
    from .blockout_jobs import MINUTES

    jobs = runtime.state.blockout_jobs
    if jobs is None:
        return []
    return [
        f"{core.model_label(item.model)}, {MINUTES.get(item.tier, 'a few minutes')}"
        for item in tuple(jobs.actions.values())
        if item.phase in {"SUBMITTING", "POLLING", "LISTING", "READING"}
        and item.request_id not in shown
    ]


def auto_quote(scene, now):
    """Pump hook: price the visible Blockout design once its inputs settle."""
    return runtime.ensure_blockout_jobs().auto_quote(scene, now)


class SCENARIO_OT_blockout_design(bpy.types.Operator):
    bl_idname = "scenario.blockout_design"
    bl_label = "Get Blockout price"
    bl_description = "Request the exact price for a Blockout plan before approving generation"

    @classmethod
    def poll(cls, context):
        from .operators import _network_poll

        return _network_poll(cls, context)

    def execute(self, context):
        props = context.scene.scenario_blockout
        prompt = props.prompt.strip()
        if not prompt and not props.image_path:
            self.report({"WARNING"}, "Describe the scene or choose a reference image first")
            return {"CANCELLED"}
        try:
            _design(context, prompt)
        except ScenarioError as error:
            self.report({"WARNING"}, error.reason)
            return {"CANCELLED"}
        except Exception:
            self.report(
                {"WARNING"}, "Could not request a Blockout price; check inputs and connection"
            )
            return {"CANCELLED"}
        return {"FINISHED"}


class SCENARIO_OT_blockout_upload_image(bpy.types.Operator):
    bl_idname = "scenario.blockout_upload_image"
    bl_label = "Upload reference image"
    bl_description = "Upload the chosen picture to Scenario so the plan can follow it"

    @classmethod
    def poll(cls, context):
        from .operators import _network_poll

        return _network_poll(cls, context)

    def execute(self, context):
        try:
            runtime.ensure_blockout_jobs().upload_image(context.scene)
        except ScenarioError as error:
            self.report({"WARNING"}, error.reason)
            return {"CANCELLED"}
        except Exception:
            self.report({"WARNING"}, "Upload could not start; check the image and try again")
            return {"CANCELLED"}
        return {"FINISHED"}


class SCENARIO_OT_blockout_refine(bpy.types.Operator):
    bl_idname = "scenario.blockout_refine"
    bl_label = "Refine blockout"
    bl_description = (
        "Request the exact price for a refined Blockout plan before approving generation"
    )

    @classmethod
    def poll(cls, context):
        from .operators import _network_poll

        return _network_poll(cls, context)

    def execute(self, context):
        props = context.scene.scenario_blockout
        change = props.refine.strip()
        previous = stored_plan(context.scene)
        if not change:
            self.report({"WARNING"}, "Describe the change to make")
            return {"CANCELLED"}
        if not previous:
            self.report({"WARNING"}, "Design a blockout first, then refine it")
            return {"CANCELLED"}
        try:
            _design(context, change, previous=previous)
        except ScenarioError as error:
            self.report({"WARNING"}, error.reason)
            return {"CANCELLED"}
        except Exception:
            self.report(
                {"WARNING"}, "Could not request a Blockout price; check inputs and connection"
            )
            return {"CANCELLED"}
        return {"FINISHED"}


class SCENARIO_OT_blockout_build(bpy.types.Operator):
    bl_idname = "scenario.blockout_build"
    bl_label = "Build blockout"
    bl_description = "Build the greybox from the current plan, locally, without calling the LLM"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        elements = core.parse_plan(json.dumps(stored_plan(context.scene)))
        if not elements:
            self.report({"WARNING"}, "No blockout plan yet; design one first")
            return {"CANCELLED"}
        try:
            created = build_blockout(
                context, elements, dress=context.scene.scenario_blockout.dress_scene
            )
        except (ValueError, RuntimeError):
            self.report(
                {"WARNING"}, "Could not build safely; inspect the existing Blockout collection"
            )
            return {"CANCELLED"}
        added = f", added a {' and a '.join(created.added)}" if created.added else ""
        self.report({"INFO"}, f"Built {len(created)} elements{added}")
        return {"FINISHED"}


class SCENARIO_OT_blockout_clear(bpy.types.Operator):
    bl_idname = "scenario.blockout_clear"
    bl_label = "Clear blockout"
    bl_description = "Delete the Blockout collection and forget the plan"
    bl_options = {"REGISTER", "UNDO"}

    def invoke(self, context, event):
        return context.window_manager.invoke_confirm(self, event)

    def execute(self, context):
        try:
            removed = clear_blockout(context.scene)
        except (ValueError, RuntimeError):
            self.report(
                {"WARNING"}, "The Blockout contains shared or unrelated data; preserve it first"
            )
            return {"CANCELLED"}
        context.scene.scenario_blockout.plan_json = ""
        self.report({"INFO"}, f"Cleared {removed} object(s)")
        return {"FINISHED"}


CLASSES = (
    SCENARIO_OT_blockout_design,
    SCENARIO_OT_blockout_upload_image,
    SCENARIO_OT_blockout_approve,
    SCENARIO_OT_blockout_refine,
    SCENARIO_OT_blockout_build,
    SCENARIO_OT_blockout_clear,
)


def register():
    for cls in CLASSES:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(CLASSES):
        bpy.utils.unregister_class(cls)
