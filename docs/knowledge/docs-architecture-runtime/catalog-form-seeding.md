---
{
  "type": "Evidence",
  "id": "docs-architecture-runtime.catalog-form-seeding",
  "title": "Catalog form seeding without scene updates",
  "evidence": {
    "path": "docs/architecture/runtime.md",
    "scope": "catalog-form-seeding",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-10",
    "base_revision": "33d00b0554151c4de04731fd1a5e5c64ed50855b",
    "limits": "Catalog, model-detail and model-restore form synchronization stores schema defaults, enum corrections and restored model enum indices as raw ID properties, so it runs no RNA update callback and does not tag the scene for a dependency update. A seeded form re-arms its own price in its own scene and a seeded duration still drives the camera path. Native Blender 5.1.2 probes showed that any RNA assignment to a property with an update callback tags the Scene even with an unchanged value, while plain properties, collection add/remove and raw ID property writes do not. Installed regressions cover the first load, a restored enum index, per-scene repricing, seeded duration, explicit edits that still invalidate, and an MCP approval surviving a seeding catalog load. A temporary pre/post dump of every lane field, estimate state and shot duration was identical for first load, explicit selection and reload. The Edit 3D default selection when a saved index falls outside the task list still uses RNA and stays conservative. No desktop timing, other OS or Blender series, live catalog or release acceptance is established.",
    "sources": {
      "scenario/blender/generation.py": "6fcde0ba8495a44d0c562971f3ddf8b31714bc19fec8fbe7b47145d8fb0035ab",
      "scenario/blender/params_ui.py": "bda117a82c203865b9d8edb7129f0114e1a04db7a56d44eb557ea039148fca34",
      "scenario/blender/props.py": "78c910be6224eb94d0930bfb73408646ec70782ed68fa5aca444d98f940cdb1a",
      "scenario/blender/render_commands.py": "44b23a549f765b121de56f57476fbf6fe17402c26bc02034909c0a51794b4ef8",
      "scenario/blender/handlers.py": "699dba07a70d4b796f29e2e52799abb62d2ae7d0595b484c1f984f156cae1834",
      "tests/blender/test_generation.py": "27b397a4c8487f84150cdcd065f407c0fd671e7a01a994c0af04338f82fbc5d4",
      "tests/blender/test_model_generation.py": "1c1c89644d0d7881adbeaef4a73ed2e41b20c4434c2930414dc35d08cb8d74c2"
    }
  }
}
---

Evidence for the [canonical guide](../../architecture/runtime.md).
