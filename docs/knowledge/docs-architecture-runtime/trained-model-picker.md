---
{
  "type": "Evidence",
  "id": "docs-architecture-runtime.trained-model-picker",
  "title": "Trained-model catalog load and picker reads in the active SDK catalog",
  "evidence": {
    "path": "docs/architecture/runtime.md",
    "scope": "trained-model-picker",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-10",
    "base_revision": "33d00b0554151c4de04731fd1a5e5c64ed50855b",
    "limits": "Reviewed the trained-model sentences of the active SDK catalog paragraph: generation.request_catalog queues the private trained list read with the public catalog through trained_models.request, the picker's Trained chip starts base description reads on demand (trained_models.request_bases, and from a delivered list only while model_picker.trained_view_open), local MCP list_models with the trained source starts the same reads and lists the same rows (topic docs-architecture-runtime.trained-models-mcp), and model_filter and catalog.models_for_lane keep LoRAs, compositions and other trained types out of the lane lists and the other chips while private custom models that reach them stay listed. Retirement clears the trained state with the catalog (generation.clear_catalog calls trained_models.clear; RuntimeState holds the trained fields). Other claims of the paragraph keep their own topic. The installed suite on macOS 27.0.1 arm64, Blender 5.1.2, Python 3.13.9 passed 1,266 tests (OK, 2 Windows-only skips) with ZIP sha256 e62f0acc496aef67a835b014532c94326220640c541d130fe5a36a4632efb9d6, whose 148 Python files match git archive of the reviewed fix commit, including the 12 tests of tests/blender/test_mcp_trained_models.py against the socket-free synthetic service of tests/blender/test_trained_models.py (captured public FLUX.1 Dev and Z-Image bases and public trained fixtures plus synthetic private records; submissions answered only by that service where a test opts in). Re-checked on 2026-10-10 after the MCP fix commit (ensure_record, apply_picks, placement_error, _described and model_schema/_body_for): request_catalog, clear_catalog, request_bases and list_models are unchanged; the claims above still hold. Not established: Blender 5.0 and 5.2, Linux and Windows runs; a session with a real MCP client; live reads, dry runs or paid runs; private LoRAs and compositions against the service; result quality.",
    "sources": {
      "docs/architecture/runtime.md": "9ee1eaf6ac0933c8345962404275c319dee768c598152ba48cd07754c9d14b0b",
      "scenario/blender/generation.py": "17c12bf4ee35dd3e0f15b5fdc9b0038d394330f601160ca1e8eb80b86df99a8b",
      "scenario/blender/trained_models.py": "f3ce308f83794bcf4a4a5ed92525e53b5cb511c235ccdd3f3f97da28f270ab9a",
      "scenario/blender/model_picker.py": "3f4bd5d9bd397c8ceb53a62852f1ba458a06ca3bba1f125a66e4163a74b93ff5",
      "scenario/blender/runtime.py": "0cb590b37bf3593496cd09bb7c9167fab481ad3b49a211a828f1a3677c7368b4",
      "scenario/core/api/model_filter.py": "b900243e9a58d7490ac3df633832a58af55e0cf8e02bdd8917f50a7a951696b6",
      "scenario/core/api/catalog.py": "b6ba46cea2581665879d6083330fa2aae536af42b31c80420f16ba49e92fb08f",
      "scenario/mcp/tools_scenario.py": "32962ae1546dd74f80da6a0e4c5ca05c5c403496dd2657341156dc88667825ba",
      "tests/blender/test_offline_runtime.py": "daf592f19255d371263812862759c19b8cb7b7ce045505c090280c0d2898b18e",
      "tests/blender/test_trained_models.py": "247bc538aecd573d4de44c10006044f0adbf6270185babafca6ba377e0b0fe3d"
    }
  }
}
---

Evidence for [the active SDK catalog](../../architecture/runtime.md#active-sdk-catalog).
