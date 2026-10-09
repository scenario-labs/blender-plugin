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
    "base_revision": "b57c398f35fb2148c82fb8b26f6a40564d3f52ef",
    "limits": "Reviewed that progress uses SDKAdapter.job (jobs.with_raw_response.retrieve), already used by refresh_remote and cancel_remote, with no new request, endpoint, raw fallback or SDK issue. The offline SDK 2.2.0 contract shows the raw wrapper keeps a fractional progress, active status and statusHistory and that the parsed Job exposes progress and status; a unit test checks the SDK status literals equal the five active plus three terminal statuses. No live service response is claimed.",
    "sources": {
      "scenario/core/api/sdk_adapter.py": "1247ca79813ac35fe4bedad564e3588c41a52506e16580bb85178161ce875bfb",
      "scenario/core/jobs/coordinator.py": "a8b7efb39e74a1a34f350ff7274e2e714a06933383743744dd22e6e1b7d7096d",
      "scenario/core/jobs/progress.py": "bf8bea9be0d1ba3c6ca7c2495fecf61eb67481ffb7499d1e30633cc154871af5",
      "tests/unit/test_scenario_sdk_contract.py": "7e81dddf2735aa5b04c477d8459e6454c18a6f565af8ee447052705690647e00",
      "tests/unit/test_job_progress.py": "c6ab3586b2b9ae8f4abf957a36b066b20cb8f01259fda6d9db5c858b11204a17"
    }
  }
}
---

# Remote progress from the polling retrieve

Evidence for [the canonical document](../../SDK_ADOPTION.md).
