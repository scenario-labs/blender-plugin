---
{
  "type": "Evidence",
  "id": "docs-mesh-application.saved-splat-import",
  "title": "Saved Gaussian splat import",
  "description": "Worker-decoded SPZ, .splat and Gaussian PLY units built as a new point cloud under a reviewed claim.",
  "evidence": {
    "path": "docs/MESH_APPLICATION.md",
    "scope": "saved-splat-import",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-10",
    "base_revision": "33d00b0554151c4de04731fd1a5e5c64ed50855b",
    "limits": "Inspected splat_application (POINT_CHOICES, the 1,000,000 default, OPENGL and OPENCV axes with FORMAT_AXES defaults, foreach_set writes of splat_color, splat_opacity and splat_radius looked up by name, a new Geometry Nodes group with Mesh to Points, Point scale and a Max radius cap at the 99th percentile of at most 10,000 sampled radii, a new unlit Emission and Transparent material with a 2.2 gamma, no reuse by name, publication through _publish with the bottom center of the decoded bounds at the cursor, rollback over objects, collections, meshes, materials and node groups, uncertainty on incomplete cleanup), ModelJobs splat options, revise_model_application, the prepare_model routing through JobSession.prepare_model_import and the local-operation slot with a busy-slot rejection, the mapping of worker ResultError and SplatCancelled to Nothing was imported before any claim, JobSession.apply_recovered_model accepting only the approved unit and options, the mesh PLY fallback to the snapshot path, the splat summary and the native notices. Installed tests cover SPZ v2 and v3, 3DGS PLY and .splat point counts, thinning, both axes, the cursor anchor, attributes, the evaluated cloud and material, the radius cap and Point scale, fresh data beside existing names, exact rollback, worker-thread refusal, a Cycles CPU render, an EEVEE render on macOS, and runtime journeys for options, revision, a mesh and a splat PLY, SPZ v4 and changed-file refusals, a busy slot, the extension notice, reuse claims, unchanged request, paid and download counts and receipt-only retry. Isolated macOS arm64 probes on Blender 5.0.1, 5.1.2 and 5.2.1 built and rendered synthetic points and timed one 1,000,000-record decode and build; one run each, not a guarantee. The full installed suite passed 1,271 tests with 2 Windows-only skips on macOS arm64 Blender 5.0.1, 5.1.2 and 5.2.1; Linux and Windows CI runs are not claimed. Provider files, default axes, viewport performance and physical desktop review are not established. On 2026-10-10 fingerprints were refreshed after import_snapshot began reading bound OBJ normal, roughness and metallic maps as Non-Color by saved texture role and adding a Normal Map node only when one is missing; the statements here were rechecked and are unchanged, as is the review date. On 2026-10-12 fingerprints were refreshed after rewrite_mtl began adding -bm 1 to a bound normal statement without one, so an imported OBJ normal map has full Strength; the statements here were rechecked and are unchanged, as is the review date. On 2026-10-12 this branch was rebuilt on the saved package import branch after that branch was rebuilt on main 72c5340c, which now holds #356, without the unmerged remote progress branch. The replay conflicted only in imports, the view projection, the job_status description, the generated prepare_result_application row, a transfer guide paragraph and test fixtures. These statements were rechecked against the rebuilt sources, including main's later coordinator, worker and result changes (Film export runs outside the local-operation slot; the splat preparation still uses it and registers one verification for one claim), and are unchanged; the unit suite passed and the fingerprints were refreshed. The installed results named here are from the earlier head. On 2026-10-12 the branch was rebuilt again on the package import branch, itself rebuilt on main 4bd0061d, which now holds #369 (remote progress), #402 (saved model import undo), #377 and #379 (the saved image first-frame handoff and its native control), #401 (composer session end), #373 (asset organization reviews), #378 (MCP organization tools) and #380 (Library organization); the earlier notes' main without #369 no longer applies. The replay kept #369's remote projection, job_status paragraph and test helpers, and the handoff's runtime wrapper, apply_saved_result branch, MCP purpose and native first-frame descriptor and operator, beside this import, and import_splat now records #402's two desktop Undo checkpoints when the saved-result command asks for history. The guide's splat section now says the import records the native Undo steps of a model import; installed tests undo and redo a splat import and check that a failed first checkpoint builds nothing and returns the job to review. The other statements here were rechecked and are unchanged. The unit suite and the full installed suite on macOS arm64 Blender 5.1.2 passed against the rebuilt code; the fingerprints were refreshed and the review date is unchanged. On 2026-10-12 the job_session.py and workers.py fingerprints were refreshed after that rebuild: #373's organization review commands go through the shared request queue, not the local-operation slot, so the preparation and slot statements here are unchanged.",
    "sources": {
      "scenario/blender/splat_application.py": "0bbd5b488b2f3b3874db281fa1f7516d919d566bea2a22c77c1258054b10c729",
      "scenario/blender/model_application.py": "501ba21b816ecd4db78d9f3da35cfa5b507f2e6cff5409ad87b5d118ad325753",
      "scenario/blender/job_session.py": "48375992376c9d905ec7dbb2c7acb04444acfa6e09a5e6534eeb1c4f0ebeab88",
      "scenario/blender/model_jobs.py": "31ec59656bb44b4e87111e3ea535cd76e9e988b2123d56cdc4aa8968273f6aff",
      "scenario/blender/job_recovery.py": "4b4768790db13f35adbe3d80ee3c52ee63fc34e84955f4a56d2448b65f545eeb",
      "scenario/core/ui/saved_job_actions.py": "d25a4144d0357e0025606e6d3befb7dde6558df45f7c85b8f1db9383d83ba086",
      "scenario/mcp/tools_scenario.py": "ce080d1ee9f995ab01ecbb6bba9f802f772b8f2d6b3fd061695e6f985f1a58a5",
      "scenario/core/scene/splats.py": "a8462e1b261ffe3c56eb4476cf457bd19c29147ff1306460863254669907a1ad",
      "scenario/core/jobs/results.py": "fbf05ea8baed20b055b946a1eef66337b698002c1b8066de1551b84adfb2f4b7",
      "scenario/core/jobs/workers.py": "2127fde9e058254ccd165426cbfc8166da2813b3e598309c9000becf9565f6d6",
      "tests/blender/test_splat_application.py": "3cf88d7c33560200411c2cbe9ab3282efdb73a2d18f8e518f1b1b64247997d71",
      "tests/blender/test_model_generation.py": "1627264d78606a37f6414d68ed57ddf8cc5761cfe0268c8e78ed935b0c2290a3",
      "tests/blender/test_model_packages.py": "82504559876668b33118cc3a3d936f614714e17606bef0b4699ded8ef0ad678a",
      "tests/blender/helpers.py": "d3a77292bc65b1421a98c470ed3c0ba531eeb5e2d83dc1c2fb2c11b426703f73"
    }
  }
}
---

# Saved Gaussian splat import

Evidence for [the canonical document](../../MESH_APPLICATION.md#saved-gaussian-splat-import).
