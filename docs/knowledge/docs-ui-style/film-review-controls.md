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
    "limits": "Inspected session-owned FilmReviewCommands over the existing JobSession review prepare, apply, receipt-retry and discard commands: separate preparation and build approvals, at most 16 handles, original scene/production/recipe/origin guards, copy deletion through the coordinator on invalidation, cancellation and discard, consumption-aware build failures, receipt-only recovery and inspected dismissal. Also inspected the native Film > Review panel and operators, unsaved per-scene Final/Previs WindowManager state, the Studio Film Review page, the runtime maintenance poll and MCP prepare_film_review, film_review_status and build_film_review. Installed synthetic tests cover native/MCP handle sharing, dismissed dialogs, cancellation during probing and local-slot admission, frame and recipe invalidation, scene switching and deletion, missing master and ffprobe, rollback, receipt retry, inspected dismissal, the handle bound, shutdown cleanup, read-only panel/Studio drawing, mode navigation and Edit Mode gating. Exact ZIP 5a205452735c87911a03af36b30db413d99e60263c8a646e77b02fcf84f8183f passed 1,171 installed tests with 2 Windows-only skips on macOS arm64 Blender 5.1.2 only. The fixture used an offline SDK transport and mocked ffprobe; no service call, upload, download or spend occurred. No physical desktop interaction, screenshot, included-master fixture, live provider media, other Blender version, other OS/DPI, human motion/audio review, video export or release acceptance is established. Only this review-controls topic was reviewed.",
    "sources": {
      "scenario/blender/film_review_commands.py": "6a79f9592f85d01d4894d6775be3e30ac2c16b21d330fe2119c56a34458d0afb",
      "scenario/blender/film_review_controls.py": "5877fdfd377b00f8ce2c25d64d804b8c488052af36ee757822c7d9f636aed69c",
      "scenario/blender/film_review.py": "c5ae003ab2786ae3bf598e2f62faf4d393ca68669d2ca4f5a76c9bfdd0020b3d",
      "scenario/blender/job_session.py": "4f8557a7d47d75bea9eabc7e45db6a95d683fb394ae4f92272b8fed60824a7ce",
      "scenario/blender/film.py": "081e91ecae88fdf9cd57bbc968d944190cc15f67e44cf735bb7354a86c39693d",
      "scenario/blender/studio.py": "7a4a6b694ba4becb7a51dac11f95838a35d9f2a3dc752d85a50e1b1cd0f1f071",
      "scenario/blender/runtime.py": "e6e836339a392b91a53b5060edd9ce6ccbafefb799901c599a5d17fa606c0d3e",
      "scenario/mcp/tools_scenario.py": "fbbd42123644fae0c6c819b3e9d71254e380a063f89ab88783e9120fc93b115d",
      "tests/blender/test_film_review_controls.py": "39902d2a36f206d9bb5d45ab891a1ea615fd9dde2919a62c0dc3c76cfcfeb4a1",
      "tests/blender/test_studio_view.py": "78fc2021e77f20b541217e8ce7fc137c994adb5a98f39db346b83849716e4acf",
      "tests/blender/test_mcp_contracts.py": "dbd15f36c6237161861c4312954831719d02de8a0cb542950c44896cdbe20e2f",
      "tests/unit/test_mcp_descriptions.py": "6b9a7e0e71409da45c6591dffd14e5e2c38520023c8f0ec518a98c2c97a19f31"
    }
  }
}
---

Source evidence for [the canonical guide](../../UI_STYLE.md).
