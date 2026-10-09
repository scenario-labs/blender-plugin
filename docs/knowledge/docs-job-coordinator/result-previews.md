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
      "scenario/core/jobs/result_previews.py": "fccebeef052749a0e98678df789f35660ebdbc37eb30b79f978e5ef68b714701",
      "scenario/core/jobs/preview_scheduler.py": "ba072b0748b5210527ed953da66794a8e3fca3617608960bc8a0a57a42d9737c",
      "scenario/core/jobs/results.py": "b914e5d3dd6920d61dbfc93c44f23c65c2bec70c82b8322bfda405c200461341",
      "scenario/core/jobs/coordinator.py": "6a61a53044ac5dcaa46ccd0c2ff2c672d275b2fbbc4b719d6881f311e69720e9",
      "scenario/core/jobs/workers.py": "39e769705a7ae81582906460f01efe648390149f67aa99352ca77e2cb6f6e98f",
      "tests/unit/test_result_previews.py": "3b1ef379ff47c48ef181da224c22db1cf1eaed3ffe4d5a161461a7ad066c4eb4",
      "tests/unit/test_preview_scheduler.py": "fc371a0b47c6036282610f4c6f11feb24770dfb9bd1e44472953255527c815e8",
      "tests/unit/test_job_workers.py": "32ea1de8ba32c30e5a1441ede694b7f740f39ab370640e1baccfd319818835f9",
      "scenario/core/jobs/transfers.py": "809323c378949b690e0cc7b1572a8e621819349e72c622f6b59f287c2bb05024"
    }
  }
}
---

# Saved-result preview commands and lane

Evidence for [the canonical guide](../../JOB_COORDINATOR.md).
