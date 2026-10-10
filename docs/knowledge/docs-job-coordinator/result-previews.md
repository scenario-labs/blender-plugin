---
{
  "type": "Evidence",
  "id": "docs-job-coordinator.result-previews",
  "title": "Saved-result preview commands and lane",
  "evidence": {
    "path": "docs/JOB_COORDINATOR.md",
    "scope": "result-previews",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-10",
    "base_revision": "33d00b0554151c4de04731fd1a5e5c64ed50855b",
    "limits": "Inspected preview target reads, the batch, publication, discard and maintenance-only commands, bulk metadata reads for every batch size, receipt rechecks, transfer failures reported pending until the final poll while receipt and content failures fail at once, cancellation passed to preview transfers and inactive-coordinator cleanup, and the dedicated preview thread's admission, cancellation, idleness, retirement and shutdown. Offline unit tests only for these commands; no job state transition or revision change is made. Live provider behavior, UI and MCP wiring are outside this topic.",
    "sources": {
      "scenario/core/jobs/result_previews.py": "d33234f02a85f67a573ca1d097ebd8921578ba3c38047811249ac4484367c7d3",
      "scenario/core/jobs/preview_scheduler.py": "bfe2b96bad5f175a28ca71b95d6cc0d478e40ee009e55c7929724fca88898a65",
      "scenario/core/jobs/results.py": "217d9c40dddffd5cb109313e62b27d6055526b7cbb4032eb1292ef2c6d04b92e",
      "scenario/core/jobs/coordinator.py": "79c7c4aeaa4e0d9dfb9047ffcc1f5101330a7fda36ec81e8f450d8d9d072e883",
      "scenario/core/jobs/workers.py": "08f9d8488e9df9892177a2f2570422d5d3e3a35dae89796f469640d4e2b97f35",
      "tests/unit/test_result_previews.py": "937a378d1aa27ff7e9aa1ff2f086521bd62fd52d26227297029febe3d75a1fbd",
      "tests/unit/test_preview_scheduler.py": "b7aa9552994cb02a6dfabcabd24c1a1e187f6bc9bafbe9411ad859782e83376b",
      "tests/unit/test_job_workers.py": "32ea1de8ba32c30e5a1441ede694b7f740f39ab370640e1baccfd319818835f9",
      "scenario/core/jobs/transfers.py": "809323c378949b690e0cc7b1572a8e621819349e72c622f6b59f287c2bb05024"
    }
  }
}
---

# Saved-result preview commands and lane

Evidence for [the canonical guide](../../JOB_COORDINATOR.md).
