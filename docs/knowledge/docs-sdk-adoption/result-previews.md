---
{
  "type": "Evidence",
  "id": "docs-sdk-adoption.result-previews",
  "title": "Saved-result preview metadata through the SDK",
  "evidence": {
    "path": "docs/SDK_ADOPTION.md",
    "scope": "result-previews",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-09",
    "base_revision": "fb699b8555f7cee62147794516cc7aaa224864f7",
    "limits": "Inspected the pinned SDK 2.2.0 assets.get_bulk method, used for every preview batch, its thumbnail/preview response types and those of assets.retrieve, and the adapter's bulk read and online check. MockTransport contracts prove serialization, parsing and a single attempt for retryable statuses and timeouts with synthetic fixtures only; no live endpoint, permission, field coverage, deleted-asset behavior or raw fallback is claimed or needed.",
    "sources": {
      "scenario/core/api/sdk_adapter.py": "c224d4ca17565315726553848c9bc9471ea418b52a87c271c9211dfb283ced24",
      "scenario/core/jobs/results.py": "b914e5d3dd6920d61dbfc93c44f23c65c2bec70c82b8322bfda405c200461341",
      "tests/unit/test_sdk_adapter.py": "01470f1f127241676396c4aef24f7923868203959ff004a0a1864786471c51b1",
      "tests/unit/test_scenario_sdk_contract.py": "86f187d9a40db8e145c630ccf0cf6181e6f044947675fde5189ccfef24095d30",
      "tests/unit/test_result_previews.py": "4fe845288119b74ba49b89d136777ccc5257ccf1f8a690d65f285e612f4fe01a"
    }
  }
}
---

# Saved-result preview metadata through the SDK

Evidence for [the canonical guide](../../SDK_ADOPTION.md).
