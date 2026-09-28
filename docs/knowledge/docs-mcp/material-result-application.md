---
{
  "type": "Evidence",
  "id": "docs-mcp.material-result-application",
  "title": "Saved texture set material assignment",
  "description": "Explicit shared assignment to one captured mesh material slot.",
  "evidence": {
    "path": "docs/MCP.md",
    "scope": "material-result-application",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-09-28",
    "base_revision": "474858e8e0df57f915385e82a7cfdf40f86c6fd9",
    "limits": "Inspected one saved texture set applied to an explicitly captured local single-user UV mesh slot through shared native/MCP commands. Maps use stored allowlisted roles and verified bounded PNG/EXR receipts, new packed images and a new Principled material. Tests cover slot and scene changes, preserved old data and face indices, bounded decode, complete/incomplete rollback and receipt-only retry. Exact packaged ZIP passes 606 full native tests each on macOS arm64 Blender 5.0.1/5.1.2/5.2.1. Desktop interaction remains pending: the offline isolated fixture reached ready but computer control could not access its window. This is not native mouse/focus/keyboard acceptance. Only ready/apply_failed saved jobs qualify; already-applied asset reuse, multiple texture sets, multi-object/shared-mesh application and global undo remain outside this slice. Provider normal conventions, tiling, actual image quality, paid provider checks, other OS desktop support, #263 resolution and full Materials/release acceptance are unverified. No new API operation or SDK dependency change beyond the separately reviewed texture-role persistence foundation.",
    "sources": {
      "scenario/blender/material_application.py": "1eb0c7ddb62e1b0422d00f30d04d3cc226f02efe175bd4c41cd71e889d74a8d1",
      "scenario/blender/image_application.py": "aedd8fdad1f92ae4abfe2721a0061189fe94c6dc91f7ff85106ceecc56edb0cc",
      "scenario/blender/job_session.py": "21697a4e01ec6ea49f17144d770a669d1de3f51a3b1600d29639c3fcdd567100",
      "scenario/blender/model_jobs.py": "8cabf25adbe965245e5b9cfab19cd052bd5e3b5ba4d2a52af0ca6eab11a81005",
      "scenario/blender/runtime.py": "3a67b9936955ca25f5e453e2b22a3f2d03b0f5d60101ffb470e2faded9f3909e",
      "scenario/blender/job_recovery.py": "574dc622a7bfe79b60139f3f23bdd42c1098506a11cb52366fb83c7d10f9a351",
      "scenario/mcp/tools_scenario.py": "a85335d2c6dcc197ed4f04cbc6591530759e28c01b878496d0e560d9035e0c35",
      "scenario/core/jobs/result_metadata.py": "5a454fcd5024e015dc4b4ae5ff40909f6b121ef6d73a4bdd70def58985da17c4",
      "scenario/core/jobs/store.py": "bf8c638af4ae4a7335450eb4329827944912813433deeccba8f3c97d0faa2f6f",
      "tests/blender/test_material_application.py": "5a8554aa2e884c971989efe8c42bbc1ae7a17d8febd261547a4aa4496d38a167",
      "tests/blender/test_model_generation.py": "e077f18b5bbf7ac3b26da0fe32dad2d7ee0ad1040c3fbfd56d9f8db65082fc04"
    }
  }
}
---

# Saved texture set material assignment

Evidence for [the canonical document](../../MCP.md).
