---
{
  "type": "Evidence",
  "id": "docs-mcp.film-export-controls",
  "title": "Native and MCP Film video export controls",
  "evidence": {
    "path": "docs/MCP.md",
    "scope": "film-export-controls",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-10",
    "base_revision": "33d00b0554151c4de04731fd1a5e5c64ed50855b",
    "limits": "Inspected session-owned FilmExportCommands (JobSession.film_export) over the existing export_film, publish_film_export, cancel_film_export and deliver_local_export session commands: inspection of local review scenes tagged as downloaded final or previs reviews with the current production ID and canonical recipe digest (timeline, foreign, changed-recipe, non-string-tag and library scenes excluded), per-candidate view-layer synchronization before origin capture, blocking reasons from the shared snapshot strip and media rules, preparation that binds the recipe and review scene origins, settings and a destination resolved by the session policy, an exact-string render approval that refuses a different destination, Edit Mode or a running export without consuming and otherwise is consumed once, the main-thread snapshot and owned-thread export, cached progress, cancellation, PUBLISH_FAILED with a separately chosen and approved copy-only re-publish, discard of private staging only, READY invalidation by origin, recipe or destination changes, at most eight handles with eviction only of finished handles that own no files, and shutdown cleanup after the export thread joins. Also inspected the native Film > Export panel and operators (an ExportHelper destination choice at the Output Folder's Film subfolder with numbered portable suggestions, audio and size choices, the separate Render video and Save video copy confirmations, Open folder and Copy SHA-256), the Studio Film Review page drawing both panels, the runtime maintenance poll and redraw, the Film panel's Export line and the MCP tools film_export_sources, prepare_film_export, render_film_export and film_export_review, whose agent destinations must resolve inside the Output Folder through film_export_policy.require_within (only the missing default Film folder may be created; spellings are not folded), plus film_export_policy.default_name. Installed synthetic tests cover inspection filters and blocking reasons, refused destinations and settings, Output Folder and link-escape restriction, exact-destination approval, the native file browser and Render dialogs including dismissal, numbered names and explicit audio and size choices, MCP and native handle sharing, cached progress and its panel text, cancellation without a destination, a failed save followed by a native copy-only re-publish, READY invalidation by a frame change, object selection or a new destination file, an export surviving a later edit, read-only panel and Studio drawing, Edit Mode gating, retirement, shutdown cleanup, the handle bound and registration order; unit tests cover default_name, require_within and the MCP description contract. One real child export of a 128 by 72 review used Blender's decode check; the other installed tests replace the child with a fast handoff while the real publish runs. Installed tests ran on macOS arm64 Blender 5.1.2 only; the PR records the exact ZIP. The fixture used an offline SDK transport and mocked review ffprobe; no service call, upload, download or spend occurred. No physical desktop interaction, screenshot, other Blender version, other OS/DPI, Windows path behavior for these controls, human playback review, live provider media, Studio case-study bundle or release acceptance is established. Only this export-controls topic was reviewed.",
    "sources": {
      "scenario/blender/film_export.py": "c62be3deca825545352feb1d8a486513538494cfb4fc2c70ae5249622d9c0c69",
      "scenario/blender/film_export_controls.py": "1f2ed405426630521410578938561afa04e438c078a8b91b0bb9fd0c62d1aa48",
      "scenario/core/jobs/film_export_policy.py": "621cb11a7281771db13bd3f06df05bf4437759ad12d0c494bf9c3dd3ebe6092f",
      "scenario/core/jobs/local_export.py": "3fe9dec68501ab40b6e292d41d4b62f54fd7049d4d47fdcde95feeb744c0e4a7",
      "scenario/blender/local_capture.py": "e0a07cda6bf8806368e7676d3fbbb3eaedc98cf62de8c76859e0e7091abcc50a",
      "scenario/core/jobs/coordinator.py": "58481d249c456139b8d228e7a91b3da4a6d0b03cfe0000e6ff53a5a27fc265f9",
      "scenario/blender/job_session.py": "21a022d6fac1a79be7a9ba6ab36b4450e9c15bc4f13a1f2186a15be05b0f2ed5",
      "scenario/blender/runtime.py": "221be244d46335a3bba76a06cc49b92365fe08d949b328a7865e84cb7ff5bdcb",
      "scenario/blender/film.py": "b8637080e4f7d792fc980eee6b672e08e906aca7341725f2384faa979c30666a",
      "scenario/blender/studio.py": "2a1560148ddea59008cb2611deaafabc0c7c74c6444923a4d84974a875d615f2",
      "scenario/mcp/tools_scenario.py": "8ab46fb065f06c9982a306decdd1019ff951f1111719bce83f586b1f81339a62",
      "tests/blender/test_film_export_controls.py": "35a2008d2949bf115d7db6a9fb4f89e82185e8b02fb8bccff7b0bbb064adf726",
      "tests/blender/test_studio_view.py": "ee8fa811a541bfbeeb96f24f0a16bfb2402f65ffadceb9331a8c9268d1cfea47",
      "tests/blender/test_mcp_contracts.py": "f070d6b59904d6054ba5926184dbac03655ca9b6f6d9ee843f7465d255c91abd",
      "tests/unit/test_film_export_policy.py": "e1f3776b5aebb036c1fce99f48d1d0e1ac979ab19969264d70a558b78b733852",
      "tests/unit/test_mcp_descriptions.py": "379ee89d194d4572b1342925230810dc27cd76a04b6d8ccb32dcb5863196ef93"
    }
  }
}
---

Source evidence for [the canonical guide](../../MCP.md).
