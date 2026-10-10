---
{
  "type": "Evidence",
  "id": "docs-sdk-adoption.asset-organization-writes",
  "title": "Scoped asset organization writes in the SDK adapter",
  "evidence": {
    "path": "docs/SDK_ADOPTION.md",
    "scope": "asset-organization-writes",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-10",
    "base_revision": "33d00b0554151c4de04731fd1a5e5c64ed50855b",
    "limits": "Reviewed the published SDK 2.2.0 collections.list/retrieve/create, collections.assets.add/remove, assets.update_tags and assets.get_bulk methods, their raw-response wrappers, request bodies, query parameters, retry and idempotency behavior, including the update_tags strict=false wording that the endpoint behaves as if idempotent, which the adapter does not treat as a replay contract, the add docstring's 49-asset cap, the decoded JSON or text body that APIStatusError exposes for a refused add, and the required tags and collectionIds fields of the get_bulk response model, against the public Python SDK and API reference pages. Synthetic MockTransport tests exercise wire mapping, project scope, selected credentials, online and closed-client gating for writes and organization reads, rejection of unencodable, control, format (other than joiners between other characters) and separator characters before dispatch, status classification into rejected and uncertain outcomes, the AlreadyMembers subclass raised only for an add refused with HTTP 400 and the exact already-member reason (other reasons, non-JSON bodies, non-string reasons, other statuses and other endpoints stay plain), malformed, deeply nested or mismatched acknowledgements, deeply nested read bodies, the acknowledged collection ID on a renamed create, sanitized messages that never echo the body, exception copy and pickle, single attempts, strict read-back metadata, identifier and bulk record checks shared with models_bulk and run against both reads, and read-back reconciliation after an applied-then-lost write, an already-member refusal that wrote nothing, or a 409. The already-member 400, its reason text, the one-transaction add and the 400 above 49 IDs are documented as observed on the service by the hosted Scenario MCP, not as an API reference contract; no live collection, tag or bulk read request was made from this repository to confirm them. The label rules are not a confusable check. DELETE body survival through the production edge, removal of a non-member, get_bulk handling of missing or inaccessible IDs and its live 200-ID cap, name uniqueness, tag and name limits and service normalization remain unverified. No coordinator, JobSession, MCP or native Library integration, desktop or release acceptance is claimed.",
    "sources": {
      "docs/SDK_ADOPTION.md": "94007fff6ebc8c49def727974a11091cc55c3f4de7f63fcf4195b54cfaf0d6d7",
      "scenario/core/api/sdk_adapter.py": "43eb582d077677e2975c21e13cd3164b319c96f14a36988c6b9f04ca56124121",
      "tests/unit/test_scenario_sdk_contract.py": "d7159a4b43550bf7e5411e72658a001311f810ce6786b41f41f6da6eb491addc",
      "tests/unit/test_sdk_adapter_organization.py": "0b5a891b4b197eb3208eeb88444f6bbb705422940d8f53f264fe640192152c7e",
      "scenario/sdk-wheel-lock.json": "1c933e40d98552b6952b8093990619e30c87cba18b5af90801d84ffd9f62dd8c",
      "uv.lock": "a7b510cd1251679c6ff54186dffd8ca2a18da32a414dc1b427715da9f411a51d"
    }
  }
}
---

Evidence for [the canonical guide](../../SDK_ADOPTION.md#asset-organization-writes).
