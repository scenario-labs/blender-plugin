---
{
  "type": "Evidence",
  "id": "docs-sdk-adoption.asset-organization-writes",
  "title": "Scoped asset organization writes in the SDK adapter",
  "evidence": {
    "path": "docs/SDK_ADOPTION.md",
    "scope": "asset-organization-writes",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-09",
    "base_revision": "b57c398f35fb2148c82fb8b26f6a40564d3f52ef",
    "limits": "Reviewed the published SDK 2.2.0 collections.list/retrieve/create, collections.assets.add/remove, assets.update_tags and assets.get_bulk methods, their raw-response wrappers, request bodies, query parameters and retry and idempotency behavior, against the public Python SDK and API reference pages. Synthetic MockTransport tests exercise wire mapping, project scope, selected credentials, online and closed-client gating, status classification into rejected and uncertain outcomes, malformed or mismatched acknowledgements, sanitized messages, single attempts and read-back reconciliation after an applied-then-lost write or a 409. No live collection, tag or bulk read request was made. Re-adding a member, DELETE body survival through the production edge, name uniqueness, tag and name limits and service normalization remain unverified. No coordinator, JobSession, MCP or native Library integration, desktop or release acceptance is claimed.",
    "sources": {
      "docs/SDK_ADOPTION.md": "50d30b0ccb9cb19268f78e3e50730783b6a59f6f6fdf178256fb5283a5908cce",
      "scenario/core/api/sdk_adapter.py": "124e92fe4900563890e8b87d24a863607724e2a80dc2c75ea441c8f471c4e789",
      "tests/unit/test_scenario_sdk_contract.py": "3d191ec2818c3bb0e9f1e6f70a5f6e99d0d4907e32880c4d36c5356d0f9d577f",
      "tests/unit/test_sdk_adapter_organization.py": "d243d6dc2feb0c380b2ffb37b4ab480168eecd63eca466923878744e337f1216",
      "scenario/sdk-wheel-lock.json": "1c933e40d98552b6952b8093990619e30c87cba18b5af90801d84ffd9f62dd8c",
      "uv.lock": "a7b510cd1251679c6ff54186dffd8ca2a18da32a414dc1b427715da9f411a51d"
    }
  }
}
---

Evidence for [the canonical guide](../../SDK_ADOPTION.md#asset-organization-writes).
