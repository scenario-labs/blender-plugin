# Local MCP reference

## Overview

`scenario-blender` connects an agent to the open Blender scene and generation
into that scene. The hosted server at `mcp.scenario.com` provides platform-wide
operations such as collections, training, workflow authoring and usage.
Local workflow discovery and approved execution use the same saved-job session
as model generation. Connect either
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
Rows identify `source: generation` or `cloud`. A record created through the
[cloud adoption foundation](JOB_COORDINATOR.md#adopting-a-completed-cloud-job)
has `cu_cost_exact: null`, because no local quote exists. `job_status` preserves
the same distinction. Use `recover_cloud_job` to save a completed cloud model
job before explicit download and result approval.
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

For one saved video/audio asset, pass its `asset_id` to the same preparation
command. Show the returned scene, frame, kind and local-file requirement before
approval. Confirmation inserts one MP4/WebM movie or MP3/WAV/OGG sound strip on
an unused channel; it preserves scene timing and omits embedded video audio.
Changed frames also invalidate this approval. One selected asset consumes the
job's application claim; receipt-only recovery never inserts another strip.
The independent media file must remain available to the blend file. See
[saved media application](BLENDER_JOB_CONTEXT.md#explicit-saved-video-and-audio-application)
for size, rollback and persistence limits.

For a self-contained GLB, the same `asset_id` argument returns `kind: model` and the
approved `cursor` instead of a media frame. Show its scene and cursor before
approval. The importer adds one new model group and packs embedded textures;
it leaves current selection intact. The cursor is rechecked before the durable
claim. Rigs, weights and node/morph animation clips stay in the new group.
Timing uses the current scene FPS, with unchanged frame and timeline range.
External-file, pointer-animation and non-GLB results remain unsupported.
See [model import](MESH_APPLICATION.md#explicit-saved-glb-import)
for bounds and recovery. This never replaces an existing mesh.

For one unapplied saved panorama, pass `purpose: world` and its `asset_id` to
`prepare_result_application`; show the scene, current World and returned `format`
before approval. `format` states the saved media type's declared format, such as
`JPEG (LDR)` or an OpenEXR whose ACES AP0 primaries use ACES2065-1; restoration
returns `null`. The same apply command verifies and packs a supported 2:1 PNG,
JPEG or scanline OpenEXR as an explicitly chosen equirectangular environment.
The actual container must match the saved media type. It preserves the previous
World. This is not a seamless-content or actual HDR-range guarantee.

After a completed World assignment, `purpose: restore_world` prepares a separate
session-local restore without an asset ID. Show that operation before consuming
its handle. Edited owned World/image data or a changed destination prevents
restoration. The completed job stays `applied` and cannot be replayed. Existing
automatically imported Image jobs also stay ineligible for another claim. See
[World approval and limits](WORLD_APPLICATION.md#saved-result-ui-and-mcp-approval).

For one unapplied saved texture set, `purpose: material` captures the active mesh,
its active material slot and unambiguous stored map roles. Show that destination
and map list before consuming the shared application approval. It packs new
images, creates a material and changes only that slot. It does not reuse a new
selection after confirmation. See [material application](MATERIAL_APPLICATION.md)
for single-user/UV restrictions, supported maps, rollback and no-global-undo limits.

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
Only mesh export works in background mode. `render_form` uses the native render
form and the same upload session for explicit scene/first-frame slots. Its
`prepare` action requires a GUI for scene captures; first-frame file uploads also
work headlessly. Result-specific application remains separate.

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
| `list_assets` | Read one asset-library page using the selected credentials and optional project scope. | `public`: boolean<br>`page_size`: integer<br>`pagination_token`: string<br>`collection_id`: string | read-only annotation |
| `search_assets` | Search asset-library metadata through the shared SDK session. | `query`*: string<br>`public`: boolean<br>`limit`: integer<br>`offset`: integer | read-only annotation |
| `list_workflows` | List workflows in the selected credential/project scope without spending. | `privacy`: string (['private', 'public'])<br>`query`: string<br>`offset`: integer<br>`limit`: integer | read-only annotation |
| `workflow_schema` | Read a workflow's declared input definitions without spending. | `workflow_id`*: string | read-only annotation |
| `estimate_workflow` | Request a free exact workflow price bound to the selected scene and connection. | `workflow_id`*: string<br>`parameters`: object | - |
| `run_workflow` | Approve one unchanged workflow estimate and persist its identity before paid dispatch. | `workflow_id`*: string<br>`parameters`: object<br>`quote_id`*: string<br>`approved_cost`*: string | - |
| `discard_workflow_estimate` | Discard one ready unsubmitted workflow approval without changing saved jobs. | `quote_id`*: string | - |
| `prepare_film_composition` | Inspect saved Film media and prepare a final or previs composition without spending. | `context_id`*: string<br>`production_id`*: string<br>`mode`: string (['final', 'previs'])<br>`score_task_id`: string | - |
| `film_composition_review` | Inspect, cancel or discard a session-local Film composition review. | `review_id`*: string<br>`action`: string (['status', 'cancel', 'discard']) | - |
| `estimate_film_composition` | Request the exact server price for one READY verified Film composition. | `review_id`*: string | read-only annotation |
| `generate_film_composition` | Approve one exact Film composition price and save its master identity before a single submission. | `review_id`*: string<br>`approved_cost`*: string | - |
| `prepare_film_review` | Copy and measure saved Film media for a final or previs review scene without building or spending. | `context_id`*: string<br>`production_id`*: string<br>`mode`: string (['final', 'previs'])<br>`score_task_id`: string<br>`include_master`: boolean | - |
| `film_review_status` | Inspect, cancel or discard a session-local Film review, or retry only its known saved receipt. | `review_id`*: string<br>`action`: string (['status', 'cancel', 'discard', 'retry_receipt', 'dismiss_uncertain'])<br>`inspected`: boolean | - |
| `build_film_review` | Approve one READY Film review and build a new review scene from its private copies. | `review_id`*: string | - |
| `film_capture_sources` | Inspect matching local scenes for one Film shot before capture. | `production_id`*: string<br>`shot_id`*: string | read-only annotation |
| `prepare_film_capture` | Prepare a local shot capture for separate render approval. | `context_id`*: string<br>`production_id`*: string<br>`shot_id`*: string<br>`source_id`*: string<br>`kind`: string (['STILL', 'VIDEO'])<br>`width`: integer<br>`height`: integer<br>`color_type`: string (['MATERIAL', 'TEXTURE', 'OBJECT']) | - |
| `render_film_capture` | Approve a READY Film capture and start one local render on the shared workers. | `review_id`*: string | - |
| `film_capture_review` | Inspect, cancel or discard an owner-local Film capture. | `review_id`*: string<br>`action`: string (['status', 'cancel', 'discard']) | - |
| `upload_film_capture` | Upload the reviewed bytes of one completed Film capture through the shared upload runtime. | `review_id`*: string | - |
| `film_timeline_sources` | Inspect matching local scenes for every shot in the current Film recipe. | `production_id`*: string | read-only annotation |
| `prepare_film_timeline` | Prepare explicit completed shot choices for separate timeline build approval. | `context_id`*: string<br>`production_id`*: string<br>`selections`*: object | - |
| `film_timeline_review` | Inspect or discard an owner-local Film timeline review. | `review_id`*: string<br>`action`: string (['status', 'discard'])<br>`inspected`: boolean | - |
| `build_film_timeline` | Approve one READY Film timeline review and create a new editable scene-strip sequence. | `review_id`*: string | - |
| `film_shot_sources` | Inspect eligible downloaded hero models for one shot in the current Film recipe. | `production_id`*: string<br>`shot_id`*: string | read-only annotation |
| `prepare_film_shot` | Verify explicit saved hero selections and prepare a shot for separate build approval. | `context_id`*: string<br>`production_id`*: string<br>`shot_id`*: string<br>`selections`*: object | - |
| `film_shot_review` | Inspect or discard a Film shot review, or retry only its known persistence receipts. | `review_id`*: string<br>`action`: string (['status', 'discard', 'retry_receipts', 'dismiss_uncertain'])<br>`inspected`: boolean | - |
| `build_film_shot` | Approve one READY Film review and build a new shot scene from its verified saved models. | `review_id`*: string | - |
| `film_recipe` | Inspect or load the current scene's Film recipe, or explicitly start a new production. | `action`: string (['inspect', 'load', 'new_production'])<br>`recipe`: object | - |
| `estimate_film_task` | Request the exact server price for one model task in the loaded Film recipe. | `production_id`*: string<br>`task_id`*: string | read-only annotation |
| `approve_film_task` | Approve one unchanged Film estimate and save its identity before one paid submission. | `quote_id`*: string<br>`approved_cost`*: string | - |
| `discard_film_estimate` | Release one unsubmitted Film estimate so its task can be repriced. | `quote_id`*: string | - |
| `bind_film_upload` | Associate one imported saved upload with a Film upload task without sending bytes. | `production_id`*: string<br>`task_id`*: string<br>`context_id`*: string<br>`request_id`*: string<br>`expected_revision`*: integer | - |
| `upload_reference` | Upload an explicitly chosen image, audio, video or 3D file through the shared durable upload session. | `path`*: string<br>`kind`: string (['image', 'audio', 'video', '3d']) | - |
| `reference_upload_status` | Read a reference upload's progress while the shared session advances its already authorized work. | `context_id`*: string<br>`reference_id`*: string | read-only annotation |
| `list_reference_uploads` | Inspect saved uploads under the selected credential scope, including after restart. | none | read-only annotation |
| `recover_reference_upload` | Explicitly inspect a known remote upload, cancel unclaimed preparation, or clean its finished private source copy. | `context_id`*: string<br>`request_id`*: string<br>`expected_revision`*: integer<br>`action`*: string (['refresh', 'cancel_prepared', 'cleanup']) | destructive annotation |
| `prepare_result_application` | Prepare explicit saved image/media/model import, material assignment, panorama World replacement, or session-local World restoration. | `context_id`*: string<br>`request_id`*: string<br>`expected_revision`*: integer<br>`asset_id`: string<br>`purpose`: string (['import', 'material', 'world', 'restore_world', 'mesh_edit', 'mesh_source'])<br>`mesh_policy`: string (['REMESH', 'UV', 'RETEXTURE', 'PARTS', 'RIG'])<br>`mesh_placement`: string (['WORLD', 'LOCAL'])<br>`keep_original`: boolean | read-only annotation |
| `apply_result_application` | Apply or restore saved results after the user approves the prepared destination and operation. | `context_id`*: string<br>`application_id`*: string | destructive annotation |
| `recover_local_job` | Explicitly recover a saved job without repeating generation or importing into another scene. | `context_id`*: string<br>`request_id`*: string<br>`expected_revision`*: integer<br>`action`*: string (['refresh', 'resume', 'cancel', 'recover_download', 'retry_receipt']) | destructive annotation |
| `list_local_jobs` | Inspect durable local jobs for the selected API-key pair without network requests. | none | read-only annotation |
| `cancel_prepared_job` | Cancel an unsubmitted durable local intent without contacting Scenario. | `context_id`*: string<br>`request_id`*: string<br>`expected_revision`*: integer | destructive annotation |
| `estimate_blockout` | Get the exact free estimate for the current scene's Blockout description or refinement. This reads the native Blockout fields and current plan; it does not generate or build geometry. Approve the exact returned cu_cost_exact separately. Args: action DESIGN or REFINE. Returns: quote_id, action, cu_cost_exact. | `action`: string (['DESIGN', 'REFINE']) | read-only annotation |
| `approve_blockout` | Spend the explicitly approved exact cost once for estimate_blockout. Args: quote_id and approved_cost. Inputs, current plan and origin must still match. Returns: request_id and state. The unchanged source scene receives a complete plan; no geometry is built automatically. Inspect list_local_jobs after failure or restart; never repeat an uncertain submission. | `quote_id`*: string<br>`approved_cost`*: string | - |
| `prepare_blockout_plan` | Read and validate one saved Scenario LLM plan for the current scene without generating or building geometry. Args: context_id, request_id, expected_revision from list_local_jobs. Returns: review_id, state, scene, elements, groups, replaces_plan, error. Poll blockout_plan_status until ready, then review the destination and replacement before apply_blockout_plan. | `context_id`*: string<br>`request_id`*: string<br>`expected_revision`*: integer | read-only annotation |
| `blockout_plan_status` | Inspect a prepared saved-plan review or discard its finished approval handle. Args: context_id, review_id, optional discard. Returns: state, scene, elements, groups, replaces_plan, error; discarded state when requested. Never generates or changes a scene. | `context_id`*: string<br>`review_id`*: string<br>`discard`: boolean | read-only annotation |
| `apply_blockout_plan` | Use a ready saved-plan review once, after explicit destination and replacement approval. Args: context_id, review_id from prepare_blockout_plan. Returns: scene, elements, geometry_changed=false. Replaces only the unchanged destination scene stored Blockout plan; use native Build plan separately. Never spends or builds geometry. | `context_id`*: string<br>`review_id`*: string | destructive annotation |
| `read_model_text` | Read one explicitly selected complete text asset from a successful saved model job, including after restart. Obtain context_id and revision from list_local_jobs and asset_id from job_status results. Returns: request_id, asset_id and bounded full text. Never spends, parses a plan, applies to the scene or substitutes a truncated preview. Args: context_id, request_id, expected_revision, asset_id. | `context_id`*: string<br>`request_id`*: string<br>`expected_revision`*: integer<br>`asset_id`*: string | read-only annotation |
| `estimate_prompt` | Get the exact server price for New, Rewrite or Translate on the current scene's native prompt field. This does not generate or change text. Args: lane and action (GENERATE, REWRITE, TRANSLATE). Returns: quote_id and cu_cost_exact. Obtain explicit approval of that exact cost before approve_prompt. The current field text/model must remain unchanged. | `lane`: string (enum: see tools/list)<br>`action`*: string (['GENERATE', 'REWRITE', 'TRANSLATE']) | read-only annotation |
| `approve_prompt` | Spend the explicitly approved exact price once for a quote from estimate_prompt. Args: quote_id and approved_cost (the unchanged decimal string). Returns: request_id and queued state. Queues one durable submission; never retry an uncertain outcome. The shared runtime updates only the unchanged original prompt field. Inspect list_local_jobs for recovery. | `quote_id`*: string<br>`approved_cost`*: string | destructive annotation |
| `read_prompt_result` | Read full text from a saved successful prompt or translation job without generating, spending or applying it. Args: context_id, request_id and expected_revision from list_local_jobs; refresh a known remote job's status first if necessary. Returns: prompts; old scene origins are readable but are never silently applied to the current scene. | `context_id`*: string<br>`request_id`*: string<br>`expected_revision`*: integer | read-only annotation |
| `list_models` | List the loaded lane catalog, with curated models first and at most 40 matches. | `lane`: string (enum: see tools/list)<br>`query`: string | read-only annotation |
| `model_schema` | Read the model's current form parameters for this Blender extension. | `model_id`*: string | read-only annotation |
| `render_form` | Inspect or prepare the native Render Image/Video form without submitting generation. | `lane`*: string (['render_image', 'render_video'])<br>`action`: string (['inspect', 'configure', 'prepare', 'remove'])<br>`settings`: object<br>`role`: string (['scene', 'first_frame'])<br>`reference_key`: string | - |
| `estimate_cost` | Get the exact CU cost with a dry run that spends no credits. | `model_id`*: string<br>`parameters`: object<br>`lane`: string (enum: see tools/list) | read-only annotation |
| `generate` | Submit a generation that spends the user's credits. Every model lane uses durable shared jobs. | `lane`*: string (enum: see tools/list)<br>`quote_id`*: string<br>`approved_cost`*: string<br>`model_id`*: string<br>`parameters`: object; Model parameters; file parameters take Scenario asset ids | spends credits |
| `job_status` | Read one local generation's status and cost without spending credits. Active model jobs advance through shared remote polling and verified downloads; restarted jobs remain inspection-only. | `job_id`: string; Scenario job id (job_...) or the local_id returned by generate<br>`id`: string; Same as job_id, kept for compatibility | read-only annotation |
| `wait_for_job` | Wait for a generation while Blender remains responsive. Shared jobs return when delivery finishes, pauses for review, or the wait expires. Restarted shared jobs remain inspection-only until explicitly resumed. Prototype records return a local snapshot immediately with scoped recovery guidance. | `job_id`: string; Scenario job id (job_...) or the local_id returned by generate<br>`id`: string; Same as job_id, kept for compatibility<br>`timeout`: number | read-only annotation |
| `recover_cloud_job` | Read one completed cloud model job into the selected credential-scoped saved jobs. | `job_id`*: string<br>`model_id`*: string | - |
| `import_result` | Reject direct cached-file import and explain the required saved-result approval flow. | `job_id`: string; Scenario job id (job_...) or the local_id returned by generate<br>`id`: string; Same as job_id, kept for compatibility | - |
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
| Review one saved video/audio strip | `prepare_result_application(context_id, request_id, expected_revision, asset_id)` | Local scene/frame capture; show returned destination for approval |
| Review one saved GLB | `prepare_result_application(context_id, request_id, expected_revision, asset_id)` | Local scene/cursor capture; show the returned destination for approval |
| Review panorama World or restore | `prepare_result_application(context_id, request_id, expected_revision, purpose, asset_id)` | Use `world` with one PNG/JPEG/OpenEXR asset and show its `format`, or `restore_world` for the retained session handle |
| Apply approved saved results | `apply_result_application(context_id, application_id)` | Local verified import or strip insertion into the captured destination; no platform call |
| Wait | `wait_for_job(job_id or id, timeout)`, one job without blocking Blender | `jobs_wait` |
| Reference upload | `upload_reference(path, kind)` or `capture_reference(source)`, then `reference_upload_status(context_id, reference_id)` until imported | `upload_asset`, `upload_asset_complete` for an existing file |
| Saved upload recovery | `list_reference_uploads`, then `recover_reference_upload(context_id, request_id, expected_revision, action)` | Known-upload status retrieval; local cancellation/cleanup have no platform equivalent |
| History | `list_generations(limit)` | `jobs_list` |
| Recover a cloud result | `recover_cloud_job`, then explicit saved-result approval | No Blender scene access |
| Prompt assistance | `estimate_prompt(lane, action)` then `approve_prompt(quote_id, approved_cost)`; same native prompt field and exact-price approval | `prompt_spark` for generation; SDK `generate.translate` for English translation |
| Saved prompt text | `read_prompt_result(context_id, request_id, expected_revision)` | `job_get` and `asset_get`; read-only recovery without Blender mutation |
| Inspect scene | `scene_summary`, `object_detail`, `datablocks_summary`, `blender_api_help` | Local only |
| Change scene | `select_objects`, `set_frame`, `camera_path`, `execute_python` | Local only |
| Capture scene | `screenshot_viewport`, `render_still` | Local only |
| Workflow discovery | `list_workflows`, `workflow_schema` | `workflows_list`, `workflow_get` |
| Asset library metadata | `list_assets`, `search_assets` | SDK `assets.list` and `search.asset_search`; no hosted tool-name equivalence asserted here |
| Workflow price and execution | `estimate_workflow`, `run_workflow` | `workflow_run` |
| Discard workflow approval | `discard_workflow_estimate` | Local only; no remote cancellation |
| Collections, training, workflow authoring and usage | Use the hosted server | Discover operations in the hosted tool reference |

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
A zero timeout reads status immediately. Shared waits observe their scoped session
on the HTTP thread while main-thread maintenance performs delivery. Server stop
interrupts waiting; a changed session rejects the old completion. Waiting does
not approve generation, cancellation or scene application.

Prototype registry records have no automatic service engine. Their waits return
the saved local snapshot immediately, including nonterminal records, with
`recover_cloud_job` guidance. Their saved status is not a fresh remote status.
No credentials, service requests or registry writes are needed for cold reads.

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
assignment from their media type. Supported video/audio uses the explicit
asset and scene/frame approval above. Embedded GLBs use the corresponding
scene/cursor approval; in-place editing is separate. `import_result` rejects
direct cached-file import, including prototype records, with guidance for scoped
recovery and explicit destination approval. It requires complete selected
credentials to inspect the saved store. Read-only inspection of any prototype record
uses its local snapshot without credentials, polling or manager creation. No
prototype result event automatically applies cached files into the current scene.

Speech-to-text (`audio2txt`) and video-to-motion (`video23d`) models are
experimental. `estimate_cost` and `generate` describe this status and accept
them like other models, and `list_models` returns the picker's status text in
each entry's `capability_status` (empty otherwise), named apart from the
server's model status. Their results stay in saved jobs.
`prepare_result_application` imports a returned GLB or media file by file type
only; motion and transcription handling is not accepted ([#190](https://github.com/scenario-labs/blender-plugin/issues/190)).

### Preparing Render Image and Render Video

1. Discover a model with `list_models(lane=render_image|render_video)` and inspect
   its parameters with `model_schema`.
2. Call `render_form` with `action=configure` and `settings`: select `model_id`,
   supply `look` or choose `spark_enabled=false` for the photoreal default, edit
   scalar `parameters`, and optionally provide `style_assets`. These edits change
   the current native form; they do not capture, upload or submit generation.
3. Call `render_form(action=prepare, role=scene)` to capture and upload the current
   camera/viewport. For Render Video, set `first_frame_path` and prepare
   `role=first_frame` when using it. Inspect until uploads finish. Captures use
   the current scene/camera and existing clip range; later scene edits do not
   change these uploaded snapshots.
4. An empty look with automatic Spark enabled requires a separate
   `estimate_prompt(lane=..., action=GENERATE)` and explicit `approve_prompt`
   with its exact approved cost. The shared pump delivers the look only to the
   unchanged form. Render Video Spark requires the uploaded first frame.
5. Call `estimate_cost` with the same lane/model and **omit `parameters`**. Show
   `cu_cost_exact`, obtain approval, then pass that exact string and `quote_id`
   to `generate`, again omitting `parameters`. Both tools rebuild the native
   decorated prompt and ordered uploaded inputs. Changed inputs, scene or
   credentials cannot spend an old approval.

Use `render_form(action=inspect)` to read preparation errors and reference
handles. `action=remove` requires the exact current `reference_key`; it detaches
that slot without canceling or deleting its saved upload. Repeated preparation
refuses an occupied slot, including uncertain uploads. Inspect saved progress
before explicitly replacing a snapshot. A model change requires removing its
old references first. `style_assets` replaces only unmarked style references;
marked uploads require explicit removal. Optional scalar parameters accept null
to disable them; invalid edits fail before changing the form. Final quotes still
validate conditional and one-of schema requirements.

Inspection returns only the enabled parameters used by the render lane. Its
`parameters` object can be passed back to `configure`, including numeric choices
represented by Blender's string enum identifiers. Only declared numeric choices
accept these strings; other numeric settings still require JSON numbers.

Raw render-lane parameter calls now fail with preparation guidance. Use the
ordinary Image/Video lanes for direct model parameters. Scene capture, file
upload, Spark approval and render submission remain separate actions. Offline
native tests cover this shared preparation path; live provider and desktop
acceptance, multi-object material application and Film remain #65/#68 work.


### Reusing completed shared results

Use the same `prepare_result_application` and `apply_result_application` sequence
with a fresh observed revision and destination. Preparation returns `reuse: true`
for another local application of a completed result; show this explicitly with
the selected files and destination before applying. It does not submit generation.
Restoration returns `reuse: false` and targets the most recent World assignment
for that job in the selected scene and current file session. Applying the same
result in another scene preserves both scenes' restoration handles.

`job_status.local_applications` reports each local claim's identifier, source
revision, purpose, selected asset IDs, destination identity and state. The
original generation's `status: applied` does not prove a new local application
finished. Observe `actions`, `delivery_paused`, errors and the local outcome.
The `objects`, `materials` and `images` lists include every still-live output of
that job retained by the current session, including earlier reuse. Deleted data
is omitted, and receipt retry does not duplicate entries. These display names are
not durable object identifiers and are not reconstructed after restart.
An unfinished local claim blocks further reuse, including after restart. A
session-owned `retry_receipt` action saves only the known outcome. No tool clears
uncertainty or automatically repeats scene work. Each job retains at most 128
local claims without evicting earlier records.

## Captured mesh input history

`estimate_cost` also returns `mesh_sources` for typed 3D inputs that identify
completed mesh snapshot uploads in the selected credential/project scope.
`job_status` retains these bindings after submission and restart. Each includes
the exact parameter/array position, asset and upload identities, captured origin,
export hash, source fingerprints and transforms. Ordinary assets and file uploads
have no inferred source metadata. Ambiguous matches fail before spending.

The shared coordinator persists and revalidates these records before its paid
claim. They describe uploaded snapshots and stay out of Scenario request bodies.
They do not prove the current source is unchanged, establish provider alignment,
or authorize finding/replacing an object after restart. See
[the storage contract](JOB_STORAGE.md#captured-mesh-inputs-in-generation-intents).


## Applying to an original mesh source

Use `prepare_result_application` with `purpose: mesh_source`, the observed job
revision and one saved GLB `asset_id`. It resolves the job's single captured mesh
input against the same session's unchanged live export, ignoring active selection.
Show the returned target, asset, policy, coordinate placement and Keep original
choice before calling `apply_result_application`. The generic `mesh_edit` purpose
continues to review the active mesh as an explicit destination.

Multiple captured inputs/sources, changed sources and missing live guards fail
before mutation. Undo/load, credential retirement and restart cannot restore a
guard from saved provenance. This shares the native
[captured-source action](MESH_APPLICATION.md#applying-to-the-captured-mesh-source),
including verification, durable claims and no generation or automatic retry.


## Saved mesh undo status

`mesh_edit.undo_available` reports whether a desktop Blender history checkpoint
was recorded for a completed saved mesh edit. This applies to REMESH, UV and
RETEXTURE and PARTS through `mesh_edit` and `mesh_source` review. Respect Blender's Global
Undo and history limits; a false value does not mean application failed or may
be repeated. Headless application does not create desktop history.

Undo/Redo restores scene data without replaying service calls or changing durable
job/application/spending records. The transient `mesh_edit` status becomes null
after a history change, including Redo; it is not rebound by object name.
History changes discard live target authority,
so another local application requires fresh destination review. See the
[full history contract](MESH_APPLICATION.md#native-undo-for-saved-mesh-edits).


### Saved parts application

Use `mesh_policy: PARTS` with `purpose: mesh_edit` or `mesh_source` and one
explicit saved GLB asset. Review that every mesh in this artifact is intended as
a part. The source retains its object identity and becomes an empty mesh parent
with 2 to 128 named static children; Keep original defaults to true. The same
explicit coordinate mapping, target checks, durable claims and undo limits apply.
`mesh_edit.parts` reports the child names while the live application is valid;
history invalidation clears the transient mesh status without resetting the job.
Do not reconstruct authority from those names. See the
[parts contract](MESH_APPLICATION.md#apply-static-parts) for limits and rollback.


## Attaching a returned rig

Use `mesh_policy: RIG` with `purpose: mesh_source` for the unchanged original
exported source, or `mesh_edit` for a newly reviewed destination. Show the named
source, coordinate mapping and Keep original choice. The source must be unrigged;
one returned mesh and armature must have exactly matching indexed geometry and
normalized bone weights. This preserves source geometry, UVs and materials while
adding the returned skin/rig clips. Morphs, mesh animation and incompatible
modifiers/constraints are rejected. Move the source and its new rig group together
afterward. `mesh_edit.rig` names the current session's attached armature; it is not
a durable lookup authority after undo/load. The shared native history and
receipt-only recovery rules apply. See [the RIG contract](MESH_APPLICATION.md#attach-a-returned-rig)
for bounds and provider/retargeting limitations.


## Blockout plan commands

`estimate_blockout` reads the current scene's native Blockout description, type,
scale and previous plan for DESIGN or REFINE. It returns an exact free quote;
`approve_blockout` requires that quote and unchanged decimal cost, then persists
one intent before submission. Changed fields, scenes or credentials reject the
approval. UI and MCP use the same facade and job session. Complete returned JSON
updates only the unchanged original scene's stored plan; geometry is built by a
separate explicit local **Build plan** action.

After failure or restart, use `list_local_jobs` for context/revision and
`job_status` for saved asset IDs. `read_model_text` retrieves one selected full
text output without spending or applying it to a scene. Incomplete previews must
be downloaded successfully; truncated JSON prefixes are not plans. For native recovery, choose **Read saved Blockout plan** in saved jobs, then
**Use saved Blockout plan** to review the destination and whether its existing
plan will be replaced. This does not change geometry or spend credits.

MCP uses `prepare_blockout_plan` with the current context and saved revision,
then `blockout_plan_status` until ready. Show the scene, element/group counts and
replacement flag before explicit `apply_blockout_plan` approval. The handle is
single-use and bound to the unchanged destination and saved record. Pass
`discard: true` to the status command to discard a finished review. The complete
plan stays in memory until approval; no result text is stored in job metadata.
Use native **Build plan** separately for geometry. Native plan application has
Undo; MCP consumers retain the same scope and destination guards without a
promise of native Undo for direct tool calls.

## Cloud history and scoped saved results

`list_generations` returns `local_request_ids` for cloud rows matched to the
selected credential-bound store. All cloud rows expose empty `local_files`; use
`list_local_jobs` and the returned request identity for current status/revision
and explicit result preparation/approval. Matching is refreshed even when the
cloud page was loaded before a local remote-job acknowledgement.

`job_status`, `wait_for_job` and the old `import_result` lookup prefer a matching
scoped record to an old unscoped cache. `import_result` rejects direct application
of both saved jobs and prototype cache entries. Ambiguous remote IDs require a
local request ID, and a failed store read never falls back to cached import.
Cold prototype-only status reads retain their existing behavior; no prototype
registry migration is performed.

For an unsaved successful model row, call `recover_cloud_job(job_id, model_id)`.
The shared SDK read verifies the current remote job/model and saves a scoped
cloud result. Pending UI/MCP reads for that job/model share one worker. Repeated
reads preserve the existing intent, result receipts and application history,
including after restart. The response returns context, request ID and revision.
Read failures may be explicitly retried; this never retries generation.
Use `recover_local_job(action: resume)` to download, then prepare and approve the
result destination. The recovery read does not download files or mutate a scene,
and it rejects delivery into a changed credential context.

### Film task commands

Film is experimental. Every Film tool description says so, matching the native
panel header and Studio's Film pages; the commands remain available.

`film_recipe` loads or inspects the native scene's validated recipe and stable
production identity. Loading preserves identity; `new_production` deliberately
starts another production without submitting anything. Save the blend file.
`estimate_film_task` uses that identity and task name to return resolved inputs
and an exact shared SDK quote. `approve_film_task` consumes the quote with its
verbatim CU cost before durable submission. `discard_film_estimate` releases an
unused quote. `bind_film_upload` saves an immutable reference to an unchanged
imported upload observed through `list_reference_uploads`.

If a scene switch interrupted the estimate response, return to the original scene
and call `film_recipe` with `action: inspect`. A `quoted` task returns the existing
`quote_id`, `model_id`, `parameters` and `cu_cost_exact` for approval or discard.
Inspection completes already-admitted preparation but never requests a new price;
stale quotes are omitted. Pending preparation appears as `quoting` or `binding`.
Saved upload associations remain visible as `bound` after an interrupted response.
Identical binding retries are revalidated; a different upload or revision is
rejected before replacing an already-bound task's displayed status.

Recipe management, inspection and upload association are local operations with
no platform equivalent. Estimate/approval use the same model operations as
`estimate_cost`/`generate`, through the shared session. Use `job_status`,
`wait_for_job`, explicit recovery and application for saved results; Film does
not auto-import or replay uncertain tasks. These commands do not construct scenes,
capture shots, assemble media or export a finished film.

### Film shot commands

`film_shot_sources` lists eligible saved GLBs for each hero and returns the
current context token. `prepare_film_shot` binds explicit per-hero asset/job
revision selections to that context, production, recipe and destination.
`film_shot_review` polls verification status without building; its other actions
discard unapproved work, save known receipts or dismiss an uncertain review after
explicit inspection (`inspected: true`). Dismissal never clears a durable claim
and refuses pending receipt handles. `build_film_shot` separately approves one
ready review, claims all sources and builds a new scene while retaining the
working scene. It must not be repeated after uncertainty.

These four local Blender commands have no platform equivalent and make no
generation/download request. They share native UI review handles but do not add a
native operator Undo entry. Timeline approval uses the commands below;
capture and export remain separate.

### Film capture commands

Inspect `film_capture_sources(production_id, shot_id)` and choose an opaque
source handle. `prepare_film_capture` requires that handle and context identity,
with still/video, dimensions and color mode. Show the exact returned settings
for approval before `render_film_capture(review_id)`. Rendering consumes that
review once and returns immediately; `film_capture_review` polls, cancels local
work or explicitly discards its private files after work stops.

Once CAPTURED, review the local output and ask for separate upload approval
before `upload_film_capture`. Staging checks its content hash before remote
initialization. Poll the ordinary `reference_upload_status` handle, inspect
uncertainty without retry, then explicitly `bind_film_upload` after import.
Neither local rendering nor uploading grants generation approval.
These tools use the [same native capture owner](FILM_PLAN.md#shared-capture-and-upload-approval).
Reviews expire with the session, capture files are cleaned on shutdown and
interrupted captures never resume automatically.

### Editable Film timeline commands

`film_timeline_sources` returns current-context opaque scene choices for every
recipe shot. `prepare_film_timeline` requires that context, production and a
complete shot-to-source-ID mapping. `build_film_timeline` separately approves
the resulting review, rechecks unchanged local scenes and creates a new editable
scene-strip sequence. The working scene stays selected. Later edits to the
referenced shots affect the timeline.

`film_timeline_review` reads status or discards a review; uncertain partial
cleanup requires `inspected: true` and must never be replayed automatically.
These four local commands have no platform equivalent, make no service call and
never change saved jobs or import result files. Local scene markers establish
recipe compatibility, not service provenance. They share the native command
owner but do not create a native operator Undo entry. Capture and review assembly
use the separate commands in this section; video export remains unavailable.

### Film composition commands

Inspect `film_recipe` for the selected context and production, then call
`prepare_film_composition` with final/previs mode. Poll `film_composition_review`
until local saved-media verification is READY. `estimate_film_composition` returns
the resolved model payload and full `cu_cost_exact`; obtain explicit approval of
both before `generate_film_composition(review_id, approved_cost)`.

Preparation needs retained upload files or downloaded results and installed
`ffprobe`; it never uploads or downloads missing sources. The reviewed recipe
and original scene stay unchanged. Pricing/submission use the existing shared SDK
model path. Cancel/discard release preparation or approval, preserving saved jobs
and media. On an error, lost response or restart, inspect the recipe's declared
master job and use ordinary saved-job recovery; never repeat uncertain generation.
These tools share [native composition review](FILM_PLAN.md#native-and-mcp-composition-controls).
Synthetic native interaction passes on macOS Blender 5.1.2; live provider and
other OS/DPI acceptance remain pending. Review assembly uses the commands below.

### Film review commands

Inspect `film_recipe` for the selected context and production, then call
`prepare_film_review` with final/previs mode and an explicit optional
`include_master`. Poll `film_review_status` until READY. Show its timing,
shot/source/audio-segment counts, private copy size and master inclusion, and
obtain explicit build approval before `build_film_review(review_id)`. Building
needs a Blender window in Object Mode; an Edit Mode rejection keeps the review.

Preparation copies retained upload files or downloaded results into private
extension storage and needs installed `ffprobe` and matching frame rates; it never
uploads, downloads, generates or claims. Recipe, frame, scene or connection changes
invalidate the review and delete its copies; scene changes include selecting, adding
or editing objects. Building one review also invalidates any other unbuilt review
for the same scene, so prepare and build one at a time. Keep the recipe scene
selected until building: selecting another scene and then the recipe scene again
also invalidates it. `WAITING` means preparation finished while another scene was
active; a return through the scene selector turns it into `ERROR`, so prepare again.
Building consumes the review, saves application claims for generated sources and
creates a new scene while the working scene stays selected. `film_review_status` can
cancel preparation, discard an unbuilt review's copies, `retry_receipt` for a known
saved outcome or dismiss an inspected uncertain review with `inspected: true`; none
rebuilds or clears a saved claim. An uncertain review blocks new preparation for its
scene until dismissed.

These three local commands have no platform equivalent, make no service call and
share the [native review controls](FILM_PLAN.md#native-and-mcp-review-controls).
They do not create a native operator Undo entry. Handles expire with the session.
Installed synthetic tests cover them; desktop interaction, live media and video
export remain pending.


## Workflow execution

Use `list_workflows` for a private or public catalog and `workflow_schema` for
its declared inputs. Listing reads the full bounded catalog, deduplicates IDs
and returns at most 40 filtered rows with `next_offset`. A new call refreshes
metadata, so pages are not a stable snapshot. Inputs retain conditional and file
definitions; supported form validation happens again with fresh metadata at
estimation. File parameters use already uploaded Scenario asset IDs.

`estimate_workflow` requests a free exact quote through SDK 2.2.0
[`workflows.run`](https://docs.scenario.com/api/python/resources/workflows/methods/run)
with `dry_run="true"` in the query. It returns the original `parameters`, the
normalized `payload` including defaults, and `cu_cost_exact`. Review that payload
and price. `run_workflow` requires its `quote_id`, the same workflow and original
parameters, and that exact decimal string as `approved_cost`.

Approval is bound to the current scene revision, file, credential and project.
It is consumed before local persistence and the single paid dispatch. A timeout
or failed write never permits reusing it. Inspect `job_status` and
`list_local_jobs`; closing a view does not stop admitted work. Known jobs use the
same polling, download, explicit application and restart recovery as model jobs.
Workflow results are never automatically imported. `discard_workflow_estimate`
releases only a ready local approval, leaving saved jobs unchanged.

General workflow cancellation and interactive approval/selection nodes are not
exposed. Workflow authoring, the expanded Studio form and live provider/output
acceptance remain incomplete. Do not substitute node rejection for cancellation
or infer live compatibility from the synthetic installed command tests.


## Asset library metadata

Use `list_assets` to read one page of assets accessible in the configured
credential/project scope. `public: true` instead requests the public library.
An optional `collection_id` narrows listing. Continue with the returned
`next_pagination_token` and the same filters; no cursor is followed automatically.

Use `search_assets` with nonempty `query` text for server-side asset search.
Continue with the returned `next_offset`, keeping query, public selection and
limit unchanged. The estimated total is not a stable snapshot, and changes to
the library can change later results. Each call is bounded to 100 rows.

Both commands return reference metadata: asset ID, name, description, MIME and
generation types, tags and collection IDs. Download URL fields, account records
and indexed text bodies are omitted. Search text can be incomplete, so it is
never exposed as a complete text asset. These calls do not download, upload,
generate, apply results or change collection/tag organization. Returned asset IDs
can be used in supported model/workflow parameters before a fresh exact quote.
Scene/session changes reject stale delivery; an explicit retry repeats only a
read. Native Library presentation and integrated attachment remain pending.
