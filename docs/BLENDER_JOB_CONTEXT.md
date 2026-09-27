# Blender job contexts

`scenario.blender.job_session.JobSession` owns one explicitly selected SDK
connection, scoped store, coordinator and worker pool. Extension registration
installs file, dependency, frame, undo and redo hooks; it creates no session,
connection or worker. This is the integration boundary for the shared runtime.
The active runtime now creates one selected session lazily for local MCP recovery
inspection, prepared-intent cancellation, and Image UI/MCP quote/submission and
result delivery.
Other generation lanes remain on the prototype path.

`runtime.ensure_job_session()` binds the session to the catalog's credential-local
scope and store. The job owner gets a separate SDK HTTP pool using the same
explicit credentials and worker-safe online-permission event. Catalog retirement
disables both pools' network permission; each owner closes its own pool only after
its in-flight work finishes. A catalog preview quote is not a session-issued quote
and cannot be reused for shared paid dispatch.

Credential changes and runtime reset deactivate the session without waiting for
network I/O. The existing session registry retains in-flight work so its receipt
can finish in the original store. GUI timers and the main-thread MCP loop reap
retired sessions after completion. Closing a panel does not retire the session.
File loading retires the selected session through the existing lifecycle hooks.
The next recovery call creates a fresh owner and context token for the same store.

The local MCP tools `list_local_jobs` and `cancel_prepared_job` perform no service
requests. Inspection returns exact saved costs and recovery suggestions, not new
spending approval. Cancellation needs the current context token and observed
record revision, and only accepts an unclaimed prepared intent. Resetting, loading a file or
switching credentials invalidates the context token, even if another scope has
the same request ID. Shared saved-job controls below also expose known model-job
cancellation and download/receipt recovery. Uploads and remaining paid entry
points still need active integration. These recovery
tools do not import prototype jobs. Image submission creates new durable intents.

Active Image jobs poll and download through this session. `apply_images` requires
an owned verification completion, resolves the original scene/revision, and claims
`applying` before loading any image. Every byte snapshot must match its saved
receipt and supported container before Blender decodes and packs it. Multiple
variants are imported together; failure removes only newly created images.
Confirmed rollback records `apply_failed`; incomplete rollback or uncertain
receipt persistence retains `applying`. `retry_image_receipt` can acknowledge a
known completed import without importing again, using its owner-local handle.
These methods never rebind a restarted job by scene name. Explicit recovered
image imports use a separately approved destination as described below. The Image facade exposes
receipt-only retry to UI/MCP while its original owner retains the outcome handle.

## Origin and quote lifetime

On Blender's main thread, capture inputs together with
`origin = capture(scene, target)`, then request the estimate.
`prepare(estimate, origin=origin)` validates that same origin and persists its
opaque file-session, scene and optional object identities in the durable intent.
It never stamps an old quote with a fresh revision after estimation.
Names, active-object selection and file paths are never used to rediscover a
missing target. `capture` also exposes this origin for callers preparing inputs.
Removed RNA scene/target references are reported as `OriginUnavailable` at capture
and delivery boundaries; callers do not need a separate stale-RNA error branch.
Dependency updates conservatively invalidate the affected scene's revisions;
frame changes invalidate unconditionally in their own pre-change hook, regardless
of whether the unevaluated depsgraph lists updates. Undo/redo and file loading
invalidate captured state too. Every main-thread scene callback and reaper tick
prunes removed captured scenes and deleted object wrappers, including when a surviving
scene has no dependency updates. Deleted targets invalidate the scenes that captured
them and their registry entries are dropped; live targets in other scenes retain
their origins. The target pass reads captured RNA references, proportional to captured
target count; it does not scan every object or rediscover targets by name. Unlinked
but still live objects remain recorded, while delivery still requires originating-scene
membership. Reused object names never rebind a deleted target. This is an event-level guard, not synchronous interception of every
scene deletion; work already durably claimed remains in flight.
Render-thread frame/dependency callbacks invalidate only the thread-safe revision
registry conservatively across sessions; they never inspect or mutate bpy data. Callers
must prepare inputs and capture their origin together on the main thread.

A thread-safe, bpy-free revision registry is checked again by the coordinator
inside the submission claim, with its lock held through the durable SUBMITTING
write. Invalidation is serialized against that boundary; it cannot slip between
the origin check and storage commit. A queued
quote whose origin was invalidated cannot spend. Work already claimed can finish
and persist to its originating scope. The optional `origin_guard` context-manager factory on
`JobCoordinator` must be thread-safe and must never access Blender. The guard covers local
SQLite work only, never HTTP; invalidation may briefly wait for that commit.

The coordinator can apply this same pure revision guard to configured upload
preparation and mutation claims; see [upload commands](SDK_UPLOADS.md#shared-worker-commands).
The optional session upload configuration below uses this boundary. Inspection
and explicit upload refresh do not rediscover or rebind targets.

File identities are deliberately session-local. Restarted records stay available
for recovery, but automatic application cannot assume an old file or target is
unchanged. Explicit Image recovery captures a new destination for review;
matching a scene or object name is insufficient. Other result types still need
their own explicit recovery integration.

## Results and lifecycle

`submit`, `refresh_remote` and `cancel_remote` return task handles. `drain()` returns completed
outcomes on the main thread without waiting for network work. Per-task errors
for invalid worker origin/scope or malformed results do not drop successful
neighbors from the same drain. Undrained outcomes count against a separate
admission limit, so a closed view cannot accumulate
unbounded completed payloads. UI closure itself does not deactivate the session.

`deliver(completion, callback)` validates the issuing session, active scope,
origin revision, selected scene and continued target membership immediately
before calling `callback(result, captured_scene, captured_target)`. Successful
outcomes can be delivered only once, even when the callback fails. This guard
never performs import itself or marks a job APPLIED: durable import transactions
and error/retry UI must be layered above it. Failed or stale results are available
for caller review; they never silently fall back to the current selection.

Account/project switching must explicitly deactivate the previous session before
creating its replacement from authoritative credentials/scope. File loading does
this automatically. A main-thread timer closes inactive owners after tracked work
finishes; an explicit headless loop can call shutdown directly. Extension disable
joins every session before unregistering Blender services. HTTP waits retain the
worker timeout limitations; shutting down is not remote cancellation.

Once every owned worker has exited, session-local outcomes and registry ownership
are released even if SDK connection cleanup raises. Direct `shutdown()` callers
still observe that exception. The background reaper and extension unregister
isolate ordinary failures per session, log a fixed message without transport
exception details, and continue servicing or cleaning up the other owners.
Unregister removes timer and lifecycle hooks even after session cleanup failures,
allowing the remaining extension registry cleanup to proceed. Control exceptions
continue to propagate; a session with live workers retains its ownership.

The selected API-key context and worker-safe online snapshot are bound by the
active runtime as described above. Remaining lane activation and recovered
application of other result types remain separate work. The account scope is a local pseudonym,
not a guessed server account ID.

## Recovery inspection and cancellation

`recovery_plan()` is a main-thread, read-only view of the selected connection's
saved jobs and suggested actions. It does not rediscover Blender targets, change
records or submit requests. Restarted records retain their original origins.

`cancel_prepared(request_id, expected_revision=...)` durably cancels an unclaimed
local intent immediately on the main thread. It bypasses the worker queue and
completion-admission limit, so a full queue cannot delay cancellation until after
a queued submission spends. The queued submission subsequently fails its stored
state check. An already claimed request or stale revision fails explicitly; local
cancellation does not promise remote cancellation.

`cancel_remote(request_id, expected_revision=...)` uses the same bounded pool and
completion queue as refresh/submission. Its original origin is loaded from this
connection's scoped store, never captured from the currently selected scene.
The [coordinator's model-job cancellation contract](JOB_COORDINATOR.md#known-model-job-cancellation)
still governs eligibility, the durable single-action claim and authoritative
status polling. A canceled acknowledgement alone cannot report terminal success;
an uncertain response remains recoverable by refreshing the known ID without
replaying the action. General workflow cancellation is unsupported.

Cancellation, refresh and recovery inspection deliberately do not require the
old scene/target to remain available. This allows explicit cancellation and
reconciliation after deletion or restart. Their completions still carry the
original stored origin; `deliver` continues to reject unavailable, stale or
unrecognized origins before Blender application. The Image facade exposes these
methods through the saved-job controls below; account scope remains the explicit
credential-bound local identity rather than a guessed discovery result.

## Stored result retrieval and verification

The optional `result_downloader` and `result_root` constructor arguments forward
an explicit [storage policy and private root](RESULT_TRANSFERS.md) to the shared
coordinator. Supply both together; incomplete configuration fails before workers
start. The application owner must choose trusted storage hosts, provide a
thread-safe online-access snapshot and retain the private directory through
application. No default production host policy is selected by the session.
Without storage configuration, download and verification report a configuration
error without changing the stored job, including a reopened READY record.

On the main thread, `load_results`, `download_results`, `recover_downloads` and
`verify_results` queue
the corresponding [coordinator commands](JOB_COORDINATOR.md#result-retrieval-and-download-commands)
with the original stored origin and expected record revision. Metadata and signed
transfer work run on the existing pool. Like refresh and cancellation, these
commands remain available after a scene switch, target deletion or restart;
retrieval does not grant permission to apply into a new Blender context.

`drain` validates both the record inside `VerifiedResults` and ordinary result
records against the issuing origin/scope. Verification returns a frozen result
containing a tuple of verified local paths. `deliver` still requires the original
current scene/target and permits the completion to be used once. Receipt
verification does not lock file bytes, run an importer or mark a job APPLIED;
callers must preserve private storage ownership. The explicit World command below
supplies one application path. Download failures remain `DOWNLOAD_FAILED` for explicit retry, while
local verification failures do not trigger another download or generation.
Explicit interrupted-download recovery only reconciles verified local receipts
and durable state under the cross-process transfer lock. A restarted session can
recover those downloads, but its completion cannot rebind an old scene or target.

## Explicit saved-result World application

`apply_world(completion, asset_id=...)` consumes an owned `verify_results`
completion on the main thread. The caller explicitly selects one saved asset as
an equirectangular panorama; neither its name nor its aspect ratio establishes
that projection. The command requires the original current scene/revision and
continued membership of any captured target. It never falls back to selection,
names or another file session. An invalid selection does not consume the outcome.

Immediately before mutation, it consumes the completion and acquires the
[durable application claim](JOB_COORDINATOR.md#durable-application-claims).
The [World primitive](WORLD_APPLICATION.md) checks the selected saved receipt
against the exact decoded bytes. Other results from a multi-asset job remain
available on disk; this command applies only the selected asset, then marks the
job APPLIED. It performs no service call, download, generation or blend-file save.
`AppliedWorldResult` contains the final stored record and the primitive's guarded
restoration handle as `application`. APPLIED records the completed local scene
assignment, not a saved file, undo entry or complete generation workflow.

A known parsing/application failure becomes APPLY_FAILED only when the original
World binding and both World/image allocation sets are unchanged after the
primitive's cleanup. A fresh verification completion can then support an explicit
local retry. The consumed completion can never be reused. Stale revisions,
unavailable origins and interrupted claims do not trigger retries or rebinding.

Unexpected exceptions, failed rollback/allocation cleanup and persistence errors
raise `WorldResultUncertain`; control exceptions propagate. A durable APPLYING
claim is never automatically reset. If persistence fails after successful scene
assignment, the exception retains its `application` restoration handle. The saved
record may already be APPLIED if its commit succeeded before the error. Inspect
both scene and record; never repeat or undo the mutation merely because a write
failed. Guarded restoration is an explicit caller action and does not rewrite
the durable record. As with all primitive handles, discard it after file load,
undo or extension shutdown. SQLite and Blender do not share an atomic transaction.

When scene assignment completed and only its receipt failed,
`retry_world_receipt(outcome)` accepts the exact `WorldResultUncertain` raised by
this session. It retries or acknowledges only the original successful receipt,
using the coordinator's saved outcome evidence. It never reads or mutates a scene,
reapplies a World, restores anything, verifies files, downloads or generates.
It returns `AppliedWorldResult` with the saved record and original restoration
handle, then consumes the pending outcome. A failed retry raises the same sanitized
outcome so callers can retain it for another explicit attempt. Fabricated, foreign,
consumed and shutdown-session outcomes are rejected, as are errors from uncertain
scene mutations or failed cleanup. The pending handle is caller-owned and is not
reconstructed after restart. Origin invalidation alone does not block bookkeeping;
session shutdown discards pending receipts. A later explicit restoration is left
intact: APPLIED acknowledges the prior assignment, not the current World binding.

Installed native fixtures cover claim ordering, exact selection, changed bytes,
safe local retry, original context/ownership, interrupted or uncertain outcomes,
write acknowledgement loss and guarded restoration. The command is available to
explicit integrations only; active UI/MCP entry points and recovery UX remain
separate work.


## Shared asynchronous estimates

After capturing inputs and origin on the main thread, `quote_model` or
`quote_workflow` queues metadata retrieval and exact SDK estimation on the same
session worker pool. Its completion carries an `OriginQuote`, not a stored job;
no intent is persisted merely to display a price. `drain` checks its scope and
origin, and `deliver` rechecks the selected captured scene/target as usual.
`prepare_quote` accepts that unchanged quote after selection and persists its
original origin once. Scene changes during metadata/estimation reject the quote;
the caller must recapture inputs and request a new estimate. The quote cannot be
rebound through the older direct-estimate preparation method. These APIs do not
authorize paid dispatch or replace the active UI/MCP call sites by themselves.

## Upload references

The session optionally accepts `upload_store`, `upload_sources` and
`part_uploader`, forwarding the complete configuration to its existing
coordinator and bounded worker pool. Their scope and explicit storage-host policy
must satisfy the [upload contracts](SDK_UPLOADS.md#shared-worker-commands).
There is no default production host allowlist or automatic upload configuration;
partial configuration raises `TypeError` before starting another worker owner.
With all three dependencies supplied, a mismatched upload/job scope still raises
`ValueError`; the existing source and transfer-policy validation also applies.

Capture the scene/target origin with the chosen source before calling
`prepare_upload(source, origin=..., kind=..., content_type=...)`. Main-thread
admission checks that origin and completion capacity before queuing staging.
`initialize_upload`, `transfer_upload_part` and `finalize_upload` load the
persisted record through public `inspect_upload`, resolve its original target at
admission, and queue the existing command with the supplied expected revision. The core
origin guard checks again before intent persistence and mutation claims, so a
queued command cannot use a stale captured revision. No source read, storage PUT
or service call runs on Blender's main thread.

`inspect_upload` and `upload_recovery_plan` are synchronous main-thread metadata
reads. They remain available when completion capacity is full and do not require
the old scene/target to exist. `refresh_upload` likewise queues an explicit status
read using the saved origin, allowing recovery after target deletion or restart.
It never transfers another part, recreates initialization or repeats completion.
Unknown requests in another account/project are absent, not rebound to the
current connection or selection.

`cancel_prepared_upload(request_id, expected_revision=...)` is synchronous on the
main thread and bypasses worker/completion queue capacity. It cancels only local
PREPARED intent in the active selected scope. Target deletion, origin invalidation
or restarting the session does not prevent this local bookkeeping. The returned
record is immediate; no completion is queued and no scene mutation, source read,
file deletion or service request occurs. Initialization races are decided by the
durable revision claim: already claimed or uncertain uploads cannot be canceled
through this command. Inactive sessions reject it. It does not provide remote
abort or active UI/MCP cancellation controls.

`discard_upload_source(request_id, expected_revision=...)` queues explicit
[finished-upload source cleanup](SDK_UPLOADS.md#explicit-finished-upload-source-cleanup)
on the existing workers. Hashing and deletion stay off Blender's main thread.
Admission still checks the active scope and completion capacity, but needs no
current old scene/target, including after restart. The command returns the
unchanged terminal upload record and never changes the scene or deletes the
user's original file. Cleanup completions retain their original origin; they do
not authorize delivery into a replacement target. No active cleanup UI is added.

Upload task outcomes use the normal `drain`/`deliver` path: successful records
must match the stored scope/origin, and delivery rechecks the current captured
scene/target before a once-only main-thread callback. A late claimed receipt may
persist after a file switch, while delivery remains blocked. Restarted origins
remain unrecognized for automatic application even when status refresh succeeds.
Callbacks do not by themselves attach a reference or commit a Blender application
transaction. Active UI/MCP upload controls and explicit recovery/application UX
remain separate work; account/project identity is still supplied by the caller.

## Active Image submission

[ModelJobs](../scenario/blender/model_jobs.py) retains bounded ephemeral quote
handles and in-memory display projections for the selected session. UI and MCP
Image generation share its quote and submission commands. Handles bind the
captured scene, exact input snapshot and session-issued SDK estimate. Submission
validates the current inputs and exact approved cost before consuming the handle
and persisting intent. The coordinator still checks origin, ownership and expiry
at dispatch. No handle is reconstructed from a saved fingerprint after restart.

`drain(task=...)` collects only the requested task, leaving other consumers'
completions intact. Context maintenance drives Image quote/receipt delivery in
both the GUI and actual CLI loop. Image status after restart is read from the
credential-scoped store, without automatically polling or resubmitting remotely.
Active jobs poll, download and import supported image results through this owner.
Local reference upload and other result types remain unwired; this slice must
not be advertised as complete release acceptance.

## Active saved-job controls

The Jobs panel can inspect saved jobs without network activity. Recovery buttons
and MCP `recover_local_job` share `ModelJobs.control`, guarded by the selected
context token and exact saved revision. Queued commands retain their original scope.

- `refresh` observes a known remote ID once, without continuing delivery.
- `resume` polls and downloads the existing job, including after restart or a
  failed download, without authorizing automatic import.
- `cancel` uses the coordinator's once-claimed model cancellation command and
  continues observing the known ID. The acknowledgement alone is not cancellation.
- `recover_download` verifies interrupted saved receipts under the existing lock,
  without network access or import.
- `retry_receipt` saves an already completed image import's outcome without any
  scene mutation. The exact pending owner-local handle must still exist.

No action reconstructs a quote, replays an uncertain submission, guesses a remote
ID or rebinds the original scene. Missing/stale revisions and retired contexts fail
before command dispatch. The UI confirms remote cancellation through its native
invoke path. MCP recovery waits off the main thread and rechecks its owner before
returning status. Shared `wait_for_job` reads saved state on the HTTP worker while
the main thread advances delivery; pause, failure, completion or timeout returns
the current result without canceling or regenerating. Stopping the MCP server
interrupts its wait without canceling the generation.

## Explicit recovered Image application

For downloaded PNG/EXR results in `ready` or confirmed `apply_failed` state,
**Import saved images** captures the current file-session/scene revision and
shows a native confirmation dialog. MCP `prepare_result_application` returns
the scene, image names and a single-use `application_id`; after user approval,
`apply_result_application` consumes it. Neither inspection nor download authorizes
an import. Canceling the dialog discards its approval. Approvals are owner-local,
bounded to 128 and never persisted or reconstructed after restart.

Admission rechecks the selected context, exact stored record and destination
before queuing verification on the existing workers. When verification finishes,
`apply_recovered_images(completion, destination=...)` resolves that same captured
destination again. It uses the coordinator's explicit recovered claim to save
`applying` and `application_origin` atomically before decoding or packing images.
The original `intent.origin`, request, scope, quote and result receipts stay
unchanged. Scene/file changes require new review; the importer never recaptures
the current selection as replacement approval.

The importer adds packed image datablocks to the current file; it assigns no
object, material or World and does not save the blend file. The Image Editor can
select the imported images. Import, rollback and receipt-only recovery use the
same primitive as automatic delivery. `applied` and interrupted `applying`
records cannot be imported again through this command. No service call, download
or paid submission occurs during application.
