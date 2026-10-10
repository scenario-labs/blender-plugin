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
    "limits": "Reviewed the trained-model routes section, the catalog-section sentence on quote reads and the adapter-coverage sentences that now link to it against the listed sources: LoRA inputs named only by uiConfig.lorasComponent (modelInput model_array with modelTypes, scaleInput number_array, optional modelIdInput model), refused as malformed when names, types or modelTypes do not match; stack and composition as the only route kinds, matching the captured dry runs, with direct trained targets still refused by the unchanged estimate_model gate; the strength policy in forms.prepare_run (no invented 1.0, a declared scalar or matching list default only, one strength per LoRA, each LoRA once, no orphan strengths, no modelIdInput with a stack), applied only to inputs the caller chose (not empty and not equal to the schema default) plus legacy wiring, and a malformed component refusing only requests that choose a model or number-array input; SDKAdapter passing uiConfig through forms.record_schema and the pure prepare_model and prepare_workflow; JobCoordinator._quote preparing first, then fresh-reading chosen model references and composition concepts through SDKAdapter.model with the selected project, deduplicated, bounded at 16 and origin-checked before each read, mapping AdapterUnavailable 403/404, untrained status, type mismatch, a LoRA in modelIdInput and incompatible or unreadable concepts to RouteQuoteError before any dry run, and refusing an estimate whose target or payload differs from the checked one; fixed error text naming labels, positions, sanitized REST types and statuses only; the sidebar estimate status showing RouteQuoteError text and MCP estimate_cost returning it; apply, compatibility and compatible_bases as pure helpers with no UI or MCP caller yet. Evidence is offline: captured base and public trained fixtures, synthetic variants, a socket-free MockTransport through the real SDK 2.2.0 adapter and coordinator, every captured dry-run case compared with the local outcome (concept status assumed trained because the capture did not record it), and two installed native tests on Blender 5.1.2. No live read, dry run or paid run was made for this review. Private LoRAs and compositions, the Z-Image and Qwen slots, workflow lorasComponent inputs, the service strength for a LoRA in modelIdInput, scale step enforcement and result quality remain unverified; picker, sidebar strength controls, defaults and MCP trained listings remain #97 work.",
    "sources": {
      "docs/SDK_ADOPTION.md": "c88dfb07939f597db7e27a88424813c23c3cf3be6cff3612dc6baab859057319",
      "scenario/core/api/trained_routes.py": "908b49b8b5ecdd8ee5869fe07178b80b9e2d3a385b11d694babaf2515a3f0162",
      "scenario/core/schema/forms.py": "249d12ebf9d86a3db957896b8a16730841c86794489f80bf77a862de86a0a0da",
      "scenario/core/api/sdk_adapter.py": "7909438eeba80757ded5f6ce531a5a82b86bfc1ca812215a3e8b868b2ff6fa19",
      "scenario/core/jobs/coordinator.py": "85a0621245ba75cf6a986967db15abe0fafb413aa4f8f62c2eadeb8c67d5ba3b",
      "scenario/blender/generation.py": "f418a545d2400727c377f80ef4bbe1366197469b5cafd35f90a96be8e7d43011",
      "scenario/core/api/catalog.py": "b6ba46cea2581665879d6083330fa2aae536af42b31c80420f16ba49e92fb08f",
      "tests/unit/test_trained_routes.py": "6365c81a3df51abb5160404061644168a1cde4b7c914ae0732f4b3dfc6f5a7e0",
      "tests/unit/test_trained_route_quotes.py": "4d58d391482ec7608062eff516cd20bc3e03c761c8a4103b80c6f2fc5c6458a4",
      "tests/unit/test_trained_contracts.py": "8c3301aaeeed51313d460bfd1c346d38ad0f9b6eb4fd5c64e4bb41fca1127018",
      "tests/unit/test_forms.py": "a639ad556efeeb4d80491a08acaa367a5e1a102dece5615b3e6e4ac2fb5f17f9",
      "tests/blender/test_sdk_estimates.py": "3c688536d60eef67422afe3c31c7f99f380dbabab6f2b91bddc3c511c6d53090",
      "tests/fixtures/models/trained/contracts.json": "15c19f7c77dd5dbc9c94b61a1cad8b3785a0105d7c4f21c984bdabf26e0fa779"
    }
  }
}
---

Evidence for [trained-model routes](../../SDK_ADOPTION.md#trained-model-routes).
