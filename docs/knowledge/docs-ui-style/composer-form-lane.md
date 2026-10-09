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
    "limits": "Source-reviewed the composer tab, prompt mirror, model chip, price label, status line, enablement and Generate/Enter dispatch, the sidebar Edit form's Generate row and the Generate operator's lane mapping. Before the change, installed tests on Blender 5.1.2 macOS arm64 showed a 1.5 CU Text price and Text model while Generate charged the Edit form's own 7.25 CU quote, a Text-only price enabling the composer, and a permanently disabled Edit form Generate row. Installed tests now run the real composer draw function with recording drawing primitives and the real modal handler, operator and offline SDK transport. They cover the displayed Edit price, model, placeholder and prompt; the Edit quote being consumed while the Text quote is untouched; Enter; a disabled button with only a Text price; a rejected submission keeping the modal handler alive; prompt flush across a mode switch; model chip and Settings dispatch; and the sidebar Edit form. Pixel output, desktop pointer/keyboard/focus interaction, other OS/DPI and live pricing are not established.",
    "sources": {
      "scenario/blender/props.py": "511b333e2bb5359235ab6883ed232e55048eb91e740b1db675e9e37e930ea5a8",
      "scenario/blender/operators.py": "f59b9ccd5295e9f2bbac08ad883bd549f52c113142d7f3d22cd45a8e3ff1f87c",
      "scenario/blender/panels.py": "483c4334ca74eb40a753115180ea082ee731ae4bf430d35563d8ef5dbb4651bb",
      "scenario/blender/pump.py": "86f5c8416f58b2d83ec525fb350e555c0a9631cc34cdd119d9172dfc41fe7a15",
      "scenario/blender/composer/state.py": "4eb460283dba15ed11654dca107688490e75c70ca65b0a4aee060e2410282603",
      "scenario/blender/composer/draw.py": "ef2815fc1b2aa352abea72950ebc4861c69e0dcb3e25f11d5f6cd1c91e4046b5",
      "scenario/blender/composer/modal.py": "4aaac614b5d5787eb5c0f05e966cbe23a4a2691e675a2f15669ceab687aa2701",
      "scenario/core/ui/composer_layout.py": "385cc25b9181c39bb81bf6aa2251fada4201cc4564f31f334b75241e7b43a5b0",
      "tests/blender/test_composer.py": "b2d642f835d752dabd0fb1f77c3bdb3e3b3332e127eace0201ba6ad26a1c305b",
      "tests/blender/test_model_generation.py": "128515afe6ee019c4d359b27ab40016313722c223255e05da172bd6d8ed22038",
      "tests/unit/test_composer_layout.py": "c78888f7f6a921d0a0878c92623c4d87d51646fd69240631872460034855f5e9"
    }
  }
}
---

# Composer form lane in 3D Edit mode

Supports the [UI style guide](../../UI_STYLE.md#buttons): with the 3D tab in Edit
mode, the composer shows, prices and submits the Edit 3D form, and a ready 3D-tab
price never labels or enables that submission.
