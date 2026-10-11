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
    "reviewed_at": "2026-10-11",
    "base_revision": "72723f02a97a7226b1c697c31d8124b77ac92c86",
    "limits": "Inspected selected SDK 2.2.0 low-level GET/PUT response and options behavior, including per-request max_retries, and the named teams/projects (SDK issue #29) and workflow_user_selection (SDK issue #33) extensions. Offline tests cover explicit credential isolation, query separation, permission/lifetime, single-attempt errors, including the selection fallback's own max_retries=0 on an SDK client configured to retry, malformed responses, API-key generation without tenant parameters or discovery, and the dependency flags for each missing generated method. No live endpoint acceptance, exhaustive discovery pagination, server principal/default-project inference or active durable-runtime integration is claimed. Selection request semantics have their own workflow-step-decisions topic. Re-reviewed after rebasing on #352 and #357: extension requests share the adapter's status mapping, so their status failures raise AdapterStatusError with the credential, project and rate-limit text; discovery sends no project and never names the Project ID; the #357 contract additions (private trained lists, models.get_bulk, model 403/404) use generated methods and add no extension. Neighboring Scenario MCP implementation informed the discovery route contracts; the selection route follows the public API reference; no private records or code were copied. Re-reviewed on 72723f02 after #355: collection list, retrieve and create, collection membership add and remove, assets.update_tags and assets.get_bulk are generated 2.2.0 raw-response methods on the configured client and add no extension; the extension methods, their status mapping and the dependency flags are unchanged.",
    "sources": {
      "scenario/core/api/sdk_extensions.py": "f82720de4f2c0c82494489dad7ddfd26e18e00b46ae3da5df86cc91fc41bb744",
      "scenario/core/api/sdk_adapter.py": "f541b2eaa8ea8dbdcb9636a161961f33239b4f3febe63ca1a1a54e5e57071628",
      "tests/unit/test_sdk_extensions.py": "2e87d523c0836944b0ac5ecc05cfd4edb579a72f7b511bd855b0e59f13550b70",
      "tests/unit/test_scenario_sdk_contract.py": "f95d78222688a19c98ade0595afc24375e2d38784e58a6a557b67dff64a2e4fd",
      "tests/blender/test_sdk_bundle.py": "2b1a6d5d53eabef928518c687a8c8f2ed95e8e7ac255a0ef00e1d4ae43da88e2"
    }
  }
}
---

# Named SDK resource extensions

Evidence for [the canonical document](../../SDK_ADOPTION.md).
