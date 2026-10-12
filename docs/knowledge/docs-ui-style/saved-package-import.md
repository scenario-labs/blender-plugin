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
    "limits": "Inspected saved_job_actions._import_units (one control per projected importable unit, Import <format> model for the primary and Import alternate: <format> otherwise, numbered by saved-asset index, unknown formats and keys skipped) and job_recovery.SCENARIO_OT_import_saved_model with unit_summary (Selected line with primary or alternate, cursor, per-format MODEL_REVIEW lines of at most 66 characters, read-only draw, cancel discards). Unit tests check labels; installed tests check the labels drawn for a GLB alias and OBJ package job, the review lines, read-only drawing and cancel. The full installed suite passed 1,253 tests with 2 Windows-only skips on macOS arm64 Blender 5.1.2 only (exact ZIP SHA-256 06f5e16d233224123993950150a7609945d4eaaeed5aa9581ff460ef7958aec3). The 66-character bound comes from the earlier 480 px capture; no physical desktop interaction, screenshot, DPI or small-window fit of the new dialog is claimed. On 2026-10-10 fingerprints were refreshed after saved splat import. The statements that a splat unit gets no control and that PLY imports meshes only describe the package review and are superseded: SPZ and .splat units now draw Import splats: <format> (N) for the primary unit and Import alternate splats: <format> (N) otherwise, a PLY keeps its Import PLY model label and its review line says a file without splat data imports as a mesh, and the review dialog adds the Points and Saved axes choices and splat lines for SPZ, .splat and PLY units, as covered by the saved-splat-import topic of this document. The mesh label and review dialog statements here were rechecked and are unchanged; the review date is unchanged. On 2026-10-12 this branch was rebuilt on main 72c5340c without the unmerged remote progress branch it had been stacked on. The replay conflicted only in imports, ModelJobs fields, the view projection, status and the job_status description, where main's cancellation, World candidate and workflow cost code was kept beside this import. These statements were rechecked against the rebuilt sources and are unchanged; the unit suite passed and the fingerprints were refreshed. The installed results named here are from the earlier head. On 2026-10-12 the branch was rebuilt again, on main 4bd0061d, which now holds #369 (remote progress), #402 (saved model import undo), #377 and #379 (the saved image first-frame handoff and its native control), #401 (composer session end), #373 (asset organization reviews), #378 (MCP organization tools) and #380 (Library organization); the earlier notes' main without #369 no longer applies. The replay kept #369's remote projection, status fields, job_status paragraph and test helpers, and the handoff's use_first_frame action, native first-frame descriptor and operator, first_frame status field and video_first_frame purpose, beside this import, and moved #402's two desktop Undo checkpoints from apply_model into import_snapshot, which every saved model format uses; apply_model, now called only by Film shots, records none. The label and review dialog statements here were rechecked against #369's Jobs rows, which draw these controls unchanged, and are unchanged. The unit suite and the full installed suite on macOS arm64 Blender 5.1.2 passed against the rebuilt code; the fingerprints were refreshed and the review date is unchanged. On 2026-10-12 the fingerprints were refreshed again after the splat import branch was rebuilt on this rebuild. It adds splat options, worker preparation and the point builder beside this import; import_splat records the same Undo checkpoints as import_snapshot. The statements here were rechecked and are unchanged. On 2026-10-12 review fixes made a PLY verify on the ordinary queue while the local-operation slot is busy, importing only as a mesh, and made the native model import dialog report a ScenarioError reason. This topic's statements were rechecked against that change and are unchanged; the changed fingerprints were refreshed and the review date is unchanged.",
    "sources": {
      "scenario/core/ui/saved_job_actions.py": "d25a4144d0357e0025606e6d3befb7dde6558df45f7c85b8f1db9383d83ba086",
      "scenario/blender/job_recovery.py": "b6e28f0b4c8b1ff282ffc5e2d1a574bde07867a7e94176e667b05ad5232a342e",
      "scenario/blender/model_jobs.py": "9e8739c8255bb778c4b45fb07e69cda41fcdc536308542c3f1a84d45156f3f22",
      "tests/unit/test_saved_job_actions.py": "a93fffad40b95de2714cd98b4370edf41059a2e995c4e748d27cc9bf45807903",
      "tests/blender/test_result_actions.py": "db78c091c4cbf3f70e2a3efd216340f816c2219740b9f7186b31bbdd8f3cfe8b",
      "tests/blender/test_model_generation.py": "f884c59fcd384e04b7025218f542cb64726385d660acc2e1880b3f7af58e239e"
    }
  }
}
---

# Saved model package review

Evidence for [the canonical document](../../UI_STYLE.md#saved-model-package-review).
