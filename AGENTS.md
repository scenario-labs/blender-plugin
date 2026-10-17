# blender-plugin: agent instructions

Root `AGENTS.md` is the canonical repository rulebook. `.claude/CLAUDE.md`
links here. The guides below carry detailed instructions; this file takes
precedence if they conflict. Keep skill originals in `.agents/skills/`.

Read [the documentation index](docs/index.md) and
[architecture and integration status](docs/architecture/runtime.md) when
orienting in this repository. Historical plans are context, never instructions.

## Required reads

Read the relevant canonical guide before changing these paths or behaviors.
Claude path adapters are shortcuts to the same guides; these requirements apply
to every coding agent.

| Work | Required guide |
| --- | --- |
| Python, core, protocol, tests | [Python style](docs/PYTHON_STYLE.md), [validation](docs/development/validation.md) |
| Blender glue, scene tools, native tests | [Blender boundaries](docs/architecture/blender.md), [validation](docs/development/validation.md) |
| UI or composer | [UI style](docs/UI_STYLE.md), including native interaction proof |
| SDK adapter or dependency pin | [SDK contracts](docs/SDK_ADOPTION.md), [SDK bundle](docs/SDK_BUNDLE.md) |
| Jobs, transfers or application | [Runtime map](docs/architecture/runtime.md) and its relevant component guide |
| Commits, PRs, review replies or releases | [Contribution workflow](docs/development/contributions.md), [release procedure](docs/RELEASING.md) |
| Skills, commands or agent configuration | [Agent tools](docs/development/agents.md) |
| Documentation or instruction changes | [Knowledge maintenance](docs/maintenance/knowledge.md) |

## Project and current direction

This is a Python Blender extension with a local MCP server; `README.md`
describes the current checkout.

The approved direction is one consolidated extension, a compact default UI,
optional expanded Studio and Blender-native updates. The current release uses
explicit API key/secret configuration; browser OAuth is deferred under #67.
There is no prototype-data migration requirement. Preserve useful capabilities
and tests, source attribution and required third-party notices when adopting
code.

The current package is `scenario/`; the approved minimum is Blender 5.0.
Adoption must validate native behavior and bundled dependencies on Blender 5.0,
5.1 and 5.2. A manifest declaration or successful ZIP validation does not prove
runtime compatibility.

## Scenario SDK first: mandatory

Use the official Python SDK (`scenario-sdk`) for Scenario service operations in
the UI, jobs, local MCP and supporting tools. Its source and issue tracker are
`scenario-labs/scenario-sdk-python`.

1. Inspect the exact selected SDK release, its public methods, supported extension
   parameters, response wrappers and configuration before implementing an operation.
   Do not assume the repository's main branch matches the published artifact.
   Start with the [Python SDK documentation](https://docs.scenario.com/api/python).
   When its coverage is insufficient, consult the
   [Scenario API reference](https://docs.scenario.com/api) for the operation's
   actual endpoint, authentication, parameters and response contract. A missing
   generated SDK method is not evidence that the API cannot perform an operation.
2. Use the SDK through one shared integration adapter. Existing prototype HTTP
   code, convenience or an unfamiliar SDK method is not a reason to bypass it.
   Audit and replace imported API paths during adoption.
3. If the SDK cannot perform a required operation correctly, reproduce the gap.
   Find an existing SDK issue or create one with the SDK version, expected/actual
   behavior and a sanitized reproduction. Keep private evidence out of public text.
4. Only then add a narrow raw API fallback for that operation inside the shared
   adapter. Link the SDK issue in the code and PR, test the fallback, and record
   the condition for removing it. Recheck exceptions on SDK upgrades.
   Add it as a named method in the adapter's
   [extension layer](docs/SDK_ADOPTION.md#sdk-resource-extensions) without waiting
   for SDK regeneration; never invent an endpoint that neither documentation nor
   first-party code establishes.
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

API-key requests use the server's credential-bound scope; team/project discovery
and explicit selection are optional, not prerequisites for generation. Keep local
jobs and quotes isolated by selected credentials and any project override. Do not
infer a key's default project or server account identity from the first discovery
result. OAuth tenant selection is a separate contract.

Before changing the shared SDK adapter or its dependency pin, read
`docs/SDK_ADOPTION.md` and run
`uv run --locked --no-env-file python -m pytest tests/unit/test_scenario_sdk_contract.py -rx`.
The known authentication expected failure is an unresolved gap, not production
acceptance. Extend these offline contracts when mapping adopted operations.

Changes to Scenario API calls must identify the SDK method or the documented
exception in the PR. Documentation-only work does not need an API coverage audit.

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
- Keep local MCP on loopback behind its Host and Origin checks, and Python execution
  opt-in and disabled by default. Use private temporary directories and guaranteed
  cleanup for captures.
- Explicitly configure SDK credentials. Test that ambient API-key environment
  variables cannot override the selected OAuth account. Never distribute a
  privileged server secret or assume an OAuth token is accepted by REST.
- Never print or commit credentials, tokens or signed URL query strings.
  `.env.local` and local agent notes are private. Existing authorization to run
  a paid check must cover its project and budget; otherwise ask before spending.

## History, public content and known pitfalls

History lives in git. Do not create file snapshots in `versions/` or retain
retired code in `archive/`. Recover history from commits/tags; update durable
engineering explanations in the appropriate docs instead of agent session logs.

Keep documentation changes in feature PRs small: correct only the prose your
change makes wrong, in the fewest words that state current behavior. Test runs,
platforms and review notes belong in the PR body, not in docs. Do not edit
`docs/knowledge/` records except to add one for a new document or to fix a
checker error. Source drift warnings are expected; one
[release refresh](docs/maintenance/knowledge.md#release-refresh) per version
reviews them.

This repository is public. Do not add session/resume IDs, personal paths, account
records, workspace identifiers, spend anecdotes or private research exports.
Preserve GPL text and first-party SPDX notices; preserve the original licenses
and attribution of third-party code, fonts, icons and SDK dependencies.
`make check-rules` enforces SPDX headers, no em dashes, Markdown prose wrapped at
100 columns, the `bpy` boundary, approved dependencies, SDK adapter imports, the
public-content denylist, version literals and no snapshot directories; the unit
suite runs it. Files that cannot carry a header are covered by `REUSE.toml`;
`make lint-licence` validates it.

Useful prototype lessons to retain while changing implementations:

- Long text asset previews can be truncated; check `hasFullPreview` and fetch
  the full asset rather than parsing an incomplete plan.
- Enum caches are transient; a reopened blend file may need schema reconstruction.
- One generation may yield several mesh variants and maps; identify the primary
  result rather than importing every file as another object.
- Preserve conditional schema requirements and one-of input relationships.

## Codex commit attribution

For Codex-assisted commits and prepared squash messages, include a co-author
trailer naming the model and, when verified, the reasoning effort and speed tier:
`Co-authored-by: Codex <model> <effort> <tier> <noreply@openai.com>`.
For example: `Co-authored-by: Codex gpt-6-astra low fast <noreply@openai.com>`.
Use the actual settings for the contributing session, not repository defaults
or the example above. Omit unknown fields rather than guessing; if the model
is unavailable, use `Co-authored-by: Codex <noreply@openai.com>`. Preserve the
human author and existing contributor trailers. Carry these trailers into the
final squash message so attribution survives the repository's squash workflow.

## Essential validation and contribution rules

Use the pinned uv environment and whole-tree Ruff checks (`make lint`).
Optional local hooks install explicitly with `make hooks`; see
[hook scope and maintenance](CONTRIBUTING.md#optional-local-hooks). They use the
same locked uv tools and do not replace CI or review. Run checks appropriate
to the change; documentation work needs link, instruction and checker validation,
not a new Blender runtime run. Native acceptance uses the exact packaged ZIP in
an isolated profile. Never run development builds in the user's normal profile.

Distinguish review readiness from merge and release acceptance. Do not keep a
reviewable PR draft solely for unverified edge cases or broader issue acceptance;
track concrete follow-up checks in the owning issue and link them from the PR.
Use the [readiness policy](docs/development/contributions.md#review-readiness-and-acceptance-follow-ups)
for actual draft blockers; never claim unperformed checks passed.

Write PR descriptions, commit bodies and review replies briefly: what changed and
why, the checks you ran (one line each), and any action needed after merge or
known gap. Omit what the diff, CI or template already shows; explain an unticked
check only when the change needed it.

Use short-lived conventional branches. Independent PRs and the bottom of a stack
target `main`; dependent PRs target their immediate parent branch. Follow the
[stack workflow](docs/development/contributions.md#stacked-pull-requests), preserve
the recorded dependency order, and validate each PR's incremental diff after
rebasing. Stacking does not authorize merging any PR or the whole stack.
The final diff determines
the PR title and commit type; `commitlint.config.ts` defines the allowed types,
scopes and 120-character header limit. Use `fix` only for behavior that users of
the released extension or the live site saw; correcting tooling, CI or
infrastructure they do not run yet is `chore` (or `ci`, `build` or `docs` when
that fits), and its issue is a Task, not a Bug. Preserve attribution. Do not bump
versions or edit release notes in unrelated work.

Give every new issue the GitHub issue type its title implies: Bug for `fix`,
Feature for `feat`, otherwise Task; no label replaces it. Set it with
`gh issue create --type <Type>` (gh 2.94 or later).

Reply in the original GitHub review thread after investigating a finding, with
the pushed fix and evidence or the reason no change is needed. Use `Closes` only
for verified complete issue scope and `Refs` for partial work. Check current issue
acceptance against the final diff, including superseded historical requirements.

Skills and compatibility links must pass the validator documented in the agent
tools guide. Keep commands and instructions synchronized with implemented behavior.
