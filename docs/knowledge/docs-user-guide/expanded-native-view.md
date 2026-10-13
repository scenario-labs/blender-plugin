---
{
  "type": "Evidence",
  "id": "docs-user-guide.expanded-native-view",
  "title": "Explicit expanded native Studio view",
  "evidence": {
    "path": "docs/USER_GUIDE.md",
    "scope": "expanded-native-view",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-13",
    "base_revision": "a0a0c9259535a483acff2f3d52a9e161449ececc",
    "limits": "2026-10-13: reviewed the current guide's Studio bullet in Find your way around and the Expanded Studio view introduction (header button, page names, Create, page switching, Esc or click outside, jobs continuing). Checked against scenario/blender/popover.py (the header draws Scenario, then Studio), scenario/blender/studio.py (popup operator and bounded width, PAGES and tab rows, Create drawing the sidebar SCENARIO_PT_main, Jobs and Results drawing the sidebar Jobs and Generations panels, Connection, unsaved WindowManager navigation, the focused-prompt flush before opening and the Esc or click outside label), scenario/blender/panels.py (the reused sidebar panels and tab rows), scenario/blender/composer/state.py and scenario/blender/composer/modal.py (focused-prompt flush and refusal, outside-click passthrough so the header click opens Studio), scenario/blender/pump.py (jobs advance on a timer independent of the popup, which each tick refreshes) and scenario/blender/registry.py (registration). Page names match the code, but the tabs read Create, Film, Workflows, Library, Jobs, Results, Connection, unlike the guide's list order, which was reported for correction. Installed tests in tests/blender/test_studio_view.py, with fixtures from tests/blender/test_workflow_commands.py, were read, not run: unsaved navigation, every page drawn without starting jobs or changing an exact quote, Jobs and Results reusing the sidebar rows, admitted work continuing after navigation, focused-prompt flush and conflict refusal, outside-click handoff, popup width and compact tab rows. No offline unit test covers these claims. Not verified in this review: dismissal by Esc or by clicking outside on the current build (native popup behaviour; the code only states it in a label), native input and focus, alternate DPI and IME composition (acceptance follow-ups under #66), and other OS. The Workflows, Library and Film page controls have separate evidence. Earlier (2026-10-09, exact ZIP built before the Workflows, Library and Film pages joined Studio): offline macOS arm64 Blender 5.1.2 desktop checks with tools/desktop_review.py and tools/desktop_review_scene.py covered Unicode prompt handoff, populated-form scrolling, quote-preserving page navigation, continued saved-job polling, small-window fit at UI scale 2.0, Escape dismissal and viewport return. No live service, upload or paid generation.",
    "sources": {
      "docs/USER_GUIDE.md": "d81c4fbc7ccd6fd05b987dfc9a77f191ad567cc0486b2f9983b755402bad526b",
      "scenario/blender/studio.py": "41e0e0305bb47e3c82809fdfcddf34a89406198f2745e0009cfde697575b217c",
      "scenario/blender/registry.py": "c3a880832b4cf47ce530ecea582a5c73e53c8f346d5a6521b7c023bab31cd9e3",
      "scenario/blender/popover.py": "7366e3dd7f5ad9414d9ad9e3246c072beef207f6edfbc6705488210fa1dbee35",
      "scenario/blender/composer/state.py": "1686db41dc0b10dd6a8bdbd024b05da9e1c4651f9deac7bb967d5b5ee2814a29",
      "scenario/blender/panels.py": "ed89c44a0d327f3a9de13d62f6bb44116e9ff88defdabc01e805900ee45c3d67",
      "tests/blender/test_studio_view.py": "6e9b1ccbd76ea6a9c4909bf5f72fe374988012e0573037d0ef0ed9a2a9522880",
      "tests/blender/test_workflow_commands.py": "636c2e5a69c4a7a2e4a4aceff171d939af8bddb46a57d77d297fe661bbd1e312",
      "tools/desktop_review.py": "91db1219a8fa78cb77d4297a7556a47e677975001b2860234c82fa741e1c14e1",
      "scenario/blender/composer/modal.py": "45104e3c6c7081ef6b969551c2c04387524595f23ff8ce4bcbb70dea7e52957a",
      "tools/desktop_review_scene.py": "40d0cdf90289a286c44e70dc4d3ea5ad70337a849c7d578f161de2933f9bdfc8",
      "scenario/blender/pump.py": "0c53227fe2f22b1d24963eb0a9ceaac32a35f35afc5f8cb058ee6ed0ee178dec"
    }
  }
}
---

Evidence for [the canonical guide](../../USER_GUIDE.md).
