---
{
  "type": "Evidence",
  "id": "docs-job-coordinator.result-previews",
  "title": "Saved-result preview commands and lane",
  "evidence": {
    "path": "docs/JOB_COORDINATOR.md",
    "scope": "result-previews",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-09",
    "base_revision": "fb699b8555f7cee62147794516cc7aaa224864f7",
    "limits": "Inspected preview target reads, the batch, publication and discard commands, bulk metadata reads for every batch size, receipt rechecks, cancellation passed to preview transfers and inactive-coordinator cleanup, and the dedicated preview thread's admission, cancellation, idleness, retirement and shutdown. Offline unit tests only for these commands; no job state transition or revision change is made. Live provider behavior, UI and MCP wiring are outside this topic.",
    "sources": {
      "scenario/core/jobs/result_previews.py": "792b330dcb9007e9b4500cdca119e8122eb93a1c64e9e9fbcf881a96650c689c",
      "scenario/core/jobs/preview_scheduler.py": "cb75fc5ff870438352430c331ea7a2a4a5d9da307dfb44ad9a44bfbdb2c5e7dc",
      "scenario/core/jobs/results.py": "b914e5d3dd6920d61dbfc93c44f23c65c2bec70c82b8322bfda405c200461341",
      "scenario/core/jobs/coordinator.py": "6a61a53044ac5dcaa46ccd0c2ff2c672d275b2fbbc4b719d6881f311e69720e9",
      "scenario/core/jobs/workers.py": "39e769705a7ae81582906460f01efe648390149f67aa99352ca77e2cb6f6e98f",
      "tests/unit/test_result_previews.py": "076c04df828fe9068be328f754da0c01dc8c3134d1bd2d6065d33ee01971ee0d",
      "tests/unit/test_preview_scheduler.py": "2e5b9b8a67e24ea8afe20c954b8ac6d66092e4ed57a6c0846e357e7e5b9ff463",
      "tests/unit/test_job_workers.py": "32ea1de8ba32c30e5a1441ede694b7f740f39ab370640e1baccfd319818835f9",
      "scenario/core/jobs/transfers.py": "809323c378949b690e0cc7b1572a8e621819349e72c622f6b59f287c2bb05024"
    }
  }
}
---

# Saved-result preview commands and lane

Evidence for [the canonical guide](../../JOB_COORDINATOR.md).
