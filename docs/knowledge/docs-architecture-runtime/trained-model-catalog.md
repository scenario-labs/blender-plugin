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
    "base_revision": "fb699b8555f7cee62147794516cc7aaa224864f7",
    "limits": "Reviewed that bulk summaries are explicit, read once per catalog connection, shared between overlapping callers, cached apart from form schemas and cleared on retirement, that trained records are classified with a malformed type treated as unsupported rather than raised, and that lane lists and the picker keep the former LoRA exclusion while still listing private custom models. No UI, MCP or catalog-load caller uses these reads yet; native interaction, live service behavior and routing remain separate work under #97.",
    "sources": {
      "docs/architecture/runtime.md": "495ee6405983eb6dbe2d6fe32c723bf33bc366d18af97f07fecba8969db4681d",
      "scenario/core/api/catalog.py": "b6ba46cea2581665879d6083330fa2aae536af42b31c80420f16ba49e92fb08f",
      "scenario/core/api/model_filter.py": "431d83e059c1575f05917e7fe2bb9b3d76a1ef73dc27e57d827e54e433697dbc",
      "scenario/core/api/sdk_catalog.py": "500ebca1a4da228ba0c96b7fa904e322602d67985837f1bdaaa7f19b93fc39a8",
      "tests/unit/test_catalog_lanes.py": "6ab30217c2fd9f1226041c1090a5f68d804f9e0a9d732ff8ed253dff03aeef9b",
      "tests/unit/test_model_filter.py": "aae42f098958a1670858426e716f6cb2b522373e5993605d12fe0adae3abceea",
      "tests/unit/test_sdk_catalog.py": "c096bc59602fde7db0ae983047f36ce8b427fd4bea7093c158b87d5a3a9539ea"
    }
  }
}
---

Evidence for [the active SDK catalog](../../architecture/runtime.md#active-sdk-catalog).
