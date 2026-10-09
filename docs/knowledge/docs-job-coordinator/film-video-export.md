---
{
  "type": "Evidence",
  "id": "docs-job-coordinator.film-video-export",
  "title": "Owned offline Film video export",
  "evidence": {
    "path": "docs/JOB_COORDINATOR.md",
    "scope": "film-video-export",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-09",
    "base_revision": "b57c398f35fb2148c82fb8b26f6a40564d3f52ef",
    "limits": "Inspected export_film and publish_film_export origin/active checks, placeholder release on render failure and retirement, issued staged-export tracking and the LocalExportWorker admission, cancellation and join. Unit tests use the actual coordinator with an offline SDK transport and simulated renders. No Scenario request or job record is involved.",
    "sources": {
      "scenario/blender/job_session.py": "96ed0e4825912df5de7dd939c8e963f7846e268326e256441e6c2e618801c55c",
      "scenario/core/jobs/coordinator.py": "08cfc053a4b27cac03e4002dab7429de06516ccdfeec9d1243a84e3414e7ba1d",
      "scenario/core/jobs/local_export.py": "ca449fe8eb3969af94534488bfadd3789c98985205dc421225431398c4a81164",
      "scenario/core/jobs/workers.py": "beb81e0452ad08b1691feebbf20a558b2c60c098ca28114d5255b4073208755d",
      "tests/unit/test_local_export.py": "e941073573fed89af84a19ff91a15d890a7af36b93896fe0e4a03c696fe325af"
    }
  }
}
---

Source evidence for [the canonical guide](../../JOB_COORDINATOR.md).
