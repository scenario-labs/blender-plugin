# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Synchronous returned-clip application to a captured source's existing rig.

A returned armature's clips are copied onto the armature that the captured
source's Armature skin uses. The source mesh, its skin and the rig's rest data are
never modified, and no returned object is kept. Bones are matched by name only;
retargeting across different skeletons is unsupported.
"""

import math
import re
from dataclasses import dataclass, field

import bpy

from . import mesh_application as mesh

# Rotation channels pose a bone relative to its rest orientation, so a different
# rest poses it differently. One provider re-rigging its own rigged character
# moved some joints' rest orientations by up to about 11 degrees; a skeleton built
# for another pose or orientation differs by tens of degrees.
REST_TOLERANCE = math.radians(15)
_CHANNEL = re.compile(
    r'pose\.bones\["((?:[^"\\]|\\.)*)"\]\.'
    r"(location|rotation_quaternion|rotation_euler|rotation_axis_angle|scale)"
)
_ROTATIONS = frozenset({"rotation_quaternion", "rotation_euler", "rotation_axis_angle"})


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


def _rest(bone):
    """Rest orientation relative to the parent bone, or to armature space for a root."""
    matrix = bone.matrix_local
    if bone.parent is not None:
        matrix = bone.parent.matrix_local.inverted_safe() @ matrix
    return matrix.to_quaternion().normalized()


def _offset(bone):
    return (bone.head_local - bone.parent.head_local).length


def _scale(source, destination):
    """Destination per result armature-space unit, from shared parent-relative bone offsets.

    Location channels are armature-space distances. A returned rig's object scale
    (for example 0.01 with centimetre bones) does not enter armature space.
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
    """Require one armature whose clips key bones the destination rig has with the same rest."""
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
        ):
            raise mesh.MeshApplicationError("Animated bones must keep the same hierarchy")
        if properties & _ROTATIONS and (
            source.pose.bones[name].rotation_mode != destination.pose.bones[name].rotation_mode
        ):
            raise mesh.MeshApplicationError("Animated bones must use the same rotation mode")
        dot = min(1.0, abs(_rest(returned).dot(_rest(existing))))
        if 2 * math.acos(dot) > REST_TOLERANCE:
            raise mesh.MeshApplicationError("The destination rig's rest pose does not match")
    # Rest-head location keys stay zero at any scale; sampled exports key every bone.
    return destination, clips, _scale(source, destination) if moved else 1.0


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


def _copy(action, slot, rig, ratio):
    """A new clip for the destination rig, its location keys rescaled."""
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
    return clip, bound


def _track(data, name, action, slot):
    track = data.nla_tracks.new()
    track.name = name
    strip = track.strips.new(name, math.floor(action.frame_range[0]), action)
    strip.action_slot = slot
    track.mute = True
    if strip.action_slot != slot:
        raise mesh.MeshApplicationError("Could not keep a clip in the NLA")
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
    action, handle, identifier = before[:3]
    data.action = action
    if action is not None:
        data.action_slot = next((slot for slot in action.slots if slot.handle == handle), None)
    data.last_slot_identifier = identifier


@dataclass(eq=False)
class AnimationApplication:
    """Internal synchronous rollback handle; finalized by the saved-result command.

    Accepting keeps the new clips and tracks. Rollback restores the rig's previous
    animation assignment and tracks; the caller removes the new clip datablocks.
    """

    source: object
    rig: object
    actions: tuple
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

    Timeline settings stay unchanged. Clip timing already follows the destination
    frame rate through the shared staging scene.
    """
    rig, clips, ratio = validate_clips(target, objects)
    before = _state(rig)
    actions, tracks = [], []
    try:
        for action, slot in clips:
            actions.append(_copy(action, slot, rig, ratio))
        data = rig.animation_data or rig.animation_data_create()
        if data.action is not None:
            tracks.append(_track(data, data.action.name, data.action, data.action_slot))
        for clip, slot in actions:
            tracks.append(_track(data, clip.name, clip, slot))
        clip, slot = actions[0]
        data.action = clip
        data.action_slot = slot
        if (data.action, data.action_slot) != (clip, slot):
            raise mesh.MeshApplicationError("Blender did not assign the returned clip")
        return AnimationApplication(
            target.obj,
            rig,
            tuple(clip for clip, _ in actions),
            tuple(tracks),
            before,
            _state(rig),
        )
    except BaseException:
        _restore(rig, before, tracks)
        for clip, _ in actions:
            bpy.data.actions.remove(clip)
        raise
