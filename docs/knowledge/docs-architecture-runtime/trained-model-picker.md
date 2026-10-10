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
    "limits": "Reviewed the trained-model sentences of the active SDK catalog paragraph: generation.request_catalog queues the private trained list read with the public catalog through trained_models.request, the picker's Trained chip starts base description reads on demand (trained_models.request_bases, and from a delivered list only while model_picker.trained_view_open), local MCP list_models with the trained source starts the same reads and lists the same rows (topic docs-architecture-runtime.trained-models-mcp), and model_filter and catalog.models_for_lane keep LoRAs, compositions and other trained types out of the lane lists and the other chips while private custom models that reach them stay listed. Retirement clears the trained state with the catalog (generation.clear_catalog calls trained_models.clear; RuntimeState holds the trained fields). Other claims of the paragraph keep their own topic. The installed suite on macOS 27.0.1 arm64, Blender 5.1.2, Python 3.13.9 passed 1,264 tests (OK, 2 Windows-only skips) with ZIP sha256 d64765ad8f515f272d21c3fdb9b4f04645d43b053f4f86355d741915cb65e16c, whose 148 Python files match git archive of the reviewed implementation commit, including the 10 tests of tests/blender/test_mcp_trained_models.py against the socket-free synthetic service of tests/blender/test_trained_models.py (captured public FLUX.1 Dev and Z-Image bases and public trained fixtures plus synthetic private records; submissions answered only by that service where a test opts in). Not established: Blender 5.0 and 5.2, Linux and Windows runs; a session with a real MCP client; live reads, dry runs or paid runs; private LoRAs and compositions against the service; result quality.",
    "sources": {
      "docs/architecture/runtime.md": "9ee1eaf6ac0933c8345962404275c319dee768c598152ba48cd07754c9d14b0b",
      "scenario/blender/generation.py": "339ce612dd6d2dc0fe05478d53f1742ed267f3363465ce4cac68ea4b011c1920",
      "scenario/blender/trained_models.py": "9b54ff883bc36fdecdd7ddb4e29669cee786722204ec611899d89b1f0a703ba5",
      "scenario/blender/model_picker.py": "3f4bd5d9bd397c8ceb53a62852f1ba458a06ca3bba1f125a66e4163a74b93ff5",
      "scenario/blender/runtime.py": "0cb590b37bf3593496cd09bb7c9167fab481ad3b49a211a828f1a3677c7368b4",
      "scenario/core/api/model_filter.py": "b900243e9a58d7490ac3df633832a58af55e0cf8e02bdd8917f50a7a951696b6",
      "scenario/core/api/catalog.py": "b6ba46cea2581665879d6083330fa2aae536af42b31c80420f16ba49e92fb08f",
      "scenario/mcp/tools_scenario.py": "9b0e2dd87ff708889636525124c4a1eb935a45e56983f9138872742717d067db",
      "tests/blender/test_offline_runtime.py": "daf592f19255d371263812862759c19b8cb7b7ce045505c090280c0d2898b18e",
      "tests/blender/test_trained_models.py": "247bc538aecd573d4de44c10006044f0adbf6270185babafca6ba377e0b0fe3d"
    }
  }
}
---

Evidence for [the active SDK catalog](../../architecture/runtime.md#active-sdk-catalog).
