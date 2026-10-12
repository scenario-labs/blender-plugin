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
    "reviewed_at": "2026-10-12",
    "base_revision": "4bd0061d73f6d049a86adac37119cc7a2c37741c",
    "limits": "Inspected saved_job_actions (SPLAT_FORMATS labels Import splats and Import alternate splats, the PLY model label and import_notice status rows after the controls) and SCENARIO_OT_import_saved_model (SPLAT_POINT_ITEMS and SPLAT_AXIS_ITEMS dropdowns set from the approval in invoke, check() exchanging the approval through revise_model_application with an error line on a changed destination, execute syncing options first and cancelling on failure, SPLAT_REVIEW lines within 66 characters, read-only draw). Unit tests check labels and notices; installed tests check drawn lines, dropdowns, read-only drawing, revision under a new handle, the old handle's refusal, confirmation and cancel. The full installed suite passed 1,271 tests with 2 Windows-only skips on macOS arm64 Blender 5.0.1, 5.1.2 and 5.2.1; Linux and Windows CI runs are not claimed. No physical desktop interaction, screenshot, DPI or small-window fit, or viewport navigation after a large import is claimed. On 2026-10-12 this branch was rebuilt on the saved package import branch after that branch was rebuilt on main 72c5340c, which now holds #356, without the unmerged remote progress branch. The replay conflicted only in imports, the view projection, the job_status description, the generated prepare_result_application row, a transfer guide paragraph and test fixtures. These statements were rechecked against the rebuilt sources, including main's later coordinator, worker and result changes (Film export runs outside the local-operation slot; the splat preparation still uses it and registers one verification for one claim), and are unchanged; the unit suite passed and the fingerprints were refreshed. The installed results named here are from the earlier head. On 2026-10-12 the branch was rebuilt again on the package import branch, itself rebuilt on main 4bd0061d, which now holds #369 (remote progress), #402 (saved model import undo), #377 and #379 (the saved image first-frame handoff and its native control), #401 (composer session end), #373 (asset organization reviews), #378 (MCP organization tools) and #380 (Library organization); the earlier notes' main without #369 no longer applies. The replay kept #369's remote projection, job_status paragraph and test helpers, and the handoff's runtime wrapper, apply_saved_result branch, MCP purpose and native first-frame descriptor and operator, beside this import, and import_splat now records #402's two desktop Undo checkpoints when the saved-result command asks for history. The label, notice and review dialog statements were rechecked beside #369's Jobs rows and are unchanged. The unit suite and the full installed suite on macOS arm64 Blender 5.1.2 passed against the rebuilt code; the fingerprints were refreshed and the review date is unchanged. On 2026-10-12 review fixes changed two behaviors: while the local-operation slot is busy, a PLY now queues ordinary verification and apply_recovered_model imports it only through the mesh snapshot path, whose _snapshot_ply asks for a new review when it finds splat data, while SPZ and .splat imports are still refused before anything is queued; and the native model import dialog now reports a ScenarioError reason after Model import was not started. The review paragraph now says a refusal at confirmation is reported with its reason after Model import was not started:, using the same _refusal wording as the first-frame dialog, and the test sentence names the busy-slot reason; an installed test drives invoke and execute with the real slot held. No physical desktop check of that report is claimed. The unit suite and the full installed suite on macOS arm64 Blender 5.0.1, 5.1.2 and 5.2.1 passed against the fixed code; Linux and Windows CI runs of the new tests are not claimed.",
    "sources": {
      "scenario/core/ui/saved_job_actions.py": "d25a4144d0357e0025606e6d3befb7dde6558df45f7c85b8f1db9383d83ba086",
      "scenario/blender/job_recovery.py": "b6e28f0b4c8b1ff282ffc5e2d1a574bde07867a7e94176e667b05ad5232a342e",
      "scenario/blender/model_jobs.py": "9e8739c8255bb778c4b45fb07e69cda41fcdc536308542c3f1a84d45156f3f22",
      "tests/unit/test_saved_job_actions.py": "a93fffad40b95de2714cd98b4370edf41059a2e995c4e748d27cc9bf45807903",
      "tests/blender/test_model_generation.py": "f884c59fcd384e04b7025218f542cb64726385d660acc2e1880b3f7af58e239e"
    }
  }
}
---

# Saved Gaussian splat import

Evidence for [the canonical document](../../UI_STYLE.md#saved-splat-review).
