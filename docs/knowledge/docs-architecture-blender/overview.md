---
{
  "type": "Evidence",
  "id": "docs-architecture-blender.overview",
  "title": "docs/architecture/blender.md: overview",
  "description": "Repository evidence for the named source family and canonical document.",
  "evidence": {
    "path": "docs/architecture/blender.md",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-09-24",
    "limits": "Explicit JobSession World application was reviewed against owned verification, original-context checks, core claims, exact receipt-bound decoding and installed native failure/rollback/persistence cases. Other lifecycle, component, format and restoration claims retain prior evidence. One selected asset completes the job; there is no per-asset journal or atomic blend-file save. Active UI/MCP, authoritative account/project discovery, production storage policy, undo/recovery UX and live acceptance remain separate; no human approval is implied.",
    "sources": {
      "scenario/blender/job_session.py": "d717347e944a4a6f6add3f5af140a51a111e729a522e511c3a66f16df40336b6",
      "scenario/blender/mcp_service.py": "ec45907c26301d5c0c2e48fe2eab09136cd52aadb00c6be5401d23ec7d868715",
      "scenario/blender/mesh_application.py": "8ec54ba9e782c0cfc0f0f46092f28e4995f5c42d1d96065f4a0dbe99d1e8ea62",
      "scenario/blender/pump.py": "f3b5718c778bb3906f4d07a18a3a87e856812b1aea4a889b533124f9812140bb",
      "scenario/blender/world_application.py": "95a10cae5b1ec3fdc758a18dcb4e70a50ffe10961c1ab38e0c5bb9ea6dbe8934",
      "scenario/core/jobs/coordinator.py": "c4c8e9d40cce9da0d858883ac198c40b801859202f453e56eb53441b468d7ac2",
      "scenario/core/scene/placement.py": "7f2568b5e3804b01929376dd6a2c879d2191e626368f6b1c89b3c275cc96aa5c",
      "tests/blender/test_mesh_application.py": "dd3e6277fc9ef0fe529b70cd6cefb9c365a3ec01d66f6a2f1dc4164d6576c396",
      "tests/blender/test_session_results.py": "fed6c554fe817c6d455d6e9a00a0e142d18366b285662448b1e8d453d1ee2fd6",
      "tests/blender/test_world_application.py": "f8fddd0ddf5d5e4612c9109585f95db64a51d9a3aac4a050d59a7a8b66ba796b",
      "tests/unit/test_application_claims.py": "e2b993b16b8b97a9705ad68b46c2823c3c8006a32a73bd9968143605cb369989"
    },
    "scope": "overview",
    "base_revision": "cdc8775a4a074a4997eca84cec2699e0dbb16e8c"
  }
}
---

# docs/architecture/blender.md: overview

Evidence for [the canonical document](../../architecture/blender.md).

Source families separate independent maintenance work. The review date, coverage,
source fingerprints and document-wide limitations were preserved during the split.
Grouping sources does not renew the review or attribute every inherited claim to
this subset. Review and narrow this topic's limits when its evidence changes.
