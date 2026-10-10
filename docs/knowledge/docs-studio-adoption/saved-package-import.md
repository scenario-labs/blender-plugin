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
    "limits": "Reviewed the 3D imports row: shared saved jobs classify GLB, glTF, FBX, OBJ and mesh PLY results into ordered units with one explicit, receipt-checked import per unit, and the prototype Add to scene path in apply_3d is unchanged. Live provider package shapes and desktop review remain open; Gaussian splat adoption is not advanced.",
    "sources": {
      "scenario/blender/model_jobs.py": "a40917107e28be6b41e7c813bbb0721dd9f4ca3df1365067201687ae1b172dc5",
      "scenario/blender/model_application.py": "77c373fe556c7dd66dd47c70b8602254c56c66f9e678e4e489d61c6a6dabef17",
      "scenario/blender/job_recovery.py": "dca1e9698f00e36f052144a88f6aa0a6443908b2e2597f5172964042f5471320",
      "scenario/blender/apply_3d.py": "563c404b3c5704eb35ae0f10fee8359f95d2e18011fa9b120e23037ad2eadfd7",
      "tests/blender/test_model_packages.py": "75f5753a8b5efcfdddabfe0197848ef155eb863543ddf60aea041f5243f31388"
    }
  }
}
---

# Saved model package adoption

Evidence for [the canonical document](../../STUDIO_ADOPTION.md#capability-decisions).
