# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""The committed monthly smoke plan, its case selection and its fixed total cap."""

import json
from decimal import Decimal
from pathlib import Path

import httpx
import pytest

from scenario.core.config import Credentials
from tools import smoke_ci as ci
from tools import smoke_image as model
from tools import smoke_inputs as inputs
from tools import smoke_suite as suite
from tools.dev_config import LiveSettings

ROOT = Path(__file__).resolve().parents[2]
MODELS = ROOT / "tests" / "fixtures" / "models"
DEFAULT_SCOPE = LiveSettings(Credentials("fixture-key", "fixture-secret"))
REFERENCE = (
    "tests/fixtures/synthetic/reference-toadstool-512.png",
    "b70e8debff0ba0fc7dd8823a9a38229600e3fd7b8f22a1a32c490b4310182e02",
)
# The text-to-speech model has no recorded fixture; these are its live field names.
SPEECH = {
    "id": "model_google-gemini-3-8-flash-lite-tts",
    "type": "custom",
    "inputs": [
        {"name": "text", "type": "string", "required": True},
        {"name": "language", "type": "string", "default": "en-US"},
    ],
}


def monthly_plan():
    return json.loads(ci.MONTHLY_PLAN.read_bytes())


def cases_by_kind():
    return {case["result_kind"]: case for case in monthly_plan()["cases"]}


def test_monthly_cap_is_the_reviewed_40_cu():
    assert ci.MONTHLY_MAX_CU == Decimal("40")
    assert ci.MONTHLY_PLAN == ROOT / "tests" / "smoke" / "monthly-plan.json"


def test_monthly_plan_is_a_reference_plan_for_the_default_scope_only():
    plan = monthly_plan()
    entries = inputs.validate(plan, DEFAULT_SCOPE)
    assert [(entry["file"], entry["sha256"]) for entry in entries] == [REFERENCE]
    assert [(entry["kind"], entry["content_type"]) for entry in entries] == [("image", "image/png")]
    # A public plan names reviewed repository files, never imported assets or projects.
    assert plan["project_id"] is None
    assert "asset_" not in ci.MONTHLY_PLAN.read_text()
    with pytest.raises(model.SmokeError, match="selected test project"):
        inputs.validate(plan, LiveSettings(DEFAULT_SCOPE.credentials, "configured-project"))


def test_monthly_cases_are_one_reference_image_plus_cheap_download_checks():
    kinds = [case["result_kind"] for case in monthly_plan()["cases"]]
    assert kinds == ["image", "material", "audio"]
    selected = cases_by_kind()
    # The only image case also exercises the reference upload path.
    assert selected["image"]["parameters"]["referenceImages"] == [{"$input": "reference"}]
    # The material case downloads and checks every supported texture role.
    assert selected["material"]["parameters"]["maps"] == list(model.MATERIAL_MAP_ROLES)
    assert selected["material"]["parameters"]["width"] == 512
    assert selected["image"]["parameters"]["resolution"] == "512"


def test_monthly_reference_file_matches_its_reviewed_digest():
    entries = inputs.validate(monthly_plan(), DEFAULT_SCOPE)
    if not (ROOT / REFERENCE[0]).is_file():
        pytest.skip("The committed reference image arrives with #381")
    paths = inputs.source_paths(entries, ROOT)
    assert model.digest(paths["reference"].read_bytes()) == REFERENCE[1]


def budget_run(tmp_path, costs, cap):
    """Run the monthly cases through budget-run with recorded schemas and no paid call."""
    schemas = {
        "model_google-gemini-3-1-flash": json.loads(
            (MODELS / "model_google-gemini-3-1-flash.json").read_text()
        ),
        "model_patina-material": json.loads((MODELS / "model_patina-material.json").read_text()),
        SPEECH["id"]: {"model": SPEECH},
    }
    resolved = inputs.resolve(monthly_plan()["cases"], {"reference": "asset-fixture"}, set())
    plan = tmp_path / "plan.json"
    plan.write_bytes(model.json_bytes({"schema_version": 1, "project_id": None, "cases": resolved}))
    quoted, submitted = [], []

    def handler(request):
        assert "projectId" not in request.url.params
        identifier = request.url.path.rsplit("/", 1)[1]
        if request.method == "GET":
            return httpx.Response(200, json=schemas[identifier])
        assert request.url.params.get("dryRun") == "true", "Quotes never submit"
        quoted.append((identifier, json.loads(request.content)))
        return httpx.Response(200, content='{"creativeUnitsCost":' + costs[identifier] + "}")

    def execute(args, settings):
        if args.command == "quote":
            return model.execute(args, settings, transport=httpx.MockTransport(handler))
        submitted.append((args.run_dir.name, args.approved_cost, args.max_cu))
        return 0

    root = tmp_path / "suite"
    argv = ["budget-run", "--plan", str(plan), "--run-dir", str(root), "--max-cu", cap]
    result = suite.run(suite.parser().parse_args(argv), DEFAULT_SCOPE, execute=execute)
    return result, root, quoted, submitted


def test_quoted_monthly_cases_fit_the_cap_and_submit_each_exact_quote(tmp_path):
    costs = {
        "model_google-gemini-3-1-flash": "10.75",
        "model_patina-material": "7.75",
        "model_google-gemini-3-8-flash-lite-tts": "1",
    }
    result, root, quoted, submitted = budget_run(tmp_path, costs, format(ci.MONTHLY_MAX_CU, "f"))
    assert result == 0
    assert [identifier for identifier, _ in quoted] == list(costs)
    assert quoted[0][1]["referenceImages"] == ["asset-fixture"]
    assert json.loads((root / "suite.json").read_bytes())["total_cost"] == "19.50"
    assert submitted == [
        ("image", Decimal("10.75"), Decimal("10.75")),
        ("material", Decimal("7.75"), Decimal("7.75")),
        ("audio", Decimal("1"), Decimal("1")),
    ]


@pytest.mark.parametrize(
    "image,allowed", [("31.25", True), ("31.2500000000000000000000000000001", False)]
)
def test_monthly_total_above_the_cap_submits_nothing(tmp_path, image, allowed):
    costs = {
        "model_google-gemini-3-1-flash": image,
        "model_patina-material": "7.75",
        "model_google-gemini-3-8-flash-lite-tts": "1",
    }
    cap = format(ci.MONTHLY_MAX_CU, "f")
    if allowed:
        assert budget_run(tmp_path, costs, cap)[0] == 0
        return
    with pytest.raises(model.SmokeError, match="aggregate cap") as error:
        budget_run(tmp_path, costs, cap)
    assert error.value.code == 3
    assert not (tmp_path / "suite" / "suite-attempt").exists()
