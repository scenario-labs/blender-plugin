# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Humanoid skeleton families that returned motion is retargeted between."""

import pytest

from scenario.core.scene import humanoid


def skeleton(family, prefix="", extra=()):
    """Parent names for one family's bones: a spine chain, limbs under it, extra bones."""
    names = dict(zip(humanoid.SLOTS, humanoid.FAMILIES[family][1], strict=True))
    parents = {}
    for slot, name in names.items():
        up = humanoid.PARENTS.get(slot)
        parents[prefix + name] = prefix + names[up] if up else None
    for name, parent in extra:
        parents[prefix + name] = prefix + parent
    return parents


@pytest.mark.parametrize("family", sorted(humanoid.FAMILIES))
def test_each_family_maps_all_slots_to_its_bones(family):
    found, mapping = humanoid.detect(skeleton(family))
    assert found == family
    assert list(mapping) == list(humanoid.SLOTS)
    assert mapping["hips"] == humanoid.FAMILIES[family][1][0]


def test_a_namespace_prefix_and_extra_bones_are_accepted():
    parents = skeleton("mixamo", "mixamorig:", extra=(("LeftHandIndex1", "LeftHand"),))
    found, mapping = humanoid.detect(parents)
    assert (found, mapping["l_hand"]) == ("mixamo", "mixamorig:LeftHand")
    assert humanoid.label(found) == "Mixamo"


def test_a_missing_bone_or_a_broken_hierarchy_is_not_a_humanoid():
    parents = skeleton("meshy")
    del parents["LeftToeBase"]
    assert humanoid.detect(parents) is None
    parents = skeleton("meshy")
    # A shin under the other thigh is not the leg the slot expects.
    parents["LeftLeg"] = "RightUpLeg"
    assert humanoid.detect(parents) is None
    assert humanoid.detect({"Hips": None, "Spine": "Hips", "Head": "Spine"}) is None


def test_two_bones_with_one_name_under_different_prefixes_are_ambiguous():
    parents = skeleton("mixamo", "a:")
    parents.update(skeleton("mixamo", "b:"))
    assert humanoid.detect(parents) is None


def test_every_slot_points_at_a_child_or_like_its_parent():
    for slot in humanoid.SLOTS:
        pointer = humanoid.CHILDREN.get(slot) or humanoid.CHILDREN[humanoid.LEAVES[slot]]
        assert pointer in humanoid.SLOTS
    assert set(humanoid.PARENTS) == set(humanoid.SLOTS) - {"hips"}
