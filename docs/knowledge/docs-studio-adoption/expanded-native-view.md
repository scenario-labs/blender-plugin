---
{
  "type": "Evidence",
  "id": "docs-studio-adoption.expanded-native-view",
  "title": "Explicit expanded native Studio view",
  "evidence": {
    "path": "docs/STUDIO_ADOPTION.md",
    "scope": "expanded-native-view",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-09",
    "base_revision": "afc40209d5a3bf86b30ac01e99e75d513a2b8e64",
    "limits": "Reviewed explicit native popup, unsaved navigation, shared panel drawing, guarded composer flush and outside-click passthrough. Installed synthetic tests cover quote/form/scene ownership, continued work and click handoff. Exact-ZIP offline macOS arm64 Blender 5.1.2 desktop evidence covers Unicode prompt handoff/editing, populated-form scrolling, quote-preserving page navigation, continued saved-job polling, small-window fit at UI scale 2.0, Escape and viewport return. The successful repeat exited cleanly with unchanged normal profile; an earlier shortcut-triggered exit hit fixture cleanup failure. Alternate DPI and IME composition remain unverified acceptance follow-ups under #66, not draft blockers for this scoped PR. Workflow/library forms and complete retained Studio/compact/release acceptance remain separate. No live service, upload or paid generation. Shared focused-prompt guard now also runs before modal blur, with installed regressions for changed prompt/lane/scene and unfocused stale text. Fixed ZIP 15f730160c62c2e7a700b25ac6c8a7a1d134122c30ef3e5c85842912c463777b passes 1,088 tests on each supported Blender version on macOS arm64. Its desktop attempt did not produce visible input effects, so earlier physical-input evidence remains tied to the preceding ZIP.",
    "sources": {
      "docs/STUDIO_ADOPTION.md": "3522cb894a410d7aef37c2c47edcdb7ddf37771ede1082b5c179fffb14979bad",
      "scenario/blender/studio.py": "504005a858f052419ac3fccca29a0d12f1830f6e0c515229297861aaf546545d",
      "scenario/blender/registry.py": "5ecf514d4b3eb13b38ac71b178179be898650c73c7261cfa4c971cad7dbb271c",
      "scenario/blender/popover.py": "7366e3dd7f5ad9414d9ad9e3246c072beef207f6edfbc6705488210fa1dbee35",
      "scenario/blender/composer/state.py": "063ea956a996356b7dd1b28cc16b7dc4aaa1806a9336efe7d0d79052afbf5f79",
      "scenario/blender/panels.py": "0ea312ede072b4e25c8177120214d404b449ea60db10c02edd12ad5eb985d989",
      "tests/blender/test_studio_view.py": "e2e8e0a53ad5f7def6b2c03b3061110bc6cb3f370307035ecf2370792aafcffb",
      "tests/blender/test_workflow_commands.py": "dcae5af50aa9e4530d734d84e578bf417c0816f14a98fac1b33e830161bb3e85",
      "tools/desktop_review.py": "91db1219a8fa78cb77d4297a7556a47e677975001b2860234c82fa741e1c14e1",
      "scenario/blender/composer/modal.py": "362aa797f4f52a8e8e320a024f64bd187eab39cdc32fbc8f26c03d4d168daebb",
      "tools/desktop_review_scene.py": "40d0cdf90289a286c44e70dc4d3ea5ad70337a849c7d578f161de2933f9bdfc8"
    }
  }
}
---

Evidence for [the canonical guide](../../STUDIO_ADOPTION.md).
