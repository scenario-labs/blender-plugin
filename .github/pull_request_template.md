<!--
The PR title becomes the squash commit header: type(scope): summary.
Use an imperative summary, no trailing period, and at most 120 characters.
Scopes: core, api, jobs, scene, schema, blender, ui, composer, mcp, tests,
tools, docs, ci, deps, release, agents, repo.
Example: fix(blender): preserve the current frame after a viewport capture

Keep one concern per PR. See CONTRIBUTING.md and docs/development/contributions.md.
Mark applicable checks below; explain checks that do not apply or were not run.
Do not claim human review, test results or authorization that has not happened.
-->

## What does this PR change?

<!-- Lead with the problem and the resulting behavior for users or maintainers.
For a behavior change, give a concrete before/after example when useful. For
internal work, explain its maintenance benefit. Name any action needed to use or
validate the change and any material limits. Keep the detail proportional to the
change; a file inventory alone does not explain its effect.

Use Closes #n only for complete issue acceptance; use Refs #n for partial work
and describe what remains. -->

## Validation

- [ ] Relevant locked pytest checks and changed-file Ruff checks pass; exact commands and results are recorded below.
- [ ] Native changes were tested with `make test-blender` against the exact packaged ZIP in an isolated profile; Blender/OS versions and results, or the reason this was not needed, are stated.
- [ ] Packaging changes pass `make build`; the ZIP and dependency licenses were inspected.
- [ ] UI changes include before/after screenshots and native input, focus and viewport evidence, with Blender/OS versions.
- [ ] Live/paid smoke status is stated. Any paid check had prior authorization for its project, exact quote and budget; private approval details remain private.

<!-- Validation evidence and relevant limitations: -->

## Public content

- [ ] No private account, customer, workspace, project or internal infrastructure records are exposed.
- [ ] No credentials, MCP bearer tokens, signed URL query strings or private job/asset IDs are included.
- [ ] No personal paths, agent session IDs, private research exports or spend anecdotes are included.

## Coding rules

- [ ] New first-party source files have the SPDX copyright and GPL-3.0-or-later headers; existing notices are preserved.
- [ ] Scenario service changes use the shared official SDK adapter or identify the documented issue-linked exception. Dependency changes include the exact bundle and applicable native validation.
- [ ] `scenario/core` remains free of `bpy`; Blender operations stay on the main thread, and UI drawing does not mutate properties.
- [ ] No em dashes or unrelated manual version/changelog edits are introduced; documentation and commands match the resulting behavior.

## Authorship and licensing

- [ ] Human review of the complete diff is recorded before merge.
- [ ] Original work is identified; adopted third-party code/assets retain their compatible licenses and attribution.
- [ ] Original contributions are licensed inbound=outbound under GPL-3.0-or-later, the repository license.

<!-- If an agent contributed, name the harness and retain accurate co-author
trailers on commits and in the final squash message. Human review may be pending. -->
