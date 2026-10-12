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
    "limits": "Inspected saved_job_actions._import_units (one control per projected importable unit, Import <format> model for the primary and Import alternate: <format> otherwise, numbered by saved-asset index, unknown formats and keys skipped) and job_recovery.SCENARIO_OT_import_saved_model with unit_summary (Selected line with primary or alternate, cursor, per-format MODEL_REVIEW lines of at most 66 characters, read-only draw, cancel discards). Unit tests check labels; installed tests check the labels drawn for a GLB alias and OBJ package job, the review lines, read-only drawing and cancel. The full installed suite passed 1,253 tests with 2 Windows-only skips on macOS arm64 Blender 5.1.2 only (exact ZIP SHA-256 06f5e16d233224123993950150a7609945d4eaaeed5aa9581ff460ef7958aec3). The 66-character bound comes from the earlier 480 px capture; no physical desktop interaction, screenshot, DPI or small-window fit of the new dialog is claimed. On 2026-10-12 this branch was rebuilt on main 72c5340c without the unmerged remote progress branch it had been stacked on. The replay conflicted only in imports, ModelJobs fields, the view projection, status and the job_status description, where main's cancellation, World candidate and workflow cost code was kept beside this import. These statements were rechecked against the rebuilt sources and are unchanged; the unit suite passed and the fingerprints were refreshed. The installed results named here are from the earlier head. On 2026-10-10 fingerprints were refreshed after saved splat import. Statements here about splat refusal, splats not being offered or splat import remaining open describe the package review only and are superseded: SPZ, .splat and PLY units are now prepared on a worker and offered, a PLY without splat data continues through this package snapshot, and the summary gains a splat field, as covered by the saved-splat-import topic of this document. The package snapshot, image guard, claim and rollback claims were rechecked and are unchanged; the review date is unchanged. On 2026-10-12 the branch was rebuilt again, on main 4bd0061d, which now holds #369 (remote progress), #402 (saved model import undo), #377 and #379 (the saved image first-frame handoff and its native control), #401 (composer session end), #373 (asset organization reviews), #378 (MCP organization tools) and #380 (Library organization); the earlier notes' main without #369 no longer applies. The replay kept #369's remote projection, status fields, job_status paragraph and test helpers, and the handoff's use_first_frame action, native first-frame descriptor and operator, first_frame status field and video_first_frame purpose, beside this import, and moved #402's two desktop Undo checkpoints from apply_model into import_snapshot, which every saved model format uses; apply_model, now called only by Film shots, records none. The label and review dialog statements here were rechecked against #369's Jobs rows, which draw these controls unchanged, and are unchanged. The unit suite and the full installed suite on macOS arm64 Blender 5.1.2 passed against the rebuilt code; the fingerprints were refreshed and the review date is unchanged.",
    "sources": {
      "scenario/core/ui/saved_job_actions.py": "4315254386cf9c91788694ce8a3a4dd0435ab8325e6727727d21b1efe726120a",
      "scenario/blender/job_recovery.py": "ff6c45e43a0dc79666a98ee6c0bdf421cc0e6d4a173c2e5d81d3c448c2796346",
      "scenario/blender/model_jobs.py": "f9bb80a01c12136fd1d463c3cf825c2b049c373aa4ed0f8e4a1022cee8f24838",
      "tests/unit/test_saved_job_actions.py": "b32432e2c1acbb3ca99fb7fb21bf6ac37785d4ed284a236c611ebda273e424be",
      "tests/blender/test_result_actions.py": "db78c091c4cbf3f70e2a3efd216340f816c2219740b9f7186b31bbdd8f3cfe8b",
      "tests/blender/test_model_generation.py": "5e9481456f39de8b2fb18913ed38c73c72180424c953ab578f267c09e0377669"
    }
  }
}
---

# Saved model package review

Evidence for [the canonical document](../../UI_STYLE.md#saved-model-package-review).
