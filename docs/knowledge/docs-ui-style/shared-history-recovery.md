---
{
  "type": "Evidence",
  "id": "docs-ui-style.shared-history-recovery",
  "title": "Scoped saved jobs in cloud history",
  "evidence": {
    "path": "docs/UI_STYLE.md",
    "scope": "shared-history-recovery",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-05",
    "base_revision": "4589f22964cc9cf99e53ec37bb8c5dbe6948c96b",
    "limits": "Scoped history lookup and explicit saved-result recovery routing, including unscoped-cache collisions, ambiguous IDs, storage failures, fresh acknowledgement, restart and credential changes. Incomplete credentials permit cold read-only inspection but reject all MCP import dispatch. Synthetic installed functional tests: 749 pass on each macOS arm64 Blender 5.0.1, 5.1.2 and 5.2.1. Desktop input on macOS arm64 Blender 5.1.2 with the same ZIP and a preloaded synthetic cloud page verifies the project-history toggle, matched-row Inspect saved jobs action, unchanged saved record/scene/images/request count, no legacy import dispatch/tracking, and subsequent viewport selection/Home navigation. The disposable profile is removed and the normal profile remains unchanged. This does not prove live cloud refresh, completed download/import or other OS/DPI interaction. No arbitrary-cloud-job adoption, prototype migration, live/paid provider or integrated release acceptance.",
    "sources": {
      "scenario/core/history.py": "70f03b84bd4eaa98712332b97ee492180d91f1663825e8f967cfbb7a9cfce781",
      "scenario/blender/history.py": "01e55d9f4ce82ab82ed29792f51086413272bb051315132241d17786b03360be",
      "scenario/blender/operators.py": "c702667513650b9008e96e1d6f26addd3923a9a29fa19b929251a079bf7214f0",
      "scenario/blender/panels.py": "c296255f787e284baa15adb6fd3f478ae7876f71df59b175b50ebb4f40a85673",
      "scenario/mcp/tools_scenario.py": "23be0918a72222c90fe91e6878d267f2f782f8d2a40a4db93006d2332c8627fb",
      "scenario/blender/runtime.py": "bbf2a6a457d13db9a8159add5f39f6b927fb055cfaa91008c81930c7d034dd00",
      "scenario/blender/model_jobs.py": "93758190ff21f930cea9f664dbdcd5942459058ac0df7e9914dcf991daf8bfae",
      "tests/unit/test_history.py": "47084c58bb62aa7cfd4d31c163b635ce8f4f65313bd10d1b93679c0773612174",
      "tests/blender/test_sdk_history.py": "0f5e06746e85b9432448bb584dc9b8be8e41802dd9d074a88a5ea31a329cc6bf",
      "tests/blender/test_mcp_contracts.py": "4ff84c26aaa5bdb76ef7b91f274163c400dc5db43224a6bfeeee6de7ee36a12b",
      "docs/images/history-saved-job-row.png": "b45ad654d74b7ef9177da0495ded6b30e501b8b35108bcfe76cfec4e0e603e31",
      "docs/images/history-saved-job-recovery.png": "bde44b263afa662e742bb9d1b12427b68d66e999a79239fd7fd822034b9c7537"
    }
  }
}
---

# Scoped saved jobs in cloud history

Evidence for [the canonical guide](../../UI_STYLE.md).
