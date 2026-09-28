# Scoped upload metadata commands

The shared [SDK adapter](../scenario/core/api/sdk_adapter.py) exposes the
multipart upload metadata lifecycle through the packaged **scenario-sdk 2.2.0**.
These commands do not read files, transfer bytes, persist signed URLs, start a
background worker or connect the prototype UI/MCP by themselves. The active
[reference integration](#active-reference-uploads) uses them for local MCP uploads.
They are a foundation for
[#64](https://github.com/scenario-labs/blender-plugin/issues/64) and
[#65](https://github.com/scenario-labs/blender-plugin/issues/65).

| Command | Public SDK method | Behavior |
| --- | --- | --- |
| `create_upload(...)` | `uploads.with_raw_response.create` | POST multipart metadata once; returns the unwrapped `upload` record |
| `upload(identifier)` | `uploads.with_raw_response.retrieve` | GET a known upload in the selected project |
| `complete_upload(identifier)` | `uploads.with_raw_response.trigger_action(action="complete")` | Explicitly request completion once; return the actual reported processing state |

The adapter's selected credentials, HTTPS API endpoint and immutable project
apply to every command. Callers cannot inject a different project or arbitrary
SDK extension parameters through upload options. Online permission is checked
before each request; closed clients reject commands. The SDK has retries disabled
and redirects disabled, including for reads and completion acknowledgements.
A selected local account/team identity is not itself proof of server permissions.

## Inputs and responses

Initialization accepts the SDK's multipart kinds (`3d`, `asset`, `audio`,
`avatar`, `image`, `model`, `text`, `video`), a file basename, a bare MIME type,
an integer byte count and a positive integer part count. Zero bytes are allowed
as metadata; this does not claim the service accepts empty media. These local
checks do not invent service size/part limits or a chunking policy. The caller
must bind this metadata to its actual file before future byte transfer.

Optional asset settings use the SDK's `collection_ids`, `parent_id` and `hide`
names; the SDK serializes their documented camel-case wire aliases. They are
copied and validated before dispatch. Model uploads reject asset options,
matching the selected SDK's contract. URL ingestion and model-provider import
shortcuts are outside this multipart-only interface.

Upload and asset-option identifiers follow a local maximum of 256 characters
and reject path separators, URL metacharacters, whitespace and control characters.
Every response must contain an `upload` object with a valid ID and a nonempty
string status. Retrieval/completion require the returned ID to match the requested
one. The adapter retains unknown fields and statuses instead of manufacturing a
terminal result. Transfer instructions are preserved as metadata; they are **not
a validated or authorized storage transfer plan**. Do not log raw records: parts
may contain signed URLs and other sensitive response details.

## Completion and uncertain responses

The SDK 2.2.0 generated action parameter is `Literal["complete"]`; its docstring
says `"upload-complete"`. The adapter uses the generated literal already covered
by the dependency contracts. Actual service acceptance remains unverified; do not
silently substitute another action or invent an abort endpoint.

Only an explicit caller action can initialize or finalize an upload. The caller
must first establish that all its parts transferred successfully before calling
`complete_upload`. This low-level adapter cannot establish that from metadata.
A `validating` acknowledgement stays `validating`; even `complete` must not be
silently interpreted as an imported asset. Preserve the returned `entityId`,
`jobId`, actual status and future fields for the higher-level lifecycle.

A timeout, HTTP failure or invalid receipt after a mutation may leave an upload
created or completion accepted remotely. The adapter raises a redacted error and
makes no second request. It does not automatically create another upload, repeat
completion or poll. A higher-level owner must persist request/file/scope identity,
retain known upload IDs, distinguish uncertain mutation from transfer failure,
and reconcile through explicit reads. An unknown initialization ID remains
uncertain; do not attach a guessed upload or automatically recreate it.

## Remaining integration and verification

Signed PUT transport, private source staging, durable claims and explicit shared
worker commands are available as described below. The active local MCP path now
selects a host/size policy and exposes explicit saved-upload recovery. Typed form
attachment and explicit native recovery use the controls below; automatic orphan
retention and live acceptance remain separate work.
Finished uploads have explicit verified source cleanup as described below.
Storage requests must check destination/online policy and never forward
Scenario Authorization. No upload-abort method was established in this SDK.

Offline contracts exercise the actual SDK through MockTransport, including
scoping, field aliases, one-attempt failures, response identity, future processing
states, invalid inputs and ambient credential isolation. Installed-ZIP tests use
the bundled SDK with synthetic responses. These checks do not establish live
upload acceptance, OAuth transport or successful file import. Live checks require
their own authorized project and applicable budget.


## Signed part byte transfer

[`PartUploader`](../scenario/core/jobs/upload_transfers.py) performs one storage
PUT attempt for a supplied immutable `bytes` snapshot. SDK upload initialization,
retrieval and completion remain in the shared adapter. The pinned SDK exposes
numbered part URLs and expiration metadata; it does not transfer these bytes.
The primitive introduces no raw Scenario API endpoint or SDK fallback.

The caller must persist the upload identity, original scope, source/part digest
and transfer claim before calling it. It must bind the chosen URL and part number
to that SDK upload plan, check expiration, and choose an explicit part-size policy.
There is no implicit trusted-host list: the caller supplies an HTTPS storage
policy. `StoragePolicy` uses exact configured hosts; active reference uploads use
the separate S3 REST policy described below. Policies must come from reviewed
configuration, not by copying hosts from incoming URLs. No method initializes or
finalizes an upload here.

Inputs require a positive part number, a nonempty immutable byte snapshot within
the policy's byte limit, a bare MIME type, and a SHA256 matching the saved part
identity. Invalid or changed bytes fail before connecting. Large files must be
staged and split by the application; this primitive never reads the user's source
path or assembles a whole file in memory. Empty media needs a separately verified
service contract rather than an invented zero-part upload.

The transport uses verified TLS with bundled certificate authorities and sends
only PUT, Content-Type, Content-Length and Connection: close (plus HTTP's Host).
It has no Scenario credentials, cookies, ambient proxy/certificate settings,
redirect handling, URL logging or automatic retry. Body writes are at most 64 KiB;
permission and elapsed-time budget are checked between them and before reading
the response. Blocking DNS/TLS/socket calls retain the existing transfer timeout
limitations. Revocation cannot retract bytes already sent.

HTTP 200, 201 or 204 yields a URL-free `UploadedPart(number, size, sha256)` receipt.
This acknowledges this PUT only; it does not establish remote digest validation,
all-parts completion or successful asset import. Response bodies and ETags are
neither read nor persisted. The selected SDK completion method does not take ETags.

Failures before the first possible HTTP write raise sanitized `TransferError`.
After that boundary, transport errors and non-success HTTP statuses raise
`UploadUncertain`: storage may have accepted bytes. There is no retry or automatic
completion. The caller must preserve the durable claim and reconcile using the
known upload identity. Control exceptions propagate after cleanup and likewise
must leave the caller's persisted claim available for recovery. Ordinary cleanup
errors do not replace an acknowledged receipt with a failure that could invite
replay. These are offline transport contracts, not live upload acceptance.


## Durable upload claims

[`UploadStore`](../scenario/core/jobs/upload_store.py) records immutable source
metadata, whole-file and per-part SHA256 identities, original account/project
scope and Blender origin in a separate versioned SQLite database. It does not
read source files, run workers or call the network. The application must stage
and hash its actual source before creating the intent, then verify each part
against that identity before sending it. Signed URLs and credentials have no
fields in this record. Local chunking limits are not service acceptance claims.

Initialization, each part, and finalization require a committed claim before the
caller performs the corresponding mutation. Revisions and immediate SQLite
transactions reject stale or competing claims across connections. A part receipt
must match the claimed number, exact size and saved digest; receipts form an
ordered prefix. Finalization requires every receipt. Only an authoritative
imported observation can attach an asset ID.

Reopening preserves in-flight states verbatim. An interrupted initialization
without a known remote ID remains uncertain; it cannot be reset or recreated.
A part claimed without a receipt cannot be claimed again, including after a
restart. Uncertain finalization cannot be retried. Explicit SDK reads of a known
upload may reconcile processing, imported or failed observations without sending
bytes again. The selected SDK has no per-part receipt or abort API; pending
remote status alone cannot prove an interrupted part was rejected. No automatic
retry or cleanup endpoint is invented here.

The store validates source identity, state invariants, scope and revision when
reading. Missing/corrupt records, foreign databases, future versions and failed
writes raise errors and preserve evidence rather than resetting storage. Failed
receipt persistence leaves the earlier claim in place. New database files and
directories use private permissions where supported. The application owns the
storage directory under Blender's extension user path and must prevent its
replacement while in use. Each SQLite connection rechecks the database with
`lstat`, including after a competing creation. This rejects a symlink observed
at that boundary; it is not an atomic defense against an attacker who controls
the directory and can swap the path after the check. This database is separate from the job database;
there is no migration or active prototype integration in this component.


## Shared worker commands

The coordinator optionally owns one `UploadStore`, `UploadSources` and
`PartUploader` with the same scope as its job store. Its existing `JobWorkers`
queue exposes fixed commands; there is no second SDK client or thread pool.
It also exposes synchronous local cancellation, which does not wait behind queued
initialization or consume another queue slot.

| Command | Behavior |
| --- | --- |
| `prepare_upload` | Copy the chosen source into private storage and persist its immutable identity; no network |
| `initialize_upload` | Verify the staged whole file, commit initialization intent, call SDK create once and preserve the returned ID |
| `transfer_upload_part` | Retrieve the known upload, verify its metadata/next part destination and immutable bytes, claim and send exactly one part |
| `finalize_upload` | Require all saved receipts, claim completion, then call the SDK completion action once |
| `refresh_upload` | Retrieve a known upload and commit recognized processing/imported/failed observations without replay |
| `cancel_prepared_upload` | Immediately cancel only PREPARED local intent at its expected revision; no source access, deletion or remote request |
| `discard_upload_source` | Explicitly remove a verified staged copy for a CANCELED, FAILED or IMPORTED upload; retain its durable record and the user's original file |

Local cancellation requires the active selected scope but does not require the
old Blender origin or source file to remain available. It works offline and after
reopening the scoped store. The same SQLite revision check arbitrates cancellation
against initialization, including independent owners. When cancellation wins, a
queued or preflighting initializer cannot commit its claim and never dispatches.
When initialization wins, cancellation refuses; INITIALIZING, uncertain, remote
and terminal states cannot be reset or reported as remotely aborted. The selected
SDK still provides no verified upload-abort operation.

The canceled record retains source identity and original scope/origin. Both the
user's file and staged snapshot remain untouched; explicit source cleanup uses
the separate command below. Repeated cancellation and stale revisions require
reloading saved state.
A storage error may occur before or after commit: inspect the record rather than
assuming cancellation succeeded, resetting it or starting another upload. This
immediate command returns its immutable saved record directly, not a queued task.

Staging defaults to a local 256 MiB file limit and 8 MiB parts, configurable by
the application. Files are copied with bounded reads into a new private directory;
symlinks, nonregular sources, changed size/timestamps and incomplete copies fail.
File and directory flushes precede intent persistence (directory fsync on POSIX).
The original path is not stored. Subsequent edits to the original file do not
alter the snapshot. Each part read rechecks size and its saved digest; initialization
also verifies the full digest. On Windows, comparing a path with an open file uses
creation time where available because those APIs can assign different meanings
to `ctime`. Checks before and after reading the same open file still compare its
`ctime`, along with identity, size and modification time, to reject changes.
The application must retain ownership of the
staging directory and ancestors. Failed intent persistence or deactivation after
staging may leave a private orphan for explicit retention/cleanup policy; no
user source is deleted. These are local resource limits, not service guarantees.

The SDK's pending multipart plan must match kind, filename, MIME, size, count and
ordered part numbers. The selected URL must match the configured exact host policy
and carry a timezone-aware expiry more than 30 seconds away. This local freshness
margin is not a transfer-duration guarantee. A fresh plan is retrieved for each
explicit part command; signed URLs remain ephemeral. Provider-specific size,
part-order and expiry formats still need live acceptance. Model import is rejected
because its entity is not an asset reference.

Deactivation before a mutation claim prevents dispatch. Once claimed, responses
can persist only to the old scope; a later command is rejected by that inactive
owner. Ordinary errors after a claim conservatively become uncertainty, including
local permission revocation or definitive rejections; the commands do not infer
that retry is safe. Failed persistence and thread-control exceptions leave the
in-flight claim intact. A known upload's `complete`, `validating` or `validated`
status means processing, not imported. Only `imported` with a valid `entityId`
binds an asset; pending status does not release uncertain claims.

Preparation requires a captured `JobOrigin` before reading the source. When the
coordinator has an `origin_guard`, preparation checks that revision before staging
and again while persisting the intent. Initialization and part transfer check it
before preflight; initialization, each part and finalization hold the same pure
revision guard through their durable mutation claim. Invalidation cannot slip
between that check and the committed claim. The guard must be thread-safe and
must not access `bpy`; the shared `OriginRevisions` registry supplies that boundary.
File staging/verification and HTTP remain outside the guard. An unrelated scene's
revision does not invalidate the captured origin.

If the origin changes during staging, no upload intent is saved or dispatched.
The completed private snapshot can remain as an orphan for explicit retention
and cleanup, matching failed persistence or deactivation after staging. The
finished-upload cleanup command requires a saved terminal record; it cannot remove
these unrecorded orphans or arbitrary staging directories. A request already durably
claimed may finish and save its receipt under the original scope/origin. Inspection
and explicit remote refresh intentionally do not require a current origin, so a
missing scene or a new file session does not erase recovery evidence. They never
rebind it, release a claim or repeat a mutation. Callers without an `origin_guard`
remain responsible for establishing their own current-origin policy.

Offline tests exercise the actual SDK with synthetic HTTP responses and mocked
storage connections, including the installed extension and shared worker queue.
No live source is uploaded by these tests. Active UI/MCP wiring, authoritative
account discovery, production storage policy and user-facing recovery remain #65.

## Explicit finished-upload source cleanup

`discard_upload_source(request_id, expected_revision=...)` runs through the existing
worker queue and accepts only CANCELED, FAILED or IMPORTED records in the active
selected scope. It needs no current Blender origin or online access. PREPARED,
in-flight and uncertain uploads retain their sources. Cleanup never cancels an
upload, calls a service, deletes a remote asset or changes its saved history.
It returns the same immutable record, including all source hashes and receipts.

The command derives one private staging directory from the saved scope and request
identity. It accepts only `source.bin` there, verifies its saved whole-file and
part hashes within the configured byte limits, then rechecks file/directory
identity and contents immediately before removal. Symlinks, hard-linked or
nonregular files, changed bytes/metadata and unfamiliar files are preserved with
an error. It never recursively deletes a directory or reads the user's original
path. The original source is not stored and remains untouched.

Hash verification happens outside the coordinator lock. The final removal guard
rechecks active ownership and the exact saved record, so credential retirement
during verification prevents deletion. File removal and empty-directory removal
occur under that guard. As with staging and downloads, the application must own
the private directory and its ancestors: path checks do not establish atomic
protection against an attacker replacing files between filesystem calls.

An absent snapshot or an empty known staging directory is safe to clean again.
If interruption or a filesystem error occurs after unlinking the file, the
remaining empty directory can be removed by a later explicit retry, including
after restart. The durable terminal record stays unchanged. Concurrent cleanup
attempts may report an identity/removal conflict and require retry; no command
recreates a source or hides an unsuccessful filesystem operation. Directory
metadata durability across sudden power loss is not guaranteed. Corrupt copies,
unrecorded staging orphans, automatic retention and recovery UI remain separate.

## Scoped inspection and recovery visibility

`JobCoordinator.inspect_upload(request_id)` returns the immutable `StoredUpload`
for that coordinator's service/account/team/project scope, or `None` when no
matching local request exists. `upload_recovery_plan()` lists that scope's saved
records in local request-ID order, each wrapped in a frozen `UploadRecoveryItem`.
These public methods use the configured upload owner; callers do not need access
to its private store. The existing upload store, source staging and transfer
policy configuration is still required. Inactive owners reject inspection.

The snapshot retains the original scope, Blender origin, revision, source
identity, remote upload/asset IDs and durable part claims/receipts. It contains
no signed transfer URLs, credentials or original source paths. It is saved
metadata, not proof that the staged file still exists or that a Blender target
can receive a reference. No file verification, network request or recovery write
occurs during inspection. Invalid persisted records raise `StoreError` without
resetting the evidence or returning a partial recovery list.

| Saved progress | Suggested `UploadRecoveryAction` | Meaning |
| --- | --- | --- |
| Prepared | `REVIEW_SOURCE` | Review the staged source before any explicit initialization |
| Initializing or initialization uncertain, without an upload ID | `RECONCILE_UNKNOWN` | Preserve uncertainty; do not guess an ID or recreate the upload |
| Uploading, without an active part claim | `REVIEW_TRANSFER` | Review saved receipts and remaining parts or completion |
| Uploading with an active part claim, part uncertain, finalizing, finalization uncertain, or processing | `POLL_REMOTE` | A known upload can be retrieved explicitly; pending status does not release a claim |
| Imported, failed or canceled | `FINISHED` | No further upload recovery is suggested; import alone does not apply a Blender reference |

Suggestions never authorize initialization, transfer, completion, retry or a
claim reset. An in-flight worker may still finish after inspection or context
deactivation; its receipt stays in the original scope. Earlier snapshots remain
unchanged, and subsequent commands must still pass their revision/state guards.
After restart, a newly configured owner reads the same claims without assuming
that a previous worker is dead. The optional
[JobSession upload facade](BLENDER_JOB_CONTEXT.md#upload-references) forwards these
commands through its existing workers and guarded main-thread delivery. Form UI
and local MCP recovery controls use these commands as described below.

## Active reference uploads

[`ReferenceUploads`](../scenario/blender/reference_uploads.py) is a main-thread
facade over the selected `JobSession`, scoped upload store and existing workers.
`upload_reference` starts one explicitly authorized local-file upload, with an
explicit `kind` of `image` (the default), `audio`, `video` or `3d`;
`capture_reference` prepares a viewport/camera still or clip, or a selected-mesh
GLB first. Both return a
session-owned handle immediately. Poll `reference_upload_status` until the saved
state is `imported`, then pass its `asset_id` to the intended model file input
in a fresh estimate. Uploading
does not submit generation or approve its cost. Generation forms use the same
owner through **Upload reference** for image, audio, video and 3D files. Image
inputs also support explicit still captures; video inputs support explicit clips.
**Upload selected mesh** creates one GLB reference for an empty 3D input. Preparation
runs on the main thread in private temporary storage retained until asynchronous
staging finishes or the session retires. Clips use the preview range when enabled,
otherwise the scene range, at 1280x720 with no audio or implicit duration padding.
Capture settings/current frame and mesh selection are restored. Stills/clips need
an interactive viewport; mesh export also works headlessly. Uploaded snapshots do
not track later source edits. It never uploads while drawing or pricing.
Render pinned captures, Prompt Spark and non-image result application remain
separate integration; reference preparation does not establish their acceptance.

The upload kind and final file extension must match the local format policy.
An omitted kind remains `image`; a video path does not silently change the kind.
Unknown kinds and mismatched/unsupported extensions fail before staging or SDK
requests. MIME metadata follows the documented Scenario upload guide below.

| Reference kind | Accepted filename extensions |
| --- | --- |
| `image` | PNG, JPG/JPEG, WebP, GIF, AVIF, TIF/TIFF, HEIC/HEIF, SVG |
| `audio` | MP3, WAV, OGG, M4A |
| `video` | MP4, WebM |
| `3d` | GLB, GLTF, OBJ, FBX, STL, PLY, VOX |

This is filename-based metadata selection, not media decoding, conversion or
provider validation. Only the chosen file is staged. GLTF/OBJ sidecars, external
textures and buffers are not discovered or uploaded; prepare a self-contained
input when the model needs one. Model-specific format constraints still apply.
Status and saved/recovery inspection expose the persisted `kind` and
`content_type`; these are null in status until staging has persisted the intent.
All kinds share the same byte limits, origin guards and uncertain-write policy.

Multipart request MIME values follow the public upload contract, including
`audio/m4a` for M4A and `application/vnd.autodesk.fbx` for FBX. These need not
match aliases on generated or inspected assets. Before PUT, the saved MIME
must match the upload record exactly; do not normalize it from a later asset
response. The saved chosen filename is compared with `originalFileName`;
response `fileName` identifies the server storage object, not the chosen name.

Preparation snapshots up to 256 MiB into private storage, using 8 MiB parts
(the final part may be smaller). Metadata replaces basename characters outside
ASCII letters, digits, dots, underscores and hyphens with underscores; the original
file is never renamed. Later edits to that file cannot change the staged bytes.
These are application limits, not a claim that every format/size is accepted by
every model. Scene revision changes stop further mutation claims. Initialization,
each PUT and completion still require durable claims and use one attempt only.
Known processing uploads are polled at two-second intervals. Uncertain responses
stop automatic mutation; no later status read releases a part claim or replays
initialization/completion. The facade retains at most 128 handles per session.
An admission rejection from a full worker/outcome queue has not started a task;
the facade waits briefly and retries admission only. It never treats a failed
task as this safe case. Explicit refresh that confirms `processing` re-enables
status reads, while uncertain initialization/part/finalization cannot be replayed.
The facade owns recovery tasks and drains their outcomes even after the dialog
closes or the MCP caller disconnects. Recovery suspends automatic admission for
its record until the saved outcome has been observed; a successful local cancellation cannot schedule
initialization from a stale in-memory projection. Completed task projections are
also refreshed from durable storage before selecting their next command.

The [Scenario upload guide](https://docs.scenario.com/get-started/content/uploading-assets)
documents multipart uploads and signed S3 destinations. The active `S3UploadPolicy`
accepts HTTPS S3 global/regional REST endpoints under `amazonaws.com`, including
virtual-hosted and dual-stack forms described by the
[AWS S3 endpoint guide](https://docs.aws.amazon.com/AmazonS3/latest/developerguide/RESTAPI.html).
It rejects S3 website endpoints, other AWS services, custom CNAMEs, IP literals,
credentials, fragments and nonstandard ports. It is intentionally broader than
an exact bucket allowlist: the selected SDK's validated known-upload response is
trusted to choose the bucket/path. No local caller supplies a transfer URL.
The coordinator verifies upload/source identity, numbered parts and expiration
before that URL reaches the transport. Result downloads retain their separate
exact CDN-host policy. Neither transport sends Scenario credentials, follows
redirects, uses ambient proxies nor retries a PUT.

Capture files live in a private temporary directory. The session retains that
directory until staging completes, including while retired workers finish; drain
or shutdown removes it. Filesystem cleanup errors are sanitized and retained for
a later shutdown attempt. Process crashes can leave temporary or staging orphans;
automatic orphan retention remains unimplemented. Render-result capture forces
PNG and restores the scene's output settings. Viewport/camera capture needs a GUI;
image inputs in generation forms also offer Render Result capture.

After restart or context change, `list_reference_uploads` reads only the current
credential scope's saved metadata. `recover_reference_upload` requires its context
token and observed revision. It can refresh a known remote ID, cancel an unclaimed
local preparation, or delete the verified private source of a finished upload.
It cannot recreate an unknown upload, resend a part, finalize again or abort
remotely. Source cleanup never deletes the original file. Inspection/imported
metadata does not authorize attaching a reference into a different scene.

Offline native tests exercise actual SDK wrappers, SQLite and workers through
synthetic API/PUT responses, including changed origins, lost responses, restart
inspection and cleanup. Transport unit tests separately exercise signed PUT and
host rejection. This is not live S3/import acceptance or GUI interaction proof.

### Typed form attachment

[`reference_form.py`](../scenario/blender/reference_form.py) binds each explicit
upload to the original scene object, lane, model ID, input kind, reference slot
and source fields. Supported kinds are image, audio, video and 3D; still captures
are offered only for image inputs.
A saved marker blocks a second upload click, including after reopening a blend.
Local validation or rejected queue admission removes the marker only when no
task was accepted; the user can correct that input and retry. Asynchronous errors
retain it. A transient timer context without the originating scene pauses further
admission and attachment; returning to that scene still requires the unchanged
origin, model and slot.
The main-thread maintenance pump converts the unchanged slot to a Scenario asset
only after an imported observation and a fresh origin check. It marks the label
as an uploaded snapshot and invalidates the form's prior estimate. Generation
then quotes/submits the immutable asset ID, not the later contents of the original
file. A marked upload that has not attached blocks request construction in
every lane, preventing duplicate prototype upload while it is pending or
uncertain. Explicit clips and mesh snapshots use these same guards; unmarked
implicit generation-time preparation and render pinned captures remain separate.
An unloaded or list-only model schema is a temporary state, not an edited input.
In-flight bindings wait for model inputs before attachment and recheck the kind
when they load. Saved assets retain their scope checks; request construction
reports the unloaded model until its schema is available. Saved-reference
confirmation also requires loaded inputs and a fresh review after loading.

Uploaded references retain their credential-scope fingerprint. Reopening under
another connection, changing the input kind or manually changing that asset ID
blocks pricing rather than silently using it in another account/project. These local markers are not server
permission checks and contain no credentials. A scene/model/slot change prevents
late attachment; it does not abort already authorized remote work. No upload
operation grants generation approval.

**Inspect uploads** snapshots this connection's durable metadata without sending
bytes. Its paginated view shows errors, state and request IDs. Explicit actions
refresh a known upload, cancel an unclaimed preparation, or clean a terminal
upload's verified private staging copy. Cancellation and cleanup ask for
confirmation. These actions share MCP recovery ownership, context/revision guards
and no-replay rules; cleanup preserves the original file.

Automatic attachment handles do not survive restart. **Use saved upload** on a
reference slot or **Saved uploads** on a typed input offers attachment only for
matching imported media from the selected scope. **Use this reference** opens a
separate confirmation naming the scene, lane, model, input, reference and file.
The inspection view captures the destination before opening; a scene, model or
reference-list change requires reopening it. Confirmation consumes a single-use
approval and rechecks the stored record, current scope, scene revision and entire reference
form before adding or replacing a slot. Changed selections require a fresh review.
Attaching invalidates the previous price and never submits generation. Native
tests save/reopen an actual blend before explicitly approving the recovered
reference; they do not establish physical GUI interaction or live-service acceptance.
Never remove and re-add a reference as a substitute for reconciling an uncertain upload.
