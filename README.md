<p align="center">
  <a href="https://scenario.com"><img src="docs/images/scenario-logo.png" height="84" alt="Scenario"></a>
</p>
<h1 align="center">Scenario for Blender</h1>
<p align="center">
  <a href="https://github.com/scenario-labs/blender-plugin/releases"><img alt="Latest release" src="https://img.shields.io/github/v/release/scenario-labs/blender-plugin"></a>
  <a href="LICENSE"><img alt="Licence GPL-3.0-or-later" src="https://img.shields.io/badge/license-GPL--3.0--or--later-blue"></a>
  <img alt="Blender 5.0 and later" src="https://img.shields.io/badge/Blender-5.0%2B-orange">
  <a href="https://docs.scenario.com"><img alt="API documentation" src="https://img.shields.io/badge/documentation-api-black.svg"></a>
  <a href="https://help.scenario.com"><img alt="App documentation" src="https://img.shields.io/badge/documentation-app-black.svg"></a>
  <a href="https://mcp.scenario.com/docs"><img alt="MCP documentation" src="https://img.shields.io/badge/documentation-mcp-black.svg"></a>
  <a href="https://scorecard.dev/viewer/?uri=github.com/scenario-labs/blender-plugin"><img alt="OpenSSF Scorecard" src="https://api.scorecard.dev/projects/github.com/scenario-labs/blender-plugin/badge"></a>
</p>

**Experimental.** Bring Scenario image, video, 3D, PBR material and audio generation
into Blender. Use scene captures and selected meshes as inputs, explore camera
moves, and turn a written scene description into a greybox layout with Blockout.
A compact composer, sidebar and local MCP server provide access from your scene.
This is a Python extension with pinned SDK dependency wheels, licensed
GPL-3.0-or-later. Read the [known limitations](docs/KNOWN_LIMITATIONS.md) before
relying on a workflow; shared runtime and interface adoption remain in progress.

![The Scenario sidebar with all creation tabs and a clearly labelled offline Image example](docs/images/panel-image.png)

## Requirements

- Blender 5.0 or later, as declared in the [extension manifest](scenario/blender_manifest.toml).
- A Scenario account with API access, an API key and its secret. See
  [Obtain your API key](https://docs.scenario.com/get-started/documentation/quick-start-guide/step-1-obtain-your-api-key)
  and [Scenario help](https://help.scenario.com) for current account requirements.
- An internet connection and Blender's **Allow Online Access** setting enabled
  under Edit > Preferences > System > Network before contacting Scenario.
- Scenario generations and prompt helpers consume Creative Units (CU). Review
  the displayed estimate before Generate; models, parameters and references
  affect the cost. See [costs](docs/USER_GUIDE.md#costs) and the limitations above.

## Install

1. Download `scenario-<version>.zip` from the
   [releases page](https://github.com/scenario-labs/blender-plugin/releases). Keep it zipped.
   [Verify the download](docs/USER_GUIDE.md#verify-your-download) when checksums and
   attestations are supplied with that release.
2. Drag the ZIP onto a Blender window, or use Edit > Preferences > Get Extensions
   > Install from Disk. The extension appears as "Scenario" in Blender's Add-ons list.
3. In Scenario, open Organization settings > API Keys > Add API Key and follow
   the instructions to obtain the key and secret.
4. Open Edit > Preferences > Add-ons > Scenario. Leave **Credentials** set to
   **Saved in Blender**, paste the key and secret, then press **Test connection**.
   Choose an Output Folder for generated files.

### Updates

A ZIP installed from disk uses Blender's local repository and does not receive
automatic updates from Scenario. Install a newer release ZIP the same way and
restart Blender. An official hosted extension repository and its native update
controls are still [in development](https://github.com/scenario-labs/blender-plugin/issues/37).

### Why not extensions.blender.org

The [Blender Extensions terms](https://extensions.blender.org/terms-of-service/)
restrict extensions whose functionality depends on external registration, keys
or payments, including access to external services. Scenario requires an account
and API credentials, so this extension is distributed through GitHub releases.
Its manifest declares the permissions it uses and their reasons.

## Quick start

In the 3D viewport, press **N** and open **Scenario**, or use the Scenario button
in the viewport header. Pick a lane and model, enter a prompt, add any required
reference and inspect the estimate before Generate. Results appear in Generations
and your Output Folder, with actions for viewing or importing supported media.
The [user guide](docs/USER_GUIDE.md) describes each lane and its controls.

## Features

- [Image](docs/USER_GUIDE.md#image): generate from text or reference images and use results as textures or references.
- [Video](docs/USER_GUIDE.md#video): generate from prompts, images or scene playblasts.
- [3D](docs/USER_GUIDE.md#3d): generate meshes or apply provider edit tasks to an exported selection. Safe in-place editing remains incomplete.
- [Materials](docs/USER_GUIDE.md#materials): generate PBR maps for selected meshes.
- [Audio](docs/USER_GUIDE.md#audio): generate speech, music or sound effects and add results to the sequencer.
- [Render Image](docs/USER_GUIDE.md#render-image): use a scene capture and look references to produce a still.
- [Render Video](docs/USER_GUIDE.md#render-video): work with timeline captures, a camera path planner and style references.
- [Blockout](docs/USER_GUIDE.md#blockout): turn a scene description into a greybox layout, then refine or rebuild it.
- [Prompt tools and model picker](docs/USER_GUIDE.md#the-form): browse models and prepare prompts; prompt helpers can spend credits.
- [Floating composer](docs/USER_GUIDE.md#the-floating-composer): access the current lane from the viewport.
- [Generations](docs/USER_GUIDE.md#generations): inspect local results and available project history.

## Agents (MCP)

The local `scenario-blender` server connects an authorized agent to the open
scene and generation into it. The hosted [mcp.scenario.com](https://mcp.scenario.com)
server provides platform-wide collections, training, workflows and usage without
requiring Blender; connect both when needed.

The default local endpoint is `http://127.0.0.1:9876/mcp`. **Agents (MCP)** shows
its status and bearer token and provides client setup for Claude Code, Cursor,
Claude Desktop and Codex under the name `scenario-blender`. Treat the token and
copied setup as secrets. Connected agents can read the scene and request paid
work; arbitrary Python execution is a separate opt-in permission, disabled by default.

Use the [MCP reference](docs/MCP.md) for complete client setup, tool contracts,
security controls and headless configuration. The headless entry point is:

```sh
blender --background scene.blend --command scenario_blender
```

### Authentication

Scenario API requests use an API key and secret. Saved Blender credentials are
the default; **Credentials > Environment** explicitly selects an environment
pair instead. The extension does not provide browser OAuth sign-in. The hosted
Scenario MCP service has its own authentication, described in its linked docs.
Blender stores saved credentials in its preferences, not an OS keychain.

## What leaves your machine

Cost previews send prompts and parameters to `https://api.cloud.scenario.com`
while you edit, before Generate. Generation and prompt tools can upload files,
scene captures or exported meshes and spend credits. Catalogs and thumbnails
load from Scenario; cloud history loads when requested. Saved keys, prompts,
job state and media remain in Blender preferences, extension storage or output
files. Connected local agents can read your scene and request paid work using
your account. Read [Privacy and data handling](docs/PRIVACY.md) for destinations,
storage, clipboard use and current limits.

## Documentation

Start with the [user guide](docs/USER_GUIDE.md), [known limitations](docs/KNOWN_LIMITATIONS.md)
and [changelog](CHANGELOG.md). The [documentation index](docs/index.md) links
architecture, integration status and developer references. A public HTML handbook
URL will be added when its hosting is available. Build HTML from the maintained
Markdown with `make docs`; see [documentation builds](CONTRIBUTING.md#documentation-builds)
for website and single-file outputs.

## Staying up to date

Follow [releases](https://github.com/scenario-labs/blender-plugin/releases), or
choose **Watch > Custom > Releases** on GitHub for release notifications.

## Support

Use [Support](SUPPORT.md) for bug reports, feature requests and the information
to include. Account, billing and API-key questions go to support@scenario.com
or Scenario's in-app support. Never post credentials, bearer tokens or signed
asset URLs in a public issue.

Report vulnerabilities privately through **Security > Report a vulnerability**
or the contact in [Security](SECURITY.md); do not open a public issue.

## Development

Read [Contributing](CONTRIBUTING.md) for the pinned environment, local checks,
portable tools and isolated Blender test loop. [AGENTS.md](AGENTS.md) is the
canonical conventions contract for humans and agents; [agent tools](docs/development/agents.md)
describes the shared commands. Follow the [Code of Conduct](CODE_OF_CONDUCT.md).
Optional local hooks are installed with `make hooks`; see [installation and scope](CONTRIBUTING.md#optional-local-hooks).
Offline tests need no Scenario account. Live smoke tests spend credits and
require explicit authorization; they are outside the default checks.

Native CI covers Blender 5.0.1, 5.1.2 and 5.2.1 on Linux and Windows for pull
requests. A separate informational workflow schedules Blender 5.1.2 checks on
macOS Apple silicon and Windows x64 weekly; see [run evidence and maintenance](CONTRIBUTING.md#bumping-the-blender-matrix)
for its first hosted acceptance and failure tracking.

## Sibling integrations

Scenario for Blender is one of several Scenario integrations. The plugins share
the Scenario name, the id `scenario` inside each host's namespace and the support
channel (support@scenario.com), not necessarily the same licence.

- [Scenario for Unity](https://github.com/scenario-labs/Scenario-Unity), Unity package `com.scenarioinc.scenario`. Scenario for Unity is MIT-licensed; this extension is GPL-3.0-or-later because Blender add-ons that import bpy must be GPL-compatible.
- [Scenario skills for agents](https://github.com/scenario-labs/skills) (MIT).
- The [Scenario MCP server](https://mcp.scenario.com) provides Scenario tools outside Blender. The [MCP guide](docs/MCP.md#local-server-and-mcpscenariocom) explains how it relates to this extension's local server.

## Licence

Copyright 2026 Scenario Inc. First-party extension code is free software: you
can redistribute it and/or modify it under the terms of the GNU General Public
License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
It is distributed WITHOUT ANY WARRANTY; see [LICENSE](LICENSE) for the full text.
First-party source headers and the extension manifest declare GPL-3.0-or-later,
and the extension ZIP includes the same GPL text. Bundled dependencies, adopted
sources and assets retain their original licences and notices; see the
[SDK bundle](docs/SDK_BUNDLE.md) and [source adoption](docs/STUDIO_ADOPTION.md).

[Blender's licence guidance](https://www.blender.org/about/license/) requires a
GPL-compatible licence for published add-ons using its Python API. The
[Blender Extensions Platform](https://docs.blender.org/manual/en/latest/advanced/extensions/licenses.html)
requires GPL-3.0-or-later for add-ons it hosts. This project distributes outside
that platform and uses GPL-3.0-or-later for its first-party extension code.

The GPL grants no trademark rights: "Scenario" and the Scenario logo belong to Scenario Inc., and Blender is a registered trademark of the Blender Foundation; this extension is not affiliated with or endorsed by the Blender Foundation. See [TRADEMARKS.md](TRADEMARKS.md).

### Acknowledgements

The local MCP design acknowledges
[Blender Lab's blender_mcp project](https://projects.blender.org/lab/blender_mcp)
(GPL-3.0-or-later, Blender Authors) as a design reference.
Its [project page](https://www.blender.org/lab/mcp-server/) describes
the upstream implementation, which uses a separate stdio MCP server and TCP
connection to its Blender add-on. This extension implements authenticated
loopback HTTP, main-thread tool dispatch and an opt-in Python gate.

The [SPZ reader](scenario/core/scene/spz.py) reads
[Niantic's SPZ Gaussian splat format](https://github.com/nianticlabs/spz).
The [MCP protocol module](scenario/mcp/protocol.py) supports protocol revisions
2025-06-18, 2025-03-26 and 2024-11-05.

The Scenario logo comes from the [official skills repository](https://github.com/scenario-labs/skills/blob/main/resources/scenario-logo.png);
its [original source licence](docs/images/scenario-logo.LICENSE) is retained.
