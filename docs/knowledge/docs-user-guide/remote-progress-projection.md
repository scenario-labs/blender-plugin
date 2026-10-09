---
{
  "type": "Evidence",
  "id": "docs-user-guide.remote-progress-projection",
  "title": "Jobs panel progress wording",
  "description": "User-facing description of shared job status words and progress.",
  "evidence": {
    "path": "docs/USER_GUIDE.md",
    "scope": "remote-progress-projection",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-09",
    "base_revision": "fb699b8555f7cee62147794516cc7aaa224864f7",
    "limits": "Reviewed the Jobs bullet against panels.SHARED_STATUS_TEXT, SHARED_OFFLINE_TEXT, progress.LABELS and the percent rule, the two-second POLL_INTERVAL with redraw on row or online access change, the stale and offline line texts and restart behaviour that needs the Refresh status or Resume download descriptor labels. ModelJobs.poll gives a SUCCEEDED view a non-terminal display status, so a finished job stays in Jobs as finished on Scenario until its results are downloaded and, with online access off, shows Download paused while online access is disabled; an installed test draws that row through the real Jobs panel and shows the download resuming once access returns. Installed native tests on macOS arm64 Blender 5.0.1, 5.1.2 and 5.2.1 cover these claims. No desktop interaction, screenshot, other operating system or live provider progress is claimed.",
    "sources": {
      "scenario/blender/panels.py": "18b655d47e620589b822b643248d81135d7dd37aa1c23350ccfd020b797b2fdf",
      "scenario/blender/model_jobs.py": "2daeab1ce44043c115f8956bd70e08ad19a73d2e70140f72f4e8fbda7a3e524f",
      "scenario/blender/pump.py": "dca1e1db201d017f99ce2d006292b1a990a81b224639fefbc5964ce3cdff61f1",
      "scenario/core/jobs/progress.py": "bf8bea9be0d1ba3c6ca7c2495fecf61eb67481ffb7499d1e30633cc154871af5",
      "scenario/core/ui/saved_job_actions.py": "db27851f0e2026a9e418ed111d74d4ac468b2a49b84b72ab8c75446dc2a68bae",
      "tests/blender/test_model_generation.py": "bdac7e6d4f3909bf1c03abe96b49753b77f2e655728b388bcf485bb55b9669c8"
    }
  }
}
---

# Jobs panel progress wording

Evidence for [the canonical document](../../USER_GUIDE.md).
