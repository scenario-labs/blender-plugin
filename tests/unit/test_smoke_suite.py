# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Aggregate approvals exercise the real SDK, coordinator and durable stores."""

import json
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from decimal import Decimal
from pathlib import Path
from threading import Event

import httpx
import pytest

from scenario.core.api.sdk_adapter import AdapterError
from scenario.core.config import Credentials
from scenario.core.jobs.coordinator import SubmissionUncertain
from scenario.core.jobs.transfers import DownloadedResult, ResultDownloader, StoragePolicy
from tools import smoke_image as model
from tools import smoke_suite as suite
from tools.dev_config import LiveSettings

SETTINGS = LiveSettings(Credentials("fixture-key", "fixture-secret"), "fixture-project")
DATA = b"offline result; receipt and metadata coverage only"


class Downloads(ResultDownloader):
    def __init__(self):
        super().__init__(StoragePolicy(frozenset({"cdn.scenario.com"})), online_access=lambda: True)

    def download(self, url, *, root, name, expected_size, expected_sha256):
        self._policy.destination(url)
        (root / name).write_bytes(DATA)
        return DownloadedResult(name, len(DATA), model.digest(DATA))


@pytest.fixture
def fixture(tmp_path):
    root = tmp_path / "suite"
    plan = tmp_path / "plan.json"
    value = {
        "schema_version": 1,
        "project_id": SETTINGS.project_id,
        "cases": [
            {
                "name": kind,
                "result_kind": kind,
                "model": kind,
                "parameters": {
                    "prompt": "private fixture prompt marker",
                    **({"maps": ["basecolor", "normal"]} if kind == "material" else {}),
                },
            }
            for kind in model.RESULT_KINDS
        ],
    }
    plan.write_bytes(model.json_bytes(value))
    material_model = json.loads(
        (Path(__file__).parents[1] / "fixtures/models/model_patina-material.json").read_text()
    )["model"]
    calls = []
    behavior = {"cost": "0.10000000000000000000000000001", "fail": None, "hold": None}

    def handler(request):
        calls.append(request)
        assert request.url.params.get("projectId") == SETTINGS.project_id
        path = request.url.path
        kind = path.rsplit("/", 1)[1]
        if "/models/" in path:
            inputs = [{"name": "prompt", "type": "string"}]
            if kind == "material":
                inputs += [
                    field
                    for field in material_model["inputs"]
                    if field["name"] in {"maps", "numOutputs"}
                ]
            return httpx.Response(
                200,
                json={
                    "model": {
                        "id": kind,
                        "type": "custom",
                        "inputs": inputs,
                    }
                },
            )
        if request.url.params.get("dryRun") == "true":
            if behavior["fail"] == "quote-" + kind:
                raise httpx.ReadTimeout("private quote response", request=request)
            return httpx.Response(200, content='{"creativeUnitsCost":' + behavior["cost"] + "}")
        if request.method == "POST":
            assert (root / "suite-attempt").is_file()
            if behavior["hold"]:
                behavior["hold"]()
            if behavior["fail"] == kind:
                raise httpx.ReadTimeout("private uncertain response", request=request)
            return httpx.Response(200, json={"job": {"jobId": kind}})
        if "/jobs/" in path:
            assets = [kind + "-base", kind + "-normal"] if kind == "material" else [kind]
            return httpx.Response(
                200,
                json={
                    "job": {"jobId": kind, "status": "success", "metadata": {"assetIds": assets}}
                },
            )
        if "/assets/" in path:
            mime = {
                "image": "image/png",
                "video": "video/mp4",
                "model": "model/gltf-binary",
                "audio": "audio/wav",
            }.get(kind, "image/png")
            metadata = (
                {"type": "texture-albedo" if kind.endswith("base") else "texture-normal"}
                if kind.startswith("material-")
                else {}
            )
            return httpx.Response(
                200,
                json={
                    "asset": {
                        "id": kind,
                        "status": "success",
                        "mimeType": mime,
                        "metadata": metadata,
                        "properties": {"size": len(DATA)},
                        "url": "https://cdn.scenario.com/result?private=secret",
                    }
                },
            )
        raise AssertionError("Unexpected request")

    def execute(args, settings):
        return model.execute(
            args, settings, transport=httpx.MockTransport(handler), downloader=Downloads()
        )

    def args(command, **overrides):
        values = [command, "--run-dir", str(root)]
        if command in {"quote", "budget-run"}:
            values += ["--plan", str(plan)]
        if command in {"submit", "budget-run"}:
            values += ["--max-cu", "1"]
        if command == "submit":
            raw = (root / "suite.json").read_bytes()
            values += [
                "--approved-suite",
                model.digest(raw),
                "--approved-total",
                json.loads(raw)["total_cost"],
            ]
        parsed = suite.parser().parse_args(values)
        for name, value in overrides.items():
            setattr(parsed, name, value)
        return parsed

    def run(command, settings=SETTINGS, **overrides):
        return suite.run(args(command, **overrides), settings, execute=execute)

    return root, plan, value, calls, behavior, args, execute, run


def paid(calls):
    return [
        request
        for request in calls
        if request.method == "POST" and "dryRun" not in request.url.params
    ]


def test_all_kinds_exact_aggregate_and_offline_resume(fixture, capsys):
    root, _, _, calls, _, _, _, run = fixture
    assert run("quote") == 0
    assert not paid(calls)
    manifest = json.loads((root / "suite.json").read_bytes())
    assert manifest["total_cost"] == "0.50000000000000000000000000005"
    assert run("submit", max_cu=Decimal(manifest["total_cost"])) == 0
    assert len(paid(calls)) == 5
    before = len(calls)
    assert run("resume") == 0 and len(calls) == before
    with pytest.raises(model.SmokeError, match="attempted"):
        run("submit")
    output = capsys.readouterr().out
    assert all(
        secret not in output
        for secret in (
            "fixture-key",
            "fixture-secret",
            "private fixture prompt marker",
            "fixture-project",
        )
    )


@pytest.mark.parametrize(
    "field,value",
    [("max_cu", Decimal("0.5")), ("approved_total", Decimal("0.5")), ("approved_suite", "0" * 64)],
)
def test_bad_aggregate_approval_spends_nothing(fixture, field, value):
    root, _, _, calls, _, _, _, run = fixture
    run("quote")
    before = len(calls)
    with pytest.raises(model.SmokeError):
        run("submit", **{field: value})
    assert len(calls) == before and not paid(calls)
    assert not (root / "suite-attempt").exists()


def test_changed_last_quote_stops_before_first_submission(fixture):
    root, _, _, calls, _, _, _, run = fixture
    run("quote")
    path = root / "audio" / "quote.json"
    path.write_bytes(path.read_bytes() + b" ")
    with pytest.raises(model.SmokeError, match="quote changed"):
        run("submit")
    assert not paid(calls)


def test_lost_second_receipt_stops_remaining_cases_without_refund_or_replay(fixture):
    root, _, _, calls, behavior, _, _, run = fixture
    run("quote")
    behavior["fail"] = "material"
    with pytest.raises(SubmissionUncertain):
        run("submit")
    assert len(paid(calls)) == 2
    assert not (root / "video" / "submission-attempt").exists()
    with pytest.raises(model.SmokeError, match="attempted"):
        run("submit")
    with pytest.raises(model.SmokeError, match="review"):
        run("resume")
    assert len(paid(calls)) == 2


def test_fresh_price_change_stops_before_any_paid_request(fixture):
    root, _, _, calls, behavior, _, _, run = fixture
    run("quote")
    behavior["cost"] = "0.2"
    with pytest.raises(model.SmokeError, match="Fresh quote"):
        run("submit")
    assert not paid(calls) and (root / "suite-attempt").exists()


def test_failed_later_quote_cannot_leave_an_approved_partial_suite(fixture):
    root, _, _, calls, behavior, _, _, run = fixture
    behavior["fail"] = "quote-material"
    with pytest.raises(AdapterError):
        run("quote")
    assert not paid(calls) and not (root / "suite.json").exists()


def test_project_mismatch_fails_before_quote_storage_or_network(fixture):
    root, _, _, calls, _, _, _, run = fixture
    with pytest.raises(model.SmokeError, match="project"):
        run("quote", settings=replace(SETTINGS, project_id=None))
    assert not root.exists() and not calls


@pytest.mark.parametrize("change", ["duplicate", "path", "empty", "many", "unknown"])
def test_invalid_plan_rejected_before_network(fixture, change):
    root, plan, value, calls, _, _, _, run = fixture
    if change == "duplicate":
        value["cases"][1]["name"] = value["cases"][0]["name"]
    elif change == "path":
        value["cases"][0]["name"] = "../escape"
    elif change == "empty":
        value["cases"] = []
    elif change == "many":
        value["cases"] *= 2
    else:
        value["cases"][-1]["unknown"] = True
    plan.write_bytes(model.json_bytes(value))
    with pytest.raises(model.SmokeError):
        run("quote")
    assert not root.exists() and not calls


@pytest.mark.parametrize("command", ["quote", "budget-run"])
def test_reserved_case_name_fails_before_storage_or_network(fixture, command):
    root, plan, value, calls, _, _, _, run = fixture
    value["cases"][-1]["name"] = "suite-attempt"
    plan.write_bytes(model.json_bytes(value))
    with pytest.raises(model.SmokeError, match="reserved"):
        run(command)
    assert not root.exists() and not calls


def test_budget_run_requires_positive_cap_and_reserves_total_before_spend(fixture):
    root, _, _, calls, _, _, _, run = fixture
    with pytest.raises(model.SmokeError, match="positive"):
        run("budget-run", max_cu=Decimal(0))
    assert not root.exists() and not calls
    with pytest.raises(model.SmokeError, match="aggregate cap"):
        run("budget-run", max_cu=Decimal("0.5"))
    assert not paid(calls) and not (root / "suite-attempt").exists()


def test_concurrent_suite_submissions_cannot_repeat_paid_calls(fixture):
    _, _, _, calls, behavior, args, execute, run = fixture
    run("quote")
    entered, release = Event(), Event()

    def hold():
        entered.set()
        assert release.wait(10)

    behavior["hold"] = hold
    approved = args("submit")
    with ThreadPoolExecutor(max_workers=2) as pool:
        first = pool.submit(suite.run, approved, SETTINGS, execute=execute)
        try:
            assert entered.wait(10)
            with pytest.raises(model.SmokeError, match="attempted"):
                run("submit")
        finally:
            release.set()
        assert first.result(timeout=10) == 0
    assert len(paid(calls)) == 5


@pytest.mark.parametrize("command", ["submit", "budget-run"])
def test_main_requires_explicit_opt_in_before_loading_credentials(monkeypatch, tmp_path, command):
    monkeypatch.delenv("SCENARIO_SMOKE", raising=False)
    monkeypatch.setattr(
        suite, "live_settings", lambda: pytest.fail("Credentials read without opt-in")
    )
    args = [command, "--run-dir", str(tmp_path / "run"), "--max-cu", "1"]
    args += (
        ["--plan", "unused"]
        if command == "budget-run"
        else ["--approved-suite", "0" * 64, "--approved-total", "1"]
    )
    assert suite.main(args) == 2


def test_budget_authorized_execution_quotes_every_case_before_first_spend(fixture):
    root, _, _, calls, _, _, _, run = fixture
    assert run("budget-run") == 0
    first_paid = next(index for index, request in enumerate(calls) if request in paid(calls))
    quoted = {
        request.url.path.rsplit("/", 1)[1]
        for request in calls[:first_paid]
        if request.url.params.get("dryRun") == "true"
    }
    assert quoted == set(model.RESULT_KINDS)
    assert len(paid(calls)) == 5 and (root / "suite-attempt").is_file()


def test_changed_credentials_cannot_submit_any_case(fixture):
    _, _, _, calls, _, _, _, run = fixture
    run("quote")
    count = len(calls)
    with pytest.raises(model.SmokeError, match="Credentials or project changed"):
        run(
            "submit",
            settings=replace(SETTINGS, credentials=Credentials("another-key", "another-secret")),
        )
    assert len(calls) == count and not paid(calls)
