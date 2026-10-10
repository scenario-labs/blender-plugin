---
{
  "type": "Evidence",
  "id": "docs-sdk-adoption.trained-model-contracts",
  "title": "Trained-model REST contracts",
  "evidence": {
    "path": "docs/SDK_ADOPTION.md",
    "scope": "trained-model-contracts",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-10",
    "base_revision": "33d00b0554151c4de04731fd1a5e5c64ed50855b",
    "limits": "Reviewed the zero-spend capture tool and its committed results against the section's claims: reads through models.list (private trained and public), models.retrieve, models.get_bulk, assets.list and composition concept reads; dryRun=true probes through the adapter request guard and configured zero-retry SDK client that issue no Estimate, refuse any call without dry_run=true or with ipDetection and record 4xx replies while 5xx fail the run; and a second quote of each accepted base-model route through SDKAdapter.estimate_model that is never submitted. The recorded live capture used SDK 2.2.0 and an API-key pair in its credential-bound scope without a project override; the private trained list was empty. Committed results show LoRA stacks, a single LoRA by modelId and flux.1-composition by modelId accepted on FLUX.1 Dev (and LoRA stacks on FLUX.2 Dev and Flux Kontext), direct /generate/custom/{trainedId} rejected with HTTP 400 for three trained types, trained details without inputs or uiConfig and with custom false, list and bulk rows without schemas, five base lorasComponent slot shapes, readable concept LoRAs including an unlisted one, the service validation table and prices, where LoRAs left the FLUX.1 Dev quote unchanged and raised the Kontext quote while no FLUX.2 Dev quote without a LoRA was captured. Offline tests pin those shapes, compare the client policy (forms.prepare_run plus the quote-time reference check, see trained-model routes) with every captured request, accept a later capture's recorded local refusal of a request the service accepts, and confirm the estimate_model gate still refuses trained targets. The validation table's client column was re-reviewed against those tests. The uncommitted exploratory list of other LoRA-capable bases is reported, not pinned. No paid run, FLUX.2 Dev price without a LoRA, result quality, service default strength, modelId plus loras merge semantics, private LoRA or composition behavior, bulk batch limit above 50 or absent-ID behavior is established; UI, MCP and defaults remain #97 work.",
    "sources": {
      "docs/SDK_ADOPTION.md": "c88dfb07939f597db7e27a88424813c23c3cf3be6cff3612dc6baab859057319",
      "tools/capture_trained_contracts.py": "1b700978bc90a4fbb2b233b5fa0afcc57156823155a398c10acc9d022c6f3dec",
      "tests/unit/test_trained_contracts.py": "8c3301aaeeed51313d460bfd1c346d38ad0f9b6eb4fd5c64e4bb41fca1127018",
      "tests/unit/test_capture_trained_contracts.py": "6a73c5cfb4ddd26c3163bcb8082cbb5446b0cc4225b31a376a6bf09de2007479",
      "tests/fixtures/models/trained/contracts.json": "15c19f7c77dd5dbc9c94b61a1cad8b3785a0105d7c4f21c984bdabf26e0fa779",
      "scenario/core/api/sdk_adapter.py": "7909438eeba80757ded5f6ce531a5a82b86bfc1ca812215a3e8b868b2ff6fa19",
      "scenario/core/api/catalog.py": "b6ba46cea2581665879d6083330fa2aae536af42b31c80420f16ba49e92fb08f",
      "scenario/core/schema/forms.py": "249d12ebf9d86a3db957896b8a16730841c86794489f80bf77a862de86a0a0da"
    }
  }
}
---

Evidence for [trained-model REST contracts](../../SDK_ADOPTION.md#trained-model-rest-contracts).
