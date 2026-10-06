---
{
  "type": "Evidence",
  "id": "docs-blender-job-context.mesh-input-binding",
  "title": "Captured mesh inputs in generation quotes",
  "evidence": {
    "path": "docs/BLENDER_JOB_CONTEXT.md",
    "scope": "mesh-input-binding",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-06",
    "base_revision": "e156d350cd282bfbcda98b378b4f6c88fd608fd7",
    "limits": "Inspected typed 3D input matching against scoped imported captures, immutable quote/job provenance, pre-prepare and pre-claim revalidation, local MCP/status exposure and atomic job schema 6 upgrades preserving prior uncertain claims and local applications. Offline tests cover model/workflow payload parity, array positions, scope separation, ambiguous/missing sources, corruption rejection and migration rollback. Native synthetic UI/MCP tests preserve the same source binding and exact SDK body across submission and restart. Source metadata describes the uploaded snapshot, not current Blender object state, provider alignment, automatic in-place application or restored target authority. No new API operation, dependency, UI control, live spending or release acceptance. Other evidence topics retain their scope. Schema-selection regressions cover both conflicting metadata keys, missing/null primary fields with a valid fallback, and absent/null schemas without a fallback. Provenance follows the same field selection as SDK payload preparation; invalid schemas stop before estimate dispatch. The storage guide identifies schema 6 and the supported 2-5 upgrade range.",
    "sources": {
      "scenario/core/jobs/mesh_source.py": "6448123e64f6d3f012de62b714f2fcffdeb173d530f6fd316d4022f354595229",
      "scenario/core/jobs/store.py": "f8095b6cd7d26d8ce11725dbba73b8b0a329c3bd9c2297496462d9ba4e4e3d8e",
      "scenario/core/jobs/coordinator.py": "af11251092730473c741f6cf03c4437cffa16ec7bdd85b5cbad846c491fc30ea",
      "scenario/core/jobs/uploads.py": "b0f4747a23834c345c47bb1b3fa34554f621724daaf97a7a4c62305a501cc2a0",
      "scenario/blender/model_jobs.py": "988ce9d31a3bdbb23e5bd6b55196e2037199c1d8d043642cfbf9110caf38d3a4",
      "scenario/mcp/tools_scenario.py": "a0053efcae525ed92620e228ac4c6e53edbf69225340a9ea16eb12fe837ee00b",
      "tests/unit/test_shared_quotes.py": "735cac0a46637a71adb7a06a4f654dee96669c3b4b3d6e805c7aa8dd54775251",
      "tests/unit/test_job_store.py": "b5d6c35e680276e50f99f3f2059e58755b07951c4d9ab2d9f1b764f1ebd4d56f",
      "tests/blender/test_model_generation.py": "53c2c470a8ed207a6f836430b11af2e1ab928176acf2bccc579e555cf160fc15",
      "tests/blender/test_job_store.py": "2d62ed4cc6a4023f6dd761dd5ece79529358f5e540f39534c1deb44f39c6358f",
      "scenario/core/api/sdk_adapter.py": "6cc3758eebf05f066a0aa11ed4d5c6ec96fb87b72f02f3d609cfdd97b88b044e",
      "scenario/core/schema/forms.py": "f13c662733ae8badc4a16c21f32b545e93c55d8f1dee2c8816cfce8b940df33a"
    }
  }
}
---

# Captured mesh inputs in generation quotes

Evidence for [the canonical guide](../../BLENDER_JOB_CONTEXT.md).
