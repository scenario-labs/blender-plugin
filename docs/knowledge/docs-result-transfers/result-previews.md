---
{
  "type": "Evidence",
  "id": "docs-result-transfers.result-previews",
  "title": "Saved-result preview transfers",
  "evidence": {
    "path": "docs/RESULT_TRANSFERS.md",
    "scope": "result-previews",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-09",
    "base_revision": "fb699b8555f7cee62147794516cc7aaa224864f7",
    "limits": "Inspected reuse of the configured result downloader, host policy, byte caps, private staging, content checks and cleanup for preview stills and clips, and receipt-rehashed local copies. Offline fakes enforce the storage policy; no live CDN transfer.",
    "sources": {
      "scenario/core/jobs/result_previews.py": "c8c8574a201ddbd979126120c0ae872ecaff851a00661b2a12472991a55b9cce",
      "scenario/core/jobs/transfers.py": "36a1a3d9482bfec2ed79b2205a935198f195591b2ed64f991318dd7a21b2fb3b",
      "scenario/core/jobs/media_probe.py": "6db22b8cb051d6cabd6847b207d8380e181c80f28a5f50b2a987174bd9a95c7a",
      "scenario/core/jobs/results.py": "53b3c6b9cea1092b6011f67ac4960c199551c8d0c0aef1c76e5948c4b3401094",
      "tests/unit/test_result_previews.py": "ee00b4a254224b007ce89d6fca50fdf6806ba0381847fe93ee4bcd0b5563aa6c"
    }
  }
}
---

# Saved-result preview transfers

Evidence for [signed result downloads](../../RESULT_TRANSFERS.md).
