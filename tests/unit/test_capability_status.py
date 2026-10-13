# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Capabilities whose result handling is not accepted carry an explicit status, never a block."""

import pytest

from scenario.core.api import model_filter
from scenario.core.api.catalog import ModelRecord
from scenario.core.ui.capability_status import UNACCEPTED_CAPABILITIES, label, model_status

# Words that read as a refusal or a missing capability, although these models run.
REFUSALS = ("not accepted", "refused", "unsupported", "not supported", "cannot", "unavailable")


@pytest.mark.parametrize(
    ("capabilities", "expected"),
    [
        (["audio2txt"], "Experimental: speech-to-text in testing"),
        (["VIDEO23D"], "Experimental: video-to-motion in testing"),
        (["txt23d", "video23d"], "Experimental: video-to-motion in testing"),
        (
            ["audio2txt", "video23d"],
            "Experimental: speech-to-text, video-to-motion in testing",
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
    # Generic import is offered by file type, so a returned model or media file
    # may still import; the status must not claim it cannot be applied.
    for capability in UNACCEPTED_CAPABILITIES:
        status = model_status([capability]).lower()
        assert status.endswith(" in testing"), status
        for claim in ("cannot", "saved", "without", "application"):
            assert claim not in status, (capability, claim)


@pytest.mark.parametrize("subject", [*UNACCEPTED_CAPABILITIES.values(), "LoRAs and compositions"])
def test_every_status_reads_as_experimental_never_as_a_refusal(subject):
    # The trained-model line uses the same wording ("LoRAs and compositions"); "not accepted"
    # read as if the service refused a model that runs.
    status = label(subject)
    assert status == f"Experimental: {subject} in testing"
    for refusal in REFUSALS:
        assert refusal not in status.lower(), (subject, refusal)


def test_flagged_models_stay_visible_in_the_picker():
    for capability in UNACCEPTED_CAPABILITIES:
        record = ModelRecord.from_api(
            {"id": f"model_{capability}", "name": capability, "capabilities": [capability]}
        )
        assert model_filter.visible(record), capability
        assert model_status(record.capabilities).startswith("Experimental: ")
