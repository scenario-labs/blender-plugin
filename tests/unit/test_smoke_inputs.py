# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Reference automation uses real SDK/store commands without live transfers."""

import copy
import json
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

import httpx
import pytest

from scenario.core.config import Credentials
from scenario.core.jobs.upload_transfers import PartUploader, S3UploadPolicy, UploadedPart
from scenario.core.jobs.uploads import UploadError, UploadMutationUncertain
from tools import smoke_image as model
from tools import smoke_inputs as inputs
from tools import smoke_suite as suite
from tools.dev_config import LiveSettings

SETTINGS = LiveSettings(Credentials("fixture-key", "fixture-secret"), "fixture-project")
# Only the create response carries the multipart plan; retrieval omits it.
PLAN_FIELDS = ("originalFileName", "contentType", "fileSize", "partsCount", "parts")


@pytest.fixture
def env(tmp_path):
    source = tmp_path / "source"
    source.mkdir()
    entries = []
    for name in ["first", "second"]:
        data = ("synthetic " + name).encode()
        (source / (name + ".png")).write_bytes(data)
        entries.append(
            {
                "name": name,
                "file": name + ".png",
                "sha256": model.digest(data),
                "kind": "image",
                "content_type": "image/png",
            }
        )
    plan = {
        "schema_version": 2,
        "project_id": SETTINGS.project_id,
        "inputs": entries,
        "cases": [
            {
                "name": "edit",
                "model": "fixture-model",
                "result_kind": "image",
                "parameters": {"images": [{"$input": "first"}, {"$input": "second"}]},
            }
        ],
    }
    path = tmp_path / "plan.json"
    root = tmp_path / "suite-inputs"
    events, remote = [], {}
    behavior = {"fail": None, "imported": False, "plan": {}}

    def handler(request):
        assert request.url.params.get("projectId") == SETTINGS.project_id
        event = (
            "finalize"
            if request.url.path.endswith("/action")
            else "initialize"
            if request.method == "POST"
            else "poll"
        )
        events.append(event)
        assert (root / "inputs.json").is_file(), "Persist all input bindings before writes"
        if behavior["fail"] == event and events.count(event) >= behavior.get("fail_after", 1):
            raise httpx.ReadTimeout("private response must not escape", request=request)
        if event == "initialize":
            body = json.loads(request.content)
            ident = "upload-" + str(len(remote))
            expires = datetime.now(UTC) + timedelta(hours=48)
            remote[ident] = {
                "id": ident,
                "source": "multipart",
                "kind": body["kind"],
                "status": "pending",
                "fileName": "uploads/synthetic-storage/" + body["fileName"],
                "originalFileName": body["fileName"],
                "contentType": body["contentType"],
                "fileSize": body["fileSize"],
                "partsCount": body["parts"],
                "parts": [
                    {
                        "number": 1,
                        "url": "https://fixture-bucket.s3-accelerate.amazonaws.com/fixture"
                        "?partNumber=1&fixture-signature=private-fixture",
                        "expires": expires.isoformat(timespec="milliseconds").replace(
                            "+00:00", "Z"
                        ),
                    }
                ],
                **behavior["plan"],
            }
        else:
            ident = request.url.path.split("/")[-2 if event == "finalize" else -1]
        response = copy.deepcopy(remote[ident])
        if event != "initialize":
            response = {key: value for key, value in response.items() if key not in PLAN_FIELDS}
        if event == "finalize" or behavior["imported"]:
            response.update(status="imported", entityId="asset-" + ident)
            remote[ident] = {**remote[ident], **response}
        return httpx.Response(200, json={"upload": response})

    class Uploader(PartUploader):
        def __init__(self):
            super().__init__(S3UploadPolicy(), online_access=lambda: True)

        def upload(self, url, data, *, number, content_type, expected_sha256):
            self.policy.destination(url)
            events.append("put")
            assert model.digest(data) == expected_sha256
            if behavior["fail"] == "put":
                raise RuntimeError("private upload failure")
            return UploadedPart(number, len(data), expected_sha256)

    def args(command="upload"):
        path.write_bytes(model.json_bytes(plan))
        return SimpleNamespace(
            command=command,
            plan=path,
            approved_plan=model.digest(path.read_bytes()),
            input_root=source,
            run_dir=root,
            timeout=1,
        )

    upload_execute = inputs.execute

    def execute(arguments=None, settings=SETTINGS):
        return upload_execute(
            arguments or args(),
            settings,
            transport=httpx.MockTransport(handler),
            uploader=Uploader(),
        )

    return SimpleNamespace(
        plan=plan,
        path=path,
        root=root,
        source=source,
        args=args,
        execute=execute,
        events=events,
        behavior=behavior,
        remote=remote,
    )


def test_inputs_publish_exact_plan_without_generation_and_resume_offline(env, capsys):
    destination = env.execute()
    prepared = json.loads(destination.read_bytes())
    assert prepared["schema_version"] == 1
    assert prepared["cases"][0]["parameters"]["images"] == ["asset-upload-0", "asset-upload-1"]
    assert env.events == ["initialize", "poll", "put", "finalize"] * 2
    env.events.clear()
    assert env.execute(env.args("resume")) == destination
    assert env.events == []
    with pytest.raises(FileExistsError):
        env.execute()
    out = capsys.readouterr().out
    assert all(
        secret not in out
        for secret in [
            "fixture-key",
            "fixture-secret",
            "fixture-project",
            "asset-upload",
            "private",
            "first.png",
        ]
    )


@pytest.mark.parametrize("failure", ["initialize", "put", "finalize"])
def test_uncertain_upload_stops_remaining_inputs_and_resume_never_writes(env, failure):
    env.behavior["fail"] = failure
    with pytest.raises(UploadMutationUncertain):
        env.execute()
    assert env.events.count("initialize") == 1
    assert not (env.root / "prepared-plan.json").exists()
    env.events.clear()
    env.behavior.update(fail=None, imported=True)
    with pytest.raises(model.SmokeError):
        env.execute(env.args("resume"))
    assert all(event == "poll" for event in env.events)
    assert not (env.root / "prepared-plan.json").exists()


def test_resume_after_an_interrupted_transfer_reports_restart_without_sending(env, capsys):
    env.behavior["fail"] = "poll"
    with pytest.raises(UploadError, match="no bytes sent"):
        env.execute()
    assert env.events == ["initialize", "poll"]
    env.events.clear()
    env.behavior["fail"] = None
    with pytest.raises(model.SmokeError, match="start a new input upload run") as error:
        env.execute(env.args("resume"))
    assert error.value.code == 4
    # Recovery read the known upload once; it never sent, completed or recreated.
    assert env.events == ["poll"]
    assert not (env.root / "prepared-plan.json").exists()
    assert "private" not in capsys.readouterr().out


@pytest.mark.parametrize(
    "plan",
    [
        {"parts": []},
        {"originalFileName": None},
        {
            "parts": [
                {
                    "number": 1,
                    "url": "https://storage.example.invalid/part",
                    "expires": "2099-01-01T00:00:00Z",
                }
            ]
        },
    ],
)
def test_unusable_create_plan_stops_with_restart_guidance_before_any_part(env, plan):
    env.behavior["plan"] = plan
    with pytest.raises(model.SmokeError, match="start a new input upload run") as error:
        env.execute()
    assert error.value.code == 4
    assert env.events == ["initialize"]


def test_all_source_hashes_checked_before_first_remote_write(env):
    (env.source / "second.png").write_bytes(b"changed source")
    with pytest.raises(UploadError, match="stable upload source"):
        env.execute()
    assert env.events == []


@pytest.mark.parametrize(
    "change", ["scope", "plan", "path", "unused", "unknown", "link", "missing"]
)
def test_invalid_plan_or_source_fails_before_remote_work(env, change):
    args = env.args()
    if change == "scope":
        with pytest.raises(model.SmokeError):
            env.execute(args, replace(SETTINGS, project_id="other"))
        return
    if change == "plan":
        args.approved_plan = "0" * 64
    else:
        if change == "path":
            env.plan["inputs"][0]["file"] = "../first.png"
        elif change == "unused":
            env.plan["cases"][0]["parameters"]["images"].pop()
        elif change == "unknown":
            env.plan["cases"][0]["parameters"]["images"][0]["$input"] = "missing"
        elif change == "link":
            (env.source / "first.png").unlink()
            try:
                (env.source / "first.png").symlink_to(env.source / "second.png")
            except (OSError, NotImplementedError):
                pytest.skip("Symbolic link creation is unavailable on this host")
        else:
            (env.source / "first.png").unlink()
        args = env.args()
    with pytest.raises(model.SmokeError):
        env.execute(args)
    assert env.events == []


def test_recovery_rejects_changed_credentials_and_bindings(env):
    env.execute()
    env.events.clear()
    with pytest.raises(model.SmokeError, match="original input credentials"):
        env.execute(
            env.args("resume"), replace(SETTINGS, credentials=Credentials("other", "secret"))
        )
    manifest = env.root / "inputs.json"
    value = json.loads(manifest.read_bytes())
    value["requests"]["first"] = value["requests"]["second"]
    manifest.write_bytes(model.json_bytes(value))
    with pytest.raises(model.SmokeError, match="reviewed input"):
        env.execute(env.args("resume"))
    assert env.events == []


def test_quote_mode_cannot_upload_and_budget_mode_requires_explicit_authorization(env):
    env.args()
    for command in ["quote", "budget-run"]:
        argv = [command, "--plan", str(env.path), "--run-dir", str(env.root)]
        if command == "budget-run":
            argv += ["--max-cu", "1"]
        with pytest.raises(model.SmokeError, match="explicitly"):
            suite.run(suite.parser().parse_args(argv), SETTINGS)
    assert not env.root.exists()


def test_budget_automation_uploads_references_but_over_cap_never_generates(env, monkeypatch):
    env.args()
    quoted = []

    def handler(request):
        assert env.events == ["initialize", "poll", "put", "finalize"] * 2
        assert request.url.params.get("projectId") == SETTINGS.project_id
        if "/models/" in request.url.path:
            return httpx.Response(
                200,
                json={
                    "model": {
                        "id": "fixture-model",
                        "type": "custom",
                        "inputs": [{"name": "images", "type": "file_array"}],
                    }
                },
            )
        assert request.url.params.get("dryRun") == "true", "No paid call allowed above the cap"
        quoted.append(json.loads(request.content))
        return httpx.Response(200, content='{"creativeUnitsCost":2}')

    def model_execute(args, settings):
        return model.execute(args, settings, transport=httpx.MockTransport(handler))

    monkeypatch.setattr(inputs, "execute", env.execute)
    root = env.root.with_name("suite")
    args = suite.parser().parse_args(
        [
            "budget-run",
            "--plan",
            str(env.path),
            "--run-dir",
            str(root),
            "--max-cu",
            "1",
            "--upload-inputs",
            "--input-root",
            str(env.source),
        ]
    )
    with pytest.raises(model.SmokeError, match="aggregate cap"):
        suite.run(args, SETTINGS, execute=model_execute)
    assert quoted == [{"images": ["asset-upload-0", "asset-upload-1"]}]
    assert not (root / "suite-attempt").exists()
    assert (env.root / "prepared-plan.json").is_file()


def test_known_completion_uncertainty_can_recover_plan_using_reads_only(env):
    env.behavior.update(fail="finalize", fail_after=2)
    with pytest.raises(UploadMutationUncertain):
        env.execute()
    assert not (env.root / "prepared-plan.json").exists()
    env.events.clear()
    env.behavior.update(fail=None, imported=True)
    assert env.execute(env.args("resume")).is_file()
    assert env.events == ["poll"]


def test_zero_budget_stops_before_input_upload(env):
    env.args()
    args = suite.parser().parse_args(
        [
            "budget-run",
            "--plan",
            str(env.path),
            "--run-dir",
            str(env.root),
            "--max-cu",
            "0",
            "--upload-inputs",
            "--input-root",
            str(env.source),
        ]
    )
    with pytest.raises(model.SmokeError, match="positive explicit cap"):
        suite.run(args, SETTINGS)
    assert not env.root.exists() and not env.events


def test_upload_cli_requires_opt_in_before_credentials(env, monkeypatch):
    monkeypatch.delenv("SCENARIO_SMOKE", raising=False)
    monkeypatch.setattr(
        inputs, "live_settings", lambda: pytest.fail("Read credentials before opt-in")
    )
    args = env.args()
    assert (
        inputs.main(
            [
                "upload",
                "--plan",
                str(args.plan),
                "--run-dir",
                str(args.run_dir),
                "--input-root",
                str(args.input_root),
                "--approved-plan",
                args.approved_plan,
            ]
        )
        == 2
    )
    assert not env.root.exists()
