---
{
  "type": "Evidence",
  "id": "docs-ui-style.saved-package-import",
  "title": "Saved model package review",
  "description": "Per-unit import labels and the format-aware model review dialog.",
  "evidence": {
    "path": "docs/UI_STYLE.md",
    "scope": "saved-package-import",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-10",
    "base_revision": "33d00b0554151c4de04731fd1a5e5c64ed50855b",
    "limits": "Inspected saved_job_actions._import_units (one control per projected importable unit, Import <format> model for the primary and Import alternate: <format> otherwise, numbered by saved-asset index, unknown formats and keys skipped) and job_recovery.SCENARIO_OT_import_saved_model with unit_summary (Selected line with primary or alternate, cursor, per-format MODEL_REVIEW lines of at most 66 characters, read-only draw, cancel discards). Unit tests check labels; installed tests check the labels drawn for a GLB alias and OBJ package job, the review lines, read-only drawing and cancel. The full installed suite passed 1,253 tests with 2 Windows-only skips on macOS arm64 Blender 5.1.2 only (exact ZIP SHA-256 06f5e16d233224123993950150a7609945d4eaaeed5aa9581ff460ef7958aec3). The 66-character bound comes from the earlier 480 px capture; no physical desktop interaction, screenshot, DPI or small-window fit of the new dialog is claimed.",
    "sources": {
      "scenario/core/ui/saved_job_actions.py": "d88da9348592b0de6d7d800ad22c276075e7ef7ec24b4ead2775cb711d8fe41b",
      "scenario/blender/job_recovery.py": "dca1e9698f00e36f052144a88f6aa0a6443908b2e2597f5172964042f5471320",
      "scenario/blender/model_jobs.py": "a40917107e28be6b41e7c813bbb0721dd9f4ca3df1365067201687ae1b172dc5",
      "tests/unit/test_saved_job_actions.py": "cb947e78c0c296ad94315a4263155aa8bc52981715b0e78f500b8b4eb774d7a6",
      "tests/blender/test_result_actions.py": "f32d2f046510bd6ad0a5e1bbd5b82253e021e6dd2f84ce25be66e6b8f2615394",
      "tests/blender/test_model_generation.py": "2c5f2efe6eb50b2adada205aa04fd0ac8770f78ca1a9dab737192cad6c508ab3"
    }
  }
}
---

# Saved model package review

Evidence for [the canonical document](../../UI_STYLE.md#saved-model-package-review).
