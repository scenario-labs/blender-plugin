---
{
  "type": "Evidence",
  "id": "docs-ui-style.repeat-generation",
  "title": "Generate again after a confirmed job",
  "evidence": {
    "path": "docs/UI_STYLE.md",
    "scope": "repeat-generation",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-13",
    "base_revision": "d3e6589fa7df0e49de39696c2fbaae591daa0c22",
    "limits": "Reviewed the in-memory per-scene, per-lane repeat after Generate: the last price stays on the sidebar and composer button, no quote is requested while the submission is still being sent, a fresh free quote follows its confirmation, Generate and the composer's Enter stay disabled until the 2 s delay passed, an edit drops the repeat for normal pricing, and a lost submission re-prices into the duplicate refusal. Installed Blender 5.1.2 macOS arm64 tests drive the pump, labels and enablement; no screenshot, physical click timing or live service run is established.",
    "sources": {
      "scenario/blender/generation.py": "033b2d4f091f23355d105c5e214806a274a6a27a8f8f5c12a1fd9dd8973daa59",
      "scenario/blender/pump.py": "d3436568482e3a0aa4f5e06243591d5d69ab282cd0e7edf17076e62252666568",
      "scenario/blender/panels.py": "dae2c8208afb394dc1c4673facbc5de653972ef7fe0f5b3a5c4848c2c1092f15",
      "scenario/blender/runtime.py": "4b953ccef0d00d1dded484440e88a54c3e1f28b6f7063e2554a01cc261ab0f98",
      "scenario/blender/props.py": "184cbc93187f403e3241e80156d72ff9ef84f33056bb9f8a8d52b7ededaa7d66",
      "scenario/blender/composer/draw.py": "ea4802e13778af19546d14c0c974ddb745063658b26fb55232872f6dc0a01076",
      "scenario/blender/composer/modal.py": "45104e3c6c7081ef6b969551c2c04387524595f23ff8ce4bcbb70dea7e52957a",
      "scenario/core/jobs/coordinator.py": "50f3725c3f8e66613de22f9892d36816f07e9d17ede9eda8fe3369d5813e0ca3",
      "tests/blender/test_model_generation.py": "bfda97d359ecc45484d75e95b9c047a8b37ae34ec6ad73edb2e4e5fe14aca311"
    }
  }
}
---

# Generate again after a confirmed job

Evidence for [the canonical guide](../../UI_STYLE.md).
