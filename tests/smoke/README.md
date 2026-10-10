# Live acceptance checks

All model checks use the same SDK adapter, exact quotes, credential-scoped job
store and result transfers as the adopted runtime. The former Image, Material,
Video and image-to-3D entry points now share one quote/submit/resume implementation.
The generic entry point also supports audio. No smoke runs in ordinary tests or
PR CI. The aggregate suite and protected workflow below implement the shared
budget path for [#40](https://github.com/scenario-labs/blender-plugin/issues/40),
including a [monthly plan](#monthly-plan) with a fixed total cap. Live
reference-upload and monthly-run acceptance remain pending.

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
or run extra multi-view estimates. The [explicit reference plan](#prepare-reference-inputs) below also automates
shared upload commands; live upload acceptance remains separate. Material receipts retain the shared runtime's documented texture
roles; this tool does not construct or apply Blender materials.

Omit `--env-file` and use `--no-env-file` when the shell supplies credentials.
Keep the spending flag out of dotenv files. Offline tests use synthetic SDK
responses and never spend. Separate runs have separate approvals and caps; their
sum is not enforced by an account-wide budget ledger.


## One aggregate budget for a suite

`tools.smoke_suite` coordinates one to eight cases through the same model engine.
It does not introduce another SDK adapter or submission implementation. Create a
private plan with an explicit `project_id`: JSON `null` means the test key's
default scope; a string must exactly match `SCENARIO_TEST_PROJECT_ID`.

```json
{
  "schema_version": 1,
  "project_id": null,
  "cases": [
    {
      "name": "image",
      "result_kind": "image",
      "model": "MODEL_ID",
      "parameters": {"prompt": "A blue ceramic cup on a white background"}
    }
  ]
}
```

Add cases for the other result kinds using current supported model IDs and their
actual schemas. The plan is private: inputs may contain uploaded asset IDs. It
must not contain local file paths as substitutes for uploaded references. This
version-1 plan consumes already imported references. Version 2 below can prepare
explicitly authorized local files; Blender capture and live acceptance remain
separate. Case names are unique lowercase labels, not paths; `suite-attempt` is
reserved for internal state. Console output uses case numbers, not those labels.

```sh
make smoke SMOKE_ARGS="quote --plan workdir/smoke-plan.json --run-dir workdir/suite"
```

The command validates every case before contacting Scenario, quotes every case
without submitting, and writes one `suite.json` binding all quote hashes and the
exact total. No rounded float is used for the total. Review the private plan,
selected credentials/project, each quote and aggregate cost before approval:

```sh
SCENARIO_SMOKE=1 make smoke SMOKE_ARGS="submit --run-dir workdir/suite --approved-suite SUITE_SHA256 --approved-total EXACT_TOTAL --max-cu APPROVED_TOTAL_CAP"
```

Every saved quote and the total must match before the first submission. The
suite exclusively reserves its entire budget with a persistent attempt marker;
each case still obtains a fresh exact quote and uses the shared durable claim.
A price/payload change, lost response or failed case stops the suite immediately.
Uncertain costs are not refunded to allow another case. Do not retry `submit` or
start another suite to recover an interrupted one. Resume only cases that were
already attempted:

```sh
make smoke SMOKE_ARGS="resume --run-dir workdir/suite"
```

Unattempted cases remain unsubmitted and require review; resume cannot spend.
Preserve the complete suite directory, individual databases and scope keys.
A directory copied or edited outside the command is not another authorization.
Independent suites still do not share an account-wide or monthly budget ledger.

`budget-run --plan PLAN --run-dir NEW_DIRECTORY --max-cu CAP` is for separately
budget-authorized automation. It requires `SCENARIO_SMOKE=1` and a positive,
explicit aggregate cap. It quotes all cases and automatically binds those exact
quotes only if their total fits the previously authorized budget. This mode does
not require a human to approve each subsequently fetched price; the separate
approval is for the specified plan/project and total budget. Do not invoke it
when authorization only covers an earlier exact quote or another plan. There is
no default allowance. `--timeout` bounds polling per case, as in the model engine.

## Prepare reference inputs

A version-2 plan adds one to eight `inputs`, each with an exact SHA-256 of the
reviewed file. Cases refer to them with an object containing only
`{"$input": "reference-name"}`, including within arrays. Every input must be used.
For example, replace the illustrative hash, model ID and parameter name below
with the actual reviewed file/model contract:

```json
{
  "schema_version": 2,
  "project_id": null,
  "inputs": [
    {
      "name": "reference",
      "file": "reference.png",
      "sha256": "0000000000000000000000000000000000000000000000000000000000000000",
      "kind": "image",
      "content_type": "image/png"
    }
  ],
  "cases": [
    {
      "name": "edit",
      "result_kind": "image",
      "model": "MODEL_ID",
      "parameters": {"images": [{"$input": "reference"}]}
    }
  ]
}
```

`file` is relative to an explicit input directory, uses forward slashes and
cannot escape that directory or traverse symbolic links. Each regular file must
be nonempty and at most 32 MiB. Supported kinds are `image`, `video`, `audio`,
`3d`, `asset` and `text`; these declarations do not establish provider support
for a format or a particular model parameter. There is no model upload/import.

Review the plan, source bytes, destination test scope and permission to send
those files. Compute the plan file's SHA-256 and supply it only after that upload
authorization. Upload approval does not approve generation:

```sh
SCENARIO_SMOKE=1 uv run --locked --env-file .env.local python -m tools.smoke_inputs upload \
  --plan workdir/reference-plan.json --approved-plan PLAN_SHA256 \
  --input-root workdir/reviewed-inputs --run-dir workdir/suite-inputs
make smoke SMOKE_ARGS="quote --plan workdir/suite-inputs/prepared-plan.json --run-dir workdir/suite"
```

The upload command privately stages and hashes **all** sources before the first
remote initialization. It saves every input/request/scope binding, then uses the
existing coordinator's SDK upload initialization/retrieval/completion and signed
S3 part transport. A changed file, project or approval fails before remote work;
any upload failure or uncertainty stops subsequent inputs. No mutation is
retried. A new run directory is required and must not be created as a workaround
for uncertainty. On complete import, `prepared-plan.json` contains version-1
cases with exact asset IDs; it remains private. Model quotes/schema validation
then run normally. Uploads can complete even when a later model schema or budget
check prevents generation.

Recovery requires the original directory, scope key, stores and credentials:

```sh
uv run --locked --env-file .env.local python -m tools.smoke_inputs resume \
  --run-dir workdir/suite-inputs
```

This command can only poll known uploads or read imported records. It never
initializes, transfers, finalizes or submits generation. Unknown initialization,
incomplete transfer or unattempted inputs require explicit inspection; it cannot
finish them by replaying writes. Fully imported records recreate the same
prepared plan without service requests. Keep source snapshots and private state
until uncertainty and acceptance evidence are resolved. `--timeout` bounds
polling per input, not the transport's own request duration.

For a separately authorized version-2 automation plan, `budget-run` additionally
requires `--upload-inputs --input-root DIRECTORY`. Authorization must cover the
exact listed source bytes and uploads as well as the generation plan, scope and
total cap. Input state lives beside the suite in `SUITE_DIRECTORY-inputs`.
All inputs must import before any case is quoted; every quote must fit the same
aggregate budget before generation begins. Ordinary `quote` never uploads, and
version-1 automation is unchanged.

## Protected hosted execution and recovery

The `smoke` workflow dispatches on `main` or on the first of each month. Forks,
other branches, PR events and Actions reruns cannot execute the paid job. The
unprivileged admission job reads the existing environment and requires reviewers
plus exactly a `main` branch policy; it never creates an unprotected environment.
The paid job waits for the `smoke` environment approval, then reads that policy
again before using any Scenario credential. An API error fails closed.

Configure the [maintainer prerequisites](../../docs/MAINTAINERS.md#smoke-lane)
first. Admission validates one plan and one total cap and freezes both into job
outputs. The approval job name shows them, and execution uses those same values,
so later inputs or environment variables cannot change them after review:

- The monthly schedule always runs the [committed monthly plan](#monthly-plan)
  with the fixed 40 CU total cap, `MONTHLY_MAX_CU` in `tools/smoke_ci.py`. It
  reads no dispatch input or repository variable; changing the plan or the cap
  takes a reviewed commit.
- A manual dispatch chooses `plan`: `monthly` (the default) or `private`, the
  `SMOKE_PLAN_JSON` environment secret. Its `max_cu` defaults to `40`; a zero,
  empty or malformed cap fails before execution. Only a `private` dispatch
  receives the private plan secret.

Approving means authorizing the displayed plan, the configured test scope and the
displayed total cap, including the exact input files/hashes of a version-2 plan.
`budget-run` quotes every case before the first submission; when the exact total
exceeds the cap, it exits 3 and submits nothing. Hosted input paths are relative
to the checked-out repository; use reviewed fixtures and preserve their licenses.
Decline if these inputs or authorization are unclear.
The job never prints the plan, account/project, asset/job IDs or raw exceptions.

### Monthly plan

[`monthly-plan.json`](monthly-plan.json) is a public version-2 plan for the test
key's default scope (`project_id` is `null`). It holds no asset or project ID,
and the schedule needs no private plan secret. It keeps one image case and adds
the cheapest checks that still cover the upload and download paths:

| Case | Model and size | Covers |
| --- | --- | --- |
| `image` | `model_google-gemini-3-1-flash`, 512, one output | Upload of the committed reference image, then image generation and download |
| `material` | `model_patina-material`, 512 x 512, all five maps | Multi-file texture download and every map-role check |
| `audio` | `model_google-gemini-3-8-flash-lite-tts`, one short sentence | Audio download and the audio media-type check |

Video and 3D stay in the private plan: the private plan's current video and 3D
cases each quote above the monthly cap, so its dispatch needs an explicit higher
`max_cu`.

Each run uploads the reference image again before quoting. Uploads spend no CU,
but every run leaves one imported asset in the test scope. If the reference file
is missing or its bytes differ from the recorded digest, input preparation stops
before any upload, quote or submission. A configured `SCENARIO_TEST_PROJECT_ID`
does not match the plan's `null` project, so the run also stops before any
service request; keep the default scope or commit a matching plan.

When a price change pushes the exact total above 40 CU, the monthly run exits 3
and submits nothing. Re-quote the plan with the
[reference input commands](#prepare-reference-inputs), which never submit, then
trim a case or raise `MONTHLY_MAX_CU` in a reviewed change. The cap applies per
run. Manual dispatches are separate authorizations and share no monthly ledger,
and the workflow configures no provider-side project budget. GitHub disables a
public repository's schedules after 60 days without activity; re-enable the
workflow from the Actions tab.

Before any service request, GnuPG must encrypt and decrypt a test file using a
private temporary home. The workflow preserves only `smoke-recovery.gpg`, an
AES-256 OpenPGP archive with integrity protection, retained for seven days.
It includes the private plan, uploaded-input snapshots/state, prepared asset
references, quotes, attempt markers, stores and results; keep
the recovery passphrase outside public logs and artifacts. A setup failure cannot
spend. A normal failed suite still reaches encryption/upload. A hard runner kill,
job timeout or artifact service failure can prevent preservation; inspect cloud
history and uncertainty before authorizing any new run. A rerun is not recovery.

Download the encrypted artifact before it expires. On a trusted machine, decrypt
interactively into a private directory and inspect the archive before extracting:

```sh
umask 077
mkdir smoke-recovery
cd smoke-recovery
gpg --output recovery.tar --decrypt /path/to/smoke-recovery.gpg
tar -tf recovery.tar
tar -xf recovery.tar
```

With the original test credentials/project, run `tools.smoke_suite resume` against
`smoke/suite` from the repository's pinned environment. For version-2 input
recovery, use `tools.smoke_inputs resume --run-dir smoke/suite-inputs`; this does
not start or resume generation. If model quoting never completed, inspect and
obtain a new explicit generation decision rather than rerunning `budget-run`.
Do not publish decrypted
contents or remove attempt markers. Keep the old passphrase for each retained
artifact when rotating the environment secret. No hosted run, live upload,
paid provider output, native application or motion/audio review is implied by
offline runner and encryption tests.
