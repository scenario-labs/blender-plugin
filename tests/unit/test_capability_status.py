# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Capabilities without Blender application carry an explicit status, never a block."""

import pytest

from scenario.core.api import model_filter
from scenario.core.api.catalog import ModelRecord
from scenario.core.ui.capability_status import UNAPPLIED_CAPABILITIES, model_status


@pytest.mark.parametrize(
    ("capabilities", "expected"),
    [
        (["audio2txt"], "Experimental: speech-to-text result stays saved"),
        (["VIDEO23D"], "Experimental: video-to-motion result stays saved"),
        (["txt23d", "video23d"], "Experimental: video-to-motion result stays saved"),
        (
            ["audio2txt", "video23d"],
            "Experimental: speech-to-text, video-to-motion result stays saved",
        ),
        (["txt2img", "img2img"], ""),
        (["txt2audio", "3d23d"], ""),
        ([], ""),
        (None, ""),
    ],
)
def test_status_names_only_capabilities_without_application(capabilities, expected):
    assert model_status(capabilities) == expected


def test_flagged_models_stay_visible_in_the_picker():
    for capability in UNAPPLIED_CAPABILITIES:
        record = ModelRecord.from_api(
            {"id": f"model_{capability}", "name": capability, "capabilities": [capability]}
        )
        assert model_filter.visible(record), capability
        assert model_status(record.capabilities).startswith("Experimental: ")
