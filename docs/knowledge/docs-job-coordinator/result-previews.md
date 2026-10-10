---
{
  "type": "Evidence",
  "id": "docs-job-coordinator.result-previews",
  "title": "Saved-result preview commands and lane",
  "evidence": {
    "path": "docs/JOB_COORDINATOR.md",
    "scope": "result-previews",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-11",
    "base_revision": "72723f02a97a7226b1c697c31d8124b77ac92c86",
    "limits": "Inspected preview target reads, the batch, publication, discard and maintenance-only commands, bulk metadata reads for every batch size, receipt rechecks, transfer failures reported pending until the final poll while receipt and content failures fail at once, cancellation passed to preview transfers and inactive-coordinator cleanup, and the dedicated preview thread's admission, cancellation, idleness, retirement and shutdown. Offline unit tests only for these commands; no job state transition or revision change is made. Live provider behavior, UI and MCP wiring are outside this topic. Re-reviewed on 2026-10-10: the preview commands section adds review_preview_targets (store-only; 1 to 50 distinct IDs of a remote workflow job; review keys without a receipt) and the batch's recheck of the same remote workflow job; checked against coordinator.py, results.py and the review unit tests, added as a source. Only the fingerprints of touched sources that matched the base were refreshed. Re-reviewed on 2026-10-10 after two review preview fixes: the review preview unit tests gained a scheduler retry case (an intact entry reused, a lost one fetched again with one metadata read and one transfer); the claims here are unchanged and only that test file's fingerprint was refreshed.",
    "sources": {
      "scenario/core/jobs/result_previews.py": "b17c9f0ebd80e222090c0ad83339b27d7f261a7e1cb5a7bf02d2ca261d9ceb09",
      "scenario/core/jobs/preview_scheduler.py": "aedd1fa55614dd342688a15bba9639fb31f10590d2bbd7dfd4be2344912641d2",
      "scenario/core/jobs/results.py": "a1c52d70390adcc49900e5ef457e0c0c864e0ecb5cd313ecbc268a43994bbc95",
      "scenario/core/jobs/coordinator.py": "aa0524bec5371d0541829223babd29cdf78f3bbca5231d1de1d5179afff2bd58",
      "scenario/core/jobs/workers.py": "dece4686af0b0889b99341a99d6d5143d48cdf63919fecef90299b834fbe9bc3",
      "tests/unit/test_result_previews.py": "4d390e017e94382b3f80a46e8bb58da0c51b8e328bc02bf8e761cc59d6754a46",
      "tests/unit/test_preview_scheduler.py": "42f7b5057fd0ef01e788a60e9201d7aad8e8e5a75e0d7b3174e11e3ed9b605dd",
      "tests/unit/test_job_workers.py": "32ea1de8ba32c30e5a1441ede694b7f740f39ab370640e1baccfd319818835f9",
      "scenario/core/jobs/transfers.py": "af6442afac9d146fab63563a04f62e97440b6eef9099b579a3f2dfe4fcae2e2c",
      "tests/unit/test_workflow_review_previews.py": "41040fae354b6f8584513af9e9e2e029e6a746d97644452fce548634dccbc308"
    }
  }
}
---

# Saved-result preview commands and lane

Evidence for [the canonical guide](../../JOB_COORDINATOR.md).
