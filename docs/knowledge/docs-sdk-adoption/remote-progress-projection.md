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
    "base_revision": "1d86f53d3489b23f2447be69cb589140e2f3ba64",
    "limits": "Reviewed that progress uses SDKAdapter.job (jobs.with_raw_response.retrieve), already used by refresh_remote and cancel_remote, with no new request, endpoint, raw fallback or SDK issue. The offline SDK 2.2.0 contract shows the raw wrapper keeps a fractional progress, active status and statusHistory and that the parsed Job exposes progress and status; a unit test checks the SDK status literals equal the five active plus three terminal statuses. No live service response is claimed.",
    "sources": {
      "scenario/core/api/sdk_adapter.py": "784ac9f7f7c071291086eef894a4bcb3d895e53b8b26a233efea2d119f395765",
      "scenario/core/jobs/coordinator.py": "2abac8aa7823376d38aa8d585f5328f87a4c4330868c9e55c294563db526b8a8",
      "scenario/core/jobs/progress.py": "bf8bea9be0d1ba3c6ca7c2495fecf61eb67481ffb7499d1e30633cc154871af5",
      "tests/unit/test_scenario_sdk_contract.py": "01ffd891685f8e1370970056959d794c0c0e5aa051a4e252b99166a95a41db8b",
      "tests/unit/test_job_progress.py": "c6ab3586b2b9ae8f4abf957a36b066b20cb8f01259fda6d9db5c858b11204a17"
    }
  }
}
---

# Remote progress from the polling retrieve

Evidence for [the canonical document](../../SDK_ADOPTION.md).
