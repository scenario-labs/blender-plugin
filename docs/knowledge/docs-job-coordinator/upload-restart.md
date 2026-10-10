---
{
  "type": "Evidence",
  "id": "docs-job-coordinator.upload-restart",
  "title": "Coordinator upload restart and part plan lifetime",
  "description": "Part plans are forgotten on deactivation; a new coordinator restarts instead of resuming.",
  "evidence": {
    "path": "docs/JOB_COORDINATOR.md",
    "scope": "upload-restart",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-10",
    "base_revision": "33d00b0554151c4de04731fd1a5e5c64ed50855b",
    "limits": "Reviewed JobCoordinator.restart_upload, deactivate() retiring cached part plans and abandoned source cleanup with offline unit tests, including a failed restart that removes its unrecorded copy and one that keeps a possibly recorded replacement. Other document claims retain their separate evidence.",
    "sources": {
      "scenario/core/jobs/coordinator.py": "bf64e6b76a4ddd71e4023c9b3085e90b1646fe722570b8fb3df0834530c78213",
      "scenario/core/jobs/uploads.py": "df83f0035ccffd13578d9fc0fffb28dfc43bf503a54b4971186230dc2b5a9f4f",
      "scenario/core/jobs/upload_store.py": "0e8f7a2799779200e666b76699948cd4c00db734fb71a92a26d9181154785f7a",
      "tests/unit/test_upload_commands.py": "fbba32b54382916d0dc5ca4b342156575435634bb805b794401b49d95473ac4a",
      "tests/unit/test_upload_inspection.py": "018582057616385030e61ad3f727ccd0409b0097ee7825d84dd5c916e51a0780"
    }
  }
}
---

# Coordinator upload restart and part plan lifetime

Evidence for [the canonical document](../../JOB_COORDINATOR.md).
