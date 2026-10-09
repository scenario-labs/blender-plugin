---
{
  "type": "Evidence",
  "id": "docs-user-guide.composer-form-lane",
  "title": "Composer form lane in 3D Edit mode",
  "evidence": {
    "path": "docs/USER_GUIDE.md",
    "scope": "composer-form-lane",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-09",
    "base_revision": "fb699b8555f7cee62147794516cc7aaa224864f7",
    "limits": "Reviewed the floating composer paragraph's 3D Edit mode, replaced-form and no-prompt statements against the composer state, draw and modal code, the Settings and model chip flush, the lane tab and double-click focus rules, the 3D Settings dialog and the Edit form's Generate row. Installed tests on macOS arm64 Blender 5.0.1, 5.1.2 and 5.2.1 cover the displayed Edit model, prompt and price, Generate/Enter submission of the Edit quote, the disabled state without an Edit price, refused typing, Esc, Enter, Generate and a lane tab after a replacement, a refused outside click (the guarded flush that test_composer.py checks after a mode switch and test_studio_view.py drives through the modal handler after a lane change), a double-click that keeps the original text, the dialogs' flush, the no-prompt placeholder, a lane tab to a form without a prompt and a model without a prompt loaded under a focused prompt. A private offline event-queue GUI check on the same versions, without OS input, covers the earlier interactions on a ZIP built before the lane tab, double-click and model-change rules. Other statements in that paragraph, including the Settings route to Edit mode, keep their own topics' limits. Rechecked after rebasing onto main's model description status and retry, material guidance and picker thumbnail changes, which leave the lane rule and its callers unchanged. Rechecked after merging main's handbook changes, which add the Settings route to Edit mode to that paragraph and an outside-click sentence to the next one, and main's sidebar status wrapping and job strip geometry, which leave the Generate row choice, the no-prompt rule and the composer strings unchanged. Physical HID input, IME, other OS/DPI and live generation are not established.",
    "sources": {
      "scenario/blender/props.py": "46a827a761bf326d07c93da34a92a8ae64563d9ece17b94c592ab5b33079b920",
      "scenario/blender/panels.py": "0377a9f6d77bd6667db907ff46ed1b2d460e020de6e25cc91d6594080fde8be7",
      "scenario/blender/composer/state.py": "5927141c8725d5cd80323a25b52bda60dd5950948169f9488c5e27e4f7b42763",
      "scenario/blender/composer/draw.py": "d12422eac4229e10bdc5d722890fd56cd998f4c4deec2211d7bf2a3506a80c7f",
      "scenario/blender/composer/modal.py": "c907602659c6921205b9f06989e8c3ca5fc9168d0d1053d83181e008d240cd46",
      "scenario/core/ui/composer_layout.py": "2b44792ff7ad509e8e24c3224c2c9108a65dccd2eea6bb78778d444a72cb9f1f",
      "tests/blender/test_composer.py": "8c2a944a24091247b17cfb6f72f96353980ab5584563cac96ceea0c1c79f8f73",
      "tests/blender/test_studio_view.py": "1e763f4c22eecaece1be36def00d565460d68dd424f4aad6c09ee8b90db16625"
    }
  }
}
---

# Composer form lane in 3D Edit mode

Supports the floating composer section of the [user guide](../../USER_GUIDE.md#the-floating-composer):
the 3D tab in Edit mode shows, prices and generates the Edit 3D form, and text
typed in the composer stays in the form it was typed into.
