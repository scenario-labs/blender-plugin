---
{
  "type": "Evidence",
  "id": "docs-architecture-blender.saved-package-import",
  "title": "Blender saved model package boundary",
  "description": "Main-thread staging and publication boundary for saved model packages.",
  "evidence": {
    "path": "docs/architecture/blender.md",
    "scope": "saved-package-import",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-10",
    "base_revision": "33d00b0554151c4de04731fd1a5e5c64ed50855b",
    "limits": "Reviewed the Saved models boundary against model_application: GLB and package snapshots are staged on the main thread in a disposable scene and published at the approved cursor, selection is preserved, only package textures are packed and the timeline is unchanged. The full installed suite passed 1,253 tests with 2 Windows-only skips on macOS arm64 Blender 5.1.2 only (exact ZIP SHA-256 06f5e16d233224123993950150a7609945d4eaaeed5aa9581ff460ef7958aec3). On 2026-10-10 fingerprints were refreshed after import_snapshot began reading bound OBJ normal, roughness and metallic maps as Non-Color by saved texture role and adding a Normal Map node only when one is missing; the statements here were rechecked and are unchanged, as is the review date. On 2026-10-12 fingerprints were refreshed after rewrite_mtl began adding -bm 1 to a bound normal statement without one, so an imported OBJ normal map has full Strength; the statements here were rechecked and are unchanged, as is the review date. On 2026-10-12 the branch was rebuilt again, on main 4bd0061d, which now holds #369 (remote progress), #402 (saved model import undo), #377 and #379 (the saved image first-frame handoff and its native control), #401 (composer session end), #373 (asset organization reviews), #378 (MCP organization tools) and #380 (Library organization). The replay kept #369's remote projection, status fields, job_status paragraph and test helpers, and the handoff's use_first_frame action, native first-frame descriptor and operator, first_frame status field and video_first_frame purpose, beside this import, and moved #402's two desktop Undo checkpoints from apply_model into import_snapshot, which every saved model format uses; apply_model, now called only by Film shots, records none. The staging, cursor, preserved selection, package texture packing and unchanged timeline statements here were rechecked against #402's change and are unchanged; import_snapshot now also records those checkpoints when the saved-result command asks for history. The unit suite and the full installed suite on macOS arm64 Blender 5.1.2 passed against the rebuilt code; the fingerprints were refreshed and the review date is unchanged.",
    "sources": {
      "scenario/blender/model_application.py": "d956046473b0cc174ea79daa95c07c22f730f192612c6d8cadc4e9229e50a816",
      "tests/blender/test_model_packages.py": "8ebac60fc363667ba061930806f658149c8d1649750ccd2e0b2670ec1fa963e0",
      "tests/blender/test_model_application.py": "21d0ff0623f68951f3eb2e6edda73c2d5aa35b0917c8b333e512d056648e0802"
    }
  }
}
---

# Blender saved model package boundary

Evidence for [the canonical document](../../architecture/blender.md#saved-models).
