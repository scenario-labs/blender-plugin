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
The prototype generation path does not yet require a stored approved quote.

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
| `list_models` | List the loaded lane catalog, with curated models first and at most 40 matches. | `lane`: string (enum: see tools/list)<br>`query`: string | read-only annotation |
| `model_schema` | Read the model's current form parameters for this Blender extension. | `model_id`*: string | read-only annotation |
| `estimate_cost` | Get the exact CU cost with a dry run that spends no credits. | `model_id`*: string<br>`parameters`: object | read-only annotation |
| `generate` | Submit a generation that spends the user's credits and automatically places its result in Blender. | `lane`*: string (enum: see tools/list)<br>`model_id`*: string<br>`parameters`: object; Model parameters; file parameters take Scenario asset ids | spends credits |
| `job_status` | Read one local generation's status, cost and downloaded files without spending credits. | `job_id`: string; Scenario job id (job_...) or the local_id returned by generate<br>`id`: string; Same as job_id, kept for compatibility | read-only annotation |
| `wait_for_job` | Wait for one tracked generation using a client-side status loop in Blender. | `job_id`: string; Scenario job id (job_...) or the local_id returned by generate<br>`id`: string; Same as job_id, kept for compatibility<br>`timeout`: number | read-only annotation |
| `import_result` | Apply an already downloaded generation again to the current Blender scene and selection. | `job_id`: string; Scenario job id (job_...) or the local_id returned by generate<br>`id`: string; Same as job_id, kept for compatibility | - |
| `capture_reference` | Capture a 1280x720 viewport or camera still and upload it as a Scenario reference asset. | `source`: string (['VIEWPORT', 'CAMERA']) | GUI required |
| `list_generations` | List recent cloud generations using this Blender runtime's loaded history. | `limit`: integer | read-only annotation |
<!-- tools:end -->

## Security model

The Blender integration binds only to `127.0.0.1`. MCP operations require the
bearer token, checked with a constant-time comparison. `/health` is unauthenticated
and reports availability, Blender version and server name/version. Native clients
may omit Origin; a supplied Origin must be an HTTP(S) loopback origin. Other
origins and browser CORS preflights are refused. This is local access control,
not a promise that a token-holding program is safe.

**Allow connected agents to run Python** is off by default and fails closed if
preferences are unavailable. With it off, an authorized agent can still read
and change the scene, capture/upload a reference and request paid generation.
Require an estimate and explicit spending approval. If a generation call times
out, inspect job status; do not submit it again blindly. Client timeouts do not
prove that queued or remote work was canceled.

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
| Wait | `wait_for_job(job_id or id, timeout)`, one job in a blocking local loop | `jobs_wait` |
| Reference upload | `capture_reference(source)`, captures the scene first | `upload_asset`, `upload_asset_complete` for an existing file |
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
  or modify the scene. Prefer short status polls to a long blocking wait.

Maintainers: run `make mcp-docs` after changing tool definitions and
`uv run --locked --no-env-file python tools/gen_mcp_docs.py --check` to detect drift.
