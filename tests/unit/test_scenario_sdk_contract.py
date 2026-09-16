# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Verify SDK behavior that the Blender integration will depend on.

Studio adoption will replace its custom Scenario client with the official SDK.
These tests document and check the assumptions needed for that replacement:
project selection and dry-run flags reach the correct query parameters,
model-specific inputs and exact quote bytes survive unchanged, response fields
remain accessible, and disabling retries prevents a second submission attempt.
Upload lifecycle and job discovery tests check scope, wrappers and cursors;
cancellation fixtures preserve acknowledgements and completion races.
They also record the known bug where ambient Basic credentials override an
explicitly selected Bearer token; that assertion is an expected failure.

The real pinned SDK runs against a fake HTTP service (httpx.MockTransport).
Tests inspect its outgoing requests and how it parses synthetic responses.
Network connections are forbidden, so even submission tests spend no credits.

These are dependency checks: an SDK upgrade that changes these behaviors needs
review. They do not yet exercise a Blender integration adapter, prove that the
live API accepts the requests, or establish native Blender compatibility.
"""

import base64
import copy
import json
import socket
from decimal import Decimal

import httpx
import pytest
from scenario_sdk import APIConnectionError, APIStatusError, APITimeoutError, Scenario

BASE_URL = "https://api.example.invalid/v1"
PROJECT = "fixture-project"
SDK_ENV = (
    "SCENARIO_SDK_API_KEY",
    "SCENARIO_SDK_API_SECRET",
    "SCENARIO_SDK_JWT",
    "SCENARIO_BASE_URL",
    "SCENARIO_CUSTOM_HEADERS",
)


@pytest.fixture(autouse=True)
def offline_environment(monkeypatch):
    # Test isolation only. Production must not mutate process-wide credentials.
    for name in SDK_ENV:
        monkeypatch.delenv(name, raising=False)

    def deny_network(*args, **kwargs):
        pytest.fail("SDK contract tests must not open network connections")

    monkeypatch.setattr(socket.socket, "connect", deny_network)
    monkeypatch.setattr(socket.socket, "connect_ex", deny_network)
    monkeypatch.setattr(socket, "create_connection", deny_network)


@pytest.fixture
def client_factory():
    clients = []

    def create(handler, **options):
        settings = {
            "base_url": BASE_URL,
            "api_key": "fixture-key",
            "api_secret": "fixture-secret",
            "max_retries": 0,
            "timeout": 5.0,
            "http_client": httpx.Client(
                transport=httpx.MockTransport(handler),
                follow_redirects=False,
                trust_env=False,
            ),
        }
        settings.update(options)
        sdk = Scenario(**settings)
        clients.append(sdk)
        return sdk

    yield create
    for sdk in clients:
        sdk.close()


@pytest.mark.parametrize("operation", ["model", "workflow"])
@pytest.mark.parametrize("dry_run", [True, False])
def test_generation_keeps_scope_and_dry_run_out_of_payload(client_factory, operation, dry_run):
    requests = []
    payload = {
        "prompt": "fixture prompt",
        "numImages": 2,
        "references": [{"assetId": "fixture-asset", "strength": 0.5}],
        "model_specific": {"preserveThisKey": True},
    }
    original = copy.deepcopy(payload)

    def respond(request):
        requests.append(request)
        return httpx.Response(200, json={"job": {"jobId": "fixture-job"}})

    sdk = client_factory(respond)
    if operation == "model":
        result = sdk.generate.run_model(
            "fixture-model", body=payload, dry_run=dry_run, project_id=PROJECT
        )
        method, path = "POST", "/v1/generate/custom/fixture-model"
    else:
        result = sdk.workflows.run(
            "fixture-workflow", body=payload, dry_run=dry_run, project_id=PROJECT
        )
        method, path = "PUT", "/v1/workflows/fixture-workflow/run"
    assert len(requests) == 1
    request = requests[0]
    assert (request.method, request.url.path) == (method, path)
    assert dict(request.url.params) == {"dryRun": str(dry_run).lower(), "projectId": PROJECT}
    assert json.loads(request.content) == original
    assert payload == original
    assert result.job.job_id == "fixture-job"
    assert result.to_dict()["job"]["jobId"] == "fixture-job"


def test_estimate_wrapper_preserves_exact_decimal_quote(client_factory):
    # Use the SDK's public response wrapper, not a low-level HTTP method.
    # JSON bytes retain precision that the generated float model cannot retain.
    quote = b'{"creativeUnitsCost":0.10000000000000001,"costDetails":{"generation":0.10000000000000001}}'
    sdk = client_factory(lambda request: httpx.Response(200, content=quote))
    response = sdk.generate.with_raw_response.run_model(
        "fixture-model", body={"prompt": "fixture"}, dry_run=True, project_id=PROJECT
    )
    estimate = json.loads(response.read(), parse_float=Decimal)
    assert estimate["creativeUnitsCost"] == Decimal("0.10000000000000001")
    assert estimate["costDetails"]["generation"] == estimate["creativeUnitsCost"]


@pytest.mark.parametrize(
    "resource,identifier,wrapper",
    [
        ("models", "fixture-model", "model"),
        ("assets", "fixture-asset", "asset"),
        ("jobs", "fixture-job", "job"),
    ],
)
def test_retrieve_keeps_scope_and_response_extensions(
    client_factory, resource, identifier, wrapper
):
    requests = []
    fixture = {wrapper: {"id": identifier, "futureField": {"retain": True}}}

    def respond(request):
        requests.append(request)
        return httpx.Response(200, json=fixture)

    sdk = client_factory(respond)
    result = getattr(sdk, resource).retrieve(identifier, project_id=PROJECT)
    assert len(requests) == 1
    request = requests[0]
    assert (request.method, request.url.path) == ("GET", f"/v1/{resource}/{identifier}")
    assert dict(request.url.params) == {"projectId": PROJECT}
    assert result.to_dict()[wrapper]["futureField"] == {"retain": True}


def test_cancel_uses_remote_action_and_keeps_acknowledged_status(client_factory):
    requests = []

    def respond(request):
        requests.append(request)
        # An action acknowledgement need not yet report a terminal status.
        return httpx.Response(200, json={"job": {"jobId": "fixture-job", "status": "in-progress"}})

    sdk = client_factory(respond)
    result = sdk.jobs.trigger_action("fixture-job", action="cancel", project_id=PROJECT)
    assert len(requests) == 1
    request = requests[0]
    assert (request.method, request.url.path) == ("POST", "/v1/jobs/fixture-job/action")
    assert dict(request.url.params) == {"projectId": PROJECT}
    assert json.loads(request.content) == {"action": "cancel"}
    assert result.job.status == "in-progress"


@pytest.mark.parametrize("status", [408, 409, 429, 500, 503])
@pytest.mark.parametrize("operation", ["model", "workflow"])
def test_submission_http_errors_never_retry(client_factory, status, operation):
    requests = []

    def respond(request):
        requests.append(request)
        return httpx.Response(
            status, json={"error": "fixture failure"}, headers={"Retry-After": "0"}
        )

    sdk = client_factory(respond)
    with pytest.raises(APIStatusError) as error:
        if operation == "model":
            sdk.generate.run_model("fixture-model", body={}, dry_run=False, project_id=PROJECT)
        else:
            sdk.workflows.run("fixture-workflow", body={}, dry_run=False, project_id=PROJECT)
    assert error.value.status_code == status
    assert len(requests) == 1


@pytest.mark.parametrize(
    "failure,expected",
    [
        (httpx.ReadTimeout, APITimeoutError),
        (httpx.ConnectError, APIConnectionError),
    ],
)
@pytest.mark.parametrize("operation", ["model", "workflow"])
def test_submission_transport_failure_never_retries(client_factory, failure, expected, operation):
    requests = []

    def fail(request):
        requests.append(request)
        raise failure("fixture lost response", request=request)

    sdk = client_factory(fail)
    with pytest.raises(expected):
        if operation == "model":
            sdk.generate.run_model("fixture-model", body={}, dry_run=False, project_id=PROJECT)
        else:
            sdk.workflows.run("fixture-workflow", body={}, dry_run=False, project_id=PROJECT)
    assert len(requests) == 1


def test_redirect_is_not_followed_by_explicit_transport(client_factory):
    requests = []

    def redirect(request):
        requests.append(request)
        return httpx.Response(307, headers={"Location": "https://storage.example.invalid/redirect"})

    sdk = client_factory(redirect)
    with pytest.raises(APIStatusError):
        sdk.generate.run_model("fixture-model", body={}, dry_run=False, project_id=PROJECT)
    assert len(requests) == 1
    assert requests[0].url.host == "api.example.invalid"


def test_explicit_basic_credentials_override_ambient_basic(client_factory, monkeypatch):
    monkeypatch.setenv("SCENARIO_SDK_API_KEY", "ambient-key")
    monkeypatch.setenv("SCENARIO_SDK_API_SECRET", "ambient-secret")
    requests = []

    def respond(request):
        requests.append(request)
        return httpx.Response(200, json={"job": {"jobId": "fixture-job"}})

    sdk = client_factory(respond)
    sdk.jobs.retrieve("fixture-job", project_id=PROJECT)
    expected = base64.b64encode(b"fixture-key:fixture-secret").decode("ascii")
    assert requests[0].headers["Authorization"] == f"Basic {expected}"


@pytest.mark.xfail(
    strict=True,
    raises=AssertionError,
    reason="SDK 2.1.0 auth precedence: https://github.com/scenario-labs/scenario-sdk-python/issues/26",
)
def test_explicit_bearer_must_override_ambient_basic(client_factory, monkeypatch):
    monkeypatch.setenv("SCENARIO_SDK_API_KEY", "ambient-key")
    monkeypatch.setenv("SCENARIO_SDK_API_SECRET", "ambient-secret")
    requests = []

    def respond(request):
        requests.append(request)
        return httpx.Response(200, json={"job": {"jobId": "fixture-job"}})

    sdk = client_factory(respond, api_key=None, api_secret=None, bearer_auth="selected-oauth")
    sdk.jobs.retrieve("fixture-job", project_id=PROJECT)
    assert requests[0].headers["Authorization"] == "Bearer selected-oauth"


@pytest.fixture
def upload_record():
    return {
        "id": "fixture-upload",
        "authorId": "fixture-author",
        "ownerId": PROJECT,
        "createdAt": "2026-01-01T00:00:00Z",
        "updatedAt": "2026-01-01T00:00:00Z",
        "fileName": "reference.png",
        "kind": "image",
        "source": "multipart",
        "status": "pending",
        "parts": [
            {
                "number": number,
                "url": f"https://storage.example.invalid/part-{number}?signature=synthetic",
                "expires": "2026-01-01T01:00:00Z",
            }
            for number in (1, 2)
        ],
        "futureField": {"retain": True},
    }


def test_upload_create_preserves_parts_and_asset_options(client_factory, upload_record):
    requests = []
    options = {
        "collection_ids": ["fixture-collection"],
        "parent_id": "fixture-parent",
        "hide": False,
    }
    original = copy.deepcopy(options)

    def respond(request):
        requests.append(request)
        return httpx.Response(200, json={"upload": upload_record})

    sdk = client_factory(respond)
    result = sdk.uploads.create(
        project_id=PROJECT,
        kind="image",
        file_name="reference.png",
        content_type="image/png",
        file_size=4096,
        parts=2,
        asset_options=options,
    )
    # Creation returns transfer instructions; it must not PUT bytes to storage.
    assert len(requests) == 1
    request = requests[0]
    assert (request.method, request.url.path) == ("POST", "/v1/uploads")
    assert dict(request.url.params) == {"projectId": PROJECT}
    assert json.loads(request.content) == {
        "kind": "image",
        "fileName": "reference.png",
        "contentType": "image/png",
        "fileSize": 4096,
        "parts": 2,
        "assetOptions": {
            "collectionIds": ["fixture-collection"],
            "parentId": "fixture-parent",
            "hide": False,
        },
    }
    assert options == original
    assert result.upload.id == "fixture-upload"
    assert [part.number for part in result.upload.parts] == [1, 2]
    assert result.to_dict()["upload"] == upload_record


@pytest.mark.parametrize("operation", ["retrieve", "complete"])
@pytest.mark.parametrize("status", ["validating", "imported", "failed"])
def test_upload_poll_and_completion_keep_processing_state(
    client_factory, upload_record, operation, status
):
    requests = []
    upload_record.update(status=status, jobId="fixture-upload-job", entityId="fixture-asset")
    if status == "failed":
        upload_record["errorMessage"] = "fixture validation failure"

    def respond(request):
        requests.append(request)
        return httpx.Response(200, json={"upload": upload_record})

    sdk = client_factory(respond)
    if operation == "retrieve":
        result = sdk.uploads.retrieve("fixture-upload", project_id=PROJECT)
        method, path, body = "GET", "/v1/uploads/fixture-upload", b""
    else:
        # The generated Literal is "complete" although its docstring says
        # "upload-complete". This tests serialization, not live acceptance.
        result = sdk.uploads.trigger_action("fixture-upload", action="complete", project_id=PROJECT)
        method, path, body = "POST", "/v1/uploads/fixture-upload/action", b'{"action":"complete"}'
    assert len(requests) == 1
    request = requests[0]
    assert (request.method, request.url.path) == (method, path)
    assert dict(request.url.params) == {"projectId": PROJECT}
    assert request.content == body
    assert result.upload.status == status
    assert result.upload.job_id == "fixture-upload-job"
    assert result.upload.entity_id == "fixture-asset"
    assert result.to_dict()["upload"] == upload_record


@pytest.mark.parametrize("job_type", ["custom", "workflow"])
def test_job_pages_preserve_filters_and_reconciliation_fields(client_factory, job_type):
    requests = []
    metadata = {
        "input": {"prompt": "fixture"},
        "assetIds": ["fixture-asset"],
        "output": {"text": "fixture result"},
        "workflowId": "fixture-workflow",
        "workflowJobId": "fixture-parent-job",
        "futureField": {"retain": True},
    }

    def respond(request):
        requests.append(request)
        # Bound this fake service so a broken cursor cannot hang the test.
        assert len(requests) <= 2
        page_number = len(requests)
        return httpx.Response(
            200,
            json={
                "jobs": [
                    {
                        "jobId": f"fixture-job-{page_number}",
                        "jobType": job_type,
                        "status": "success",
                        "metadata": metadata,
                    }
                ],
                "nextPaginationToken": "cursor+/= fixture" if page_number == 1 else None,
            },
        )

    sdk = client_factory(respond)
    first = sdk.jobs.list(
        project_id=PROJECT,
        author_id="fixture-author",
        workflow_id="fixture-workflow",
        type=job_type,
        status="success",
        hide_results=False,
        page_size=1,
    )
    assert len(requests) == 1
    assert first.jobs[0].job_id == "fixture-job-1"
    assert first.next_pagination_token == "cursor+/= fixture"
    second = first.get_next_page()
    assert len(requests) == 2
    assert not second.has_next_page()
    for index, (request, page) in enumerate(zip(requests, (first, second), strict=True)):
        expected_query = {
            "projectId": PROJECT,
            "authorId": "fixture-author",
            "workflowId": "fixture-workflow",
            "type": job_type,
            "status": "success",
            "hideResults": "false",
            "pageSize": "1",
        }
        if index:
            expected_query["paginationToken"] = "cursor+/= fixture"
        assert (request.method, request.url.path) == ("GET", "/v1/jobs")
        assert dict(request.url.params) == expected_query
        assert request.content == b""
        job = page.jobs[0]
        assert job.job_id == f"fixture-job-{index + 1}"
        assert job.job_type == job_type
        assert job.to_dict()["metadata"] == metadata


def test_job_list_serializes_multiple_types_as_csv(client_factory):
    requests = []

    def respond(request):
        requests.append(request)
        return httpx.Response(200, json={"jobs": []})

    sdk = client_factory(respond)
    page = sdk.jobs.list(project_id=PROJECT, types=["custom", "workflow", "upload"])
    assert len(requests) == 1
    assert dict(requests[0].url.params) == {"projectId": PROJECT, "types": "custom,workflow,upload"}
    assert page.jobs == []
    assert not page.has_next_page()


@pytest.mark.parametrize("status", ["in-progress", "canceled", "success"])
def test_cancel_acknowledgement_can_race_with_completion(client_factory, status):
    requests = []
    fixture = {
        "job": {
            "jobId": "fixture-job",
            "status": status,
            "metadata": {"assetIds": ["fixture-asset"]},
            "futureField": True,
        }
    }

    def respond(request):
        requests.append(request)
        return httpx.Response(200, json=fixture)

    sdk = client_factory(respond)
    result = sdk.jobs.trigger_action("fixture-job", action="cancel", project_id=PROJECT)
    assert len(requests) == 1
    assert result.to_dict() == fixture
    assert result.job.status == status


def test_workflow_rejection_targets_an_approval_node(client_factory):
    requests = []

    def respond(request):
        requests.append(request)
        return httpx.Response(
            200, json={"job": {"jobId": "fixture-workflow-job", "status": "in-progress"}}
        )

    sdk = client_factory(respond)
    # This is a node decision, not a general cancel-workflow operation.
    result = sdk.workflows.user_approval(
        "fixture-workflow",
        project_id=PROJECT,
        node_id="fixture-node",
        workflow_job_id="fixture-workflow-job",
        action="reject",
    )
    assert len(requests) == 1
    request = requests[0]
    assert (request.method, request.url.path) == (
        "PUT",
        "/v1/workflows/fixture-workflow/user-approval",
    )
    assert dict(request.url.params) == {"projectId": PROJECT}
    assert json.loads(request.content) == {
        "nodeId": "fixture-node",
        "workflowJobId": "fixture-workflow-job",
        "action": "reject",
    }
    assert result.job.job_id == "fixture-workflow-job"
    assert result.job.status == "in-progress"


@pytest.mark.parametrize("operation", ["upload-create", "upload-complete", "cancel"])
@pytest.mark.parametrize("failure", ["timeout", 409, 429, 503])
def test_upload_and_cancel_failures_do_not_replay_mutations(client_factory, operation, failure):
    requests = []

    def fail(request):
        requests.append(request)
        if failure == "timeout":
            raise httpx.ReadTimeout("fixture lost response", request=request)
        return httpx.Response(
            failure, json={"error": "fixture failure"}, headers={"Retry-After": "0"}
        )

    sdk = client_factory(fail)
    expected = APITimeoutError if failure == "timeout" else APIStatusError
    with pytest.raises(expected):
        if operation == "upload-create":
            sdk.uploads.create(
                project_id=PROJECT,
                kind="image",
                file_name="reference.png",
                content_type="image/png",
                file_size=4096,
                parts=1,
            )
        elif operation == "upload-complete":
            sdk.uploads.trigger_action("fixture-upload", action="complete", project_id=PROJECT)
        else:
            sdk.jobs.trigger_action("fixture-job", action="cancel", project_id=PROJECT)
    assert len(requests) == 1
