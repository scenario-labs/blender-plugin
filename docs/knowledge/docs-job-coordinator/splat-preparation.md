---
{
  "type": "Evidence",
  "id": "docs-job-coordinator.splat-preparation",
  "title": "Worker splat preparation commands",
  "evidence": {
    "path": "docs/JOB_COORDINATOR.md",
    "scope": "splat-preparation",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-11",
    "base_revision": "1d86f53d3489b23f2447be69cb589140e2f3ba64",
    "limits": "Inspected coordinator registration of the preparation's verification ticket, single-use claims, deactivation, cancellation before each receipt hash and between decoding chunks, changed-record or changed-file rejection, mesh PLY routing and fail-closed non-mesh PLY layouts, and JobWorkers admission through the shared local-operation slot. Offline unit tests cover these commands with synthetic receipts and a service transport that fails on any request. One receipt's hash is not interrupted. JobSession, UI and MCP wiring, scene application and live acceptance are not established. On 2026-10-12, rechecked against the sources of the saved splat import branch after it was rebuilt on main: the canonical section gained a sentence about JobSession.prepare_model_import, covered by docs-job-coordinator.saved-splat-import; this topic's command claims are unchanged, and the review date is unchanged.",
    "sources": {
      "scenario/core/jobs/coordinator.py": "3b759a4026a244cdfe8e1db2915338eb1333aba2d324e929a62f3b7d8392fe2d",
      "scenario/core/jobs/workers.py": "61040c548fe30c9533615df4e7ad05066fb92d665db11d5244f99990770737d1",
      "scenario/core/jobs/results.py": "45d5af2933626173d734339c3694042342bf961f9de52589bddafe11287d4418",
      "scenario/core/scene/splats.py": "a8462e1b261ffe3c56eb4476cf457bd19c29147ff1306460863254669907a1ad",
      "tests/unit/test_model_import_preparation.py": "cf65bbbce6f8366db9268b83c5efbcba9ac1567c8e30dab3dd014f8cbd1899af"
    }
  }
}
---

# Worker splat preparation commands

Evidence for [the canonical guide](../../JOB_COORDINATOR.md).
