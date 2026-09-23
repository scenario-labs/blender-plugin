# SDK contracts for Studio adoption

The shared adapter for compact creation, expanded Studio and local MCP must use
`scenario-sdk`. The adoption baseline is **2.1.0**, inspected from the published
[PyPI release](https://pypi.org/project/scenario-sdk/2.1.0/). Its wheel is
`scenario_sdk-2.1.0-py3-none-any.whl`, with SHA256
`a770cc2b40203d8ac5fa3b613e54e054e1e19c6594a029d2bc61218a831091d2`.
The development dependency group pins this version and the MockTransport test
client, `httpx==0.28.1`; [uv.lock](../uv.lock) pins their transitive dependencies.

This is a prerequisite for [Studio adoption](https://github.com/scenario-labs/blender-plugin/issues/64).
The SDK is pinned for development and packaged as a runtime dependency. The
[shared read/estimate adapter](../scenario/core/api/sdk_adapter.py) now uses it;
the existing UI and local MCP still use the prototype client pending shared-job
integration. See [SDK_BUNDLE.md](SDK_BUNDLE.md) for exact artifact/notice pinning,
supported wheel targets, staging and installed-runtime verification.

## Executable contracts

Run the tests with:

```sh
uv sync --locked
uv run --locked python -m pytest tests/unit/test_scenario_sdk_contract.py -rx
```

[The tests](../tests/unit/test_scenario_sdk_contract.py) call public SDK methods
through `httpx.MockTransport`, with socket connections forbidden. All IDs,
credentials, payloads and responses are synthetic. Both `dry_run=True` and
`dry_run=False` are tested without contacting Scenario or spending credits.
[SDK contracts CI](../.github/workflows/sdk-contracts.yml) repeats these checks
using the locked environment.

| Adapter requirement | SDK 2.1.0 contract exercised |
| --- | --- |
| Generic model estimate and submission | `generate.run_model`: POST, unchanged model-specific body, `dryRun` and `projectId` in the query |
| Workflow estimate and submission | `workflows.run`: PUT, unchanged workflow-specific body, `dryRun` and `projectId` in the query |
| Exact quote preservation | `generate.with_raw_response.run_model` retains JSON bytes for decimal parsing; this is a public SDK wrapper, not a custom endpoint call |
| Model, asset and job retrieval | `models.retrieve`, `assets.retrieve`, `jobs.retrieve`: project query and response wrappers, including unrecognized fields |
| Multipart upload lifecycle | `uploads.create/retrieve/trigger_action`: project query, asset-option aliases, part URLs and processing/result fields; creation does not transfer bytes |
| Job discovery | `jobs.list`: `jobs` page wrapper, filters, comma-separated `types`, opaque cursor and project/filter preservation on the next page |
| Workflow approval rejection | `workflows.user_approval(action="reject")`: workflow, job and node identity; this is not general workflow cancellation |
| Remote cancellation | `jobs.trigger_action(action="cancel")`: POST action and project query; acknowledgements can remain in progress or report a completion race; upload/cancel failures make one attempt |
| Uncertain submissions | `max_retries=0` makes one attempt for model/workflow transport errors and retryable HTTP statuses, even with `Retry-After` |
| Redirect handling | An explicit HTTP client with `follow_redirects=False` prevents a second request; also use `trust_env=False` to avoid ambient proxy configuration |
| Authentication | Explicit Basic credentials take precedence over ambient Basic credentials; explicit Bearer precedence has the known failure below |

Synthetic responses intentionally cover partial and extended records. Passing
these tests proves serialization and parsing of those fixtures, not live endpoint
acceptance, complete schemas, remote cancellation or successful generation.

## Upload and job operation boundaries

The operation audit uses the published wheel's `resources/uploads.py`,
`resources/jobs.py`, `resources/workflows.py`, their generated parameter/response
models and `pagination.py`. The adapter now exposes bounded job discovery as
described below; inference cancellation is exposed through the coordinator,
and multipart upload metadata commands are mapped in
[SDK_UPLOADS.md](SDK_UPLOADS.md).

| Operation | Request and response shape |
| --- | --- |
| Begin multipart upload | `uploads.create`: POST `/uploads`; `projectId` query; `kind`, `fileName`, `contentType`, `fileSize`, `parts` and optional `assetOptions` body; response wrapped in `upload` |
| Poll upload | `uploads.retrieve`: GET `/uploads/{id}` with `projectId`; `upload.status`, `jobId`, `entityId`, `errorMessage` and extension fields remain accessible |
| Finalize upload | `uploads.trigger_action(action="complete")`: POST `/uploads/{id}/action`, action body and `projectId` query; response remains an `upload`, potentially still `validating` |
| Discover jobs | `jobs.list`: GET `/jobs`; supports `authorId`, `workflowId`, `status`, `type` or comma-separated `types`, `hideResults`, `pageSize`, `paginationToken` and `projectId`; `jobs` array plus `nextPaginationToken` |
| Retrieve known job | `jobs.retrieve`: GET `/jobs/{id}`, `projectId` query, `job` wrapper |
| Request inference cancellation | `jobs.trigger_action(action="cancel")`: POST `/jobs/{id}/action`, `projectId` query, `job` wrapper |
| Reject workflow approval | `workflows.user_approval(action="reject")`: PUT `/workflows/{id}/user-approval`, `projectId` query, `nodeId`/`workflowJobId`/`action` body, `job` wrapper |

### Uploads and signed storage

The SDK returns numbered upload parts with URLs and expiry values; creating an
upload makes only the Scenario API request. The inspected resource has no byte
transfer or upload-abort method. The generated completion parameter is
`Literal["complete"]`, while its docstring says `"upload-complete"`. Tests record
the literal's serialization; service acceptance of that action remains to verify.
Do not silently substitute the docstring value or invent an abort endpoint.

Before enabling file transfer, define a separate storage transport that checks
online permission and destination policy, sends no Scenario Authorization header,
does not follow redirects implicitly, and keeps signed URL queries out of logs
and persistent records. Expiry, part transfer failure, completion uncertainty and
server-side cleanup still need implementation and verification. An upload
completion acknowledgement alone does not establish that an asset is imported.

The [signed result transport](RESULT_TRANSFERS.md) implements the download
primitive with explicit trusted-host configuration, bounded reads and atomic
non-overwriting output. The coordinator now connects scoped SDK job/asset metadata to persisted download
state and explicit retries with fresh URLs. Production host selection, interrupted
worker reconciliation, UI wiring and upload-part transfers remain separate work.

### Reconciliation and cancellation

Job records retain `jobId`, `jobType`, status and metadata such as inputs,
produced asset IDs, non-asset output and workflow/job relationships. The tests
exercise explicit next-page requests with unchanged project and filters. The
adapter implements bounded discovery through `SDKAdapter.jobs`: explicit page
requests, project and filters on every page, online permission before every request,
loop detection and a hard page limit. Exact duplicate IDs are deduplicated;
conflicting records with the same ID fail the listing so callers can refresh.
Malformed pages and later-page errors never return a silent partial result.
Discovery omits embedded results by default (`hide_results=True`); callers can
explicitly request them with `False`. This option stays unchanged on every page.
Job IDs use the same validation as retrieval, so malformed or padded IDs fail
the listing. Unknown response fields/statuses are preserved. Listings are not server snapshots;
retrieve a known remote ID again before acting on its state.

The inspected SDK has no dedicated lookup by client request identity or explicit
idempotency parameter for model/workflow submission. Generic extension parameters
do not establish server support for either. A listing of similar inputs is only
a set of candidates, not proof of which job belongs to an uncertain submission.
Persist scope and request identity before dispatch; poll a known remote ID, but
keep a lost-ID submission uncertain unless authoritative correlation is available.
Never resolve an empty or ambiguous listing by automatically submitting again.

The job action documentation limits cancellation to inference jobs. The captured
model-generation record in `tests/fixtures/patina-copper-512/job.json` uses
`jobType=custom`; the pinned retrieve-response enum includes both `custom` and
`inference`. The coordinator accepts these two kinds only for persisted model
operations, with a durable `cancel_requested` claim before its single action.
No general
workflow-cancel method appears in the inspected workflow resource. Rejection
requires a user-approval node and has node/loop-specific semantics; it must not
be repurposed as general cancellation. A response may still be `in-progress` or
already `success`; the SDK preserves it without forcing `canceled`. Live support
remains acceptance work under #65; the coordinator tests completion races and
known-ID restart polling offline.
Record a sanitized upstream SDK issue before any fallback for these boundaries;
this audit introduces no raw calls or fallback and claims no live service failure.

## Known authentication failure

[SDK issue #26](https://github.com/scenario-labs/scenario-sdk-python/issues/26)
tracks ambient Basic credentials overriding explicitly selected Bearer auth.
The expected behavior is an executable **strict expected failure**: the suite
reports it separately, and an unexpected pass fails CI so an SDK update requires
reviewing and removing the marker. This is an unresolved adoption blocker, not
accepted account-switching behavior in the unconfigured SDK.

The dependency tests clear SDK environment variables only to isolate fixtures.
The adapter does not edit process-wide environment variables. It configures all
credential arguments and the API URL explicitly, owns an HTTP client with
`trust_env=False` and `follow_redirects=False`, and overrides the SDK's public
`default_headers` property with adapter-owned headers including the selected
Authorization value. This configuration avoids ambient Basic/header overrides;
it is not a raw endpoint fallback. Adapter contracts leave conflicting ambient
values in place and verify both Basic and Bearer requests. Keep the upstream
expected failure until the SDK itself fixes #26, and remove the configuration
workaround only after a verified environment-isolation interface replaces it.
Token serialization does not establish browser OAuth acceptance by REST.

## Adapter coverage

The adapter provides reads/estimates and a coordinator-only submission hook.
The [job coordinator](JOB_COORDINATOR.md) commits a scoped intent before dispatch,
consumes each issued quote once and preserves uncertain outcomes. Inference
cancellation is available through the coordinator; product UI/MCP dispatch
remains unavailable. All calls use public SDK methods
with `max_retries=0`; their `with_raw_response` wrappers preserve wire JSON.

| Adapter operation | SDK 2.1.0 method and contract |
| --- | --- |
| Public/private model catalog | `models.list`: explicit page size/status/privacy, `paginationToken`, scope on every page, deduplication and cursor-loop/page-limit failures |
| Public/private workflow catalog | `workflows.list`: SDK REST catalog replaces the need for Studio's public-workflow HTTP bypass; pagination and scope are tested synthetically |
| Known model-job cancellation | `jobs.trigger_action(action="cancel")` through its public raw-response wrapper: one attempt, selected project, no terminal-state assumption from acknowledgement; coordinator retrieves before and after the action |
| Scoped job discovery | `jobs.list` through the public raw-response wrapper: optional author/workflow/type/status filters, 1–200 items per page, bounded pagination and explicit errors instead of partial or conflicting history |
| Multipart upload metadata | `uploads.create/retrieve/trigger_action(action="complete")`: immutable project scope, strict input/receipt identity, retained processing/future fields; no byte transfer, retry or automatic completion |
| Model/workflow/asset/job records | `models.retrieve`, `workflows.retrieve`, `assets.retrieve`, `jobs.retrieve`: unwrap the named record and retain unknown fields |
| Custom-model estimate | `generate.run_model(dry_run=True)`: adopted form value validation plus retained conditional/one-of rules; inputs in JSON and dry-run/project in query |
| Workflow estimate | `workflows.run(dry_run=True)`: normalize workflow fields/defaults and preserve the same query/body boundary |
| Exact estimate record | Keep immutable request/response bytes and a `Decimal` cost, including zero; reject absent, negative, nonnumeric or non-finite costs rather than inventing a free estimate |

Each client owns an immutable selected project and connection scope. Estimates
from a different client fail `owns_estimate`, including a recreated client for
the same account. Only the original issued object is accepted; copies and consumed quotes fail
ownership checks. The coordinator binds it to persisted request/origin identity;
neither mechanism grants spending authorization. Online permission is
checked before every request, including every catalog page. Blender callers must
supply a predicate reflecting their actual online-access permission.

Custom-model records must explicitly declare `type=custom`; trained-model
routing remains unavailable until its REST schema contract is established.
The adapter uses the same pure payload preparation as form callers: validate
explicit input types first, merge actual defaults and mandatory routing, then
validate the final values and each conditional/either-or clause. Overlapping
clauses remain separate requirements. Malformed schema names and route IDs fail
before SDK dispatch, without coercion. Captured custom-model fixtures exercise
this shared path, including Minimax frame dependencies and Rodin prompt/image
alternatives.

The native panel parser remains tolerant of unknown conditional sibling names so
model descriptions can still render. Strict form preparation and SDK estimation
reject those schemas before dispatch; known sibling relationships remain enforced
in both paths.

The pure LoRA/composition routing helper retains required base-model wiring and
existing scale alignment behavior. Its sanitized remote-MCP projection and
synthetic composition tests do not establish REST routing, universal strength
bounds, catalog discovery, model selection UI or paid execution. Remote-MCP
`run_with` metadata is not silently assumed to exist in REST. Upload/job dependency contracts
are mapped above; multipart metadata commands use the adapter as described in
[SDK_UPLOADS.md](SDK_UPLOADS.md). Signed result downloads have a standalone
[transport primitive](RESULT_TRANSFERS.md); upload byte transfer, durable transfer
recovery, account/project discovery, search/organization and workflow cancellation
remain to implement. Submission uses the coordinator contract above; live
acceptance remains separate.

Run the adapter and command contracts offline with:

```sh
uv run --locked --no-env-file python -m pytest tests/unit/test_sdk_adapter.py tests/unit/test_check_sdk.py
```

The explicit live command is documented in
[CONTRIBUTING.md](../CONTRIBUTING.md#live-commands). Its existence and synthetic
tests do not claim live service acceptance or authorize a paid operation.

## Source baseline and remaining work

The selected Studio candidate is
[`e2b0277064f0c502d46524fba1d006d0ac83f846`](https://github.com/edemaistre/scenario-blender-studio/commit/e2b0277064f0c502d46524fba1d006d0ac83f846),
version 0.1.5. Its runtime and test trees are unchanged from the previously
inspected `bfeac2873f3a3cb9e2bef1fdf97a14431ce4c65f`; later commits add documentation
and validation media. See [the source and capability inventory](STUDIO_ADOPTION.md)
for tree identities, retained/replaced/deferred capabilities, ownership and intake
boundaries. Version 0.1.5 adds generation progress and automatic asset previews to 0.1.4.
Its `src/scenario_studio/client.py` still uses a custom remote-MCP client, including
project discovery and a public-workflow HTTP path. Importing it unchanged would
not satisfy the SDK-first contract.

Before the adopted extension is accepted:

- Map the client operations to the exact SDK's methods and response wrappers.
  Verify catalog pagination/schema normalization, team/project discovery,
  multipart upload/finalization, signed downloads, asset search and collection
  operations. Do not infer coverage from a similar method name.
- Reproduce each uncovered operation and link an upstream SDK issue before a
  narrow raw API fallback in the shared adapter. No fallback is introduced here.
- Bind exact quotes to payload/account/project, persist request identity before
  paid dispatch, and preserve an uncertain state after a lost response. SDK
  retry settings alone do not provide application persistence or prevent a
  second caller from submitting again.
- Verify workflow cancellation separately: the SDK's `jobs.trigger_action`
  documentation currently describes cancellation of inference jobs only.
- Maintain the pinned runtime bundle and its licenses, including the SDK's MIT
  notice and `pydantic-core` binary wheels. Re-run actual installed-bundle checks
  on dependency upgrades; a development lockfile alone is not bundle evidence.
- Complete supported OS/CPU acceptance on Blender 5.0, 5.1 and 5.2, including
  native UI behavior and coexistence with other extensions. The new isolated
  dependency/adapter contracts do not establish those broader properties.
- Preserve Studio source provenance/authorship, GPL text, Poppins OFL and Tabler
  MIT notices when importing useful source, tests and resources. Keep demo
  media, historical ZIPs and account-specific validation exports out of the
  canonical runtime tree.

Shared scoped jobs and local MCP integration remain under
[#65](https://github.com/scenario-labs/blender-plugin/issues/65); authentication
under [#67](https://github.com/scenario-labs/blender-plugin/issues/67); integrated
acceptance under [#68](https://github.com/scenario-labs/blender-plugin/issues/68).
