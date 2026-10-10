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
    "limits": "Inspected reuse of the configured result downloader, host policy, byte caps, the declared Content-Length it requires because previews have no expected size, the optional cancellation event, private staging, content and still dimension checks and cleanup for preview stills and clips, transfer failures that the preview window polls again without changing the downloader's single attempt or same-host redirect rule, and receipt-rehashed local copies. Offline fakes enforce the storage policy, and mocked connections cover cancellation and a redirect to another host or a response without Content-Length, each followed by a direct answer; no live CDN transfer. Re-reviewed on 2026-10-10: the preview transfer section adds that workflow review assets use the same still transfer, their own signed url when declared within the still bounds and otherwise their thumbnail, and that a declared size over the 8 MiB cap is refused before any transfer; checked against review_sources, fetch and the review unit tests, added as a source. Only the fingerprints of touched sources that matched the base were refreshed. Re-reviewed on 2026-10-10 after two review preview fixes: the review preview unit tests gained a scheduler retry case (an intact entry reused, a lost one fetched again with one metadata read and one transfer); the claims here are unchanged and only that test file's fingerprint was refreshed.",
    "sources": {
      "scenario/core/jobs/result_previews.py": "b17c9f0ebd80e222090c0ad83339b27d7f261a7e1cb5a7bf02d2ca261d9ceb09",
      "scenario/core/jobs/transfers.py": "af6442afac9d146fab63563a04f62e97440b6eef9099b579a3f2dfe4fcae2e2c",
      "scenario/core/jobs/media_probe.py": "6db22b8cb051d6cabd6847b207d8380e181c80f28a5f50b2a987174bd9a95c7a",
      "scenario/core/jobs/results.py": "a1c52d70390adcc49900e5ef457e0c0c864e0ecb5cd313ecbc268a43994bbc95",
      "tests/unit/test_result_previews.py": "4d390e017e94382b3f80a46e8bb58da0c51b8e328bc02bf8e761cc59d6754a46",
      "tests/unit/test_result_transfers.py": "c7ce52c89e0423602fcfb8593b6b11530962169b4921a7df53cb33a8850dcf2d",
      "tests/unit/test_preview_scheduler.py": "42f7b5057fd0ef01e788a60e9201d7aad8e8e5a75e0d7b3174e11e3ed9b605dd",
      "tests/unit/test_workflow_review_previews.py": "41040fae354b6f8584513af9e9e2e029e6a746d97644452fce548634dccbc308"
    }
  }
}
---

# Saved-result preview transfers

Evidence for [signed result downloads](../../RESULT_TRANSFERS.md).
