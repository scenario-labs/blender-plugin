---
{
  "type": "Evidence",
  "id": "release-acceptance.native-library-view",
  "title": "Native scoped Library browsing and model reference confirmation",
  "evidence": {
    "path": "docs/maintenance/release-acceptance.md",
    "scope": "native-library-view",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-09",
    "base_revision": "cf54d3a314ed06461aadf06722401e11e752cbd3",
    "limits": "Reviewed one-page native asset browsing/search, bounded explicit continuation, shared SDK/session metadata, exact destination confirmation and persistent scoped model references. Exact packaged source passed 1,127 installed tests on each macOS arm64 Blender 5.0.1/5.1.2/5.2.1 (two Windows-only skips each); fifteen tests cover native state/command boundaries. No live service calls or spending. Native physical input, screenshots, focus, viewport and DPI acceptance remain pending. Workflow reference selection, organization writes and thumbnails remain separate. Remaining desktop acceptance is tracked under #66/#68 separately from review readiness. This UI layer does not establish complete issue or release acceptance. Review follow-up verifies safe dialog redraw after scene removal and continued rejection of attachment to that removed scene. The rebased candidate passes 3,872 unit tests with the known SDK expected failure. The test synchronization helper documents why task failures are checked after polling.",
    "sources": {
      "docs/maintenance/release-acceptance.md": "335458bf630adf84c86d21b3349d242efed6afe976aaf9159900d46e9c637c5c",
      "scenario/blender/library_view.py": "a9a572e66541358dac6aa29c065f7e9efbea73869c763cd8b82bea649a414df9",
      "scenario/blender/job_session.py": "3e25f86663d7024d22813e854aa26db84f64dc9a90f4b681c86961167f8a43d8",
      "scenario/blender/reference_form.py": "520583bf3399a0f79a880f027a5beb61de9dd0eea83c89f9d7500c17b80b4d13",
      "scenario/blender/runtime.py": "a999a4790a44bd1174fda0b4ba88d25db17d877400de30cf0b87f32096cd92aa",
      "scenario/blender/registry.py": "5d5ee900afeb2663f540fb08bbedacde60400a9c572387f26dd697404d6a504d",
      "scenario/blender/studio.py": "8a0e393c26c835e5eda14278389e7411fdb50260e2129567e5b6408eb3524d2a",
      "scenario/core/api/library.py": "4b2b71807f983f6ea9d2cde1d54f969de7f99d1f3fbd5a5cf29459704861d4ca",
      "scenario/mcp/tools_scenario.py": "5fa8768f9b8356fb9b5071cf7c889305b06e55905a72d4caf62114f9202b0f4d",
      "tests/blender/test_library_view.py": "55af5cc01912b9e11b09fa28a748bb5a1294640e95d8f80dc903f1d1102382d7",
      "tests/blender/test_asset_library.py": "0ca458607e9dc8bd11a7209ff300bd62dd209191a85278e5975a3bdc44cd33b8",
      "tests/blender/test_studio_view.py": "df340fe53b88b1489ca0795bdbeafd8508b9760deb49d44778645fca90195e9e",
      "tests/blender/run_all.py": "cf87559414f0f7613cf95b2c06c7ab4944400cdc6fd6d30045a2d8231a7c990b"
    }
  }
}
---

Evidence for [the canonical guide](../../maintenance/release-acceptance.md).
