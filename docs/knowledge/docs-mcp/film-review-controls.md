---
{
  "type": "Evidence",
  "id": "docs-mcp.film-review-controls",
  "title": "Native and MCP Film review controls",
  "evidence": {
    "path": "docs/MCP.md",
    "scope": "film-review-controls",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-09",
    "base_revision": "fb699b8555f7cee62147794516cc7aaa224864f7",
    "limits": "Inspected session-owned FilmReviewCommands over the existing JobSession review prepare, apply, receipt-retry and discard commands: separate preparation and build approvals, at most 16 handles, original scene/production/recipe/origin guards, copy deletion through the coordinator on invalidation (including the shared session's frame_change_pre origin revocation when a window selects the recipe scene again, depsgraph_update_post revocation after object selection or edits, and the undo_pre/redo_pre reset of every origin), cancellation and discard, consumption-aware build failures, receipt-only recovery and inspected dismissal. Also inspected the native Film > Review panel and operators, including the preparing/ready warning line, the prepare dialog's separate saved-job StoreError message and the build operator's UNDO-only options matching the timeline build; unsaved per-scene Final/Previs WindowManager state, the Studio Film Review page, the runtime maintenance poll and MCP prepare_film_review, film_review_status and build_film_review with their invalidation wording. Installed synthetic tests cover native/MCP handle sharing, dismissed dialogs, a storage error in the prepare dialog, cancellation during probing and local-slot admission, readable full-queue admission, frame and recipe invalidation, object selection and a direct call of the session's registered Undo/Redo handler invalidating ready reviews and preparing reviews (while probing is blocked, cancelling it, and after the worker returned but before maintenance, releasing its late copies) and deleting their copies, the warning line on preparing and ready reviews, a real window.scene round trip that fails waiting and ready reviews and deletes their copies while a built review keeps its scene, recipe scene deletion, an included saved master with an enabled dialog option and muted movie and sound alternates, and a previs review prepared and built beside a ready final review, which fails after the build's explicitly evaluated dependency update and builds again after a fresh preparation. They also cover missing master and ffprobe, rollback, receipt retry, inspected dismissal, the handle bound, shutdown cleanup, read-only panel/Studio drawing, mode navigation, Edit Mode gating and the build operator options; a unit test pins the MCP invalidation wording. Blender's own undo history stepping was not exercised for reviews, and invalidation by adding or editing objects is inferred from the same dependency handler rather than tested. The installed suite for this source passed 1,191 tests with 2 Windows-only skips on macOS arm64 Blender 5.1.2 only; the PR records the exact ZIP. The fixture used an offline SDK transport and mocked ffprobe; no service call, upload, download or spend occurred. No physical desktop interaction, screenshot, live provider media, other Blender version, other OS/DPI, human motion/audio review, video export or release acceptance is established. Readiness after a window selects the recipe scene again is not established; the shared origin rule is unchanged. Only this review-controls topic was reviewed.",
    "sources": {
      "scenario/blender/film_review_commands.py": "c198ae29e23a885e8bf2123fe400010cbbfb3db528498cf3781bcf6b63e16dc7",
      "scenario/blender/film_review_controls.py": "c0de361bd4060f396925ec88ac33eedb5954fa9e1fda1c0e9c6c604a201292b6",
      "scenario/blender/film_review.py": "c5ae003ab2786ae3bf598e2f62faf4d393ca68669d2ca4f5a76c9bfdd0020b3d",
      "scenario/blender/film_timeline_controls.py": "ec844854c2eaafa22930967ed3904997b93d675542e6072f96cc303b3c1b6767",
      "scenario/blender/job_session.py": "4f8557a7d47d75bea9eabc7e45db6a95d683fb394ae4f92272b8fed60824a7ce",
      "scenario/blender/film.py": "081e91ecae88fdf9cd57bbc968d944190cc15f67e44cf735bb7354a86c39693d",
      "scenario/blender/studio.py": "7a4a6b694ba4becb7a51dac11f95838a35d9f2a3dc752d85a50e1b1cd0f1f071",
      "scenario/blender/runtime.py": "b14d964efc5d31f17c863d8dc7e6bd4f7f4f1024388e5c0d2628ce9e08ba876c",
      "scenario/mcp/tools_scenario.py": "fbfcbdb67dadaffc2d8fdf0ebef3667cd868112df838b4fe004d01af20e39674",
      "tests/blender/test_film_review_controls.py": "79df14f44f4e92bdba5153ec6beec6aae4fffd37feb0fffad6252d1630003587",
      "tests/blender/test_studio_view.py": "78fc2021e77f20b541217e8ce7fc137c994adb5a98f39db346b83849716e4acf",
      "tests/blender/test_mcp_contracts.py": "dbd15f36c6237161861c4312954831719d02de8a0cb542950c44896cdbe20e2f",
      "tests/unit/test_mcp_descriptions.py": "5691c030d27baaacdc7302daab7ccbc04fdd29c8096e8b8f0cfc74ce6b55c3d4"
    }
  }
}
---

Source evidence for [the canonical guide](../../MCP.md).
