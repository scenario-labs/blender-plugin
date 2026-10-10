---
{
  "type": "Evidence",
  "id": "docs-user-guide.saved-package-import",
  "title": "Saved model package import guidance",
  "description": "User guidance for importing saved GLB, glTF, FBX, OBJ and mesh PLY results.",
  "evidence": {
    "path": "docs/USER_GUIDE.md",
    "scope": "saved-package-import",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-10",
    "base_revision": "33d00b0554151c4de04731fd1a5e5c64ed50855b",
    "limits": "Reviewed the 3D guidance against the per-unit labels, the review summary, the supported formats, OBJ map binding, glTF resource binding, embedded FBX textures, external texture rejection and FBX clip timing, splat refusal, the Nothing was imported pause and the 256 MiB per file and 512 MiB per package limits, and the generic-import wording for experimental models. The full installed suite passed 1,253 tests with 2 Windows-only skips on macOS arm64 Blender 5.1.2 only (exact ZIP SHA-256 06f5e16d233224123993950150a7609945d4eaaeed5aa9581ff460ef7958aec3). No desktop screenshot of the new controls, live provider package or splat import is claimed.",
    "sources": {
      "scenario/blender/job_recovery.py": "dca1e9698f00e36f052144a88f6aa0a6443908b2e2597f5172964042f5471320",
      "scenario/core/ui/saved_job_actions.py": "d88da9348592b0de6d7d800ad22c276075e7ef7ec24b4ead2775cb711d8fe41b",
      "scenario/blender/model_application.py": "77c373fe556c7dd66dd47c70b8602254c56c66f9e678e4e489d61c6a6dabef17",
      "scenario/blender/model_jobs.py": "a40917107e28be6b41e7c813bbb0721dd9f4ca3df1365067201687ae1b172dc5",
      "scenario/core/scene/model_formats.py": "5cccc357bab6dea268ba2940cf3a8bd2b1688322f5fa7a8c09229f06b3d05aaf",
      "scenario/core/ui/capability_status.py": "5e18990d7117e420c6046cd01d992fa9dfe7f3dbb09702860ff5a45fc973dcd1",
      "tests/blender/test_model_packages.py": "75f5753a8b5efcfdddabfe0197848ef155eb863543ddf60aea041f5243f31388",
      "tests/blender/test_model_generation.py": "2c5f2efe6eb50b2adada205aa04fd0ac8770f78ca1a9dab737192cad6c508ab3"
    }
  }
}
---

# Saved model package import guidance

Evidence for [the canonical document](../../USER_GUIDE.md#3d).
