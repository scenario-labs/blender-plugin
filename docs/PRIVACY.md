# Privacy and data handling

Scenario for Blender is a client for your own Scenario account. This page describes
what the extension sends, where it sends it, what stays on your machine, and the
limits of its current controls. It does not replace Scenario's service policies.

## What leaves your machine, and when

- With valid credentials and online access enabled, cost previews send your prompt
  and available model parameters while you edit the visible form, before you press
  Generate. The API request uses `?dryRun=true` to request a price without starting
  a generation. Generate sends the completed request again and can spend credits.
- Attached viewport or camera stills, playblast clips and the Render Result are
  captured or saved and uploaded when you generate. A selected mesh used as a
  reference is exported to GLB, including evaluated modifiers and embedded materials.
  Reference files you attach are uploaded for the requested operation.
- New, Rewrite and Translate send prompt text and model context to Scenario's
  prompt services. Prompt Spark in Render Image and Render Video also receives a
  still of the view. Prompt helpers can spend credits independently of generation.
- The model catalog is requested automatically when credentials are available;
  opening the model picker can download thumbnails. Test connection retrieves team
  and project information. Refresh cloud and Older in Generations retrieve job
  history and prompt text; connected agents can request history too.
- Scenario API requests authenticate with your selected key/secret pair using an
  HTTP Basic `Authorization` header over TLS. They identify the extension with
  `ScenarioBlender/<version>`. Signed storage transfers use the URL's authorization;
  they do not forward the Scenario API key/secret header.
- An agent connected to the local MCP server can request scene information,
  captures, uploads and paid generations on your behalf. Its own service may
  receive what that agent reads from Blender.

## Where it goes

The Scenario API is `https://api.cloud.scenario.com`. Upload parts, generated
files, full text results and model thumbnails use content URLs returned by the
service, so content transfers are not limited to the API hostname. The Create a
key in the portal button opens `https://app.scenario.com/team` in your browser.
The local agent connection uses loopback HTTP, described below.

The extension has no telemetry, analytics or automatic crash-reporting service,
and no independent update-check service. Blender manages configured extension
repositories and their update checks separately.

Blender's Allow Online Access setting gates catalog loading, MCP startup and
interactive network actions. It is not an instantaneous network cutoff: work
already started can finish, and the current prototype's thumbnail/download paths
do not all check that setting independently. Close Blender or disconnect the
network when you need a complete cutoff. These gaps remain part of the
[shared-runtime integration](https://github.com/scenario-labs/blender-plugin/issues/65).

## What is stored on your machine

When Credentials is set to Saved in Blender, Blender saves the key and secret in
`userpref.blend` as plain text. Password fields hide their display; they do not
encrypt storage or use an OS keychain. Standard preference locations are:

- Linux: `$HOME/.config/blender/X.Y/config/userpref.blend`
- macOS: `/Users/$USER/Library/Application Support/Blender/X.Y/config/userpref.blend`
- Windows: `%USERPROFILE%\AppData\Roaming\Blender Foundation\Blender\X.Y\config\userpref.blend`

Portable installations and custom Blender resource paths can use another location.
To avoid saving the pair in Blender, select Credentials > Environment and launch
Blender with both `SCENARIO_API_KEY` and `SCENARIO_API_SECRET`. This source is
explicitly selected; it does not override or combine with saved credentials.
Switching sources does not erase values already saved in Blender. Clear both
saved fields and save preferences to remove them there; also check backups and
how your launcher stores environment variables. Rotate the key in Scenario if
it leaks or a machine holding it is lost.

Generated files go to the Output Folder, normally `~/Downloads/Scenario`, grouped
by kind and day. The extension's own user directory under Blender's extensions
folder holds `state/jobs.json`, including job requests and prompts, and caches:
`cache/captures`, `cache/exports`, `cache/thumbs`, `cache/models` and
`cache/list_public.json`. Scene properties, imported media and prompts can also
be saved in your `.blend` file. Uninstalling is not a promise to erase these files;
delete the extension's user directory yourself for a clean removal and remove
outputs or `.blend` copies separately. Local deletion does not delete cloud jobs
or assets.

Extension logs go to Blender's console; it does not configure its own log file.
A terminal or host application may retain that output. Diagnostics can include
file paths, job identifiers and service errors; review them before sharing.
Agent setup snippets contain the local session token. Do not assume logs,
clipboard history or screenshots are safe to publish without inspection.

The clipboard is written by Copy buttons (asset IDs, errors and MCP setup) and by
copy/cut in the composer; it is read when you paste into the composer. Clipboard
managers may retain copied tokens or text. Play opens media locally in Blender's
player or your system player.

## The local MCP server

The server binds to `127.0.0.1`, using the port selected in Preferences (default `9876`). Calls
require the local session token. Blender normally generates it for the session;
an explicitly supplied token must be changed by its owner. This is a local
connection, not Scenario's API credential, and programs holding it can read the
scene, take captures and request generation that spends your Scenario credits.
The prototype's `estimate_cost` and `generate` are separate actions; its current
MCP interface does not itself enforce approval of a previously displayed quote.
Only connect agents you authorize to perform those actions.

Arbitrary Python execution is disabled by default. Enabling it gives a connected
agent code execution in Blender with your user's permissions. That switch is not
a sandbox for Python or for the other scene and generation tools. The
[MCP reference](MCP.md#security-model) describes access controls and connection setup.

## Terms

Scenario service use is covered by its [Terms and Conditions](https://www.scenario.com/terms-and-conditions)
and [Privacy Policy](https://www.scenario.com/privacy-policy), subject to any
applicable account agreement. Security and compliance information is available
in the [Scenario Trust Portal](https://trust.scenario.com). Consult
[Scenario documentation](https://docs.scenario.com) for account and API access
requirements. This extension note describes local behavior; service retention,
processing and contractual commitments are governed by those service policies.
