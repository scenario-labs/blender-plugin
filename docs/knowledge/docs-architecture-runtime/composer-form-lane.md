---
{
  "type": "Evidence",
  "id": "docs-architecture-runtime.composer-form-lane",
  "title": "Shared Edit 3D form lane rule",
  "evidence": {
    "path": "docs/architecture/runtime.md",
    "scope": "composer-form-lane",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-09",
    "base_revision": "b57c398f35fb2148c82fb8b26f6a40564d3f52ef",
    "limits": "Inspected the shared lane rule and its callers: the pricing pump's visible lane, the sidebar and Settings form choice, the composer state, draw and modal handler and the Generate operator, plus the model picker's model-to-form mapping and the composer's commit guard. Lane-bound quote validation and durable submission in generation.py and model_jobs.py are unchanged. Installed offline tests on macOS arm64 Blender 5.0.1, 5.1.2 and 5.2.1 cover the Edit quote being consumed by the composer while a ready 3D-tab quote is left untouched, no request when only the 3D-tab price is ready, and no write or request after the form behind a focused prompt changed. No live provider pricing, physical desktop input or release acceptance is claimed.",
    "sources": {
      "scenario/blender/props.py": "46a827a761bf326d07c93da34a92a8ae64563d9ece17b94c592ab5b33079b920",
      "scenario/blender/operators.py": "f59b9ccd5295e9f2bbac08ad883bd549f52c113142d7f3d22cd45a8e3ff1f87c",
      "scenario/blender/panels.py": "abe7bc63bf56e039078cbaa0b12e3843d8e1bab5bbff107e721693475efd7ec5",
      "scenario/blender/pump.py": "86f5c8416f58b2d83ec525fb350e555c0a9631cc34cdd119d9172dfc41fe7a15",
      "scenario/blender/model_picker.py": "d5e9a5ddd15899aac0d0e35b03754687430bc80e3e85a77ffb0cfbe2620a2fb0",
      "scenario/blender/composer/state.py": "5927141c8725d5cd80323a25b52bda60dd5950948169f9488c5e27e4f7b42763",
      "scenario/blender/composer/draw.py": "364718a446857458b2cf8de2adfe121a1e8b6d7400c73e66b983a70ac65c0701",
      "scenario/blender/composer/modal.py": "c4b14d08fc0a727119cc94dc72f37a011f60c6eddca5531b3c641731dd6c91a6",
      "tests/blender/test_composer.py": "0bb5e1b317627d05efa4aad9261e32a043d3c7e05e566dcfee5e6d1361921c23"
    }
  }
}
---

# Shared Edit 3D form lane rule

Evidence for the [canonical guide](../../architecture/runtime.md).
