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

`submit` and `refresh_remote` return task handles. `drain()` returns completed
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
UI/MCP activation and durable result downloads/application remain separate work.
No account ID is guessed and no privileged or live service call is introduced.


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
