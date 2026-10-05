---
{
  "type": "Evidence",
  "id": "docs-mcp.film-shot-controls",
  "title": "Shared native and MCP Film shot controls",
  "evidence": {
    "path": "docs/MCP.md",
    "scope": "film-shot-controls",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-05",
    "base_revision": "e4da254583900a68da7414e0ac2744656831e47f",
    "limits": "Native/MCP saved Film hero selection, local verification, separate build approval and receipt/dismissal controls over the existing scoped session. Synthetic installed tests cover cross-entry-point handles, cancellation without claims, stale context, persistent selection, read-only drawing and recovery without rebuilding. Exact ZIP passes 855 native tests each on macOS arm64 Blender 5.0.1, 5.1.2 and 5.2.1. Desktop interaction on 5.1.2 verifies source/build cancellation, review discard, explicit two-hero build with the working scene preserved, native Undo/Redo with durable receipts unchanged, viewport selection/keyboard focus and scene switching. Zero service requests/downloads; clean isolated-profile teardown and normal profile unchanged. No SDK operation, paid generation, live provider or motion/audio acceptance, other OS/DPI proof, timeline approval, capture, finishing/export or release authorization. Other evidence topics retain their scope.",
    "sources": {
      "scenario/blender/film_scene_controls.py": "0692d269579019eedc9937b19c4fe3b7faa429123ce9945f170bdf0755c10cfb",
      "scenario/blender/film.py": "eb2d6e038d4f558b74def74f8ebcf3f522be92fd5ba228b772b7ea6d2b078280",
      "scenario/blender/film_application.py": "785d21fd8e4b9cd584de9c98c7351d8f6204730887ed556d1c96436cca5730dc",
      "scenario/blender/film_jobs.py": "33f48400e01bfaa0a75a690b510fa3c78ca785522d68aa449a8bca65b1e73504",
      "scenario/blender/runtime.py": "acab2019230abce044dc30d53e14700a806a64c60e23c3916c10d76ce7645e4d",
      "scenario/mcp/tools_scenario.py": "e6b2f0f6c7f250772ea2fb74f7aecb15c8176ffe995814f25290012006f03ae8",
      "tests/blender/test_film_shot_controls.py": "0b9c6e817d489fde78df6b601441ec0e95c6ff1b49d20a4a8ac85b9be4d130a6",
      "tests/blender/test_mcp_contracts.py": "8a66b26d69a14b27b85cbb48f3729597ec86165ad62e9280a615700fe5b9a897",
      "tests/unit/test_mcp_descriptions.py": "2f09bd5620a9a26b5d4963bbee8cffc95bb6c55009fdb216cc9b4157e24a5aff"
    }
  }
}
---

Source evidence for [the canonical guide](../../MCP.md).
