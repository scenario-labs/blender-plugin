# Runtime map and integration status

The extension package is [scenario/](../../scenario/). It uses the scoped SDK runtime for generation and recovery, alongside retained
local helpers and separately tested application components.
The supported minimum in the [manifest](../../scenario/blender_manifest.toml)
is Blender 5.0; dependency and runtime acceptance have separate gates.

## Active entry points

| Responsibility | Source | Current behavior |
| --- | --- | --- |
| Registration | [registry.py](../../scenario/blender/registry.py) | Registers properties, panels, operators, composer, pump and local server integration. The `scenario_blender` headless command serves local MCP on the main thread. |
| UI lifetime and state | [runtime.py](../../scenario/blender/runtime.py) | Owns the credential-bound SDK catalog and process-wide UI/MCP state; native form quote/submission and Film task/capture/composition controls use the selected `JobSession`; local Film final assembly/export remain to integrate. |
| UI generation | [generation.py](../../scenario/blender/generation.py) | Every native model form consumes a lane-bound session quote before durable submission; unfinished file/capture/Spark inputs block final pricing and submission. |
| Main-thread application | [pump.py](../../scenario/blender/pump.py) | Drains SDK catalog events and maintains shared job delivery. Unbound prototype completions cannot apply results. GUI timer handling differs from headless execution. |
| Local MCP | [server.py](../../scenario/mcp/server.py), [tools_scenario.py](../../scenario/mcp/tools_scenario.py), [mcp_service.py](../../scenario/blender/mcp_service.py) | Queues scene tools for main-thread execution; model listing/schema use the same SDK catalog as the UI, all model generation lanes use the shared session; prototype records remain local snapshots. |
| Credentials | [config.py](../../scenario/core/config.py), [prefs.py](../../scenario/prefs.py) | Credentials default to the saved Blender pair; environment credentials require explicit selection and cannot mix with preferences. Optional project selection scopes both catalog and shared jobs; OAuth and live permission acceptance remain separate. |

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

The same connection also exposes core reads for later trained-model routing
([#97](https://github.com/scenario-labs/blender-plugin/issues/97)). Explicit bulk
model summaries are read at most once per connection, share pending reads, are
cached apart from form schemas and are cleared on retirement. Trained records
from the private list and public LoRAs are classified from REST fields; a
malformed `type` is unsupported rather than an exception. No UI, MCP or catalog
load calls these reads yet. Lane lists and the picker keep their former
exclusion of LoRAs, compositions and other trained types, and still list a
private custom model that reaches them.
See [trained-model catalog reads](../SDK_ADOPTION.md#trained-model-catalog-reads).

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
remain in memory. Opening the store alone does not activate a `JobSession` or
job workers. Quote, submission, upload and recovery entry points lazily activate
the shared session described below. They use the same selected scope while the
catalog retains its own metadata pool. Prototype jobs are not migrated or resumed;
[local prototype records](#local-prototype-records) remain read-only snapshots.

**Test connection** uses the same SDK context for one fresh model-list page of
size one. It runs on a worker, leaves cached models intact, and shares a pending
check across repeated clicks. The GUI/headless completion queue updates status
only for the current connection and request. In background mode, the operator
waits for its connection worker and drains that queue without a GUI timer. The
account strip shows pending, error or success independently of cached models.
Credential changes and runtime reset
discard late success and failure. The result confirms model access; it does not
derive account/project identity or activate durable jobs. Failures carry the
adapter's fixed status text for every SDK request: HTTP 401 and 403 ask to check
the selected key and secret, a 403 names the Project ID only when that request
carried the override, and 429 asks for a later retry. Other statuses keep the
generic HTTP text; no message includes response bodies, URLs or identifiers.

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
Explicit saved-job controls and result transfers across model lanes use the same session below.

## Optional project selection

Preferences expose an explicit optional Project ID for either credential source.
`runtime.project_id` trims surrounding whitespace and treats blank as no override;
the shared JobScope validates nonempty IDs before storage or SDK construction.
The selected value is passed to `open_credential_store` and therefore to both
catalog and job SDK pools. Neither discovery nor a guessed server identity is
required. This uses the existing SDK `project_id` query configuration unchanged.

Project changes follow the same retirement path as credential changes: clear
catalog/schema/history/quote projections, deactivate the old session and reject
late callback authority. In-flight receipts remain in their original scoped store.
Returning to a project reopens its records with fresh session approval identity;
normalized-equivalent edits keep the current session. Read-only history and Film
controls check both credentials and project without mutating state in drawing.
Prototype jobs have no reliable credential or project ownership. Their automatic
service engine is retired for every selection, including the default project;
clearing the override cannot resume it. See [local prototype records](#local-prototype-records).
This does not migrate prototype data or establish live project permissions,
discovery or complete release acceptance.

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
Render forms prepare scene snapshots and optional first-frame uploads in
explicit role-bound slots. Saved video/audio, GLB models, material maps and supported
mesh edits use explicit destination approval through the shared session; their
format and target limits are described below and in the application guides.
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
supports bounded 8-/16-bit grayscale/RGB/RGBA PNG and scanline OpenEXR; other formats remain saved
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
Saved PNG, JPEG and OpenEXR results, including `image/aces`, also offer explicit
World replacement, with a separate guarded restore in the current session.
Application refuses a file whose container differs from its saved media type;
[World application](../WORLD_APPLICATION.md#accepted-local-files) lists the
accepted variants. Completed jobs can reuse saved results
through fresh UI/MCP approval and a separate durable local claim, preserving the
original generation outcome. Interrupted local claims block another application.
Saved texture sets also offer explicit one-mesh material-slot approval, using
[stored roles and packed material construction](../MATERIAL_APPLICATION.md).
Render-lane MCP calls use the native form preparation described below, including
uploaded inputs, prompt decoration and separate Spark approval. Do not describe this slice as
complete generation, supported release acceptance, or completion of #65.

## Local prototype records

The catalog worker manager retains read-only local registry access for saved
media tools and status inspection. It has no client factory, paid submission,
raw estimate, polling, upload, download or automatic resume methods. Starting it
or changing online access, credentials or project does not modify old records or
send requests for them. New generation and remote recovery belong to the scoped
SDK JobSession. No second job engine or prototype migration is provided.

Local MCP `job_status` reads the saved prototype snapshot. `wait_for_job` returns
that snapshot immediately, even for a nonterminal record, with guidance to use
`recover_cloud_job` under explicitly selected credentials. It does not imply the
saved remote status is current. Cold lookups need no manager or complete credentials.
Known cloud jobs can be recovered through the SDK; applying their results still
requires a separately approved destination. Local video insertion and audio
preview continue to use their existing explicit file controls.

An unbound `job_done` event may project a local status row but cannot invoke an
image, material, mesh, media or render-lane application callback. It displays
recovery guidance instead. Shared delivery retains its own scope, receipt and
scene guards. The removed prototype engine tests are replaced by read-only
startup/pump and late-event regressions; shared submission, uncertainty,
transfers and deferred wait tests remain. This retirement does not establish
live provider acceptance or complete retained-capability acceptance. The
[service operation inventory](../SDK_ADOPTION.md#service-operation-inventory)
records removal of the unused prototype service helpers.

## Shared runtime components

The table describes implemented connections in this checkout. It does not certify
live provider behavior, physical interaction or the release acceptance gates in
[#68](https://github.com/scenario-labs/blender-plugin/issues/68). See the
[candidate evidence](../maintenance/release-acceptance.md) for tested artifacts
and environments.

| Component | Current connection | Remaining boundary |
| --- | --- | --- |
| Scoped SDK commands | [SDKAdapter](../../scenario/core/api/sdk_adapter.py) serves the selected catalog and job pools. Adopted service operations and tracked exceptions are listed in the [SDK guide](../SDK_ADOPTION.md#service-operation-inventory). | Live authentication/provider acceptance; unsupported operations are not implied by SDK availability. |
| Catalog and quotes | [SDKCatalog](../../scenario/core/api/sdk_catalog.py) owns model browsing; [ModelJobs](../../scenario/blender/model_jobs.py) routes UI/MCP exact quotes through the selected JobSession coordinator and workers. | Catalog browsing alone creates no quote or spending approval. Full retained-lane live acceptance remains. |
| Durable intent and coordination | [JobSession](../../scenario/blender/job_session.py) uses the scoped [store](../../scenario/core/jobs/store.py) and [coordinator](../../scenario/core/jobs/coordinator.py). Model forms, workflows, Film generation and recovery share this application owner. | Uncertain submissions require reconciliation; they cannot be retried as new paid requests. |
| Worker ownership | [RuntimeState](../../scenario/blender/runtime.py) selects one active session; its [workers](../../scenario/core/jobs/workers.py) outlive panel closure. Retirement stops admission while old owners retain in-flight persistence and cleanup. | Retired owners cannot deliver into a replacement connection or scene; cleanup failures may retain ownership for retry. |
| Origin and stale-result protection | [JobSession](../../scenario/blender/job_session.py) binds entry points to the selected credentials/project and captured scene/target. Restart recovery uses fresh context and destination approval. | Saved names or IDs cannot restore live scene authority; see the [context contract](../BLENDER_JOB_CONTEXT.md). |
| Result downloads | [ModelJobs](../../scenario/blender/model_jobs.py) drives saved manifests, bounded transfers and explicit interrupted-download recovery for model lanes. [Transfers](../RESULT_TRANSFERS.md) retain verified receipts and configured storage hosts. | Only admitted Image jobs automatically apply supported images to their original scene; other model results need explicit destination approval. Unsupported formats and uncertain states remain saved for inspection. |
| Application claims | Native [saved-job controls](../../scenario/blender/job_recovery.py) and [MCP result commands](../MCP.md) prepare and apply image, media, GLB, material, World and supported mesh-edit destinations through ModelJobs/JobSession. Claims precede scene mutation; known receipt retries do not repeat it. | Restarted uncertain claims require inspection. Format, target, rollback and undo limits differ by application; no atomic blend-file save is promised. |
| Prompt Spark | [Prompt commands](../SDK_ADOPTION.md#prompt-spark-command-boundary) use exact quotes, durable submission and complete text recovery on the shared workers. Native/MCP New, Rewrite and Translate require unchanged-field approval; render preparation has a separate Spark approval. | Live provider acceptance remains; Spark approval does not authorize the subsequent render generation. |
| Uploads | [Reference uploads](../SDK_UPLOADS.md) use private staging, signed storage transfers and durable SDK commands on the shared workers. Native/MCP recovery and saved-reference attachment require the selected scope and fresh destination approval. | Workflow direct-file upload integration and live upload/result journeys remain open. |
| Model forms | [Schema forms](../../scenario/core/schema/forms.py) validate adopted model inputs before shared pricing and submission. | Trained/custom-model discovery and verified routing remain under #97. |
| Mesh and World | [Mesh](../MESH_APPLICATION.md) and [World](../WORLD_APPLICATION.md) application have explicit UI/MCP destination flows for supported saved results. | Provider-specific mesh contracts under #99 and panoramic generation under #98 remain incomplete; local application does not close them. |

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
job recovery. Prototype records remain local snapshots and cannot authorize new
service work or result application.

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

Each page keeps only model inference (`custom`) jobs; uploads, workflow runs and
mesh preview renders are skipped locally, so a page can list fewer rows than it
read, or none. The panel draws every loaded row, keeps **Load older** while a
cursor remains, and says so when a page listed no generation. MCP
`list_generations` reports rows beyond its `limit` as `more_loaded` and a
remaining cursor as `older_page`; `older=true` requests that page through the
same cursor and pending-read rules as **Load older**, and retries a failed older
read. It accepts only JSON booleans and cannot be combined with `refresh`. A
failed older read sets a separate older-page error and keeps the loaded rows and
cursor, as **Load older** does: later MCP calls return those rows with
`older_error` and a retry note, and only a repeated cursor points to `refresh=true`.

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
`FilmJobs`; capture uses that session below, while finishing and release acceptance remain.

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
status. `JobSession.film_timeline` now supplies bounded explicit local shot
selection and single-use timeline approval through native controls and MCP.
It rechecks live scenes and captured revisions and creates a new editable
scene-strip sequence without importing results or changing saved jobs.
The [local capture foundation](../FILM_PLAN.md#local-capture-foundation) now exports
an immutable blend snapshot on the main thread and renders stills or exact-range
MP4s in an owned offline Blender child. Its bpy-free worker primitive checks
optional installed media tools and cleans child profiles on success or failure.
The [shared capture command](../FILM_PLAN.md#shared-capture-and-upload-approval)
now binds native/MCP approval to both recipe and shot revisions, queues one local
render through the existing workers and drains it from the maintenance pump.
Retirement/cancellation stops the child, while cleanup waits for workers to join.
Separate upload approval verifies the captured content hash during staging and
then uses the existing reference lifecycle. This adds no worker pool or job store.
Desktop interaction, finishing/export and release acceptance remain separate.

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

## Composition preparation component

The [unpaid Film composition helpers](../FILM_PLAN.md#unpaid-composition-drafts)
can prepare and revalidate final/previs task drafts from scoped saved outputs.
They preserve cut and audio timing without mutating the recipe, reserving a job
or making service requests. The existing `JobSession.prepare_film_composition` and worker pool provide
[receipt-bound media measurement](../FILM_PLAN.md#verified-media-preparation),
current-source rechecks and guarded delivery. The session also exposes
[composition quoting](../FILM_PLAN.md#quoted-composition-generation) with saved-source
checks through the existing exact-price preparation and single-dispatch claim.
[Native/MCP composition controls](../FILM_PLAN.md#native-and-mcp-composition-controls)
now retain the draft and original recipe for separate price and generation
approval. The existing `FilmJobs` owner maintains reviews and uses `ModelJobs` to
save the master without changing the recipe. Declared master IDs remain visible
through local inspection after restart. Synthetic native composition interaction
passes on macOS Blender 5.1.2; see [the evidence and limits](../UI_STYLE.md#film-composition-controls).
Live provider and other OS/DPI acceptance remain pending.
The [native review primitive](../FILM_PLAN.md#native-saved-media-review-primitive)
now assembles independent receipt-bound picture/audio sequences. Its
[shared command layer](../FILM_PLAN.md#shared-native-review-preparation-and-application)
prepares copies on existing workers, then separately checks original recipe/scene
approval and durable generated-source application claims. Native/MCP presentation
and approval controls still need wiring. Portable export remains unimplemented.


## Active workflow commands

Local MCP `list_workflows` and `workflow_schema` queue SDK metadata reads on the
selected JobSession. Exact-task ownership distinguishes metadata from saved job
completions, and delivery still checks the originating scene and connection.
`estimate_workflow` and `run_workflow` reuse ModelJobs' bounded quote ownership,
durable submission and polling; the issued estimate determines the SDK operation.
An explicit operation tag prevents a model approval from authorizing a workflow
or vice versa. Failed workflow quotes release their retained approval capacity.

The original parameters, normalized payload/defaults and exact decimal price are
separate fields. Approval consumes the handle before persistence and requires
unchanged input, scene and connection. Results stay saved for explicit application;
there is no workflow-specific worker pool, store or automatic import. Native
workflow controls below now share those commands. Interactive nodes, general
cancellation and live output acceptance remain open under #64/#65/#66/#68.


## Explicit expanded native view

[studio.py](../../scenario/blender/studio.py) registers an explicitly invoked
native popup and unsaved WindowManager navigation. The header entry point is
[popover.py](../../scenario/blender/popover.py); no lifecycle hook invokes it.
It reuses existing panel drawing and operators for Create, Film, Jobs, Results
and Connection, retaining scene-owned forms and application-owned sessions.
Closing the popup owns no worker teardown or job cancellation.

Composer synchronization retains its source scene. Opening Studio flushes a
focused prompt only into that unchanged scene/lane/form; navigation itself does
not change scene data. Installed checks cover quote identity under native owner
tagging, read-only drawing and continued jobs. The composer commits on blur and
passes the same outside click to native controls. Offline desktop evidence covers
first-click Studio opening, Unicode prompt edits, populated-form scrolling,
quote-preserving navigation, continued saved-job polling, small-window fit,
Escape and viewport return. Alternate-DPI/IME acceptance, workflow and Library
interaction and complete #66 remain pending.

## Native workflow controls

[workflow_controls.py](../../scenario/blender/workflow_controls.py) owns only
scene form data and session-bound UI projections. Explicit catalog/detail actions
use `JobSession.workflow_metadata`; the application maintenance pump drains them
on the main thread. Changed scene/form snapshots reject late input-load and price
delivery. Catalog lists can instead use `deliver_workflow_catalog`, which consumes
only an issued listing from the active session and grants no scene/form authority.
Unrelated form edits therefore do not reject native catalog refreshes. The form
persists its raw schema and reconstructs dynamic choices after reopening without
network access or mutation during drawing.

Pricing and confirmation use the existing `ModelJobs.quote_workflow` and
`submit_workflow` commands. Native and MCP entry points share the same quote
registry, exact-price check, operation tag, durable submission and results.
The confirmation shows normalized payload values, including service defaults.
Credential/project retirement discards the UI controller with the shared owner;
file-load retirement removes approval handles while saved scene inputs survive.
Closing Studio owns no cancellation or teardown. No new transport, store or
worker pool is introduced. Interactive nodes, general workflow cancellation,
integrated workflow reference upload and physical/live acceptance remain separate.

The 32-entry UI projection cache reclaims idle entries under pressure, discarding
any unused price but preserving saved scene inputs and independently owned jobs.
Pending reads/quotes are never evicted. Required-field inclusion uses the same
parsed `required_always` rules as model forms.

## Shared asset library reads

`JobSession.asset_library` admits one list/search request to the existing worker
pool and records exact-task metadata ownership separately from saved-job results.
The coordinator uses the selected SDK adapter and checks admission around the
read. Main-thread delivery consumes the issued completion and checks its scene
and session; retirement cannot route metadata into a replacement connection.

Local MCP `list_assets` and `search_assets` expose bounded pages with explicit
continuation. Their projection omits signed download URLs, indexed previews and
account identifiers. Reads do not initialize ModelJobs, persist generation jobs
or grant download/application authority. Native Library controls use these same
reads. Collection/tag editing and live acceptance remain separate.

## Native Library projection and attachment

[library_view.py](../../scenario/blender/library_view.py) retains one bounded page
and at most 128 continuation positions, with explicit refresh/search/navigation.
Its filters are unsaved WindowManager properties. The runtime maintenance pump
uses `deliver_asset_library` to consume only owned library metadata from the active
session without granting scene application authority. This permits unrelated
scene edits during a read; MCP retains its existing scene-bound delivery contract.
Both surfaces use the same URL-free metadata projection in `core/api/library.py`.

Reference confirmations capture the original scene, model, lane, input and complete
reference destination. Weakly held approval identity and fresh destination checks
prevent forged/repeated/stale application. Display names are captured at review
time; drawing does not dereference a removed scene. Attachment adds only a matching,
unoccupied model reference, preserves existing slots, records the selected scope,
and invalidates the old price. It does not start a transfer or paid submission.
The existing persisted reference-scope guard applies after reopening as well.
Organization mutations and physical/live acceptance remain outside this UI layer.
No new SDK transport, worker pool or job store is added.

## Workflow Library reference bindings

[workflow_references.py](../../scenario/blender/workflow_references.py) prepares
choices for the loaded workflow form. The Library owner holds their single-use
identities; confirmation checks the captured scene origin, full form signature,
selected scope and proposed value before mutation. Model and workflow targets
share catalog reads without introducing another service client or worker owner.

`core.schema.forms.append_file_reference` validates one proposed file edit,
including kind, duplicate IDs, capacity, types and allowed values. It defers array
minimums and unrelated required inputs while the artist is filling the form;
existing complete validation remains authoritative before a quote/submission.
A Library-managed input persists its scope digest and canonical value. The native
parameter builder rejects changed or cross-connection marked inputs; disabling
an input omits it while preserving its binding. The form signature includes that
binding, so attachment/clearing invalidates a prior approval even without a native
RNA edit event. Explicit clearing verifies the original form and retains the
existing unchecked-input/default semantics. Direct workflow uploads, interactive
nodes, general cancellation and physical/live acceptance remain separate.
