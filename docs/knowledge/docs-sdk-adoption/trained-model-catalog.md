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
    "limits": "Reviewed the private trained list (privacy=private, status=trained, page size, cursor, project and online checks on every page), REST type classification for every pinned SDK 2.2.0 type literal, a non-string type classified as unsupported, one custom_private definition that counts private-list membership, lane and picker exclusion equal to the former blanket LoRA exclusion for every type literal, privacy and lineage (private custom models stay listed where records reach lanes or the picker), the models.get_bulk adapter (chunk and call bounds, requested-identity, duplicate and conflict checks, no partial result), bulk request element validation before deduplication, the per-connection summary cache kept apart from form schemas, single-flight sharing, retirement and AdapterUnavailable for model HTTP 403/404. Evidence is offline: inspected pinned wheel sources, the public get-bulk API reference and MockTransport tests with socket connections forbidden. No live read, dry run, route, picker change, MCP surface, quote or paid flow is claimed; lorasComponent bases, live bulk fields, batch limit and absent-ID behavior remain unverified under #97.",
    "sources": {
      "docs/SDK_ADOPTION.md": "37863b3fe4b7d88a1bdc0b3e92d0e697868201f8b1a33961c074c2d6ad70608c",
      "scenario/core/api/catalog.py": "a3e96f97db671a1979c764a82d34557be86d66f6e9c1277900890116ef3f3781",
      "scenario/core/api/model_filter.py": "431d83e059c1575f05917e7fe2bb9b3d76a1ef73dc27e57d827e54e433697dbc",
      "scenario/core/api/sdk_adapter.py": "50f91198e6ae0238afd17d0a748577d5fc2e8f2d91a20633ebc2b5e15c2d5184",
      "scenario/core/api/sdk_catalog.py": "eb47bfbd97271e1bcc9eb4e2c587b0b50d3976a477e55ada5ee1fd3816142ddc",
      "tests/unit/test_catalog_lanes.py": "e47edc13227d2161a935f349791fac9951ef6c738259463de8af413186f1fd6a",
      "tests/unit/test_model_filter.py": "aae42f098958a1670858426e716f6cb2b522373e5993605d12fe0adae3abceea",
      "tests/unit/test_scenario_sdk_contract.py": "f30eae28a93d08b4a0d0b93f635e587548ebeea95a79155ee551d63d9fd664dc",
      "tests/unit/test_sdk_adapter.py": "f609df76386ad3cb7097b0465b72431b668dc75dcacc26c2dbddfa29210dc5bb",
      "tests/unit/test_sdk_catalog.py": "5b05a3bb9d941107b35531dab1c02e81a72f42689f8f21bfc84be068d30567c4"
    }
  }
}
---

Evidence for [trained-model catalog reads](../../SDK_ADOPTION.md#trained-model-catalog-reads).
