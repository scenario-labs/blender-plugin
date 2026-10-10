---
{
  "type": "Evidence",
  "id": "docs-ui-style.saved-media-playback",
  "title": "Saved media playback rows and waveform box",
  "evidence": {
    "path": "docs/UI_STYLE.md",
    "scope": "saved-media-playback",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-10",
    "base_revision": "33d00b0554151c4de04731fd1a5e5c64ed50855b",
    "limits": "Reviewed that Play, Play in Blender and Waveform are saved-job descriptors sharing one row per downloaded media result, numbered over every saved asset and drawn by job_recovery.draw_controls for Jobs, Generations and the Studio pages that reuse them; that they are not job actions or MCP job_status names; and that the waveform box reads only cached controller state, sizes text and icon with preferences.system.ui_scale and builds its icon in the timer. Recording-layout draws refuse file, store and session access. Installed-ZIP native tests ran on macOS arm64 Blender 5.1.2 with the system opener and the animation player process patched; no player was opened and no desktop interaction, screenshot or human listening is claimed. Physical input, focus, viewport interaction and UI-scale screenshots remain #189 and #68 acceptance.",
    "sources": {
      "scenario/core/ui/saved_job_actions.py": "075c3dbe813629c45bbb28c6c3a79a43d4f282454a68ee2e9e3fef8f62fbe2d6",
      "scenario/blender/job_recovery.py": "4b237b2c40e440f138a2fe5d21c6a6398221074c47edf88b9f7cd1389ba1b267",
      "scenario/blender/result_media.py": "276b32bbb8e7c1eafa904d4e2762ecfbfaf8e9cfb3c611ffac300f1bea080b69",
      "scenario/blender/panels.py": "3fbc87ec9c92f91e619527b99f166303ee3a7628c056bba6b804325a16cff3c6",
      "tests/blender/test_result_media.py": "1a3609b7b385291ca5b47ca45e3119a00121898e12f10e7e9d715efcfd9d4aa6",
      "tests/blender/test_result_actions.py": "be4e4f5c5a60cae95945e5fbc3663ac0f04fa0742f33e1b7d3f6dc79f70f9660",
      "tests/unit/test_saved_job_actions.py": "8776484540675fb0e5b7a0be0a56eeb5d3a1d49e7d2582c5afcb335a90acda38"
    }
  }
}
---

# Saved media playback rows and waveform box

Evidence for [the canonical guide](../../UI_STYLE.md).
