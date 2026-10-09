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
    "limits": "Inspected preview target reads, the batch, publication and discard commands, receipt rechecks, cancellation and inactive-coordinator cleanup, and the dedicated preview thread's admission, cancellation, retirement and shutdown. Offline unit tests only for these commands; no job state transition or revision change is made. Live provider behavior, UI and MCP wiring are outside this topic.",
    "sources": {
      "scenario/core/jobs/result_previews.py": "c8c8574a201ddbd979126120c0ae872ecaff851a00661b2a12472991a55b9cce",
      "scenario/core/jobs/preview_scheduler.py": "4a8d4924e4e959be28ab314ddce976f5e7290cf461ae8e784475e185da0d28f7",
      "scenario/core/jobs/results.py": "53b3c6b9cea1092b6011f67ac4960c199551c8d0c0aef1c76e5948c4b3401094",
      "scenario/core/jobs/coordinator.py": "6a61a53044ac5dcaa46ccd0c2ff2c672d275b2fbbc4b719d6881f311e69720e9",
      "scenario/core/jobs/workers.py": "ff77957be1e66ca7f24abc04b9378a39ca9f3db7959e00abc326f5fb6b0b2f66",
      "tests/unit/test_result_previews.py": "ee00b4a254224b007ce89d6fca50fdf6806ba0381847fe93ee4bcd0b5563aa6c",
      "tests/unit/test_preview_scheduler.py": "983759e1177dcb961d4d3bd057cb2c6281761f75ec9310a31eb3430787c72404",
      "tests/unit/test_job_workers.py": "e83d56663d556c583ca16b99c613775a16e916c01128767ab6658d965257aaf3"
    }
  }
}
---

# Saved-result preview commands and lane

Evidence for [the canonical guide](../../JOB_COORDINATOR.md).
