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
    "limits": "Inspected the pinned SDK 2.2.0 assets.get_bulk method, used for every preview batch, its thumbnail/preview response types and those of assets.retrieve, and the adapter's bulk asset read and online check, both separate from the models_bulk wrapper of models.get_bulk and from asset_records, the organization read-back that also calls assets.get_bulk. MockTransport contracts prove serialization, parsing and a single attempt for retryable statuses and timeouts with synthetic fixtures only; no live endpoint, permission, field coverage, deleted-asset behavior or raw fallback is claimed or needed. Re-reviewed on 2026-10-10: the operation table row adds that stills of a waiting workflow step's review assets use the same get_bulk read and signed transport; checked against results.py, where review targets reuse _preview_metadata and bulk_assets, and the review unit tests, added as a source. The adapter is unchanged; only the fingerprints of touched sources that matched the base were refreshed.",
    "sources": {
      "scenario/core/api/sdk_adapter.py": "d19509e010e0b04252b948fc035b9096b06151d6360bd76f5939a94a1c407605",
      "scenario/core/jobs/results.py": "a1c52d70390adcc49900e5ef457e0c0c864e0ecb5cd313ecbc268a43994bbc95",
      "tests/unit/test_sdk_adapter.py": "287a8ce8ebce83537cc1862d47f69b1348d477b37f9cf37e2368eac2e3ebfbb1",
      "tests/unit/test_scenario_sdk_contract.py": "94d4b23fbdb5bc0dd3c540b8daa8cf62191fdcdb1ac2e302f1a7cc97a6be67ae",
      "tests/unit/test_result_previews.py": "4d390e017e94382b3f80a46e8bb58da0c51b8e328bc02bf8e761cc59d6754a46",
      "tests/unit/test_workflow_review_previews.py": "12fb0b5f4f8cd6f15c5868996ef108f01192fadf4e9f70f1b62f1b0c6a38a83e"
    }
  }
}
---

# Saved-result preview metadata through the SDK

Evidence for [the canonical guide](../../SDK_ADOPTION.md).
