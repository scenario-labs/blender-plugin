# Local MCP reference

## Overview

`scenario-blender` connects an agent to the open Blender scene and generation
into that scene. The hosted server at `mcp.scenario.com` provides platform-wide
operations such as collections, training, workflows and usage. Connect either
or both according to the task; they have separate authentication and capabilities.

The local server accepts MCP JSON-RPC over HTTP at
`http://127.0.0.1:9876/mcp` by default. It starts with the extension in a GUI
session when Blender's **Allow Online Access** is on. The **MCP Port** preference
sets the first port; if busy, the server tries the next three. Copy the actual
URL from **Scenario > Agents (MCP)**. An authenticated GET on `/mcp` returns 405:
use POST for tool calls; the server does not provide an SSE stream.

The extension is experimental. The [runtime map](architecture/runtime.md)
separates implemented helpers from active UI/MCP integration. A tool description
is guidance for the connected agent, not a server-enforced spending approval.
Every `generate` model lane now requires a session-owned quote and the exact
approved cost. Native generation forms now use the same shared quotes and
submission boundary; pending files, captures and Prompt Spark preparation must
finish before a usable final quote.

`list_local_jobs` inspects the separate credential-scoped durable store and returns
saved costs, revisions and suggested recovery actions without contacting Scenario.
It includes all new MCP and native form model submissions,
but does not import prototype records or refresh remote jobs.
`cancel_prepared_job` cancels only an unsubmitted durable intent, using the context
token and revision from inspection. A reset, file load or credential switch invalidates that
token. Claimed or uncertain submissions require reconciliation, never blind retry.

`recover_local_job` uses that token and the observed revision for explicit refresh,
resume/download, known model-job cancellation, interrupted-download reconciliation
or pending import-receipt retry. Resuming a restarted job does not import it into
the current scene. Shared `wait_for_job` waits without blocking Blender's main
thread and returns when delivery finishes, needs review, or reaches its timeout.
See [job contexts](BLENDER_JOB_CONTEXT.md) for lifetime and remaining integration.

To import recovered PNG/EXR results, call `prepare_result_application` with the
current context, request and revision, then show its destination and image list
to the user. After approval, `apply_result_application` consumes the returned
handle once. Scene/file changes invalidate it. Verification and the durable
application claim precede image import; an interrupted import is never retried
automatically. These commands spend no credits and make no service requests.

## Typed local references

`upload_reference` accepts a chosen local file and an optional `kind`: `image`
(the default), `audio`, `video` or `3d`. The kind must match the filename extension;
an omitted kind never infers a different media type. For example, a WAV input
uses `{"path": "/chosen/reference.wav", "kind": "audio"}`. See the
[format policy and limits](SDK_UPLOADS.md#active-reference-uploads).

Poll `reference_upload_status` until `imported` before using the returned asset ID
in a model estimate. Status, `list_reference_uploads` and recovery return saved
`kind` and `content_type` metadata; initial staging can report null metadata.
Only the selected file is sent: no conversion, external-buffer or texture-sidecar
discovery. Upload approval does not approve generation, and a lost response must
be reconciled using saved progress instead of starting another upload. The same uploads and saved-reference recovery are available in generation
forms for image, audio, video and 3D inputs. `capture_reference` also supports explicit `VIEWPORT_CLIP`, `CAMERA_CLIP` and
`MESH` snapshots. Clips use the preview/scene range at 1280x720 without audio,
trimming or padding; mesh export produces one GLB from the selected meshes.
Only mesh export works in background mode. Native render forms use the same
upload session for their explicit scene/first-frame slots. MCP still supplies its
final model parameters directly; render prompt decoration and automatic Spark
preparation are not new MCP operations. Result-specific application remains separate.

## Token lifecycle

GUI startup generates a bearer token the first time the server starts in a
Blender session. The extension holds it in memory and does not save it to disk.
The panel masks it; Copy buttons include the full token in setup snippets.
Restarting Blender changes a generated token, so copy the setup again. A token
explicitly supplied to the headless command remains the caller's responsibility.

The local token is different from your Scenario API key and secret. Client
configuration, shell history, clipboard managers and process listings may retain
copied tokens; keep them out of source control, screenshots and shared logs.

## Client setup

Use the panel's Copy buttons for the actual port and platform paths. Examples
below use placeholders, never real credentials. These clients must run where
`127.0.0.1` reaches the same machine as Blender; a hosted agent cannot reach your
computer's loopback address directly.

### Claude Code

```sh
claude mcp add --transport http scenario-blender http://127.0.0.1:9876/mcp \
  --header "Authorization: Bearer <token>"
```

### Cursor

Add the copied entry to your client MCP configuration:

```json
{
  "mcpServers": {
    "scenario-blender": {
      "url": "http://127.0.0.1:9876/mcp",
      "headers": {"Authorization": "Bearer <token>"}
    }
  }
}
```

### Claude Desktop

The stdio bridge forwards requests to the running Blender server. Copy the
installed shim path from the panel and verify that the command points to an
available Python 3 interpreter. The current panel can fall back to `python3`
on Windows instead of discovering Blender's bundled `python.exe`; select an
absolute working interpreter path there. Replace both path placeholders:

```json
{
  "mcpServers": {
    "scenario-blender": {
      "command": "<absolute path to Blender Python>",
      "args": [
        "<installed extension>/mcp/stdio_shim.py",
        "--url", "http://127.0.0.1:9876/mcp",
        "--token", "<token>"
      ]
    }
  }
}
```

The bridge token is a process argument. It does not start Blender or grant
Scenario API access by itself.

### Codex

The installed CLI supports `--url` and `--bearer-token-env-var`. Export the token
in the environment that launches Codex, then add the server:

```sh
export SCENARIO_BLENDER_TOKEN='<token>'
codex mcp add scenario-blender --url http://127.0.0.1:9876/mcp \
  --bearer-token-env-var SCENARIO_BLENDER_TOKEN
```

The equivalent `config.toml` entry is:

```toml
[mcp_servers.scenario-blender]
url = "http://127.0.0.1:9876/mcp"
bearer_token_env_var = "SCENARIO_BLENDER_TOKEN"
```

Restart a client launched before the environment variable was set. See the
[official Codex MCP configuration](https://learn.chatgpt.com/docs/extend/mcp?surface=cli)
for configuration and token-environment behavior.

### Connection check

This request lists tool metadata; it does not call a generation tool:

```sh
curl -sS -X POST http://127.0.0.1:9876/mcp \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/list"}'
```

### Headless Blender

With the extension enabled, use the registered underscore command:

```sh
export SCENARIO_BLENDER_TOKEN='<token>'
blender --background scene.blend --command scenario_blender --port 9876
```

Blender must allow online access; `--online-mode` explicitly enables it for the
invocation. `--token '<token>'` overrides the environment but exposes the token
in process arguments. Supplied tokens are hidden in the startup banner. If
neither source is present, the command generates a token and displays it once
in that banner. Stop with Ctrl+C. Scene captures need the GUI; other scene tools
use the headless main-thread request loop. Development builds and tests use the
[isolated native runner](../CONTRIBUTING.md#native-blender-test-loop).

Cost estimates use the shared SDK job session. Model preparation and credential
checks run on Blender's main thread; fresh metadata and the dry-run request run
on the session workers. The MCP request thread waits without blocking Blender.
`estimate_cost` returns `quote_id` and `cu_cost_exact`, the server cost as a
decimal string, alongside the numeric `cu_cost` and `details`. An estimate does
not authorize spending; `generate` requires the exact approved cost and quote.

## Tools

The table is generated from the same definitions served by `tools/list`. That
response includes full argument guidance, examples and returned keys. The job
tools require `job_id` or the compatibility alias `id`; either accepts a
`local_id` from generation or a known Scenario job ID. A nonempty `job_id` wins
when both are supplied.

<!-- tools:start -->
Generated by `tools/gen_mcp_docs.py` from `scenario/mcp/tools_*.py`.
Do not edit this block by hand; run `make mcp-docs`. An asterisk marks a required argument.

### Scene tools (run on Blender's main thread)

| Tool | Description | Arguments | Notes |
| --- | --- | --- | --- |
| `scene_summary` | Inspect the open Blender scene before choosing a scene operation. | none | read-only annotation |
| `object_detail` | Inspect one named Blender object's transform, geometry summary and custom properties. | `name`*: string | read-only annotation |
| `execute_python` | Run arbitrary Python with bpy on Blender's main thread, only when explicitly enabled in preferences. | `code`*: string; Python source. bpy and result = {} are preloaded. | destructive annotation; Python preference gate; off by default |
| `select_objects` | Replace the selection in the current view layer with the named Blender objects. | `names`*: array | - |
| `set_frame` | Move Blender's timeline to a frame and evaluate the scene there. | `frame`*: integer | - |
| `screenshot_viewport` | Capture the visible 3D viewport area as a PNG image, including its UI overlays. | none | read-only annotation; GUI required |
| `camera_path` | Build an animated scene camera from a preset, description or explicit waypoints for Render Video. | `preset`: string<br>`duration`: number; seconds<br>`focal`: number; mm<br>`aim_at_subject`: boolean<br>`description`: string; e.g. 'slow orbit, 8 s, 35mm'<br>`waypoints`: array | - |
| `render_still` | Capture a quick OpenGL camera or viewport still as a PNG at the requested size. | `source`: string (['CAMERA', 'VIEWPORT'])<br>`width`: integer<br>`height`: integer | read-only annotation; GUI required |
| `blender_api_help` | Inspect Blender's running Python API before writing a script. | `path`*: string; e.g. bpy.ops.mesh.primitive_cube_add, bpy.types.Object, bpy.data.objects | read-only annotation |
| `datablocks_summary` | Summarize the datablocks in the open Blender file. | none | read-only annotation |

### Scenario tools

| Tool | Description | Arguments | Notes |
| --- | --- | --- | --- |
| `upload_reference` | Upload an explicitly chosen image, audio, video or 3D file through the shared durable upload session. | `path`*: string<br>`kind`: string (['image', 'audio', 'video', '3d']) | - |
| `reference_upload_status` | Read a reference upload's progress while the shared session advances its already authorized work. | `context_id`*: string<br>`reference_id`*: string | read-only annotation |
| `list_reference_uploads` | Inspect saved uploads under the selected credential scope, including after restart. | none | read-only annotation |
| `recover_reference_upload` | Explicitly inspect a known remote upload, cancel unclaimed preparation, or clean its finished private source copy. | `context_id`*: string<br>`request_id`*: string<br>`expected_revision`*: integer<br>`action`*: string (['refresh', 'cancel_prepared', 'cleanup']) | destructive annotation |
| `prepare_result_application` | Prepare explicit import of downloaded PNG/EXR images from a saved job into the current file. | `context_id`*: string<br>`request_id`*: string<br>`expected_revision`*: integer | read-only annotation |
| `apply_result_application` | Import and pack saved images after the user approves the prepared destination. | `context_id`*: string<br>`application_id`*: string | destructive annotation |
| `recover_local_job` | Explicitly recover a saved job without repeating generation or importing into another scene. | `context_id`*: string<br>`request_id`*: string<br>`expected_revision`*: integer<br>`action`*: string (['refresh', 'resume', 'cancel', 'recover_download', 'retry_receipt']) | destructive annotation |
| `list_local_jobs` | Inspect durable local jobs for the selected API-key pair without network requests. | none | read-only annotation |
| `cancel_prepared_job` | Cancel an unsubmitted durable local intent without contacting Scenario. | `context_id`*: string<br>`request_id`*: string<br>`expected_revision`*: integer | destructive annotation |
| `list_models` | List the loaded lane catalog, with curated models first and at most 40 matches. | `lane`: string (enum: see tools/list)<br>`query`: string | read-only annotation |
| `model_schema` | Read the model's current form parameters for this Blender extension. | `model_id`*: string | read-only annotation |
| `estimate_cost` | Get the exact CU cost with a dry run that spends no credits. | `model_id`*: string<br>`parameters`: object<br>`lane`: string (enum: see tools/list) | read-only annotation |
| `generate` | Submit a generation that spends the user's credits. Every model lane uses durable shared jobs. | `lane`*: string (enum: see tools/list)<br>`quote_id`*: string<br>`approved_cost`*: string<br>`model_id`*: string<br>`parameters`: object; Model parameters; file parameters take Scenario asset ids | spends credits |
| `job_status` | Read one local generation's status and cost without spending credits. Active model jobs advance through shared remote polling and verified downloads; restarted jobs remain inspection-only. | `job_id`: string; Scenario job id (job_...) or the local_id returned by generate<br>`id`: string; Same as job_id, kept for compatibility | read-only annotation |
| `wait_for_job` | Wait for a generation while Blender remains responsive. Shared jobs return when delivery finishes, pauses for review, or the wait expires. Restarted jobs remain inspection-only until explicitly resumed. | `job_id`: string; Scenario job id (job_...) or the local_id returned by generate<br>`id`: string; Same as job_id, kept for compatibility<br>`timeout`: number | read-only annotation |
| `import_result` | Apply a downloaded prototype generation again to the current Blender scene and selection. | `job_id`: string; Scenario job id (job_...) or the local_id returned by generate<br>`id`: string; Same as job_id, kept for compatibility | - |
| `capture_reference` | Capture a viewport/camera still or clip, or export selected meshes, and upload the snapshot as a Scenario reference asset. | `source`: string (['VIEWPORT', 'CAMERA', 'VIEWPORT_CLIP', 'CAMERA_CLIP', 'MESH']) | - |
| `list_generations` | List recent cloud generations using this Blender runtime's loaded history. | `limit`: integer<br>`refresh`: boolean | read-only annotation |
<!-- tools:end -->

## Security model

The Blender integration binds only to `127.0.0.1`. MCP operations require the
bearer token, checked with a constant-time comparison. `/health` is unauthenticated
and reports availability, Blender version and server name/version. Native clients
may omit Origin; a supplied Origin must be an HTTP(S) loopback origin. Other
origins and browser CORS preflights are refused. This is local access control,
not a promise that a token-holding program is safe.

Early POST and Origin rejections send the complete HTTP error with
`Connection: close`, then close the socket's write side before discarding a
bounded pending body. Only an unambiguous declared length within the existing
10 MiB body limit can be discarded, in chunks under a one-second total deadline.
Rejected bytes are never parsed or dispatched. This staged teardown reduces the
risk of a TCP reset hiding the error from clients still sending their body;
malformed, chunked or oversized requests close without reading their declared body.

**Allow connected agents to run Python** is off by default and fails closed if
preferences are unavailable. With it off, an authorized agent can still read
and change the scene, capture/upload a reference and request paid generation.
Require an estimate and explicit spending approval. If a generation call times
out, inspect job status; do not submit it again blindly. Client timeouts do not
prove that queued or remote work was canceled.

The server's own main-thread queue deadline has an explicit execution boundary.
A request that expires before its handler starts is removed from execution and
returns `the tool was not executed`; resuming Blender cannot run that old request.
Stopping the server also rejects new admission and releases queued callers
without executing their tools, including after a restart. A handler already
running is not interrupted: its timeout reports an unknown outcome and asks the
client to inspect the operation before retrying. This does not cancel remote
jobs or establish whether an HTTP client's independent timeout happened before
or after dispatch.

With Python enabled, a connected agent can run arbitrary Python with your user's
permissions. The blocklist in `scenario/mcp/sandbox.py` is a guard rail, not a
security boundary. The token can be copied into client configuration files and,
for the stdio bridge, command arguments. Do not expose the port through a public
proxy or share setup snippets. Report vulnerabilities through
[SECURITY.md](../SECURITY.md); see [privacy and local data](PRIVACY.md) for uploads,
credential storage and data handling.

## Local server and mcp.scenario.com

Local names retain their verb-first form. The platform uses names such as
`models_list` and `job_get`; similar names do not make their parameters or scene
behavior interchangeable. Remote names below were checked against the
[hosted tool reference](https://mcp.scenario.com/docs/tools).

| Concept | scenario-blender | Hosted platform |
| --- | --- | --- |
| Choose models | `list_models(lane, query)` | `models_list`, `search`, `recommend` |
| Model parameters | `model_schema(model_id)` | `model_schema_get` |
| Price without generating | `estimate_cost(model_id, parameters)` | `model_run` with `dry_run=true` |
| Generate | `generate(lane, model_id, parameters)`, automatic scene application | `model_run` |
| Job status | `job_status(job_id or id)` | `job_get` |
| Durable local recovery | `list_local_jobs`, `cancel_prepared_job` | Local only; no remote polling or cancellation |
| Saved job actions | `recover_local_job(context_id, request_id, expected_revision, action)` | Scoped job refresh/cancellation, asset retrieval, or local receipt recovery; never a new generation |
| Review saved Image import | `prepare_result_application(context_id, request_id, expected_revision)` | Local destination capture; show the returned scene and images for approval |
| Apply approved saved images | `apply_result_application(context_id, application_id)` | Local verified import into the captured destination; no platform call |
| Wait | `wait_for_job(job_id or id, timeout)`, one job without blocking Blender | `jobs_wait` |
| Reference upload | `upload_reference(path, kind)` or `capture_reference(source)`, then `reference_upload_status(context_id, reference_id)` until imported | `upload_asset`, `upload_asset_complete` for an existing file |
| Saved upload recovery | `list_reference_uploads`, then `recover_reference_upload(context_id, request_id, expected_revision, action)` | Known-upload status retrieval; local cancellation/cleanup have no platform equivalent |
| History | `list_generations(limit)` | `jobs_list` |
| Apply an existing result | `import_result(job_id or id)` | No Blender scene access |
| Prompt assistance | Panel controls | `prompt_spark` |
| Inspect scene | `scene_summary`, `object_detail`, `datablocks_summary`, `blender_api_help` | Local only |
| Change scene | `select_objects`, `set_frame`, `camera_path`, `execute_python` | Local only |
| Capture scene | `screenshot_viewport`, `render_still` | Local only |
| Collections, training, workflows and usage | Use the hosted server | Discover operations in the hosted tool reference |

Connect both when needed: use the local setup above for Blender and the
[hosted server setup](https://mcp.scenario.com/docs) for Scenario-wide work.
Some platform operations are discovered through its tool catalog.

`capture_reference` now returns `context_id` and `reference_id`, rather than an
immediate asset ID or a local capture path. Both upload tools return while the
shared session stages and transfers the prepared reference. Poll `reference_upload_status`
until `state` is `imported`, then use `asset_id` in a fresh `estimate_cost` call.
The generation still requires its own exact-cost approval. Do not repeat an
uncertain upload: inspect saved progress and explicitly refresh its known ID.
After restart, use `list_reference_uploads`; session handles do not survive.
Recovery can refresh, cancel unclaimed preparation, or clean a finished private
source copy, without replaying upload mutations or deleting the original file.
See [upload limits and destination policy](SDK_UPLOADS.md#active-reference-uploads).

`wait_for_job` accepts a finite timeout from 0 to 170 seconds (default 170).
A zero timeout reads status immediately. Other waits observe the captured local
record on the HTTP thread; they do not submit, retry, cancel or poll the remote
service. The main thread prepares the wait and returns its final status. Runtime
shutdown and server stop interrupt waiting; a changed credential context, manager
or record rejects the old completion. This does not establish account-scoped
persistence for the prototype job registry or guarantee that automatic scene
application has finished when a remote job reaches a terminal status.

## Troubleshooting

- **401:** the token is missing or differs from the server's current token. Copy
  the setup again; check the actual port and the client's launch environment.
- **No free port from 9876:** all four candidate ports are busy. Choose a different
  MCP Port and copy the newly displayed URL.
- **Allow Online Access is off:** enable it in Blender's System preferences before
  starting the server; this permission also allows Scenario network operations.
- **Capture fails in background mode:** open a GUI session with a 3D viewport.
- **Catalog is still loading:** retry after loading completes and inspect the
  extension's status for credential or service errors. This is separate from the
  local MCP bearer token.
- **Call times out:** a modal dialog or long-running main-thread tool can delay
  other requests. Check status before repeating any action that may spend credits
  or modify the scene. `wait_for_job` leaves the main thread available while
  waiting, but its preparation and final status delivery still require that thread.

Maintainers: run `make mcp-docs` after changing tool definitions and
`uv run --locked --no-env-file python tools/gen_mcp_docs.py --check` to detect drift.

## Model quote and submission contract

For every model lane, `estimate_cost` returns `quote_id` and `cu_cost_exact`.
After explicit user approval, pass those values as `quote_id` and `approved_cost`
to `generate` with the same lane, model and parameters. The estimate's lane
is `image` when omitted. A changed lane, scene, credential context, input or
consumed quote requires a fresh estimate. An estimate alone does not authorize
spending. Failed or timed-out submissions must be inspected by their returned
local ID, never blindly repeated.

All MCP model submissions persist intent before SDK dispatch. `job_status`,
`wait_for_job` and `list_local_jobs` expose saved state across restart. Active
jobs poll and download through the shared session; restarted jobs need explicit
recovery. `wait_for_job` lets the main thread advance work and returns at a
terminal/review state or its timeout. Cancellation and interrupted download
recovery use the same scoped revision guards as Image.

Only the Image lane automatically imports verified PNG/EXR images into its
unchanged original scene. Other lanes stop at `ready` after saving downloads;
there is no implicit texture assignment, mesh import or sequencer insertion.
`job_status.results` reports asset identity, media type, expected size and whether
a download receipt was recorded. This inspection does not reverify local files
or authorize scene application. Recovered display records use generic
`kind: model`; original lane metadata is not persisted. PNG/EXR results can use
the explicit image import approval above, without inferring a material or World
assignment from their media type. `import_result` accepts prototype records only;
shared jobs reject it with guidance for explicit PNG/EXR application. A cold
session identifies saved prototype records from the local registry before
accessing shared jobs, so inspecting or importing an already downloaded
completed prototype result does not require Scenario credentials or create a
manager that resumes unrelated pending jobs. Non-terminal prototype lookups
still use the manager-owned record so active waits observe its progress.

Render lanes take the explicit model parameters supplied by the caller. They do
not run the UI's capture, style decoration or Prompt Spark preparation. Non-image
UI capture/Spark preparation, result-specific application and Film
remain integration work under #65/#68. This change does not complete their
end-to-end acceptance or authorize release.
