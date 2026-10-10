---
{
  "type": "Evidence",
  "id": "docs-sdk-adoption.result-previews",
  "title": "Saved-result preview metadata through the SDK",
  "evidence": {
    "path": "docs/SDK_ADOPTION.md",
    "scope": "result-previews",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-10",
    "base_revision": "33d00b0554151c4de04731fd1a5e5c64ed50855b",
    "limits": "Inspected the pinned SDK 2.2.0 assets.get_bulk method, used for every preview batch, its thumbnail/preview response types and those of assets.retrieve, and the adapter's bulk asset read and online check, both separate from the models_bulk wrapper of models.get_bulk. MockTransport contracts prove serialization, parsing and a single attempt for retryable statuses and timeouts with synthetic fixtures only; no live endpoint, permission, field coverage, deleted-asset behavior or raw fallback is claimed or needed.",
    "sources": {
      "scenario/core/api/sdk_adapter.py": "258e4fba314e2c1ac030ff65a9e63b4c0bf88c5f89e5eea4217ca0f36303b9fc",
      "scenario/core/jobs/results.py": "217d9c40dddffd5cb109313e62b27d6055526b7cbb4032eb1292ef2c6d04b92e",
      "tests/unit/test_sdk_adapter.py": "287a8ce8ebce83537cc1862d47f69b1348d477b37f9cf37e2368eac2e3ebfbb1",
      "tests/unit/test_scenario_sdk_contract.py": "bb509e1722c97fe1cf85296bbacf35d64b2599d1d211bb2ad0edc4e190277d7b",
      "tests/unit/test_result_previews.py": "937a378d1aa27ff7e9aa1ff2f086521bd62fd52d26227297029febe3d75a1fbd"
    }
  }
}
---

# Saved-result preview metadata through the SDK

Evidence for [the canonical guide](../../SDK_ADOPTION.md).
