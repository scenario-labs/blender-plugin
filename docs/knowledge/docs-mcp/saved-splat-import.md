---
{
  "type": "Evidence",
  "id": "docs-mcp.saved-splat-import",
  "title": "Saved Gaussian splat import",
  "description": "MCP splat options, splat_options in approvals, worker refusals and model_import.splat.",
  "evidence": {
    "path": "docs/MCP.md",
    "scope": "saved-splat-import",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-10",
    "base_revision": "33d00b0554151c4de04731fd1a5e5c64ed50855b",
    "limits": "Inspected prepare_result_application (splat_max_points and splat_axes passed to prepare_asset_application, rejected without an asset_id or for other purposes, splat_options in the model approval, the worker and point-cloud notes), the schema enums and descriptions of prepare_result_application, apply_result_application and job_status, ModelJobs option validation and the model_import splat summary. gen_mcp_docs --check passes with the two new arguments in the generated table, and an offline unit contract keeps the enums aligned with splat_application and the native dialog. Installed MCP journeys cover defaults, explicit options, invalid options, a mesh unit with splat options, a mesh and a splat PLY, SPZ v4 and changed-file refusals, a busy slot, reuse and receipt-only retry. The full installed suite passed 1,271 tests with 2 Windows-only skips on macOS arm64 Blender 5.0.1, 5.1.2 and 5.2.1; Linux and Windows CI runs are not claimed. No headless MCP CLI run for splats or live provider acceptance is claimed.",
    "sources": {
      "scenario/mcp/tools_scenario.py": "e8c6fef90ce04ee326af504c3a6a24f68d8e7b4a2b26d58be20e60bf159881c8",
      "scenario/blender/model_jobs.py": "6d091ac315d207654aa209d3b84b5ea51b85dbf8fbf1eba02423dccc64471a4d",
      "scenario/blender/runtime.py": "a71f3d3d63d4bd67961387fa2209b38aa1bf774f380b107f5fd97bc6ffa0c28c",
      "tools/gen_mcp_docs.py": "405471c39482b9a84853b4950d251ab159b1f0de9f45117f2405e40ee1822b0e",
      "tests/unit/test_mcp_descriptions.py": "16f9e558e9abc040e080dd0ba1157ac57bd8a534a0f710247f5e8e5d007d0c02",
      "tests/blender/test_model_generation.py": "5e9481456f39de8b2fb18913ed38c73c72180424c953ab578f267c09e0377669"
    }
  }
}
---

# Saved Gaussian splat import

Evidence for [the canonical document](../../MCP.md).
