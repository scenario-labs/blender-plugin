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
    "base_revision": "72723f02a97a7226b1c697c31d8124b77ac92c86",
    "limits": "Reviewed the Jobs bullet against panels.SHARED_STATUS_TEXT, SHARED_OFFLINE_TEXT, progress.LABELS and the percent rule, the two-second POLL_INTERVAL with redraw on row or online access change, the stale and offline line texts and restart behaviour that needs the Refresh status or Resume download descriptor labels. ModelJobs gives a SUCCEEDED view whose results it downloads (downloads_results) a non-terminal display status, so a finished generation stays in Jobs as finished on Scenario, then downloading results and, as non-terminal ready, results saved until applied; the Image lane's automatic import ends in applied, which Generations lists. With online access off the finished row shows Download paused while online access is disabled; an installed test draws that row through the real Jobs panel and shows the download resuming once access returns. Finished Prompt Spark, Translate and Blockout records keep the terminal succeeded; installed tests inspect each with Inspect saved jobs and find it listed only in Generations. The ready row staying in Jobs until a non-Image result is applied is established by code review of JobRecord.is_terminal and the display mapping. Installed native tests on macOS arm64 Blender 5.0.1, 5.1.2 and 5.2.1 cover these claims. No desktop interaction, screenshot, other operating system or live provider progress is claimed.",
    "sources": {
      "scenario/blender/panels.py": "4edcd5c17b73035fa45bcd6e9d6d76252ba4b984a028f544029bf8e76d0aac1b",
      "scenario/blender/model_jobs.py": "8046852c9bb43eca3d5cb0b987c06df473b99e66cbc6cc5b66c245c38ea2f482",
      "scenario/blender/pump.py": "d146e694610b8ec4ca23b4577da1d792d4ae2c0dbc8d7a8a88d690571a330acd",
      "scenario/core/jobs/progress.py": "bf8bea9be0d1ba3c6ca7c2495fecf61eb67481ffb7499d1e30633cc154871af5",
      "scenario/core/ui/saved_job_actions.py": "db27851f0e2026a9e418ed111d74d4ac468b2a49b84b72ab8c75446dc2a68bae",
      "tests/blender/test_model_generation.py": "26f6c6d95667096e50c4df2ba93d3fa37bf253cd64245ac6ca614dc3a47291f9",
      "tests/blender/helpers.py": "de6a4841486130ed22e5a67d006fe859b27d2f0af5246ca4d87b9229d2a298f5",
      "tests/blender/test_prompt_tools.py": "3337cbe8e763b7436c69394e3de5b056dd2f02156acc5da3de8307267c275dde",
      "tests/blender/test_blockout_jobs.py": "6151fbd3136147da03d6221962fb8492dd67f60fa2f0748687a44b1367e575b4"
    }
  }
}
---

# Jobs panel progress wording

Evidence for [the canonical document](../../USER_GUIDE.md).
