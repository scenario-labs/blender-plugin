# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Capture through the real pinned SDK and adapter, with a synthetic service and local files."""

import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import httpx
import pytest

from scenario.core.api.sdk_adapter import Credentials, SDKAdapter
from tools import capture_trained_contracts as capture

BASE = "model_fixture-base"
LORA = "model_PublicLora000000000000"
COMPOSITION = "model_PublicComposition00000"
UNLISTED_CONCEPT = "model_UnlistedConcept0000000"
FOREIGN_CONCEPT = "model_ForeignConcept00000000"
NONPUBLIC_PARENT = "model_NonPublicParent0000000"
PRIVATE_LORA = "model_PrivateLora00000000000"
PRIVATE_PARENT = "model_PrivateParent000000000"
PRIVATE_ASSET = "asset_PrivateReference000000"
PROJECT = "proj_PrivateProject000000000"
PRIVATE_NAME = "Secret character study"
SIGNED = "https://storage.example/dataset.json?X-Amz-Credential=SECRET"  # secrets-allow: synthetic fixture
SECRETS = (
    PRIVATE_LORA,
    PRIVATE_PARENT,
    PRIVATE_ASSET,
    PROJECT,
    PRIVATE_NAME,
    "SECRET",
    UNLISTED_CONCEPT,
    FOREIGN_CONCEPT,
    NONPUBLIC_PARENT,
    "owner-secret",
)
CASES = (
    ("stack", "stack", BASE, {"prompt": "p", "loras": ["@lora"], "lorasScale": [0.8]}),
    ("composition", "composition", BASE, {"prompt": "p", "modelId": "@composition"}),
    (
        "reference",
        "stack",
        BASE,
        {"prompt": "p", "referenceImages": [capture.REFERENCE], "loras": ["@lora"]},
    ),
    ("direct", "direct", "@lora", {"prompt": "p", "aspectRatio": "1:1"}),
    ("wrong_type", "check", BASE, {"prompt": "p", "loras": ["@composition"]}),
)


def base_record():
    return {
        "id": BASE,
        "name": "Fixture base",
        "type": "custom",
        "privacy": "public",
        "status": "trained",
        "custom": True,
        "capabilities": ["txt2img"],
        "ownerId": "owner-secret",
        "exampleAssetIds": ["asset_PublicExample000000000"],
        "inputs": [
            {
                "name": "modelId",
                "type": "model",
                "modelTypes": ["flux.1-lora", "flux.1-composition"],
            },
            {"name": "loras", "type": "model_array", "modelTypes": ["flux.1-lora"], "maxLength": 6},
            {"name": "lorasScale", "type": "number_array", "min": 0, "max": 2},
            {"name": "prompt", "type": "string", "required": {"always": True}},
            {"name": "referenceImages", "type": "file_array"},
            {"name": "numOutputs", "type": "number", "default": 1},
        ],
        "uiConfig": {
            "lorasComponent": {
                "label": "Model",
                "modelInput": "loras",
                "scaleInput": "lorasScale",
                "modelIdInput": "modelId",
            }
        },
    }


def trained_record(model_id, kind):
    return {
        "id": model_id,
        "name": "Public style",
        "type": kind,
        "privacy": "public",
        "status": "trained",
        "custom": False,
        "ownerId": "owner-secret",
        "parentModelId": NONPUBLIC_PARENT,
        "parameters": {"datasetJsonPath": SIGNED},
        "concepts": [{"modelId": UNLISTED_CONCEPT, "scale": 0.7}, {"modelId": LORA, "scale": 0.8}],
    }


PRIVATE_ROW = {
    "id": PRIVATE_LORA,
    "name": PRIVATE_NAME,
    "type": "flux.1-lora",
    "privacy": "private",
    "status": "trained",
    "parentModelId": PRIVATE_PARENT,
}


@pytest.fixture
def service(tmp_path, monkeypatch):
    monkeypatch.setattr(capture, "FIXTURES", tmp_path)
    monkeypatch.setattr(capture, "BASE_IDS", (BASE,))
    monkeypatch.setattr(capture, "PUBLIC_TRAINED", {"lora": LORA, "composition": COMPOSITION})
    monkeypatch.setattr(capture, "CASES", CASES)
    monkeypatch.setattr(
        capture,
        "live_settings",
        lambda: SimpleNamespace(
            credentials=SimpleNamespace(key="fixture-key", secret="fixture-secret"),
            project_id=PROJECT,
        ),
    )
    monkeypatch.setenv("SCENARIO_SDK_API_KEY", "ambient-key")
    state = SimpleNamespace(
        root=tmp_path,
        requests=[],
        clients=[],
        private=[dict(PRIVATE_ROW)],
        assets=[{"id": PRIVATE_ASSET, "mimeType": "image/png"}],
        public_ids=[BASE, LORA, COMPOSITION],
        fail_path=None,
        echo=None,
        reply_key=None,
    )
    records = {
        BASE: base_record(),
        LORA: trained_record(LORA, "flux.1-lora"),
        COMPOSITION: trained_record(COMPOSITION, "flux.1-composition"),
        PRIVATE_LORA: {**PRIVATE_ROW, "custom": False},
        UNLISTED_CONCEPT: {"id": UNLISTED_CONCEPT, "type": "flux.1-lora", "privacy": "unlisted"},
    }
    # Another account's concept: the selected credentials cannot read it.
    records[COMPOSITION]["concepts"].append({"modelId": FOREIGN_CONCEPT, "scale": 0.2})

    def generate(request, model_id):
        params = request.url.params
        assert params["dryRun"] == "true" and "ipDetection" not in params
        body = json.loads(request.content)
        if model_id != BASE:
            # A reason about a private record may name it; only its status is kept.
            detail = f" ({PRIVATE_NAME})" if model_id == PRIVATE_LORA else ""
            reason = f"Custom models only are supported for this endpoint{detail}"
            return httpx.Response(400, json={"reason": reason})
        loras = body.get("loras", [])
        if any(item not in (LORA, PRIVATE_LORA) for item in loras):
            echo = f" (seen {state.echo})" if state.echo else ""
            return httpx.Response(400, json={"reason": f"Invalid model(s): {loras[0]}.{echo}"})
        quote = {"creativeUnitsCost": 3.5, "creativeUnitsDiscount": 0, "costDetails": {"x": 3.5}}
        if state.reply_key:
            quote[state.reply_key] = True
        return httpx.Response(269, json=quote)

    def handle(request):
        state.requests.append(request)
        path, params = request.url.path, request.url.params
        assert params["projectId"] == PROJECT
        assert request.headers["Authorization"].startswith("Basic ")
        if path == state.fail_path:
            return httpx.Response(500, json={"reason": f"internal {PRIVATE_NAME}"})
        if request.method == "GET" and path == "/v1/models":
            if params["privacy"] == "private":
                assert params["status"] == "trained"
                return httpx.Response(200, json={"models": state.private})
            rows = [{**records[i], "inputs": None, "uiConfig": None} for i in state.public_ids]
            return httpx.Response(200, json={"models": rows})
        if request.method == "GET" and path == "/v1/assets":
            return httpx.Response(200, json={"assets": state.assets})
        if request.method == "GET" and path.startswith("/v1/models/"):
            model_id = path.rsplit("/", 1)[1]
            rows = {row["id"]: {**row, "custom": False} for row in state.private}
            known = {**rows, **records}
            if model_id not in known:
                return httpx.Response(404, json={"reason": f"Model {model_id} not found"})
            return httpx.Response(200, json={"model": known[model_id]})
        if request.method == "POST" and path == "/v1/models/get-bulk":
            ids = json.loads(request.content)["modelIds"]
            return httpx.Response(200, json={"models": [{"id": i, "type": "custom"} for i in ids]})
        if request.method == "POST" and path.startswith("/v1/generate/custom/"):
            return generate(request, path.rsplit("/", 1)[1])
        raise AssertionError(f"unexpected request {request.method} {path}")

    def create(*args, **kwargs):
        client = SDKAdapter(
            *args,
            **kwargs,
            base_url="https://service.example.invalid/v1",
            transport=httpx.MockTransport(handle),
        )
        state.clients.append(client)
        return client

    monkeypatch.setattr(capture, "SDKAdapter", create)
    return state


def written(root):
    return {
        path.relative_to(root).as_posix(): path.read_text(encoding="utf-8")
        for path in sorted(root.rglob("*.json"))
    }


def test_capture_reads_and_quotes_with_dry_runs_only(service, capsys):
    assert capture.main([]) == 0
    calls = [(r.method, r.url.path) for r in service.requests]
    generate = [r for r in service.requests if r.url.path.startswith("/v1/generate/")]
    assert {method for method, _ in calls} == {"GET", "POST"}
    assert all(
        path in {"/v1/models", "/v1/assets", "/v1/models/get-bulk"}
        or path.startswith(("/v1/models/model_", "/v1/generate/custom/"))
        for _, path in calls
    )
    # Each case dry-runs once; accepted base routes are quoted again through
    # estimate_model; the private LoRA gets a direct and a via-base dry run.
    assert len(generate) == 5 + 3 + 2
    assert all(r.url.params["dryRun"] == "true" for r in generate)
    assert all(client._closed for client in service.clients)
    files = written(service.root)
    assert sorted(files) == [
        "models/trained/bases/model_fixture-base.json",
        "models/trained/contracts.json",
        f"models/trained/public/{COMPOSITION}.json",
        f"models/trained/public/{LORA}.json",
    ]
    assert not list(service.root.glob(".recording-*"))
    output = capsys.readouterr()
    assert output.out.splitlines()[:4] == [
        "stack: accepted",
        "model_id: not captured",
        "composition: accepted",
        "direct: rejected",
    ]
    assert output.err == ""


def test_private_records_and_identifiers_are_never_written(service, capsys):
    assert capture.main([]) == 0
    text = "\n".join(written(service.root).values())
    output = capsys.readouterr()
    for secret in SECRETS:
        assert secret not in text + output.out + output.err
    contracts = json.loads(written(service.root)["models/trained/contracts.json"])
    private = contracts["catalog"]["privateTrained"]
    assert private["present"] is True
    assert private["listRowsCarry"] == {"inputs": False, "uiConfig": False}
    assert private["types"] == {
        "flux.1-lora": {
            "detailCarries": {"inputs": False, "uiConfig": False},
            "custom": False,
            "direct": {"status": 400, "fields": ["reason"]},
            "viaBase": {
                "base": BASE,
                "route": "model_id",
                "status": 269,
                "fields": ["costDetails", "creativeUnitsCost", "creativeUnitsDiscount"],
            },
        }
    }
    reference = {case["case"]: case for case in contracts["dryRuns"]}["reference"]
    assert reference["body"]["referenceImages"] == [capture.REFERENCE_PLACEHOLDER]
    assert contracts["scope"] == {"credentials": "explicit API-key pair", "projectOverride": True}
    # Concepts are read by ID, but only their readability and type are kept.
    assert contracts["catalog"]["compositionConcepts"] == {
        "composition": [
            {"listedPublic": False, "readable": True, "type": "flux.1-lora", "privacy": "unlisted"},
            {"listedPublic": True, "readable": True, "type": "flux.1-lora", "privacy": "public"},
            {"listedPublic": False, "readable": False, "status": 404},
        ]
    }


def test_public_records_are_scrubbed_projections(service):
    assert capture.main([]) == 0
    files = written(service.root)
    lora = json.loads(files[f"models/trained/public/{LORA}.json"])["model"]
    assert set(lora) == {*capture.TRAINED_FIELDS, "observedFields"} - {"compliantModelIds"} - {
        "capabilities"
    }
    assert "parameters" in lora["observedFields"] and "parameters" not in lora
    # The composition projection is scrubbed first: its unlisted and foreign
    # concepts and its non-public parent take placeholders 1, 2 and 3, which
    # the same IDs reuse in later records.
    composition = json.loads(files[f"models/trained/public/{COMPOSITION}.json"])["model"]
    assert [concept["modelId"] for concept in composition["concepts"]] == [
        "model_FIXTURE0000000000000001",
        LORA,
        "model_FIXTURE0000000000000002",
    ]
    assert lora["parentModelId"] == "model_FIXTURE0000000000000003"
    assert lora["concepts"] == [
        {"modelId": "model_FIXTURE0000000000000001", "scale": 0.7},
        {"modelId": LORA, "scale": 0.8},
    ]
    base = json.loads(files["models/trained/bases/model_fixture-base.json"])["model"]
    assert base["ownerId"] == "proj_FIXTURE00000000000000000"
    assert base["exampleAssetIds"] == ["asset_FIXTURE0000000000000001"]
    assert base["uiConfig"] == base_record()["uiConfig"]
    assert base["inputs"] == base_record()["inputs"]


def test_decisions_record_dry_run_outcomes(service):
    assert capture.main([]) == 0
    contracts = json.loads(written(service.root)["models/trained/contracts.json"])
    cases = {case["case"]: case for case in contracts["dryRuns"]}
    assert cases["wrong_type"]["reply"] == {"reason": f"Invalid model(s): {COMPOSITION}."}
    assert cases["direct"]["reply"]["reason"].startswith("Custom models only")
    assert cases["stack"]["adapterQuote"] == {
        "addedDefaults": ["numOutputs"],
        "reply": {"creativeUnitsCost": 3.5, "creativeUnitsDiscount": 0, "costDetails": {"x": 3.5}},
    }
    assert "adapterQuote" not in cases["wrong_type"] and "adapterQuote" not in cases["direct"]
    assert contracts["routes"] == capture.decide(contracts["dryRuns"])


def test_a_private_copy_of_a_captured_public_model_keeps_the_public_id(service, capsys):
    # The public parent is not a private value, so the leak check must not
    # refuse a capture that records it; the private copy itself stays hidden.
    service.private[0]["parentModelId"] = LORA
    assert capture.main([]) == 0
    text = "\n".join(written(service.root).values())
    assert LORA in text
    output = capsys.readouterr()
    assert PRIVATE_LORA not in text + output.out + output.err
    assert PRIVATE_NAME not in text + output.out + output.err


def test_a_reply_echoing_a_readable_private_id_is_scrubbed(service):
    # A slug-like private ID escapes the random-identifier pattern, so it is
    # replaced only because the private list registered it.
    slug = "model_private-character-slug"
    service.private[0]["id"] = slug
    service.echo = slug
    assert capture.main([]) == 0
    contracts = json.loads(written(service.root)["models/trained/contracts.json"])
    reason = {case["case"]: case for case in contracts["dryRuns"]}["wrong_type"]["reply"]["reason"]
    assert reason == f"Invalid model(s): {COMPOSITION}. (seen model_FIXTURE0000000000000004)"
    assert slug not in "\n".join(written(service.root).values())


def test_a_private_value_the_scrubber_cannot_reach_stops_the_capture(service, capsys):
    # Reply keys are not rewritten; the final leak check refuses to write them.
    service.reply_key = PRIVATE_ASSET
    assert capture.main([]) == 1
    assert written(service.root) == {}
    output = capsys.readouterr()
    assert PRIVATE_ASSET not in output.out + output.err


def test_scope_without_an_image_skips_reference_cases(service):
    service.assets = []
    assert capture.main([]) == 0
    contracts = json.loads(written(service.root)["models/trained/contracts.json"])
    reference = {case["case"]: case for case in contracts["dryRuns"]}["reference"]
    assert reference["status"] is None
    assert reference["skipped"] == "No image asset in the selected scope"
    assert contracts["routes"]["stack"] == {"result": "accepted", "cases": ["stack", "reference"]}


@pytest.mark.parametrize(
    "fail_path", ["/v1/models", f"/v1/models/{LORA}", f"/v1/generate/custom/{BASE}"]
)
def test_failures_leave_existing_fixtures_and_hide_service_text(service, capsys, fail_path):
    old = service.root / "models/trained/contracts.json"
    old.parent.mkdir(parents=True)
    old.write_text("old contracts", encoding="utf-8")
    service.fail_path = fail_path
    assert capture.main([]) == 1
    assert old.read_text(encoding="utf-8") == "old contracts"
    assert sorted(written(service.root)) == ["models/trained/contracts.json"]
    output = capsys.readouterr()
    assert output.err == "Trained-model contract capture failed; no fixture was changed.\n"
    assert PRIVATE_NAME not in output.out + output.err
    assert all(client._closed for client in service.clients)


def test_a_captured_model_missing_from_the_public_list_stops_before_dry_runs(service):
    service.public_ids = [BASE, LORA]
    assert capture.main([]) == 1
    assert not any(r.url.path.startswith("/v1/generate/") for r in service.requests)
    assert written(service.root) == {}


def test_dry_run_refuses_options_that_are_not_a_dry_run():
    sent = []

    def handle(request):
        sent.append(request)
        return httpx.Response(269, json={"creativeUnitsCost": 1})

    client = SDKAdapter(
        Credentials("fixture-key", "fixture-secret"),
        online=lambda: True,
        base_url="https://service.example.invalid/v1",
        transport=httpx.MockTransport(handle),
    )
    original = client._request

    def tampered(method, *args, **kwargs):
        kwargs.pop("dry_run")
        return original(method, *args, **kwargs)

    with client:
        assert capture.dry_run(client, BASE, {"prompt": "p"}) == (269, {"creativeUnitsCost": 1})
        client._request = tampered
        with pytest.raises(ValueError, match="dry runs only"):
            capture.dry_run(client, BASE, {"prompt": "p"})
        with pytest.raises(ValueError):
            capture.dry_run(client, "bad/id", {"prompt": "p"})
    assert len(sent) == 1 and sent[0].url.params["dryRun"] == "true"


def test_scrubber_keeps_public_and_schema_text_and_replaces_the_rest():
    scrubber = capture.Scrubber({LORA}, [PROJECT, PRIVATE_ASSET])
    text = (
        f"{LORA} model_array model_bfl-flux-1-dev {capture.MISSING_MODEL} "
        f"{UNLISTED_CONCEPT} {PRIVATE_ASSET} in {PROJECT} {UNLISTED_CONCEPT}"
    )
    assert scrubber.text(text) == (
        f"{LORA} model_array model_bfl-flux-1-dev {capture.MISSING_MODEL} "
        "model_FIXTURE0000000000000001 asset_FIXTURE0000000000000001 in "
        "private_FIXTURE0000000000000001 model_FIXTURE0000000000000001"
    )
    assert scrubber.data({"a": [PROJECT, 3, None]}) == {
        "a": ["private_FIXTURE0000000000000001", 3, None]
    }
    assert scrubber.leaked(f"x {PRIVATE_ASSET}") and not scrubber.leaked(scrubber.text(text))


def test_decide_classifies_route_outcomes():
    cases = [
        {"case": "a", "route": "stack", "status": 269},
        {"case": "b", "route": "stack", "status": None},
        {"case": "c", "route": "composition", "status": 269},
        {"case": "d", "route": "composition", "status": 400},
        {"case": "e", "route": "direct", "status": 404},
        {"case": "f", "route": "check", "status": 400},
    ]
    assert capture.decide(cases) == {
        "stack": {"result": "accepted", "cases": ["a", "b"]},
        "model_id": {"result": "not captured", "cases": []},
        "composition": {"result": "mixed", "cases": ["c", "d"]},
        "direct": {"result": "rejected", "cases": ["e"]},
    }


def test_publish_restores_the_previous_directory_when_replacement_fails(tmp_path, monkeypatch):
    target = tmp_path / "models/trained"
    target.mkdir(parents=True)
    (target / "contracts.json").write_text("previous", encoding="utf-8")
    replace = capture.os.replace
    calls = []

    def fail_second(source, destination):
        calls.append(Path(destination).name)
        if len(calls) == 2:
            raise OSError("disk full")
        replace(source, destination)

    monkeypatch.setattr(capture.os, "replace", fail_second)
    with pytest.raises(OSError):
        capture.publish({"models/trained/contracts.json": {"new": True}}, tmp_path)
    assert (target / "contracts.json").read_text(encoding="utf-8") == "previous"
    assert not list(tmp_path.glob(".recording-*"))


def test_publish_replaces_stale_files(tmp_path):
    target = tmp_path / "models/trained"
    (target / "public").mkdir(parents=True)
    (target / "public/model_Stale000000000000000.json").write_text("{}", encoding="utf-8")
    capture.publish({"models/trained/contracts.json": {"new": True}}, tmp_path)
    assert written(tmp_path) == {"models/trained/contracts.json": '{\n "new": true\n}\n'}


def test_publish_refuses_a_symlinked_output(tmp_path):
    (tmp_path / "models").mkdir()
    (tmp_path / "elsewhere").mkdir()
    (tmp_path / "models/trained").symlink_to(tmp_path / "elsewhere")
    with pytest.raises(ValueError, match="inside its directory"):
        capture.publish({"models/trained/contracts.json": {}}, tmp_path)


@pytest.mark.parametrize("argv,code", [(["--help"], 0), (["--unknown"], 2)])
def test_cli_help_and_invalid_arguments_do_not_request_credentials(monkeypatch, argv, code):
    settings = Mock(side_effect=AssertionError("must not request credentials"))
    monkeypatch.setattr(capture, "live_settings", settings)
    with pytest.raises(SystemExit) as error:
        capture.main(argv)
    assert error.value.code == code
    settings.assert_not_called()
