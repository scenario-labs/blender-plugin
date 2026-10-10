# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Standalone owned Blender process for portable Film case-study libraries.

The portable layout (bundle-relative media, packed textures, curated scenes)
adapts Emmanuel de Maistre's Scenario Studio case-study export. Unlike that
source, which rewrote and restored the working file's own paths, this child
edits only a private snapshot. It follows the render_worker.py process pattern:
an offline, factory-startup child that never imports or registers the extension.

``bundle`` points every external file reference at the bundle's Media folder,
rebuilds sound strips so no earlier path stays in them, repacks packed images
under neutral names, removes Scenario properties that identify jobs, assets or
productions, removes the extension's saved settings (composer lanes and their
references, Film and workflow forms) and writes the chosen scenes as a data
library. ``verify`` opens that library and reports its scenes, file references and
remaining properties.
"""

import json
import os
import sys
from collections import Counter
from pathlib import Path

MEDIA = "Media"
PACKED = "Packed"
MAX_PARAMETERS = 4 * 1024 * 1024
# Descriptive Scenario tags that name no account, job, asset or production.
KEEP = frozenset(
    {
        "scenario_film",
        "scenario_sequence_kind",
        "scenario_film_sequence_kind",
        "scenario_film_shot_id",
        "scenario_audio_mix",
        "scenario_role",
        "scenario_primitive",
        "scenario_asset_policy",
        "scenario_hero_id",
        "scenario_reference_task",
        "scenario_camera_path",
        "scenario_shot_frames",
        "scenario_shot_source",
    }
)
COLLECTIONS = (
    "actions",
    "armatures",
    "brushes",
    "cache_files",
    "cameras",
    "collections",
    "curves",
    "fonts",
    "grease_pencils",
    "hair_curves",
    "images",
    "lattices",
    "libraries",
    "lightprobes",
    "lights",
    "linestyles",
    "masks",
    "materials",
    "meshes",
    "metaballs",
    "movieclips",
    "node_groups",
    "objects",
    "paint_curves",
    "palettes",
    "particles",
    "pointclouds",
    "scenes",
    "shape_keys",
    "sounds",
    "speakers",
    "texts",
    "textures",
    "volumes",
    "worlds",
)
SOUND_SETTINGS = (
    "mute",
    "lock",
    "volume",
    "pan",
    "sound_offset",
    "show_waveform",
    "pitch_correction",
    "color_tag",
    "use_default_fade",
    "effect_fader",
    "blend_type",
    "blend_alpha",
    "use_linear_modifiers",
    "select",
    "select_left_handle",
    "select_right_handle",
)


def _parameters():
    arguments = sys.argv[sys.argv.index("--") + 1 :]
    if len(arguments) != 1:
        raise ValueError("Provide the owned case-study specification")
    path = Path(arguments[0]).resolve()
    if path.stat().st_size > MAX_PARAMETERS:
        raise ValueError("Case-study specification is too large")
    spec = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(spec, dict) or spec.get("mode") not in {"bundle", "verify"}:
        raise ValueError("Choose a case-study bundle or verification")
    scenes, media = spec.get("scenes"), spec.get("media")
    if not isinstance(scenes, list) or not scenes or not all(isinstance(s, str) for s in scenes):
        raise ValueError("Name the case-study scenes")
    if not isinstance(media, list) or not all(isinstance(item, dict) for item in media):
        raise ValueError("List the case-study media")
    return spec


def _key(value):
    return os.path.normcase(os.path.normpath(value))


def _overwrite(owner, attribute, value, filler):
    """Blender keeps fixed-size path buffers: replace an earlier value in full first."""
    setattr(owner, attribute, filler)
    setattr(owner, attribute, value)


FILE_FILLER = "_" * 1022
STRIP_FILLER = "_" * 760 + "/" + "_" * 250
DIRECTORY_FILLER = "_" * 766 + "/"
NAME_FILLER = "_" * 254


def _ids(bpy):
    for name in COLLECTIONS:
        for item in getattr(bpy.data, name, ()):
            yield item
            tree = getattr(item, "node_tree", None)
            if tree is not None:
                yield tree
            if isinstance(item, bpy.types.Scene):
                yield item.collection


def _scenario(key):
    return key.lower().lstrip("_").startswith("scenario")


def _private(owner):
    keys = []
    for key in list(owner.keys()):
        value = owner[key]
        if _scenario(key) and not (key in KEEP and isinstance(value, (str, int, float))):
            keys.append(key)
    return keys


def _settings(owner):
    """The extension's registered settings, which Blender 5 stores apart from custom ones.

    Unregistered here, they still travel with the data: composer lanes keep reference
    uploads' request and asset IDs, concept jobs and local paths; the Film form keeps
    its production and raw recipe. None of it is needed to open the review.
    """
    group = owner.bl_system_properties_get(do_create=False)
    if group is None:
        return None, []
    return group, [key for key in group.keys() if _scenario(key)]


def _remove(owner):
    for key in _private(owner):
        del owner[key]
    group, keys = _settings(owner)
    for key in keys:
        del group[key]


def _leftovers(owner, label):
    return [f"{label}:{key}" for key in _private(owner)] + [
        f"{label} setting:{key}" for key in _settings(owner)[1]
    ]


def _plain(value):
    """Copy an ID property value; groups and arrays become plain Python data."""
    if hasattr(value, "to_dict"):
        return value.to_dict()
    if hasattr(value, "to_list"):
        return value.to_list()
    return value


def _channels(bpy, animation):
    if animation is None:
        return []
    curves = list(animation.drivers)
    actions = [animation.action]
    actions += [strip.action for track in animation.nla_tracks for strip in track.strips]
    for action in actions:
        if action is None:
            continue
        if hasattr(action, "layers"):
            for layer in action.layers:
                for strip in layer.strips:
                    for bag in strip.channelbags:
                        curves.extend(bag.fcurves)
        else:
            curves.extend(action.fcurves)
    return curves


def _rebuild_sound(bpy, scene, strip, path, index):
    """Replace one sound strip so its hidden legacy path is the bundle's relative path."""
    if len(strip.modifiers) or len(getattr(strip, "retiming_keys", ())):
        raise ValueError("Remove sound strip modifiers and retiming before the case study")
    parent = strip.parent_meta()
    container = parent.strips if parent is not None else scene.sequence_editor.strips
    name, channel = strip.name, strip.channel
    timing = (strip.frame_start, strip.frame_offset_start, strip.frame_offset_end)
    expected = (strip.frame_final_start, strip.frame_final_end, channel)
    settings = {key: getattr(strip, key) for key in SOUND_SETTINGS if hasattr(strip, key)}
    private = _private(strip)
    custom = {key: _plain(strip[key]) for key in strip.keys() if key not in private}
    temporary = f"scenario-case-study-{index}"
    # Renaming moves its animation and drivers along; they come back below.
    strip.name = temporary
    mono = strip.sound.use_mono
    replacement = container.new_sound(name, path, channel, int(timing[0]))
    if replacement.name != name or replacement.sound is None:
        raise ValueError("Blender could not rebuild a case-study sound strip")
    replacement.sound.use_mono = mono
    replacement.frame_start = timing[0]
    replacement.frame_offset_start, replacement.frame_offset_end = timing[1:]
    for key, value in settings.items():
        setattr(replacement, key, value)
    for key, value in custom.items():
        replacement[key] = value
    old = f'strips_all["{bpy.utils.escape_identifier(temporary)}"]'
    new = f'strips_all["{bpy.utils.escape_identifier(name)}"]'
    for curve in _channels(bpy, scene.animation_data):
        if old in curve.data_path:
            curve.data_path = curve.data_path.replace(old, new)
    container.remove(strip)
    replacement.channel = channel
    if (
        replacement.frame_final_start,
        replacement.frame_final_end,
        replacement.channel,
    ) != expected:
        raise ValueError("Blender did not keep a rebuilt sound strip's timing")


def _bundle(bpy, spec):
    output = Path(spec["output"])
    if output.exists() or output.parent != Path(bpy.data.filepath).parent:
        raise ValueError("The case-study library must be new and beside the snapshot")
    names = {}
    for item in spec["media"]:
        if not isinstance(item.get("path"), str) or not isinstance(item.get("name"), str):
            raise ValueError("Each case-study media file needs a path and a name")
        names[_key(item["path"])] = "//" + MEDIA + "/" + item["name"]
    scenes = [bpy.data.scenes.get(name) for name in spec["scenes"]]
    if any(scene is None or scene.library is not None for scene in scenes):
        raise ValueError("The snapshot does not hold the case-study scenes")
    if len(bpy.data.libraries):
        raise ValueError("Make linked data local before exporting the case study")

    def relative(value):
        try:
            return names[_key(bpy.path.abspath(value))]
        except KeyError:
            raise ValueError("A case-study file reference was not in the approved media") from None

    counts = dict.fromkeys(
        ("recreated_sound_strips", "repacked_images", "packed_fonts", "packed_sounds"), 0
    )
    for index, image in enumerate(bpy.data.images, 1):
        if image.source in {"GENERATED", "VIEWER"} or image.type not in {"IMAGE", "MULTILAYER"}:
            continue
        if image.packed_file is not None:
            if len(image.packed_files) != 1:
                raise ValueError("Use single-file packed images in the case study")
            data = bytes(image.packed_file.data)
            suffix = Path(image.filepath_raw).suffix.lower()[:9] or ".png"
            image.unpack(method="REMOVE")
            _overwrite(image, "filepath_raw", f"//{PACKED}/{index:03d} image{suffix}", FILE_FILLER)
            image.pack(data=data, data_len=len(data))
            counts["repacked_images"] += 1
        elif image.source == "FILE":
            _overwrite(image, "filepath_raw", relative(image.filepath_raw), FILE_FILLER)
        else:
            raise ValueError("Use single-file or packed image textures in the case study")
    for index, font in enumerate(bpy.data.fonts, 1):
        if font.filepath == "<builtin>":
            continue
        if font.packed_file is not None:
            suffix = Path(font.filepath).suffix.lower()[:9] or ".ttf"
            _overwrite(font, "filepath", f"//{PACKED}/{index:03d} font{suffix}", FILE_FILLER)
            counts["packed_fonts"] += 1
        else:
            _overwrite(font, "filepath", relative(font.filepath), FILE_FILLER)
    rebuild = []
    for scene in bpy.data.scenes:
        editor = scene.sequence_editor
        for strip in tuple(editor.strips_all) if editor is not None else ():
            if strip.type in {"MOVIECLIP", "MASK"}:
                raise ValueError("Remove clip and mask strips before the case study")
            if strip.type == "MOVIE":
                _overwrite(strip, "filepath", relative(strip.filepath), STRIP_FILLER)
            elif strip.type == "IMAGE":
                directory = strip.directory
                elements = [relative(os.path.join(directory, e.filename)) for e in strip.elements]
                _overwrite(strip, "directory", "//" + MEDIA + "/", DIRECTORY_FILLER)
                for element, path in zip(strip.elements, elements, strict=True):
                    _overwrite(element, "filename", path.rsplit("/", 1)[1], NAME_FILLER)
            elif strip.type == "SOUND":
                if strip.sound is None or strip.sound.packed_file is not None:
                    raise ValueError("Unpack sound strip audio before the case study")
                rebuild.append((scene, strip, relative(strip.sound.filepath)))
    for index, sound in enumerate(bpy.data.sounds, 1):
        if sound.packed_file is not None:
            suffix = Path(sound.filepath).suffix.lower()[:9] or ".wav"
            _overwrite(sound, "filepath", f"//{PACKED}/{index:03d} sound{suffix}", FILE_FILLER)
            counts["packed_sounds"] += 1
        else:
            _overwrite(sound, "filepath", relative(sound.filepath), FILE_FILLER)
    for index, (scene, strip, path) in enumerate(rebuild, 1):
        _rebuild_sound(bpy, scene, strip, path, index)
        counts["recreated_sound_strips"] += 1
    for scene in bpy.data.scenes:
        # An absolute output folder is neither portable nor needed by the review.
        _overwrite(scene.render, "filepath", "//render/", FILE_FILLER)
        editor = scene.sequence_editor
        for strip in tuple(editor.strips_all) if editor is not None else ():
            _remove(strip)
    for owner in _ids(bpy):
        _remove(owner)
    for scene in scenes:
        for layer in scene.view_layers:
            layer.update()
    bpy.data.libraries.write(
        str(output), set(scenes), path_remap="NONE", fake_user=True, compress=False
    )
    return {"written": [scene.name for scene in scenes], "counts": counts}


def _verify(bpy, spec):
    expected = {item["name"] for item in spec["media"] if isinstance(item.get("name"), str)}
    paths = bpy.utils.blend_paths(absolute=False, packed=False, local=False)
    # Packed data appears only in the full listing; keep what the unpacked one lacks.
    every = Counter(bpy.utils.blend_paths(absolute=False, packed=True, local=False))
    every.subtract(Counter(paths))
    every = sorted(path for path, count in every.items() for _ in range(max(0, count)))
    leftovers = []
    for owner in _ids(bpy):
        leftovers += _leftovers(owner, type(owner).__name__)
    for scene in bpy.data.scenes:
        editor = scene.sequence_editor
        for strip in tuple(editor.strips_all) if editor is not None else ():
            leftovers += _leftovers(strip, "Strip")
    missing = [
        path
        for path in paths
        if not path.startswith("//" + MEDIA + "/")
        or path[len(MEDIA) + 3 :] not in expected
        or not os.path.isfile(bpy.path.abspath(path))
    ]
    return {
        "scenes": [scene.name for scene in bpy.data.scenes],
        "libraries": len(bpy.data.libraries),
        "paths": paths,
        "packed_paths": every,
        "properties": leftovers,
        "missing": missing,
    }


def main():
    import bpy

    spec = _parameters()
    report = Path(spec["report"])
    if report.exists():
        raise ValueError("The case-study report must be new")
    result = _bundle(bpy, spec) if spec["mode"] == "bundle" else _verify(bpy, spec)
    with report.open("x", encoding="utf-8") as stream:
        json.dump(result, stream)


if __name__ == "__main__":
    main()
