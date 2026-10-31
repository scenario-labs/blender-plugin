# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
from scenario.core.scene import capture_plan as cp


def test_frame_span_uses_preview_range_when_asked():
    assert cp.frame_span(1, 250, 24) == (1, 250, 250 / 24)
    assert cp.frame_span(1, 250, 24, use_preview=True, preview_start=10, preview_end=57) == (
        10,
        57,
        48 / 24,
    )


def test_choose_duration_rounds_up_and_clamps():
    allowed = (-1, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15)
    assert cp.choose_duration(2.0, allowed) == (4, "padded to the 4 s minimum")
    assert cp.choose_duration(6.2, allowed) == (7, "")
    assert cp.choose_duration(40.0, allowed) == (15, "trimmed to the 15 s maximum")
    assert cp.choose_duration(5.0, (-1,)) == (-1, "")


def test_clip_frames_for_limit():
    assert cp.clip_frames_for(15, 24, 1, 1000) == (1, 360)
    assert cp.clip_frames_for(15, 24, 1, 100) == (1, 100)


def test_tag_prompt_adds_missing_mentions_once():
    assert cp.tag_prompt("a wolf running", True, True).startswith("@video1 @image1 ")
    assert cp.tag_prompt("use @image1 as style", False, True) == "use @image1 as style"
    assert cp.tag_prompt("", True, False) == "@video1"


def test_ensure_min_frames_pads_short_clips():
    assert cp.ensure_min_frames(1, 12, 24) == (1, 96, True)
    assert cp.ensure_min_frames(10, 200, 24) == (10, 200, False)
    assert cp.ensure_min_frames(1, 48, 24, min_seconds=2.0) == (1, 48, False)


def test_clamp_duration_for_numeric_ranges():
    assert cp.clamp_duration(6.0, 5, 15) == (6, "")
    assert cp.clamp_duration(6.04, 5, 15) == (7, "")
    assert cp.clamp_duration(2.0, 5, 15) == (5, "padded to the 5 s minimum")
    assert cp.clamp_duration(30.0, 5, 15) == (15, "trimmed to the 15 s maximum")
    assert cp.clamp_duration(2.5, None, None, integer=False) == (2.5, "")


def test_capture_size_keeps_the_frame_shape_on_a_1280_long_side():
    assert cp.capture_size(1920, 1080) == (1280, 720)
    assert cp.capture_size(1080, 1920) == (720, 1280)
    assert cp.capture_size(2048, 2048) == (1280, 1280)
    assert cp.capture_size(1440, 1080) == (1280, 960)
    # A 2.39:1 frame and an uneven viewport round each side to an even pixel count.
    assert cp.capture_size(2390, 1000) == (1280, 536)
    assert cp.capture_size(1645, 1027) == (1280, 800)
    assert cp.capture_size(1027, 1645) == (800, 1280)
    assert cp.capture_size(640, 480, long_side=320) == (320, 240)


def test_capture_size_follows_the_displayed_shape_of_non_square_pixels():
    # Anamorphic 2:1 pixels show a 1920x1080 frame as 32:9.
    assert cp.capture_size(1920, 1080, pixel_aspect=(2.0, 1.0)) == (1280, 360)
    assert cp.capture_size(1080, 1080, pixel_aspect=(1.0, 2.0)) == (640, 1280)


def test_capture_size_sides_are_even_and_never_empty():
    for width in range(1, 400, 7):
        for height in (1, 3, 17, 401, 1081):
            size = cp.capture_size(width, height)
            assert max(size) == 1280
            assert all(side >= 2 and side % 2 == 0 for side in size), (width, height, size)


def test_capture_size_of_an_empty_or_invalid_frame_is_16_9():
    for frame in ((0, 720), (1280, 0), (-5, 10), (float("nan"), 10), (float("inf"), 1)):
        assert cp.capture_size(*frame) == (1280, 720), frame
    assert cp.capture_size(1920, 1080, pixel_aspect=(1.0, 0.0)) == (1280, 720)


def test_clip_label_names_each_capture_size_once():
    assert cp.clip_label(1, 48, 2.0, 24.0) == "Frames 1 to 48: 2.0 s at 24 fps"
    assert (
        cp.clip_label(1, 48, 2.0, 24.0, [(720, 1280)])
        == "Frames 1 to 48: 2.0 s at 24 fps, 720x1280"
    )
    assert (
        cp.clip_label(10, 57, 1.96, 23.976, [(720, 1280), (1280, 800), (720, 1280)])
        == "Frames 10 to 57: 2.0 s at 23.976 fps, 720x1280, 1280x800"
    )
