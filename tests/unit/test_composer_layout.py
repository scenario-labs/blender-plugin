# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
from scenario.core.ui import composer_layout as cl


def test_text_field_editing_and_caret():
    f = cl.TextField("hello")
    assert f.caret == 5
    f.insert(" world")
    assert f.text == "hello world" and f.caret == 11
    f.move(-5)
    f.backspace()
    assert f.text == "helloworld" and f.caret == 5
    f.delete()
    assert f.text == "helloorld"
    f.home()
    assert f.caret == 0
    f.end()
    assert f.caret == len(f.text)
    f.select_all()
    assert f.selection == (0, len(f.text))
    f.replace_selection("x")
    assert f.text == "x" and f.caret == 1 and f.selection is None


def test_visible_slice_keeps_caret_visible():
    f = cl.TextField("a" * 50)
    assert f.visible_slice(20) == (30, 50)
    f.home()
    assert f.visible_slice(20) == (0, 20)
    f.move(25)
    start, end = f.visible_slice(20)
    assert start <= 25 <= end and end - start == 20


def test_pill_placement_and_hit_testing():
    collapsed = cl.pill_placement(1600, 900, expanded=False, scale=1.0)
    assert collapsed.pill_rect.w == cl.PILL_WIDTH and collapsed.pill_rect.y == cl.MARGIN
    assert abs((collapsed.pill_rect.x + collapsed.pill_rect.w / 2) - 800) < 1
    assert collapsed.hit(800, cl.MARGIN + 10) == ("expand",)
    assert collapsed.hit(10, 10) is None
    expanded = cl.pill_placement(1600, 900, expanded=True, scale=1.0)
    card = expanded.card_rect
    assert card.w == cl.CARD_WIDTH and card.x >= 0 and card.y >= 0
    tab = expanded.tab_rects["material"]
    assert expanded.hit(tab.x + 2, tab.y + 2) == ("tab", "material")
    p = expanded.prompt_rect
    assert expanded.hit(p.x + 5, p.y + 5) == ("prompt",)
    g = expanded.generate_rect
    assert expanded.hit(g.x + 1, g.y + 1) == ("generate",)
    m = expanded.model_rect
    assert expanded.hit(m.x + 1, m.y + 1) == ("model",)
    c = expanded.collapse_rect
    assert expanded.hit(c.x + 1, c.y + 1) == ("collapse",)
    for rect in (card, tab, p, g, m, c):
        assert rect.x >= 0 and rect.y >= 0 and rect.x + rect.w <= 1600 and rect.y + rect.h <= 900


def test_scale_multiplies_every_size_and_fits_small_regions():
    hi = cl.pill_placement(1800, 900, expanded=True, scale=2.0)
    assert hi.card_rect.w == cl.CARD_WIDTH * 2
    narrow = cl.pill_placement(500, 400, expanded=True, scale=1.0)
    assert narrow.card_rect.w <= 500 - 2 * cl.MARGIN
    assert narrow.card_rect.x >= 0


def test_prompt_placeholder_and_lane_labels():
    assert cl.LANE_ORDER == ("image", "video", "3d", "material", "render_image", "render_video")
    assert (
        cl.LANE_LABELS["image"] == "Image"
        and cl.LANE_LABELS["render_image"] == "Render Image"
        and cl.LANE_LABELS["render_video"] == "Render Video"
    )
    assert cl.placeholder_for("image").startswith("Describe")
    assert "Prompt Spark" in cl.placeholder_for(
        "render_image"
    ) and "Prompt Spark" in cl.placeholder_for("render_video")
    assert cl.placeholder_for("unknown") == "Type a prompt"


def test_shift_arrows_extend_and_shrink_the_selection():
    f = cl.TextField("hello world")  # caret at 11
    f.move(-1, extend=True)
    assert f.selection == (10, 11) and f.caret == 10 and f.anchor == 11
    f.move(-4, extend=True)
    assert f.selection == (6, 11) and f.selected_text() == "world"
    f.move(1, extend=True)  # shrink from the caret side
    assert f.selection == (7, 11) and f.selected_text() == "orld"
    f.move(4, extend=True)  # caret meets the anchor: no selection
    assert f.selection is None and f.caret == 11
    f.home(extend=True)
    assert f.selection == (0, 11) and f.caret == 0
    f.end(extend=True)
    assert f.selection is None and f.caret == 11
    f.move(-3)
    f.home(extend=True)
    f.end(extend=True)  # anchor stays at 8, caret to the end
    assert f.selection == (8, 11)


def test_plain_moves_collapse_onto_the_selection_edge():
    f = cl.TextField("abcdef", caret=1)
    f.move(3, extend=True)  # selects bcd, caret 4
    assert f.selection == (1, 4)
    f.move(1)
    assert f.selection is None and f.caret == 4
    f.move(-3, extend=True)
    f.move(-1)
    assert f.selection is None and f.caret == 1
    f.move(2, extend=True)
    f.home()
    assert f.selection is None and f.caret == 0
    f.move(2, extend=True)
    f.end()
    assert f.selection is None and f.caret == 6


def test_typing_paste_backspace_delete_act_on_the_selection():
    f = cl.TextField("hello world", caret=0)
    f.move(5, extend=True)
    f.insert("bye")
    assert f.text == "bye world" and f.caret == 3 and f.selection is None
    f.move(-3, extend=True)
    f.backspace()
    assert f.text == " world" and f.caret == 0
    f.move(1, extend=True)
    f.delete()
    assert f.text == "world" and f.caret == 0
    f.select_all()
    f.insert("pasted text")
    assert f.text == "pasted text" and f.caret == 11
    f.select_all()
    f.replace_selection("")
    assert f.text == "" and f.selection is None
    f.select_all()  # nothing to select in an empty field
    assert f.selection is None


def test_click_shift_click_drag_and_double_click():
    f = cl.TextField("one two  three")
    f.caret_at(2)
    assert f.caret == 2 and f.selection is None
    f.caret_at(6, extend=True)  # shift-click
    assert f.selection == (2, 6) and f.selected_text() == "e tw"
    f.caret_at(0, extend=True)  # drag back past the anchor
    assert f.selection == (0, 2)
    f.caret_at(99)
    assert f.caret == len(f.text) and f.selection is None
    f.select_word_at(5)
    assert f.selected_text() == "two" and f.caret == 7
    f.select_word_at(8)  # inside the double space
    assert f.selected_text() == "  "
    f.select_word_at(0)
    assert f.selected_text() == "one"
    f.select_word_at(50)  # clamped to the last character
    assert f.selected_text() == "three"
    empty = cl.TextField("")
    empty.select_word_at(0)
    assert empty.selection is None


def test_copy_and_cut():
    f = cl.TextField("copy me please", caret=0)
    assert f.copy() == "copy me please"  # nothing selected: the whole text
    f.move(4, extend=True)
    assert f.copy() == "copy" and f.text == "copy me please"
    assert f.cut() == "copy" and f.text == " me please" and f.caret == 0 and f.selection is None
    assert f.cut() == " me please" and f.text == ""


def test_selection_setter_keeps_compatibility_and_set_text_clears_it():
    f = cl.TextField("abcdef")
    f.selection = (1, 4)
    assert f.selection == (1, 4) and f.caret == 4
    f.selection = None
    assert f.selection is None and f.caret == 4
    f.select_all()
    f.set_text("xy")
    assert f.selection is None and f.caret == 2
    f.selection = (0, 50)  # clamped
    assert f.selection == (0, 2)


def test_visible_slice_follows_the_caret_while_selecting():
    f = cl.TextField("a" * 50, caret=50)
    f.home(extend=True)
    start, end = f.visible_slice(20)
    assert start == 0 and end == 20 and f.selection == (0, 50)
    f.caret_at(45, extend=True)
    start, end = f.visible_slice(20)
    assert start <= 45 <= end


def test_settings_chip_and_corner_minus_button():
    expanded = cl.pill_placement(1600, 900, expanded=True, scale=1.0)
    card, c = expanded.card_rect, expanded.collapse_rect
    pad = cl.PAD
    assert (
        c.w == c.h == cl.TAB_HEIGHT
    )  # the minus button is a cell of the tab row, same height as the tabs
    assert abs((card.right - c.right) - pad) < 1e-6  # same padding on the right as the card
    tab = next(iter(expanded.tab_rects.values()))
    assert abs(c.y - tab.y) < 1e-6 and abs(c.h - tab.h) < 1e-6  # aligned with the tab row
    for rect in expanded.tab_rects.values():
        assert rect.right <= c.x  # tabs never run under the button
    s = expanded.settings_rect
    assert s is not None and s.x > expanded.model_rect.right and s.right < expanded.generate_rect.x
    assert expanded.hit(s.x + 1, s.y + 1) == ("settings",)
    assert expanded.hit(c.x + c.w - 1, c.y + c.h - 1) == ("collapse",)
    assert len(expanded.tab_rects) == 6 and expanded.hit(
        *_center(expanded.tab_rects["render_video"])
    ) == ("tab", "render_video")
    # the narrowest region that still shows the card: its minimum width plus its margins
    narrow = cl.pill_placement(cl.MIN_CARD_WIDTH + 2 * cl.MARGIN, 400, expanded=True, scale=1.0)
    assert narrow.expanded and narrow.card_rect.w == cl.MIN_CARD_WIDTH
    assert narrow.settings_rect is None or narrow.settings_rect.right < narrow.generate_rect.x
    assert narrow.hit(narrow.model_rect.x + 1, narrow.model_rect.y + 1) == ("model",)


def _center(rect):
    return rect.x + rect.w / 2, rect.y + rect.h / 2


def test_offset_moves_the_composer_and_is_clamped_to_keep_it_reachable():
    base = cl.pill_placement(1600, 900, expanded=True)
    moved = cl.pill_placement(1600, 900, expanded=True, offset=(120.0, 300.0))
    assert (
        moved.card_rect.x == base.card_rect.x + 120.0
        and moved.card_rect.y == base.card_rect.y + 300.0
    )
    assert moved.card_rect.w == base.card_rect.w
    # every control travels with the card
    assert (
        moved.prompt_rect.y == base.prompt_rect.y + 300.0
        and moved.generate_rect.x == base.generate_rect.x + 120.0
    )
    # dragged far away: at least MIN_VISIBLE px stay inside the region
    far = cl.pill_placement(1600, 900, expanded=True, offset=(5000.0, -5000.0))
    assert far.card_rect.x == 1600 - cl.MIN_VISIBLE
    assert far.card_rect.y == cl.MIN_VISIBLE - far.card_rect.h
    left = cl.pill_placement(1600, 900, expanded=True, offset=(-5000.0, 5000.0))
    assert left.card_rect.x == cl.MIN_VISIBLE - left.card_rect.w
    assert left.card_rect.y == 900 - cl.MIN_VISIBLE
    # the collapsed pill shares the offset (same centre point), and clamps the same way
    pill = cl.pill_placement(1600, 900, expanded=False, offset=(120.0, 300.0))
    assert pill.pill_rect.y == cl.MARGIN + 300.0
    assert (
        abs((pill.pill_rect.x + pill.pill_rect.w / 2) - (moved.card_rect.x + moved.card_rect.w / 2))
        < 1e-6
    )


def test_width_override_is_clamped_between_the_minimum_and_the_region():
    wide = cl.pill_placement(1600, 900, expanded=True, width=1200)
    assert wide.card_rect.w == 1200
    assert wide.generate_rect.right == wide.card_rect.right - cl.PAD
    too_wide = cl.pill_placement(1600, 900, expanded=True, width=5000)
    assert too_wide.card_rect.w == 1600 - 2 * cl.MARGIN
    too_narrow = cl.pill_placement(1600, 900, expanded=True, width=10)
    assert too_narrow.card_rect.w == cl.MIN_CARD_WIDTH
    scaled = cl.pill_placement(3200, 1800, expanded=True, scale=2.0, width=10)
    assert scaled.card_rect.w == cl.MIN_CARD_WIDTH * 2
    assert (
        cl.clamp_width(50, 1600) == cl.MIN_CARD_WIDTH
        and cl.clamp_width(50, 1600, expanded=False) == cl.MIN_PILL_WIDTH
    )
    pill = cl.pill_placement(1600, 900, expanded=False, width=600)
    assert pill.pill_rect.w == 600


def test_resize_grip_and_drag_hit_kinds():
    layout = cl.pill_placement(1600, 900, expanded=True)
    card = layout.card_rect
    grip = layout.resize_rect
    assert (
        grip is not None
        and grip.right == card.right
        and grip.y == card.y
        and grip.w == cl.RESIZE_SIZE
    )
    assert layout.hit(card.right - 2, card.y + 2) == ("resize",)
    # empty card area (between the tabs row and the prompt) is a drag handle
    gap_y = layout.prompt_rect.top + (layout.tab_rects["image"].y - layout.prompt_rect.top) / 2
    assert layout.hit(card.x + card.w / 2, gap_y) == ("drag",)
    assert layout.hit(card.x - 5, card.y + 5) is None
    assert layout.hit(layout.generate_rect.x + 5, layout.generate_rect.y + 5) == ("generate",)
    collapsed = cl.pill_placement(1600, 900, expanded=False)
    assert collapsed.hit(collapsed.pill_rect.x + 5, collapsed.pill_rect.y + 5) == ("expand",)
    assert collapsed.resize_rect is None


def _controls(layout):
    rects = [layout.card_rect, layout.prompt_rect, layout.model_rect, layout.generate_rect]
    rects += [layout.collapse_rect, layout.resize_rect, *layout.tab_rects.values()]
    return rects + ([layout.settings_rect] if layout.settings_rect is not None else [])


# a 1600 px viewport with a 56 px toolbar on the left and a 300 px sidebar on the right
INSETS = (56.0, 300.0)
SIDEBAR_X = 1600 - 300


def test_side_regions_centre_the_composer_in_the_uncovered_span():
    expanded = cl.pill_placement(1600, 900, expanded=True, insets=INSETS)
    card = expanded.card_rect
    assert expanded.insets == INSETS
    assert card.w == cl.CARD_WIDTH
    assert abs((card.x + card.w / 2) - (56 + (SIDEBAR_X - 56) / 2)) < 1e-6
    for rect in _controls(expanded):
        assert rect.x >= 56 + cl.MARGIN and rect.right <= SIDEBAR_X - cl.MARGIN
    g, c = expanded.generate_rect, expanded.collapse_rect
    assert expanded.hit(*_center(g)) == ("generate",)
    assert expanded.hit(*_center(c)) == ("collapse",)
    assert expanded.hit(SIDEBAR_X + 10, g.y + 1) is None
    assert expanded.offset() == (0.0, 0.0)
    pill = cl.pill_placement(1600, 900, expanded=False, insets=INSETS)
    assert abs((pill.pill_rect.x + pill.pill_rect.w / 2) - (card.x + card.w / 2)) < 1e-6
    assert pill.hit(*_center(pill.pill_rect)) == ("expand",)


def test_default_card_narrows_instead_of_running_under_the_sidebar():
    # a viewport where the centred default card would reach 110 px under a 300 px sidebar
    plain = cl.pill_placement(1200, 900, expanded=True)
    assert plain.card_rect.right > 1200 - 300
    fitted = cl.pill_placement(1200, 900, expanded=True, insets=(56, 300))
    span = 1200 - 56 - 300
    assert fitted.card_rect.w == span - 2 * cl.MARGIN
    assert fitted.card_rect.x == 56 + cl.MARGIN
    assert fitted.card_rect.right == 1200 - 300 - cl.MARGIN
    for kind in ("generate", "collapse"):
        rect = getattr(fitted, f"{kind}_rect")
        assert rect.right < 1200 - 300 and fitted.hit(*_center(rect)) == (kind,)


def test_saved_width_and_offset_are_clamped_to_the_uncovered_span():
    span = SIDEBAR_X - 56
    wide = cl.pill_placement(1600, 900, expanded=True, width=5000, insets=INSETS)
    assert wide.card_rect.w == span - 2 * cl.MARGIN
    assert cl.clamp_width(5000, 1600, insets=INSETS) == span - 2 * cl.MARGIN
    assert cl.clamp_width(10, 1600, insets=INSETS) == cl.MIN_CARD_WIDTH
    # a side region is a hard edge: the card never slides under the sidebar or the toolbar
    right = cl.pill_placement(1600, 900, expanded=True, offset=(5000.0, 0.0), insets=INSETS)
    assert right.card_rect.right == SIDEBAR_X
    assert right.generate_rect.right < SIDEBAR_X and right.collapse_rect.right < SIDEBAR_X
    left = cl.pill_placement(1600, 900, expanded=True, offset=(-5000.0, 0.0), insets=INSETS)
    assert left.card_rect.x == 56
    pill = cl.pill_placement(1600, 900, expanded=False, offset=(5000.0, 0.0), insets=INSETS)
    assert pill.pill_rect.right == SIDEBAR_X
    # a bare region edge keeps the existing rule: MIN_VISIBLE px stay inside the region
    bare = cl.pill_placement(1600, 900, expanded=True, offset=(-5000.0, 0.0), insets=(0, 300))
    assert bare.card_rect.x == cl.MIN_VISIBLE - bare.card_rect.w
    # an in-span offset moves the card from the span centre, the vertical clamp is unchanged
    moved = cl.pill_placement(1600, 900, expanded=True, offset=(120.0, 300.0), insets=INSETS)
    base = cl.pill_placement(1600, 900, expanded=True, insets=INSETS)
    assert moved.card_rect.x == base.card_rect.x + 120.0
    assert moved.card_rect.y == base.card_rect.y + 300.0


def test_layout_offset_reproduces_the_clamped_placement():
    for insets in ((0.0, 0.0), INSETS):
        for expanded in (True, False):
            clamped = cl.pill_placement(
                1600, 900, expanded=expanded, offset=(5000.0, -5000.0), insets=insets
            )
            again = cl.pill_placement(
                1600, 900, expanded=expanded, offset=clamped.offset(), insets=insets
            )
            assert again.pill_rect == clamped.pill_rect
    plain = cl.pill_placement(1600, 900, expanded=True, offset=(120.0, 300.0))
    assert plain.offset() == (120.0, 300.0)


def test_drawn_width_and_offset_reproduce_the_placement():
    # a drag release stores the drawn width and offset; laying them out again changes nothing,
    # including a span too small for the card (the pill stands in), below the pill floor and a
    # region too short for the card
    cases = (
        (1600, 900, INSETS),
        (1600, 900, (0.0, 0.0)),
        (900, 900, (56, 400)),
        (700, 900, (56, 400)),
        (600, 900, (56, 400)),
        (1600, 150, INSETS),
    )
    for region_w, region_h, insets in cases:
        for width in (None, 10, 900, 5000):
            for offset in ((0.0, 0.0), (5000.0, -5000.0), (-5000.0, 300.0)):
                drawn = cl.pill_placement(
                    region_w, region_h, expanded=True, offset=offset, width=width, insets=insets
                )
                again = cl.pill_placement(
                    region_w,
                    region_h,
                    expanded=True,
                    offset=drawn.offset(),
                    width=drawn.pill_rect.w,
                    insets=insets,
                )
                assert again == drawn, (region_w, region_h, insets, width, offset)


def test_the_card_needs_its_minimum_width_and_margins():
    for scale in (1.0, 2.0, 4.0):
        need = (cl.MIN_CARD_WIDTH + 2 * cl.MARGIN) * scale
        insets = (56 * scale, 300 * scale)
        room = insets[0] + insets[1] + need
        assert cl.card_fits(room, 900 * scale, scale, insets)
        assert not cl.card_fits(room - 1, 900 * scale, scale, insets)
        fits = cl.pill_placement(room, 900 * scale, expanded=True, scale=scale, insets=insets)
        assert fits.expanded and fits.card_fits
        assert fits.card_rect.w == cl.MIN_CARD_WIDTH * scale
        assert fits.card_rect.x == insets[0] + cl.MARGIN * scale  # the margins stay
        short = cl.pill_placement(room - 1, 900 * scale, expanded=True, scale=scale, insets=insets)
        assert not short.expanded and not short.card_fits and short.card_rect is None
    # unusable insets are ignored here too: the whole region counts
    assert cl.card_fits(1600, 900, 1.0, (900, 900))


def test_the_card_needs_its_height_and_margins():
    for scale in (1.0, 2.0, 4.0):
        need = (cl.CARD_HEIGHT + 2 * cl.MARGIN) * scale
        region_w = 1800 * scale  # wide enough for the default card
        assert cl.card_fits(region_w, need, scale)
        assert not cl.card_fits(region_w, need - 1, scale)
        fits = cl.pill_placement(region_w, need, expanded=True, scale=scale)
        assert fits.expanded and fits.card_fits
        card = fits.card_rect
        assert card.h == cl.CARD_HEIGHT * scale and card.y == cl.MARGIN * scale  # the margins stay
        assert card.top == need - cl.MARGIN * scale
        # the rows stack without overlapping: tabs over the prompt over the model row
        tab = fits.tab_rects["image"]
        assert tab.y >= fits.prompt_rect.top and tab.top <= card.top
        for row in (fits.model_rect, fits.generate_rect):
            assert fits.prompt_rect.y >= row.top and row.y >= card.y
        # one pixel shorter: the pill, whatever the saved card width
        for width in (None, cl.MIN_CARD_WIDTH * scale):
            short = cl.pill_placement(region_w, need - 1, expanded=True, scale=scale, width=width)
            collapsed = cl.pill_placement(region_w, need - 1, expanded=False, scale=scale)
            assert not short.expanded and not short.card_fits and short.card_rect is None
            assert short.pill_rect == collapsed.pill_rect
            assert short.hit(*_center(short.pill_rect)) == ("form",)
            assert collapsed.hit(*_center(collapsed.pill_rect)) == ("form",)
    # both conditions hold together: a tall region does not rescue a span too narrow for the card
    assert not cl.card_fits(cl.MIN_CARD_WIDTH + 2 * cl.MARGIN - 1, 5000, 1.0)


# the physical desktop case: Retina at a Preferences resolution scale of 2 (custom-interface UI
# scale 4), a 226 px toolbar and a 1122 px sidebar over a 2477 px viewport: about 1129 px stay
# uncovered
RETINA = {"region_w": 2477, "scale": 4.0, "insets": (226.0, 1122.0)}
RETINA_SIDEBAR_X = 2477 - 1122


def test_a_span_narrower_than_the_card_shows_the_pill_instead():
    span = RETINA["region_w"] - sum(RETINA["insets"])
    assert span < cl.MIN_CARD_WIDTH * RETINA["scale"]
    for width in (None, 1680, 5000):
        shown = cl.pill_placement(expanded=True, region_h=1600, width=width, **RETINA)
        collapsed = cl.pill_placement(expanded=False, region_h=1600, **RETINA)
        # the collapsed pill's geometry, whatever the saved card width
        assert not shown.expanded and not shown.card_fits
        assert shown.pill_rect == collapsed.pill_rect and shown.base == collapsed.base
        assert shown.card_rect is None and shown.tab_rects == {} and shown.resize_rect is None
        pill = shown.pill_rect
        assert (
            pill.w == span - 2 * cl.MARGIN * 4
        )  # the default pill, shrunk to the span minus margins
        assert pill.x == 226 + cl.MARGIN * 4 and pill.right == RETINA_SIDEBAR_X - cl.MARGIN * 4
        # a click on it opens the lane's form instead of expanding, collapsed or not
        assert shown.hit(*_center(pill)) == ("form",)
        assert collapsed.hit(*_center(pill)) == ("form",)
        assert shown.hit(RETINA_SIDEBAR_X + 10, pill.y + 1) is None
    # with the sidebar closed the same viewport holds the card again
    closed = cl.pill_placement(
        RETINA["region_w"], 1600, expanded=True, scale=4.0, width=1680, insets=(226.0, 0.0)
    )
    assert closed.expanded and closed.card_fits and closed.card_rect.w == 1680
    pill = cl.pill_placement(
        RETINA["region_w"], 1600, expanded=False, scale=4.0, insets=(226.0, 0.0)
    )
    assert pill.hit(*_center(pill.pill_rect)) == ("expand",)


def test_the_pill_standing_in_for_the_card_moves_and_clamps_like_the_pill():
    # a saved offset past the sidebar edge stops there, and the drawn offset reproduces the placement
    for offset in ((5000.0, 300.0), (-5000.0, -5000.0), (120.0, 40.0)):
        shown = cl.pill_placement(expanded=True, region_h=1600, offset=offset, **RETINA)
        assert shown.pill_rect.x >= 226 and shown.pill_rect.right <= RETINA_SIDEBAR_X
        again = cl.pill_placement(expanded=True, region_h=1600, offset=shown.offset(), **RETINA)
        assert again == shown
        collapsed = cl.pill_placement(expanded=False, region_h=1600, offset=offset, **RETINA)
        assert collapsed.pill_rect == shown.pill_rect


def test_a_span_narrower_than_the_pill_keeps_the_pill_floor():
    # room for neither the card nor the pill minimum: the pill keeps that floor from the toolbar edge
    floor = cl.pill_placement(2477, 1600, expanded=True, scale=4.0, insets=(226.0, 1700.0))
    assert not floor.expanded and floor.hit(*_center(floor.pill_rect)) == ("form",)
    assert floor.pill_rect.w == cl.MIN_PILL_WIDTH * 4 and floor.pill_rect.x == 226
    # without an overlapping toolbar it ends at the sidebar edge instead
    bare = cl.pill_placement(2477, 1600, expanded=True, scale=4.0, insets=(0.0, 1900.0))
    assert bare.pill_rect.w == cl.MIN_PILL_WIDTH * 4 and bare.pill_rect.right == 2477 - 1900
    # between the pill minimum and the card minimum the pill narrows to its minimum with its margins kept,
    # then a narrower span eats into the margins
    tight = cl.pill_placement(900, 400, expanded=True, insets=(56, 400))
    assert not tight.expanded and tight.pill_rect.w == cl.PILL_WIDTH
    kept = cl.pill_placement(800, 400, expanded=True, insets=(56, 400))  # a 344 px span
    assert kept.pill_rect.w == 344 - 2 * cl.MARGIN
    assert kept.pill_rect.x == 56 + cl.MARGIN and kept.pill_rect.right == 800 - 400 - cl.MARGIN
    narrow = cl.pill_placement(700, 400, expanded=True, insets=(56, 400))  # a 244 px span
    assert narrow.pill_rect.w == cl.MIN_PILL_WIDTH
    assert narrow.pill_rect.x >= 56 and narrow.pill_rect.right <= 700 - 400
    assert narrow.pill_rect.x - 56 < cl.MARGIN  # the margins give way before the minimum width


def test_unusable_insets_are_ignored():
    covered = cl.pill_placement(1600, 900, expanded=True, insets=(900, 900))
    plain = cl.pill_placement(1600, 900, expanded=True)
    assert covered.card_rect == plain.card_rect and covered.insets == (0.0, 0.0)
    negative = cl.pill_placement(1600, 900, expanded=True, insets=(-50, None))
    assert negative.card_rect == plain.card_rect


def _per_char(px):
    """A font metric: every character, the ellipsis included, is `px` wide."""
    return lambda text: px * len(text)


def test_short_lane_labels_are_distinct_and_none_starts_another():
    shorts = [cl.LANE_SHORT_LABELS[lane] for lane in cl.LANE_ORDER]
    assert len(set(shorts)) == len(cl.LANE_ORDER)
    for short in shorts:
        assert short and cl.ELLIPSIS not in short
        assert not any(other != short and other.startswith(short) for other in shorts)
    for lane in cl.LANE_ORDER:
        assert len(cl.LANE_SHORT_LABELS[lane]) <= len(cl.LANE_LABELS[lane])


def test_tab_label_keeps_the_full_label_when_it_fits():
    measure = _per_char(6.0)
    for lane in cl.LANE_ORDER:
        assert cl.tab_label(lane, 200, measure) == cl.LANE_LABELS[lane]
    # exactly as wide as the box still fits
    assert cl.tab_label("render_image", 6.0 * len("Render Image"), measure) == "Render Image"


def test_tab_label_switches_to_the_short_label_tab_by_tab():
    labels = {lane: cl.tab_label(lane, 40, _per_char(6.0)) for lane in cl.LANE_ORDER}
    assert labels == {
        "image": "Image",
        "video": "Video",
        "3d": "3D",
        "material": "Mat",
        "render_image": "R-Img",
        "render_video": "R-Vid",
    }
    # Render Image and Render Video never share a label once shortened
    assert labels["render_image"] != labels["render_video"]


def test_tab_label_clips_the_short_label_only_as_a_last_resort_and_never_to_nothing():
    measure = _per_char(6.0)
    assert cl.tab_label("render_image", 29, measure) == "R-I…"
    assert cl.tab_label("render_image", 13, measure) == "R…"
    assert cl.tab_label("material", 13, measure) == "M…"
    for lane in cl.LANE_ORDER:
        for room in (0, -10, 5):
            label = cl.tab_label(lane, room, measure)
            assert label and label[0] == cl.LANE_SHORT_LABELS[lane][0]
    # a two-character label is not swapped for an equally wide clipped one
    assert cl.tab_label("3d", 0, measure) == "3D"


def test_clip_label_measures_with_the_injected_metric():
    widths = {"R-Img": 39.0, "R-Im…": 36.0, "R-I…": 30.0, "R-…": 25.0, "R…": 18.0}
    measure = widths.__getitem__
    assert cl.clip_label("R-Img", 39, measure) == "R-Img"
    assert cl.clip_label("R-Img", 30, measure) == "R-I…"
    assert cl.clip_label("R-Img", 20, measure) == "R…"
    assert cl.clip_label("R-Img", 1, measure) == "R…"  # the narrowest, never empty
    assert cl.clip_label("", 0, _per_char(6.0)) == ""


def test_every_tab_reads_at_the_minimum_card_width_on_every_scale():
    # glyphs about 0.65 em wide: Blender's UI font at 12 px measures R-Img at 39 px
    for scale in (1.0, 2.0, 4.0):
        font_px = 12 * scale
        measure = _per_char(0.65 * font_px)
        insets = (56 * scale, 300 * scale)
        region_w = insets[0] + insets[1] + (cl.MIN_CARD_WIDTH + 2 * cl.MARGIN) * scale
        layout = cl.pill_placement(region_w, 900, expanded=True, scale=scale, insets=insets)
        assert layout.card_rect.w == cl.MIN_CARD_WIDTH * scale
        labels = layout.tab_labels(measure)
        assert list(labels) == list(cl.LANE_ORDER)
        assert labels["render_image"] == "R-Img" and labels["render_video"] == "R-Vid"
        assert len(set(labels.values())) == len(cl.LANE_ORDER)
        for lane, label in labels.items():
            room = layout.tab_rects[lane].w - cl.CHIP_TEXT_INSET * scale
            assert label and cl.ELLIPSIS not in label and measure(label) <= room
        # the default card shows every full label
        wide = cl.pill_placement(1800 * scale, 900, expanded=True, scale=scale)
        assert wide.tab_labels(measure) == cl.LANE_LABELS
    # a pill has no tabs to label
    assert cl.pill_placement(1600, 900, expanded=False).tab_labels(_per_char(6.0)) == {}
