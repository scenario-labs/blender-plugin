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
    "limits": "Reviewed the floating composer paragraph's 3D Edit mode, replaced-form and no-prompt statements against the composer state, draw and modal code, the Settings and model chip flush, the 3D Settings dialog and the Edit form's Generate row. Installed tests on macOS arm64 Blender 5.0.1, 5.1.2 and 5.2.1 cover the displayed Edit model, prompt and price, Generate/Enter submission of the Edit quote, the disabled state without an Edit price, refused typing, Esc, Enter and Generate after a replacement, the dialogs' flush and the no-prompt placeholder. A private offline event-queue GUI check on the same versions covers the same interactions with the exact ZIP, without OS input. Other statements in that paragraph keep their inherited limits. A lane tab click keeps a focused prompt: it can leave a replaced form without Esc and show a focused field for a model that takes no prompt; neither path is covered. Rechecked after rebasing onto main's model description status and retry, material guidance and picker thumbnail changes, which leave the lane rule and its callers unchanged. Physical HID input, IME, other OS/DPI and live generation are not established.",
    "sources": {
      "scenario/blender/props.py": "46a827a761bf326d07c93da34a92a8ae64563d9ece17b94c592ab5b33079b920",
      "scenario/blender/panels.py": "aad54275f97ce8645f79863bd0ef55a8a964ca7ceaeecf25fa1f97532a948338",
      "scenario/blender/composer/state.py": "5927141c8725d5cd80323a25b52bda60dd5950948169f9488c5e27e4f7b42763",
      "scenario/blender/composer/draw.py": "d12422eac4229e10bdc5d722890fd56cd998f4c4deec2211d7bf2a3506a80c7f",
      "scenario/blender/composer/modal.py": "c4b14d08fc0a727119cc94dc72f37a011f60c6eddca5531b3c641731dd6c91a6",
      "scenario/core/ui/composer_layout.py": "ff162716a0f456f391152ae638eb5457107edb7bace6a906f0a85eaadf88d0b1",
      "tests/blender/test_composer.py": "0bb5e1b317627d05efa4aad9261e32a043d3c7e05e566dcfee5e6d1361921c23"
    }
  }
}
---

# Composer form lane in 3D Edit mode

Supports the floating composer section of the [user guide](../../USER_GUIDE.md#the-floating-composer):
the 3D tab in Edit mode shows, prices and generates the Edit 3D form, and text
typed in the composer stays in the form it was typed into.
