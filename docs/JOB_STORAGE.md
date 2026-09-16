# Scoped job intent storage

[`JobStore`](../scenario/core/jobs/store.py) is the local persistence foundation
for [shared jobs #65](https://github.com/scenario-labs/blender-plugin/issues/65).
It does not start workers, call Scenario, modify Blender or replace the prototype
registry yet. The eventual shared coordinator must use this store before paid
dispatch; UI and local MCP must call that same coordinator.

## Identity and ownership

The caller supplies one immutable `JobScope`: exact API base URL, stable account
identity, optional team and optional project. These are non-secret identifiers,
not credentials. Every query and key includes that scope. Switching accounts or
projects means selecting another store instance; a request ID from another scope
cannot be read or changed through the current instance.

`JobIntent` freezes the local request ID, model/workflow target, payload SHA-256,
server quote SHA-256, exact quoted cost as a decimal string, and originating
file/scene/target/revision IDs. IDs describe the captured origin, never current
selection. Generate a fresh request ID for an intentional new operation and hash
the exact immutable payload/quote bytes held by the SDK estimate. The caller must
still verify the estimate belongs to the current adapter and matches the current
scope, payload and origin before authorizing dispatch.

Only hashes and exact cost are persisted for payload/quote identity. No prompt,
credential, raw service response, file path or signed storage URL is stored.
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

The database has an application ID and schema version **1**. SQLite transactions
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
its database disappears. No prototype import or automatic migration is provided.

## State boundaries

| Stage | Allowed progression |
| --- | --- |
| Prepared intent | `prepared` → `submitting` or local `canceled` |
| Submission attempt | `submitting` → `remote` with a remote ID, or `uncertain` |
| Lost response | `uncertain` → `remote` only after authoritative correlation |
| Remote job | `remote` → `succeeded`, `failed` or acknowledged `canceled` |
| Download | `succeeded` → `downloading` → `ready` or `download_failed`; explicit download retry is allowed |
| Blender application | `ready` → `applying` → `applied` or `apply_failed`; explicit application retry requires origin/target checks |

There is no transition from `submitting` or `uncertain` back to `prepared` or
`submitting`. Neither a timeout nor an empty job listing permits replay. Remote
cancellation may race with success; the coordinator must reconcile the server's
actual state rather than declaring a cancellation on request acknowledgement.

Opening storage never executes or automatically advances work. At startup, once
old workers are stopped, the coordinator must treat saved `submitting` as
uncertain, poll known remote IDs, and surface interrupted downloads/application
for explicit recovery. In particular, an interrupted Blender application may
already have changed the scene; do not blindly apply it again. View closure does
not imply cancellation, and a reopened file/account must not retarget a result.

## Validation and remaining integration

The unit suite exercises reopen, precise cost/identity preservation, all scope
components, stale and concurrent writers, invalid transitions, failed commit
rollback, process exit before commit, and corrupt/incompatible databases. An
installed-ZIP baseline test verifies SQLite and the store inside Blender's Python.

The prototype still uses its existing registry until the shared coordinator is
wired in. Result/download metadata, cancellation intents, durable recovery
commands, bounded workers, teardown, current-quote validation, SDK dispatch,
UI/MCP integration and safe main-thread application remain under #65. This store
adds no alternate executor and does not claim those acceptance criteria complete.
