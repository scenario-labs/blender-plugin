---
{
  "type": "Evidence",
  "id": "docs-ui-style.saved-splat-import",
  "title": "Saved Gaussian splat import",
  "description": "Splat import labels, review dropdowns, option revision through check() and post-import status rows.",
  "evidence": {
    "path": "docs/UI_STYLE.md",
    "scope": "saved-splat-import",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-10",
    "base_revision": "33d00b0554151c4de04731fd1a5e5c64ed50855b",
    "limits": "Inspected saved_job_actions (SPLAT_FORMATS labels Import splats and Import alternate splats, the PLY model label and import_notice status rows after the controls) and SCENARIO_OT_import_saved_model (SPLAT_POINT_ITEMS and SPLAT_AXIS_ITEMS dropdowns set from the approval in invoke, check() exchanging the approval through revise_model_application with an error line on a changed destination, execute syncing options first and cancelling on failure, SPLAT_REVIEW lines within 66 characters, read-only draw). Unit tests check labels and notices; installed tests check drawn lines, dropdowns, read-only drawing, revision under a new handle, the old handle's refusal, confirmation and cancel. The full installed suite passed 1,271 tests with 2 Windows-only skips on macOS arm64 Blender 5.0.1, 5.1.2 and 5.2.1; Linux and Windows CI runs are not claimed. No physical desktop interaction, screenshot, DPI or small-window fit, or viewport navigation after a large import is claimed.",
    "sources": {
      "scenario/core/ui/saved_job_actions.py": "059a18316cee82773f63d4dd24ab5a0184475a399d1d891a6773318b79670dfe",
      "scenario/blender/job_recovery.py": "a01e758c030606442395f7cda47695b2eff6cbe11d82eadbb259a2cdf6296fb3",
      "scenario/blender/model_jobs.py": "6d091ac315d207654aa209d3b84b5ea51b85dbf8fbf1eba02423dccc64471a4d",
      "tests/unit/test_saved_job_actions.py": "344c5cf819f80eea47fdb83c732b0fb0d9b844f9f3b2029131a1bf9226e7fcc2",
      "tests/blender/test_model_generation.py": "5e9481456f39de8b2fb18913ed38c73c72180424c953ab578f267c09e0377669"
    }
  }
}
---

# Saved Gaussian splat import

Evidence for [the canonical document](../../UI_STYLE.md#saved-splat-review).
