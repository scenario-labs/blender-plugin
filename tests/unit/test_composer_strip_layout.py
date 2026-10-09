# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Placement, chip fitting and hit precedence of the composer's job strip tray."""

import pytest

from scenario.core.ui import composer_layout as cl

SCALES = (1.0, 1.25, 1.5, 2.0)


def _width(label, scale):
    """About the 11 px label width plus padding that the composer measures with blf."""
    return (len(label) * 6.5 + 20) * scale


def _spec(scale=1.0, *chips):
    return cl.StripSpec(tuple((key, _width(label, scale)) for key, label in chips))


def _center(rect):
    return rect.x + rect.w / 2, rect.y + rect.h / 2


def _inside(inner, outer):
    eps = 1e-6
    return (
        inner.x >= outer.x - eps
        and inner.y >= outer.y - eps
        and inner.right <= outer.right + eps
        and inner.top <= outer.top + eps
    )


def _rects(strip):
    return (strip.dot_rect, strip.text_rect, strip.progress_rect, strip.dismiss_rect) + tuple(
        rect for _, rect in strip.chip_rects
    )


INSPECT = ("inspect", "Inspect")
DOWNLOAD = ("recover_download", "Check interrupted download")


def test_tray_sits_above_the_card_at_its_width_and_leaves_the_card_unchanged():
    layout = cl.pill_placement(1600, 900, expanded=True)
    strip = cl.strip_placement(
        layout, 1600, 900, _spec(1.0, ("import_model:a1", "Import model"), INSPECT)
    )
    card = layout.card_rect
    assert not strip.hidden and strip.indicator_rect is None
    assert strip.rect == cl.Rect(card.x, card.top + cl.STRIP_GAP, card.w, cl.STRIP_HEIGHT)
    assert layout == cl.pill_placement(1600, 900, expanded=True)
    assert [key for key, _ in strip.chip_rects] == ["import_model:a1", "inspect"]
    for rect in _rects(strip):
        assert _inside(rect, strip.rect)


@pytest.mark.parametrize("scale", SCALES)
def test_tray_flips_below_the_card_near_the_region_top(scale):
    s = scale
    room = cl.MARGIN * s + cl.CARD_HEIGHT * s + cl.STRIP_GAP * s + cl.STRIP_HEIGHT * s
    spec = _spec(s, INSPECT)
    fits = cl.pill_placement(2000, 900 * s, True, s, offset=(0.0, 900 * s - room))
    above = cl.strip_placement(fits, 2000, 900 * s, spec)
    assert not above.hidden and above.rect.y == fits.card_rect.top + cl.STRIP_GAP * s
    assert above.rect.top <= 900 * s
    near = cl.pill_placement(2000, 900 * s, True, s, offset=(0.0, 900 * s - room + 2))
    below = cl.strip_placement(near, 2000, 900 * s, spec)
    assert not below.hidden and below.rect.top == near.card_rect.y - cl.STRIP_GAP * s
    parked = cl.pill_placement(2000, 900 * s, True, s, offset=(0.0, 5000.0))
    top = cl.strip_placement(parked, 2000, 900 * s, spec)
    assert not top.hidden and top.rect.top == parked.card_rect.y - cl.STRIP_GAP * s
    assert top.rect.y >= 0


@pytest.mark.parametrize("scale", SCALES)
def test_tray_hides_in_regions_too_short_for_card_and_tray(scale):
    s = scale
    room = (cl.MARGIN + cl.CARD_HEIGHT + cl.STRIP_GAP + cl.STRIP_HEIGHT) * s
    spec = _spec(s, INSPECT)
    tall = cl.pill_placement(2000, room, True, s)
    assert not cl.strip_placement(tall, 2000, room, spec).hidden
    short = cl.pill_placement(2000, room - 1, True, s)
    strip = cl.strip_placement(short, 2000, room - 1, spec)
    assert strip.hidden and strip.rect is None and strip.chip_rects == ()
    point = _center(short.card_rect)
    assert strip.hit(*point) is None
    assert cl.composer_hit(short, strip, *point) == short.hit(*point)


@pytest.mark.parametrize("scale", SCALES)
def test_both_chips_fit_at_the_minimum_card_width(scale):
    s = scale
    region_w = (cl.MIN_CARD_WIDTH + 2 * cl.MARGIN) * s
    layout = cl.pill_placement(region_w, 900 * s, True, s)
    assert layout.card_rect.w == pytest.approx(cl.MIN_CARD_WIDTH * s)
    strip = cl.strip_placement(layout, region_w, 900 * s, _spec(s, DOWNLOAD, INSPECT))
    (download_key, download), (inspect_key, inspect) = strip.chip_rects
    assert (download_key, inspect_key) == ("recover_download", "inspect")
    gap, pad = cl.STRIP_GAP * s, cl.STRIP_PAD * s
    assert strip.dismiss_rect.right == pytest.approx(strip.rect.right - pad)
    assert inspect.right == pytest.approx(strip.dismiss_rect.x - gap)
    assert download.right == pytest.approx(inspect.x - gap)
    assert strip.text_rect.right == pytest.approx(download.x - gap)
    assert strip.text_rect.w >= cl.STRIP_MIN_TEXT * s
    assert strip.dot_rect.x == pytest.approx(strip.rect.x + pad)
    assert strip.dot_rect.right + gap == pytest.approx(strip.text_rect.x)
    progress = strip.progress_rect
    assert (progress.x, progress.w) == (strip.text_rect.x, strip.text_rect.w)
    assert progress.h == pytest.approx(cl.PROGRESS_HEIGHT * s)
    assert progress.top <= strip.text_rect.y
    for rect in _rects(strip):
        assert _inside(rect, strip.rect)
    assert _inside(strip.rect, cl.Rect(0, 0, region_w, 900 * s))


@pytest.mark.parametrize("scale", SCALES)
def test_other_chips_drop_before_inspect_last_listed_first(scale):
    s = scale
    region_w = (cl.MIN_CARD_WIDTH + 2 * cl.MARGIN) * s
    layout = cl.pill_placement(region_w, 900 * s, True, s)
    wide = cl.StripSpec((("apply", 250 * s), ("inspect", _width("Inspect", s))))
    strip = cl.strip_placement(layout, region_w, 900 * s, wide)
    assert [key for key, _ in strip.chip_rects] == ["inspect"]
    assert strip.text_rect.w >= cl.STRIP_MIN_TEXT * s
    two = cl.StripSpec((("a", 100 * s), ("b", 100 * s), ("inspect", _width("Inspect", s))))
    kept = cl.strip_placement(layout, region_w, 900 * s, two)
    assert [key for key, _ in kept.chip_rects] == ["a", "inspect"]


def test_tray_hides_when_inspect_and_readable_text_cannot_fit():
    layout = cl.pill_placement(1600, 900, expanded=True)
    spec = _spec(1.0, ("apply", "Apply... (2)"), INSPECT)
    narrow = cl.strip_placement(layout, 1600, 900, spec, insets=(700.0, 700.0))
    assert narrow.hidden and narrow.chip_rects == ()
    huge = cl.strip_placement(layout, 1600, 900, cl.StripSpec((("inspect", 900.0),)))
    assert huge.hidden
    covered = cl.strip_placement(layout, 1600, 900, spec, insets=(900.0, 900.0))
    assert covered.hidden


def test_tray_stays_in_the_span_side_regions_leave_uncovered():
    spec = _spec(1.0, INSPECT)
    insets = (100.0, 300.0)
    span = cl.Rect(100.0, 0.0, 1200.0, 900.0)
    for dx, expected_x in ((-200.0, None), (-350.0, 100.0), (200.0, 480.0)):
        layout = cl.pill_placement(1600, 900, True, offset=(dx, 0.0))
        strip = cl.strip_placement(layout, 1600, 900, spec, insets=insets)
        assert strip.rect.w == layout.card_rect.w
        assert strip.rect.x == (layout.card_rect.x if expected_x is None else expected_x)
        assert _inside(strip.rect, span)
    layout = cl.pill_placement(1600, 900, expanded=True)
    narrowed = cl.strip_placement(layout, 1600, 900, spec, insets=(600.0, 600.0))
    assert narrowed.rect == cl.Rect(600.0, layout.card_rect.top + cl.STRIP_GAP, 400.0, 30.0)
    off_left = cl.pill_placement(1600, 900, True, offset=(-5000.0, 0.0))
    bare = cl.strip_placement(off_left, 1600, 900, spec)
    assert off_left.card_rect.x < 0 and bare.rect.x == 0
    assert cl.strip_placement(off_left, 1600, 900, spec, insets=None).rect == bare.rect


def test_hit_precedence_strip_first_and_card_hits_unchanged():
    layout = cl.pill_placement(1600, 900, expanded=True)
    strip = cl.strip_placement(
        layout, 1600, 900, _spec(1.0, ("cancel", "Cancel generation"), INSPECT)
    )
    assert cl.composer_hit(layout, strip, *_center(strip.dismiss_rect)) == ("job_dismiss",)
    for key, rect in strip.chip_rects:
        assert cl.composer_hit(layout, strip, *_center(rect)) == ("job", key)
        assert cl.composer_hit(layout, strip, rect.x, rect.y) == ("job", key)
    assert cl.composer_hit(layout, strip, *_center(strip.text_rect)) == ("drag",)
    assert cl.composer_hit(layout, strip, *_center(strip.dot_rect)) == ("drag",)
    assert cl.composer_hit(layout, strip, strip.rect.x + 1, strip.rect.y + 1) == ("drag",)
    between = (strip.rect.x + 10, layout.card_rect.top + cl.STRIP_GAP / 2)
    assert cl.composer_hit(layout, strip, *between) is None
    card_rects = [
        layout.prompt_rect,
        layout.generate_rect,
        layout.model_rect,
        layout.collapse_rect,
        layout.settings_rect,
        *layout.tab_rects.values(),
    ]
    for rect in card_rects:
        point = _center(rect)
        assert cl.composer_hit(layout, strip, *point) == layout.hit(*point) != ("drag",)
    corner = (layout.card_rect.right - 2, layout.card_rect.y + 2)
    assert cl.composer_hit(layout, strip, *corner) == ("resize",)
    assert cl.composer_hit(layout, None, *corner) == ("resize",)
    assert cl.composer_hit(layout, None, *_center(strip.dismiss_rect)) is None


@pytest.mark.parametrize("scale", SCALES)
def test_collapsed_pill_gets_only_a_draw_only_indicator(scale):
    s = scale
    pill = cl.pill_placement(1600 * s, 900 * s, False, s)
    strip = cl.strip_placement(pill, 1600 * s, 900 * s, _spec(s, INSPECT))
    assert strip.hidden and strip.rect is None and strip.chip_rects == ()
    indicator, rect = strip.indicator_rect, pill.pill_rect
    assert indicator.h == pytest.approx(cl.INDICATOR_HEIGHT * s)
    assert indicator.x == pytest.approx(rect.x + cl.CARD_RADIUS * s)
    assert indicator.right == pytest.approx(rect.right - cl.CARD_RADIUS * s)
    assert rect.y < indicator.y and indicator.top <= rect.y + 6 * s  # under the prompt field
    assert cl.composer_hit(pill, strip, *_center(indicator)) == ("expand",)
    assert strip.hit(*_center(indicator)) is None
