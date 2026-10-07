---
{
  "type": "Evidence",
  "id": "docs-ui-style.expanded-native-view",
  "title": "Explicit expanded native Studio view",
  "evidence": {
    "path": "docs/UI_STYLE.md",
    "scope": "expanded-native-view",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-07",
    "base_revision": "d18a95212410a8babc37145b4ff2007e5e2cc011",
    "limits": "Reviewed the explicit native popup, unsaved navigation, shared native panel drawing and guarded composer flush. Installed synthetic tests cover quote/form/scene ownership and continued admitted work. The desktop application was launched in an isolated profile, but CUA returned cgWindowNotFound before pointer/keyboard actions or screenshots. Physical input, visual layout, dismissal, small-window, DPI and Unicode/IME acceptance are not established; the UI PR remains draft. Workflow/library forms and complete retained Studio/compact/release acceptance remain separate. No live service call, upload or paid generation is included.",
    "sources": {
      "docs/UI_STYLE.md": "ae970bfd39e1ef2c5701c15afd7b1a64aa41f06554d01ade249fd9651914a044",
      "scenario/blender/studio.py": "c2cabbeaf881c59e4139dbaa9f17f63d2efc3bf9446d5c8672425902b5ecc764",
      "scenario/blender/registry.py": "5ecf514d4b3eb13b38ac71b178179be898650c73c7261cfa4c971cad7dbb271c",
      "scenario/blender/popover.py": "7366e3dd7f5ad9414d9ad9e3246c072beef207f6edfbc6705488210fa1dbee35",
      "scenario/blender/composer/state.py": "1dda3de8748993fd75cc94fb20a0f08d303051f02e61ce72ff6837a12c025f7a",
      "scenario/blender/panels.py": "0ea312ede072b4e25c8177120214d404b449ea60db10c02edd12ad5eb985d989",
      "tests/blender/test_studio_view.py": "a1fb335dc6b4f19715c2e3aca4db370526284260a0a760733f5b5888619f1b57",
      "tests/blender/test_workflow_commands.py": "1439fa908ec461b0ed2d2314f2e58e918bfd5bdf1b7c35ea682ab3f641c5db5f"
    }
  }
}
---

Evidence for [the canonical guide](../../UI_STYLE.md).
