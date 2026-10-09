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
    "base_revision": "33d00b0554151c4de04731fd1a5e5c64ed50855b",
    "limits": "Inspected selected SDK 2.2.0 low-level GET/PUT response and options behavior, including per-request max_retries, and the named teams/projects (SDK issue #29) and workflow_user_selection (SDK issue #33) extensions. Offline tests cover explicit credential isolation, query separation, permission/lifetime, single-attempt errors, including the selection fallback's own max_retries=0 on an SDK client configured to retry, malformed responses, API-key generation without tenant parameters or discovery, and the dependency flags for each missing generated method. No live endpoint acceptance, exhaustive discovery pagination, server principal/default-project inference or active durable-runtime integration is claimed. Selection request semantics have their own workflow-step-decisions topic. Re-reviewed after rebasing on #352 and #357: extension requests share the adapter's status mapping, so their status failures raise AdapterStatusError with the credential, project and rate-limit text; discovery sends no project and never names the Project ID; the #357 contract additions (private trained lists, models.get_bulk, model 403/404) use generated methods and add no extension. Neighboring Scenario MCP implementation informed the discovery route contracts; the selection route follows the public API reference; no private records or code were copied.",
    "sources": {
      "scenario/core/api/sdk_extensions.py": "f82720de4f2c0c82494489dad7ddfd26e18e00b46ae3da5df86cc91fc41bb744",
      "scenario/core/api/sdk_adapter.py": "82d37a4f38b72726ca0060ee0cf66e769cec758f96a166aeeed92580d3fe0a08",
      "tests/unit/test_sdk_extensions.py": "2e87d523c0836944b0ac5ecc05cfd4edb579a72f7b511bd855b0e59f13550b70",
      "tests/unit/test_scenario_sdk_contract.py": "3b126ec239e38d0e5482c15fafdb93ab3326418e0b3ae966ded3ea3d90d75070",
      "tests/blender/test_sdk_bundle.py": "2b1a6d5d53eabef928518c687a8c8f2ed95e8e7ac255a0ef00e1d4ae43da88e2"
    }
  }
}
---

# Named SDK resource extensions

Evidence for [the canonical document](../../SDK_ADOPTION.md).
