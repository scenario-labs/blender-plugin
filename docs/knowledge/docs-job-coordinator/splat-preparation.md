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
    "base_revision": "72723f02a97a7226b1c697c31d8124b77ac92c86",
    "limits": "Inspected coordinator registration of the preparation's verification ticket, single-use claims, deactivation, cancellation before each receipt hash and between decoding chunks, changed-record or changed-file rejection, mesh PLY routing and fail-closed non-mesh PLY layouts, and JobWorkers admission through the shared local-operation slot. Offline unit tests cover these commands with synthetic receipts and a service transport that fails on any request. One receipt's hash is not interrupted. JobSession, UI and MCP wiring, scene application and live acceptance are not established.",
    "sources": {
      "scenario/core/jobs/coordinator.py": "62d13ea128834a15d1355dc32f628bb63413e171f6a0946ef9736410e7ede541",
      "scenario/core/jobs/workers.py": "3d840e62059f7c4caa9a0892f9856d077cbfe63074190521f1dfe61c8e234034",
      "scenario/core/jobs/results.py": "f316fc3fb9e8799ce1aa0cc679ca8870c8b40239b6fb12c022ce1548de63169a",
      "scenario/core/scene/splats.py": "a8462e1b261ffe3c56eb4476cf457bd19c29147ff1306460863254669907a1ad",
      "tests/unit/test_model_import_preparation.py": "cf65bbbce6f8366db9268b83c5efbcba9ac1567c8e30dab3dd014f8cbd1899af"
    }
  }
}
---

# Worker splat preparation commands

Evidence for [the canonical guide](../../JOB_COORDINATOR.md).
