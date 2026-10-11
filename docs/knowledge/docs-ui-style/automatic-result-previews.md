---
{
  "type": "Evidence",
  "id": "docs-ui-style.automatic-result-previews",
  "title": "Saved result preview tiles",
  "evidence": {
    "path": "docs/UI_STYLE.md",
    "scope": "automatic-result-previews",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-11",
    "base_revision": "33d00b0554151c4de04731fd1a5e5c64ed50855b",
    "limits": "Reviewed result_previews.draw and its calls from panels.draw_result and draw_active_job, reused by Studio: tiles drawn only from precomputed controller state for the current context token, the icon or the kind's built-in icon at the same scale, numbered captions, one information line per distinct waiting status, an ERROR line and Retry preview (N) for missing, failed or unreadable previews, sizes from the region width divided by preferences.system.ui_scale, and no draw-time thumbnail for shared image rows. Recording layouts refuse file, os.stat and store access during draw. Installed-ZIP native tests (tests/blender/test_result_preview_tiles.py) ran on macOS arm64 Blender 5.0.1, 5.1.2 and 5.2.1 with synthetic PNG images, a synthetic SDK transport and an offline storage stub; drawing was checked through recording layouts and MagicMock panels, not physical input. No desktop interaction, screenshot, UI-scale review, live Scenario thumbnail or other operating system is claimed. Re-checked for the roughness caption fix: the caption labels moved to ROLE_LABEL in core.jobs.result_previews, which now has a label for every role in result_metadata.TEXTURE_ROLES, including roughness from 3d-texture-roughness, so no texture map is captioned by its kind alone. A unit test asserts that its keys equal TEXTURE_ROLES and an installed tile test captions roughness and smoothness maps; for this change the native suite ran on macOS arm64 Blender 5.1.2 only. The other claims are unchanged. Re-checked for the number-first tile captions: a tile now keeps its role or kind label and its number separately, draw writes Tile.title, the number first as (3) Albedo, under each icon, so Blender, which keeps the start of a label that does not fit, clips the label before the number, and Tile.caption keeps Albedo (3) for status, error and Retry lines. The Saved result previews section states the rule and the test. An installed tile test draws a GLB, an OBJ and two maps through a recording layout and checks the captions under the icons, the grouped status line and, with blf, that each number with an ellipsis fits its icon width in Blender's UI font; before the fix it read Model (1), Albedo (3), Model (2) and Normal (4). For this change the native suite ran on macOS arm64 Blender 5.0.1, 5.1.2 and 5.2.1. Blender's clipping itself is not exercised by the tests, and the number-first captions have no desktop evidence yet. The other claims are unchanged.",
    "sources": {
      "scenario/blender/result_previews.py": "81ed0f8bc793aa14120b9aebfe3955487c9e4f89d2f7f3ef1b9af3f991a318d0",
      "scenario/blender/panels.py": "c5ba66faaa0b5732a75e5519a4f6755fc06ef2db07374686835cf5ba32ab5389",
      "scenario/blender/studio.py": "d4ba0b268cdcc1a6d9477cb5f190ebb18233010de5b5963fecf941ba05995fb8",
      "tests/blender/test_result_preview_tiles.py": "35014551021f5c879153add113297216ac7ff49eb0f38102ff394f6d99c8df2b"
    }
  }
}
---

# Saved result preview tiles

Evidence for [the canonical guide](../../UI_STYLE.md).
