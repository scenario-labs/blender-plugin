---
{
  "type": "Evidence",
  "id": "docs-mcp.saved-mesh-undo",
  "title": "Saved mesh undo",
  "evidence": {
    "path": "docs/MCP.md",
    "scope": "saved-mesh-undo",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-04",
    "base_revision": "4589f22964cc9cf99e53ec37bb8c5dbe6948c96b",
    "limits": "Inspected saved static REMESH/UV/RETEXTURE desktop checkpoints, preparation/final-checkpoint failure behavior, status, unchanged durable job records and invalidation of pending target authority. Exact ZIP passed 688 native tests each on macOS arm64 Blender 5.0.1/5.1.2/5.2.1; isolated 5.1.2 desktop menu undo/redo, approval and viewport interaction verified with synthetic transport. History follows existing Blender preferences and retention limits; background test eligibility is explicitly forced to exercise real undo operators. No live provider, paid, other OS desktop, rig/segmentation, new-object import undo or release acceptance claim. Other evidence topics retain their original scope.",
    "sources": {
      "scenario/blender/mesh_result_application.py": "194af586f1535a989bfe85e6b09a8b909a14673e0ba784814ba688a742601b65",
      "scenario/blender/model_jobs.py": "1f46c52d28730d0b4d692a9bab9dacaa59eed64974c46fdc1bb4e32bd620aba4",
      "scenario/blender/job_recovery.py": "b71b323a20793ef9b7a7297342402ccb52b46da6f3cadcb328b2e253c587a5c1",
      "scenario/blender/job_session.py": "67ea833c9edcf0982e4518c61c1095348259d94a22a92265e63716496f98e5a7",
      "scenario/mcp/tools_scenario.py": "8b735a6c740c909910b80d164861e4675d902876ad827ab4e190e54cd74ce93a",
      "tests/blender/test_model_generation.py": "1ddb84500408897316b54936a3132b65581ee734775ed30c091a0590ccaa7a12"
    }
  }
}
---

# Saved mesh undo

Evidence for [the canonical guide](../../MCP.md).
