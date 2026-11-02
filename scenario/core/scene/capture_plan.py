# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Capture sizes, frame ranges, clip durations and Seedance prompt tagging. No bpy."""

import math

MIN_CLIP_SECONDS = 4.0  # Seedance's minimum output is 4 s; a 0.5 s reference clip failed with an internal error (2026-08-28)
CAPTURE_LONG_SIDE = 1280  # pixels on the long side of every scene still and clip


def capture_size(width, height, pixel_aspect=(1.0, 1.0), long_side=CAPTURE_LONG_SIDE):
    """(width, height) in square pixels for a capture framed like a width x height frame.

    `pixel_aspect` is the frame's pixel shape (Blender's pixel aspect X and Y), so a
    frame of non-square pixels keeps the shape it is displayed with. The long side is
    `long_side` and both sides are even, as H.264 clips require. A frame without a
    positive size, such as a collapsed viewport, falls back to 16:9.
    """
    try:
        ratio = (width * pixel_aspect[0]) / (height * pixel_aspect[1])
    except (TypeError, ZeroDivisionError, IndexError):
        ratio = 0.0
    if not (math.isfinite(ratio) and ratio > 0):
        ratio = 16 / 9
    if ratio >= 1:
        return long_side, _even(long_side / ratio)
    return _even(long_side * ratio), long_side


def _even(value):
    return max(2, 2 * round(value / 2))


def clip_label(start, end, seconds, fps, sizes=()):
    """The capture line of a clip form: its frames, length, rate and each capture size."""
    text = f"Frames {start} to {end}: {seconds:.1f} s at {fps:g} fps"
    names = dict.fromkeys(f"{width}x{height}" for width, height in sizes)
    return ", ".join((text, *names))


def frame_span(
    frame_start, frame_end, fps, use_preview=False, preview_start=None, preview_end=None
):
    start, end = frame_start, frame_end
    if use_preview and preview_start is not None and preview_end is not None:
        start, end = preview_start, preview_end
    frames = max(1, end - start + 1)
    return start, end, frames / float(fps or 24)


def choose_duration(seconds, allowed_values, minimum=None):
    numeric = sorted(int(v) for v in allowed_values if isinstance(v, (int, float)) and int(v) > 0)
    if not numeric:
        return (-1 if -1 in allowed_values else None), ""
    needed = max(1, math.ceil(seconds - 1e-6))
    for value in numeric:
        if value >= needed:
            note = f"padded to the {value} s minimum" if value > needed else ""
            return value, note
    return numeric[-1], f"trimmed to the {numeric[-1]} s maximum"


def clamp_duration(seconds, minimum, maximum, integer=True):
    """Duration for a model with a numeric range (Minimax H3: 5 to 15 s): the clip length rounded up, clamped."""
    needed = math.ceil(seconds - 1e-6) if integer else round(seconds, 2)
    value = max(1, needed)
    note = ""
    if minimum is not None and value < minimum:
        value, note = minimum, f"padded to the {minimum:g} s minimum"
    if maximum is not None and value > maximum:
        value, note = maximum, f"trimmed to the {maximum:g} s maximum"
    return (int(value) if integer else float(value)), note


def ensure_min_frames(start, end, fps, min_seconds=MIN_CLIP_SECONDS):
    """Extend the end frame so the clip lasts at least `min_seconds`; returns (start, end, padded)."""
    needed = int(math.ceil(min_seconds * (fps or 24)))
    if end - start + 1 < needed:
        return start, start + needed - 1, True
    return start, end, False


def clip_frames_for(seconds_limit, fps, start, end):
    max_frames = int(seconds_limit * (fps or 24))
    if end - start + 1 > max_frames:
        end = start + max_frames - 1
    return start, end


def tag_prompt(prompt, has_video, has_image):
    prompt = (prompt or "").strip()
    tags = []
    if has_video and "@video1" not in prompt:
        tags.append("@video1")
    if has_image and "@image1" not in prompt:
        tags.append("@image1")
    return (" ".join(tags) + (" " if prompt and tags else "") + prompt).strip()
