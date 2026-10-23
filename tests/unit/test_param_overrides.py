# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
from scenario.core.api import catalog
from scenario.core.api.catalog import ModelRecord, param_override, starting_value
from scenario.core.schema.params import parse_schema

P2 = "model_tripo-p2-image-to-3d"
# The inputs of the live model description that the starting values touch, as REST sends them.
P2_INPUTS = [
    {"name": "image", "type": "file", "kind": "image", "required": True},
    {"name": "pbr", "type": "boolean", "default": True},
    {"name": "faceLimit", "type": "number", "min": 48, "max": 50000},
    {"name": "autoSize", "type": "boolean", "default": False},
    {"name": "quad", "type": "boolean", "default": False, "costImpact": True},
]


def p2_schema(inputs=P2_INPUTS):
    record = ModelRecord.from_api(
        {"id": P2, "name": "Tripo P2", "capabilities": ["img23d"], "inputs": inputs}
    )
    return parse_schema(record)


def test_rodin_material_defaults_to_pbr_only_for_rodin():
    assert param_override("model_rodin-hyper3d-v2-5-text-to-3d", "material") == "PBR"
    assert param_override("model_rodin-hyper3d-v2-5", "material") == "PBR"
    assert param_override("model_meshy-7-txt23d", "material") is None


def test_tripo_p2_starts_at_real_size_with_a_mesh_light_enough_to_rig():
    schema = p2_schema()
    assert starting_value(P2, schema.by_name("autoSize")) is True
    assert starting_value(P2, schema.by_name("faceLimit")) == 50000
    # Only the two curated settings change; the others keep the schema's own start.
    assert starting_value(P2, schema.by_name("pbr")) is None
    assert starting_value(P2, schema.by_name("quad")) is None
    assert starting_value(P2, schema.by_name("image")) is None


def test_tripo_p2_start_stays_within_the_models_own_face_limit():
    # 50,000 is the model's maximum; the form must never start above what the schema allows.
    face_limit = p2_schema().by_name("faceLimit")
    assert face_limit.max == catalog.PARAM_OVERRIDES[P2]["faceLimit"]


def test_a_start_the_current_schema_no_longer_accepts_is_not_used():
    schema = p2_schema(
        [
            {"name": "faceLimit", "type": "number", "min": 48, "max": 25000},
            {"name": "autoSize", "type": "string", "allowedValues": ["off", "on"]},
        ]
    )
    assert starting_value(P2, schema.by_name("faceLimit")) is None
    assert starting_value(P2, schema.by_name("autoSize")) is None


def test_starting_values_belong_to_their_model():
    schema = p2_schema()
    assert starting_value("model_tripo-v3-1-image-to-3d", schema.by_name("autoSize")) is None
    assert starting_value("model_tripo-v3-1-image-to-3d", schema.by_name("faceLimit")) is None


def test_tripo_p2_is_the_first_image_to_3d_default_and_3_1_stays_available():
    curated = catalog.DEFAULT_MODELS["3d"]
    assert curated.index(P2) < curated.index("model_tripo-v3-1-image-to-3d")
    records = [
        ModelRecord.from_api(
            {"id": model_id, "name": model_id, "capabilities": ["img23d"], "status": "trained"}
        )
        for model_id in (
            "model_tripo-v3-1-image-to-3d",
            "model_meshy-7-1-img23d",
            P2,
        )
    ]
    got = [r.id for r in catalog.models_for_lane("3d", records)]
    assert got[0] == P2
    assert "model_tripo-v3-1-image-to-3d" in got


P2_TEXT = "model_tripo-p2-text-to-3d"


def p2_text_schema():
    record = ModelRecord.from_api(
        {
            "id": P2_TEXT,
            "name": "Tripo P2 Text to 3D",
            "capabilities": ["txt23d"],
            "inputs": [
                {"name": "prompt", "type": "string", "required": True},
                *P2_INPUTS[1:],
            ],
        }
    )
    return parse_schema(record)


def test_tripo_p2_text_starts_a_prop_at_real_size_with_a_light_mesh():
    schema = p2_text_schema()
    assert starting_value(P2_TEXT, schema.by_name("autoSize")) is True
    assert starting_value(P2_TEXT, schema.by_name("faceLimit")) == 50000
    assert schema.by_name("faceLimit").max == catalog.PARAM_OVERRIDES[P2_TEXT]["faceLimit"]
    # PBR is already the schema's own start; the prompt and quad mesh keep theirs.
    assert starting_value(P2_TEXT, schema.by_name("pbr")) is None
    assert starting_value(P2_TEXT, schema.by_name("quad")) is None
    assert starting_value(P2_TEXT, schema.by_name("prompt")) is None


def test_tripo_p2_text_is_the_first_text_to_3d_default_and_the_others_stay_listed():
    others = ("model_meshy-7-1-txt23d", "model_rodin-hyper3d-v2-5-text-to-3d")
    curated = catalog.DEFAULT_MODELS["3d"]
    assert curated[0] == P2_TEXT
    records = [
        ModelRecord.from_api(
            {"id": model_id, "name": model_id, "capabilities": ["txt23d"], "status": "trained"}
        )
        for model_id in (*others, P2_TEXT)
    ]
    got = [r.id for r in catalog.models_for_lane("3d", records)]
    assert got == [P2_TEXT, *others]
