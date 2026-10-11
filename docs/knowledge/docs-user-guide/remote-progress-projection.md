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
    "reviewed_at": "2026-10-11",
    "base_revision": "7fb15252f747f52db24f7e659f8d5048241f803e",
    "limits": "Reviewed the Jobs bullet against panels.SHARED_STATUS_TEXT, SHARED_OFFLINE_TEXT, progress.LABELS and the percent rule, the two-second POLL_INTERVAL with redraw on row or online access change, the stale and offline line texts and restart behaviour that needs the Refresh status or Resume download descriptor labels. ModelJobs gives a SUCCEEDED view whose results it downloads (downloads_results) a non-terminal display status, so a finished generation stays in Jobs as finished on Scenario, then downloading results and, as non-terminal ready, results saved until applied; the Image lane's automatic import ends in applied, which Generations lists. With online access off the finished row shows Download paused while online access is disabled; an installed test draws that row through the real Jobs panel and shows the download resuming once access returns. Finished Prompt Spark, Translate and Blockout records keep the terminal succeeded; installed tests inspect each with Inspect saved jobs and find it listed only in Generations. The ready row staying in Jobs until a non-Image result is applied is established by code review of JobRecord.is_terminal and the display mapping. Installed native tests on macOS arm64 Blender 5.0.1, 5.1.2 and 5.2.1 cover these claims. No desktop interaction, screenshot, other operating system or live provider progress is claimed.",
    "sources": {
      "scenario/blender/panels.py": "8c9ed56c0d83b4c0cfd4578e7158c05f1df895f7c2765319c0894c1ca0491e83",
      "scenario/blender/model_jobs.py": "5a378d786f8c775bf097673c9962f449a868506e234ed9e829f0d221ad059d4f",
      "scenario/blender/pump.py": "d146e694610b8ec4ca23b4577da1d792d4ae2c0dbc8d7a8a88d690571a330acd",
      "scenario/core/jobs/progress.py": "bf8bea9be0d1ba3c6ca7c2495fecf61eb67481ffb7499d1e30633cc154871af5",
      "scenario/core/ui/saved_job_actions.py": "c98f130355ee502b298532005d2f0c12ac8041a8690fe66d324aaf4deb772b04",
      "tests/blender/test_model_generation.py": "e3a6885f17b3e800ebf6e1d43c0328e2fc87f1eb3a7a903325b0f75aa4f701c4",
      "tests/blender/helpers.py": "de6a4841486130ed22e5a67d006fe859b27d2f0af5246ca4d87b9229d2a298f5",
      "tests/blender/test_prompt_tools.py": "a9c04c117248f0630d8a9f02af2df95357904fae5ae767e260a97d0531d9a10b",
      "tests/blender/test_blockout_jobs.py": "94a8e8157b551e2604229b3d5a57df0e9a74b8572476fbd527a077b4ff8a4069"
    }
  }
}
---

# Jobs panel progress wording

Evidence for [the canonical document](../../USER_GUIDE.md).
