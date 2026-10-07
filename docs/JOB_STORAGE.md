# Scoped job intent storage

[`JobStore`](../scenario/core/jobs/store.py) is the local persistence foundation
for [shared jobs #65](https://github.com/scenario-labs/blender-plugin/issues/65).
It does not start workers, call Scenario, modify Blender or replace the prototype
registry yet. The eventual shared coordinator must use this store before paid
dispatch; UI and local MCP must call that same coordinator.

## Identity and ownership

The caller supplies one immutable `JobScope`: exact API base URL, stable local
account scope, optional team and optional project. These are non-secret identifiers,
not credentials. Every query and key includes that scope. Switching accounts or
projects means selecting another store instance; a request ID from another scope
cannot be read or changed through the current instance.

For explicit API-key credentials,
[`open_credential_store`](../scenario/core/jobs/credential_storage.py) binds that
scope to the exact service and selected key/secret pair. A random installation-local
key signs this input with HMAC-SHA256; only the resulting `local-key-…` pseudonym
enters `JobScope.account_id`. It is not a server account identifier and is never
sent to Scenario. No discovery request or team/project selection is required.
Optional explicit team/project values still partition the store. Changing either
credential selects different records; switching back to the original pair restores
access to its records. Credential rotation does not automatically transfer jobs.

The active Blender catalog opens this store in the extension user-data directory
at `state/shared-jobs/`. `scope.key` must be backed up together with `jobs.sqlite3`.
The key is published complete without replacing a competing process's key; an
invalid key or a missing key beside an existing database fails explicitly and
preserves the files. First-time creators serialize on the permanent `.scope.lock`
file, then atomically replace their private temporary file into the still-absent
key path. This requires no hard-link support. Lock contention waits at most two
seconds before an explicit retry-later error; OS file locks are released when
the descriptor or process closes. Do not unlink the lock while Blender is using
the directory, since competing creators must lock the same file. New lock files
remain empty: Windows supports [locking beyond EOF](https://learn.microsoft.com/en-us/cpp/c-runtime-library/reference/locking?view=msvc-170),
so no sentinel write can race with another owner's mandatory byte-range lock.
No raw API credential is written by this binding. The local
key is not encryption, and losing it prevents recreating the old scope even with
the original credentials. Different installation keys produce different scopes.

The runtime retires this store selection together with its catalog when credentials
change. `ensure_job_store()` reopens the selected local history after a runtime
reset without starting workers or replaying submissions. Storage failure blocks
creation of the catalog context too. Explicit local MCP recovery inspection and
prepared-intent cancellation lazily activate the selected
[JobSession](BLENDER_JOB_CONTEXT.md). Image UI/MCP submission now persists new
intents through that same session before paid SDK dispatch. Remaining lanes and
recovery UI need integration; prototype records are not imported.

`JobIntent` freezes the local request ID, model/workflow target (or the fixed `prompt`/`translate` target for prompt helpers), payload SHA-256,
server quote SHA-256, exact quoted cost as a decimal string, and originating
file/scene/target/revision IDs. IDs describe the captured origin, never current
selection. Generate a fresh request ID for an intentional new operation and hash
the exact immutable payload/quote bytes held by the SDK estimate. The caller must
still verify the estimate belongs to the current adapter and matches the current
scope, payload and origin before authorizing dispatch.

Only hashes and exact cost are persisted for payload/quote identity. No prompt,
credential, raw service response, absolute file path or signed storage URL is stored.
Result manifests retain portable basenames, asset IDs, media types, optional
expected size/digest, allowlisted image texture roles and verified download receipts.
An old stored quote is not reusable spending authorization after restart. The
store does not itself verify a supplied fingerprint against a live estimate or
prove ownership of a supplied remote ID; those checks belong to the coordinator.

## Atomicity and failures

Pass a database path beneath Blender's `bpy.utils.extension_path_user(...)` from
the Blender integration. The core module accepts a path so unit tests and workers
remain bpy-free; it must not be pointed inside the installed extension. Use a
private local directory. Newly created directories/database files request 0700/
0600 permissions where the OS supports them; existing parent permissions and
Windows ACLs are not changed. Scope separation is application isolation, not
on-disk encryption or protection from another process with filesystem access.
Every connection rechecks that the database is a regular nonsymlink file,
including after a competing creation. The parent must remain trusted: this check
and SQLite's path open are separate operations, not an atomic no-follow open.

The database has an application ID and schema version **8**. SQLite transactions
with `synchronous=FULL` commit the whole change or report `StoreError`; no cached
in-memory result is reported as saved before commit succeeds. `BEGIN IMMEDIATE`
serializes writers across threads/processes. Each operation owns a connection,
with a two-second lock timeout. Storage failure must stop the caller before the
next external side effect. Filesystem/hardware durability still depends on the
platform honoring SQLite's synchronization operations; use local storage.

Creation rejects an existing request identity. Updates require the last observed
revision and increment it atomically, so only one racing caller can claim a
prepared request. `StoreConflict` means reload; it is never permission to create
another request or resend. Intent fields and a known remote job ID cannot change.

Foreign databases, unsupported versions, malformed records and mismatched stored
identities/revisions raise errors. They are preserved for explicit recovery,
never silently replaced with empty history. An already-open store also fails if
its database disappears. Previous shared schemas 2 through 7 upgrade in one
transaction that validates every scope, record, identity and revision. A corrupt
row or failed commit preserves all previous rows and the old version. This is
not a prototype import; version 1 and foreign databases remain rejected. Schema 2/3
results receive an unknown (`None`) texture role; schema 4 roles are preserved. Migration never contacts
Scenario or infers semantics from filenames. Schema 3 application destinations
are preserved, while schema 2 retains its original-origin application semantics.
Schemas before 5 receive an empty local-application history; schema 5 preserves
its existing claims, including unfinished applications. Schemas before 6
receive empty mesh input bindings; schema 6 preserves its captured mesh sources.
Schema 7 cloud results remain cloud records without synthetic spend or Film
bindings. Older extension builds reject schema 8; stop older Blender processes before
upgrading and do not expect an older build to open the upgraded store.

## Explicit cloud result records

Schema 7 adds `CloudJobIntent` for a completed model job retrieved using the
selected SDK connection. It retains a local recovery ID, exact scope, locally
captured scene origin, model ID and `source: cloud`. It has no payload or quote
hashes, no quoted cost and no captured mesh source. Selecting a cloud result
cannot invent proof of a local generation or authorize another submission.

The [coordinator](JOB_COORDINATOR.md#adopting-a-completed-cloud-job) verifies
the remote job before calling `adopt_cloud_job`. The store inserts it directly
as `succeeded`, with the confirmed remote ID and no result manifest. Only the
existing download and application states are valid for this intent type;
`create` and submission reject it. Result retrieval and destination approval
remain separate commands.

Adoption checks the selected scope for the remote ID within the same write
transaction. One existing record with the same model is returned unchanged,
preserving its original quote, origin, state and receipts. Ambiguous remote IDs,
conflicting models and local-ID collisions fail explicitly. Repeated or competing
reads cannot overwrite a saved application or create a second recovery record.
This is an explicit cloud read, not bulk import of the prototype registry.

## State boundaries

| Stage | Allowed progression |
| --- | --- |
| Prepared intent | `prepared` → `submitting` or local `canceled` |
| Submission attempt | `submitting` → `remote` with a remote ID, or `uncertain` |
| Lost response | `uncertain` → `remote` only after authoritative correlation |
| Remote job | `remote` → observed `succeeded`, `failed` or `canceled`, or durable `cancel_requested` |
| Cancellation claim | `cancel_requested` → observed `succeeded`, `failed` or `canceled`; never reset or replay |
| Download | `succeeded` → `downloading` → `ready` or `download_failed`; explicit download retry is allowed |
| Blender application | `ready` → `applying` → `applied` or `apply_failed`; explicit application retry requires origin/target checks |

There is no transition from `submitting` or `uncertain` back to `prepared` or
`submitting`. Neither a timeout nor an empty job listing permits replay. Remote
cancellation may race with success; the coordinator must reconcile the server's
actual state rather than declaring a cancellation on request acknowledgement.
A cancellation command claims `remote → cancel_requested` with the same atomic
revision check before sending. A second coordinator/process cannot claim it
again. Restart recovery polls this state even after a crash before sending;
there is no lease expiry or explicit reset/reattempt command. Schema 3 retains the
immutable result manifest and receipts introduced in schema 2 and adds a separate
`application_origin`. Claiming `applying` atomically saves that destination before
any Blender mutation. Automatic application uses the original intent origin;
explicit recovery may supply a newly approved destination. Neither changes the
intent. Application receipts preserve the claimed destination. A new destination
requires a new claim after confirmed rollback, never an interrupted `applying`
record. Upgrading schema 2 records in application states records their original
origin as the destination. Older readers reject schema 3 instead of dropping it.

Opening storage never executes or automatically advances work. At startup, once
old workers are stopped, the coordinator must treat saved `submitting` as
uncertain, poll known remote IDs, and surface interrupted downloads/application
for explicit recovery. In particular, an interrupted Blender application may
already have changed the scene; do not blindly apply it again. View closure does
not imply cancellation, and a reopened file/account must not retarget a result.


## Result transfer ownership

`result_transfer_lock(request_id)` holds a nonblocking OS file lock keyed by the
private database filename, full scope hash and request hash. Result download and
recovery commands use this same lock. POSIX uses `flock`; Windows locks byte zero
with `msvcrt.locking`. Other platforms fail closed. Locks release when their
file descriptor closes or the process exits. They have no timeout lease and do
not hold a SQLite transaction during network work.

Sidecar lock files remain beside the database in a private directory. Never
unlink them while any owner may be active: a replacement inode could admit two
owners. Symlinked/nonregular/multiply-linked lock files are rejected. The parent
directory is resolved once when opening the store, so aliases such as macOS
`/tmp` share the database and lock location; retargeting an alias cannot redirect
an already opened store. The database filename itself is never resolved through
a symlink and symlinked database files remain rejected. The resolved parent
must remain privately owned and all owners must use the same canonical database
path on a local filesystem that supports these locks. This is a cooperating
writer protocol, not protection from arbitrary disk access or direct store calls.
Stop all older extension processes that do not use this protocol before running
recovery; a schema upgrade does not establish lock compatibility.

The coordinator's explicit `recover_downloads` command rechecks receipts under
this lock before moving an interrupted `downloading` record to `ready` or
`download_failed`. It never resets a submission or uncertain application, adopts
unreceipted bytes, deletes files or performs network work. See the
[recovery command](JOB_COORDINATOR.md#explicit-interrupted-download-recovery).

## Durable result metadata

After observing remote success, `set_results` binds a nonempty tuple of at most
128 `ResultAsset` entries once. Each entry has an opaque asset ID, portable
basename, normalized media type, optional expected size/SHA256 and optional
allowlisted `texture_role`. The role is independent of MIME: it describes image
semantics, never a file decoder. Unknown roles remain `None`; arbitrary metadata,
prompts and URLs are not retained. Current schema records require the role key
even when null, so a truncated record cannot silently gain defaults. Duplicate asset
IDs and filenames (case-insensitive for portable filesystems) are rejected. The
caller must obtain metadata from the original scoped SDK job/asset responses;
the store does not prove provider ownership or follow an incoming URL. Use a
private result directory unique to the scope/request, so filenames cannot collide
with another job's output.

The manifest is committed before `downloading` can be claimed. Each successful
transfer calls `record_download` with its `DownloadedResult`; it must match the
manifest's name and any expected size/digest. Receipts cannot be replaced.
Revision checks and SQLite transactions serialize these writes with other job
updates. A write failure preserves the previous durable record and propagates.
Partial receipts survive `download_failed` and an explicit retry. `ready` requires
a receipt for every asset. Neither a manifest nor a receipt is permission to
spend again or apply to a different origin.

Before using an existing receipt, call `verify_download` from the
[transfer module](RESULT_TRANSFERS.md). It rehashes the local regular file and
checks its size, bounded reads and stable file identity. Missing, modified,
symlinked or non-regular files fail without deletion or network work. Only the
caller can decide explicit repair; an unreceipted published file is not implicitly
trusted after a crash. Do not promote an interrupted `applying` record to applied
or retry it automatically: the scene may already have changed.

## Validation and remaining integration

The unit suite exercises reopen, precise cost/identity preservation, all scope
components, stale and concurrent writers, invalid transitions, failed commit
rollback, process exit before commit, and corrupt/incompatible databases. An
installed-ZIP baseline test verifies SQLite and the store inside Blender's Python.

The prototype still uses its existing registry until the shared coordinator is
wired in. Result command orchestration, UI/MCP integration, live cancellation
acceptance and safe main-thread application remain under #65. Cancellation
claims, coordinator recovery and bounded workers provide foundations without
completing those integrated acceptance criteria.


Prompt Spark and translation intents use operations `prompt` and `translate`
respectively, and the same prepared,
submitting, uncertain and known-remote lifecycle. These operations add no dedicated database fields; the current storage version
is documented above. Older readers reject the new operation
instead of interpreting it as model/workflow intent. Restart can inspect and
refresh a known job ID; it cannot recover spending authorization or replay the
request from the stored hashes. Prompt text/results are not persisted here.


## Durable local result reuse

A generation job's original `applied` state remains terminal. Local reuse adds
`local_applications` to that same scoped record rather than reopening generation
or overwriting its first application destination. Each entry retains a unique
application ID, the reviewed job revision, captured file/scene/target revision,
purpose and selected asset IDs. It stores no extra paths, prompts, credentials,
URLs or Blender names. Supported purpose labels are images, media, model,
mesh_edit, World and material; a label does not establish decoder compatibility
or scene acceptance. New mesh replacements use `mesh_edit`; new static-model
imports retain `model`. Existing claims keep their recorded labels, including
older mesh replacements stored as `model`. This adds a validated label without
changing schema-5 fields. Older readers reject an unknown label; do not downgrade
a store containing newer application purposes.

`claim_local_application` requires the exact current revision of an applied job,
valid selected result IDs and no unfinished reuse. It appends an `applying` entry
and increments the job revision in one SQLite write transaction. Competing owners
cannot both claim the same review. The original intent, exact quote, remote ID,
results, download receipts, first application origin and generation state remain
unchanged. Claims do not verify files or establish user permission: the shared
coordinator and eventual UI/MCP caller must provide those checks.

`finish_local_application` records only known success (`applied`) or confirmed
no-change/full rollback (`failed`) against that same unfinished identity and
revision. It increments the job revision without replacing history. A failed
write can have committed; inspect the exact successor and retry only a known
receipt, never scene work. An interrupted `applying` record survives restart and
blocks another reuse. Elapsed time, file loading or another process cannot clear
it. There is no automatic uncertainty resolver or manual reset in this component.

Histories are limited to 128 entries per job and preserve every admitted entry.
At capacity, new reuse is rejected without evicting prior outcomes. Decoding
requires every version-5 field, unique identities, ordered source revisions,
matching selected asset IDs and a consistent final outcome/revision. Unsupported
formats and malformed histories fail closed. Schema upgrades validate all scopes
and roll back completely on corrupt rows or commit failures; stop old Blender
processes before upgrading and do not downgrade the database.

Native UI and MCP use these records through the existing runtime and fresh
[saved-result approval](BLENDER_JOB_CONTEXT.md#explicit-local-result-reuse), including
byte verification before decoding. Status inspection exposes the separate local
outcomes. Resolution of uncertain scene outcomes still requires inspection; no
automatic reset or replay is offered.


## Captured mesh inputs in generation intents

Schema 6 stores `JobIntent.mesh_sources`, an immutable tuple of typed input
bindings. Each binding records the parameter and optional array index, imported
asset ID, upload request/revision, captured upload origin and exact mesh export
provenance. It accompanies the exact normalized payload and quote hashes before
the submission claim. Metadata stays local; the SDK request still contains only
the model/workflow parameters.

The shared quote path uses the SDK adapter's schema selection: model `inputs`
with a missing/null fallback to `parameters`, and workflow `inputs_definition`
with a missing/null fallback to `inputs`. Bindings use the same selected fields
as payload preparation; unused alternate schema keys cannot add provenance.
Absent or null schemas without a usable fallback stop before estimation.
The shared quote path matches only declared 3D file inputs to completed captured
uploads in the selected credential/project scope. Prompt strings, unknown assets
and ordinary file uploads acquire no inferred source. Repeated array values keep
their positions for both `type: file_array` and `type: file` with `array: true`,
matching payload validation. Ambiguous captured records for the same asset reject the quote.
The coordinator rechecks every binding before preparation and again before the
paid claim. A missing or changed upload stops dispatch while preserving the job.

Bindings describe the immutable uploaded snapshot, not the current geometry of
an object. Their origin may differ from the generation's current scene context.
They neither retarget the job nor authorize automatic application, provider
alignment or original-object recovery after restart. Reopening keeps the source
history available for explicit review; no paid request is replayed.


## Film task reservations

Schema 8 adds optional `JobIntent.film_task`: the opaque production ID, bounded
task name, normalized recipe SHA256 and task/dependency SHA256. Only model intents
may carry it. Existing schemas 2 through 7 receive `None` after full validation;
cloud result records remain unchanged. Current records require the field, even
when null. Invalid/truncated bindings fail closed. No raw recipe, prompt, path,
credential or signed URL is added to storage.

`create` checks the selected scope for the same production/task inside its existing
`BEGIN IMMEDIATE` transaction, then inserts the intent and binding together. A
competing owner cannot reserve the same task even with a different recipe digest,
request ID, origin or model. Every existing state keeps its reservation, including
an unsubmitted cancellation or failed generation. A new take requires a new task
name and separately reviewed fresh quote. Failed commits roll back both identity
and reservation; a committed write with a lost acknowledgement is discoverable
through `film_job` and cannot be repeated.

`film_job(production_id, task_id)` returns only the selected credential scope's
record, rejecting ambiguous matches. It never reconstructs a quote or changes
state. A derived index selects the exact scope, production and task without
decoding unrelated history. It checks at most two matches, preserving ambiguity
rejection and the existing transaction's atomic reservation. Index creation
preserves records and skips malformed JSON; direct reads still reject damaged
records. The [Film command](FILM_PLAN.md#durable-model-tasks) verifies completed
results and matching task/dependency digests before reference reuse. Low-level
store calls trust the coordinator's binding; a caller-supplied digest is not
proof of recipe validation or permission. Existing submission, transfer and
application states remain unchanged.
