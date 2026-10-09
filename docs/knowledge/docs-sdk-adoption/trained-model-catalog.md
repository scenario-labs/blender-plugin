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
    "base_revision": "b57c398f35fb2148c82fb8b26f6a40564d3f52ef",
    "limits": "Reviewed the private trained list (privacy=private, status=trained, page size, cursor, project and online checks on every page), REST type classification for every pinned SDK 2.2.0 type literal, unchanged lane and picker exclusion, the models.get_bulk adapter (chunk and call bounds, requested-identity, duplicate and conflict checks, no partial result), the per-connection summary cache kept apart from form schemas, single-flight sharing, retirement and AdapterUnavailable for model HTTP 403/404. Evidence is offline: inspected pinned wheel sources, the public get-bulk API reference and MockTransport tests with socket connections forbidden. No live read, dry run, route, picker, MCP surface, quote or paid flow is claimed; lorasComponent bases, live bulk fields, batch limit and absent-ID behavior remain unverified under #97.",
    "sources": {
      "docs/SDK_ADOPTION.md": "37eca901b41db3f3c4eaf71625944c67ce5ca0bed854c3c1c97836fd6e2f2b24",
      "scenario/core/api/catalog.py": "74fa842ed4ec58703b9a851ac73418eb5659407e4a46373683c06d739f440059",
      "scenario/core/api/model_filter.py": "6bab0d03bdb5944d1ff4bbbaccea916425c83a81584e976a7c2d69e2f5db8476",
      "scenario/core/api/sdk_adapter.py": "50f91198e6ae0238afd17d0a748577d5fc2e8f2d91a20633ebc2b5e15c2d5184",
      "scenario/core/api/sdk_catalog.py": "f10d96711d43398b5297c5ea372cc20daff07487c8264ab4145e437962958f65",
      "tests/unit/test_catalog_lanes.py": "e4df9c69bb8fd5402d3eb14955f670d5886e42a471264e0f2f700f38aad2337e",
      "tests/unit/test_scenario_sdk_contract.py": "f30eae28a93d08b4a0d0b93f635e587548ebeea95a79155ee551d63d9fd664dc",
      "tests/unit/test_sdk_adapter.py": "f609df76386ad3cb7097b0465b72431b668dc75dcacc26c2dbddfa29210dc5bb",
      "tests/unit/test_sdk_catalog.py": "4183c23e0be8d01bdb245c32a1279496c379ed5830d7bc64028de9a964872447"
    }
  }
}
---

Evidence for [trained-model catalog reads](../../SDK_ADOPTION.md#trained-model-catalog-reads).
