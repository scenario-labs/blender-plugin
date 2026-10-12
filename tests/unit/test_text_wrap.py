# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Word wrapping by measured width, as panel status labels use it."""

from pathlib import Path

import pytest

import scenario
from scenario.core.ui.text_wrap import NO_BREAK, wrap

# A proportional stand-in for a font: narrow and wide glyphs differ, so a
# character count cannot predict where a line ends.
WIDTHS = {"i": 2, "l": 2, ".": 2, " ": 3, NO_BREAK: 3, "·": 3, "M": 10, "W": 10}


def measure(text):
    return sum(WIDTHS.get(character, 6) for character in text)


def test_lines_fill_the_measured_width_and_break_only_at_ordinary_spaces():
    status = f"Verified saved audio{NO_BREAK}· 1.00{NO_BREAK}s{NO_BREAK}· Stereo{NO_BREAK}· 44.1{NO_BREAK}kHz"
    lines = wrap(status, 160, measure)
    assert lines == [
        f"Verified saved audio{NO_BREAK}· 1.00{NO_BREAK}s{NO_BREAK}·",
        f"Stereo{NO_BREAK}· 44.1{NO_BREAK}kHz",
    ]
    assert " ".join(lines) == status
    assert all(measure(line) <= 160 for line in lines)
    # Greedy: the next word would not have fit on the first line.
    assert measure(f"{lines[0]} {lines[1].split(' ')[0]}") > 160


@pytest.mark.parametrize("width", [48, 61, 97, 160, 400])
def test_every_line_fits_and_the_text_survives(width):
    text = "Decoding the verified saved audio in an offline Blender process..."
    lines = wrap(text, width, measure)
    assert all(measure(line) <= width for line in lines)
    assert " ".join(lines) == text
    for line, following in zip(lines, lines[1:], strict=False):
        assert measure(f"{line} {following.split(' ')[0]}") > width


def test_narrow_glyphs_fit_more_characters_than_wide_ones():
    assert wrap("ill lil ill lil", 36, measure) == ["ill lil ill lil"]
    assert wrap("MWM WMW MWM WMW", 36, measure) == ["MWM", "WMW", "MWM", "WMW"]


def test_a_word_wider_than_the_line_splits_between_characters():
    assert wrap("abcdefgh ij", 18, measure) == ["abc", "def", "gh", "ij"]
    assert wrap("abcdefgh", 1, measure) == ["a", "b", "c", "d", "e", "f", "g", "h"]


def test_a_hyphen_never_breaks_a_word_that_fits_a_line():
    # textwrap would also break after the hyphen: "please re-" / "run it".
    assert measure("please re-") <= 60
    assert wrap("please re-run it", 60, measure) == ["please", "re-run it"]


def test_a_word_wider_than_the_line_splits_after_its_last_hyphen_that_fits():
    # As textwrap splits a long word; "model-final-v" alone would also fit.
    assert measure("model-final-v") <= 70
    assert wrap("model-final-v2.glb", 70, measure) == ["model-final-", "v2.glb"]
    # A prefix of hyphens alone is no break point.
    assert wrap("---abcdefgh", 36, measure) == ["---abc", "defgh"]


def test_sources_spell_the_no_break_space_as_an_escape():
    # A literal U+00A0 reads as an ordinary space, and an editor can turn it
    # into one without anyone noticing.
    assert NO_BREAK == "\u00a0"
    package = Path(scenario.__file__).parent
    literal = [
        path.relative_to(package).as_posix()
        for path in sorted(package.rglob("*.py"))
        if NO_BREAK in path.read_text(encoding="utf-8")
    ]
    assert literal == []


def test_ascii_whitespace_runs_collapse_and_empty_text_has_no_lines():
    assert wrap("a  b\tc\nd", 100, measure) == ["a b c d"]
    assert wrap("", 100, measure) == []
    assert wrap("   ", 100, measure) == []
