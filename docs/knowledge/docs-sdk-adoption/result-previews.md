---
{
  "type": "Evidence",
  "id": "docs-sdk-adoption.result-previews",
  "title": "Saved-result preview metadata through the SDK",
  "evidence": {
    "path": "docs/SDK_ADOPTION.md",
    "scope": "result-previews",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-11",
    "base_revision": "72723f02a97a7226b1c697c31d8124b77ac92c86",
    "limits": "Inspected the pinned SDK 2.2.0 assets.get_bulk method, used for every preview batch, its thumbnail/preview response types and those of assets.retrieve, and the adapter's bulk asset read and online check, both separate from the models_bulk wrapper of models.get_bulk and from asset_records, the organization read-back that also calls assets.get_bulk. MockTransport contracts prove serialization, parsing and a single attempt for retryable statuses and timeouts with synthetic fixtures only; no live endpoint, permission, field coverage, deleted-asset behavior or raw fallback is claimed or needed.",
    "sources": {
      "scenario/core/api/sdk_adapter.py": "d19509e010e0b04252b948fc035b9096b06151d6360bd76f5939a94a1c407605",
      "scenario/core/jobs/results.py": "761f48bcee7eb3de0dbc77bc59d075b273b2b866843d3ed8390434b9607fd8fe",
      "tests/unit/test_sdk_adapter.py": "287a8ce8ebce83537cc1862d47f69b1348d477b37f9cf37e2368eac2e3ebfbb1",
      "tests/unit/test_scenario_sdk_contract.py": "94d4b23fbdb5bc0dd3c540b8daa8cf62191fdcdb1ac2e302f1a7cc97a6be67ae",
      "tests/unit/test_result_previews.py": "4d390e017e94382b3f80a46e8bb58da0c51b8e328bc02bf8e761cc59d6754a46"
    }
  }
}
---

# Saved-result preview metadata through the SDK

Evidence for [the canonical guide](../../SDK_ADOPTION.md).
