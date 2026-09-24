# Releases

## Versioning and authorization

The maintainer merges release PRs and authorizes publication. Merging a release
PR starts automatic publication; it is not a preview or a packaging-only test.

New tags use `blender-plugin-vX.Y.Z`, package versions use `X.Y.Z`, and the archive
is `scenario-X.Y.Z.zip`. Preserve historical `v*` tags and releases. Let
release-please update the changelog, release manifest and package version fields.
Do not manually bump them in unrelated work. The extension remains experimental.

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
The helper is a partial implementation of
[#37](https://github.com/scenario-labs/blender-plugin/issues/37); release discovery,
automatic retention selection, the site builder, Pages deployment and native
setup/update controls remain separate integration work. Successful local generation
does not prove that an archive was published, attested or accepted at runtime.

Before using this for a published repository, verify each selected stable release
and its downloaded assets using the publication checks above. Exclude drafts and
prereleases. Create `inventory.json` next to the exact downloaded ZIP files with
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
