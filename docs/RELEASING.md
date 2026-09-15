# Releases

## Versioning and authorization

The maintainer merges release PRs and authorizes publication. Merging a release
PR starts automatic publication; it is not a preview or a packaging-only test.

New tags use `blender-plugin-vX.Y.Z`, package versions use `X.Y.Z`, and the archive
is `scenario-X.Y.Z.zip`. Preserve historical `v*` tags and releases. Let
release-please update the changelog, release manifest and package version fields.
Do not manually bump them in unrelated work. The next planned release is 0.9.10;
the Blender minimum change in PR #62 intentionally has neither `!` nor a
`BREAKING CHANGE` footer.

The extension remains experimental. The first supported consolidated release
also requires Studio adoption, browser OAuth, shared scoped UI/MCP jobs, compact
creation and native updates. Track acceptance in
[roadmap #674](https://github.com/scenario-labs/roadmap/issues/674) and
[#68](https://github.com/scenario-labs/blender-plugin/issues/68).

## Pipeline

[release-please.yml](../.github/workflows/release-please.yml) runs on pushes to
`main`:

1. Discover an unfinished draft or create a release draft when a release is due.
2. Check out its exact commit and require the release SHA, triggering workflow
   SHA and checkout SHA to match.
3. Build with Blender 5.0.1 on Linux, require `LICENSE`, validate the ZIP, generate
   `SHA256SUMS` and attest both files. Attach the files to the draft.
4. Validate that same ZIP with Blender 5.1.2 and 5.2.1.
5. Publish only after those jobs succeed. Publication creates the tag through
   the release App and triggers the separate public-changelog workflow.
6. Generate/update the next release PR after publication, or when no release
   was due.

A green run with skipped assets, validation and publish jobs proves release-PR
generation only. ZIP validation proves package format, not native runtime or
dependency compatibility. The minimum is Blender 5.0; the exact bundled SDK and
native behavior must also pass 5.0, 5.1 and 5.2 under isolated profiles (#32/#64).
Native extension repository delivery remains separate work in #37.

## First automated release acceptance

Track these unfinished checks in [#36](https://github.com/scenario-labs/blender-plugin/issues/36)
and [roadmap #672](https://github.com/scenario-labs/roadmap/issues/672), even if
the implementation issue was automatically closed by a merge:

- Review the release PR's complete diff and checks. Expect the changelog,
  `.release-please-manifest.json`, `scenario/__init__.py` and
  `scenario/blender_manifest.toml` version updates.
- After the maintainer merges, record the original workflow run and release
  commit. Verify successful Linux build, both validation jobs and publication.
- Verify the published tag resolves to that commit. Download the published
  assets into an empty directory and run:

  ```sh
  gh release download blender-plugin-vX.Y.Z -R scenario-labs/blender-plugin \
    --pattern scenario-X.Y.Z.zip --pattern SHA256SUMS
  shasum -a 256 -c SHA256SUMS
  gh attestation verify scenario-X.Y.Z.zip -R scenario-labs/blender-plugin
  gh attestation verify SHA256SUMS -R scenario-labs/blender-plugin
  ```

  Inspect the verified provenance source commit and workflow identity against
  the original run. Record the evidence; a matching checksum alone is insufficient.
- After the first automated tag succeeds, the repository admin removes only
  the RepositoryRole 5 bypass from tag ruleset 22257778. Preserve Integration
  4751046, both `refs/tags/v*` and `refs/tags/blender-plugin-v*`, and all tag rules.
- After successful publication and download verification, the repository admin
  enables immutable releases and reads the setting back. Do not edit historical
  releases to make them immutable. Once enabled, a broken release needs a new
  version, never an edited asset.

## Recovery

For a transient build, upload or admin failure, rerun the **original workflow
commit**. Do not rebuild an older draft from newer `main`: the triggering commit
is part of signed provenance. Rerunning the original run cannot pick up a later
code fix; a code/workflow correction requires a separately reviewed release
path. Do not delete drafts or alter tags as an automatic recovery step.

Release-App credentials, installation and bypass configuration should be checked
only when evidence points to an access failure. They are not routine setup steps
for each release.

## Public changelog

[publish-changelog.yml](../.github/workflows/publish-changelog.yml) runs after
publication or by explicit manual dispatch for a published stable tag. It skips
bodies without user-facing sections and requires `CHANGELOG_INGEST_SECRET`.
Organization-level secret access is visible through
`gh api repos/scenario-labs/blender-plugin/actions/organization-secrets`; an empty
`gh secret list` does not establish that the secret is missing.

The website must deploy
[website #235](https://github.com/scenario-labs/scenario-com-landing-page/pull/235)
and apply migration `20260911_100000` before Blender ingestion is ready. Verify
the production deployment contains that merge and obtain migration evidence
for both the `blender-plugin` source enum value and `blender_plugin_prompt`
column. Merge into `develop`, a preview deployment or a reachable public page
does not prove this.

The endpoint can return HTTP 200 with database or queue failures. The workflow
requires an acknowledgement for the exact version and fails on those errors.
`queued` means accepted for asynchronous processing. `already exists` may refer
to a processing or failed record, so it warns and requires checking website
status. Neither response proves publication. Verify the public entry has the
Plugins group, a `Plugins - Blender` title and a `plugins-blender-vX-Y-Z` slug.

After a timeout or ingest failure, inspect database/queue state before retrying.
The workflow does not automatically repeat the POST or request an overwrite.
Rerunning cannot repair an existing failed entry; website recovery or overwrite
needs a separate authorized action. Changelog recovery is independent of the
release workflow and must not republish or rebuild release assets.
