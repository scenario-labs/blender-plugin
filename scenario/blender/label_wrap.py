# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Wrap panel label text to the width Blender's interface font measures for it.

Draw code passes its context and an inset: the interface units that panels,
boxes, the first line's icon and Blender's clipping margin take from the
measured width in its layout. Only preferences, the region and font metrics are
read. Measuring sets the interface font's size, which Blender sets again before
it draws or measures any interface text; no property is written.
"""

from contextlib import contextmanager

import blf

from ..core.ui.text_wrap import wrap

FONT = 0  # Blender's interface font
MIN_WIDTH = 60  # interface units: about twelve characters at the default text size
_popup_width = None  # interface units of the popup layout being drawn, when declared


@contextmanager
def popup_layout(width):
    """Measure labels drawn inside this block against a popup ``width`` interface units wide.

    ``invoke_popup`` lays its block out at the requested width times the
    interface scale, but Blender builds that layout before it sizes the popup's
    region, so ``context.region_popup`` is 0 px wide on the first draw. A popup
    that draws wrapped labels declares its requested width here, so its first
    draw and every refresh wrap alike.
    """
    global _popup_width
    previous, _popup_width = _popup_width, width
    try:
        yield
    finally:
        _popup_width = previous


def ui_scale(context):
    """Blender's custom-interface multiplier; background Blender reports 0, read as 1.

    It already includes the resolution scale. The pixel size is a line width
    derived from the same DPI, so multiplying it by ``view.ui_scale`` would count
    that scale twice.
    """
    return context.preferences.system.ui_scale or 1.0


def region_width(context):
    """Pixel width that labels are measured against.

    A declared popup layout comes first. Otherwise a popup's own region once
    Blender has sized it, because a popup's context region is the one it was
    invoked from, such as a header that spans the whole area. Otherwise, as
    for an undeclared popup that is not sized yet, the context's region.
    """
    if _popup_width is not None:
        return _popup_width * ui_scale(context)
    popup = context.region_popup
    if popup is not None and popup.width > 0:
        return popup.width
    region = context.region
    return region.width if region is not None else 300


def label_lines(context, text, inset):
    """Lines of ``text`` that fit a label ``inset`` interface units narrower than that width."""
    scale = ui_scale(context)
    width = max(MIN_WIDTH, region_width(context) / scale - inset) * scale
    blf.size(FONT, context.preferences.ui_styles[0].widget.points * scale)
    return wrap(text, width, lambda line: blf.dimensions(FONT, line)[0])
