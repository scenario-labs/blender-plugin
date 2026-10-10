---
{
  "type": "Evidence",
  "id": "docs-world-application.world-candidates",
  "title": "Saved World candidates and numbering",
  "description": "Which saved results the World action offers and how its buttons are numbered.",
  "evidence": {
    "path": "docs/WORLD_APPLICATION.md",
    "scope": "world-candidates",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-10",
    "base_revision": "33d00b0554151c4de04731fd1a5e5c64ed50855b",
    "limits": "Inspected World candidate selection. ModelJobs.actions, the projected world_assets list, prepare_world_application and job_recovery.draw_controls share panorama.world_candidate, which keeps PNG, JPEG and OpenEXR media types and excludes saved results whose metadata declares a texture role. Each Set panorama as World (N) button numbers a candidate by its position among all results, as Import model (N) and the strip actions do. Headless native tests reproduce a 3D package (GLB, PBR maps and one unmapped image) and a texture set, including refused MCP World preparation for a map; a unit test covers the predicate. A free read of a live 3D package on 2026-10-10 showed its four PNG maps declaring texture roles at 2048x2048. The saved job records no image dimensions, so an ordinary image without a role is still offered and fails during application; a dimension-based offer needs saved dimensions. No desktop interaction review of the changed buttons, other OS, paid generation, #98 completion or release acceptance.",
    "sources": {
      "scenario/core/scene/panorama.py": "3680feac102599bf04bf5b0e6a7a63f0d292c9536f9833848ba5217c8619a890",
      "scenario/core/jobs/result_metadata.py": "87921d743217e5c81ddd1c11dcade42aef15c4aeed6d2a1189391c94f940153c",
      "scenario/blender/model_jobs.py": "145048eb71c3a8f3893f8eded431557917e7c873caf9cd1561a812440a19e596",
      "scenario/blender/job_recovery.py": "4d611336b38544d9f6edbd1391ce37c8b7edba44dc3ce9b4ea1be6458186291e",
      "scenario/mcp/tools_scenario.py": "27ca5858dbd4374c3ec0c768d0042aa9967b33dfcbaccad65fe2f7c3ea5c2454",
      "tests/unit/test_panorama.py": "0b2006c19f9ce2edf276579d77745011664edaebfe4dc2d962b7b2dc1b03188a",
      "tests/blender/test_model_generation.py": "045008a3ff3c60059d647afe673473d930d0ee3aa274d80bdc0810d7ab1f06b1"
    }
  }
}
---

# Saved World candidates and numbering

Evidence for [the canonical document](../../WORLD_APPLICATION.md).
