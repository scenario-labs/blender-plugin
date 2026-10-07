# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
import json

from conftest import FIXTURES

from scenario.core.api.catalog import ModelRecord, models_for_lane


def load(name):
    return json.loads((FIXTURES / "models" / f"{name}.json").read_text())


def test_model_record_from_api_reads_schema_and_lanes():
    rec = ModelRecord.from_api(load("model_patina-material")["model"])
    assert rec.id == "model_patina-material"
    assert "txt2img" in rec.capabilities
    assert len(rec.parameters) == 15
    assert rec.ui_config["selects"]["maps"]["basecolor"] == "Base Color"
    assert rec.lanes == {"image", "material", "render_image"}
    assert rec.deprecated_successor is None


def test_deprecated_tag_names_successor():
    rec = ModelRecord.from_api(
        {
            "id": "model_old",
            "name": "Old",
            "capabilities": ["img23d"],
            "tags": ["deprecated:model_new"],
        }
    )
    assert rec.deprecated_successor == "model_new"
    assert rec.lanes == {"3d"}


def test_models_for_lane_orders_curated_first_and_drops_deprecated():
    records = [
        ModelRecord.from_api({"id": "model_zeta", "name": "Zeta", "capabilities": ["txt2img"]}),
        ModelRecord.from_api(
            {
                "id": "model_google-gemini-3-1-flash",
                "name": "Gemini",
                "capabilities": ["txt2img", "img2img"],
            }
        ),
        ModelRecord.from_api(
            {
                "id": "model_old",
                "name": "Old",
                "capabilities": ["txt2img"],
                "tags": ["deprecated:model_zeta"],
            }
        ),
        ModelRecord.from_api({"id": "model_video", "name": "Vid", "capabilities": ["txt2video"]}),
        ModelRecord.from_api(
            {"id": "model_patina", "name": "Patina maps", "capabilities": ["img2img"]}
        ),
    ]
    image = [r.id for r in models_for_lane("image", records)]
    assert image[0] == "model_google-gemini-3-1-flash"
    assert "model_old" not in image and "model_video" not in image
    assert image[-1] == "model_zeta"
    assert [r.id for r in models_for_lane("material", records)] == ["model_patina"]
    assert [r.id for r in models_for_lane("video", records)] == ["model_video"]
