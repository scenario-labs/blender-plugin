---
{
  "type": "Evidence",
  "id": "docs-material-application.material-result-application",
  "title": "Saved texture set material assignment",
  "description": "Explicit shared assignment to one captured mesh material slot.",
  "evidence": {
    "path": "docs/MATERIAL_APPLICATION.md",
    "scope": "material-result-application",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-06",
    "base_revision": "031f109fc71049f6087ac01ab8f71f01c84d05c4",
    "limits": "Inspected one saved texture set applied to an explicitly captured local single-user UV mesh slot through shared native/MCP commands. Maps use stored allowlisted roles and verified bounded PNG/EXR receipts, new packed images and a new Principled material. Tests cover slot and scene changes, preserved old data and face indices, bounded decode, complete/incomplete rollback and receipt-only retry. Dedicated albedo takes precedence over a coexisting base preview, which stays saved but is not loaded into the material. Repeated roles remain rejected. Regression tests cover complete map sets in both asset orders, shared native/MCP approvals, packed shader wiring and unchanged saved results/request counts. Exact ZIP 80f65d4b2993c4da7b8f21f7a6b19f8bdbe54dbc70809c59122d392096b0d4af passes 620 full native tests each on macOS arm64 Blender 5.0.1/5.1.2/5.2.1. Earlier isolated macOS arm64 Blender 5.1.2 desktop interaction verifies mouse approval, applied state, one packed material, unchanged mock request/submission counts, material preview, selection, keyboard views/orbit, zoom, clean exit and unchanged normal profile. UI_STYLE.md records that earlier desktop ZIP and test app identity qualification; the inaccessible-window attempt was not a pass. Mixed preview/albedo selection has native functional coverage, not a new desktop interaction run. This scoped review refreshes only the material selector and its two regression-source fingerprints; other source drift remains visible. Only ready/apply_failed saved jobs qualify; already-applied asset reuse, multiple texture sets, multi-object/shared-mesh application and global undo remain outside this slice. Provider normal conventions, tiling, actual image quality, paid provider checks, other OS desktop support, #263 resolution and full Materials/release acceptance are unverified. No new API operation or SDK dependency change beyond the separately reviewed texture-role persistence foundation.",
    "sources": {
      "scenario/blender/material_application.py": "bd8035e8cb12c7ee0b38f3027f02d2c4b654ca01d8d1939943e4bac5afe9ef03",
      "scenario/blender/image_application.py": "aedd8fdad1f92ae4abfe2721a0061189fe94c6dc91f7ff85106ceecc56edb0cc",
      "scenario/blender/job_session.py": "7ea7fde61e532dbb558ed9131267f4dfd8c8d6e377af0321a5eafe0743713901",
      "scenario/blender/model_jobs.py": "8cabf25adbe965245e5b9cfab19cd052bd5e3b5ba4d2a52af0ca6eab11a81005",
      "scenario/blender/runtime.py": "3a67b9936955ca25f5e453e2b22a3f2d03b0f5d60101ffb470e2faded9f3909e",
      "scenario/blender/job_recovery.py": "574dc622a7bfe79b60139f3f23bdd42c1098506a11cb52366fb83c7d10f9a351",
      "scenario/mcp/tools_scenario.py": "a85335d2c6dcc197ed4f04cbc6591530759e28c01b878496d0e560d9035e0c35",
      "scenario/core/jobs/result_metadata.py": "5a454fcd5024e015dc4b4ae5ff40909f6b121ef6d73a4bdd70def58985da17c4",
      "scenario/core/jobs/store.py": "3d700759ae589d64ffd039128daf12e0f05463541aa4be5537d3accae65cfd2b",
      "tests/blender/test_material_application.py": "af4e963039c05053b672cad66695cb0b620f342a54cedd9931b4ce5690919453",
      "tests/blender/test_model_generation.py": "2a45b698a6cf0c5ba27e17f758de569ab04187c49d0233ba6f2857c8810d7ef9",
      "docs/images/saved-material-approval.png": "e2fd7af8a14c8509899e03adf10aeb18120e4ff7a3f3b31a64e728312b284c65",
      "docs/images/saved-material-result.png": "833af1068618e0abb78d6b624840477dfb549b7f314de112fa8b9370f6bacfcf"
    }
  }
}
---

# Saved texture set material assignment

Evidence for [the canonical document](../../MATERIAL_APPLICATION.md).
