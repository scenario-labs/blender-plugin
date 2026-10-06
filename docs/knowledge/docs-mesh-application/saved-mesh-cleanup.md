---
{
  "type": "Evidence",
  "id": "docs-mesh-application.saved-mesh-cleanup",
  "title": "Saved mesh import cleanup",
  "evidence": {
    "path": "docs/MESH_APPLICATION.md",
    "scope": "saved-mesh-cleanup",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-06",
    "base_revision": "a3f9ea976a2a425729f55b6f5a09607c5d473328",
    "limits": "Reviewed receipt-bound static GLB staging, mesh-policy rejection and import cleanup. A real morph-target GLB regression verifies that deleting its imported mesh also frees shape keys, restores the exact datablock sets and preserves the captured source; two separately reviewed local attempts record confirmed failure rather than uncertainty. A synthetic importer helper action and unused node-group/image regression covers successful orphan cleanup, dependency order and preservation of existing fake-user data and live replacement materials. Animated GLBs remain rejected before Blender import; injected helper animation is defensive cleanup coverage, not animated-format acceptance. Native tests do not establish provider output quality, desktop approval, other edit policies or release acceptance.",
    "sources": {
      "scenario/blender/mesh_result_application.py": "5b23cc19ffa6a240bb97b686bbbd1c0f18d5caf50191598aab5a6c32b9ce3de7",
      "scenario/blender/model_application.py": "bc904880f7af28d74ae6cccd6b3dea3cc0dff164806e15a8a6fa3eadd9ba2560",
      "scenario/blender/mesh_application.py": "99e0af39cd720903982dee3480a20dd25164f318ca14d2550b4fc31ed8e6d935",
      "scenario/blender/job_session.py": "5216d7c5b3dae533e653645526f40f2fa4d6d51b1534f5f12912546a042f0a49",
      "scenario/core/scene/glb.py": "4dfcea10743bb83305e5fd1f34815501955347490c711ab4d3e45ea4b3b7468e",
      "tests/blender/test_mesh_result_application.py": "28acd44ffab4d96a10727fb3c93870745d2096b09e12a8112c25b9ec948cc505",
      "tests/unit/test_glb.py": "6d75fc6fc88c1a98c7b459e8835e50680012bfe5dcafb05970dbf619893936aa"
    }
  }
}
---

# Saved mesh import cleanup

Evidence for [the canonical guide](../../MESH_APPLICATION.md).
