---
{
  "type": "Evidence",
  "id": "docs-known-limitations.saved-package-import",
  "title": "Saved model package import limits",
  "description": "Conservative package binding, FBX texture and timing limits and unsupported model types.",
  "evidence": {
    "path": "docs/KNOWN_LIMITATIONS.md",
    "scope": "saved-package-import",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-10",
    "base_revision": "33d00b0554151c4de04731fd1a5e5c64ed50855b",
    "limits": "Reviewed the limitation against classification without persisted lineage (several OBJ or glTF files, MTLs or maps for one slot stay unbound and reported), the image guard that runs after Blender's FBX importer, FBX clip timing, the binary-only FBX signature, unsupported ksplat, sog, STL and USD types and synchronous main-thread snapshots. The full installed suite passed 1,253 tests with 2 Windows-only skips on macOS arm64 Blender 5.1.2 only (exact ZIP SHA-256 06f5e16d233224123993950150a7609945d4eaaeed5aa9581ff460ef7958aec3). Provider package shapes and glTF JSON delivery have no live evidence. On 2026-10-10 fingerprints were refreshed after import_snapshot began reading bound OBJ normal, roughness and metallic maps as Non-Color by saved texture role and adding a Normal Map node only when one is missing; the statements here were rechecked and are unchanged, as is the review date. On 2026-10-12 fingerprints were refreshed after rewrite_mtl began adding -bm 1 to a bound normal statement without one, so an imported OBJ normal map has full Strength; the statements here were rechecked and are unchanged, as is the review date. On 2026-10-12 this branch was rebuilt on main 72c5340c without the unmerged remote progress branch it had been stacked on. The replay conflicted only in imports, ModelJobs fields, the view projection, status and the job_status description, where main's cancellation, World candidate and workflow cost code was kept beside this import. These statements were rechecked against the rebuilt sources and are unchanged; the unit suite passed and the fingerprints were refreshed. The installed results named here are from the earlier head. On 2026-10-12 the branch was rebuilt again, on main 4bd0061d, which now holds #369 (remote progress), #402 (saved model import undo), #377 and #379 (the saved image first-frame handoff and its native control), #401 (composer session end), #373 (asset organization reviews), #378 (MCP organization tools) and #380 (Library organization); the earlier notes' main without #369 no longer applies. The replay kept #369's remote projection, status fields, job_status paragraph and test helpers, and the handoff's use_first_frame action, native first-frame descriptor and operator, first_frame status field and video_first_frame purpose, beside this import, and moved #402's two desktop Undo checkpoints from apply_model into import_snapshot, which every saved model format uses; apply_model, now called only by Film shots, records none. The limitation statements were rechecked against the rebuilt model_application.py and are unchanged. The unit suite and the full installed suite on macOS arm64 Blender 5.1.2 passed against the rebuilt code; the fingerprints were refreshed and the review date is unchanged.",
    "sources": {
      "scenario/blender/model_application.py": "d956046473b0cc174ea79daa95c07c22f730f192612c6d8cadc4e9229e50a816",
      "scenario/core/scene/model_formats.py": "900ae616efe5c6c194712784a9014a67e86fc6c2330766d46c8d27781ca78d08",
      "scenario/core/scene/model_references.py": "0431633b34f6f77b52b971dc657803f63ecafda3bd7cbd6c14e8ddbd572913da",
      "tests/blender/test_model_packages.py": "8ebac60fc363667ba061930806f658149c8d1649750ccd2e0b2670ec1fa963e0",
      "tests/unit/test_model_formats.py": "00bfa89a675ed2a301e13e5bfc587b6ed81ce953ef00ebe842253e5db8b5cfa5"
    }
  }
}
---

# Saved model package import limits

Evidence for [the canonical document](../../KNOWN_LIMITATIONS.md#creation-and-scene-application).
