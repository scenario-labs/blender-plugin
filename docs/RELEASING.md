# Releases

## Versioning and authorization

The maintainer merges release PRs and authorizes publication. Merging a release
PR starts automatic publication; it is not a preview or a packaging-only test.

New tags use `blender-plugin-vX.Y.Z`, package versions use `X.Y.Z`, and the archive
is `scenario-X.Y.Z.zip`. Preserve historical `v*` tags and releases. Let
release-please update the changelog, release manifest and package version fields.
Do not manually bump them in unrelated work. The extension remains experimental.

The [release configuration](../release-please-config.json) uses semantic versions.
Before 1.0, fixes increase the patch version, features increase the minor version,
and breaking changes increase the minor version. After 1.0, breaking changes
increase the major version. Mark a breaking change with `!` or a
`BREAKING CHANGE` footer; review the proposed version before merging the release PR.

1.0.0 is a deliberate maintainer decision, not an automatic bump: use a
`Release-As: 1.0.0` footer on the squash commit of an ordinary PR whose description
explains why the extension is considered stable. This policy documents the
mechanism; it does not authorize a stability declaration or publication.

## Correcting a version or release note

For an intentional version override, the maintainer places a
`Release-As: X.Y.Z` footer in the ordinary PR's squash body. Preserve attribution
and issue references. Review the next generated release PR to confirm the
requested version; do not edit the manifest, package version or changelog by hand.
See [release-please's version override](https://github.com/googleapis/release-please#how-do-i-change-the-version-number).

Retitle a wrongly typed PR before merging it. For a squash-merged PR whose
unreleased note needs correction, maintainers can add a `BEGIN_COMMIT_OVERRIDE`
and `END_COMMIT_OVERRIDE` block to that merged PR's body with the corrected
Conventional Commit message. Keep required trailers in the replacement and
inspect the refreshed release PR before publication. Follow the
[upstream override format](https://github.com/googleapis/release-please#how-can-i-fix-release-notes).
This does not rewrite Git history or authorize editing published release assets.

## Extension id

The extension id is `scenario` and it is final. Blender scopes extension modules
per repository (`bl_ext.<repository_module_name>.scenario`), so the module
namespace also identifies the configured repository. The updater matches the id
against that repository's `index.json`; it also contributes to the per-user state
and cache paths returned by `bpy.utils.extension_path_user` in
[runtime.py](../scenario/blender/runtime.py). Renaming it would break update
matching and leave existing user state behind.

Distribution uses GitHub release assets; the planned hosted extension repository
is tracked in #37. Publishing there does not require a globally unique id on
extensions.blender.org. Keep the id unique within our own repository.
[Manifest tests](../tests/unit/test_manifest.py) enforce this decision and the
approved Blender 5.0 floor alongside metadata, tags, GPL and permission rules.
The offline tests are a scoped early check; native ZIP validation and supported
Blender runtime acceptance remain separate requirements.

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
native behavior must also pass 5.0, 5.1 and 5.2 under isolated profiles.

## First automated release acceptance

Complete these checks when publishing the first automated release:

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
- After the first automated tag succeeds, remove the repository-admin bypass
  from tag protection. Preserve the release App bypass, both `refs/tags/v*`
  and `refs/tags/blender-plugin-v*`, and all tag protection rules.
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

## Offline extension repository snapshots

[repository.py](../tools/repository.py) prepares a new local repository directory
from an explicit inventory of already-built archives. It uses Blender's native
`extension validate` and `extension server-generate` commands in a fresh isolated
profile with online access disabled. It never rebuilds a ZIP or changes a manifest.
The helpers are a partial implementation of
[#37](https://github.com/scenario-labs/blender-plugin/issues/37); network discovery,
Pages deployment and native setup/update controls remain
separate integration work. Successful local generation
does not prove that an archive was published, attested or accepted at runtime.

[`make site`](../CONTRIBUTING.md#complete-site-snapshots) combines this generator
with the handbook renderer in one new output directory. Supply the retained
inventory below with `SITE_ARGS="--inventory selected-assets/inventory.json"`.
The site retains every selected archive byte-for-byte beneath `repo/`; docs-only
rebuilds must reuse that complete inventory. The complete guide and repository
are staged before exposing the output, and existing output is never replaced.
This command does not discover releases, verify attestations or deploy Pages.
Publication remains a separate gate requiring a fresh verified inventory so a
stale docs build cannot roll the hosted repository back.

### Select retained releases offline

[release_inventory.py](../tools/release_inventory.py) selects exact downloaded
archives from a complete, recent paginated GitHub release snapshot. Export that
snapshot with this read-only command:

```sh
gh api repos/scenario-labs/blender-plugin/releases --paginate --slurp > releases.json
```

Keep each release's downloaded `scenario-X.Y.Z.zip` and `SHA256SUMS` together in
`downloaded-assets/blender-plugin-vX.Y.Z/`. Verify their provenance using the
publication checks above. The selector itself makes no network requests and does
not verify attestations, tag commit identity, snapshot completeness or current
publication state. A metadata file and matching checksum are not provenance.

Supply the supported matrix explicitly. This example selects for Blender 5.0,
5.1 and 5.2 and the extension's four declared platforms:

```sh
uv run --locked --no-env-file python tools/release_inventory.py \
  --releases releases.json --assets downloaded-assets --output selected-assets \
  --blender-version 5.0.0 --blender-version 5.1.0 --blender-version 5.2.0 \
  --platform linux-x64 --platform windows-x64 \
  --platform macos-arm64 --platform macos-x64
```

For each Blender/platform pair, selection chooses the highest numeric stable
version whose manifest covers it, regardless of release dates or snapshot order.
It retains the union of those choices, including an older release needed for a
different compatibility range. Drafts, prereleases and historical tags outside
`blender-plugin-vX.Y.Z` are excluded. All remaining candidates must have exact
tag/archive/manifest version and extension identity, canonical release asset
URLs, bounded sizes, matching checksums, safe ZIP layouts and valid SDK bundles.
A damaged newer candidate fails the run instead of silently downgrading.

Uncovered matrix cells and overlapping retained Blender/platform ranges fail.
The selector never changes a manifest to resolve overlap, rewrites an archive,
or invents compatibility. Selection uses declared Blender/platform ranges;
Python wheel support and runtime acceptance still need native validation. The
new output directory contains only the unchanged selected ZIPs and an inventory
accepted by `repository.py`. Existing output is preserved and failed preparation
leaves no partial snapshot. Keep the inputs and output untracked. Empty adopted
release channels fail; prototype releases are not substitutes.

### Validate and generate the repository

Before using this for a published repository, verify each selected stable release
and its downloaded assets using the publication checks above. Exclude drafts and
prereleases. Use the selector's output, or create `inventory.json` manually next
to the exact downloaded ZIP files with
this structure, replacing the illustrative version, filename, checksum and size
with the verified values:

```json
{
  "schema_version": 1,
  "extension_id": "scenario",
  "archives": [
    {
      "file": "scenario-1.0.0.zip",
      "version": "1.0.0",
      "sha256": "0000000000000000000000000000000000000000000000000000000000000000",
      "size": 12345
    }
  ]
}
```

Choose the stable archives needed for the supported Blender/platform matrix;
do not supply every historical release. All supplied entries are retained,
including older versions needed by a different compatibility range. Entries
with overlapping Blender ranges on any common platform are rejected, even if
their release versions or Python wheel tags differ. A missing maximum means no
upper bound; a maximum is exclusive. Missing platforms means all platforms.
Adjacent Blender ranges and disjoint platform sets are allowed. The tool never
silently chooses a winner or alters old manifests to make overlapping releases fit.

```sh
uv run --locked --no-env-file python tools/repository.py \
  --blender /path/to/blender \
  --inventory /path/to/verified-assets/inventory.json \
  --output dist/repository-snapshot
```

The output directory must not exist. The helper checks each archive's identity,
stable three-component version, size, SHA-256, safe ZIP layout and own SDK bundle
lock, then validates it with Blender. It cross-checks every generated index entry
against its archive, including Blender/platform/Python compatibility, hash, size
and a relative URL resolving to the exact file. Missing, extra or inconsistent
entries fail. ZIP filenames must be plain ASCII filenames; symlinks are rejected.

The completed snapshot contains the unchanged ZIPs, sorted `index.json`, an HTML
listing and normalized `inventory.json`. Replaying that inventory with the same
Blender executable produces identical file contents. Generation failures leave
no partial output and preserve existing snapshots; native logs remain under
`.blender-profile` (or `--artifacts`). Keep generated snapshots untracked. The
existing `tools/build.py --repo` remains a local current-source build convenience;
it does not verify a retained release inventory.

## Included commit types

[release-please-config.json](../release-please-config.json) includes every type
accepted by commitlint: `feat`, `fix`, `perf`, `revert`, `docs`, `chore`, `ci`,
`test`, `refactor`, `build` and `style`. Maintenance and documentation changes
appear in their own sections alongside product changes. Commitlint validates
messages; release-please controls their visibility in the generated notes.

Keep these sections aligned when adding a commit type. Visible maintenance-only
changes can produce a patch release proposal; feature and breaking-change
version rules remain unchanged. Merging a configuration change refreshes the
open release PR on the next successful release-please run. Review the generated
notes there before merging the release PR.

## Public changelog

[publish-changelog.yml](../.github/workflows/publish-changelog.yml) runs after
publication or by explicit manual dispatch for a published stable tag. It skips
bodies without changelog sections and requires `CHANGELOG_INGEST_SECRET`.
The workflow sends release notes to the Scenario changelog and checks the
response for the exact release version. A successful HTTP status alone is
insufficient: a response can report that processing failed.

`queued` means accepted for asynchronous processing. `already exists` means the
version has been received before; check its public visibility rather than
assuming it was published. Verify the entry appears at
[scenario.com/changelog](https://www.scenario.com/changelog) under Plugins with
a `Plugins - Blender` title.

After a timeout or ingest failure, check the changelog and the workflow result
before retrying. The workflow does not automatically repeat the POST or request
an overwrite. If an existing entry is not visible, contact the changelog
maintainer. Changelog recovery is independent of the release workflow and must
not republish or rebuild release assets.
