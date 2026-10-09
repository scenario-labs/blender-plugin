---
{
  "type": "Evidence",
  "id": "docs-ui-style.composer-form-lane",
  "title": "Composer form lane in 3D Edit mode",
  "evidence": {
    "path": "docs/UI_STYLE.md",
    "scope": "composer-form-lane",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-09",
    "base_revision": "fb699b8555f7cee62147794516cc7aaa224864f7",
    "limits": "Source-reviewed the composer tab, prompt mirror and commit guard, model chip, price label, status line, enablement, Generate/Enter/Esc/collapse/drag dispatch, the Settings and model chip flush, the no-prompt placeholder, the sidebar and Settings Edit form, the Generate operator and the model picker's model-to-form mapping. Rechecked after rebasing onto main's model description status and retry, material guidance and picker thumbnail changes, which leave the lane rule and its callers unchanged. Run against the base product code on macOS arm64 Blender 5.1.2, the installed composer tests report 16 failures and 2 errors: the card showed the Text form's 1.5 CU price and that quote enabled its Generate while the operator routes the 3D tab in Edit mode to the Edit form's 7.25 CU quote, the sidebar Edit Generate stayed disabled for its own quote, the model chip picked for the 3D-tab form, Settings and the model chip opened their dialogs with the prompt still focused, and keys typed after a mode switch still edited the Text prompt. Installed tests now run the real composer draw function with recording drawing primitives and the real modal handler, operator and offline SDK transport; the exact ZIP 89c07a5b0642ca02b53d5c1fcb57968f03fde32b3ae942ac7f048690f9272011 passes 1,176 installed tests on each macOS arm64 Blender 5.0.1, 5.1.2 and 5.2.1. A private offline GUI check ran that ZIP in an isolated profile on the same three versions through Blender's event queue (--enable-event-simulate, window without focus, no OS input injected), recorded prompts and screenshots after each step, saw no network activity and left the normal profile unchanged. Offline, no price was ready and the Settings dialog showed its loading state, so the mode switch was a property change while it was open, and Generate could not submit. The blur click's missing viewport selection was observed on an unchanged code path. A lane tab click keeps a focused prompt: it can leave a replaced form without Esc and show a focused field for a model that takes no prompt; neither path is covered. Physical HID keyboard/pointer input, IME, focus across applications, other OS/DPI, live pricing and paid submission are not established.",
    "sources": {
      "scenario/blender/props.py": "46a827a761bf326d07c93da34a92a8ae64563d9ece17b94c592ab5b33079b920",
      "scenario/blender/operators.py": "6245f4125a49c3a8d6c461cbf8caee0bf713057b9d3835fb8cab496da6364be3",
      "scenario/blender/panels.py": "aad54275f97ce8645f79863bd0ef55a8a964ca7ceaeecf25fa1f97532a948338",
      "scenario/blender/pump.py": "86f5c8416f58b2d83ec525fb350e555c0a9631cc34cdd119d9172dfc41fe7a15",
      "scenario/blender/model_picker.py": "28640e2b99044c33a546fb8d9f721842bd4deca02f7941253f6378ff384c0498",
      "scenario/blender/composer/state.py": "5927141c8725d5cd80323a25b52bda60dd5950948169f9488c5e27e4f7b42763",
      "scenario/blender/composer/draw.py": "d12422eac4229e10bdc5d722890fd56cd998f4c4deec2211d7bf2a3506a80c7f",
      "scenario/blender/composer/modal.py": "c4b14d08fc0a727119cc94dc72f37a011f60c6eddca5531b3c641731dd6c91a6",
      "scenario/core/ui/composer_layout.py": "ff162716a0f456f391152ae638eb5457107edb7bace6a906f0a85eaadf88d0b1",
      "tests/blender/test_composer.py": "0bb5e1b317627d05efa4aad9261e32a043d3c7e05e566dcfee5e6d1361921c23",
      "tests/blender/test_model_generation.py": "128515afe6ee019c4d359b27ab40016313722c223255e05da172bd6d8ed22038",
      "tests/unit/test_composer_layout.py": "d1537847fbd611b35a402c88fac4f26267c6f4d38cd8c582f1af563688e6b77c"
    }
  }
}
---

# Composer form lane in 3D Edit mode

Supports the [UI style guide](../../UI_STYLE.md#buttons): with the 3D tab in Edit
mode, the composer shows, prices and submits the Edit 3D form, a ready 3D-tab
price never labels or enables that submission, and a focused prompt never writes
into a form that replaced the one it was synchronized from.
