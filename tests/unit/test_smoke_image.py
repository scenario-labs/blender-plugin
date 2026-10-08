# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Real SDK/coordinator/store acceptance commands with offline service responses."""

import json
import runpy
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from pathlib import Path
from threading import Event

import httpx
import pytest

from scenario.core.api.sdk_adapter import AdapterError, Credentials
from scenario.core.config import Credentials as ToolCredentials
from scenario.core.jobs.coordinator import SubmissionUncertain
from scenario.core.jobs.credential_storage import open_credential_store
from scenario.core.jobs.results import ResultError
from scenario.core.jobs.store import JobState, JobStore, StoreError
from scenario.core.jobs.transfers import DownloadedResult, ResultDownloader, StoragePolicy
from tools import smoke_image as smoke
from tools.dev_config import LiveSettings

COST = "0.10000000000000001"
DATA = b"synthetic image bytes; receipt verification, not image decoding"
MODEL = {"id": "model", "type": "custom", "inputs": [{"name": "prompt", "type": "string"}]}
SETTINGS = LiveSettings(ToolCredentials("fixture-key", "fixture-secret"))


class Downloads(ResultDownloader):
    def __init__(self):
        super().__init__(StoragePolicy(frozenset({"cdn.scenario.com"})), online_access=lambda: True)
        self.fail = False
        self.paths = []

    def download(self, url, *, root, name, expected_size, expected_sha256):
        self._policy.destination(url)
        if self.fail:
            raise RuntimeError("private-signed-url?secret=redact")
        assert expected_size == len(DATA)
        path = root / name
        with path.open("xb") as output:
            output.write(DATA)
        self.paths.append(path)
        return DownloadedResult(name, len(DATA), smoke.digest(DATA))


@pytest.fixture(params=smoke.RESULT_KINDS)
def run(tmp_path, request):
    kind = request.param
    root = tmp_path / "run"
    inputs = tmp_path / "parameters.json"
    inputs.write_text('{"prompt":"private fixture prompt"}')
    calls = []
    behavior = {"cost": COST, "model": MODEL, "status": "success", "fail": None}
    if kind == "material":
        recorded = json.loads(
            (Path(__file__).parents[1] / "fixtures/models/model_patina-material.json").read_text()
        )["model"]
        behavior["model"] = {
            **MODEL,
            "inputs": [
                *MODEL["inputs"],
                *(field for field in recorded["inputs"] if field["name"] in {"maps", "numOutputs"}),
            ],
        }
    media_types = {
        "image": [("image/png", None)],
        "video": [("video/mp4", None)],
        "audio": [("audio/wav", None)],
        "model": [("model/gltf-binary", None), ("image/png", None)],
        "material": [
            ("image/png", role)
            for role in (
                "texture",
                "texture-albedo",
                "texture-normal",
                "texture-smoothness",
                "texture-metallic",
                "texture-height",
            )
        ],
    }
    behavior["assets"] = [
        {
            "id": f"asset-{index}",
            "status": "success",
            "mimeType": mime,
            "properties": {"size": len(DATA)},
            "metadata": {"type": role},
            "url": "https://cdn.scenario.com/result?secret=redact",
        }
        for index, (mime, role) in enumerate(media_types[kind])
    ]
    downloads = Downloads()

    def store(settings=SETTINGS):
        return open_credential_store(
            root,
            Credentials(settings.credentials.key, settings.credentials.secret),
            project_id=settings.project_id,
        )

    def handler(request):
        calls.append(request)
        assert (
            request.headers["Authorization"]
            == Credentials(SETTINGS.credentials.key, SETTINGS.credentials.secret).authorization()
        )
        if request.url.path == "/v1/models/model":
            return httpx.Response(200, json={"model": behavior["model"]})
        if request.url.params.get("dryRun") == "true":
            if behavior["fail"] == "estimate":
                raise httpx.ReadTimeout("private response", request=request)
            if callable(behavior.get("quote_hook")):
                behavior["quote_hook"]()
            return httpx.Response(200, content='{"creativeUnitsCost":' + behavior["cost"] + "}")
        if request.method == "POST":
            records = store(
                replace(SETTINGS, project_id=request.url.params.get("projectId"))
            ).records()
            assert len(records) == 1 and records[0].state == JobState.SUBMITTING
            assert (root / "submission-attempt").is_file()
            if behavior["fail"] == "submit":
                raise httpx.ReadTimeout("private signed URL", request=request)
            return httpx.Response(200, json={"job": {"jobId": "remote"}})
        if request.url.path == "/v1/jobs/remote":
            if behavior["fail"] == "poll":
                raise httpx.ReadTimeout("private response", request=request)
            return httpx.Response(
                200,
                json={
                    "job": {
                        "jobId": "remote",
                        "status": behavior["status"],
                        "metadata": {"assetIds": [asset["id"] for asset in behavior["assets"]]},
                    }
                },
            )
        if request.url.path.startswith("/v1/assets/"):
            asset = next(a for a in behavior["assets"] if request.url.path.endswith("/" + a["id"]))
            return httpx.Response(200, json={"asset": asset})
        raise AssertionError("Unexpected SDK request")

    def args(command, **overrides):
        values = [command, "--run-dir", str(root)]
        if command == "quote":
            values += ["--model", "model", "--parameters", str(inputs)]
        if command == "submit":
            values += [
                "--approved-quote",
                smoke.digest((root / "quote.json").read_bytes()),
                "--approved-cost",
                COST,
                "--max-cu",
                COST,
            ]
        result = smoke.parser(default_result_kind=kind).parse_args(values)
        for name, value in overrides.items():
            setattr(result, name, value)
        return result

    def execute(command, *, settings=SETTINGS, **overrides):
        return smoke.execute(
            args(command, **overrides),
            settings,
            transport=httpx.MockTransport(handler),
            downloader=downloads,
        )

    return root, calls, behavior, downloads, store, args, execute


def paid(calls):
    return [call for call in calls if call.method == "POST" and "dryRun" not in call.url.params]


def test_quote_submit_restart_verify_exact_cost_and_scope_without_project(run, capsys):
    root, calls, _, downloads, store, _, execute = run
    assert execute("quote") == 0
    assert len(calls) == 2 and not paid(calls) and not store().records()
    assert execute("submit") == 0
    assert len(paid(calls)) == 1
    assert all("projectId" not in call.url.params for call in calls)
    assert all("ipDetection" not in call.url.params for call in calls)
    assert store().records()[0].intent.quote_cost == COST
    before = len(calls)
    assert execute("resume") == 0 and len(calls) == before
    with pytest.raises(smoke.SmokeError, match="already exists"):
        execute("submit")
    assert len(paid(calls)) == 1 and len(downloads.paths) == len(store().records()[0].results)
    output = capsys.readouterr().out + (root / "report.json").read_text()
    for private in (
        "fixture-key",
        "fixture-secret",
        "private fixture",
        "secret=redact",
        "remote",
        "asset",
    ):
        # The public state name 'remote' is emitted; actual IDs are not included
        # in JSON reports and are checked separately below.
        if private != "remote":
            assert private not in output
    report = json.loads((root / "report.json").read_text())
    assert report["jobs"][0]["results"] == [
        {"size": len(DATA), "sha256": smoke.digest(DATA)} for _ in downloads.paths
    ]
    assert "remote" not in (root / "report.json").read_text()


@pytest.mark.parametrize("change", ["approved_cost", "max_cu", "approved_quote"])
def test_bad_approval_stops_before_any_new_network(run, change):
    root, calls, _, _, store, _, execute = run
    execute("quote")
    values = {
        "approved_cost": smoke.decimal_cost("0.1"),
        "max_cu": smoke.decimal_cost("0"),
        "approved_quote": "0" * 64,
    }
    with pytest.raises(smoke.SmokeError):
        execute("submit", **{change: values[change]})
    assert len(calls) == 2 and not paid(calls) and not store().records()
    assert not (root / "submission-attempt").exists()


@pytest.mark.parametrize("change", ["cost", "model"])
def test_fresh_quote_cost_or_normalized_payload_drift_cannot_spend(run, change):
    _, calls, behavior, _, store, _, execute = run
    execute("quote")
    behavior[change] = (
        "0.1"
        if change == "cost"
        else {
            **MODEL,
            "inputs": MODEL["inputs"] + [{"name": "seed", "type": "integer", "default": 123}],
        }
    )
    with pytest.raises(smoke.SmokeError, match="Fresh quote"):
        execute("submit")
    assert not paid(calls) and not store().records()
    before = len(calls)
    with pytest.raises(smoke.SmokeError, match="already attempted"):
        execute("submit")
    assert len(calls) == before


@pytest.mark.parametrize("command", ["submit", "resume"])
@pytest.mark.parametrize(
    "settings",
    [
        replace(SETTINGS, project_id="another-project"),
        LiveSettings(ToolCredentials("other-key", "other-secret")),
    ],
)
def test_scope_change_rejected_before_network(run, command, settings):
    _, calls, _, _, _, _, execute = run
    execute("quote")
    with pytest.raises(smoke.SmokeError, match="Credentials or project changed"):
        execute(command, settings=settings)
    assert len(calls) == 2


def test_explicit_project_is_preserved_for_every_sdk_request(run):
    _, calls, _, _, _, _, execute = run
    settings = replace(SETTINGS, project_id="selected-project")
    execute("quote", settings=settings)
    assert execute("submit", settings=settings) == 0
    assert all(call.url.params["projectId"] == "selected-project" for call in calls)


def test_lost_receipt_is_durable_and_resume_never_replays(run):
    _, calls, behavior, _, store, _, execute = run
    execute("quote")
    behavior["fail"] = "submit"
    with pytest.raises(SubmissionUncertain):
        execute("submit")
    assert store().records()[0].state == JobState.UNCERTAIN
    before = len(calls)
    for command in ("resume", "submit"):
        with pytest.raises(smoke.SmokeError) as error:
            execute(command)
        assert error.value.code == 4
    assert len(calls) == before and len(paid(calls)) == 1


@pytest.mark.parametrize("failure", ["estimate", "poll", "download"])
def test_recovery_retains_claims_and_never_generates_again(run, failure):
    _, calls, behavior, downloads, store, _, execute = run
    execute("quote")
    behavior["fail"] = failure
    downloads.fail = failure == "download"
    with pytest.raises((AdapterError, ResultError)):
        execute("submit")
    count = len(paid(calls))
    behavior["fail"], downloads.fail = None, False
    if failure == "estimate":
        assert not store().records()
        with pytest.raises(smoke.SmokeError, match="already attempted"):
            execute("submit")
        with pytest.raises(smoke.SmokeError, match="one saved request"):
            execute("resume")
    else:
        assert execute("resume") == 0
    assert len(paid(calls)) == count


def test_failed_durable_claim_cannot_spend(run, monkeypatch):
    _, calls, _, _, store, _, execute = run
    execute("quote")
    original = JobStore.transition

    def fail(self, *args, **kwargs):
        if kwargs.get("state") == JobState.SUBMITTING:
            raise StoreError("private storage path")
        return original(self, *args, **kwargs)

    monkeypatch.setattr(JobStore, "transition", fail)
    with pytest.raises(StoreError):
        execute("submit")
    assert store().records()[0].state == JobState.PREPARED and not paid(calls)
    with pytest.raises(smoke.SmokeError) as error:
        execute("resume")
    assert error.value.code == 4 and not paid(calls)


def test_competing_submit_process_owners_only_one_can_dispatch(run):
    _, calls, behavior, _, _, _, execute = run
    execute("quote")
    entered, release = Event(), Event()

    def pause():
        entered.set()
        assert release.wait(10)

    behavior["quote_hook"] = pause
    with ThreadPoolExecutor(max_workers=1) as pool:
        first = pool.submit(execute, "submit")
        try:
            assert entered.wait(10)
            with pytest.raises(smoke.SmokeError, match="already attempted"):
                execute("submit")
        finally:
            release.set()
        assert first.result(timeout=10) == 0
    assert len(paid(calls)) == 1


def test_quote_cannot_overwrite_run_and_changed_result_fails_offline(run):
    _, calls, _, downloads, _, _, execute = run
    execute("quote")
    with pytest.raises(FileExistsError):
        execute("quote")
    assert len(calls) == 2
    execute("submit")
    downloads.paths[0].write_bytes(b"changed")
    before = len(calls)
    with pytest.raises(Exception, match="could not be verified"):
        execute("resume")
    assert len(calls) == before and len(paid(calls)) == 1


@pytest.mark.parametrize("value", ["NaN", "Infinity", "-1", "1e10000", "", "0.1junk"])
def test_invalid_cap_rejected_without_credentials_or_calls(value, monkeypatch):
    monkeypatch.setattr(smoke, "live_settings", lambda: pytest.fail("credentials accessed"))
    with pytest.raises(SystemExit) as error:
        smoke.main(
            [
                "submit",
                "--run-dir",
                "unused",
                "--approved-quote",
                "0" * 64,
                "--approved-cost",
                "1",
                "--max-cu",
                value,
            ]
        )
    assert error.value.code == 2


def test_opt_in_missing_and_private_errors_are_sanitized(monkeypatch, capsys):
    monkeypatch.delenv("SCENARIO_SMOKE", raising=False)
    monkeypatch.setattr(smoke, "live_settings", lambda: pytest.fail("credentials accessed"))
    assert (
        smoke.main(
            [
                "submit",
                "--run-dir",
                "unused",
                "--approved-quote",
                "0" * 64,
                "--approved-cost",
                "1",
                "--max-cu",
                "1",
            ]
        )
        == 2
    )
    monkeypatch.setattr(smoke, "live_settings", lambda: SETTINGS)

    def fail(*args):
        raise RuntimeError("private response?token=secret")

    monkeypatch.setattr(smoke, "execute", fail)
    assert smoke.main(["resume", "--run-dir", "unused"]) == 1
    assert "private response" not in capsys.readouterr().out


@pytest.mark.parametrize(
    "script_name", ["smoke_image", "smoke_video", "smoke_material", "smoke_image_to_3d"]
)
def test_compatibility_entry_point_checks_credentials_before_network(
    tmp_path, monkeypatch, capsys, script_name
):
    script = Path(__file__).resolve().parents[1] / "smoke" / (script_name + ".py")
    monkeypatch.setattr(
        "sys.argv",
        [
            str(script),
            "quote",
            "--run-dir",
            str(tmp_path / "run"),
            "--model",
            "model",
            "--parameters",
            "unused",
        ],
    )
    for name in ("SCENARIO_TEST_API_KEY", "SCENARIO_TEST_API_SECRET"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("SCENARIO_API_KEY", "unrelated")
    monkeypatch.setenv("SCENARIO_API_SECRET", "unrelated")
    monkeypatch.setattr(smoke, "SDKAdapter", lambda *a, **kw: pytest.fail("client constructed"))
    with pytest.raises(SystemExit) as error:
        runpy.run_path(str(script), run_name="__main__")
    assert error.value.code == 2
    assert "Configure the explicit test API-key pair" in capsys.readouterr().out


def test_quote_file_changed_after_approval_rejected(run):
    root, calls, _, _, _, args, execute = run
    execute("quote")
    approved = args("submit")
    plan = json.loads((root / "quote.json").read_text())
    plan["parameters"]["prompt"] = "different input"
    (root / "quote.json").write_bytes(smoke.json_bytes(plan))
    with pytest.raises(smoke.SmokeError, match="record changed"):
        smoke.execute(approved, SETTINGS)
    assert len(calls) == 2 and not (root / "submission-attempt").exists()


def test_missing_scope_key_cannot_silently_replace_history(run):
    root, calls, _, _, _, _, execute = run
    execute("quote")
    (root / "scope.key").unlink()
    with pytest.raises(smoke.SmokeError, match="incomplete"):
        execute("submit")
    assert not (root / "scope.key").exists() and len(calls) == 2


def test_polling_deadline_preserves_known_job_for_resume(run, monkeypatch):
    _, calls, behavior, _, store, _, execute = run
    execute("quote")
    behavior["status"] = "pending"
    original = smoke.follow
    ticks = iter((0, 0, 1, 2))

    def bounded(coordinator, storage, *, timeout, result_kind, material_payload=None):
        return original(
            coordinator,
            storage,
            timeout=1,
            result_kind=result_kind,
            material_payload=material_payload,
            clock=lambda: next(ticks),
            sleep=lambda _: None,
        )

    monkeypatch.setattr(smoke, "follow", bounded)
    with pytest.raises(smoke.SmokeError, match="deadline") as error:
        execute("submit")
    assert error.value.code == 4 and store().records()[0].state == JobState.REMOTE
    behavior["status"] = "success"
    monkeypatch.setattr(smoke, "follow", original)
    assert execute("resume") == 0 and len(paid(calls)) == 1


def test_zero_quote_can_only_submit_with_explicit_zero_approval(run):
    _, calls, behavior, _, _, _, execute = run
    behavior["cost"] = "0"
    execute("quote")
    assert (
        execute("submit", approved_cost=smoke.decimal_cost("0"), max_cu=smoke.decimal_cost("0"))
        == 0
    )
    assert len(paid(calls)) == 1


def test_main_uses_selected_test_pair_despite_ambient_runtime_values(tmp_path, monkeypatch):
    monkeypatch.setenv("SCENARIO_TEST_API_KEY", "selected-key")
    monkeypatch.setenv("SCENARIO_TEST_API_SECRET", "selected-secret")
    monkeypatch.setenv("SCENARIO_TEST_PROJECT_ID", "selected-project")
    monkeypatch.setenv("SCENARIO_API_KEY", "ambient-key")
    monkeypatch.setenv("SCENARIO_API_SECRET", "ambient-secret")
    calls = []

    def handler(request):
        calls.append(request)
        assert (
            request.headers["Authorization"]
            == Credentials("selected-key", "selected-secret").authorization()
        )
        assert request.url.params["projectId"] == "selected-project"
        if request.method == "GET":
            return httpx.Response(200, json={"model": MODEL})
        assert request.url.params["dryRun"] == "true"
        return httpx.Response(200, content='{"creativeUnitsCost":1}')

    original = smoke.SDKAdapter

    def adapter(credentials, **kwargs):
        kwargs["transport"] = httpx.MockTransport(handler)
        return original(credentials, **kwargs)

    monkeypatch.setattr(smoke, "SDKAdapter", adapter)
    inputs = tmp_path / "input.json"
    inputs.write_text('{"prompt":"fixture"}')
    assert (
        smoke.main(
            [
                "quote",
                "--run-dir",
                str(tmp_path / "run"),
                "--parameters",
                str(inputs),
                "--model",
                "model",
            ]
        )
        == 0
    )
    assert len(calls) == 2 and not paid(calls)


def test_wrong_result_kind_never_counts_as_success_or_regenerates(run):
    _, calls, behavior, _, store, _, execute = run
    execute("quote")
    for asset in behavior["assets"]:
        asset["mimeType"] = "application/octet-stream"
    with pytest.raises(smoke.SmokeError, match="approved result kind"):
        execute("submit")
    assert store().records()[0].state == JobState.READY
    before = len(calls)
    with pytest.raises(smoke.SmokeError, match="approved result kind"):
        execute("resume")
    assert len(calls) == before and len(paid(calls)) == 1


def test_result_kind_is_bound_to_quote_and_cannot_switch_wrappers(run):
    root, calls, _, _, _, args, execute = run
    execute("quote")
    approved = args("submit")
    plan = json.loads((root / "quote.json").read_text())
    other = "audio" if plan["result_kind"] != "audio" else "video"
    for command in ("submit", "resume"):
        with pytest.raises(smoke.SmokeError, match="matching this run"):
            execute(command, expected_result_kind=other)
    plan["result_kind"] = other
    (root / "quote.json").write_bytes(smoke.json_bytes(plan))
    approved.expected_result_kind = None
    with pytest.raises(smoke.SmokeError, match="record changed"):
        smoke.execute(approved, SETTINGS)
    assert len(calls) == 2 and not (root / "submission-attempt").exists()


def test_generic_entry_point_requires_explicit_result_kind_before_credentials(monkeypatch):
    monkeypatch.setattr(smoke, "live_settings", lambda: pytest.fail("credentials accessed"))
    with pytest.raises(SystemExit) as error:
        smoke.main(
            ["quote", "--run-dir", "unused", "--model", "model", "--parameters", "unused"],
            default_result_kind=None,
        )
    assert error.value.code == 2


def test_original_image_quote_can_resume_and_submit_without_migration(run):
    root, calls, _, _, _, _, execute = run
    execute("quote")
    plan = json.loads((root / "quote.json").read_text())
    if plan["result_kind"] != "image":
        return
    plan.pop("result_kind")
    plan["schema_version"] = 1
    (root / "quote.json").write_bytes(smoke.json_bytes(plan))
    assert execute("submit") == 0
    assert execute("resume") == 0 and len(paid(calls)) == 1


@pytest.mark.parametrize(
    "script_name", ["smoke_image", "smoke_video", "smoke_material", "smoke_image_to_3d"]
)
@pytest.mark.parametrize("command", ["bare", "submit"])
def test_every_script_blocks_unapproved_spending_before_credentials(
    script_name, command, monkeypatch
):
    script = Path(__file__).resolve().parents[1] / "smoke" / (script_name + ".py")
    monkeypatch.delenv("SCENARIO_SMOKE", raising=False)
    monkeypatch.setattr(smoke, "live_settings", lambda: pytest.fail("credentials accessed"))
    argv = [str(script)]
    if command == "submit":
        argv += [
            "submit",
            "--run-dir",
            "unused",
            "--approved-quote",
            "0" * 64,
            "--approved-cost",
            "1",
            "--max-cu",
            "1",
        ]
    monkeypatch.setattr("sys.argv", argv)
    with pytest.raises(SystemExit) as error:
        runpy.run_path(str(script), run_name="__main__")
    assert error.value.code == 2


@pytest.mark.parametrize("run", ["material"], indirect=True)
@pytest.mark.parametrize(
    "missing",
    [
        "texture-albedo",
        "texture-normal",
        "texture-smoothness",
        "texture-metallic",
        "texture-height",
    ],
)
def test_material_defaults_require_every_quoted_map_on_submit_and_resume(run, missing):
    root, calls, behavior, _, store, _, execute = run
    execute("quote")
    plan = json.loads((root / "quote.json").read_text())
    assert plan["schema_version"] == 3
    assert json.loads(plan["material_payload_json"])["maps"] == [
        "basecolor",
        "normal",
        "roughness",
        "metalness",
        "height",
    ]
    behavior["assets"] = [a for a in behavior["assets"] if a["metadata"]["type"] != missing]
    with pytest.raises(smoke.SmokeError, match="approved result kind"):
        execute("submit")
    assert store().records()[0].state == JobState.READY
    before = len(calls)
    with pytest.raises(smoke.SmokeError, match="approved result kind"):
        execute("resume")
    assert len(calls) == before and len(paid(calls)) == 1


@pytest.mark.parametrize("run", ["material"], indirect=True)
@pytest.mark.parametrize("maps", [[], ["normal"], ["basecolor", "normal"]])
def test_material_explicit_subset_and_texture_only_do_not_require_other_maps(run, maps):
    root, calls, behavior, _, _, _, execute = run
    (root.parent / "parameters.json").write_text(json.dumps({"prompt": "fixture", "maps": maps}))
    selected = {
        "texture",
        *("texture-albedo" if name == "basecolor" else "texture-" + name for name in maps),
    }
    behavior["assets"] = [a for a in behavior["assets"] if a["metadata"]["type"] in selected]
    execute("quote")
    assert execute("submit") == execute("resume") == 0
    assert len(paid(calls)) == 1


@pytest.mark.parametrize("run", ["material"], indirect=True)
@pytest.mark.parametrize("complete", [False, True])
def test_material_requires_each_requested_map_for_the_quoted_output_count(run, complete):
    root, calls, behavior, _, _, _, execute = run
    (root.parent / "parameters.json").write_text(json.dumps({"prompt": "fixture", "numOutputs": 2}))
    second = [{**a, "id": a["id"] + "-second"} for a in behavior["assets"]]
    if not complete:
        second = [a for a in second if a["metadata"]["type"] != "texture-height"]
    behavior["assets"] += second
    execute("quote")
    if complete:
        assert execute("submit") == execute("resume") == 0
    else:
        with pytest.raises(smoke.SmokeError, match="approved result kind"):
            execute("submit")
    assert len(paid(calls)) == 1


@pytest.mark.parametrize("run", ["material"], indirect=True)
def test_material_resume_rejects_expectations_rewritten_after_submission(run):
    root, calls, behavior, _, _, _, execute = run
    execute("quote")
    behavior["assets"] = behavior["assets"][:3]
    with pytest.raises(smoke.SmokeError, match="approved result kind"):
        execute("submit")
    plan = json.loads((root / "quote.json").read_text())
    payload = json.loads(plan["material_payload_json"])
    payload["maps"] = ["basecolor", "normal"]
    plan["material_payload_json"] = json.dumps(payload)
    plan["payload_sha256"] = smoke.digest(plan["material_payload_json"].encode())
    (root / "quote.json").write_bytes(smoke.json_bytes(plan))
    before = len(calls)
    with pytest.raises(smoke.SmokeError, match="differ from the saved request"):
        execute("resume")
    assert len(calls) == before and len(paid(calls)) == 1


@pytest.mark.parametrize("run", ["material"], indirect=True)
def test_material_old_quote_cannot_spend_or_claim_completeness_but_can_recover(run):
    root, calls, behavior, _, store, _, execute = run
    execute("quote")
    quote_path = root / "quote.json"
    current = quote_path.read_bytes()
    plan = json.loads(current)
    plan["schema_version"] = 2
    plan.pop("material_payload_json")
    quote_path.write_bytes(smoke.json_bytes(plan))
    before = len(calls)
    with pytest.raises(smoke.SmokeError, match="create a new quote"):
        execute("submit")
    assert len(calls) == before and not (root / "submission-attempt").exists()
    quote_path.write_bytes(current)
    behavior["fail"] = "poll"
    with pytest.raises(AdapterError):
        execute("submit")
    quote_path.write_bytes(smoke.json_bytes(plan))
    behavior["fail"] = None
    with pytest.raises(smoke.SmokeError, match="inspect saved results"):
        execute("resume")
    assert store().records()[0].state == JobState.READY
    assert all(item.receipt for item in store().records()[0].results)
    assert len(paid(calls)) == 1


@pytest.mark.parametrize("run", ["material"], indirect=True)
def test_material_changed_schema_map_defaults_require_new_approval(run):
    _, calls, behavior, _, store, _, execute = run
    execute("quote")
    behavior["model"] = {
        **behavior["model"],
        "inputs": [
            {**field, "default": ["basecolor", "normal"]} if field["name"] == "maps" else field
            for field in behavior["model"]["inputs"]
        ],
    }
    with pytest.raises(smoke.SmokeError, match="Fresh quote or payload changed"):
        execute("submit")
    assert not paid(calls) and not store().records()


@pytest.mark.parametrize("run", ["material"], indirect=True)
def test_material_model_without_supported_map_contract_cannot_produce_approval(run):
    root, calls, behavior, _, _, _, execute = run
    behavior["model"] = MODEL
    with pytest.raises(smoke.SmokeError, match="supported maps"):
        execute("quote")
    assert not (root / "quote.json").exists() and not paid(calls)
