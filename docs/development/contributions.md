# Commits and pull requests

Use a short-lived `type/issue-description` branch and target `main`. Respect the
recorded base of an existing stacked PR; do not silently retarget it. Review the
complete PR diff and dependencies. Preserve unrelated work in other branches.

`commitlint.config.ts` is authoritative for Conventional Commit types, scopes,
the 120-character header limit and the no-em-dash rule. Choose the type from the
final diff, not the inherited title:

| Type                   | Change                                                    |
| ---------------------- | --------------------------------------------------------- |
| feat / fix / perf      | New capability, corrected product behavior or performance |
| refactor               | Product structure with unchanged behavior                 |
| test                   | Tests only                                                |
| docs                   | Documentation, agent instructions and command Markdown    |
| build                  | Package/build configuration                               |
| ci                     | Workflows and automation                                  |
| style / chore / revert | Formatting, maintenance or a revert                       |

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
