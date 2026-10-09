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
    "base_revision": "ad143c8e2406123217888301badcb49638033fd8",
    "limits": "Inspected preview target reads, the batch, publication and discard commands, bulk metadata reads for every batch size, receipt rechecks, cancellation passed to preview transfers and inactive-coordinator cleanup, and the dedicated preview thread's admission, cancellation, idleness, retirement and shutdown. Offline unit tests only for these commands; no job state transition or revision change is made. Live provider behavior, UI and MCP wiring are outside this topic.",
    "sources": {
      "scenario/core/jobs/result_previews.py": "afd49b8052fd0953c1b1fe10b8a8f3f6fd6e383a7d5ddd6647aa4f00e002d893",
      "scenario/core/jobs/preview_scheduler.py": "f9e20eaa003f7baafee3d8ddb78730b459741b2330bc8a21e9b6dff140efdc03",
      "scenario/core/jobs/results.py": "b914e5d3dd6920d61dbfc93c44f23c65c2bec70c82b8322bfda405c200461341",
      "scenario/core/jobs/coordinator.py": "6a61a53044ac5dcaa46ccd0c2ff2c672d275b2fbbc4b719d6881f311e69720e9",
      "scenario/core/jobs/workers.py": "39e769705a7ae81582906460f01efe648390149f67aa99352ca77e2cb6f6e98f",
      "tests/unit/test_result_previews.py": "d34505132b8d4474911889ac697e848d3653593fa34ddb0eac3fb62794e9f830",
      "tests/unit/test_preview_scheduler.py": "8ff8325a17caa7dc79bd67d40d750d710163da0dd99a3e69eec25fde2c8d9b73",
      "tests/unit/test_job_workers.py": "32ea1de8ba32c30e5a1441ede694b7f740f39ab370640e1baccfd319818835f9",
      "scenario/core/jobs/transfers.py": "809323c378949b690e0cc7b1572a8e621819349e72c622f6b59f287c2bb05024"
    }
  }
}
---

# Saved-result preview commands and lane

Evidence for [the canonical guide](../../JOB_COORDINATOR.md).
