---
{
  "type": "Evidence",
  "id": "docs-ui-style.native-library-view",
  "title": "Native scoped Library browsing and model reference confirmation",
  "evidence": {
    "path": "docs/UI_STYLE.md",
    "scope": "native-library-view",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-09",
    "base_revision": "d55f21eee597284d2482780c7c93f84115a119ff",
    "limits": "Reviewed one-page native asset browsing/search, bounded explicit continuation, shared SDK/session metadata, exact destination confirmation and persistent scoped model references. Exact packaged source passed 1,127 installed tests on each macOS arm64 Blender 5.0.1/5.1.2/5.2.1 (two Windows-only skips each); fifteen tests cover native state/command boundaries. No live service calls or spending. Native physical input, screenshots, focus, viewport and DPI acceptance remain pending. Workflow reference selection, organization writes and thumbnails remain separate. Remaining desktop acceptance is tracked under #66/#68 separately from review readiness. This UI layer does not establish complete issue or release acceptance. Review follow-up verifies safe dialog redraw after scene removal and continued rejection of attachment to that removed scene. The rebased candidate passes 3,872 unit tests with the known SDK expected failure. The test synchronization helper documents why task failures are checked after polling. The Studio/Library regression section separately records scoped native input on earlier ZIP 024b7654346463d89cb80e149c278254d9ac9de022447b90b1101f6d9c915351. This review preserves the merged evidence above and verifies temporary popup refresh and RNA-backed Library input choices. Earlier artifact-specific results do not establish new-head physical input, broad DPI, IME or live service acceptance. Scoped 2026-10-10 check of the Render Video first-frame handoff, not a full re-review: reference_form adds the _RESULT provenance marker to the form snapshot and drops it when a saved upload replaces a slot; Library attachment, scope checks and upload delivery are unchanged. The claims above still hold; the review date and base revision are unchanged.",
    "sources": {
      "docs/UI_STYLE.md": "aa3596d18ee4af19ef5858899eea134ebf953d41b09fbcc06070037ca62c8503",
      "scenario/blender/library_view.py": "4ce0e8ca5a402136d7b5e2dbbe5b0f24f2b5480ed81afb3782c38252b3a65039",
      "scenario/blender/job_session.py": "3e25f86663d7024d22813e854aa26db84f64dc9a90f4b681c86961167f8a43d8",
      "scenario/blender/reference_form.py": "da7dd52526ea89c4871d791963fb84ba3432200f34b85c0e856abd5f8d100889",
      "scenario/blender/runtime.py": "a999a4790a44bd1174fda0b4ba88d25db17d877400de30cf0b87f32096cd92aa",
      "scenario/blender/registry.py": "5d5ee900afeb2663f540fb08bbedacde60400a9c572387f26dd697404d6a504d",
      "scenario/blender/studio.py": "ccdc50f2047cbab1792b1dd2a52a2b9e0c36ba9a85c315a7794d344e06b3e544",
      "scenario/core/api/library.py": "4b2b71807f983f6ea9d2cde1d54f969de7f99d1f3fbd5a5cf29459704861d4ca",
      "scenario/mcp/tools_scenario.py": "5fa8768f9b8356fb9b5071cf7c889305b06e55905a72d4caf62114f9202b0f4d",
      "tests/blender/test_library_view.py": "a9e34b45135904e6c1b4d1cc5ed774e2ee47383cd8f9b8f2b0e1e5bfac505f3d",
      "tests/blender/test_asset_library.py": "0ca458607e9dc8bd11a7209ff300bd62dd209191a85278e5975a3bdc44cd33b8",
      "tests/blender/test_studio_view.py": "e33f0e44cbe75cabdfa38ecd68ca991e010a4e0322803813f3464b2c9e9f7e78",
      "tests/blender/run_all.py": "cf87559414f0f7613cf95b2c06c7ab4944400cdc6fd6d30045a2d8231a7c990b"
    }
  }
}
---

Evidence for [the canonical guide](../../UI_STYLE.md).
