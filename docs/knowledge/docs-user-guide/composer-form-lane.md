---
{
  "type": "Evidence",
  "id": "docs-user-guide.composer-form-lane",
  "title": "Composer form lane in 3D Edit mode",
  "evidence": {
    "path": "docs/USER_GUIDE.md",
    "scope": "composer-form-lane",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-11",
    "base_revision": "fb699b8555f7cee62147794516cc7aaa224864f7",
    "limits": "Reviewed the floating composer paragraph's 3D Edit mode, replaced-form and no-prompt statements against the composer state, draw and modal code, the Settings and model chip flush, the lane tab and double-click focus rules, the 3D Settings dialog and the Edit form's Generate row. Installed tests on macOS arm64 Blender 5.0.1, 5.1.2 and 5.2.1 cover the displayed Edit model, prompt and price, Generate/Enter submission of the Edit quote, the disabled state without an Edit price, refused typing, Esc, Enter, Generate and a lane tab after a replacement, a refused outside click (the guarded flush that test_composer.py checks after a mode switch and test_studio_view.py drives through the modal handler after a lane change), a double-click that keeps the original text, the dialogs' flush, the no-prompt placeholder, a lane tab to a form without a prompt and a model without a prompt loaded under a focused prompt. A private offline event-queue GUI check on the same versions, without OS input, covers the earlier interactions on a ZIP built before the lane tab, double-click and model-change rules. Other statements in that paragraph, including the Settings route to Edit mode, keep their own topics' limits. Rechecked after rebasing onto main's model description status and retry, material guidance and picker thumbnail changes, which leave the lane rule and its callers unchanged. Rechecked after merging main's handbook changes, which add the Settings route to Edit mode to that paragraph and an outside-click sentence to the next one, and main's sidebar status wrapping and job strip geometry, which leave the Generate row choice, the no-prompt rule and the composer strings unchanged. Rechecked after rebasing onto main's overlapping-sidebar composer, which adds the dragging, short-label and no-room sentences to that paragraph and ends a focused prompt without writing a replaced form when the card gives way to the pill (an exit the paragraph does not list), and main's saved-job action, history kind, captured origin and selected-scene pricing changes, which leave the Generate row choice, the no-prompt rule, the dialog flush and the composer strings unchanged. The rebased ZIP was rerun only on macOS arm64 Blender 5.1.2, where every composer test passes. Physical HID input, IME, other OS/DPI and live generation are not established.",
    "sources": {
      "scenario/blender/props.py": "ae85f36f0e051e578466776ffff2c74f8ba70dc8b06506030aff81b6d80f3d40",
      "scenario/blender/panels.py": "6f8aa0ae9842509b1d93dc9a3e57a59ab8225b172ac577b5bf10586e12c2fc21",
      "scenario/blender/composer/state.py": "5927141c8725d5cd80323a25b52bda60dd5950948169f9488c5e27e4f7b42763",
      "scenario/blender/composer/draw.py": "4806dd6d6972920493ed90adf98aba673814abf525affad7bd4234579180a8a9",
      "scenario/blender/composer/modal.py": "027be2cf79c1dd8d22df65889319d7eced5251b5e71d425a927fee42ce211593",
      "scenario/core/ui/composer_layout.py": "cca5f608aeb8648ec8ee91de5d38dcbccbd08f280818cfde7bd703afb12da592",
      "tests/blender/test_composer.py": "d8e879cb60eabb28febed0154974b121b54990c73a75d6c8c1606cddc7c47b37",
      "tests/blender/test_studio_view.py": "d65762fbbcf6ce9dd63356097697c30b9b22a8fb07bec0866c3ae64e79ad8c7c"
    }
  }
}
---

# Composer form lane in 3D Edit mode

Supports the floating composer section of the [user guide](../../USER_GUIDE.md#the-floating-composer):
the 3D tab in Edit mode shows, prices and generates the Edit 3D form, and text
typed in the composer stays in the form it was typed into.
