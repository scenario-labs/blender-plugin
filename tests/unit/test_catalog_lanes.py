# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Lane filters added in 0.6.0: Render Image, Render Video, Edit 3D."""

import typing

from scenario.core.api import catalog


def rec(model_id, name, caps, tags=(), inputs=(), desc=""):
    return catalog.ModelRecord.from_api(
        {
            "id": model_id,
            "name": name,
            "capabilities": list(caps),
            "tags": list(tags),
            "status": "trained",
            "inputs": list(inputs),
            "shortDescription": desc,
        }
    )


RECORDS = [
    rec(
        "model_google-gemini-3-1-flash",
        "Gemini 3.1",
        ["txt2img", "img2img", "video2img"],
        ["sc:featured"],
    ),
    rec("model_bria-remove-background", "Bria Remove Background", ["img2img"]),
    rec("model_patina-material", "PATINA Material", ["txt2img", "img2img"]),
    rec("model_some-lora", "Cartoon Backgrounds 2.0", ["txt2img", "img2img"], ["sc:scenario"]),
    rec("model_scenario-llm", "Scenario LLM", ["txt2txt", "img2txt"], ["tool"]),
    rec("model_bytedance-seedance-2-0", "Seedance 2.0", ["txt2video", "img2video", "video2video"]),
    rec("model_minimax-h3", "Minimax H3", ["txt2video", "img2video", "video2video"]),
    rec("model_kling-v3-i2v-pro", "Kling V3 I2V Pro", ["img2video"]),
    rec(
        "model_meshy-7-retexture",
        "Meshy 7 - Retexture",
        ["3d23d"],
        inputs=[
            {"name": "model", "type": "file", "kind": "3d"},
            {"name": "imageStyle", "type": "file", "kind": "image"},
        ],
    ),
    rec(
        "model_tripo-retopology",
        "Tripo Retopology",
        ["3d23d"],
        inputs=[{"name": "model", "type": "file", "kind": "3d"}],
    ),
    rec(
        "model_tencent-uv-unwrapping",
        "Tencent UV Unwrapping",
        ["3d23d"],
        inputs=[{"name": "file3d", "type": "file", "kind": "3d"}],
    ),
    rec("model_meshy-7-txt23d", "Meshy 7 - Text-to-3D", ["txt23d"]),
]


def ids(records):
    return [r.id for r in records]


def test_render_image_lane_keeps_edit_models_and_drops_utilities_and_patina():
    got = ids(catalog.models_for_lane("render_image", RECORDS))
    assert got[0] == "model_google-gemini-3-1-flash"
    assert "model_some-lora" in got
    assert "model_bria-remove-background" not in got
    assert "model_patina-material" not in got
    assert "model_scenario-llm" not in got


def test_render_video_lane_needs_a_video_input():
    got = ids(catalog.models_for_lane("render_video", RECORDS))
    assert got[:2] == ["model_bytedance-seedance-2-0", "model_minimax-h3"]
    assert "model_kling-v3-i2v-pro" not in got


def test_edit3d_lane_and_tasks():
    assert ids(catalog.models_for_lane("edit3d", RECORDS)) == [
        "model_meshy-7-retexture",
        "model_tripo-retopology",
        "model_tencent-uv-unwrapping",
    ]
    assert ids(catalog.edit3d_models("RETEXTURE", RECORDS)) == ["model_meshy-7-retexture"]
    assert ids(catalog.edit3d_models("REMESH", RECORDS)) == ["model_tripo-retopology"]
    assert ids(catalog.edit3d_models("UV", RECORDS)) == ["model_tencent-uv-unwrapping"]
    assert ids(catalog.edit3d_models("RIG", RECORDS)) == []
    assert len(catalog.edit3d_models("ALL", RECORDS)) == 3
    assert (
        "model_rodin-hyper3d-bang" in catalog.edit3d_task("PARTS")[3]
        and "model_rodin-hyper3d-bang" in catalog.edit3d_task("RETEXTURE")[3]
    )
    assert catalog.edit3d_task("REMESH")[1] == "Remesh"
    assert catalog.edit3d_task("nope")[0] == "ALL"


def test_mesh_param_and_tagged_models():
    assert catalog.mesh_param(RECORDS[8]) == "model"
    assert catalog.mesh_param(RECORDS[10]) == "file3d"
    assert catalog.mesh_param(RECORDS[0]) is None
    assert catalog.tagged_video_model("model_bytedance-seedance-2-0-mini")
    assert not catalog.tagged_video_model("model_minimax-h3")


def test_every_curated_edit3d_model_belongs_to_a_task():
    tasked = {m for task in catalog.EDIT3D_TASKS for m in task[3]}
    assert set(catalog.DEFAULT_MODELS["edit3d"]) <= tasked


def test_trained_records_are_excluded_from_every_lane():
    lora = catalog.ModelRecord.from_api(
        {
            "id": "model_lora1",
            "name": "Cartoon Backgrounds 2.0",
            "type": "flux.1-lora",
            "capabilities": ["txt2img", "img2img"],
            "tags": ["sc:scenario"],
            "status": "trained",
        }
    )
    trained = catalog.ModelRecord.from_api(
        {
            "id": "model_lora2",
            "name": "Neo3D Realism",
            "type": "custom",
            "capabilities": ["txt2img"],
            "parentModelId": "model_flux",
            "status": "trained",
        }
    )
    composition = catalog.ModelRecord.from_api(
        {
            "id": "model_mix",
            "name": "Mix",
            "type": "flux.1-composition",
            "capabilities": ["txt2img"],
            "concepts": [{"modelId": "model_lora1", "scale": 0.5}],
            "status": "trained",
        }
    )
    private = catalog.ModelRecord.from_api(
        {
            "id": "model_private",
            "name": "Team model",
            "type": "custom",
            "privacy": "private",
            "capabilities": ["txt2img"],
            "status": "trained",
        }
    )
    kinds = [catalog.trained_kind(r) for r in (lora, trained, composition, private)]
    assert kinds == ["lora", "unsupported", "composition", "custom_private"]
    assert all(catalog.is_trained(r) for r in (lora, trained, composition, private))
    assert not catalog.is_trained(RECORDS[0])
    got = ids(catalog.models_for_lane("image", RECORDS + [lora, trained, composition, private]))
    assert got == ids(catalog.models_for_lane("image", RECORDS))
    assert "model_lora1" not in ids(catalog.models_for_lane("render_image", RECORDS + [lora]))


def _sdk_model_types():
    from scenario_sdk.types import (
        model_get_bulk_response,
        model_list_response,
        model_retrieve_response,
    )

    models = (
        model_retrieve_response.Model,
        model_get_bulk_response.Model,
        model_list_response.ModelListResponse,
    )
    found = [set(typing.get_args(model.model_fields["type"].annotation)) for model in models]
    assert found[0] == found[1] == found[2]
    return found[0]


# Pinned scenario-sdk 2.2.0 model type literals. An SDK upgrade that changes this set needs a
# classification review before the expected kinds below are updated.
SDK_LORA_TYPES = {
    "flux.1-kontext-lora",
    "flux.1-krea-lora",
    "flux.1-lora",
    "flux.2-dev-edit-lora",
    "flux.2-dev-lora",
    "flux.2-klein-4b-edit-lora",
    "flux.2-klein-4b-lora",
    "flux.2-klein-9b-edit-lora",
    "flux.2-klein-9b-lora",
    "flux.2-klein-base-4b-edit-lora",
    "flux.2-klein-base-4b-lora",
    "flux.2-klein-base-9b-edit-lora",
    "flux.2-klein-base-9b-lora",
    "qwen-image-2512-lora",
    "qwen-image-edit-2509-lora",
    "qwen-image-edit-2511-lora",
    "qwen-image-edit-lora",
    "qwen-image-lora",
    "zimage-de-turbo-lora",
    "zimage-lora",
    "zimage-turbo-lora",
}
SDK_UNSUPPORTED_TYPES = {
    "elevenlabs-voice",
    "flux.1",
    "flux.1-kontext-dev",
    "flux.1-krea-dev",
    "flux.1-pro",
    "flux.1.1-pro-ultra",
    "flux1.1-pro",
    "gpt-image-1",
}


def test_trained_kind_classifies_every_pinned_sdk_model_type():
    assert _sdk_model_types() == SDK_LORA_TYPES | SDK_UNSUPPORTED_TYPES | {
        "flux.1-composition",
        "custom",
    }
    for model_type in _sdk_model_types():
        for privacy in ("public", "private"):
            record = catalog.ModelRecord.from_api(
                {"id": "m", "type": model_type, "privacy": privacy}
            )
            if model_type in SDK_LORA_TYPES:
                expected = "lora"
            elif model_type == "flux.1-composition":
                expected = "composition"
            elif model_type == "custom":
                expected = "custom_private" if privacy == "private" else None
            else:
                expected = "unsupported"
            assert catalog.trained_kind(record) == expected, (model_type, privacy)


def test_custom_lineage_and_unknown_types_are_unsupported_not_routes():
    for raw in (
        {"type": "custom", "trainingImagesNumber": 12},
        {"type": "custom", "concepts": [{"modelId": "model_lora1"}]},
        {"type": "custom", "parentModelId": "model_base", "privacy": "private"},
        {"type": "future-model-type"},
    ):
        assert (
            catalog.trained_kind(catalog.ModelRecord.from_api({"id": "m", **raw})) == "unsupported"
        )
    for raw in (
        {},
        {"type": "custom", "trainingImagesNumber": 0},
        {"type": "custom", "privacy": "unlisted"},
    ):
        assert catalog.trained_kind(catalog.ModelRecord.from_api({"id": "m", **raw})) is None


def test_trained_models_lists_private_scope_then_public_loras_once():
    def record(model_id, model_type, privacy):
        return catalog.ModelRecord.from_api(
            {"id": model_id, "type": model_type, "privacy": privacy}
        )

    private = [
        record("private-lora", "flux.1-lora", "private"),
        record("private-mix", "flux.1-composition", "private"),
        record("private-custom", "custom", "private"),
        record("unlisted-custom", "custom", "unlisted"),
        record("voice", "elevenlabs-voice", "private"),
        record("private-lora", "flux.1-lora", "private"),
    ]
    public = [
        record("base", "custom", "public"),
        record("public-lora", "qwen-image-lora", "public"),
        record("public-mix", "flux.1-composition", "public"),
        record("hosted", "flux.1-pro", "public"),
        record("private-lora", "flux.1-lora", "public"),
    ]
    pairs = catalog.trained_models(private, public)
    assert [(kind, r.id) for kind, r in pairs] == [
        ("lora", "private-lora"),
        ("composition", "private-mix"),
        ("custom_private", "private-custom"),
        ("custom_private", "unlisted-custom"),
        ("unsupported", "voice"),
        ("lora", "public-lora"),
        ("composition", "public-mix"),
    ]
    assert pairs[0][1].privacy == "private"
    assert catalog.trained_models([], []) == []


def test_audio_lane_lists_speech_music_and_sfx_models():
    music = rec("model_elevenlabs-music-v2", "ElevenLabs Music v2", ["txt2audio"])
    cover = rec("model_minimax-music-cover", "Minimax Music Cover", ["audio2audio"])
    got = ids(catalog.models_for_lane("audio", RECORDS + [music, cover]))
    assert got == ["model_elevenlabs-music-v2", "model_minimax-music-cover"]
    assert "model_google-gemini-3-1-flash" not in got
    assert catalog.DEFAULT_MODELS["render_image"][0] == "model_openai-gpt-image-2"
