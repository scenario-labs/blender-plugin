# SDK contracts for Studio adoption

The shared adapter for compact creation, expanded Studio and local MCP must use
`scenario-sdk`. The adoption baseline is **2.1.0**, inspected from the published
[PyPI release](https://pypi.org/project/scenario-sdk/2.1.0/). Its wheel is
`scenario_sdk-2.1.0-py3-none-any.whl`, with SHA256
`a770cc2b40203d8ac5fa3b613e54e054e1e19c6594a029d2bc61218a831091d2`.
The development dependency group pins this version and the MockTransport test
client, `httpx==0.28.1`; [uv.lock](../uv.lock) pins their transitive dependencies.

This is a prerequisite for [Studio adoption](https://github.com/scenario-labs/blender-plugin/issues/64).
The SDK is currently a development dependency for contract tests. It has not
replaced either prototype's client or been added to the extension ZIP.

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
accepted account-switching behavior.

The tests clear SDK environment variables only to isolate fixtures. Production
code must not temporarily edit process-wide environment variables in Blender.
The shared adapter must isolate selected credentials, custom headers and base
URL without affecting other workers or extensions. A tested SDK configuration
workaround or an upstream fix is needed before OAuth wiring. Token serialization
alone does not establish that browser OAuth tokens are accepted by REST.

## Source baseline and remaining work

The currently inspected Studio candidate is
[`bfeac2873f3a3cb9e2bef1fdf97a14431ce4c65f`](https://github.com/edemaistre/scenario-blender-studio/commit/bfeac2873f3a3cb9e2bef1fdf97a14431ce4c65f),
version 0.1.5. It adds generation progress and automatic asset previews to 0.1.4.
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
- Package the pinned runtime dependencies and their licenses, including the
  SDK's MIT license notice and binary wheels required by dependencies such as
  `pydantic-core`. A development lockfile is not an extension wheel bundle.
- Validate the actual bundle inside Blender 5.0, 5.1 and 5.2, including isolated
  installation/import, representative operations and native UI behavior.
- Preserve Studio source provenance/authorship, GPL text, Poppins OFL and Tabler
  MIT notices when importing useful source, tests and resources. Keep demo
  media, historical ZIPs and account-specific validation exports out of the
  canonical runtime tree.

Shared scoped jobs and local MCP integration remain under
[#65](https://github.com/scenario-labs/blender-plugin/issues/65); authentication
under [#67](https://github.com/scenario-labs/blender-plugin/issues/67); integrated
acceptance under [#68](https://github.com/scenario-labs/blender-plugin/issues/68).
