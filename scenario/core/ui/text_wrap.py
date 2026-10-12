# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Word wrapping by measured width. No bpy.

Blender clips a panel label that is wider than its row, and its interface font
is proportional, so a character count cannot say where a status line must
break. Callers pass the width their font measures for a string. Lines break at
the ASCII whitespace that ``textwrap`` breaks at, so a no-break space keeps a
value with its unit. Unlike ``textwrap``, a word that fits a line is never
broken after a hyphen. A word wider than a whole line is split after its last
hyphen that fits, as ``textwrap`` splits a long word, else after its last
character that fits.
"""

import re

NO_BREAK = "\u00a0"
_SPACES = re.compile(r"[\t\n\x0b\x0c\r ]+")


def wrap(text, width, measure):
    """Lines of ``text`` that each measure at most ``width``, filled greedily.

    ``measure`` returns a string's width in the unit of ``width``.
    """
    lines, line = [], ""
    for word in _SPACES.split(text):
        if not word:
            continue
        joined = f"{line} {word}" if line else word
        if measure(joined) <= width:
            line = joined
            continue
        if line:
            lines.append(line)
        line = word
        while len(line) > 1 and measure(line) > width:
            cut = _prefix(line, width, measure)
            lines.append(line[:cut])
            line = line[cut:]
    if line:
        lines.append(line)
    return lines


def _prefix(word, width, measure):
    """Length of the proper prefix of ``word`` to put on a line ``width`` wide, at least 1.

    The longest prefix that fits, shortened to end at its last hyphen when one
    follows something other than hyphens.
    """
    low, high = 1, len(word) - 1
    while low < high:
        middle = (low + high + 1) // 2
        if measure(word[:middle]) <= width:
            low = middle
        else:
            high = middle - 1
    hyphen = word.rfind("-", 0, low)
    return hyphen + 1 if hyphen > 0 and word[:hyphen].strip("-") else low
