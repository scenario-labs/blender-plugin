# Scenario for Blender

[![Release](https://img.shields.io/github/v/release/scenario-labs/blender-plugin)](https://github.com/scenario-labs/blender-plugin/releases)

**Status: experimental.** A Blender 5.0+ extension that brings [Scenario](https://scenario.com) image, video, 3D and PBR material generation into the viewport, generates audio for the sequencer, renders the scene as a finished still or clip (Render Image / Render Video, with Prompt Spark writing the look and a 20-move camera path library), edits the selected mesh with Scenario's 3D tools (remesh, retexture, UV unwrap, rigging, animate, parts), offers Prompt Spark / Rewrite / Translate next to every prompt and a model picker with Scenario's own taxonomy (no LoRAs), and runs a local MCP server so agents (Claude Code, Cursor, Claude Desktop, Codex) can build and generate in the open scene. Python extension with pinned SDK dependency wheels, GPL-3.0-or-later. You need a Scenario account and an API key (Pro plan or above).

**User guide: [`docs/USER_GUIDE.md`](docs/USER_GUIDE.md)**. Changelog: [`CHANGELOG.md`](CHANGELOG.md).
See [known limitations](docs/KNOWN_LIMITATIONS.md) and the [documentation index](docs/index.md).

Quick start: download `scenario-<version>.zip` from the releases (or run `uv run --locked --no-env-file python tools/build.py`), drag it onto Blender, paste your key in Preferences > Add-ons > Scenario, press N in the 3D viewport and open the Scenario tab. For automated releases, verify your download with `gh attestation verify scenario-<version>.zip -R scenario-labs/blender-plugin` and check `SHA256SUMS` ([details](docs/USER_GUIDE.md#verify-your-download)). See the [documentation index](docs/index.md) for current architecture, development guidance and historical context.

---


**For contributors and coding agents:** read [AGENTS.md](AGENTS.md), the canonical
rulebook shared through `.claude/CLAUDE.md`, and [CONTRIBUTING.md](CONTRIBUTING.md).
See [commits, branches and pull requests](CONTRIBUTING.md#commits-branches-and-pull-requests)
for the review workflow and PR checklist.
Canonical [agent tools](docs/development/agents.md) describe the shared skills and commands.

## Why

Bring Scenario's generation into the Blender viewport so creators stay in one tool. Decisions taken 2026-08-28: API key + secret first (OAuth later, feasible via mcp.scenario.com dynamic client registration), v1 extras = render-to-real + Patina materials, native N-panel plus a floating composer, skyboxes and the Scenario-only 3D utilities (retopo, retexture, rigging, motion) in v2.

## Files

- `docs/USER_GUIDE.md` and `docs/images/`: the maintained user guide and screenshots.
- `docs/handbook-template.html` and `tools/build_docs_html.py`: render that Markdown with `make docs`; see [documentation builds](CONTRIBUTING.md#documentation-builds) for website and single-file outputs.
- `docs/engineering/design-v1.md`: the v1 design (architecture, lanes, phases, tests).
- `docs/MODEL_PAYLOAD_AUDIT.md`, `docs/UI_STYLE.md`: the model-payload audit and the UI style guide.
- `tests/fixtures/`: recorded model schemas and a real Patina Material job (6 maps) used as test fixtures.
- `versions/`: previous states of deliverables (v0 = idea-stage README).
- [`.env.example`](.env.example) and [developer environment setup](CONTRIBUTING.md#environment-variables): explicit test credentials for live tools.
- `scenario/`: the extension source (`core/` is plain Python, `blender/` is the bpy glue). `blender_manifest.toml` at its root.
- `tests/unit/` (pytest, no Blender), `tests/blender/` (run inside `blender --background`), `tests/smoke/` (opt-in, spends credits), `tests/fixtures/` (recorded API records and a real Patina job).
- `tools/build.py`, `tools/install.py`, `tools/record_fixtures.py`, `tools/gui_screenshot.py`, `tools/blank.blend`. `dist/` (ignored) holds built zips.
- `docs/engineering/plans/`: P0 and P1 implementation plans (executed task by task).
- `CHANGELOG.md`: what shipped per phase.

## Run it

1. `uv run --locked --no-env-file python tools/install.py --launch` builds, validates and opens the extension in a fresh isolated development profile. For normal use, install the release ZIP through Blender.
2. Blender > Edit > Preferences > Add-ons > Scenario: paste an API key and secret (Scenario portal > Team > API Keys, Project or Team scope), press Test connection.
3. In the 3D viewport press N, open the Scenario tab (or the Scenario button in the viewport header), pick a model, type a prompt, read the CU price on Generate, generate.

## 3D results: one mesh per job

Providers return several variants of one result (Meshy: GLB + OBJ + texture PNGs; Rodin with `material=All`: a shaded GLB and a PBR GLB). The add-on imports one primary mesh (glTF first, then the variant with the most PBR textures), switches the viewport to Material Preview so textures show, and lists the other mesh files in Generations with an Add button (plus Add to scene and Select for the primary mesh). Rodin defaults to `PBR`. Root causes and the fix are in `CHANGELOG.md` 0.5.1.

## Floating composer

A pill at the bottom of every 3D viewport shows the current prompt and a Generate button; click it to expand lane tabs (Image, Video, 3D, Materials, Render Img, Render Vid), an editable prompt with real text selection (click, drag, Shift+arrows, double-click, Ctrl/Cmd+A/C/X/V; Enter generates, Esc blurs), the model chip (opens the model picker), a Settings chip (opens the sidebar) and the live CU quote. The composer is the quick path; every setting lives in the sidebar, which the header "Scenario" button opens. The sidebar tab has four panels: Scenario (lane tabs), Jobs, Generations, Agents (MCP). If drawing ever fails repeatedly the composer switches itself off; re-enable it in Preferences.

## Install from a repository (updates through Blender)

`uv run --locked --no-env-file python tools/build.py --repo` builds `dist/repo/` (index.json, the zip, an HTML listing). Host that folder on any static HTTPS server, then in Blender: Preferences > Get Extensions > Repositories > add the `index.json` URL (requires Allow Online Access). Updates then appear in Blender's own updater. The Extensions store itself is not an option for an account-gated add-on (ToS 3.10 / 4.3), see the spec.

## Agents (MCP)

The local `scenario-blender` server connects an authorized agent to the open
scene and generation into it. The hosted `mcp.scenario.com` server provides
platform-wide collections, training, workflows and usage; connect both when
needed. Copy client setup from **Scenario > Agents (MCP)**, and use the
[MCP reference](docs/MCP.md) for tool contracts, complete client examples,
headless setup, token handling and the security model.
For headless use, run `blender --background scene.blend --command scenario_blender`;
see the reference for token configuration and online-access requirements.

## What leaves your machine

Cost previews send prompts and parameters to `https://api.cloud.scenario.com` while you edit, before Generate.
Generation and prompt tools can upload attached files, scene captures or exported meshes and spend credits.
Catalogs and thumbnails load from Scenario; cloud history loads when requested.
Saved keys, prompts, job state and media remain in Blender preferences, extension storage or output files.
Connected local agents can read your scene and request paid work using your account.
Read [Privacy and data handling](docs/PRIVACY.md) for destinations, storage, clipboard use and current limits.

## Tests

- Python environment, linting and formatting: [`docs/PYTHON_STYLE.md`](docs/PYTHON_STYLE.md), `uv sync --locked`, `make lint` and `make format`.
- `make test`: unit tests (pytest, no Blender).
- `make test-blender`: build, validate and test an exact ZIP in a fresh disposable profile, including imports and authenticated MCP. See the [native test loop](CONTRIBUTING.md#native-blender-test-loop) for coverage, artifacts and binary selection.
- Paid smoke scripts: see [live commands and authorization](CONTRIBUTING.md#live-commands).
- GUI checks require an isolated profile and native interaction review; see [validation](docs/development/validation.md).


## Commit messages and PR titles

Every change lands by a squash-merged pull request, so the PR title becomes the commit header on `main`. Titles and commit messages follow [Conventional Commits](https://www.conventionalcommits.org): `type(scope): summary`, imperative, at most 120 characters, no em dashes. `commitlint.config.ts` is the single source of truth (types from `@commitlint/config-conventional`, the scope list, the no-em-dash rule). CI lints the PR title with it (`pr-title`, in `.github/workflows/pr-name.yml`) and the branch commits (`commits`, in `.github/workflows/commitlint.yml`). Node is not part of the checkout; to run the same check locally:

```
npm install --no-save --no-package-lock --no-audit --no-fund @commitlint/cli@21 @commitlint/config-conventional@21 @commitlint/types@21
printf '%s\n' "feat(ui): my title" | npx --no-install commitlint --config commitlint.config.ts --verbose
```

## Verified vs assumed

Verified live (2026-08-28): REST Basic auth, model records carry UI schema, `?dryRun=true` cost preview, Patina returns 6 typed map assets, multipart upload flow, GLB asset shape, OAuth dynamic registration on mcp.scenario.com. Assumed: Patina smoothness semantics (pixels suggest dark = rough), normal-map convention. Native runtime compatibility on Blender 5.0, 5.1 and 5.2 must be verified separately from release ZIP validation.

## Support

Read the [user guide](docs/USER_GUIDE.md) first. [SUPPORT.md](SUPPORT.md) says
where to ask a question, how to file a bug and what to include. Account, billing,
credit and security matters go to [support@scenario.com](mailto:support@scenario.com),
never to a public issue.

## Security

Report vulnerabilities privately, see [SECURITY.md](SECURITY.md). Never paste API keys, MCP bearer tokens or signed asset URLs into issues or pull requests.

## Licence and provenance

GPL-3.0-or-later (see `LICENSE`), the licence Blender requires for add-ons that use `bpy`. The extension zip carries a copy of the licence text (`scenario/LICENSE`, identical to the root `LICENSE`). Pinned SDK dependencies and their notices are described in [`docs/SDK_BUNDLE.md`](docs/SDK_BUNDLE.md). The MCP bridge follows the Blender Lab `blender_mcp` protocol shape, rewritten.

The GPL grants no trademark rights: "Scenario" and the Scenario logo belong to Scenario Inc., and Blender is a registered trademark of the Blender Foundation; this extension is not affiliated with or endorsed by the Blender Foundation. See [TRADEMARKS.md](TRADEMARKS.md).
