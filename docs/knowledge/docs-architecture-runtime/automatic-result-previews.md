---
{
  "type": "Evidence",
  "id": "docs-architecture-runtime.automatic-result-previews",
  "title": "Result previews row with the preview controller",
  "evidence": {
    "path": "docs/architecture/runtime.md",
    "scope": "automatic-result-previews",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-11",
    "base_revision": "33d00b0554151c4de04731fd1a5e5c64ed50855b",
    "limits": "Reviewed the runtime map row: the preview controller requests stills for drawn jobs, decodes image copies on the main thread in a temporary data block and builds icons from rehashed cache files; clip display, MCP parity, live thumbnail coverage and desktop acceptance remain. Installed-ZIP native tests (tests/blender/test_result_preview_tiles.py) ran on macOS arm64 Blender 5.0.1, 5.1.2 and 5.2.1 with synthetic PNG images, a synthetic SDK transport and an offline storage stub; drawing was checked through recording layouts and MagicMock panels, not physical input. No desktop interaction, screenshot, UI-scale review, live Scenario thumbnail or other operating system is claimed. The controller decodes image copies and icons with the shared preview_decode helper from #384, re-checked here; its own copy of that decode was removed, and semi-transparent high bit-depth pixels are now unpremultiplied before the sRGB conversion as the helper documents. Re-checked for the roughness caption fix: the caption labels moved to ROLE_LABEL in core.jobs.result_previews, which now has a label for every role in result_metadata.TEXTURE_ROLES, including roughness from 3d-texture-roughness, so no texture map is captioned by its kind alone. A unit test asserts that its keys equal TEXTURE_ROLES and an installed tile test captions roughness and smoothness maps; for this change the native suite ran on macOS arm64 Blender 5.1.2 only. The other claims are unchanged. Re-checked for the number-first tile captions: a tile now keeps its role or kind label and its number separately, draw writes Tile.title, the number first as (3) Albedo, under each icon, so Blender, which keeps the start of a label that does not fit, clips the label before the number, and Tile.caption keeps Albedo (3) for status, error and Retry lines. This document makes no caption claim; its other claims are unchanged.",
    "sources": {
      "scenario/blender/result_previews.py": "81ed0f8bc793aa14120b9aebfe3955487c9e4f89d2f7f3ef1b9af3f991a318d0",
      "scenario/core/jobs/result_previews.py": "f2bef8bfd24c2f75f45c0eaa3f85b7bd4806324bfcc0c3abb4062ed6cd147bef",
      "scenario/core/jobs/results.py": "f6a9702a09824cb28c46d99cfa1a37fa194d64ba2ad1c830bf11884e1b66d31f",
      "scenario/core/jobs/preview_scheduler.py": "b4deebeae3ff7a09c5b602df8af8f96608838a8b675e79c2fd6614a6b128186b",
      "tests/blender/test_result_preview_tiles.py": "35014551021f5c879153add113297216ac7ff49eb0f38102ff394f6d99c8df2b",
      "tests/unit/test_result_previews.py": "b5f75e6c2d562ae9c85dea8a4a6bf89d0a5c9bc3c7d556e5b9baf804ceafc34e",
      "scenario/blender/runtime.py": "ed7c47498c849441926d2d3032aac00a6b20744e1e8ad75a7f31ca044ab57db2",
      "scenario/blender/preview_decode.py": "30c21fe513960e0aa4730122721115301784ed2e4a5b2e724cd670845fa978f9"
    }
  }
}
---

# Result previews row with the preview controller

Evidence for [the canonical guide](../../architecture/runtime.md).
