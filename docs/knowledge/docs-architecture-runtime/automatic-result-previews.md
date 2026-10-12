---
{
  "type": "Evidence",
  "id": "docs-architecture-runtime.automatic-result-previews",
  "title": "Result previews row with the preview controller",
  "evidence": {
    "path": "docs/architecture/runtime.md",
    "scope": "automatic-result-previews",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-12",
    "base_revision": "33d00b0554151c4de04731fd1a5e5c64ed50855b",
    "limits": "Reviewed the runtime map row: the preview controller requests stills for drawn jobs, decodes image copies on the main thread in a temporary data block and builds icons from rehashed cache files; clip display, MCP parity, live thumbnail coverage and desktop acceptance remain. Installed-ZIP native tests (tests/blender/test_result_preview_tiles.py) ran on macOS arm64 Blender 5.0.1, 5.1.2 and 5.2.1 with synthetic PNG images, a synthetic SDK transport and an offline storage stub; drawing was checked through recording layouts and MagicMock panels, not physical input. No desktop interaction, screenshot, UI-scale review, live Scenario thumbnail or other operating system is claimed. The controller decodes image copies and icons with the shared preview_decode helper from #384, re-checked here; its own copy of that decode was removed, and semi-transparent high bit-depth pixels are now unpremultiplied before the sRGB conversion as the helper documents. Re-checked for the roughness caption fix: the caption labels moved to ROLE_LABEL in core.jobs.result_previews, which now has a label for every role in result_metadata.TEXTURE_ROLES, including roughness from 3d-texture-roughness, so no texture map is captioned by its kind alone. A unit test asserts that its keys equal TEXTURE_ROLES and an installed tile test captions roughness and smoothness maps; for this change the native suite ran on macOS arm64 Blender 5.1.2 only. The other claims are unchanged. Re-checked for the number-first tile captions: a tile now keeps its role or kind label and its number separately, draw writes Tile.title, the number first as (3) Albedo, under each icon, so Blender, which keeps the start of a label that does not fit, clips the label before the number, and Tile.caption keeps Albedo (3) for status, error and Retry lines. This document makes no caption claim; its other claims are unchanged. Re-checked for the measured status wrapping: draw now wraps the status, error and Retry lines with label_wrap, shared with the waveform box, measured in Blender's interface font against the drawn region (inside Studio the width it requests for its popup, otherwise a sized popup region first, also for the icon size) less TEXT_INSET 96, and keeps a caption such as Model (2) whole with a no-break space; installed tile tests measure the lines in a 561 px sidebar at interface scale 2, in a 600 px popup invoked from a 2400 px region, whose case fails with the previous 7-unit estimate, and inside studio.draw_view with a 0 px popup region and a 300-unit request, whose lines and icon scale 5.0 match a sized refresh and which fails without Studio's declared width (icon scale 2.5 and one-word lines). For this change the native suite ran on macOS arm64 Blender 5.1.2 only. This document makes no wrapping claim; its other claims are unchanged. This topic's evidence statements describe its own review; the partial physical desktop passes that UI_STYLE, KNOWN_LIMITATIONS and RESULT_PREVIEWS record were not part of it.",
    "sources": {
      "scenario/blender/result_previews.py": "4e9b66ce4f799befdb2ade19d9c524dbae08766811caffa86a340095de217973",
      "scenario/core/jobs/result_previews.py": "f2bef8bfd24c2f75f45c0eaa3f85b7bd4806324bfcc0c3abb4062ed6cd147bef",
      "scenario/core/jobs/results.py": "f6a9702a09824cb28c46d99cfa1a37fa194d64ba2ad1c830bf11884e1b66d31f",
      "scenario/core/jobs/preview_scheduler.py": "b4deebeae3ff7a09c5b602df8af8f96608838a8b675e79c2fd6614a6b128186b",
      "tests/blender/test_result_preview_tiles.py": "d5b88d2e52d415755d7849c1766a6aa083934e893287753fd2fbe173b3daa9f9",
      "tests/unit/test_result_previews.py": "b5f75e6c2d562ae9c85dea8a4a6bf89d0a5c9bc3c7d556e5b9baf804ceafc34e",
      "scenario/blender/runtime.py": "ed7c47498c849441926d2d3032aac00a6b20744e1e8ad75a7f31ca044ab57db2",
      "scenario/blender/preview_decode.py": "30c21fe513960e0aa4730122721115301784ed2e4a5b2e724cd670845fa978f9"
    }
  }
}
---

# Result previews row with the preview controller

Evidence for [the canonical guide](../../architecture/runtime.md).
