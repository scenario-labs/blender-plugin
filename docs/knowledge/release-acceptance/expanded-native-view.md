---
{
  "type": "Evidence",
  "id": "release-acceptance.expanded-native-view",
  "title": "Explicit expanded native Studio view",
  "evidence": {
    "path": "docs/maintenance/release-acceptance.md",
    "scope": "expanded-native-view",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-09",
    "base_revision": "afc40209d5a3bf86b30ac01e99e75d513a2b8e64",
    "limits": "Reviewed explicit native popup, unsaved navigation, shared panel drawing, guarded composer flush and outside-click passthrough. Installed synthetic tests cover quote/form/scene ownership, continued work and click handoff. Exact-ZIP offline macOS arm64 Blender 5.1.2 desktop evidence covers Unicode prompt handoff/editing, populated-form scrolling, quote-preserving page navigation, continued saved-job polling, small-window fit at UI scale 2.0, Escape and viewport return. The successful repeat exited cleanly with unchanged normal profile; an earlier shortcut-triggered exit hit fixture cleanup failure. Alternate DPI and IME composition remain unverified acceptance follow-ups under #66, not draft blockers for this scoped PR. Workflow/library forms and complete retained Studio/compact/release acceptance remain separate. No live service, upload or paid generation.",
    "sources": {
      "docs/maintenance/release-acceptance.md": "9810d05da6c11e2ce09771c98f03d0de330de4382db07c7e55096ba951cb553c",
      "scenario/blender/studio.py": "c2cabbeaf881c59e4139dbaa9f17f63d2efc3bf9446d5c8672425902b5ecc764",
      "scenario/blender/registry.py": "5ecf514d4b3eb13b38ac71b178179be898650c73c7261cfa4c971cad7dbb271c",
      "scenario/blender/popover.py": "7366e3dd7f5ad9414d9ad9e3246c072beef207f6edfbc6705488210fa1dbee35",
      "scenario/blender/composer/state.py": "1dda3de8748993fd75cc94fb20a0f08d303051f02e61ce72ff6837a12c025f7a",
      "scenario/blender/panels.py": "0ea312ede072b4e25c8177120214d404b449ea60db10c02edd12ad5eb985d989",
      "tests/blender/test_studio_view.py": "505fe86a65b7d605f9d0aa6fd0939649aca127f963599c905f6f6c9e6d4a9bcd",
      "tests/blender/test_workflow_commands.py": "dcae5af50aa9e4530d734d84e578bf417c0816f14a98fac1b33e830161bb3e85",
      "tools/desktop_review.py": "91db1219a8fa78cb77d4297a7556a47e677975001b2860234c82fa741e1c14e1",
      "scenario/blender/composer/modal.py": "de2e25d1e4b601b8ca42e0028345b0744745cb702bf667669983b5a4eee95412",
      "tools/desktop_review_scene.py": "40d0cdf90289a286c44e70dc4d3ea5ad70337a849c7d578f161de2933f9bdfc8"
    }
  }
}
---

Evidence for [the canonical guide](../../maintenance/release-acceptance.md).
