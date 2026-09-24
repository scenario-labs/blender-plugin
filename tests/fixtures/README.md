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
written. The normal recorder also sanitizes each fixture write, but still uses
the prototype transport and its existing partial model list. Migration to the
shared SDK adapter, complete recording coverage and truthful recording metadata
are separate remaining work under #9. The cleanup command does not refresh API records or download media.

Live recording requires explicitly selected test credentials and authorization;
see [contributor configuration](../../CONTRIBUTING.md#environment-variables).
The default test suite needs neither credentials nor a Scenario account.
