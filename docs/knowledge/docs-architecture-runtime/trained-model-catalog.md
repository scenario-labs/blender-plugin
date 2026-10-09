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
    "limits": "Reviewed that bulk summaries are explicit, read once per catalog connection, shared between overlapping callers, cached apart from form schemas and cleared on retirement, that trained records are classified with a malformed type treated as unsupported rather than raised, and that lane lists and the picker keep the former LoRA exclusion while still listing private custom models. No UI, MCP or catalog-load caller uses these reads yet; native interaction, live service behavior and routing remain separate work under #97.",
    "sources": {
      "docs/architecture/runtime.md": "495ee6405983eb6dbe2d6fe32c723bf33bc366d18af97f07fecba8969db4681d",
      "scenario/core/api/catalog.py": "a3e96f97db671a1979c764a82d34557be86d66f6e9c1277900890116ef3f3781",
      "scenario/core/api/model_filter.py": "431d83e059c1575f05917e7fe2bb9b3d76a1ef73dc27e57d827e54e433697dbc",
      "scenario/core/api/sdk_catalog.py": "dd27cfd15758157a74d2a82760ce69b17a6a1377256951c5538bdd6772dacc7d",
      "tests/unit/test_catalog_lanes.py": "e47edc13227d2161a935f349791fac9951ef6c738259463de8af413186f1fd6a",
      "tests/unit/test_model_filter.py": "aae42f098958a1670858426e716f6cb2b522373e5993605d12fe0adae3abceea",
      "tests/unit/test_sdk_catalog.py": "f54a0bef971ac29b6d50c55bb99e44b447c63b88f0092460ddcc84bf07a21c97"
    }
  }
}
---

Evidence for [the active SDK catalog](../../architecture/runtime.md#active-sdk-catalog).
