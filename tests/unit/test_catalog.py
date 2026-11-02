# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
import json

from conftest import FIXTURES

from scenario.core.api.catalog import ModelRecord, is_texture_model, model_kind, models_for_lane


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


def test_model_kind_names_the_most_specific_lane_of_any_catalog_record():
    def kind(model_id, *caps, tags=()):
        record = {"id": model_id, "name": model_id, "capabilities": list(caps), "tags": list(tags)}
        return model_kind(ModelRecord.from_api(record))

    assert kind("model_patina-material", "txt2img", "img2img") == "material"
    assert kind("model_scenario-texture", "txt2img", "img2img", tags=("sc:texture",)) == "material"
    assert kind("model_mesh", "img23d", "img2img") == "3d"
    assert kind("model_retexture", "3d23d") == "3d"
    assert kind("model_sfx", "video2audio") == "audio"
    assert kind("model_clip", "img2video", "img2img") == "video"
    assert kind("model_edit", "video2video") == "video"
    assert kind("model_still", "img2img") == "image"
    # Lane lists drop deprecated and trained records; the kind they produce is unchanged.
    assert kind("model_old", "img23d", tags=("deprecated:model_new",)) == "3d"
    assert kind("model_llm", "txt2txt", "img2txt") is None


def test_materials_lane_lists_patina_then_scenario_texture_then_other_texture_models():
    def record(model_id, name, caps=("txt2img", "img2img"), tags=("sc:texture",), **extra):
        raw = {"id": model_id, "name": name, "capabilities": list(caps), "tags": list(tags)}
        return ModelRecord.from_api({**raw, "type": "custom", "status": "trained", **extra})

    records = [
        record("model_ideogram-v4-tiling", "Ideogram V4 Tiling"),
        record("model_brick-texture", "Brick Texture"),
        record("model_scenario-texture", "Scenario Texture"),
        record("model_patina", "PATINA Image to Maps", caps=("img2img",), tags=()),
        record("model_patina-material", "PATINA Material"),
        # Trained texture models carry the tag too, like the "Textures - ..." LoRAs.
        record("model_textures-moss", "Textures - Moss", type="flux.1-lora"),
        record("model_texture-upscale", "Texture Upscale", tags=("texture", "tool")),
        record("model_texture-mesh", "Texture Mesh", caps=("3d23d",)),
        record("model_old-texture", "Old Texture", tags=("sc:texture", "deprecated:model_x")),
        record("model_gemini", "Gemini", tags=()),
    ]
    material = [r.id for r in models_for_lane("material", records)]
    assert material == [
        "model_patina-material",
        "model_patina",
        "model_scenario-texture",
        "model_brick-texture",
        "model_ideogram-v4-tiling",
    ]
    render = [r.id for r in models_for_lane("render_image", records)]
    assert render == ["model_gemini"]
    # Like PATINA, texture models stay in the Image lane.
    assert set(material) <= {r.id for r in models_for_lane("image", records)}
    by_id = {r.id: r for r in records}
    assert not is_texture_model(by_id["model_textures-moss"])
    assert not is_texture_model(by_id["model_texture-mesh"])
    assert model_kind(by_id["model_textures-moss"]) == "image"
    assert model_kind(by_id["model_ideogram-v4-tiling"]) == "material"
