---
{
  "type": "Evidence",
  "id": "tests-fixtures-readme.static-model-application",
  "title": "Explicit saved static GLB import",
  "description": "Receipt-bound static model application shared by native UI and MCP.",
  "evidence": {
    "path": "tests/fixtures/README.md",
    "scope": "static-model-application",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-09-28",
    "base_revision": "474858e8e0df57f915385e82a7cfdf40f86c6fd9",
    "limits": "Inspected static embedded GLB preflight, private receipt snapshot, staged native import and selective rollback, scene/cursor approval, durable claim and receipt-only recovery with shutdown cleanup. Exact packaged ZIP passes synthetic native tests on macOS arm64 Blender 5.0.1/5.1.2/5.2.1. Isolated 5.1.2 desktop confirms one group at the approved cursor, unchanged mock submissions/requests, preserved selection, keyboard/viewport interaction and normal-profile fingerprint; UI_STYLE.md records the ZIP and test-app identity qualification. Static embedded single-scene GLBs only, bounded synchronous work; no rig/animation, external files, other formats, in-place mesh/UV/retexture, live provider acceptance, other OS desktop proof, global undo, #263 resolution or release acceptance.",
    "sources": {
      "scenario/core/scene/glb.py": "4dfcea10743bb83305e5fd1f34815501955347490c711ab4d3e45ea4b3b7468e",
      "scenario/blender/model_application.py": "ac01e82399dae82042b9ee33225f65df282fb7290351bad77025a960df1ccaa0",
      "scenario/blender/job_session.py": "26bc22627c4c988da46906e3c274c236e9ded788948fe18ac9f9f7701373ac68",
      "scenario/blender/model_jobs.py": "22b00da3de70d494555f3ba38add355c23925e323f0c0ab37cc7e3a1f6db3beb",
      "scenario/blender/job_recovery.py": "a79596ff4d1d08032c07c756a84430b3902a48f578d136bcb0b14803735f909a",
      "scenario/blender/runtime.py": "4eeb479cee877e8b1e2e18fabede37b5737ba5e7336a1faead804bf9f7987425",
      "scenario/mcp/tools_scenario.py": "219a7e7bb819df0a43a03bba805d3382bb168307641fb88e9e4c07b7a4e608be",
      "tests/unit/test_glb.py": "6d75fc6fc88c1a98c7b459e8835e50680012bfe5dcafb05970dbf619893936aa",
      "tests/blender/test_model_application.py": "e2df895c64f40a7a912a05c70e30d82a4768c47216bb91ed54e05f85f8f3e6ae",
      "tests/blender/test_model_generation.py": "c550a41186f17f075aad60787b7a7a50e50f370f4aa21f8b06ed88a2e78fb5b0",
      "tests/fixtures/synthetic/static-triangle.glb": "35a1a3d3f5c875577f3bb97440ba0c9766d5ab5a0c8b54759e88569da47272f0",
      "tests/fixtures/README.md": "a854832beebfc7ffe26b09a22e1877c6fbe70e8a8389358d09d2c585b81e49f6",
      "docs/images/saved-model-approval.png": "0189562c83184b2f3afaa69ffaf7cf0df025e34bcb12d267073064b7fca4594a",
      "docs/images/saved-model-result.png": "fb343f4da9cc64d16bf07909a89d8d5aaecf5cafee273148ea3ed6ceeb5666db"
    }
  }
}
---

# Explicit saved static GLB import

Evidence for [the canonical document](../../../tests/fixtures/README.md).
