---
{
  "type": "Evidence",
  "id": "docs-sdk-adoption.sdk-resource-extensions",
  "title": "Named SDK resource extensions",
  "description": "Optional discovery fallbacks and API-key implicit tenant scope.",
  "evidence": {
    "path": "docs/SDK_ADOPTION.md",
    "scope": "sdk-resource-extensions",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-09-26",
    "base_revision": "92d7d576b84b0c09767ca50a35cc99908666994e",
    "limits": "Inspected selected SDK 2.1.0 low-level GET response/options behavior and named teams/projects extensions. Offline tests cover explicit credential isolation, query separation, permission/lifetime, single-attempt errors, malformed responses and API-key generation without tenant parameters or discovery. No live endpoint acceptance, exhaustive discovery pagination, server principal/default-project inference or active durable-runtime integration is claimed. Neighboring Scenario MCP implementation informed the route contracts; no private records or code were copied.",
    "sources": {
      "scenario/core/api/sdk_extensions.py": "8c48acaa4a3534fe310c44eba7b76c539a5b632e1f089597516a474f25e8341a",
      "scenario/core/api/sdk_adapter.py": "0b1f4dc13f43c1cf27343064dc0c8d9cf87b43e6a403911223ee8431a3549557",
      "tests/unit/test_sdk_extensions.py": "e833a64c66d8087964b368b519a69594663d542bf4fc88c9b8ba91f01063f722",
      "tests/unit/test_scenario_sdk_contract.py": "4ef624d988934c9f57183c39519ffde5887adef65769a3431d2c2ef7988c657f",
      "tests/blender/test_sdk_bundle.py": "60d92e8726c5b7ab82b1fe9d95817ce659b1a6f4f00887e15a04b337a2c8daca"
    }
  }
}
---

# Named SDK resource extensions

Evidence for [the canonical document](../../SDK_ADOPTION.md).
