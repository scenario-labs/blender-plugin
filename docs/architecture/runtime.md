# Runtime map and integration status

The extension package is [scenario/](../../scenario/). It currently contains the
active prototype runtime and separately tested components for its replacement.
The supported minimum in the [manifest](../../scenario/blender_manifest.toml)
is Blender 5.0; dependency and runtime acceptance have separate gates.

## Active entry points

| Responsibility | Source | Current behavior |
| --- | --- | --- |
| Registration | [registry.py](../../scenario/blender/registry.py) | Registers properties, panels, operators, composer, pump and local server integration. The `scenario_blender` headless command serves local MCP on the main thread. |
| UI lifetime and state | [runtime.py](../../scenario/blender/runtime.py) | Owns the credential-bound SDK catalog and process-wide UI/MCP state; generation still uses the prototype `ScenarioClient` and `JobManager`. |
| UI generation | [generation.py](../../scenario/blender/generation.py) | Prepares the current lane and submits through the prototype manager. |
| Main-thread application | [pump.py](../../scenario/blender/pump.py) | Drains prototype events and applies results to Blender. GUI timer handling differs from headless execution. |
| Local MCP | [server.py](../../scenario/mcp/server.py), [tools_scenario.py](../../scenario/mcp/tools_scenario.py), [mcp_service.py](../../scenario/blender/mcp_service.py) | Queues scene tools for main-thread execution; model listing/schema use the same SDK catalog as the UI, while other service tools still call the prototype runtime. |
| Credentials | [config.py](../../scenario/core/config.py), [prefs.py](../../scenario/prefs.py) | Credentials default to the saved Blender pair; environment credentials require explicit selection and cannot mix with preferences. OAuth is deferred; shared runtime scope/project integration remains #65. |

These are source-inspection findings. Do not infer UI/MCP parity from the shared
adapter's test coverage, or promote prototype transport usage into an approved
exception to the mandatory SDK policy in [AGENTS.md](../../AGENTS.md).

## Active SDK catalog

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
refresh. Authoritative account/project discovery remains blocked by
[SDK issue #29](https://github.com/scenario-labs/scenario-sdk-python/issues/29);
no account identity is derived from credentials and no shared `JobSession` or
durable account store is activated by catalog reads. Durable quotes, submission,
uploads, history and result application still need active SDK adoption under
#65. Invalidating a visible quote does not establish safe migration of those
prototype paid jobs or their late callbacks.

## Active SDK cost previews

UI and MCP cost previews use the same connection and cached schema as catalog
reads. The adapter validates model inputs and retains the exact decimal cost,
payload and response bytes. UI requests capture nested inputs before starting a
worker; unique request keys distinguish scenes and successive edits. Delivery is
bound to the original scene object, so copied or deleted scenes cannot receive a
late preview. Main-thread delivery rejects retired connections and superseded forms. Current previews are
retained in memory; Blender's float property is only their existing display value.

MCP prepares inputs on the main thread, performs the SDK dry run on its HTTP
request thread, and queues delivery back to the main thread to recheck credentials.
The response includes `cu_cost_exact` as a decimal string alongside the existing
numeric `cu_cost` and cost details. Missing or malformed prices fail instead of
becoming zero. These reads do not upload references, persist jobs, approve spending
or establish UI/MCP paid-submission parity. The legacy manager estimate method
remains only for historical smoke scripts.

Local MCP `wait_for_job` captures a local record on the main thread and waits
on the HTTP thread. Other scene tools and the GUI pump remain available. Its
completion rechecks the manager, credentials and record identity; shutdown
interrupts the wait without cancelling or resubmitting the generation. This
responsive read does not migrate prototype jobs into the durable scoped runtime.

## Replacement components already present

| Component | Source and contract | Integration still required |
| --- | --- | --- |
| Scoped SDK commands | [sdk_adapter.py](../../scenario/core/api/sdk_adapter.py), [SDK guide](../SDK_ADOPTION.md) | Route every adopted service operation through the adapter; establish live authentication and provider contracts. |
| Shared catalog and quotes | [coordinator.py](../../scenario/core/jobs/coordinator.py), [workers.py](../../scenario/core/jobs/workers.py), [job guide](../JOB_COORDINATOR.md#shared-catalog-and-origin-bound-quotes) | Scoped current-schema reads and exact origin-bound quotes use the shared queue. Active UI/MCP catalog reads now use the SDK adapter, but their adoption of this durable coordinator/quote path still requires authoritative identity. |
| Durable intent and coordination | [store.py](../../scenario/core/jobs/store.py), [coordinator.py](../../scenario/core/jobs/coordinator.py), [job guide](../JOB_COORDINATOR.md) | Replace view/prototype-owned jobs with one application runtime for UI and MCP; complete recovery UX. |
| Worker ownership | [workers.py](../../scenario/core/jobs/workers.py) | Attach lifecycle to the application context, not a panel; integrate shutdown and delivery. |
| Origin and stale-result protection | [job_session.py](../../scenario/blender/job_session.py), [context guide](../BLENDER_JOB_CONTEXT.md) | Bind actual entry points to the selected account, scene and targets, including explicit restart recovery. |
| Bounded result downloads | [transfers.py](../../scenario/core/jobs/transfers.py), [transfer guide](../RESULT_TRANSFERS.md) | Coordinator/worker result commands now fetch SDK metadata, persist manifests/receipts and verify downloads. Production storage policy, interrupted-worker reconciliation and UI/application hand-off remain. |
| Durable application claims | [application commands](../JOB_COORDINATOR.md#durable-application-claims), [World command](../BLENDER_JOB_CONTEXT.md#explicit-saved-result-world-application) | Owner-issued verification tickets can claim the original result and persist an explicit application outcome. Optional JobSession World application binds one saved asset's decoded bytes and scene assignment to that claim; other result types, recovery UX and active UI/MCP wiring remain separate. |
| Upload commands | [upload guide](../SDK_UPLOADS.md) | Private source staging, signed PUT parts and durable SDK upload commands share the coordinator/workers. Public scoped inspection and optional JobSession forwarding preserve captured origins and guarded delivery; production policy, recovery UI and active entry-point wiring remain. |
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
