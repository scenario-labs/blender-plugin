---
{
  "type": "Evidence",
  "id": "docs-mesh-application.verified-mesh-replacement",
  "title": "Verified saved mesh replacement",
  "evidence": {
    "path": "docs/MESH_APPLICATION.md",
    "scope": "verified-mesh-replacement",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-04",
    "base_revision": "4589f22964cc9cf99e53ec37bb8c5dbe6948c96b",
    "limits": "Inspected captured source snapshots, explicit coordinate/policy mapping, receipt-bound isolated GLB import, one-mesh selection, rollback-before-cleanup and shared session claim/receipt integration. Native synthetic checks cover remesh, exact-topology UV, packed materials, preserved source context/selection, stale targets, ambiguous results, uncertainty, distinct local reuse and persistence-only retry. UI/MCP approval, pre-generation export metadata, provider coordinate/topology guarantees, other edit policies, global undo, persistent restoration and live/release acceptance remain incomplete. No new SDK/API operation or paid test. Other topics retain their evidence scope.",
    "sources": {
      "scenario/blender/mesh_application.py": "99e0af39cd720903982dee3480a20dd25164f318ca14d2550b4fc31ed8e6d935",
      "scenario/blender/mesh_result_application.py": "73ef54edb7fe04c6c3807db817b35f13655fdb2d57aaf83b622f6fd6a8aee70f",
      "scenario/blender/model_application.py": "d643c021f421008bf51174ad4666af6441bbef25cfae2b9e533b6b63df6b0262",
      "scenario/blender/job_session.py": "5216d7c5b3dae533e653645526f40f2fa4d6d51b1534f5f12912546a042f0a49",
      "tests/blender/test_mesh_result_application.py": "6116240a3be369b1a6f07e3f66994e10ed2573589c39dcb2293ccb7314b5b5d4",
      "tests/blender/test_mesh_application.py": "dd3e6277fc9ef0fe529b70cd6cefb9c365a3ec01d66f6a2f1dc4164d6576c396",
      "tests/blender/test_model_application.py": "050be4af5e45bbc12442c67e450a44ba1ad67f7d0986582c4565af66f1ff2b4a"
    }
  }
}
---

# Verified saved mesh replacement

Evidence for [the canonical guide](../../MESH_APPLICATION.md).
