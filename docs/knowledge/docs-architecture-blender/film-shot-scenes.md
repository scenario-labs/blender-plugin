---
{
  "type": "Evidence",
  "id": "docs-architecture-blender.film-shot-scenes",
  "title": "Native Film shot and timeline construction",
  "evidence": {
    "path": "docs/architecture/blender.md",
    "scope": "film-shot-scenes",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-07",
    "base_revision": "5c89611767b1f9dec869493941730145d56c3d65",
    "limits": "Source-reviewed native shot/timeline primitives: validated recipe geometry and camera motion, receipt-bound independent animated GLB actors, new-data rollback and exact editorial scene-strip timing. Synthetic installed tests cover scene/context preservation, animation evaluation, malformed/tampered sources and deleted/foreign scenes. No native/MCP builder registration, scoped Film task selection, application claims, desktop motion acceptance, capture/encoding, finishing/export, live provider acceptance or release authorization is established. Motion/NLA choreography adapts the selected first-party Studio source; the shared model importer supplies receipt and embedded-resource checks. Follow-up regressions measure evaluated armature/morph bounds and align action stops with motion at 24/30/60 fps. Hero size validation permits one proportional dimension or neither and rejects width plus height before import or scene mutation; unit and native regressions cover that boundary.",
    "sources": {
      "scenario/blender/film_scene.py": "b4193e062049de8287d830e6e6e5ea74e5a15ef1e88d213255c74b0f951ecaa8",
      "scenario/blender/model_application.py": "ae730d74dacc8fee03fe31401e125e4ae3d2c1c5622364d5ba6669433c9d2cf0",
      "scenario/blender/shot_planner.py": "1a332a637731b63baeb9e46f9df62c316e441794ea82dd9ea6b6d2496a5018e0",
      "scenario/core/scene/film_plan.py": "ac5350c7b052038dc8e31bbd614f70cfe44a0858df0c325f9ee07f06e44d1321",
      "scenario/core/scene/film_scene_plan.py": "1451035b64cd07814b890c63357da867b0a7649dca494913d054a491397636a2",
      "tests/blender/test_film_scene.py": "a08877da524836fd2ffbddced2f89655a5f0a7960960913aa5eae7231533c056",
      "tests/blender/helpers.py": "e5f6937be429c970101f5a12b54e2188ba03772af6805211e9bf9dc98cd928a9",
      "tests/unit/test_film_plan.py": "a5030609dafa4105b1e2d6fd065072ddfedaba308e073c8295332fcbd7a245a5"
    }
  }
}
---

Source evidence for [the canonical guide](../../architecture/blender.md).
