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
    "limits": "Inspected splat_application (POINT_CHOICES, the 1,000,000 default, OPENGL and OPENCV axes with FORMAT_AXES defaults, foreach_set writes of splat_color, splat_opacity and splat_radius looked up by name, a new Geometry Nodes group with Mesh to Points, Point scale and a Max radius cap at the 99th percentile of at most 10,000 sampled radii, a new unlit Emission and Transparent material with a 2.2 gamma, no reuse by name, publication through _publish with the bottom center of the decoded bounds at the cursor, rollback over objects, collections, meshes, materials and node groups, uncertainty on incomplete cleanup), ModelJobs splat options, revise_model_application, the prepare_model routing through JobSession.prepare_model_import and the local-operation slot with a busy-slot rejection, the mapping of worker ResultError and SplatCancelled to Nothing was imported before any claim, JobSession.apply_recovered_model accepting only the approved unit and options, the mesh PLY fallback to the snapshot path, the splat summary and the native notices. Installed tests cover SPZ v2 and v3, 3DGS PLY and .splat point counts, thinning, both axes, the cursor anchor, attributes, the evaluated cloud and material, the radius cap and Point scale, fresh data beside existing names, exact rollback, worker-thread refusal, a Cycles CPU render, an EEVEE render on macOS, and runtime journeys for options, revision, a mesh and a splat PLY, SPZ v4 and changed-file refusals, a busy slot, the extension notice, reuse claims, unchanged request, paid and download counts and receipt-only retry. Isolated macOS arm64 probes on Blender 5.0.1, 5.1.2 and 5.2.1 built and rendered synthetic points and timed one 1,000,000-record decode and build; one run each, not a guarantee. The full installed suite passed 1,271 tests with 2 Windows-only skips on macOS arm64 Blender 5.0.1, 5.1.2 and 5.2.1; Linux and Windows CI runs are not claimed. Provider files, default axes, viewport performance and physical desktop review are not established. On 2026-10-10 fingerprints were refreshed after import_snapshot began reading bound OBJ normal, roughness and metallic maps as Non-Color by saved texture role and adding a Normal Map node only when one is missing; the statements here were rechecked and are unchanged, as is the review date. On 2026-10-12 fingerprints were refreshed after rewrite_mtl began adding -bm 1 to a bound normal statement without one, so an imported OBJ normal map has full Strength; the statements here were rechecked and are unchanged, as is the review date.",
    "sources": {
      "scenario/blender/splat_application.py": "0395a8ce98a15e45d2d7dc78ad4b3f4b0e1578b1b97010b00b70670cabf7454a",
      "scenario/blender/model_application.py": "ede45e886635fcb3768673ba83c0ee7e5b99d59ed2f8fc9a8d537028b9832dc9",
      "scenario/blender/job_session.py": "3ab7ea580ca986f9d86eb7a0735a96293627aa53016cc4172820fdc184e98163",
      "scenario/blender/model_jobs.py": "6d091ac315d207654aa209d3b84b5ea51b85dbf8fbf1eba02423dccc64471a4d",
      "scenario/blender/job_recovery.py": "a01e758c030606442395f7cda47695b2eff6cbe11d82eadbb259a2cdf6296fb3",
      "scenario/core/ui/saved_job_actions.py": "059a18316cee82773f63d4dd24ab5a0184475a399d1d891a6773318b79670dfe",
      "scenario/mcp/tools_scenario.py": "e8c6fef90ce04ee326af504c3a6a24f68d8e7b4a2b26d58be20e60bf159881c8",
      "scenario/core/scene/splats.py": "a8462e1b261ffe3c56eb4476cf457bd19c29147ff1306460863254669907a1ad",
      "scenario/core/jobs/results.py": "f29048daaca9cafd1a5ceaef4d8eebb70ac2328bae25ded45451be9672dddac7",
      "scenario/core/jobs/workers.py": "2d7b0820062d5a702d742f64fa25fd6c9ca472f0d1f258c7ea8fd17f81a2ba0a",
      "tests/blender/test_splat_application.py": "3cf88d7c33560200411c2cbe9ab3282efdb73a2d18f8e518f1b1b64247997d71",
      "tests/blender/test_model_generation.py": "5e9481456f39de8b2fb18913ed38c73c72180424c953ab578f267c09e0377669",
      "tests/blender/test_model_packages.py": "82504559876668b33118cc3a3d936f614714e17606bef0b4699ded8ef0ad678a",
      "tests/blender/helpers.py": "ab38e5d0d475b2cabf02b744ff775989a5bd59c852bb823ce2c66a455fcb8c50"
    }
  }
}
---

# Saved Gaussian splat import

Evidence for [the canonical document](../../MESH_APPLICATION.md#saved-gaussian-splat-import).
