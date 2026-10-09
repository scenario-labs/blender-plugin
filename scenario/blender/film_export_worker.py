# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Standalone owned Blender process for Film video export and its decode check.

This first-party script follows the render_worker.py process pattern. It runs in
an offline, factory-startup child and never imports or registers the extension.
``render`` encodes one snapshot sequencer scene with Blender's built-in FFmpeg;
``verify`` decodes a finished MP4 in a fresh scene and reports what Blender saw.
"""

import json
import sys
from pathlib import Path

BLOCKED_STRIPS = frozenset({"SCENE", "MOVIECLIP", "MASK"})
MAX_SECONDS = 900


def _parameters():
    arguments = sys.argv[sys.argv.index("--") + 1 :]
    if len(arguments) != 1:
        raise ValueError("Provide the owned export specification")
    path = Path(arguments[0]).resolve()
    if path.stat().st_size > 65536:
        raise ValueError("Export specification is too large")
    spec = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(spec, dict) or spec.get("mode") not in {"render", "verify"}:
        raise ValueError("Choose an export render or verification")
    width, height, fps = spec["width"], spec["height"], spec["fps"]
    if any(
        type(value) is not int or not 64 <= value <= 4096 or value % 2 for value in (width, height)
    ):
        raise ValueError("Use even export dimensions from 64 to 4096 pixels")
    if type(fps) is not int or not 1 <= fps <= 120:
        raise ValueError("Use an integer export frame rate from 1 to 120")
    if type(spec["audio"]) is not bool:
        raise ValueError("Choose whether the export includes audio")
    return path, spec


def _require_encoder(bpy):
    # Blender lists every codec whether or not its FFmpeg libraries can encode
    # it, so only a build without FFmpeg is detectable here. A missing H.264 or
    # AAC encoder fails inside the render below; its log stays in staging.
    if not bpy.app.ffmpeg.supported:
        raise RuntimeError("This Blender build cannot encode video")


def _render(bpy, path, spec):
    start, end, fps = spec["frame_start"], spec["frame_end"], spec["fps"]
    if (
        type(start) is not int
        or type(end) is not int
        or not 1 <= start <= end <= 1048574
        or end - start + 1 > min(108000, MAX_SECONDS * fps)
    ):
        raise ValueError("Export at most fifteen minutes of positive frames")
    _require_encoder(bpy)
    scene = bpy.data.scenes.get(spec["scene_name"])
    if scene is None or scene.library is not None or scene.sequence_editor is None:
        raise ValueError("Choose a snapshot scene with sequencer strips")
    strips = tuple(scene.sequence_editor.strips_all)
    if not strips or any(strip.type in BLOCKED_STRIPS for strip in strips):
        raise ValueError("Export only movie, sound, image, text and effect strips")
    output = path.parent / "output"
    if output.is_symlink() or not output.is_dir() or any(output.iterdir()):
        raise ValueError("The owned export output directory must be new and empty")
    if bpy.context.window is not None:
        bpy.context.window.scene = scene
    render = scene.render
    render.use_sequencer = True
    render.use_compositing = False
    render.use_stamp = False
    render.use_border = False
    render.use_crop_to_border = False
    render.use_multiview = False
    render.film_transparent = False
    render.resolution_x, render.resolution_y = spec["width"], spec["height"]
    render.resolution_percentage = 100
    render.pixel_aspect_x = render.pixel_aspect_y = 1.0
    render.fps, render.fps_base = fps, 1.0
    render.frame_map_old = render.frame_map_new = 100
    scene.frame_start, scene.frame_end, scene.frame_step = start, end, 1
    image = render.image_settings
    if hasattr(image, "media_type"):
        image.media_type = "VIDEO"
    image.file_format = "FFMPEG"
    image.color_mode = "RGB"
    ffmpeg = render.ffmpeg
    ffmpeg.format = "MPEG4"
    ffmpeg.codec = "H264"
    # 8-bit 4:2:0 is the verified output; never inherit the scene's 10-bit depth.
    image.color_depth = "8"
    ffmpeg.constant_rate_factor = "HIGH"
    ffmpeg.ffmpeg_preset = "GOOD"
    ffmpeg.use_autosplit = False
    ffmpeg.use_lossless_output = False
    if spec["audio"]:
        ffmpeg.audio_codec = "AAC"
        ffmpeg.audio_channels = "STEREO"
        ffmpeg.audio_mixrate = 48000
        ffmpeg.audio_bitrate = 192
        ffmpeg.audio_volume = 1.0
    else:
        ffmpeg.audio_codec = "NONE"
    render.use_file_extension = False
    render.filepath = str(output / "film.mp4")
    total = end - start + 1
    step = max(1, total // 100)
    rendered = [0]

    def report(*_):
        rendered[0] += 1
        if rendered[0] % step == 0 or rendered[0] == total:
            print(f"SCENARIO_PROGRESS {min(rendered[0], total)}/{total}", flush=True)

    bpy.app.handlers.render_post.append(report)
    try:
        result = bpy.ops.render.render(animation=True, scene=scene.name)
    finally:
        bpy.app.handlers.render_post.remove(report)
    if "FINISHED" not in result:
        raise RuntimeError("Blender did not finish the video export")


def _duration(strip):
    # Blender 5.1 deprecates frame_duration in favour of content_duration.
    if hasattr(strip, "content_duration"):
        return strip.content_duration
    return strip.frame_duration


def _pixels(bpy, path):
    image = bpy.data.images.load(str(path), check_existing=False)
    try:
        return tuple(round(value * 255) for value in image.pixels[:])
    finally:
        bpy.data.images.remove(image)


def _verify(bpy, path, spec):
    frames = spec["frames"]
    if type(frames) is not int or not 1 <= frames <= min(108000, MAX_SECONDS * spec["fps"]):
        raise ValueError("Verify at most fifteen minutes of positive frames")
    video = Path(spec["video"])
    if not video.is_absolute() or video.is_symlink() or not video.is_file():
        raise ValueError("Verify one owned regular MP4 file")
    # Use the factory context scene: frame changes on other scenes are not
    # reliably applied to background still renders.
    scene = bpy.context.scene
    render = scene.render
    render.fps, render.fps_base = spec["fps"], 1.0
    render.resolution_x, render.resolution_y = spec["width"], spec["height"]
    render.resolution_percentage = max(1, min(100, 12800 // max(spec["width"], spec["height"])))
    render.use_sequencer = True
    render.use_compositing = False
    render.use_stamp = False
    image = render.image_settings
    if hasattr(image, "media_type"):
        image.media_type = "IMAGE"
    image.file_format = "PNG"
    image.color_mode = "RGBA"
    editor = scene.sequence_editor_create()
    # A sentinel below the opaque movie stays hidden only when Blender decodes
    # the movie frame; two sentinel colors make the comparison content-independent.
    sentinel = editor.strips.new_effect("Sentinel", "COLOR", 1, 1, length=frames)
    movie = editor.strips.new_movie("Export", str(video), 2, 1, fit_method="FILL")
    measured = {
        "width": movie.elements[0].orig_width if movie.elements else 0,
        "height": movie.elements[0].orig_height if movie.elements else 0,
        "fps": movie.fps,
        "frames": _duration(movie),
        "sound": None,
    }
    try:
        sound = editor.strips.new_sound("Export audio", str(video), 3, 1)
    except RuntimeError:
        sound = None
    if sound is not None and sound.sound is not None:
        measured["sound"] = {
            "frames": _duration(sound),
            "rate": sound.sound.samplerate,
            "channels": sound.sound.channels,
        }
        sound.mute = True
    scene.frame_start, scene.frame_end = 1, frames
    decoded = []
    for index, frame in enumerate((1, frames)):
        renders = []
        for shade, color in enumerate(((1.0, 0.0, 1.0), (0.0, 1.0, 0.0))):
            target = path.parent / f"decoded-{index}-{shade}.png"
            if target.exists() or target.is_symlink():
                raise FileExistsError("Refusing to overwrite a decoded verification frame")
            sentinel.color = color
            scene.frame_current = frame
            render.filepath = str(target)
            result = bpy.ops.render.render(write_still=True, scene=scene.name)
            if "FINISHED" not in result or not target.is_file():
                raise RuntimeError("Blender could not render the verification frame")
            renders.append(_pixels(bpy, target))
        decoded.append(renders[0] == renders[1])
    measured["decoded"] = decoded
    (path.parent / "measured.json").write_text(json.dumps(measured), encoding="utf-8")


def main():
    import bpy

    path, spec = _parameters()
    if spec["mode"] == "render":
        _render(bpy, path, spec)
    else:
        _verify(bpy, path, spec)


if __name__ == "__main__":
    main()
