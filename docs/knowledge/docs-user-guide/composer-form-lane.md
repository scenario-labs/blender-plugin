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
    "base_revision": "b57c398f35fb2148c82fb8b26f6a40564d3f52ef",
    "limits": "Reviewed the floating composer paragraph's 3D Edit mode statement against the composer draw/modal code, the 3D Settings dialog and the Edit form's Generate row. Installed offline tests on Blender 5.1.2 macOS arm64 cover the displayed Edit model, prompt and price, Generate/Enter submission of the Edit quote and the disabled state without an Edit price. Other statements in that paragraph keep their inherited limits. Desktop interaction, screenshots, other OS/DPI and live generation are not established.",
    "sources": {
      "scenario/blender/props.py": "511b333e2bb5359235ab6883ed232e55048eb91e740b1db675e9e37e930ea5a8",
      "scenario/blender/panels.py": "483c4334ca74eb40a753115180ea082ee731ae4bf430d35563d8ef5dbb4651bb",
      "scenario/blender/composer/state.py": "4eb460283dba15ed11654dca107688490e75c70ca65b0a4aee060e2410282603",
      "scenario/blender/composer/draw.py": "ef2815fc1b2aa352abea72950ebc4861c69e0dcb3e25f11d5f6cd1c91e4046b5",
      "scenario/blender/composer/modal.py": "4aaac614b5d5787eb5c0f05e966cbe23a4a2691e675a2f15669ceab687aa2701",
      "tests/blender/test_composer.py": "b2d642f835d752dabd0fb1f77c3bdb3e3b3332e127eace0201ba6ad26a1c305b"
    }
  }
}
---

# Composer form lane in 3D Edit mode

Supports the floating composer section of the [user guide](../../USER_GUIDE.md#the-floating-composer):
the 3D tab in Edit mode shows, prices and generates the Edit 3D form.
