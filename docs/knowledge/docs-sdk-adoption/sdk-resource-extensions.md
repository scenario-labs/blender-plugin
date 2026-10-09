---
{
  "type": "Evidence",
  "id": "docs-sdk-adoption.sdk-resource-extensions",
  "title": "Named SDK resource extensions",
  "description": "Optional discovery and workflow user-selection fallbacks, and API-key implicit tenant scope.",
  "evidence": {
    "path": "docs/SDK_ADOPTION.md",
    "scope": "sdk-resource-extensions",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-09",
    "base_revision": "b57c398f35fb2148c82fb8b26f6a40564d3f52ef",
    "limits": "Inspected selected SDK 2.2.0 low-level GET/PUT response and options behavior, including per-request max_retries, and the named teams/projects (SDK issue #29) and workflow_user_selection (SDK issue #33) extensions. Offline tests cover explicit credential isolation, query separation, permission/lifetime, single-attempt errors, malformed responses, API-key generation without tenant parameters or discovery, and the dependency flags for each missing generated method. No live endpoint acceptance, exhaustive discovery pagination, server principal/default-project inference or active durable-runtime integration is claimed. Selection request semantics have their own workflow-step-decisions topic. Neighboring Scenario MCP implementation informed the discovery route contracts; the selection route follows the public API reference; no private records or code were copied.",
    "sources": {
      "scenario/core/api/sdk_extensions.py": "f82720de4f2c0c82494489dad7ddfd26e18e00b46ae3da5df86cc91fc41bb744",
      "scenario/core/api/sdk_adapter.py": "3c8615df80c9beb688f689c4ab6fd14f2bc49640c72d2ea4a842aba7d1b6dc7e",
      "tests/unit/test_sdk_extensions.py": "58bc9de1ed02dd4ae4b36645d3e87858af593a466db80411d96fcf878d0522ac",
      "tests/unit/test_scenario_sdk_contract.py": "a23b96b3792abb83fbca65f0755e7d7c33cec08cd3f739f8cf0dc67e16ffc026",
      "tests/blender/test_sdk_bundle.py": "2b1a6d5d53eabef928518c687a8c8f2ed95e8e7ac255a0ef00e1d4ae43da88e2"
    }
  }
}
---

# Named SDK resource extensions

Evidence for [the canonical document](../../SDK_ADOPTION.md).
