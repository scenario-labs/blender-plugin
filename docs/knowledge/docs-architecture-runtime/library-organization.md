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
    "base_revision": "72723f02a97a7226b1c697c31d8124b77ac92c86",
    "limits": "Reviewed the Native Library organization subsection and the edited closing sentences of the Native Library projection and attachment section against the Library view, the pure display module, AssetOrganization and the runtime pump: collection pages and one review card held as view state, collection reads and reviews through session.asset_organization with no new worker, transport or persisted property, operators preparing, applying and discarding while drawing only renders cached projections, the pump polling the shared owner before the Library view, a single row update per finished result from read-back records, refresh marks, a verified new collection joining the loaded list even when 200 are already loaded, and retirement with the session. Installed-ZIP Blender 5.1.2 tests on macOS arm64 with a stateful synthetic worker-thread service and offline unit tests cover these paths. Blender 5.0 and 5.2 were not run locally for this topic. No physical desktop input, focus, typing, Unicode or IME composition, Escape, viewport, small-window or alternate-DPI evidence and no screenshots exist for these controls; that evidence is pending under #66 and will be collected later in an unlocked session. No live collection, tag or bulk request was made from this repository; the observed already-member 400 and one-transaction add, service name uniqueness, DELETE body survival, tag normalization and live limits remain unverified here.",
    "sources": {
      "docs/architecture/runtime.md": "b6e556e94575e1e5207d3fa08e2ada3a2e0083e94ed0fd9fad2a90916ef2f5b6",
      "scenario/blender/library_view.py": "9d64adaa197fc1d212c95b3b256d61ff67acdc9456ef1266c61c3168b2c50f17",
      "scenario/core/ui/library_organization.py": "e583e5b900b4532c25f6fc146c97d4ab3989243a0295ec915546e6b9dadd974f",
      "scenario/blender/asset_organization.py": "597a1026ad96d07f563f54ff2651591dc9c9fc4bf6a3f19bee5bf43509ada7ce",
      "scenario/blender/runtime.py": "33461ba284a3b85282784f699e249a66df2f2503a55ad2acdda8756602957cae",
      "scenario/core/jobs/organization.py": "69ad48086ff2b763c565a22bce2bf60e142afbc10e757c56d938daf2198fbeba",
      "tests/blender/test_library_organization.py": "6da76fcae49830a07389f77dba025ce17fa5ae2750995bd52c94d90927579d7d",
      "tests/unit/test_library_organization.py": "5795cb464357418efa275114ecf0846a55b9dd102e9d2cd3cf4d1fa97dc90f16",
      "tests/blender/run_all.py": "f32e42a29f8c0403f6f1524d17fc3e020cb44ee4ec0173fe657c3ff609a74bba",
      "scenario/blender/job_session.py": "716ded390ab45861111d5ed0146d7ca3f28175c2730f2d2b9e6c7a0480ae7572"
    }
  }
}
---

# Native Library organization projection

Evidence for [the canonical guide](../../architecture/runtime.md#native-library-organization).
