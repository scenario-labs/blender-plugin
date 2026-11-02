# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Returned humanoid clips retargeted onto a rig with another skeleton.

Text-to-motion models animate their own skeleton, such as Mixamo or Unreal,
which neither names nor orients bones like the user's rig. When both rigs are
recognized humanoids (see `core.scene.humanoid`), each of the 22 body slots
copies its bone's world orientation from the returned clip, frame by frame:

- The rest skeletons are aligned through a character frame built from the rest
  heads (left from the right to the left thigh, up from the hips to the head).
  Each destination bone then turns by the swing that takes its rest direction,
  head to child slot head, onto the returned bone's, so a T-pose clip plays on
  an A-pose rig and bone axis conventions do not matter.
- The clip's first frame defines the source facing on the floor: posed
  orientations and root motion are mapped through level character frames, so
  the character moves in its own facing, wherever it stands in the scene.
- Feet keep their own pitch: both rest poses stand flat on the floor, however
  high each ankle sits over the ball of its foot, so a foot only turns on the
  floor to meet the returned one at rest, and then follows its turns from there.
- Root motion moves the destination hips by the returned hips' travel since the
  first frame, scaled by the ratio of the two legs' lengths. Some files carry that
  travel on the returned armature object instead, when the skin leaves their
  scene root out of its joints: those object keys move the returned skeleton in
  the world each frame, and so reach the hips the same way.
- The hips then move up or down by one height for the whole clip, which puts the
  feet on the floor the rest pose stands on: a clip can start with soft knees or
  raised heels, so its first frame does not fix the hips' height. Each frame
  measures how far the lowest ankle or ball joint stands over its rest height on
  the destination, and over its lowest height in the clip on the returned
  skeleton, scaled like the travel; the median difference is the height.

Every frame of the clip is sampled and keyed linearly: the hips get location and
rotation keys, the other slots rotation keys in their own rotation mode. Bones
outside the slots, such as fingers, keep their current pose.
"""

import math
import statistics
from dataclasses import dataclass, field

import bpy
from mathutils import Euler, Matrix, Quaternion, Vector

from ..core.scene import humanoid
from . import mesh_application as mesh

_UP = Vector((0, 0, 1))
_SMALL = 1e-6
# Slots whose rest direction only turns on the floor: both rests stand flat on it.
_FEET = frozenset({"l_foot", "r_foot"})
# The joints a standing foot rests on: the ankles and the balls of the feet.
_SOLES = ("l_foot", "r_foot", "l_toe", "r_toe")
# Imported keys land on whole frames only up to float rounding, such as 89.000004.
_FRAME_NOISE = 1e-3


def whole_frames(frame_range):
    """The first and last whole frames covering `frame_range`, past float rounding of its ends."""
    start, end = (
        round(frame) if abs(frame - round(frame)) < _FRAME_NOISE else frame for frame in frame_range
    )
    return math.floor(start), math.ceil(end)


def _parents(rig):
    return {bone.name: bone.parent.name if bone.parent else None for bone in rig.data.bones}


def _path(rig, names):
    """The named bones and their ancestors, parents first."""
    bones = {}
    for name in names:
        bone = rig.data.bones[name]
        for item in (bone, *bone.parent_recursive):
            bones[item.name] = item
    return sorted(bones.values(), key=lambda bone: len(bone.parent_recursive))


def _standard(bones):
    """Whether every bone inherits its parent's full transform, which the sampling assumes."""
    return all(
        bone.use_inherit_rotation and bone.inherit_scale == "FULL" and bone.use_local_location
        for bone in bones
    )


def _relative(bone):
    """A bone's rest matrix relative to its parent, or in armature space for a root."""
    if bone.parent is None:
        return bone.matrix_local.copy()
    return bone.parent.matrix_local.inverted_safe() @ bone.matrix_local


def _turn(matrix):
    return matrix.to_3x3().normalized()


def _frame(points, level):
    """A character's axes as matrix columns, from world joint heads by slot.

    Up runs from the hips to the head, or along world Z when `level`; left runs
    from the right thigh to the left one, square to up.
    """
    up = _UP if level else points["head"] - points["hips"]
    left = points["l_upleg"] - points["r_upleg"]
    if up.length < _SMALL:
        raise mesh.MeshApplicationError("Cannot retarget a skeleton without height")
    up = up.normalized()
    left -= left.dot(up) * up
    if left.length < _SMALL:
        raise mesh.MeshApplicationError("Cannot retarget a skeleton without hip width")
    left.normalize()
    return Matrix((left, up.cross(left), up)).transposed()


def _flat(direction):
    """A direction's heading on the floor, or the direction itself when it points straight down."""
    level = direction - direction.dot(_UP) * _UP
    return level if level.length > _SMALL else direction


def _leg(points):
    """The mean thigh plus shin length."""
    return (
        sum(
            (points[f"{side}_leg"] - points[f"{side}_upleg"]).length
            + (points[f"{side}_foot"] - points[f"{side}_leg"]).length
            for side in "lr"
        )
        / 2
    )


def _local(owner, keyed, frame):
    """A pose bone's or object's own transform at `frame`: keyed channels, else current values."""

    def values(name, current):
        channel = keyed.get(name, {})
        return [
            channel[index].evaluate(frame) if index in channel else value
            for index, value in enumerate(current)
        ]

    mode = owner.rotation_mode
    if mode == "QUATERNION":
        rotation = Quaternion(values("rotation_quaternion", owner.rotation_quaternion))
        rotation = rotation.normalized().to_matrix()
    elif mode == "AXIS_ANGLE":
        angle, *axis = values("rotation_axis_angle", owner.rotation_axis_angle)
        axis = Vector(axis)
        rotation = Matrix.Rotation(angle, 3, axis) if axis.length > _SMALL else Matrix.Identity(3)
    else:
        rotation = Euler(values("rotation_euler", owner.rotation_euler), mode).to_matrix()
    location = Vector(values("location", owner.location))
    scale = Vector(values("scale", owner.scale))
    return Matrix.LocRotScale(location, rotation, scale)


def _basis(pose_bone, curves, frame):
    """A bone's local pose at `frame`: its keyed channels, else its current values."""
    basis = _local(pose_bone, curves.get(pose_bone.name, {}), frame)
    if pose_bone.bone.use_connect:
        # Blender ignores a connected bone's location.
        basis.translation = Vector()
    return basis


@dataclass(eq=False)
class Retarget:
    """A validated slot mapping between a returned skeleton and the destination rig."""

    source: object
    destination: object
    # The returned skeleton's family, such as "mixamo".
    family: str
    # Slot to bone name, on each rig.
    source_bones: dict = field(repr=False)
    destination_bones: dict = field(repr=False)

    def __post_init__(self):
        source, destination = self.source, self.destination
        self._source_path = _path(source, self.source_bones.values())
        self._destination_path = _path(destination, self.destination_bones.values())
        if not _standard(self._source_path):
            raise mesh.MeshApplicationError(
                "The returned skeleton's bones must inherit rotation and scale"
            )
        if not _standard(self._destination_path):
            raise mesh.MeshApplicationError("Retargeted bones must inherit rotation and scale")
        if any(
            destination.pose.bones[name].rotation_mode == "AXIS_ANGLE"
            for name in self.destination_bones.values()
        ):
            raise mesh.MeshApplicationError(
                "Retargeted bones must use quaternion or Euler rotation"
            )
        self._slots = {name: slot for slot, name in self.destination_bones.items()}
        self._relative = {
            (rig, bone.name): _relative(bone)
            for rig, path in ((source, self._source_path), (destination, self._destination_path))
            for bone in path
        }

        def rest(rig, bones):
            world = rig.matrix_world
            return {slot: world @ rig.data.bones[name].head_local for slot, name in bones.items()}

        source_rest = rest(source, self.source_bones)
        destination_rest = rest(destination, self.destination_bones)
        # Source rest world to destination rest world, for bone directions.
        aligned = _frame(destination_rest, False) @ _frame(source_rest, False).transposed()
        self._level = _frame(destination_rest, True)
        self._leg = _leg(destination_rest)
        self._hips = destination_rest["hips"]
        self._soles = [destination_rest[item].z for item in _SOLES]
        swings = {}
        for slot, child in humanoid.CHILDREN.items():
            returned = aligned @ (source_rest[child] - source_rest[slot])
            existing = destination_rest[child] - destination_rest[slot]
            if returned.length < _SMALL or existing.length < _SMALL:
                raise mesh.MeshApplicationError("Cannot retarget bones of zero length")
            if slot in _FEET:
                returned, existing = _flat(returned), _flat(existing)
            swings[slot] = existing.rotation_difference(returned).to_matrix()
        # P_destination = P_source' @ offset, with P_source' the returned bone's world
        # orientation mapped into the destination's frame.
        self._offsets = {}
        for slot in humanoid.SLOTS:
            swing = swings[humanoid.LEAVES.get(slot, slot)]
            returned = (
                aligned
                @ _turn(source.matrix_world)
                @ _turn(source.data.bones[self.source_bones[slot]].matrix_local)
            )
            existing = _turn(destination.matrix_world) @ _turn(
                destination.data.bones[self.destination_bones[slot]].matrix_local
            )
            self._offsets[slot] = returned.inverted() @ swing @ existing

    def _source_pose(self, curves, frame):
        """Armature-space pose matrices of the mapped returned bones and their ancestors."""
        poses = {}
        for bone in self._source_path:
            basis = _basis(self.source.pose.bones[bone.name], curves, frame)
            parent = poses.get(bone.parent.name) if bone.parent else None
            relative = self._relative[self.source, bone.name]
            poses[bone.name] = (relative if parent is None else parent @ relative) @ basis
        return poses

    def _world(self, carried, frame):
        """The returned armature object's world matrix at `frame`, with its own keys if any."""
        source = self.source
        if not carried:
            return source.matrix_world
        parent = (
            source.parent.matrix_world @ source.matrix_parent_inverse
            if source.parent is not None
            else Matrix.Identity(4)
        )
        return parent @ _local(source, carried, frame)

    def _lift(self, feet, ratio):
        """The world height added to the hips' keys so the feet stand on the rest floor.

        `feet` holds, for each frame, the returned and destination sole joint heights.
        """
        lowest = [min(heights) for heights in zip(*(returned for returned, _ in feet), strict=True)]
        return statistics.median(
            ratio * min(z - low for z, low in zip(returned, lowest, strict=True))
            - min(z - rest for z, rest in zip(mine, self._soles, strict=True))
            for returned, mine in feet
        )

    def clip(self, action, slot, curves, name, carried=None):
        """A new action named `name` playing the clip on the destination rig, and its slot.

        `carried` maps the returned armature object's own keyed properties to their
        curves by index, as `curves` does for each bone.
        """
        rig = self.destination
        start, end = whole_frames(action.frame_range)
        frames = range(start, end + 1)
        world = self._world(carried, frames[0])
        first = self._source_pose(curves, frames[0])
        posed = {item: world @ first[bone].translation for item, bone in self.source_bones.items()}
        # Source world to destination world, both levelled on the floor.
        mapping = self._level @ _frame(posed, True).transposed()
        leg = _leg(posed)
        if leg < _SMALL:
            raise mesh.MeshApplicationError("Cannot retarget a skeleton without legs")
        ratio = self._leg / leg
        back = _turn(rig.matrix_world).inverted()
        inverse = rig.matrix_world.inverted_safe()
        hips = self.source_bones["hips"]
        keys = {bone: [] for bone in self._slots}
        # The hips' inverted rest and head each frame, and both rigs' sole heights.
        heads, feet = [], []
        # Unmapped bones on the way keep their current pose.
        held = {
            bone.name: rig.pose.bones[bone.name].matrix_basis.copy()
            for bone in self._destination_path
            if bone.name not in self._slots
        }
        for frame in frames:
            pose = self._source_pose(curves, frame)
            world = self._world(carried, frame)
            into = mapping @ _turn(world)
            mine = {}
            for bone in self._destination_path:
                parent = mine.get(bone.parent.name) if bone.parent else None
                relative = self._relative[rig, bone.name]
                rest = relative if parent is None else parent @ relative
                item = self._slots.get(bone.name)
                if item is None:
                    mine[bone.name] = rest @ held[bone.name]
                    continue
                turn = back @ into @ _turn(pose[self.source_bones[item]]) @ self._offsets[item]
                head = rest.translation
                if item == "hips":
                    travel = world @ pose[hips].translation - posed["hips"]
                    head = inverse @ (self._hips + mapping @ travel * ratio)
                target = Matrix.Translation(head) @ turn.to_4x4()
                mine[bone.name] = target
                basis = rest.inverted_safe() @ target
                keys[bone.name].append(basis.to_quaternion().normalized())
                if item == "hips":
                    heads.append((rest.inverted_safe(), head))
            feet.append(
                (
                    [(world @ pose[self.source_bones[item]].translation).z for item in _SOLES],
                    [
                        (rig.matrix_world @ mine[self.destination_bones[item]].translation).z
                        for item in _SOLES
                    ],
                )
            )
        lift = inverse.to_3x3() @ (_UP * self._lift(feet, ratio))
        locations = [inverted @ (head + lift) for inverted, head in heads]
        new = bpy.data.actions.new(name)
        try:
            bound = new.slots.new(id_type="OBJECT", name=rig.name)
            bag = new.layers.new("Layer").strips.new(type="KEYFRAME").channelbags.new(bound)
            for bone, rotations in keys.items():
                mode = rig.pose.bones[bone].rotation_mode
                if mode == "QUATERNION":
                    for index in range(1, len(rotations)):
                        # Neighbouring keys take the shorter way round.
                        if rotations[index].dot(rotations[index - 1]) < 0:
                            rotations[index].negate()
                    _keys(bag, bone, "rotation_quaternion", frames, rotations)
                else:
                    eulers = []
                    for rotation in rotations:
                        eulers.append(rotation.to_euler(mode, *eulers[-1:]))
                    _keys(bag, bone, "rotation_euler", frames, eulers)
            _keys(bag, self.destination_bones["hips"], "location", frames, locations)
        except BaseException:
            # The caller removes only the clips returned to it.
            bpy.data.actions.remove(new)
            raise
        return new, bound


def _keys(bag, bone, prop, frames, rows):
    path = f'pose.bones["{bpy.utils.escape_identifier(bone)}"].{prop}'
    for index, values in enumerate(zip(*rows, strict=True)):
        curve = bag.fcurves.new(path, index=index, group_name=bone)
        points = curve.keyframe_points
        points.add(len(frames))
        points.foreach_set(
            "co", [item for pair in zip(frames, values, strict=True) for item in pair]
        )
        for point in points:
            point.interpolation = "LINEAR"
        curve.update()


def plan(source, destination):
    """A retarget between two recognized humanoid rigs, or None when either is not one."""
    found = humanoid.detect(_parents(source)), humanoid.detect(_parents(destination))
    if None in found:
        return None
    (family, source_bones), (_family, destination_bones) = found
    return Retarget(source, destination, family, source_bones, destination_bones)
