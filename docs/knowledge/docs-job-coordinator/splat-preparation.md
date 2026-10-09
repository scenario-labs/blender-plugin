---
{
  "type": "Evidence",
  "id": "docs-job-coordinator.splat-preparation",
  "title": "Worker splat preparation commands",
  "evidence": {
    "path": "docs/JOB_COORDINATOR.md",
    "scope": "splat-preparation",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-09",
    "base_revision": "fb699b8555f7cee62147794516cc7aaa224864f7",
    "limits": "Inspected coordinator registration of the preparation's verification ticket, single-use claims, deactivation, cancellation before each receipt hash and between decoding chunks, changed-record or changed-file rejection, mesh PLY routing and fail-closed non-mesh PLY layouts, and JobWorkers admission through the shared local-operation slot. Offline unit tests cover these commands with synthetic receipts and a service transport that fails on any request. One receipt's hash is not interrupted. JobSession, UI and MCP wiring, scene application and live acceptance are not established.",
    "sources": {
      "scenario/core/jobs/coordinator.py": "3807613afe3c4b8a3cb25e0e3862fbfabdd80ad649c7a96769c5a218dc60872a",
      "scenario/core/jobs/workers.py": "2d7b0820062d5a702d742f64fa25fd6c9ca472f0d1f258c7ea8fd17f81a2ba0a",
      "scenario/core/jobs/results.py": "f29048daaca9cafd1a5ceaef4d8eebb70ac2328bae25ded45451be9672dddac7",
      "scenario/core/scene/splats.py": "a8462e1b261ffe3c56eb4476cf457bd19c29147ff1306460863254669907a1ad",
      "tests/unit/test_model_import_preparation.py": "cf65bbbce6f8366db9268b83c5efbcba9ac1567c8e30dab3dd014f8cbd1899af"
    }
  }
}
---

# Worker splat preparation commands

Evidence for [the canonical guide](../../JOB_COORDINATOR.md).
