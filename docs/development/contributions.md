# Commits and pull requests

Use a short-lived `type/issue-description` branch and target `main`. Respect the
recorded base of an existing stacked PR; do not silently retarget it. Review the
complete PR diff and dependencies. Preserve unrelated work in other branches.

`commitlint.config.ts` is authoritative for Conventional Commit types, scopes,
the 120-character header limit and the no-em-dash rule. Choose the type from the
final diff, not the inherited title. Write `type(scope): summary` with an imperative
summary and no trailing period. For example,
`fix(blender): preserve the current frame after a viewport capture`.

| Type                   | Change                                                    |
| ---------------------- | --------------------------------------------------------- |
| feat / fix / perf      | New capability, corrected product behavior or performance |
| refactor               | Product structure with unchanged behavior                 |
| test                   | Tests only                                                |
| docs                   | Documentation, agent instructions and command Markdown    |
| build                  | Package/build configuration                               |
| ci                     | Workflows and automation                                  |
| style / chore / revert | Formatting, maintenance or a revert                       |

Squash merges use the PR title as the commit header. Keep branch commits
conventional too: current CI checks them. A missing scope is a warning; when a
scope fits, choose it from the map below. Every accepted type can appear in the
generated release notes; see [release behavior](../RELEASING.md#included-commit-types).

Mark a breaking change with `!` before the colon, such as
`feat(mcp)!: rename a tool`, or a `BREAKING CHANGE:` footer. Describe the behavior
consumers must adapt to. Split unrelated changes into separate PRs so a squash
commit describes one concern. Preserve contributor trailers in the squash body.

## Scopes

The ordered scope list follows [commitlint.config.ts](../../commitlint.config.ts).
Tests for a product area keep that area's scope; `tests` names harness changes.

| Scope | Responsibility |
| --- | --- |
| `core` | Cross-cutting `scenario/core` behavior, including configuration and history |
| `api` | `scenario/core/api`: SDK adapter, service operations and catalog |
| `jobs` | `scenario/core/jobs`: durable jobs, workers, transfers and records |
| `scene` | `scenario/core/scene`: captures, materials, placement and scene planning |
| `schema` | `scenario/core/schema`: forms and model parameter validation |
| `blender` | `scenario/blender` glue and `scenario/prefs.py`: operators, application and lifecycle |
| `ui` | Panels, forms, popovers, model picker, prompt tools, icons and `docs/UI_STYLE.md` |
| `composer` | `scenario/blender/composer` and `scenario/core/ui/composer_layout.py` |
| `mcp` | `scenario/mcp` and `scenario/blender/mcp_service.py` |
| `tests` | Shared test harnesses, fakes and fixture recording |
| `tools` | `tools/` and the Makefile |
| `docs` | README, documentation and the user guide |
| `ci` | Workflows, rulesets and hooks |
| `deps` | Dependency, Blender and action version pins |
| `release` | Release configuration, version fields and changelog automation |
| `agents` | Agent instructions, skills, commands and configuration |
| `repo` | Licenses, community policies, templates and ownership files |

## PR descriptions and review

Complete the [PR template](../../.github/pull_request_template.md). Mark applicable
checks and explain omitted validation. A pending human review is not approval:
agents may submit a reviewable PR, but must not mark that review complete.
Original contributions use the repository's GPL-3.0-or-later license. Adopted
sources retain their original compatible licenses, notices and attribution.

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
For Codex-assisted commits, follow the accurate model attribution or fallback
trailer in [AGENTS.md](../../AGENTS.md#codex-commit-attribution). Name any other
contributing harness and preserve its contributor trailers too.
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

## Local hook maintenance

[Optional hooks](../../.pre-commit-config.yaml) use local commands from the locked
uv development group: pre-commit, its standard file-hygiene hooks,
conventional-pre-commit and Ruff. Update their exact development pins with
`uv add --dev PACKAGE==VERSION`, review `uv.lock`, and run the hook regression
tests. `pre-commit autoupdate` does not update these local uv-managed tools.
No Ruff hook version can drift from CI because both invoke the same dependency.

The commit-msg hook checks accepted types and allows ordinary merge/fixup
messages. CI remains authoritative for scopes, header length and the complete
commit policy. The branch hook rejects direct commits on `main`; these optional
local checks do not change repository protection settings.

The [secret guard](../../tools/check_secrets.py) checks forbidden paths and added
lines from the Git index, so an unstaged edit cannot hide staged content. Run it
directly with `uv run --locked --no-env-file python tools/check_secrets.py`; filenames
after `--` restrict the scan. It reports file, line and pattern, never the matched
line or value. It recognizes common credential/token/signed-URL shapes and rejects
environment files except `.env.example`, private keys, local state and build
artifacts. It is not a full security scan. Existing unchanged content, binary/media
content, its own source and unit-test module, and deliberately marked `secrets-allow`
lines are outside the content scan; review any exception carefully. Only
`tools/blank.blend` is permitted among Blender scenes, and job-registry fixtures
must remain under `tests/fixtures/`.

Tests run the actual hook framework in disposable Git repositories, covering
staging, redaction, commit-message rejection, changed-file formatting and fixture
preservation. No hooks are installed into a contributor's checkout by CI or
the unit suite. Hooks are a local convenience; the repository's CI remains the
review gate, and whole-tree normalization remains #28.

## GitHub Actions updates

[Dependabot](../../.github/dependabot.yml) checks GitHub Actions weekly and groups
version updates into one `actions` PR with the `dependencies` and `area:ci` labels.
The `ci(deps)` commit prefix produces Conventional Commit titles; do not add
`include: scope`, which would append a second dependency scope.

Keep third-party action references pinned to a full 40-character commit SHA with
the release version in a trailing comment, for example
`uses: actions/checkout@<sha> # vX.Y.Z`. Review generated SHA and version-comment
changes together, including upstream release notes, workflow permissions and CI
results. Dependabot update PRs follow the ordinary review and merge process.

[The offline house-rule checker](../../tools/check_rules.py) currently implements
`actions-pinned` for workflow YAML and local composite-action manifests. Run
`make check-rules`, or use `uv run --locked --no-env-file python tools/check_rules.py`
with explicit file paths and optional `--rule actions-pinned`. `--list` reports
only implemented rules. The unit suite checks the repository and exercises
failure cases, so ordinary unit CI also enforces the convention.
The default scan includes tracked files and new files that Git does not ignore,
so a proposed workflow is checked before it is staged.

Write `uses` on its own line with a plain, single-quoted or double-quoted value.
Remote actions and reusable workflows need a lowercase 40-character SHA and a
trailing full release-version comment such as `# v1.2.3`. Local `./` references
use the caller checkout; `docker://` references remain outside this rule.
Multiline values, aliases and flow-style action declarations fail with a request
to use the supported form. Script block contents and comments are not action
declarations. This is a line-oriented convention check, not a general YAML
validator; it does not resolve tags or prove a comment matches its SHA. Review
upstream release identity and use workflow validation for those separate checks.

This configuration covers GitHub Actions only. Python/SDK updates still require
the [dependency bundle procedure](../SDK_BUNDLE.md); adding automatic updates for
them requires coordinating development pins with the exact packaged wheel bundle.
Repository settings and live Dependabot acceptance remain tracked in #39. Other
house rules, approved-dependency enforcement and REUSE coverage remain under #29;
the checker does not claim they are implemented. Local checks do not prove that
GitHub's administrative gates are enabled.
