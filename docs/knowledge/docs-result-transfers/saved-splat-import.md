---
{
  "type": "Evidence",
  "id": "docs-result-transfers.saved-splat-import",
  "title": "Saved Gaussian splat import",
  "description": "Use of worker splat preparation by saved splat imports and the prototype builder delegation.",
  "evidence": {
    "path": "docs/RESULT_TRANSFERS.md",
    "scope": "saved-splat-import",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-10",
    "base_revision": "33d00b0554151c4de04731fd1a5e5c64ed50855b",
    "limits": "Reviewed the closing paragraph of worker-side splat preparation: JobSession.prepare_model_import queues ResultCommands.prepare_model_import for saved SPZ, .splat and PLY units, the point-cloud builder creates fresh Geometry Nodes and material data, and the prototype import_spz delegates to it. The full installed suite passed 1,271 tests with 2 Windows-only skips on macOS arm64 Blender 5.0.1, 5.1.2 and 5.2.1; Linux and Windows CI runs are not claimed. Provider MIME types, SPZ versions, axis conventions and original-file bytes still need live evidence. On 2026-10-12 this branch was rebuilt on the saved package import branch after that branch was rebuilt on main 72c5340c, which now holds #356, without the unmerged remote progress branch. The replay conflicted only in imports, the view projection, the job_status description, the generated prepare_result_application row, a transfer guide paragraph and test fixtures. These statements were rechecked against the rebuilt sources, including main's later coordinator, worker and result changes (Film export runs outside the local-operation slot; the splat preparation still uses it and registers one verification for one claim), and are unchanged; the unit suite passed and the fingerprints were refreshed. The installed results named here are from the earlier head. On 2026-10-12 the branch was rebuilt again on the package import branch, itself rebuilt on main 4bd0061d, which now holds #369 (remote progress), #402 (saved model import undo), #377 and #379 (the saved image first-frame handoff and its native control), #401 (composer session end), #373 (asset organization reviews), #378 (MCP organization tools) and #380 (Library organization); the earlier notes' main without #369 no longer applies. The replay kept #369's remote projection, job_status paragraph and test helpers, and the handoff's runtime wrapper, apply_saved_result branch, MCP purpose and native first-frame descriptor and operator, beside this import, and import_splat now records #402's two desktop Undo checkpoints when the saved-result command asks for history. The closing paragraph was rechecked and is unchanged. The unit suite and the full installed suite on macOS arm64 Blender 5.1.2 passed against the rebuilt code; the fingerprints were refreshed and the review date is unchanged.",
    "sources": {
      "scenario/core/jobs/results.py": "fbf05ea8baed20b055b946a1eef66337b698002c1b8066de1551b84adfb2f4b7",
      "scenario/blender/job_session.py": "48375992376c9d905ec7dbb2c7acb04444acfa6e09a5e6534eeb1c4f0ebeab88",
      "scenario/blender/splat_application.py": "0bbd5b488b2f3b3874db281fa1f7516d919d566bea2a22c77c1258054b10c729",
      "scenario/blender/apply_splat.py": "95562972fc2a8f49e10ddac30563d55b434160246b6fa323ba288d4d1338c23e",
      "tests/blender/test_splat_application.py": "3cf88d7c33560200411c2cbe9ab3282efdb73a2d18f8e518f1b1b64247997d71"
    }
  }
}
---

# Saved Gaussian splat import

Evidence for [the canonical document](../../RESULT_TRANSFERS.md#worker-side-splat-preparation).
