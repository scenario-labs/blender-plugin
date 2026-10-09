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
    "base_revision": "b57c398f35fb2148c82fb8b26f6a40564d3f52ef",
    "limits": "Source-reviewed the composer tab, prompt mirror and commit guard, model chip, price label, status line, enablement, Generate/Enter/Esc/collapse/drag dispatch, the Settings and model chip flush, the no-prompt placeholder, the sidebar and Settings Edit form, the Generate operator and the model picker's model-to-form mapping. Installed tests on Blender 5.1.2 macOS arm64 reproduced, before each fix, a 1.5 CU Text price shown while Generate charged the Edit form's 7.25 CU quote, and a focused Text prompt written into the Edit form by a keystroke, Backspace, Enter, Esc or Generate after a mode switch (12 failing subtests). Installed tests now run the real composer draw function with recording drawing primitives and the real modal handler, operator and offline SDK transport; the exact ZIP d209e483e4c4a6db0283aa5a63e42ff010912a50903050c1a18ad3b7d8bbccd2 passes 1,162 installed tests on each macOS arm64 Blender 5.0.1, 5.1.2 and 5.2.1. A private offline GUI check ran that ZIP in an isolated profile on the same three versions through Blender's event queue (--enable-event-simulate, window without focus, no OS input injected), recorded prompts and screenshots after each step, saw no network activity and left the normal profile unchanged. Offline, no price was ready and the Settings dialog showed its loading state, so the mode switch was a property change while it was open, and Generate could not submit. The blur click's missing viewport selection was observed on an unchanged code path. Physical HID keyboard/pointer input, IME, focus across applications, other OS/DPI, live pricing and paid submission are not established.",
    "sources": {
      "scenario/blender/props.py": "46a827a761bf326d07c93da34a92a8ae64563d9ece17b94c592ab5b33079b920",
      "scenario/blender/operators.py": "f59b9ccd5295e9f2bbac08ad883bd549f52c113142d7f3d22cd45a8e3ff1f87c",
      "scenario/blender/panels.py": "abe7bc63bf56e039078cbaa0b12e3843d8e1bab5bbff107e721693475efd7ec5",
      "scenario/blender/pump.py": "86f5c8416f58b2d83ec525fb350e555c0a9631cc34cdd119d9172dfc41fe7a15",
      "scenario/blender/model_picker.py": "d5e9a5ddd15899aac0d0e35b03754687430bc80e3e85a77ffb0cfbe2620a2fb0",
      "scenario/blender/composer/state.py": "5927141c8725d5cd80323a25b52bda60dd5950948169f9488c5e27e4f7b42763",
      "scenario/blender/composer/draw.py": "364718a446857458b2cf8de2adfe121a1e8b6d7400c73e66b983a70ac65c0701",
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
