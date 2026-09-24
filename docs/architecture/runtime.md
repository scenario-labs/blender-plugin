# Runtime map and integration status

The extension package is [scenario/](../../scenario/). It currently contains the
active prototype runtime and separately tested components for its replacement.
The supported minimum in the [manifest](../../scenario/blender_manifest.toml)
is Blender 5.0; dependency and runtime acceptance have separate gates.

## Active entry points

| Responsibility | Source | Current behavior |
| --- | --- | --- |
| Registration | [registry.py](../../scenario/blender/registry.py) | Registers properties, panels, operators, composer, pump and local server integration. The `scenario_blender` headless command serves local MCP on the main thread. |
| UI lifetime and state | [runtime.py](../../scenario/blender/runtime.py) | Creates the prototype `ScenarioClient`, `Catalog` and `JobManager`; owns process-wide UI/MCP state. |
| UI generation | [generation.py](../../scenario/blender/generation.py) | Prepares the current lane and submits through the prototype manager. |
| Main-thread application | [pump.py](../../scenario/blender/pump.py) | Drains prototype events and applies results to Blender. GUI timer handling differs from headless execution. |
| Local MCP | [server.py](../../scenario/mcp/server.py), [tools_scenario.py](../../scenario/mcp/tools_scenario.py), [mcp_service.py](../../scenario/blender/mcp_service.py) | Queues scene tools for main-thread execution; service tools still call the prototype runtime. |
| Credentials | [config.py](../../scenario/core/config.py), [prefs.py](../../scenario/prefs.py) | Credentials default to the saved Blender pair; environment credentials require explicit selection and cannot mix with preferences. OAuth is deferred; shared runtime scope/project integration remains #65. |

These are source-inspection findings. Do not infer UI/MCP parity from the shared
adapter's test coverage, or promote prototype transport usage into an approved
exception to the mandatory SDK policy in [AGENTS.md](../../AGENTS.md).

## Replacement components already present

| Component | Source and contract | Integration still required |
| --- | --- | --- |
| Scoped SDK commands | [sdk_adapter.py](../../scenario/core/api/sdk_adapter.py), [SDK guide](../SDK_ADOPTION.md) | Route every adopted service operation through the adapter; establish live authentication and provider contracts. |
| Shared catalog and quotes | [coordinator.py](../../scenario/core/jobs/coordinator.py), [workers.py](../../scenario/core/jobs/workers.py), [job guide](../JOB_COORDINATOR.md#shared-catalog-and-origin-bound-quotes) | Current-schema reads and exact origin-bound quotes use the shared queue; active UI/MCP call sites remain to adopt them. |
| Durable intent and coordination | [store.py](../../scenario/core/jobs/store.py), [coordinator.py](../../scenario/core/jobs/coordinator.py), [job guide](../JOB_COORDINATOR.md) | Replace view/prototype-owned jobs with one application runtime for UI and MCP; complete recovery UX. |
| Worker ownership | [workers.py](../../scenario/core/jobs/workers.py) | Attach lifecycle to the application context, not a panel; integrate shutdown and delivery. |
| Origin and stale-result protection | [job_session.py](../../scenario/blender/job_session.py), [context guide](../BLENDER_JOB_CONTEXT.md) | Bind actual entry points to the selected account, scene and targets, including explicit restart recovery. |
| Bounded result downloads | [transfers.py](../../scenario/core/jobs/transfers.py), [transfer guide](../RESULT_TRANSFERS.md) | Coordinator/worker result commands now fetch SDK metadata, persist manifests/receipts and verify downloads. Production storage policy, interrupted-worker reconciliation and UI/application hand-off remain. |
| Upload commands | [upload guide](../SDK_UPLOADS.md) | Private source staging, signed PUT parts and durable SDK upload commands share the coordinator/workers; production policy, recovery UI and active entry-point wiring remain. |
| Strict model forms | [forms.py](../../scenario/core/schema/forms.py) | Complete trained/custom-model discovery and verified REST routing under #97. |
| Mesh and World application | [mesh guide](../MESH_APPLICATION.md), [World guide](../WORLD_APPLICATION.md) | User-facing generation/history/apply flows under #99 and #98. |

The job lifecycle records intent before submission, binds an exact estimate to
scope and origin, and treats transport uncertainty as recoverable uncertainty.
A timeout does not authorize another paid request. Follow each component guide
for its actual state machine and tested boundaries.

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
