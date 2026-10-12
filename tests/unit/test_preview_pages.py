# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Paging a saved job's preview tiles: offsets, clamping, reset and the range label."""

import pytest

from scenario.core.ui import preview_pages
from scenario.core.ui.preview_pages import Page, PageOffsets

SIX = ("albedo", "normal", "height", "metallic", "ao", "edge")


def test_four_or_fewer_results_need_no_page():
    for count in range(5):
        results = SIX[:count]
        assert preview_pages.page(results, 0) is None
        assert preview_pages.visible(results, 0) == results


def test_pages_step_by_four_and_the_last_page_stays_full():
    assert preview_pages.page(SIX, 0) == Page(0, 1, 4, 6)
    assert preview_pages.visible(SIX, 0) == SIX[:4]
    # The next page ends at the last result instead of showing a short page.
    assert preview_pages.step(0, len(SIX), 1) == 2
    assert preview_pages.page(SIX, 2) == Page(2, 3, 6, 6)
    assert preview_pages.visible(SIX, 2) == SIX[2:]
    assert preview_pages.step(2, len(SIX), -1) == 0
    nine = tuple(f"result-{index}" for index in range(9))
    assert [preview_pages.step(offset, 9, 1) for offset in (0, 4, 5)] == [4, 5, 5]
    assert [preview_pages.step(offset, 9, -1) for offset in (5, 4, 1, 0)] == [1, 0, 0, 0]
    assert preview_pages.visible(nine, 5) == nine[5:]


def test_offsets_clamp_to_the_results():
    assert [preview_pages.clamp(offset, 6) for offset in (-3, 0, 1, 2, 3, 99)] == [
        0,
        0,
        1,
        2,
        2,
        2,
    ]
    assert preview_pages.clamp(3, 4) == 0
    assert preview_pages.clamp(3, 0) == 0
    assert preview_pages.visible(SIX, 99) == SIX[2:]


def test_page_label_and_arrow_availability():
    first, last = preview_pages.page(SIX, 0), preview_pages.page(SIX, 2)
    # A hyphen-minus, as the UI style's range labels use.
    assert (first.label, last.label) == ("1-4 of 6", "3-6 of 6")
    assert (first.previous, first.next) == (False, True)
    assert (last.previous, last.next) == (True, False)
    middle = preview_pages.page(tuple(range(12)), 4)
    assert (middle.label, middle.previous, middle.next) == ("5-8 of 12", True, True)


def test_steps_must_be_one_page_back_or_forward():
    for direction in (0, 2, -2, True, 1.0, None):
        with pytest.raises(ValueError, match="previous or next"):
            preview_pages.step(0, 6, direction)


def test_offsets_are_per_job_and_reset_when_its_results_change():
    offsets = PageOffsets()
    assert offsets.offset("job", SIX) == 0
    assert offsets.move("job", SIX, 1) == 2
    assert offsets.move("job", SIX, 1) == 2  # Clamped at the last page.
    assert offsets.offset("job", SIX) == 2
    assert offsets.offset("other", SIX) == 0
    # A changed result set starts again at the first page.
    changed = SIX[:5]
    assert offsets.offset("job", changed) == 0
    assert offsets.move("job", changed, 1) == 1
    assert offsets.offset("job", SIX) == 0
    assert offsets.move("job", SIX, -1) == 0
    assert offsets.offset("job", SIX) == 0


def test_pruning_drops_offsets_of_jobs_no_longer_shown_or_changed():
    offsets = PageOffsets()
    offsets.move("kept", SIX, 1)
    offsets.move("changed", SIX, 1)
    offsets.move("gone", SIX, 1)
    offsets.prune({"kept": SIX, "changed": SIX[1:]})
    assert offsets.offset("kept", SIX) == 2
    assert offsets.offset("changed", SIX) == 0
    assert offsets.offset("gone", SIX) == 0
    assert dict(offsets.items()) == {"kept": 2}
    offsets.clear()
    assert dict(offsets.items()) == {}
