---
{
  "type": "Evidence",
  "id": "docs-job-coordinator.trained-model-route-quotes",
  "title": "Quote-time checks of trained-model references",
  "evidence": {
    "path": "docs/JOB_COORDINATOR.md",
    "scope": "trained-model-route-quotes",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-10",
    "base_revision": "33d00b0554151c4de04731fd1a5e5c64ed50855b",
    "limits": "Reviewed the shared-catalog sentence and the new quote paragraph against JobCoordinator._quote and _check_references: the pure adapter preparation before any read, fresh reads of every model the caller chose in a model or model_array input (values equal to a schema default are not read) and of a chosen composition's concepts through the same selected adapter, at most 16 reads, an active-context and origin check before each read and after the last, RouteQuoteError (a QuoteError) for 403/404, untrained, incompatible, LoRA-in-modelIdInput or strength-policy failures with no dry run, intent or store write, other adapter failures and origin changes propagating unchanged, and the target/payload equality check between the checked preparation and the estimate. MockTransport tests through the real SDK 2.2.0 adapter cover model and workflow quotes, request order and project query, the read bound, transport failure, a scene change during reads, echoed defaults and identical payload bytes through JobWorkers with the base model as durable target; two installed native tests on Blender 5.1.2 cover the sidebar status text and MCP estimate_cost error with no dry run. No live or paid acceptance is claimed; recovery and submission paths are unchanged and were not re-reviewed.",
    "sources": {
      "docs/JOB_COORDINATOR.md": "73d34740a01a1088f229d72edc936f73b3d6ede6cbf5076765b44e285b4f61b6",
      "scenario/core/jobs/coordinator.py": "85a0621245ba75cf6a986967db15abe0fafb413aa4f8f62c2eadeb8c67d5ba3b",
      "scenario/core/api/trained_routes.py": "71266a1f78c2201b7b871c5b84309f4475331a262ffb461f6f45cf5be4bf261a",
      "scenario/core/schema/forms.py": "4478d2883602a0107767f9eff7bf030c8b11f1e60203df0ce9130c28ee384c71",
      "scenario/core/api/sdk_adapter.py": "7909438eeba80757ded5f6ce531a5a82b86bfc1ca812215a3e8b868b2ff6fa19",
      "scenario/blender/generation.py": "f418a545d2400727c377f80ef4bbe1366197469b5cafd35f90a96be8e7d43011",
      "tests/unit/test_trained_route_quotes.py": "98e68a228b82315c8dde92bd5295058ef75b5947b1620897feacb7909df37682",
      "tests/unit/test_shared_quotes.py": "0c486e4f75c978e40a1b893120ae2f0d7f0b28620f77b3e1b93bca292bd4c063",
      "tests/blender/test_sdk_estimates.py": "3c688536d60eef67422afe3c31c7f99f380dbabab6f2b91bddc3c511c6d53090"
    }
  }
}
---

Evidence for [the quote-time trained-model checks](../../JOB_COORDINATOR.md#shared-catalog-and-origin-bound-quotes).
