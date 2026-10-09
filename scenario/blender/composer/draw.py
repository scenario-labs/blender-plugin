# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""gpu/blf drawing of the floating composer. Runs inside a POST_PIXEL draw handler on the main thread; no IO."""

import math

import blf
import bpy
import gpu
from gpu_extras.batch import batch_for_shader

from ...core.ui import composer_layout as cl
from .. import generation, panels, runtime

_batches = {}
_shader = None
FONT = 0
ACCENT = (0.36, 0.55, 1.0, 1.0)
ACCENT_DIM = (0.36, 0.55, 1.0, 0.35)
CARD = (0.11, 0.11, 0.12, 0.92)
FIELD = (0.06, 0.06, 0.07, 1.0)
TEXT = (0.92, 0.92, 0.92, 1.0)
MUTED = (0.6, 0.6, 0.62, 1.0)
TAB = (0.2, 0.2, 0.22, 1.0)
TAB_HOVER = (0.28, 0.28, 0.3, 1.0)
SELECTION = (0.36, 0.55, 1.0, 0.45)
PROMPT_INSET = 12  # horizontal text inset inside the prompt field, in unscaled pixels


def _shader_get():
    global _shader
    if _shader is None:
        _shader = gpu.shader.from_builtin("UNIFORM_COLOR")
    return _shader


def _rounded_verts(w, h, r, segments=6):
    r = max(0.0, min(r, w / 2, h / 2))
    verts = []
    corners = (
        (w - r, h - r, 0.0),
        (r, h - r, math.pi / 2),
        (r, r, math.pi),
        (w - r, r, 3 * math.pi / 2),
    )
    for cx, cy, start in corners:
        for i in range(segments + 1):
            a = start + (math.pi / 2) * i / segments
            verts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    return verts


def _batch(w, h, r):
    key = (int(w), int(h), int(r))
    batch = _batches.get(key)
    if batch is None:
        verts = _rounded_verts(key[0], key[1], key[2])
        batch = batch_for_shader(_shader_get(), "TRI_FAN", {"pos": verts})
        if len(_batches) > 64:
            _batches.clear()
        _batches[key] = batch
    return batch


def rect(x, y, w, h, color, radius=8.0):
    if w <= 0 or h <= 0:
        return
    shader = _shader_get()
    with gpu.matrix.push_pop():
        gpu.matrix.translate((x, y, 0))
        shader.uniform_float("color", color)
        _batch(w, h, radius).draw(shader)


def text(x, y, size, string, color=TEXT, max_width=None):
    blf.size(FONT, size)
    if max_width is not None:
        while string and blf.dimensions(FONT, string)[0] > max_width:
            string = string[:-2] + "…" if len(string) > 2 else ""
    blf.color(FONT, *color)
    blf.position(FONT, x, y, 0)
    blf.draw(FONT, string)
    return blf.dimensions(FONT, string)[0]


def ui_scale(context):
    """Blender's multiplier for custom interface drawing: the display DPI times the Preferences resolution scale.

    The system pixel size is a line width derived from that same DPI (4 on Retina at a resolution scale of 2), so
    multiplying it by the resolution scale would count that scale twice. Background Blender reports 0, which
    stands for 1 so sizes derived from it are never zero."""
    return context.preferences.system.ui_scale or 1.0


# side regions drawn over the viewport with region overlap, and the space flag that shows each
SIDE_REGIONS = {"TOOLS": "show_region_toolbar", "UI": "show_region_ui"}


def overlap_insets(area, region):
    """(left, right) widths of `region` covered by the area's visible toolbar and sidebar.

    With region overlap these regions are drawn over the WINDOW region; without it they sit beside it and do
    not overlap its x-range. Each inset is measured from the edge the covering region is closer to (region.x
    and width, so a flipped sidebar counts on the left)."""
    if area is None or region is None:
        return (0.0, 0.0)
    space = getattr(getattr(area, "spaces", None), "active", None)
    x0 = region.x
    x1 = x0 + region.width
    centre = (x0 + x1) / 2
    left = right = 0.0
    for other in area.regions:
        flag = SIDE_REGIONS.get(other.type)
        if flag is None or other.width <= 1 or not getattr(space, flag, True):
            continue
        lo, hi = max(x0, other.x), min(x1, other.x + other.width)
        if hi <= lo:
            continue
        if other.x + other.width / 2 >= centre:
            right = max(right, float(x1 - lo))
        else:
            left = max(left, float(hi - x0))
    return (left, right)


# Blender's default sidebar width at a UI scale of 1 (UI_SIDEBAR_PANEL_WIDTH). A hidden sidebar reports a width of
# 1 px, so this stands in for the width it opens at.
SIDEBAR_WIDTH = 220


def card_fits_with_sidebar(context):
    """Whether the card still fits `context.region` once the area's sidebar is shown, as the model chip shows it.

    A visible sidebar is already measured, so showing it changes nothing. A hidden one covers (region overlap) or
    takes (no overlap) its width from the uncovered span once shown: its reported width when it has one, else
    Blender's default sidebar width at this UI scale. A sidebar widened before it was hidden reopens wider than
    that estimate."""
    area, region = getattr(context, "area", None), context.region
    space = getattr(getattr(area, "spaces", None), "active", None)
    sidebar = next((r for r in getattr(area, "regions", ()) if r.type == "UI"), None)
    if region is None or sidebar is None:
        return True
    if sidebar.width > 1 and getattr(space, "show_region_ui", True):
        return True
    scale = ui_scale(context)
    left, right = overlap_insets(area, region)
    width = sidebar.width if sidebar.width > 1 else SIDEBAR_WIDTH * scale
    if sidebar.x + sidebar.width / 2 >= region.x + region.width / 2:
        right += width
    else:
        left += width
    if left + right >= region.width:
        return False  # the sidebar would cover the whole viewport
    return cl.card_fits(region.width, region.height, scale, (left, right))


def composer_layout(context, state):
    """Geometry of the composer in `context.region`: the one layout drawing and hit testing share."""
    region = context.region
    return cl.pill_placement(
        region.width,
        region.height,
        state.expanded,
        ui_scale(context),
        offset=state.offset,
        width=state.width if state.expanded else None,
        insets=overlap_insets(getattr(context, "area", None), region),
    )


def prompt_metrics(prompt_rect, field, scale):
    """Font size, visible slice and text origin of the prompt field: shared by drawing and mouse hit testing."""
    font_px = int(12 * scale)
    blf.size(FONT, font_px)
    char_w = max(1.0, blf.dimensions(FONT, "M")[0] * 0.8)
    width_chars = int((prompt_rect.w - 2 * PROMPT_INSET * scale) / char_w)
    start, end = field.visible_slice(width_chars)
    return font_px, start, end, prompt_rect.x + PROMPT_INSET * scale


def caret_index_at(px, prompt_rect, field, scale):
    """Character index under the horizontal pixel `px`, measured on the visible slice (nearest glyph boundary)."""
    font_px, start, end, x0 = prompt_metrics(prompt_rect, field, scale)
    blf.size(FONT, font_px)
    rel = px - x0
    if rel <= 0:
        return start
    previous = 0.0
    for i in range(start + 1, end + 1):
        width = blf.dimensions(FONT, field.text[start:i])[0]
        if width >= rel:
            return i if (width - rel) <= (rel - previous) else i - 1
        previous = width
    return end


def _measure(font_px):
    """Text width in px at `font_px`, for the label choices of the pure layout."""
    blf.size(FONT, font_px)
    return lambda string: blf.dimensions(FONT, string)[0]


def _chip(r, label, scale, font_px, hovered, fill=TAB, color=TEXT, centered=False, clip=True):
    """A rounded chip with its label. `clip=False` draws a label already fitted (lane tabs) as it is."""
    rect(r.x, r.y, r.w, r.h, TAB_HOVER if hovered else fill, 6 * scale)
    blf.size(FONT, font_px)
    tw = blf.dimensions(FONT, label)[0]
    x = r.x + (max(4 * scale, (r.w - tw) / 2) if centered else 10 * scale)
    text(
        x,
        r.y + (r.h - font_px) / 2 + 2 * scale,
        font_px,
        label,
        color,
        max_width=r.w - cl.CHIP_TEXT_INSET * scale if clip else None,
    )


def _minus_button(cr, scale, hovered):
    rect(cr.x, cr.y, cr.w, cr.h, TAB_HOVER if hovered else TAB, 4 * scale)
    bar_h = max(1.5, 2 * scale)
    rect(cr.x + cr.w * 0.25, cr.y + (cr.h - bar_h) / 2, cr.w * 0.5, bar_h, TEXT, 0)


def _grip(gr, scale, hovered):
    """Three short diagonal bars in the bottom-right corner: the resize handle of the expanded card."""
    shader = _shader_get()
    color = TEXT if hovered else MUTED
    lines = []
    for i in range(3):
        d = (4 + 4 * i) * scale
        lines.append((gr.right - d, gr.y + 2 * scale))
        lines.append((gr.right - 2 * scale, gr.y + d))
    batch = batch_for_shader(shader, "LINES", {"pos": lines})
    gpu.state.line_width_set(max(1.0, 1.5 * scale))
    shader.uniform_float("color", color)
    batch.draw(shader)
    gpu.state.line_width_set(1.0)


def status_note(lane_state):
    """The line shown next to the model chip: a failed model description, a quote problem, the lane's error, else the add-on's temporary message."""
    error = generation.lane_error(lane_state)  # without a stale saved model-load failure
    failure = runtime.state.model_errors.get(lane_state.model_id)
    if failure is not None and generation.schema_for(lane_state.model_id) is None:
        return error or failure  # explains why the quote is unavailable
    if lane_state.estimate_state in ("ERROR", "UNAVAILABLE") and lane_state.estimate_error:
        return lane_state.estimate_error
    if error:
        return error
    visible = getattr(runtime, "message_visible", None)
    if callable(visible):
        return visible() or ""
    return runtime.state.last_message or ""


def _prompt_field(pr, field, focused, lane, scale):
    rect(pr.x, pr.y, pr.w, pr.h, FIELD, 6 * scale)
    font_px, start, end, x0 = prompt_metrics(pr, field, scale)
    text_y = pr.y + (pr.h - font_px) / 2 + 2 * scale
    if not field.text:
        text(
            x0,
            text_y,
            font_px,
            cl.placeholder_for(lane),
            MUTED,
            max_width=pr.w - 2 * PROMPT_INSET * scale,
        )
        if focused:
            rect(x0, pr.y + 8 * scale, max(1.0, 1.5 * scale), pr.h - 16 * scale, TEXT, 0)
        return
    blf.size(FONT, font_px)
    sel = field.selection
    if sel and focused:
        a, b = max(sel[0], start), min(sel[1], end)
        if b > a:
            sx0 = x0 + blf.dimensions(FONT, field.text[start:a])[0]
            sx1 = x0 + blf.dimensions(FONT, field.text[start:b])[0]
            rect(sx0, pr.y + 6 * scale, sx1 - sx0, pr.h - 12 * scale, SELECTION, 3 * scale)
    text(x0, text_y, font_px, field.text[start:end], TEXT)
    if focused:
        caret_x = (
            x0 + blf.dimensions(FONT, field.text[start : max(start, min(field.caret, end))])[0]
        )
        rect(caret_x, pr.y + 8 * scale, max(1.0, 1.5 * scale), pr.h - 16 * scale, TEXT, 0)


def draw_composer():
    context = bpy.context
    region = context.region
    scene = context.scene
    if region is None or scene is None or not hasattr(scene, "scenario"):
        return
    if (
        context.space_data is None
        or context.space_data.type != "VIEW_3D"
        or context.space_data.region_3d is None
    ):
        return
    state = runtime.state.composer
    if state is None:
        return
    layout = composer_layout(context, state)
    scale = layout.scale
    state.layout = layout
    lane_state = (
        state.sync_from_lane(scene)
        if not state.focused
        else scene.scenario.lane_state(state.lane_for(scene))
    )
    lane = state.lane_for(scene)
    enabled = panels.generate_enabled(lane_state, lane)
    font_px = int(12 * scale)
    gpu.state.blend_set("ALPHA")
    try:
        if not layout.expanded:
            # the collapsed composer shares the card's language: same fill, same corner radius, same field and button
            # styles; it also stands in for an expanded card the uncovered span cannot hold
            r = layout.pill_rect
            rect(r.x, r.y, r.w, r.h, CARD, 12 * scale)
            gen_w = 96 * scale
            inset = 6 * scale
            field_rect = cl.Rect(r.x + inset, r.y + inset, r.w - gen_w - 3 * inset, r.h - 2 * inset)
            rect(field_rect.x, field_rect.y, field_rect.w, field_rect.h, FIELD, 6 * scale)
            label = lane_state.prompt or cl.placeholder_for(lane)
            text(
                field_rect.x + 10 * scale,
                r.y + (r.h - font_px) / 2 + 2 * scale,
                font_px,
                label,
                TEXT if lane_state.prompt else MUTED,
                max_width=field_rect.w - 20 * scale,
            )
            gx = r.right - inset - gen_w
            rect(
                gx,
                r.y + inset,
                gen_w,
                r.h - 2 * inset,
                ACCENT if enabled else TAB,
                6 * scale,
            )
            blf.size(FONT, font_px)
            button_text = "Generate" if runtime.online() else "Offline"
            tw = blf.dimensions(FONT, button_text)[0]
            text(
                gx + max(4 * scale, (gen_w - tw) / 2),
                r.y + (r.h - font_px) / 2 + 2 * scale,
                font_px,
                button_text,
                TEXT if enabled else MUTED,
                max_width=gen_w - 8 * scale,
            )
            return
        card = layout.card_rect
        rect(card.x, card.y, card.w, card.h, CARD, 12 * scale)
        # full labels when they fit, else the short ones; the layout clips only as a last resort, never to nothing
        labels = layout.tab_labels(_measure(font_px))
        for tab_lane, tr in layout.tab_rects.items():
            active = tab_lane == lane
            _chip(
                tr,
                labels[tab_lane],
                scale,
                font_px,
                hovered=(state.hover == ("tab", tab_lane)) and not active,
                fill=ACCENT if active else TAB,
                centered=True,
                clip=False,
            )
        _minus_button(layout.collapse_rect, scale, hovered=(state.hover == ("collapse",)))
        _prompt_field(layout.prompt_rect, state.field, state.focused, lane, scale)
        mr = layout.model_rect
        model_name = panels.model_button_text(lane_state)
        _chip(mr, model_name, scale, font_px, hovered=(state.hover == ("model",)))
        note_x = mr.right + 10 * scale
        if layout.settings_rect is not None:
            _chip(
                layout.settings_rect,
                "Settings",
                scale,
                font_px,
                hovered=(state.hover == ("settings",)),
                color=MUTED,
                centered=True,
            )
            note_x = layout.settings_rect.right + 10 * scale
        gr = layout.generate_rect
        rect(gr.x, gr.y, gr.w, gr.h, ACCENT if enabled else TAB, 6 * scale)
        label = panels.generate_button_text(lane_state)
        blf.size(FONT, font_px)
        tw = blf.dimensions(FONT, label)[0]
        text(
            gr.x + max(8 * scale, (gr.w - tw) / 2),
            gr.y + (gr.h - font_px) / 2 + 2 * scale,
            font_px,
            label,
            TEXT if enabled else MUTED,
            max_width=gr.w - 12 * scale,
        )
        if layout.resize_rect is not None and (
            (state.hover == ("resize",)) or state.drag_mode == "resize"
        ):
            _grip(
                layout.resize_rect, scale, hovered=True
            )  # the corner only shows itself when the pointer reaches it
        note = status_note(lane_state)
        if note and gr.x - note_x > 40 * scale:
            text(
                note_x,
                mr.y + (mr.h - font_px) / 2 + 2 * scale,
                int(11 * scale),
                note,
                MUTED,
                max_width=gr.x - note_x - 10 * scale,
            )
    finally:
        gpu.state.blend_set("NONE")
