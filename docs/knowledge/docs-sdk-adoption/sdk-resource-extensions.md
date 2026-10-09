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
    "base_revision": "fb699b8555f7cee62147794516cc7aaa224864f7",
    "limits": "Inspected selected SDK 2.2.0 low-level GET/PUT response and options behavior, including per-request max_retries, and the named teams/projects (SDK issue #29) and workflow_user_selection (SDK issue #33) extensions. Offline tests cover explicit credential isolation, query separation, permission/lifetime, single-attempt errors, including the selection fallback's own max_retries=0 on an SDK client configured to retry, malformed responses, API-key generation without tenant parameters or discovery, and the dependency flags for each missing generated method. No live endpoint acceptance, exhaustive discovery pagination, server principal/default-project inference or active durable-runtime integration is claimed. Selection request semantics have their own workflow-step-decisions topic. Neighboring Scenario MCP implementation informed the discovery route contracts; the selection route follows the public API reference; no private records or code were copied.",
    "sources": {
      "scenario/core/api/sdk_extensions.py": "f82720de4f2c0c82494489dad7ddfd26e18e00b46ae3da5df86cc91fc41bb744",
      "scenario/core/api/sdk_adapter.py": "1104fbb8a78b13deafd3c5098d932da39a8fdfa9ee38707e7a96452ec72877a5",
      "tests/unit/test_sdk_extensions.py": "4770f482ae18aa01aea6ffb5525d06c7b15a48143901acb24eb9e438d83fb51b",
      "tests/unit/test_scenario_sdk_contract.py": "a23b96b3792abb83fbca65f0755e7d7c33cec08cd3f739f8cf0dc67e16ffc026",
      "tests/blender/test_sdk_bundle.py": "2b1a6d5d53eabef928518c687a8c8f2ed95e8e7ac255a0ef00e1d4ae43da88e2"
    }
  }
}
---

# Named SDK resource extensions

Evidence for [the canonical document](../../SDK_ADOPTION.md).
