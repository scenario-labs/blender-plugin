---
{
  "type": "Evidence",
  "id": "docs-user-guide.saved-splat-import",
  "title": "Saved Gaussian splat import",
  "description": "User steps for Import splats, point limits, saved axes and the post-import notices.",
  "evidence": {
    "path": "docs/USER_GUIDE.md",
    "scope": "saved-splat-import",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-10",
    "base_revision": "33d00b0554151c4de04731fd1a5e5c64ed50855b",
    "limits": "Reviewed the 3D guidance and the worlds sentence against the Import splats and Import PLY model labels, the Points and Saved axes dropdown items and defaults, the PLY mesh or splat routing, the unlit point-cloud material needing Material Preview or Rendered view, the Point scale and Max radius modifier inputs, the Shown as points and extension notices and the SPZ v4 refusal. The full installed suite passed 1,271 tests with 2 Windows-only skips on macOS arm64 Blender 5.0.1, 5.1.2 and 5.2.1; Linux and Windows CI runs are not claimed. No desktop screenshot of the dialog, provider world or axis evidence is claimed.",
    "sources": {
      "scenario/blender/job_recovery.py": "a01e758c030606442395f7cda47695b2eff6cbe11d82eadbb259a2cdf6296fb3",
      "scenario/core/ui/saved_job_actions.py": "059a18316cee82773f63d4dd24ab5a0184475a399d1d891a6773318b79670dfe",
      "scenario/blender/splat_application.py": "0395a8ce98a15e45d2d7dc78ad4b3f4b0e1578b1b97010b00b70670cabf7454a",
      "scenario/blender/model_jobs.py": "6d091ac315d207654aa209d3b84b5ea51b85dbf8fbf1eba02423dccc64471a4d",
      "tests/blender/test_model_generation.py": "5e9481456f39de8b2fb18913ed38c73c72180424c953ab578f267c09e0377669"
    }
  }
}
---

# Saved Gaussian splat import

Evidence for [the canonical document](../../USER_GUIDE.md#3d).
