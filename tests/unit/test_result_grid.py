# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""The Results grid: pages without overlap, tile geometry and a selected result's facts."""

from datetime import UTC, timedelta, timezone

import pytest

from scenario.core.ui import result_grid
from scenario.core.ui.result_grid import GridPage

ROWS = tuple(f"result-{index}" for index in range(14))


def test_one_page_of_results_needs_no_pager():
    for count in (0, 1, 12):
        rows = ROWS[:count]
        assert result_grid.page(count, 0) is None
        assert result_grid.visible(rows, 0) == rows


def test_pages_split_the_results_without_overlap():
    assert result_grid.page(14, 0) == GridPage(0, 1, 12, 14)
    assert result_grid.visible(ROWS, 0) == ROWS[:12]
    # Unlike a job's preview tiles, the last page is short instead of repeating results.
    assert result_grid.page(14, 1) == GridPage(1, 13, 14, 14)
    assert result_grid.visible(ROWS, 1) == ROWS[12:]
    assert result_grid.page(24, 1) == GridPage(1, 13, 24, 24)
    assert result_grid.page(25, 2) == GridPage(2, 25, 25, 25)


def test_page_label_and_pager_availability():
    first, last = result_grid.page(14, 0), result_grid.page(14, 1)
    # A hyphen-minus, as the UI style's range labels use.
    assert (first.label, last.label) == ("1-12 of 14", "13-14 of 14")
    assert (first.previous, first.next) == (False, True)
    assert (last.previous, last.next) == (True, False)
    middle = result_grid.page(40, 1)
    assert (middle.label, middle.previous, middle.next) == ("13-24 of 40", True, True)


def test_a_page_that_no_longer_exists_is_drawn_as_the_nearest_one():
    # Fewer results, such as after a connection change: the last page that exists.
    assert result_grid.clamp(5, 14) == 1
    assert result_grid.page(14, 5) == GridPage(1, 13, 14, 14)
    assert result_grid.visible(ROWS, 5) == ROWS[12:]
    assert [result_grid.clamp(index, 30) for index in (-1, 0, 1, 2, 3)] == [0, 0, 1, 2, 2]
    assert result_grid.clamp(3, 0) == 0
    assert result_grid.visible((), 3) == ()
    for index in (None, 1.0, True, "1"):
        assert result_grid.clamp(index, 30) == 0


def test_steps_move_one_page_and_stop_at_either_end():
    assert result_grid.step(0, 30, 1) == 1
    assert result_grid.step(1, 30, 1) == 2
    assert result_grid.step(2, 30, 1) == 2
    assert result_grid.step(2, 30, -1) == 1
    assert result_grid.step(0, 30, -1) == 0
    # A page beyond the results steps back from the last one that exists.
    assert result_grid.step(9, 30, -1) == 1
    assert result_grid.step(0, 12, 1) == 0
    for direction in (0, 2, -2, True, 1.0, None):
        with pytest.raises(ValueError, match="previous or next"):
            result_grid.step(0, 30, direction)


def test_a_result_returns_to_the_page_that_holds_it():
    assert [result_grid.page_of(position) for position in (0, 11, 12, 23, 24)] == [0, 0, 1, 1, 2]
    assert result_grid.page_of(-1) == 0


def test_neighbors_follow_the_drawn_order_and_stop_at_either_end():
    assert result_grid.neighbors(ROWS, "result-0") == (None, "result-1")
    assert result_grid.neighbors(ROWS, "result-5") == ("result-4", "result-6")
    assert result_grid.neighbors(ROWS, "result-13") == ("result-12", None)
    assert result_grid.neighbors(("only",), "only") == (None, None)
    assert result_grid.neighbors(ROWS, "gone") == (None, None)
    assert result_grid.neighbors(iter(ROWS[:2]), "result-1") == ("result-0", None)


def test_tiles_aim_at_eighty_units_between_two_and_six_columns():
    # Studio's widest popup: six columns of large icons.
    columns, scale = result_grid.tile_layout(950)
    assert columns == 6
    assert scale == pytest.approx(min(8.0, (950 - 5 * 8) / 6 / 20))
    # The default sidebar: two columns, each tile its share of the row.
    assert result_grid.tile_layout(170) == (2, pytest.approx((170 - 8) / 2 / 20))
    assert result_grid.tile_layout(264)[0] == 3
    assert result_grid.tile_layout(352)[0] == 4
    # A narrow region keeps two columns, at the smallest icons.
    assert result_grid.tile_layout(60) == (2, 2.5)
    assert result_grid.tile_layout(-20) == (2, 2.5)
    # A very wide one keeps six columns, at the largest icons.
    assert result_grid.tile_layout(4000) == (6, 8.0)


def test_tiles_fit_their_columns():
    for width in range(120, 1200, 7):
        columns, scale = result_grid.tile_layout(width)
        # Each tile's image fits its share of the row, beside the spacing.
        if scale > result_grid.TILE_MIN_SCALE:
            assert columns * scale * 20 + (columns - 1) * 8 <= width + 1e-9


def test_the_selected_preview_grows_with_the_width_up_to_the_still_size():
    assert result_grid.detail_scale(160) == 8.0
    assert result_grid.detail_scale(940) == 12.0
    assert result_grid.detail_scale(40) == 4.0


def test_sizes_read_in_binary_units():
    assert result_grid.size_label(0) == "0 bytes"
    assert result_grid.size_label(1) == "1 byte"
    assert result_grid.size_label(1023) == "1023 bytes"
    assert result_grid.size_label(1536) == "1.5 KiB"
    assert result_grid.size_label(2_500_000) == "2.4 MiB"
    # Rounded before choosing the unit, never "1024.0 KiB".
    assert result_grid.size_label(1024**2 - 1) == "1.0 MiB"
    assert result_grid.size_label(3 * 1024**3) == "3.0 GiB"
    assert result_grid.size_label(5 * 1024**4) == "5.0 TiB"
    for size in (None, -1, 1.5, True, "12"):
        assert result_grid.size_label(size) == ""


def test_summary_names_the_kind_the_saved_size_and_the_result_count():
    assert result_grid.summary("image", 2_500_000, 1) == "Image, 2.4 MiB"
    assert result_grid.summary("material", 1536, 6) == "Material, 1.5 KiB, 6 results"
    assert result_grid.summary("3d", None, 2) == "3D model, 2 results"
    assert result_grid.summary("model", None, 0) == "Result"
    assert result_grid.summary("video", None, None) == "Video"


def test_the_submission_time_prefers_the_saved_claim_and_reads_in_local_time():
    assert result_grid.submitted_label("2026-10-22T13:04:05.123Z", 0.0, UTC) == "2026-10-22 13:04"
    paris = timezone(timedelta(hours=2))
    assert result_grid.submitted_label("2026-10-22T13:04:05.123Z", 0.0, paris) == (
        "2026-10-22 15:04"
    )
    # The saved claim wins over the session row's own time.
    assert result_grid.submitted_label("2026-10-22T13:04:05.123Z", 1.0, UTC) == "2026-10-22 13:04"
    # A row without a claim falls back to when this session made it.
    assert result_grid.submitted_label(None, 1_800_000_000.0, UTC) == "2027-01-15 08:00"
    assert result_grid.submitted_label(None, 1_800_000_000, UTC) == "2027-01-15 08:00"


def test_an_unknown_submission_time_draws_nothing():
    for claimed, created in (
        (None, 0.0),
        (None, -5.0),
        ("not a time", 0.0),
        ("2026-10-22T13:04:05", 0.0),  # no time zone
        (None, float("inf")),
        (None, float("nan")),
        (None, True),
        (None, "1800000000"),
    ):
        assert result_grid.submitted_label(claimed, created, UTC) == ""
