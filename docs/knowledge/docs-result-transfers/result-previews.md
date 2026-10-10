---
{
  "type": "Evidence",
  "id": "docs-result-transfers.result-previews",
  "title": "Saved-result preview transfers",
  "evidence": {
    "path": "docs/RESULT_TRANSFERS.md",
    "scope": "result-previews",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-10",
    "base_revision": "33d00b0554151c4de04731fd1a5e5c64ed50855b",
    "limits": "Inspected reuse of the configured result downloader, host policy, byte caps, the optional cancellation event, private staging, content and still dimension checks and cleanup for preview stills and clips, transfer failures that the preview window polls again without changing the downloader's single attempt or same-host redirect rule, and receipt-rehashed local copies. Offline fakes enforce the storage policy, and mocked connections cover cancellation and a redirect to another host followed by a direct answer; no live CDN transfer.",
    "sources": {
      "scenario/core/jobs/result_previews.py": "d33234f02a85f67a573ca1d097ebd8921578ba3c38047811249ac4484367c7d3",
      "scenario/core/jobs/transfers.py": "809323c378949b690e0cc7b1572a8e621819349e72c622f6b59f287c2bb05024",
      "scenario/core/jobs/media_probe.py": "6db22b8cb051d6cabd6847b207d8380e181c80f28a5f50b2a987174bd9a95c7a",
      "scenario/core/jobs/results.py": "217d9c40dddffd5cb109313e62b27d6055526b7cbb4032eb1292ef2c6d04b92e",
      "tests/unit/test_result_previews.py": "937a378d1aa27ff7e9aa1ff2f086521bd62fd52d26227297029febe3d75a1fbd",
      "tests/unit/test_result_transfers.py": "2b412aed88b59ed5233a95aedb7bbca69de89b900f694b14205fb18f937fb8af",
      "tests/unit/test_preview_scheduler.py": "3dc08f8f31f906e3926a84ee1eaa7ad99cf146ba7ebbcae0e1941c8af89f58e8"
    }
  }
}
---

# Saved-result preview transfers

Evidence for [signed result downloads](../../RESULT_TRANSFERS.md).
