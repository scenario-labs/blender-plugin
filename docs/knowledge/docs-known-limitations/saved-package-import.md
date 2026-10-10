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
    "limits": "Reviewed the limitation against classification without persisted lineage (several OBJ or glTF files, MTLs or maps for one slot stay unbound and reported), the image guard that runs after Blender's FBX importer, FBX clip timing, the binary-only FBX signature, unsupported ksplat, sog, STL and USD types and synchronous main-thread snapshots. The full installed suite passed 1,253 tests with 2 Windows-only skips on macOS arm64 Blender 5.1.2 only (exact ZIP SHA-256 06f5e16d233224123993950150a7609945d4eaaeed5aa9581ff460ef7958aec3). Provider package shapes and glTF JSON delivery have no live evidence.",
    "sources": {
      "scenario/blender/model_application.py": "77c373fe556c7dd66dd47c70b8602254c56c66f9e678e4e489d61c6a6dabef17",
      "scenario/core/scene/model_formats.py": "5cccc357bab6dea268ba2940cf3a8bd2b1688322f5fa7a8c09229f06b3d05aaf",
      "scenario/core/scene/model_references.py": "e045878d3d7913843b32c784d7e3fd97f54f774f4e6066d0c36ee7564eca1e14",
      "tests/blender/test_model_packages.py": "75f5753a8b5efcfdddabfe0197848ef155eb863543ddf60aea041f5243f31388",
      "tests/unit/test_model_formats.py": "85bb70275db0d6471e4b7fd25bb5a3e0f33e44e9f6f8a1b755a7409a7e2a95fb"
    }
  }
}
---

# Saved model package import limits

Evidence for [the canonical document](../../KNOWN_LIMITATIONS.md#creation-and-scene-application).
