---
{
  "type": "Evidence",
  "id": "docs-sdk-adoption.trained-model-routes",
  "title": "Trained-model routes",
  "evidence": {
    "path": "docs/SDK_ADOPTION.md",
    "scope": "trained-model-routes",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-11",
    "base_revision": "72723f02a97a7226b1c697c31d8124b77ac92c86",
    "limits": "Reviewed the trained-model routes section, the catalog-section sentence on quote reads and the adapter-coverage sentences that now link to it against the listed sources: LoRA inputs named only by uiConfig.lorasComponent (modelInput model_array with modelTypes, scaleInput number_array, optional modelIdInput model), refused as malformed when names, types or modelTypes do not match; stack and composition as the only route kinds, matching the captured dry runs, with direct trained targets still refused by the unchanged estimate_model gate; the strength policy in forms.prepare_run (no invented 1.0, a declared scalar or matching list default only, one strength per LoRA, each LoRA once (also when merging legacy wiring would drop a repeat), no orphan strengths, no modelIdInput with a stack), applied only to inputs the caller chose (not empty and not equal to the schema default) plus legacy wiring, and a malformed component refusing only requests that choose a model or number-array input; SDKAdapter passing uiConfig through forms.record_schema and the pure prepare_model and prepare_workflow; JobCoordinator._quote preparing first, then fresh-reading chosen model references and composition concepts through SDKAdapter.model with the selected project, deduplicated, bounded at 16 and origin-checked before each read, mapping AdapterUnavailable 403/404, untrained status, type mismatch, a malformed modelTypes on a chosen input (before any reference read), a LoRA in modelIdInput and incompatible or unreadable concepts to RouteQuoteError before any dry run, with a composition-specific message when its concepts exceed the read bound, and refusing an estimate whose target or payload differs from the checked one; fixed error text naming labels, positions, sanitized REST types and statuses only; the sidebar estimate status showing RouteQuoteError text and MCP estimate_cost returning it; apply, compatibility and compatible_bases as pure helpers with no UI or MCP caller yet. Evidence is offline: captured base and public trained fixtures, synthetic variants, a socket-free MockTransport through the real SDK 2.2.0 adapter and coordinator, every captured dry-run case compared with the local outcome (concept status assumed trained because the capture did not record it), and two installed native tests on Blender 5.1.2. No live read, dry run or paid run was made for this review. Private LoRAs and compositions, the Z-Image and Qwen slots, workflow lorasComponent inputs, the service strength for a LoRA in modelIdInput, scale step enforcement and result quality remain unverified; picker, sidebar strength controls, defaults and MCP trained listings remain #97 work. Re-checked after rebasing onto main 72723f02a: the merged scene-aware estimate handling in generation.py, cancellation and upload changes in the coordinator, organization-write and bulk-read refactors in the adapter, undeclared conditional siblings in forms, catalog model_kind and the extension-written MCP failure text leave these claims unchanged; the native tests were not re-run after the rebase.",
    "sources": {
      "docs/SDK_ADOPTION.md": "6c642097355cd326c8b7812c4620e77fd9582648f6d70ddea6faed805b22b802",
      "scenario/core/api/trained_routes.py": "71266a1f78c2201b7b871c5b84309f4475331a262ffb461f6f45cf5be4bf261a",
      "scenario/core/schema/forms.py": "319d0e2bf1a5e03a6ef89782c580dfb7bd26c01a637981316c2b0322253f852b",
      "scenario/core/api/sdk_adapter.py": "0a3b2f3ae5543ae60b556d4c4c45576c37b85b03cadf8eade69012ea8d1731dd",
      "scenario/core/jobs/coordinator.py": "56ded5cb9e902e160e0c178adac4b4b5cac438f6b968e68a4b2796f3ac9c1602",
      "scenario/blender/generation.py": "e70dcf71e4f42687fb065c17e6064f662ebefa6260cfdc03441b21c1daa94228",
      "scenario/core/api/catalog.py": "42b88d959ed39454a4bd037d3db457271a0a309d9f693c45c3490959d3c7ac9f",
      "tests/unit/test_trained_routes.py": "c44b2a6adccfe219f509a3e0b5141bef9ac35c1eb4980c443193f970b0446919",
      "tests/unit/test_trained_route_quotes.py": "98e68a228b82315c8dde92bd5295058ef75b5947b1620897feacb7909df37682",
      "tests/unit/test_trained_contracts.py": "8c3301aaeeed51313d460bfd1c346d38ad0f9b6eb4fd5c64e4bb41fca1127018",
      "tests/unit/test_forms.py": "dfd29abbabf2674e05d5dccb8e2d07c76f75f6215a684986cdab373369866e03",
      "tests/blender/test_sdk_estimates.py": "66d6383e2207ce23a932a528dbaa28ebdf8336d76d2b941395e917aaf1dc6b09",
      "tests/fixtures/models/trained/contracts.json": "15c19f7c77dd5dbc9c94b61a1cad8b3785a0105d7c4f21c984bdabf26e0fa779"
    }
  }
}
---

Evidence for [trained-model routes](../../SDK_ADOPTION.md#trained-model-routes).
