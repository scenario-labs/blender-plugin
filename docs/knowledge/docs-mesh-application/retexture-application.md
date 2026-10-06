---
{
  "type": "Evidence",
  "id": "docs-mesh-application.retexture-application",
  "title": "Retexture application",
  "evidence": {
    "path": "docs/MESH_APPLICATION.md",
    "scope": "retexture-application",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-04",
    "base_revision": "4589f22964cc9cf99e53ec37bb8c5dbe6948c96b",
    "limits": "Inspected strict static-mesh RETEXTURE policy, UV/material adoption, geometry and non-UV attribute preservation, captured destination UI/MCP approval and existing durable claims. Exact ZIP native tests pass on macOS arm64 Blender 5.0.1/5.1.2/5.2.1; isolated 5.1.2 desktop evidence exercises menu, cancellation, keyboard confirmation and viewport input. Requires exact indexed topology and mapped positions; source materials remain untouched. No live provider coordinate/topology/appearance acceptance, new service call, paid test, rig/segmentation policy, global undo or release claim. Other evidence topics retain their own scope.",
    "sources": {
      "scenario/blender/mesh_application.py": "b575b30cd254950e367420669584977cb00126e944b2abc698de2283b05e03e3",
      "scenario/blender/mesh_result_application.py": "e1bf22bd9b1aceaad0a484fb676020b7c43b076fa8f29feb4dfe6f5a0b2e295e",
      "scenario/blender/job_recovery.py": "d3f24327efd77ba2f35fbd99f845a02d553e779d6f5f9839b43c1af890c69ab9",
      "scenario/blender/model_jobs.py": "9bd2ad2ff2e55b69aecc5e49e44ea66e71d153d4936cbe1eed0bfc7988a74a09",
      "scenario/mcp/tools_scenario.py": "fc881809a7f449f2f4d33c88693535ae0a6fcd58f442b597d9112f21ebf79ca2",
      "tests/blender/test_mesh_application.py": "953d1246748f1d16d41c0fb108b38e5fa608ba381a4b482792192f7924ab6c60",
      "tests/blender/test_mesh_result_application.py": "ade82d85b370c2692a17373c2e853e00be416caa014d41bf8e42ddf428bc4468",
      "tests/blender/test_model_generation.py": "a9fd4a7438989983eee175cdd69ccc966a292abf329b6f49039bc6e55a49f723"
    }
  }
}
---

# Retexture application

Evidence for [the canonical guide](../../MESH_APPLICATION.md).
