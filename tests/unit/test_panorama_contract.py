# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Panorama model contracts against the recorded GET /models schemas."""

import copy
import json
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace

import pytest

from scenario.core.api import catalog
from scenario.core.api.catalog import ModelRecord
from scenario.core.scene import panorama_contract as contracts
from scenario.core.scene.panorama import MAX_PIXELS
from scenario.core.schema.forms import prepare_run
from scenario.core.schema.params import parse_schema, validate

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures/models"
FLUX = "model_scenario-skybox-flux"
GPT = "model_scenario-skybox-gpt"
WORLD = "model_hunyuan-world-image-to-skybox"
HDRI = "model_hdri-skybox"
UPSCALE = "model_sc-upscale-flux-skybox"
SAVED = "asset_savedpanorama"
UPSCALED = "asset_upscaledpanorama"


def raw(model_id):
    return json.loads((FIXTURES / f"{model_id}.json").read_text())["model"]


def schema(model_id, data=None):
    return parse_schema(ModelRecord.from_api(raw(model_id) if data is None else data))


def run(model_id, body, *, refs=None, data=None):
    parsed = schema(model_id, data)
    return contracts.prepare(
        contracts.CONTRACTS[model_id], parsed.specs, body, panorama_refs=refs or {}
    )


def ok(model_id, body, *, refs=None):
    """Prepare a valid request and check it also passes the schema and SDK forms."""
    prepared, errors = run(model_id, body, refs=refs)
    assert errors == []
    parsed = schema(model_id)
    assert validate(parsed.specs, prepared, parsed.one_of) == []
    target, payload = prepare_run(model_id, {"parameters": raw(model_id)["inputs"]}, prepared)
    assert target == model_id
    assert {key: payload[key] for key in prepared} == prepared
    return prepared


def saved(asset_id=SAVED, **options):
    return {asset_id: contracts.PanoramaRef(asset_id, producer=FLUX, **options)}


def test_every_contract_matches_its_recorded_public_record():
    assert contracts.PANORAMA_MODELS == (FLUX, GPT, WORLD, HDRI, UPSCALE)
    assert set(contracts.PANORAMA_MODES) == {c.mode for c in contracts.CONTRACTS.values()}
    for model_id, contract in contracts.CONTRACTS.items():
        data = raw(model_id)
        record = ModelRecord.from_api(data)
        # Plain public custom models: ordinary lane records, accepted by the
        # adapter's estimate gate and never classified as trained.
        assert (data["type"], data["privacy"], data["status"]) == ("custom", "public", "trained")
        assert not data.get("parentModelId") and not data.get("trainingImagesNumber")
        assert catalog.trained_kind(record) is None
        names = {spec.name for spec in schema(model_id).specs}
        assert contract.required_fields <= names, model_id
        _, errors = run(model_id, {})
        assert contracts.CONTRACT_CHANGED not in errors, model_id


def test_describe_never_calls_an_ldr_result_hdr():
    for contract in contracts.CONTRACTS.values():
        text = contracts.describe(contract)
        assert "World" in text
        if contract.output == "hdr":
            assert contract.mode == contracts.HDRI
            assert "HDR OpenEXR" in text
        else:
            assert "LDR" in text and "HDR" not in text
        summary = contracts.summary(contract)
        assert json.loads(json.dumps(summary)) == summary
        assert summary["mode"] == contract.mode


def test_models_for_mode_keeps_record_order_and_skips_other_models():
    records = [ModelRecord.from_api(raw(model_id)) for model_id in reversed(contracts.CONTRACTS)]
    records.append(ModelRecord.from_api({"id": "model_other", "capabilities": ["txt2img"]}))
    assert [r.id for r in contracts.models_for_mode(contracts.GENERATE, records)] == [GPT, FLUX]
    assert [r.id for r in contracts.models_for_mode(contracts.FROM_IMAGE, records)] == [WORLD]
    assert [r.id for r in contracts.models_for_mode(contracts.HDRI, records)] == [HDRI]
    assert [r.id for r in contracts.models_for_mode(contracts.UPSCALE, records)] == [UPSCALE]
    assert contracts.contract_for("model_other") is None


def test_flux_makes_one_panorama_unless_asked_and_restyles_only_saved_panoramas():
    assert ok(FLUX, {"prompt": "a forest"}) == {"prompt": "a forest", "numOutputs": 1}
    assert ok(FLUX, {"prompt": "a forest", "numOutputs": 3})["numOutputs"] == 3
    body = {"prompt": "a forest", "image": SAVED}
    assert ok(FLUX, body, refs=saved())["image"] == SAVED
    _, errors = run(FLUX, body)
    assert errors == [
        "Reference Image: use a saved, downloaded 360 panorama result from this account and project"
    ]


def test_gpt_uses_only_two_to_one_sizes_and_up_to_ten_still_references():
    assert ok(GPT, {"prompt": "a desert"}) == {"prompt": "a desert", "width": 2048, "height": 1024}
    assert ok(GPT, {"prompt": "x", "width": 3072, "height": 1536})["width"] == 3072
    assert ok(GPT, {"prompt": "x", "width": 3840.0, "height": 1920.0})["height"] == 1920
    stills = [f"asset_still{index}" for index in range(10)]
    assert ok(GPT, {"prompt": "x", "referenceImages": stills})["referenceImages"] == stills
    for body in (
        {"prompt": "x", "width": 3840, "height": 640},
        {"prompt": "x", "width": 2048},
        {"prompt": "x", "height": 1024},
        {"prompt": "x", "width": 1024, "height": 512},
    ):
        _, errors = run(GPT, body)
        assert errors == ["Choose a 2:1 panorama size: 2048x1024, 3072x1536, 3840x1920"], body
    _, errors = run(GPT, {"prompt": "x", "referenceImages": [*stills, "asset_more"]})
    assert errors == ["Reference Images: use at most 10"]


def test_hy_world_requires_one_still_of_any_saved_or_uploaded_image():
    assert ok(WORLD, {"image": "asset_capture"}) == {"image": "asset_capture"}
    assert ok(WORLD, {"image": "asset_capture", "prompt": "a harbor"})["prompt"] == "a harbor"
    _, errors = run(WORLD, {})
    assert "Image: add an image" in errors
    _, errors = run(WORLD, {"image": 5})
    assert errors == ["Image: use Scenario asset IDs"]


def test_hdri_forces_one_exr_output_and_takes_only_a_saved_panorama():
    body = ok(HDRI, {"image": SAVED}, refs=saved())
    assert body == {
        "image": SAVED,
        "outputExr": True,
        "outputHdr": False,
        "conversionCubemapCross": False,
        "conversionCubemapFaces": False,
    }
    assert ok(HDRI, {"image": SAVED, "outputHdr": False}, refs=saved()) == body
    prepared, errors = run(HDRI, {"image": SAVED, "outputHdr": True}, refs=saved())
    assert errors == ["Output HDR is fixed to False in the Environment lane"]
    assert prepared["outputHdr"] is False
    _, errors = run(HDRI, {"image": SAVED, "outputExr": 1}, refs=saved())
    assert errors == ["Output EXR is fixed to True in the Environment lane"]
    _, errors = run(HDRI, {"image": "asset_any_image"})
    assert errors == [
        "Skybox Image: use a saved, downloaded 360 panorama result from this account and project"
    ]
    _, errors = run(HDRI, {})
    assert errors == ["Skybox Image: add a saved 360 panorama"]


def test_upscale_factor_stays_within_the_world_limit():
    assert ok(UPSCALE, {"image": SAVED}, refs=saved())["upscaleFactor"] == 2
    _, errors = run(UPSCALE, {"image": SAVED, "upscaleFactor": 3}, refs=saved())
    assert errors == [
        "Scaling Factor must be at most 2 so the result stays within the 32-megapixel World limit"
    ]
    flux_sized = saved(width=1536, height=768)
    assert ok(UPSCALE, {"image": SAVED, "upscaleFactor": 5}, refs=flux_sized)["upscaleFactor"] == 5
    assert 25 * 1536 * 768 <= MAX_PIXELS < 36 * 1536 * 768
    _, errors = run(UPSCALE, {"image": SAVED, "upscaleFactor": 6}, refs=flux_sized)
    assert errors == [
        "Scaling Factor must be at most 5 so the result stays within the 32-megapixel World limit"
    ]
    largest = saved(width=3840, height=1920)
    assert ok(UPSCALE, {"image": SAVED}, refs=largest)["upscaleFactor"] == 2
    _, errors = run(UPSCALE, {"image": SAVED}, refs=saved(width=8192, height=4096))
    assert errors == ["This panorama is too large to upscale within the 32-megapixel World limit"]
    upscaled = {UPSCALED: contracts.PanoramaRef(UPSCALED, producer=UPSCALE)}
    _, errors = run(UPSCALE, {"image": UPSCALED}, refs=upscaled)
    assert errors == [
        "An upscaled panorama's size is unknown here; upscale its source panorama with a "
        "larger factor instead"
    ]
    styles = [f"asset_style{index}" for index in range(5)]
    _, errors = run(UPSCALE, {"image": SAVED, "imagePrompt": styles}, refs=saved())
    assert errors == ["Style Images: use at most 4"]
    _, errors = run(UPSCALE, {"imagePrompt": styles[:1]})
    assert errors == ["Image: add a saved 360 panorama"]


def _changed(model_id, input_name, **changes):
    data = copy.deepcopy(raw(model_id))
    for field in data["inputs"]:
        if field["name"] == input_name:
            field.update(changes)
    return data


@pytest.mark.parametrize(
    ("model_id", "data"),
    [
        (
            HDRI,
            {**raw(HDRI), "inputs": [f for f in raw(HDRI)["inputs"] if f["name"] != "outputHdr"]},
        ),
        (HDRI, _changed(HDRI, "outputHdr", type="string")),
        (HDRI, _changed(HDRI, "image", type="file_array")),
        (HDRI, _changed(HDRI, "image", kind="video")),
        (FLUX, _changed(FLUX, "numOutputs", min=2)),
        (FLUX, _changed(FLUX, "image", name="initImage")),
        (GPT, _changed(GPT, "width", step=100)),
        (GPT, _changed(GPT, "height", max=1000)),
        (GPT, _changed(GPT, "referenceImages", type="file")),
        (UPSCALE, _changed(UPSCALE, "upscaleFactor", type="string")),
        (WORLD, _changed(WORLD, "image", name="photo")),
    ],
)
def test_schema_drift_fails_closed_with_one_explicit_error(model_id, data):
    body = {"prompt": "x", "image": SAVED}
    prepared, errors = run(model_id, body, refs=saved(), data=data)
    assert errors == [contracts.CONTRACT_CHANGED]
    assert prepared == body


def test_contract_records_are_immutable_and_lane_defaults_stay_lane_scoped():
    contract = contracts.CONTRACTS[FLUX]
    with pytest.raises(AttributeError):
        contract.mode = contracts.HDRI
    assert replace(contract, defaults=()).required_fields == {"prompt", "image"}
    # Lane defaults apply only to Environment requests; the Image lane keeps the
    # schema defaults of the same models.
    for model_id in contracts.PANORAMA_MODELS:
        assert model_id not in catalog.PARAM_OVERRIDES


def _saved(
    asset_id, media_type="image/png", *, projection="equirectangular", source="asset", receipt=True
):
    asset = SimpleNamespace(
        asset_id=asset_id, media_type=media_type, projection=projection, source=source
    )
    return SimpleNamespace(asset=asset, receipt=object() if receipt else None)


def _record(target, *items):
    return SimpleNamespace(intent=SimpleNamespace(target_id=target), results=items)


def test_saved_panorama_refs_accept_only_downloaded_ldr_360_results():
    records = (
        _record(
            FLUX,
            _saved("flat"),
            _saved("pending", receipt=False),
            _saved("plain", projection=None),
            _saved("exr-file", "image/exr"),
            _saved("exr-original", "image/x-exr", source="original"),
            _saved("aces-original", "image/aces", source="original"),
        ),
        _record(UPSCALE, _saved("upscaled", "image/jpeg")),
    )
    wanted = {"flat", "pending", "plain", "exr-file", "exr-original", "aces-original", "upscaled"}
    refs = contracts.saved_panorama_refs(records, wanted)
    assert refs == {
        "flat": contracts.PanoramaRef("flat", producer=FLUX),
        "upscaled": contracts.PanoramaRef("upscaled", producer=UPSCALE),
    }
    # Only requested IDs are returned, so other saved results are never offered.
    assert contracts.saved_panorama_refs(records, {"other"}) == {}
    assert contracts.HDR_MEDIA_TYPES == {"image/exr", "image/x-exr", "image/aces"}


def test_native_wording_and_lookups_follow_the_contracts():
    assert set(contracts.MODE_DESCRIPTIONS) == set(contracts.PANORAMA_MODES)
    assert contracts.SIZE_PRESETS == contracts.CONTRACTS[GPT].sizes
    assert all(width == 2 * height for width, height in contracts.SIZE_PRESETS)
    for contract in contracts.CONTRACTS.values():
        line = contracts.result_line(contract)
        assert line.startswith("Result: ") and "World" in line
        assert ("HDR" in line) is (contract.output == "hdr")
        for rule in contract.references:
            assert contracts.reference_rule(contract, rule.param) is rule
        assert contracts.reference_rule(contract, "prompt") is None
