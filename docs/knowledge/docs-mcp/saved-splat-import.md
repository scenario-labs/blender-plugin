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
    "limits": "Inspected prepare_result_application (splat_max_points and splat_axes passed to prepare_asset_application, rejected without an asset_id or for other purposes, splat_options in the model approval, the worker and point-cloud notes), the schema enums and descriptions of prepare_result_application, apply_result_application and job_status, ModelJobs option validation and the model_import splat summary. gen_mcp_docs --check passes with the two new arguments in the generated table, and an offline unit contract keeps the enums aligned with splat_application and the native dialog. Installed MCP journeys cover defaults, explicit options, invalid options, a mesh unit with splat options, a mesh and a splat PLY, SPZ v4 and changed-file refusals, a busy slot, reuse and receipt-only retry. The full installed suite passed 1,271 tests with 2 Windows-only skips on macOS arm64 Blender 5.0.1, 5.1.2 and 5.2.1; Linux and Windows CI runs are not claimed. No headless MCP CLI run for splats or live provider acceptance is claimed. On 2026-10-12 this branch was rebuilt on the saved package import branch after that branch was rebuilt on main 72c5340c, which now holds #356, without the unmerged remote progress branch. The replay conflicted only in imports, the view projection, the job_status description, the generated prepare_result_application row, a transfer guide paragraph and test fixtures. These statements were rechecked against the rebuilt sources, including main's later coordinator, worker and result changes (Film export runs outside the local-operation slot; the splat preparation still uses it and registers one verification for one claim), and are unchanged; the unit suite passed and the fingerprints were refreshed. The installed results named here are from the earlier head. On 2026-10-12 the branch was rebuilt again on the package import branch, itself rebuilt on main 4bd0061d, which now holds #369 (remote progress), #402 (saved model import undo), #377 and #379 (the saved image first-frame handoff and its native control), #401 (composer session end), #373 (asset organization reviews), #378 (MCP organization tools) and #380 (Library organization); the earlier notes' main without #369 no longer applies. The replay kept #369's remote projection, job_status paragraph and test helpers, and the handoff's runtime wrapper, apply_saved_result branch, MCP purpose and native first-frame descriptor and operator, beside this import, and import_splat now records #402's two desktop Undo checkpoints when the saved-result command asks for history. The job_status description keeps #369's paragraph after the import sentence, and gen_mcp_docs --check passes. The statements here were rechecked and are unchanged. The unit suite and the full installed suite on macOS arm64 Blender 5.1.2 passed against the rebuilt code; the fingerprints were refreshed and the review date is unchanged.",
    "sources": {
      "scenario/mcp/tools_scenario.py": "ce080d1ee9f995ab01ecbb6bba9f802f772b8f2d6b3fd061695e6f985f1a58a5",
      "scenario/blender/model_jobs.py": "31ec59656bb44b4e87111e3ea535cd76e9e988b2123d56cdc4aa8968273f6aff",
      "scenario/blender/runtime.py": "a62737e55602985dba9fde0199e6ffd65d73e174df0de664c49e0277661671e1",
      "tools/gen_mcp_docs.py": "405471c39482b9a84853b4950d251ab159b1f0de9f45117f2405e40ee1822b0e",
      "tests/unit/test_mcp_descriptions.py": "f80c0f50a4dce07f863cf2b749effb2ac29efdd381d04aea1ec1ce4c30308421",
      "tests/blender/test_model_generation.py": "1627264d78606a37f6414d68ed57ddf8cc5761cfe0268c8e78ed935b0c2290a3"
    }
  }
}
---

# Saved Gaussian splat import

Evidence for [the canonical document](../../MCP.md).
