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
    "reviewed_at": "2026-10-12",
    "base_revision": "33d00b0554151c4de04731fd1a5e5c64ed50855b",
    "limits": "Reviewed the 3D guidance against the per-unit labels, the review summary, the supported formats, OBJ map binding, Non-Color OBJ normal, roughness and metallic maps with the normal map through a Normal Map node at full strength unless the saved MTL sets another -bm, glTF resource binding, embedded FBX textures, external texture rejection and FBX clip timing, splat refusal, the Nothing was imported pause and the 256 MiB per file and 512 MiB per package limits, and the generic-import wording for experimental models. The full installed suite passed 1,256 tests with 2 Windows-only skips on macOS arm64 Blender 5.1.2 (exact ZIP SHA-256 54cc6483f7ef1f3d94f4af5fee44dffc3144be96758604b5c5c2a1954d4ed2b1), and the installed baseline passed 778 tests on macOS arm64 Blender 5.0.1 and 5.2.1 from separate builds of the same checkout. No desktop recheck of the OBJ normal strength, desktop screenshot of the new controls, live provider package or splat import is claimed. On 2026-10-12 only the OBJ normal strength guidance and the test results were re-reviewed; the other statements keep their 2026-10-10 review.",
    "sources": {
      "scenario/blender/job_recovery.py": "dca1e9698f00e36f052144a88f6aa0a6443908b2e2597f5172964042f5471320",
      "scenario/core/ui/saved_job_actions.py": "d88da9348592b0de6d7d800ad22c276075e7ef7ec24b4ead2775cb711d8fe41b",
      "scenario/blender/model_application.py": "c7fff225f53b796c0206ef4d3ba69ca4ff077d8cfdb3bc062dfbd4051ab3e0a3",
      "scenario/blender/model_jobs.py": "a40917107e28be6b41e7c813bbb0721dd9f4ca3df1365067201687ae1b172dc5",
      "scenario/core/scene/model_formats.py": "da33dd578b40705e9ddd79bc69afe9984b07f2f3e43764ce94b02aa7a6639a15",
      "scenario/core/ui/capability_status.py": "5e18990d7117e420c6046cd01d992fa9dfe7f3dbb09702860ff5a45fc973dcd1",
      "tests/blender/test_model_packages.py": "8ebac60fc363667ba061930806f658149c8d1649750ccd2e0b2670ec1fa963e0",
      "tests/blender/test_model_generation.py": "2c5f2efe6eb50b2adada205aa04fd0ac8770f78ca1a9dab737192cad6c508ab3"
    }
  }
}
---

# Saved model package import guidance

Evidence for [the canonical document](../../USER_GUIDE.md#3d).
