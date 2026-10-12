---
{
  "type": "Evidence",
  "id": "docs-architecture-runtime.library-organization",
  "title": "Native Library organization projection",
  "evidence": {
    "path": "docs/architecture/runtime.md",
    "scope": "library-organization",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-12",
    "base_revision": "3acb9625dc28bc74a6b764163ce6a6ca27144528",
    "limits": "Reviewed the Native Library organization subsection and the edited closing sentences of the Native Library projection and attachment section against the Library view, the pure display module, AssetOrganization and the runtime pump: collection pages and one review card held as view state, collection reads and reviews through session.asset_organization with no new worker, transport or persisted property, operators preparing, applying and discarding while drawing only renders cached projections, the pump polling the shared owner before the Library view, a single row update per finished result from read-back records, refresh marks, a verified new collection joining the loaded list even when 200 are already loaded, a page or collection read still running when the read-back arrives taking it once more, a ready card naming an agent's change that holds the owner's single apply, with Apply refused for that reason, and retirement with the session. Installed-ZIP Blender 5.1.2 tests on macOS arm64 with a stateful synthetic worker-thread service and offline unit tests cover these paths. Blender 5.0 and 5.2 were not run locally for this topic. A physical macOS 27 arm64, Blender 5.1.2 desktop pass on an earlier candidate of this branch, at UI scales 1 and 2 and in a 1018 by 671 point window, passed Library loads, dialog focus, Unicode tags, Escape, Cancel and outside clicks, Discard and Dismiss without requests and viewport shortcuts afterwards; Japanese IME composition did not start in the native text field, as in Blender's own fields. It found the review card out of view after OK on a lower row, Refresh and Load collections drawn disabled after their reads until the pointer moved, and an outdated hint after a load found no collections; the card placement, read-enabled controls and dialog text that replace them, Apply on a desktop, Blender 5.0 and 5.2 and other platforms still need a desktop check under #66. Its screenshots stay private. No live collection or tag write was made from this repository, and that desktop pass made reads only; the observed already-member 400 and one-transaction add, service name uniqueness, DELETE body survival, tag normalization and live limits remain unverified here. The latest installed run was on this branch on main 3acb9625, after its restack onto the parent's rebase over the local Film export owner, which conflicted only in evidence records; the full run passed. The three installed tests for the Library fixes that keep read-back on rows and collections a running read replaces and name an agent's change holding the single apply failed before those fixes.",
    "sources": {
      "docs/architecture/runtime.md": "4fd8326ed4eefb6766088348d7229ab5a02650457dfe1bd800e8b42bd0f241b5",
      "scenario/blender/library_view.py": "8f69ff39c990e3cc6cffd2c5980397c8d1b68241bf6f31d58885d52ca6fc0254",
      "scenario/core/ui/library_organization.py": "922eba9285e9794e3269dd60e7f28f6b2fe4dca334703dc2d7e2f42b55829e3c",
      "scenario/blender/asset_organization.py": "2cddba739852c4f914398b8c9fd1d98029122fdb468aab61456268183f1fc75f",
      "scenario/blender/runtime.py": "5ff43fb59215fed469c0638a660a679a6c15fd63a0148169031e01a4b6dfcfd7",
      "scenario/core/jobs/organization.py": "69ad48086ff2b763c565a22bce2bf60e142afbc10e757c56d938daf2198fbeba",
      "tests/blender/test_library_organization.py": "4422a822b32be3bb3e48b34318ebe2f69db471f943a970f09af5c5af6d832b70",
      "tests/unit/test_library_organization.py": "798a3df61cb6c91af8c3e0cce2d957144b87ab9d92bd174bd4dc62383510a5d4",
      "tests/blender/run_all.py": "808c5fc5fa9fe528c1bceb709b527834107e0ebc9dc587df6cb262a558b35b34",
      "scenario/blender/job_session.py": "f065103af678936bdd575474698ae7d36cea79f4269ae668fb5d7acd865ddddf"
    }
  }
}
---

# Native Library organization projection

Evidence for [the canonical guide](../../architecture/runtime.md#native-library-organization).
