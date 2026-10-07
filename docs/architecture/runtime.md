# Runtime map and integration status

The extension package is [scenario/](../../scenario/). It currently contains the
active prototype runtime and separately tested components for its replacement.
The supported minimum in the [manifest](../../scenario/blender_manifest.toml)
is Blender 5.0; dependency and runtime acceptance have separate gates.

## Active entry points

| Responsibility | Source | Current behavior |
| --- | --- | --- |
| Registration | [registry.py](../../scenario/blender/registry.py) | Registers properties, panels, operators, composer, pump and local server integration. The `scenario_blender` headless command serves local MCP on the main thread. |
| UI lifetime and state | [runtime.py](../../scenario/blender/runtime.py) | Owns the credential-bound SDK catalog and process-wide UI/MCP state; native form quote/submission uses the selected `JobSession`; Film task controls use the same owner; Film capture/finishing remain to integrate. |
| UI generation | [generation.py](../../scenario/blender/generation.py) | Every native model form consumes a lane-bound session quote before durable submission; unfinished file/capture/Spark inputs block final pricing and submission. |
| Main-thread application | [pump.py](../../scenario/blender/pump.py) | Drains prototype events and applies results to Blender. GUI timer handling differs from headless execution. |
| Local MCP | [server.py](../../scenario/mcp/server.py), [tools_scenario.py](../../scenario/mcp/tools_scenario.py), [mcp_service.py](../../scenario/blender/mcp_service.py) | Queues scene tools for main-thread execution; model listing/schema use the same SDK catalog as the UI, all model generation lanes now use the shared session; ancillary service tools still call the prototype runtime. |
| Credentials | [config.py](../../scenario/core/config.py), [prefs.py](../../scenario/prefs.py) | Credentials default to the saved Blender pair; environment credentials require explicit selection and cannot mix with preferences. OAuth is deferred; shared runtime scope/project integration remains #65. |

These are source-inspection findings. Do not infer UI/MCP parity from the shared
adapter's test coverage, or promote prototype transport usage into an approved
exception to the mandatory SDK policy in [AGENTS.md](../../AGENTS.md).

## Active SDK catalog

Blockout Design/Refine now use
[BlockoutJobs](../../scenario/blender/blockout_jobs.py), owned by the selected
JobSession. UI and MCP share exact quote approval, durable submission, polling
and complete text retrieval. Guarded delivery stores a plan; explicit local
Build plan creates geometry. No unbound prototype event can apply a late plan.
The [Blockout contract](../BLENDER_JOB_CONTEXT.md#blockout-plan-commands) describes
scene ownership and recovery limits. Saved-plan recovery reads complete text
through that session, then requires a separate approval bound to a newly selected
scene and its unchanged Blockout fields. It replaces the stored plan only;
geometry still needs Build plan. This scoped integration does not establish
Film or complete release acceptance.

[SDKCatalog](../../scenario/core/api/sdk_catalog.py) binds model list/detail
reads to the explicitly selected API-key pair. The application owns this context;
opening or closing a panel does not replace it. The existing manager dispatches
reads off the main thread through one reusable SDK adapter/HTTP pool per catalog
connection. Retirement disables later requests immediately; the last active
reader closes the pool. Extension teardown does not wait for catalog network I/O
or close a pool underneath an in-flight request.

Overlapping list refreshes share one complete paginated SDK read for the same
connection and privacy scope. Public and private lists can progress independently;
each caller receives its own records. Failed or interrupted pagination preserves
the previous complete cache, releases all waiting callers and permits an explicit
retry. A later refresh still reads the service. Retiring credentials rejects the
pending result and clears both privacy caches.
List records are converted before publishing the cache. Malformed-record
conversion failures preserve the previous list and reach every overlapping caller
as a sanitized `ScenarioError`, keeping failures on the catalog event queue.

The GUI pump and main-thread MCP catalog/schema calls deliver the same queued
completions. Credential changes retire the context, discard its model/schema
caches and visible quotes, and reject late success/error events from the old
context. Main-thread entry points and GUI ticks mirror Blender's online-access
permission into a thread-safe event; each SDK request, including subsequent
catalog pages, checks that snapshot. Workers never read `bpy`.

The list is delivered before the curated model schemas finish warming. Each
successful detail becomes available independently; the final catalog event
rebuilds derived lane choices with the available details. One failed detail does
not hide the list or successful neighbors. Warmup events preserve existing
visible estimates, including the derived 3D/Edit 3D lanes. The provisional list
does not start a second bulk schema warmup. A selected model can still request its
detail independently; concurrent reads of the same model share one request. An
explicit selection or mode/task change invalidates its quote immediately, and
schema completion re-arms pricing if the estimate timer observed a missing schema.
That intent survives failed detail reads until a successful retry; switching
models does not re-price the new selection, and credential retirement or active
runtime reset clears retained intent and schema caches.
Restoring a dynamic enum's index to the same stable model id does not count as a
new selection. All events retain the credential-context identity check.

Caches are connection-local and in memory. The active path does not reuse the
prototype's unscoped disk model cache. Restart therefore requires a catalog
refresh. API-key requests use the server's credential-bound scope without requiring
team/project selection. Missing generated discovery resources in
[SDK issue #29](https://github.com/scenario-labs/scenario-sdk-python/issues/29)
are bridged by the adapter's [named extensions](../SDK_ADOPTION.md#sdk-resource-extensions).
Discovery is optional and does not infer the key's default project from the first
listed project. Opening the catalog also opens the
[credential-bound local job store](../JOB_STORAGE.md#identity-and-ownership).
Its installation-local HMAC pseudonym binds the exact selected key/secret pair to
`JobScope.account_id`; it is not a discovered server account and is never sent to
the API. The catalog's adapter carries the same scope. Credential changes retire
both selections; switching back or restarting reopens the original records.
Missing/corrupt local scope keys and storage failures block context creation with
an explicit error rather than silently replacing history. Model/schema caches
remain in memory. No shared `JobSession` or job workers are activated by opening
the store. Durable quotes, submission,
uploads and result application still need active SDK adoption under
#65. Invalidating a visible quote does not establish safe migration of those
prototype paid jobs or their late callbacks.

**Test connection** uses the same SDK context for one fresh model-list page of
size one. It runs on a worker, leaves cached models intact, and shares a pending
check across repeated clicks. The GUI/headless completion queue updates status
only for the current connection and request. In background mode, the operator
waits for its connection worker and drains that queue without a GUI timer. The
account strip shows pending, error or success independently of cached models.
Credential changes and runtime reset
discard late success and failure. The result confirms model access; it does not
derive account/project identity or activate durable jobs.

Explicit local MCP recovery calls now lazily activate the selected
[JobSession](../BLENDER_JOB_CONTEXT.md). `list_local_jobs` reads its durable
records and `cancel_prepared_job` cancels only an unsubmitted intent, guarded by
the observed revision and a current-context token. Neither sends service requests
or imports prototype jobs. The session owns a separate SDK pool with the same
credential scope and online-permission snapshot as the catalog. Credential changes
and runtime reset stop admission; in-flight receipts keep their original scope.
File loading retires the selected owner and invalidates its context token; the
next recovery call creates a fresh session against the same scoped store.
GUI ticks and the headless MCP loop reap retired sessions after work finishes.
Native model form entry points use this session for quote-bound submission, as described below.
Explicit saved-job controls and active Image transfers use the same session below.

## Active SDK cost previews and model submission

Native model forms use [ModelJobs](../../scenario/blender/model_jobs.py), a main-thread
facade over the existing selected `JobSession`, coordinator and worker pool.
It does not own another executor or persistent registry. UI and MCP prepare the
same model inputs; each quote captures the scene before a worker retrieves fresh
SDK model metadata and the exact server estimate. UI cost delivery is keyed to
the originating scene/form. Only the currently selected scene can receive a
usable quote. Completion is routed by the ticket's originating lane, not the
currently selected tab. Repricing releases only that form's former approval.

The result action **Remove background** selects a current Image background-removal
model and prepares one local file reference with default settings. It no longer
submits through the prototype manager. The user explicitly uploads the reference,
reviews the shared exact estimate and chooses Generate. Failed file/model/schema
preflight preserves the current form; a successful preparation invalidates its
old quote without canceling existing jobs or admitted uploads.

Clicking **Generate** in any model form requires its unchanged ready quote. MCP `generate`
for every model lane requires its `quote_id` and the explicitly approved `cu_cost_exact`
string as `approved_cost`. The quote also binds its lane: callers cannot turn an
Image approval into a render, material or other lane submission. A displayed float
is not used to reconstruct the price.
The facade consumes the handle before preparation; the coordinator persists an
intent and claims `submitting` before the single SDK request. Repeated clicks,
reused quote handles, changed inputs, stale origins and failed writes cannot
repeat that submission. Timeouts retain uncertain saved state without retry.
An unsuccessful UI attempt clears the ready price and requires explicit repricing;
it never silently obtains another approval. Retained MCP/UI approvals are not evicted
to admit new quotes. At capacity, new estimates are rejected until a consumed handle
can be reclaimed; repricing a UI form explicitly releases its previous approval.

GUI and headless main-thread context maintenance drains completed submissions,
polls their known remote IDs at two-second intervals and downloads successful
results through the coordinator. Saved state is projected into the existing Jobs view. This projection is
not registered with the prototype manager. Closing a panel does not stop work;
credential/file changes retire the owner while in-flight receipts stay in the
original store. Local MCP status can inspect these records after restart.
The model-job pump and explicit inspection retain scoped shared sidebar rows,
deduplicated by local job ID, with the owner's current projection replacing stale
copies. Existing rows keep their order while newly observed rows appear first;
shared rows take precedence over prototype collisions. Only prototype rows have
a fifty-row display limit. Active recovered jobs remain visible even without
creation timestamps. These display rules do not delete saved jobs or stop workers.

This is a pre-release integration slice. Image local-file/capture references
must be uploaded before pricing/submission. Local MCP now uses the
[shared reference upload path](../SDK_UPLOADS.md#active-reference-uploads);
generation forms expose **Upload reference** for typed local files and image
stills, with guarded lane/input attachment and saved inspection.
Render forms now prepare scene snapshots and optional first-frame uploads in
explicit role-bound slots. Video/audio result application is explicit; mesh and
material and in-place edit application remain separate integration.
Explicit viewport/camera clips and selected-mesh GLB uploads now share the typed
reference lifecycle through both forms and MCP. They stage private snapshots;
clips preserve the preview/scene range without duration padding, and mesh export
restores selection. Later source edits do not change an uploaded reference.
Native recovery can refresh known uploads, cancel unclaimed preparation
and clean terminal staging copies. Reusing an imported reference after restart or
form changes requires a fresh destination confirmation and invalidates old prices.
Existing Scenario asset IDs are supported. Downloaded images
are receipt-verified again on the main thread, decoded from private snapshots and
packed as image datablocks after a durable application claim. Automatic import
supports bounded RGB/RGBA PNG and scanline OpenEXR; other formats remain saved
without import. It does not assign textures or replace scene targets. A stale
origin, read/download error or uncertain application stops automatic delivery
without another generation. The [transfer policy](../RESULT_TRANSFERS.md#active-image-delivery)
names the documented CDN hosts. The Jobs panel's **Inspect saved jobs** button
and MCP `list_local_jobs` provide saved state. UI recovery buttons and
`recover_local_job` use the current context token and observed revision to refresh,
resume polling/download, cancel a known model job, reconcile interrupted download
receipts, or save a pending import receipt. These actions never submit generation.
Resuming after restart does not approve import into the new scene. **Import saved
images** captures the selected destination for confirmation. MCP uses
`prepare_result_application` followed by explicit `apply_result_application`.
Both reverify local bytes and recheck the approved scene revision before an
atomic application claim saves the destination separately from the original job
origin. An interrupted import cannot be claimed again.
Its `job_status` and `wait_for_job` return the current saved state; active jobs
advance through the same maintenance pump. `wait_for_job` waits on the HTTP worker
while the main thread remains available for delivery. It returns at completion,
review-required state or timeout, and rejects a changed credential context.
An unresumed restarted record is returned immediately.
Native model forms no longer dispatch through the prototype manager. Files,
captures and Spark preparation must finish before the final quote. Render forms
require uploaded scene/first-frame snapshots, then use the same quote and submit
path. An empty look with automatic Spark enabled remains blocked; users can enter
a look or disable automatic Spark for the default look. Non-image model jobs now
use the same durable submission, polling, download, cancellation and recovery
commands. They stop at saved `ready` results without automatically assigning
materials, importing meshes or inserting media strips. Status includes the saved
result manifest and receipt presence, without returning paths for unverified
application. Restarted display records are generic model jobs; the original lane
is not persisted. Explicit PNG/EXR import remains available by result type.
For supported video/audio, **Add video/audio strip** and MCP
`prepare_result_application(asset_id=...)` capture one asset and the selected
scene/frame for approval. The shared command verifies local receipts and claims
application before inserting one strip. Receipt retry never repeats insertion;
see [saved media application](../BLENDER_JOB_CONTEXT.md#explicit-saved-video-and-audio-application).
The same asset-selected MCP approval and **Import model** support one
self-contained GLB at the captured cursor. Import stages in a disposable
scene, preserves existing selection and packs its textures. Rigs, weights and
node/morph animation clips remain in the new group; timing uses scene FPS without
changing the current frame or timeline range. Its separate durable claim/receipt
recovery follows the same session; in-place rig/animation transfer remains open.
Saved PNG/EXR results also offer explicit World replacement, with a separate
guarded restore in the current session. Completed jobs can reuse saved results
through fresh UI/MCP approval and a separate durable local claim, preserving the
original generation outcome. Interrupted local claims block another application.
Saved texture sets also offer explicit one-mesh material-slot approval, using
[stored roles and packed material construction](../MATERIAL_APPLICATION.md).
Render-lane MCP calls use the native form preparation described below, including
uploaded inputs, prompt decoration and separate Spark approval. Do not describe this slice as
complete generation, supported release acceptance, or completion of #65.

For prototype jobs, local MCP `wait_for_job` captures a local record on the main thread and waits
on the HTTP thread. Other scene tools and the GUI pump remain available. Its
completion rechecks the manager, credentials and record identity; shutdown
interrupts the wait without cancelling or resubmitting the generation. This
responsive read does not migrate prototype jobs into the durable scoped runtime.

## Replacement components already present

| Component | Source and contract | Integration still required |
| --- | --- | --- |
| Scoped SDK commands | [sdk_adapter.py](../../scenario/core/api/sdk_adapter.py), [SDK guide](../SDK_ADOPTION.md) | Route every adopted service operation through the adapter; establish live authentication and provider contracts. |
| Shared catalog and quotes | [coordinator.py](../../scenario/core/jobs/coordinator.py), [workers.py](../../scenario/core/jobs/workers.py), [job guide](../JOB_COORDINATOR.md#shared-catalog-and-origin-bound-quotes) | Scoped current-schema reads and exact origin-bound quotes use the shared queue. Active UI/MCP catalog reads now use the SDK adapter, but their adoption of this durable coordinator/quote path still requires credential-bound local persistence and origin integration. |
| Durable intent and coordination | [store.py](../../scenario/core/jobs/store.py), [coordinator.py](../../scenario/core/jobs/coordinator.py), [job guide](../JOB_COORDINATOR.md) | Replace view/prototype-owned jobs with one application runtime for UI and MCP; complete recovery UX. |
| Worker ownership | [workers.py](../../scenario/core/jobs/workers.py) | Attach lifecycle to the application context, not a panel; integrate shutdown and delivery. |
| Origin and stale-result protection | [job_session.py](../../scenario/blender/job_session.py), [context guide](../BLENDER_JOB_CONTEXT.md) | Bind actual entry points to the selected account, scene and targets, including explicit restart recovery. |
| Bounded result downloads | [transfers.py](../../scenario/core/jobs/transfers.py), [transfer guide](../RESULT_TRANSFERS.md) | Active Image jobs use configured CDN hosts, persisted receipts and guarded image import. Explicit interrupted-download recovery verifies saved receipts under a cross-process lock without service calls. Recovery controls, orphan-file reconciliation and other lanes remain. |
| Durable application claims | [application commands](../JOB_COORDINATOR.md#durable-application-claims), [World command](../BLENDER_JOB_CONTEXT.md#explicit-saved-result-world-application) | Owner-issued verification tickets can claim the original result and persist an explicit application outcome. Optional JobSession World application binds one saved asset's decoded bytes and scene assignment to that claim. Explicit receipt retry can save or acknowledge a known completed assignment without repeating scene work; restart reconciliation, other result types, recovery UX and active UI/MCP wiring remain separate. |
| Prompt Spark commands | [SDK guide](../SDK_ADOPTION.md#prompt-spark-command-boundary), [coordinator](../JOB_COORDINATOR.md#prompt-spark-commands) | Exact SDK quotes, durable single-use submission and full-text recovery through the existing JobSession pool. New, Rewrite and Translate share native/MCP approval and unchanged-field delivery; render look preparation uses uploaded image snapshots and its own approval before the final render quote. |
| Upload commands | [upload guide](../SDK_UPLOADS.md) | Local MCP and generation-form typed files/image stills use private staging, signed S3 PUT parts and durable SDK commands on the existing workers. Guarded form attachment invalidates old prices. UI/MCP recovery survives restart; saved-reference attachment requires a matching input kind and fresh destination confirmation. Live acceptance remains. |
| Strict model forms | [forms.py](../../scenario/core/schema/forms.py) | Complete trained/custom-model discovery and verified REST routing under #97. |
| Mesh and World application | [mesh guide](../MESH_APPLICATION.md), [World guide](../WORLD_APPLICATION.md) | User-facing generation/history/apply flows under #99 and #98. |

The job lifecycle records intent before submission, binds an exact estimate to
scope and origin, and treats transport uncertainty as recoverable uncertainty.
A timeout does not authorize another paid request. Follow each component guide
for its actual state machine and tested boundaries.

## Local MCP queue lifetime

The main-thread executor in [server.py](../../scenario/mcp/server.py) admits each
queued request once before its monotonic deadline. Expiry and shutdown cancel
requests that have not started; a later GUI/headless pump or server restart cannot
execute them. Queue admission, start and shutdown are synchronized, while handlers
run without holding the admission lock. Shutdown therefore releases queued callers
without waiting for an unrelated tool to finish.

A timeout after the handler starts reports an unknown outcome. The executor neither
interrupts nor replays the handler, and a completed result wins a concurrent timeout
observation. This local boundary does not replace durable request identity or remote
job recovery, and does not make the prototype paid runtime accepted.

## Active SDK history

Cloud history uses the selected catalog connection's SDK adapter and HTTP pool.
`jobs.with_raw_response.list` reads one page at a time with inputs/results visible;
`assets.with_raw_response.retrieve` resolves at most 30 prompt previews per page.
Prompt text is local to each read, with no session-wide or cross-credential cache.
Unavailable or explicitly truncated text previews remain unresolved; an existing
local job's prompt can still supply the display text. Full text downloads remain
part of transfer integration.

The existing worker queue delivers pages to both the GUI and headless MCP.
Connection identity and request keys reject superseded results and errors;
credential retirement clears visible cloud history and its cursor. A failed read
preserves the last valid page. Empty successful pages count as loaded, duplicate
rows are suppressed, and repeated pagination cursors fail without changing the
visible page. MCP `list_generations(refresh=true)` explicitly refreshes or retries;
subsequent calls without `refresh` deliver/read the shared result. Repeated UI or
MCP refresh requests reuse a pending history read instead of starting more workers.
The MCP `refresh` argument accepts only JSON booleans; other types fail before
starting or delivering history work.

Cloud rows now identify matching jobs in the selected credential-bound store.
Those rows offer **Inspect saved jobs**, which exposes the existing recovery and
destination-approval controls. The native history import entry point rechecks
current storage even when the displayed page predates a remote acknowledgement.
MCP status and import lookup likewise prefer scoped saved records to an old
unscoped cache; ambiguous remote IDs require an explicit local request ID.
Neither path borrows the old cache's files or silently applies a saved result.
Explicit history reads cache saved remote IDs for drawing; live shared-job views
cover acknowledgements delivered after the cloud page. Drawing performs no job
database reads. Native import and MCP history/status/import responses still
recheck current storage, independently of the display snapshot. A failed saved
read disables cloud-row actions until an explicit read succeeds; switching
credentials clears the snapshot. Storage failures do not fall back to the older
import path.
MCP import also requires complete selected credentials before consulting either
store; missing credentials permit cold read-only inspection, never application.

The cloud page itself remains an in-memory browse result. A
[shared cloud adoption command](../JOB_COORDINATOR.md#adopting-a-completed-cloud-job)
can verify and save one completed model job without fabricating a local quote
or submitting generation. Native **Save for recovery** and MCP
`recover_cloud_job` share its bounded pending reads and paused saved-job view.
Completed MCP results remain bound to their owning facade independently of the
16-entry display cache. Job rows merge by request ID without periodic reordering;
shared recovery rows take precedence over legacy collisions and are exempt from
the prototype's existing 50-row limit.
Neither uses old cached files, downloads results or applies to the current scene.
The old MCP `import_result` now rejects prototype files with recovery guidance.
History rendering ignores legacy file/action projections, including a duplicate
session row, while explicit saved-result commands retain their byte verification
and destination approval. Desktop interaction and live provider acceptance remain
separate; this does not complete #65 or #68.

## Film input contracts

[Film recipe helpers](../FILM_PLAN.md) preserve data-only recipe/scene validation,
editorial timing, continuity declarations and ordered task references. Project
selection is optional; referenced outputs must match the full selected job scope.
These helpers do not submit work, create scenes or own storage.
The optional Film panel and local MCP now share task preparation/approval through
`FilmJobs`; capture/finishing and release acceptance remain to integrate.

The shared `quote_film_task` command now binds model tasks to the existing scoped
job store and quote/submission queue. Recipe and transitive task digests protect
reference reuse; atomic production/task reservation prevents another attempt
through a fresh quote after restart or uncertainty. The native `JobSession`
exposes the command with existing scene guards. `FilmJobs` binds its approval
to the saved scene recipe and production identity, then uses `ModelJobs` for
submission, polling and downloads without automatic application. Explicit upload-task association now selects an already imported
scoped upload and saves its immutable source/asset identity in the same job
database. Dependent quotes recheck that upload locally; association sends no
bytes and never replays uncertain uploads. See [durable Film tasks](../FILM_PLAN.md#durable-model-tasks).

The [native Film scene primitives](../FILM_PLAN.md#native-shot-and-timeline-primitives)
now construct complete new shot scenes and editable timelines from validated
recipes and explicit saved GLB receipts. They restore the current scene and roll
back only new data on failure. The [shared shot application command](../FILM_PLAN.md#shared-shot-application-command)
now verifies selected credential-bound task outputs, captures the unchanged recipe
scene, claims every source job before building and supports receipt-only recovery.
The [native/MCP shot controls](../FILM_PLAN.md#native-and-mcp-shot-controls) expose
source inspection, local verification, separate build approval and recovery over
that command. The maintenance pump owns verification delivery; draw reads cached
status. Timeline approval, capture and finishing remain to integrate.

## Shared MCP render preparation

Local MCP `render_form` edits and inspects the native Render Image/Video form,
explicitly prepares its scene/first-frame uploads, and removes only a freshly
identified reference. The existing upload session owns work after the tool
returns. Model changes require explicit removal of previous references; an
occupied or uncertain slot cannot start another upload implicitly.

Render `estimate_cost` and `generate` use the same native request builder,
including prompt decoration and uploaded input ordering. Callers omit raw model
parameters and configure the form first. Empty automatic looks require the
existing separate Spark quote/approval/delivery before the final render price.
No capture, upload or paid Spark call occurs during render generation. Result
application remains explicit. See the [MCP sequence](../MCP.md#preparing-render-image-and-render-video)
and [context contract](../BLENDER_JOB_CONTEXT.md#mcp-render-form-commands).
This completes this local command integration, not live or desktop acceptance.

## Where to make a change

- Pure request, schema, persistence and scene-planning logic belongs under
  `scenario/core/`, without importing `bpy`.
- Blender state, operators and main-thread application belong under
  `scenario/blender/`; see [Blender boundaries](blender.md).
- Protocol/transport code belongs under `scenario/mcp/`; scene tools still obey
  the Blender main-thread rule.
- [Unit tests](../../tests/unit/) exercise pure logic; [native tests](../../tests/blender/)
  exercise the installed package. [Smoke scripts](../../tests/smoke/) are opt-in
  paid work, never part of documentation maintenance.
- Build, installation and isolation are owned by [tools/](../../tools/) and
  [Makefile](../../Makefile), not a second packaging path.

## Acceptance boundaries

[#64](https://github.com/scenario-labs/blender-plugin/issues/64) owns consolidated
adoption, [#65](https://github.com/scenario-labs/blender-plugin/issues/65) shared
runtime integration, [#66](https://github.com/scenario-labs/blender-plugin/issues/66)
the views, [#67](https://github.com/scenario-labs/blender-plugin/issues/67)
future OAuth authentication (deferred for this release) and [#68](https://github.com/scenario-labs/blender-plugin/issues/68)
integrated release acceptance. Offline serialization tests and source inspection
do not satisfy their live or native acceptance criteria.

The current release follows the [API-key release plan](../maintenance/release-plan.md).
OAuth deferral does not relax credential precedence, project scope or paid-job safety.

## Saved 3D edit application boundary

The [verified saved-mesh command](../MESH_APPLICATION.md#captured-source-and-verified-saved-mesh-command)
connects receipt-checked GLB import to explicit remesh/UV/retexture/parts and
[compatible rig attachment](../MESH_APPLICATION.md#attach-a-returned-rig). `JobSession.apply_recovered_mesh` binds one selected asset to a captured
source object and a durable original or local-reuse claim. It rejects changed
geometry/context, ambiguous multi-mesh results and uncertain rollback, while
known receipt retry only saves persistence. The caller supplies an explicit
Blender-imported-scene-to-source-local matrix, edit policy and Keep original choice.
Native **Apply mesh edit** and MCP `purpose: mesh_edit` now prepare the same
captured target, explicit scene/local placement, policy and Keep original review.
No service operation or second executor is added. The captured-source flow below
connects export metadata to this review. Provider mapping contracts and remaining
edit policies still need integration; this is not full #99 or release acceptance.

## Mesh upload source identity

Mesh snapshot uploads preserve [export provenance](../SDK_UPLOADS.md#captured-mesh-export-provenance)
with their durable upload intent: exact exported bytes, source session IDs,
base-mesh fingerprints, world matrices and exporter settings. Export rechecks its
captured source before worker admission; staging rejects a mismatched file hash.
Multiple sources remain explicit without guessing a primary mesh. Upload schema 2
upgrades existing records transactionally without resetting uncertain claims.

The shared quote coordinator binds captured uploads to typed 3D inputs and
persists their source snapshots in
[generation intents](../JOB_STORAGE.md#captured-mesh-inputs-in-generation-intents).
This does not change the generation origin or authorize automatic mesh replacement. Provider alignment, operation-specific policies and live acceptance
remain separate. No SDK request or dependency changes are introduced.


## Captured mesh source application

Native **Apply to captured source** and MCP `purpose: mesh_source` connect
persisted quote/input provenance to an unchanged live source retained during
export. They ignore active selection and feed the existing explicit mesh review
and durable application path. Ordinary destination review stays available after
restart; saved IDs alone cannot recreate original-source ownership. See
[the mesh contract](../MESH_APPLICATION.md#applying-to-the-captured-mesh-source).
Multi-source ambiguity, unsupported rigs/modifiers, provider coordinate contracts,
remaining edit policies and global undo still limit #99 acceptance.
