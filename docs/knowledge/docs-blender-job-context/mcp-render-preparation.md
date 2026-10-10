---
{
  "type": "Evidence",
  "id": "docs-blender-job-context.mcp-render-preparation",
  "title": "Shared MCP render form preparation",
  "evidence": {
    "path": "docs/BLENDER_JOB_CONTEXT.md",
    "scope": "mcp-render-preparation",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-06",
    "base_revision": "4589f22964cc9cf99e53ec37bb8c5dbe6948c96b",
    "limits": "Inspected local MCP render form configuration, explicit scene/first-frame preparation and guarded reference removal through the existing native upload lifecycle. Render estimate and submission rebuild the native decorated request, require prepared uploaded inputs and separate Spark approval, and retain shared exact-cost, scope, scene and single-use submission checks. Native fixtures exercise input validation, reference identity, typed upload delivery, changed forms, shared UI/MCP payloads and separate Spark approval. No new SDK endpoint, fallback, dependency or paid job engine. This evidence does not establish physical desktop capture, live provider behavior, audio/motion review, all-lane release acceptance, or resolution of #263. UI layout is unchanged. Historical render-preparation evidence remains limited to its recorded sources and artifacts. Style replacement is restricted to the native selected style input; audio/other inputs and first-frame reservations survive configuration. Multi-select parameter configuration accepts only unique current schema choices, bounded by the choice count before iterating or storing caller values. Invalid arrays leave the entire form unchanged. Empty optional selections and disabling remain supported; the separate style-asset limit is not applied to parameter choices. Scoped 2026-10-10 check of the Render Video first-frame handoff, not a full re-review: first_frame_enabled also counts a role-tagged first-frame slot that holds an asset without a local file (a saved-image handoff); uploaded slots, removal, changed-path and ordering rules are unchanged; test_reference_form adds one test that a saved upload attached over a handed-off slot drops its provenance; existing tests are unchanged. The claims above still hold; the review date and base revision are unchanged.",
    "sources": {
      "scenario/blender/render_commands.py": "19a070771863828d0eca6e93d8b9a03f49ff547091667416df29ed4e950a21ef",
      "scenario/blender/render_references.py": "0f5cf2596e96aed0c8cc8a87d0940c6d2c493005621202ab04838ce82a6a2ff6",
      "scenario/blender/reference_form.py": "9652fb1aa2644be3fb81bb59ba4d8034f0ea979ae50462701f607daf8d4b420d",
      "scenario/blender/render_lanes.py": "812bee11a5c33b3d3f9467303d3ed8f8523dddebfd0ebc69ae78cc6ad8655c3b",
      "scenario/blender/render_prompt_jobs.py": "5789166b017b45e9a56e5390ccc8ce7b9d374e03932c080dee1a189ff08a5edd",
      "scenario/blender/generation.py": "d19a174a7e3e362d384ab04ff31233571688a48dadafcfe70f21f6db6d4e669f",
      "scenario/blender/model_jobs.py": "5152fda72e78e3a11ed45dbda38251659caa1c8c116be568b77170d2cf78906d",
      "scenario/mcp/tools_scenario.py": "35f700477b84d5c052a73ff4cf245aa444814a405e627b765ec7e7424c92568c",
      "tests/blender/test_render_lanes.py": "731ca76cbec967ac336278165678e38d91933b8f58a9c87269c02adeac3c0f95",
      "tests/blender/test_reference_form.py": "fed7cac0dd659b3de7cf86569530ccfe615a4da66f72b2a929d74d785183d888",
      "tests/blender/test_prompt_tools.py": "edbc16f517593a051a20e5aa5c8e57095fa64ddd3691ba6bc3acc59d9b064f1c",
      "tests/blender/test_model_generation.py": "5908f8d0ae1f1f08ba58b6f2c55761df59a70d28adf7f27d900e30fe06d9f69a",
      "tests/unit/test_mcp_descriptions.py": "cf0f5a487b26656402ce40a7e2c4abce1be3f95e7a0d0542f7504c45cc5d0578",
      "tests/unit/test_mcp_docs.py": "92887a224070de8781b7206b574cf2a9dbc8e809772bb202b89c2c097c428cbd"
    }
  }
}
---

Source evidence for [the canonical guide](../../BLENDER_JOB_CONTEXT.md).
