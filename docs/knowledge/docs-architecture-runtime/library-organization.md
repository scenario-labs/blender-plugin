---
{
  "type": "Evidence",
  "id": "docs-architecture-runtime.library-organization",
  "title": "Native Library organization projection",
  "evidence": {
    "path": "docs/architecture/runtime.md",
    "scope": "library-organization",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-11",
    "base_revision": "1d86f53d3489b23f2447be69cb589140e2f3ba64",
    "limits": "Reviewed the Native Library organization subsection and the edited closing sentences of the Native Library projection and attachment section against the Library view, the pure display module, AssetOrganization and the runtime pump: collection pages and one review card held as view state, collection reads and reviews through session.asset_organization with no new worker, transport or persisted property, operators preparing, applying and discarding while drawing only renders cached projections, the pump polling the shared owner before the Library view, a single row update per finished result from read-back records, refresh marks, a verified new collection joining the loaded list even when 200 are already loaded, and retirement with the session. Installed-ZIP Blender 5.1.2 tests on macOS arm64 with a stateful synthetic worker-thread service and offline unit tests cover these paths. Blender 5.0 and 5.2 were not run locally for this topic. A physical macOS 27 arm64, Blender 5.1.2 desktop pass on an earlier candidate of this branch, at UI scales 1 and 2 and in a 1018 by 671 point window, passed Library loads, dialog focus, Unicode tags, Escape, Cancel and outside clicks, Discard and Dismiss without requests and viewport shortcuts afterwards; Japanese IME composition did not start in the native text field, as in Blender's own fields. It found the review card out of view after OK on a lower row, Refresh and Load collections drawn disabled after their reads until the pointer moved, and an outdated hint after a load found no collections; the card placement, read-enabled controls and dialog text that replace them, Apply on a desktop, Blender 5.0 and 5.2 and other platforms still need a desktop check under #66. Its screenshots stay private. No live collection or tag write was made from this repository, and that desktop pass made reads only; the observed already-member 400 and one-transaction add, service name uniqueness, DELETE body survival, tag normalization and live limits remain unverified here. Rechecked after the Library view started drawing the review card under the organized asset's row, left the controls that start a read enabled while it runs, named a connection without collections in the Organize dialog and kept a settled card's outcome shown after another caller's prepare evicts its review: the view still prepares, applies and discards only through the shared owner, sends nothing new and draws read-only, so these claims are unchanged. Rechecked after a restack onto the MCP branch's rebase onto main 1d86f53d, which conflicted only in evidence records: main's merged changes to the runtime map, the runtime pump, JobSession and the installed test list leave this subsection, the pump order (the shared owner before the Library view) and the session retiring the view and its reviews unchanged. The installed tests last ran on this branch before that restack; only the unit suite ran locally after it.",
    "sources": {
      "docs/architecture/runtime.md": "81db351224c74e912c8775b6306733689f626dab07448bef5ada4bed4d988037",
      "scenario/blender/library_view.py": "c6edd4e8d63907cb7cbb36fde39963b38844b40e9dbc5f21de99381cd0cfc5a3",
      "scenario/core/ui/library_organization.py": "e6e3b208a4cb375412fc73779ed15ae56c9e9ea63d883a90d5ec54f6d868def4",
      "scenario/blender/asset_organization.py": "597a1026ad96d07f563f54ff2651591dc9c9fc4bf6a3f19bee5bf43509ada7ce",
      "scenario/blender/runtime.py": "67fdc8cb36158ef2bcf51c3d43d3db76fb8981b63ac18c5f5915819762bce983",
      "scenario/core/jobs/organization.py": "69ad48086ff2b763c565a22bce2bf60e142afbc10e757c56d938daf2198fbeba",
      "tests/blender/test_library_organization.py": "100262ba2e1c546fba06d25e06c6f6b778eb90cf0a01bf73447cb91f908834a6",
      "tests/unit/test_library_organization.py": "d820a1028a2ec18e8da636708e1c02618a006d47f5838c77a07e85dcc6b0be89",
      "tests/blender/run_all.py": "a3c22695eb7385958cc220fe7393e27a1fad92d135dc71a5d4c4279712c53b16",
      "scenario/blender/job_session.py": "e2e6533c21e38805235a9929c8725445dfca9abbe14f085ddf73c1d3bfc9ef42"
    }
  }
}
---

# Native Library organization projection

Evidence for [the canonical guide](../../architecture/runtime.md#native-library-organization).
