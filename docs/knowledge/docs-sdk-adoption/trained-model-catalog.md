---
{
  "type": "Evidence",
  "id": "docs-sdk-adoption.trained-model-catalog",
  "title": "Trained-model catalog reads",
  "evidence": {
    "path": "docs/SDK_ADOPTION.md",
    "scope": "trained-model-catalog",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-09",
    "base_revision": "fb699b8555f7cee62147794516cc7aaa224864f7",
    "limits": "Reviewed the private trained list (privacy=private, status=trained, page size, cursor, project and online checks on every page), REST type classification for every pinned SDK 2.2.0 type literal, a non-string type classified as unsupported, one custom_private definition that counts private-list membership, lane and picker exclusion equal to the former blanket LoRA exclusion for every type literal, privacy and lineage (private custom models stay listed where records reach lanes or the picker), is_trained as a lane filter that is also true for hosted base types and false for custom_private while routing kinds come from USABLE_TRAINED_KINDS, the models.get_bulk adapter (chunk and call bounds, requested-identity, duplicate and conflict checks, no partial result), bulk requests checked with the adapter's shared identifier rules before any pending read is owned, so an invalid ID fails only its own request and never a concurrent caller sharing a valid ID, the per-connection summary cache kept apart from form schemas, single-flight sharing in which refresh skips cached summaries but joins an in-flight read, retirement and AdapterUnavailable for model HTTP 403/404, whose status-naming text reaches form and MCP description reads through SDKCatalog and the job coordinator's direct model reads as an AdapterError. Evidence is offline: inspected pinned wheel sources, the public get-bulk API reference and MockTransport tests with socket connections forbidden. No live read, dry run, route, picker change, MCP surface, quote or paid flow is claimed; lorasComponent bases, live bulk fields, batch limit and absent-ID behavior remain unverified under #97.",
    "sources": {
      "docs/SDK_ADOPTION.md": "6dd8ecfd8c99b3a0400c89d1688106d4138b60c234e356984bd37daa4f307f98",
      "scenario/blender/generation.py": "6f73c4ba35ceb97097d1356b2267c5b2b7a2a7105b6900d0376d2604f9e9de8f",
      "scenario/core/api/catalog.py": "b6ba46cea2581665879d6083330fa2aae536af42b31c80420f16ba49e92fb08f",
      "scenario/core/api/model_filter.py": "431d83e059c1575f05917e7fe2bb9b3d76a1ef73dc27e57d827e54e433697dbc",
      "scenario/core/api/sdk_adapter.py": "d15f63c0bf67a1a1b84794fb55b48fe61ca53fec2a48d8b64e3d22651d067e3d",
      "scenario/core/api/sdk_catalog.py": "500ebca1a4da228ba0c96b7fa904e322602d67985837f1bdaaa7f19b93fc39a8",
      "scenario/core/jobs/coordinator.py": "a8b7efb39e74a1a34f350ff7274e2e714a06933383743744dd22e6e1b7d7096d",
      "scenario/core/jobs/manager.py": "f79ea01367faf949a139d7daaeb55ff47e58d86cc98fd58e5ed3c6bcfd6183ab",
      "tests/unit/test_catalog_lanes.py": "6ab30217c2fd9f1226041c1090a5f68d804f9e0a9d732ff8ed253dff03aeef9b",
      "tests/unit/test_model_filter.py": "aae42f098958a1670858426e716f6cb2b522373e5993605d12fe0adae3abceea",
      "tests/unit/test_scenario_sdk_contract.py": "f30eae28a93d08b4a0d0b93f635e587548ebeea95a79155ee551d63d9fd664dc",
      "tests/unit/test_sdk_adapter.py": "4a4db64dd5e4106f236ab150e9add62fd7948026acc932fc2b5c412ea8663ebb",
      "tests/unit/test_sdk_catalog.py": "c096bc59602fde7db0ae983047f36ce8b427fd4bea7093c158b87d5a3a9539ea"
    }
  }
}
---

Evidence for [trained-model catalog reads](../../SDK_ADOPTION.md#trained-model-catalog-reads).
