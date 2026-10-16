# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
import math

import pytest

from scenario.core.scene import placement


def test_bottom_center_offset_moves_bbox_bottom_to_target():
    dx, dy, dz = placement.bottom_center_offset((-1, -2, 0.5), (3, 2, 4.5), (10, 20, 30))
    assert (dx, dy, dz) == (9.0, 20.0, 29.5)


def test_target_size_accepts_metres_in_range_and_none():
    assert placement.target_size(None) is None
    assert placement.target_size(1) == 1.0 and isinstance(placement.target_size(1), float)
    assert placement.target_size(placement.MIN_TARGET_SIZE_M) == 0.01
    assert placement.target_size(placement.MAX_TARGET_SIZE_M) == 1000.0


@pytest.mark.parametrize(
    "value", [0, -1, 0.009, 1000.5, math.inf, -math.inf, math.nan, True, "1.0", [1.0]]
)
def test_target_size_refuses_values_outside_the_range(value):
    with pytest.raises(ValueError, match="target_size_m must be a number of metres"):
        placement.target_size(value)


def test_fit_scale_sizes_the_longest_side():
    assert placement.fit_scale((0, 0, 0), (1, 0.5, 1.9), None) == 1.0
    assert math.isclose(placement.fit_scale((0, 0, 0), (1, 0.5, 1.9), 1.16), 1.16 / 1.9)
    # A flat model scales by its longest side too.
    assert placement.fit_scale((2, 0, 0), (3, 0, 1), 0.5) == 0.5
    with pytest.raises(ValueError, match="no measurable size"):
        placement.fit_scale((1, 1, 1), (1, 1, 1), 1.0)


def test_importer_for_extension():
    assert placement.importer_for("a.glb") == "gltf" and placement.importer_for("b.GLTF") == "gltf"
    assert placement.importer_for("c.fbx") == "fbx" and placement.importer_for("d.obj") == "obj"
    assert placement.importer_for("e.vox") is None
