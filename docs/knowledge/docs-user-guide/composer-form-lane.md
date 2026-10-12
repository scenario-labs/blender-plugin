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
    "limits": "Reviewed the floating composer paragraph's 3D Edit mode, replaced-form and no-prompt statements against the composer state, draw and modal code, the Settings and model chip flush, the lane tab and double-click focus rules, the 3D Settings dialog and the Edit form's Generate row. Installed tests on macOS arm64 Blender 5.0.1, 5.1.2 and 5.2.1 cover the displayed Edit model, prompt and price, Generate/Enter submission of the Edit quote, the disabled state without an Edit price, refused typing, Esc, Enter, Generate and a lane tab after a replacement, a refused outside click (the guarded flush that test_composer.py checks after a mode switch and test_studio_view.py drives through the modal handler after a lane change), a double-click that keeps the original text, the dialogs' flush, the no-prompt placeholder, a lane tab to a form without a prompt and a model without a prompt loaded under a focused prompt. A private offline event-queue GUI check on the same versions, without OS input, covers the earlier interactions on a ZIP built before the lane tab, double-click and model-change rules. Other statements in that paragraph, including the Settings route to Edit mode, keep their own topics' limits. Rechecked after rebasing onto main's model description status and retry, material guidance and picker thumbnail changes, which leave the lane rule and its callers unchanged. Rechecked after merging main's handbook changes, which add the Settings route to Edit mode to that paragraph and an outside-click sentence to the next one, and main's sidebar status wrapping and job strip geometry, which leave the Generate row choice, the no-prompt rule and the composer strings unchanged. Rechecked after rebasing onto main's overlapping-sidebar composer, which adds the dragging, short-label and no-room sentences to that paragraph and ends a focused prompt without writing a replaced form when the card gives way to the pill (an exit the paragraph does not list), and main's saved-job action, history kind, captured origin and selected-scene pricing changes, which leave the Generate row choice, the no-prompt rule, the dialog flush and the composer strings unchanged. Rechecked after rebasing onto main's composer double-click pairing and whole-viewport clamp, World candidates and history paging, workflow step decisions, trained model routes and defaults, saved result previews, workflow input uploads, original result assets and upload staging cleanup: main adds the viewport-edge and whole-card sentences to that paragraph, and a paired press selects a word of a replaced form's original text and does not focus a field without a prompt, which an installed test now covers; the sidebar only changes its history rows, so the paragraph's Edit form, replaced-form and no-prompt statements, the Generate row choice and the dialog flush are unchanged. The rebased ZIP was rerun only on macOS arm64 Blender 5.1.2, where every composer test passes. Physical HID input, IME, other OS/DPI and live generation are not established. Rechecked after the composer session lifetime change: modal.py only gains a wrapper that ends the session when modal raises and a cancel callback, and test_composer.py only gains lifetime and file-load tests, so the lane rule, its callers, the commit guard and the Generate dispatch are unchanged; every installed composer test passes on macOS arm64 Blender 5.1.2.",
    "sources": {
      "scenario/blender/props.py": "ae85f36f0e051e578466776ffff2c74f8ba70dc8b06506030aff81b6d80f3d40",
      "scenario/blender/panels.py": "6ebb4781ff62c6a155bc1db067a40eb33f6107cd34325d040fac3c877d0cbde6",
      "scenario/blender/composer/state.py": "943d2b3410966c62a00ef7b4a3251a66727f761e5b556e91565ec29d22c50ed4",
      "scenario/blender/composer/draw.py": "4806dd6d6972920493ed90adf98aba673814abf525affad7bd4234579180a8a9",
      "scenario/blender/composer/modal.py": "968819bc3ec818fd5e7afe8ebe801832c66b65556251366da456d2043171a27e",
      "scenario/core/ui/composer_layout.py": "69781a9e870670fbc95cf16b82f8337be24a1f3eeadf60dd1f4a654227124a1a",
      "tests/blender/test_composer.py": "6eadb29d4e7bf1e975e541ad2396768591132876bcea9f4ae268106e4a4ae777",
      "tests/blender/test_studio_view.py": "d65762fbbcf6ce9dd63356097697c30b9b22a8fb07bec0866c3ae64e79ad8c7c"
    }
  }
}
---

# Composer form lane in 3D Edit mode

Supports the floating composer section of the [user guide](../../USER_GUIDE.md#the-floating-composer):
the 3D tab in Edit mode shows, prices and generates the Edit 3D form, and text
typed in the composer stays in the form it was typed into.
