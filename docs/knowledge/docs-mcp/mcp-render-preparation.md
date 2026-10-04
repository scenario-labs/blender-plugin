---
{
  "type": "Evidence",
  "id": "docs-mcp.mcp-render-preparation",
  "title": "Shared MCP render form preparation",
  "evidence": {
    "path": "docs/MCP.md",
    "scope": "mcp-render-preparation",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-04",
    "base_revision": "4589f22964cc9cf99e53ec37bb8c5dbe6948c96b",
    "limits": "Inspected local MCP render form configuration, explicit scene/first-frame preparation and guarded reference removal through the existing native upload lifecycle. Render estimate and submission rebuild the native decorated request, require prepared uploaded inputs and separate Spark approval, and retain shared exact-cost, scope, scene and single-use submission checks. Native fixtures exercise input validation, reference identity, typed upload delivery, changed forms, shared UI/MCP payloads and separate Spark approval. No new SDK endpoint, fallback, dependency or paid job engine. This evidence does not establish physical desktop capture, live provider behavior, audio/motion review, all-lane release acceptance, or resolution of #263. UI layout is unchanged. Historical render-preparation evidence remains limited to its recorded sources and artifacts. Style replacement is restricted to the native selected style input; audio/other inputs and first-frame reservations survive configuration.",
    "sources": {
      "scenario/blender/render_commands.py": "d35546f97200978fdefa9800bf9304a773860bb354018c764b44baf6f577f6b2",
      "scenario/blender/render_references.py": "ca13ca03952d4bdfe13c8280e46f192fb5e7e525778393cdba2c9d71ae37db71",
      "scenario/blender/reference_form.py": "9652fb1aa2644be3fb81bb59ba4d8034f0ea979ae50462701f607daf8d4b420d",
      "scenario/blender/render_lanes.py": "812bee11a5c33b3d3f9467303d3ed8f8523dddebfd0ebc69ae78cc6ad8655c3b",
      "scenario/blender/render_prompt_jobs.py": "5789166b017b45e9a56e5390ccc8ce7b9d374e03932c080dee1a189ff08a5edd",
      "scenario/blender/generation.py": "d19a174a7e3e362d384ab04ff31233571688a48dadafcfe70f21f6db6d4e669f",
      "scenario/blender/model_jobs.py": "5152fda72e78e3a11ed45dbda38251659caa1c8c116be568b77170d2cf78906d",
      "scenario/mcp/tools_scenario.py": "35f700477b84d5c052a73ff4cf245aa444814a405e627b765ec7e7424c92568c",
      "tests/blender/test_render_lanes.py": "380c36df92ada2d46cb2ba0b6dfabe5f0fb7d6611c4377f3c23559dbf7061b83",
      "tests/blender/test_reference_form.py": "2e96cf07d7a1f45acdd238164162fb475c30a196ba7dd4cd9bd679d6bd2111d3",
      "tests/blender/test_prompt_tools.py": "edbc16f517593a051a20e5aa5c8e57095fa64ddd3691ba6bc3acc59d9b064f1c",
      "tests/blender/test_model_generation.py": "5908f8d0ae1f1f08ba58b6f2c55761df59a70d28adf7f27d900e30fe06d9f69a",
      "tests/unit/test_mcp_descriptions.py": "cf0f5a487b26656402ce40a7e2c4abce1be3f95e7a0d0542f7504c45cc5d0578",
      "tests/unit/test_mcp_docs.py": "92887a224070de8781b7206b574cf2a9dbc8e809772bb202b89c2c097c428cbd"
    }
  }
}
---

Source evidence for [the canonical guide](../../MCP.md).
