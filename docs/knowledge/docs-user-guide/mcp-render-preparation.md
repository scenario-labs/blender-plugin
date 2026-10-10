---
{
  "type": "Evidence",
  "id": "docs-user-guide.mcp-render-preparation",
  "title": "Shared MCP render form preparation",
  "evidence": {
    "path": "docs/USER_GUIDE.md",
    "scope": "mcp-render-preparation",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-10",
    "base_revision": "4589f22964cc9cf99e53ec37bb8c5dbe6948c96b",
    "limits": "Inspected local MCP render form configuration, explicit scene/first-frame preparation and guarded reference removal through the existing native upload lifecycle. Render estimate and submission rebuild the native decorated request, require prepared uploaded inputs and separate Spark approval, and retain shared exact-cost, scope, scene and single-use submission checks. Native fixtures exercise input validation, reference identity, typed upload delivery, changed forms, shared UI/MCP payloads and separate Spark approval. No new SDK endpoint, fallback, dependency or paid job engine. This evidence does not establish physical desktop capture, live provider behavior, audio/motion review, all-lane release acceptance, or resolution of #263. UI layout is unchanged. Historical render-preparation evidence remains limited to its recorded sources and artifacts. Style replacement is restricted to the native selected style input; audio/other inputs and first-frame reservations survive configuration. Scoped 2026-10-10 check of the Render Video first-frame handoff, not a full re-review: first_frame_enabled also counts a role-tagged first-frame slot that holds an asset without a local file (a saved-image handoff); uploaded slots, removal, changed-path and ordering rules are unchanged; test_reference_form adds one test that a saved upload attached over a handed-off slot drops its provenance; existing tests are unchanged. The claims above still hold; the review date and base revision are unchanged. Re-checked 2026-10-10 for Render Video first-frame routing: render_references.target uses render_lanes.first_frame_target, which keeps the first-frame input unless params.Schema.exclusive pairs it with the clip input, then uses the first image array that can go with the clip (the frame orders first), else None so the first frame is refused. Schema.exclusive is read from file-input description wording only (Seedance 2.x, Minimax H3 and Wan 3.0 say a first frame can't be combined with reference images or videos); no schema field expresses it. render_form reports first_frame_route and the form draws a two-line note once a frame is chosen. Shared validation (params.validate_requirements through generation.build_request, forms.prepare_run and MCP raw bodies) refuses described exclusive pairs before any quote. Installed test_render_lanes tests cover the captured Seedance 2.0 schema (frame first in referenceImages, clip kept, no image input), an undeclared schema keeping the exact input, a model with no image input that can go with the clip, an old first-frame slot refused before pricing and the base Video lane guard; the full native suite passed on Blender 5.1.2 macOS arm64 only. No paid run has used a first frame sent as a reference image. Re-checked 2026-10-10 for the guard's scope: params.clause_inputs now also names settings for the payload audit, while Schema.exclusive still pairs file inputs only, so the routing and refusal claims above are unchanged; a free GET-only read of the 709 public models that day, without a project override, found pairs on the same 11 models. A setting described as exclusive (Kling V3 Omni generateAudio with a reference video) is not refused.",
    "sources": {
      "scenario/blender/render_commands.py": "d35546f97200978fdefa9800bf9304a773860bb354018c764b44baf6f577f6b2",
      "scenario/blender/render_references.py": "4897d8fe89d4bfbd9e171392cfa88feff4fa6a35ba88c40e4f63158fdb93aa47",
      "scenario/blender/reference_form.py": "9652fb1aa2644be3fb81bb59ba4d8034f0ea979ae50462701f607daf8d4b420d",
      "scenario/blender/render_lanes.py": "812bee11a5c33b3d3f9467303d3ed8f8523dddebfd0ebc69ae78cc6ad8655c3b",
      "scenario/blender/render_prompt_jobs.py": "5789166b017b45e9a56e5390ccc8ce7b9d374e03932c080dee1a189ff08a5edd",
      "scenario/blender/generation.py": "d19a174a7e3e362d384ab04ff31233571688a48dadafcfe70f21f6db6d4e669f",
      "scenario/blender/model_jobs.py": "5152fda72e78e3a11ed45dbda38251659caa1c8c116be568b77170d2cf78906d",
      "scenario/mcp/tools_scenario.py": "35f700477b84d5c052a73ff4cf245aa444814a405e627b765ec7e7424c92568c",
      "tests/blender/test_render_lanes.py": "380c36df92ada2d46cb2ba0b6dfabe5f0fb7d6611c4377f3c23559dbf7061b83",
      "tests/blender/test_reference_form.py": "fed7cac0dd659b3de7cf86569530ccfe615a4da66f72b2a929d74d785183d888",
      "tests/blender/test_prompt_tools.py": "edbc16f517593a051a20e5aa5c8e57095fa64ddd3691ba6bc3acc59d9b064f1c",
      "tests/blender/test_model_generation.py": "5908f8d0ae1f1f08ba58b6f2c55761df59a70d28adf7f27d900e30fe06d9f69a",
      "tests/unit/test_mcp_descriptions.py": "cf0f5a487b26656402ce40a7e2c4abce1be3f95e7a0d0542f7504c45cc5d0578",
      "tests/unit/test_mcp_docs.py": "92887a224070de8781b7206b574cf2a9dbc8e809772bb202b89c2c097c428cbd",
      "scenario/core/schema/params.py": "c94572f3737be87f1f419fb082664b6abe2ade2eca344ba22de589734dae85bb"
    }
  }
}
---

Source evidence for [the canonical guide](../../USER_GUIDE.md).
