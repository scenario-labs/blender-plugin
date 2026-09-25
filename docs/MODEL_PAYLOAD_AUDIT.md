# Model payload audit

[The audit tool](../tools/audit_payloads.py) checks the extension's schema parser
against selected model records. It can read an explicit offline fixture directory
or fetch missing records through the shared Scenario SDK adapter. It never
estimates, submits a generation or downloads media. A passing report covers these
schema heuristics; it does not prove live generation, UI reachability or complete
JSON Schema validation.

## What it checks

The default inventory combines the curated creation lanes, Edit 3D task models
and Patina models. It is not the whole service catalog or every trained model.
The checks flag:

- Required files whose descriptions make them conditional, unless the parser
  already represents the relationship as a one-of group.
- Multiple required file inputs, for review rather than automatic rejection.
- Prompts described as alternatives to a still-required file.
- Edit 3D models without a detectable mesh input.
- Prompts that the Edit 3D schema fails to select for drawing.
- Required flags lost during parsing, and empty schemas.

The implementation retains the existing heuristics. It does not automatically
repair schemas or loosen requirements. A finding needs investigation; for example,
a model may correctly require both a mesh and a reference image.

## Run offline

Use reviewed fixture files without credentials or network access:

```sh
uv run --locked --no-env-file python tools/audit_payloads.py \
  --offline --cache tests/fixtures/models \
  --models model_rodin-hyper3d-bang model_meshy-7-retexture \
  --fail-on HIGH --report audit.md
```

`--offline` requires an explicit `--cache` directory. It accepts both raw model
objects and recorded `{"model": {...}}` wrappers, verifies the requested model
identity and leaves the files unchanged. A missing, malformed, mismatched or
symlinked cache entry is reported as a failure; it never falls back to a service
call. The tool does not read credential files. `uv --no-env-file` also prevents
uv from loading them.

## Run with selected test credentials

After selecting the test account and optional project through the
[developer configuration](../CONTRIBUTING.md#environment-variables), run:

```sh
uv run --locked --env-file .env.local python tools/audit_payloads.py \
  --fail-on HIGH --report audit.md
```

Live mode requires the explicit `SCENARIO_TEST_API_KEY` and
`SCENARIO_TEST_API_SECRET` pair, even when all selected schemas are already
cached, so the cache remains bound to that account selection. The optional
`SCENARIO_TEST_PROJECT_ID` is sent as `projectId`. Runtime credentials and ambient
SDK credentials do not override that selection.

By default, each live run gets a new private temporary cache, removed when the
run exits; there is no cross-run reuse. `SCHEMA_CACHE` or `--cache DIR` selects
a persistent cache, with the flag taking precedence. Its parent must already
exist. Live records reside in separate hashed subdirectories for the selected
credentials, project and API base URL. The hash partitions local cache files;
it is not authoritative account identity. The SDK client is created only for
the first cache miss and is closed after the run. Complete new cache files
replace entries atomically. Remove an entry from a persistent scoped directory
to request a fresh read. Cache hits have no expiry and do not establish current
service behavior. Keep raw caches private and inspect reports before sharing them.

Live cache roots and scoped directories must be real directories, not symlinks
or Windows reparse points. On POSIX they must belong to the current user and
have no group/other permission bits. Resolved parents must belong to that user
or root and have no group/other write bits, except trusted-owner sticky directories
such as `/tmp`. Parent aliases such as macOS `/var` are resolved before use.
Existing permissions are never changed. Missing persistent cache/scoped directories
are created privately only after a successful model read. Extended ACLs and Windows
ownership are not inspected by these standard-library checks: choose a parent and cache
accessible only to the intended user and trusted administrators. The checks
do not defend against other software running as that user or authenticate
cached schema contents.

An explicitly supplied offline directory has no implicit account selection.
To examine a saved live cache offline, pass its exact hashed subdirectory with
`--offline --cache`, rather than its root. Offline fixture directories remain
read-only inputs and do not need live-cache ownership or private permissions.

## Reports and exits

`--models ID [ID ...]` selects a subset; omitted IDs use the curated inventory.
Duplicate IDs are checked once. `--report PATH` writes Markdown to an existing
parent directory; otherwise the report is printed. Reports include the UTC run
date, cache mode, chosen threshold, checked-schema count, failures and findings.
They omit SDK exception bodies and URL content in finding descriptions. No
report or cache is committed by the tool.

| Exit | Meaning |
| --- | --- |
| `0` | No failures/findings at the selected threshold, or report-only mode when `--fail-on` is omitted |
| `1` | With `--fail-on HIGH`, `MED` or `LOW`: at least one finding at that severity or higher, or any fetch/schema/cache failure |
| `2` | Invalid command usage, missing live credentials, unsafe/inaccessible live-cache configuration, invalid SDK setup, an unwritable report or temporary-cache cleanup failure |

Temporary-cache cleanup failures produce a fixed diagnostic without exposing
filesystem details. A completed audit report is still written, preserving its
findings and fetch failures, while the process returns `2` for the cleanup failure.

An empty schema is a HIGH finding. Invalid response identities and schemas that
cannot be parsed are failures. The report-only default preserves the previous
non-gating behavior; automated callers must select `--fail-on`.

## SDK operation and remaining automation

The exact pinned SDK release and bundle are documented in
[SDK_ADOPTION.md](SDK_ADOPTION.md) and [SDK_BUNDLE.md](SDK_BUNDLE.md). The audit uses
`SDKAdapter.model`, which calls SDK 2.1.0's public
`models.with_raw_response.retrieve(model_id, project_id=...)` method for
`GET /models/{id}`. It retains the complete model object for the existing parser.
No raw API fallback, low-level SDK verb or dependency change is introduced.
The shared adapter disables automatic retries and isolates ambient credentials.

The [public API documentation](https://docs.scenario.com/) and
[official Python SDK release](https://pypi.org/project/scenario-sdk/2.1.0/)
describe service contracts. This audit does not invoke any paid endpoint or
`dryRun` operation. Offline MockTransport checks verify the selected SDK mapping;
actual service acceptance must be recorded separately.

The weekly workflow, report artifact retention, scoped CI credentials and
failure-issue deduplication remain tracked in
[#41](https://github.com/scenario-labs/blender-plugin/issues/41). This CLI change
does not schedule or enable a live audit. The old live investigation and fixes
remain in [the changelog](../CHANGELOG.md) under versions 0.9.3 and 0.9.4; their
historical observations are not fresh service results.
