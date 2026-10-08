---
{
  "type": "Evidence",
  "id": "docs-architecture-runtime.native-library-view",
  "title": "Native scoped Library browsing and model reference confirmation",
  "evidence": {
    "path": "docs/architecture/runtime.md",
    "scope": "native-library-view",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-08",
    "base_revision": "d18a95212410a8babc37145b4ff2007e5e2cc011",
    "limits": "Reviewed one-page native asset browsing/search, bounded explicit continuation, shared SDK/session metadata, exact destination confirmation and persistent scoped model references. Exact packaged source passed 1,115 installed tests on each macOS arm64 Blender 5.0.1/5.1.2/5.2.1 (two Windows-only skips each); fifteen tests cover native state/command boundaries. No live service calls or spending. Native physical input, screenshots, focus, viewport and DPI acceptance remain pending. Workflow reference selection, organization writes and thumbnails remain separate. This draft UI layer does not establish complete issue or release acceptance. Review follow-up verifies safe dialog redraw after scene removal and continued rejection of attachment to that removed scene.",
    "sources": {
      "docs/architecture/runtime.md": "f4ea045c1edbd9a447e092d44edb78224bc6b2f1e4c3a99ac45fcc2b582a9c85",
      "scenario/blender/library_view.py": "a9a572e66541358dac6aa29c065f7e9efbea73869c763cd8b82bea649a414df9",
      "scenario/blender/job_session.py": "aa103df3b675099707f700eaee8de9658cf8119a17f4b1b926bf7e8a944f5652",
      "scenario/blender/reference_form.py": "520583bf3399a0f79a880f027a5beb61de9dd0eea83c89f9d7500c17b80b4d13",
      "scenario/blender/runtime.py": "c082e67decc2bff5af8c3641c4c5fa21aaf0e0a2e503496736eab9f0ba0e7bc2",
      "scenario/blender/registry.py": "5d5ee900afeb2663f540fb08bbedacde60400a9c572387f26dd697404d6a504d",
      "scenario/blender/studio.py": "d873e1b5a33ddc6db8f2ddd83b65c1f222d0073b43b90f5e54979042a6fee0c7",
      "scenario/core/api/library.py": "4b2b71807f983f6ea9d2cde1d54f969de7f99d1f3fbd5a5cf29459704861d4ca",
      "scenario/mcp/tools_scenario.py": "5fa8768f9b8356fb9b5071cf7c889305b06e55905a72d4caf62114f9202b0f4d",
      "tests/blender/test_library_view.py": "54900aab30e373b72b8d0d26d5094363d55edc3a1fa8a977433b355de58d8cb3",
      "tests/blender/test_asset_library.py": "0ca458607e9dc8bd11a7209ff300bd62dd209191a85278e5975a3bdc44cd33b8",
      "tests/blender/test_studio_view.py": "25b0ebccbd05e5195f5aad80e09c0cc066bfdd35170c755b7b0e77a36f1e3009",
      "tests/blender/run_all.py": "cf87559414f0f7613cf95b2c06c7ab4944400cdc6fd6d30045a2d8231a7c990b"
    }
  }
}
---

Evidence for [the canonical guide](../../architecture/runtime.md).
