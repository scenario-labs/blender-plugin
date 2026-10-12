---
{
  "type": "Evidence",
  "id": "docs-ui-style.saved-media-playback",
  "title": "Saved media playback rows and waveform box",
  "evidence": {
    "path": "docs/UI_STYLE.md",
    "scope": "saved-media-playback",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-12",
    "base_revision": "33d00b0554151c4de04731fd1a5e5c64ed50855b",
    "limits": "Reviewed that Play, Play in Blender and Waveform are saved-job descriptors sharing one row per downloaded media result, numbered over every saved asset and drawn by job_recovery.draw_controls for Jobs, Generations and the Studio pages that reuse them; that they are not job actions or MCP job_status names; and that the waveform box reads only cached controller state and builds its icon in the timer. Re-reviewed on 2026-10-12 for the status wrapping: label_wrap measures each candidate line with blf font 0 at the widget text points times preferences.system.ui_scale (1 when background Blender reports 0), against a width less result_media.TEXT_INSET. That width is the one studio.draw_view declares through label_wrap.popup_layout, the width Studio passes to invoke_popup, which Blender 5.1.2's WM_operator_ui_popup multiplies by UI_SCALE_FAC for the popup's layout; else a sized context.region_popup; else context.region. Blender 5.1.2's popup_block_create sets the popup's new temporary region as region_popup before the first layout and ED_region_floating_init sizes it only afterwards, so that region is 0 px wide on the first draw; this was read from the 5.1.2 source, and a review's GUI probe on 5.1.2 logged 0 px on the first draw and the full width on the refresh. text_wrap breaks only at ASCII whitespace, never after a hyphen inside a word that fits (textwrap would), and splits a word wider than a line after its last hyphen that fits, else after its last character that fits; NO_BREAK is spelled as an escape. summary joins values and units, and each separator with the part before it, with no-break spaces. TEXT_INSET 106 adds slack to the 100 interface units measured from a private screenshot of the second physical pass (Blender 5.1.2 macOS Retina, UI scale 1.0, 561 px sidebar with category tabs); other nesting depths, fonts and sidebar layouts were not measured, and Studio's requested width has no sidebar tabs to subtract, so the inset is conservative there. Unit tests cover the wrap with a proportional stand-in font. Installed-ZIP native tests on macOS arm64 Blender 5.1.2 measure every drawn line with blf against that physical bound at 561 px and interface scale 2, at interface scale 4, in a sized 600 px popup invoked from a 2400 px region, and inside studio.draw_view with a 0 px popup region and a 300-unit request, whose lines and icon scale match a sized refresh; that test failed before the declaration with six short lines and icon scale 3. The desktop paragraph was reconciled with the private report of both physical passes (Blender 5.1.2 macOS arm64, UI scale 1.0, ZIPs built before the measured wrapping): the rows in the sidebar Jobs panel and on the Studio Jobs page, Play video opening the system player, Play in Blender opening the animation player that Escape closed with Blender's window frontmost again, and Waveform reaching its summary and icon. The measured wrapping, Play audio, desktop Cancel, Retry and close, viewport interaction, UI scale 2.0, other platforms and listening have no desktop evidence; they remain #189 and #68 acceptance.",
    "sources": {
      "scenario/core/ui/saved_job_actions.py": "075c3dbe813629c45bbb28c6c3a79a43d4f282454a68ee2e9e3fef8f62fbe2d6",
      "scenario/blender/job_recovery.py": "4b237b2c40e440f138a2fe5d21c6a6398221074c47edf88b9f7cd1389ba1b267",
      "scenario/blender/result_media.py": "4a5479d5592c54810687c12ace5190896747a7bb55443dfa0b5c485c204e5a88",
      "scenario/blender/panels.py": "3fbc87ec9c92f91e619527b99f166303ee3a7628c056bba6b804325a16cff3c6",
      "tests/blender/test_result_media.py": "b3c16d6844bd2bdfc4631913c53b26db050d4520f021ac7b4af7e567a516e73c",
      "tests/blender/test_result_actions.py": "be4e4f5c5a60cae95945e5fbc3663ac0f04fa0742f33e1b7d3f6dc79f70f9660",
      "tests/unit/test_saved_job_actions.py": "8776484540675fb0e5b7a0be0a56eeb5d3a1d49e7d2582c5afcb335a90acda38",
      "scenario/blender/label_wrap.py": "3e0cf29b6d34332b42fe1dc8dd589a1b26b962ead15da1843b3327a568a4a849",
      "scenario/core/ui/text_wrap.py": "c1998b35d3e44309f63f05386806b6a1e30979683b9d68e4169344b0d9d458f4",
      "tests/unit/test_text_wrap.py": "25015e65e490a8e1d842a72c2378e523854913e0ca65c7b796201de1d3f7fc7a",
      "scenario/blender/studio.py": "f3c017d3d03df01bcc643ca52569db002dcb906a6300c9b3e53f46134bdbb800"
    }
  }
}
---

# Saved media playback rows and waveform box

Evidence for [the canonical guide](../../UI_STYLE.md).
