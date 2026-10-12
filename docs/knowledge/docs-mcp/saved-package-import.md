---
{
  "type": "Evidence",
  "id": "docs-mcp.saved-package-import",
  "title": "MCP saved model package import",
  "description": "Model approval fields, job_status import units and the model_import summary.",
  "evidence": {
    "path": "docs/MCP.md",
    "scope": "saved-package-import",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-10",
    "base_revision": "33d00b0554151c4de04731fd1a5e5c64ed50855b",
    "limits": "Inspected the model branch of prepare_result_application (format, primary, members with roles and media types, glTF resources, cursor and per-format note), prepare_asset_application routing, the prepare_result_application, apply_result_application and job_status descriptions, and ModelJobs.status import_units, import_findings and model_import. The generated table renders first lines and schemas, and the schema is unchanged; gen_mcp_docs --check passes. Installed MCP journeys cover an OBJ package with reuse, a changed member, a changed GLB, the FBX frame-rate mismatch and splat and STL refusal, and offline unit contracts check the descriptions. The full installed suite passed 1,253 tests with 2 Windows-only skips on macOS arm64 Blender 5.1.2 only (exact ZIP SHA-256 06f5e16d233224123993950150a7609945d4eaaeed5aa9581ff460ef7958aec3). No headless MCP CLI run for a non-GLB package, live provider acceptance or splat import is claimed. On 2026-10-10 fingerprints were refreshed after saved splat import. Statements here about splat refusal, splats not being offered or splat import remaining open describe the package review only and are superseded: SPZ, .splat and PLY units are now prepared on a worker and offered, a PLY without splat data continues through this package snapshot, and the summary gains a splat field, as covered by the saved-splat-import topic of this document. The package snapshot, image guard, claim and rollback claims were rechecked and are unchanged; the review date is unchanged. On 2026-10-10 fingerprints were refreshed after import_snapshot began reading bound OBJ normal, roughness and metallic maps as Non-Color by saved texture role and adding a Normal Map node only when one is missing; the statements here were rechecked and are unchanged, as is the review date. On 2026-10-12 this branch was rebuilt on main 72c5340c without the unmerged remote progress branch it had been stacked on. The replay conflicted only in imports, ModelJobs fields, the view projection, status and the job_status description, where main's cancellation, World candidate and workflow cost code was kept beside this import. These statements were rechecked against the rebuilt sources and are unchanged; the unit suite passed and the fingerprints were refreshed. The installed results named here are from the earlier head. On 2026-10-12 the branch was rebuilt again, on main 4bd0061d, which now holds #369 (remote progress), #402 (saved model import undo), #377 and #379 (the saved image first-frame handoff and its native control), #401 (composer session end), #373 (asset organization reviews), #378 (MCP organization tools) and #380 (Library organization); the earlier notes' main without #369 no longer applies. The replay kept #369's remote projection, status fields, job_status paragraph and test helpers, and the handoff's use_first_frame action, native first-frame descriptor and operator, first_frame status field and video_first_frame purpose, beside this import, and moved #402's two desktop Undo checkpoints from apply_model into import_snapshot, which every saved model format uses; apply_model, now called only by Film shots, records none. The job_status description keeps #369's projection paragraph after this import sentence, and status returns both sets of fields; gen_mcp_docs --check passes. These statements were rechecked and are unchanged. The unit suite and the full installed suite on macOS arm64 Blender 5.1.2 passed against the rebuilt code; the fingerprints were refreshed and the review date is unchanged.",
    "sources": {
      "scenario/mcp/tools_scenario.py": "794987607f30634e0d0eda74940b8264641c80ac4a5a04b5d8a8880662033183",
      "scenario/blender/model_jobs.py": "f9bb80a01c12136fd1d463c3cf825c2b049c373aa4ed0f8e4a1022cee8f24838",
      "scenario/blender/model_application.py": "ede45e886635fcb3768673ba83c0ee7e5b99d59ed2f8fc9a8d537028b9832dc9",
      "tools/gen_mcp_docs.py": "405471c39482b9a84853b4950d251ab159b1f0de9f45117f2405e40ee1822b0e",
      "tests/unit/test_mcp_descriptions.py": "c7d007341e13625150bb765ad144a4dbae0c3d669a1e87b496bc70dfeaf46071",
      "tests/blender/test_model_generation.py": "5e9481456f39de8b2fb18913ed38c73c72180424c953ab578f267c09e0377669"
    }
  }
}
---

# MCP saved model package import

Evidence for [the canonical document](../../MCP.md#overview).
