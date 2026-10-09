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
    "limits": "Reviewed the published SDK 2.2.0 collections.list/retrieve/create, collections.assets.add/remove, assets.update_tags and assets.get_bulk methods, their raw-response wrappers, request bodies, query parameters, retry and idempotency behavior, and the required tags and collectionIds fields of the get_bulk response model, against the public Python SDK and API reference pages. Synthetic MockTransport tests exercise wire mapping, project scope, selected credentials, online and closed-client gating, rejection of unencodable, control, bidirectional, invisible and separator characters before dispatch, status classification into rejected and uncertain outcomes, malformed or mismatched acknowledgements, the acknowledged collection ID on a renamed create, sanitized messages, exception copy and pickle, single attempts, strict read-back metadata and read-back reconciliation after an applied-then-lost write or a 409. No live collection, tag or bulk read request was made. Re-adding a member, DELETE body survival through the production edge, get_bulk handling of missing or inaccessible IDs and its live 200-ID cap, name uniqueness, tag and name limits and service normalization remain unverified. No coordinator, JobSession, MCP or native Library integration, desktop or release acceptance is claimed.",
    "sources": {
      "docs/SDK_ADOPTION.md": "1bdf93452c8b58622be485df9687f2e7b9743ec154e8ec368cc59f81ac5dbce6",
      "scenario/core/api/sdk_adapter.py": "53d14b9ee932af6e24b5ddae855b8436188324dea2eedc9df461f68cea5635da",
      "tests/unit/test_scenario_sdk_contract.py": "5927cc6b76d594914e65b3cb5110abc662c615f374abb4cdfe1d137325188072",
      "tests/unit/test_sdk_adapter_organization.py": "7a9daced9e2ee9e357def7f5232578f0d0a2ee45dcfd805c9767d0cb67b41917",
      "scenario/sdk-wheel-lock.json": "1c933e40d98552b6952b8093990619e30c87cba18b5af90801d84ffd9f62dd8c",
      "uv.lock": "a7b510cd1251679c6ff54186dffd8ca2a18da32a414dc1b427715da9f411a51d"
    }
  }
}
---

Evidence for [the canonical guide](../../SDK_ADOPTION.md#asset-organization-writes).
