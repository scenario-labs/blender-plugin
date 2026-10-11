---
{
  "type": "Evidence",
  "id": "docs-sdk-adoption.trained-model-contracts",
  "title": "Trained-model REST contracts",
  "evidence": {
    "path": "docs/SDK_ADOPTION.md",
    "scope": "trained-model-contracts",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-11",
    "base_revision": "72723f02a97a7226b1c697c31d8124b77ac92c86",
    "limits": "Reviewed the zero-spend capture tool and its committed results against the section's claims: reads through models.list (private trained and public), models.retrieve, models.get_bulk, assets.list and composition concept reads; dryRun=true probes through the adapter request guard and configured zero-retry SDK client that issue no Estimate, refuse any call without dry_run=true or with ipDetection and record 4xx replies while 5xx fail the run; and a second quote of each accepted base-model route through SDKAdapter.estimate_model that is never submitted. The recorded live capture used SDK 2.2.0 and an API-key pair in its credential-bound scope without a project override; the private trained list was empty. Committed results show LoRA stacks, a single LoRA by modelId and flux.1-composition by modelId accepted on FLUX.1 Dev (and LoRA stacks on FLUX.2 Dev and Flux Kontext), direct /generate/custom/{trainedId} rejected with HTTP 400 for three trained types, trained details without inputs or uiConfig and with custom false, list and bulk rows without schemas, five base lorasComponent slot shapes, readable concept LoRAs including an unlisted one, the service validation table and prices, where LoRAs left the FLUX.1 Dev quote unchanged and raised the Kontext quote while no FLUX.2 Dev quote without a LoRA was captured. Offline tests pin those shapes, compare the client policy (forms.prepare_run plus the quote-time reference check, see trained-model routes) with every captured request, accept a later capture's recorded local refusal of a request the service accepts, and confirm the estimate_model gate still refuses trained targets. The validation table's client column was re-reviewed against those tests. The uncommitted exploratory list of other LoRA-capable bases is reported, not pinned. No paid run, FLUX.2 Dev price without a LoRA, result quality, service default strength, modelId plus loras merge semantics, private LoRA or composition behavior, bulk batch limit above 50 or absent-ID behavior is established; UI, MCP and defaults remain #97 work. Re-checked after rebasing onto main 72723f02a: the merged organization-write and bulk-read refactors in the adapter, undeclared conditional siblings in forms and catalog model_kind leave these claims unchanged.",
    "sources": {
      "docs/SDK_ADOPTION.md": "6c642097355cd326c8b7812c4620e77fd9582648f6d70ddea6faed805b22b802",
      "tools/capture_trained_contracts.py": "1b700978bc90a4fbb2b233b5fa0afcc57156823155a398c10acc9d022c6f3dec",
      "tests/unit/test_trained_contracts.py": "8c3301aaeeed51313d460bfd1c346d38ad0f9b6eb4fd5c64e4bb41fca1127018",
      "tests/unit/test_capture_trained_contracts.py": "6a73c5cfb4ddd26c3163bcb8082cbb5446b0cc4225b31a376a6bf09de2007479",
      "tests/fixtures/models/trained/contracts.json": "15c19f7c77dd5dbc9c94b61a1cad8b3785a0105d7c4f21c984bdabf26e0fa779",
      "scenario/core/api/sdk_adapter.py": "0a3b2f3ae5543ae60b556d4c4c45576c37b85b03cadf8eade69012ea8d1731dd",
      "scenario/core/api/catalog.py": "42b88d959ed39454a4bd037d3db457271a0a309d9f693c45c3490959d3c7ac9f",
      "scenario/core/schema/forms.py": "319d0e2bf1a5e03a6ef89782c580dfb7bd26c01a637981316c2b0322253f852b"
    }
  }
}
---

Evidence for [trained-model REST contracts](../../SDK_ADOPTION.md#trained-model-rest-contracts).
