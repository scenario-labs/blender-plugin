# Quote-bound job commands

[`JobCoordinator`](../scenario/core/jobs/coordinator.py) implements synchronous
commands for the shared runtime under #65. It connects the scoped
[SDK adapter](SDK_ADOPTION.md) to the [intent store](JOB_STORAGE.md). It has no
worker pool, timer, UI ownership or bpy calls. The prototype UI/MCP still uses
its existing manager until the shared runtime is integrated.

## Prepare, claim, send, acknowledge

1. Build the adapter with the selected service, non-secret account/team identity
   and optional project. `account_id` is required for the coordinator even though
   read/estimate-only adapters may omit it. Missing identity fails before any
   request; a store with different scope is also rejected.
   The authentication layer supplies these identities; they are not proof that
   a token has been accepted by the remote service.
2. Obtain a real estimate through the adapter. Only the actual unchanged object
   issued by that active adapter is accepted; copying its public fields does not
   create another issued quote.
3. After the caller chooses the quote, `prepare(estimate, origin)` persists a
   fresh immutable intent and returns an ephemeral `PreparedJob`. This does not
   send a paid request. The local quote lifetime defaults to 120 seconds from
   **estimate issuance**, not preparation. It is a local freshness policy, not a
   claim about server pricing guarantees. Injected clocks must use the same
   monotonic time domain as the adapter.
4. An explicit `submit` command supplies the current normalized payload,
   operation/target and captured origin including its revision. These must match
   the prepared request. UI callers must invalidate/rebuild the current request
   when fields, account/project, scene or target revision change.
5. Inside the adapter's required `before_send` callback, the coordinator commits
   `prepared → submitting` using the current stored revision. A failed write,
   stale record, inactive coordinator or expired/mismatched quote stops dispatch.
6. The adapter consumes the issued quote once and calls public
   `generate.with_raw_response.run_model(dry_run=False)` or
   `workflows.with_raw_response.run(dry_run=False)`, with `max_retries=0`.
   Project and dry-run stay in the query, and the quoted payload is unchanged.
7. A valid remote job ID is committed before the command returns a remote record.
   No result is applied to Blender by this command.

`submit` is a spending command for an explicitly authorized user/MCP action.
Neither a quote, `PreparedJob`, callback nor persisted record grants spending
permission by itself. Integration must preserve its own approval boundary.
All verification in this change uses MockTransport with external sockets denied;
no live generation is performed by the test suite.

## Failure and context boundaries

Transport/HTTP failures and missing/malformed receipts after a durable claim
produce `SubmissionUncertain` and store `uncertain`. This includes remote IDs
that cannot satisfy the store's identity rules (such as overlong IDs or internal
Unicode whitespace), even if SDK-level ID validation accepted them. No failure
triggers a second request, and a consumed quote cannot be reused through another
coordinator.
Even an apparent HTTP rejection is treated conservatively until reconciliation.
If saving uncertainty or the successful receipt fails, `StoreError` propagates;
the durable `submitting` record remains recoverable and cannot be resubmitted.

Closing/deactivating an account context invalidates queued preparations. Network
work is outside the coordinator lock, so `deactivate()` does not wait for an
in-flight response. Already claimed work can finish; its receipt stays bound to
the original account/project and origin. It must never be applied to a newly
selected scene or object. A worker owner must wait for active calls before closing
their HTTP clients. View closure alone must not deactivate application jobs.

Restart recovery must not recreate a `PreparedJob` from stored fingerprints.
Stored `submitting`/`uncertain` requests require reconciliation; similar inputs in
job listings are not authoritative correlation. Current-quote validation,
submission ordering and single-use consumption are tested with the actual SDK,
including racing callers and late responses. Installed-Blender tests verify the
same ordering against the bundled SDK and SQLite.

The store persists result manifests and receipts; connecting download commands,
main-thread application and UI/MCP remains separate integration work. The low-level adapter hook orders persistence but cannot enforce correct
behavior by arbitrary callers; product code must use the shared coordinator.

## Restart inspection and known-job refresh

`recovery_plan()` returns immutable records and their suggested next action for
this scope only. It performs no network call or write. Prepared requests need a
new quote; submitting/uncertain requests need authoritative correlation; known
remote jobs can be polled. Interrupted downloads and application require explicit
review, while completed/failed/canceled records are finished. Inspection does not
claim another process's worker is dead or silently change its state.

`refresh_remote(request_id, expected_revision=...)` only accepts the current
`remote` or `cancel_requested` record with a known remote ID. It uses `SDKAdapter.job`, which calls the
public SDK `jobs.retrieve` with the selected project and online-access guard.
A matching ID and recognized terminal state are committed before returning an
immutable `RemoteSnapshot`. Unknown states, mismatched IDs, read failures and
failed persistence preserve local state. A stale polling result cannot overwrite
a newer decision; simultaneous identical terminal results are idempotent.

The snapshot retains the response in memory behind copy-on-read JSON access.
Raw responses, result text and signed URLs are not persisted. The saved remote ID
allows result metadata to be fetched again. There is deliberately no command to
attach a guessed remote ID or regenerate an unknown submission.

`cancel_prepared(request_id, expected_revision=...)` durably cancels only an
unclaimed local intent and sends no request. A queued submit will subsequently
fail its stored-state check. Remote cancellation is separate: neither canceling
a Python future nor receiving an action acknowledgement proves server cancellation.

## Application-owned workers

`JobWorkers` owns a coordinator and its SDK client for an application context.
It starts a fixed number of non-daemon threads, bounds the pending queue, and
rejects excess commands before dispatch. `submit` copies the current JSON
payload at admission; the coordinator checks the original quote, origin and
expiry again when the worker reaches the spend boundary. `refresh_remote` uses
the same pool. There is no generic callable execution or Blender access.

Each command returns a `JobTask` with `done()` and `result(timeout=...)`. A GUI
owner polls from its main-thread pump; a headless owner can block explicitly.
No result callback runs application code on a worker. Results retain their
stored scope/origin; callers must verify the captured file/scene/revision/target
before any Blender mutation. Exceptions remain observable through `result`.
The owner retains task handles; workers drop completed task/payload references.
Ordinary command exceptions settle the task and leave worker capacity available.
Thread-control exceptions (such as `SystemExit` or `KeyboardInterrupt`) settle
that task, deactivate the owner and cancel queued execution, then propagate out
of the worker. The application owner still calls `shutdown()` to join other
in-flight work and close the client; no pending task is abandoned unresolved.

`cancel_prepared` persists local cancellation immediately. If a queued command
later runs, the coordinator rejects it before network dispatch. If dispatch has
already claimed the record, cancellation reports a conflict: it cannot claim
that remote work was canceled. A failed cancellation write propagates.

On a context switch, `deactivate()` stops admission, invalidates quotes and
cancels queued task execution without waiting for network calls. Their PREPARED
records remain available for recovery review; cancellation of execution alone
is not a durable user cancellation. Already claimed requests can finish and
persist only to the original store. Closing/collapsing a view must not call this
method. A file-load owner must suppress old-target application independently.

On extension disable/exit, `shutdown()` deactivates, joins in-flight workers,
then closes the SDK connection. It is idempotent and safe for concurrent owners;
it rejects calls from its own worker threads. It does not kill network I/O or
promise instant shutdown; HTTP timeout policy still applies. Direct synchronous
coordinator/adapter users must also be stopped before transferring ownership or
shutdown. One owner per coordinator is required. UI/MCP lifecycle hooks and
main-thread result application remain separate integration work; the prototype
runtime is not replaced or supplemented by a second active runtime here.


## Known model-job cancellation

`cancel_remote(request_id, expected_revision=...)` accepts only a current scoped
`remote` record with a known ID and a model operation. A fresh `jobs.retrieve`
observation must identify `jobType=custom` or `jobType=inference`. The sanitized
[captured model-job fixture](../tests/fixtures/patina-copper-512/job.json) uses
`custom`; the pinned SDK 2.1.0 enum also includes `inference`. These are model-job
categories, not a general workflow-cancellation contract. Workflow operations
and other kinds remain unsupported. A job already observed terminal is committed
without sending a cancellation.

After eligibility checks, an atomic revision-checked store transition commits
`remote → cancel_requested` before the SDK action. This claim serializes competing
coordinators and Blender processes sharing the database; only one can dispatch.
A failed claim write stops the action. There is no lease expiry or reset back to
`remote`, so process death or a delayed first caller cannot allow another caller
to repeat the same cancellation. Stale revisions and inactive contexts fail too.

The winning caller makes one SDK `jobs.trigger_action(action="cancel")` call,
with the selected project, online-access guard and `max_retries=0`. The action
acknowledgement never establishes terminal status, even if it reports `canceled`.
A subsequent `jobs.retrieve` supplies the authoritative snapshot: an active job
remains `cancel_requested`, a completed job becomes `succeeded`, and only observed
`canceled` becomes `canceled`. Completion races retain their actual outcome.

Action/observation transport or malformed-wrapper failures report
`CancellationUncertain`; invalid status/identity evidence reports `RecoveryError`.
Both preserve the durable cancellation claim and known ID for explicit refresh.
Persistence and revision conflicts also propagate; failed writes never report
terminal success. After restart, `recovery_plan()` suggests polling that saved ID,
including if the process died after the claim but before sending. Recovery never
replays the action. A fresh explicit cancel command also rejects a claimed job;
a safe reattempt/reset contract is not implemented. This conservative boundary
can leave a job running after a claim-before-send crash or definitive action
rejection, while polling still recovers its eventual terminal result.

The SQL schema and stored record fields remain unchanged. The additional
`cancel_requested` state requires a reader that understands it; older readers
fail closed on that record instead of silently treating it as dispatchable.

`JobWorkers.cancel_remote` uses the bounded application pool and the same task
polling interface. Deactivation before the action is claimed stops dispatch;
once claimed, late observations stay bound to the original store. Shutdown
joins this work before closing the SDK. General workflow cancellation, live
service acceptance, and the UI/MCP cancellation controls remain outstanding
under #65; rejecting a workflow approval node is not a substitute. Captured job
types and offline tests do not establish live cancellation acceptance.


## Result retrieval and download commands

`load_results(request_id, expected_revision=...)` rechecks the saved successful
job through public SDK `jobs.retrieve`, then reads every asset through
`assets.retrieve`, always under the original immutable project scope. Only a
matching successful job with a nonempty unique `metadata.assetIds` list (up to
128) is supported. Each retrieved asset must match its ID and declare success,
a valid MIME type and an integral nonnegative `properties.size`. Unsupported
non-asset outputs and malformed/changed metadata fail explicitly. No result list
is inferred from a similar job or current selection.

The entire URL-free manifest is committed once after metadata validation. Local
basenames derive from index, asset-ID digest and MIME extension; provider paths
and filenames never choose local directories. Signed URLs remain in memory.
These contracts come from the pinned SDK's job/asset response models plus the
captured model-job asset list; they still need live provider acceptance.

Configure the coordinator with `result_downloader=ResultDownloader(policy, ...)`
and an existing absolute private `result_root` from Blender's extension user
data. There is no implicit storage-host allowlist. The root is split by hashes
of the full account/team/project/service scope and local request identity, so
identical asset names in separate requests cannot overwrite each other.

`download_results` loads a missing manifest, durably claims `downloading`, and
retrieves each unfinished asset again for a fresh signed URL. Identity, MIME and
size must still match the manifest. The bounded downloader publishes without
overwriting files; its verification uses the same configured byte cap. Each
receipt commits before advancing to another asset. Existing receipts are
rehash-verified instead of redownloaded. All receipts must exist before `ready`.

A transfer, metadata or verification failure saves `download_failed` and reports
a sanitized error. A persistence failure propagates and can leave `downloading`
for explicit recovery inspection; it never claims an uncommitted state was saved.
An explicit retry accepts only `succeeded` or `download_failed`, refreshes missing
URLs and preserves completed receipts. It never deletes/replaces a suspect file,
resumes an interrupted worker automatically or calls generation. An unreceipted
published file after a crash requires separate explicit reconciliation.

`verify_results` returns the unchanged scoped/origin-bound record and verified
local paths for `ready`, `apply_failed` or `applied`. It performs no service call
or scene mutation and rejects a changed job revision. These paths are not an
application authorization: the Blender owner must recheck origin/target and
atomically claim application before changing the scene. Interrupted `applying`
is deliberately rejected; a prior scene mutation may already have occurred.

All three methods are available through `JobWorkers` using the same bounded pool,
SDK lifetime and main-thread polling interface. Deactivation stops subsequent
asset work; a transfer already in flight can save its receipt to the old scope.
Closing a view must not deactivate these application-owned workers. Runtime
registration, production host configuration, interrupted-download reconciliation,
application recovery and UI/MCP controls remain integration work under #65.


## Reference upload commands

Optional upload storage, source staging and signed PUT configuration attach to
this same coordinator and worker queue. Their scope must match the job store.
See [upload commands](SDK_UPLOADS.md#shared-worker-commands) for preparation,
initialization, one-part transfer, finalization and explicit refresh. They do not
submit generation, create another client/pool, or apply references to Blender.
The active UI/MCP still needs to adopt these commands and its recovery controls.
