# Contributing to Scenario for Blender

This guide covers the mechanics of a good contribution.
[AGENTS.md](AGENTS.md) is the conventions contract for humans and agents and
takes precedence where the guides overlap. Read the
[Python tooling guide](docs/PYTHON_STYLE.md) before making changes.

## Before you start

Open an [issue](https://github.com/scenario-labs/blender-plugin/issues/new/choose)
before work beyond a typo so maintainers can agree on the scope. Follow the
[Code of Conduct](CODE_OF_CONDUCT.md). Account, billing and credit questions go
through [Support](SUPPORT.md); report vulnerabilities through
[Security](SECURITY.md), never in a public issue. Current account requirements
belong in the [Scenario documentation](https://docs.scenario.com).

This repository is public and permanent. Keep issue text, PR text, commits and
artifacts publicly shareable: no credentials or MCP bearer tokens, signed asset
URLs, private account/project/workspace identifiers, internal repositories or
hostnames, personal paths, agent session IDs or spend anecdotes. Review generated
fixtures, screenshots and logs before sharing them.

## Set up

Fork the repository if you are not a member, then clone your fork. Install the
pinned uv version from the [Python tooling guide](docs/PYTHON_STYLE.md) and run
`uv sync --locked` from the repository root. uv selects the locked development
interpreter; avoid a separate pip-managed environment.

Blender 5.0 is the extension minimum. Native compatibility is checked separately
on the supported 5.0, 5.1 and 5.2 builds; a system Python test run does not prove
Blender compatibility. On Windows, call the Python tools directly or use Make
from a compatible shell. The [portable tools](#portable-build-install-and-download-tools)
describe binary discovery and explicit `--blender` overrides for every platform.
No Scenario account or credentials are needed for offline unit tests, building
the extension or native tests. Build preparation can download pinned SDK wheels;
the native test processes themselves forbid external network access.

## Run the checks

| Command | Purpose |
| --- | --- |
| `make test` | Locked offline unit tests; Blender is not needed. |
| `make lint LINT_PATHS="path/to/changed.py"` | Check changed Python files with pinned Ruff. |
| `make knowledge` | Validate documentation navigation, local links and evidence metadata. |
| `make build` | Build and validate the exact extension ZIP. |
| `make test-blender` | Build, install and test in a disposable Blender profile. |
| `make install` | Install into a new disposable profile for manual checks. |

The [validation guide](docs/development/validation.md) defines additional checks
for each kind of change and the implemented CI matrices. Test the exact candidate
ZIP, not a previously installed copy. Never use a normal Blender profile for
development builds. UI changes need native input, focus and viewport checks as
well as before/after images; follow [UI style](docs/UI_STYLE.md) and the
[capture procedure](#repeatable-gui-screenshots). A screenshot alone is not
interaction proof. Local hooks are separate tooling under
[#30](https://github.com/scenario-labs/blender-plugin/issues/30); use their
documented install command only when that configuration is present.

Pull requests run offline checks. A fork workflow can wait for a maintainer's
approval to run. Paid/live tools are opt-in and never required PR checks; the
[live-command section](#live-commands) states their authorization boundary.
Follow the current PR check results rather than assuming that a planned
aggregate check or repository protection setting already exists.

## Commits, branches and pull requests

Work on a short-lived `type/issue-description` branch and target `main`.
Keep one concern per pull request. PRs are squash-merged: the title becomes the
commit header, so use `type(scope): summary`, an imperative summary without a
trailing period, and at most 120 characters. Both PR titles and branch commits
are checked with [commitlint.config.ts](commitlint.config.ts).

Use the [canonical contribution guide](docs/development/contributions.md) for
the type definitions, [scope-to-path map](docs/development/contributions.md#scopes),
breaking changes, attribution and review follow-up. Complete the
[PR template](.github/pull_request_template.md) with actual validation evidence
and limitations; human review can remain pending when an agent opens the PR.
Release automation owns version fields and changelog updates. See the
[release procedure](docs/RELEASING.md) for current publication behavior.

## Naming and trademarks

The manifest `name` stays `Scenario` and the `id` stays `scenario`; do not add the
Blender logo as extension branding in icons, docs or listings (see
[TRADEMARKS.md](TRADEMARKS.md)). Forks that ship a modified build must pick their
own extension id and name, unless they have written permission from Scenario Inc.

## Coding and documentation rules

Follow the canonical [repository rules](AGENTS.md), [Python style](docs/PYTHON_STYLE.md)
and [Blender boundaries](docs/architecture/blender.md). Scenario service operations
use the shared official SDK adapter; an exception needs a reproduced SDK gap,
tracking issue and narrow adapter fallback. Keep `bpy` out of `scenario/core`,
Blender operations on the main thread and property writes out of `draw()`.
Use the exact server estimate before spending; REST `dryRun` is a query parameter.
Do not introduce em dashes into maintained text or code.

History lives in Git. Recover older states with `git show <tag>:<path>` or the
release ZIP. Do not preserve retired code or copies of earlier deliverables in
the working tree. [Engineering history](docs/engineering/README.md) is context,
not a current implementation recipe.

Review the [knowledge-maintenance guide](docs/maintenance/knowledge.md) for every
documentation change. Keep current user-facing limits in
[Known limitations](docs/KNOWN_LIMITATIONS.md). Existing canonical guides retain
their names; engineering notes use lowercase filenames and historical plans
retain their date prefix. Follow the [documentation index](docs/index.md) rather
than adding a second copy of a maintained policy.

## Licensing of contributions

By submitting an original contribution you agree that it is licensed under
GPL-3.0-or-later, the licence of this repository (inbound = outbound).
You keep the copyright in your work: there is no copyright assignment, no CLA and no DCO sign-off.
Existing history is not re-signed.

First-party source files carry the SPDX copyright and GPL-3.0-or-later lines
from [scenario/__init__.py](scenario/__init__.py), after a shebang when present.
In a file you materially change or create, you may add your own
`SPDX-FileCopyrightText: <year> <name>` line alongside the existing holder lines;
never remove an existing notice. The [GPL text](LICENSE) remains unchanged.

The copyright holder in every Scenario notice is `Scenario Inc.`, the legal name
in [Scenario's Terms and Conditions](https://www.scenario.com/terms-and-conditions):
`SPDX-FileCopyrightText: <year> Scenario Inc.` in source headers and
`copyright = ["<year> Scenario Inc."]` in `scenario/blender_manifest.toml`.
Do not shorten it to `Scenario`.

Adopted compatible source, fonts, icons, assets and SDK dependencies retain their
original licences and attribution. Identify the source, licence and modifications
in the PR, including when an agent assisted. The first-party licence policy does
not replace third-party notices. Blender's
[licensing guidance](https://www.blender.org/about/license/) requires published
scripts using its Python API to be GPL-compatible; this extension chooses
GPL-3.0-or-later.

## AI-agent contributors

Agents follow the same contribution and licensing rules. Name the contributing
harness in the PR, preserve existing authors and retain accurate co-author
trailers using [the attribution rule](AGENTS.md#codex-commit-attribution), including
in the squash message. A human reviews the complete diff before merge; an agent
may open a reviewable PR with that review explicitly pending. Automated bot
reviews do not constitute human approval.

## How issues are triaged

Maintainers choose the issue type and one primary area, using labels such as
`bug`, `enhancement`, `documentation`, `question` and `area:*`. For defects, include
the observed Blender and OS versions; `needs-repro` or `needs-info` requests
missing evidence. `model-behaviour` distinguishes provider behavior from an
extension defect, while `known-limit` points to the limitations guide.
`good first issue` and `help wanted` identify contribution opportunities.
Maintainers track priority and effort in the Blender Plugin project. Repository
administration and release authorization remain maintainer responsibilities.

### Sibling integration repositories

New Scenario integration repositories are named lowercase `<host>-plugin`
(this repository is `blender-plugin`). The extension or package id is `scenario`
inside the host's namespace: Blender extension id `scenario`, Unity package
`com.scenarioinc.scenario`. Existing repositories keep their names:
`Scenario-Unity` is not renamed because its Git URL is embedded in users' Unity
package manifests. Every integration repository carries a root `LICENSE`,
`CONTRIBUTING.md`, `CODE_OF_CONDUCT.md` and `SECURITY.md`, and the topic `scenario`.

## Optional local hooks

After `uv sync --locked`, run `make hooks` once in each checkout to install the
pre-commit and commit-msg hooks. The equivalent command works without Make:

```sh
uv run --locked --no-env-file pre-commit install --hook-type pre-commit --hook-type commit-msg
```

The hooks run Ruff on staged Python files, check file hygiene and house rules,
guard added staged lines against common secrets, and check the Conventional Commit
type. All tools use the pinned uv development group; no separate hook environment
or Node installation is required. Review and re-stage any formatting changes.
The full commitlint scope/header policy remains in CI.

Run `uv run --locked --no-env-file pre-commit run` to check staged files manually.
`--all-files` also visits existing prototype lint/format debt tracked in #28;
it is not the changed-file CI acceptance scope. Recorded fixtures are excluded
from newline/whitespace rewriting. Hooks are optional and do not replace CI or
review. See [hook maintenance and secret-check limits](docs/development/contributions.md#local-hook-maintenance).


## Environment variables

The extension uses saved Blender credentials by default and reads the runtime
API key and secret from the process environment only when that source is
explicitly selected. Development tools use a separate test credential pair. Copy
[`.env.example`](.env.example) to `.env.local` (git-ignored) for live tools.
Load it explicitly with `uv run --locked --env-file .env.local`; exported process
variables take precedence, including empty values. uv is the only dotenv loader;
Python scripts do not read credential files. CI can supply test variables directly
without a file. See [uv's dotenv options](https://docs.astral.sh/uv/configuration/files/#environment-variables).

`make test` and `make test-blender` need no credentials. `make test` disables
uv dotenv loading even if `UV_ENV_FILE` is set. Live and paid scripts are outside
the default unit-test collection and are not added to PR workflows.

| Variable | Read in | Effect | Set by |
| --- | --- | --- | --- |
| `SCENARIO_TEST_API_KEY`, `SCENARIO_TEST_API_SECRET` | `tools/dev_config.py`: `live_settings` | Required pair for smoke scripts, fixture recording and payload audit; passed explicitly to the client, with no fallback to runtime credentials | Developer or CI secrets |
| `SCENARIO_TEST_PROJECT_ID` | `tools/dev_config.py`: `live_settings` | Optional; unset/blank omits project selection. When supplied, sent as `projectId` in live-tool request queries | Developer or project-specific fixture |
| `SCENARIO_API_KEY`, `SCENARIO_API_SECRET` | `scenario/core/config.py`: `resolve_credentials` | Used only when **Credentials > Environment** is explicitly selected in Scenario Preferences. Both values must come from that source; saved Blender credentials are the default. Not used by live-tool credential selection | Developer launching Blender |
| `SCENARIO_API_BASE` | `tools/audit_payloads.py`: `main` | Audit-only REST base URL; default `https://api.cloud.scenario.com/v1` | Developer |
| `SCENARIO_SMOKE` | `tests/smoke/*.py` | `=1` allows a paid smoke to run; keep this out of dotenv files | Developer, on the command line after authorization |
| `SCENARIO_GUI_PROBE` | `scenario/blender/operators.py`: `probe_mode`; `scenario/mcp/tools_scenario.py`: `generate`; `tools/gui_screenshot.py`; `tools/capture_gui.py`; `tools/capture_gui_scene.py` | `=1` gates panel Generate and MCP generation during screenshots; it is not a general network or spending sandbox | Screenshot tool |
| `SCENARIO_PROBE_MODEL` | `tools/gui_screenshot.py` | Selects a model for 3D-tab screenshots | Test tools |
| `SCENARIO_SHOT_SOURCE` | `tests/blender/test_shot_planner.py` | `=1` loads the shot planner from source rather than the installed extension; unsuitable as evidence of ZIP acceptance | Test tools |
| `SCHEMA_CACHE` | `tools/audit_payloads.py` | Cached schema root; default `<tempdir>/scenario-schema-cache`, with separate hashed subdirectories for credentials, project and API base URL | Developer |

`SCENARIO_BLENDER_TOKEN` supplies the local MCP bearer token to the headless
`scenario_blender` command and the generated Codex client snippet. An explicit
`--token` wins over this environment value. With neither configured, the command
generates and displays a session token; supplied tokens are hidden in its startup
banner. This is separate from Scenario API authentication. Empty or malformed
explicit tokens are rejected rather than silently replaced.

A project ID is **not required for API-key authentication**. Leave the optional
project variable blank to use the API key’s default scope, or supply a project ID
to select the intended project explicitly. Project-selection tests may require
their own fixture and skip clearly when it is absent; that is not a global credential requirement.
Never put development credentials in the extension ZIP or a normal Blender profile.

## Live commands

From the repository root, after `uv sync --locked`:

```sh
# Exercise the new SDK adapter's catalog read (no record export).
uv run --locked --env-file .env.local python -m tools.check_sdk
# Explicit SDK estimate for a custom model; parameters.json is a local input object.
uv run --locked --env-file .env.local python -m tools.check_sdk --model MODEL_ID --parameters parameters.json
# Fetch schemas without submitting generations (or reuse the local schema cache).
uv run --locked --env-file .env.local python tools/audit_payloads.py
# Fetch records into tests/fixtures; review and sanitize before committing them.
uv run --locked --env-file .env.local python tools/record_fixtures.py
```

If CI or your shell already supplies the test pair, omit `--env-file .env.local`;
use `--no-env-file` to explicitly disable file loading. Missing/blank credentials
produce one actionable error before a service call. Neither script submits a
generation. The older audit/record scripts still use the prototype REST client: SDK migration and verified
non-spending service contracts remain tracked in #64 and #41.

`tools.check_sdk` uses the shared SDK read/estimate adapter and always sends
estimates with `dryRun=true` in the query. It prints counts and the exact cost,
not account records, request inputs or signed URLs. It has no paid submission
command and is never invoked by offline tests or PR CI. Live endpoint acceptance
must be recorded separately from synthetic SDK contract results.

The scripts in `tests/smoke/` spend credits. Credentials alone do not authorize a
run: agree on the account/project, exact quote and budget first. After approval,
the image smoke command is:

```sh
SCENARIO_SMOKE=1 uv run --locked --env-file .env.local python tests/smoke/smoke_image.py
```

The material, video and image-to-3D scripts use the same prefix; image-to-3D also
requires an input-image path. These prototype scripts do not yet implement the
complete budget, uncertain-submission and protected CI requirements of #40.
Do not treat their opt-in flag as a substitute for those requirements or run
smokes as part of offline verification. uv loads every variable in a dotenv file,
so keep the spending flag on the command line only.

## Native Blender test loop

Run from the repository root after `uv sync --locked`:

```sh
make test-blender
# Equivalent portable command (also works without make):
uv run --locked --no-env-file python tools/test_blender.py
# Select a particular Blender executable, including paths containing spaces:
uv run --locked --no-env-file python tools/test_blender.py --blender /path/to/blender
```

The runner checks `--blender`, then `BLENDER`, then PATH, platform locations and
local `.blender/` builds. Platform locations include the standard or versioned
Blender applications under `/Applications` on macOS; `/snap/bin/blender`,
`/usr/bin/blender` and `/opt/blender*/blender` on Linux; and versioned Blender
Foundation installations under `C:/Program Files` on Windows. Versioned
installations and cached builds use numeric version ordering. Cache discovery
selects only the current platform's executable layout, including the nested
Linux/Windows archives produced by the fetcher. An explicit selection takes
precedence and a missing selection is an error.

`uv run --locked --no-env-file python tools/blender_env.py` prints the selected
executable without launching it. `--manifest-version` (also `--version`) prints
the extension manifest version and needs no Blender installation; it does not
report the selected Blender's version. The test runner reports actual
Blender/Python/OS versions and rejects binaries below the manifest minimum.
An installed Blender 4.x cannot provide acceptance evidence for this extension's
5.0+ target. Discovery alone does not prove runtime compatibility.

Build preparation stages the pinned SDK wheels and their original notices in a
temporary source tree, downloading missing artifacts from PyPI into the ignored
`.blender/wheels/` cache and checking their hashes. Native test processes still
forbid external network access. See [SDK bundle details](docs/SDK_BUNDLE.md).

Every run creates its own directory under `.blender-profile/`, builds to an exact
ZIP filename, validates that file, installs it in a fresh profile and checks all
installed files against the ZIP. Missing, changed and extra files fail the run;
source-checkout imports are forbidden. Supplying `--zip /path/to/candidate.zip`
tests a copied snapshot of an existing artifact instead of rebuilding.

The default **baseline** covers registration defaults and paths,
fixture-driven generation events, image/material/GLB import, installed core/MCP
dependency imports, offline generation gating and authenticated MCP. A scene-tool
request also checks that Blender work runs on the main thread. The runner then
checks disable/re-enable. External socket connections are forbidden and recorded
as failures even if application code catches the exception; loopback is allowed
for local MCP. No Scenario credentials, dotenv files or paid calls are needed.

The baseline also covers history, render-lane request preparation and prompt
operators with synthetic clients. Test context managers restore credentials and
Blender's online-access preference, isolate job/cache/output paths, stop workers
and clean temporary storage. Prompt tests import only the verified installed ZIP.

Online/offline contracts toggle Blender's actual preference with fixture credentials.
They cover catalog worker success/failure and loading state, refused offline MCP
startup, network-operator polls, persisted jobs and pump resume gating. Synthetic
clients exercise online branches; service transport tripwires and the runner's
external socket guard remain active.

The baseline also imports the actual bundled SDK and all runtime dependencies,
checks loaded source/binary identities, and exercises catalog/estimate/auth
contracts through a synthetic HTTP transport with Blender's real online setting.
The JSON test report includes dependency versions and the native wheel identity.

This baseline is smaller than the full existing suite.
Use `--suite all` (or `make test-blender BLENDER_TEST_ARGS="--suite all"`) to run
all integration tests through the same guards. Full adoption coverage, broader
offline behavior, SDK bundle compatibility, GUI/input/rendering and OS acceptance
remain separate work; the baseline does not certify those paths.

The runner removes inherited Scenario credentials and Blender/Python path
overrides from its child environment. It uses fresh user resources and temporary
files, redirects test output into that profile, and compares file metadata in the
normal Blender profile before/after successful runs. It never reuses or deletes
a profile supplied through the shell. Avoid changing your normal preferences
while this check runs, since that would correctly report a profile change.

Artifacts in `.blender-profile/run-*` include per-phase logs, the candidate ZIP,
its SHA-256 and JSON runtime/test reports. Blender failures retain their exit code;
a per-process timeout prevents indefinite hangs. Successful profiles and temporary
files are removed unless `--keep-profile` is given. Failed profiles remain for
investigation. `--artifacts DIR` changes the parent directory for these unique runs.
Do not invoke `tests/blender/run_all.py` directly; it refuses unmanaged profiles.

[Blender baseline CI](.github/workflows/blender-baseline.yml) runs the full offline
unit suite on Linux and the same native baseline on Linux x64 and Windows x64
with Blender **5.0.1, 5.1.2 and 5.2.1**. It reuses the release pipeline's checksum-verifying setup action and
publishes logs/reports/ZIPs, including on failure. The `blender-baseline-ok` check
requires every leg to pass. Required-check rules remain a maintainer follow-up.
To change a pinned version, verify each platform archive checksum in the official
[Blender download directory](https://download.blender.org/release/), update the
matrix version and hash together, and inspect the actual runtime report from CI.


### Portable build, install and download tools

The build/install/download tools use Python 3.11.13+ and the standard library. Select Blender with `BLENDER`
or `--blender`; an explicitly selected missing binary is an error. Build/install
commands create fresh profiles under `.blender-profile/tools-*`, strip inherited
Scenario credentials and Blender/Python path overrides, and retain per-phase logs.

```sh
uv run --locked --no-env-file python tools/build.py --output dist
uv run --locked --no-env-file python tools/build.py --repo
uv run --locked --no-env-file python tools/install.py --zip dist/scenario-<version>.zip --launch
```

`build.py` builds the manifest's exact ZIP, checks its GPL text and validates it
before copying it to the output directory. `--repo` generates `OUTPUT/repo/`.
Successful build profiles are removed; failures retain their profiles and logs.
`install.py` builds when `--zip` is absent, verifies installed files against that
ZIP and retains its new profile. `--launch` opens that profile for manual testing.
An existing shell profile is never reused. Remove the printed `tools-*` directory
when finished with it and after closing Blender. `make build` and `make install`
accept `BLENDER_BUILD_ARGS` and `BLENDER_INSTALL_ARGS`, respectively.

On Linux x64, Windows x64 or macOS Apple silicon, fetch an official Blender release with:

```sh
uv run --locked --no-env-file python tools/fetch_blender.py --version 5.0.1
```

The fetcher reads the official checksum file, verifies the archive before
extraction and prints the executable path to use with `BLENDER`. CI supplies
`--sha256` to pin the expected digest. Archives are cached under `.blender/`;
every invocation re-extracts the verified archive into the same managed slot for
that platform, version and checksum. Successful replacement removes the previous extraction;
a failed extraction leaves it intact. On macOS, the verified DMG is mounted read-only
at a private temporary path; only `Blender.app` is copied. The tool detaches that
mount before publishing the installation, retrying a busy mount once with forced
detach. If macOS refuses both attempts, the command fails and leaves the private
mount named in the error for manual cleanup, without traversing its contents.
Do not fetch a build while using that cached
Blender executable. Older builds from the previous tool may leave randomly named
version directories; remove those manually when no longer in use.
Other platforms require a separately installed Blender selected with `BLENDER`.
No download happens implicitly during build, install or tests.
The macOS downloader is available locally; the setup action and native CI matrix
still cover Linux and Windows only. Scheduled macOS coverage remains tracked in #42.

Screenshot probes prepare the blockout form without submitting a design.
Design/refine operators also respect offline access, missing credentials and
`SCENARIO_GUI_PROBE=1`. This flag is a development guard, not a paid-test mode.

The optional Pillow-based `tools/make_icons.py` renderer can use Windows Arial
or DejaVu, Linux system/Blender fonts, or fonts from flat and fetched Linux/Windows
cache layouts. This only broadens font discovery; it does not regenerate tracked
icons or add Pillow to the extension. If no usable font is found, the renderer
keeps its existing geometric fallback.

### Repeatable GUI screenshots

Use an interactive desktop session (the command opens and closes its own Blender
window). The capture runner builds or installs an exact ZIP in a fresh offline
profile, prepares a version-matched default scene, and captures the Scenario UI:

```sh
uv run --locked --no-env-file python tools/capture_gui.py --blender /path/to/blender \
  --zip dist/scenario-<version>.zip --output workdir/screenshots \
  --view sidebar --fixture form --label "milestone / candidate commit"
uv run --locked --no-env-file python tools/capture_gui.py --blender /path/to/blender \
  --zip dist/scenario-<version>.zip --output workdir/screenshots \
  --view composer --fixture form --label "milestone / candidate commit"
```

Omit `--zip` to build the current source. Successful cleanup keeps one candidate
ZIP, screenshots, reports and
logs; staged source/wheels and the temporary ZIP copy are removed. Setup errors
produce a failed report when the output directory is writable. A cleanup error
retains capture evidence with `status: cleanup_failed` and a nonzero exit.
The Blender-side `gui.json` reports `captured` only after the sidebar/composer
and both credential-preference screenshots have been written; a timeout between
timer callbacks cannot leave a successful capture report.
The composer has no audio lane; use `--view sidebar --lane audio` for that lane.

`--fixture empty` (default) captures the
signed-out UI; `form` supplies a clearly named synthetic model and fake credentials
in memory, without service requests or an actual quote. The current sidebar hides
its form while offline; the composer can display the synthetic model and prompt.
`--lane` selects image,
video, audio or 3d. Capture runs always use offline mode and the GUI probe guard.
Inherited Scenario credentials and Blender/Python overrides are removed.
`--gpu-backend` can select a Blender graphics backend explicitly; the capture
report records the actual backend and renderer. Blank captures are rejected.
On Linux, `--capture-backend x11` uses xdotool and ImageMagick to read only the
visible window belonging to the disposable Blender process. This is useful when
software OpenGL produces a blank GPU screenshot; the default remains Blender’s
screenshot operator. The report identifies the capture mechanism.

Each invocation keeps a unique timestamped directory containing `plugin.png`,
`report.json`, the candidate ZIP, the fixture blend and phase logs. The report
records the ZIP/PNG hashes, actual Blender/Python/OS, view, lane, fixture and an
optional user-supplied label. A label identifies the intended milestone; the ZIP
hash identifies the actual artifact. Successful profiles are removed. Failure
profiles remain for diagnosis, and the command exits unsuccessfully on missing
GUI evidence, a missing PNG, changed installed files, timeout or runtime mismatch.

**Inspect each saved image:** the API's active-tab value alone does not establish
what Blender rendered. A captured image also does not prove input/focus behavior,
live API access or paid generation. Keep local images and an evidence index in
ignored `workdir/screenshots/`; when using worktrees, pass the root checkout's
absolute screenshots directory to collect milestones together.

The Blender baseline CI matrix also captures sidebar and composer on 5.0.1,
5.1.2 and 5.2.1 using a virtual X display, Openbox and software OpenGL. The X11
capture backend reads the Blender window directly because llvmpipe can return
black frames through Blender’s GPU screenshot operator. CI passes the
same ZIP that completed the native tests to the capture runner. Each matrix
leg publishes `blender-screenshots-<version>` with PNGs, JSON evidence and logs;
the baseline artifact retains the corresponding ZIP. Profiles and local fixture
blend files are excluded from uploads. A capture failure fails that matrix leg.
Download and inspect these artifacts during review: software-rendered Linux
images complement local native GUI checks and do not replace input testing or
other OS/GPU acceptance.


## Documentation builds

Edit [the Markdown guide](docs/USER_GUIDE.md) for all guide prose. The
[handbook template](docs/handbook-template.html) contains presentation, navigation
and version slots only. `make docs` renders the guide to ignored `site/index.html`
and copies just its referenced images beside it. A neighboring `.assets.json`
record lets repeat builds remove unchanged image copies that the guide no longer
uses, including when switching the same output to inline mode. Unrecorded files
are retained; modified old copies and symlinked destinations stop the build for
inspection. Keep that record with a website output directory between builds.
The version comes from the
extension manifest. Python-Markdown is pinned in the development environment;
it is not included in the extension ZIP or imported by Blender tooling.

For a single HTML file containing the content and images:

```sh
uv run --locked --no-env-file python tools/build_docs_html.py \
  --inline-images --output dist/scenario-handbook.html
```

Both modes retain the template's `fonts.googleapis.com` stylesheet, which loads
fonts from Google when viewed online. Single-file output does not mean fully
offline typography; system fonts remain available without that connection.
Relative documentation links point to their repository files or directories on GitHub.
The renderer rejects missing/empty images, empty alt text, image paths outside
the guide directory, incomplete document metadata and unknown template slots.
Authored `{{...}}` examples in Markdown remain literal guide content.
It accepts `--source`, `--template`, `--manifest` and `--output` paths; images are
relative to the Markdown source, and relative links must resolve in this repository.
Review the rendered page at wide and narrow widths after presentation changes.
Generated HTML and `site/` are ignored; do not commit them or copy old guides into
snapshot directories. Hosting, release attachment and the native update controls
remain separate work under #37. Screenshot/content acceptance remains #13/#14.
