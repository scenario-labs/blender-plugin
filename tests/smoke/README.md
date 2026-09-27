# Live acceptance checks

The Image check uses the same SDK adapter, quote coordinator, credential-scoped
job store and result transfer commands as the adopted Image runtime. It replaces
the old Image prototype smoke. The other three scripts remain prototype tools;
the complete multi-suite entry point, protected GitHub environment, budgeted CI
and hosted acceptance in [#40](https://github.com/scenario-labs/blender-plugin/issues/40)
are still pending. No smoke runs in ordinary tests or PR CI.

## Quote and approve one Image request

Use the pinned uv environment. Configure the explicit test API-key pair described
in [CONTRIBUTING](../../CONTRIBUTING.md#environment-variables). The optional
`SCENARIO_TEST_PROJECT_ID` selects a project; leaving it blank uses the API key's
default scope. Agree on that concrete test scope and budget before spending.
Do not infer the default project from a discovery list.

Create a private JSON input object appropriate to the selected custom Image model,
for example a prompt and that model's supported size/output parameters. The tool
retrieves the current model schema and validates those inputs through the shared
adapter. It does not upload local references. Use an already imported asset ID
when an authorized reference is needed.

```sh
mkdir -p workdir
uv run --locked --env-file .env.local python -m tools.smoke_image quote \
  --run-dir workdir/image-check --model MODEL_ID --parameters parameters.json
```

`quote` performs model retrieval and a `dryRun=true` estimate, never generation or
IP detection. It creates a new private run directory, prints the exact decimal CU
cost and the SHA-256 of `quote.json`, and saves the selected credential scope,
model, inputs, normalized payload hash and exact price there. Existing run
directories are rejected. Review the private quote file and intended test scope;
the printed hash binds subsequent approval to those exact bytes.

After explicit approval, replace `QUOTE_SHA256`, `EXACT_COST` and `APPROVED_CAP`
below with the reviewed values. There is no default spending cap. Both decimal
arguments must be nonnegative, finite decimal strings without exponent notation.

```sh
SCENARIO_SMOKE=1 uv run --locked --env-file .env.local python -m tools.smoke_image submit \
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
transport, and verifies saved receipt hashes/sizes. Image MIME metadata is checked;
this does not decode images or establish visual quality. It does not upload,
cancel, import into Blender or apply to a scene. Native UI/MCP acceptance remains
a separate check against the exact installed release candidate.

## Resume without repeating generation

Keep the run directory, database and scope key together. After a process exit,
known-job polling failure or failed download, use the original credentials and
optional project:

```sh
uv run --locked --env-file .env.local python -m tools.smoke_image resume \
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
| 0 | Quote saved without submission, or downloaded Image receipts verified |
| 1 | Service, storage, transfer or terminal job failure; inspect saved state |
| 2 | Invalid usage, missing opt-in/credentials, quote identity or scope mismatch |
| 3 | Approval/cap mismatch or changed fresh quote/payload; no generation submitted |
| 4 | Saved state needs review or polling deadline expired; no generation replay |

Stdout contains only costs, an approval hash, known state names and file counts.
`report.json` contains state, cost, payload hash and result byte counts/hashes; it
omits credentials, raw responses, request inputs, project/job/asset IDs and signed
URLs. Review even that summary before sharing. The rest of the run directory is
private and must never be committed or uploaded as a public artifact. The directory
is retained deliberately for recovery; remove it only after the job's outcome is
resolved and required evidence has been reviewed. The directory and its ancestors
must remain privately owned; this is not protection against a local attacker.

`python tests/smoke/smoke_image.py` accepts the same subcommands as the module.
An old bare invocation fails without contacting Scenario. Omit `--env-file` and
use `--no-env-file` when the shell supplies credentials. Keep the spending flag
out of dotenv files. Offline tests use synthetic SDK responses and never spend.
