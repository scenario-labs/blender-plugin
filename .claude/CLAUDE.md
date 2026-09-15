# Scenario for Blender: agent instructions

`.claude/CLAUDE.md` is the canonical source for shared repository conventions
and Claude Code guidance. Root `AGENTS.md` directs Codex to read this file and
adds Codex-specific instructions. Edit shared conventions here without duplicating
them in `AGENTS.md`. Paths below are repository-relative.

## Project and current direction

This is a Python Blender extension with a local MCP server. Read `README.md`
for the current checkout and `docs/UI_STYLE.md` before changing UI behavior.
Older design documents and session notes describe the prototype; they do not
override the user's instructions or the current issue and PR scope.

The approved direction is one consolidated extension, a compact default UI,
optional expanded Studio, browser OAuth and Blender-native updates. There is no
prototype-data migration requirement. Preserve useful capabilities and tests,
source attribution and required third-party notices when adopting code.

The current package is `scenario/`; the approved minimum is Blender 5.0.
Adoption must validate native behavior and bundled dependencies on Blender 5.0,
5.1 and 5.2. A manifest declaration or successful ZIP validation does not prove
runtime compatibility.

## Repository map

- `scenario/core/`: API, jobs, schema, scene plans and UI calculations without bpy.
- `scenario/blender/`: Blender operators, properties, panels, composer and pump.
- `scenario/mcp/`: local protocol/server and tools; Blender-facing tools execute
  on the main thread, while protocol and transport code remain bpy-free.
- `scenario/prefs.py`, `scenario/__init__.py`, `scenario/blender_manifest.toml`:
  preferences, registration and package metadata.
- `tests/unit/`: pytest without Blender; `tests/blender/`: native integration
  tests; `tests/smoke/`: opt-in paid checks; `tests/fixtures/`: sanitized data.
- `tools/` and `Makefile`: build, installation, capture and test entry points.
- `docs/USER_GUIDE.md`, `docs/UI_STYLE.md`, `docs/MODEL_PAYLOAD_AUDIT.md`:
  user guidance, UI conventions and historical schema evidence.

Update this map and the commands when the adopted package changes.

## Scenario SDK first: mandatory

Use the official Python SDK (`scenario-sdk`) for Scenario service operations in
the UI, jobs, local MCP and supporting tools. Its source and issue tracker are
`scenario-labs/scenario-sdk-python`.

1. Inspect the exact selected SDK release, its public methods, supported extension
   parameters, response wrappers and configuration before implementing an operation.
   Do not assume the repository's main branch matches the published artifact.
2. Use the SDK through one shared integration adapter. Existing prototype HTTP
   code, convenience or an unfamiliar SDK method is not a reason to bypass it.
   Audit and replace imported API paths during adoption.
3. If the SDK cannot perform a required operation correctly, reproduce the gap.
   Find an existing SDK issue or create one with the SDK version, expected/actual
   behavior and a sanitized reproduction. Keep private evidence out of public text.
4. Only then add a narrow raw API fallback for that operation inside the shared
   adapter. Link the SDK issue in the code and PR, test the fallback, and record
   the condition for removing it. Recheck exceptions on SDK upgrades.
5. Custom endpoint calls through low-level SDK HTTP verbs are fallbacks too.
   A documented endpoint's `with_raw_response` wrapper is still SDK usage.
   Browser authorization, signed storage transfers and update repositories are
   distinct protocols: document their actual SDK coverage, not a blanket HTTP ban.
6. Pin and package the SDK and its required dependencies, including wheels when
   needed. Validate the exact bundle with Blender's Python and supported OS/CPU
   combinations; preserve dependency licenses. The SDK supersedes the old blanket
   stdlib-only/no-wheels rule, without authorizing unrelated dependencies.
7. Configure retries explicitly. Use `max_retries=0` for paid submissions unless
   a verified server idempotency contract makes retry safe. A timeout is an
   uncertain submission, not permission to submit again.

Before changing the shared SDK adapter or its dependency pin, read
`docs/SDK_ADOPTION.md` and run
`uv run --locked python -m pytest tests/unit/test_scenario_sdk_contract.py -rx`.
The known authentication expected failure is an unresolved gap, not production
acceptance. Extend these offline contracts when mapping adopted operations.

Changes to Scenario API calls must identify the SDK method or the documented
exception in the PR. Documentation-only work does not need an API coverage audit.
The SDK is an adoption requirement; its presence in these instructions does not
mean the current prototype client has already been replaced.

## Blender, jobs and authentication

- Keep bpy operations on Blender's main thread, never under `scenario/core/`.
  Workers perform network work and queue results; the GUI pump applies them.
  Headless operation needs its own blocking queue processing.
- Never mutate properties during `draw()`. Follow `docs/UI_STYLE.md` and verify
  native input, focus and viewport interaction when changing the composer.
- Keep job lifetime independent of an open UI. Persist request identity and scope
  before spending; recover uncertain jobs without blind resubmission.
- Bind quotes and callbacks to the exact payload, account, project, scene and
  target. Closing a view or switching context must not misroute a late result.
- Preserve the exact server estimate before a paid action. REST `dryRun` belongs
  in the query, not the JSON body; use the selected SDK's documented parameter.
- Respect `bpy.app.online_access` before network activity. Store state under
  `bpy.utils.extension_path_user`, never inside the installed extension.
- Keep local MCP authenticated, Python execution opt-in and disabled by default.
  Use private temporary directories and guaranteed cleanup for captures.
- Explicitly configure SDK credentials. Test that ambient API-key environment
  variables cannot override the selected OAuth account. Never distribute a
  privileged server secret or assume an OAuth token is accepted by REST.
- Never print or commit credentials, tokens or signed URL query strings.
  `.env.local` and local agent notes are private. Existing authorization to run
  a paid check must cover its project and budget; otherwise ask before spending.

## Validation and local commands

See [the environment reference](../CONTRIBUTING.md#environment-variables) for
developer credentials and explicit live commands.

Use the uv version required by `pyproject.toml`. Run `uv sync --locked` to create
the worktree's `.venv` from `uv.lock` and the interpreter in `.python-version`.
`make test` runs `uv run --locked --no-env-file python -m pytest`; use the same prefix for
focused tests. Development dependencies belong in `[dependency-groups].dev`;
commit the updated lockfile when changing them. Do not maintain a parallel
requirements-dev.txt or install ad hoc tools into the managed environment.
For an explicit interpreter check, use `uv run --locked --python <version>`.
Blender native tests still use Blender's bundled Python and an isolated profile.
Preserve exit codes when capturing logs, and distinguish passed checks from
checks that were not run.

Use the pinned Ruff configuration before further Python development:
`make format` applies safe fixes and formatting; `make lint` checks both.
During Studio adoption, scope these commands with `LINT_PATHS` to changed or
adopted files. CI checks whole changed Python files; full-tree findings remain
tracked in #28 until the dedicated mechanical normalization. Do not reformat
obsolete prototypes as unrelated cleanup. Follow `docs/PYTHON_STYLE.md`,
including Blender registration/annotation cautions, and keep any eventual
pre-commit hook version aligned with the required Ruff version.

`make test-blender` owns fresh disposable profiles for its entire build/install/test
sequence, including probes. It strips inherited credentials and Blender/Python path
overrides, verifies installed ZIP contents and reports actual runtime versions.
See [the native test loop](../CONTRIBUTING.md#native-blender-test-loop). Use `BLENDER`
or `--blender` to select a supported binary; discovery does not prove compatibility.

The portable build/install tools also create fresh isolated profiles and scrub
inherited credentials and path overrides. For every direct Blender invocation outside these tools,
including probes, export an absolute disposable profile:
`export BLENDER_USER_RESOURCES="$PWD/.blender-profile"`.
Never install development builds into the user's normal profile.

- `make build`: build and validate the extension ZIP; use
  `BLENDER_BUILD_ARGS="--repo"` to also generate a local extension repository.
- `make install`: build and install into a new isolated profile; use
  `BLENDER_INSTALL_ARGS="--launch"` to open it.
- `make test-blender`: build/validate/install an exact ZIP, then run the offline
  baseline in a new profile. No prior installation is needed. Logs and ZIP remain
  under `.blender-profile/run-*`; successful profiles are removed. Use
  `BLENDER_TEST_ARGS="--suite all"` for the full existing integration suite.
- For package changes, inspect the resulting ZIP, validate it and check its
  license content. Keep root `LICENSE` and `scenario/LICENSE` identical.
- For UI changes, exercise native behavior and inspect captured screenshots.
  Report actual Blender/OS versions and limitations.
- For instruction or documentation changes, check links, symlinks, commands and
  the diff. Do not run the full Blender suite just to populate a test count.
- Smoke tests, generation, prompt helpers and scene design can spend credits.
  Do not run them as part of a documentation command.

Read `scenario/blender/registry.py` before using the headless MCP CLI; the
prototype's hyphenated command is a known issue, not a working example to copy.

## Commits and pull requests

Use a short-lived `type/issue-description` branch and target `main`. Respect the
recorded base of an existing stacked PR; do not silently retarget it. Review the
complete PR diff and dependencies. Preserve unrelated work in other branches.

`commitlint.config.ts` is authoritative for Conventional Commit types, scopes,
the 120-character header limit and the no-em-dash rule. Choose the type from the
final diff, not the inherited title:

| Type | Change |
| --- | --- |
| feat / fix / perf | New capability, corrected product behavior or performance |
| refactor | Product structure with unchanged behavior |
| test | Tests only |
| docs | Documentation, agent instructions and command Markdown |
| build | Package/build configuration |
| ci | Workflows and automation |
| style / chore / revert | Formatting, maintenance or a revert |

Scopes: core, api, jobs, scene, schema, blender, ui, composer, mcp, tests, tools,
docs, ci, deps, release, agents, repo. Squash merges use the PR title as the
commit header. Keep branch commits conventional too: current CI checks them.

Lead PR descriptions with the problem and resulting behavior. Include relevant
validation and limitations; do not invent passing counts, approvals or authorship.
Use `Closes` only for fully completed issues and `Refs` for partial work.
Before creating or updating a PR, read related issues and check their current
acceptance criteria against the final diff and verified evidence. Add missing
references, explain remaining scope for partial work, and verify GitHub's closing
links. Closing keywords in a PR description only apply when it targets the default
branch; recheck stacked PRs after retargeting. Carry verified references into the
squash message and check issue state after an authorized merge. Generated release
notes and historical keywords are not evidence that an issue is complete.
Preserve actual contributor attribution. Keep issue references in commit footers.
Write multiline PR bodies/messages to files and use `--body-file` or `-F`,
with proper shell quoting.

When asked to check or address a PR review comment, always reply in that
comment's GitHub thread after investigating. State the outcome concisely:
link the pushed fix commit and relevant validation, explain why no change is
needed, or describe what remains unresolved. Apply this to human and bot
comments alike. A local fix or a chat response alone does not complete the
review follow-up. Do not claim a fix is pushed before it is available remotely.

For local commit linting, use the versions and command from
`.github/workflows/pr-name.yml`:
`npx --no-install commitlint --config commitlint.config.ts --verbose`.
If unavailable, use that workflow's ad-hoc npm install command. Do not add a
Node project or lockfile for the Blender extension.

Do not manually bump package versions or edit release notes in an unrelated PR.
Read the actual release workflow/configuration before describing release behavior.
New release tags use `blender-plugin-vX.Y.Z`; package versions stay `X.Y.Z` and
release ZIPs stay `scenario-X.Y.Z.zip`. Preserve historical `v*` tags and releases.

## History, public content and known pitfalls

History lives in git. Do not create file snapshots in `versions/` or retain
retired code in `archive/`. Recover history from commits/tags; update durable
engineering explanations in the appropriate docs instead of agent session logs.

This repository is public. Do not add session/resume IDs, personal paths, account
records, workspace identifiers, spend anecdotes or private research exports.
Preserve GPL text and first-party SPDX notices; preserve the original licenses
and attribution of third-party code, fonts, icons and SDK dependencies.

Useful prototype lessons to retain while changing implementations:
- Long text asset previews can be truncated; check `hasFullPreview` and fetch
  the full asset rather than parsing an incomplete plan.
- Enum caches are transient; a reopened blend file may need schema reconstruction.
- One generation may yield several mesh variants and maps; identify the primary
  result rather than importing every file as another object.
- Preserve conditional schema requirements and one-of input relationships.

## Claude commands

- `/download-artifacts <prnumber>`: collect the PR head's CI artifacts under
  ignored `workdir/`, preserve screenshot history and create a local review index.
- `/pr-summary`: update the current PR's summary/title from its actual diff and
  verified evidence; return a draft instead when requested.
- `/squash-message`: prepare and lint one squash message, align the PR title when
  needed, and copy it with `pbcopy` when available. It never commits or merges.

Private notes belong in ignored `.claude/CLAUDE.local.md` or `CLAUDE.local.md`.
