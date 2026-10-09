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
    "limits": "Reviewed the Jobs bullet against panels.SHARED_STATUS_TEXT, SHARED_OFFLINE_TEXT, progress.LABELS and the percent rule, the two-second POLL_INTERVAL with redraw on row or online access change, the stale and offline line texts and restart behaviour that needs the Refresh status or Resume download descriptor labels. ModelJobs gives a SUCCEEDED view whose results it downloads (downloads_results) a non-terminal display status, so a finished generation stays in Jobs as finished on Scenario, then downloading results and, as non-terminal ready, results saved until applied; the Image lane's automatic import ends in applied, which Generations lists. With online access off the finished row shows Download paused while online access is disabled; an installed test draws that row through the real Jobs panel and shows the download resuming once access returns. Finished Prompt Spark, Translate and Blockout records keep the terminal succeeded; installed tests inspect each with Inspect saved jobs and find it listed only in Generations. The ready row staying in Jobs until a non-Image result is applied is established by code review of JobRecord.is_terminal and the display mapping. Installed native tests on macOS arm64 Blender 5.0.1, 5.1.2 and 5.2.1 cover these claims. No desktop interaction, screenshot, other operating system or live provider progress is claimed.",
    "sources": {
      "scenario/blender/panels.py": "18b655d47e620589b822b643248d81135d7dd37aa1c23350ccfd020b797b2fdf",
      "scenario/blender/model_jobs.py": "e49b0513dbaaa8c7805da01af007b0e0ff0598ac2c52f6d9afd583a9980b4163",
      "scenario/blender/pump.py": "dca1e1db201d017f99ce2d006292b1a990a81b224639fefbc5964ce3cdff61f1",
      "scenario/core/jobs/progress.py": "bf8bea9be0d1ba3c6ca7c2495fecf61eb67481ffb7499d1e30633cc154871af5",
      "scenario/core/ui/saved_job_actions.py": "db27851f0e2026a9e418ed111d74d4ac468b2a49b84b72ab8c75446dc2a68bae",
      "tests/blender/test_model_generation.py": "9defb9e875aa425a4130ef3208994b20bb3f2c2ab27057b79d48635a13db5be7",
      "tests/blender/helpers.py": "642e7e9d178824befedb1eaf9f6344b0631af2baaf492e8c87993e533ad9d6e6",
      "tests/blender/test_prompt_tools.py": "3337cbe8e763b7436c69394e3de5b056dd2f02156acc5da3de8307267c275dde",
      "tests/blender/test_blockout_jobs.py": "6151fbd3136147da03d6221962fb8492dd67f60fa2f0748687a44b1367e575b4"
    }
  }
}
---

# Jobs panel progress wording

Evidence for [the canonical document](../../USER_GUIDE.md).
