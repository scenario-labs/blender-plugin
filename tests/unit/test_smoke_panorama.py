# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Environment lane contract cases through the real smoke engine, suite and stores."""

import json
import re
from dataclasses import replace
from pathlib import Path

import httpx
import pytest

from scenario.core.api.catalog import ModelRecord
from scenario.core.config import Credentials
from scenario.core.jobs.transfers import DownloadedResult, ResultDownloader, StoragePolicy
from scenario.core.scene import panorama_contract as contracts
from scenario.core.schema.params import parse_schema, validate
from tests.unit.test_panorama import exr, jpeg, png
from tools import smoke_image as model
from tools import smoke_inputs
from tools import smoke_suite as suite
from tools.dev_config import LiveSettings

ROOT = Path(__file__).resolve().parents[2]
FIXTURES = ROOT / "tests/fixtures/models"
SETTINGS = LiveSettings(Credentials("fixture-key", "fixture-secret"), "fixture-project")
FLUX = "model_scenario-skybox-flux"
GPT = "model_scenario-skybox-gpt"
WORLD = "model_hunyuan-world-image-to-skybox"
HDRI = "model_hdri-skybox"
UPSCALE = "model_sc-upscale-flux-skybox"
LDR = png(1536, 768)
HDR = exr(2048, 1024)
PREVIEW = jpeg(2048, 1024)
PLAIN = "model_plain"
SAVED = {"$panorama": "panorama-text"}
PROMPT = {"name": "prompt", "type": "string"}
HDRI_LOCKS = {
    "outputExr": True,
    "outputHdr": False,
    "conversionCubemapCross": False,
    "conversionCubemapFaces": False,
}


def recorded(model_id):
    return json.loads((FIXTURES / f"{model_id}.json").read_text())["model"]


class Service:
    """Offline Scenario responses: recorded schemas, dry runs and one job per paid request."""

    def __init__(self):
        self.calls = []
        self.models = {model_id: recorded(model_id) for model_id in contracts.PANORAMA_MODELS}
        self.files = {}
        self.assets = {}
        self.jobs = {}
        # The assets one job returns: (mime type, metadata type, bytes, original).
        self.outputs = {
            FLUX: [("image/png", "skybox-base-360", LDR, None)],
            GPT: [("image/png", "skybox-base-360", LDR, None)],
            WORLD: [("image/jpeg", "skybox-base-360", jpeg(1536, 768), None)],
            UPSCALE: [("image/png", "upscale-skybox", png(3072, 1536), None)],
            HDRI: [("image/jpeg", "skybox-hdri", PREVIEW, ("image/x-exr", HDR))],
        }

    def handler(self, request):
        self.calls.append(request)
        path = request.url.path
        if path.startswith("/v1/models/"):
            return httpx.Response(200, json={"model": self.models[path.rsplit("/", 1)[1]]})
        if request.url.params.get("dryRun") == "true":
            return httpx.Response(200, content='{"creativeUnitsCost":15.75}')
        if request.method == "POST":
            job = f"job-{len(self.jobs) + 1}"
            self.jobs[job] = []
            for index, (mime, kind, data, original) in enumerate(
                self.outputs[path.rsplit("/", 1)[1]], 1
            ):
                asset_id = f"asset-{job}-{index}"
                url = f"https://cdn.scenario.com/{asset_id}/file?secret=redact"
                self.files[url] = data
                asset = {
                    "id": asset_id,
                    "status": "success",
                    "mimeType": mime,
                    "properties": {"size": len(data)},
                    "metadata": {"type": kind} if kind else {},
                    "url": url,
                }
                if original:
                    location = f"https://cdn.scenario.com/{asset_id}/original?secret=redact"
                    self.files[location] = original[1]
                    asset.update(originalMimeType=original[0], originalFileUrl=location)
                self.assets[asset_id] = asset
                self.jobs[job].append(asset_id)
            return httpx.Response(200, json={"job": {"jobId": job}})
        if path.startswith("/v1/jobs/"):
            job = path.rsplit("/", 1)[1]
            return httpx.Response(
                200,
                json={
                    "job": {
                        "jobId": job,
                        "status": "success",
                        "metadata": {"assetIds": self.jobs[job]},
                    }
                },
            )
        if path.startswith("/v1/assets/"):
            return httpx.Response(200, json={"asset": self.assets[path.rsplit("/", 1)[1]]})
        raise AssertionError("Unexpected SDK request")

    def bodies(self, *, dry_run):
        return [
            (call.url.path.rsplit("/", 1)[1], json.loads(call.content))
            for call in self.calls
            if call.method == "POST" and (call.url.params.get("dryRun") == "true") == dry_run
        ]


class Downloads(ResultDownloader):
    def __init__(self, service):
        super().__init__(StoragePolicy(frozenset({"cdn.scenario.com"})), online_access=lambda: True)
        self.service = service

    def download(
        self,
        url,
        *,
        root,
        name,
        expected_size,
        expected_sha256,
        max_bytes=None,
        cancel=None,
        partial=None,
    ):
        self._policy.destination(url)
        data = self.service.files[url]
        # A declared original has no size metadata, so a byte cap must bound it.
        assert expected_size == len(data) or (expected_size is None and max_bytes)
        (root / name).write_bytes(data)
        return DownloadedResult(name, len(data), model.digest(data))


class Runs:
    """Single runs of the real engine in one directory, as `--saved-runs` reads them."""

    def __init__(self, tmp_path, service):
        self.root = tmp_path / "runs"
        self.root.mkdir()
        self.inputs = tmp_path / "inputs"
        self.inputs.mkdir()
        self.service = service

    def execute(self, values, settings=SETTINGS):
        args = model.parser(default_result_kind=None).parse_args(values)
        return model.execute(
            args,
            settings,
            transport=httpx.MockTransport(self.service.handler),
            downloader=Downloads(self.service),
        )

    def quote(self, name, model_id, kind, parameters, *, saved=None, settings=SETTINGS):
        path = self.inputs / f"{name}.json"
        path.write_bytes(model.json_bytes(parameters))
        values = ["quote", "--run-dir", str(self.root / name), "--result-kind", kind]
        values += ["--model", model_id, "--parameters", str(path)]
        if saved is not None:
            values += ["--saved-runs", str(saved)]
        return self.execute(values, settings)

    def submit(self, name, settings=SETTINGS):
        raw = (self.root / name / "quote.json").read_bytes()
        cost = json.loads(raw)["cost"]
        values = ["submit", "--run-dir", str(self.root / name), "--approved-quote"]
        values += [model.digest(raw), "--approved-cost", cost, "--max-cu", cost]
        return self.execute(values, settings)

    def plan(self, name):
        return json.loads((self.root / name / "quote.json").read_bytes())

    def complete(self, name, model_id=FLUX, parameters=None):
        assert self.quote(name, model_id, "panorama", parameters or {"prompt": "a lake"}) == 0
        assert self.submit(name) == 0
        return self.service.jobs[f"job-{len(self.service.jobs)}"][0]


@pytest.fixture
def service():
    return Service()


@pytest.fixture
def runs(tmp_path, service):
    return Runs(tmp_path, service)


def requests(service):
    return len(service.calls)


def test_flux_text_case_quotes_and_submits_the_contract_body(runs, service):
    assert runs.quote("text", FLUX, "panorama", {"prompt": "a lake at dawn"}) == 0
    [(target, quoted)] = service.bodies(dry_run=True)
    # The lane default makes one panorama where the schema default makes two.
    assert target == FLUX and quoted["numOutputs"] == 1 and quoted["prompt"] == "a lake at dawn"
    plan = runs.plan("text")
    assert plan["schema_version"] == model.CONTRACT_QUOTE and plan["panorama_refs"] == []
    assert plan["parameters"] == {"prompt": "a lake at dawn", "numOutputs": 1}
    assert not service.bodies(dry_run=False)
    assert runs.submit("text") == 0
    [(_, paid)] = service.bodies(dry_run=False)
    assert paid == quoted


@pytest.mark.parametrize(
    "model_id,kind,expected",
    [(FLUX, "image", "panorama"), (GPT, "hdri", "panorama"), (HDRI, "panorama", "hdri")],
)
def test_contract_model_requires_its_result_kind_before_network(
    runs, service, model_id, kind, expected
):
    with pytest.raises(model.SmokeError, match=f"Use the {expected} result kind") as error:
        runs.quote("case", model_id, kind, {"prompt": "a lake"})
    assert error.value.code == 2
    assert not service.calls and not (runs.root / "case").exists()


def test_gpt_case_refuses_a_size_outside_the_presets_before_any_dry_run(runs, service):
    with pytest.raises(model.SmokeError, match="2:1 panorama size") as error:
        runs.quote("gpt", GPT, "panorama", {"prompt": "a lake", "width": 3840, "height": 640})
    assert error.value.code == 2
    assert service.calls and not service.bodies(dry_run=True) and not service.bodies(dry_run=False)
    assert runs.quote("preset", GPT, "panorama", {"prompt": "a lake"}) == 0
    [(_, quoted)] = service.bodies(dry_run=True)
    assert (quoted["width"], quoted["height"]) == (2048, 1024)


ELSEWHERE = "only in a panorama model input"
ONLY = "Fill a saved 360 panorama input only"


@pytest.mark.parametrize(
    "model_id,kind,parameters,message",
    [
        # Placeholders fill only contract inputs that take a saved 360 panorama.
        ("model_custom", "image", {"image": {"$panorama": "text"}}, ELSEWHERE),
        (GPT, "panorama", {"prompt": "x", "referenceImages": [{"$panorama": "text"}]}, ELSEWHERE),
        (FLUX, "panorama", {"prompt": "x", "style": {"nested": {"$panorama": "text"}}}, ELSEWHERE),
        (
            UPSCALE,
            "panorama",
            {"image": {"$panorama": "text"}, "imagePrompt": [{"$panorama": "t"}]},
            ELSEWHERE,
        ),
        # Those inputs take nothing else: no raw, uploaded or malformed reference.
        (HDRI, "hdri", {"image": "asset-uploaded"}, ONLY),
        (HDRI, "hdri", {"image": {"$input": "capture"}}, ONLY),
        (HDRI, "hdri", {"image": {"$panorama": "../escape"}}, ONLY),
        (HDRI, "hdri", {"image": {"$panorama": "text", "index": 1}}, ONLY),
        (HDRI, "hdri", {"image": None}, ONLY),
    ],
)
def test_saved_panorama_inputs_accept_only_exact_placeholders(
    runs, service, model_id, kind, parameters, message
):
    with pytest.raises(model.SmokeError, match=message) as error:
        runs.quote("case", model_id, kind, parameters, saved=runs.root)
    assert error.value.code == 2
    assert not service.calls and not (runs.root / "case").exists()


def test_hdri_case_uses_a_verified_saved_panorama_and_the_contract_locks(runs, service):
    saved = runs.complete("text")
    before = requests(service)
    assert runs.quote("hdri", HDRI, "hdri", {"image": {"$panorama": "text"}}, saved=runs.root) == 0
    # Resolving the saved panorama is offline: only model reads and the dry run follow.
    quoting = service.calls[before:]
    assert all(
        call.url.path == f"/v1/models/{HDRI}" or call.url.params.get("dryRun") == "true"
        for call in quoting
    )
    assert [call.url.params.get("dryRun") for call in quoting].count("true") == 1
    target, quoted = service.bodies(dry_run=True)[-1]
    assert target == HDRI and quoted["image"] == saved
    assert {key: quoted[key] for key in HDRI_LOCKS} == HDRI_LOCKS
    plan = runs.plan("hdri")
    assert plan["panorama_refs"] == [
        {"asset_id": saved, "producer": FLUX, "width": 1536, "height": 768}
    ]
    assert runs.submit("hdri") == 0
    target, paid = service.bodies(dry_run=False)[-1]
    assert target == HDRI and paid == quoted
    # The hdri kind verified the downloaded OpenEXR original, not the JPEG preview.
    report = json.loads((runs.root / "hdri" / "report.json").read_text())
    assert report["jobs"][0]["results"] == [{"size": len(HDR), "sha256": model.digest(HDR)}]


def test_upscale_cap_uses_the_measured_size_of_the_saved_panorama(runs, service):
    runs.complete("text")
    reference = {"image": {"$panorama": "text"}}
    # 1536 x 768 at 6x exceeds the 32-megapixel World limit; 5x fits.
    with pytest.raises(model.SmokeError, match="at most 5"):
        runs.quote("x6", UPSCALE, "panorama", {**reference, "upscaleFactor": 6}, saved=runs.root)
    assert (
        runs.quote("x5", UPSCALE, "panorama", {**reference, "upscaleFactor": 5}, saved=runs.root)
        == 0
    )
    assert service.bodies(dry_run=True)[-1][1]["upscaleFactor"] == 5


@pytest.mark.parametrize("stage", ["quote", "submit"])
def test_inputs_the_schema_says_cannot_be_combined_never_reach_a_dry_run(runs, service, stage):
    # No recorded skybox schema names exclusive inputs today. When a file input's
    # description says so, the smoke tool refuses the body as the native form and MCP do.
    runs.complete("text")
    parameters = {"image": {"$panorama": "text"}, "imagePrompt": ["asset-style"]}
    if stage == "submit":
        assert runs.quote("styled", UPSCALE, "panorama", parameters, saved=runs.root) == 0
    [style] = [item for item in service.models[UPSCALE]["inputs"] if item["name"] == "imagePrompt"]
    style["description"] = "Optional images to guide the style. Mutually exclusive with image."
    before = requests(service)
    refused = "Image can't be combined with Style Images"
    with pytest.raises(model.SmokeError, match=refused) as error:
        if stage == "quote":
            runs.quote("styled", UPSCALE, "panorama", parameters, saved=runs.root)
        else:
            runs.submit("styled")
    assert error.value.code == {"quote": 2, "submit": 3}[stage]
    assert all(call.url.params.get("dryRun") != "true" for call in service.calls[before:])
    assert all(target != UPSCALE for target, _ in service.bodies(dry_run=False))
    assert (runs.root / "styled" / "quote.json").exists() == (stage == "submit")


@pytest.mark.parametrize(
    "change", ["missing", "absent", "unfinished", "unprojected", "hdr", "changed", "scope"]
)
def test_saved_panorama_must_be_a_verified_ldr_result_of_this_scope(runs, service, change):
    settings = SETTINGS
    saved = runs.root
    if change == "unprojected":
        # A completed image run whose saved metadata declares no projection.
        service.models[PLAIN] = {"id": PLAIN, "type": "custom", "inputs": [PROMPT]}
        service.outputs[PLAIN] = [("image/png", None, LDR, None)]
        assert runs.quote("text", PLAIN, "image", {"prompt": "a lake"}) == 0
        assert runs.submit("text") == 0
    elif change == "hdr":
        # An HDRI run's saved file is its OpenEXR original: an environment, not an input.
        runs.complete("source", FLUX)
        reference = {"image": {"$panorama": "source"}}
        assert runs.quote("text", HDRI, "hdri", reference, saved=saved) == 0
        assert runs.submit("text") == 0
    elif change == "unfinished":
        assert runs.quote("text", FLUX, "panorama", {"prompt": "a lake"}) == 0
    elif change != "absent":
        runs.complete("text")
    if change == "missing":
        saved = None
    elif change == "changed":
        [result] = (runs.root / "text" / "results").rglob("*.png")
        result.write_bytes(LDR + b"tampered")
    elif change == "scope":
        settings = replace(SETTINGS, project_id="another-project")
    before = requests(service)
    messages = {
        "missing": "--saved-runs",
        "absent": "completed private run",
        "unfinished": "no completed",
        "unprojected": "no downloaded LDR 360",
        "hdr": "no downloaded LDR 360",
        "changed": "could not be verified",
        "scope": "selected credentials and project",
    }
    with pytest.raises(model.SmokeError, match=messages[change]):
        runs.quote(
            "hdri", HDRI, "hdri", {"image": {"$panorama": "text"}}, saved=saved, settings=settings
        )
    assert requests(service) == before and not (runs.root / "hdri").exists()


def test_saved_panorama_refuses_openexr_bytes_declared_as_png(runs, service):
    # The asset declares a PNG 360 result, but its verified bytes are an OpenEXR file.
    service.outputs[FLUX] = [("image/png", "skybox-base-360", HDR, None)]
    runs.complete("text")
    before = requests(service)
    with pytest.raises(model.SmokeError, match="OpenEXR data, not a 2:1 PNG or JPEG") as error:
        runs.quote("hdri", HDRI, "hdri", {"image": {"$panorama": "text"}}, saved=runs.root)
    assert error.value.code == 1
    assert requests(service) == before and not (runs.root / "hdri").exists()


def test_submit_rechecks_the_contract_and_refuses_schema_drift_without_spending(runs, service):
    assert runs.quote("text", FLUX, "panorama", {"prompt": "a lake"}) == 0
    inputs = service.models[FLUX]["inputs"]
    service.models[FLUX]["inputs"] = [item for item in inputs if item["name"] != "numOutputs"]
    with pytest.raises(model.SmokeError, match="contract changed") as error:
        runs.submit("text")
    assert error.value.code == 3
    assert (
        not service.bodies(dry_run=False) and (runs.root / "text" / "submission-attempt").is_file()
    )


@pytest.mark.parametrize("change", ["refs", "invalid", "older"])
def test_changed_or_older_contract_quotes_cannot_spend(runs, service, change):
    runs.complete("text")
    assert runs.quote("hdri", HDRI, "hdri", {"image": {"$panorama": "text"}}, saved=runs.root) == 0
    path = runs.root / "hdri" / "quote.json"
    plan = json.loads(path.read_bytes())
    if change == "refs":
        # Even a re-approved record cannot name a panorama that was never verified.
        plan["panorama_refs"] = []
    elif change == "invalid":
        plan["panorama_refs"] = [{"asset_id": "asset-job-1-1"}]
    else:
        # Records before version 4 never ran the contract check.
        plan["schema_version"] = 2
        del plan["panorama_refs"]
    path.write_bytes(model.json_bytes(plan))
    before = requests(service)
    with pytest.raises(model.SmokeError, match="contract|references") as error:
        runs.submit("hdri")
    assert error.value.code == {"refs": 3, "invalid": 4, "older": 4}[change]
    assert len(service.bodies(dry_run=False)) == 1
    if change != "refs":
        assert requests(service) == before


def test_hdri_kind_fails_without_an_openexr_original(runs, service):
    runs.complete("text")
    service.outputs[HDRI] = [("image/jpeg", "skybox-hdri", PREVIEW, None)]
    assert runs.quote("hdri", HDRI, "hdri", {"image": {"$panorama": "text"}}, saved=runs.root) == 0
    with pytest.raises(model.SmokeError, match="approved result kind") as error:
        runs.submit("hdri")
    assert error.value.code == 1 and len(service.bodies(dry_run=False)) == 2


def test_capture_case_sends_the_uploaded_still_and_needs_no_saved_run(runs, service):
    assert runs.quote("capture", WORLD, "panorama", {"image": "asset-capture"}) == 0
    [(target, quoted)] = service.bodies(dry_run=True)
    assert target == WORLD and quoted["image"] == "asset-capture"
    assert runs.plan("capture")["panorama_refs"] == []


# Suites.


def write(path, value):
    path.write_bytes(model.json_bytes(value))
    return path


def suite_run(service, values, settings=SETTINGS):
    def execute(args, settings):
        return model.execute(
            args,
            settings,
            transport=httpx.MockTransport(service.handler),
            downloader=Downloads(service),
        )

    return suite.run(suite.parser().parse_args(values), settings, execute=execute)


def generation_plan():
    return {
        "schema_version": 1,
        "project_id": SETTINGS.project_id,
        "cases": [
            {
                "name": "panorama-text",
                "result_kind": "panorama",
                "model": FLUX,
                "parameters": {"prompt": "a quiet lake at dawn"},
            },
            {
                "name": "panorama-capture",
                "result_kind": "panorama",
                "model": WORLD,
                "parameters": {"image": "asset-capture"},
            },
        ],
    }


def conversion_plan():
    return {
        "schema_version": 1,
        "project_id": SETTINGS.project_id,
        "cases": [
            {
                "name": "hdri",
                "result_kind": "hdri",
                "model": HDRI,
                "parameters": {"image": {"$panorama": "panorama-text"}},
            },
            {
                "name": "upscale",
                "result_kind": "panorama",
                "model": UPSCALE,
                "parameters": {"image": {"$panorama": "panorama-capture"}, "upscaleFactor": 2},
            },
        ],
    }


def test_two_suites_convert_saved_panoramas_with_exact_aggregate_approvals(tmp_path, service):
    first, second = tmp_path / "panorama-suite", tmp_path / "panorama-hdri"
    plan = write(tmp_path / "generation.json", generation_plan())
    assert (
        suite_run(
            service, ["budget-run", "--run-dir", str(first), "--plan", str(plan), "--max-cu", "100"]
        )
        == 0
    )
    text, capture = (service.jobs[job][0] for job in ("job-1", "job-2"))
    plan = write(tmp_path / "conversion.json", conversion_plan())
    values = ["quote", "--run-dir", str(second), "--plan", str(plan)]
    # Without the completed first suite, nothing is stored or requested.
    before = requests(service)
    with pytest.raises(model.SmokeError, match="--saved-runs"):
        suite_run(service, values)
    assert requests(service) == before and not second.exists()
    assert suite_run(service, [*values, "--saved-runs", str(first)]) == 0
    hdri, upscale = (body for _, body in service.bodies(dry_run=True)[-2:])
    assert hdri["image"] == text and {key: hdri[key] for key in HDRI_LOCKS} == HDRI_LOCKS
    assert upscale["image"] == capture and upscale["upscaleFactor"] == 2
    raw = (second / "suite.json").read_bytes()
    approval = ["submit", "--run-dir", str(second), "--approved-suite", model.digest(raw)]
    approval += ["--approved-total", json.loads(raw)["total_cost"], "--max-cu", "100"]
    assert suite_run(service, approval) == 0
    paid = service.bodies(dry_run=False)
    assert [target for target, _ in paid] == [FLUX, WORLD, HDRI, UPSCALE]
    assert paid[2][1] == hdri and paid[3][1] == upscale
    before = requests(service)
    assert suite_run(service, ["resume", "--run-dir", str(second)]) == 0
    assert requests(service) == before


@pytest.mark.parametrize(
    "case,message",
    [
        ({"result_kind": "image", "model": FLUX, "parameters": {"prompt": "x"}}, "panorama result"),
        (
            {"result_kind": "panorama", "model": GPT, "parameters": {"referenceImages": [SAVED]}},
            ELSEWHERE,
        ),
        ({"result_kind": "hdri", "model": HDRI, "parameters": {"image": "asset-raw"}}, ONLY),
    ],
)
def test_suite_refuses_panorama_cases_before_storage_or_network(tmp_path, service, case, message):
    value = {
        "schema_version": 1,
        "project_id": SETTINGS.project_id,
        "cases": [{"name": "a", **case}],
    }
    plan = write(tmp_path / "plan.json", value)
    values = ["quote", "--run-dir", str(tmp_path / "suite"), "--plan", str(plan)]
    with pytest.raises(model.SmokeError, match=message):
        suite_run(service, [*values, "--saved-runs", str(tmp_path)])
    assert not service.calls and not (tmp_path / "suite").exists()


def test_budget_run_verifies_saved_panoramas_before_any_upload(tmp_path, service):
    capture = tmp_path / "inputs" / "capture.png"
    capture.parent.mkdir()
    capture.write_bytes(png(512, 512))
    value = {
        "schema_version": 2,
        "project_id": SETTINGS.project_id,
        "inputs": [
            {
                "name": "capture",
                "file": "capture.png",
                "sha256": model.digest(capture.read_bytes()),
                "kind": "image",
                "content_type": "image/png",
            }
        ],
        "cases": [
            {
                "name": "panorama-capture",
                "result_kind": "panorama",
                "model": WORLD,
                "parameters": {"image": {"$input": "capture"}},
            },
            conversion_plan()["cases"][0],
        ],
    }
    plan = write(tmp_path / "plan.json", value)
    values = ["budget-run", "--run-dir", str(tmp_path / "suite"), "--plan", str(plan)]
    values += ["--max-cu", "100", "--upload-inputs", "--input-root", str(capture.parent)]
    with pytest.raises(model.SmokeError, match="--saved-runs"):
        suite_run(service, values)
    with pytest.raises(model.SmokeError, match="completed private run"):
        suite_run(service, [*values, "--saved-runs", str(tmp_path)])
    assert not service.calls
    assert not (tmp_path / "suite").exists() and not (tmp_path / "suite-inputs").exists()


def test_only_quoting_commands_take_saved_runs():
    for command in ("submit", "resume"):
        values = [command, "--run-dir", "run", "--saved-runs", "runs"]
        with pytest.raises(SystemExit):
            suite.parser().parse_args(values)
        with pytest.raises(SystemExit):
            model.parser(default_result_kind=None).parse_args(values)


# The guide's plans.


def guide_plans():
    text = (ROOT / "tests/smoke/README.md").read_text()
    section = text.split("## Panorama contract cases", 1)[1].split("\n## ", 1)[0]
    return [json.loads(block) for block in re.findall(r"```json\n(.*?)```", section, re.S)]


def test_guide_panorama_plans_pass_plan_and_contract_checks():
    generation, conversion = guide_plans()
    settings = replace(SETTINGS, project_id=None)
    assert generation["inputs"][0]["sha256"] == "CAPTURE_SHA256"
    generation["inputs"][0]["sha256"] = "0" * 64
    smoke_inputs.validate(generation, settings)
    suite.validate_plan(conversion, settings)
    refs = {"asset-saved": contracts.PanoramaRef("asset-saved", FLUX, 1536, 768)}
    for case in generation["cases"] + conversion["cases"]:
        parameters = json.loads(
            json.dumps(case["parameters"])
            .replace('{"$input": "capture"}', '"asset-capture"')
            .replace('{"$panorama": "panorama-text"}', '"asset-saved"')
            .replace('{"$panorama": "panorama-capture"}', '"asset-saved"')
        )
        schema = parse_schema(ModelRecord.from_api(recorded(case["model"])))
        body, errors = contracts.prepare(
            contracts.CONTRACTS[case["model"]], schema.specs, parameters, panorama_refs=refs
        )
        assert errors == [] and validate(schema.specs, body, schema.one_of) == [], case["name"]
    names = [case["name"] for case in generation["cases"]]
    assert [case["parameters"]["image"]["$panorama"] for case in conversion["cases"]] == names
