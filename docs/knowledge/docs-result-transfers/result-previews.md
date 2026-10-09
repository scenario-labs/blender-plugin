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
    "limits": "Inspected reuse of the configured result downloader, host policy, byte caps, the optional cancellation event, private staging, content and still dimension checks and cleanup for preview stills and clips, and receipt-rehashed local copies. Offline fakes enforce the storage policy and a mocked connection covers cancellation; no live CDN transfer.",
    "sources": {
      "scenario/core/jobs/result_previews.py": "792b330dcb9007e9b4500cdca119e8122eb93a1c64e9e9fbcf881a96650c689c",
      "scenario/core/jobs/transfers.py": "809323c378949b690e0cc7b1572a8e621819349e72c622f6b59f287c2bb05024",
      "scenario/core/jobs/media_probe.py": "6db22b8cb051d6cabd6847b207d8380e181c80f28a5f50b2a987174bd9a95c7a",
      "scenario/core/jobs/results.py": "b914e5d3dd6920d61dbfc93c44f23c65c2bec70c82b8322bfda405c200461341",
      "tests/unit/test_result_previews.py": "076c04df828fe9068be328f754da0c01dc8c3134d1bd2d6065d33ee01971ee0d",
      "tests/unit/test_result_transfers.py": "2b412aed88b59ed5233a95aedb7bbca69de89b900f694b14205fb18f937fb8af"
    }
  }
}
---

# Saved-result preview transfers

Evidence for [signed result downloads](../../RESULT_TRANSFERS.md).
