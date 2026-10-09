---
{
  "type": "Evidence",
  "id": "docs-sdk-adoption.sdk-upgrade-contract",
  "title": "SDK version and extension contract",
  "description": "Current SDK release and named extension workflow.",
  "evidence": {
    "path": "docs/SDK_ADOPTION.md",
    "scope": "sdk-upgrade-contract",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-09",
    "base_revision": "b57c398f35fb2148c82fb8b26f6a40564d3f52ef",
    "limits": "Scoped review of SDK 2.2.0 pin, wheel hash, unchanged runtime dependency closure and MIT notice, adopted method signatures and raw response/query contracts. Estimates use the documented string true and submission omits dryRun. The authentication workaround, missing discovery resources (SDK issue #29) and missing workflows.user_selection (SDK issue #33) remain tracked; the unit dependency contracts flag each missing generated method for review on upgrade, and the installed-bundle test also flags user_selection. The 2026-10-09 review rechecked drift since the original upgrade review: the manifest changed only its website link and still bundles scenario_sdk-2.2.0; later adapter and contract-test changes for prompt/translate, asset library reads and workflow decisions keep dry_run \"true\" for estimates, omission for submissions and zero retries. This record updates current SDK-version references only; unrelated implementation claims retain their prior evidence. No live service or paid acceptance is claimed.",
    "sources": {
      "pyproject.toml": "b60c17fedfd6a9ee2ceb6c3093247fa08f513ae32aa0e59a4a90173da61e4672",
      "uv.lock": "a7b510cd1251679c6ff54186dffd8ca2a18da32a414dc1b427715da9f411a51d",
      "scenario/sdk-wheel-lock.json": "1c933e40d98552b6952b8093990619e30c87cba18b5af90801d84ffd9f62dd8c",
      "scenario/blender_manifest.toml": "5f57a656085a4c092c3c5fe17d136ac200c378c7058b06fb192ce056c4e3f41c",
      "scenario/core/api/sdk_adapter.py": "1104fbb8a78b13deafd3c5098d932da39a8fdfa9ee38707e7a96452ec72877a5",
      "tests/unit/test_scenario_sdk_contract.py": "a23b96b3792abb83fbca65f0755e7d7c33cec08cd3f739f8cf0dc67e16ffc026",
      "tests/unit/test_wheel_bundle.py": "59b7da96a9afc57f0f288a1ad915b0a134b4fcc4aeae0cf9b1807db59dfd64c1",
      "tests/blender/test_sdk_bundle.py": "2b1a6d5d53eabef928518c687a8c8f2ed95e8e7ac255a0ef00e1d4ae43da88e2"
    }
  }
}
---

# SDK version and extension contract

Evidence for [the canonical document](../../SDK_ADOPTION.md).
