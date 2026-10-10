---
{
  "type": "Evidence",
  "id": "docs-ui-style.automatic-result-previews",
  "title": "Saved result preview tiles",
  "evidence": {
    "path": "docs/UI_STYLE.md",
    "scope": "automatic-result-previews",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-10",
    "base_revision": "33d00b0554151c4de04731fd1a5e5c64ed50855b",
    "limits": "Reviewed result_previews.draw and its calls from panels.draw_result and draw_active_job, reused by Studio: tiles drawn only from precomputed controller state for the current context token, the icon or the kind's built-in icon at the same scale, numbered captions, one information line per distinct waiting status, an ERROR line and Retry preview (N) for missing, failed or unreadable previews, sizes from the region width divided by preferences.system.ui_scale, and no draw-time thumbnail for shared image rows. Recording layouts refuse file, os.stat and store access during draw. Installed-ZIP native tests (tests/blender/test_result_preview_tiles.py) ran on macOS arm64 Blender 5.0.1, 5.1.2 and 5.2.1 with synthetic PNG images, a synthetic SDK transport and an offline storage stub; drawing was checked through recording layouts and MagicMock panels, not physical input. No desktop interaction, screenshot, UI-scale review, live Scenario thumbnail or other operating system is claimed.",
    "sources": {
      "scenario/blender/result_previews.py": "f3de3c68e2e7d8401775fe27e3fa3f7e5e4e6ef07cb78dab32e11d3aaeab2641",
      "scenario/blender/panels.py": "c5ba66faaa0b5732a75e5519a4f6755fc06ef2db07374686835cf5ba32ab5389",
      "scenario/blender/studio.py": "d4ba0b268cdcc1a6d9477cb5f190ebb18233010de5b5963fecf941ba05995fb8",
      "tests/blender/test_result_preview_tiles.py": "be11193504d7053c384b96dce8249b5296cb955ef72bbfd02e194060dc1d85d8"
    }
  }
}
---

# Saved result preview tiles

Evidence for [the canonical guide](../../UI_STYLE.md).
