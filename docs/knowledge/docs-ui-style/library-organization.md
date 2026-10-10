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
    "limits": "Reviewed the Library organization section and its two pointers in the Explicit Studio view and Native Library controls sections against the Library view, the pure display module, the AssetOrganization owner and the runtime pump order: explicit collection reads (50 per page, at most 200, repeated cursors rejected), Browse setting the filter only in execute, row tag and membership summaries with +N counts, the Organize dialog fields and captured labels, the dynamic collection enum resolved through OperatorProperties, inline validation before OK, prepare-only OK and cancel preparing nothing, one review card and its phases, Apply gated on the shown READY review and single use, read-back row updates and refresh marks for rows that left the browsed collection, a verified new collection joining the loaded list, disabled public, loading and applying states, retirement on credential, Project ID or file change, the card surviving Studio redraws during Apply, sanitized refusals, online access off and the shared native and MCP owner. Installed-ZIP Blender 5.1.2 tests on macOS arm64 with a stateful synthetic worker-thread service and offline unit tests cover these paths. Blender 5.0 and 5.2 were not run locally for this topic. No physical desktop input, focus, typing, Unicode or IME composition, Escape, viewport, small-window or alternate-DPI evidence and no screenshots exist for these controls; that evidence is pending under #66 and will be collected later in an unlocked session. No live collection, tag or bulk request was made; service name uniqueness, re-adding a member, DELETE body survival, tag normalization and live limits remain unverified. No release acceptance is claimed.",
    "sources": {
      "docs/UI_STYLE.md": "2375b5a3066cdb65f0e6465500c639d5d772516cb81b129e5028c0a8fb1857af",
      "scenario/blender/library_view.py": "128d5f59000c37e6ddce965fbe2c1f61da7d6e55a45a33661ba8a13baf20cc14",
      "scenario/core/ui/library_organization.py": "79ce2541b2ec332797e64c56a436e917f7431b9e96e45866d2b7abb413aabd20",
      "scenario/blender/asset_organization.py": "597a1026ad96d07f563f54ff2651591dc9c9fc4bf6a3f19bee5bf43509ada7ce",
      "scenario/blender/runtime.py": "9468693ddd2941575470018633b425885401ae68551c89fc88773ef0fce20933",
      "scenario/core/jobs/organization.py": "7f69ce28e4c54e3c2b819cc76735d001671de6bcfcb12145b2cd90b059e8b84d",
      "tests/blender/test_library_organization.py": "54dc4032b89c4849760280aced9e784855552fb8296f61e6c0a6128bdc4c1653",
      "tests/unit/test_library_organization.py": "5795cb464357418efa275114ecf0846a55b9dd102e9d2cd3cf4d1fa97dc90f16",
      "tests/blender/run_all.py": "b3019328085a8334dd3347248a9b145d3a23533ffbafcfac9304962df189a6c8",
      "scenario/blender/studio.py": "d4ba0b268cdcc1a6d9477cb5f190ebb18233010de5b5963fecf941ba05995fb8"
    }
  }
}
---

# Native Library collection and tag organization

Evidence for [the canonical guide](../../UI_STYLE.md#library-organization).
