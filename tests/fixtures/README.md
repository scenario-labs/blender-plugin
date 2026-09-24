# Test fixtures

## Inventory

These fixtures support offline parsing, payload and result tests. Recording dates
below come from the commits that first added each file, not a recent API refresh.

| Path | Contents and source | Recorded |
| --- | --- | --- |
| `models/*.json` | Eighteen model records from `GET /models/{id}` | 2026-08-28 and 2026-08-29 |
| `models_list_page1.json` | Five public models from `GET /models?privacy=public&pageSize=5` | 2026-08-28 |
| `patina-copper-512/model_record.json` | Model record from `GET /models/model_patina-material` | 2026-08-28 |
| `patina-copper-512/dryrun_response.json` | Estimate from `POST /models/model_patina-material/inferences?dryRun=true` | 2026-08-28 |
| `patina-copper-512/job.json` | Patina job response from `GET /jobs/{jobId}` | 2026-08-28 |
| `patina-copper-512/*.png` | Six maps from that job; `manifest.json` maps asset IDs, types, files and sizes | 2026-08-28 |
| `smoke/playblast_72f.mp4` | Blender viewport playblast used by the opt-in video smoke script | 2026-08-28 |

## Provenance and rights

The JSON records and Patina maps are captured Scenario API responses and outputs.
The playblast is a Blender capture. Git history records their addition, but does
not establish which legal entity owned the generating account or media rights.
Maintainer confirmation of those rights and the final media licence/provenance
statement remain tracked in [#9](https://github.com/scenario-labs/blender-plugin/issues/9).
Do not infer an assignment or change an existing licence from this inventory.
No `PROVENANCE.json` has been generated for a new recording run.

## Identifiers and URLs

The recorder replaces string-valued account fields `userId`, `authorId`,
`createdBy`, `ownerId`, `projectId` and `teamId` with stable synthetic placeholders.
It replaces HTTP URLs whose query contains `Key-Pair-Id`, `Policy`, `Signature`,
`X-Amz-Signature` or `X-Amz-Credential` with `https://cdn.example/FIXTURE`, including
case variants and percent-encoded query names. Treat signed URLs as credentials.
This is a targeted sanitizer, not a guarantee that arbitrary response fields or
free text contain no sensitive data. Inspect proposed fixture diffs before commit.

Asset, job, model and collection identifiers, ordinary documentation URLs and
schema values stay intact. Non-string account fields remain inspectable rather
than being coerced, since they may be schema definitions or malformed responses.
Offline [hygiene tests](../unit/test_fixture_hygiene.py) check every committed JSON
file without printing the rejected values.

## Local cleanup and recording

This command uses no credentials and makes no API calls:

```sh
uv run --locked --no-env-file python tools/record_fixtures.py --scrub-existing
```

It preserves compact versus indented JSON and a final newline where present;
unchanged files are not rewritten. Invalid JSON stops cleanup before any file is
written. The cleanup command does not refresh API records or download media.

The normal recorder uses the shared SDK adapter and the pinned SDK's public
`models.with_raw_response.retrieve/list` methods. It reads all eighteen model
records named in `MODEL_IDS` and one public page of five models, using the
explicit test credential pair and optional project from the environment. It
reconstructs each detail's `model` wrapper around the adapter's complete model
record; unrelated top-level detail metadata is not recorded. The list page
retains its wrapper, unknown fields and next-page cursor. No speculative
pagination parameter, generation request or media download is performed.

Every required read must succeed before local files change. A missing or failed
model stops the run rather than silently retaining a stale record. Sanitized
files are staged, then replaced individually; `PROVENANCE.json` is published
last with the UTC recording date, SDK version, recorder path, scrub policy and
written-file/endpoint map. It records no account identity or ownership assertion.
A failed publication may leave some complete new fixtures, but removes the prior
provenance first so it cannot claim the partial set is a successful refresh.
Inspect the diff and retry the explicit read command if needed. Temporary staging
is cleaned when the process exits normally, including handled failures; an abrupt
process kill can leave a `.recording-*` directory to inspect and remove.

No fixture refresh or provenance file is included in this change. Real endpoint
acceptance and maintainer confirmation of media rights remain under #9.

Live recording requires explicitly selected test credentials and authorization;
see [contributor configuration](../../CONTRIBUTING.md#environment-variables).
The default test suite needs neither credentials nor a Scenario account.
