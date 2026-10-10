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
    "limits": "Reviewed the limitation against classification without persisted lineage (several OBJ or glTF files, MTLs or maps for one slot stay unbound and reported), the image guard that runs after Blender's FBX importer, FBX clip timing, the binary-only FBX signature, unsupported ksplat, sog, STL and USD types and synchronous main-thread snapshots. The full installed suite passed 1,253 tests with 2 Windows-only skips on macOS arm64 Blender 5.1.2 only (exact ZIP SHA-256 06f5e16d233224123993950150a7609945d4eaaeed5aa9581ff460ef7958aec3). Provider package shapes and glTF JSON delivery have no live evidence. On 2026-10-10 fingerprints were refreshed after import_snapshot began reading bound OBJ normal, roughness and metallic maps as Non-Color by saved texture role and adding a Normal Map node only when one is missing; the statements here were rechecked and are unchanged, as is the review date.",
    "sources": {
      "scenario/blender/model_application.py": "c7fff225f53b796c0206ef4d3ba69ca4ff077d8cfdb3bc062dfbd4051ab3e0a3",
      "scenario/core/scene/model_formats.py": "da33dd578b40705e9ddd79bc69afe9984b07f2f3e43764ce94b02aa7a6639a15",
      "scenario/core/scene/model_references.py": "e045878d3d7913843b32c784d7e3fd97f54f774f4e6066d0c36ee7564eca1e14",
      "tests/blender/test_model_packages.py": "a10ef992d91fe7c2d69db6ca17968091ce9bc6a6e1852fad4c734c825c9fa6f8",
      "tests/unit/test_model_formats.py": "00bfa89a675ed2a301e13e5bfc587b6ed81ce953ef00ebe842253e5db8b5cfa5"
    }
  }
}
---

# Saved model package import limits

Evidence for [the canonical document](../../KNOWN_LIMITATIONS.md#creation-and-scene-application).
