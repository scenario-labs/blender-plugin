---
{
  "type": "Evidence",
  "id": "docs-film-plan.film-shot-scenes",
  "title": "Native Film shot and timeline construction",
  "evidence": {
    "path": "docs/FILM_PLAN.md",
    "scope": "film-shot-scenes",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-04",
    "base_revision": "4589f22964cc9cf99e53ec37bb8c5dbe6948c96b",
    "limits": "Source-reviewed native shot/timeline primitives: validated recipe geometry and camera motion, receipt-bound independent animated GLB actors, new-data rollback and exact editorial scene-strip timing. Synthetic installed tests cover scene/context preservation, animation evaluation, malformed/tampered sources and deleted/foreign scenes. No native/MCP builder registration, scoped Film task selection, application claims, desktop motion acceptance, capture/encoding, finishing/export, live provider acceptance or release authorization is established. Motion/NLA choreography adapts the selected first-party Studio source; the shared model importer supplies receipt and embedded-resource checks.",
    "sources": {
      "scenario/blender/film_scene.py": "97f4502fa9fd6a7768733fc76d84e096b8424e90115aa5446d9a1e76c72b9035",
      "scenario/blender/model_application.py": "ae730d74dacc8fee03fe31401e125e4ae3d2c1c5622364d5ba6669433c9d2cf0",
      "scenario/blender/shot_planner.py": "1a332a637731b63baeb9e46f9df62c316e441794ea82dd9ea6b6d2496a5018e0",
      "scenario/core/scene/film_plan.py": "fea102d507d3544c5ccfa1b89a04743339f88ecbfd65e5aa84384399ae5efa95",
      "scenario/core/scene/film_scene_plan.py": "1451035b64cd07814b890c63357da867b0a7649dca494913d054a491397636a2",
      "tests/blender/test_film_scene.py": "319165c468af1aa8e8f4d31e26a89f309b2977ead9e2535f30aca021ee1b17da",
      "tests/blender/helpers.py": "e5f6937be429c970101f5a12b54e2188ba03772af6805211e9bf9dc98cd928a9"
    }
  }
}
---

Source evidence for [the canonical guide](../../FILM_PLAN.md).
