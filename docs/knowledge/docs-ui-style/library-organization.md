---
{
  "type": "Evidence",
  "id": "docs-ui-style.library-organization",
  "title": "Native Library collection and tag organization",
  "evidence": {
    "path": "docs/UI_STYLE.md",
    "scope": "library-organization",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-10",
    "base_revision": "33d00b0554151c4de04731fd1a5e5c64ed50855b",
    "limits": "Reviewed the Library organization section and its two pointers in the Explicit Studio view and Native Library controls sections against the Library view, the pure display module, the AssetOrganization owner and the runtime pump order: explicit collection reads (50 per page, at most 200, repeated cursors rejected), Browse setting the filter only in execute, row tag and membership summaries with +N counts, the Organize dialog fields and captured labels, the dynamic collection enum resolved through OperatorProperties, inline validation before OK, prepare-only OK and cancel preparing nothing, one review card and its phases, Apply gated on the shown READY review and single use, an asset added elsewhere before Apply reading back as Verified after one refused request with an already-in-the-collection note, read-back row updates and refresh marks for rows that left the browsed collection, a verified new collection joining the loaded list even at the 200-collection read bound, disabled public, loading and applying states, retirement on credential, Project ID or file change, the card surviving Studio redraws during Apply, sanitized refusals, online access off and the shared native and MCP owner, including its 32-review bound: when open agent reviews fill it, Organize reports that cause, keeps the card and prepares or sends nothing. Installed-ZIP Blender 5.1.2 tests on macOS arm64 with a stateful synthetic worker-thread service and offline unit tests cover these paths. Blender 5.0 and 5.2 were not run locally for this topic. No physical desktop input, focus, typing, Unicode or IME composition, Escape, viewport, small-window or alternate-DPI evidence and no screenshots exist for these controls; that evidence is pending under #66 and will be collected later in an unlocked session. No live collection, tag or bulk request was made from this repository; the observed already-member 400 and one-transaction add, service name uniqueness, DELETE body survival, tag normalization and live limits remain unverified here. No release acceptance is claimed.",
    "sources": {
      "docs/UI_STYLE.md": "0004cc8716031d52db3457e6ece7c3c498c21410feb2bf1a081dbf24193b01c8",
      "scenario/blender/library_view.py": "9d64adaa197fc1d212c95b3b256d61ff67acdc9456ef1266c61c3168b2c50f17",
      "scenario/core/ui/library_organization.py": "e583e5b900b4532c25f6fc146c97d4ab3989243a0295ec915546e6b9dadd974f",
      "scenario/blender/asset_organization.py": "597a1026ad96d07f563f54ff2651591dc9c9fc4bf6a3f19bee5bf43509ada7ce",
      "scenario/blender/runtime.py": "9468693ddd2941575470018633b425885401ae68551c89fc88773ef0fce20933",
      "scenario/core/jobs/organization.py": "69ad48086ff2b763c565a22bce2bf60e142afbc10e757c56d938daf2198fbeba",
      "tests/blender/test_library_organization.py": "6da76fcae49830a07389f77dba025ce17fa5ae2750995bd52c94d90927579d7d",
      "tests/unit/test_library_organization.py": "5795cb464357418efa275114ecf0846a55b9dd102e9d2cd3cf4d1fa97dc90f16",
      "tests/blender/run_all.py": "b3019328085a8334dd3347248a9b145d3a23533ffbafcfac9304962df189a6c8",
      "scenario/blender/studio.py": "d4ba0b268cdcc1a6d9477cb5f190ebb18233010de5b5963fecf941ba05995fb8"
    }
  }
}
---

# Native Library collection and tag organization

Evidence for [the canonical guide](../../UI_STYLE.md#library-organization).
