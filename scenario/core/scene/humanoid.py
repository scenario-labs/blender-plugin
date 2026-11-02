# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Humanoid skeletons that a returned motion can be retargeted between. No bpy.

Text-to-motion models return a clip on their own skeleton, not on the user's
rig. Each family below names the bones of one skeleton convention for the same
22 body slots. A rig is recognized as a family when it has every bone the
family names, after any `namespace:` prefix such as Mixamo's `mixamorig:`, and
each slot's bone descends from its parent slot's bone. Other bones, such as
fingers, twist bones and end bones, are allowed and stay unmapped.
"""

SLOTS = (
    "hips",
    "spine",
    "chest",
    "upper_chest",
    "neck",
    "head",
    "l_shoulder",
    "l_arm",
    "l_forearm",
    "l_hand",
    "r_shoulder",
    "r_arm",
    "r_forearm",
    "r_hand",
    "l_upleg",
    "l_leg",
    "l_foot",
    "l_toe",
    "r_upleg",
    "r_leg",
    "r_foot",
    "r_toe",
)
_LIMBS = (
    "LeftShoulder",
    "LeftArm",
    "LeftForeArm",
    "LeftHand",
    "RightShoulder",
    "RightArm",
    "RightForeArm",
    "RightHand",
    "LeftUpLeg",
    "LeftLeg",
    "LeftFoot",
    "LeftToeBase",
    "RightUpLeg",
    "RightLeg",
    "RightFoot",
    "RightToeBase",
)
# Bone names in slot order, by family; the display name comes first.
FAMILIES = {
    # Meshy Rigging and Animation; its spine counts down towards the neck.
    "meshy": ("Meshy", ("Hips", "Spine02", "Spine01", "Spine", "neck", "Head", *_LIMBS)),
    "mixamo": ("Mixamo", ("Hips", "Spine", "Spine1", "Spine2", "Neck", "Head", *_LIMBS)),
    "smpl": (
        "SMPL",
        (
            "Pelvis",
            "Spine1",
            "Spine2",
            "Spine3",
            "Neck",
            "Head",
            "L_Collar",
            "L_Shoulder",
            "L_Elbow",
            "L_Wrist",
            "R_Collar",
            "R_Shoulder",
            "R_Elbow",
            "R_Wrist",
            "L_Hip",
            "L_Knee",
            "L_Ankle",
            "L_Foot",
            "R_Hip",
            "R_Knee",
            "R_Ankle",
            "R_Foot",
        ),
    ),
    # Unreal Engine 5 and MetaHuman bodies, with five spine bones.
    "unreal": (
        "Unreal",
        (
            "pelvis",
            "spine_01",
            "spine_03",
            "spine_05",
            "neck_01",
            "head",
            "clavicle_l",
            "upperarm_l",
            "lowerarm_l",
            "hand_l",
            "clavicle_r",
            "upperarm_r",
            "lowerarm_r",
            "hand_r",
            "thigh_l",
            "calf_l",
            "foot_l",
            "ball_l",
            "thigh_r",
            "calf_r",
            "foot_r",
            "ball_r",
        ),
    ),
}
# The slot a bone points to: its direction runs from its head to that slot's head.
CHILDREN = {
    "hips": "spine",
    "spine": "chest",
    "chest": "upper_chest",
    "upper_chest": "neck",
    "neck": "head",
    **{
        f"{side}_{slot}": f"{side}_{child}"
        for side in "lr"
        for slot, child in (
            ("shoulder", "arm"),
            ("arm", "forearm"),
            ("forearm", "hand"),
            ("upleg", "leg"),
            ("leg", "foot"),
            ("foot", "toe"),
        )
    },
}
# Slots with no child slot point like their parent slot.
LEAVES = {
    "head": "neck",
    **{f"{s}_{end}": f"{s}_{p}" for s in "lr" for end, p in (("hand", "forearm"), ("toe", "foot"))},
}
# Each slot's parent slot; shoulders hang from the upper chest and legs from the hips.
PARENTS = {
    **{child: slot for slot, child in CHILDREN.items()},
    "l_shoulder": "upper_chest",
    "r_shoulder": "upper_chest",
    "l_upleg": "hips",
    "r_upleg": "hips",
}


def short_name(name):
    """A bone name without its `namespace:` prefix."""
    return name.rsplit(":", 1)[-1]


def detect(parents):
    """The family and slot-to-bone mapping of a rig, or None.

    `parents` maps every bone name to its parent's name, or None for a root.
    """
    names = {}
    for name in parents:
        # Two bones that differ only by prefix are ambiguous: leave them out.
        names[short_name(name)] = None if short_name(name) in names else name
    for family, (_label, wanted) in FAMILIES.items():
        mapping = {slot: names.get(bone) for slot, bone in zip(SLOTS, wanted, strict=True)}
        if None in mapping.values():
            continue
        if all(_descends(parents, mapping[slot], mapping[up]) for slot, up in PARENTS.items()):
            return family, mapping
    return None


def label(family):
    return FAMILIES[family][0]


def _descends(parents, name, ancestor):
    seen = set()
    name = parents.get(name)
    while name is not None and name not in seen:
        if name == ancestor:
            return True
        seen.add(name)
        name = parents.get(name)
    return False
