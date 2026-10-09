# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Geometry and text editing for the floating composer. No bpy, no gpu: pure numbers and strings."""

from dataclasses import dataclass, field

MARGIN = 24
PILL_WIDTH, PILL_HEIGHT = 320, 44
# card height: pad + tabs + gap + prompt + gap + model row + pad, no empty band under the buttons
CARD_WIDTH, CARD_HEIGHT = 820, 132
TAB_HEIGHT, ROW_GAP, PAD = 24, 8, 12
GENERATE_WIDTH, MODEL_WIDTH, COLLAPSE_SIZE, SETTINGS_WIDTH = 190, 200, 20, 84
RESIZE_SIZE, MIN_CARD_WIDTH, MIN_PILL_WIDTH, MIN_VISIBLE, DRAG_THRESHOLD = 16, 420, 200, 40, 4
LANE_ORDER = ("image", "video", "3d", "material", "render_image", "render_video")
LANE_LABELS = {
    "image": "Image",
    "video": "Video",
    "3d": "3D",
    "material": "Materials",
    "render_image": "Render Image",
    "render_video": "Render Video",
}
PLACEHOLDERS = {
    "image": "Describe the image to generate",
    "video": "Describe the video, or capture the timeline",
    "3d": "Describe the object",
    "material": "Describe the material (weathered copper, mossy stone...)",
    "render_image": "Describe the look to render the viewport with (empty: Prompt Spark writes it)",
    "render_video": "Describe the look of the video (empty: Prompt Spark writes it)",
}


def placeholder_for(lane):
    return PLACEHOLDERS.get(lane, "Type a prompt")


@dataclass
class Rect:
    x: float
    y: float
    w: float
    h: float

    def contains(self, px, py):
        return self.x <= px <= self.x + self.w and self.y <= py <= self.y + self.h

    @property
    def right(self):
        return self.x + self.w

    @property
    def top(self):
        return self.y + self.h


class TextField:
    """Single-line editor: text, caret index and a selection anchor.

    The selection is the span between `anchor` and `caret` (None when they coincide or no anchor is set), so
    extending with Shift+arrows, Shift+Home/End, shift-click or a drag only ever moves the caret."""

    def __init__(self, text="", caret=None):
        self.text = text
        self.caret = len(text) if caret is None else max(0, min(caret, len(text)))
        self.anchor = None

    # -- selection ----------------------------------------------------------
    @property
    def selection(self):
        if self.anchor is None or self.anchor == self.caret:
            return None
        a, b = sorted((self.anchor, self.caret))
        return (a, b)

    @selection.setter
    def selection(self, value):
        if value is None:
            self.anchor = None
            return
        a, b = value
        self.anchor, self.caret = self._clamp(a), self._clamp(b)

    def _clamp(self, index):
        return max(0, min(len(self.text), int(index)))

    def _clear_selection(self):
        self.anchor = None

    def _start_extend(self):
        if self.anchor is None:
            self.anchor = self.caret

    def selected_text(self):
        sel = self.selection
        return self.text[sel[0] : sel[1]] if sel else ""

    def select_all(self):
        self.anchor = 0
        self.caret = len(self.text)

    def select_word_at(self, index):
        """Select the word (or the whitespace run) under `index`, as a double-click does."""
        if not self.text:
            return
        i = max(0, min(len(self.text) - 1, int(index)))
        space = self.text[i].isspace()
        a = i
        while a > 0 and self.text[a - 1].isspace() == space:
            a -= 1
        b = i + 1
        while b < len(self.text) and self.text[b].isspace() == space:
            b += 1
        self.anchor, self.caret = a, b

    def caret_at(self, index, extend=False):
        """Place the caret from a click (or a drag when `extend` is true, which keeps the press position as anchor)."""
        if extend:
            self._start_extend()
        else:
            self._clear_selection()
        self.caret = self._clamp(index)

    # -- clipboard -----------------------------------------------------------
    def copy(self):
        return self.selected_text() or self.text

    def cut(self):
        if self.selection:
            out = self.selected_text()
            self.replace_selection("")
            return out
        out = self.text
        self.set_text("")
        return out

    # -- editing -------------------------------------------------------------
    def insert(self, s):
        if self.selection:
            self.replace_selection(s)
            return
        self._clear_selection()
        self.text = self.text[: self.caret] + s + self.text[self.caret :]
        self.caret += len(s)

    def backspace(self):
        if self.selection:
            self.replace_selection("")
            return
        self._clear_selection()
        if self.caret > 0:
            self.text = self.text[: self.caret - 1] + self.text[self.caret :]
            self.caret -= 1

    def delete(self):
        if self.selection:
            self.replace_selection("")
            return
        self._clear_selection()
        if self.caret < len(self.text):
            self.text = self.text[: self.caret] + self.text[self.caret + 1 :]

    def replace_selection(self, s):
        if not self.selection:
            self.insert(s)
            return
        a, b = self.selection
        self.text = self.text[:a] + s + self.text[b:]
        self.caret = a + len(s)
        self.anchor = None

    def set_text(self, text):
        self.text = text or ""
        self.caret = min(self.caret, len(self.text))
        self.anchor = None

    # -- caret movement --------------------------------------------------------
    def move(self, delta, extend=False):
        if extend:
            self._start_extend()
            self.caret = self._clamp(self.caret + delta)
            return
        sel = self.selection
        self._clear_selection()
        if sel:
            # collapse onto the edge, like a native text field
            self.caret = sel[0] if delta < 0 else sel[1]
            return
        self.caret = self._clamp(self.caret + delta)

    def home(self, extend=False):
        if extend:
            self._start_extend()
        else:
            self._clear_selection()
        self.caret = 0

    def end(self, extend=False):
        if extend:
            self._start_extend()
        else:
            self._clear_selection()
        self.caret = len(self.text)

    def visible_slice(self, width_chars):
        width_chars = max(1, int(width_chars))
        if len(self.text) <= width_chars:
            return 0, len(self.text)
        start = max(0, min(self.caret - width_chars + 1, len(self.text) - width_chars))
        if self.caret < start:
            start = self.caret
        return start, min(len(self.text), start + width_chars)


@dataclass
class Layout:
    expanded: bool
    scale: float
    pill_rect: Rect
    card_rect: Rect = None
    tab_rects: dict = field(default_factory=dict)
    prompt_rect: Rect = None
    model_rect: Rect = None
    generate_rect: Rect = None
    collapse_rect: Rect = None
    settings_rect: Rect = None
    resize_rect: Rect = None

    def hit(self, px, py):
        """What the pointer is on. `expand` (collapsed pill), `resize` (corner grip), `drag` (empty card area) or a control."""
        if not self.expanded:
            return ("expand",) if self.pill_rect.contains(px, py) else None
        if self.card_rect is None or not self.card_rect.contains(px, py):
            return None
        if self.resize_rect is not None and self.resize_rect.contains(px, py):
            return ("resize",)
        if self.collapse_rect.contains(px, py):
            return ("collapse",)
        for lane, rect in self.tab_rects.items():
            if rect.contains(px, py):
                return ("tab", lane)
        if self.prompt_rect.contains(px, py):
            return ("prompt",)
        if self.generate_rect.contains(px, py):
            return ("generate",)
        if self.model_rect.contains(px, py):
            return ("model",)
        if self.settings_rect is not None and self.settings_rect.contains(px, py):
            return ("settings",)
        return ("drag",)


# Job strip tray, in unscaled pixels: a separate row as wide as the expanded card, outside it.
STRIP_HEIGHT, STRIP_GAP, STRIP_PAD, STRIP_MIN_TEXT, STRIP_DOT = 30, 6, 8, 96, 8
DISMISS_SIZE, CHIP_INSET, PROGRESS_HEIGHT, INDICATOR_HEIGHT = 18, 4, 3, 2
CARD_RADIUS = 12  # corner radius the card and the pill are drawn with
INSPECT_CHIP = "inspect"  # the one strip chip that is never dropped


@dataclass(frozen=True)
class StripSpec:
    """The chips a job strip asks for, left to right, as (key, width) pairs.

    Widths are region pixels at the drawn font size, already scaled, so the caller measures each
    label exactly as it draws it."""

    chips: tuple = ()


@dataclass
class StripLayout:
    """Geometry of the job strip. A hidden strip draws no tray and takes no clicks.

    `chip_rects` holds the chips that fit, left to right, as (key, Rect) pairs. `indicator_rect`
    is a draw-only line inside the collapsed pill: the pill keeps its `expand` hit."""

    hidden: bool
    rect: Rect = None
    dot_rect: Rect = None
    text_rect: Rect = None
    progress_rect: Rect = None
    chip_rects: tuple = ()
    dismiss_rect: Rect = None
    indicator_rect: Rect = None

    def hit(self, px, py):
        """`job_dismiss`, (`job`, key) for a chip, `drag` on the rest of the tray, else None."""
        if self.hidden or self.rect is None or not self.rect.contains(px, py):
            return None
        if self.dismiss_rect.contains(px, py):
            return ("job_dismiss",)
        for key, rect in self.chip_rects:
            if rect.contains(px, py):
                return ("job", key)
        return ("drag",)


def _pill_indicator(pill, scale):
    radius = CARD_RADIUS * scale
    width = pill.w - 2 * radius
    if width <= 0:
        return None
    height = INDICATOR_HEIGHT * scale
    return Rect(pill.x + radius, pill.y + height, width, height)


def strip_placement(layout, region_w, region_h, spec, insets=(0.0, 0.0)):
    """Place the job strip for a composer `layout` returned by pill_placement.

    Expanded, the tray sits above the card when it fits below the region top, else below the card,
    else it is hidden; the card's own controls never move. `insets` are the (left, right) widths of
    side regions drawn over this one, as the composer placement records them: the tray stays in the
    span they leave uncovered, narrowing to it when the card is wider. Chips are right-aligned before
    the dismiss box. While the status text would be narrower than STRIP_MIN_TEXT, chips other than
    INSPECT_CHIP are dropped, last listed first. A tray that still cannot hold that text, Inspect and
    the dismiss box is hidden. Collapsed, only the pill's indicator line is placed."""
    s = layout.scale
    if not layout.expanded:
        return StripLayout(True, indicator_rect=_pill_indicator(layout.pill_rect, s))
    card = layout.card_rect
    left, right = (max(0.0, float(edge or 0.0)) for edge in (insets or (0.0, 0.0)))
    span_lo, span_hi = left, region_w - right
    w = min(card.w, span_hi - span_lo)
    h, gap, pad = STRIP_HEIGHT * s, STRIP_GAP * s, STRIP_PAD * s
    dot, dismiss, inset = STRIP_DOT * s, DISMISS_SIZE * s, CHIP_INSET * s
    if card.top + gap + h <= region_h:
        y = card.top + gap
    elif card.y - gap - h >= 0:
        y = card.y - gap - h
    else:
        return StripLayout(True)
    chips = [(str(key), max(0.0, float(width))) for key, width in spec.chips]

    def text_width():
        # pad, dot, gap, text, gap, then each chip and its gap, the dismiss box and pad
        return w - (2 * pad + dot + 2 * gap + dismiss) - sum(cw + gap for _, cw in chips)

    minimum = STRIP_MIN_TEXT * s
    droppable = [index for index, (key, _) in enumerate(chips) if key != INSPECT_CHIP]
    while droppable and text_width() < minimum:
        del chips[droppable.pop()]
    if w <= 0 or text_width() < minimum:
        return StripLayout(True)
    tray = Rect(_clamp(card.x, span_lo, span_hi - w), y, w, h)
    dismiss_rect = Rect(tray.right - pad - dismiss, y + (h - dismiss) / 2, dismiss, dismiss)
    chip_rects, cx = [], dismiss_rect.x - gap
    for key, cw in reversed(chips):
        cx -= cw
        chip_rects.append((key, Rect(cx, y + inset, cw, h - 2 * inset)))
        cx -= gap
    chip_rects.reverse()
    text_x = tray.x + pad + dot + gap
    text_w = (chip_rects[0][1].x if chip_rects else dismiss_rect.x) - gap - text_x
    progress = Rect(text_x, y + PROGRESS_HEIGHT * s, text_w, PROGRESS_HEIGHT * s)
    text = Rect(text_x, progress.top, text_w, tray.top - inset - progress.top)
    return StripLayout(
        False,
        tray,
        Rect(tray.x + pad, text.y + (text.h - dot) / 2, dot, dot),
        text,
        progress,
        tuple(chip_rects),
        dismiss_rect,
    )


def composer_hit(layout, strip, px, py):
    """What the pointer is on: the job strip first, then the composer's unchanged hits."""
    hit = strip.hit(px, py) if strip is not None else None
    return hit or layout.hit(px, py)


def _clamp(value, lo, hi):
    if hi < lo:
        hi = lo
    return max(lo, min(hi, value))


def clamp_width(width, region_w, scale=1.0, expanded=True):
    """A card or pill width that fits the region: never narrower than the minimum, never wider than the region minus margins."""
    s = float(scale or 1.0)
    margin = MARGIN * s
    minimum = (MIN_CARD_WIDTH if expanded else MIN_PILL_WIDTH) * s
    maximum = max(minimum, region_w - 2 * margin)
    return _clamp(float(width), minimum, maximum)


def clamp_offset(offset, size, region_w, region_h, scale=1.0):
    """Keep at least MIN_VISIBLE px of a `size`-wide/high box inside the region, given its default bottom-centre position."""
    s = float(scale or 1.0)
    w, h = size
    margin = MARGIN * s
    keep = MIN_VISIBLE * s
    base_x, base_y = (region_w - w) / 2, margin
    ox, oy = offset
    x = _clamp(base_x + ox, keep - w, region_w - keep)
    y = _clamp(base_y + oy, keep - h, region_h - keep)
    return (x - base_x, y - base_y)


def pill_placement(region_w, region_h, expanded, scale=1.0, offset=(0.0, 0.0), width=None):
    """Geometry of the composer. `offset` moves it from its default bottom-centre spot (region pixels), `width`
    overrides the card (expanded) or pill (collapsed) width; both are clamped so the composer stays reachable."""
    s = float(scale or 1.0)
    margin = MARGIN * s
    offset = tuple(offset or (0.0, 0.0))
    if not expanded:
        w = clamp_width(width if width else PILL_WIDTH * s, region_w, s, expanded=False)
        w = min(w, max(MIN_PILL_WIDTH * s, region_w - 2 * margin))
        h = PILL_HEIGHT * s
        ox, oy = clamp_offset(offset, (w, h), region_w, region_h, s)
        return Layout(False, s, Rect((region_w - w) / 2 + ox, margin + oy, w, h))
    w = clamp_width(width if width else CARD_WIDTH * s, region_w, s, expanded=True)
    w = min(w, max(MIN_CARD_WIDTH * s, region_w - 2 * margin))
    h = min(CARD_HEIGHT * s, region_h - 2 * margin)
    ox, oy = clamp_offset(offset, (w, h), region_w, region_h, s)
    x, y = (region_w - w) / 2 + ox, margin + oy
    card = Rect(x, y, w, h)
    pad, gap = PAD * s, ROW_GAP * s
    tab_h = TAB_HEIGHT * s
    tabs_y = card.top - pad - tab_h
    # the minus button is a cell of the tab row: same height as the tabs, in the top-right corner
    collapse = Rect(card.right - pad - tab_h, tabs_y, tab_h, tab_h)
    tab_rects, tx = {}, x + pad
    tab_w = (collapse.x - gap - (x + pad) - gap * (len(LANE_ORDER) - 1)) / len(LANE_ORDER)
    for lane in LANE_ORDER:
        tab_rects[lane] = Rect(tx, tabs_y, tab_w, tab_h)
        tx += tab_w + gap
    row_h = 34 * s
    prompt_y = tabs_y - gap - row_h
    prompt = Rect(x + pad, prompt_y, w - 2 * pad, row_h)
    bottom_y = prompt_y - gap - row_h
    if bottom_y < y + pad:
        bottom_y = y + pad
    model = Rect(x + pad, bottom_y, min(MODEL_WIDTH * s, w / 2 - pad), row_h)
    generate = Rect(
        card.right - pad - min(GENERATE_WIDTH * s, w / 2 - pad),
        bottom_y,
        min(GENERATE_WIDTH * s, w / 2 - pad),
        row_h,
    )
    settings = None
    room = generate.x - gap - (model.right + gap)
    if room >= 40 * s:
        settings = Rect(model.right + gap, bottom_y, min(SETTINGS_WIDTH * s, room), row_h)
    grip = RESIZE_SIZE * s
    resize = Rect(card.right - grip, card.y, grip, grip)  # bottom-right corner
    return Layout(
        True,
        s,
        Rect(x, y, w, h),
        card,
        tab_rects,
        prompt,
        model,
        generate,
        collapse,
        settings,
        resize,
    )
