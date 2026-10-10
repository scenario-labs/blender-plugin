---
{
  "type": "Evidence",
  "id": "docs-sdk-adoption.trained-model-routes",
  "title": "Trained-model routes",
  "evidence": {
    "path": "docs/SDK_ADOPTION.md",
    "scope": "trained-model-routes",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-10",
    "base_revision": "33d00b0554151c4de04731fd1a5e5c64ed50855b",
    "limits": "Reviewed the trained-model routes section, the catalog-section sentence on quote reads and the adapter-coverage sentences that now link to it against the listed sources: LoRA inputs named only by uiConfig.lorasComponent (modelInput model_array with modelTypes, scaleInput number_array, optional modelIdInput model), refused as malformed when names, types or modelTypes do not match; stack and composition as the only route kinds, matching the captured dry runs, with direct trained targets still refused by the unchanged estimate_model gate; the strength policy in forms.prepare_run (no invented 1.0, a declared scalar or matching list default only, one strength per LoRA, each LoRA once (also when merging legacy wiring would drop a repeat), no orphan strengths, no modelIdInput with a stack), applied only to inputs the caller chose (not empty and not equal to the schema default) plus legacy wiring, and a malformed component refusing only requests that choose a model or number-array input; SDKAdapter passing uiConfig through forms.record_schema and the pure prepare_model and prepare_workflow; JobCoordinator._quote preparing first, then fresh-reading chosen model references and composition concepts through SDKAdapter.model with the selected project, deduplicated, bounded at 16 and origin-checked before each read, mapping AdapterUnavailable 403/404, untrained status, type mismatch, a malformed modelTypes on a chosen input (before any reference read), a LoRA in modelIdInput and incompatible or unreadable concepts to RouteQuoteError before any dry run, with a composition-specific message when its concepts exceed the read bound, and refusing an estimate whose target or payload differs from the checked one; fixed error text naming labels, positions, sanitized REST types and statuses only; the sidebar estimate status showing RouteQuoteError text and MCP estimate_cost returning it; apply, compatibility and compatible_bases as pure helpers with no UI or MCP caller yet. Evidence is offline: captured base and public trained fixtures, synthetic variants, a socket-free MockTransport through the real SDK 2.2.0 adapter and coordinator, every captured dry-run case compared with the local outcome (concept status assumed trained because the capture did not record it), and two installed native tests on Blender 5.1.2. No live read, dry run or paid run was made for this review. Private LoRAs and compositions, the Z-Image and Qwen slots, workflow lorasComponent inputs, the service strength for a LoRA in modelIdInput, scale step enforcement and result quality remain unverified; picker, sidebar strength controls, defaults and MCP trained listings remain #97 work.",
    "sources": {
      "docs/SDK_ADOPTION.md": "2ac9db6688bebee1a418db0d20ef24c38c8aa1e907e278a4ce893acd5665419b",
      "scenario/core/api/trained_routes.py": "71266a1f78c2201b7b871c5b84309f4475331a262ffb461f6f45cf5be4bf261a",
      "scenario/core/schema/forms.py": "4478d2883602a0107767f9eff7bf030c8b11f1e60203df0ce9130c28ee384c71",
      "scenario/core/api/sdk_adapter.py": "7909438eeba80757ded5f6ce531a5a82b86bfc1ca812215a3e8b868b2ff6fa19",
      "scenario/core/jobs/coordinator.py": "85a0621245ba75cf6a986967db15abe0fafb413aa4f8f62c2eadeb8c67d5ba3b",
      "scenario/blender/generation.py": "f418a545d2400727c377f80ef4bbe1366197469b5cafd35f90a96be8e7d43011",
      "scenario/core/api/catalog.py": "b6ba46cea2581665879d6083330fa2aae536af42b31c80420f16ba49e92fb08f",
      "tests/unit/test_trained_routes.py": "c44b2a6adccfe219f509a3e0b5141bef9ac35c1eb4980c443193f970b0446919",
      "tests/unit/test_trained_route_quotes.py": "98e68a228b82315c8dde92bd5295058ef75b5947b1620897feacb7909df37682",
      "tests/unit/test_trained_contracts.py": "8c3301aaeeed51313d460bfd1c346d38ad0f9b6eb4fd5c64e4bb41fca1127018",
      "tests/unit/test_forms.py": "dfd29abbabf2674e05d5dccb8e2d07c76f75f6215a684986cdab373369866e03",
      "tests/blender/test_sdk_estimates.py": "3c688536d60eef67422afe3c31c7f99f380dbabab6f2b91bddc3c511c6d53090",
      "tests/fixtures/models/trained/contracts.json": "15c19f7c77dd5dbc9c94b61a1cad8b3785a0105d7c4f21c984bdabf26e0fa779"
    }
  }
}
---

Evidence for [trained-model routes](../../SDK_ADOPTION.md#trained-model-routes).
