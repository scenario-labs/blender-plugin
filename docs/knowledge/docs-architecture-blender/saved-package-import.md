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
    "limits": "Reviewed the Saved models boundary against model_application: GLB and package snapshots are staged on the main thread in a disposable scene and published at the approved cursor, selection is preserved, only package textures are packed and the timeline is unchanged. The full installed suite passed 1,253 tests with 2 Windows-only skips on macOS arm64 Blender 5.1.2 only (exact ZIP SHA-256 06f5e16d233224123993950150a7609945d4eaaeed5aa9581ff460ef7958aec3). On 2026-10-10 fingerprints were refreshed after import_snapshot began reading bound OBJ normal, roughness and metallic maps as Non-Color by saved texture role and adding a Normal Map node only when one is missing; the statements here were rechecked and are unchanged, as is the review date.",
    "sources": {
      "scenario/blender/model_application.py": "c7fff225f53b796c0206ef4d3ba69ca4ff077d8cfdb3bc062dfbd4051ab3e0a3",
      "tests/blender/test_model_packages.py": "a10ef992d91fe7c2d69db6ca17968091ce9bc6a6e1852fad4c734c825c9fa6f8",
      "tests/blender/test_model_application.py": "21d0ff0623f68951f3eb2e6edda73c2d5aa35b0917c8b333e512d056648e0802"
    }
  }
}
---

# Blender saved model package boundary

Evidence for [the canonical document](../../architecture/blender.md#saved-models).
