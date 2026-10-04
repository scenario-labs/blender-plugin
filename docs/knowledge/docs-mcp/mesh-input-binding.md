---
{
  "type": "Evidence",
  "id": "docs-mcp.mesh-input-binding",
  "title": "Captured mesh inputs in generation quotes",
  "evidence": {
    "path": "docs/MCP.md",
    "scope": "mesh-input-binding",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-04",
    "base_revision": "4589f22964cc9cf99e53ec37bb8c5dbe6948c96b",
    "limits": "Inspected typed 3D input matching against scoped imported captures, immutable quote/job provenance, pre-prepare and pre-claim revalidation, local MCP/status exposure and atomic job schema 6 upgrades preserving prior uncertain claims and local applications. Offline tests cover model/workflow payload parity, array positions, scope separation, ambiguous/missing sources, corruption rejection and migration rollback. Native synthetic UI/MCP tests preserve the same source binding and exact SDK body across submission and restart. Source metadata describes the uploaded snapshot, not current Blender object state, provider alignment, automatic in-place application or restored target authority. No new API operation, dependency, UI control, live spending or release acceptance. Other evidence topics retain their scope.",
    "sources": {
      "scenario/core/jobs/mesh_source.py": "6448123e64f6d3f012de62b714f2fcffdeb173d530f6fd316d4022f354595229",
      "scenario/core/jobs/store.py": "8a28fe796ea668eb525386e9e6400ab528f1c305cf6b7a488c4ff14e0d04eb35",
      "scenario/core/jobs/coordinator.py": "af11251092730473c741f6cf03c4437cffa16ec7bdd85b5cbad846c491fc30ea",
      "scenario/core/jobs/uploads.py": "b0f4747a23834c345c47bb1b3fa34554f621724daaf97a7a4c62305a501cc2a0",
      "scenario/blender/model_jobs.py": "5f9e9968f44139ba5d2cbdfb9f09c1a9c2839678e8d2e071950f4ef2009d05bf",
      "scenario/mcp/tools_scenario.py": "4a484dcf226b426427b767b6b5df5c854a6a8071811873b4d6a6b2defe1f44bd",
      "tests/unit/test_shared_quotes.py": "f60f4620dac1955d107bce7abdc5c5fd644e60d55f0a30a4c02e15c7fff43120",
      "tests/unit/test_job_store.py": "918b72771f92aea0862a05db4767488758bf33da4dbf42be15eeb66eebb3401b",
      "tests/blender/test_model_generation.py": "d6d69b3d813214ccde404cea801e70a797e0bb76b83626d543f29086826eab79",
      "tests/blender/test_job_store.py": "2d62ed4cc6a4023f6dd761dd5ece79529358f5e540f39534c1deb44f39c6358f"
    }
  }
}
---

# Captured mesh inputs in generation quotes

Evidence for [the canonical guide](../../MCP.md).
