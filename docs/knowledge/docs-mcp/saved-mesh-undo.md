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
    "limits": "Inspected saved static REMESH/UV/RETEXTURE desktop checkpoints, preparation/final-checkpoint failure behavior, status, unchanged durable job records, transient mesh-status retirement and retained pre-checkpoints after verified failed import and invalidation of pending target authority. Exact ZIP passed 689 native tests each on macOS arm64 Blender 5.0.1/5.1.2/5.2.1; isolated 5.1.2 desktop menu undo/redo, approval and viewport interaction verified with synthetic transport. History follows existing Blender preferences and retention limits; background test eligibility is explicitly forced to exercise real undo operators. No live provider, paid, other OS desktop, rig/segmentation, new-object import undo or release acceptance claim. Other evidence topics retain their original scope.",
    "sources": {
      "scenario/blender/mesh_result_application.py": "194af586f1535a989bfe85e6b09a8b909a14673e0ba784814ba688a742601b65",
      "scenario/blender/model_jobs.py": "d501d8e38e12f882da4c296c197155757882bf0041e34eb47fe8e24a27e8a826",
      "scenario/blender/job_recovery.py": "b71b323a20793ef9b7a7297342402ccb52b46da6f3cadcb328b2e253c587a5c1",
      "scenario/blender/job_session.py": "1ddb95974ffb9c52d26c2dc4772547da338d42e181b21209814c7e34fbaa9537",
      "scenario/mcp/tools_scenario.py": "8b735a6c740c909910b80d164861e4675d902876ad827ab4e190e54cd74ce93a",
      "tests/blender/test_model_generation.py": "746ac15feb1b373997d95e79453c1edec9f6308e3206d1c8a63792fc074af524"
    }
  }
}
---

# Saved mesh undo

Evidence for [the canonical guide](../../MCP.md).
