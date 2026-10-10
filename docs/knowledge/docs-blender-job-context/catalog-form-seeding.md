---
{
  "type": "Evidence",
  "id": "docs-blender-job-context.catalog-form-seeding",
  "title": "Catalog loads keep captured origins",
  "evidence": {
    "path": "docs/BLENDER_JOB_CONTEXT.md",
    "scope": "catalog-form-seeding",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-10",
    "base_revision": "33d00b0554151c4de04731fd1a5e5c64ed50855b",
    "limits": "Reviewed dependency-update origin invalidation against catalog form synchronization only. Catalog seeding and model-index restoration avoid RNA update callbacks, so a catalog load no longer makes origins, quotes or approvals captured before it stale; explicit selections and edits still invalidate them. Installed Blender 5.1.2 regressions cover a session origin across the first load and a restored model index, and an MCP approval across a seeding catalog load. Other origin, render-thread, deletion and history claims retain prior evidence. No desktop timing, other Blender series, live or release acceptance is established.",
    "sources": {
      "scenario/blender/job_session.py": "aa6b64633ca02992f355436eb3601147fa1a7457234c1e795f417a46a851b8eb",
      "scenario/core/jobs/origins.py": "d1282d67aacdfe2444a776cf1338667bea9ee67392ff3f473db581a0f8059977",
      "scenario/blender/generation.py": "6fcde0ba8495a44d0c562971f3ddf8b31714bc19fec8fbe7b47145d8fb0035ab",
      "scenario/blender/params_ui.py": "bda117a82c203865b9d8edb7129f0114e1a04db7a56d44eb557ea039148fca34",
      "tests/blender/test_generation.py": "27b397a4c8487f84150cdcd065f407c0fd671e7a01a994c0af04338f82fbc5d4",
      "tests/blender/test_model_generation.py": "1c1c89644d0d7881adbeaef4a73ed2e41b20c4434c2930414dc35d08cb8d74c2"
    }
  }
}
---

Evidence for the [canonical guide](../../BLENDER_JOB_CONTEXT.md).
