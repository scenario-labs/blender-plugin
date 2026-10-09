# Maintainers

This document is for repository admins and for agents that change repository
settings. Contributors read [CONTRIBUTING.md](../CONTRIBUTING.md); the release
procedure is [RELEASING.md](RELEASING.md). Every setting below is read back with
the command next to it; when a setting changes, the same pull request updates
this document.

The tables distinguish the inspected state from pending decisions. They do not
authorize settings changes. Re-read GitHub before acting: source checks cannot
prove that remote configuration still matches this record. Keep credentials,
raw private project exports and collaborator details out of public evidence.

## Branch model

`main` is the only long-lived development branch. Changes arrive through pull
requests from forks or short-lived `type/issue-description` branches and are
squash-merged. The Conventional Commit PR title becomes the commit header on
`main`; preserve contributor trailers in the squash body. See the
[commit guide](development/contributions.md).

Do not push directly to `main` or create release tags by hand. Release-please
owns the release PR, version changes and publication flow. New tags use
`blender-plugin-vX.Y.Z`; historical `v*` tags remain protected. Merging a release
PR authorizes publication, not just packaging validation. An older-release fix,
if needed, uses an explicitly reviewed, on-demand `release/X.Y` branch and
release-please target-branch configuration; the current workflow targets `main`.
There is no standing `develop` branch. Releases are ZIPs attached to tags, and
merging ordinary product work is not a deployment of the extension.

```sh
gh api repos/scenario-labs/blender-plugin/branches --paginate --jq '.[].name'
gh api repos/scenario-labs/blender-plugin --jq .default_branch
```

## Rulesets

All four listed rulesets are active. Empty exclusions apply to the listed
repository ref patterns.

| Ruleset | ID / target | Inspected rules | Bypass |
| --- | --- | --- | --- |
| main - integrity | `22257774`; branch `refs/heads/main` | No deletion or non-fast-forward updates; linear history; pull request with squash only and zero required approvals; extra approval for unattributed changes. Code quality severity `errors`. CodeQL security threshold `high_or_higher`, alert threshold `errors`. Required status checks `ci-ok`, `pr-title` and `commits`, all integration `15368`; strict up-to-date policy off, enforcement on creation on. | None |
| main - review | `22257776`; branch `refs/heads/main` | Pull request with squash only; one approval, dismiss stale reviews, resolve review threads, extra approval for unattributed changes. | `RepositoryRole` `5` (repository admin), `always` |
| versioning | `22257778`; tags `refs/tags/v*` and `refs/tags/blender-plugin-v*` | Restrict creation, updates, deletion and non-fast-forward updates. | Repository admin `5` and release App integration `4751046`, both `always` |
| Default security | `3247630`; inherited organization repository policy | Restrict repository creation, deletion and transfer. | `OrganizationAdmin`, `always` |

Both branch pull-request rules have code-owner approval and last-push approval
off, no specific required reviewers, and dismissal restrictions disabled. The
integrity rule also has stale-review dismissal and thread-resolution requirements
off; the review rule supplies those requirements. Admin review bypass does not
bypass integrity: direct pushes, force pushes and deletion of `main` remain
prohibited. Other contributors need the configured review approval; unattributed
changes require an additional approval. Tag restrictions have their own bypasses.

On 2026-10-09, `ci-ok` from [CI](../.github/workflows/ci.yml) was added to
required status checks after its successful GitHub Actions check identity
(integration `15368`) was verified. API readback confirms that every other
integrity rule, condition and bypass actor is unchanged; the review ruleset is
unchanged too. CodeQL and code-quality enforcement remain in the integrity
ruleset. Preserve the existing `commits` and `pr-title` checks.

Renaming a required check can block every merge until an administrator updates
its ruleset context. Coordinate the workflow and settings changes, then update
this record. Do not replace a ruleset from a historical example; read its complete
conditions, rules and bypass actors before an approved update.

```sh
gh api repos/scenario-labs/blender-plugin/rulesets
gh api repos/scenario-labs/blender-plugin/rules/branches/main
gh api repos/scenario-labs/blender-plugin/rulesets/22257774
gh api repos/scenario-labs/blender-plugin/rulesets/22257776
gh api repos/scenario-labs/blender-plugin/rulesets/22257778
gh api repos/scenario-labs/blender-plugin/rulesets/3247630
```

## Merge settings

| Setting | Inspected value |
| --- | --- |
| `allow_squash_merge` | `true` |
| `allow_merge_commit` | `false` |
| `allow_rebase_merge` | `false` |
| `allow_update_branch` | `true` |
| `delete_branch_on_merge` | `true` |
| `allow_auto_merge` | `true` |
| `squash_merge_commit_title` | `PR_TITLE` |
| `squash_merge_commit_message` | `COMMIT_MESSAGES` |
| `web_commit_signoff_required` | `false` |

`COMMIT_MESSAGES` retains branch commit messages for the proposed squash body.
Review the final body and co-author trailers before merging; the setting alone
does not verify attribution or release notes. There is no DCO sign-off or
copyright assignment; the [contribution licensing policy](../CONTRIBUTING.md#licensing-of-contributions)
applies. Release-please's configuration and proposed release PR remain the
source of truth for resulting notes and versions.

```sh
gh api repos/scenario-labs/blender-plugin --jq '{allow_squash_merge,allow_merge_commit,allow_rebase_merge,allow_update_branch,delete_branch_on_merge,allow_auto_merge,squash_merge_commit_title,squash_merge_commit_message,web_commit_signoff_required}'
```

## Security baseline

| Capability | Inspected state / remaining scope |
| --- | --- |
| Secret scanning, push protection, non-provider patterns, validity checks | Enabled |
| AI secret detection, delegated alert dismissal, delegated bypass | Disabled |
| Dependabot alerts and security updates | Enabled; automated fixes are not paused |
| Private vulnerability reporting | Enabled; use [SECURITY.md](../SECURITY.md) |
| CodeQL default setup | Configured; default suite, remote threat model, weekly, standard runner. API language values: `actions`, `javascript`, `javascript-typescript`, `python`, `typescript`. |
| Actions | Enabled; allowed actions `all`, SHA pinning not required administratively |
| Default workflow token | `read`; cannot approve pull requests |
| Fork PR workflow approval | `all_external_contributors` |
| Immutable releases | Disabled, not enforced by the owner; first-release verification remains #36 |

[Dependabot](../.github/dependabot.yml) currently updates GitHub Actions weekly.
The extension also has pinned Python/SDK dependencies and bundled wheels; the
old stdlib-only assumption is obsolete. Their coordinated update procedure is
[SDK_BUNDLE.md](SDK_BUNDLE.md), not automatic version updates from the Actions
configuration. Source checks enforce full action SHA pins, but that does not
establish repository-level pin enforcement or an allowed-action policy (#39).

```sh
gh api repos/scenario-labs/blender-plugin --jq .security_and_analysis
gh api repos/scenario-labs/blender-plugin/private-vulnerability-reporting
gh api repos/scenario-labs/blender-plugin/code-scanning/default-setup
gh api --include repos/scenario-labs/blender-plugin/vulnerability-alerts # 204 means enabled
gh api repos/scenario-labs/blender-plugin/automated-security-fixes
gh api repos/scenario-labs/blender-plugin/actions/permissions
gh api repos/scenario-labs/blender-plugin/actions/permissions/workflow
gh api repos/scenario-labs/blender-plugin/actions/permissions/fork-pr-contributor-approval
gh api repos/scenario-labs/blender-plugin/immutable-releases
```

## Features and metadata

### Supply-chain report

[Scorecard CI](../.github/workflows/scorecard.yml) publishes after pushes to
`main` and each Monday. The [public report](https://scorecard.dev/viewer/?uri=github.com/scenario-labs/blender-plugin)
and README badge reported **6.4** for `5d1f5a2` on 2026-09-25. The
[default-branch run](https://github.com/scenario-labs/blender-plugin/actions/runs/36132873905)
succeeded, and its Scorecard SARIF analysis appears alongside CodeQL without an
upload error or a finding against the Scorecard workflow itself. Scorecard is
informational and is not a required check. This is a dated publication check,
not a claim that its findings are resolved or that the extension is accepted.

Use the [triage procedure](development/contributions.md#scorecard-triage) for
current results. Paginate code-scanning analyses: frequent CodeQL uploads can
push the latest Scorecard result beyond the first API page.

### Repository presentation

Issues and projects are on; wiki and Discussions are off. Keep documentation in
this repository, and route questions through [SUPPORT.md](../SUPPORT.md), the
issue forms or `support@scenario.com`. The approved direction keeps Discussions
off; revisit after external participation justifies a monitored Q&A channel.
The wiki is already off and needs no further change under #20.

Pages is configured with build type `workflow`, custom domain `blender.scenario.com`
and enforced HTTPS. The handbook at `https://blender.scenario.com/` serves the
installation, update and support guidance; the repository homepage and
[extension manifest](../scenario/blender_manifest.toml) Website link point there.
This handbook publication does not establish native repository availability:
`/repo/index.json` remains intentionally absent until a verified adopted release
is published under #36/#37. The Pages API's `status: null` is not a content check;
verify the live response and page before changing these links again.

The description is:

> Scenario for Blender: AI images, video, 3D and PBR materials in the viewport, plus a local MCP server for agents. Blender 5.0+ extension, GPL-3.0-or-later.

The repository currently has no custom social preview: `usesCustomOpenGraphImage`
is `false`, and its image URL uses `opengraph.githubassets.com`. The replacement
card is pending under #19. After its reviewed source lands, regenerate it with
`uv run --locked --no-env-file python tools/make_social_preview.py` and upload
`docs/images/social-preview.png` by hand through Settings > General > Social
preview > Edit > Upload an image. Use the merged artifact, and re-upload after
any approved card change. Confirm `usesCustomOpenGraphImage` is `true`, the image
URL uses `repository-images.githubusercontent.com`, and the rendered shared-link
preview matches the intended card. A committed PNG does not prove the admin
upload or downstream preview acceptance.

Topics are `3d`, `agentic-ai`, `ai`, `blender`, `blender-addon`,
`blender-extension`, `generative-ai`, `mcp`, `mcp-server`, `python`, `scenario`,
`text-to-3d`, `text-to-image` and `text-to-video`.

```sh
gh api repos/scenario-labs/blender-plugin --jq '{has_issues,has_projects,has_wiki,has_discussions,has_pages,homepage,topics,description}'
gh api repos/scenario-labs/blender-plugin/pages
gh api graphql -f query='{ repository(owner:"scenario-labs", name:"blender-plugin") { usesCustomOpenGraphImage openGraphImageUrl } }'
```

## Access

The inspected repository team grant is `@scenario-labs/platform` with **admin**
permission. The original target was maintain; deciding and applying that change
remains #20/#21. Do not describe the target as already applied or reduce access
without the owner's decision. [CODEOWNERS](../.github/CODEOWNERS) requests reviews
for specific release, automation, licence and security paths; it grants no access
and required code-owner approval remains off. Review the direct-collaborator
policy separately under #21 without publishing personal access records.

Repository admins can bypass the review ruleset, and admins plus the release
App can bypass versioning. Nothing bypasses main integrity. A collaborator's
write permission does not permit a direct update to protected `main`.
Administrative API access depends on the caller's repository/organization role
and token permissions. A permission error is not evidence that a feature is
disabled; do not automatically expand token scopes or change grants to inspect it.

```sh
gh api repos/scenario-labs/blender-plugin/teams --jq '.[] | {slug, permission}'
gh api orgs/scenario-labs/teams/platform/repos/scenario-labs/blender-plugin \
  -H 'Accept: application/vnd.github.v3.repository+json' --jq .role_name
```

### Smoke lane

The [paid smoke workflow](../.github/workflows/smoke.yml) requires the existing
`smoke` environment, at least one required reviewer and a custom deployment
policy allowing exactly the `main` branch. Its read-only admission checks use
GitHub's [environment API](https://docs.github.com/en/rest/deployments/environments#get-an-environment)
and [branch-policy API](https://docs.github.com/en/rest/deployments/branch-policies#list-deployment-branch-policies).
These checks run before the protected job and again after approval. A missing or
unreadable gate fails closed. API readback on
2026-10-09 confirms the environment exists, requires the maintainer reviewer,
allows self-review for an explicitly approved dispatch, and accepts exactly the
`main` branch. The workflow itself still never creates or relaxes these rules.

The authorized test key/default scope, private plan and recovery secret were
installed as environment secrets on 2026-10-09. Secret values were passed through
private standard input and never logged. The recovery passphrase is retained
privately outside Git. Environment secrets are:

- `SCENARIO_TEST_API_KEY` and `SCENARIO_TEST_API_SECRET`.
- Optional `SCENARIO_TEST_PROJECT_ID`; blank is the key's default scope.
- `SMOKE_PLAN_JSON`, following the [private suite format](../tests/smoke/README.md#one-aggregate-budget-for-a-suite).
- `SMOKE_RECOVERY_PASSPHRASE`, a randomly generated secret of at least 32 characters,
  retained privately for decrypting artifacts after rotation.

The repository variable `SMOKE_MAX_TOTAL_CU` remains unset, so scheduled runs have
no positive allowance and fail admission before the protected job. A manual
validation run is separately budget-authorized; it does not enable recurring spend.
Set that repository variable only after agreeing on the monthly
scheduled plan and per-run aggregate allowance. It has no positive default.
Configure any provider-side project/monthly budget separately; the workflow's cap
is per run, and manual runs do not share a monthly ledger. The approval job shows
the cap frozen by admission. Review that amount and the configured private plan
and scope before approving. Version-2 plans also authorize exact input files and
hashes from the checked-out repository; the protected job stages them privately
and uploads through shared durable commands before quoting. Approval covers
those uploads even if model validation or the cap later prevents generation.
Do not put paid secrets at repository scope merely
to bypass this environment; the free API audit remains separate.

Actions reruns are refused, even after an apparently early failure. Recover from
the encrypted archive with the original scope using the non-submitting resume
command. A new dispatch requires a new spending decision, never an assumed retry.
See [hosted recovery and limits](../tests/smoke/README.md#protected-hosted-execution-and-recovery).
The [zero-cap hosted check](https://github.com/scenario-labs/blender-plugin/actions/runs/37946825690)
failed admission and skipped the protected job, with no Scenario request.
The [authorized hosted check](https://github.com/scenario-labs/blender-plugin/actions/runs/37946893572)
passed admission and visibly paused at the required-reviewer gate before approval.
Its result and encrypted recovery validation remain pending until recorded below;
configuration and a paused job alone do not establish live completion under #40/#68.

## Project and labels

[Blender Plugin project 31](https://github.com/orgs/scenario-labs/projects/31)
is **private**. Public issues remain visible and are triaged on that private
board. Visibility is an owner decision under #20; this document does not make
the project public or disclose its item inventory.

| Field | Options, including the actual emoji spelling |
| --- | --- |
| Status | `📋 Backlog`, `🔖 Next`, `🏗 In progress`, `👀 In review`, `👀 Staging`, `✅ Released`, `🗑️ Dropped` |
| Priority | `P0 🌋`, `P1 🏔`, `P2 🏕`, `P3 🏝` |
| Effort | `Tiny 🦔`, `Small 🐇`, `Medium 🐂`, `Large 🦑`, `xLarge 🐋` |

Current views are `View 1` (table) and `Board` (board). Enabled workflows are
`Auto-add sub-issues to project`, `Item added to project`, `Item closed` and
`Pull request merged`. `Auto-close issue` and `Pull request linked to issue` are
disabled. No Auto-archive workflow appears in the inspected response. Desired
views are By Priority (table grouped by Priority), By size (table grouped by
Effort), Roadmap (board by Status) and By Type (table grouped by issue type).
Those views, Auto-archive configuration and the exact workflow targets still
require project UI review under #20.
An enabled flag alone does not prove its trigger/filter/target is correct.

Epics live in [scenario-labs/roadmap](https://github.com/scenario-labs/roadmap);
the project's enabled sub-issue workflow is intended to add their sub-issues.
Labels are curated: shared roadmap labels plus `area:*`, `blender:*`, `os:*`,
`needs-repro`, `needs-info`, `model-behaviour` and `known-limit`. Do not blindly
clone another repository's labels. Older Blender labels remain useful for
historical reports and do not establish current runtime support.

```sh
gh project view 31 --owner scenario-labs --format json
gh project field-list 31 --owner scenario-labs --format json
gh label list --repo scenario-labs/blender-plugin --limit 100
gh api graphql -f query='{ organization(login:"scenario-labs") { projectV2(number:31) { public views(first:20){nodes{name layout}} workflows(first:30){nodes{name enabled}} } } }'
```

## Open admin steps

These tasks retain their existing owner issues. Read back the result and update
this guide after an authorized change; do not treat the checklist as permission
to perform it.

- [ ] Finish authorized hosted smoke and encrypted-recovery acceptance: #40. The environment, reviewer, main-only policy and private secrets are configured; recurring allowance remains disabled.
- [x] Add and read back the `ci-ok` required check with its verified GitHub Actions identity; preserve existing `pr-title`, `commits`, CodeQL, code-quality and review rules: #45. Hosted negative-check evidence and this documentation merge remain part of issue completion.
- [ ] Verify the first automated release, then remove the repository-admin tag bypass while retaining release App integration `4751046`, both tag patterns and all protection rules; enable immutable releases only after publication and download verification: #36.
- [ ] Decide restricted allowed actions and require SHA pinning after workflow pins and update behavior are verified: #39.
- [ ] Complete #56: the published handbook, homepage and manifest Website link are aligned; desktop Website-action acceptance remains. Native update publication remains #37.
- [ ] Upload the reviewed, merged social-preview card and verify its custom-image flag, URL and rendered shared-link preview: #19.
- [ ] Decide the platform team's maintain/admin grant and confirm required code-owner review and direct-write policy: #20 / #21.
- [ ] Decide project visibility; finish the requested views, Auto-archive and built-in workflow targets through the project UI: #20.

Release-App setup belongs to completed #35: the current workflow references its
organization-provided client ID/private-key secrets, and the tag ruleset includes
the App bypass. Do not re-install or replace credentials as a routine release
step. Secret availability and publication success still require the release
acceptance in #36; this guide does not reveal secret values or claim a release
has been published. Wiki-off is verified. Remaining #20 acceptance is the access
and project decision work above, plus review of this baseline.
