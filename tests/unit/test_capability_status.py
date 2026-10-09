# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Capabilities whose result handling is not accepted carry an explicit status, never a block."""

import pytest

from scenario.core.api import model_filter
from scenario.core.api.catalog import ModelRecord
from scenario.core.ui.capability_status import UNACCEPTED_CAPABILITIES, model_status


@pytest.mark.parametrize(
    ("capabilities", "expected"),
    [
        (["audio2txt"], "Experimental: speech-to-text not accepted"),
        (["VIDEO23D"], "Experimental: video-to-motion not accepted"),
        (["txt23d", "video23d"], "Experimental: video-to-motion not accepted"),
        (
            ["audio2txt", "video23d"],
            "Experimental: speech-to-text, video-to-motion not accepted",
        ),
        (["txt2img", "img2img"], ""),
        (["txt2audio", "3d23d"], ""),
        ([], ""),
        (None, ""),
    ],
)
def test_status_names_only_unaccepted_capabilities(capabilities, expected):
    assert model_status(capabilities) == expected


def test_status_claims_acceptance_only_not_missing_application():
    # Generic import is offered by file type, so a returned GLB or media file
    # may still import; the status must not claim it cannot be applied.
    for capability in UNACCEPTED_CAPABILITIES:
        status = model_status([capability]).lower()
        assert status.endswith(" not accepted"), status
        for claim in ("cannot", "saved", "without", "application"):
            assert claim not in status, (capability, claim)


def test_flagged_models_stay_visible_in_the_picker():
    for capability in UNACCEPTED_CAPABILITIES:
        record = ModelRecord.from_api(
            {"id": f"model_{capability}", "name": capability, "capabilities": [capability]}
        )
        assert model_filter.visible(record), capability
        assert model_status(record.capabilities).startswith("Experimental: ")
