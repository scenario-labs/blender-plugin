---
{
  "type": "Evidence",
  "id": "docs-architecture-runtime.trained-model-catalog",
  "title": "Trained-model catalog reads in the active SDK catalog",
  "evidence": {
    "path": "docs/architecture/runtime.md",
    "scope": "trained-model-catalog",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-09",
    "base_revision": "b57c398f35fb2148c82fb8b26f6a40564d3f52ef",
    "limits": "Reviewed that bulk summaries are explicit, read once per catalog connection, shared between overlapping callers, cached apart from form schemas and cleared on retirement, and that trained records are classified without entering lane lists. No UI, MCP or catalog-load caller uses these reads yet; native interaction, live service behavior and routing remain separate work under #97.",
    "sources": {
      "docs/architecture/runtime.md": "d9c5c4da868daecb9ccefbba8d0bade212592a79157c35b1e91cc883392df509",
      "scenario/core/api/catalog.py": "74fa842ed4ec58703b9a851ac73418eb5659407e4a46373683c06d739f440059",
      "scenario/core/api/sdk_catalog.py": "f10d96711d43398b5297c5ea372cc20daff07487c8264ab4145e437962958f65",
      "tests/unit/test_catalog_lanes.py": "e4df9c69bb8fd5402d3eb14955f670d5886e42a471264e0f2f700f38aad2337e",
      "tests/unit/test_sdk_catalog.py": "4183c23e0be8d01bdb245c32a1279496c379ed5830d7bc64028de9a964872447"
    }
  }
}
---

Evidence for [the active SDK catalog](../../architecture/runtime.md#active-sdk-catalog).
