---
{
  "type": "Evidence",
  "id": "docs-ui-style.composer-placement",
  "title": "Composer placement beside overlapping side regions",
  "evidence": {
    "path": "docs/UI_STYLE.md",
    "scope": "composer-placement",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-09",
    "base_revision": "b57c398f35fb2148c82fb8b26f6a40564d3f52ef",
    "limits": "Source-reviewed composer placement within the span left by visible overlapping TOOLS/UI regions, shared draw/hit-test layout, hard side-region clamping of saved offsets and widths, small-span narrowing including the 200 px floor below which the card starts at the toolbar edge, the scaled 40 px bare-edge minimum, move and resize drags that start from the clamped placement as drawn, and releases that store the drawn offset (and width after a resize) while Escape restores the saved placement. Unit tests cover inset centring, clamping, narrowing and offset and width round trips. Installed native tests use synthetic overlapping, hidden, beside and flipped regions with stubbed gpu/blf drawing, call the modal's drag move and release handlers with synthetic events while the sidebar is opened and closed, and check the background viewport's real regions, on Blender 5.1.2 macOS arm64 only. Headers, the asset shelf and other horizontal regions are not considered. No physical desktop input, screenshot, other DPI or Blender 5.0/5.2 run is claimed; physical sidebar-open acceptance remains under #66.",
    "sources": {
      "scenario/core/ui/composer_layout.py": "0e34da2f43b9b5fb7949af37a202d5b82bdf1240f80108a86d07cd193367b32d",
      "scenario/blender/composer/draw.py": "94fc06b19a9f78ca70fa3383c78fa16e0f3fea4e4b838d2e0d0eff16f7d89d32",
      "scenario/blender/composer/modal.py": "a13131121ef97171d00053e00b039b9fc2ab0b049babc47468d137c96602e975",
      "scenario/blender/composer/state.py": "063ea956a996356b7dd1b28cc16b7dc4aaa1806a9336efe7d0d79052afbf5f79",
      "tests/unit/test_composer_layout.py": "e879022bbed198f9b88736d657cfd6676bfe957dd3d86705991fe2ddf1acadb9",
      "tests/blender/test_composer.py": "416377742218d775450de54d0248b8aec872d18b2d9c03abc4646d5386a0c58c"
    }
  }
}
---

# Composer placement beside overlapping side regions

Supports the [UI style guide](../../UI_STYLE.md#composer-placement) for how the floating
composer keeps clear of the toolbar and sidebar drawn over the 3D viewport.
