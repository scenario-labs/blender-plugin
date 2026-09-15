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
| Remote cancellation | `jobs.trigger_action(action="cancel")`: POST action and project query; an acknowledgement is not necessarily a terminal canceled status |
| Uncertain submissions | `max_retries=0` makes one attempt for model/workflow transport errors and retryable HTTP statuses, even with `Retry-After` |
| Redirect handling | An explicit HTTP client with `follow_redirects=False` prevents a second request; also use `trust_env=False` to avoid ambient proxy configuration |
| Authentication | Explicit Basic credentials take precedence over ambient Basic credentials; explicit Bearer precedence has the known failure below |

Synthetic responses intentionally cover partial and extended records. Passing
these tests proves serialization and parsing of those fixtures, not live endpoint
acceptance, complete schemas, remote cancellation or successful generation.

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

The adapter is deliberately a read/estimate foundation. It has no paid dispatch
or cancellation entry point; #65 must establish durable request identity and
reconciliation before enabling those actions. All calls use public SDK methods
with `max_retries=0`; their `with_raw_response` wrappers preserve wire JSON.

| Adapter operation | SDK 2.1.0 method and contract |
| --- | --- |
| Public/private model catalog | `models.list`: explicit page size/status/privacy, `paginationToken`, scope on every page, deduplication and cursor-loop/page-limit failures |
| Public/private workflow catalog | `workflows.list`: SDK REST catalog replaces the need for Studio's public-workflow HTTP bypass; pagination and scope are tested synthetically |
| Model/workflow/asset/job records | `models.retrieve`, `workflows.retrieve`, `assets.retrieve`, `jobs.retrieve`: unwrap the named record and retain unknown fields |
| Custom-model estimate | `generate.run_model(dry_run=True)`: adopted form value validation plus retained conditional/one-of rules; inputs in JSON and dry-run/project in query |
| Workflow estimate | `workflows.run(dry_run=True)`: normalize workflow fields/defaults and preserve the same query/body boundary |
| Exact estimate record | Keep immutable request/response bytes and a `Decimal` cost, including zero; reject absent, negative, nonnumeric or non-finite costs rather than inventing a free estimate |

Each client owns an immutable selected project and connection scope. Estimates
from a different client fail `owns_estimate`, including a recreated client for
the same account. This is a building block for shared-runtime invalidation, not
a persisted quote or spending-authorization mechanism. Online permission is
checked before every request, including every catalog page. Blender callers must
supply a predicate reflecting their actual online-access permission.

Custom-model records must explicitly declare `type=custom`; trained-model
routing remains unavailable until its REST schema contract is established.
Studio's pure routing helper/tests are retained, but remote-MCP `run_with`
metadata is not silently assumed to exist in REST. Uploads, signed transfers,
discovery, search/organization, submission and cancellation remain to be mapped.

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
