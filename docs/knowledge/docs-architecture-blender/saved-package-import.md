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
    "limits": "Reviewed the Saved models boundary against model_application: GLB and package snapshots are staged on the main thread in a disposable scene and published at the approved cursor, selection is preserved, only package textures are packed and the timeline is unchanged. The full installed suite passed 1,253 tests with 2 Windows-only skips on macOS arm64 Blender 5.1.2 only (exact ZIP SHA-256 06f5e16d233224123993950150a7609945d4eaaeed5aa9581ff460ef7958aec3).",
    "sources": {
      "scenario/blender/model_application.py": "77c373fe556c7dd66dd47c70b8602254c56c66f9e678e4e489d61c6a6dabef17",
      "tests/blender/test_model_packages.py": "75f5753a8b5efcfdddabfe0197848ef155eb863543ddf60aea041f5243f31388",
      "tests/blender/test_model_application.py": "21d0ff0623f68951f3eb2e6edda73c2d5aa35b0917c8b333e512d056648e0802"
    }
  }
}
---

# Blender saved model package boundary

Evidence for [the canonical document](../../architecture/blender.md#saved-models).
