---
{
  "type": "Evidence",
  "id": "docs-job-coordinator.trained-model-route-quotes",
  "title": "Quote-time checks of trained-model references",
  "evidence": {
    "path": "docs/JOB_COORDINATOR.md",
    "scope": "trained-model-route-quotes",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-11",
    "base_revision": "72723f02a97a7226b1c697c31d8124b77ac92c86",
    "limits": "Reviewed the shared-catalog sentence and the new quote paragraph against JobCoordinator._quote and _check_references: the pure adapter preparation before any read, fresh reads of every model the caller chose in a model or model_array input (values equal to a schema default are not read) and of a chosen composition's concepts through the same selected adapter, at most 16 reads, an active-context and origin check before each read and after the last, RouteQuoteError (a QuoteError) for 403/404, untrained, incompatible, LoRA-in-modelIdInput or strength-policy failures with no dry run, intent or store write, other adapter failures and origin changes propagating unchanged, and the target/payload equality check between the checked preparation and the estimate. MockTransport tests through the real SDK 2.2.0 adapter cover model and workflow quotes, request order and project query, the read bound, transport failure, a scene change during reads, echoed defaults and identical payload bytes through JobWorkers with the base model as durable target; two installed native tests on Blender 5.1.2 cover the sidebar status text and MCP estimate_cost error with no dry run. No live or paid acceptance is claimed; recovery and submission paths are unchanged and were not re-reviewed. Re-checked after rebasing onto main 72723f02a: the merged scene-aware estimate handling in generation.py, cancellation and upload changes in the coordinator, organization-write and bulk-read refactors in the adapter, undeclared conditional siblings in forms, catalog model_kind and the extension-written MCP failure text leave these claims unchanged; the native tests were not re-run after the rebase.",
    "sources": {
      "docs/JOB_COORDINATOR.md": "7d8322bd13d53ba70aad42d7e462fdd867f7c8e03a9a88761ded921bdc17e4b9",
      "scenario/core/jobs/coordinator.py": "56ded5cb9e902e160e0c178adac4b4b5cac438f6b968e68a4b2796f3ac9c1602",
      "scenario/core/api/trained_routes.py": "71266a1f78c2201b7b871c5b84309f4475331a262ffb461f6f45cf5be4bf261a",
      "scenario/core/schema/forms.py": "319d0e2bf1a5e03a6ef89782c580dfb7bd26c01a637981316c2b0322253f852b",
      "scenario/core/api/sdk_adapter.py": "0a3b2f3ae5543ae60b556d4c4c45576c37b85b03cadf8eade69012ea8d1731dd",
      "scenario/blender/generation.py": "e70dcf71e4f42687fb065c17e6064f662ebefa6260cfdc03441b21c1daa94228",
      "tests/unit/test_trained_route_quotes.py": "98e68a228b82315c8dde92bd5295058ef75b5947b1620897feacb7909df37682",
      "tests/unit/test_shared_quotes.py": "0c486e4f75c978e40a1b893120ae2f0d7f0b28620f77b3e1b93bca292bd4c063",
      "tests/blender/test_sdk_estimates.py": "66d6383e2207ce23a932a528dbaa28ebdf8336d76d2b941395e917aaf1dc6b09"
    }
  }
}
---

Evidence for [the quote-time trained-model checks](../../JOB_COORDINATOR.md#shared-catalog-and-origin-bound-quotes).
