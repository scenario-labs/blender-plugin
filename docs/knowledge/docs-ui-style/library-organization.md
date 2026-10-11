---
{
  "type": "Evidence",
  "id": "docs-ui-style.library-organization",
  "title": "Native Library collection and tag organization",
  "evidence": {
    "path": "docs/UI_STYLE.md",
    "scope": "library-organization",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-11",
    "base_revision": "72723f02a97a7226b1c697c31d8124b77ac92c86",
    "limits": "Reviewed the Library organization section and its two pointers in the Explicit Studio view and Native Library controls sections against the Library view, the pure display module, the AssetOrganization owner and the runtime pump order: explicit collection reads (50 per page, at most 200, repeated cursors rejected), Browse setting the filter only in execute, row tag and membership summaries with +N counts, the Organize dialog fields and captured labels, the dynamic collection enum resolved through OperatorProperties, inline validation before OK, prepare-only OK and cancel preparing nothing, one review card and its phases, Apply gated on the shown READY review and single use, an asset added elsewhere before Apply reading back as Verified after one refused request with an already-in-the-collection note, read-back row updates and refresh marks for rows that left the browsed collection, a verified new collection joining the loaded list even at the 200-collection read bound, disabled public, loading and applying states, retirement on credential, Project ID or file change, the card surviving Studio redraws during Apply, sanitized refusals, online access off and the shared native and MCP owner, including its 32-review bound: when open agent reviews fill it, Organize reports that cause, keeps the card and prepares or sends nothing. Installed-ZIP Blender 5.1.2 tests on macOS arm64 with a stateful synthetic worker-thread service and offline unit tests cover these paths. Blender 5.0 and 5.2 were not run locally for this topic. No physical desktop input, focus, typing, Unicode or IME composition, Escape, viewport, small-window or alternate-DPI evidence and no screenshots exist for these controls; that evidence is pending under #66 and will be collected later in an unlocked session. No live collection, tag or bulk request was made from this repository; the observed already-member 400 and one-transaction add, service name uniqueness, DELETE body survival, tag normalization and live limits remain unverified here. No release acceptance is claimed.",
    "sources": {
      "docs/UI_STYLE.md": "e4cf7be5bf794700a95af06b6dd76e5317adc3bbdde6950dfcc6b9f8784fc580",
      "scenario/blender/library_view.py": "9d64adaa197fc1d212c95b3b256d61ff67acdc9456ef1266c61c3168b2c50f17",
      "scenario/core/ui/library_organization.py": "e583e5b900b4532c25f6fc146c97d4ab3989243a0295ec915546e6b9dadd974f",
      "scenario/blender/asset_organization.py": "597a1026ad96d07f563f54ff2651591dc9c9fc4bf6a3f19bee5bf43509ada7ce",
      "scenario/blender/runtime.py": "33461ba284a3b85282784f699e249a66df2f2503a55ad2acdda8756602957cae",
      "scenario/core/jobs/organization.py": "69ad48086ff2b763c565a22bce2bf60e142afbc10e757c56d938daf2198fbeba",
      "tests/blender/test_library_organization.py": "6da76fcae49830a07389f77dba025ce17fa5ae2750995bd52c94d90927579d7d",
      "tests/unit/test_library_organization.py": "5795cb464357418efa275114ecf0846a55b9dd102e9d2cd3cf4d1fa97dc90f16",
      "tests/blender/run_all.py": "f32e42a29f8c0403f6f1524d17fc3e020cb44ee4ec0173fe657c3ff609a74bba",
      "scenario/blender/studio.py": "7a4a6b694ba4becb7a51dac11f95838a35d9f2a3dc752d85a50e1b1cd0f1f071"
    }
  }
}
---

# Native Library collection and tag organization

Evidence for [the canonical guide](../../UI_STYLE.md#library-organization).
