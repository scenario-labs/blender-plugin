# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Shared harness plumbing that runs with or without Atheris.

Each harness reads its mode from the first input byte, so a seed selects the same
path under Atheris and under pytest. The rest of the input feeds a data provider:
``atheris.FuzzedDataProvider`` when fuzzing, ``DataProvider`` otherwise. Both are
deterministic functions of the input; they need not consume bytes the same way.
"""

import struct


class DataProvider:
    """Pure-Python stand-in for the ``atheris.FuzzedDataProvider`` methods harnesses use."""

    def __init__(self, data):
        self._data = bytes(data)
        self._offset = 0

    def remaining_bytes(self):
        return len(self._data) - self._offset

    def ConsumeBytes(self, count):
        count = max(0, min(count, self.remaining_bytes()))
        value = self._data[self._offset : self._offset + count]
        self._offset += count
        return value

    def ConsumeIntInRange(self, low, high):
        span = high - low
        if span <= 0:
            return low
        raw = int.from_bytes(self.ConsumeBytes((span.bit_length() + 7) // 8), "little")
        return low + raw % (span + 1)

    def ConsumeBool(self):
        return bool(self.ConsumeIntInRange(0, 1))

    def ConsumeFloat(self):
        return struct.unpack("<d", self.ConsumeBytes(8).ljust(8, b"\0"))[0]

    def PickValueInList(self, values):
        return values[self.ConsumeIntInRange(0, len(values) - 1)]

    def ConsumeUnicodeNoSurrogates(self, count):
        width = self.ConsumeIntInRange(0, 2)
        if width == 0:
            return "".join(chr(byte & 0x7F) for byte in self.ConsumeBytes(count))
        size = 2 if width == 1 else 4
        raw = self.ConsumeBytes(count * size)
        characters = []
        for index in range(0, len(raw) - size + 1, size):
            point = int.from_bytes(raw[index : index + size], "little") % 0x110000
            characters.append(chr(point - 0x800 if 0xD800 <= point <= 0xDFFF else point))
        return "".join(characters)


def split(data):
    """The harness mode from the first byte, and the rest of the input."""
    return (data[0], data[1:]) if data else (0, b"")


def mostly(fdp, valid, hostile=(), words=()):
    """Usually a valid choice, sometimes a hostile one or arbitrary JSON.

    Inputs that are valid but for one part reach the checks that a part guards.
    """
    pick = fdp.ConsumeIntInRange(0, 7)
    if pick < 6 or (pick == 6 and not hostile):
        return fdp.PickValueInList(list(valid))
    return fdp.PickValueInList(list(hostile)) if pick == 6 else json_value(fdp, words, 1)


def json_value(fdp, words=(), depth=3):
    """A JSON-shaped value, including the odd types a hostile peer can send."""
    kind = fdp.ConsumeIntInRange(0, 7 if depth > 0 else 5)
    if kind == 0:
        return None
    if kind == 1:
        return fdp.ConsumeBool()
    if kind == 2:
        return fdp.ConsumeIntInRange(-(2**64), 2**64)
    if kind == 3:
        return fdp.ConsumeFloat()
    if kind == 4 or not words:
        return fdp.ConsumeUnicodeNoSurrogates(fdp.ConsumeIntInRange(0, 12))
    if kind == 5:
        return fdp.PickValueInList(list(words))
    if kind == 6:
        return [json_value(fdp, words, depth - 1) for _ in range(fdp.ConsumeIntInRange(0, 4))]
    return {
        str(json_value(fdp, words, 0)): json_value(fdp, words, depth - 1)
        for _ in range(fdp.ConsumeIntInRange(0, 4))
    }
