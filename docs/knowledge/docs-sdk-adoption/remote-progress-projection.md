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
    "reviewed_at": "2026-10-11",
    "base_revision": "72723f02a97a7226b1c697c31d8124b77ac92c86",
    "limits": "Reviewed that progress uses SDKAdapter.job (jobs.with_raw_response.retrieve), already used by refresh_remote and cancel_remote, with no new request, endpoint, raw fallback or SDK issue. The offline SDK 2.2.0 contract shows the raw wrapper keeps a fractional progress, active status and statusHistory and that the parsed Job exposes progress and status; a unit test checks the SDK status literals equal the five active plus three terminal statuses. No live service response is claimed.",
    "sources": {
      "scenario/core/api/sdk_adapter.py": "43eb582d077677e2975c21e13cd3164b319c96f14a36988c6b9f04ca56124121",
      "scenario/core/jobs/coordinator.py": "86d723261acb1fda7ef9718248be03c46de52cf6086277f15b673a46487551f5",
      "scenario/core/jobs/progress.py": "bf8bea9be0d1ba3c6ca7c2495fecf61eb67481ffb7499d1e30633cc154871af5",
      "tests/unit/test_scenario_sdk_contract.py": "39a1fba8e75fa08b895c46f84f63a641c06d04d008fe243ebcdc3e67e0ac5e32",
      "tests/unit/test_job_progress.py": "c6ab3586b2b9ae8f4abf957a36b066b20cb8f01259fda6d9db5c858b11204a17"
    }
  }
}
---

# Remote progress from the polling retrieve

Evidence for [the canonical document](../../SDK_ADOPTION.md).
