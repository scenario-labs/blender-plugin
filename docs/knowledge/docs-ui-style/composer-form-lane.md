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
    "limits": "Source-reviewed the composer tab, prompt mirror and commit guard, model chip, price label, status line, enablement, Generate/Enter/Esc/collapse/drag dispatch, the lane tab and double-click focus rules, the Settings and model chip flush, the no-prompt placeholder and text-key guard, the sidebar and Settings Edit form, the Generate operator and the model picker's model-to-form mapping. Rechecked after rebasing onto main's model description status and retry, material guidance and picker thumbnail changes, which leave the lane rule and its callers unchanged. Rechecked after merging main's prepared job cancellation, experimental status, Codex token, handbook, sidebar status wrapping, World panorama, trained model catalog and job strip changes: the model picker only gains a read-only experimental status label, the sidebar only wraps its status labels, the layout module only gains job strip geometry after the composer layout, and the generation fixture only gains tests and a panorama helper option, so the lane rule, the Generate row choice, the composer strings, the model-to-form mapping and the fixture's default dry-run cost are unchanged. Run against the base revision's product code on macOS arm64 Blender 5.1.2, the installed composer tests report 20 failures and 3 errors, all in the Edit form tests: the card showed the Text form's 1.5 CU price and that quote enabled its Generate while the operator routes the 3D tab in Edit mode to the Edit form's 7.25 CU quote, the sidebar Edit Generate stayed disabled for its own quote, the model chip picked for the 3D-tab form, Settings and the model chip opened their dialogs with the prompt still focused, and keys typed after a mode switch still edited the Text prompt. The lane tab, double-click and model-change rules came after the GUI check below: on the composer code that check ran, their 4 installed tests report 5 failures, one in each of 3 tests and one in each of the replaced-form test's 2 tab subtests. Installed tests run the real composer draw function with recording drawing primitives and the real modal handler, operator and offline SDK transport; the packaged ZIP built from these sources passes 1,221 installed tests on each macOS arm64 Blender 5.0.1, 5.1.2 and 5.2.1. A private offline GUI check ran the earlier ZIP 89c07a5b0642ca02b53d5c1fcb57968f03fde32b3ae942ac7f048690f9272011 in an isolated profile on the same three versions through Blender's event queue (--enable-event-simulate, window without focus, no OS input injected), recorded prompts and screenshots after each step, saw no network activity and left the normal profile unchanged; it did not exercise the lane tab, double-click or model-change rules. Offline, no price was ready and the Settings dialog showed its loading state, so the mode switch was a property change while it was open, and Generate could not submit. The blur click's missing viewport selection was observed on an unchanged code path. Physical HID keyboard/pointer input, IME, focus across applications, other OS/DPI, live pricing and paid submission are not established.",
    "sources": {
      "scenario/blender/props.py": "46a827a761bf326d07c93da34a92a8ae64563d9ece17b94c592ab5b33079b920",
      "scenario/blender/operators.py": "6245f4125a49c3a8d6c461cbf8caee0bf713057b9d3835fb8cab496da6364be3",
      "scenario/blender/panels.py": "0377a9f6d77bd6667db907ff46ed1b2d460e020de6e25cc91d6594080fde8be7",
      "scenario/blender/pump.py": "86f5c8416f58b2d83ec525fb350e555c0a9631cc34cdd119d9172dfc41fe7a15",
      "scenario/blender/model_picker.py": "951e3b936dcb76070987f18ce7886c3f2eb3f94740f860926014e867830944f6",
      "scenario/blender/composer/state.py": "5927141c8725d5cd80323a25b52bda60dd5950948169f9488c5e27e4f7b42763",
      "scenario/blender/composer/draw.py": "d12422eac4229e10bdc5d722890fd56cd998f4c4deec2211d7bf2a3506a80c7f",
      "scenario/blender/composer/modal.py": "c907602659c6921205b9f06989e8c3ca5fc9168d0d1053d83181e008d240cd46",
      "scenario/core/ui/composer_layout.py": "2b44792ff7ad509e8e24c3224c2c9108a65dccd2eea6bb78778d444a72cb9f1f",
      "tests/blender/test_composer.py": "8c2a944a24091247b17cfb6f72f96353980ab5584563cac96ceea0c1c79f8f73",
      "tests/blender/test_model_generation.py": "f1a175353a558901dbf02bf936ef4cf1ca6e613ecfe811b034a4472fe1cb828f",
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
