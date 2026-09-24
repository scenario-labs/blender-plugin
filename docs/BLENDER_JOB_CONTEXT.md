# Blender job contexts

`scenario.blender.job_session.JobSession` owns one explicitly selected SDK
connection, scoped store, coordinator and worker pool. Extension registration
installs file, dependency, frame, undo and redo hooks; it creates no session,
connection or worker. This is the integration boundary for the shared runtime.
The existing prototype UI/MCP has not yet been switched to it.

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

File identities are deliberately session-local. Restarted records stay available
for recovery, but automatic application cannot assume an old file or target is
unchanged. Persistent target selection and explicit recovery/application UI remain
integration work; matching a scene or object name is insufficient.

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

The actual authentication context, safe online-access snapshot for worker calls,
UI/MCP activation and durable result application remain separate work.
No account ID is guessed and no privileged or live service call is introduced.

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
unrecognized origins before Blender application. These session methods do not
add active UI/MCP controls or solve authoritative account/project discovery.

## Stored result retrieval and verification

The optional `result_downloader` and `result_root` constructor arguments forward
an explicit [storage policy and private root](RESULT_TRANSFERS.md) to the shared
coordinator. Supply both together; incomplete configuration fails before workers
start. The application owner must choose trusted storage hosts, provide a
thread-safe online-access snapshot and retain the private directory through
application. No default production host policy is selected by the session.

On the main thread, `load_results`, `download_results` and `verify_results` queue
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
callers must preserve private storage ownership and implement durable application
separately. Download failures remain `DOWNLOAD_FAILED` for explicit retry, while
local verification failures do not trigger another download or generation.


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
