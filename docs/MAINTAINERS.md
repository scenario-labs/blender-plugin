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
| main - integrity | `22257774`; branch `refs/heads/main` | No deletion or non-fast-forward updates; linear history; pull request with squash only and zero required approvals; extra approval for unattributed changes. Code quality severity `errors`. CodeQL security threshold `high_or_higher`, alert threshold `errors`. Required status checks `pr-title` and `commits`, both integration `15368`; strict up-to-date policy off, enforcement on creation on. | None |
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

`ci-ok` exists in [CI](../.github/workflows/ci.yml), but is **not currently a
required status check**. CodeQL enforcement is already in the integrity ruleset,
not the review ruleset proposed in the original audit. Reconcile the remaining
required-check decision under #45 without dropping the existing `commits`, CodeQL
or code-quality protection. Do not replace a ruleset from a historical example;
read its complete conditions, rules and bypass actors before an approved update.

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

Issues and projects are on; wiki and Discussions are off. Keep documentation in
this repository, and route questions through [SUPPORT.md](../SUPPORT.md), the
issue forms or `support@scenario.com`. The approved direction keeps Discussions
off; revisit after external participation justifies a monitored Q&A channel.
The wiki is already off and needs no further change under #20.

Pages is configured with build type `workflow` and URL
`https://scenario-labs.github.io/blender-plugin/`; its API status is `null`.
Configuration is not proof that the handbook is deployed (#37). The repository
homepage is `https://www.scenario.com`. The
[extension manifest](../scenario/blender_manifest.toml) points its Website link
to this repository. Move both to the Pages handbook only after its publication
and content are verified, under #56.

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

- [ ] Add/reconcile the `ci-ok` required check after verifying its reported identity; retain the existing `pr-title`, `commits`, CodeQL and code-quality rules unless an explicit reviewed decision changes them: #45.
- [ ] Verify the first automated release, then remove the repository-admin tag bypass while retaining release App integration `4751046`, both tag patterns and all protection rules; enable immutable releases only after publication and download verification: #36.
- [ ] Decide restricted allowed actions and require SHA pinning after workflow pins and update behavior are verified: #39.
- [ ] Verify the published Pages handbook, then switch the homepage and manifest Website link: #56.
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
