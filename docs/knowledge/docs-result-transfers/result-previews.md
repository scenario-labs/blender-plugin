---
{
  "type": "Evidence",
  "id": "docs-result-transfers.result-previews",
  "title": "Saved-result preview transfers",
  "evidence": {
    "path": "docs/RESULT_TRANSFERS.md",
    "scope": "result-previews",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-11",
    "base_revision": "72723f02a97a7226b1c697c31d8124b77ac92c86",
    "limits": "Inspected reuse of the configured result downloader, host policy, byte caps, the declared Content-Length it requires because previews have no expected size, the optional cancellation event, private staging, content and still dimension checks and cleanup for preview stills and clips, transfer failures that the preview window polls again without changing the downloader's single attempt or same-host redirect rule, and receipt-rehashed local copies. Offline fakes enforce the storage policy, and mocked connections cover cancellation and a redirect to another host or a response without Content-Length, each followed by a direct answer; no live CDN transfer.",
    "sources": {
      "scenario/core/jobs/result_previews.py": "d33234f02a85f67a573ca1d097ebd8921578ba3c38047811249ac4484367c7d3",
      "scenario/core/jobs/transfers.py": "af6442afac9d146fab63563a04f62e97440b6eef9099b579a3f2dfe4fcae2e2c",
      "scenario/core/jobs/media_probe.py": "6db22b8cb051d6cabd6847b207d8380e181c80f28a5f50b2a987174bd9a95c7a",
      "scenario/core/jobs/results.py": "761f48bcee7eb3de0dbc77bc59d075b273b2b866843d3ed8390434b9607fd8fe",
      "tests/unit/test_result_previews.py": "4d390e017e94382b3f80a46e8bb58da0c51b8e328bc02bf8e761cc59d6754a46",
      "tests/unit/test_result_transfers.py": "c7ce52c89e0423602fcfb8593b6b11530962169b4921a7df53cb33a8850dcf2d",
      "tests/unit/test_preview_scheduler.py": "42f7b5057fd0ef01e788a60e9201d7aad8e8e5a75e0d7b3174e11e3ed9b605dd"
    }
  }
}
---

# Saved-result preview transfers

Evidence for [signed result downloads](../../RESULT_TRANSFERS.md).
