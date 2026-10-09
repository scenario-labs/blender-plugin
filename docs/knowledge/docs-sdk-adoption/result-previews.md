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
    "limits": "Inspected the pinned SDK 2.2.0 assets.retrieve and assets.get_bulk methods and their thumbnail/preview response types, and the adapter's bulk read and online check. MockTransport contracts prove serialization and parsing of synthetic fixtures only; no live endpoint, permission, field coverage or raw fallback is claimed or needed.",
    "sources": {
      "scenario/core/api/sdk_adapter.py": "c224d4ca17565315726553848c9bc9471ea418b52a87c271c9211dfb283ced24",
      "scenario/core/jobs/results.py": "53b3c6b9cea1092b6011f67ac4960c199551c8d0c0aef1c76e5948c4b3401094",
      "tests/unit/test_sdk_adapter.py": "be011d917f4bab08ebec945725ca974467f794db559a4bbc0cbecd1cb56597da",
      "tests/unit/test_scenario_sdk_contract.py": "86f187d9a40db8e145c630ccf0cf6181e6f044947675fde5189ccfef24095d30",
      "tests/unit/test_result_previews.py": "ee00b4a254224b007ce89d6fca50fdf6806ba0381847fe93ee4bcd0b5563aa6c"
    }
  }
}
---

# Saved-result preview metadata through the SDK

Evidence for [the canonical guide](../../SDK_ADOPTION.md).
