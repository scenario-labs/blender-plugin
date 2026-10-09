---
{
  "type": "Evidence",
  "id": "docs-ui-style.film-review-controls",
  "title": "Native and MCP Film review controls",
  "evidence": {
    "path": "docs/UI_STYLE.md",
    "scope": "film-review-controls",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-09",
    "base_revision": "b57c398f35fb2148c82fb8b26f6a40564d3f52ef",
    "limits": "Inspected session-owned FilmReviewCommands over the existing JobSession review prepare, apply, receipt-retry and discard commands: separate preparation and build approvals, at most 16 handles, original scene/production/recipe/origin guards, copy deletion through the coordinator on invalidation (including the shared session's frame_change_pre origin revocation when a window selects the recipe scene again), cancellation and discard, consumption-aware build failures, receipt-only recovery and inspected dismissal. Also inspected the native Film > Review panel and operators, unsaved per-scene Final/Previs WindowManager state, the Studio Film Review page, the runtime maintenance poll and MCP prepare_film_review, film_review_status and build_film_review. Installed synthetic tests cover native/MCP handle sharing, dismissed dialogs, cancellation during probing and local-slot admission, readable full-queue admission, frame and recipe invalidation, a real window.scene round trip that fails waiting and ready reviews and deletes their copies while a built review keeps its scene, recipe scene deletion, an included saved master with an enabled dialog option and muted movie and sound alternates, missing master and ffprobe, rollback, receipt retry, inspected dismissal, the handle bound, shutdown cleanup, read-only panel/Studio drawing, mode navigation and Edit Mode gating. Exact ZIP 6f603031597728935ff43802b3f0b852d0947a11b73cd3e9f3632f98f3982677 passed 1,173 installed tests with 2 Windows-only skips on macOS arm64 Blender 5.1.2 only. The fixture used an offline SDK transport and mocked ffprobe; no service call, upload, download or spend occurred. No physical desktop interaction, screenshot, live provider media, other Blender version, other OS/DPI, human motion/audio review, video export or release acceptance is established. Readiness after a window selects the recipe scene again is not established; the shared origin rule is unchanged. Only this review-controls topic was reviewed.",
    "sources": {
      "scenario/blender/film_review_commands.py": "c198ae29e23a885e8bf2123fe400010cbbfb3db528498cf3781bcf6b63e16dc7",
      "scenario/blender/film_review_controls.py": "e38e1eeba4f83991326fe65394cc1202d2dad01390bc7603e2c38613c213ee77",
      "scenario/blender/film_review.py": "c5ae003ab2786ae3bf598e2f62faf4d393ca68669d2ca4f5a76c9bfdd0020b3d",
      "scenario/blender/job_session.py": "4f8557a7d47d75bea9eabc7e45db6a95d683fb394ae4f92272b8fed60824a7ce",
      "scenario/blender/film.py": "081e91ecae88fdf9cd57bbc968d944190cc15f67e44cf735bb7354a86c39693d",
      "scenario/blender/studio.py": "7a4a6b694ba4becb7a51dac11f95838a35d9f2a3dc752d85a50e1b1cd0f1f071",
      "scenario/blender/runtime.py": "e6e836339a392b91a53b5060edd9ce6ccbafefb799901c599a5d17fa606c0d3e",
      "scenario/mcp/tools_scenario.py": "2b054fadaf1a65e24aa34909d85b276e25d181a8c31b4ce29b6af2521574ca29",
      "tests/blender/test_film_review_controls.py": "38a6e5523291805c987327babe8e644378277c53f0f253fd66792f1e66d51566",
      "tests/blender/test_studio_view.py": "78fc2021e77f20b541217e8ce7fc137c994adb5a98f39db346b83849716e4acf",
      "tests/blender/test_mcp_contracts.py": "dbd15f36c6237161861c4312954831719d02de8a0cb542950c44896cdbe20e2f",
      "tests/unit/test_mcp_descriptions.py": "6b9a7e0e71409da45c6591dffd14e5e2c38520023c8f0ec518a98c2c97a19f31"
    }
  }
}
---

Source evidence for [the canonical guide](../../UI_STYLE.md).
