# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Synchronous returned-clip application to a captured source's existing rig.

A returned armature's clips are copied onto the armature that the captured
source's Armature skin uses. The source mesh, its skin and the rig's rest data are
never modified, and no returned object is kept. Bones are matched by name only;
retargeting across different skeletons is unsupported.

Both rigs bind the same character in the same rest pose, but a re-rig can orient
a bone differently on it. Skinning moves a vertex by its bone's armature-space
deform matrix, the posed matrix times the inverted rest. A bone that inherits
rotation and scale and keys a local location, as every glTF bone does and so the
matching destination bone must, with rest rotation A, pose rotation q and pose
location l, deforms by A q A^-1 about its rest head and moves by A l, after its
parent's deform. The destination therefore gets q' = C q C^-1 and l' = C l with
C = A_destination^-1 A_result, so every bone, and every mesh it moves, deforms as
in the returned clip. The rest head positions stay the destination's: the user's
mesh bends about its own joints.

A is the armature-space rest when the rigs match that way, so a turned character
plays the clip in its own facing. Otherwise, as when an FBX import turns its
armature object and its bones back, A is the world-space rest: the armature
object's rotation times the armature-space rest.
"""

import logging
import math
import re
from dataclasses import dataclass, field

import bpy
from mathutils import Vector

from . import mesh_application as mesh

_log = logging.getLogger("scenario.jobs")

# Clips are corrected for rest differences (see above), which only holds when both
# rigs bind the character in the same pose. One provider re-rigging its own rigged
# character moved some joints' rest orientations by up to about 11 degrees relative
# to their parents; a skeleton built for another pose or orientation differs by
# tens of degrees, which a correction would turn into a wrong motion.
REST_TOLERANCE = math.radians(15)
# Smaller rest differences are export rounding: their keys are copied unchanged.
_NEGLIGIBLE = 1e-5
# Exported uniform scale keys can differ between axes by a few 1e-5.
_UNIFORM = 1e-4
_CHANNEL = re.compile(
    r'pose\.bones\["((?:[^"\\]|\\.)*)"\]\.'
    r"(location|rotation_quaternion|rotation_euler|rotation_axis_angle|scale)"
)
_ROTATIONS = frozenset({"rotation_quaternion", "rotation_euler", "rotation_axis_angle"})
# Vector components a correction rotates: location, and the quaternion's X, Y and Z
# (conjugation keeps W). Both maps are linear, so rotating every key and handle of
# curves that share their timing rotates the interpolated values exactly, and the
# dot product between keys, and so their sign continuity, is kept.
_VECTORS = {"location": (0, 1, 2), "rotation_quaternion": (1, 2, 3)}
_INTERPOLATIONS = frozenset({"CONSTANT", "LINEAR", "BEZIER"})


def _clips(rig):
    """The active clip first, then each NLA strip's clip, as Blender's importer orders them."""
    data = rig.animation_data
    pairs = []
    if data is not None:
        if data.action is not None:
            pairs.append((data.action, data.action_slot))
        pairs.extend(
            (strip.action, strip.action_slot)
            for track in data.nla_tracks
            for strip in track.strips
            if strip.action is not None
        )
    clips = []
    for action, slot in pairs:
        if slot is None:
            raise mesh.MeshApplicationError("Every returned clip must be bound to its armature")
        if not any(action == seen and slot == bound for seen, bound in clips):
            clips.append((action, slot))
    if not clips:
        raise mesh.MeshApplicationError("The returned armature has no animation clips")
    return clips


def _channelbags(action, slot):
    return [
        bag
        for layer in action.layers
        for strip in layer.strips
        if (bag := strip.channelbag(slot)) is not None
    ]


def _values(curve):
    """Key and handle values (not frames) of one curve."""
    values = []
    for name in ("co", "handle_left", "handle_right"):
        pairs = [0.0] * (2 * len(curve.keyframe_points))
        curve.keyframe_points.foreach_get(name, pairs)
        values.extend(pairs[1::2])
    return values


def _channels(action, slot):
    """Map each animated bone to its animated properties; reject anything else.

    Also report whether any location key moves a bone away from its rest head.
    """
    if any(
        bag.fcurves
        for other in action.slots
        if other != slot
        for bag in _channelbags(action, other)
    ):
        raise mesh.MeshApplicationError("Clips that animate other objects are unsupported")
    bones, moved = {}, False
    for bag in _channelbags(action, slot):
        for curve in bag.fcurves:
            match = _CHANNEL.fullmatch(curve.data_path)
            if match is None or curve.modifiers:
                raise mesh.MeshApplicationError(
                    "Clips may only key bone location, rotation and scale"
                )
            name = bpy.utils.unescape_identifier(match.group(1))
            bones.setdefault(name, set()).add(match.group(2))
            if match.group(2) == "location" and not moved:
                moved = any(abs(value) > 1e-9 for value in _values(curve))
    return bones, moved


def _orientation(rig, bone, world):
    """Rest orientation in armature space, or in world space with `world`."""
    rest = bone.matrix_local.to_quaternion()
    if world:
        rest = rig.matrix_world.to_quaternion() @ rest
    return rest.normalized()


def _rest(rig, bone, world):
    """Rest orientation relative to the parent bone, or to the chosen space for a root."""
    if bone.parent is None:
        return _orientation(rig, bone, world)
    matrix = bone.parent.matrix_local.inverted_safe() @ bone.matrix_local
    return matrix.to_quaternion().normalized()


def _angle(rotation):
    return 2 * math.acos(min(1.0, abs(rotation.w)))


def _curves(action, slot):
    """Each bone's curves by property and array index."""
    curves = {}
    for bag in _channelbags(action, slot):
        for curve in bag.fcurves:
            match = _CHANNEL.fullmatch(curve.data_path)
            name = bpy.utils.unescape_identifier(match.group(1))
            properties = curves.setdefault(name, {})
            properties.setdefault(match.group(2), {})[curve.array_index] = curve
    return curves


def _timing(curve):
    """What makes a curve's interpolation the same function of its key values as another's."""
    keys = curve.keyframe_points
    interpolation = tuple(key.interpolation for key in keys)
    names = ("co", "handle_left", "handle_right") if "BEZIER" in interpolation else ("co",)
    frames = []
    for name in names:
        pairs = [0.0] * (2 * len(keys))
        keys.foreach_get(name, pairs)
        frames.append(tuple(pairs[::2]))
    return curve.extrapolation, interpolation, tuple(frames)


def _shared(curves):
    """Whether these curves share keys, handle frames and interpolation exactly."""
    timing = {_timing(curve) for curve in curves}
    return len(timing) == 1 and set(next(iter(timing))[1]) <= _INTERPOLATIONS


def _constant(curves, value):
    return all(abs(item - value) <= 1e-6 for curve in curves for item in _values(curve))


def _correctable(properties, rotation_mode):
    """Raise unless a rest correction can transform this bone's curves exactly."""
    for name, curves in properties.items():
        if name in _VECTORS:
            present = [curves[index] for index in _VECTORS[name] if index in curves]
            if len(present) == 3 and _shared(present):
                continue
            # A missing component holds its rest value, which the correction keeps.
            if len(present) < 3 and _constant(present, 0.0):
                continue
            raise mesh.MeshApplicationError(
                "Rest-corrected bones must key each vector channel together"
            )
        if name == "scale":
            # A different rest would turn an axis-aligned stretch off its axes.
            present = list(curves.values())
            uniform = len(present) == 3 and _shared(present)
            if uniform:
                values = [_values(curve) for curve in present]
                uniform = all(
                    max(items) - min(items) <= _UNIFORM * max(1.0, *map(abs, items))
                    for items in zip(*values, strict=True)
                )
            if not (uniform or _constant(present, 1.0)):
                raise mesh.MeshApplicationError(
                    "Bones whose rest pose differs can only scale uniformly"
                )
    if properties.keys() & _ROTATIONS and rotation_mode != "QUATERNION":
        raise mesh.MeshApplicationError(
            "Bones whose rest pose differs must use quaternion rotation"
        )


def _within(source, destination, animated, world):
    """Whether each animated bone's rest is within tolerance in the chosen space.

    Every animated bone's rest is compared relative to its parent. An animated bone
    whose parent is not animated is also compared absolutely: its correction
    carries the rest difference of the unkeyed bones above it, which no key
    corrects. Below it, corrections compose exactly along the keyed chain.
    """
    for name in animated:
        returned, existing = source.data.bones[name], destination.data.bones[name]
        measures = [_rest]
        if returned.parent is not None and returned.parent.name not in animated:
            measures.append(_orientation)
        for measure in measures:
            pair = (measure(source, returned, world), measure(destination, existing, world))
            if 2 * math.acos(min(1.0, abs(pair[0].dot(pair[1])))) > REST_TOLERANCE:
                return False
    return True


def _corrections(source, destination, animated, clips, world):
    """Each animated bone's rest correction C and the largest correction angle.

    Only bones whose correction exceeds export rounding are returned, after their
    curves are checked in every clip.
    """
    corrections, largest = {}, 0.0
    for name in animated:
        existing = _orientation(destination, destination.data.bones[name], world)
        returned = _orientation(source, source.data.bones[name], world)
        correction = existing.inverted() @ returned
        angle = _angle(correction)
        largest = max(largest, angle)
        if angle > _NEGLIGIBLE:
            corrections[name] = correction.to_matrix()
    for action, slot in clips:
        curves = _curves(action, slot)
        for name in corrections:
            if name in curves:
                _correctable(curves[name], destination.pose.bones[name].rotation_mode)
    return corrections, largest


def _rotate(curves, matrix):
    """Rotate the vector that three curves key, in every key and handle value."""
    for curve in curves:
        if any(key.interpolation == "BEZIER" for key in curve.keyframe_points):
            # Automatic handles would be recomputed from each curve alone.
            for key in curve.keyframe_points:
                key.handle_left_type = key.handle_right_type = "FREE"
    count = len(curves[0].keyframe_points)
    for name in ("co", "handle_left", "handle_right"):
        columns = []
        for curve in curves:
            pairs = [0.0] * (2 * count)
            curve.keyframe_points.foreach_get(name, pairs)
            columns.append(pairs)
        for index in range(1, 2 * count, 2):
            vector = matrix @ Vector([pairs[index] for pairs in columns])
            for pairs, value in zip(columns, vector, strict=True):
                pairs[index] = value
        for curve, pairs in zip(curves, columns, strict=True):
            curve.keyframe_points.foreach_set(name, pairs)
    for curve in curves:
        curve.update()


def _offset(bone):
    return (bone.head_local - bone.parent.head_local).length


def _scale(source, destination):
    """Destination per result armature-space unit, from shared parent-relative bone offsets.

    Location channels are armature-space distances. A returned rig's object scale
    (for example 0.01 with centimetre bones) does not enter armature space; the
    rest correction handles object rotation.
    """
    shared = [
        (bone, destination.data.bones[bone.name])
        for bone in source.data.bones
        if bone.parent is not None
        and bone.name in destination.data.bones
        and destination.data.bones[bone.name].parent is not None
        and destination.data.bones[bone.name].parent.name == bone.parent.name
    ]
    returned = sum(_offset(bone) for bone, _ in shared)
    existing = sum(_offset(bone) for _, bone in shared)
    ratio = existing / returned if returned > 1e-9 else math.nan
    if not math.isfinite(ratio) or ratio <= 1e-9:
        raise mesh.MeshApplicationError("Cannot derive the clip scale from shared bone offsets")
    return ratio


def validate_clips(target, objects):
    """Require one armature whose clips key bones the destination rig has with a close rest.

    Return the destination rig, the clips, the location scale, the rest corrections
    and the largest correction angle.
    """
    mesh.validate_target(target)
    if target.skin is None:
        raise mesh.MeshApplicationError("Apply animation requires a mesh skinned to an armature")
    rigs = [obj for obj in objects if obj.type == "ARMATURE"]
    if len(rigs) != 1 or any(obj.type not in {"MESH", "ARMATURE", "EMPTY"} for obj in objects):
        raise mesh.MeshApplicationError("Animation application requires one returned armature")
    source = rigs[0]
    for obj in objects:
        keys = obj.data.shape_keys if obj.type == "MESH" else None
        if (obj != source and obj.animation_data) or (keys and keys.animation_data):
            raise mesh.MeshApplicationError("Only armature bone clips can be applied")
    if source.data.animation_data:
        raise mesh.MeshApplicationError("Armature-data animation is unsupported")
    destination = target.skin.rig
    data = destination.animation_data
    if data is not None and data.use_tweak_mode:
        raise mesh.MeshApplicationError("Leave NLA tweak mode on the destination rig")
    if data is not None and any(track.is_solo for track in data.nla_tracks):
        # Blender plays no active action beside a soloed track outside tweak mode.
        raise mesh.MeshApplicationError("Unsolo the destination rig's NLA track")
    if any(rig.matrix_world.to_3x3().determinant() <= 0 for rig in (source, destination)):
        # A mirrored or flattened armature object has no rest rotation to correct by.
        raise mesh.MeshApplicationError("Apply animation needs rigs that are not mirrored")
    clips = _clips(source)
    animated, moved = {}, False
    for action, slot in clips:
        bones, offset = _channels(action, slot)
        moved = moved or offset
        for name, properties in bones.items():
            animated.setdefault(name, set()).update(properties)
    for name, properties in animated.items():
        returned = source.data.bones.get(name)
        existing = destination.data.bones.get(name)
        if returned is None or existing is None:
            raise mesh.MeshApplicationError("The destination rig lacks a bone the clips animate")
        if (
            (returned.parent.name if returned.parent else None)
            != (existing.parent.name if existing.parent else None)
            or returned.use_connect != existing.use_connect
            or returned.use_inherit_rotation != existing.use_inherit_rotation
            or returned.inherit_scale != existing.inherit_scale
            or returned.use_local_location != existing.use_local_location
        ):
            raise mesh.MeshApplicationError("Animated bones must keep the same hierarchy")
        if properties & _ROTATIONS and (
            source.pose.bones[name].rotation_mode != destination.pose.bones[name].rotation_mode
        ):
            raise mesh.MeshApplicationError("Animated bones must use the same rotation mode")
    # Armature space first: a turned character keeps the clip in its own facing.
    for world in (False, True):
        if _within(source, destination, animated, world):
            break
    else:
        raise mesh.MeshApplicationError("The destination rig's rest pose does not match")
    _log.info("Clip rests compared in %s space", "world" if world else "armature")
    # Constraints and drivers evaluate after the action and would override the clips.
    drivers = data.drivers if data is not None else ()
    driven = {
        bpy.utils.unescape_identifier(match.group(1))
        for curve in drivers
        if (match := _CHANNEL.fullmatch(curve.data_path))
    }
    if driven & animated.keys() or any(
        destination.pose.bones[name].constraints for name in animated
    ):
        raise mesh.MeshApplicationError("Constraints or drivers move the animated bones")
    corrections, largest = _corrections(source, destination, animated, clips, world)
    # Rest-head location keys stay zero at any scale; sampled exports key every bone.
    ratio = _scale(source, destination) if moved else 1.0
    return destination, clips, ratio, corrections, largest


def _state(rig):
    """Every animation setting this application changes, and the NLA tracks it preserves."""
    data = rig.animation_data
    if data is None:
        return None
    return (
        data.action,
        data.action_slot_handle,
        data.last_slot_identifier,
        data.action_extrapolation,
        data.action_blend_type,
        data.action_influence,
        data.use_nla,
        data.use_tweak_mode,
        tuple(
            (
                track,
                track.name,
                track.mute,
                track.is_solo,
                track.lock,
                tuple(
                    (strip, strip.action, strip.action_slot_handle, strip.mute)
                    for strip in track.strips
                ),
            )
            for track in data.nla_tracks
        ),
    )


def _copy(action, slot, rig, ratio, corrections):
    """A new clip for the destination rig, its location keys rescaled and rest-corrected."""
    clip = action.copy()
    clip.use_fake_user = False
    clip.name = f"{rig.name} {action.name}"
    bound = next(item for item in clip.slots if item.identifier == slot.identifier)
    for other in tuple(clip.slots):
        if other != bound:
            clip.slots.remove(other)
    bound.name_display = rig.name
    if ratio != 1.0:
        for bag in _channelbags(clip, bound):
            for curve in bag.fcurves:
                if not curve.data_path.endswith(".location"):
                    continue
                for name in ("co", "handle_left", "handle_right"):
                    values = [0.0] * (2 * len(curve.keyframe_points))
                    curve.keyframe_points.foreach_get(name, values)
                    values[1::2] = [value * ratio for value in values[1::2]]
                    curve.keyframe_points.foreach_set(name, values)
                curve.update()
    for name, properties in _curves(clip, bound).items():
        matrix = corrections.get(name)
        if matrix is None:
            continue
        for property_name, indices in _VECTORS.items():
            curves = properties.get(property_name, {})
            if all(index in curves for index in indices):
                _rotate([curves[index] for index in indices], matrix)
    return clip, bound


def _track(data, name, action, slot):
    track = data.nla_tracks.new()
    try:
        track.name = name
        strip = track.strips.new(name, math.floor(action.frame_range[0]), action)
        strip.action_slot = slot
        track.mute = True
        if strip.action_slot != slot:
            raise mesh.MeshApplicationError("Could not keep a clip in the NLA")
    except BaseException:
        # The caller's rollback only knows the tracks returned to it.
        data.nla_tracks.remove(track)
        raise
    return track


def _restore(rig, before, tracks):
    data = rig.animation_data
    if data is None:
        return
    for track in tracks:
        # RNA wrappers differ per access: compare, never test identity.
        if any(item == track for item in data.nla_tracks):
            data.nla_tracks.remove(track)
    if before is None:
        rig.animation_data_clear()
        return
    action, handle, identifier, extrapolation, blend, influence = before[:6]
    data.action = action
    if action is not None:
        data.action_slot = next((slot for slot in action.slots if slot.handle == handle), None)
    data.last_slot_identifier = identifier
    data.action_extrapolation = extrapolation
    data.action_blend_type = blend
    data.action_influence = influence


@dataclass(eq=False)
class AnimationApplication:
    """Internal synchronous rollback handle; finalized by the saved-result command.

    Accepting keeps the new clips and tracks. Rollback restores the rig's previous
    animation assignment and tracks; the caller removes the new clip datablocks.
    """

    source: object
    rig: object
    actions: tuple
    # The largest rest correction applied to an animated bone, in degrees.
    rest_correction_deg: float
    _tracks: tuple = field(repr=False)
    _before: tuple | None = field(repr=False)
    _applied: tuple = field(repr=False)
    _closed: bool = field(default=False, repr=False)
    # ANIMATE leaves mesh data alone, so there is no Keep original copy.
    original = None

    def accept(self):
        if self._closed:
            raise mesh.MeshApplicationError("This application receipt is already finalized")
        self._closed = True

    def rollback(self):
        if self._closed:
            raise mesh.MeshApplicationError("This application receipt is already finalized")
        try:
            if _state(self.rig) != self._applied:
                raise mesh.MeshApplicationError(
                    "Rig animation changed; inspect the rig before recovery"
                )
            _restore(self.rig, self._before, self._tracks)
            if _state(self.rig) != self._before:
                raise mesh.MeshApplicationError("Could not restore the rig's previous animation")
        except ReferenceError:
            raise mesh.MeshApplicationError(
                "Application data was removed; rollback is unavailable"
            ) from None
        self._closed = True


def apply_clips(target, objects):
    """Assign the first returned clip; keep it, the others and any previous action in muted NLA.

    The rig's action blending becomes Replace at full influence. Timeline settings
    stay unchanged. Clip timing already follows the destination frame rate through
    the shared staging scene.
    """
    rig, clips, ratio, corrections, largest = validate_clips(target, objects)
    before = _state(rig)
    actions, tracks = [], []
    try:
        for action, slot in clips:
            actions.append(_copy(action, slot, rig, ratio, corrections))
        data = rig.animation_data or rig.animation_data_create()
        if data.action is not None:
            tracks.append(_track(data, data.action.name, data.action, data.action_slot))
        for clip, slot in actions:
            tracks.append(_track(data, clip.name, clip, slot))
        clip, slot = actions[0]
        data.action = clip
        data.action_slot = slot
        # The clip replaces the rest pose fully, as on the returned rig.
        data.action_blend_type = "REPLACE"
        data.action_influence = 1.0
        if (data.action, data.action_slot) != (clip, slot):
            raise mesh.MeshApplicationError("Blender did not assign the returned clip")
        return AnimationApplication(
            target.obj,
            rig,
            tuple(clip for clip, _ in actions),
            round(math.degrees(largest), 1),
            tuple(tracks),
            before,
            _state(rig),
        )
    except BaseException:
        _restore(rig, before, tracks)
        for clip, _ in actions:
            bpy.data.actions.remove(clip)
        raise
