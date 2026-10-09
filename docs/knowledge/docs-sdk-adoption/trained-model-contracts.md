---
{
  "type": "Evidence",
  "id": "docs-sdk-adoption.trained-model-contracts",
  "title": "Trained-model REST contracts",
  "evidence": {
    "path": "docs/SDK_ADOPTION.md",
    "scope": "trained-model-contracts",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-09",
    "base_revision": "33d00b0554151c4de04731fd1a5e5c64ed50855b",
    "limits": "Reviewed the zero-spend capture tool and its committed results against the section's claims: reads through models.list (private trained and public), models.retrieve, models.get_bulk, assets.list and composition concept reads; dryRun=true probes through the adapter request guard and configured zero-retry SDK client that issue no Estimate, refuse any call without dry_run=true or with ipDetection and record 4xx replies while 5xx fail the run; and a second quote of each accepted base-model route through SDKAdapter.estimate_model that is never submitted. The recorded live capture used SDK 2.2.0 and an API-key pair in its credential-bound scope without a project override; the private trained list was empty. Committed results show LoRA stacks, a single LoRA by modelId and flux.1-composition by modelId accepted on FLUX.1 Dev (and LoRA stacks on FLUX.2 Dev and Flux Kontext), direct /generate/custom/{trainedId} rejected with HTTP 400 for three trained types, trained details without inputs or uiConfig and with custom false, list and bulk rows without schemas, five base lorasComponent slot shapes, readable concept LoRAs including an unlisted one, the service validation table and prices. Offline tests pin those shapes, compare today's prepare_run with each service answer and confirm the estimate_model gate still refuses trained targets. The uncommitted exploratory list of other LoRA-capable bases is reported, not pinned. No paid run, result quality, service default strength, modelId plus loras merge semantics, private LoRA or composition behavior, bulk batch limit above 50 or absent-ID behavior is established; routing, UI, MCP and defaults remain #97 work.",
    "sources": {
      "docs/SDK_ADOPTION.md": "d168a38362140b7f67fa393be60831eb0451d82c07f123d41a83cf751d502070",
      "tools/capture_trained_contracts.py": "9aac0c05c9d8cd24e3975cff31736382e23b1e15e01cbc89f40c3ce0ae284937",
      "tests/unit/test_trained_contracts.py": "27ccb9cae8d115068c8c49647dd5da919843ed61f7cd96e51d04302b523bc038",
      "tests/unit/test_capture_trained_contracts.py": "8379d8ca993dad228506bdf2978551bbd551bc8545f83bc3f9b7972fc3e5c821",
      "tests/fixtures/models/trained/contracts.json": "15c19f7c77dd5dbc9c94b61a1cad8b3785a0105d7c4f21c984bdabf26e0fa779",
      "scenario/core/api/sdk_adapter.py": "aa638824ce7af67c9b70d12b759f361ab88f41cb0bc7f39213f1ce1d3e8d39ff",
      "scenario/core/api/catalog.py": "b6ba46cea2581665879d6083330fa2aae536af42b31c80420f16ba49e92fb08f",
      "scenario/core/schema/forms.py": "bc1e91677c33f2a0f9ff0a8ce7be51ba238653aab52d9d88e3e37fd23ab962b4"
    }
  }
}
---

Evidence for [trained-model REST contracts](../../SDK_ADOPTION.md#trained-model-rest-contracts).
