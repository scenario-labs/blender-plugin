---
{
  "type": "Evidence",
  "id": "docs-architecture-runtime.expanded-native-view",
  "title": "Explicit expanded native Studio view",
  "evidence": {
    "path": "docs/architecture/runtime.md",
    "scope": "expanded-native-view",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-09",
    "base_revision": "afc40209d5a3bf86b30ac01e99e75d513a2b8e64",
    "limits": "Reviewed explicit native popup, unsaved navigation, shared panel drawing, guarded composer flush and outside-click passthrough. Installed synthetic tests cover quote/form/scene ownership, continued work and click handoff. Exact-ZIP offline macOS arm64 Blender 5.1.2 desktop evidence covers Unicode paste, first-click Studio opening, Film navigation, Escape and viewport return with unchanged normal profile. Populated forms, active-job/quote desktop journeys, small-window, alternate DPI, scrolling and IME composition remain unverified; keep the PR draft. Workflow/library forms and complete retained Studio/compact/release acceptance remain separate. No live service, upload or paid generation.",
    "sources": {
      "docs/architecture/runtime.md": "f40a24674845ad4c06858188185ced9b03a073ae6025a012ea0794767b01fbe7",
      "scenario/blender/studio.py": "c2cabbeaf881c59e4139dbaa9f17f63d2efc3bf9446d5c8672425902b5ecc764",
      "scenario/blender/registry.py": "5ecf514d4b3eb13b38ac71b178179be898650c73c7261cfa4c971cad7dbb271c",
      "scenario/blender/popover.py": "7366e3dd7f5ad9414d9ad9e3246c072beef207f6edfbc6705488210fa1dbee35",
      "scenario/blender/composer/state.py": "1dda3de8748993fd75cc94fb20a0f08d303051f02e61ce72ff6837a12c025f7a",
      "scenario/blender/panels.py": "0ea312ede072b4e25c8177120214d404b449ea60db10c02edd12ad5eb985d989",
      "tests/blender/test_studio_view.py": "505fe86a65b7d605f9d0aa6fd0939649aca127f963599c905f6f6c9e6d4a9bcd",
      "tests/blender/test_workflow_commands.py": "1439fa908ec461b0ed2d2314f2e58e918bfd5bdf1b7c35ea682ab3f641c5db5f",
      "tools/desktop_review.py": "91db1219a8fa78cb77d4297a7556a47e677975001b2860234c82fa741e1c14e1",
      "scenario/blender/composer/modal.py": "de2e25d1e4b601b8ca42e0028345b0744745cb702bf667669983b5a4eee95412",
      "tools/desktop_review_scene.py": "40d0cdf90289a286c44e70dc4d3ea5ad70337a849c7d578f161de2933f9bdfc8"
    }
  }
}
---

Evidence for [the canonical guide](../../architecture/runtime.md).
