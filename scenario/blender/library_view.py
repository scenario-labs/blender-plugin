# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Explicit asset browsing and confirmed model references over shared workers."""

import textwrap
from dataclasses import dataclass
from weakref import WeakSet

import bpy
from bpy.props import BoolProperty, EnumProperty, PointerProperty, StringProperty

from ..core.api.library import asset_summary
from . import generation, props, reference_form, runtime, workflow_references


def asset_kind(asset):
    mime = str(asset.get("mime_type", "")).lower().split(";", 1)[0].strip()
    if mime in {"model/gltf-binary", "model/gltf+json", "model/obj", "model/fbx"}:
        return "3d"
    prefix = mime.split("/", 1)[0]
    return prefix if prefix in {"image", "audio", "video"} else None


class ScenarioLibraryView(bpy.types.PropertyGroup):
    target: EnumProperty(
        name="Reference destination",
        items=(
            ("MODEL", "Model", "Add to the selected Create form"),
            ("WORKFLOW", "Workflow", "Add to the loaded workflow form"),
        ),
        default="MODEL",
        options={"SKIP_SAVE"},
    )
    query: StringProperty(name="Search", options={"SKIP_SAVE"})
    public: BoolProperty(name="Public assets", options={"SKIP_SAVE"})
    collection: StringProperty(name="Collection ID", options={"SKIP_SAVE"})


def selection(view):
    return view.query.strip(), view.public, view.collection.strip()


@dataclass(frozen=True, eq=False)
class ReferenceApproval:
    asset_id: str
    label: str
    kind: str
    scene: object
    scene_name: str
    origin: object
    lane_name: str
    model_id: str
    model_label: str
    param_name: str
    input_label: str
    destination: str


class LibraryView:
    def __init__(self, session):
        self.session = session
        self.task = None
        self.pending = None
        self.filters = None
        self.assets = []
        self.cursors = [None]
        self.index = 0
        self.next_cursor = None
        self.error = ""
        self.approvals = WeakSet()

    def current(self):
        return (
            runtime.state.library_view is self
            and runtime.state.job_session is self.session
            and self.session.active
            and runtime.catalog_selection_matches()
        )

    def start(self, scene, filters, direction="REFRESH"):
        if not self.current():
            raise ValueError("The connection changed; refresh Library")
        if self.task is not None:
            raise ValueError("Wait for the current Library request")
        query, public, collection = filters
        if query and collection:
            raise ValueError("Clear Collection ID before searching, or clear Search to browse it")
        if direction == "REFRESH":
            index, cursor = 0, None
        else:
            if filters != self.filters:
                raise ValueError("Filters changed; refresh Library first")
            if direction == "NEXT" and self.next_cursor is not None:
                index, cursor = self.index + 1, self.next_cursor
            elif direction == "PREVIOUS" and self.index:
                index, cursor = self.index - 1, self.cursors[self.index - 1]
            else:
                raise ValueError("This page is unavailable")
        options = {"public": public}
        if query:
            options.update(query=query, limit=40, offset=cursor or 0)
        else:
            options.update(page_size=40, pagination_token=cursor, collection_id=collection or None)
        task = self.session.asset_library(scene, **options)
        self.pending = filters, direction, index, cursor
        self.task, self.error = task, ""

    def poll(self):
        if self.task is None:
            return
        outcomes = self.session.drain(task=self.task)
        if not outcomes:
            return
        self.task = None
        try:
            page = self.session.deliver_asset_library(outcomes[0])
            if not self.current():
                return
            filters, direction, index, cursor = self.pending
            rows = [asset_summary(row) for row in page["assets"]]
            next_cursor = page.get("next_offset" if filters[0] else "next_pagination_token")
            cursors = [None] if direction == "REFRESH" else self.cursors[:index] + [cursor]
            if next_cursor is not None and next_cursor in cursors:
                raise ValueError("Library returned a repeated page; refresh to browse again")
            # Bound navigation memory; refreshing always starts at the first page.
            if len(cursors) > 128:
                cursors, index = cursors[-128:], 127
            self.assets, self.filters = rows, filters
            self.cursors, self.index, self.next_cursor = cursors, index, next_cursor
            self.error = ""
        except Exception:
            self.error = "Library could not load this page. Check the connection and refresh."
        finally:
            self.pending = None

    def prepare(self, context, asset_id, *, target="MODEL"):
        if not self.current():
            raise ValueError("The connection changed; refresh Library")
        asset = next((row for row in self.assets if row["asset_id"] == asset_id), None)
        if asset is None or not asset_kind(asset):
            raise ValueError("Choose a Library asset with a supported file type")
        if target == "WORKFLOW":
            choices = workflow_references.choices(
                context,
                self.session,
                asset_id,
                str(asset.get("name") or asset_id),
                asset_kind(asset),
            )
            self.approvals.update(choices)
            return choices
        if target != "MODEL":
            raise ValueError("Choose a model or workflow destination")
        lane_name = context.scene.scenario.lane
        if lane_name not in props.GENERATION_LANES:
            raise ValueError("Choose a generation form in Create first")
        lane = context.scene.scenario.lane_state(lane_name)
        schema = generation.schema_for(lane.model_id)
        if schema is None:
            raise ValueError("Load a model in Create before choosing a reference")
        bpy.context.view_layer.update()
        origin = self.session.capture(context.scene)
        choices = []
        for spec in schema.specs:
            if reference_form.input_kind(lane, spec.name) != asset_kind(asset):
                continue
            matching = [ref for ref in lane.references if ref.param_name == spec.name]
            if (spec.ptype == "file" and matching) or (
                spec.max_length is not None and len(matching) >= spec.max_length
            ):
                continue
            if any(ref.source == "ASSET" and ref.asset_id == asset_id for ref in matching):
                continue
            approval = ReferenceApproval(
                asset_id,
                str(asset.get("name") or asset_id),
                asset_kind(asset),
                context.scene,
                context.scene.name,
                origin,
                lane_name,
                lane.model_id,
                runtime.state.records[lane.model_id].name,
                spec.name,
                spec.label,
                reference_form._destination_key(context.scene, lane_name),
            )
            self.approvals.add(approval)
            choices.append(approval)
        if not choices:
            raise ValueError(
                "No matching empty input; choose a model or remove a reference in Create"
            )
        return choices

    def attach(self, approval):
        if not self.current() or approval not in self.approvals:
            raise ValueError("Review this asset and destination again")
        self.approvals.remove(approval)
        self.session.validate_destination(approval.origin)
        if isinstance(approval, workflow_references.WorkflowReferenceApproval):
            return workflow_references.attach(approval, self.session)
        scene = approval.scene
        if (
            scene.scenario.lane != approval.lane_name
            or reference_form._destination_key(scene, approval.lane_name) != approval.destination
        ):
            raise ValueError("The destination changed; review it again")
        lane = scene.scenario.lane_state(approval.lane_name)
        if reference_form.input_kind(lane, approval.param_name) != approval.kind:
            raise ValueError("Load the matching model input and review it again")
        # Recheck capacity even if the model's schema changed without editing RNA.
        spec = generation.schema_for(lane.model_id).by_name(approval.param_name)
        matching = [ref for ref in lane.references if ref.param_name == approval.param_name]
        if (spec.ptype == "file" and matching) or (
            spec.max_length is not None and len(matching) >= spec.max_length
        ):
            raise ValueError("This input is full; remove a reference in Create first")
        ref = lane.references.add()
        try:
            ref.param_name, ref.source, ref.asset_id = (
                approval.param_name,
                "ASSET",
                approval.asset_id,
            )
            ref.label = approval.label
            ref[reference_form._SCOPE] = reference_form.scope_key(self.session.scope)
            ref[reference_form._ASSET] = approval.asset_id
            ref[reference_form._KIND] = approval.kind
            props.mark_estimate_dirty(lane)
        except Exception:
            lane.references.remove(len(lane.references) - 1)
            raise
        return ref


def controls(*, create=False):
    if create:
        session = runtime.ensure_job_session()
        if runtime.state.library_view is None:
            runtime.state.library_view = LibraryView(session)
    owner = runtime.state.library_view
    return owner if owner is not None and owner.current() else None


class SCENARIO_OT_library_page(bpy.types.Operator):
    bl_idname = "scenario.library_page"
    bl_label = "Refresh Library"
    bl_description = "Read one asset page using the selected connection and filters"
    direction: EnumProperty(items=[(x, x.title(), "") for x in ("REFRESH", "NEXT", "PREVIOUS")])

    def execute(self, context):
        try:
            controls(create=True).start(
                context.scene,
                selection(context.window_manager.scenario_library_view),
                self.direction,
            )
        except ValueError as error:
            self.report({"WARNING"}, str(error))
            return {"CANCELLED"}
        except Exception:
            self.report({"WARNING"}, "Enable online access and check the selected connection")
            return {"CANCELLED"}
        return {"FINISHED"}


def _inputs(self, context):
    return getattr(self, "_input_choices", [("NONE", "Review a Library asset first", "")])


class SCENARIO_OT_library_reference(bpy.types.Operator):
    bl_idname = "scenario.library_reference"
    bl_label = "Use as reference"
    bl_description = "Review the scene, model and input before adding this asset as a reference"
    asset_id: StringProperty(options={"HIDDEN", "SKIP_SAVE"})
    input_name: EnumProperty(name="Input", items=_inputs)

    def invoke(self, context, event):
        try:
            self._owner = controls()
            if self._owner is None:
                raise ValueError("Refresh Library before choosing a reference")
            view = getattr(context.window_manager, "scenario_library_view", None)
            self._approvals = self._owner.prepare(
                context, self.asset_id, target=getattr(view, "target", "MODEL")
            )
            self._input_choices = [(x.param_name, x.input_label, "") for x in self._approvals]
            self.input_name = self._approvals[0].param_name
        except ValueError as error:
            self.report({"WARNING"}, str(error))
            return {"CANCELLED"}
        except Exception:
            self.report(
                {"WARNING"}, "The destination is unavailable; refresh Library and review it again"
            )
            return {"CANCELLED"}
        return context.window_manager.invoke_props_dialog(self, width=480)

    def draw(self, context):
        approval = self._approvals[0]
        self.layout.label(text="Asset: " + approval.label)
        self.layout.label(text="Scene: " + approval.scene_name)
        if isinstance(approval, workflow_references.WorkflowReferenceApproval):
            self.layout.label(text="Workflow: " + approval.workflow_label)
        else:
            self.layout.label(text="Model: " + approval.model_label)
            self.layout.label(text="Form: " + approval.lane_name.replace("_", " ").title())
        self.layout.prop(self, "input_name")
        self.layout.label(text="Add this reference, then review a new generation price")

    def execute(self, context):
        try:
            approval = next(x for x in self._approvals if x.param_name == self.input_name)
            self._owner.attach(approval)
        except (AttributeError, StopIteration):
            self.report({"WARNING"}, "Review the asset and destination first")
            return {"CANCELLED"}
        except Exception:
            self.report({"WARNING"}, "The destination changed; review this reference again")
            return {"CANCELLED"}
        self.report({"INFO"}, "Reference added; review a new price in the destination form")
        return {"FINISHED"}


def draw(layout, context):
    view = context.window_manager.scenario_library_view
    box = layout.box()
    box.label(text="Asset Library", icon="ASSET_MANAGER")
    box.prop(view, "target")
    box.prop(view, "public")
    box.prop(view, "query")
    box.prop(view, "collection")
    owner = controls()
    row = box.row()
    row.enabled = owner is None or owner.task is None
    row.operator("scenario.library_page", text="Refresh", icon="FILE_REFRESH").direction = "REFRESH"
    if owner is None:
        box.label(text="Refresh to load assets in the selected connection")
        return
    if owner.task is not None:
        box.label(text="Loading assets…")
    if owner.error:
        # Generic error is bounded; service text and signed URLs are never shown.
        for line in textwrap.wrap(owner.error, width=48):
            box.label(text=line, icon="ERROR")
    changed = owner.filters != selection(view)
    if changed and owner.filters is not None:
        box.label(text="Filters changed; refresh to update these results")
    row = box.row(align=True)
    prev = row.row(align=True)
    prev.enabled = not changed and owner.task is None and owner.index > 0
    prev.operator("scenario.library_page", text="Previous").direction = "PREVIOUS"
    nex = row.row(align=True)
    nex.enabled = not changed and owner.task is None and owner.next_cursor is not None
    nex.operator("scenario.library_page", text="Next").direction = "NEXT"
    if owner.filters is not None and not owner.assets:
        box.label(text="No assets on this page")
    for asset in owner.assets:
        item = layout.box()
        item.label(text=str(asset.get("name") or asset["asset_id"]))
        item.label(text=str(asset.get("mime_type") or "Unknown file type"))
        row = item.row()
        row.enabled = asset_kind(asset) is not None
        row.operator("scenario.library_reference", text="Use as reference").asset_id = asset[
            "asset_id"
        ]


CLASSES = (ScenarioLibraryView, SCENARIO_OT_library_page, SCENARIO_OT_library_reference)


def register():
    for cls in CLASSES:
        bpy.utils.register_class(cls)
    bpy.types.WindowManager.scenario_library_view = PointerProperty(
        type=ScenarioLibraryView, options={"SKIP_SAVE"}
    )


def unregister():
    del bpy.types.WindowManager.scenario_library_view
    for cls in reversed(CLASSES):
        bpy.utils.unregister_class(cls)
