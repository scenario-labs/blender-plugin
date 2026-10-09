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
    "limits": "Source-reviewed composer placement within the span left by visible overlapping TOOLS/UI regions, shared draw/hit-test layout, hard side-region clamping of saved offsets and widths, small-span narrowing and the offset recomputed after drags. Unit tests cover inset centring, clamping, narrowing and offset round trips. Installed native tests use synthetic overlapping, hidden, beside and flipped regions with stubbed gpu/blf drawing, plus the background viewport's real regions, on Blender 5.1.2 macOS arm64 only. Headers, the asset shelf and other horizontal regions are not considered. No physical desktop input, screenshot, other DPI or Blender 5.0/5.2 run is claimed; physical sidebar-open acceptance remains under #66.",
    "sources": {
      "scenario/core/ui/composer_layout.py": "0e34da2f43b9b5fb7949af37a202d5b82bdf1240f80108a86d07cd193367b32d",
      "scenario/blender/composer/draw.py": "94fc06b19a9f78ca70fa3383c78fa16e0f3fea4e4b838d2e0d0eff16f7d89d32",
      "scenario/blender/composer/modal.py": "891702f13673ac7acd5447e5d6aaaa31ef97fdb0d45880fbea39ade04db800cd",
      "tests/unit/test_composer_layout.py": "f2ec94f36b0bbea91b4ac603f67bef44d406d36d9696660b9a89c53e801b715f",
      "tests/blender/test_composer.py": "218a432c6d1f229082ffa84fac2127c4c9aaf995530c7c529de873033426492a"
    }
  }
}
---

# Composer placement beside overlapping side regions

Supports the [UI style guide](../../UI_STYLE.md#composer-placement) for how the floating
composer keeps clear of the toolbar and sidebar drawn over the 3D viewport.
