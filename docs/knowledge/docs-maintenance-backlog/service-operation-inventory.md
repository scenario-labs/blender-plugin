---
{
  "type": "Evidence",
  "id": "docs-maintenance-backlog.service-operation-inventory",
  "title": "docs/maintenance/backlog.md: SDK service operation inventory",
  "evidence": {
    "path": "docs/maintenance/backlog.md",
    "scope": "service-operation-inventory",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-07",
    "base_revision": "03b070b9cb663b63cf8a411f6126efb40d4c66d0",
    "limits": "Reviewed retirement of the old Spark/LLM service clients and replacement of their fallback claims with shared SDK prompt quote/approval and complete-text recovery behavior. Shared results reject truncated previews and unusable asset references without new generation. SDK prompt and text-result regression coverage remains. No fresh provider failure reproduction, paid calls, desktop acceptance or unrelated composer review is claimed.",
    "sources": {
      "scenario/blender/prompt_tools.py": "1f465204554e10fae9f0903c84f8f834ba8a492451f1c855bde083cca36527e4",
      "scenario/blender/prompt_jobs.py": "8fc6c9b949806c086e8595a0aa6221bb217cc3d3b32c92a7e7eb9cabc4714313",
      "scenario/core/api/sdk_adapter.py": "28f759aeaa504bdcb435ff26dbf5fe8515b32c49d20b770467157fd0d0012735",
      "scenario/core/jobs/results.py": "d1e9ae96786d9bfaf92f8e1eddc5a0ca467a3b6e834e99f0c4633ffb4d32c15f",
      "tests/unit/test_prompt_results.py": "1c92e1748f5fa57f0047e4471e7fb95104f8e5efa66628373bf254529ddbb25a"
    }
  }
}
---

Evidence for [the canonical document](../../maintenance/backlog.md).
