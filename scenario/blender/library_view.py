# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Explicit asset browsing, confirmed references and reviewed organization over shared workers."""

import textwrap
import uuid
from dataclasses import dataclass
from weakref import WeakSet, WeakValueDictionary

import bpy
from bpy.props import BoolProperty, EnumProperty, PointerProperty, StringProperty

from ..core.api.library import asset_summary
from ..core.jobs.organization import (
    OrganizationBusy,
    Outcome,
    Phase,
    ReviewUnavailable,
    review_payload,
)
from ..core.ui import library_organization as organizing
from . import generation, props, reference_form, runtime, workflow_references
from .asset_organization import safe_message

COLLECTION_PAGE = 50
MAX_COLLECTIONS = 200


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
        # Explicitly loaded collection pages; names label rows and the Organize dialog.
        self.collections = []
        self.collections_loaded = False
        self.collections_task = None
        self.collections_pending = None
        self.collections_next = None
        self.collections_tokens = []
        self.collections_error = ""
        # One native review card, owned by the session's shared AssetOrganization.
        self.review_id = None
        self.review = None
        self.review_label = ""
        # The review whose read-back already updated rows; only the shown review syncs.
        self.synced_review_id = None
        self.stale = set()

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
        """Pump-only: consume finished reads and review progress; never sends a write."""
        self._poll_page()
        self._poll_collections()
        self._sync_review()

    def _poll_page(self):
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
            self.stale.clear()
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

    # Collections: explicit reads held as view state, never started by drawing.

    def load_collections(self, direction="LOAD"):
        if not self.current():
            raise ValueError("The connection changed; refresh Library")
        if self.collections_task is not None:
            raise ValueError("Wait for the current collections request")
        if direction == "LOAD":
            token = None
        elif direction == "MORE" and self.more_collections():
            token = self.collections_next
        else:
            raise ValueError("No more collections can be loaded here")
        task = self.session.asset_organization.collections(
            page_size=COLLECTION_PAGE, pagination_token=token
        )
        self.collections_task, self.collections_pending = task, (direction, token)
        self.collections_error = ""

    def more_collections(self):
        return self.collections_next is not None and len(self.collections) < MAX_COLLECTIONS

    def _poll_collections(self):
        task = self.collections_task
        if task is None or not task.done():
            return
        self.collections_task = None
        direction, token = self.collections_pending
        self.collections_pending = None
        try:
            page = self.session.asset_organization.take_collections(task)
            if not self.current():
                return
            loaded = [] if direction == "LOAD" else list(self.collections)
            tokens = [] if direction == "LOAD" else [*self.collections_tokens, token]
            next_token = page["next_pagination_token"]
            if next_token is not None and next_token in tokens:
                raise ValueError("Scenario repeated a collection page; load collections again")
            known = {row["collection_id"] for row in loaded}
            for row in page["collections"]:
                if row["collection_id"] not in known and len(loaded) < MAX_COLLECTIONS:
                    known.add(row["collection_id"])
                    loaded.append(row)
            self.collections, self.collections_tokens = loaded, tokens
            self.collections_next, self.collections_loaded = next_token, True
            self.collections_error = ""
        except ValueError as error:
            self.collections_error = str(error)
        except Exception as error:
            self.collections_error = safe_message(
                error, "Collections could not load. Check the connection and try again."
            )

    def collection_names(self):
        return {row["collection_id"]: row["name"] for row in self.collections if row["name"]}

    def collection_choices(self):
        """Enum items for the Organize dialog: loaded collections, then the browsed one."""
        items = []
        for row in self.collections:
            count = row.get("asset_count")
            label = organizing.clip(row["name"] or row["collection_id"], 40)
            if count is not None:
                label += f" ({count})"
            items.append((row["collection_id"], label, ""))
        browsed = self.filters[2] if self.filters is not None else ""
        if browsed and all(item[0] != browsed for item in items):
            items.append((browsed, organizing.clip("Browsed collection " + browsed, 48), ""))
        return items

    def browse_collection(self, view, scene, collection_id):
        """Set the Collection ID filter to a loaded collection and read its first page."""
        if not self.current():
            raise ValueError("The connection changed; refresh Library")
        if all(row["collection_id"] != collection_id for row in self.collections):
            raise ValueError("Load collections and choose a listed one")
        if self.task is not None:
            raise ValueError("Wait for the current Library request")
        view.query, view.public, view.collection = "", False, collection_id
        self.start(scene, selection(view))

    # Organization: one review card per view, prepared and applied through the
    # session's shared AssetOrganization owner, the same reviews MCP uses.

    def applying(self):
        return self.review is not None and self.review.get("phase") == Phase.APPLYING.value

    def organize_block(self):
        """Why Organize is unavailable for this page, or "" when it is offered."""
        if not self.current():
            return "The connection changed; refresh Library"
        if self.filters is None:
            return "Refresh Library before organizing an asset"
        if self.filters[1]:
            return "Public assets cannot be organized here; browse your own assets"
        if self.task is not None:
            return "Wait for the current Library request"
        if self.applying():
            return "Wait for the current organization change to finish"
        return ""

    def organizable(self, asset_id):
        block = self.organize_block()
        if block:
            raise ValueError(block)
        asset = next((row for row in self.assets if row["asset_id"] == asset_id), None)
        if asset is None:
            raise ValueError("Refresh Library and choose a listed asset")
        return asset

    def organize(self, asset_id, action, *, collection_id="", collection_name="", tags=""):
        """Validate one dialog choice and queue its fresh read; nothing is written yet."""
        asset = self.organizable(asset_id)
        if not runtime.online():
            raise ValueError("Allow Online Access in Blender's preferences first")
        operation, arguments = organizing.request_arguments(
            action,
            asset_id,
            collection_id=collection_id,
            collection_name=collection_name,
            tags=tags,
        )
        owner = self.session.asset_organization
        try:
            review_id = owner.prepare(operation, **arguments)
        except OrganizationBusy as error:
            raise ValueError(organizing.REVIEWS_FULL) from error
        previous = self.review_id
        self.review_id, self.review = review_id, None
        self.review_label = str(asset.get("name") or asset_id)
        if previous is not None:
            self._release(previous)
        self._sync_review()
        return review_id

    def apply_review(self, review_id):
        if not self.current():
            raise ValueError("The connection changed; refresh Library")
        self._sync_review()
        if (
            not review_id
            or review_id != self.review_id
            or self.review is None
            or self.review.get("phase") != Phase.READY.value
        ):
            raise ValueError("Apply only the ready review shown in Library, once")
        self.session.asset_organization.apply(review_id)
        self._sync_review()

    def dismiss_review(self, review_id):
        if not review_id or review_id != self.review_id:
            raise ValueError("This review is no longer shown")
        self._sync_review()
        if self.applying():
            raise ValueError("A change that is being applied cannot be discarded")
        self._release(review_id)
        self.review_id = self.review = None
        self.review_label = ""

    def _release(self, review_id):
        try:
            self.session.asset_organization.discard(review_id)
        except ReviewUnavailable:
            pass

    def _sync_review(self):
        """Refresh the card from the shared review and update rows from read-back records."""
        if self.review_id is None or not self.session.active:
            return
        try:
            status = self.session.asset_organization.review(self.review_id)
        except ReviewUnavailable as error:
            self.review = {"phase": "UNAVAILABLE", "message": str(error)}
            return
        self.review = review_payload(status)
        if (
            status.phase == Phase.FINISHED
            and status.result is not None
            and status.review_id != self.synced_review_id
        ):
            self.synced_review_id = status.review_id
            self._update_rows(status.request, status.result)

    def _update_rows(self, request, result):
        """Show what Scenario read back; rows leave a filtered page only on refresh."""
        browsed = self.filters[2] if self.filters is not None else ""
        for outcome in result.outcomes:
            if outcome.tags is None:
                continue
            row = next((item for item in self.assets if item["asset_id"] == outcome.asset_id), None)
            if row is None:
                continue
            row["tags"] = list(outcome.tags)
            row["collection_ids"] = list(outcome.collection_ids or ())
            if browsed and browsed not in row["collection_ids"]:
                self.stale.add(outcome.asset_id)
            else:
                self.stale.discard(outcome.asset_id)
        created = result.created_collection_id
        if (
            created
            and result.create_outcome == Outcome.VERIFIED
            and self.collections_loaded
            and all(row["collection_id"] != created for row in self.collections)
        ):
            # MAX_COLLECTIONS bounds reads; a collection created here joins even at that bound.
            self.collections.append(
                {
                    "collection_id": created,
                    "name": request.collection_name,
                    "asset_count": None,
                    "model_count": None,
                    "updated_at": None,
                }
            )


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


@dataclass
class ReferenceMenu:
    items: list


_reference_menus = WeakValueDictionary()
_NO_INPUTS = [("NONE", "Review a Library asset first", "")]


def _inputs(self, context):
    # Blender passes OperatorProperties here, not the Python operator instance.
    menu = _reference_menus.get(self.menu_id)
    return menu.items if menu is not None else _NO_INPUTS


class SCENARIO_OT_library_reference(bpy.types.Operator):
    bl_idname = "scenario.library_reference"
    bl_label = "Use as reference"
    bl_description = "Review the scene, model and input before adding this asset as a reference"
    asset_id: StringProperty(options={"HIDDEN", "SKIP_SAVE"})
    menu_id: StringProperty(options={"HIDDEN", "SKIP_SAVE"})
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
            self._menu = ReferenceMenu([(x.param_name, x.input_label, "") for x in self._approvals])
            self.menu_id = uuid.uuid4().hex
            _reference_menus[self.menu_id] = self._menu
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


_SAFE_FAILURE = "Organization is unavailable; refresh Library and try again"


class SCENARIO_OT_library_collections(bpy.types.Operator):
    bl_idname = "scenario.library_collections"
    bl_label = "Load collections"
    bl_description = "Read collections in the selected connection; this changes nothing"
    direction: EnumProperty(items=[("LOAD", "Load", ""), ("MORE", "More", "")])

    def execute(self, context):
        try:
            controls(create=True).load_collections(self.direction)
        except ValueError as error:
            self.report({"WARNING"}, str(error))
            return {"CANCELLED"}
        except Exception as error:
            self.report({"WARNING"}, safe_message(error, _SAFE_FAILURE))
            return {"CANCELLED"}
        return {"FINISHED"}


class SCENARIO_OT_library_collection_filter(bpy.types.Operator):
    bl_idname = "scenario.library_collection_filter"
    bl_label = "Browse collection"
    bl_description = "Browse this collection's assets; clears Search and Public assets"
    collection_id: StringProperty(options={"HIDDEN", "SKIP_SAVE"})

    def execute(self, context):
        try:
            owner = controls()
            if owner is None:
                raise ValueError("Load collections first")
            owner.browse_collection(
                context.window_manager.scenario_library_view, context.scene, self.collection_id
            )
        except ValueError as error:
            self.report({"WARNING"}, str(error))
            return {"CANCELLED"}
        except Exception:
            self.report({"WARNING"}, "Enable online access and check the selected connection")
            return {"CANCELLED"}
        return {"FINISHED"}


@dataclass
class OrganizeMenu:
    items: list


_organize_menus = WeakValueDictionary()
_NO_COLLECTIONS = [(organizing.NO_COLLECTION, "Load collections in Library first", "")]


def _collections(self, context):
    # Blender passes OperatorProperties here, not the Python operator instance.
    menu = _organize_menus.get(self.menu_id)
    return menu.items if menu is not None and menu.items else _NO_COLLECTIONS


class SCENARIO_OT_library_organize(bpy.types.Operator):
    bl_idname = "scenario.library_organize"
    bl_label = "Organize asset"
    bl_description = (
        "Prepare a collection or tag change for this asset; review it before anything is sent"
    )
    asset_id: StringProperty(options={"HIDDEN", "SKIP_SAVE"})
    menu_id: StringProperty(options={"HIDDEN", "SKIP_SAVE"})
    action: EnumProperty(name="Action", items=organizing.ACTIONS, options={"SKIP_SAVE"})
    collection_id: EnumProperty(name="Collection", items=_collections, options={"SKIP_SAVE"})
    collection_name: StringProperty(name="New collection name", options={"SKIP_SAVE"})
    tags: StringProperty(
        name="Tags", description="Comma-separated tags, kept exactly", options={"SKIP_SAVE"}
    )

    def invoke(self, context, event):
        try:
            owner = controls()
            if owner is None:
                raise ValueError("Refresh Library before organizing an asset")
            asset = owner.organizable(self.asset_id)
            self._owner = owner
            self._asset_label = str(asset.get("name") or asset["asset_id"])
            self._connection = organizing.connection_label(owner.session.scope.project_id)
            self._menu = OrganizeMenu(owner.collection_choices())
            self.menu_id = uuid.uuid4().hex
            _organize_menus[self.menu_id] = self._menu
            if self._menu.items:
                browsed = owner.filters[2]
                ids = [item[0] for item in self._menu.items]
                self.collection_id = browsed if browsed in ids else ids[0]
        except ValueError as error:
            self.report({"WARNING"}, str(error))
            return {"CANCELLED"}
        except Exception as error:
            self.report({"WARNING"}, safe_message(error, _SAFE_FAILURE))
            return {"CANCELLED"}
        return context.window_manager.invoke_props_dialog(self, width=480)

    def draw(self, context):
        layout = self.layout
        layout.label(text="Asset: " + organizing.clip(self._asset_label, 40))
        layout.label(text=self._connection)
        layout.prop(self, "action")
        if self.action in {"ADD", "REMOVE"}:
            layout.prop(self, "collection_id")
        elif self.action == "CREATE":
            layout.prop(self, "collection_name")
        else:
            layout.prop(self, "tags")
        problem = organizing.dialog_problem(
            self.action,
            has_collections=bool(self._menu.items),
            collection_id=self.collection_id,
            collection_name=self.collection_name,
            tags=self.tags,
        )
        for index, line in enumerate(textwrap.wrap(problem, organizing.WIDTH)):
            layout.label(text=line, icon="ERROR" if index == 0 else "BLANK1")
        for index, line in enumerate(textwrap.wrap(organizing.NOTICE, organizing.WIDTH)):
            layout.label(text=line, icon="INFO" if index == 0 else "BLANK1")
        layout.label(text="OK reads the current state for review; nothing is sent yet")

    def execute(self, context):
        try:
            owner = getattr(self, "_owner", None)
            if owner is None or owner is not controls():
                raise ValueError("Open Organize from a listed Library asset")
            owner.organize(
                self.asset_id,
                self.action,
                collection_id=self.collection_id,
                collection_name=self.collection_name,
                tags=self.tags,
            )
        except ValueError as error:
            self.report({"WARNING"}, str(error))
            return {"CANCELLED"}
        except Exception as error:
            self.report({"WARNING"}, safe_message(error, _SAFE_FAILURE))
            return {"CANCELLED"}
        self.report({"INFO"}, "Review the change in Studio > Library before applying it")
        return {"FINISHED"}


class SCENARIO_OT_library_organization_apply(bpy.types.Operator):
    bl_idname = "scenario.library_organization_apply"
    bl_label = "Apply organization change"
    bl_description = (
        "Send the reviewed change once; it uses no credits and Blender Undo does not reverse it"
    )
    review_id: StringProperty(options={"HIDDEN", "SKIP_SAVE"})

    def execute(self, context):
        try:
            owner = controls()
            if owner is None:
                raise ValueError("The connection changed; prepare the change again")
            owner.apply_review(self.review_id)
        except ValueError as error:
            self.report({"WARNING"}, str(error))
            return {"CANCELLED"}
        except Exception as error:
            self.report({"WARNING"}, safe_message(error, _SAFE_FAILURE))
            return {"CANCELLED"}
        return {"FINISHED"}


class SCENARIO_OT_library_organization_discard(bpy.types.Operator):
    bl_idname = "scenario.library_organization_discard"
    bl_label = "Discard organization review"
    bl_description = "Close this review card; nothing is sent"
    review_id: StringProperty(options={"HIDDEN", "SKIP_SAVE"})

    def execute(self, context):
        try:
            owner = controls()
            if owner is None:
                raise ValueError("The connection changed; refresh Library")
            owner.dismiss_review(self.review_id)
        except ValueError as error:
            self.report({"WARNING"}, str(error))
            return {"CANCELLED"}
        except Exception as error:
            self.report({"WARNING"}, safe_message(error, _SAFE_FAILURE))
            return {"CANCELLED"}
        return {"FINISHED"}


def _draw_review(layout, owner):
    review = owner.review
    if review is None:
        return
    box = layout.box()
    box.label(text="Organization review", icon="OUTLINER_COLLECTION")
    if owner.review_label:
        box.label(text="Asset: " + organizing.clip(owner.review_label, 40))
    for text, icon in organizing.review_lines(review, names=owner.collection_names()):
        box.label(text=text, icon=icon)
    actions = organizing.card_actions(review.get("phase"))
    if not actions:
        return
    row = box.row(align=True)
    if "APPLY" in actions:
        apply = row.operator("scenario.library_organization_apply", text="Apply", icon="CHECKMARK")
        apply.review_id = owner.review_id
    label = "Discard" if "DISCARD" in actions else "Dismiss"
    row.operator("scenario.library_organization_discard", text=label).review_id = owner.review_id


def _draw_collections(layout, owner, view):
    box = layout.box()
    box.label(text="Collections", icon="OUTLINER_COLLECTION")
    row = box.row(align=True)
    busy = owner is not None and owner.collections_task is not None
    load = row.row(align=True)
    load.enabled = not busy
    load.operator("scenario.library_collections", text="Load collections").direction = "LOAD"
    more = row.row(align=True)
    more.enabled = owner is not None and not busy and owner.more_collections()
    more.operator("scenario.library_collections", text="More").direction = "MORE"
    if owner is None:
        return
    if busy:
        box.label(text="Loading collections…")
    for line in textwrap.wrap(owner.collections_error, organizing.WIDTH):
        box.label(text=line, icon="ERROR")
    if owner.collections_loaded and not owner.collections:
        box.label(text="No collections in this connection")
    browsed = view.collection.strip()
    for item in owner.collections:
        count = item.get("asset_count")
        text = organizing.clip(item["name"] or item["collection_id"], 32)
        if count is not None:
            text += f" ({count})"
        line = box.row()
        line.label(text=text, icon="CHECKMARK" if item["collection_id"] == browsed else "NONE")
        browse = line.row()
        browse.enabled = owner.task is None
        browse.operator("scenario.library_collection_filter", text="Browse").collection_id = item[
            "collection_id"
        ]
    if owner.collections_next is not None and not owner.more_collections():
        box.label(text=f"Showing the first {MAX_COLLECTIONS} collections")


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
        _draw_collections(layout, None, view)
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
    if owner.filters is not None and owner.filters[1]:
        box.label(text="Organize is unavailable for Public assets")
    _draw_review(layout, owner)
    _draw_collections(layout, owner, view)
    names = owner.collection_names()
    organize = not owner.organize_block()
    for asset in owner.assets:
        item = layout.box()
        item.label(text=str(asset.get("name") or asset["asset_id"]))
        item.label(text=str(asset.get("mime_type") or "Unknown file type"))
        item.label(text=organizing.tags_summary(asset.get("tags") or ()))
        item.label(text=organizing.membership_summary(asset.get("collection_ids") or (), names))
        if asset["asset_id"] in owner.stale:
            item.label(text="No longer in this collection; refresh", icon="FILE_REFRESH")
        row = item.row(align=True)
        reference = row.row(align=True)
        reference.enabled = asset_kind(asset) is not None
        reference.operator("scenario.library_reference", text="Use as reference").asset_id = asset[
            "asset_id"
        ]
        change = row.row(align=True)
        change.enabled = organize
        change.operator("scenario.library_organize", text="Organize").asset_id = asset["asset_id"]


CLASSES = (
    ScenarioLibraryView,
    SCENARIO_OT_library_page,
    SCENARIO_OT_library_reference,
    SCENARIO_OT_library_collections,
    SCENARIO_OT_library_collection_filter,
    SCENARIO_OT_library_organize,
    SCENARIO_OT_library_organization_apply,
    SCENARIO_OT_library_organization_discard,
)


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
