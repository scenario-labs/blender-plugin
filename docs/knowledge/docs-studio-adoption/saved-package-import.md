---
{
  "type": "Evidence",
  "id": "docs-studio-adoption.saved-package-import",
  "title": "Saved model package adoption",
  "description": "Studio adoption row for classified, receipt-checked saved model imports.",
  "evidence": {
    "path": "docs/STUDIO_ADOPTION.md",
    "scope": "saved-package-import",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-10",
    "base_revision": "33d00b0554151c4de04731fd1a5e5c64ed50855b",
    "limits": "Reviewed the 3D imports row: shared saved jobs classify GLB, glTF, FBX, OBJ and mesh PLY results into ordered units with one explicit, receipt-checked import per unit, and the prototype Add to scene path in apply_3d is unchanged. Live provider package shapes and desktop review remain open; Gaussian splat adoption is not advanced. On 2026-10-10 fingerprints were refreshed after import_snapshot began reading bound OBJ normal, roughness and metallic maps as Non-Color by saved texture role and adding a Normal Map node only when one is missing; the statements here were rechecked and are unchanged, as is the review date. On 2026-10-12 fingerprints were refreshed after rewrite_mtl began adding -bm 1 to a bound normal statement without one, so an imported OBJ normal map has full Strength; the statements here were rechecked and are unchanged, as is the review date.",
    "sources": {
      "scenario/blender/model_jobs.py": "a40917107e28be6b41e7c813bbb0721dd9f4ca3df1365067201687ae1b172dc5",
      "scenario/blender/model_application.py": "c7fff225f53b796c0206ef4d3ba69ca4ff077d8cfdb3bc062dfbd4051ab3e0a3",
      "scenario/blender/job_recovery.py": "dca1e9698f00e36f052144a88f6aa0a6443908b2e2597f5172964042f5471320",
      "scenario/blender/apply_3d.py": "563c404b3c5704eb35ae0f10fee8359f95d2e18011fa9b120e23037ad2eadfd7",
      "tests/blender/test_model_packages.py": "8ebac60fc363667ba061930806f658149c8d1649750ccd2e0b2670ec1fa963e0"
    }
  }
}
---

# Saved model package adoption

Evidence for [the canonical document](../../STUDIO_ADOPTION.md#capability-decisions).
