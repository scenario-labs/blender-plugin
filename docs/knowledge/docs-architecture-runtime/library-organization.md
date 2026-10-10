---
{
  "type": "Evidence",
  "id": "docs-architecture-runtime.library-organization",
  "title": "Native Library organization projection",
  "evidence": {
    "path": "docs/architecture/runtime.md",
    "scope": "library-organization",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-10",
    "base_revision": "33d00b0554151c4de04731fd1a5e5c64ed50855b",
    "limits": "Reviewed the Native Library organization subsection and the edited closing sentences of the Native Library projection and attachment section against the Library view, the pure display module, AssetOrganization and the runtime pump: collection pages and one review card held as view state, collection reads and reviews through session.asset_organization with no new worker, transport or persisted property, operators preparing, applying and discarding while drawing only renders cached projections, the pump polling the shared owner before the Library view, a single row update per finished result from read-back records, refresh marks, a verified new collection joining the loaded list even when 200 are already loaded, and retirement with the session. Installed-ZIP Blender 5.1.2 tests on macOS arm64 with a stateful synthetic worker-thread service and offline unit tests cover these paths. Blender 5.0 and 5.2 were not run locally for this topic. No physical desktop input, focus, typing, Unicode or IME composition, Escape, viewport, small-window or alternate-DPI evidence and no screenshots exist for these controls; that evidence is pending under #66 and will be collected later in an unlocked session. No live collection, tag or bulk request was made from this repository; the observed already-member 400 and one-transaction add, service name uniqueness, DELETE body survival, tag normalization and live limits remain unverified here.",
    "sources": {
      "docs/architecture/runtime.md": "8b26e9f850cc15600c3725f5e3abfbb6d337ff6d241ec659f0df2b8a016e9e1c",
      "scenario/blender/library_view.py": "9d64adaa197fc1d212c95b3b256d61ff67acdc9456ef1266c61c3168b2c50f17",
      "scenario/core/ui/library_organization.py": "e583e5b900b4532c25f6fc146c97d4ab3989243a0295ec915546e6b9dadd974f",
      "scenario/blender/asset_organization.py": "597a1026ad96d07f563f54ff2651591dc9c9fc4bf6a3f19bee5bf43509ada7ce",
      "scenario/blender/runtime.py": "9468693ddd2941575470018633b425885401ae68551c89fc88773ef0fce20933",
      "scenario/core/jobs/organization.py": "69ad48086ff2b763c565a22bce2bf60e142afbc10e757c56d938daf2198fbeba",
      "tests/blender/test_library_organization.py": "6da76fcae49830a07389f77dba025ce17fa5ae2750995bd52c94d90927579d7d",
      "tests/unit/test_library_organization.py": "5795cb464357418efa275114ecf0846a55b9dd102e9d2cd3cf4d1fa97dc90f16",
      "tests/blender/run_all.py": "b3019328085a8334dd3347248a9b145d3a23533ffbafcfac9304962df189a6c8",
      "scenario/blender/job_session.py": "e33a7ff821ae27d3c354a017c8b85315b0ac81ccc972d9e402892fbfdbfb4702"
    }
  }
}
---

# Native Library organization projection

Evidence for [the canonical guide](../../architecture/runtime.md#native-library-organization).
