# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Which input an image file dropped on the Scenario sidebar joins, without Blender."""

import pytest

from scenario.core.schema.params import ParamSpec
from scenario.core.ui import reference_drop


def spec(name, ptype="file_array", kind="image", max_length=None):
    return ParamSpec(name, name.title(), ptype, kind=kind, max_length=max_length)


SPECS = (
    spec("prompt", ptype="string", kind=None),
    spec("video", kind="video"),
    spec("mask", ptype="file"),
    spec("images", max_length=2),
)


def test_the_first_image_input_with_room_takes_the_drop():
    assert reference_drop.image_input("image", SPECS, {}) == "mask"
    assert reference_drop.image_input("image", SPECS, {"mask": 1}) == "images"
    assert reference_drop.image_input("image", SPECS, {"mask": 1, "images": 1}) == "images"
    assert reference_drop.image_input("image", SPECS, {"mask": 1, "images": 2}) is None


def test_an_input_without_a_kind_is_an_image_input_and_no_maximum_means_room():
    specs = (spec("reference", kind=None),)
    assert reference_drop.image_input("video", specs, {"reference": 40}) == "reference"


def test_inputs_of_other_kinds_never_take_an_image():
    specs = (spec("clip", kind="video"), spec("mesh", kind="3d"), spec("voice", kind="audio"))
    assert reference_drop.image_input("audio", specs, {}) is None


@pytest.mark.parametrize(
    "lane", ["render_image", "render_video", "panorama", "edit3d", "blockout", "workflow", ""]
)
def test_lanes_with_their_own_reference_rules_take_no_drop(lane):
    assert reference_drop.image_input(lane, SPECS, {}) is None


@pytest.mark.parametrize(
    ("path", "expected"),
    [
        ("/tmp/a.png", True),
        ("/tmp/A.JPG", True),
        ("/tmp/a.jpeg", True),
        ("/tmp/a.webp", True),
        ("/tmp/a.exr", False),
        ("/tmp/a.mp4", False),
        ("/tmp/png", False),
        ("", False),
        (None, False),
    ],
)
def test_only_reference_image_extensions_are_dropped(path, expected):
    assert reference_drop.is_image_file(path) is expected
