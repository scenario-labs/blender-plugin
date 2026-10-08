# Live acceptance checks

All model checks use the same SDK adapter, exact quotes, credential-scoped job
store and result transfers as the adopted runtime. The former Image, Material,
Video and image-to-3D entry points now share one quote/submit/resume implementation.
The generic entry point also supports audio. No smoke runs in ordinary tests or
PR CI. The protected GitHub environment, aggregate budget and scheduled multi-suite
CI in [#40](https://github.com/scenario-labs/blender-plugin/issues/40) remain pending.

These commands verify service round-trips and saved result receipts. They do not
establish native UI/MCP interaction, scene application, playback quality, Film
or integrated release acceptance. Each run checks one explicitly selected model
and input object, not every provider in a lane.

## Quote and approve one model request

Use the pinned uv environment. Configure the explicit test API-key pair described
in [CONTRIBUTING](../../CONTRIBUTING.md#environment-variables). The optional
`SCENARIO_TEST_PROJECT_ID` selects a project; leaving it blank uses the API key's
default scope. Agree on that concrete test scope and budget before spending.
Do not infer the default project from a discovery list.

Create a private JSON input object appropriate to the selected custom model,
for example a prompt and that model's supported size/output parameters. The tool
retrieves the current model schema and validates those inputs through the shared
adapter. It does not upload local references. Use an already imported asset ID
when an authorized reference is needed.

```sh
mkdir -p workdir
uv run --locked --env-file .env.local python -m tools.smoke_model quote \
  --run-dir workdir/image-check --result-kind image \
  --model MODEL_ID --parameters parameters.json
```

`quote` performs model retrieval and a `dryRun=true` estimate, never generation or
IP detection. It creates a new private run directory, prints the exact decimal CU
cost and the SHA-256 of `quote.json`, and saves the selected credential scope,
model, inputs, expected result kind, normalized payload hash and exact price there. Existing run
directories are rejected. Review the private quote file and intended test scope;
the printed hash binds subsequent approval to those exact bytes.

After explicit approval, replace `QUOTE_SHA256`, `EXACT_COST` and `APPROVED_CAP`
below with the reviewed values. There is no default spending cap. Both decimal
arguments must be nonnegative, finite decimal strings without exponent notation.

```sh
SCENARIO_SMOKE=1 uv run --locked --env-file .env.local python -m tools.smoke_model submit \
  --run-dir workdir/image-check --approved-quote QUOTE_SHA256 \
  --approved-cost EXACT_COST --max-cu APPROVED_CAP
```

The command rejects a changed quote file, cost above the cap, mismatched exact
approval, or changed key/project before making service requests. It claims one
submission attempt with an exclusive persistent marker, fetches a fresh schema
and estimate, and requires unchanged normalized payload and exact price before
preparing and submitting through the coordinator. The marker is retained even
if fresh estimation fails. A price or schema change needs a new reviewed quote;
it cannot silently renew spending approval. A zero cap rejects a positive quote
before service calls; a genuinely zero quote may proceed with explicit approval.

The shared coordinator commits the job intent and submission claim before the
SDK sends once, with retries disabled. A lost receipt retains uncertainty.
The tool polls only a known remote ID, downloads through the bounded trusted-CDN
transport, and verifies saved receipt hashes/sizes. The expected result
kind is checked using saved MIME types and texture roles; this does not decode
media or establish visual/audio quality. It does not upload,
cancel, import into Blender or apply to a scene. Native UI/MCP acceptance remains
a separate check against the exact installed release candidate.

## Resume without repeating generation

Keep the run directory, database and scope key together. After a process exit,
known-job polling failure or failed download, use the original credentials and
optional project:

```sh
uv run --locked --env-file .env.local python -m tools.smoke_model resume \
  --run-dir workdir/image-check
```

`resume` cannot estimate or submit. It polls a known saved job, reconciles an
interrupted download through the shared transfer lock, retries a failed download
with fresh metadata, or verifies already completed files offline. Prepared,
submitting and uncertain jobs require review; they are never reconstructed as
new spending requests. An empty run with an attempt marker also requires review.
Do not delete markers, clone a quote/run directory, remove saved jobs or start
another run to recover uncertainty. Separate new runs are separate authorizations;
the tool is not an account-wide budget ledger or a server-side spend limit.

`submit` and `resume` accept `--timeout SECONDS` (1–3600, default 300) for polling.
This is not a hard wall-clock kill: SDK requests and bounded downloads have their
own timeouts. A polling deadline preserves the job and never cancels or resubmits.

| Exit | Meaning |
| --- | --- |
| 0 | Quote saved without submission, or downloaded receipts and expected result metadata verified |
| 1 | Service, storage, transfer or terminal job failure; inspect saved state |
| 2 | Invalid usage, missing opt-in/credentials, quote identity or scope mismatch |
| 3 | Approval/cap mismatch or changed fresh quote/payload; no generation submitted |
| 4 | Saved state needs review or polling deadline expired; no generation replay |

Stdout contains only costs, an approval hash, known state names and file counts.
`report.json` contains result kind, state, cost, payload hash and result byte counts/hashes; it
omits credentials, raw responses, request inputs, project/job/asset IDs and signed
URLs. Review even that summary before sharing. The rest of the run directory is
private and must never be committed or uploaded as a public artifact. The directory
is retained deliberately for recovery; remove it only after the job's outcome is
resolved and required evidence has been reviewed. The directory and its ancestors
must remain privately owned; this is not protection against a local attacker.

## Result kinds and entry points

Choose `--result-kind` during `quote`; it is saved inside the approval digest.
Submission and recovery read that saved value and offer no override. Every saved
file must have a valid receipt and nonempty bytes. The following additional
metadata checks apply:

| Result kind | Required saved result metadata |
| --- | --- |
| `image` | Every result is an image |
| `material` | Every result is an image; base/albedo and every quoted map role meet the quoted output count |
| `video` | At least one video result; companion files remain verified |
| `model` | At least one binary glTF result (`model/gltf-binary`); companion files remain verified |
| `audio` | At least one audio result; companion files remain verified |

Material quotes use schema version 3 and retain the exact normalized SDK payload
inside the approval digest. Checks use its `maps` selection, including model-schema
defaults, and `numOutputs` (one through four, default one). Supported map names are
`basecolor`, `normal`, `roughness`, `metalness` and `height`, as in the recorded
Patina schemas. Roughness accepts the shared runtime's roughness or inverse
smoothness role. Explicit subsets require only the selected maps; `maps: []`
checks texture-only output. Missing or unsupported map contracts cannot create a
material approval. Role counts do not establish which maps belong to each variant,
image decoding or material quality.

Before accepting recovered material results, the retained payload must match the
saved job's immutable payload digest. A changed quote cannot weaken its map checks.
Older version-2 material quotes lack normalized map expectations: they cannot
submit, and need a new quote in a new run directory if still unsubmitted. For an
existing job, keep its original run and use `resume`; polling/download and receipt
recovery still work, but completion exits 4 for manual inspection instead of
claiming map completeness. Never start another generation to recover that job.
Non-material version-1/2 compatibility is unchanged.

A mismatch fails the check while preserving downloaded results for inspection.
`resume` rechecks them without submitting again. MIME metadata alone does not
prove the file can be decoded; native import and human motion/audio review are
separate #68 requirements.

The existing `tools.smoke_image` module and `tests/smoke/smoke_image.py` select
`image` automatically. The scripts `smoke_material.py`, `smoke_video.py` and
`smoke_image_to_3d.py` select `material`, `video` and `model` respectively and
accept the same three subcommands. They reject a saved run for a different kind.
Bare historical invocations now fail with usage guidance before credentials or
network activity; there is no automatic model choice, quote approval or CU cap.
Old version-1 Image quote records remain usable as Image checks without rewriting
them; their original digest, attempt marker and durable state still apply.

For Video and image-to-3D, prepare/upload references explicitly through the shared
native or MCP upload commands and put the resulting authorized asset IDs in the
input JSON. These smoke commands do not upload a path argument, perform captures,
or run extra multi-view estimates. Reference upload/recovery automation still
needs its own acceptance work; removing the old unscoped uploader does not prove
that journey. Material receipts retain the shared runtime's documented texture
roles; this tool does not construct or apply Blender materials.

Omit `--env-file` and use `--no-env-file` when the shell supplies credentials.
Keep the spending flag out of dotenv files. Offline tests use synthetic SDK
responses and never spend. Separate runs have separate approvals and caps; their
sum is not enforced by an account-wide budget ledger.
