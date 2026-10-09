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
    "base_revision": "33d00b0554151c4de04731fd1a5e5c64ed50855b",
    "limits": "Reviewed the published SDK 2.2.0 collections.list/retrieve/create, collections.assets.add/remove, assets.update_tags and assets.get_bulk methods, their raw-response wrappers, request bodies, query parameters, retry and idempotency behavior, including the update_tags strict=false wording that the endpoint behaves as if idempotent, which the adapter does not treat as a replay contract, and the required tags and collectionIds fields of the get_bulk response model, against the public Python SDK and API reference pages. Synthetic MockTransport tests exercise wire mapping, project scope, selected credentials, online and closed-client gating for writes and organization reads, rejection of unencodable, control, format (other than joiners between other characters) and separator characters before dispatch, status classification into rejected and uncertain outcomes, malformed, deeply nested or mismatched acknowledgements, deeply nested read bodies, the acknowledged collection ID on a renamed create, sanitized messages, exception copy and pickle, single attempts, strict read-back metadata, identifier and bulk record checks shared with models_bulk and run against both reads, and read-back reconciliation after an applied-then-lost write or a 409. The label rules are not a confusable check. No live collection, tag or bulk read request was made. Re-adding a member, DELETE body survival through the production edge, get_bulk handling of missing or inaccessible IDs and its live 200-ID cap, name uniqueness, tag and name limits and service normalization remain unverified. No coordinator, JobSession, MCP or native Library integration, desktop or release acceptance is claimed.",
    "sources": {
      "docs/SDK_ADOPTION.md": "f2470754c22cf4ae40903f8c134538122368092406c1689efc9c764cdea21a75",
      "scenario/core/api/sdk_adapter.py": "8741ed98d0d4ace8a4d1c21a65aaf79f85eeabf69023477d23fa028f4911bb95",
      "tests/unit/test_scenario_sdk_contract.py": "9946d4d0234bf828c33954932401c4e11e2b57959ef3939ca4bcfa2ea03d6463",
      "tests/unit/test_sdk_adapter_organization.py": "d09e50faacab46bebfd4b2d8f2bed87a0f498c475789e8f0ac8e57a6f41c3d6a",
      "scenario/sdk-wheel-lock.json": "1c933e40d98552b6952b8093990619e30c87cba18b5af90801d84ffd9f62dd8c",
      "uv.lock": "a7b510cd1251679c6ff54186dffd8ca2a18da32a414dc1b427715da9f411a51d"
    }
  }
}
---

Evidence for [the canonical guide](../../SDK_ADOPTION.md#asset-organization-writes).
