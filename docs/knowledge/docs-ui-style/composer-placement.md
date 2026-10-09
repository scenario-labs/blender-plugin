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
    "base_revision": "fb699b8555f7cee62147794516cc7aaa224864f7",
    "limits": "Source-reviewed composer placement within the span left by visible overlapping TOOLS/UI regions, shared draw/hit-test layout, hard side-region clamping of saved offsets and widths, the pill shown in place of an expanded card when the uncovered span cannot hold the card's minimum width plus margins or the region cannot hold its height plus margins (drawn, hit and dragged as the pill, a click opening the lane's Settings dialog with a status message that is also reported to the status bar, the stored expanded choice and card width unchanged, a focused prompt committed and left, or left with a warning and without overwriting a lane prompt changed elsewhere), the pill narrowing to its 200 px minimum with its margins kept, then into the margins, and keeping that minimum from the toolbar edge below it, the scaled 40 px bare-edge minimum, move and resize drags that start from the clamped placement as drawn, releases that store the drawn offset (and width after a resize) while Escape restores the saved placement, lane tab labels chosen in the pure layout from injected text widths (full, else short, else the short label clipped with an ellipsis, never empty), and the model chip showing the sidebar only when the card still fits beside it. A hidden sidebar is predicted at its reported width, else at Blender's 220 px default times the UI scale: background Blender 5.1.2 reports a hidden 3D View sidebar as 1 px wide and the factory startup's visible Image and Node Editor sidebars as 220 px; a sidebar widened before it was hidden can reopen wider than predicted. Unit tests cover inset centring, clamping, the card-fit width and height thresholds at scales 1, 2 and 4, the scale-4 Retina sidebar span, the pill's narrowing and floor, offset and width round trips including a short region, and tab label selection. Installed native tests use synthetic overlapping, hidden, beside and flipped regions, synthetic scale-4 Retina and short-viewport (scales 1, 2 and 4) contexts, a custom-UI scale of 4 with pixel size 4 and resolution scale 2 with stubbed gpu/blf drawing, call the modal's event, drag move and release handlers with synthetic events while the sidebar is opened and closed, press the model chip with the sidebar opener and picker patched, and check the background viewport's real regions, on Blender 5.1.2 macOS arm64 only. The Settings dialog, the model picker and the sidebar opener are stubbed in these tests. Headers, the asset shelf and other horizontal regions are not avoided, and the height check uses the whole main region. The composer scale is preferences.system.ui_scale: a physical macOS Blender 5.2.1 Retina session at a Preferences resolution scale of 2 reported a pixel size of 4 and DPI 288, so the earlier pixel size times resolution scale drew the composer at 8 instead of 4. A physical macOS Blender 5.2.1 check at that resolution scale reported the card under the sidebar and blank or truncated tab labels before this change. A physical rerun of this branch's packaged ZIP in an isolated Blender 5.2.1 profile on macOS 27.0.1 arm64 (Retina window 1512 x 917 pt, offline, CGEvent input) then showed: at resolution scale 2, the pill drawn at Blender's UI size; with the sidebar hidden, a click expanding the card with the tabs Image, Video, 3D, Materials, R-Img and R-Vid; with the 1,122 px sidebar open, the pill clear of the toolbar and sidebar, and a click opening the Image settings dialog with the no-room hint in the status bar; closing the sidebar bringing the card back by itself; and the model chip with the sidebar hidden opening the picker alone while the sidebar stayed hidden. At resolution scale 1, the card expanded with full tab labels and the model chip opened the picker and showed the sidebar, with the card clear of it. No Blender 5.0/5.1 physical run, other OS, external display DPI or online generation is claimed, and remaining composer acceptance stays under #66.",
    "sources": {
      "scenario/core/ui/composer_layout.py": "61d139e6e8bb886b061aee796b84484b2990efc772b136d63b1553aa1f4d508f",
      "scenario/blender/composer/draw.py": "af14182391dacb90947693e91633b071f93e1622fc0222d55f30f3d506d0b6f0",
      "scenario/blender/composer/modal.py": "328ee896ce9d0c765f067f4aac5ecb0a854dcfcfc8077b065f7d6db86ba1c7e7",
      "scenario/blender/composer/state.py": "063ea956a996356b7dd1b28cc16b7dc4aaa1806a9336efe7d0d79052afbf5f79",
      "scenario/blender/popover.py": "7366e3dd7f5ad9414d9ad9e3246c072beef207f6edfbc6705488210fa1dbee35",
      "tests/unit/test_composer_layout.py": "78c7362c9ecf1b5b43660425b49ff80314c3abe6351ab9ef8266684aa5b8730e",
      "tests/blender/test_composer.py": "3b8f83392c612a6064aad10d8141501e24578893a7f620026193fd151293615e"
    }
  }
}
---

# Composer placement beside overlapping side regions

Supports the [UI style guide](../../UI_STYLE.md#composer-placement) for how the floating
composer keeps clear of the toolbar and sidebar drawn over the 3D viewport.
