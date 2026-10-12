---
{
  "type": "Evidence",
  "id": "docs-architecture-blender.saved-splat-import",
  "title": "Saved Gaussian splat import",
  "description": "Blender boundary for the main-thread splat point-cloud builder.",
  "evidence": {
    "path": "docs/architecture/blender.md",
    "scope": "saved-splat-import",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-10",
    "base_revision": "33d00b0554151c4de04731fd1a5e5c64ed50855b",
    "limits": "Reviewed the Saved models boundary against splat_application: main-thread only through validate_destination, no file reads or importers, new mesh, node group and material without reuse by name, publication through the model group helper and verified rollback. The full installed suite passed 1,271 tests with 2 Windows-only skips on macOS arm64 Blender 5.0.1, 5.1.2 and 5.2.1; Linux and Windows CI runs are not claimed. On 2026-10-10 fingerprints were refreshed after import_snapshot began reading bound OBJ normal, roughness and metallic maps as Non-Color by saved texture role and adding a Normal Map node only when one is missing; the statements here were rechecked and are unchanged, as is the review date.",
    "sources": {
      "scenario/blender/splat_application.py": "0395a8ce98a15e45d2d7dc78ad4b3f4b0e1578b1b97010b00b70670cabf7454a",
      "scenario/blender/model_application.py": "ede45e886635fcb3768673ba83c0ee7e5b99d59ed2f8fc9a8d537028b9832dc9",
      "tests/blender/test_splat_application.py": "3cf88d7c33560200411c2cbe9ab3282efdb73a2d18f8e518f1b1b64247997d71"
    }
  }
}
---

# Saved Gaussian splat import

Evidence for [the canonical document](../../architecture/blender.md#saved-models).
