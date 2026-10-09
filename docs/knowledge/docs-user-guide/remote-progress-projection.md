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
    "limits": "Reviewed the Jobs bullet against panels.SHARED_STATUS_TEXT, SHARED_OFFLINE_TEXT, progress.LABELS and the percent rule, the two-second POLL_INTERVAL with redraw on row or online access change, the stale and offline line texts and restart behaviour that needs the Refresh status or Resume download descriptor labels. The Download paused while online access is disabled wording is drawn only for a succeeded row, which the Jobs panel does not reach: ModelJobs.poll leaves that view's display status as succeeded, which JobRecord.is_terminal treats as terminal, so it is listed under Generations and that part of the Jobs bullet is not established. Installed native tests on macOS arm64 Blender 5.0.1, 5.1.2 and 5.2.1 cover these claims. No desktop interaction, screenshot, other operating system or live provider progress is claimed.",
    "sources": {
      "scenario/blender/panels.py": "18b655d47e620589b822b643248d81135d7dd37aa1c23350ccfd020b797b2fdf",
      "scenario/blender/model_jobs.py": "ba849a84b2a3d80ad307e64f77ebd17945f22fde83325ad0ae987bf004e65629",
      "scenario/blender/pump.py": "dca1e1db201d017f99ce2d006292b1a990a81b224639fefbc5964ce3cdff61f1",
      "scenario/core/jobs/progress.py": "bf8bea9be0d1ba3c6ca7c2495fecf61eb67481ffb7499d1e30633cc154871af5",
      "scenario/core/ui/saved_job_actions.py": "db27851f0e2026a9e418ed111d74d4ac468b2a49b84b72ab8c75446dc2a68bae",
      "tests/blender/test_model_generation.py": "8a198d8f3d0484306a7c7152d0ee716fe9f80d120df1ce778a4291cedbc52c41"
    }
  }
}
---

# Jobs panel progress wording

Evidence for [the canonical document](../../USER_GUIDE.md).
