---
{
  "type": "Evidence",
  "id": "docs-sdk-adoption.remote-progress-projection",
  "title": "Remote progress from the polling retrieve",
  "description": "SDK method used for shared job progress and its offline contract.",
  "evidence": {
    "path": "docs/SDK_ADOPTION.md",
    "scope": "remote-progress-projection",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-09",
    "base_revision": "33d00b0554151c4de04731fd1a5e5c64ed50855b",
    "limits": "Reviewed that progress uses SDKAdapter.job (jobs.with_raw_response.retrieve), already used by refresh_remote and cancel_remote, with no new request, endpoint, raw fallback or SDK issue. The offline SDK 2.2.0 contract shows the raw wrapper keeps a fractional progress, active status and statusHistory and that the parsed Job exposes progress and status; a unit test checks the SDK status literals equal the five active plus three terminal statuses. No live service response is claimed.",
    "sources": {
      "scenario/core/api/sdk_adapter.py": "aa638824ce7af67c9b70d12b759f361ab88f41cb0bc7f39213f1ce1d3e8d39ff",
      "scenario/core/jobs/coordinator.py": "a8b7efb39e74a1a34f350ff7274e2e714a06933383743744dd22e6e1b7d7096d",
      "scenario/core/jobs/progress.py": "bf8bea9be0d1ba3c6ca7c2495fecf61eb67481ffb7499d1e30633cc154871af5",
      "tests/unit/test_scenario_sdk_contract.py": "307f1650f460a41ddb748b1b3eb03610a1fecdfafa6cfaab6a4bdf71e3fa2154",
      "tests/unit/test_job_progress.py": "c6ab3586b2b9ae8f4abf957a36b066b20cb8f01259fda6d9db5c858b11204a17"
    }
  }
}
---

# Remote progress from the polling retrieve

Evidence for [the canonical document](../../SDK_ADOPTION.md).
