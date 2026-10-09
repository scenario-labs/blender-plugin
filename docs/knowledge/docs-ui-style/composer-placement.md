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
    "limits": "Source-reviewed composer placement within the span left by visible overlapping TOOLS/UI regions, shared draw/hit-test layout, hard side-region clamping of saved offsets and widths, the pill shown in place of an expanded card whose minimum width plus margins does not fit that span (drawn, hit and dragged as the pill, a click opening the lane's Settings dialog with a status message, the stored expanded choice and card width unchanged, a focused prompt committed and left), the pill's margin drop and 200 px floor from the toolbar edge, the scaled 40 px bare-edge minimum, move and resize drags that start from the clamped placement as drawn, releases that store the drawn offset (and width after a resize) while Escape restores the saved placement, and lane tab labels chosen in the pure layout from injected text widths (full, else short, else the short label clipped with an ellipsis, never empty). Unit tests cover inset centring, clamping, the card-fit threshold at scales 1, 2 and 4, the scale-4 Retina sidebar span, the pill floor, offset and width round trips and tab label selection. Installed native tests use synthetic overlapping, hidden, beside and flipped regions and a synthetic scale-4 Retina context with stubbed gpu/blf drawing, call the modal's event, drag move and release handlers with synthetic events while the sidebar is opened and closed, and check the background viewport's real regions, on Blender 5.1.2 macOS arm64 only. The Settings dialog itself is stubbed in these tests. Headers, the asset shelf and other horizontal regions are not avoided. A physical macOS Blender 5.2.1 check at composer scale 4 reported the card under the sidebar and blank or truncated tab labels before this change; no physical rerun, screenshot, other DPI or Blender 5.0/5.2 installed run is claimed for it, and physical sidebar-open acceptance remains under #66.",
    "sources": {
      "scenario/core/ui/composer_layout.py": "36cb4cb57704fefe3c883a544b7dde98a3a61ca0326eb9164d18bf9188717cc8",
      "scenario/blender/composer/draw.py": "4906c1270731940ef3d69187f8ea7730e2230039e9b14ca342a4f3799b950806",
      "scenario/blender/composer/modal.py": "f2345eab02d0e576112115ff67f2a4da197da949696405014779a4b7c4e14ddf",
      "scenario/blender/composer/state.py": "063ea956a996356b7dd1b28cc16b7dc4aaa1806a9336efe7d0d79052afbf5f79",
      "tests/unit/test_composer_layout.py": "cf6d8487d91102964071042aa80dc3ec59ba6121a7a47d427f92eb77173e96d9",
      "tests/blender/test_composer.py": "5ad06388b21599a90a5fd83e197f3e8bd21f5b7642d5cac0fd89393cc2a2eadd"
    }
  }
}
---

# Composer placement beside overlapping side regions

Supports the [UI style guide](../../UI_STYLE.md#composer-placement) for how the floating
composer keeps clear of the toolbar and sidebar drawn over the 3D viewport.
