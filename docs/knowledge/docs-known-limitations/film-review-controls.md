---
{
  "type": "Evidence",
  "id": "docs-known-limitations.film-review-controls",
  "title": "Native and MCP Film review controls",
  "evidence": {
    "path": "docs/KNOWN_LIMITATIONS.md",
    "scope": "film-review-controls",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-09",
    "base_revision": "33d00b0554151c4de04731fd1a5e5c64ed50855b",
    "limits": "Inspected session-owned FilmReviewCommands over the existing JobSession review prepare, apply, receipt-retry and discard commands: separate preparation and build approvals, at most 16 handles, original scene/production/recipe/origin guards, copy deletion through the coordinator on invalidation (including the shared session's frame_change_pre origin revocation when a window selects the recipe scene again, depsgraph_update_post revocation after object selection or edits, and the undo_pre/redo_pre reset of every origin), cancellation and discard, consumption-aware build failures, receipt-only recovery and inspected dismissal. Also inspected the native Film > Review panel and operators, including the preparing/ready warning line, the prepare dialog's separate saved-job StoreError message and the build operator's UNDO-only options matching the timeline build; unsaved per-scene Final/Previs WindowManager state, the Studio Film Review page, the runtime maintenance poll and MCP prepare_film_review, film_review_status and build_film_review with their invalidation wording; film_review_status cancels before its maintenance poll, like the native Cancel button and film_composition_review. Installed synthetic tests cover native/MCP handle sharing, dismissed dialogs, a storage error in the prepare dialog, cancellation during probing and, over MCP, after probing returned but before maintenance delivered it, local-slot admission, readable full-queue admission, frame and recipe invalidation, object selection and a direct call of the session's registered Undo/Redo handler invalidating ready reviews and preparing reviews (while probing is blocked, cancelling it, and after the worker returned but before maintenance, releasing its late copies) and deleting their copies, the warning line on preparing and ready reviews, a real window.scene round trip that fails waiting and ready reviews and deletes their copies while a built review keeps its scene, recipe scene deletion, an included saved master with an enabled dialog option and muted movie and sound alternates, and a previs review prepared and built beside a ready final review, which fails after the build's explicitly evaluated dependency update and builds again after a fresh preparation. They also cover missing master and ffprobe, rollback, receipt retry, inspected dismissal, the handle bound, shutdown cleanup, read-only panel/Studio drawing, mode navigation, Edit Mode gating and the build operator options; a unit test pins the MCP invalidation wording. Blender's own undo history stepping was not exercised for reviews, and invalidation by adding or editing objects is inferred from the same dependency handler rather than tested. The installed suite for this source passed 1,227 tests with 2 Windows-only skips on macOS arm64 Blender 5.1.2 only; the PR records the exact ZIP. The fixture used an offline SDK transport and mocked ffprobe; no service call, upload, download or spend occurred. No physical desktop interaction, screenshot, live provider media, other Blender version, other OS/DPI, human motion/audio review, video export or release acceptance is established. Readiness after a window selects the recipe scene again is not established; the shared origin rule is unchanged. Only this review-controls topic was reviewed.",
    "sources": {
      "scenario/blender/film_review_commands.py": "c198ae29e23a885e8bf2123fe400010cbbfb3db528498cf3781bcf6b63e16dc7",
      "scenario/blender/film_review_controls.py": "c0de361bd4060f396925ec88ac33eedb5954fa9e1fda1c0e9c6c604a201292b6",
      "scenario/blender/film_review.py": "c5ae003ab2786ae3bf598e2f62faf4d393ca68669d2ca4f5a76c9bfdd0020b3d",
      "scenario/blender/film_timeline_controls.py": "ec844854c2eaafa22930967ed3904997b93d675542e6072f96cc303b3c1b6767",
      "scenario/blender/job_session.py": "107dd8b06d1328229bcb6c4c34baed3e4a904e8450f8b68c3bd4c41aba41e9e1",
      "scenario/blender/film.py": "081e91ecae88fdf9cd57bbc968d944190cc15f67e44cf735bb7354a86c39693d",
      "scenario/blender/studio.py": "7a4a6b694ba4becb7a51dac11f95838a35d9f2a3dc752d85a50e1b1cd0f1f071",
      "scenario/blender/runtime.py": "64b6e702f91c80be66ee6378125745b2db1d10f583bddd9f449dd3a06d15b4f8",
      "scenario/mcp/tools_scenario.py": "48433524336a5a89335fe3a85b51378aa151d6a8ad6f93eb092ed740e7b04d47",
      "tests/blender/test_film_review_controls.py": "0368403d25af22be33730babc2b5dc30239cb1bca3fab64189219dc623fddd71",
      "tests/blender/test_studio_view.py": "78fc2021e77f20b541217e8ce7fc137c994adb5a98f39db346b83849716e4acf",
      "tests/blender/test_mcp_contracts.py": "dbd15f36c6237161861c4312954831719d02de8a0cb542950c44896cdbe20e2f",
      "tests/unit/test_mcp_descriptions.py": "5691c030d27baaacdc7302daab7ccbc04fdd29c8096e8b8f0cfc74ce6b55c3d4"
    }
  }
}
---

Source evidence for [the canonical guide](../../KNOWN_LIMITATIONS.md).
