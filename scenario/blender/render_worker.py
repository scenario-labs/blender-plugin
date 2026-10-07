# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Standalone owned Blender render process; adapted from Studio render_worker.py.

The selected first-party source and attribution are recorded in
docs/STUDIO_ADOPTION.md. This script does not import or register the extension.
"""

import json
import sys
from pathlib import Path


def main():
    import bpy

    arguments = sys.argv[sys.argv.index("--") + 1 :]
    if len(arguments) != 1:
        raise ValueError("Provide the owned render specification")
    spec_path = Path(arguments[0]).resolve()
    if spec_path.stat().st_size > 65536:
        raise ValueError("Render specification is too large")
    spec = json.loads(spec_path.read_text(encoding="utf-8"))
    start, end = spec["frame_start"], spec["frame_end"]
    width, height = spec["width"], spec["height"]
    if (
        type(start) is not int
        or type(end) is not int
        or not 1 <= start <= end <= 1048574
        or not 1 <= end - start + 1 <= 1800
    ):
        raise ValueError("Choose one to 1800 bounded frames")
    if any(type(value) is not int or not 64 <= value <= 4096 for value in (width, height)):
        raise ValueError("Use bounded render dimensions")
    if spec["color_type"] not in {"MATERIAL", "TEXTURE", "OBJECT"}:
        raise ValueError("Choose a supported Workbench color mode")
    scene = bpy.data.scenes.get(spec["scene_name"])
    if scene is None or scene.camera is None or scene.camera not in tuple(scene.objects):
        raise ValueError("Choose a snapshot scene with its own camera")
    frames = spec_path.parent / "frames"
    if frames.is_symlink() or not frames.is_dir():
        raise ValueError("The owned frame directory is missing")
    if bpy.context.window is not None:
        bpy.context.window.scene = scene
    scene.render.engine = "BLENDER_WORKBENCH"
    scene.render.resolution_x, scene.render.resolution_y = width, height
    scene.render.resolution_percentage = 100
    if hasattr(scene.render.image_settings, "media_type"):
        scene.render.image_settings.media_type = "IMAGE"
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGB"
    scene.render.image_settings.color_depth = "8"
    scene.render.film_transparent = False
    scene.render.use_sequencer = False
    scene.render.use_compositing = False
    scene.render.use_border = False
    scene.render.use_crop_to_border = False
    scene.render.use_multiview = False
    scene.render.use_single_layer = True
    layer = scene.view_layers[0]
    layer.use = True
    scene.render.use_file_extension = True
    scene.render.use_stamp = False
    shading = scene.display.shading
    shading.light, shading.color_type = "STUDIO", spec["color_type"]
    shading.studiolight_rotate_z = 0.5
    shading.show_shadows, shading.show_cavity = True, True
    shading.cavity_type = "BOTH"
    shading.curvature_ridge_factor, shading.curvature_valley_factor = 1.2, 0.7
    shading.show_specular_highlight, shading.show_object_outline = True, False
    shading.background_type = "WORLD"
    scene.display.render_aa = "8"
    size = 0
    for index, frame in enumerate(range(start, end + 1), 1):
        path = frames / f"Frame-{index:06d}.png"
        if path.exists() or path.is_symlink():
            raise FileExistsError("Refusing to overwrite a captured frame")
        scene.frame_set(frame)
        scene.render.filepath = str(path)
        bpy.ops.render.render(write_still=True, scene=scene.name, layer=layer.name)
        size += path.stat().st_size
        if size > 2 * 1024**3:
            raise ValueError("Rendered frames exceeded the size policy")
        print(f"SCENARIO_PROGRESS {index}/{end - start + 1}", flush=True)


if __name__ == "__main__":
    main()
