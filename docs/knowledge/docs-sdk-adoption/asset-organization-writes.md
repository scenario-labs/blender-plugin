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
    "base_revision": "fb699b8555f7cee62147794516cc7aaa224864f7",
    "limits": "Reviewed the published SDK 2.2.0 collections.list/retrieve/create, collections.assets.add/remove, assets.update_tags and assets.get_bulk methods, their raw-response wrappers, request bodies, query parameters, retry and idempotency behavior, including the update_tags strict=false wording that the endpoint behaves as if idempotent, which the adapter does not treat as a replay contract, and the required tags and collectionIds fields of the get_bulk response model, against the public Python SDK and API reference pages. Synthetic MockTransport tests exercise wire mapping, project scope, selected credentials, online and closed-client gating for writes and organization reads, rejection of unencodable, control, format (other than joiners between other characters) and separator characters before dispatch, status classification into rejected and uncertain outcomes, malformed, deeply nested or mismatched acknowledgements, deeply nested read bodies, the acknowledged collection ID on a renamed create, sanitized messages, exception copy and pickle, single attempts, strict read-back metadata and read-back reconciliation after an applied-then-lost write or a 409. The label rules are not a confusable check. No live collection, tag or bulk read request was made. Re-adding a member, DELETE body survival through the production edge, get_bulk handling of missing or inaccessible IDs and its live 200-ID cap, name uniqueness, tag and name limits and service normalization remain unverified. No coordinator, JobSession, MCP or native Library integration, desktop or release acceptance is claimed.",
    "sources": {
      "docs/SDK_ADOPTION.md": "dec1858e21b3d4c090088b7064702c6c096dd3cc319ed8284c60d5a1c88dda7a",
      "scenario/core/api/sdk_adapter.py": "759a1ab059f3156b03ae7b5ea57da1eb4e90fd43b8f1771047a8a7acd87af541",
      "tests/unit/test_scenario_sdk_contract.py": "5927cc6b76d594914e65b3cb5110abc662c615f374abb4cdfe1d137325188072",
      "tests/unit/test_sdk_adapter_organization.py": "97c79751380c580a8046cc2032dec7df91fddf7adf02d5d2b4a93d0304cff9cc",
      "scenario/sdk-wheel-lock.json": "1c933e40d98552b6952b8093990619e30c87cba18b5af90801d84ffd9f62dd8c",
      "uv.lock": "a7b510cd1251679c6ff54186dffd8ca2a18da32a414dc1b427715da9f411a51d"
    }
  }
}
---

Evidence for [the canonical guide](../../SDK_ADOPTION.md#asset-organization-writes).
