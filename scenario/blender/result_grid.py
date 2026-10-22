# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Finished generations as a grid of preview tiles, and one selected result large.

Studio's Results page opens on the grid; the sidebar's Generations panel
offers it beside its list, which stays its default. A tile shows the
generation's first ranked preview from ``result_previews``, or its kind's
icon while there is none. Choosing a tile shows that preview large with the
prompt, model, kind, saved size, submission time and approved price, then the
same model row, preview tiles and saved-job controls a list row draws.

The layout of each surface, the shared page and the selected result are
unsaved window-manager state. Only this module's operators change the page
and selection, never drawing; a page or selection that no longer exists is
drawn as the nearest page or as the grid. Nothing here downloads, applies,
spends or changes the scene.
"""

import bpy
from bpy.props import EnumProperty, IntProperty, PointerProperty, StringProperty

from ..core.ui import result_grid as grid
from . import label_wrap, panels, result_previews, runtime

SURFACES = ("SIDEBAR", "STUDIO")
LAYOUTS = (
    ("LIST", "List", "Show each generation as a row with its actions", "LONGDISPLAY", 0),
    (
        "GRID",
        "Grid",
        "Show generations as preview tiles; choose one for a large preview and its actions",
        "IMGDISPLAY",
        1,
    ),
)
# Interface units of the region a grid row cannot use: the sidebar panel's
# margins and category tabs, as the preview tile rows reserve beside a job box,
# or Studio's popup edges. The selected result is drawn in a box, 10 narrower.
MARGIN = {"SIDEBAR": 50, "STUDIO": 10}
BOX_MARGIN = 10
# Lines of a long prompt drawn above the selected result's model.
PROMPT_LINES = 6


class ScenarioResultsView(bpy.types.PropertyGroup):
    # Browsing must not tag a scene and invalidate its quote: unsaved window state.
    sidebar_layout: EnumProperty(
        name="Generations layout", items=LAYOUTS, default="LIST", options={"SKIP_SAVE"}
    )
    studio_layout: EnumProperty(
        name="Results layout", items=LAYOUTS, default="GRID", options={"SKIP_SAVE"}
    )
    page: IntProperty(name="Results page", min=0, options={"SKIP_SAVE"})
    result: StringProperty(name="Selected result", options={"SKIP_SAVE"})


def state(context=None):
    """The window manager's results view, or None before registration."""
    manager = (context or bpy.context).window_manager
    return getattr(manager, "scenario_results_view", None) if manager is not None else None


def _layout_property(surface):
    return f"{surface.lower()}_layout"


def layout_of(context, surface):
    """``LIST`` or ``GRID`` for one surface; the list when nothing is registered."""
    view = state(context)
    return "LIST" if view is None else getattr(view, _layout_property(surface))


def settled():
    """Finished rows in the order Generations draws them, newest first."""
    return [row for row in runtime.state.jobs_view if row.is_terminal]


def previewed(rows=None):
    """Local IDs of the finished rows Generations draws on either surface.

    A surface showing the list draws the first page of rows; one showing the
    grid draws the shared page and the selected result. The preview
    controller requests stills for these rows only.
    """
    rows = settled() if rows is None else rows
    view = state()
    layouts = {"LIST"} if view is None else {getattr(view, _layout_property(s)) for s in SURFACES}
    ids = set()
    if "LIST" in layouts:
        ids.update(row.local_id for row in rows[: grid.PAGE_SIZE])
    if "GRID" in layouts:
        ids.update(row.local_id for row in grid.visible(rows, view.page))
        if view.result:
            ids.add(view.result)
    return ids


def draw_toggle(layout, context, surface):
    """The List and Grid choice of one surface, as a segmented control."""
    view = state(context)
    if view is not None:
        panels.equal_segments(layout, view, _layout_property(surface), ("LIST", "GRID"))


def _width(context, surface):
    return label_wrap.region_width(context) / label_wrap.ui_scale(context) - MARGIN[surface]


def _placeholder(record, tile):
    """The built-in icon a tile without a preview draws at preview size."""
    if not record.is_success:
        return "ERROR"
    if tile is not None:
        return result_previews.KIND_ICON[tile.kind]
    return panels.KIND_ICON.get(record.kind, "FILE")


def _icon(record, tile):
    if tile is not None and tile.icon_id:
        return tile.icon_id
    return result_previews.builtin_icon(_placeholder(record, tile))


def _pager(layout, page):
    row = layout.row(align=True)
    previous = row.row(align=True)
    previous.enabled = page.previous
    previous.operator(
        "scenario.page_results", text="Previous", icon="TRIA_LEFT"
    ).direction = "PREVIOUS"
    label = row.row(align=True)
    label.alignment = "CENTER"
    label.label(text=page.label)
    following = row.row(align=True)
    following.enabled = page.next
    following.operator("scenario.page_results", text="Next", icon="TRIA_RIGHT").direction = "NEXT"


def _draw_grid(layout, context, rows, surface, index):
    page = grid.page(len(rows), index)
    if page is not None:
        _pager(layout, page)
    columns, scale = grid.tile_layout(_width(context, surface))
    flow = layout.grid_flow(row_major=True, columns=columns, even_columns=True, align=False)
    shown = grid.visible(rows, index)
    for record in shown:
        cell = flow.column(align=True)
        cell.template_icon(icon_value=_icon(record, result_previews.cover(record)), scale=scale)
        button = cell.row(align=True)
        button.alert = not record.is_success
        button.operator(
            "scenario.show_result", text=panels._short_prompt(record)
        ).local_id = record.local_id
    # Blender spreads fewer cells than columns across the whole row; blank cells
    # keep the tiles of a page shorter than one row as wide as a full row's.
    for _ in range(columns - len(shown)):
        flow.column().label(text="")


def _draw_detail(layout, context, record, rows, surface):
    previous, following = grid.neighbors((row.local_id for row in rows), record.local_id)
    navigation = layout.row(align=True)
    back = navigation.row(align=True)
    back.enabled = previous is not None
    back.operator("scenario.show_result", text="", icon="TRIA_LEFT").local_id = previous or ""
    navigation.operator("scenario.show_result", text="All results", icon="IMGDISPLAY").local_id = ""
    forward = navigation.row(align=True)
    forward.enabled = following is not None
    forward.operator("scenario.show_result", text="", icon="TRIA_RIGHT").local_id = following or ""
    tile = result_previews.cover(record)
    box = layout.box()
    width = _width(context, surface) - BOX_MARGIN
    if tile is not None:
        box.template_icon(icon_value=_icon(record, tile), scale=grid.detail_scale(width))
    prompt = (
        record.meta.get("prompt") or record.meta.get("spark_look") or record.meta.get("look") or ""
    ).strip()
    if prompt:
        # Wrapped like the preview status lines, which share the box's margins.
        lines = label_wrap.label_lines(context, prompt, result_previews.TEXT_INSET)
        for index, line in enumerate(lines[:PROMPT_LINES]):
            box.label(text=line, icon="TEXT" if index == 0 else "BLANK1")
    panels.draw_result_model(box, record)
    # A recovered saved job knows only that it ran a model; its preview names the kind.
    kind = record.kind if record.kind in grid.KIND_LABEL or tile is None else tile.kind
    asset_id = tile.asset_id if tile is not None else panels._primary_asset(record)
    size = (record.meta.get("result_sizes") or {}).get(asset_id)
    box.label(
        text=grid.summary(kind, size, len(record.asset_ids)),
        icon=panels.KIND_ICON.get(kind, "FILE") if record.is_success else "ERROR",
    )
    submitted = grid.submitted_label(record.meta.get("claimed_at"), record.created_at)
    if submitted:
        box.label(text=f"Submitted {submitted}", icon="TIME")
    cost = panels.result_cost_label(record)
    if cost:
        box.label(text=cost, icon="FUND")
    panels.draw_result_body(box, record, single_icon=tile is None)


def draw(layout, context, rows, surface):
    """The grid's page, or the selected result large; reads memory only, writes nothing."""
    view = state(context)
    if view is None:
        return
    selected = next((row for row in rows if row.local_id == view.result), None)
    if view.result and selected is not None:
        _draw_detail(layout, context, selected, rows, surface)
    elif rows:
        _draw_grid(layout, context, rows, surface, view.page)
    else:
        layout.label(text="Nothing generated yet in this session")


def _redraw():
    from . import pump, studio

    pump.redraw()
    studio.redraw_popups()


class SCENARIO_OT_show_result(bpy.types.Operator):
    bl_idname = "scenario.show_result"
    bl_label = "Show result"
    bl_description = (
        "Show this result's large preview, details and actions; nothing is downloaded, "
        "applied, spent or changed in the scene"
    )
    bl_options = {"INTERNAL"}
    local_id: StringProperty(options={"HIDDEN", "SKIP_SAVE"})

    @classmethod
    def description(cls, context, properties):
        if not properties.local_id:
            return "Show every result as a grid of previews again"
        return cls.bl_description

    def execute(self, context):
        view = state(context)
        if view is None:
            return {"CANCELLED"}
        if self.local_id:
            rows = [row.local_id for row in settled()]
            if self.local_id not in rows:
                self.report({"WARNING"}, "This generation is no longer listed; refresh the results")
                return {"CANCELLED"}
            # The grid returns to the page holding the result shown last.
            view.page = grid.page_of(rows.index(self.local_id))
        view.result = self.local_id
        _redraw()
        return {"FINISHED"}


class SCENARIO_OT_page_results(bpy.types.Operator):
    bl_idname = "scenario.page_results"
    bl_label = "Show other results"
    bl_description = (
        "Show the previous or next results in the grid; nothing is downloaded, applied, "
        "spent or changed in the scene"
    )
    bl_options = {"INTERNAL"}
    direction: EnumProperty(
        items=(
            ("PREVIOUS", "Previous", "The previous page of results"),
            ("NEXT", "Next", "The next page of results"),
        ),
        options={"HIDDEN", "SKIP_SAVE"},
    )

    @classmethod
    def description(cls, context, properties):
        which = "previous" if properties.direction == "PREVIOUS" else "next"
        return (
            f"Show the {which} {grid.PAGE_SIZE} results in the grid; nothing is downloaded, "
            "applied, spent or changed in the scene"
        )

    def execute(self, context):
        view = state(context)
        if view is None:
            return {"CANCELLED"}
        total = len(settled())
        current = grid.clamp(view.page, total)
        index = grid.step(current, total, -1 if self.direction == "PREVIOUS" else 1)
        if index == current:
            return {"CANCELLED"}
        view.page = index
        _redraw()
        return {"FINISHED"}


CLASSES = (ScenarioResultsView, SCENARIO_OT_show_result, SCENARIO_OT_page_results)


def register():
    for cls in CLASSES:
        bpy.utils.register_class(cls)
    bpy.types.WindowManager.scenario_results_view = PointerProperty(
        type=ScenarioResultsView, options={"SKIP_SAVE"}
    )


def unregister():
    del bpy.types.WindowManager.scenario_results_view
    for cls in reversed(CLASSES):
        bpy.utils.unregister_class(cls)
