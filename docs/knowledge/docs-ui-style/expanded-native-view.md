---
{
  "type": "Evidence",
  "id": "docs-ui-style.expanded-native-view",
  "title": "Explicit expanded native Studio view",
  "evidence": {
    "path": "docs/UI_STYLE.md",
    "scope": "expanded-native-view",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-09",
    "base_revision": "d55f21eee597284d2482780c7c93f84115a119ff",
    "limits": "Reviewed explicit native popup, unsaved navigation, shared panel drawing, guarded composer flush and outside-click passthrough. Installed synthetic tests cover quote/form/scene ownership, continued work and click handoff. Exact-ZIP offline macOS arm64 Blender 5.1.2 desktop evidence covers Unicode prompt handoff/editing, populated-form scrolling, quote-preserving page navigation, continued saved-job polling, small-window fit at UI scale 2.0, Escape and viewport return. The successful repeat exited cleanly with unchanged normal profile; an earlier shortcut-triggered exit hit fixture cleanup failure. Alternate DPI and IME composition remain unverified acceptance follow-ups under #66, not draft blockers for this scoped PR. Workflow/library forms and complete retained Studio/compact/release acceptance remain separate. No live service, upload or paid generation. Shared focused-prompt guard now also runs before modal blur, with installed regressions for changed prompt/lane/scene and unfocused stale text. Fixed ZIP 15f730160c62c2e7a700b25ac6c8a7a1d134122c30ef3e5c85842912c463777b passes 1,088 tests on each supported Blender version on macOS arm64. Its desktop attempt did not produce visible input effects, so earlier physical-input evidence remains tied to the preceding ZIP. The Studio/Library regression section separately records scoped native input on earlier ZIP 024b7654346463d89cb80e149c278254d9ac9de022447b90b1101f6d9c915351. This review preserves the merged evidence above and verifies temporary popup refresh and RNA-backed Library input choices. Earlier artifact-specific results do not establish new-head physical input, broad DPI, IME or live service acceptance.",
    "sources": {
      "docs/UI_STYLE.md": "aa3596d18ee4af19ef5858899eea134ebf953d41b09fbcc06070037ca62c8503",
      "scenario/blender/studio.py": "ccdc50f2047cbab1792b1dd2a52a2b9e0c36ba9a85c315a7794d344e06b3e544",
      "scenario/blender/registry.py": "5ecf514d4b3eb13b38ac71b178179be898650c73c7261cfa4c971cad7dbb271c",
      "scenario/blender/popover.py": "7366e3dd7f5ad9414d9ad9e3246c072beef207f6edfbc6705488210fa1dbee35",
      "scenario/blender/composer/state.py": "063ea956a996356b7dd1b28cc16b7dc4aaa1806a9336efe7d0d79052afbf5f79",
      "scenario/blender/panels.py": "0ea312ede072b4e25c8177120214d404b449ea60db10c02edd12ad5eb985d989",
      "tests/blender/test_studio_view.py": "e33f0e44cbe75cabdfa38ecd68ca991e010a4e0322803813f3464b2c9e9f7e78",
      "tests/blender/test_workflow_commands.py": "dcae5af50aa9e4530d734d84e578bf417c0816f14a98fac1b33e830161bb3e85",
      "tools/desktop_review.py": "91db1219a8fa78cb77d4297a7556a47e677975001b2860234c82fa741e1c14e1",
      "docs/images/studio-viewport-return.png": "057d74191f2eb85eaff2c91fec8a14420223225c0d7bc8e1e24243c29ecdb1a9",
      "scenario/blender/composer/modal.py": "362aa797f4f52a8e8e320a024f64bd187eab39cdc32fbc8f26c03d4d168daebb",
      "tools/desktop_review_scene.py": "40d0cdf90289a286c44e70dc4d3ea5ad70337a849c7d578f161de2933f9bdfc8",
      "docs/images/studio-prompt-handoff.png": "cd831973c7776312609d11ee7e665fe45baa213e38d085f2526e759d86df72a1",
      "docs/images/studio-composer-focused.png": "2ca0522bbae52924e951ce2a98cf6d06e91ca58fdfabc20e67a24ee12cb79e53",
      "docs/images/studio-active-job.png": "0ca3676e819fdc135a2352bfafbe8e362217eebc34848be23d4a93e44c56aded",
      "docs/images/studio-narrow-form.png": "db9f3806231cedd8e6b13eb4cefc7db95669c8539b3e0d9413ad879fbe754207",
      "scenario/blender/pump.py": "86f5c8416f58b2d83ec525fb350e555c0a9631cc34cdd119d9172dfc41fe7a15"
    }
  }
}
---

Evidence for [the canonical guide](../../UI_STYLE.md).
